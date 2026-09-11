import discord
from discord.ext import commands, tasks
from helpers.colors import COLOR_ACCENT
import feedparser
import logging

log = logging.getLogger("DarkSide.SecurityNews")

RSS_FEEDS = {
    "The Hacker News": "https://thehackernews.com/rss.xml",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "SecurityWeek": "https://feeds.feedburner.com/securityweek",
    "The Register (Security)": "https://www.theregister.com/security/headlines.atom",
    "Ars Technica (Security)": "https://feeds.arstechnica.com/arstechnica/security",
    "Wired (Security)": "https://www.wired.com/feed/category/security/latest/rss",
    "Threatpost": "https://threatpost.com/feed/",
    "SANS Internet Storm Center": "https://isc.sans.edu/rssfeed_full.xml",
    "Naked Security (Sophos)": "https://news.sophos.com/en-us/feed/",
    "Schneier on Security": "https://www.schneier.com/feed/atom/",
    "Graham Cluley": "https://grahamcluley.com/feed/",
    "CSO Online": "https://www.csoonline.com/feed/",
    "ZDNET (Security)": "https://www.zdnet.com/topic/security/rss.xml",
    "TechCrunch (Security)": "https://techcrunch.com/category/security/feed/",
    "Help Net Security": "https://www.helpnetsecurity.com/feed/",
    "Infosecurity Magazine": "https://www.infosecurity-magazine.com/rss/news/",
    "CyberScoop": "https://cyberscoop.com/feed/",
    "The Record": "https://therecord.media/feed",
    "Malwarebytes Labs": "https://www.malwarebytes.com/blog/feed/index.xml",
    "Cisco Talos": "https://blog.talosintelligence.com/rss/",
    "CrowdStrike Blog": "https://www.crowdstrike.com/en-us/blog/feed/",
    "Unit 42 (Palo Alto Networks)": "https://unit42.paloaltonetworks.com/feed/",
    "Microsoft Security Blog": "https://www.microsoft.com/en-us/security/blog/feed/",
    "Google Cloud Threat Intelligence": "https://cloud.google.com/blog/topics/threat-intelligence/rss/",
    "SC Media": "https://www.scmagazine.com/feed",
    "Tripwire State of Security": "https://www.tripwire.com/state-of-security/feed",
    "IBM Security Intelligence": "https://securityintelligence.com/feed/",
    "Recorded Future Blog": "https://www.recordedfuture.com/feed",
}

class SecurityNews(commands.Cog, name="security_news"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._target_channels: dict[int, int] = {}
        self._last_seen: dict[str, str] = {}
        self.fetch_security_news.start()

    def cog_unload(self) -> None:
        self.fetch_security_news.cancel()

    @commands.hybrid_group(
        name="secnews",
        invoke_without_command=True,
        description="Manage cybersecurity news feeds.",
    )
    @commands.has_permissions(administrator=True)
    async def secnews(self, ctx: commands.Context) -> None:
        """Manage cybersecurity news feeds."""
        prefix = ctx.prefix
        embed = discord.Embed(
            title="Configuration - Security News",
            description=f"Use `{prefix}secnews setchannel #channel` to set the news feed channel.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed, delete_after=20)

    @secnews.command(name="setchannel", description="Set the channel where security news will be posted.")
    @commands.has_permissions(administrator=True)
    async def secnews_setchannel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        """Configure the target channel for cyber alerts."""
        await self.bot.database.set_secnews_channel(ctx.guild.id, channel.id)
        self._target_channels[ctx.guild.id] = channel.id
        
        embed = discord.Embed(
            title="Channel Configured",
            description=f"Latest cyber news will now be sent to {channel.mention}.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed)

    @secnews.command(name="test", description="Force an immediate check of all security news feeds.")
    @commands.has_permissions(administrator=True)
    async def secnews_test(self, ctx: commands.Context) -> None:
        """Manually trigger a feed check, useful to verify the setup without waiting for the next cycle."""
        if ctx.guild.id not in self._target_channels:
            embed = discord.Embed(
                description="No channel is configured yet. Use `secnews setchannel #channel` first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        await ctx.send("Checking feeds now, this may take a few seconds...", delete_after=10)
        await self.fetch_security_news()
        embed = discord.Embed(
            description="Feed check complete. If no new article showed up, every feed was already up to date.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed)

    @tasks.loop(hours=2)
    async def fetch_security_news(self) -> None:
        if not self._target_channels:
            return

        for source_name, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    continue

                last_seen_id = self._last_seen.get(feed_url)
                new_entries = []
                for entry in feed.entries:
                    entry_id = entry.get("id", entry.get("link"))
                    if entry_id == last_seen_id:
                        break
                    new_entries.append(entry)

                if not new_entries:
                    continue

                # Remember the newest entry so we don't repost it next time.
                newest_id = new_entries[0].get("id", new_entries[0].get("link"))
                self._last_seen[feed_url] = newest_id
                await self.bot.database.set_secnews_last_seen(feed_url, newest_id)

                # On the very first run for a feed, only post the latest article
                # instead of flooding the channel with the whole backlog.
                if last_seen_id is None:
                    new_entries = new_entries[:1]

                for entry in reversed(new_entries):
                    summary = getattr(entry, "summary", "")
                    embed = discord.Embed(
                        title=entry.title,
                        url=entry.link,
                        description=f"{summary[:350]}...\n\n[Read full article]({entry.link})",
                        color=COLOR_ACCENT
                    )
                    embed.set_footer(text=f"Source: {source_name} | DarkSide SecIntel")

                    for guild_id, channel_id in self._target_channels.items():
                        channel = self.bot.get_channel(channel_id)
                        if not channel:
                            continue
                        await channel.send(embed=embed)

            except Exception as e:
                log.error(f"Error while fetching '{source_name}' RSS feed: {e}")

    @fetch_security_news.before_loop
    async def before_fetch_security_news(self) -> None:
        await self.bot.wait_until_ready()
        # bot.database is only assigned once setup_hook finishes, which happens
        # before the READY event fires, so it's safe to read from here.
        self._target_channels = await self.bot.database.get_secnews_channels()
        self._last_seen = await self.bot.database.get_secnews_last_seen()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SecurityNews(bot))