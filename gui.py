from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from app import (
    DEFAULT_MODEL,
    SUPPORTED_EXTS,
    TranscriptionCancelled,
    resolve_output_dir,
    transcribe_file,
    validate_audio_path,
)


class TranscriberGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("阿拉伯语音频转写工具")
        self.geometry("760x650")
        self.minsize(680, 580)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.last_output_dir: Path | None = None

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.device_var = tk.StringVar(value="auto")
        self.vad_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="请选择一个阿拉伯语音频或视频文件")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self.after(100, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Hint.TLabel", foreground="#555555")

        container = ttk.Frame(self, padding=22)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)

        ttk.Label(container, text="阿拉伯语音频转写工具", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="音频仅在本机处理。首次使用某个模型时需要联网下载，之后可离线运行。",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))

        files = ttk.LabelFrame(container, text="文件", padding=12)
        files.grid(row=2, column=0, sticky="ew")
        files.columnconfigure(0, weight=1)

        ttk.Entry(files, textvariable=self.input_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.choose_input_button = ttk.Button(files, text="选择音频/视频…", command=self._choose_input)
        self.choose_input_button.grid(row=0, column=1)

        ttk.Entry(files, textvariable=self.output_var).grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(10, 0))
        self.choose_output_button = ttk.Button(files, text="选择输出文件夹…", command=self._choose_output)
        self.choose_output_button.grid(row=1, column=1, pady=(10, 0))
        ttk.Label(files, text="输出文件夹留空时，会在源文件旁自动创建。", style="Hint.TLabel").grid(
            row=2, column=0, sticky="w", pady=(5, 0)
        )

        options = ttk.LabelFrame(container, text="转写设置", padding=12)
        options.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        ttk.Label(options, text="模型").grid(row=0, column=0, sticky="w")
        self.model_box = ttk.Combobox(
            options,
            textvariable=self.model_var,
            values=("tiny", "base", "small", "medium", "large-v3"),
            state="readonly",
            width=14,
        )
        self.model_box.grid(row=0, column=1, sticky="w", padx=(8, 24))
        ttk.Label(options, text="运行设备").grid(row=0, column=2, sticky="w")
        self.device_box = ttk.Combobox(
            options,
            textvariable=self.device_var,
            values=("auto", "cpu", "cuda"),
            state="readonly",
            width=12,
        )
        self.device_box.grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Checkbutton(options, text="自动过滤静音（推荐）", variable=self.vad_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Label(options, text="普通电脑建议 small；效果优先可选择 medium。", style="Hint.TLabel").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        actions = ttk.Frame(container)
        actions.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        actions.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(actions, text="开始转写", command=self._start)
        self.start_button.grid(row=0, column=0, sticky="ew")
        self.cancel_button = ttk.Button(actions, text="取消", command=self._cancel, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=(10, 0))
        self.open_button = ttk.Button(actions, text="打开结果文件夹", command=self._open_output, state="disabled")
        self.open_button.grid(row=0, column=2, padx=(10, 0))

        ttk.Label(container, textvariable=self.status_var).grid(row=5, column=0, sticky="w", pady=(16, 6))
        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=6, column=0, sticky="ew")

        log_frame = ttk.LabelFrame(container, text="运行日志", padding=8)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(14, 0))
        container.rowconfigure(7, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _choose_input(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTS))
        selected = filedialog.askopenfilename(
            title="选择阿拉伯语音频或视频",
            filetypes=(("媒体文件", patterns), ("所有文件", "*.*")),
        )
        if selected:
            self.input_var.set(selected)

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="选择输出文件夹")
        if selected:
            self.output_var.set(selected)

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            input_path = Path(self.input_var.get().strip()).expanduser().resolve()
            validate_audio_path(input_path)
        except Exception as exc:
            messagebox.showerror("无法开始", str(exc))
            return

        output_text = self.output_var.get().strip()
        output_dir = resolve_output_dir(input_path, output_text or None)
        self.last_output_dir = output_dir
        self.cancel_event.clear()
        self.progress_var.set(0)
        self.status_var.set("正在准备转写…")
        self._append_log(f"输入文件：{input_path}")
        self._append_log(f"输出目录：{output_dir}")
        self._set_running(True)

        settings = {
            "audio_path": input_path,
            "output_dir": output_dir,
            "model_name": self.model_var.get(),
            "language": "ar",
            "device": self.device_var.get(),
            "compute_type": "int8",
            "beam_size": 5,
            "vad_filter": self.vad_var.get(),
        }
        self.worker = threading.Thread(target=self._run_transcription, args=(settings,), daemon=True)
        self.worker.start()

    def _run_transcription(self, settings: dict[str, object]) -> None:
        try:
            txt_path, srt_path, info = transcribe_file(
                **settings,
                log=lambda text: self.events.put(("log", text)),
                progress=lambda current, total: self.events.put(("progress", (current, total))),
                cancel_event=self.cancel_event,
            )
            self.events.put(("done", (txt_path, srt_path, info)))
        except TranscriptionCancelled as exc:
            self.events.put(("cancelled", exc))
        except Exception as exc:
            self.events.put(("error", (exc, traceback.format_exc())))

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.status_var.set("正在取消；当前处理步骤结束后会停止…")
        self.cancel_button.configure(state="disabled")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                    if "正在加载模型" in str(payload):
                        self.status_var.set("正在加载模型（首次下载可能需要一些时间）…")
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(12)
                    elif "开始转写" in str(payload):
                        self.progress.stop()
                        self.progress.configure(mode="determinate")
                        self.status_var.set("正在转写…")
                elif kind == "progress":
                    current, total = payload  # type: ignore[misc]
                    percent = min(100.0, current / total * 100.0) if total else 0.0
                    self.progress_var.set(percent)
                    self.status_var.set(f"正在转写… {percent:.0f}%")
                elif kind == "done":
                    txt_path, srt_path, info = payload  # type: ignore[misc]
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(100)
                    self._set_running(False)
                    self.open_button.configure(state="normal")
                    language = getattr(info, "language", "unknown")
                    self.status_var.set("转写完成")
                    self._append_log(f"转写完成（检测语言：{language}）")
                    self._append_log(f"TXT：{txt_path}")
                    self._append_log(f"SRT：{srt_path}")
                    messagebox.showinfo("转写完成", "TXT 和 SRT 文件已经生成。")
                elif kind == "cancelled":
                    self.progress.stop()
                    self._set_running(False)
                    self.status_var.set("转写已取消")
                    self._append_log(str(payload))
                elif kind == "error":
                    exc, detail = payload  # type: ignore[misc]
                    self.progress.stop()
                    self._set_running(False)
                    self.status_var.set("转写失败")
                    self._append_log(detail)
                    messagebox.showerror(
                        "转写失败",
                        f"{exc}\n\n请检查网络、媒体文件以及设备设置。CPU 用户可尝试 small 模型。",
                    )
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.choose_input_button.configure(state=state)
        self.choose_output_button.configure(state=state)
        self.model_box.configure(state="disabled" if running else "readonly")
        self.device_box.configure(state="disabled" if running else "readonly")
        self.cancel_button.configure(state="normal" if running else "disabled")

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _open_output(self) -> None:
        if not self.last_output_dir:
            return
        path = str(self.last_output_dir)
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror("无法打开文件夹", str(exc))

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("转写仍在进行", "确定要停止转写并关闭窗口吗？"):
                return
            self.cancel_event.set()
        self.destroy()


def main() -> None:
    app = TranscriberGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
