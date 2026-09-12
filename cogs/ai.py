import os

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from openai import OpenAI

from helpers.colors import COLOR_ACCENT, COLOR_DEFAULT, COLOR_ERROR


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

    @app_commands.command(
        name="setup_groq",
        description="Configure the Groq API key (owner only).",
    )
    @app_commands.describe(api_key="Your Groq API key (starts with gsk_)")
    @commands.is_owner()
    @app_commands.default_permissions(administrator=True)
    async def setup_groq(self, interaction: discord.Interaction, api_key: str) -> None:
        if not api_key.startswith("gsk_"):
            embed = discord.Embed(
                description="Invalid API key. It should start with `gsk_`.",
                color=COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            lines = [l for l in lines if not l.startswith("GROQ_API_KEY=")]
            lines.append(f"GROQ_API_KEY={api_key}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            embed = discord.Embed(
                description="API key configured and saved to `.env`. The bot is now ready to use Groq.",
                color=COLOR_ACCENT,
            )
        except Exception:
            embed = discord.Embed(
                description="API key configured for this session but could not be saved to `.env`. It will be lost on restart.",
                color=COLOR_ERROR,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="ask",
        description="Ask a question to the AI (only works in the configured channel).",
    )
    @app_commands.describe(question="The question you want to ask the AI")
    async def ask(self, context: Context, *, question: str) -> None:
        channel_id = await self.bot.database.get_ai_channel(context.guild.id)
        if channel_id is None:
            embed = discord.Embed(
                description="No AI channel configured. An admin must use `/setai` first.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        if context.channel.id != channel_id:
            embed = discord.Embed(
                description=f"You can only use this command in <#{channel_id}>.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        if self.client is None:
            embed = discord.Embed(
                description="The Groq API key is not configured. An owner must run `/setup_groq` first.",
                color=COLOR_ERROR,
            )
            await context.send(embed=embed)
            return

        async with context.typing():
            try:
                response = self.client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": question},
                    ],
                    stream=False,
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"An error occurred while contacting the AI: `{e}`"

        if len(answer) > 2000:
            chunks = [answer[i:i+1990] for i in range(0, len(answer), 1990)]
            for chunk in chunks:
                await context.reply(chunk, mention_author=False)
        else:
            await context.reply(answer, mention_author=False)

    @commands.hybrid_command(
        name="setai",
        description="Set the channel where the AI command can be used.",
    )
    @app_commands.describe(channel="The channel where /ask should be allowed")
    @commands.has_permissions(administrator=True)
    async def setai(self, context: Context, channel: discord.TextChannel) -> None:
        await self.bot.database.set_ai_channel(context.guild.id, channel.id)
        embed = discord.Embed(
            description=f"AI commands will now only work in {channel.mention}.",
            color=COLOR_ACCENT,
        )
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(AI(bot))