import datetime
import platform
import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


def make_embed(desc=None, color=COLOR_DEFAULT, **kw):
    return discord.Embed(description=desc, color=color, **kw)


class Owner(commands.Cog, name="owner"):
    def __init__(self, bot):
        self.bot = bot

    async def _sync(self, context, clear, scope):
        tree = context.bot.tree
        word = "un" if clear else ""

        if scope == "global":
            if clear:
                tree.clear_commands(guild=None)
            await tree.sync()
            return await context.send(embed=make_embed(f"Slash commands have been globally {word}synchronized."))

        if scope == "guild":
            if clear:
                tree.clear_commands(guild=context.guild)
            else:
                tree.copy_global_to(guild=context.guild)
            await tree.sync(guild=context.guild)
            return await context.send(embed=make_embed(f"Slash commands have been {word}synchronized in this guild."))

        await context.send(embed=make_embed("The scope must be `global` or `guild`.", COLOR_ERROR))

    @commands.command(name="sync", description="Synchronizes the slash commands.")
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @commands.is_owner()
    async def sync(self, context, scope: str):
        await self._sync(context, False, scope)

    @commands.command(name="unsync", description="Unsynchronizes the slash commands.")
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @commands.is_owner()
    async def unsync(self, context, scope: str):
        await self._sync(context, True, scope)

    async def _manage_cog(self, context, cog, action):
        try:
            await getattr(self.bot, f"{action}_extension")(f"cogs.{cog}")
        except Exception:
            return await context.send(embed=make_embed(f"Could not {action} the `{cog}` cog.", COLOR_ERROR))
        done = {"load": "loaded", "unload": "unloaded", "reload": "reloaded"}[action]
        await context.send(embed=make_embed(f"Successfully {done} the `{cog}` cog."))

    @commands.hybrid_command(name="load", description="Load a cog")
    @app_commands.describe(cog="The name of the cog to load")
    @commands.is_owner()
    async def load(self, context, cog: str):
        await self._manage_cog(context, cog, "load")

    @commands.hybrid_command(name="unload", description="Unloads a cog.")
    @app_commands.describe(cog="The name of the cog to unload")
    @commands.is_owner()
    async def unload(self, context, cog: str):
        await self._manage_cog(context, cog, "unload")

    @commands.hybrid_command(name="reload", description="Reloads a cog.")
    @app_commands.describe(cog="The name of the cog to reload")
    @commands.is_owner()
    async def reload(self, context, cog: str):
        await self._manage_cog(context, cog, "reload")

    @commands.hybrid_command(name="shutdown", description="Make the bot shutdown.")
    @commands.is_owner()
    async def shutdown(self, context):
        await context.send(embed=make_embed("Shutting down. Bye! :wave:"))
        await self.bot.close()

    @commands.hybrid_command(name="say", description="The bot will say anything you want.")
    @app_commands.describe(message="The message that should be repeated by the bot")
    @commands.is_owner()
    async def say(self, context, *, message: str):
        await context.send(message)

    @commands.hybrid_command(name="embed", description="The bot will say anything you want, but within embeds.")
    @app_commands.describe(message="The message that should be repeated by the bot")
    @commands.is_owner()
    async def embed(self, context, *, message: str):
        await context.send(embed=make_embed(message))

    @commands.hybrid_command(name="servers", description="Lists all the servers the bot is in with an invite link.")
    @commands.is_owner()
    async def servers(self, context):
        if not self.bot.guilds:
            return await context.send(embed=make_embed("The bot is not in any server.", COLOR_ERROR))

        embed = discord.Embed(title=f"Servers ({len(self.bot.guilds)})", color=COLOR_ACCENT)
        for guild in sorted(self.bot.guilds, key=lambda g: g.name.lower()):
            invite_url = "N/A"
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    try:
                        invite_url = (await channel.create_invite(max_age=0, max_uses=0, unique=False)).url
                        break
                    except discord.HTTPException:
                        continue
            owner = guild.owner.mention if guild.owner else "Unknown"
            embed.add_field(
                name=f"{guild.name} ({guild.id})",
                value=f"Owner: {owner}\nMembers: {guild.member_count}\n[Invite]({invite_url})",
                inline=False,
            )
        await context.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="Displays the bot's resource usage and general information.")
    @commands.is_owner()
    async def botinfo(self, context):
        process = psutil.Process()
        with process.oneshot():
            cpu = process.cpu_percent(interval=0.5)
            ram = process.memory_info().rss / (1024 * 1024)
        uptime = str(datetime.timedelta(seconds=int(time.time() - self.bot.start_time)))

        embed = discord.Embed(title="Bot Information", color=COLOR_ACCENT)
        fields = (
            ("CPU Usage", f"{cpu:.2f}%"),
            ("RAM Usage", f"{ram:.2f} MB"),
            ("Uptime", uptime),
            ("Servers", len(self.bot.guilds)),
            ("Discord.py Version", discord.__version__),
            ("Python Version", platform.python_version()),
            ("System", f"{platform.system()} {platform.release()}"),
        )
        for name, value in fields:
            embed.add_field(name=name, value=str(value))
        await context.send(embed=embed)

    @commands.hybrid_command(name="broadcast", description="Send a message to every server the bot is in.")
    @app_commands.describe(message="The message to broadcast")
    @commands.is_owner()
    async def broadcast(self, context, *, message: str):
        await context.defer()
        embed = make_embed(message, COLOR_ACCENT)
        sent = failed = 0
        for guild in self.bot.guilds:
            channel = guild.system_channel
            if not channel or not channel.permissions_for(guild.me).send_messages:
                channel = next(
                    (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                    None,
                )
            if not channel:
                failed += 1
                continue
            try:
                await channel.send(embed=embed)
                sent += 1
            except discord.HTTPException:
                failed += 1
        await context.send(embed=make_embed(
            f"Broadcast sent to {sent}/{len(self.bot.guilds)} server(s). Failed: {failed}."
        ))

    @commands.hybrid_command(name="setup_suggestions", description="Set the global channel where user suggestions will be sent.")
    @commands.is_owner()
    async def setup_suggestions(self, context, channel: discord.TextChannel):
        await self.bot.database.set_owner_suggestion_channel(channel.id)
        await context.send(embed=make_embed(f"Suggestion channel set to {channel.mention}.", COLOR_ACCENT))


async def setup(bot):
    await bot.add_cog(Owner(bot))