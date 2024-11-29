# cogs/on_ready.py
from discord.ext import commands
from loguru import logger
import discord
from discord.utils import get


class OnReady(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # log bot info
        logger.info(f"Logged in as {self.bot.user.name} - {self.bot.user.id}")

        # print version
        try:
            logger.info(f"Version: {self.bot.version}")
        except AttributeError:
            logger.warning("Version not set")

        # debug latency
        logger.info(f"Latency: {self.bot.latency * 1000:.0f}ms")
        logger.info(f"Connected to {len(self.bot.guilds)} guilds")

        # check if admins is set
        try:
            logger.info(f"Admins: {len(self.bot.config['SUDOERS'])}")
        except AttributeError:
            logger.warning("Admins not set")

        # list guilds
        logger.info("Guilds:")
        for guild in self.bot.guilds:
            logger.info(f" - {guild.name} ({guild.id})")

        # print ready message
        logger.info("Status Ready ✅")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnReady(bot))
