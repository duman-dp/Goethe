import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from modules.config import PROJECT_ROOT, SpeechConfig
from modules.errors import SpeechError
from modules.speech_recognition import SpeechRecognizer, save_transcript


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        words = [
            SimpleNamespace(start=0.0, end=0.4, word=" Hallo"),
            SimpleNamespace(start=0.5, end=0.9, word=" Welt"),
        ]
        segment = SimpleNamespace(start=0.0, end=1.0, text=" Hallo Welt", words=words)
        silent = SimpleNamespace(start=1.0, end=2.0, text="", words=None)
        return iter([segment, silent]), SimpleNamespace(duration=2.0)


def recognizer_with(language_code="de", language_name="German"):
    settings = SpeechConfig(language_code=language_code, language_name=language_name, quiet=True)
    recognizer = SpeechRecognizer(settings)
    recognizer._model = FakeModel()  # no real Whisper model is needed in tests
    return recognizer


class SpeechRecognizerTests(unittest.TestCase):
    def test_configured_language_is_passed_to_whisper(self):
        for code, name in (("de", "German"), ("fr", "French"), ("zh", "Chinese")):
            recognizer = recognizer_with(code, name)
            recognizer.transcribe_video(Path("video.mp4"))
            _, kwargs = recognizer._model.calls[0]
            self.assertEqual(kwargs["language"], code)
            self.assertTrue(kwargs["word_timestamps"])

    def test_transcript_structure(self):
        transcript = recognizer_with().transcribe_video(Path("/data/videos/Lektion 1.mp4"))
        self.assertEqual(transcript["version"], 2)
        self.assertEqual(transcript["video_name"], "Lektion 1.mp4")
        self.assertEqual(transcript["video_path"], str(Path("/data/videos/Lektion 1.mp4")))
        self.assertEqual(transcript["language"], "de")
        self.assertEqual(len(transcript["segments"]), 2)
        self.assertEqual(transcript["segments"][0]["words"][1]["word"], " Welt")
        self.assertEqual(transcript["segments"][1]["words"], [])  # segment without words

    def test_creating_a_recognizer_does_not_load_anything(self):
        recognizer = SpeechRecognizer(SpeechConfig(quiet=True))
        self.assertIsNone(recognizer._model)

    def test_importing_modules_does_not_import_faster_whisper(self):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "import modules.speech_recognition, modules.setup, modules.audio_extractor;"
            "assert 'faster_whisper' not in sys.modules"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code, str(PROJECT_ROOT)], capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_compute_type_follows_device(self):
        self.assertEqual(SpeechRecognizer(SpeechConfig(device="cpu")).compute_type, "int8")
        self.assertEqual(SpeechRecognizer(SpeechConfig(device="cuda")).compute_type, "float16")
        self.assertEqual(SpeechRecognizer(SpeechConfig(device="auto")).compute_type, "default")

    def test_transcription_error_is_wrapped(self):
        recognizer = recognizer_with()

        def broken(path, **kwargs):
            raise RuntimeError("no audio stream")

        recognizer._model.transcribe = broken
        with self.assertRaises(SpeechError) as context:
            recognizer.transcribe_video(Path("broken.mp4"))
        self.assertIn("broken.mp4", str(context.exception))
        self.assertIn("no audio stream", str(context.exception))


class SaveTranscriptTests(unittest.TestCase):
    def test_roundtrip_keeps_umlauts_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sub" / "lektion.json"
            save_transcript({"segments": [{"text": "Grüße aus Köln"}]}, path)
            self.assertIn("Grüße", path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["segments"][0]["text"], "Grüße aus Köln")
            self.assertEqual([p.name for p in path.parent.iterdir()], ["lektion.json"])


if __name__ == "__main__":
    unittest.main()
