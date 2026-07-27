# Arabic Audio Transcriber

[Simplified Chinese](README.zh-CN.md)

Arabic Audio Transcriber is a beginner-friendly desktop application for transcribing Arabic audio and video with `faster-whisper`. It exports plain text and SRT subtitles, works offline after the selected Whisper model has been downloaded, and provides optional AI-assisted correction, translation, and Arabic diacritization.

## Features

- Local Arabic speech-to-text processing; audio and video files are never uploaded
- TXT and SRT exports
- Separate local transcription and optional AI processing workflows
- Whisper model availability checks at startup and before every transcription
- Custom model storage directory
- Resumable model downloads with percentage progress
- `small`, `medium` (recommended), and `large-v3` model choices
- Optional AI correction for clear ASR errors and incorrectly joined or separated words
- Optional translation into Simplified Chinese or English
- Optional Arabic diacritization (Tashkeel)
- Resumable AI processing with token usage reporting
- Original transcription files are never overwritten by AI output
- Automatic CUDA-to-CPU fallback

## Download

Download the appropriate archive from [GitHub Releases](https://github.com/Bithash1/arabic-audio-transcriber/releases):

- Windows x64: `ArabicAudioTranscriber-Windows-x64.zip`
- macOS Apple Silicon: `ArabicAudioTranscriber-macOS-Apple-Silicon.zip`

Extract the archive before running the application.

On Windows, launch `ArabicAudioTranscriber.exe`. On macOS, launch `ArabicAudioTranscriber.app`. Because the macOS build is not notarized, you may need to right-click the application and select **Open** the first time.

## Local Transcription

1. Select an Arabic audio or video file.
2. Optionally select an output directory.
3. Select a Whisper model.
4. Click **Start Local Transcription**.

The application checks each model and displays one of these states:

- Downloaded
- Not downloaded
- Repair required
- Storage location unavailable

A model requires an internet connection the first time it is downloaded. Once downloaded, that model can be used offline. Interrupted downloads can resume later.

The model selection intentionally excludes `tiny` and `base`. `medium` is recommended for a better balance between accuracy and runtime.

## Model Storage

The application displays the effective model cache path and lets you choose another directory. The default Hugging Face cache is usually:

- Windows: `C:\Users\<username>\.cache\huggingface\hub`
- macOS and Linux: `~/.cache/huggingface/hub`

Environment variables such as `HF_HOME` or `HUGGINGFACE_HUB_CACHE` can change the effective path; use the path displayed by the application as the authoritative value.

Changing the model directory affects new downloads. Existing models in both the custom and default cache are detected. If a custom location becomes unavailable, for example because an external drive is disconnected, the application asks you to reconnect it or choose another directory instead of silently downloading to the system drive.

## Optional AI Processing

Local transcription does not require an API key. After transcription, you may independently select:

- Text correction
- Translation
- Arabic diacritization
- Any combination of the above

When correction is selected with another operation, the order is:

```text
Original transcript → Correction → Translation and/or diacritization
```

AI processing sends only transcript text to the configured API service. Audio and video files are not uploaded. You must provide your own DeepSeek-compatible API key. The key can optionally be stored in the operating system keychain.

Processing is saved after every batch. Valid completed results are reused when a task is resumed, avoiding unnecessary repeated requests and token usage.

## Output Files

For an input file named `example.mp3`, output may include:

```text
example_transcript/
├── example.txt
├── example.srt
├── example.transcriber.json
├── example_ar_corrected.txt
├── example_ar_corrected.srt
├── example_ar_diacritized.txt
├── example_ar_diacritized.srt
├── example_translated.txt
├── example_translated.srt
└── example_bilingual.srt
```

`example.txt` and `example.srt` are the original local transcription and are never overwritten. AI result files are generated only for the selected operations. The `.transcriber.json` file stores resumable AI-processing state.

## Run from Source

Recommended environment:

- Python 3.10 or newer
- Windows, macOS, or Linux

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the GUI:

```bash
python gui.py
```

Windows users can also run `run_gui.bat`.

### Terminal Usage

Start with a file picker:

```bash
python app.py
```

Or pass a media file directly:

```bash
python app.py path/to/audio.mp3
```

Useful options:

```bash
python app.py path/to/audio.mp3 --model medium --device cpu
```

Run `python app.py --help` for all options.

## Development

Run tests:

```bash
python -m unittest discover -s tests -v
```

Build the application locally:

```bash
python -m pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean ArabicAudioTranscriber.spec
```

PyInstaller builds are platform-specific. Windows packages must be created on Windows, while the Apple Silicon package is created on an Apple Silicon macOS runner.

## Release Workflow

The GitHub Actions workflow builds Windows x64 and macOS Apple Silicon archives. Pushing a version tag creates or updates the matching GitHub Release and uploads both packages:

```bash
git tag v1.1.0
git push origin v1.1.0
```

The workflow can also be started manually to produce downloadable build artifacts without creating a release.

## Roadmap

- [x] Desktop GUI
- [x] Windows and macOS release packages
- [x] Local model detection and custom storage
- [x] Optional AI correction, translation, and diacritization
- [ ] Support additional AI API providers
- [ ] Batch transcription

## License

MIT
