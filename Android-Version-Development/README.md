# Android Version Development

This directory contains all source code, tests, documentation, and build configuration for the Android version of Arabic Audio Transcriber.

## Initial scope

- Native Android client developed separately from the Python desktop application.
- Local transcription remains usable without an AI API after the selected model has been downloaded.
- AI correction, translation, and Arabic diacritization remain optional post-processing features.
- Transcription results are stored in the app's internal history and can be copied, shared, or exported as UTF-8 TXT files.
- The first Android release does not expose SRT export, while internal timestamped segments may be retained for future features.

## Source audio and temporary cache policy

User-owned source audio and video must always be treated as read-only input.

- The app must never rename, edit, move, or delete the user's original media.
- If a shared content URI or selected file must be copied for background processing, the copy must be created only inside app-controlled temporary storage.
- App-created temporary media must be deleted after transcription succeeds, fails, or is cancelled.
- The app does not provide permanent audio storage or an audio-cache library.
- App history stores transcription text, processing state, and metadata only; it does not retain the original audio.

## Planned technical direction

- Kotlin and Jetpack Compose for the Android application.
- `whisper.cpp` through the Android NDK/JNI for offline inference.
- Android system file and share intents for receiving media.
- App-managed model downloads with integrity checks and resumable progress.
- Android Keystore-backed protection for optional user-provided API credentials.
