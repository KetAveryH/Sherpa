# Sherpa

Discord voice bot for tracking in-game inventory in Arc Raiders.

Sherpa joins your voice channel, listens to your speech in real-time, and responds via voice and text. Manage your inventory hands-free while playing.

## Features

- **Voice-controlled inventory** - "I picked up 15 titanium"
- **Query on demand** - "how much titanium do I have?"
- **Location tracking** - Learn and recall where items are found
- **Tips & knowledge** - Store useful game tips
- **Mission tracking** - Set and check mission goals

## Requirements

- Python 3.12 (recommended)
- FFmpeg (for audio playback)
- Discord bot with voice permissions

## API Keys

You'll need accounts and API keys for:

| Service | Purpose |
|---------|---------|
| [Discord](https://discord.com/developers/applications) | Bot token |
| [Anthropic](https://console.anthropic.com/) | Claude API for NLU |
| [Deepgram](https://console.deepgram.com/) | Speech-to-text |
| [OpenAI](https://platform.openai.com/) | Text-to-speech |

## Setup

1. Clone the repository

2. Create and activate a virtual environment:
   ```bash
   python3.12 -m venv venv312
   source venv312/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   DISCORD_BOT_TOKEN=your_discord_token
   ANTHROPIC_API_KEY=your_anthropic_key
   DEEPGRAM_API_KEY=your_deepgram_key
   OPENAI_API_KEY=your_openai_key
   ```

5. Run the bot:
   ```bash
   python -m src.bot
   ```

## Discord Commands

| Command | Description |
|---------|-------------|
| `!join` | Join your voice channel and start listening |
| `!leave` | Leave the voice channel |
| `!inventory` | Display current inventory in chat |

## How It Works

1. Bot joins your Discord voice channel
2. Deepgram transcribes your speech in real-time via WebSocket
3. Claude interprets commands and updates inventory/knowledge
4. Responses are sent to the text channel and spoken via OpenAI TTS

## Project Structure

```
src/
├── bot.py          # Discord bot and voice handling
├── sherpa.py       # Claude-powered command processing
├── storage.py      # JSON storage for inventory/knowledge
├── transcriber.py  # Deepgram streaming speech-to-text
├── tts.py          # OpenAI text-to-speech
└── audio_sink.py   # Discord audio capture
```

## Data Storage

- `data/inventory.json` - Item counts
- `data/knowledge.json` - Locations, tips, and missions
- `audio_cache/` - Cached TTS audio files
- `logs/sherpa.log` - Application logs
