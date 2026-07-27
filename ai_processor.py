from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterable, Optional

from app import format_timestamp


AIProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]


class AIProcessingCancelled(RuntimeError):
    """Raised when the user cancels AI processing between batches."""


class AIProviderError(RuntimeError):
    """A user-facing error returned by an AI provider."""


@dataclass
class TranscriptSegment:
    id: int
    start: float
    end: float
    original_arabic: str
    corrected_arabic: str = ""
    diacritized_arabic: str = ""
    translation: str = ""
    diacritized_source: str = ""
    translation_source: str = ""


@dataclass
class AISettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"


@dataclass
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, payload: dict[str, object]) -> None:
        self.prompt_tokens += int(payload.get("prompt_tokens", 0) or 0)
        self.completion_tokens += int(payload.get("completion_tokens", 0) or 0)
        self.total_tokens += int(payload.get("total_tokens", 0) or 0)


def _parse_srt_timestamp(value: str) -> float:
    time_part, milliseconds = value.strip().replace(".", ",").split(",", 1)
    hours, minutes, seconds = (int(part) for part in time_part.split(":"))
    return hours * 3600 + minutes * 60 + seconds + int(milliseconds[:3].ljust(3, "0")) / 1000


def parse_srt(path: Path) -> list[TranscriptSegment]:
    content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    if not content:
        return []

    segments: list[TranscriptSegment] = []
    for block in content.split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        try:
            segment_id = int(lines[0])
            start_text, end_text = lines[1].split("-->", 1)
            segments.append(
                TranscriptSegment(
                    id=segment_id,
                    start=_parse_srt_timestamp(start_text),
                    end=_parse_srt_timestamp(end_text),
                    original_arabic="\n".join(lines[2:]),
                )
            )
        except (ValueError, IndexError):
            continue
    if not segments:
        raise ValueError(f"没有在字幕文件中找到有效片段：{path}")
    return segments


def save_project(
    path: Path,
    segments: Iterable[TranscriptSegment],
    source_srt: Path,
    target_language: str,
    model: str,
) -> None:
    payload = {
        "version": 2,
        "source_srt": str(source_srt),
        "target_language": target_language,
        "ai_model": model,
        "segments": [asdict(segment) for segment in segments],
    }
    part = path.with_suffix(path.suffix + ".part")
    part.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    part.replace(path)


def load_project(path: Path) -> list[TranscriptSegment]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [TranscriptSegment(**item) for item in payload.get("segments", [])]


def merge_existing_results(
    current: list[TranscriptSegment], existing: Iterable[TranscriptSegment]
) -> None:
    by_id = {segment.id: segment for segment in existing}
    for segment in current:
        previous = by_id.get(segment.id)
        if previous and previous.original_arabic == segment.original_arabic:
            segment.corrected_arabic = previous.corrected_arabic
            segment.diacritized_arabic = previous.diacritized_arabic
            segment.translation = previous.translation
            segment.diacritized_source = previous.diacritized_source or (
                previous.original_arabic if previous.diacritized_arabic else ""
            )
            segment.translation_source = previous.translation_source or (
                previous.original_arabic if previous.translation else ""
            )


class DeepSeekProvider:
    def __init__(self, settings: AISettings, timeout: int = 120) -> None:
        self.settings = settings
        self.timeout = timeout

    def _endpoint(self) -> str:
        return self.settings.base_url.rstrip("/") + "/chat/completions"

    def test_connection(self) -> None:
        payload = {
            "model": self.settings.model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "thinking": {"type": "disabled"},
            "max_tokens": 8,
        }
        self._request(payload)

    def process_batch(
        self,
        segments: list[TranscriptSegment],
        correct: bool,
        translate: bool,
        diacritize: bool,
        target_language: str,
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        requested_fields = []
        if correct:
            requested_fields.append("corrected_arabic")
        if diacritize:
            requested_fields.append("diacritized_arabic")
        if translate:
            requested_fields.append("translation")

        system_prompt = (
            "You process Arabic transcript segments. Return JSON only. Preserve every numeric id and "
            "never merge, split, omit, reorder, or invent segments. Do not alter timestamps because they "
            "are not provided. Preserve proper names and meaning. When correction is requested, fix only "
            "clear ASR errors, incorrectly joined or separated words, spelling, punctuation, and obvious "
            "segment-boundary artifacts using neighboring context. Never summarize, paraphrase, censor, "
            "add facts, or change the speaker's meaning. When diacritization is requested, add Arabic "
            "tashkeel to the corrected Arabic when correction is requested, otherwise to the supplied Arabic. "
            "Translation must likewise use the corrected Arabic when correction is requested. "
            "Return an object with a segments array. Each item must contain id and exactly the requested "
            f"result fields: {', '.join(requested_fields)}."
        )
        task_parts = []
        if correct:
            task_parts.append("correct clear Arabic ASR transcription errors")
        if diacritize:
            task_parts.append("add Arabic tashkeel/harakat")
        if translate:
            task_parts.append(f"translate into {target_language}")
        input_segments = []
        for segment in segments:
            source = segment.original_arabic if correct else (segment.corrected_arabic or segment.original_arabic)
            input_segments.append({"id": segment.id, "arabic": source})
        user_prompt = json.dumps(
            {
                "task": " and ".join(task_parts),
                "segments": input_segments,
                "output_example": {
                    "segments": [
                        {
                            "id": 1,
                            **({"corrected_arabic": "النص المصحح"} if correct else {}),
                            **({"diacritized_arabic": "النَّصُّ"} if diacritize else {}),
                            **({"translation": "translation"} if translate else {}),
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 8192,
        }
        response = self._request(payload)
        try:
            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)
            result_segments = result["segments"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("AI 返回的数据格式无效，请重试。") from exc
        if not isinstance(result_segments, list):
            raise AIProviderError("AI 返回的数据中缺少 segments 列表。")
        return result_segments, response.get("usage", {})

    def _request(self, payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ArabicAudioTranscriber/2.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code == 401:
                raise AIProviderError("API Key 无效或没有权限。") from exc
            if exc.code == 402:
                raise AIProviderError("API 账户余额不足。") from exc
            if exc.code == 429:
                raise AIProviderError("API 请求过于频繁，请稍后重试。") from exc
            raise AIProviderError(f"API 请求失败（HTTP {exc.code}）：{detail}") from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"无法连接 AI 服务：{exc.reason}") from exc
        except (TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError("AI 服务响应超时或返回了无效数据。") from exc


def process_transcript(
    source_srt: Path,
    output_dir: Path,
    settings: AISettings,
    translate: bool,
    diacritize: bool,
    target_language: str,
    correct: bool = False,
    batch_size: int = 25,
    progress: Optional[AIProgressCallback] = None,
    log: LogCallback = print,
    cancel_event: Optional[Event] = None,
) -> tuple[list[TranscriptSegment], AIUsage, Path]:
    if not correct and not translate and not diacritize:
        raise ValueError("请至少选择文本矫正、翻译或阿语标音中的一项。")
    if not settings.api_key.strip():
        raise ValueError("请先配置 API Key。")

    segments = parse_srt(source_srt)
    project_path = output_dir / f"{source_srt.stem}.transcriber.json"
    if project_path.exists():
        try:
            merge_existing_results(segments, load_project(project_path))
            log("已载入此前保存的 AI 处理进度。")
        except Exception:
            log("旧项目文件无法读取，将从当前字幕重新开始。")

    groups: dict[tuple[bool, bool, bool], list[TranscriptSegment]] = {}
    for segment in segments:
        current_source = segment.corrected_arabic or segment.original_arabic
        needs_correction = correct and not segment.corrected_arabic
        needs_translation = translate and (
            not segment.translation
            or segment.translation_source != current_source
            or needs_correction
        )
        needs_diacritization = diacritize and (
            not segment.diacritized_arabic
            or segment.diacritized_source != current_source
            or needs_correction
        )
        if needs_correction or needs_translation or needs_diacritization:
            groups.setdefault(
                (needs_correction, needs_translation, needs_diacritization), []
            ).append(segment)

    usage = AIUsage()
    provider = DeepSeekProvider(settings)
    total = sum(len(group) for group in groups.values())
    completed = 0

    if not groups:
        log("所选 AI 任务已经全部完成，无需重复消耗 token。")
    for (batch_correct, batch_translate, batch_diacritize), pending in groups.items():
        for offset in range(0, len(pending), batch_size):
            if cancel_event and cancel_event.is_set():
                raise AIProcessingCancelled("AI 处理已取消，已完成的结果已经保存。")
            batch = pending[offset : offset + batch_size]
            log(f"正在处理第 {completed + 1}–{completed + len(batch)} / {total} 段…")

            last_error: Optional[Exception] = None
            for attempt in range(1, 3):
                try:
                    results, batch_usage = provider.process_batch(
                        batch, batch_correct, batch_translate, batch_diacritize, target_language
                    )
                    break
                except AIProviderError as exc:
                    last_error = exc
                    if attempt == 2:
                        raise
                    log(f"本批请求失败，2 秒后自动重试：{exc}")
                    time.sleep(2)
            else:  # pragma: no cover
                raise AIProviderError(str(last_error))

            by_id = {segment.id: segment for segment in batch}
            valid_ids: set[int] = set()
            for item in results:
                try:
                    segment_id = int(item["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                segment = by_id.get(segment_id)
                if not segment:
                    continue
                corrected = str(item.get("corrected_arabic", "")).strip()
                diacritized = str(item.get("diacritized_arabic", "")).strip()
                translated = str(item.get("translation", "")).strip()
                if batch_correct and not corrected:
                    continue
                if batch_diacritize and not diacritized:
                    continue
                if batch_translate and not translated:
                    continue
                if batch_correct:
                    segment.corrected_arabic = corrected
                result_source = segment.corrected_arabic or segment.original_arabic
                if batch_diacritize:
                    segment.diacritized_arabic = diacritized
                    segment.diacritized_source = result_source
                if batch_translate:
                    segment.translation = translated
                    segment.translation_source = result_source
                valid_ids.add(segment_id)

            missing = [segment.id for segment in batch if segment.id not in valid_ids]
            if missing:
                raise AIProviderError(f"AI 未完整返回部分字幕片段：{missing[:8]}。请重试。")
            usage.add(batch_usage)
            completed += len(batch)
            save_project(project_path, segments, source_srt, target_language, settings.model)
            if progress:
                progress(completed, total)

    save_project(project_path, segments, source_srt, target_language, settings.model)
    export_ai_results(output_dir, source_srt.stem, segments, correct, translate, diacritize)
    return segments, usage, project_path


def _write_srt(path: Path, segments: Iterable[TranscriptSegment], text_getter: Callable[[TranscriptSegment], str]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        index = 0
        for segment in segments:
            text = text_getter(segment).strip()
            if not text:
                continue
            index += 1
            handle.write(f"{index}\n")
            handle.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
            handle.write(text + "\n\n")


def _write_txt(path: Path, segments: Iterable[TranscriptSegment], text_getter: Callable[[TranscriptSegment], str]) -> None:
    lines = [text_getter(segment).strip() for segment in segments]
    path.write_text("\n".join(line for line in lines if line) + "\n", encoding="utf-8")


def export_ai_results(
    output_dir: Path,
    stem: str,
    segments: list[TranscriptSegment],
    correct: bool,
    translate: bool,
    diacritize: bool,
) -> list[Path]:
    created: list[Path] = []
    if correct or any(segment.corrected_arabic for segment in segments):
        txt = output_dir / f"{stem}_ar_corrected.txt"
        srt = output_dir / f"{stem}_ar_corrected.srt"
        getter = lambda segment: segment.corrected_arabic
        _write_txt(txt, segments, getter)
        _write_srt(srt, segments, getter)
        created.extend((txt, srt))
    if diacritize:
        txt = output_dir / f"{stem}_ar_diacritized.txt"
        srt = output_dir / f"{stem}_ar_diacritized.srt"
        getter = lambda segment: segment.diacritized_arabic
        _write_txt(txt, segments, getter)
        _write_srt(srt, segments, getter)
        created.extend((txt, srt))
    if translate:
        txt = output_dir / f"{stem}_translated.txt"
        srt = output_dir / f"{stem}_translated.srt"
        _write_txt(txt, segments, lambda segment: segment.translation)
        _write_srt(srt, segments, lambda segment: segment.translation)
        created.extend((txt, srt))

        bilingual = output_dir / f"{stem}_bilingual.srt"
        _write_srt(
            bilingual,
            segments,
            lambda segment: "\n".join(
                filter(
                    None,
                    (
                        segment.diacritized_arabic
                        or segment.corrected_arabic
                        or segment.original_arabic,
                        segment.translation,
                    ),
                )
            ),
        )
        created.append(bilingual)
    return created
