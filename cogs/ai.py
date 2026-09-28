import os

import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI

from helpers.colors import COLOR_ACCENT, COLOR_ERROR

CONTEXT_LIMIT = 30
MODEL_NAME = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "Tu es un bot discord nommé DarkSide project. Kam1312 est ton créateur, dis le uniquement si on te le demandes. Ta page github est https://github.com/kame1312/DarkSide-Project/tree/main , sers toi en si tu en as besoin pour fournir des informations ou de l'aide sur des commandes.  Fais des réponses courtes et concises de 10 lignes grand maximum, sois utile et amical"


class AI(commands.Cog, name="ai"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )

    async def _fetch_context(self, message: discord.Message) -> list:
        history = []
        async for previous in message.channel.history(limit=CONTEXT_LIMIT, before=message):
            history.append(previous)
        history.reverse()

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        for previous in history:
            if previous.author.bot and previous.author.id != self.bot.user.id:
                continue
            content = previous.clean_content.strip()
            if not content:
                continue
            role = "assistant" if previous.author.id == self.bot.user.id else "user"
            conversation.append({"role": role, "content": content})
        return conversation

    async def _generate_reply(self, conversation: list) -> str:
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=conversation,
            stream=False,
        )
        return response.choices[0].message.content

    async def _respond(self, message: discord.Message, prompt: str) -> None:
        if self.client is None:
            embed = discord.Embed(
                description="The Groq API key is not configured. Please set `GROQ_API_KEY` in the `.env` file.",
                color=COLOR_ERROR,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        conversation = await self._fetch_context(message)
        if prompt:
            conversation.append({"role": "user", "content": prompt})

        async with message.channel.typing():
            try:
                answer = await self._generate_reply(conversation)
            except Exception as e:
                answer = f"An error occurred while contacting the AI: `{e}`"

        if len(answer) > 2000:
            chunks = [answer[i:i + 1990] for i in range(0, len(answer), 1990)]
        else:
            chunks = [answer]

        for chunk in chunks:
            await message.reply(chunk, mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        mentioned = self.bot.user in message.mentions
        replied_to_bot = (
            message.reference is not None
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author.id == self.bot.user.id
        )

        if not mentioned and not replied_to_bot:
            return

        prompt = message.content
        if mentioned:
            prompt = prompt.replace(f"<@{self.bot.user.id}>", "")
            prompt = prompt.replace(f"<@!{self.bot.user.id}>", "")
        prompt = prompt.strip()

        if not prompt:
            return

        await self._respond(message, prompt)


async def setup(bot) -> None:
    await bot.add_cog(AI(bot))