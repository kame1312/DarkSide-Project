import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR

GITHUB_REPO = "kame1312/DarkSide-Project"
FEED_URL = f"https://github.com/{GITHUB_REPO}/commits/main.atom"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "gitwatch.json"
NS = {"a": "http://www.w3.org/2005/Atom"}


def make_embed(desc=None, color=COLOR_DEFAULT, **kw):
    return discord.Embed(description=desc, color=color, **kw)


class GitWatch(commands.Cog, name="gitwatch"):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = None
        self.last_commit_id = None
        self.session = None
        self._load_config()

    def _load_config(self):
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            self.channel_id = data.get("channel_id")
            self.last_commit_id = data.get("last_commit_id")
        except Exception:
            pass

    def _save_config(self):
        try:
            CONFIG_PATH.write_text(
                json.dumps({"channel_id": self.channel_id, "last_commit_id": self.last_commit_id}, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.poll_feed.start()

    def cog_unload(self):
        self.poll_feed.cancel()
        if self.session:
            asyncio.create_task(self.session.close())

    async def _fetch_commits(self):
        if self.session is None:
            return []
        try:
            async with self.session.get(FEED_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                root = ET.fromstring(await resp.text())
        except Exception:
            return []

        commits = []
        for entry in root.findall("a:entry", NS):
            def text(tag):
                node = entry.find(f"a:{tag}", NS)
                return node.text if node is not None else None
            link = entry.find("a:link", NS)
            commits.append({
                "id": text("id") or "",
                "title": text("title") or "No title",
                "link": link.attrib.get("href", "") if link is not None else "",
                "author": text("author/a:name") or "Unknown",
            })
        return commits

    @staticmethod
    def _commit_embed(commit):
        return discord.Embed(
            title=commit["title"], url=commit["link"],
            description=f"Pushed by **{commit['author']}**", color=COLOR_ACCENT)

    @tasks.loop(seconds=60)
    async def poll_feed(self):
        channel = self.bot.get_channel(self.channel_id) if self.channel_id else None
        if channel is None:
            return

        commits = await self._fetch_commits()
        if not commits:
            return
        if self.last_commit_id is None:
            self.last_commit_id = commits[0]["id"]
            return self._save_config()

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
            try:
                await channel.send(embed=self._commit_embed(commit))
            except discord.HTTPException:
                continue

    @poll_feed.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()

    @commands.group(name="gitwatch", description="Configure the GitHub push notifications.")
    @commands.is_owner()
    async def gitwatch(self, context):
        await context.send(embed=make_embed("Use `gitwatch setchannel`, `gitwatch disable` or `gitwatch test`."))

    @gitwatch.command(name="setchannel", description="Set the channel where git pushes are posted.")
    @app_commands.describe(channel="The channel to post new commits in")
    @commands.is_owner()
    async def setchannel(self, context, channel: discord.TextChannel):
        self.channel_id, self.last_commit_id = channel.id, None
        self._save_config()
        await context.send(embed=make_embed(f"Git push notifications will be posted in {channel.mention}.", COLOR_ACCENT))

    @gitwatch.command(name="disable", description="Disable git push notifications.")
    @commands.is_owner()
    async def disable(self, context):
        self.channel_id = None
        self._save_config()
        await context.send(embed=make_embed("Git push notifications disabled."))

    @gitwatch.command(name="test", description="Force a check of the GitHub feed.")
    @commands.is_owner()
    async def test(self, context):
        commits = await self._fetch_commits()
        if not commits:
            return await context.send(embed=make_embed("Could not fetch the GitHub feed.", COLOR_ERROR))
        await context.send(embed=self._commit_embed(commits[0]))


async def setup(bot):
    await bot.add_cog(GitWatch(bot))