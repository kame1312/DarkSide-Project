"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import platform

import discord
from helpers.colors import COLOR_DEFAULT, COLOR_ERROR, COLOR_ACCENT
from discord.ext import commands
from discord.ext.commands import Context


class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="help", description="List all commands the bot has loaded."
    )
    async def help(self, context: Context) -> None:
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=COLOR_DEFAULT
        )
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner" and not (await self.bot.is_owner(context.author)):
                continue
            cog_commands = cog.get_commands()
            if not cog_commands:
                continue
            data = []
            for command in cog_commands:
                description = (command.description or command.help or "No description").partition("\n")[0]
                data.append(f"{command.name} - {description}")
                # Also list subcommands so groups don't hide their commands from /help
                if isinstance(command, commands.Group):
                    for sub in command.commands:
                        sub_description = (sub.description or sub.help or "No description").partition("\n")[0]
                        data.append(f"  └ {command.name} {sub.name} - {sub_description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=cog_name.replace("_", " ").title(),
                value=f"```{help_text}```",
                inline=False,
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="serverinfo",
        description="Get some useful (or not) information about the server.",
    )
    async def serverinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in context.guild.roles]
        num_roles = len(roles)
        if num_roles > 50:
            roles = roles[:50]
            roles.append(f">>>> Displaying [50/{num_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**Server Name:**", description=f"{context.guild}", color=COLOR_DEFAULT
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="Server ID", value=context.guild.id)
        embed.add_field(name="Member Count", value=context.guild.member_count)
        embed.add_field(
            name="Text/Voice Channels", value=f"{len(context.guild.channels)}"
        )
        embed.add_field(name=f"Roles ({len(context.guild.roles)})", value=roles, inline=False)
        embed.add_field(
            name="Created at",
            value=discord.utils.format_dt(context.guild.created_at, style="F"),
            inline=False,
        )
        embed.set_footer(text=f"Server ID: {context.guild.id}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=COLOR_DEFAULT,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="invite",
        description="Get the invite link of the bot to be able to invite it.",
    )
    async def invite(self, context: Context) -> None:
        """
        Get the invite link of the bot to be able to invite it.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description=f"Invite me by clicking [here]({self.bot.invite_link}).",
            color=COLOR_ACCENT,
        )
        try:
            await context.author.send(embed=embed)
            await context.send("I sent you a private message!")
        except discord.Forbidden:
            await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(General(bot))