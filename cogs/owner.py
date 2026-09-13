import datetime
import platform
import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


class Owner(commands.Cog, name="owner"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="sync", description="Synchronizes the slash commands.")
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @commands.is_owner()
    async def sync(self, context: Context, scope: str) -> None:
        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(description="Slash commands have been globally synchronized.", color=COLOR_DEFAULT)
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(description="Slash commands have been synchronized in this guild.", color=COLOR_DEFAULT)
            await context.send(embed=embed)
            return
        embed = discord.Embed(description="The scope must be `global` or `guild`.", color=COLOR_ERROR)
        await context.send(embed=embed)

    @commands.command(name="unsync", description="Unsynchronizes the slash commands.")
    @app_commands.describe(scope="The scope of the sync. Can be `global`, `current_guild` or `guild`")
    @commands.is_owner()
    async def unsync(self, context: Context, scope: str) -> None:
        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(description="Slash commands have been globally unsynchronized.", color=COLOR_DEFAULT)
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(description="Slash commands have been unsynchronized in this guild.", color=COLOR_DEFAULT)
            await context.send(embed=embed)
            return
        embed = discord.Embed(description="The scope must be `global` or `guild`.", color=COLOR_ERROR)
        await context.send(embed=embed)

    @commands.hybrid_command(name="load", description="Load a cog")
    @app_commands.describe(cog="The name of the cog to load")
    @commands.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        try:
            await self.bot.load_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(description=f"Could not load the `{cog}` cog.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return
        embed = discord.Embed(description=f"Successfully loaded the `{cog}` cog.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @commands.hybrid_command(name="unload", description="Unloads a cog.")
    @app_commands.describe(cog="The name of the cog to unload")
    @commands.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(description=f"Could not unload the `{cog}` cog.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return
        embed = discord.Embed(description=f"Successfully unloaded the `{cog}` cog.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @commands.hybrid_command(name="reload", description="Reloads a cog.")
    @app_commands.describe(cog="The name of the cog to reload")
    @commands.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(description=f"Could not reload the `{cog}` cog.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return
        embed = discord.Embed(description=f"Successfully reloaded the `{cog}` cog.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @commands.hybrid_command(name="shutdown", description="Make the bot shutdown.")
    @commands.is_owner()
    async def shutdown(self, context: Context) -> None:
        embed = discord.Embed(description="Shutting down. Bye! :wave:", color=COLOR_DEFAULT)
        await context.send(embed=embed)
        await self.bot.close()

    @commands.hybrid_command(name="say", description="The bot will say anything you want.")
    @app_commands.describe(message="The message that should be repeated by the bot")
    @commands.is_owner()
    async def say(self, context: Context, *, message: str) -> None:
        await context.send(message)

    @commands.hybrid_command(name="embed", description="The bot will say anything you want, but within embeds.")
    @app_commands.describe(message="The message that should be repeated by the bot")
    @commands.is_owner()
    async def embed(self, context: Context, *, message: str) -> None:
        embed = discord.Embed(description=message, color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="Displays the bot's resource usage and general information.")
    @commands.is_owner()
    async def botinfo(self, context: Context) -> None:
        process = psutil.Process()
        with process.oneshot():
            cpu_usage = process.cpu_percent(interval=0.5)
            ram_usage = process.memory_info().rss / (1024 * 1024)

        uptime_seconds = time.time() - self.bot.start_time
        uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))

        guild_count = len(self.bot.guilds)

        embed = discord.Embed(title="Bot Information", color=COLOR_ACCENT)
        embed.add_field(name="CPU Usage", value=f"{cpu_usage:.2f}%", inline=True)
        embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB", inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Servers", value=f"{guild_count}", inline=True)
        embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
        embed.add_field(name="System", value=f"{platform.system()} {platform.release()}", inline=True)
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Owner(bot))