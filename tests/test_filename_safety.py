import re
import unittest

from modules.audio_extractor import FolderNamer, format_timestamp, safe_filename, transliterate


class TransliterationTests(unittest.TestCase):
    def test_german_umlauts_and_eszett(self):
        self.assertEqual(transliterate("äöüß"), "aeoeuess")
        self.assertEqual(transliterate("ÄÖÜ"), "AeOeUe")

    def test_other_accents_are_simplified(self):
        self.assertEqual(transliterate("café"), "cafe")

    def test_decomposed_input_gives_same_result(self):
        composed = "Müller"
        decomposed = "Müller"
        self.assertEqual(transliterate(composed), transliterate(decomposed))
        self.assertEqual(transliterate(decomposed), "Mueller")


class SafeFilenameTests(unittest.TestCase):
    def test_readable_german_name(self):
        self.assertEqual(safe_filename("Ich heiße Müller, schön!"), "Ich_heisse_Mueller_schoen")

    def test_question_mark_and_spaces(self):
        self.assertEqual(safe_filename("Woher kommst du?"), "Woher_kommst_du")

    def test_umlaut_words_do_not_collapse(self):
        self.assertEqual(safe_filename("Über"), "Ueber")
        self.assertNotEqual(safe_filename("schon"), safe_filename("schön"))

    def test_only_safe_characters(self):
        name = safe_filename('a/b\\c:d*e?"f<g>h|i  j\tk\nl')
        self.assertRegex(name, r"^[A-Za-z0-9_]+$")

    def test_empty_or_symbol_only_text_gets_fallback(self):
        for text in ("", "???", "   ", "..."):
            name = safe_filename(text)
            self.assertTrue(name.startswith("item_"), name)
            self.assertRegex(name, r"^item_[0-9a-f]{6}$")

    def test_non_latin_text_is_stable_and_distinct(self):
        first = safe_filename("你好")
        self.assertEqual(first, safe_filename("你好"))
        self.assertNotEqual(first, safe_filename("世界"))
        self.assertRegex(first, r"^item_[0-9a-f]{6}$")

    def test_custom_fallback(self):
        self.assertTrue(safe_filename("???", fallback="term").startswith("term_"))

    def test_long_names_are_cut_but_stay_different(self):
        prefix = "word " * 30
        first = safe_filename(prefix + "eins")
        second = safe_filename(prefix + "zwei")
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 60 + 7)
        self.assertRegex(first, r"^[A-Za-z0-9_]+$")

    def test_short_names_are_not_modified_by_hashing(self):
        self.assertEqual(safe_filename("Hobby"), "Hobby")


class FolderNamerTests(unittest.TestCase):
    def test_same_term_gets_same_folder(self):
        namer = FolderNamer()
        self.assertEqual(namer.folder_for("Wie heißt du"), namer.folder_for("Wie heißt du"))

    def test_terms_with_same_sanitized_name_get_different_folders(self):
        namer = FolderNamer()
        first = namer.folder_for("Äpfel")
        second = namer.folder_for("Aepfel")
        self.assertEqual(first, "Aepfel")
        self.assertNotEqual(first, second)
        self.assertEqual(second, "Aepfel_2")

    def test_case_insensitive_collisions_are_avoided(self):
        namer = FolderNamer()
        first = namer.folder_for("Hobby!")
        second = namer.folder_for("hobby?")
        self.assertNotEqual(first.casefold(), second.casefold())


class TimestampTests(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_timestamp(0), "00h00m00s")
        self.assertEqual(format_timestamp(135.9), "00h02m15s")
        self.assertEqual(format_timestamp(3725), "01h02m05s")
        self.assertIsNotNone(re.match(r"^\d{2}h\d{2}m\d{2}s$", format_timestamp(99.5)))


if __name__ == "__main__":
    unittest.main()
