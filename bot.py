import logging
import os
import platform
import time
from pathlib import Path

import aiosqlite
import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import DatabaseManager

load_dotenv()

ROOT = Path(__file__).resolve().parent
ERROR_COLOR = 0xE02B2B


class LoggingFormatter(logging.Formatter):
    RESET = "\x1b[0m"
    LEVEL_COLORS = {
        logging.DEBUG: "\x1b[38m\x1b[1m",
        logging.INFO: "\x1b[34m\x1b[1m",
        logging.WARNING: "\x1b[33m\x1b[1m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[31m\x1b[1m",
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        fmt = (f"\x1b[30m\x1b[1m{{asctime}}{self.RESET} {color}{{levelname:<8}}{self.RESET} "
               f"\x1b[32m\x1b[1m{{name}}{self.RESET} {{message}}")
        return logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S", style="{").format(record)


def setup_logger():
    logger = logging.getLogger("discord_bot")
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(LoggingFormatter())

    file = logging.FileHandler("discord.log", encoding="utf-8", mode="w")
    file.setFormatter(logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"))

    logger.addHandler(console)
    logger.addHandler(file)
    return logger


logger = setup_logger()


def build_intents():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True
    return intents


class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
            intents=build_intents(),
            help_command=None,
            activity=discord.Game("/help"),
        )
        self.logger = logger
        self.database = None
        self.bot_prefix = os.getenv("PREFIX")
        self.invite_link = os.getenv("INVITE_LINK")
        self.start_time = time.time()
        self.db_filename = os.getenv("DB_FILENAME", "database.db")
        self.db_path = ROOT / "database" / self.db_filename

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            await db.commit()

    async def load_cogs(self):
        for file in (ROOT / "cogs").iterdir():
            if file.suffix != ".py":
                continue
            extension = file.stem
            try:
                await self.load_extension(f"cogs.{extension}")
                self.logger.info(f"Loaded extension '{extension}'")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}\n{type(e).__name__}: {e}")

    async def setup_hook(self):
        for line in (
            f"Logged in as {self.user.name}",
            f"discord.py API version: {discord.__version__}",
            f"Python version: {platform.python_version()}",
            f"Running on: {platform.system()} {platform.release()} ({os.name})",
            f"Using database file: {self.db_filename}",
            "-------------------",
        ):
            self.logger.info(line)
        await self.init_db()
        await self.load_cogs()
        self.database = DatabaseManager(connection=await aiosqlite.connect(self.db_path))

    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context):
        name = context.command.qualified_name.split(" ")[0]
        where = f"in {context.guild.name} (ID: {context.guild.id})" if context.guild else "in DMs"
        self.logger.info(f"Executed {name} command {where} by {context.author} (ID: {context.author.id})")

    async def on_command_error(self, context, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            parts = []
            if (h := round(hours % 24)): parts.append(f"{h} hours")
            if (m := round(minutes)): parts.append(f"{m} minutes")
            if (s := round(seconds)): parts.append(f"{s} seconds")
            desc = f"**Please slow down** - You can use this command again in {' '.join(parts)}."

        elif isinstance(error, commands.NotOwner):
            desc = "You are not the owner of the bot!"
            where = (f"the guild {context.guild.name} (ID: {context.guild.id})"
                     if context.guild else "the bot's DMs")
            self.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute an owner only "
                f"command in {where}, but the user is not an owner of the bot.")

        elif isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
            if isinstance(error, commands.MissingPermissions):
                desc = f"You are missing the permission(s) `{', '.join(error.missing_permissions)}` to execute this command!"
            else:
                desc = f"I am missing the permission(s) `{', '.join(error.missing_permissions)}` to fully perform this command!"

        elif isinstance(error, commands.MissingRequiredArgument):
            await context.send(embed=discord.Embed(
                title="Error!", description=str(error).capitalize(), color=ERROR_COLOR))
            return

        else:
            self.logger.error(f"Unhandled command error: {error}")
            raise error

        await context.send(embed=discord.Embed(description=desc, color=ERROR_COLOR))


bot = DiscordBot()
bot.run(os.getenv("TOKEN"))