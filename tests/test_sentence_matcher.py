import json
import tempfile
import unittest
from pathlib import Path

from modules.errors import SentenceError, TranscriptError
from modules.sentence_matcher import (
    SentenceMatcher,
    load_sentences,
    load_transcript,
    make_match_id,
    normalize_token,
    save_matches,
)


def make_transcript(*segments):
    """Each segment is a list of (word, start, end) tuples."""
    result = []
    for words in segments:
        word_dicts = [{"word": w, "start": s, "end": e} for (w, s, e) in words]
        result.append(
            {
                "start": word_dicts[0]["start"],
                "end": word_dicts[-1]["end"],
                "text": "".join(w["word"] for w in word_dicts),
                "words": word_dicts,
            }
        )
    return {"segments": result}


LESSON = make_transcript(
    [(" Hallo,", 0.0, 0.5), (" ich", 0.6, 0.8), (" heiße", 0.8, 1.3), (" Anna.", 1.4, 1.9)],
    [(" Wie", 3.0, 3.2), (" heißt", 3.2, 3.6), (" du?", 3.6, 3.9)],
)


def find(transcript, text, language="de", threshold=100, video="videos/lesson.mp4"):
    matcher = SentenceMatcher(language, threshold)
    terms = matcher.prepare_terms([text] if isinstance(text, str) else text)
    return matcher.find_in_transcript(transcript, terms, Path(video))


class NormalizeTests(unittest.TestCase):
    def test_case_punctuation_and_eszett(self):
        self.assertEqual(normalize_token(" Heißt, "), "heisst")
        self.assertEqual(normalize_token("HEISST"), "heisst")

    def test_umlauts_are_kept_and_unicode_forms_are_equal(self):
        self.assertEqual(normalize_token("schön"), "schön")
        self.assertEqual(normalize_token("schön"), normalize_token("schön"))

    def test_pure_punctuation_becomes_empty(self):
        self.assertEqual(normalize_token(" ... "), "")


class ExactMatchingTests(unittest.TestCase):
    def test_single_word_with_timestamps(self):
        matches = find(LESSON, "ich")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (0.6, 0.8))
        self.assertTrue(matches[0].exact)
        self.assertEqual(matches[0].score, 100)

    def test_phrase_uses_first_and_last_word_timestamps(self):
        matches = find(LESSON, "Ich heiße")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (0.6, 1.3))
        self.assertEqual(matches[0].word_count, 2)
        self.assertEqual(matches[0].matched_text, "ich heiße")

    def test_punctuation_in_term_and_transcript_is_ignored(self):
        matches = find(LESSON, "Wie heißt du?")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (3.0, 3.9))

    def test_eszett_and_ss_are_equivalent(self):
        self.assertEqual(len(find(LESSON, "wie heisst du")), 1)

    def test_whole_words_only(self):
        transcript = make_transcript([(" Das", 0.0, 0.2), (" mich", 0.3, 0.5), (" ichbin", 0.6, 0.9)])
        self.assertEqual(find(transcript, "ich"), [])

    def test_all_occurrences_are_found(self):
        transcript = make_transcript(
            [(" ich", 0.0, 0.2), (" und", 0.3, 0.4), (" ich", 0.5, 0.7)],
            [(" ich", 5.0, 5.2)],
        )
        matches = find(transcript, "ich")
        self.assertEqual([m.start for m in matches], [0.0, 0.5, 5.0])

    def test_phrase_across_segment_boundary(self):
        transcript = make_transcript(
            [(" Hallo", 0.0, 0.4), (" Wie", 1.0, 1.2)],
            [(" heißt", 1.3, 1.7), (" du", 1.7, 1.9)],
        )
        matches = find(transcript, "Wie heißt du")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (1.0, 1.9))
        self.assertIn("Hallo", matches[0].context)  # context covers both segments

    def test_words_far_apart_do_not_form_a_phrase(self):
        transcript = make_transcript([(" Ich", 0.0, 0.3)], [(" heiße", 10.0, 10.4)])
        self.assertEqual(find(transcript, "Ich heiße"), [])

    def test_decomposed_umlaut_in_transcript_matches_composed_term(self):
        transcript = make_transcript([(" schön", 0.0, 0.4)])
        self.assertEqual(len(find(transcript, "schön")), 1)

    def test_words_that_are_only_punctuation_are_skipped(self):
        transcript = make_transcript([(" Wie", 0.0, 0.2), (" -", 0.2, 0.3), (" geht", 0.3, 0.5)])
        self.assertEqual(len(find(transcript, "Wie geht")), 1)

    def test_malformed_words_are_ignored_not_fatal(self):
        transcript = {
            "segments": [
                {"text": " ich", "words": [{"word": " ich", "start": 0.0, "end": 0.2}, {"word": " x"}]}
            ]
        }
        self.assertEqual(len(find(transcript, "ich")), 1)

    def test_old_transcript_format_still_works(self):
        transcript = dict(LESSON)
        transcript["words"] = []  # extra keys written by older versions
        transcript["video_path"] = "videos/lesson.mp4"
        self.assertEqual(len(find(transcript, "du")), 1)

    def test_empty_transcript(self):
        self.assertEqual(find({"segments": []}, "ich"), [])


class MatchRecordTests(unittest.TestCase):
    def test_record_contains_exact_video_path_and_stem(self):
        match = find(LESSON, "ich", video="/data/videos/Lektion 1.mp4")[0]
        self.assertEqual(match.video_path, str(Path("/data/videos/Lektion 1.mp4")))
        self.assertEqual(match.video, "Lektion 1")

    def test_ids_are_stable_and_differ_between_videos(self):
        first = find(LESSON, "ich", video="videos/a.mp4")[0]
        again = find(LESSON, "ich", video="videos/a.mp4")[0]
        other = find(LESSON, "ich", video="videos/b.mp4")[0]
        self.assertEqual(first.id, again.id)
        self.assertNotEqual(first.id, other.id)

    def test_make_match_id_depends_on_term_and_time(self):
        base = make_match_id("v", "ich", 1.0, 2.0)
        self.assertNotEqual(base, make_match_id("v", "du", 1.0, 2.0))
        self.assertNotEqual(base, make_match_id("v", "ich", 1.5, 2.0))

    def test_save_matches_roundtrip(self):
        matches = find(LESSON, "ich")
        with tempfile.TemporaryDirectory() as folder:
            path = save_matches(matches, Path(folder) / "all_matches.json", "de")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["total_matches"], 1)
        self.assertEqual(data["matches"][0]["id"], matches[0].id)


class FuzzyMatchingTests(unittest.TestCase):
    MISSPELLED = make_transcript([(" Wie", 0.0, 0.2), (" heist", 0.2, 0.5), (" du", 0.5, 0.7)])

    def test_no_fuzzy_matching_by_default(self):
        self.assertEqual(find(self.MISSPELLED, "Wie heißt du"), [])

    def test_fuzzy_fallback_finds_similar_phrase(self):
        matches = find(self.MISSPELLED, "Wie heißt du", threshold=80)
        self.assertEqual(len(matches), 1)
        self.assertFalse(matches[0].exact)
        self.assertGreaterEqual(matches[0].score, 80)
        self.assertLess(matches[0].score, 100)
        self.assertEqual((matches[0].start, matches[0].end), (0.0, 0.7))

    def test_fuzzy_threshold_is_respected(self):
        self.assertEqual(find(self.MISSPELLED, "Wie heißt du", threshold=99), [])

    def test_fuzzy_is_only_a_fallback_when_exact_exists(self):
        transcript = make_transcript(
            [(" Wie", 0.0, 0.2), (" heißt", 0.2, 0.5), (" du", 0.5, 0.7)],
            [(" Wie", 5.0, 5.2), (" heist", 5.2, 5.5), (" du", 5.5, 5.7)],
        )
        matches = find(transcript, "Wie heißt du", threshold=80)
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].exact)

    def test_very_short_terms_are_never_fuzzy(self):
        transcript = make_transcript([(" ach", 0.0, 0.2)])
        self.assertEqual(find(transcript, "ich", threshold=50), [])


class ChineseMatchingTests(unittest.TestCase):
    TRANSCRIPT = make_transcript([("你好", 0.0, 0.5), ("世界", 0.6, 1.1)])

    def test_phrase_without_spaces(self):
        matches = find(self.TRANSCRIPT, "你好世界", language="zh")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (0.0, 1.1))

    def test_characters_inside_words_use_whole_word_timestamps(self):
        matches = find(self.TRANSCRIPT, "好世", language="zh")
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].start, matches[0].end), (0.0, 1.1))


class SearchTermTests(unittest.TestCase):
    def test_duplicates_are_removed(self):
        matcher = SentenceMatcher("de")
        terms = matcher.prepare_terms(["Ich bin", "ich  bin!", "du"])
        self.assertEqual([t.text for t in terms], ["Ich bin", "du"])

    def test_terms_without_letters_are_ignored(self):
        matcher = SentenceMatcher("de")
        terms = matcher.prepare_terms(["???", "du"])
        self.assertEqual([t.text for t in terms], ["du"])

    def test_no_usable_terms_is_an_error(self):
        with self.assertRaises(SentenceError):
            SentenceMatcher("de").prepare_terms(["???", "..."])


class LoadSentencesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_comments_blank_lines_and_bom(self):
        path = self.folder / "sentences.txt"
        path.write_text("﻿# comment\n\nIch heiße\n  du  \n#another\n", encoding="utf-8")
        self.assertEqual(load_sentences(path), ["Ich heiße", "du"])

    def test_missing_file(self):
        with self.assertRaises(SentenceError) as context:
            load_sentences(self.folder / "sentences.txt")
        self.assertIn("not found", str(context.exception))

    def test_empty_list(self):
        path = self.folder / "sentences.txt"
        path.write_text("# only comments\n\n", encoding="utf-8")
        with self.assertRaises(SentenceError) as context:
            load_sentences(path)
        self.assertIn("empty", str(context.exception))

    def test_wrong_encoding(self):
        path = self.folder / "sentences.txt"
        path.write_bytes("Ich heiße".encode("latin-1"))
        with self.assertRaises(SentenceError):
            load_sentences(path)


class LoadTranscriptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_transcript(self):
        path = self.folder / "a.json"
        path.write_text(json.dumps(LESSON), encoding="utf-8")
        self.assertEqual(len(load_transcript(path)["segments"]), 2)

    def test_corrupted_json(self):
        path = self.folder / "a.json"
        path.write_text('{"segments": [', encoding="utf-8")
        with self.assertRaises(TranscriptError) as context:
            load_transcript(path)
        self.assertIn("corrupted", str(context.exception))
        self.assertIn("a.json", str(context.exception))

    def test_unexpected_structure(self):
        path = self.folder / "a.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(TranscriptError):
            load_transcript(path)

    def test_missing_file(self):
        with self.assertRaises(TranscriptError):
            load_transcript(self.folder / "nope.json")


if __name__ == "__main__":
    unittest.main()
