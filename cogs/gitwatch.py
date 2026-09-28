import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR

GITHUB_REPO = "kame1312/DarkSide-Project"
BRANCH = "main"
FEED_URL = f"https://github.com/{GITHUB_REPO}/commits/{BRANCH}.atom"
CHECK_INTERVAL = 60
CONFIG_PATH = Path(__file__).resolve().parent.parent / "gitwatch.json"
NS = {"a": "http://www.w3.org/2005/Atom"}


class GitWatch(commands.Cog, name="gitwatch"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.channel_id = None
        self.last_commit_id = None
        self.session = None
        self._load_config()

    def _load_config(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            self.channel_id = data.get("channel_id")
            self.last_commit_id = data.get("last_commit_id")
        except Exception:
            pass

    def _save_config(self) -> None:
        try:
            CONFIG_PATH.write_text(
                json.dumps({"channel_id": self.channel_id, "last_commit_id": self.last_commit_id}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()
        self.poll_feed.start()

    def cog_unload(self) -> None:
        self.poll_feed.cancel()
        if self.session:
            asyncio.create_task(self.session.close())

    async def _fetch_commits(self) -> list:
        if self.session is None:
            return []
        try:
            async with self.session.get(FEED_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
        except Exception:
            return []

        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []

        commits = []
        for entry in root.findall("a:entry", NS):
            entry_id = entry.find("a:id", NS)
            title = entry.find("a:title", NS)
            link = entry.find("a:link", NS)
            updated = entry.find("a:updated", NS)
            author = entry.find("a:author/a:name", NS)
            commits.append({
                "id": entry_id.text if entry_id is not None else "",
                "title": title.text if title is not None else "No title",
                "link": link.attrib.get("href", "") if link is not None else "",
                "updated": updated.text if updated is not None else "",
                "author": author.text if author is not None else "Unknown",
            })
        return commits

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def poll_feed(self) -> None:
        if self.channel_id is None:
            return
        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            return

        commits = await self._fetch_commits()
        if not commits:
            return

        if self.last_commit_id is None:
            self.last_commit_id = commits[0]["id"]
            self._save_config()
            return

        new_commits = []
        for commit in commits:
            if commit["id"] == self.last_commit_id:
                break
            new_commits.append(commit)

        if not new_commits:
            return

        self.last_commit_id = commits[0]["id"]
        self._save_config()

        for commit in reversed(new_commits):
            embed = discord.Embed(
                title=commit["title"],
                url=commit["link"],
                description=f"Pushed by **{commit['author']}**",
                color=COLOR_ACCENT,
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                continue

    @poll_feed.before_loop
    async def before_poll(self) -> None:
        await self.bot.wait_until_ready()

    @commands.group(name="gitwatch", description="Configure the GitHub push notifications.")
    @commands.is_owner()
    async def gitwatch(self, context: Context) -> None:
        embed = discord.Embed(description="Use `gitwatch setchannel`, `gitwatch disable` or `gitwatch test`.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @gitwatch.command(name="setchannel", description="Set the channel where git pushes are posted.")
    @app_commands.describe(channel="The channel to post new commits in")
    @commands.is_owner()
    async def setchannel(self, context: Context, channel: discord.TextChannel) -> None:
        self.channel_id = channel.id
        self.last_commit_id = None
        self._save_config()
        embed = discord.Embed(description=f"Git push notifications will be posted in {channel.mention}.", color=COLOR_ACCENT)
        await context.send(embed=embed)

    @gitwatch.command(name="disable", description="Disable git push notifications.")
    @commands.is_owner()
    async def disable(self, context: Context) -> None:
        self.channel_id = None
        self._save_config()
        embed = discord.Embed(description="Git push notifications disabled.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @gitwatch.command(name="test", description="Force a check of the GitHub feed.")
    @commands.is_owner()
    async def test(self, context: Context) -> None:
        commits = await self._fetch_commits()
        if not commits:
            embed = discord.Embed(description="Could not fetch the GitHub feed.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return
        latest = commits[0]
        embed = discord.Embed(
            title=latest["title"],
            url=latest["link"],
            description=f"Pushed by **{latest['author']}**",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(GitWatch(bot))