import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


# Core output tests do not load a real model, so keep them runnable before the
# optional, heavyweight runtime dependency has been installed.
if "faster_whisper" not in sys.modules:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = object
        sys.modules["faster_whisper"] = fake_module

import app


class AppTests(unittest.TestCase):
    def test_format_timestamp(self):
        self.assertEqual(app.format_timestamp(3661.2349), "01:01:01,234")

    def test_resolve_default_output_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "lesson.mp3"
            result = app.resolve_output_dir(media, None)
            self.assertEqual(result, root / "lesson_transcript")
            self.assertTrue(result.is_dir())

    def test_transcribe_writes_txt_and_contiguous_srt_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "lesson.mp3"
            media.touch()
            output = root / "output"
            output.mkdir()
            segments = [
                SimpleNamespace(start=0.0, end=1.2, text=" مرحبا "),
                SimpleNamespace(start=1.2, end=1.4, text="  "),
                SimpleNamespace(start=1.4, end=2.0, text=" بالعالم "),
            ]
            info = SimpleNamespace(duration=2.0, language="ar")

            class FakeModel:
                def transcribe(self, *_args, **_kwargs):
                    return iter(segments), info

            progress = []
            with mock.patch.object(
                app,
                "load_model_with_fallback",
                return_value=(FakeModel(), "cpu", "int8"),
            ):
                txt, srt, returned_info = app.transcribe_file(
                    media,
                    output,
                    "small",
                    "ar",
                    "cpu",
                    "int8",
                    5,
                    True,
                    log=lambda _text: None,
                    progress=lambda current, total: progress.append((current, total)),
                )

            self.assertEqual(txt.read_text(encoding="utf-8"), "مرحبا\nبالعالم\n")
            subtitle = srt.read_text(encoding="utf-8")
            self.assertIn("1\n00:00:00,000 --> 00:00:01,200", subtitle)
            self.assertIn("2\n00:00:01,400 --> 00:00:02,000", subtitle)
            self.assertIs(returned_info, info)
            self.assertEqual(progress[-1], (2.0, 2.0))


if __name__ == "__main__":
    unittest.main()
