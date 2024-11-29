# use yt-dlp instead of youtube_dl
import yt_dlp as youtube_dl
from pytubefix import YouTube

# for playback
from discord import FFmpegOpusAudio, FFmpegPCMAudio, PCMVolumeTransformer
import asyncio

# discord imports
from discord.ext import commands
from discord.utils import get as discord_get

# logging
import traceback
from loguru import logger

# types
import typing

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

# ytdl options
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M",
    "options": "-vn",
}
ytdlp_opts = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audioformat": "mp3",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "playlistend": 10,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            # "preferredcodec": "vorbis",
            # "preferredcodec": "opus",
            # "preferredcodec": "mp3",
            # "preferredquality": "320",
        }
    ],
}


# ytdlp client
ytdl = youtube_dl.YoutubeDL(ytdlp_opts)


# Data classes
class Track:
    def __init__(self, title: str, url: str, stream_urls: typing.List[str]):
        self.title = title
        self.url = url
        self.stream_urls = stream_urls

    def get_title(self):
        return self.title

    def get_url(self):
        return self.url

    def get_audio_url(self):
        return self.stream_urls[0]

    def get_stream_urls(self):
        return self.stream_urls


# ytdlp url extractor
async def extract_media_url(
    url: str, stream: bool = True, **kwargs
) -> typing.List[Track]:
    """
    Async extract video information from YouTube URL.

    Args:
        url (str): YouTube video or playlist URL
        stream (bool): Whether to prepare for streaming
        **kwargs: Additional arguments including optional event loop

    Returns:
        List of dictionaries containing video metadata
    """

    # Get event loop from kwargs or use default
    loop = kwargs.get("loop") or asyncio.get_event_loop()

    try:
        # Run extraction in thread executor
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        # Check if there are more than 10 entries
        # Split to first 10
        if "entries" in data and len(data["entries"]) > 10:
            data = data["entries"][:10]

        # Process playlist or single video
        if "entries" in data:
            # Playlist processing
            media_info: typing.List[Track] = []
            for entry in data["entries"]:
                if entry:
                    media_info += [
                        Track(
                            title=entry.get("title", "Unknown"),
                            url=entry.get("webpage_url", "Unknown"),
                            stream_urls=[
                                fmt.get("url")
                                for fmt in data.get("formats", [])
                                if fmt.get("acodec") != "none"
                                and fmt.get("vcodec") != "none"
                            ],
                        )
                    ]
            return media_info
        else:
            # Single video processing
            return [
                Track(
                    title=data.get("title", "Unknown"),
                    url=data.get("webpage_url", "Unknown"),
                    stream_urls=[
                        fmt.get("url")
                        for fmt in data.get("formats", [])
                        if fmt.get("acodec") != "none" and fmt.get("vcodec") != "none"
                    ],
                )
            ]

    except Exception as e:
        print(f"Error extracting media: {e}")
        return []


# Music Player
class MusicPlayer:

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.queues: typing.List[typing.Dict] = []
        self.is_playing: bool = False

    async def clear_queue(self):
        """
        Clear the queue
        """
        self.queues = []
        # stop playback
        await self.stop()

    async def queue_track(self, ctx: commands.Context, track: Track):
        """
        Queue a Track for Playback
        """
        # add to queue
        self.queues.append({"context": ctx, "track": track})
        # check if we are already playing else trigger playback
        if not self.is_playing:
            await self.play_next()

    async def play_next(self):
        """
        Play the next track in the queue
        """
        if len(self.queues):
            # get the first track
            track = self.queues.pop(0)
            track_ctx: commands.Context = track["context"]
            # is playing
            try:
                # set playing flag
                self.is_playing = True

                # get voice client
                voice = discord_get(
                    self.bot.voice_clients, channel=track_ctx.channel
                )

                # check if we are not already connected to the same channel
                if voice is None or not voice.is_connected():
                    logger.info(f"🎵 Joining {track_ctx.channel}")
                    # try to disconnect from other channels
                    try:
                        await [await vc.disconnect() for vc in self.bot.voice_clients]
                        logger.info(f"🎵 Reconnecting to target Voice Channel {track_ctx.channel.name} [{track_ctx.channel.id}]")
                    except Exception as e:
                        pass
                    # connect to the channel
                    await track_ctx.channel.connect()
                    # get voice client
                    voice = discord_get(
                        self.bot.voice_clients, channel=track_ctx.channel
                    )
                
                    

                # if voice.channel.id != track_ctx.channel.id:
                #     logger.info(f"🎵 Moving to {track_ctx.message.channel.name}")
                #     await voice.move_to(track_ctx.channel)

                # debug
                logger.info(f"🎵 Now playing: {track['track'].get_title()}")
                # log only first 20 characters
                logger.info(f"🎵 Audio URL: {track['track'].get_audio_url()[:30]}...")

                # play the track
                await track["context"].reply(
                    f"🎵 Now playing: \n`{track['track'].get_title()}`\nRequested By: `{track_ctx.author.name}`"
                )

                # play the track
                voice.play(
                    PCMVolumeTransformer(
                        FFmpegPCMAudio(track["track"].get_audio_url()), volume=0.5
                    ),
                    # FFmpegOpusAudio(track.get_audio_url(), **FFMPEG_OPTIONS),
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(), self.bot.loop
                    ),
                )
            except Exception as e:
                logger.error(traceback.format_exc())
                await track_ctx.reply(
                    f"🚫 Unable to play `{track['track'].get_title()}`"
                )
                await self.play_next()

        else:
            logger.info("🚫 Queue is empty. Stopping playback.")
            self.is_playing = False
            await self.stop()

    async def stop(self):
        """
        Stop playback and disconnect from voice channel
        """
        await [await vc.disconnect() for vc in self.bot.voice_clients]

    async def pause(self):
        """
        Pause playback
        """
        self.bot.voice_client.pause()

    async def resume(self):
        """
        Resume playback
        """
        self.bot.voice_client.resume()


# Music Cog
class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_player = MusicPlayer(bot)

    def __is_sudo_user(self, user_id: int) -> bool:
        return user_id in [int(user) for user in self.bot.config["SUDOERS"]]

    def __is_bot_allowed_in_current_server(self, server_id: int) -> bool:
        return server_id in [int(guild) for guild in self.bot.config["ALLOWED_SERVERS"]]

    def __simple_check(self, ctx: commands.Context) -> bool:
        return self.__is_sudo_user(
            ctx.author.id
        ) or self.__is_bot_allowed_in_current_server(ctx.guild.id)

    @commands.command(name="play", primary=True)
    async def play(self, ctx: commands.Context):
        """Plays if paused"""
        if self.music_player.is_playing:
            await ctx.reply("Already playing! 🎵")
        # check if the bot is allowed in the server
        await self.resume(ctx)

    @commands.command(name="play", primary=True, aliases=["p"])
    async def play(self, ctx: commands.Context, *, url):
        """Plays a song from a given url"""
        # log
        logger.info(f"{ctx.author.name} requested to play {url}")
        logger.info(
            f"{ctx.author.name} [{ctx.author.id}] at {ctx.guild.name} [{ctx.guild.id}] in vc {ctx.author.voice.channel.name} [{ctx.author.voice.channel.id}]"
        )

        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # queue the track
        await self.queue(ctx, url)

    @commands.command(name="clear_queue", aliases=["cq", "clear"])
    async def clear_queue(self, ctx):

        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # clear the queue
        if len(self.music_player.queues):
            await self.music_player.clear_queue()
            await ctx.reply("Queue cleared! 🗑️")
        else:
            await ctx.reply("There is nothing in queue to clear 🚫")

    @commands.command(name="pause")
    async def pause(self, ctx):
        # check if the bot is allowed in the server
        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # pause playback
        if self.music_player.is_playing:
            try:

                await self.music_player.pause()
                await ctx.reply("Paused playback! ⏸️")
            except Exception as e:
                logger.error(traceback.format_exc())

    @commands.command(name="resume", aliases=["r", "unpause", "res", "unp"])
    async def resume(self, ctx):
        # check if the bot is allowed in the server
        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # resume playback
        if not self.music_player.is_playing:
            try:
                await self.music_player.resume()
                await ctx.reply("Resumed playback! ▶️")
            except Exception as e:
                logger.error(traceback.format_exc())

    @commands.command(name="stop", aliases=["st", "leave", "stop playing"])
    async def stop(self, ctx):
        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # stop playback
        try:
            await self.music_player.stop()
        except Exception as e:
            logger.error(traceback.format_exc())

    @commands.command(name="queue", aliases=["q", "add", "playnext", "pn", "next"])
    async def queue(self, ctx, url):
        logger.info(f"Queueing {url}")
        # check if the bot is allowed in the server
        if not self.__simple_check(ctx):
            logger.info(f"🚫 Not Allowed. 🚫")
            return await ctx.author.send("Not Allowed. 🚫")

        # fetch
        info = await extract_media_url(url)
        # check if we have any info
        if len(info) == 1:
            logger.info(f"💿 Queueing `{info[0].get_title()}`")
            # get the first track
            track = info[0]
            # queue the track
            await self.music_player.queue_track(ctx, track)
            # reply only if queue has more than 1 track
            if len(self.music_player.queues) > 1:
                return await ctx.reply(f"🎵 Queued `{track.get_title()}`")

        elif len(info) > 1:
            logger.info(f"💿 Queueing {len(info)} tracks")
            # add tracks
            for track in info:
                await self.music_player.queue_track(ctx, track)
            # reply only if queue has more than 1 track
            if len(self.music_player.queues) > 1:
                return await ctx.reply(f"🎵 Queued {len(info)} tracks")

        else:
            # no info
            await ctx.reply("Unable to fetch media information. 🚫")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
