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
    "Utilise la langue que les messages que tu lis utilise"
)

FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

RETRYABLE = ("rate limit", "429", "does not exist", "not found", "404")


class AI(commands.Cog, name="ai"):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        self.model = None
        if api_key := os.getenv("GROQ_API_KEY"):
            self.client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            self.model = self._pick_model()

    def _pick_model(self):
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
        return next(iter(available), FALLBACK_MODELS[0])

    def _next_model(self, current):
        try:
            index = FALLBACK_MODELS.index(current)
        except ValueError:
            return None
        return FALLBACK_MODELS[index + 1] if index + 1 < len(FALLBACK_MODELS) else None

    async def _fetch_context(self, message):
        history = [m async for m in message.channel.history(limit=CONTEXT_LIMIT, before=message)]
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        for prev in reversed(history):
            if prev.author.bot and prev.author.id != self.bot.user.id:
                continue
            content = prev.clean_content.strip()
            if not content:
                continue
            if prev.author.id == self.bot.user.id:
                conversation.append({"role": "assistant", "content": content})
            else:
                conversation.append({"role": "user", "content": f"{prev.author.display_name}: {content}"})
        return conversation

    async def _generate_reply(self, conversation):
        last_error = None
        for _ in range(len(FALLBACK_MODELS)):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, messages=conversation, stream=False)
                return resp.choices[0].message.content
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                if not any(k in msg for k in RETRYABLE):
                    raise
                is_rate_limit = "rate limit" in msg or "429" in msg
                next_model = self._next_model(self.model)
                if next_model:
                    self.model = next_model
                elif is_rate_limit:
                    raise
                else:
                    self.model = self._pick_model()
        raise last_error

    async def _respond(self, message, prompt):
        if self.client is None:
            return await message.reply(embed=discord.Embed(
                description="The Groq API key is not configured. Please set `GROQ_API_KEY` in the `.env` file.",
                color=COLOR_ERROR), mention_author=False)

        conversation = await self._fetch_context(message)
        if prompt:
            conversation.append({"role": "user", "content": f"{message.author.display_name}: {prompt}"})

        async with message.channel.typing():
            try:
                answer = await self._generate_reply(conversation)
            except Exception as e:
                answer = f"An error occurred while contacting the AI: `{e}`"

        for i in range(0, len(answer), 1990):
            await message.reply(answer[i:i + 1990], mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        mentioned = self.bot.user in message.mentions
        replied = (message.reference is not None
                   and isinstance(message.reference.resolved, discord.Message)
                   and message.reference.resolved.author.id == self.bot.user.id)
        if not mentioned and not replied:
            return

        prompt = message.content
        if mentioned:
            prompt = prompt.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "")
        if prompt := prompt.strip():
            await self._respond(message, prompt)


async def setup(bot):
    await bot.add_cog(AI(bot))