from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "ArabicAudioTranscriber"
KEYRING_SERVICE = "ArabicAudioTranscriber.DeepSeek"


@dataclass
class StoredAISettings:
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    remember_key: bool = False
    model_cache_dir: str = ""


def default_settings_path() -> Path:
    return Path.home() / ".arabic_audio_transcriber" / "settings.json"


def load_settings(path: Path | None = None) -> StoredAISettings:
    target = path or default_settings_path()
    if not target.exists():
        return StoredAISettings()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return StoredAISettings(
            base_url=str(payload.get("base_url") or "https://api.deepseek.com"),
            model=str(payload.get("model") or "deepseek-v4-flash"),
            remember_key=bool(payload.get("remember_key", False)),
            model_cache_dir=str(payload.get("model_cache_dir") or ""),
        )
    except (OSError, ValueError, TypeError):
        return StoredAISettings()


def save_settings(settings: StoredAISettings, path: Path | None = None) -> None:
    target = path or default_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def load_api_key() -> str:
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, "api_key") or ""
    except Exception:
        return ""


def save_api_key(api_key: str, remember: bool) -> bool:
    try:
        import keyring

        if remember:
            keyring.set_password(KEYRING_SERVICE, "api_key", api_key)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, "api_key")
            except keyring.errors.PasswordDeleteError:
                pass
        return True
    except Exception:
        return False
