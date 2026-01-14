import os
import json
import asyncio
import logging
from typing import Callable, Awaitable

import websockets

logger = logging.getLogger("sherpa.transcriber")


class StreamingTranscriber:
    """Real-time speech-to-text using Deepgram's streaming WebSocket API."""

    def __init__(
        self,
        on_transcript: Callable[[str], Awaitable[None]],
        api_key: str | None = None,
    ):
        self.on_transcript = on_transcript

        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not set")

        self.ws = None
        self._loop = None
        self._receiver_task = None
        self._keepalive_task = None
        self._running = False

    async def start(self):
        """Start the streaming WebSocket connection."""
        self._loop = asyncio.get_running_loop()
        self._running = True

        # Deepgram streaming endpoint with options
        url = (
            "wss://api.deepgram.com/v1/listen?"
            "model=nova-2&"
            "language=en&"
            "smart_format=true&"
            "encoding=linear16&"
            "sample_rate=48000&"
            "channels=2&"
            "interim_results=true&"
            "utterance_end_ms=2500"
        )

        headers = {"Authorization": f"Token {self.api_key}"}

        self.ws = await websockets.connect(url, additional_headers=headers)
        logger.info("Deepgram WebSocket connected")

        # Start receiver and keepalive tasks
        self._receiver_task = asyncio.create_task(self._receive_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def _receive_loop(self):
        """Receive transcription results from Deepgram."""
        while self._running:
            try:
                if not self.ws:
                    await asyncio.sleep(0.5)
                    continue

                # Use wait_for to prevent blocking indefinitely
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue  # Just keep waiting, don't block

                data = json.loads(message)

                # Check for transcript
                if data.get("type") == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                        is_final = data.get("is_final", False)

                        if transcript and is_final:
                            logger.info(f"Transcribed: '{transcript}'")
                            # Don't await here - fire and forget to avoid blocking
                            asyncio.create_task(self.on_transcript(transcript))

            except websockets.exceptions.ConnectionClosed:
                if self._running:
                    logger.info("Deepgram connection closed, reconnecting...")
                    await self._reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Deepgram receiver error: {e}")
                if self._running:
                    await asyncio.sleep(1)

    async def _reconnect(self):
        """Reconnect to Deepgram."""
        if not self._running:
            return
        try:
            url = (
                "wss://api.deepgram.com/v1/listen?"
                "model=nova-2&"
                "language=en&"
                "smart_format=true&"
                "encoding=linear16&"
                "sample_rate=48000&"
                "channels=2&"
                "interim_results=true&"
                "utterance_end_ms=2500"
            )
            headers = {"Authorization": f"Token {self.api_key}"}
            self.ws = await asyncio.wait_for(
                websockets.connect(url, additional_headers=headers),
                timeout=10.0
            )
            logger.info("Deepgram reconnected")
        except asyncio.TimeoutError:
            logger.error("Deepgram reconnect timed out")
        except Exception as e:
            logger.error(f"Deepgram reconnect failed: {e}")

    async def _keepalive_loop(self):
        """Send keep-alive messages to prevent timeout."""
        try:
            while True:
                await asyncio.sleep(8)  # Send every 8 seconds
                if self.ws:
                    try:
                        # Deepgram keep-alive is just an empty JSON object
                        await self.ws.send(json.dumps({"type": "KeepAlive"}))
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    def send_audio(self, audio_bytes: bytes):
        """Send audio data to Deepgram for transcription."""
        if self.ws and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._send_audio(audio_bytes),
                self._loop
            )

    async def _send_audio(self, audio_bytes: bytes):
        """Async send audio to WebSocket."""
        if self.ws:
            try:
                await self.ws.send(audio_bytes)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")

    async def stop(self):
        """Stop the streaming connection."""
        self._running = False

        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            await self.ws.close()
            self.ws = None

        logger.info("Deepgram streaming stopped")
