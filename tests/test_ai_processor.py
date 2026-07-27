import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


if "faster_whisper" not in sys.modules:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = object
        sys.modules["faster_whisper"] = fake_module

import ai_processor


SAMPLE_SRT = """1
00:00:00,000 --> 00:00:01,200
ذهب الطالب

2
00:00:01,200 --> 00:00:03,000
إلى الجامعة
في الصباح

"""


class AIProcessorTests(unittest.TestCase):
    def test_parse_srt_preserves_multiline_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.srt"
            path.write_text(SAMPLE_SRT, encoding="utf-8")
            segments = ai_processor.parse_srt(path)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[1].original_arabic, "إلى الجامعة\nفي الصباح")
        self.assertEqual(segments[1].end, 3.0)

    def test_processing_exports_translation_diacritics_and_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            srt = root / "lesson.srt"
            srt.write_text(SAMPLE_SRT, encoding="utf-8")

            class FakeProvider:
                calls = []

                def __init__(self, _settings):
                    pass

                def process_batch(self, segments, correct, translate, diacritize, _language):
                    self.calls.append((correct, translate, diacritize, [item.id for item in segments]))
                    return [
                        {
                            "id": item.id,
                            "corrected_arabic": f"نص مصحح {item.id}",
                            "translation": f"译文 {item.id}",
                            "diacritized_arabic": f"مُشَكَّل {item.id}",
                        }
                        for item in segments
                    ], {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16}

            with mock.patch.object(ai_processor, "DeepSeekProvider", FakeProvider):
                segments, usage, project = ai_processor.process_transcript(
                    source_srt=srt,
                    output_dir=root,
                    settings=ai_processor.AISettings(api_key="test"),
                    correct=True,
                    translate=True,
                    diacritize=True,
                    target_language="简体中文",
                    batch_size=25,
                )

            self.assertEqual(len(segments), 2)
            self.assertEqual(usage.total_tokens, 16)
            self.assertTrue(project.exists())
            self.assertTrue((root / "lesson_ar_corrected.srt").exists())
            self.assertTrue((root / "lesson_ar_diacritized.srt").exists())
            self.assertTrue((root / "lesson_translated.srt").exists())
            bilingual = (root / "lesson_bilingual.srt").read_text(encoding="utf-8")
            self.assertIn("مُشَكَّل 1\n译文 1", bilingual)

    def test_existing_translation_is_not_requested_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            srt = root / "lesson.srt"
            srt.write_text(SAMPLE_SRT, encoding="utf-8")
            existing = ai_processor.parse_srt(srt)
            for segment in existing:
                segment.translation = f"已有译文 {segment.id}"
            project = root / "lesson.transcriber.json"
            ai_processor.save_project(project, existing, srt, "简体中文", "old-model")

            calls = []

            class FakeProvider:
                def __init__(self, _settings):
                    pass

                def process_batch(self, segments, correct, translate, diacritize, _language):
                    calls.append((correct, translate, diacritize))
                    return [
                        {"id": item.id, "diacritized_arabic": f"مُشَكَّل {item.id}"}
                        for item in segments
                    ], {}

            with mock.patch.object(ai_processor, "DeepSeekProvider", FakeProvider):
                result, _, _ = ai_processor.process_transcript(
                    source_srt=srt,
                    output_dir=root,
                    settings=ai_processor.AISettings(api_key="test"),
                    translate=True,
                    diacritize=True,
                    target_language="简体中文",
                )

            self.assertEqual(calls, [(False, False, True)])
            self.assertEqual(result[0].translation, "已有译文 1")

    def test_correction_recomputes_selected_downstream_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            srt = root / "lesson.srt"
            srt.write_text(SAMPLE_SRT, encoding="utf-8")
            existing = ai_processor.parse_srt(srt)
            for segment in existing:
                segment.translation = f"旧译文 {segment.id}"
                segment.translation_source = segment.original_arabic
            ai_processor.save_project(
                root / "lesson.transcriber.json",
                existing,
                srt,
                "简体中文",
                "old-model",
            )

            class FakeProvider:
                def __init__(self, _settings):
                    pass

                def process_batch(self, segments, correct, translate, diacritize, _language):
                    self.assertions = (correct, translate, diacritize)
                    return [
                        {
                            "id": item.id,
                            "corrected_arabic": f"النص المصحح {item.id}",
                            "translation": f"新译文 {item.id}",
                        }
                        for item in segments
                    ], {}

            with mock.patch.object(ai_processor, "DeepSeekProvider", FakeProvider):
                result, _, _ = ai_processor.process_transcript(
                    source_srt=srt,
                    output_dir=root,
                    settings=ai_processor.AISettings(api_key="test"),
                    correct=True,
                    translate=True,
                    diacritize=False,
                    target_language="简体中文",
                )

            self.assertEqual(result[0].corrected_arabic, "النص المصحح 1")
            self.assertEqual(result[0].translation, "新译文 1")
            self.assertEqual(result[0].translation_source, "النص المصحح 1")


if __name__ == "__main__":
    unittest.main()
