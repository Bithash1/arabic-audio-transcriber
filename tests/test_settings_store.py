import tempfile
import unittest
from pathlib import Path

import settings_store


class SettingsStoreTests(unittest.TestCase):
    def test_non_secret_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            expected = settings_store.StoredAISettings(
                base_url="https://example.com/v1",
                model="example-model",
                remember_key=True,
                model_cache_dir="/Volumes/Models/whisper",
            )
            settings_store.save_settings(expected, path)
            actual = settings_store.load_settings(path)
            content = path.read_text(encoding="utf-8")

        self.assertEqual(actual, expected)
        self.assertNotIn("api_key", content)


if __name__ == "__main__":
    unittest.main()
