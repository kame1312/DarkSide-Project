import io

import chat_exporter
import discord
from discord import app_commands
from discord.ext import commands

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


def make_embed(desc=None, color=COLOR_DEFAULT, **kw):
    return discord.Embed(description=desc, color=color, **kw)


async def export_transcript(channel):
    try:
        data = await chat_exporter.export(channel, limit=None)
    except Exception:
        return None
    if data is None:
        return None
    return discord.File(io.BytesIO(data.encode()), filename=f"transcript-{channel.name}.html")


async def send_close_log(bot, guild, channel, ticket):
    config = await bot.database.get_ticket_config(guild.id)
    if not config or not config["log_channel_id"]:
        return
    log_channel = guild.get_channel(config["log_channel_id"])
    file = await export_transcript(channel)
    if not log_channel or not file:
        return
    await log_channel.send(
        embed=make_embed(
            f"**Ticket:** {channel.name}\n"
            f"**Opened by:** <@{ticket['user_id']}>\n"
            f"**Reason:** {ticket['reason']}",
            COLOR_ERROR, title="Ticket closed",
        ),
        file=file,
    )


class TicketModal(discord.ui.Modal, title="Open a ticket"):
    reason = discord.ui.TextInput(
        label="Reason for the ticket",
        style=discord.TextStyle.paragraph,
        placeholder="Briefly explain your request...",
        max_length=500,
    )

    async def _fail(self, interaction, msg):
        await interaction.followup.send(embed=make_embed(msg, COLOR_ERROR), ephemeral=True)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        guild, user, db = interaction.guild, interaction.user, interaction.client.database

        config = await db.get_ticket_config(guild.id)
        if not config or not config["category_id"]:
            return await self._fail(interaction, "The ticket system is not configured. Please contact an administrator.")

        if existing := await db.get_open_ticket_by_user(guild.id, user.id):
            return await self._fail(interaction, f"You already have an open ticket: <#{existing['channel_id']}>")

        category = guild.get_channel(config["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await self._fail(interaction, "The ticket category could not be found. Please contact an administrator.")

        perms = dict(view_channel=True, send_messages=True, read_message_history=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(**perms),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if config["support_role_id"] and (role := guild.get_role(config["support_role_id"])):
            overwrites[role] = discord.PermissionOverwrite(**perms)

        channel = await category.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            topic=f"Ticket from {user} | Reason: {self.reason.value[:100]}",
        )
        await db.create_ticket(guild.id, channel.id, user.id, self.reason.value)

        opened = make_embed(f"**Reason:** {self.reason.value}", COLOR_ACCENT, title="Ticket opened")
        opened.set_footer(text=f"Opened by {user} • {channel.id}")
        await channel.send(
            content=f"{user.mention} welcome to your ticket. A staff member will reply shortly.",
            embed=opened, view=TicketControlView(),
        )
        await interaction.followup.send(
            embed=make_embed(f"Your ticket has been created: {channel.mention}"), ephemeral=True
        )

        if config["log_channel_id"] and (log := guild.get_channel(config["log_channel_id"])):
            await log.send(embed=make_embed(
                f"**User:** {user.mention} ({user.id})\n"
                f"**Channel:** {channel.mention}\n"
                f"**Reason:** {self.reason.value}",
                COLOR_DEFAULT, title="New ticket",
            ))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open a ticket", style=discord.ButtonStyle.green, custom_id="ticket_open_button")
    async def open_ticket(self, interaction, _):
        await interaction.response.send_modal(TicketModal())


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="ticket_close_button")
    async def close_ticket(self, interaction, _):
        ticket = await interaction.client.database.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
        await interaction.response.defer()
        await interaction.client.database.close_ticket(interaction.channel.id)
        await send_close_log(interaction.client, interaction.guild, interaction.channel, ticket)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.blurple, custom_id="ticket_transcript_button")
    async def transcript(self, interaction, _):
        if not await interaction.client.database.get_ticket(interaction.channel.id):
            return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        file = await export_transcript(interaction.channel)
        if file:
            await interaction.followup.send(file=file, ephemeral=True)
        else:
            await interaction.followup.send("Could not generate the transcript.", ephemeral=True)


class Tickets(commands.Cog, name="tickets"):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlView())

    async def _set_config(self, context, field, value):
        await self.bot.database.set_ticket_config(context.guild.id, **{field: value})
        labels = {"category_id": "Ticket category", "log_channel_id": "Log channel", "support_role_id": "Support role"}
        display = f"<@&{value}>" if field == "support_role_id" else f"<#{value}>"
        await context.send(embed=make_embed(f"{labels[field]} set to {display}.", COLOR_ACCENT))

    @commands.group(name="ticket_config", description="Configure the ticket system for this server.", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ticket_config(self, context):
        config = await self.bot.database.get_ticket_config(context.guild.id)
        if not config:
            return await context.send(embed=make_embed(
                "No configuration found. Use the subcommands to set it up.", COLOR_ERROR))

        def fmt(key, getter):
            value = config[key]
            if not value:
                return "❌ Not set"
            obj = getter(value)
            return obj.mention if obj else "❌ Not set"

        embed = discord.Embed(title="Ticket configuration", color=COLOR_ACCENT)
        embed.add_field(name="Category", value=fmt("category_id", context.guild.get_channel), inline=False)
        embed.add_field(name="Log channel", value=fmt("log_channel_id", context.guild.get_channel), inline=False)
        embed.add_field(name="Support role", value=fmt("support_role_id", context.guild.get_role), inline=False)
        await context.send(embed=embed)

    @ticket_config.command(name="category", description="Set the category where tickets are created.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_category(self, context, category: discord.CategoryChannel):
        await self._set_config(context, "category_id", category.id)

    @ticket_config.command(name="logs", description="Set the channel where ticket logs are sent.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_logs(self, context, channel: discord.TextChannel):
        await self._set_config(context, "log_channel_id", channel.id)

    @ticket_config.command(name="support", description="Set the role that can see and manage tickets.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_support(self, context, role: discord.Role):
        await self._set_config(context, "support_role_id", role.id)

    @ticket_config.command(name="reset", description="Reset the ticket configuration for this server.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_reset(self, context):
        await self.bot.database.reset_ticket_config(context.guild.id)
        await context.send(embed=make_embed("Ticket configuration has been reset.", COLOR_ACCENT))

    @commands.command(name="ticket_panel", description="Post the ticket panel in the current channel.")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, context):
        config = await self.bot.database.get_ticket_config(context.guild.id)
        if not config or not config["category_id"]:
            return await context.send(embed=make_embed(
                "The ticket system is not configured. Use `!ticket_config category` first.", COLOR_ERROR))
        embed = make_embed(
            "Click the button below to open a ticket.\nA staff member will reply in a private channel.",
            COLOR_ACCENT, title="Support")
        embed.set_footer(text="Ticket system")
        await context.send(embed=embed, view=TicketPanelView())

    @commands.hybrid_command(name="ticket_close", description="Close the current ticket.")
    async def ticket_close(self, context):
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            return await context.send(embed=make_embed("This channel is not a ticket.", COLOR_ERROR))
        await self.bot.database.close_ticket(context.channel.id)
        await send_close_log(self.bot, context.guild, context.channel, ticket)
        await context.channel.delete(reason=f"Ticket closed by {context.author}")

    @commands.hybrid_command(name="ticket_add", description="Add a member to the current ticket.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="The member to add to the ticket")
    async def ticket_add(self, context, member: discord.Member):
        if not await self.bot.database.get_ticket(context.channel.id):
            return await context.send(embed=make_embed("This channel is not a ticket.", COLOR_ERROR))
        await context.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True)
        await context.send(embed=make_embed(f"{member.mention} has been added to the ticket."))

    @commands.hybrid_command(name="ticket_remove", description="Remove a member from the current ticket.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="The member to remove from the ticket")
    async def ticket_remove(self, context, member: discord.Member):
        if not await self.bot.database.get_ticket(context.channel.id):
            return await context.send(embed=make_embed("This channel is not a ticket.", COLOR_ERROR))
        await context.channel.set_permissions(member, overwrite=None)
        await context.send(embed=make_embed(f"{member.mention} has been removed from the ticket."))


async def setup(bot):
    await bot.add_cog(Tickets(bot))