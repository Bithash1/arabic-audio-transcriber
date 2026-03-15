from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

DEFAULT_MODEL = "medium"
SUPPORTED_EXTS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".mp4", ".mkv", ".mov", ".avi", ".webm"
}


def format_timestamp(seconds: float) -> str:
    ms = int(seconds * 1000)
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def select_file_with_dialog() -> Optional[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="选择阿拉伯语音频/视频文件",
            filetypes=[
                ("媒体文件", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.mkv *.mov *.avi *.webm"),
                ("所有文件", "*.*"),
            ],
        )
        root.destroy()
        return Path(file_path) if file_path else None
    except Exception:
        return None


def ask_for_file() -> Path:
    chosen = select_file_with_dialog()
    if chosen:
        return chosen

    raw = input("请输入音频/视频文件路径（也可把文件拖进终端后回车）：\n> ").strip().strip('"')
    return Path(raw)


def resolve_output_dir(audio_path: Path, output_dir: Optional[str]) -> Path:
    if output_dir:
        out_dir = Path(output_dir).expanduser().resolve()
    else:
        out_dir = audio_path.parent / f"{audio_path.stem}_transcript"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def load_model_with_fallback(model_name: str, device: str, compute_type: str) -> tuple[WhisperModel, str, str]:
    attempts: list[tuple[str, str]] = []

    if device == "auto":
        attempts.extend([
            ("cuda", "float16"),
            ("cpu", compute_type if compute_type != "float16" else "int8"),
        ])
    elif device == "cuda":
        attempts.append(("cuda", compute_type))
    else:
        attempts.append(("cpu", compute_type))

    last_error = None
    for dev, ctype in attempts:
        try:
            print(f"\n[1/4] 正在加载模型：{model_name} | device={dev} | compute_type={ctype}")
            model = WhisperModel(model_name, device=dev, compute_type=ctype)
            return model, dev, ctype
        except Exception as exc:  # pragma: no cover
            last_error = exc
            print(f"加载失败：device={dev}, compute_type={ctype}")

    raise RuntimeError(f"模型加载失败：{last_error}") from last_error


def validate_audio_path(audio_path: Path) -> None:
    if not audio_path.exists():
        raise FileNotFoundError(f"文件不存在：{audio_path}")
    if not audio_path.is_file():
        raise ValueError(f"不是文件：{audio_path}")
    if audio_path.suffix.lower() not in SUPPORTED_EXTS:
        print("警告：文件扩展名不在常见媒体格式列表中，仍会尝试转写。")


def transcribe_file(
    audio_path: Path,
    output_dir: Path,
    model_name: str,
    language: str,
    device: str,
    compute_type: str,
    beam_size: int,
    vad_filter: bool,
) -> tuple[Path, Path, object]:
    model, actual_device, actual_compute_type = load_model_with_fallback(model_name, device, compute_type)

    print("[2/4] 模型加载完成")
    print(f"      实际运行设备：{actual_device}")
    print(f"      实际计算类型：{actual_compute_type}")
    print("[3/4] 开始转写，请耐心等待…")

    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=vad_filter,
        beam_size=beam_size,
    )

    txt_path = output_dir / f"{audio_path.stem}.txt"
    srt_path = output_dir / f"{audio_path.stem}.srt"

    print("[4/4] 正在写入文件…")
    with open(txt_path, "w", encoding="utf-8") as f_txt, open(srt_path, "w", encoding="utf-8") as f_srt:
        for i, segment in enumerate(segments, start=1):
            text = segment.text.strip()
            if not text:
                continue

            f_txt.write(text + "\n")
            f_srt.write(f"{i}\n")
            f_srt.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
            f_srt.write(text + "\n\n")

    return txt_path, srt_path, info


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="阿拉伯语音频/视频转文字工具（基于 faster-whisper）"
    )
    parser.add_argument("input", nargs="?", help="音频/视频文件路径")
    parser.add_argument("--output-dir", help="输出目录，默认在源文件旁自动创建")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Whisper 模型名，默认 medium")
    parser.add_argument("--language", default="ar", help="语言代码，默认 ar（阿拉伯语）")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto", help="运行设备，默认 auto")
    parser.add_argument("--compute-type", default="int8", help="计算类型，CPU 默认建议 int8")
    parser.add_argument("--beam-size", type=int, default=5, help="解码 beam size，默认 5")
    parser.add_argument("--no-vad", action="store_true", help="关闭静音过滤")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        audio_path = Path(args.input).expanduser().resolve() if args.input else ask_for_file().expanduser().resolve()
        validate_audio_path(audio_path)
        output_dir = resolve_output_dir(audio_path, args.output_dir)

        print("=" * 60)
        print("阿拉伯语转写工具")
        print("=" * 60)
        print(f"输入文件：{audio_path}")
        print(f"输出目录：{output_dir}")
        print(f"模型：{args.model}")
        print(f"语言：{args.language}")
        print(f"设备策略：{args.device}")
        print("=" * 60)

        txt_path, srt_path, info = transcribe_file(
            audio_path=audio_path,
            output_dir=output_dir,
            model_name=args.model,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
            beam_size=args.beam_size,
            vad_filter=not args.no_vad,
        )

        print("\n转写完成")
        print(f"检测语言：{getattr(info, 'language', 'unknown')}")
        print(f"语言置信度：{getattr(info, 'language_probability', 'unknown')}")
        print(f"TXT 文件：{txt_path}")
        print(f"SRT 文件：{srt_path}")
        print("\n可以直接把生成的 SRT 拖进剪映、Premiere 或其他字幕工具继续处理。")
        return 0

    except KeyboardInterrupt:
        print("\n用户中断。")
        return 130
    except Exception as exc:
        print("\n程序运行失败。")
        print(f"错误信息：{exc}")
        print("\n详细报错如下：")
        traceback.print_exc()
        print(
            "\n排查建议：\n"
            "1. 确认输入文件路径正确。\n"
            "2. 首次运行会自动下载模型，请保证网络正常。\n"
            "3. 若使用 CPU，优先尝试 --model small 或 --model medium。\n"
            "4. 若你强制使用 CUDA，请确认已安装对应 NVIDIA CUDA/cuDNN 运行库。"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
