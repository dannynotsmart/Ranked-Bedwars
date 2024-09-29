from discord.ext import commands

from manager import DatabaseManager

import aiohttp
import discord
import os

initial_extensions = (
    "jishaku",
)

class RankedBedwarsBot(commands.Bot):
    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            everyone = False,
            users = True,
            roles = False,
            replied_user = True
        )

        intents = discord.Intents.all()

        super().__init__(
            allowed_mentions = allowed_mentions,
            intents = intents,
            command_prefix = commands.when_mentioned_or("!")
        )

        self.db = DatabaseManager()

    async def setup_hook(self):
        for extension in initial_extensions:
            await self.load_extension(extension)

        await self.db.connect()
        await self.db.load_cache()

    async def start(self):
        async with aiohttp.ClientSession() as session:
            self.session = session
            await super().start(os.getenv("TOKEN"))

    async def on_ready(self):
        print(f"{self.user} | {self.user.id} is ready.")


