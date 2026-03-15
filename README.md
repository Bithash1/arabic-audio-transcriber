# Arabic Audio Transcriber

An offline Arabic speech-to-text tool based on `faster-whisper`, designed for beginners and lightweight local transcription.

It supports Arabic audio/video input and automatically exports transcription results as `.txt` and `.srt` subtitle files.

---

## Features

- Offline transcription (no cloud upload required)
- Arabic audio and video support
- Automatic TXT and SRT output
- Automatic CUDA → CPU fallback
- Simple file selection for non-technical users
- Suitable for local study, news analysis, and subtitle generation

---

## Requirements

Recommended environment:

- Python 3.10 or 3.11
- Windows / macOS / Linux

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

Run directly:

```bash
python app.py
```

Or on Windows, double-click:

```text
run_transcriber.bat
```

If no file path is provided, the program will open a file selection window automatically.

You can also specify a file manually:

```bash
python app.py --input your_audio.mp4
```
---

## Output

The transcription result will be saved in a folder next to the source file.

Example:

```text
example_transcript/
├── example.txt
└── example.srt
```
---

## Device Behavior

By default, the program tries GPU first:
	•	CUDA available → GPU acceleration
	•	CUDA unavailable → CPU fallback

You may also force CPU mode:

```bash
python app.py --device cpu
```
---

## Model Selection

Default model:

```text
medium
```

You may choose another model:

```bash
python app.py --model small
```

Available options:
	•	tiny
	•	base
	•	small
	•	medium
	•	large-v3

CPU users are recommended to use:

```text
small / medium
```

because large-v3 may be slow on low-performance machines.

---

## Typical Use Cases

	•	Arabic news transcription
	•	Lecture transcription
	•	Vocabulary extraction
	•	Subtitle generation
	•	Listening practice materials

---

## Roadmap

- [ ] GUI version
- [ ] Windows executable release
- [ ] Batch transcription
- [ ] Model selection in interface

---

<details>
<summary>Chinese Description / 中文说明</summary>

一个**面向电脑小白**的阿拉伯语音频/视频转写工具，基于 `faster-whisper`，支持导出：

- `.txt` 纯文本
- `.srt` 字幕文件

它适合这些场景：

- 阿拉伯语新闻、播客、采访、课程音频转写
- 视频字幕初稿生成
- 本地离线转写（音频不会上传到外部服务器）

</details>


## License

MIT
