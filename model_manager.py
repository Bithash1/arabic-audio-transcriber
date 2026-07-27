from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Event, Lock
from typing import Callable, Optional

from faster_whisper.utils import download_model as resolve_faster_whisper_model
from huggingface_hub import constants, snapshot_download
from tqdm.auto import tqdm


SUPPORTED_MODELS = ("small", "medium", "large-v3")
MODEL_REPOSITORIES = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}
MODEL_FILES = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)
REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")

DownloadProgressCallback = Callable[[float], None]


class ModelState(str, Enum):
    CHECKING = "checking"
    INSTALLED = "installed"
    NOT_DOWNLOADED = "not_downloaded"
    INCOMPLETE = "incomplete"
    STORAGE_UNAVAILABLE = "storage_unavailable"


class ModelDownloadCancelled(RuntimeError):
    """Raised when a model download is cancelled."""


@dataclass
class ModelStatus:
    model: str
    state: ModelState
    path: Optional[Path] = None
    cache_dir: Optional[Path] = None
    detail: str = ""


def default_cache_dir() -> Path:
    return Path(constants.HF_HUB_CACHE).expanduser().resolve()


def active_download_dir(custom_cache_dir: str = "") -> Path:
    return Path(custom_cache_dir).expanduser().resolve() if custom_cache_dir else default_cache_dir()


def _candidate_cache_dirs(custom_cache_dir: str = "") -> list[Path]:
    candidates = []
    if custom_cache_dir:
        candidates.append(Path(custom_cache_dir).expanduser().resolve())
    candidates.append(default_cache_dir())
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _validate_model_path(path: Path) -> tuple[bool, str]:
    missing = [name for name in REQUIRED_FILES if not (path / name).is_file()]
    has_vocabulary = any(path.glob("vocabulary.*"))
    if not has_vocabulary:
        missing.append("vocabulary.*")
    if missing:
        return False, "缺少文件：" + ", ".join(missing)
    return True, ""


def inspect_model(model: str, custom_cache_dir: str = "") -> ModelStatus:
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"不支持的模型：{model}")

    incomplete: Optional[ModelStatus] = None
    for cache_dir in _candidate_cache_dirs(custom_cache_dir):
        if not cache_dir.exists():
            continue
        try:
            resolved = Path(
                resolve_faster_whisper_model(
                    model,
                    local_files_only=True,
                    cache_dir=str(cache_dir),
                )
            ).resolve()
        except Exception as exc:
            repo_folder = cache_dir / f"models--Systran--faster-whisper-{model}"
            if repo_folder.exists():
                incomplete = ModelStatus(
                    model=model,
                    state=ModelState.INCOMPLETE,
                    cache_dir=cache_dir,
                    detail=str(exc),
                )
            continue

        valid, detail = _validate_model_path(resolved)
        if valid:
            return ModelStatus(
                model=model,
                state=ModelState.INSTALLED,
                path=resolved,
                cache_dir=cache_dir,
            )
        incomplete = ModelStatus(
            model=model,
            state=ModelState.INCOMPLETE,
            path=resolved,
            cache_dir=cache_dir,
            detail=detail,
        )

    if incomplete:
        return incomplete
    if custom_cache_dir and not Path(custom_cache_dir).expanduser().exists():
        return ModelStatus(
            model=model,
            state=ModelState.STORAGE_UNAVAILABLE,
            cache_dir=Path(custom_cache_dir).expanduser(),
            detail="自定义模型目录不存在或外部磁盘未连接。",
        )
    return ModelStatus(
        model=model,
        state=ModelState.NOT_DOWNLOADED,
        cache_dir=active_download_dir(custom_cache_dir),
    )


def inspect_all_models(custom_cache_dir: str = "") -> dict[str, ModelStatus]:
    return {model: inspect_model(model, custom_cache_dir) for model in SUPPORTED_MODELS}


def _progress_class(
    expected_bytes: int,
    callback: Optional[DownloadProgressCallback],
    cancel_event: Optional[Event],
) -> type[tqdm]:
    lock = Lock()

    class GUIProgress(tqdm):
        def __init__(self, *args, **kwargs):
            description = str(kwargs.get("desc", ""))
            self._report_bytes = description.startswith("Reconstructing")
            self._reported_bytes = float(kwargs.get("initial", 0) or 0)
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if cancel_event and cancel_event.is_set():
                raise ModelDownloadCancelled("模型下载已取消，已下载的部分将在下次继续使用。")
            result = super().update(n)
            if self._report_bytes and callback and expected_bytes > 0:
                with lock:
                    self._reported_bytes += float(n or 0)
                    callback(min(99.0, max(0.0, self._reported_bytes / expected_bytes * 100.0)))
            return result

    return GUIProgress


def download_model_with_progress(
    model: str,
    cache_dir: Path,
    progress: Optional[DownloadProgressCallback] = None,
    cancel_event: Optional[Event] = None,
) -> Path:
    if model not in MODEL_REPOSITORIES:
        raise ValueError(f"不支持的模型：{model}")
    if not cache_dir.exists():
        if cache_dir == default_cache_dir():
            cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"自定义模型目录不可用：{cache_dir}")
    if not cache_dir.is_dir():
        raise NotADirectoryError(f"模型存储位置不是文件夹：{cache_dir}")

    repo_id = MODEL_REPOSITORIES[model]
    if progress:
        progress(0.0)
    dry_run = snapshot_download(
        repo_id,
        cache_dir=str(cache_dir),
        allow_patterns=list(MODEL_FILES),
        dry_run=True,
        tqdm_class=_progress_class(0, None, cancel_event),
    )
    expected_bytes = sum(item.file_size for item in dry_run if item.will_download)
    if cancel_event and cancel_event.is_set():
        raise ModelDownloadCancelled("模型下载已取消。")

    resolved = Path(
        snapshot_download(
            repo_id,
            cache_dir=str(cache_dir),
            allow_patterns=list(MODEL_FILES),
            tqdm_class=_progress_class(expected_bytes, progress, cancel_event),
        )
    ).resolve()
    valid, detail = _validate_model_path(resolved)
    if not valid:
        raise RuntimeError(f"模型下载完成但校验失败：{detail}")
    if progress:
        progress(100.0)
    return resolved
