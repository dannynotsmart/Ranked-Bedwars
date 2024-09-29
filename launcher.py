from bot import RankedBedwarsBot

import asyncio

async def main():
    async with RankedBedwarsBot() as bot:
        await bot.start()

asyncio.run(main())