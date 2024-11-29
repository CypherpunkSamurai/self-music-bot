import discord
import asyncio
import yt_dlp


class MyClient(discord.Client):
    async def on_ready(self):
        print("Logged on as", self.user)

    async def on_message(self, message: discord.Message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.content == "rick":
            voice_channel = message.author.voice.channel
            if self.voice_client is None:
                await voice_channel.connect()

            FFMPEG_OPTIONS = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M",
                "options": "-vn",
            }
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
                "quiet": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "opus",
                        "preferredquality": "320",
                    }
                ],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                secret = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                info = ydl.extract_info(secret, download=False)
                print(info)
                url2 = info["url"]
                print(url2)
                source = discord.FFmpegPCMAudio(url2)
                vc = self.voice_client
                vc.play(source)


from config import config

client = MyClient()
client.run(config["DISCORD_TOKEN"])
