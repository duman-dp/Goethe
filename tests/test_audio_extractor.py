import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules.audio_extractor import AudioExtractor
from modules.errors import ExtractionError
from modules.sentence_matcher import Match, make_match_id


def make_match(video_path, term="Ich heiße", start=10.0, end=11.0):
    video_path = Path(video_path)
    return Match(
        id=make_match_id(video_path.stem, "ich heisse", start, end),
        term=term,
        video=video_path.stem,
        video_path=str(video_path),
        start=start,
        end=end,
        matched_text="Ich heiße",
        context="Hallo, ich heiße Anna.",
        score=100.0,
        exact=True,
        word_count=2,
    )


class FakeFfmpeg:
    """Replaces subprocess.run: writes the output file (last argument) like ffmpeg would."""

    def __init__(self, returncode=0, stderr="", write_output=True):
        self.calls = []
        self.kwargs = []
        self.returncode = returncode
        self.stderr = stderr
        self.write_output = write_output

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        self.kwargs.append(kwargs)
        if self.write_output:
            Path(command[-1]).write_bytes(b"ID3fake-mp3-data")
        return subprocess.CompletedProcess(command, self.returncode, stdout="", stderr=self.stderr)


class AudioExtractorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mp3_folder = self.root / "mp3"
        self.video_a = self.root / "Lektion 1.mp4"
        self.video_b = self.root / "Lektion 2.mkv"
        self.video_a.write_bytes(b"video")
        self.video_b.write_bytes(b"video")
        self.extractor = AudioExtractor(padding_before=0.03, padding_after=0.03, bitrate=192, ffmpeg="ffmpeg")

    def tearDown(self):
        self._tmp.cleanup()

    def run_extract(self, matches, fake=None):
        fake = fake or FakeFfmpeg()
        with mock.patch("modules.audio_extractor.subprocess.run", fake):
            result = self.extractor.extract_all(matches, self.mp3_folder)
        return result, fake

    def test_missing_ffmpeg_gives_clear_error(self):
        with mock.patch("modules.audio_extractor.shutil.which", return_value=None):
            with self.assertRaises(ExtractionError) as context:
                AudioExtractor()
        self.assertIn("ffmpeg", str(context.exception))

    def test_same_term_and_time_in_two_videos_do_not_collide(self):
        matches = [make_match(self.video_a), make_match(self.video_b)]
        result, _ = self.run_extract(matches)
        self.assertEqual(len(result.created), 2)
        self.assertEqual(len({p.name for p in result.created}), 2)
        self.assertEqual(len(result.failed), 0)
        for path in result.created:
            self.assertTrue(path.is_file())

    def test_filename_contains_term_video_time_and_id(self):
        match = make_match(self.video_a, start=135.2)
        result, _ = self.run_extract([match])
        path = result.created[0]
        self.assertEqual(path.parent.name, "Ich_heisse")
        self.assertEqual(path.name, f"Ich_heisse__Lektion_1__00h02m15s_{match.id}.mp3")

    def test_ffmpeg_command_is_argument_list_with_padding(self):
        _, fake = self.run_extract([make_match(self.video_a, start=10.0, end=11.0)])
        command = fake.calls[0]
        self.assertIsInstance(command, list)
        self.assertNotIn("shell", fake.kwargs[0])
        self.assertEqual(command[command.index("-ss") + 1], "9.970")
        self.assertEqual(command[command.index("-t") + 1], "1.060")
        self.assertEqual(command[command.index("-b:a") + 1], "192k")
        self.assertEqual(command[command.index("-i") + 1], str(self.video_a))
        self.assertIn("-vn", command)

    def test_start_is_never_negative(self):
        _, fake = self.run_extract([make_match(self.video_a, start=0.01, end=0.5)])
        command = fake.calls[0]
        self.assertEqual(command[command.index("-ss") + 1], "0.000")

    def test_existing_clips_are_skipped(self):
        matches = [make_match(self.video_a)]
        first, _ = self.run_extract(matches)
        second, fake = self.run_extract(matches)
        self.assertEqual(len(first.created), 1)
        self.assertEqual(len(second.created), 0)
        self.assertEqual(len(second.skipped), 1)
        self.assertEqual(fake.calls, [])

    def test_ffmpeg_failure_is_reported_and_leaves_no_files(self):
        fake = FakeFfmpeg(returncode=1, stderr="line one\nInvalid data found\n")
        result, _ = self.run_extract([make_match(self.video_a)], fake)
        self.assertEqual(result.created, [])
        self.assertEqual(len(result.failed), 1)
        message = result.failed[0][1]
        self.assertIn("code 1", message)
        self.assertIn("Invalid data found", message)
        self.assertEqual(list(self.mp3_folder.rglob("*.mp3")), [])

    def test_empty_output_counts_as_failure(self):
        fake = FakeFfmpeg(returncode=0, write_output=False)
        result, _ = self.run_extract([make_match(self.video_a)], fake)
        self.assertEqual(len(result.failed), 1)
        self.assertEqual(result.created, [])

    def test_missing_video_fails_clearly_without_running_ffmpeg(self):
        missing = self.root / "gone.mp4"
        matches = [make_match(missing), make_match(missing, start=20.0, end=21.0)]
        result, fake = self.run_extract(matches)
        self.assertEqual(fake.calls, [])
        self.assertEqual(len(result.failed), 2)
        self.assertIn("video not found", result.failed[0][1])

    def test_one_bad_clip_does_not_stop_the_others(self):
        missing = self.root / "gone.mp4"
        matches = [make_match(missing), make_match(self.video_a)]
        result, _ = self.run_extract(matches)
        self.assertEqual(len(result.created), 1)
        self.assertEqual(len(result.failed), 1)

    def test_timeout_is_reported(self):
        def raise_timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 1)

        with mock.patch("modules.audio_extractor.subprocess.run", raise_timeout):
            result = self.extractor.extract_all([make_match(self.video_a)], self.mp3_folder)
        self.assertEqual(len(result.failed), 1)
        self.assertIn("timed out", result.failed[0][1])

    def test_different_terms_with_same_sanitized_name_get_separate_folders(self):
        matches = [
            make_match(self.video_a, term="Äpfel", start=1.0, end=2.0),
            make_match(self.video_a, term="Aepfel", start=3.0, end=4.0),
        ]
        result, _ = self.run_extract(matches)
        self.assertEqual({p.parent.name for p in result.created}, {"Aepfel", "Aepfel_2"})


if __name__ == "__main__":
    unittest.main()
