import tempfile
import unittest
from pathlib import Path

from modules.config import (
    DEFAULT_CONFIG_YAML,
    LANGUAGES,
    PROJECT_ROOT,
    load_config,
    parse_config,
    resolve_language,
)
from modules.errors import ConfigError
from modules.speech_recognition import find_videos, transcript_path_for


class DefaultsTests(unittest.TestCase):
    def test_shipped_config_file_matches_the_built_in_default_text(self):
        shipped = (PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8")
        self.assertEqual(shipped, DEFAULT_CONFIG_YAML)

    def test_default_text_parses_to_documented_defaults(self):
        import yaml

        config = parse_config(yaml.safe_load(DEFAULT_CONFIG_YAML), PROJECT_ROOT)
        self.assertEqual(config.speech.language_code, "de")
        self.assertEqual(config.speech.model_size, "small")
        self.assertEqual(config.matching.fuzzy_threshold, 100)
        self.assertEqual(config.video_formats, ["mp4", "mkv", "avi", "mov"])
        self.assertEqual(config.warnings, [])

    def test_empty_config_uses_defaults(self):
        config = parse_config(None, PROJECT_ROOT)
        self.assertEqual(config.audio.bitrate, 192)
        self.assertEqual(config.paths.videos, (PROJECT_ROOT / "videos").resolve())

    def test_every_supported_language_resolves(self):
        for code, name in LANGUAGES.items():
            self.assertEqual(resolve_language(code), (code, name))
            self.assertEqual(resolve_language(name), (code, name))
            self.assertEqual(resolve_language(name.upper()), (code, name))
        for name in ("German", "English", "French", "Spanish", "Italian", "Portuguese", "Chinese"):
            self.assertIn(name, LANGUAGES.values())


class ValidationTests(unittest.TestCase):
    def assert_invalid(self, raw, fragment):
        with self.assertRaises(ConfigError) as context:
            parse_config(raw, PROJECT_ROOT)
        self.assertIn(fragment, str(context.exception))

    def test_unknown_language_lists_supported_languages(self):
        self.assert_invalid({"speech": {"language": "Klingon"}}, "Supported")
        self.assert_invalid({"speech": {"language": 42}}, "speech.language")

    def test_language_other_spellings(self):
        config = parse_config({"speech": {"language": "Deutsch"}}, PROJECT_ROOT)
        self.assertEqual(config.speech.language_code, "de")
        config = parse_config({"speech": {"language": "fr"}}, PROJECT_ROOT)
        self.assertEqual(config.speech.language_name, "French")

    def test_invalid_numbers(self):
        self.assert_invalid({"audio": {"bitrate": "high"}}, "audio.bitrate")
        self.assert_invalid({"audio": {"bitrate": 10}}, "between")
        self.assert_invalid({"audio": {"padding_before": -1}}, "audio.padding_before")
        self.assert_invalid({"audio": {"bitrate": 192.5}}, "whole number")
        self.assert_invalid({"matching": {"fuzzy_threshold": 0}}, "matching.fuzzy_threshold")
        self.assert_invalid({"matching": {"fuzzy_threshold": 150}}, "matching.fuzzy_threshold")
        self.assert_invalid({"audio": {"bitrate": True}}, "audio.bitrate")

    def test_invalid_speech_settings(self):
        self.assert_invalid({"speech": {"model_size": "gigantic"}}, "model_size")
        self.assert_invalid({"speech": {"device": "tpu"}}, "speech.device")
        self.assert_invalid({"speech": {"quiet": "yes please"}}, "speech.quiet")

    def test_large_is_an_alias_for_large_v3(self):
        config = parse_config({"speech": {"model_size": "large"}}, PROJECT_ROOT)
        self.assertEqual(config.speech.model_size, "large-v3")

    def test_section_must_be_a_mapping(self):
        self.assert_invalid({"audio": ["a", "b"]}, "'audio'")
        self.assert_invalid(["just", "a", "list"], "key: value")

    def test_video_formats(self):
        config = parse_config({"video_formats": [".MP4", "webm", "mp4"]}, PROJECT_ROOT)
        self.assertEqual(config.video_formats, ["mp4", "webm"])
        self.assert_invalid({"video_formats": []}, "video_formats")
        self.assert_invalid({"video_formats": "mp4"}, "video_formats")
        self.assert_invalid({"video_formats": [5]}, "video_formats")

    def test_unknown_settings_only_warn(self):
        config = parse_config({"audio": {"output_format": "mp3"}, "colour": "red"}, PROJECT_ROOT)
        joined = " ".join(config.warnings)
        self.assertIn("audio.output_format", joined)
        self.assertIn("colour", joined)

    def test_relative_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = parse_config({"paths": {"videos": "./clips", "output": str(root / "elsewhere")}}, root)
            self.assertEqual(config.paths.videos, root / "clips")
            self.assertEqual(config.paths.output, root / "elsewhere")
            self.assertEqual(config.mp3_folder, root / "elsewhere" / "mp3")


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file(self):
        with self.assertRaises(ConfigError) as context:
            load_config(root=self.root)
        self.assertIn("not found", str(context.exception))

    def test_invalid_yaml(self):
        (self.root / "config.yaml").write_text("audio: [unclosed\n  bitrate: : :", encoding="utf-8")
        with self.assertRaises(ConfigError) as context:
            load_config(root=self.root)
        self.assertIn("not valid YAML", str(context.exception))

    def test_ensure_folders_creates_everything(self):
        (self.root / "config.yaml").write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        config = load_config(root=self.root)
        config.ensure_folders()
        for name in ("videos", "transcripts", "output", "logs"):
            self.assertTrue((self.root / name).is_dir(), name)
        self.assertTrue((self.root / "output" / "mp3").is_dir())


class FindVideosTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, *names):
        for name in names:
            (self.folder / name).write_bytes(b"x")

    def test_all_configured_formats_including_mov(self):
        self.touch("a.mp4", "b.mkv", "c.avi", "d.mov", "notes.txt", "e.mp3")
        videos, duplicates = find_videos(self.folder, ["mp4", "mkv", "avi", "mov"])
        self.assertEqual([v.name for v in videos], ["a.mp4", "b.mkv", "c.avi", "d.mov"])
        self.assertEqual(duplicates, [])

    def test_formats_come_from_the_argument_not_a_fixed_list(self):
        self.touch("a.mp4", "b.webm")
        videos, _ = find_videos(self.folder, ["webm"])
        self.assertEqual([v.name for v in videos], ["b.webm"])

    def test_extension_matching_is_case_insensitive(self):
        self.touch("Lesson.MOV")
        videos, _ = find_videos(self.folder, ["mov"])
        self.assertEqual(len(videos), 1)

    def test_hidden_files_are_ignored(self):
        self.touch("._a.mp4", "b.mp4")
        videos, _ = find_videos(self.folder, ["mp4"])
        self.assertEqual([v.name for v in videos], ["b.mp4"])

    def test_same_stem_is_reported_as_duplicate(self):
        self.touch("lesson.mp4", "lesson.mkv")
        videos, duplicates = find_videos(self.folder, ["mp4", "mkv"])
        self.assertEqual(len(videos), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0][0].stem, duplicates[0][1].stem)

    def test_missing_folder(self):
        self.assertEqual(find_videos(self.folder / "nope", ["mp4"]), ([], []))

    def test_transcript_path_uses_stem(self):
        path = transcript_path_for(Path("transcripts"), Path("videos/Lektion 1.mp4"))
        self.assertEqual(path, Path("transcripts/Lektion 1.json"))


if __name__ == "__main__":
    unittest.main()
