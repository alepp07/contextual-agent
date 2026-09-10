"""Hands-free local voice companion for the contextual-agent API.

Wake-word detection runs locally. Only the command recorded after activation
is sent to the configured contextual-agent server for transcription and an
answer.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import wave
from collections.abc import Iterable
from pathlib import Path

import numpy as np


SAMPLE_RATE = 16_000
FRAME_SAMPLES = 1_280  # 80 ms: the frame size recommended by openWakeWord


def rms_level(audio: np.ndarray) -> float:
    """Return normalized RMS volume for signed 16-bit mono audio."""
    if audio.size == 0:
        return 0.0
    samples = audio.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(samples * samples)))


def should_stop_recording(
    levels: Iterable[float],
    *,
    speech_threshold: float,
    silent_frames_to_stop: int,
) -> bool:
    """Pure helper used by tests and by the command recorder."""
    speech_started = False
    silent_frames = 0
    for level in levels:
        if level >= speech_threshold:
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1
            if silent_frames >= silent_frames_to_stop:
                return True
    return False


def wav_bytes(frames: list[bytes]) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(b"".join(frames))
    return output.getvalue()


def speak(engine, text: str) -> None:
    engine.say(text)
    engine.runAndWait()


def record_command(stream, *, silence_threshold: float, max_seconds: float) -> list[bytes]:
    """Record until 1.2 seconds of silence after speech, or until timeout."""
    frames: list[bytes] = []
    speech_started = False
    silent_frames = 0
    silent_frames_to_stop = max(1, round(1.2 * SAMPLE_RATE / FRAME_SAMPLES))
    max_frames = max(1, round(max_seconds * SAMPLE_RATE / FRAME_SAMPLES))

    for _ in range(max_frames):
        data, overflowed = stream.read(FRAME_SAMPLES)
        if overflowed:
            print("[audio overflow]", file=sys.stderr)
        raw = bytes(data)
        frames.append(raw)
        level = rms_level(np.frombuffer(raw, dtype=np.int16))

        if level >= silence_threshold:
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1
            if silent_frames >= silent_frames_to_stop:
                break

    return frames if speech_started else []


def request_answer(server_url: str, frames: list[bytes], timeout: float) -> tuple[str, str]:
    import requests

    base_url = server_url.rstrip("/")
    transcription = requests.post(
        f"{base_url}/transcribe",
        files={"file": ("question.wav", wav_bytes(frames), "audio/wav")},
        timeout=timeout,
    )
    transcription.raise_for_status()
    question = transcription.json()["text"].strip()
    if not question:
        raise RuntimeError("The transcription was empty")

    response = requests.post(
        f"{base_url}/ask",
        json={"question": question},
        timeout=timeout,
    )
    response.raise_for_status()
    return question, response.json()["answer"]


def jarvis_score(prediction: dict[str, float]) -> float:
    scores = [score for name, score in prediction.items() if "jarvis" in name.lower()]
    return max(scores, default=0.0)


def run(args: argparse.Namespace) -> None:
    import openwakeword
    import pyttsx3
    import sounddevice as sd
    from openwakeword.model import Model

    print("Preparing the free local wake-word model (first run may download it)...")
    models_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
    jarvis_model = models_dir / "hey_jarvis_v0.1.onnx"
    if not jarvis_model.exists():
        openwakeword.utils.download_models(model_names=["hey_jarvis"])
    if not jarvis_model.exists():
        raise RuntimeError(
            f"Jarvis model download did not complete. Download hey_jarvis_v0.1.onnx "
            f"and save it in {models_dir}"
        )
    model = Model(
        wakeword_models=[str(jarvis_model)],
        inference_framework="onnx",
        vad_threshold=0.5,
    )
    engine = pyttsx3.init()

    print(f'Listening locally for "Hey Jarvis". Server: {args.server}')
    print("Press Ctrl+C to stop. No audio is uploaded before activation.")

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SAMPLES,
        dtype="int16",
        channels=1,
    ) as stream:
        while True:
            data, overflowed = stream.read(FRAME_SAMPLES)
            if overflowed:
                print("[audio overflow]", file=sys.stderr)
            prediction = model.predict(np.frombuffer(bytes(data), dtype=np.int16))
            if jarvis_score(prediction) < args.wake_threshold:
                continue

            print("Wake word detected")
            speak(engine, args.acknowledgement)
            model.reset()

            # Drop audio accumulated while the acknowledgement was playing.
            while stream.read_available >= FRAME_SAMPLES:
                stream.read(FRAME_SAMPLES)

            print("Listening for your question...")
            frames = record_command(
                stream,
                silence_threshold=args.silence_threshold,
                max_seconds=args.max_seconds,
            )
            if not frames:
                print("No question detected; returning to wake-word mode.")
                speak(engine, "I didn't hear a question.")
                continue

            try:
                question, answer = request_answer(args.server, frames, args.timeout)
                print(f"You: {question}\nJarvis: {answer}")
                speak(engine, answer)
            except Exception as exc:
                print(f"Request failed: {exc}", file=sys.stderr)
                speak(engine, "Sorry, I could not reach the assistant.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hands-free Hey Jarvis companion")
    parser.add_argument(
        "--server",
        default=os.getenv("JARVIS_SERVER_URL", "http://127.0.0.1:8000"),
        help="contextual-agent base URL",
    )
    parser.add_argument("--wake-threshold", type=float, default=0.5)
    parser.add_argument("--silence-threshold", type=float, default=0.015)
    parser.add_argument("--max-seconds", type=float, default=15.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--acknowledgement", default="Yes?")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except KeyboardInterrupt:
        print("\nJarvis stopped.")
