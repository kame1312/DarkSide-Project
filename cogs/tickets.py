import io

import chat_exporter
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


class TicketModal(discord.ui.Modal, title="Open a ticket"):
    reason = discord.ui.TextInput(
        label="Reason for the ticket",
        style=discord.TextStyle.paragraph,
        placeholder="Briefly explain your request...",
        max_length=500,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        config = await interaction.client.database.get_ticket_config(guild.id)
        if not config or not config["category_id"]:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="The ticket system is not configured. Please contact an administrator.",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        existing = await interaction.client.database.get_open_ticket_by_user(guild.id, user.id)
        if existing:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"You already have an open ticket: <#{existing['channel_id']}>",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        category = guild.get_channel(config["category_id"])
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                embed=discord.Embed(
                    description="The ticket category could not be found. Please contact an administrator.",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
        }

        if config["support_role_id"]:
            support_role = guild.get_role(config["support_role_id"])
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        channel = await category.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            topic=f"Ticket from {user} | Reason: {self.reason.value[:100]}",
        )

        await interaction.client.database.create_ticket(
            guild.id, channel.id, user.id, self.reason.value
        )

        embed = discord.Embed(
            title="Ticket opened",
            description=f"**Reason:** {self.reason.value}",
            color=COLOR_ACCENT,
        )
        embed.set_footer(text=f"Opened by {user} • {channel.id}")

        await channel.send(
            content=f"{user.mention} welcome to your ticket. A staff member will reply shortly.",
            embed=embed,
            view=TicketControlView(),
        )

        await interaction.followup.send(
            embed=discord.Embed(
                description=f"Your ticket has been created: {channel.mention}",
                color=COLOR_DEFAULT,
            ),
            ephemeral=True,
        )

        if config["log_channel_id"]:
            log_channel = guild.get_channel(config["log_channel_id"])
            if log_channel:
                log_embed = discord.Embed(
                    title="New ticket",
                    description=(
                        f"**User:** {user.mention} ({user.id})\n"
                        f"**Channel:** {channel.mention}\n"
                        f"**Reason:** {self.reason.value}"
                    ),
                    color=COLOR_DEFAULT,
                )
                await log_channel.send(embed=log_embed)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open a ticket",
        style=discord.ButtonStyle.green,
        custom_id="ticket_open_button",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal())


class TicketControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close_button",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await interaction.client.database.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            return

        await interaction.response.defer()
        await interaction.client.database.close_ticket(interaction.channel.id)
        await self.generate_and_send_transcript(interaction, ticket)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_transcript_button",
    )
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await interaction.client.database.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript_file = await self.export_transcript(interaction.channel)
        if transcript_file:
            await interaction.followup.send(file=transcript_file, ephemeral=True)
        else:
            await interaction.followup.send("Could not generate the transcript.", ephemeral=True)

    async def generate_and_send_transcript(self, interaction: discord.Interaction, ticket: dict) -> None:
        config = await interaction.client.database.get_ticket_config(interaction.guild.id)
        if not config or not config["log_channel_id"]:
            return
        log_channel = interaction.guild.get_channel(config["log_channel_id"])
        if not log_channel:
            return

        transcript_file = await self.export_transcript(interaction.channel)
        if not transcript_file:
            return

        embed = discord.Embed(
            title="Ticket closed",
            description=(
                f"**Ticket:** {interaction.channel.name}\n"
                f"**Opened by:** <@{ticket['user_id']}>\n"
                f"**Reason:** {ticket['reason']}"
            ),
            color=COLOR_ERROR,
        )
        await log_channel.send(embed=embed, file=transcript_file)

    async def export_transcript(self, channel: discord.TextChannel) -> discord.File | None:
        try:
            transcript = await chat_exporter.export(channel, limit=None)
            if transcript is None:
                return None
            return discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{channel.name}.html",
            )
        except Exception:
            return None


class Tickets(commands.Cog, name="tickets"):
    def __init__(self, bot) -> None:
        self.bot = bot
        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlView())

    @commands.hybrid_group(
        name="ticket_config",
        description="Configure the ticket system for this server.",
        invoke_without_command=True,
    )
    @commands.has_permissions(administrator=True)
    async def ticket_config(self, context: Context) -> None:
        config = await self.bot.database.get_ticket_config(context.guild.id)
        if not config:
            embed = discord.Embed(
                description="No configuration found. Use the subcommands to set it up.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        category = context.guild.get_channel(config["category_id"]) if config["category_id"] else None
        log_channel = context.guild.get_channel(config["log_channel_id"]) if config["log_channel_id"] else None
        support_role = context.guild.get_role(config["support_role_id"]) if config["support_role_id"] else None

        embed = discord.Embed(title="Ticket configuration", color=COLOR_ACCENT)
        embed.add_field(name="Category", value=category.mention if category else "❌ Not set", inline=False)
        embed.add_field(name="Log channel", value=log_channel.mention if log_channel else "❌ Not set", inline=False)
        embed.add_field(name="Support role", value=support_role.mention if support_role else "❌ Not set", inline=False)
        await context.send(embed=embed)

    @ticket_config.command(name="category", description="Set the category where tickets are created.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_category(self, context: Context, category: discord.CategoryChannel) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, category_id=category.id)
        embed = discord.Embed(
            description=f"Ticket category set to {category.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="logs", description="Set the channel where ticket logs are sent.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_logs(self, context: Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, log_channel_id=channel.id)
        embed = discord.Embed(
            description=f"Log channel set to {channel.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="support", description="Set the role that can see and manage tickets.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_support(self, context: Context, role: discord.Role) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, support_role_id=role.id)
        embed = discord.Embed(
            description=f"Support role set to {role.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="reset", description="Reset the ticket configuration for this server.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_reset(self, context: Context) -> None:
        await self.bot.database.reset_ticket_config(context.guild.id)
        embed = discord.Embed(
            description="Ticket configuration has been reset.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ticket_panel",
        description="Post the ticket panel in the current channel.",
    )
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, context: Context) -> None:
        config = await self.bot.database.get_ticket_config(context.guild.id)
        if not config or not config["category_id"]:
            embed = discord.Embed(
                description="The ticket system is not configured. Use `/ticket_config category` first.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title="Support",
            description="Click the button below to open a ticket.\nA staff member will reply in a private channel.",
            color=COLOR_ACCENT,
        )
        embed.set_footer(text="Ticket system")
        await context.send(embed=embed, view=TicketPanelView())

    @commands.hybrid_command(name="ticket_close", description="Close the current ticket.")
    async def ticket_close(self, context: Context) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="This channel is not a ticket.", color=COLOR_ERROR)
            )
            return

        await self.bot.database.close_ticket(context.channel.id)
        view = TicketControlView()
        await view.generate_and_send_transcript(context, ticket)
        await context.channel.delete(reason=f"Ticket closed by {context.author}")

    @commands.hybrid_command(name="ticket_add", description="Add a member to the current ticket.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="The member to add to the ticket")
    async def ticket_add(self, context: Context, member: discord.Member) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="This channel is not a ticket.", color=COLOR_ERROR)
            )
            return

        await context.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True
        )
        embed = discord.Embed(
            description=f"{member.mention} has been added to the ticket.", color=COLOR_DEFAULT
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="ticket_remove", description="Remove a member from the current ticket.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="The member to remove from the ticket")
    async def ticket_remove(self, context: Context, member: discord.Member) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="This channel is not a ticket.", color=COLOR_ERROR)
            )
            return

        await context.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            description=f"{member.mention} has been removed from the ticket.", color=COLOR_DEFAULT
        )
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Tickets(bot))