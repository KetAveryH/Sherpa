import os
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.storage import InventoryStorage
from src.sherpa import SherpaBrain
from src.transcriber import StreamingTranscriber
from src.tts import TextToSpeech
from src.audio_sink import SherpaAudioSink


def load_opus():
    """Load opus library for voice support."""
    import discord.opus
    if not discord.opus.is_loaded():
        discord.opus._load_default()
    return discord.opus.is_loaded()

load_dotenv()

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/sherpa.log"),
        logging.StreamHandler(),
    ],
)
# Reduce noise from discord internals
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logger = logging.getLogger("sherpa")


class SherpaBot(commands.Bot):
    def __init__(self, api_key: str):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(command_prefix="!", intents=intents)

        data_dir = Path("data")
        self.storage = InventoryStorage(
            data_dir / "inventory.json",
            data_dir / "knowledge.json",
        )

        self.brain = SherpaBrain(
            storage=self.storage,
            api_key=api_key,
        )

        # Transcriber is created when joining voice (needs callback)
        self.transcriber: StreamingTranscriber | None = None

        try:
            self.tts = TextToSpeech(output_dir=Path("audio_cache"))
            logger.info("TTS initialized with OpenAI")
        except ValueError as e:
            logger.warning(f"TTS not available: {e}")
            self.tts = None

        self.voice_client: discord.VoiceClient | None = None
        self.text_channel: discord.TextChannel | None = None

    async def on_ready(self):
        logger.info(f"Sherpa is ready! Logged in as {self.user}")
        # Register cog if not already registered
        if "VoiceCommands" not in self.cogs:
            self.add_cog(VoiceCommands(self))
            logger.info("VoiceCommands cog registered")

    async def handle_transcript(self, text: str):
        """Called by Deepgram when speech is transcribed."""
        logger.info(f"Transcript received: '{text}'")

        # Show transcription in chat
        if text and self.text_channel:
            await self.text_channel.send(f"**You:** {text}")

        # Process as command
        if text:
            await self.process_command(text)

    async def process_command(self, command: str):
        response = await self.brain.process_command(command)

        logger.info(f"Sherpa response: {response.response}")

        # Always type the response in chat
        if self.text_channel:
            await self.text_channel.send(f"**Sherpa:** {response.response}")

        # Also speak it via TTS
        if self.tts and self.voice_client and self.voice_client.is_connected():
            try:
                loop = asyncio.get_running_loop()
                audio_path = await loop.run_in_executor(None, self.tts.speak, response.response)
                source = discord.FFmpegPCMAudio(str(audio_path))

                if self.voice_client.is_playing():
                    self.voice_client.stop()

                self.voice_client.play(source)
                logger.info("Playing TTS response")
            except Exception as e:
                logger.error(f"TTS playback failed: {e}")


class VoiceCommands(commands.Cog):
    def __init__(self, bot: SherpaBot):
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel!")
            return

        # Load opus before attempting voice connection
        if not load_opus():
            await ctx.send("Failed to load opus library. Voice not available.")
            return

        channel = ctx.author.voice.channel
        await ctx.send(f"Attempting to join {channel.name}...")

        try:
            # Disconnect any existing voice client first
            if ctx.guild.voice_client:
                logger.info("Disconnecting existing voice client...")
                await ctx.guild.voice_client.disconnect(force=True)
                await asyncio.sleep(1)

            # Stop existing transcriber
            if self.bot.transcriber:
                await self.bot.transcriber.stop()

            logger.info(f"Connecting to voice channel: {channel.name} (ID: {channel.id})")

            # Connect with explicit timeout
            try:
                self.bot.voice_client = await asyncio.wait_for(
                    channel.connect(timeout=30.0),
                    timeout=35.0
                )
            except asyncio.TimeoutError:
                await ctx.send("Voice connection timed out.")
                logger.error("Voice connection timed out after 35 seconds")
                return

            if not self.bot.voice_client.is_connected():
                await ctx.send("Failed to establish voice connection.")
                return

            self.bot.text_channel = ctx.channel

            # Start streaming transcriber
            logger.info("Starting Deepgram streaming transcriber...")
            self.bot.transcriber = StreamingTranscriber(
                on_transcript=self.bot.handle_transcript
            )
            await self.bot.transcriber.start()

            # Start recording and stream audio to Deepgram
            logger.info("Starting audio recording...")
            sink = SherpaAudioSink(
                on_audio=self.bot.transcriber.send_audio
            )
            self.bot.voice_client.start_recording(sink, self.on_recording_stopped)

            await ctx.send(f"Sherpa joined {channel.name}! Listening...")
            logger.info(f"Successfully joined voice channel: {channel.name}")

        except Exception as e:
            logger.exception(f"Failed to join voice channel: {e}")
            await ctx.send(f"Error joining voice: {type(e).__name__}: {e}")

    async def on_recording_stopped(self, sink: SherpaAudioSink, *args):
        sink.cleanup()

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context):
        if self.bot.voice_client:
            self.bot.voice_client.stop_recording()

            # Stop transcriber
            if self.bot.transcriber:
                await self.bot.transcriber.stop()
                self.bot.transcriber = None

            await self.bot.voice_client.disconnect()
            self.bot.voice_client = None
            await ctx.send("Sherpa left the voice channel.")
            logger.info("Left voice channel")
        else:
            await ctx.send("I'm not in a voice channel!")

    @commands.command(name="inventory")
    async def inventory(self, ctx: commands.Context):
        items = self.bot.storage.get_all_items()
        if items:
            lines = [f"- {item}: {count}" for item, count in items.items()]
            await ctx.send("**Current Inventory:**\n" + "\n".join(lines))
        else:
            await ctx.send("Inventory is empty!")


async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set in .env")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set in .env")
        return

    bot = SherpaBot(api_key)
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
