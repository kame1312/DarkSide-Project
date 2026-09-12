import asyncio
import calendar
import logging
import time

import discord
import feedparser
from discord.ext import commands, tasks

from helpers.colors import COLOR_ACCENT

log = logging.getLogger("DarkSide.SecurityNews")

RSS_FEEDS = {
    # Original sources
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
    # Additional sources
    "SentinelOne Blog": "https://www.sentinelone.com/blog/feed/",
    "Check Point Research": "https://research.checkpoint.com/feed/",
    "ESET WeLiveSecurity": "https://www.welivesecurity.com/feed/",
    "Tenable Blog": "https://www.tenable.com/blog/feed",
    "Rapid7 Blog": "https://blog.rapid7.com/rss/",
    "Qualys Blog": "https://blog.qualys.com/feed",
    "Kaspersky Blog": "https://www.kaspersky.com/blog/feed/",
    "Security Affairs": "https://securityaffairs.com/feed",
    "HackRead": "https://www.hackread.com/feed/",
    "GBHackers": "https://gbhackers.com/feed/",
    "Cybersecurity News": "https://cybersecuritynews.com/feed/",
    "Latest Hacking News": "https://latesthackingnews.com/feed/",
    "KitPloit": "https://www.kitploit.com/feed/",
    "The Daily Swig": "https://portswigger.net/daily-swig/rss",
    "PortSwigger Research": "https://portswigger.net/research/rss",
    "Google Online Security Blog": "https://security.googleblog.com/feeds/posts/default",
    "Google Project Zero": "https://googleprojectzero.blogspot.com/feeds/posts/default",
    "Snyk Blog": "https://snyk.io/blog/feed/",
    "Aqua Security": "https://blog.aquasec.com/rss.xml",
    "Wiz Blog": "https://www.wiz.io/blog/rss.xml",
    "Zero Day Initiative": "https://www.zerodayinitiative.com/blog?format=rss",
    "HackerOne": "https://www.hackerone.com/blog.rss",
    "Bugcrowd": "https://www.bugcrowd.com/blog/feed/",
    "Darknet Diaries": "https://feeds.megaphone.fm/darknetdiaries",
    "Bishop Fox Blog": "https://bishopfox.com/blog/rss.xml",
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
        prefix = ctx.prefix
        embed = discord.Embed(
            title="Configuration - Security News",
            description=f"Use `{prefix}secnews setchannel #channel` to set the news feed channel.",
            color=COLOR_ACCENT,
        )
        await ctx.send(embed=embed, delete_after=20)

    @secnews.command(name="setchannel", description="Set the channel where security news will be posted.")
    @commands.has_permissions(administrator=True)
    async def secnews_setchannel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_secnews_channel(ctx.guild.id, channel.id)
        self._target_channels[ctx.guild.id] = channel.id
        embed = discord.Embed(
            title="Channel Configured",
            description=f"Latest cyber news will now be sent to {channel.mention}.",
            color=COLOR_ACCENT,
        )
        await ctx.send(embed=embed)

    @secnews.command(name="test", description="Force an immediate check of all security news feeds.")
    @commands.has_permissions(administrator=True)
    async def secnews_test(self, ctx: commands.Context) -> None:
        if ctx.guild.id not in self._target_channels:
            embed = discord.Embed(
                description="No channel is configured yet. Use `secnews setchannel #channel` first.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        await ctx.send("Checking feeds now, this may take a few seconds...", delete_after=10)
        await self.fetch_security_news()
        embed = discord.Embed(
            description="Feed check complete. If no new article showed up, every feed was already up to date.",
            color=COLOR_ACCENT,
        )
        await ctx.send(embed=embed)

    @tasks.loop(minutes=10)
    async def fetch_security_news(self) -> None:
        if not self._target_channels:
            return

        oldest_article: dict | None = None

        for source_name, feed_url in RSS_FEEDS.items():
            try:
                feed = await asyncio.to_thread(feedparser.parse, feed_url)
                if not feed.entries:
                    continue

                last_seen_id = self._last_seen.get(feed_url)

                if last_seen_id is None:
                    newest = feed.entries[0]
                    newest_id = newest.get("id") or newest.get("link")
                    if newest_id:
                        self._last_seen[feed_url] = newest_id
                        await self.bot.database.set_secnews_last_seen(feed_url, newest_id)
                    continue

                oldest_unposted = None
                for entry in feed.entries:
                    entry_id = entry.get("id") or entry.get("link")
                    if not entry_id:
                        continue
                    if entry_id == last_seen_id:
                        break
                    oldest_unposted = entry

                if oldest_unposted is None:
                    continue

                entry_id = oldest_unposted.get("id") or oldest_unposted.get("link")
                if not entry_id:
                    continue

                pub_date = (
                    oldest_unposted.get("published_parsed")
                    or oldest_unposted.get("updated_parsed")
                )
                pub_timestamp = calendar.timegm(pub_date) if pub_date else time.time()

                if oldest_article is None or pub_timestamp < oldest_article["timestamp"]:
                    oldest_article = {
                        "source_name": source_name,
                        "feed_url": feed_url,
                        "entry": oldest_unposted,
                        "entry_id": entry_id,
                        "timestamp": pub_timestamp,
                    }

            except Exception as e:
                log.error(f"Error while fetching '{source_name}' RSS feed: {e}")

        if oldest_article is None:
            return

        entry = oldest_article["entry"]
        summary = getattr(entry, "summary", "")
        link = getattr(entry, "link", "")
        title = getattr(entry, "title", "Untitled")

        embed = discord.Embed(
            title=title,
            url=link,
            description=f"{summary[:350]}...\n\n[Read full article]({link})",
            color=COLOR_ACCENT,
        )
        embed.set_footer(text=f"Source: {oldest_article['source_name']} | DarkSide SecIntel")

        for guild_id, channel_id in self._target_channels.items():
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            try:
                await channel.send(embed=embed)
            except Exception as e:
                log.error(f"Failed to send news to channel {channel_id}: {e}")

        self._last_seen[oldest_article["feed_url"]] = oldest_article["entry_id"]
        await self.bot.database.set_secnews_last_seen(
            oldest_article["feed_url"], oldest_article["entry_id"]
        )

    @fetch_security_news.before_loop
    async def before_fetch_security_news(self) -> None:
        await self.bot.wait_until_ready()
        self._target_channels = await self.bot.database.get_secnews_channels()
        self._last_seen = await self.bot.database.get_secnews_last_seen()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SecurityNews(bot))