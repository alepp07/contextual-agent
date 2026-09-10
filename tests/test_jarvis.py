import numpy as np

from jarvis import is_end_command, jarvis_score, rms_level, should_stop_recording, wav_bytes


def test_rms_level_for_silence_and_signal():
    assert rms_level(np.zeros(100, dtype=np.int16)) == 0.0
    assert rms_level(np.full(100, 16384, dtype=np.int16)) == 0.5


def test_recording_stops_only_after_speech_then_silence():
    assert should_stop_recording(
        [0.0, 0.0, 0.03, 0.02, 0.0, 0.0],
        speech_threshold=0.01,
        silent_frames_to_stop=2,
    )
    assert not should_stop_recording(
        [0.0, 0.0, 0.0],
        speech_threshold=0.01,
        silent_frames_to_stop=2,
    )


def test_conversation_end_commands():
    assert is_end_command("Goodbye, Jarvis!")
    assert is_end_command("stop listening")
    assert not is_end_command("Tell me about goodbye messages")


def test_jarvis_score_ignores_other_models():
    assert jarvis_score({"alexa": 0.9, "hey_jarvis": 0.7}) == 0.7
    assert jarvis_score({"alexa": 0.9}) == 0.0


def test_wav_bytes_creates_wav_container():
    audio = wav_bytes([np.zeros(1280, dtype=np.int16).tobytes()])
    assert audio.startswith(b"RIFF")
    assert b"WAVE" in audio[:16]
