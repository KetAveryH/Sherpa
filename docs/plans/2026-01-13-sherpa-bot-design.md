# Sherpa - Discord Voice Inventory Assistant

## Overview

Sherpa is a local-first Discord voice bot that helps track in-game inventory for Arc Raiders. It joins your Discord voice channel and listens for the wake word "hey sherpa" to receive commands.

## Core Features (v1)

- Join Discord voice channel
- Wake word "Hey Sherpa" activation
- Add/update inventory items ("I picked up 5 titanium")
- Query inventory ("how much titanium do I have?")
- Voice responses for short answers, text channel for long ones
- "Quick answer" modifier forces concise voice response
- Learn game knowledge (locations, tips) as you share it

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MacBook M4 (Local)                   │
├─────────────────────────────────────────────────────────┤
│  Discord Bot (Python)                                   │
│    ├── Voice connection to Discord                      │
│    ├── Audio capture → Local Whisper (STT)              │
│    ├── Wake word detection ("Hey Sherpa")               │
│    ├── Response → Local TTS → Discord voice             │
│    └── Long responses → Discord text channel            │
│                                                         │
│  Inventory Store (JSON file)                            │
│    └── inventory.json                                   │
│                                                         │
│  Game Knowledge Store (JSON file)                       │
│    └── knowledge.json                                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (API calls only)
                   ┌──────────────┐
                   │  Claude API  │
                   └──────────────┘
```

## Voice Pipeline

1. **Discord → Bot**: `discord.py` with voice support. Bot joins voice channel and receives audio stream.
2. **Continuous transcription**: Audio feeds into `mlx-whisper`. Processes when voice activity detected.
3. **Wake word detection**: String match on transcribed text for "hey sherpa".
4. **Silence detection**: ~1.5 seconds of silence signals end of command.
5. **Command processing**: Command sent to Claude API with inventory context.
6. **Response generation**:
   - Short (or "quick answer" requested): Piper TTS → Discord voice
   - Long: Post to Discord text channel

**Expected latency**: ~2-3 seconds (Whisper ~0.5s, Claude ~1-2s, TTS ~0.5s)

## Data Storage

### inventory.json
```json
{
  "items": {
    "titanium": 47,
    "copper wire": 12,
    "medkit": 3
  },
  "last_updated": "2026-01-13T14:30:00"
}
```

### knowledge.json
```json
{
  "locations": {
    "titanium": "industrial areas",
    "copper wire": "Salvage from broken robots"
  },
  "tips": [
    "Medkits can be crafted from herbs and bandages"
  ],
  "missions": {
    "current": "Collect 50 titanium for base upgrade"
  }
}
```

## Command Processing (Claude)

Each request to Claude includes:
- Spoken command
- Current inventory state
- Relevant knowledge context
- System prompt defining Sherpa's behavior

Claude returns:
```json
{
  "action": "UPDATE|QUERY|LEARN|MISSION",
  "changes": {},
  "response": "Natural language response",
  "response_type": "short|long"
}
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Wake word misheard | No action |
| Couldn't understand command | Voice: "Sorry, I didn't catch that" |
| Claude API timeout/error | Voice: "I'm having trouble thinking, try again" |
| Discord voice disconnected | Auto-reconnect, notify in text channel |

Logging to `logs/sherpa.log` with timestamps, transcriptions, and responses.

## Project Structure

```
discord-inventory-manager-bot/
├── src/
│   ├── bot.py              # Main Discord bot, voice handling
│   ├── transcriber.py      # Whisper integration, wake word detection
│   ├── sherpa.py           # Claude integration, command processing
│   ├── tts.py              # Piper TTS wrapper
│   └── storage.py          # JSON read/write for inventory & knowledge
├── data/
│   ├── inventory.json
│   └── knowledge.json
├── logs/
│   └── sherpa.log
├── .env                    # API keys (not committed)
├── .gitignore
├── requirements.txt
└── project_summary.txt
```

## Dependencies

### Python packages
- `discord.py[voice]` - Discord bot with voice support
- `mlx-whisper` - Apple Silicon optimized STT
- `anthropic` - Claude API client
- `piper-tts` - Local TTS
- `numpy` - Audio processing
- `python-dotenv` - Environment variable loading

### System (Homebrew)
- `ffmpeg` - Audio format conversion
- `opus` - Discord voice codec

## Setup Required (User)

1. Discord Developer Portal:
   - Create application "Sherpa"
   - Create bot, copy token
   - Enable Message Content Intent
   - Generate invite URL with: bot, applications.commands
   - Permissions: Connect, Speak, Send Messages, Read Message History

2. API Keys:
   - Claude API key from console.anthropic.com
   - Discord bot token

## Future Considerations (v2)

- Mission planning ("I need to craft X, what am I missing?")
- Inventory history/undo
- Multiple game profiles
- Area type schema for Arc Raiders locations
