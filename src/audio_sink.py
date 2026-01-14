import logging
from typing import Callable

from discord.sinks import Sink

logger = logging.getLogger("sherpa.audio")


class SherpaAudioSink(Sink):
    """Simple audio sink that forwards audio directly to a callback."""

    def __init__(self, on_audio: Callable[[bytes], None]):
        super().__init__(filters=None)
        self.on_audio = on_audio
        self._packet_count = 0

    def write(self, data: bytes, user: int):
        """Called by py-cord when audio data is received.

        Args:
            data: Raw PCM audio bytes (48kHz, 16-bit, stereo)
            user: User ID (snowflake)
        """
        self._packet_count += 1
        if self._packet_count % 100 == 1:
            logger.debug(f"Audio packet #{self._packet_count} from user {user}")

        # Forward audio directly - no buffering
        self.on_audio(data)

    def cleanup(self):
        """Called when recording stops."""
        logger.info(f"Audio sink cleanup, processed {self._packet_count} packets")
        super().cleanup()
