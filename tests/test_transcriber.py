import pytest
from src.transcriber import WakeWordDetector


def test_detect_wake_word_present():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("hey sherpa what is my titanium count")
    assert result is not None
    assert result == "what is my titanium count"


def test_detect_wake_word_missing():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("what is my titanium count")
    assert result is None


def test_detect_wake_word_case_insensitive():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("Hey Sherpa add 10 copper")
    assert result == "add 10 copper"


def test_detect_wake_word_with_filler():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("um hey sherpa uh add 5 titanium")
    assert result is not None
    assert "add 5 titanium" in result.lower()
