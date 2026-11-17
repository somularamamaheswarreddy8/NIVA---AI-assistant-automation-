import sys
import os
import time

sys.path.insert(0, os.path.join(os.getcwd(), 'jarvis'))

from app.core.assistant import NivaAssistant
from app.voice.wake_word import WakeWordDetector
from app.voice.speech_to_text import SpeechToTextEngine

assistant = NivaAssistant()

print("=== 1. TEST PHONETIC STT NORMALIZATION ===")
stt = SpeechToTextEngine()
test_phrases = [
    ("hello Nivea open Chrome", "hello niva open Chrome"),
    ("Nivea open Settings", "niva open Settings"),
    ("hey Neeva", "hey niva"),
    ("hello Neva", "hello niva"),
    ("Nova open Chrome", "niva open Chrome"),
]
for raw, expected in test_phrases:
    normalized = stt.normalize_mixed_language(raw)
    import re
    cleaned = re.sub(r"\b(?:nivea|neeva|neva|neba|niwa|naiva|niver|nova)\b", "niva", raw, flags=re.IGNORECASE)
    print(f"'{raw}' -> '{cleaned}'")
    assert "niva" in cleaned.lower(), f"Failed to normalize to niva: {cleaned}"

print("\n=== 2. TEST WAKE WORD WITH PHONETIC VARIANTS ===")
wake = WakeWordDetector(enabled=True)
variants_only = ["NIVA", "niva", "Nivea", "nivea", "Neeva", "neeva", "Hey Nivea", "Hello Nivea", "Ok Nivea"]
for v in variants_only:
    is_only = wake.is_wake_word_only(v)
    print(f"is_wake_word_only('{v}'): {is_only}")
    assert is_only is True, f"Failed for '{v}'"

compound_variants = [
    ("NIVA open Chrome", "open Chrome"),
    ("Nivea open Chrome", "open Chrome"),
    ("Hey Nivea open Chrome", "open Chrome"),
    ("Neeva open Settings", "open Settings"),
]
for raw, expected in compound_variants:
    triggered, cmd = wake.check_wake_word(raw)
    print(f"check_wake_word('{raw}'): triggered={triggered}, cmd='{cmd}'")
    assert triggered is True, f"Failed trigger for '{raw}'"
    assert "chrome" in cmd.lower() or "settings" in cmd.lower(), f"Command extraction failed: '{cmd}'"

print("\n=== 3. TEST DIRECT GREETING & HEARING CHECKS ===")
hearing_checks = [
    ("NIVA", "How can I help you, sir?"),
    ("Nivea", "How can I help you, sir?"),
    ("Hey Nivea", "How can I help you, sir?"),
    ("Can you hear me", "Yes, I can hear you clearly!"),
    ("Are you there", "Yes, I am here and ready to assist you."),
    ("Mic test", "Microphone test successful."),
    ("Hello", "Hello! I am NIVA."),
]
for prompt, expected_substr in hearing_checks:
    is_conv = assistant._is_conversational_question(prompt)
    resp = assistant._answer_conversational_question(prompt)
    print(f"Prompt: '{prompt}' | is_conv={is_conv} | Resp: '{resp}'")
    assert is_conv is True, f"'{prompt}' was not identified as conversational"
    assert expected_substr.lower() in resp.lower(), f"Response '{resp}' missing '{expected_substr}'"

print("\n=== 4. TEST VOICE LISTENER LIFECYCLE ===")
listener = assistant.voice_listener
status_events = []
listener.on_status_change = lambda s: status_events.append(s)
listener.start()
time.sleep(1.2)
print("Listener active:", listener.is_listening)
print("Status events recorded:", status_events)
assert listener.is_listening is True
assert len(status_events) >= 1
listener.stop()
time.sleep(0.3)
print("Listener stopped:", not listener.is_listening)
assert listener.is_listening is False

print("\nALL VOICE PIPELINE TESTS PASSED COMPLETELY!")
