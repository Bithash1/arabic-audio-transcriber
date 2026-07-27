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

from ai_processor import (
    AIProcessingCancelled,
    AISettings,
    DeepSeekProvider,
    process_transcript,
)
from app import (
    DEFAULT_MODEL,
    SUPPORTED_EXTS,
    TranscriptionCancelled,
    resolve_output_dir,
    transcribe_file,
    validate_audio_path,
)
from model_manager import (
    SUPPORTED_MODELS,
    ModelDownloadCancelled,
    ModelState,
    ModelStatus,
    active_download_dir,
    default_cache_dir,
    download_model_with_progress,
    inspect_all_models,
    inspect_model,
)
from settings_store import (
    StoredAISettings,
    load_api_key,
    load_settings,
    save_api_key,
    save_settings,
)


class AISettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        stored: StoredAISettings,
        api_key: str,
    ) -> None:
        super().__init__(parent)
        self.title("AI API 设置")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: tuple[StoredAISettings, str] | None = None
        self.model_cache_dir = stored.model_cache_dir

        self.base_url_var = tk.StringVar(value=stored.base_url)
        self.model_var = tk.StringVar(value=stored.model)
        self.api_key_var = tk.StringVar(value=api_key)
        self.remember_var = tk.BooleanVar(value=stored.remember_key)
        self.status_var = tk.StringVar(value="API Key 不会写入项目文件或运行日志。")

        frame = ttk.Frame(self, padding=18)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="服务商").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(frame, text="DeepSeek（OpenAI 兼容接口）").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(frame, text="Base URL").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.base_url_var, width=42).grid(row=1, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(frame, text="模型").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self.model_var,
            values=("deepseek-v4-flash", "deepseek-v4-pro"),
            width=39,
        ).grid(row=2, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(frame, text="API Key").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.api_key_var, show="•", width=42).grid(
            row=3, column=1, sticky="ew", padx=(12, 0)
        )
        ttk.Checkbutton(
            frame,
            text="使用系统钥匙串记住 API Key",
            variable=self.remember_var,
        ).grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(4, 8))
        ttk.Label(frame, textvariable=self.status_var, foreground="#555555", wraplength=430).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 12)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        self.test_button = ttk.Button(buttons, text="测试连接", command=self._test)
        self.test_button.grid(row=0, column=0)
        ttk.Button(buttons, text="取消", command=self.destroy).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(buttons, text="保存", command=self._save).grid(row=0, column=2, padx=(8, 0))

        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(20, self._center)

    def _center(self) -> None:
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _settings(self) -> AISettings:
        return AISettings(
            api_key=self.api_key_var.get().strip(),
            base_url=self.base_url_var.get().strip(),
            model=self.model_var.get().strip(),
        )

    def _validate(self) -> bool:
        settings = self._settings()
        if not settings.api_key:
            messagebox.showerror("设置不完整", "请输入 API Key。", parent=self)
            return False
        if not settings.base_url.startswith(("https://", "http://")):
            messagebox.showerror("设置不完整", "Base URL 必须以 http:// 或 https:// 开头。", parent=self)
            return False
        if not settings.model:
            messagebox.showerror("设置不完整", "请输入模型名称。", parent=self)
            return False
        return True

    def _test(self) -> None:
        if not self._validate():
            return
        settings = self._settings()
        self.test_button.configure(state="disabled")
        self.status_var.set("正在测试连接…")

        def worker() -> None:
            try:
                DeepSeekProvider(settings, timeout=30).test_connection()
                self.after(0, lambda: self._test_finished(None))
            except Exception as exc:
                self.after(0, lambda error=exc: self._test_finished(error))

        threading.Thread(target=worker, daemon=True).start()

    def _test_finished(self, error: Exception | None) -> None:
        if not self.winfo_exists():
            return
        self.test_button.configure(state="normal")
        if error:
            self.status_var.set(f"连接失败：{error}")
        else:
            self.status_var.set("连接成功，可以使用 AI 功能。")

    def _save(self) -> None:
        if not self._validate():
            return
        settings = StoredAISettings(
            base_url=self.base_url_var.get().strip(),
            model=self.model_var.get().strip(),
            remember_key=self.remember_var.get(),
            model_cache_dir=self.model_cache_dir,
        )
        try:
            save_settings(settings)
        except OSError as exc:
            messagebox.showerror("无法保存设置", str(exc), parent=self)
            return
        if not save_api_key(self.api_key_var.get().strip(), settings.remember_key) and settings.remember_key:
            messagebox.showwarning(
                "无法保存 API Key",
                "系统钥匙串不可用。API Key 本次运行仍然有效，但关闭程序后需要重新输入。",
                parent=self,
            )
        self.result = (settings, self.api_key_var.get().strip())
        self.destroy()


class TranscriberGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("阿拉伯语音频转写与 AI 处理工具")
        self.geometry("900x860")
        self.minsize(800, 760)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.worker_kind = ""
        self.last_output_dir: Path | None = None
        self.source_srt: Path | None = None
        self.privacy_confirmed = False
        self.model_statuses: dict[str, ModelStatus] = {
            model: ModelStatus(model, ModelState.CHECKING) for model in SUPPORTED_MODELS
        }

        self.stored_ai_settings = load_settings()
        self.api_key = load_api_key() if self.stored_ai_settings.remember_key else ""

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value="medium（推荐 · 检查中…）")
        self.model_path_var = tk.StringVar(value=f"默认模型目录：{default_cache_dir()}")
        self.model_detail_var = tk.StringVar(value="正在检查本机模型…")
        self.device_var = tk.StringVar(value="auto")
        self.vad_var = tk.BooleanVar(value=True)
        self.translate_var = tk.BooleanVar(value=True)
        self.diacritize_var = tk.BooleanVar(value=False)
        self.correct_var = tk.BooleanVar(value=False)
        self.target_language_var = tk.StringVar(value="简体中文")
        self.status_var = tk.StringVar(value="请选择一个阿拉伯语音频或视频文件")
        self.ai_status_var = tk.StringVar(value="请先完成本地转写")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self.after(100, self._drain_events)
        self.after(150, self._refresh_model_statuses)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Section.TLabel", font=("TkDefaultFont", 11, "bold"))
        style.configure("Hint.TLabel", foreground="#555555")

        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(9, weight=1)

        ttk.Label(container, text="阿拉伯语音频转写工具", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="本地转写与 AI 处理完全独立：首次下载 Whisper 模型后可离线转写，AI 功能按需使用。",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

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

        transcribe_frame = ttk.LabelFrame(container, text="1. 本地转写", padding=12)
        transcribe_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        transcribe_frame.columnconfigure(5, weight=1)
        ttk.Label(transcribe_frame, text="Whisper 模型").grid(row=0, column=0, sticky="w")
        self.model_box = ttk.Combobox(
            transcribe_frame,
            textvariable=self.model_var,
            values=tuple(self._model_label(model) for model in SUPPORTED_MODELS),
            state="readonly",
            width=26,
        )
        self.model_box.grid(row=0, column=1, padx=(8, 18))
        self.model_box.bind("<<ComboboxSelected>>", lambda _event: self._update_model_detail())
        ttk.Label(transcribe_frame, text="设备").grid(row=0, column=2, sticky="w")
        self.device_box = ttk.Combobox(
            transcribe_frame,
            textvariable=self.device_var,
            values=("auto", "cpu", "cuda"),
            state="readonly",
            width=9,
        )
        self.device_box.grid(row=0, column=3, padx=(8, 18))
        ttk.Checkbutton(transcribe_frame, text="过滤静音", variable=self.vad_var).grid(row=0, column=4, sticky="w")
        self.start_button = ttk.Button(transcribe_frame, text="开始本地转写", command=self._start_transcription)
        self.start_button.grid(row=0, column=5, sticky="e")
        ttk.Label(transcribe_frame, textvariable=self.model_path_var, style="Hint.TLabel", wraplength=650).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(9, 0)
        )
        self.change_model_dir_button = ttk.Button(transcribe_frame, text="更改目录…", command=self._choose_model_cache)
        self.change_model_dir_button.grid(row=1, column=4, padx=(8, 0), pady=(8, 0))
        self.open_model_dir_button = ttk.Button(transcribe_frame, text="打开目录", command=self._open_model_folder)
        self.open_model_dir_button.grid(row=1, column=5, sticky="e", pady=(8, 0))
        ttk.Label(transcribe_frame, textvariable=self.model_detail_var, style="Hint.TLabel", wraplength=760).grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            transcribe_frame,
            text="某个模型首次使用时需要联网下载；下载完成后，该模型可以离线使用。",
            style="Hint.TLabel",
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(6, 0))

        ai_frame = ttk.LabelFrame(container, text="2. AI 处理（可选）", padding=12)
        ai_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ai_frame.columnconfigure(6, weight=1)
        self.correct_check = ttk.Checkbutton(
            ai_frame,
            text="AI 文本矫正",
            variable=self.correct_var,
            command=self._update_ai_state,
        )
        self.correct_check.grid(row=0, column=0, sticky="w")
        self.translate_check = ttk.Checkbutton(ai_frame, text="翻译", variable=self.translate_var, command=self._update_ai_state)
        self.translate_check.grid(row=0, column=1, sticky="w", padx=(14, 0))
        ttk.Label(ai_frame, text="目标语言").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.language_box = ttk.Combobox(
            ai_frame,
            textvariable=self.target_language_var,
            values=("简体中文", "English"),
            state="readonly",
            width=10,
        )
        self.language_box.grid(row=0, column=3, padx=(8, 14))
        self.diacritize_check = ttk.Checkbutton(
            ai_frame,
            text="添加阿语标音（Tashkeel）",
            variable=self.diacritize_var,
            command=self._update_ai_state,
        )
        self.diacritize_check.grid(row=0, column=4, sticky="w")
        ttk.Button(ai_frame, text="API 设置…", command=self._open_ai_settings).grid(row=0, column=5, padx=(14, 8))
        self.ai_button = ttk.Button(ai_frame, text="开始 AI 处理", command=self._start_ai, state="disabled")
        self.ai_button.grid(row=0, column=6, sticky="e")
        ttk.Label(ai_frame, textvariable=self.ai_status_var, style="Hint.TLabel").grid(
            row=1, column=0, columnspan=7, sticky="w", pady=(8, 0)
        )
        ttk.Label(
            ai_frame,
            text="AI 处理时仅发送转写文字，不上传音频；原始 TXT/SRT 永远不会被覆盖。",
            style="Hint.TLabel",
        ).grid(row=2, column=0, columnspan=7, sticky="w", pady=(4, 0))

        actions = ttk.Frame(container)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        self.cancel_button = ttk.Button(actions, text="取消当前任务", command=self._cancel, state="disabled")
        self.cancel_button.grid(row=0, column=1)
        self.open_button = ttk.Button(actions, text="打开结果文件夹", command=self._open_output, state="disabled")
        self.open_button.grid(row=0, column=2, padx=(10, 0))

        ttk.Label(container, textvariable=self.status_var).grid(row=6, column=0, sticky="w", pady=(12, 5))
        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=7, column=0, sticky="ew")

        log_frame = ttk.LabelFrame(container, text="运行日志", padding=8)
        log_frame.grid(row=9, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _selected_model(self) -> str:
        value = self.model_var.get()
        for model in SUPPORTED_MODELS:
            if value.startswith(model):
                return model
        return DEFAULT_MODEL

    def _model_label(self, model: str) -> str:
        status = self.model_statuses.get(model)
        state_text = {
            ModelState.CHECKING: "检查中…",
            ModelState.INSTALLED: "已下载",
            ModelState.NOT_DOWNLOADED: "未下载",
            ModelState.INCOMPLETE: "需要修复",
            ModelState.STORAGE_UNAVAILABLE: "存储位置不可用",
        }.get(status.state if status else ModelState.CHECKING, "检查中…")
        recommendation = "推荐 · " if model == "medium" else ""
        return f"{model}（{recommendation}{state_text}）"

    def _refresh_model_labels(self) -> None:
        selected = self._selected_model()
        labels = tuple(self._model_label(model) for model in SUPPORTED_MODELS)
        self.model_box.configure(values=labels)
        self.model_var.set(self._model_label(selected))
        self._update_model_detail()

    def _refresh_model_statuses(self) -> None:
        if self.worker_kind:
            return
        self.model_statuses = {
            model: ModelStatus(model, ModelState.CHECKING) for model in SUPPORTED_MODELS
        }
        self._refresh_model_labels()
        custom_dir = self.stored_ai_settings.model_cache_dir
        active = active_download_dir(custom_dir)
        prefix = "自定义模型目录" if custom_dir else "默认模型目录"
        self.model_path_var.set(f"{prefix}：{active}")

        def worker() -> None:
            try:
                statuses = inspect_all_models(custom_dir)
                self.events.put(("model_statuses", statuses))
            except Exception as exc:
                self.events.put(("model_scan_error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _update_model_detail(self) -> None:
        model = self._selected_model()
        status = self.model_statuses.get(model, ModelStatus(model, ModelState.CHECKING))
        if status.state == ModelState.CHECKING:
            text = f"{model}：正在检查本地缓存…"
        elif status.state == ModelState.INSTALLED:
            location = status.path or status.cache_dir
            text = f"{model}：已下载；位置：{location}"
        elif status.state == ModelState.INCOMPLETE:
            text = f"{model}：文件不完整，需要重新下载修复。"
        elif status.state == ModelState.STORAGE_UNAVAILABLE:
            text = f"{model}：自定义模型目录不可用，请连接磁盘或更改目录。"
        else:
            text = f"{model}：未下载；使用时将保存至 {active_download_dir(self.stored_ai_settings.model_cache_dir)}"
        self.model_detail_var.set(text)

    def _choose_model_cache(self) -> None:
        current = active_download_dir(self.stored_ai_settings.model_cache_dir)
        selected = filedialog.askdirectory(title="选择 Whisper 模型存储文件夹", initialdir=str(current))
        if not selected:
            return
        use_default = Path(selected).expanduser().resolve() == default_cache_dir()
        self.stored_ai_settings.model_cache_dir = "" if use_default else str(Path(selected).expanduser().resolve())
        try:
            save_settings(self.stored_ai_settings)
        except OSError as exc:
            messagebox.showerror("无法保存模型目录", str(exc))
            return
        self._refresh_model_statuses()

    def _open_model_folder(self) -> None:
        status = self.model_statuses.get(self._selected_model())
        path = status.path if status and status.path else active_download_dir(self.stored_ai_settings.model_cache_dir)
        if not path.exists():
            messagebox.showerror("无法打开目录", f"模型目录不存在：{path}")
            return
        self._open_path(path)

    def _choose_input(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTS))
        selected = filedialog.askopenfilename(
            title="选择阿拉伯语音频或视频",
            filetypes=(("媒体文件", patterns), ("所有文件", "*.*")),
        )
        if selected:
            self.input_var.set(selected)
            self._detect_existing_transcript()

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="选择输出文件夹")
        if selected:
            self.output_var.set(selected)
            self._detect_existing_transcript()

    def _detect_existing_transcript(self) -> None:
        raw = self.input_var.get().strip()
        if not raw:
            return
        media = Path(raw).expanduser()
        output = Path(self.output_var.get().strip()).expanduser() if self.output_var.get().strip() else media.parent / f"{media.stem}_transcript"
        candidate = output / f"{media.stem}.srt"
        self.source_srt = candidate.resolve() if candidate.exists() else None
        if self.source_srt:
            self.last_output_dir = self.source_srt.parent
            self.open_button.configure(state="normal")
        self._update_ai_state()

    def _start_transcription(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            input_path = Path(self.input_var.get().strip()).expanduser().resolve()
            validate_audio_path(input_path)
        except Exception as exc:
            messagebox.showerror("无法开始", str(exc))
            return

        model_name = self._selected_model()
        status = inspect_model(model_name, self.stored_ai_settings.model_cache_dir)
        self.model_statuses[model_name] = status
        self._refresh_model_labels()
        if status.state == ModelState.STORAGE_UNAVAILABLE:
            messagebox.showerror(
                "模型目录不可用",
                "自定义模型目录不存在或外部磁盘未连接。\n\n"
                "请连接磁盘，或点击“更改目录”选择新的存储位置。",
            )
            return

        needs_download = status.state != ModelState.INSTALLED
        if needs_download:
            action = "重新下载并修复" if status.state == ModelState.INCOMPLETE else "下载"
            cache_dir = active_download_dir(self.stored_ai_settings.model_cache_dir)
            if not messagebox.askyesno(
                f"需要{action}模型",
                f"{model_name} 模型当前不可用，需要联网{action}。\n\n"
                f"保存位置：\n{cache_dir}\n\n"
                "下载会占用一定磁盘空间，已下载的部分可在中断后继续使用。是否继续？",
            ):
                return

        output_dir = resolve_output_dir(input_path, self.output_var.get().strip() or None)
        self.last_output_dir = output_dir
        self.source_srt = None
        self.cancel_event.clear()
        self.progress_var.set(0)
        self.status_var.set("正在准备本地转写…")
        self._append_log(f"输入文件：{input_path}")
        self._append_log(f"输出目录：{output_dir}")
        self._set_running(True, "transcription")

        settings = {
            "audio_path": input_path,
            "output_dir": output_dir,
            "model_name": model_name,
            "language": "ar",
            "device": self.device_var.get(),
            "compute_type": "int8",
            "beam_size": 5,
            "vad_filter": self.vad_var.get(),
            "model_path": status.path if status.state == ModelState.INSTALLED else None,
        }
        self.worker = threading.Thread(
            target=self._run_transcription,
            args=(settings, needs_download),
            daemon=True,
        )
        self.worker.start()

    def _run_transcription(self, settings: dict[str, object], needs_download: bool = False) -> None:
        try:
            if needs_download:
                model_name = str(settings["model_name"])
                cache_dir = active_download_dir(self.stored_ai_settings.model_cache_dir)
                self.events.put(("log", f"正在准备下载 {model_name} 模型…"))
                model_path = download_model_with_progress(
                    model_name,
                    cache_dir,
                    progress=lambda percent: self.events.put(("model_download_progress", percent)),
                    cancel_event=self.cancel_event,
                )
                settings["model_path"] = model_path
                self.events.put(("model_downloaded", (model_name, model_path, cache_dir)))
                if self.cancel_event.is_set():
                    raise ModelDownloadCancelled("模型下载已取消。")
            txt_path, srt_path, info = transcribe_file(
                **settings,
                log=lambda text: self.events.put(("log", text)),
                progress=lambda current, total: self.events.put(("transcription_progress", (current, total))),
                cancel_event=self.cancel_event,
            )
            self.events.put(("transcription_done", (txt_path, srt_path, info)))
        except (TranscriptionCancelled, ModelDownloadCancelled) as exc:
            self.events.put(("cancelled", exc))
        except Exception as exc:
            self.events.put(("error", ("本地转写", exc, traceback.format_exc())))

    def _open_ai_settings(self) -> bool:
        dialog = AISettingsDialog(self, self.stored_ai_settings, self.api_key)
        self.wait_window(dialog)
        if dialog.result:
            self.stored_ai_settings, self.api_key = dialog.result
            self._update_ai_state()
            return True
        return False

    def _start_ai(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.source_srt or not self.source_srt.exists():
            messagebox.showerror("无法开始", "请先完成本地转写。")
            return
        if not self.correct_var.get() and not self.translate_var.get() and not self.diacritize_var.get():
            messagebox.showerror("无法开始", "请至少选择文本矫正、翻译或阿语标音中的一项。")
            return
        if not self.api_key and not self._open_ai_settings():
            return
        if not self.privacy_confirmed:
            confirmed = messagebox.askyesno(
                "发送转写文字到 AI 服务",
                "AI 处理需要联网，并会把转写后的阿拉伯语文字发送给所配置的 API 服务。\n\n"
                "音频文件不会上传，原始转写不会被覆盖。是否继续？",
            )
            if not confirmed:
                return
            self.privacy_confirmed = True

        self.cancel_event.clear()
        self.progress_var.set(0)
        self.status_var.set("正在准备 AI 处理…")
        self._set_running(True, "ai")
        settings = AISettings(
            api_key=self.api_key,
            base_url=self.stored_ai_settings.base_url,
            model=self.stored_ai_settings.model,
        )
        self.worker = threading.Thread(
            target=self._run_ai,
            args=(
                settings,
                self.correct_var.get(),
                self.translate_var.get(),
                self.diacritize_var.get(),
                self.target_language_var.get(),
            ),
            daemon=True,
        )
        self.worker.start()

    def _run_ai(
        self,
        settings: AISettings,
        correct: bool,
        translate: bool,
        diacritize: bool,
        target_language: str,
    ) -> None:
        assert self.source_srt is not None
        try:
            segments, usage, project_path = process_transcript(
                source_srt=self.source_srt,
                output_dir=self.source_srt.parent,
                settings=settings,
                correct=correct,
                translate=translate,
                diacritize=diacritize,
                target_language=target_language,
                progress=lambda current, total: self.events.put(("ai_progress", (current, total))),
                log=lambda text: self.events.put(("log", text)),
                cancel_event=self.cancel_event,
            )
            self.events.put(("ai_done", (len(segments), usage, project_path)))
        except AIProcessingCancelled as exc:
            self.events.put(("cancelled", exc))
        except Exception as exc:
            self.events.put(("error", ("AI 处理", exc, traceback.format_exc())))

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
                    if "正在加载模型" in str(payload) and self.worker_kind == "transcription":
                        self.status_var.set("正在加载模型（首次下载可能需要一些时间）…")
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(12)
                    elif "开始转写" in str(payload):
                        self.progress.stop()
                        self.progress.configure(mode="determinate")
                        self.status_var.set("正在本地转写…")
                elif kind == "model_statuses":
                    self.model_statuses = payload  # type: ignore[assignment]
                    self._refresh_model_labels()
                elif kind == "model_scan_error":
                    self.model_detail_var.set(f"无法检查本机模型：{payload}")
                elif kind == "model_download_progress":
                    percent = float(payload)
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(percent)
                    self.status_var.set(f"正在下载模型… {percent:.0f}%")
                elif kind == "model_downloaded":
                    model_name, model_path, cache_dir = payload  # type: ignore[misc]
                    self.model_statuses[str(model_name)] = ModelStatus(
                        model=str(model_name),
                        state=ModelState.INSTALLED,
                        path=Path(model_path),
                        cache_dir=Path(cache_dir),
                    )
                    self._refresh_model_labels()
                    self._append_log(f"模型下载完成：{model_path}")
                    self.status_var.set("模型下载完成，正在加载模型…")
                elif kind == "transcription_progress":
                    current, total = payload  # type: ignore[misc]
                    percent = min(100.0, current / total * 100.0) if total else 0.0
                    self.progress_var.set(percent)
                    self.status_var.set(f"正在本地转写… {percent:.0f}%")
                elif kind == "ai_progress":
                    current, total = payload  # type: ignore[misc]
                    percent = min(100.0, current / total * 100.0) if total else 100.0
                    self.progress_var.set(percent)
                    self.status_var.set(f"正在 AI 处理… {current}/{total} 段")
                elif kind == "transcription_done":
                    txt_path, srt_path, info = payload  # type: ignore[misc]
                    self.source_srt = Path(srt_path)
                    self._finish_task("本地转写完成")
                    self.open_button.configure(state="normal")
                    language = getattr(info, "language", "unknown")
                    self._append_log(f"转写完成（检测语言：{language}）")
                    self._append_log(f"TXT：{txt_path}")
                    self._append_log(f"SRT：{srt_path}")
                    messagebox.showinfo("转写完成", "原始阿语 TXT 和 SRT 已生成。\n现在可以直接导出，或按需使用 AI 处理。")
                elif kind == "ai_done":
                    segment_count, usage, project_path = payload  # type: ignore[misc]
                    self._finish_task("AI 处理完成")
                    self.open_button.configure(state="normal")
                    self._append_log(f"AI 处理完成：{segment_count} 个字幕片段")
                    self._append_log(f"Token 用量：{usage.total_tokens}（输入 {usage.prompt_tokens}，输出 {usage.completion_tokens}）")
                    self._append_log(f"项目文件：{project_path}")
                    messagebox.showinfo(
                        "AI 处理完成",
                        f"结果文件已经导出。\nToken 用量：{usage.total_tokens}",
                    )
                elif kind == "cancelled":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self._set_running(False)
                    self.status_var.set("任务已取消")
                    self._append_log(str(payload))
                elif kind == "error":
                    operation, exc, detail = payload  # type: ignore[misc]
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self._set_running(False)
                    self.status_var.set(f"{operation}失败")
                    self._append_log(detail)
                    messagebox.showerror(f"{operation}失败", str(exc))
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _finish_task(self, status: str) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress_var.set(100)
        self._set_running(False)
        self.status_var.set(status)

    def _update_ai_state(self) -> None:
        has_transcript = bool(self.source_srt and self.source_srt.exists())
        has_task = self.correct_var.get() or self.translate_var.get() or self.diacritize_var.get()
        running = bool(self.worker_kind)
        self.ai_button.configure(state="normal" if has_transcript and has_task and not running else "disabled")
        self.language_box.configure(state="readonly" if self.translate_var.get() and not running else "disabled")
        if not has_transcript:
            self.ai_status_var.set("请先完成本地转写")
        elif not has_task:
            self.ai_status_var.set("请至少选择文本矫正、翻译或阿语标音")
        else:
            tasks = []
            if self.correct_var.get():
                tasks.append("文本矫正")
            if self.translate_var.get():
                tasks.append("翻译")
            if self.diacritize_var.get():
                tasks.append("阿语标音")
            self.ai_status_var.set(f"已选择：{' + '.join(tasks)}；处理需要联网和 API Key")

    def _set_running(self, running: bool, kind: str = "") -> None:
        self.worker_kind = kind if running else ""
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.choose_input_button.configure(state=state)
        self.choose_output_button.configure(state=state)
        self.model_box.configure(state="disabled" if running else "readonly")
        self.device_box.configure(state="disabled" if running else "readonly")
        self.change_model_dir_button.configure(state=state)
        self.open_model_dir_button.configure(state=state)
        self.correct_check.configure(state=state)
        self.translate_check.configure(state=state)
        self.diacritize_check.configure(state=state)
        self.cancel_button.configure(state="normal" if running else "disabled")
        self._update_ai_state()

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _open_output(self) -> None:
        if not self.last_output_dir:
            return
        self._open_path(self.last_output_dir)

    def _open_path(self, target: Path) -> None:
        path = str(target)
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
            if not messagebox.askyesno("任务仍在进行", "确定要停止当前任务并关闭窗口吗？"):
                return
            self.cancel_event.set()
        self.destroy()


def main() -> None:
    app = TranscriberGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
