import pytest
from pathlib import Path

from src.tts import TextToSpeech


def test_tts_generates_audio_file(tmp_path):
    tts = TextToSpeech(output_dir=tmp_path)
    audio_path = tts.speak("Hello world")
    assert audio_path.exists()
    assert audio_path.suffix == ".wav"


def test_tts_different_texts_different_files(tmp_path):
    tts = TextToSpeech(output_dir=tmp_path)
    path1 = tts.speak("Hello")
    path2 = tts.speak("Goodbye")
    assert path1 != path2
