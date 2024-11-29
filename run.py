import os
import asyncio
from loguru import logger
import discord
from discord.ext import commands

# config
from config import config


# self bot
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="Doraemon Microphone Bot",
    status=discord.Status.online,
    activity=discord.CustomActivity(
        "Reading Comics", emoji=discord.PartialEmoji.from_str("😂")
    ),
)
# required by on_ready cog
bot.version = "0.0.1"
bot.config = config


# load cogs
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded extension {filename}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename}: {e}")


# Main function to run the bot
async def main():
    async with bot:

        # load cogs
        logger.info(f"Loading cogs...")
        await load_cogs()

        # connect to discord
        logger.info(f"Connecting to Discord with token...")
        await bot.start(token=config["DISCORD_TOKEN"])


# Run the bot
asyncio.run(main())
