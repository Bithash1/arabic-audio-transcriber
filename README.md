# Arabic Audio Transcriber

一个**面向电脑小白**的阿拉伯语音频/视频转写工具，基于 `faster-whisper`，支持导出：

- `.txt` 纯文本
- `.srt` 字幕文件

它适合这些场景：

- 阿拉伯语新闻、播客、采访、课程音频转写
- 视频字幕初稿生成
- 本地离线转写（音频不会上传到外部服务器）

---

## 这个项目解决了什么问题

原始脚本存在几个典型痛点：

1. **要手改代码里的文件路径**
2. **对 Python 环境依赖明显**
3. **对 CUDA / CPU 切换不友好**
4. **报错信息不够面向普通用户**
5. **不适合直接拿去开源**

这个版本做了这些改进：

- 支持**命令行参数**，不必每次改源码
- 不传路径时，会**自动弹出文件选择框**
- 默认**自动尝试 CUDA，失败后回退到 CPU**
- 自动在源文件旁创建输出文件夹
- 输出清晰的中文提示，方便非程序员使用
- 附带 `requirements.txt`、`.gitignore`、`LICENSE`
- 适合直接上传到 GitHub 作为开源项目骨架

---

## 重要说明

### 1) 不一定需要单独安装 FFmpeg

`faster-whisper` 官方 README 说明：它和原版 `openai-whisper` 不同，音频解码使用的是 **PyAV**，而 **PyAV 自带 FFmpeg 库**，因此通常**不需要额外在系统里安装 FFmpeg**。citeturn166339search0

这点很关键。很多人会被 “先装 FFmpeg 再配 PATH” 这套仪式感流程劝退，像被旧时代脚本拿木棒敲脑袋。

### 2) 但 Python 版本要谨慎

`faster-whisper` 官方说明写的是 Python 3.9+。citeturn166339search0

不过在社区 issue 里，Python 3.12 上安装 `av` 出现编译失败的情况并不少见，因此**更稳妥的建议是优先使用 Python 3.10 或 3.11**。citeturn166339search4turn166339search10

### 3) 想照顾电脑小白，最好发布可执行文件

PyInstaller 官方文档说明，它可以把 Python 程序和依赖打包成一个可分发的包，用户**无需自行安装 Python** 即可运行。citeturn932345search1turn932345search5

这对“面向电脑小白”非常重要。否则你的 README 再写得像神谕，用户看到环境配置还是会原地蒸发。

---

## 项目结构

```text
arabic-audio-transcriber/
├─ app.py
├─ requirements.txt
├─ run_transcriber.bat
├─ .gitignore
├─ LICENSE
└─ README.md
```

---

## 运行方式（开发者 / 懂一点命令行的用户）

### 1. 安装 Python

推荐使用：

- Python 3.10
- Python 3.11

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

#### 方法 A：直接运行，弹出文件选择框

```bash
python app.py
```

#### 方法 B：指定文件路径

```bash
python app.py "D:\audio\news.mp4"
```

#### 方法 C：指定模型

```bash
python app.py "D:\audio\news.mp4" --model large-v3
```

#### 方法 D：强制 CPU

```bash
python app.py "D:\audio\news.mp4" --device cpu --compute-type int8
```

---

## 输出结果

程序会在原文件旁边自动创建一个文件夹，例如：

```text
news_transcript/
├─ news.txt
└─ news.srt
```

---

## 参数说明

| 参数 | 作用 | 默认值 |
|---|---|---|
| `input` | 输入音频/视频路径 | 不填则弹窗选择 |
| `--output-dir` | 输出目录 | 自动生成 |
| `--model` | Whisper 模型名 | `medium` |
| `--language` | 语言代码 | `ar` |
| `--device` | `auto/cpu/cuda` | `auto` |
| `--compute-type` | 计算类型 | `int8` |
| `--beam-size` | 解码宽度 | `5` |
| `--no-vad` | 关闭静音过滤 | 默认关闭此项 |

---

## 模型选择建议

| 模型 | 速度 | 准确率 | 适合人群 |
|---|---|---|---|
| `small` | 快 | 中 | 普通 CPU 用户 |
| `medium` | 中 | 较高 | 大多数用户，默认推荐 |
| `large-v3` | 慢 | 高 | 对精度要求高、机器性能较强 |

### 结论

- **默认推荐 `medium`**：比较均衡。
- **老电脑优先 `small`**。
- **不是所有人都该上 `large-v3`**，那玩意儿在 CPU 上有时像让自行车拖坦克。

---

## 给电脑小白的最佳发布方案

如果你的目标是：

> 别让用户装 Python，别让用户碰命令行，双击就能跑

那么建议你做两层发布：

### 方案 A：源码版（给开发者）

上传当前仓库即可。

### 方案 B：Windows 可执行版（给小白）

使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller --onefile app.py
```

PyInstaller 官方文档确认，它会把 Python 解释器和依赖一起打包。citeturn932345search1turn932345search5

打包完成后，把 `dist/app.exe` 放到 GitHub Releases 里发布即可。

> 注：PyInstaller 也支持 `spec` 文件，但官方也说明，多数场景并不需要手改 spec。citeturn932345search13

---

## GitHub 开源建议

建议仓库名：

- `arabic-audio-transcriber`
- `arabic-whisper-transcriber`
- `whisper-arabic-local-transcriber`

建议你在 GitHub 仓库里至少放这些内容：

- 项目简介
- 安装方式
- 使用示例
- 模型选择建议
- 常见报错 FAQ
- 截图 / GIF 演示
- License

---

## 推荐的 GitHub Release 策略

你可以做：

- `Source code`：源码版
- `Windows .exe`：给普通用户
- 后续再补：
  - 批量转写
  - GUI 图形界面
  - 自动生成按时间戳切分的段落
  - 阿拉伯语 + 英语混合识别

---

## 常见问题

### Q1：为什么我没装 FFmpeg 也能跑？

因为 `faster-whisper` 使用 PyAV 解码媒体文件，而 PyAV 自带 FFmpeg 库。citeturn166339search0

### Q2：为什么我电脑上 CUDA 跑不起来？

因为 GPU 模式除了程序本身，还需要 NVIDIA 的 CUDA/cuDNN 运行库。`faster-whisper` 官方 README 里明确写了 GPU 运行需要对应 NVIDIA 库。citeturn166339search0

### Q3：为什么我建议你默认用 CPU 友好的参数？

因为你想做的是**能让别人真正用起来的工具**，不是在 README 里摆一尊“需要玄学环境配置”的赛博佛像。

---

## 后续改进方向

1. 增加真正的图形界面（Tkinter / PySide6）
2. 支持批量处理整个文件夹
3. 支持输出 `.json`
4. 支持“仅导出字幕，不导出 TXT”
5. 支持拖拽文件到 exe 上直接处理
6. 支持多语言自动识别模式

---

## License

MIT
