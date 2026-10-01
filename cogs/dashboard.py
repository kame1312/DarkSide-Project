import os

import discord
from discord.ext import commands

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR

DEFAULT_PANEL_TITLE = "Support"
DEFAULT_PANEL_DESC = "Click the button below to open a ticket.\nA staff member will reply in a private channel."
DEFAULT_WELCOME = "Welcome {user} to **{guild}**!"


def make_embed(desc=None, color=COLOR_DEFAULT, **kw):
    return discord.Embed(description=desc, color=color, **kw)


def format_welcome(template, member):
    try:
        return (template or DEFAULT_WELCOME).format(
            user=member.mention, user_name=member.name, user_display=member.display_name,
            guild=member.guild.name, member_count=member.guild.member_count)
    except (KeyError, IndexError):
        return f"Welcome {member.mention} to **{member.guild.name}**!"


class SuggestionModal(discord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(title="Submit a Suggestion")
        self.title_input = discord.ui.TextInput(
            label="Title", style=discord.TextStyle.short,
            placeholder="Brief summary of your idea", max_length=100)
        self.desc_input = discord.ui.TextInput(
            label="Description", style=discord.TextStyle.paragraph,
            placeholder="Explain your idea in detail...", max_length=1500)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        channel_id = await self.bot.database.get_owner_suggestion_channel()
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if not channel:
            return await interaction.followup.send(embed=make_embed(
                "The suggestion channel is not configured. Please contact the owner.", COLOR_ERROR), ephemeral=True)

        embed = discord.Embed(title=f"💡 {self.title_input.value}",
                              description=self.desc_input.value, color=COLOR_ACCENT)
        embed.set_author(name=f"Suggestion from {interaction.user} (ID: {interaction.user.id})",
                         icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Server: {interaction.guild.name} ({interaction.guild.id})")
        await channel.send(embed=embed)
        await interaction.followup.send(embed=make_embed("Your suggestion has been sent to the owner!"), ephemeral=True)


class WelcomeMessageModal(discord.ui.Modal):
    def __init__(self, bot, current_message, parent_view, parent_message):
        self.bot, self.parent_view, self.parent_message = bot, parent_view, parent_message
        super().__init__(title="Welcome Message")
        self.message_input = discord.ui.TextInput(
            label="Message", style=discord.TextStyle.paragraph,
            placeholder="Welcome {user} to **{guild}**!",
            default=current_message or DEFAULT_WELCOME, max_length=1000)
        self.add_item(self.message_input)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        await self.bot.database.set_welcome_message(interaction.guild.id, self.message_input.value)
        self.parent_view.current_message = self.message_input.value
        try:
            await self.parent_message.edit(embed=self.parent_view.get_embed(), view=self.parent_view)
        except discord.HTTPException:
            pass


class TicketPanelModal(discord.ui.Modal):
    def __init__(self, bot, current_title, current_desc):
        self.bot = bot
        super().__init__(title="Ticket Panel Message")
        self.title_input = discord.ui.TextInput(
            label="Panel Title", style=discord.TextStyle.short, placeholder="Support",
            default=current_title or DEFAULT_PANEL_TITLE, max_length=100)
        self.desc_input = discord.ui.TextInput(
            label="Panel Description", style=discord.TextStyle.paragraph,
            placeholder="Click the button below to open a ticket...",
            default=current_desc or DEFAULT_PANEL_DESC, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        await self.bot.database.set_ticket_panel_config(
            interaction.guild.id, self.title_input.value, self.desc_input.value)


class _ConfigView(discord.ui.View):
    """Base des sous-vues de config : gère l'embed, le check et le bouton retour."""
    title = ""
    description = ""

    def __init__(self, bot, author_id, parent, banner_url=None):
        super().__init__(timeout=300)
        self.bot, self.author_id, self.parent, self.banner_url = bot, author_id, parent, banner_url

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This is not your dashboard.", ephemeral=True)
            return False
        return True

    def fields(self):
        return []

    def get_embed(self):
        embed = discord.Embed(title=self.title, description=self.description, color=COLOR_ACCENT)
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        for name, value, inline in self.fields():
            embed.add_field(name=name, value=value, inline=inline)
        return embed

    async def load_current(self, guild_id):
        pass

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=4)
    async def back(self, interaction, _):
        await interaction.response.edit_message(embed=self.parent.get_embed(), view=self.parent)


class TicketsConfigView(_ConfigView):
    title = "🎫 Tickets Configuration"
    description = "Select the channels and role below, then click **Save** to apply."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_category = self.pending_log = self.pending_support = None

    async def load_current(self, guild_id):
        config = await self.bot.database.get_ticket_config(guild_id)
        if config:
            self.pending_category = config["category_id"]
            self.pending_log = config["log_channel_id"]
            self.pending_support = config["support_role_id"]

    def fields(self):
        return [
            ("Category", f"<#{self.pending_category}>" if self.pending_category else "❌ Not set", True),
            ("Log Channel", f"<#{self.pending_log}>" if self.pending_log else "❌ Not set", True),
            ("Support Role", f"<@&{self.pending_support}>" if self.pending_support else "❌ Not set", True),
        ]

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.category],
                       placeholder="Select a category...", row=0)
    async def select_category(self, interaction, select):
        self.pending_category = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Select a log channel...", row=1)
    async def select_logs(self, interaction, select):
        self.pending_log = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select a support role...", row=2)
    async def select_support(self, interaction, select):
        self.pending_support = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾", row=3)
    async def save(self, interaction, _):
        await interaction.response.defer()
        await self.bot.database.set_ticket_config(
            interaction.guild.id, category_id=self.pending_category,
            log_channel_id=self.pending_log, support_role_id=self.pending_support)

    @discord.ui.button(label="Edit Panel Message", style=discord.ButtonStyle.primary, emoji="✏️", row=3)
    async def edit_panel(self, interaction, _):
        config = await self.bot.database.get_ticket_panel_config(interaction.guild.id)
        await interaction.response.send_modal(TicketPanelModal(
            self.bot, config["title"] if config else None,
            config["description"] if config else None))

    @discord.ui.button(label="Send Panel", style=discord.ButtonStyle.success, emoji="📩", row=3)
    async def send_panel(self, interaction, _):
        await interaction.response.defer(ephemeral=True)
        from cogs.tickets import TicketPanelView
        config = await self.bot.database.get_ticket_panel_config(interaction.guild.id)
        title = (config and config["title"]) or DEFAULT_PANEL_TITLE
        desc = (config and config["description"]) or DEFAULT_PANEL_DESC
        embed = make_embed(desc, COLOR_ACCENT, title=title)
        embed.set_footer(text="Ticket system")
        await interaction.channel.send(embed=embed, view=TicketPanelView())


class SecNewsConfigView(_ConfigView):
    title = "📰 Security News Configuration"
    description = "Select a channel below, then click **Save** to apply."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_channel = None

    async def load_current(self, guild_id):
        self.pending_channel = (await self.bot.database.get_secnews_channels()).get(guild_id)

    def fields(self):
        return [("News Channel",
                 f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set", False)]

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Select a news channel...", row=0)
    async def select_channel(self, interaction, select):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾", row=1)
    async def save(self, interaction, _):
        await interaction.response.defer()
        if self.pending_channel:
            await self.bot.database.set_secnews_channel(interaction.guild.id, self.pending_channel)

    @discord.ui.button(label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1)
    async def test(self, interaction, _):
        await interaction.response.defer(ephemeral=True)
        if cog := self.bot.get_cog("security_news"):
            await cog.fetch()


class GitWatchConfigView(_ConfigView):
    title = "🐙 GitWatch Configuration"
    description = "Select a channel below, then click **Save** to apply."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_channel = None

    async def load_current(self, guild_id=None):
        if cog := self.bot.get_cog("gitwatch"):
            self.pending_channel = cog.channel_id

    def fields(self):
        return [("Notification Channel",
                 f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set", False)]

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Select a channel...", row=0)
    async def select_channel(self, interaction, select):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾", row=1)
    async def save(self, interaction, _):
        await interaction.response.defer()
        if cog := self.bot.get_cog("gitwatch"):
            cog.channel_id = self.pending_channel
            cog.last_commit_id = None
            cog._save_config()

    @discord.ui.button(label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1)
    async def test(self, interaction, _):
        await interaction.response.defer(ephemeral=True)
        cog = self.bot.get_cog("gitwatch")
        if cog and (commits := await cog._fetch_commits()):
            c = commits[0]
            await interaction.followup.send(embed=discord.Embed(
                title=c["title"], url=c["link"],
                description=f"Pushed by **{c['author']}**", color=COLOR_ACCENT), ephemeral=True)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫", row=1)
    async def disable(self, interaction, _):
        if cog := self.bot.get_cog("gitwatch"):
            cog.channel_id = None
            cog._save_config()
        self.pending_channel = None
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class WelcomeConfigView(_ConfigView):
    title = "👋 Welcome Configuration"
    description = "Configure the welcome channel and message, then click **Save Channel** to apply the channel."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_channel = None
        self.current_message = None

    async def load_current(self, guild_id):
        config = await self.bot.database.get_welcome_config(guild_id)
        if config:
            self.pending_channel, self.current_message = config[0], config[1]

    def fields(self):
        preview = self.current_message or DEFAULT_WELCOME
        if len(preview) > 200:
            preview = preview[:200] + "..."
        return [
            ("Channel", f"<#{self.pending_channel}>" if self.pending_channel else "❌ Not set", False),
            ("Message Preview", preview, False),
        ]

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Select a welcome channel...", row=0)
    async def select_channel(self, interaction, select):
        self.pending_channel = select.values[0].id
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Save Channel", style=discord.ButtonStyle.success, emoji="💾", row=1)
    async def save_channel(self, interaction, _):
        await interaction.response.defer()
        if self.pending_channel:
            await self.bot.database.set_welcome_channel(interaction.guild.id, self.pending_channel)

    @discord.ui.button(label="Set Message", style=discord.ButtonStyle.primary, emoji="✏️", row=1)
    async def set_message(self, interaction, _):
        await interaction.response.send_modal(WelcomeMessageModal(
            self.bot, self.current_message, self, interaction.message))

    @discord.ui.button(label="Test", style=discord.ButtonStyle.primary, emoji="🧪", row=1)
    async def test(self, interaction, _):
        await interaction.response.defer(ephemeral=True)
        config = await self.bot.database.get_welcome_config(interaction.guild.id)
        if not config or not config[0]:
            return
        channel = interaction.guild.get_channel(config[0])
        if not channel:
            return
        embed = make_embed(format_welcome(config[1], interaction.user))
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Member #{interaction.guild.member_count}")
        await channel.send(content=interaction.user.mention, embed=embed)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫", row=2)
    async def disable(self, interaction, _):
        await self.bot.database.set_welcome_channel(interaction.guild.id, None)
        self.pending_channel = None
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class DashboardView(discord.ui.View):
    def __init__(self, bot, author_id, banner_url=None):
        super().__init__(timeout=600)
        self.bot, self.author_id, self.banner_url = bot, author_id, banner_url

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This is not your dashboard.", ephemeral=True)
            return False
        return True

    def get_embed(self):
        embed = discord.Embed(
            title="Configuration Dashboard",
            description="Welcome to the configuration dashboard. Click a button below to configure a feature.",
            color=COLOR_ACCENT)
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        embed.set_footer(text="DarkSide Project Dashboard")
        return embed

    async def _open(self, interaction, view_cls):
        view = view_cls(self.bot, self.author_id, self, self.banner_url)
        await view.load_current(interaction.guild.id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @discord.ui.button(label="Tickets", style=discord.ButtonStyle.primary, emoji="🎫", row=0)
    async def tickets_btn(self, interaction, _):
        await self._open(interaction, TicketsConfigView)

    @discord.ui.button(label="Security News", style=discord.ButtonStyle.primary, emoji="📰", row=0)
    async def secnews_btn(self, interaction, _):
        await self._open(interaction, SecNewsConfigView)

    @discord.ui.button(label="GitWatch", style=discord.ButtonStyle.primary, emoji="🐙", row=0)
    async def gitwatch_btn(self, interaction, _):
        await self._open(interaction, GitWatchConfigView)

    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.primary, emoji="👋", row=1)
    async def welcome_btn(self, interaction, _):
        await self._open(interaction, WelcomeConfigView)

    @discord.ui.button(label="Suggestions", style=discord.ButtonStyle.success, emoji="💡", row=1)
    async def suggestions_btn(self, interaction, _):
        await interaction.response.send_modal(SuggestionModal(self.bot))

    @discord.ui.button(label="Help", style=discord.ButtonStyle.secondary, emoji="❓", row=2)
    async def help_btn(self, interaction, _):
        embed = discord.Embed(title="Help", description="List of available commands:", color=COLOR_DEFAULT)
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner" and not await self.bot.is_owner(interaction.user):
                continue
            lines = []
            for command in cog.get_commands():
                desc = (command.description or command.help or "No description").partition("\n")[0]
                lines.append(f"{command.name} - {desc}")
                if isinstance(command, commands.Group):
                    for sub in command.commands:
                        sub_desc = (sub.description or sub.help or "No description").partition("\n")[0]
                        lines.append(f"  └ {command.name} {sub.name} - {sub_desc}")
            if lines:
                embed.add_field(name=cog_name.replace("_", " ").title(),
                                value=f"```{chr(10).join(lines)}```", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="✖️", row=2)
    async def close_btn(self, interaction, _):
        await interaction.message.delete()


class Dashboard(commands.Cog, name="dashboard"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="dashboard", description="Open the interactive configuration dashboard.")
    @commands.has_permissions(administrator=True)
    async def dashboard(self, context):
        banner = os.getenv("BANNER_URL") or (self.bot.user.banner.url if self.bot.user.banner else None)
        view = DashboardView(self.bot, context.author.id, banner)
        await context.send(embed=view.get_embed(), view=view, ephemeral=True)

    @commands.hybrid_command(name="suggest", description="Submit a suggestion to the bot owner.")
    async def suggest(self, context):
        if context.interaction:
            await context.interaction.response.send_modal(SuggestionModal(self.bot))
        else:
            await context.send("Please use the slash command `/suggest` to open the suggestion form.")


async def setup(bot):
    await bot.add_cog(Dashboard(bot))