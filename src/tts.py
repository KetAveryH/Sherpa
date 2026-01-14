import hashlib
import logging
import os
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger("sherpa.tts")


class TextToSpeech:
    """Text-to-speech using OpenAI's TTS API."""

    def __init__(
        self,
        output_dir: Path = Path("./audio_cache"),
        api_key: str | None = None,
        voice: str = "nova",  # Options: alloy, echo, fable, onyx, nova, shimmer
        model: str = "tts-1",  # tts-1 (fast) or tts-1-hd (quality)
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice = voice
        self.model = model

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=api_key)

    def speak(self, text: str) -> Path:
        """Generate speech audio file from text.

        Returns path to MP3 file. Uses caching to avoid regenerating.
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        output_path = self.output_dir / f"speech_{text_hash}.mp3"

        if output_path.exists():
            logger.debug(f"Using cached audio: {output_path}")
            return output_path

        logger.info(f"Generating TTS for: {text[:50]}...")

        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
        )

        response.stream_to_file(output_path)
        logger.debug(f"TTS audio saved to: {output_path}")

        return output_path
