import asyncio
import calendar
import logging
import time

import discord
import feedparser
from discord.ext import commands, tasks

from helpers.colors import COLOR_ACCENT

log = logging.getLogger("DarkSide.SecurityNews")
MAX_AGE = 3600

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
    "Global Security Mag": "https://www.globalsecuritymag.fr/feed",
    "ANSSI": "https://www.ssi.gouv.fr/feed/",
    "Next (Next INpact)": "https://next.ink/feed/",
    "IT-Connect": "https://www.it-connect.fr/feed/",
    "Zataz": "https://www.zataz.com/feed/",
    "LeMagIT": "https://www.lemagit.fr/rss/actualites.xml",
    "The Hacker News": "https://thehackernews.com/feeds/posts/default",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "SecurityWeek": "https://www.securityweek.com/feed/",
    "SANS ISC": "https://isc.sans.edu/rssfeed.xml",
    "Ars Technica (Security)": "https://feeds.arstechnica.com/arstechnica/security",
    "The Register (Security)": "https://www.theregister.com/security/headlines.atom",
    "CISA Advisories": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    "Malwarebytes Labs": "https://www.malwarebytes.com/blog/feed/index.xml",
    "Cisco Talos": "https://blog.talosintelligence.com/rss/",
    "PortSwigger Research": "https://portswigger.net/research/rss",
    "Hackread": "https://hackread.com/feed/",
    "GBHackers": "https://gbhackers.com/feed/",
}


class SecurityNews(commands.Cog, name="security_news"):
    def __init__(self, bot):
        self.bot = bot
        self._channels = {}
        self._seen = set()
        self._boot_done = False
        self.fetch.start()

    def cog_unload(self):
        self.fetch.cancel()

    async def _mark(self, entry_id):
        self._seen.add(entry_id)
        await self.bot.database.set_secnews_published(entry_id)

    @commands.group(name="secnews", invoke_without_command=True, description="Gère les flux d'actualités cybersécurité.")
    @commands.has_permissions(administrator=True)
    async def secnews(self, ctx):
        await ctx.send(embed=discord.Embed(
            title="Configuration - Actualités Cybersécurité",
            description=f"Utilisez `{ctx.prefix}secnews setchannel #channel` pour définir le salon des actualités.",
            color=COLOR_ACCENT,
        ), delete_after=20)

    @secnews.command(name="setchannel", description="Définit le salon où les actualités seront publiées.")
    @commands.has_permissions(administrator=True)
    async def secnews_setchannel(self, ctx, channel: discord.TextChannel):
        await self.bot.database.set_secnews_channel(ctx.guild.id, channel.id)
        self._channels[ctx.guild.id] = channel.id
        await ctx.send(embed=discord.Embed(
            title="Salon configuré",
            description=f"Les actualités cybersécurité seront désormais envoyées dans {channel.mention}.",
            color=COLOR_ACCENT,
        ))

    @secnews.command(name="test", description="Force une vérification immédiate de tous les flux.")
    @commands.has_permissions(administrator=True)
    async def secnews_test(self, ctx):
        if ctx.guild.id not in self._channels:
            return await ctx.send(embed=discord.Embed(
                description="Aucun salon n'est configuré. Utilisez d'abord `secnews setchannel #channel`.",
                color=discord.Color.red(),
            ))
        await ctx.send("Vérification des flux en cours...", delete_after=10)
        await self.fetch()
        await ctx.send(embed=discord.Embed(
            description="Vérification terminée. Si aucun nouvel article n'apparaît, tous les flux étaient déjà à jour.",
            color=COLOR_ACCENT,
        ))

    @tasks.loop(minutes=20)
    async def fetch(self):
        if not self._channels:
            return
        catchup, now = not self._boot_done, time.time()

        for source, url in RSS_FEEDS.items():
            try:
                feed = await asyncio.to_thread(feedparser.parse, url)
                fresh = []
                for entry in feed.entries:
                    entry_id = entry.get("id", entry.get("link"))
                    if not entry_id or entry_id in self._seen:
                        continue
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    too_old = published is not None and now - calendar.timegm(published) > MAX_AGE
                    if catchup and (published is None or too_old):
                        await self._mark(entry_id)
                        continue
                    fresh.append(entry)

                if not fresh:
                    continue

                for entry in fresh:
                    await self._mark(entry.get("id", entry.get("link")))

                for entry in reversed(fresh):
                    embed = discord.Embed(
                        title=entry.title,
                        url=entry.link,
                        description=f"{getattr(entry, 'summary', '')[:350]}...\n\n[Lire l'article complet]({entry.link})",
                        color=COLOR_ACCENT,
                    )
                    embed.set_footer(text=f"Source : {source} | DarkSide SecIntel")
                    for channel_id in self._channels.values():
                        if channel := self.bot.get_channel(channel_id):
                            await channel.send(embed=embed)
            except Exception as e:
                log.error(f"Erreur lors de la récupération du flux '{source}' : {e}")

        if catchup:
            self._boot_done = True

    @fetch.before_loop
    async def before_fetch(self):
        await self.bot.wait_until_ready()
        self._channels = await self.bot.database.get_secnews_channels()
        self._seen = await self.bot.database.get_secnews_published()


async def setup(bot):
    await bot.add_cog(SecurityNews(bot))