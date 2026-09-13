# Hey Jarvis voice-assistant roadmap

This document tracks the planned hands-free voice layer for the contextual-agent service.

## Target experience

1. A local listener detects the phrase "Hey Jarvis".
2. Jarvis acknowledges the user through text-to-speech.
3. The client records a question and stops after detecting silence.
4. The deployed FastAPI service transcribes the recording.
5. The agent selects document retrieval, live web search, or calculation.
6. Jarvis speaks the answer and listens for a follow-up.
7. "Goodbye" or "Stop listening" ends the active conversation.

## Architecture

- **Wake-word detection:** Runs locally so background microphone audio is not uploaded.
- **Speech-to-text:** Uses the service's `/transcribe` endpoint.
- **Agent reasoning:** Uses `/ask` with document search, web search, and calculator tools.
- **Text-to-speech:** Runs on the user's device.
- **Hosting:** The API remains deployed on Render.

## Reliability priorities

- Pre-warm the Render service when the local client starts.
- Allow longer timeouts for free-tier cold starts.
- Reopen the Windows audio stream after spoken output.
- Normalize Unicode punctuation and mathematical symbols before speech.
- Return useful error messages when transcription, search, or generation fails.
- Keep wake-word and desktop dependencies separate from the Render image.

## Privacy

The always-listening wake-word stage should run locally. Only audio captured after activation should be sent to the transcription endpoint.

## Next milestones

- Add structured conversation history to the API.
- Package the local client as a Windows system-tray application.
- Add microphone calibration and selectable input devices.
- Add integration tests for transcription and multi-turn voice sessions.
