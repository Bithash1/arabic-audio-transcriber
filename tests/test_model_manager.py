import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import model_manager


def make_valid_model(path: Path) -> None:
    path.mkdir(parents=True)
    for name in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
        (path / name).write_bytes(b"test")


class ModelManagerTests(unittest.TestCase):
    def test_installed_model_is_detected_in_default_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            snapshot = cache / "snapshot"
            make_valid_model(snapshot)
            with (
                mock.patch.object(model_manager, "default_cache_dir", return_value=cache),
                mock.patch.object(
                    model_manager,
                    "resolve_faster_whisper_model",
                    return_value=str(snapshot),
                ),
            ):
                status = model_manager.inspect_model("small")

        self.assertEqual(status.state, model_manager.ModelState.INSTALLED)
        self.assertEqual(status.path, snapshot.resolve())

    def test_deleted_or_incomplete_model_is_not_marked_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            repo = cache / "models--Systran--faster-whisper-small"
            repo.mkdir()
            with (
                mock.patch.object(model_manager, "default_cache_dir", return_value=cache),
                mock.patch.object(
                    model_manager,
                    "resolve_faster_whisper_model",
                    side_effect=OSError("missing model.bin"),
                ),
            ):
                status = model_manager.inspect_model("small")

        self.assertEqual(status.state, model_manager.ModelState.INCOMPLETE)

    def test_missing_custom_storage_is_reported_without_default_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing_custom = root / "external-disk" / "models"
            default = root / "default"
            default.mkdir()
            with (
                mock.patch.object(model_manager, "default_cache_dir", return_value=default),
                mock.patch.object(
                    model_manager,
                    "resolve_faster_whisper_model",
                    side_effect=OSError("not cached"),
                ),
            ):
                status = model_manager.inspect_model("medium", str(missing_custom))

        self.assertEqual(status.state, model_manager.ModelState.STORAGE_UNAVAILABLE)
        self.assertEqual(status.cache_dir, missing_custom)

    def test_download_reports_completion_and_validates_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            snapshot = cache / "snapshot"
            progress = []

            def fake_snapshot_download(_repo_id, **kwargs):
                if kwargs.get("dry_run"):
                    return []
                make_valid_model(snapshot)
                return str(snapshot)

            with mock.patch.object(
                model_manager,
                "snapshot_download",
                side_effect=fake_snapshot_download,
            ):
                result = model_manager.download_model_with_progress(
                    "medium",
                    cache,
                    progress=progress.append,
                )

        self.assertEqual(result, snapshot.resolve())
        self.assertEqual(progress, [0.0, 100.0])

    def test_progress_adapter_reports_percentage_and_honors_cancellation(self):
        values = []
        cancelled = threading.Event()
        progress_class = model_manager._progress_class(200, values.append, cancelled)
        bar = progress_class(total=200, desc="Reconstructing model")
        bar.update(50)
        self.assertEqual(values, [25.0])

        cancelled.set()
        with self.assertRaises(model_manager.ModelDownloadCancelled):
            bar.update(1)


if __name__ == "__main__":
    unittest.main()
