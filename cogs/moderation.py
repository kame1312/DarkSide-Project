import os
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        config = await self.bot.database.get_welcome_config(member.guild.id)
        if not config:
            return

        channel_id, message = config
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if channel is None:
            return

        try:
            text = (message or "Welcome {user} to **{guild}**!").format(
                user=member.mention,
                user_name=member.name,
                user_display=member.display_name,
                guild=member.guild.name,
                member_count=member.guild.member_count,
            )
        except (KeyError, IndexError):
            text = f"Welcome {member.mention} to **{member.guild.name}**!"

        embed = discord.Embed(description=text, color=COLOR_DEFAULT)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")

        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.Forbidden:
            pass

    @commands.hybrid_command(name="kick", description="Kick a user out of the server.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(user="The user that should be kicked.", reason="The reason why the user should be kicked.")
    async def kick(self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.guild_permissions.administrator:
            embed = discord.Embed(description="User has administrator permissions.", color=COLOR_ERROR)
            await context.send(embed=embed)
        else:
            try:
                embed = discord.Embed(description=f"**{member}** was kicked by **{context.author}**!", color=COLOR_DEFAULT)
                embed.add_field(name="Reason:", value=reason)
                await context.send(embed=embed)
                try:
                    await member.send(f"You were kicked by **{context.author}** from **{context.guild.name}**!\nReason: {reason}")
                except discord.Forbidden:
                    pass
                await member.kick(reason=reason)
            except Exception:
                embed = discord.Embed(description="An error occurred while trying to kick the user. Make sure my role is above the role of the user you want to kick.", color=COLOR_ERROR)
                await context.send(embed=embed)

    @commands.hybrid_command(name="nick", description="Change the nickname of a user on a server.")
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @app_commands.describe(user="The user that should have a new nickname.", nickname="The new nickname that should be set.")
    async def nick(self, context: Context, user: discord.User, *, nickname: str = None) -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        try:
            await member.edit(nick=nickname)
            embed = discord.Embed(description=f"**{member}'s** new nickname is **{nickname}**!", color=COLOR_DEFAULT)
            await context.send(embed=embed)
        except Exception:
            embed = discord.Embed(description="An error occurred while trying to change the nickname of the user. Make sure my role is above the role of the user you want to change the nickname.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @commands.hybrid_command(name="ban", description="Bans a user from the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(user="The user that should be banned.", reason="The reason why the user should be banned.")
    async def ban(self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        try:
            if member.guild_permissions.administrator:
                embed = discord.Embed(description="User has administrator permissions.", color=COLOR_ERROR)
                await context.send(embed=embed)
            else:
                embed = discord.Embed(description=f"**{member}** was banned by **{context.author}**!", color=COLOR_DEFAULT)
                embed.add_field(name="Reason:", value=reason)
                await context.send(embed=embed)
                try:
                    await member.send(f"You were banned by **{context.author}** from **{context.guild.name}**!\nReason: {reason}")
                except discord.Forbidden:
                    pass
                await member.ban(reason=reason)
        except Exception:
            embed = discord.Embed(title="Error!", description="An error occurred while trying to ban the user. Make sure my role is above the role of the user you want to ban.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @commands.hybrid_group(name="warning", description="Manage warnings of a user on a server.")
    @commands.has_permissions(manage_messages=True)
    async def warning(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            embed = discord.Embed(description="Please specify a subcommand.\n\n**Subcommands:**\n`add` - Add a warning to a user.\n`remove` - Remove a warning from a user.\n`list` - List all warnings of a user.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @warning.command(name="add", description="Adds a warning to a user in the server.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(user="The user that should be warned.", reason="The reason why the user should be warned.")
    async def warning_add(self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        total = await self.bot.database.add_warn(user.id, context.guild.id, context.author.id, reason)
        embed = discord.Embed(description=f"**{member}** was warned by **{context.author}**!\nTotal warns for this user: {total}", color=COLOR_DEFAULT)
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)
        try:
            await member.send(f"You were warned by **{context.author}** in **{context.guild.name}**!\nReason: {reason}")
        except discord.Forbidden:
            await context.send(f"{member.mention}, you were warned by **{context.author}**!\nReason: {reason}")

    @warning.command(name="remove", description="Removes a warning from a user in the server.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(user="The user that should get their warning removed.", warn_id="The ID of the warning that should be removed.")
    async def warning_remove(self, context: Context, user: discord.User, warn_id: int) -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        total = await self.bot.database.remove_warn(warn_id, user.id, context.guild.id)
        embed = discord.Embed(description=f"I've removed the warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total}", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @warning.command(name="list", description="Shows the warnings of a user in the server.")
    @commands.has_guild_permissions(manage_messages=True)
    @app_commands.describe(user="The user you want to get the warnings of.")
    async def warning_list(self, context: Context, user: discord.User) -> None:
        warnings_list = await self.bot.database.get_warnings(user.id, context.guild.id)
        embed = discord.Embed(title=f"Warnings of {user}", color=COLOR_DEFAULT)
        description = ""
        if len(warnings_list) == 0:
            description = "This user has no warnings."
        else:
            for warning in warnings_list:
                description += f"• Warned by <@{warning[2]}>: **{warning[3]}** (<t:{warning[4]}>) - Warn ID #{warning[5]}\n"
        embed.description = description
        await context.send(embed=embed)

    @commands.hybrid_command(name="purge", description="Delete a number of messages.")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @app_commands.describe(amount="The amount of messages that should be deleted.")
    async def purge(self, context: Context, amount: int) -> None:
        await context.send("Deleting messages...")
        purged_messages = await context.channel.purge(limit=amount + 1)
        embed = discord.Embed(description=f"**{context.author}** cleared **{len(purged_messages)-1}** messages!", color=COLOR_DEFAULT)
        await context.channel.send(embed=embed)

    @commands.hybrid_command(name="hackban", description="Bans a user without the user having to be in the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(user_id="The user ID that should be banned.", reason="The reason why the user should be banned.")
    async def hackban(self, context: Context, user_id: str, *, reason: str = "Not specified") -> None:
        try:
            await self.bot.http.ban(user_id, context.guild.id, reason=reason)
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            embed = discord.Embed(description=f"**{user}** (ID: {user_id}) was banned by **{context.author}**!", color=COLOR_DEFAULT)
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)
        except Exception:
            embed = discord.Embed(description="An error occurred while trying to ban the user. Make sure ID is an existing ID that belongs to a user.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @commands.hybrid_command(name="archive", description="Archives in a text file the last messages with a chosen limit of messages.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(limit="The limit of messages that should be archived.")
    async def archive(self, context: Context, limit: int = 10) -> None:
        log_file = f"{context.channel.id}.log"
        with open(log_file, "w", encoding="UTF-8") as f:
            f.write(f'Archived messages from: #{context.channel} ({context.channel.id}) in the guild "{context.guild}" ({context.guild.id}) at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}\n')
            async for message in context.channel.history(limit=limit, before=context.message):
                attachments = []
                for attachment in message.attachments:
                    attachments.append(attachment.url)
                attachments_text = f"[Attached File{'s' if len(attachments) >= 2 else ''}: {', '.join(attachments)}]" if len(attachments) >= 1 else ""
                f.write(f"{message.created_at.strftime('%d.%m.%Y %H:%M:%S')} {message.author} {message.id}: {message.clean_content} {attachments_text}\n")
        f = discord.File(log_file)
        await context.send(file=f)
        os.remove(log_file)

    @commands.hybrid_command(name="mute", description="Temporarily timeout a user.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(user="The user that should be muted.", duration="Duration of the mute in minutes.", reason="The reason why the user should be muted.")
    async def mute(self, context: Context, user: discord.User, duration: int, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.id == context.author.id:
            embed = discord.Embed(description="You cannot mute yourself.", color=COLOR_ERROR)
            await context.send(embed=embed, ephemeral=True)
            return
        if member.top_role >= context.author.top_role and context.guild.owner_id != context.author.id:
            embed = discord.Embed(description="You cannot mute someone with a higher or equal role.", color=COLOR_ERROR)
            await context.send(embed=embed, ephemeral=True)
            return
        try:
            delta = timedelta(minutes=duration)
            await member.timeout(delta, reason=f"Action by {context.author} | Reason: {reason}")
            embed = discord.Embed(description=f"**{member}** was muted by **{context.author}** for **{duration} minute(s)**!", color=COLOR_DEFAULT)
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)
            try:
                await member.send(f"You were muted by **{context.author}** in **{context.guild.name}** for **{duration} minute(s)**!\nReason: {reason}")
            except discord.Forbidden:
                pass
        except Exception:
            embed = discord.Embed(description="An error occurred while trying to mute the user. Make sure my role is above the role of the user you want to mute.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @commands.hybrid_command(name="unmute", description="Remove a timeout from a user.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(user="The user that should be unmuted.")
    async def unmute(self, context: Context, user: discord.User) -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        try:
            await member.timeout(None, reason=f"Unmuted by {context.author}")
            embed = discord.Embed(description=f"**{member}** was unmuted by **{context.author}**!", color=COLOR_DEFAULT)
            await context.send(embed=embed)
        except Exception:
            embed = discord.Embed(description="An error occurred while trying to unmute the user.", color=COLOR_ERROR)
            await context.send(embed=embed)

    @commands.hybrid_group(name="welcome", description="Configure the welcome message for the server.")
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                description=(
                    "Please specify a subcommand.\n\n**Subcommands:**\n"
                    "`channel` - Set the welcome channel.\n"
                    "`message` - Set the welcome message.\n"
                    "`test` - Send a preview of the welcome message.\n"
                    "`disable` - Disable the welcome message.\n\n"
                    "**Available placeholders:**\n"
                    "`{user}` - Mentions (pings) the new member\n"
                    "`{user_name}` - The member's username\n"
                    "`{user_display}` - The member's server display name\n"
                    "`{guild}` - The server name\n"
                    "`{member_count}` - The number of members in the server"
                ),
                color=COLOR_DEFAULT,
            )
            await context.send(embed=embed)

    @welcome.command(name="channel", description="Set the channel where welcome messages will be sent.")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    @app_commands.describe(channel="The welcome channel.")
    async def welcome_channel(self, context: Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_welcome_channel(context.guild.id, channel.id)
        embed = discord.Embed(description=f"Welcome channel has been set to {channel.mention}.", color=COLOR_DEFAULT)
        await context.send(embed=embed)

    @welcome.command(name="message", description="Set the welcome message.")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(message="The welcome message. Use {user} to ping the new member.")
    async def welcome_message(self, context: Context, *, message: str) -> None:
        await self.bot.database.set_welcome_message(context.guild.id, message)
        embed = discord.Embed(description="The welcome message has been updated!", color=COLOR_DEFAULT)
        preview = (
            message.replace("{user}", context.author.mention)
            .replace("{user_name}", context.author.name)
            .replace("{user_display}", context.author.display_name)
            .replace("{guild}", context.guild.name)
            .replace("{member_count}", str(context.guild.member_count))
        )
        embed.add_field(name="Preview:", value=preview[:1024], inline=False)
        await context.send(embed=embed)

    @welcome.command(name="test", description="Send a preview of the welcome message in the configured channel.")
    @commands.has_permissions(manage_guild=True)
    async def welcome_test(self, context: Context) -> None:
        config = await self.bot.database.get_welcome_config(context.guild.id)
        if not config or not config[0]:
            embed = discord.Embed(description="No welcome channel is set. Use `/welcome channel` first.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return

        channel_id, message = config
        channel = context.guild.get_channel(channel_id)
        if channel is None:
            embed = discord.Embed(description="The configured channel no longer exists. Please set it again with `/welcome channel`.", color=COLOR_ERROR)
            await context.send(embed=embed)
            return

        text = (message or "Welcome {user} to **{guild}**!").format(
            user=context.author.mention,
            user_name=context.author.name,
            user_display=context.author.display_name,
            guild=context.guild.name,
            member_count=context.guild.member_count,
        )

        preview_embed = discord.Embed(description=text, color=COLOR_DEFAULT)
        preview_embed.set_thumbnail(url=context.author.display_avatar.url)
        preview_embed.set_footer(text=f"Member #{context.guild.member_count}")
        await channel.send(content=context.author.mention, embed=preview_embed)

        confirm = discord.Embed(description=f"Preview sent to {channel.mention}.", color=COLOR_DEFAULT)
        await context.send(embed=confirm, ephemeral=True)

    @welcome.command(name="disable", description="Disable the welcome message.")
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, context: Context) -> None:
        await self.bot.database.set_welcome_channel(context.guild.id, None)
        embed = discord.Embed(description="The welcome message has been disabled.", color=COLOR_DEFAULT)
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Moderation(bot))