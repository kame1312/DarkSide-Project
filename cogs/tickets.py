import io

import chat_exporter
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


class TicketModal(discord.ui.Modal, title="Ouvrir un ticket"):
    raison = discord.ui.TextInput(
        label="Raison du ticket",
        style=discord.TextStyle.paragraph,
        placeholder="Expliquez brièvement votre demande...",
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
                    description="Le système de tickets n'est pas configuré. Contactez un administrateur.",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        existing = await interaction.client.database.get_open_ticket_by_user(guild.id, user.id)
        if existing:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"Vous avez déjà un ticket ouvert : <#{existing['channel_id']}>",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        category = guild.get_channel(config["category_id"])
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                embed=discord.Embed(
                    description="La catégorie des tickets est introuvable. Contactez un administrateur.",
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
            topic=f"Ticket de {user} | Raison : {self.raison.value[:100]}",
        )

        await interaction.client.database.create_ticket(
            guild.id, channel.id, user.id, self.raison.value
        )

        embed = discord.Embed(
            title="Ticket ouvert",
            description=f"**Raison :** {self.raison.value}",
            color=COLOR_ACCENT,
        )
        embed.set_footer(text=f"Ouvert par {user} • {channel.id}")

        await channel.send(
            content=f"{user.mention} bienvenue dans votre ticket. Un membre du staff va vous répondre.",
            embed=embed,
            view=TicketControlView(),
        )

        await interaction.followup.send(
            embed=discord.Embed(
                description=f"Votre ticket a été créé : {channel.mention}",
                color=COLOR_DEFAULT,
            ),
            ephemeral=True,
        )

        if config["log_channel_id"]:
            log_channel = guild.get_channel(config["log_channel_id"])
            if log_channel:
                log_embed = discord.Embed(
                    title="Nouveau ticket",
                    description=(
                        f"**Utilisateur :** {user.mention} ({user.id})\n"
                        f"**Salon :** {channel.mention}\n"
                        f"**Raison :** {self.raison.value}"
                    ),
                    color=COLOR_DEFAULT,
                )
                await log_channel.send(embed=log_embed)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ouvrir un ticket",
        style=discord.ButtonStyle.green,
        custom_id="ticket_open_button",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal())


class TicketControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fermer",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close_button",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await interaction.client.database.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)
            return

        await interaction.response.defer()
        await interaction.client.database.close_ticket(interaction.channel.id)
        await self.generate_and_send_transcript(interaction, ticket)
        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")

    @discord.ui.button(
        label="Transcription",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_transcript_button",
    )
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await interaction.client.database.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript_file = await self.export_transcript(interaction.channel)
        if transcript_file:
            await interaction.followup.send(file=transcript_file, ephemeral=True)
        else:
            await interaction.followup.send("Impossible de générer la transcription.", ephemeral=True)

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
            title="Ticket fermé",
            description=(
                f"**Ticket :** {interaction.channel.name}\n"
                f"**Ouvert par :** <@{ticket['user_id']}>\n"
                f"**Raison :** {ticket['reason']}"
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
                description="Aucune configuration. Utilisez les sous-commandes pour configurer.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        category = context.guild.get_channel(config["category_id"]) if config["category_id"] else None
        log_channel = context.guild.get_channel(config["log_channel_id"]) if config["log_channel_id"] else None
        support_role = context.guild.get_role(config["support_role_id"]) if config["support_role_id"] else None

        embed = discord.Embed(title="Configuration des tickets", color=COLOR_ACCENT)
        embed.add_field(name="Catégorie", value=category.mention if category else "❌ Non défini", inline=False)
        embed.add_field(name="Salon de logs", value=log_channel.mention if log_channel else "❌ Non défini", inline=False)
        embed.add_field(name="Rôle support", value=support_role.mention if support_role else "❌ Non défini", inline=False)
        await context.send(embed=embed)

    @ticket_config.command(name="category", description="Set the category where tickets are created.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_category(self, context: Context, category: discord.CategoryChannel) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, category_id=category.id)
        embed = discord.Embed(
            description=f"Catégorie des tickets définie sur {category.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="logs", description="Set the channel where ticket logs are sent.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_logs(self, context: Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, log_channel_id=channel.id)
        embed = discord.Embed(
            description=f"Salon de logs défini sur {channel.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="support", description="Set the role that can see and manage tickets.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_support(self, context: Context, role: discord.Role) -> None:
        await self.bot.database.set_ticket_config(context.guild.id, support_role_id=role.id)
        embed = discord.Embed(
            description=f"Rôle support défini sur {role.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @ticket_config.command(name="reset", description="Reset the ticket configuration for this server.")
    @commands.has_permissions(administrator=True)
    async def ticket_config_reset(self, context: Context) -> None:
        await self.bot.database.reset_ticket_config(context.guild.id)
        embed = discord.Embed(
            description="Configuration des tickets réinitialisée.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ticket_panel",
        description="Poste le panneau d'ouverture des tickets dans le salon actuel.",
    )
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, context: Context) -> None:
        config = await self.bot.database.get_ticket_config(context.guild.id)
        if not config or not config["category_id"]:
            embed = discord.Embed(
                description="Le système de tickets n'est pas configuré. Utilisez `/ticket_config category`.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title="Support",
            description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket.\nUn membre du staff vous répondra dans un salon privé.",
            color=COLOR_ACCENT,
        )
        embed.set_footer(text="Système de tickets")
        await context.send(embed=embed, view=TicketPanelView())

    @commands.hybrid_command(name="ticket_close", description="Ferme le ticket actuel.")
    async def ticket_close(self, context: Context) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="Ce salon n'est pas un ticket.", color=COLOR_ERROR)
            )
            return

        await self.bot.database.close_ticket(context.channel.id)
        view = TicketControlView()
        await view.generate_and_send_transcript(context, ticket)
        await context.channel.delete(reason=f"Ticket fermé par {context.author}")

    @commands.hybrid_command(name="ticket_add", description="Ajoute un membre au ticket actuel.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="Le membre à ajouter au ticket")
    async def ticket_add(self, context: Context, member: discord.Member) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="Ce salon n'est pas un ticket.", color=COLOR_ERROR)
            )
            return

        await context.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True
        )
        embed = discord.Embed(
            description=f"{member.mention} a été ajouté au ticket.", color=COLOR_DEFAULT
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="ticket_remove", description="Retire un membre du ticket actuel.")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(member="Le membre à retirer du ticket")
    async def ticket_remove(self, context: Context, member: discord.Member) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            await context.send(
                embed=discord.Embed(description="Ce salon n'est pas un ticket.", color=COLOR_ERROR)
            )
            return

        await context.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            description=f"{member.mention} a été retiré du ticket.", color=COLOR_DEFAULT
        )
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Tickets(bot))