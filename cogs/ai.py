import os

import discord
from discord.ext import commands
from openai import OpenAI

from helpers.colors import COLOR_ERROR

CONTEXT_LIMIT = 60

SYSTEM_PROMPT = (
    "Tu es un bot discord nommé DarkSide project. Kam1312 est ton créateur, "
    "dis le uniquement si on te le demandes. Ta page github est "
    "https://github.com/kame1312/DarkSide-Project/tree/main , sers t'en si tu en as "
    "besoin pour fournir des informations ou de l'aide sur des commandes. "
    "Dans l'historique, chaque message des utilisateurs est préfixé par leur pseudo "
    "sous la forme `Pseudo: message`. Plusieurs personnes différentes peuvent parler "
    "dans le même salon, tiens compte de qui dit quoi. "
    "Fais des réponses courtes et concises de 10 lignes grand maximum, "
    "sois utile et amical"
)

# Ordre de priorité : du meilleur au plus simple
FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class AI(commands.Cog, name="ai"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = self._pick_model()

    def _pick_model(self) -> str:
        try:
            available = {m.id for m in self.client.models.list()}
        except Exception:
            return FALLBACK_MODELS[0]

        for model_id in FALLBACK_MODELS:
            if model_id in available:
                return model_id

        for model_id in available:
            if "gpt-oss" in model_id or "llama" in model_id:
                return model_id

        return next(iter(available)) if available else FALLBACK_MODELS[0]

    def _next_model(self, current: str) -> str | None:
        try:
            index = FALLBACK_MODELS.index(current)
        except ValueError:
            return None
        if index + 1 < len(FALLBACK_MODELS):
            return FALLBACK_MODELS[index + 1]
        return None

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
            if previous.author.id == self.bot.user.id:
                conversation.append({"role": "assistant", "content": content})
            else:
                name = previous.author.display_name
                conversation.append({"role": "user", "content": f"{name}: {content}"})
        return conversation

    async def _generate_reply(self, conversation: list) -> str:
        last_error = None

        for _ in range(len(FALLBACK_MODELS)):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=conversation,
                    stream=False,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if "rate limit" in error_str or "429" in error_str:
                    next_model = self._next_model(self.model)
                    if next_model:
                        self.model = next_model
                        continue
                    raise

                if "does not exist" in error_str or "not found" in error_str or "404" in error_str:
                    next_model = self._next_model(self.model)
                    if next_model:
                        self.model = next_model
                        continue
                    self.model = self._pick_model()
                    continue

                raise

        raise last_error

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
            name = message.author.display_name
            conversation.append({"role": "user", "content": f"{name}: {prompt}"})

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