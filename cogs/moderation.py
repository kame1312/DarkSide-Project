import os
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


def make_embed(desc=None, color=COLOR_DEFAULT, **kw):
    return discord.Embed(description=desc, color=color, **kw)


def format_welcome(template, member):
    try:
        return template.format(
            user=member.mention, user_name=member.name, user_display=member.display_name,
            guild=member.guild.name, member_count=member.guild.member_count,
        )
    except (KeyError, IndexError):
        return f"Welcome {member.mention} to **{member.guild.name}**!"


class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.bot.database.get_welcome_config(member.guild.id)
        if not config or not config[0]:
            return
        channel = member.guild.get_channel(config[0])
        if not channel:
            return
        embed = make_embed(format_welcome(config[1] or "Welcome {user} to **{guild}**!", member))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.Forbidden:
            pass

    async def _punish(self, context, user, action, reason):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.guild_permissions.administrator:
            return await context.send(embed=make_embed("User has administrator permissions.", COLOR_ERROR))

        past = {"kick": "kicked", "ban": "banned"}[action]
        embed = make_embed(f"**{member}** was {past} by **{context.author}**!")
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)
        try:
            await member.send(f"You were {past} by **{context.author}** from **{context.guild.name}**!\nReason: {reason}")
        except discord.Forbidden:
            pass
        try:
            await getattr(member, action)(reason=reason)
        except Exception:
            await context.send(embed=make_embed(
                f"An error occurred while trying to {action} the user. "
                f"Make sure my role is above the role of the user you want to {action}.", COLOR_ERROR))

    @commands.hybrid_command(name="kick", description="Kick a user out of the server.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(user="The user that should be kicked.", reason="The reason why the user should be kicked.")
    async def kick(self, context, user: discord.User, *, reason: str = "Not specified"):
        await self._punish(context, user, "kick", reason)

    @commands.hybrid_command(name="ban", description="Bans a user from the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(user="The user that should be banned.", reason="The reason why the user should be banned.")
    async def ban(self, context, user: discord.User, *, reason: str = "Not specified"):
        await self._punish(context, user, "ban", reason)

    @commands.hybrid_command(name="nick", description="Change the nickname of a user on a server.")
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @app_commands.describe(user="The user that should have a new nickname.", nickname="The new nickname that should be set.")
    async def nick(self, context, user: discord.User, *, nickname: str = None):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        try:
            await member.edit(nick=nickname)
            await context.send(embed=make_embed(f"**{member}'s** new nickname is **{nickname}**!"))
        except Exception:
            await context.send(embed=make_embed(
                "An error occurred while trying to change the nickname of the user. "
                "Make sure my role is above the role of the user you want to change the nickname.", COLOR_ERROR))

    @commands.hybrid_group(name="warning", description="Manage warnings of a user on a server.")
    @commands.has_permissions(manage_messages=True)
    async def warning(self, context):
        if context.invoked_subcommand is None:
            await context.send(embed=make_embed(
                "Please specify a subcommand.\n\n**Subcommands:**\n"
                "`add` - Add a warning to a user.\n"
                "`remove` - Remove a warning from a user.\n"
                "`list` - List all warnings of a user.", COLOR_ERROR))

    @warning.command(name="add", description="Adds a warning to a user in the server.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(user="The user that should be warned.", reason="The reason why the user should be warned.")
    async def warning_add(self, context, user: discord.User, *, reason: str = "Not specified"):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        total = await self.bot.database.add_warn(user.id, context.guild.id, context.author.id, reason)
        embed = make_embed(f"**{member}** was warned by **{context.author}**!\nTotal warns for this user: {total}")
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)
        try:
            await member.send(f"You were warned by **{context.author}** in **{context.guild.name}**!\nReason: {reason}")
        except discord.Forbidden:
            await context.send(f"{member.mention}, you were warned by **{context.author}**!\nReason: {reason}")

    @warning.command(name="remove", description="Removes a warning from a user in the server.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(user="The user that should get their warning removed.", warn_id="The ID of the warning that should be removed.")
    async def warning_remove(self, context, user: discord.User, warn_id: int):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        total = await self.bot.database.remove_warn(warn_id, user.id, context.guild.id)
        await context.send(embed=make_embed(
            f"I've removed the warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total}"))

    @warning.command(name="list", description="Shows the warnings of a user in the server.")
    @commands.has_guild_permissions(manage_messages=True)
    @app_commands.describe(user="The user you want to get the warnings of.")
    async def warning_list(self, context, user: discord.User):
        warnings = await self.bot.database.get_warnings(user.id, context.guild.id)
        embed = discord.Embed(title=f"Warnings of {user}", color=COLOR_DEFAULT)
        if not warnings:
            embed.description = "This user has no warnings."
        else:
            embed.description = "\n".join(
                f"• Warned by <@{w[2]}>: **{w[3]}** (<t:{w[4]}>) - Warn ID #{w[5]}" for w in warnings)
        await context.send(embed=embed)

    @commands.hybrid_command(name="purge", description="Delete a number of messages.")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @app_commands.describe(amount="The amount of messages that should be deleted.")
    async def purge(self, context, amount: int):
        await context.send("Deleting messages...")
        purged = await context.channel.purge(limit=amount + 1)
        await context.channel.send(embed=make_embed(f"**{context.author}** cleared **{len(purged) - 1}** messages!"))

    @commands.hybrid_command(name="hackban", description="Bans a user without the user having to be in the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(user_id="The user ID that should be banned.", reason="The reason why the user should be banned.")
    async def hackban(self, context, user_id: str, *, reason: str = "Not specified"):
        try:
            await self.bot.http.ban(user_id, context.guild.id, reason=reason)
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            embed = make_embed(f"**{user}** (ID: {user_id}) was banned by **{context.author}**!")
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)
        except Exception:
            await context.send(embed=make_embed(
                "An error occurred while trying to ban the user. Make sure ID is an existing ID that belongs to a user.",
                COLOR_ERROR))

    @commands.hybrid_command(name="archive", description="Archives in a text file the last messages with a chosen limit of messages.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(limit="The limit of messages that should be archived.")
    async def archive(self, context, limit: int = 10):
        log_file = f"{context.channel.id}.log"
        with open(log_file, "w", encoding="UTF-8") as f:
            f.write(
                f'Archived messages from: #{context.channel} ({context.channel.id}) in the guild '
                f'"{context.guild}" ({context.guild.id}) at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}\n')
            async for message in context.channel.history(limit=limit, before=context.message):
                urls = [a.url for a in message.attachments]
                attached = f"[Attached File{'s' if len(urls) >= 2 else ''}: {', '.join(urls)}]" if urls else ""
                f.write(f"{message.created_at.strftime('%d.%m.%Y %H:%M:%S')} {message.author} "
                        f"{message.id}: {message.clean_content} {attached}\n")
        await context.send(file=discord.File(log_file))
        os.remove(log_file)

    @commands.hybrid_command(name="mute", description="Temporarily timeout a user.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(user="The user that should be muted.", duration="Duration of the mute in minutes.", reason="The reason why the user should be muted.")
    async def mute(self, context, user: discord.User, duration: int, *, reason: str = "Not specified"):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.id == context.author.id:
            return await context.send(embed=make_embed("You cannot mute yourself.", COLOR_ERROR), ephemeral=True)
        if member.top_role >= context.author.top_role and context.guild.owner_id != context.author.id:
            return await context.send(embed=make_embed("You cannot mute someone with a higher or equal role.", COLOR_ERROR), ephemeral=True)
        try:
            await member.timeout(timedelta(minutes=duration), reason=f"Action by {context.author} | Reason: {reason}")
            embed = make_embed(f"**{member}** was muted by **{context.author}** for **{duration} minute(s)**!")
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)
            try:
                await member.send(f"You were muted by **{context.author}** in **{context.guild.name}** for **{duration} minute(s)**!\nReason: {reason}")
            except discord.Forbidden:
                pass
        except Exception:
            await context.send(embed=make_embed(
                "An error occurred while trying to mute the user. Make sure my role is above the role of the user you want to mute.",
                COLOR_ERROR))

    @commands.hybrid_command(name="unmute", description="Remove a timeout from a user.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(user="The user that should be unmuted.")
    async def unmute(self, context, user: discord.User):
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        try:
            await member.timeout(None, reason=f"Unmuted by {context.author}")
            await context.send(embed=make_embed(f"**{member}** was unmuted by **{context.author}**!"))
        except Exception:
            await context.send(embed=make_embed("An error occurred while trying to unmute the user.", COLOR_ERROR))

    @commands.group(name="welcome", description="Configure the welcome message for the server.")
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, context):
        if context.invoked_subcommand is None:
            await context.send(embed=make_embed(
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
                "`{member_count}` - The number of members in the server"))

    @welcome.command(name="channel", description="Set the channel where welcome messages will be sent.")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    @app_commands.describe(channel="The welcome channel.")
    async def welcome_channel(self, context, channel: discord.TextChannel):
        await self.bot.database.set_welcome_channel(context.guild.id, channel.id)
        await context.send(embed=make_embed(f"Welcome channel has been set to {channel.mention}."))

    @welcome.command(name="message", description="Set the welcome message.")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(message="The welcome message. Use {user} to ping the new member.")
    async def welcome_message(self, context, *, message: str):
        await self.bot.database.set_welcome_message(context.guild.id, message)
        embed = make_embed("The welcome message has been updated!")
        embed.add_field(name="Preview:", value=format_welcome(message, context.author)[:1024], inline=False)
        await context.send(embed=embed)

    @welcome.command(name="test", description="Send a preview of the welcome message in the configured channel.")
    @commands.has_permissions(manage_guild=True)
    async def welcome_test(self, context):
        config = await self.bot.database.get_welcome_config(context.guild.id)
        if not config or not config[0]:
            return await context.send(embed=make_embed("No welcome channel is set. Use `welcome channel` first.", COLOR_ERROR))
        channel = context.guild.get_channel(config[0])
        if not channel:
            return await context.send(embed=make_embed("The configured channel no longer exists. Please set it again with `welcome channel`.", COLOR_ERROR))
        embed = make_embed(format_welcome(config[1], context.author))
        embed.set_thumbnail(url=context.author.display_avatar.url)
        embed.set_footer(text=f"Member #{context.guild.member_count}")
        await channel.send(content=context.author.mention, embed=embed)
        await context.send(embed=make_embed(f"Preview sent to {channel.mention}."), ephemeral=True)

    @welcome.command(name="disable", description="Disable the welcome message.")
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, context):
        await self.bot.database.set_welcome_channel(context.guild.id, None)
        await context.send(embed=make_embed("The welcome message has been disabled."))


async def setup(bot):
    await bot.add_cog(Moderation(bot))