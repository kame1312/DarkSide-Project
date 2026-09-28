import os

import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR

DEFAULT_PANEL_TITLE = "Support"
DEFAULT_PANEL_DESC = "Click the button below to open a ticket.\nA staff member will reply in a private channel."
DEFAULT_WELCOME = "Welcome {user} to **{guild}**!"


class SuggestionModal(discord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(title="Submit a Suggestion")

        self.suggestion_title = discord.ui.TextInput(
            label="Title",
            style=discord.TextStyle.short,
            placeholder="Brief summary of your idea",
            max_length=100,
            required=True,
        )
        self.suggestion_desc = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            placeholder="Explain your idea in detail...",
            max_length=1500,
            required=True,
        )
        self.add_item(self.suggestion_title)
        self.add_item(self.suggestion_desc)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel_id = await self.bot.database.get_owner_suggestion_channel()

        if not channel_id:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="The suggestion channel is not configured. Please contact the owner.",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="The suggestion channel is not configured. Please contact the owner.",
                    color=COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"💡 {self.suggestion_title.value}",
            description=self.suggestion_desc.value,
            color=COLOR_ACCENT,
        )
        embed.set_author(
            name=f"Suggestion from {interaction.user} (ID: {interaction.user.id})",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_footer(
            text=f"Server: {interaction.guild.name} ({interaction.guild.id})"
        )

        await channel.send(embed=embed)
        await interaction.followup.send(
            embed=discord.Embed(
                description="Your suggestion has been sent to the owner!",
                color=COLOR_DEFAULT,
            ),
            ephemeral=True,
        )


class WelcomeMessageModal(discord.ui.Modal):
    def __init__(self, bot, current_message, parent_view, parent_message):
        self.bot = bot
        self.parent_view = parent_view
        self.parent_message = parent_message
        super().__init__(title="Welcome Message")

        self.message_input = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            placeholder="Welcome {user} to **{guild}**!",
            default=current_message or DEFAULT_WELCOME,
            max_length=1000,
            required=True,
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.database.set_welcome_message(
            interaction.guild.id, self.message_input.value
        )
        self.parent_view.current_message = self.message_input.value
        try:
            await self.parent_message.edit(
                embed=self.parent_view.get_embed(), view=self.parent_view
            )
        except discord.HTTPException:
            pass


class TicketPanelModal(discord.ui.Modal):
    def __init__(self, bot, current_title, current_desc):
        self.bot = bot
        super().__init__(title="Ticket Panel Message")

        self.title_input = discord.ui.TextInput(
            label="Panel Title",
            style=discord.TextStyle.short,
            placeholder="Support",
            default=current_title or DEFAULT_PANEL_TITLE,
            max_length=100,
            required=True,
        )
        self.desc_input = discord.ui.TextInput(
            label="Panel Description",
            style=discord.TextStyle.paragraph,
            placeholder="Click the button below to open a ticket...",
            default=current_desc or DEFAULT_PANEL_DESC,
            max_length=1000,
            required=True,
        )
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.database.set_ticket_panel_config(
            interaction.guild.id, self.title_input.value, self.desc_input.value
        )


class TicketsConfigView(discord.ui.View):
    def __init__(self, bot, author_id, parent_view, banner_url=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.parent_view = parent_view
        self.banner_url = banner_url
        self.pending_category = None
        self.pending_log = None
        self.pending_support = None

    async def load_current(self, guild_id):
        config = await self.bot.database.get_ticket_config(guild_id)
        if config:
            self.pending_category = config["category_id"]
            self.pending_log = config["log_channel_id"]
            self.pending_support = config["support_role_id"]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This is not your dashboard.", ephemeral=True
            )
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="🎫 Tickets Configuration",
            description="Select the channels and role below, then click **Save** to apply.",
            color=COLOR_ACCENT,
        )
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.add_field(
            name="Category",
            value=f"<#{self.pending_category}>" if self.pending_category else "❌ Not set",
            inline=True,
        )
        embed.add_field(
            name="Log Channel",
            value=f"<#{self.pending_log}>" if self.pending_log else "❌ Not set",
            inline=True,
        )
        embed.add_field(
            name="Support Role",
            value=f"<@&{self.pending_support}>" if self.pending_support else "❌ Not set",
            inline=True,
        )
        return embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.category],
        placeholder="Select a category...",
        row=0,
    )
    async def select_category(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.pending_category = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a log channel...",
        row=1,
    )
    async def select_logs(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.pending_log = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Select a support role...",
        row=2,
    )
    async def select_support(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.pending_support = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Save", style=discord.ButtonStyle.success, emoji="💾", row=3
    )
    async def save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        await self.bot.database.set_ticket_config(
            interaction.guild.id,
            category_id=self.pending_category,
            log_channel_id=self.pending_log,
            support_role_id=self.pending_support,
        )

    @discord.ui.button(
        label="Edit Panel Message",
        style=discord.ButtonStyle.primary,
        emoji="✏️",
        row=3,
    )
    async def edit_panel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        config = await self.bot.database.get_ticket_panel_config(interaction.guild.id)
        current_title = config["title"] if config else None
        current_desc = config["description"] if config else None
        await interaction.response.send_modal(
            TicketPanelModal(self.bot, current_title, current_desc)
        )

    @discord.ui.button(
        label="Send Panel",
        style=discord.ButtonStyle.success,
        emoji="📩",
        row=4,
    )
    async def send_panel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        from cogs.tickets import TicketPanelView

        config = await self.bot.database.get_ticket_panel_config(interaction.guild.id)
        title = config["title"] if config and config["title"] else DEFAULT_PANEL_TITLE
        desc = (
            config["description"]
            if config and config["description"]
            else DEFAULT_PANEL_DESC
        )

        embed = discord.Embed(title=title, description=desc, color=COLOR_ACCENT)
        embed.set_footer(text="Ticket system")
        await interaction.channel.send(embed=embed, view=TicketPanelView())

    @discord.ui.button(
        label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=4
    )
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


class SecNewsConfigView(discord.ui.View):
    def __init__(self, bot, author_id, parent_view, banner_url=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.parent_view = parent_view
        self.banner_url = banner_url
        self.pending_channel = None

    async def load_current(self, guild_id):
        channels = await self.bot.database.get_secnews_channels()
        self.pending_channel = channels.get(guild_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This is not your dashboard.", ephemeral=True
            )
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="📰 Security News Configuration",
            description="Select a channel below, then click **Save** to apply.",
            color=COLOR_ACCENT,
        )
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.add_field(
            name="News Channel",
            value=f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set",
            inline=False,
        )
        return embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a news channel...",
        row=0,
    )
    async def select_channel(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Save", style=discord.ButtonStyle.success, emoji="💾", row=1
    )
    async def save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        if self.pending_channel:
            await self.bot.database.set_secnews_channel(
                interaction.guild.id, self.pending_channel
            )

    @discord.ui.button(
        label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1
    )
    async def test(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        cog = self.bot.get_cog("security_news")
        if cog:
            await cog.fetch_security_news()

    @discord.ui.button(
        label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=1
    )
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


class GitWatchConfigView(discord.ui.View):
    def __init__(self, bot, author_id, parent_view, banner_url=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.parent_view = parent_view
        self.banner_url = banner_url
        self.pending_channel = None

    def load_current(self):
        cog = self.bot.get_cog("gitwatch")
        if cog:
            self.pending_channel = cog.channel_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This is not your dashboard.", ephemeral=True
            )
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="🐙 GitWatch Configuration",
            description="Select a channel below, then click **Save** to apply.",
            color=COLOR_ACCENT,
        )
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.add_field(
            name="Notification Channel",
            value=f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set",
            inline=False,
        )
        return embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a channel...",
        row=0,
    )
    async def select_channel(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Save", style=discord.ButtonStyle.success, emoji="💾", row=1
    )
    async def save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        cog = self.bot.get_cog("gitwatch")
        if cog:
            cog.channel_id = self.pending_channel
            cog.last_commit_id = None
            cog._save_config()

    @discord.ui.button(
        label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1
    )
    async def test(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        cog = self.bot.get_cog("gitwatch")
        if cog:
            commits = await cog._fetch_commits()
            if commits:
                latest = commits[0]
                embed = discord.Embed(
                    title=latest["title"],
                    url=latest["link"],
                    description=f"Pushed by **{latest['author']}**",
                    color=COLOR_ACCENT,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Disable", style=discord.ButtonStyle.danger, emoji="🚫", row=1
    )
    async def disable(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self.bot.get_cog("gitwatch")
        if cog:
            cog.channel_id = None
            cog._save_config()
        self.pending_channel = None
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=2
    )
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


class WelcomeConfigView(discord.ui.View):
    def __init__(self, bot, author_id, parent_view, banner_url=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.parent_view = parent_view
        self.banner_url = banner_url
        self.pending_channel = None
        self.current_message = None

    async def load_current(self, guild_id):
        config = await self.bot.database.get_welcome_config(guild_id)
        if config:
            self.pending_channel = config[0]
            self.current_message = config[1]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This is not your dashboard.", ephemeral=True
            )
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="👋 Welcome Configuration",
            description="Configure the welcome channel and message, then click **Save Channel** to apply the channel.",
            color=COLOR_ACCENT,
        )
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.add_field(
            name="Channel",
            value=f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set",
            inline=False,
        )
        preview = self.current_message or DEFAULT_WELCOME
        if len(preview) > 200:
            preview = preview[:200] + "..."
        embed.add_field(name="Message Preview", value=preview, inline=False)
        return embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a welcome channel...",
        row=0,
    )
    async def select_channel(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Save Channel",
        style=discord.ButtonStyle.success,
        emoji="💾",
        row=1,
    )
    async def save_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        if self.pending_channel:
            await self.bot.database.set_welcome_channel(
                interaction.guild.id, self.pending_channel
            )

    @discord.ui.button(
        label="Set Message",
        style=discord.ButtonStyle.primary,
        emoji="✏️",
        row=1,
    )
    async def set_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        message = interaction.message
        await interaction.response.send_modal(
            WelcomeMessageModal(self.bot, self.current_message, self, message)
        )

    @discord.ui.button(
        label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1
    )
    async def test(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        config = await self.bot.database.get_welcome_config(interaction.guild.id)
        if config and config[0]:
            channel = interaction.guild.get_channel(config[0])
            if channel:
                text = (config[1] or DEFAULT_WELCOME).format(
                    user=interaction.user.mention,
                    user_name=interaction.user.name,
                    user_display=interaction.user.display_name,
                    guild=interaction.guild.name,
                    member_count=interaction.guild.member_count,
                )
                embed = discord.Embed(description=text, color=COLOR_DEFAULT)
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.set_footer(text=f"Member #{interaction.guild.member_count}")
                await channel.send(content=interaction.user.mention, embed=embed)

    @discord.ui.button(
        label="Disable", style=discord.ButtonStyle.danger, emoji="🚫", row=2
    )
    async def disable(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.bot.database.set_welcome_channel(interaction.guild.id, None)
        self.pending_channel = None
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(
        label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=2
    )
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


class DashboardView(discord.ui.View):
    def __init__(self, bot, author_id, banner_url=None):
        super().__init__(timeout=600)
        self.bot = bot
        self.author_id = author_id
        self.banner_url = banner_url

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This is not your dashboard.", ephemeral=True
            )
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="Configuration Dashboard",
            description="Welcome to the configuration dashboard. Click a button below to configure a feature.",
            color=COLOR_ACCENT,
        )
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.set_footer(text="DarkSide Project Dashboard")
        return embed

    @discord.ui.button(
        label="Tickets", style=discord.ButtonStyle.primary, emoji="🎫", row=0
    )
    async def tickets_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        view = TicketsConfigView(self.bot, self.author_id, self, self.banner_url)
        await view.load_current(interaction.guild.id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @discord.ui.button(
        label="Security News", style=discord.ButtonStyle.primary, emoji="📰", row=0
    )
    async def secnews_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        view = SecNewsConfigView(self.bot, self.author_id, self, self.banner_url)
        await view.load_current(interaction.guild.id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @discord.ui.button(
        label="GitWatch", style=discord.ButtonStyle.primary, emoji="🐙", row=0
    )
    async def gitwatch_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        view = GitWatchConfigView(self.bot, self.author_id, self, self.banner_url)
        view.load_current()
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @discord.ui.button(
        label="Welcome", style=discord.ButtonStyle.primary, emoji="👋", row=1
    )
    async def welcome_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        view = WelcomeConfigView(self.bot, self.author_id, self, self.banner_url)
        await view.load_current(interaction.guild.id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @discord.ui.button(
        label="Suggestions", style=discord.ButtonStyle.success, emoji="💡", row=1
    )
    async def suggestions_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(SuggestionModal(self.bot))

    @discord.ui.button(
        label="Help", style=discord.ButtonStyle.secondary, emoji="❓", row=2
    )
    async def help_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=COLOR_DEFAULT
        )
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner" and not (
                await self.bot.is_owner(interaction.user)
            ):
                continue
            cog_commands = cog.get_commands()
            if not cog_commands:
                continue
            data = []
            for command in cog_commands:
                description = (
                    command.description or command.help or "No description"
                ).partition("\n")[0]
                data.append(f"{command.name} - {description}")
                if isinstance(command, commands.Group):
                    for sub in command.commands:
                        sub_description = (
                            sub.description or sub.help or "No description"
                        ).partition("\n")[0]
                        data.append(
                            f"  └ {command.name} {sub.name} - {sub_description}"
                        )
            help_text = "\n".join(data)
            embed.add_field(
                name=cog_name.replace("_", " ").title(),
                value=f"```{help_text}```",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Close", style=discord.ButtonStyle.danger, emoji="✖️", row=2
    )
    async def close_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()


class Dashboard(commands.Cog, name="dashboard"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="dashboard", description="Open the interactive configuration dashboard."
    )
    @commands.has_permissions(administrator=True)
    async def dashboard(self, context: Context) -> None:
        banner_url = os.getenv("BANNER_URL")
        if not banner_url and self.bot.user.banner:
            banner_url = self.bot.user.banner.url

        view = DashboardView(self.bot, context.author.id, banner_url)
        await context.send(embed=view.get_embed(), view=view, ephemeral=True)

    @commands.hybrid_command(
        name="suggest", description="Submit a suggestion to the bot owner."
    )
    async def suggest(self, context: Context) -> None:
        if context.interaction:
            await context.interaction.response.send_modal(SuggestionModal(self.bot))
        else:
            await context.send(
                "Please use the slash command `/suggest` to open the suggestion form."
            )


async def setup(bot) -> None:
    await bot.add_cog(Dashboard(bot))