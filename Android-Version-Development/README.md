# Arabic Audio Transcriber for Android

[简体中文](README.zh-CN.md)

This directory is an independent native Android application. It does not import or modify the Python desktop application at build time.

## Current features

- Select audio or video through Android's system document picker or the Share menu
- Decode media with Android platform codecs; FFmpeg is not required
- Run Arabic transcription locally with `whisper.cpp`
- Download `small`, `medium` (recommended), or `large-v3` with resumable percentage progress
- Recheck model availability at startup and before each transcription
- Store text results in an app-internal history without retaining source audio
- Copy, share, or export any result as UTF-8 TXT
- Keep local transcription separate from optional AI correction, translation, and Arabic diacritization
- Protect the optional API key with Android Keystore
- Continue long model downloads and transcription tasks as foreground WorkManager jobs

## Media and privacy policy

The selected user-owned media URI is read-only. The app never renames, edits, moves, or deletes the source file.

When a provider requires a local file, the worker creates a private copy under the app cache. That directory is deleted from a `finally` block after success, failure, or cancellation. History contains text, status, and metadata only. AI processing sends transcript text to the configured HTTPS endpoint; it never sends audio or video.

## Model storage

Models are stored in the app-specific external files directory, normally similar to:

```text
/storage/emulated/0/Android/data/io.github.bithash1.arabictranscriber/files/models
```

The exact path is displayed in Settings. Android may remove this directory when the app is uninstalled. `large-v3` requires a high-memory device and may not run reliably on lower-end phones.

## Build

Requirements:

- JDK 17
- Android SDK Platform 37.0
- Android Build Tools 36.0.0
- Android NDK 28.2.13676358
- CMake 3.31.6

The repository includes Gradle Wrapper 9.4.1 and pinned `whisper.cpp` v1.9.1 sources.

```bash
./gradlew testDebugUnitTest
./gradlew lintDebug
./gradlew assembleDebug
```

The installable debug APK is generated at:

```text
app/build/outputs/apk/debug/app-debug.apk
```

The Android package currently contains `arm64-v8a` and `x86_64` native libraries. ARM64 covers modern physical Android devices; x86_64 is included for emulator testing.

## Project structure

```text
app/src/main/java/.../
├── ai/                 DeepSeek-compatible text processing
├── data/               SQLite history, preferences, and Keystore
├── model/              App and Whisper model state
├── transcription/      Android media decoding and JNI bridge
├── ui/                 Jetpack Compose UI
└── worker/             Download, transcription, and AI background work

app/src/main/cpp/       JNI adapter and CMake integration
third_party/whisper.cpp Pinned upstream inference engine
```

## Third-party software

`third_party/whisper.cpp` is distributed under its upstream MIT license. Its original license is preserved at `third_party/whisper.cpp/LICENSE`.
