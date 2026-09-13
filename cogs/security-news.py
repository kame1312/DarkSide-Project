import asyncio
import calendar
import logging
import time

import discord
import feedparser
from discord.ext import commands, tasks

from helpers.colors import COLOR_ACCENT

log = logging.getLogger("DarkSide.SecurityNews")

MAX_ARTICLE_AGE_SECONDS = 3600

RSS_FEEDS = {
    "CERT-FR (ANSSI)": "https://www.cert.ssi.gouv.fr/feed/",
    "Cybermalveillance.gouv.fr": "https://www.cybermalveillance.gouv.fr/feed/atom-flux-complet",
    "UnderNews": "https://www.undernews.fr/feed/",
    "Korben": "https://korben.info/feed",
    "Numerama": "https://www.numerama.com/feed/",
    "01net (Sécurité)": "https://www.01net.com/rss/actualites/securite/",
    "Clubic": "https://www.clubic.com/feed/news.rss",
    "Journal du Hacker": "https://www.journalduhacker.net/newest.rss",
    "Silicon.fr": "https://www.silicon.fr/feed",
    "Usine Digitale": "https://www.usine-digitale.fr/rss/rss.xml",
    "Le Monde Informatique": "https://www.lemondeinformatique.fr/rss/actualites.xml",
    "ZDNet France": "https://www.zdnet.fr/feeds/rss/actualites/",
    "Developpez.com": "https://www.developpez.com/index/rss",
    "Blog du Modérateur": "https://www.blogdumoderateur.com/feed/",
    "Global Security Mag": "https://www.globalsecuritymag.fr/feed",
}


class SecurityNews(commands.Cog, name="security_news"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._target_channels: dict[int, int] = {}
        self._published_articles: set[str] = set()
        self._boot_done: bool = False
        self.fetch_security_news.start()

    def cog_unload(self) -> None:
        self.fetch_security_news.cancel()

    @commands.hybrid_group(name="secnews", invoke_without_command=True, description="Gère les flux d'actualités cybersécurité.")
    @commands.has_permissions(administrator=True)
    async def secnews(self, ctx: commands.Context) -> None:
        prefix = ctx.prefix
        embed = discord.Embed(
            title="Configuration - Actualités Cybersécurité",
            description=f"Utilisez `{prefix}secnews setchannel #channel` pour définir le salon des actualités.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed, delete_after=20)

    @secnews.command(name="setchannel", description="Définit le salon où les actualités seront publiées.")
    @commands.has_permissions(administrator=True)
    async def secnews_setchannel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_secnews_channel(ctx.guild.id, channel.id)
        self._target_channels[ctx.guild.id] = channel.id
        embed = discord.Embed(
            title="Salon configuré",
            description=f"Les actualités cybersécurité seront désormais envoyées dans {channel.mention}.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed)

    @secnews.command(name="test", description="Force une vérification immédiate de tous les flux.")
    @commands.has_permissions(administrator=True)
    async def secnews_test(self, ctx: commands.Context) -> None:
        if ctx.guild.id not in self._target_channels:
            embed = discord.Embed(
                description="Aucun salon n'est configuré. Utilisez d'abord `secnews setchannel #channel`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        await ctx.send("Vérification des flux en cours, cela peut prendre quelques secondes...", delete_after=10)
        await self.fetch_security_news()
        embed = discord.Embed(
            description="Vérification terminée. Si aucun nouvel article n'apparaît, tous les flux étaient déjà à jour.",
            color=COLOR_ACCENT
        )
        await ctx.send(embed=embed)

    @tasks.loop(minutes=10)
    async def fetch_security_news(self) -> None:
        if not self._target_channels:
            return

        catchup = not self._boot_done
        now = time.time()

        for source_name, feed_url in RSS_FEEDS.items():
            try:
                feed = await asyncio.to_thread(feedparser.parse, feed_url)
                if not feed.entries:
                    continue

                new_entries = []
                for entry in feed.entries:
                    entry_id = entry.get("id", entry.get("link"))
                    if not entry_id:
                        continue
                    if entry_id in self._published_articles:
                        continue

                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    is_too_old = False
                    if published is not None:
                        is_too_old = now - calendar.timegm(published) > MAX_ARTICLE_AGE_SECONDS

                    if catchup and (published is None or is_too_old):
                        self._published_articles.add(entry_id)
                        await self.bot.database.set_secnews_published(entry_id)
                        continue

                    new_entries.append(entry)

                if not new_entries:
                    continue

                for entry in new_entries:
                    entry_id = entry.get("id", entry.get("link"))
                    if entry_id:
                        self._published_articles.add(entry_id)
                        await self.bot.database.set_secnews_published(entry_id)

                for entry in reversed(new_entries):
                    summary = getattr(entry, "summary", "")
                    embed = discord.Embed(
                        title=entry.title,
                        url=entry.link,
                        description=f"{summary[:350]}...\n\n[Lire l'article complet]({entry.link})",
                        color=COLOR_ACCENT
                    )
                    embed.set_footer(text=f"Source : {source_name} | DarkSide SecIntel")

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
                log.error(f"Erreur lors de la récupération du flux '{source_name}' : {e}")

        if catchup:
            self._boot_done = True

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
        self._published_articles = await self.bot.database.get_secnews_published()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SecurityNews(bot))