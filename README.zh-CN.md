# 阿拉伯语音频转写工具

[English](README.md)

Arabic Audio Transcriber 是一款面向普通用户的阿拉伯语音频与视频转写桌面工具。程序使用 `faster-whisper` 在本机生成纯文本和 SRT 字幕；所选 Whisper 模型下载完成后即可离线转写，并可按需使用 AI 进行文本矫正、翻译和阿语标音。

## 主要功能

- 阿拉伯语音频与视频在本机转写，不上传媒体文件
- 自动导出 TXT 和 SRT
- 本地转写与 AI 处理完全分离
- 启动程序和开始转写前检查模型是否完整
- 支持自定义模型存放目录
- 模型下载显示百分比，并支持中断后继续
- 提供 `small`、`medium`（推荐）和 `large-v3`
- AI 矫正明显的识别错误以及错误粘连或分开的单词
- 翻译为简体中文或英文
- 添加阿拉伯语标音（Tashkeel）
- AI 任务按批保存，可恢复进度并显示 Token 用量
- AI 结果不会覆盖原始转写
- CUDA 不可用时自动回退到 CPU

## 下载

请从 [GitHub Releases](https://github.com/Bithash1/arabic-audio-transcriber/releases) 下载对应压缩包：

- Windows x64：`ArabicAudioTranscriber-Windows-x64.zip`
- macOS Apple Silicon：`ArabicAudioTranscriber-macOS-Apple-Silicon.zip`

下载后请先解压。Windows 运行 `ArabicAudioTranscriber.exe`，macOS 运行 `ArabicAudioTranscriber.app`。

macOS 版本目前没有经过 Apple 公证。如果系统首次阻止运行，请右键应用并选择“打开”。

## 本地转写

1. 选择阿拉伯语音频或视频。
2. 根据需要选择输出文件夹。
3. 选择 Whisper 模型。
4. 点击“开始本地转写”。

程序会显示模型的实际状态：

- 已下载
- 未下载
- 需要修复
- 存储位置不可用

某个模型第一次下载时需要联网。下载完成后，该模型可以离线使用；下载中断后，下次可以继续。

模型列表不再提供 `tiny` 和 `base`。为了兼顾准确率和运行速度，推荐使用 `medium`。

## 模型存放位置

程序界面会显示当前模型缓存路径，并允许更改目录。Hugging Face 默认缓存位置通常是：

- Windows：`C:\Users\<用户名>\.cache\huggingface\hub`
- macOS 和 Linux：`~/.cache/huggingface/hub`

如果系统设置了 `HF_HOME` 或 `HUGGINGFACE_HUB_CACHE`，实际位置会发生变化，请以程序界面显示的路径为准。

更改目录只影响后续下载。程序会同时检查自定义目录和默认目录中已有的模型。如果自定义目录不可用，例如移动硬盘没有连接，程序会要求连接磁盘或更换目录，不会自动把模型下载到系统盘。

## 可选 AI 处理

本地转写不需要 API Key。完成转写后，可以分别勾选：

- 文本矫正
- 翻译
- 阿语标音
- 以上功能的任意组合

同时选择矫正和其他功能时，处理顺序为：

```text
原始转写 → 文本矫正 → 翻译和/或标音
```

AI 处理只会向所配置的 API 服务发送转写文字，不会上传音频或视频。用户需要提供自己的 DeepSeek 兼容 API Key，也可以选择把 Key 保存在操作系统钥匙串中。

每批处理完成后都会保存进度。任务中断后再次运行时，仍然有效的结果会被直接复用，避免重复请求和额外消耗 Token。

## 输出文件

输入文件为 `example.mp3` 时，可能生成：

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

`example.txt` 和 `example.srt` 是原始本地转写，永远不会被覆盖。其他文件只在选择相应 AI 功能后生成；`.transcriber.json` 用于保存可恢复的 AI 处理进度。

## 从源码运行

推荐环境：

- Python 3.10 或更高版本
- Windows、macOS 或 Linux

安装依赖：

```bash
python -m pip install -r requirements.txt
```

启动 GUI：

```bash
python gui.py
```

Windows 用户也可以运行 `run_gui.bat`。

### 终端用法

打开文件选择窗口：

```bash
python app.py
```

直接指定媒体文件：

```bash
python app.py path/to/audio.mp3
```

指定模型或设备：

```bash
python app.py path/to/audio.mp3 --model medium --device cpu
```

使用 `python app.py --help` 查看全部选项。

## 开发与测试

运行测试：

```bash
python -m unittest discover -s tests -v
```

在当前系统封装：

```bash
python -m pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean ArabicAudioTranscriber.spec
```

PyInstaller 产物与运行平台相关：Windows 安装包需要在 Windows 上构建，Apple Silicon 版本需要在 Apple Silicon macOS 环境构建。

## 发布流程

GitHub Actions 会生成 Windows x64 和 macOS Apple Silicon 压缩包。推送版本标签后，会创建或更新相应 Release，并上传两个平台的文件：

```bash
git tag v1.1.1
git push origin v1.1.1
```

也可以手动运行工作流，只生成可下载的构建产物而不创建 Release。

## 开发计划

- [x] 桌面 GUI
- [x] Windows 与 macOS 发布包
- [x] 本地模型检测和自定义存储目录
- [x] AI 矫正、翻译和阿语标音
- [ ] 接入更多 AI 平台的 API
- [ ] 批量转写

## 许可证

MIT
