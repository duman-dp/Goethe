import contextlib
import io
import re
import unittest

from modules.beautiful_logger import BeautifulLogger, Colors, display_width, strip_ansi, truncate

ROWS = [
    ("Videos", 3),
    ("Matches", 120),
    ("Output with a very long label name", "output/mp3"),
    ("Long value", "x" * 200),
    ("Wide chars", "你好世界 — ünïcödé"),
    "A plain row with an emoji 🎵 and more text",
    "z" * 300,
]


def render(colors, call):
    previous = Colors.BOLD != ""
    Colors.set_enabled(colors)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            call(BeautifulLogger(width=70))
    finally:
        Colors.set_enabled(previous)
    return buffer.getvalue()


class WidthTests(unittest.TestCase):
    def test_ansi_codes_are_ignored(self):
        self.assertEqual(display_width("\033[1m\033[96mHello\033[0m"), 5)
        self.assertEqual(strip_ansi("\033[92mok\033[0m"), "ok")

    def test_wide_characters_count_double(self):
        self.assertEqual(display_width("你好"), 4)
        self.assertEqual(display_width("📚"), 2)
        self.assertEqual(display_width("ä"), 1)

    def test_truncate(self):
        self.assertEqual(truncate("short", 10), "short")
        self.assertEqual(display_width(truncate("x" * 50, 10)), 10)
        self.assertTrue(truncate("x" * 50, 10).endswith("…"))
        self.assertLessEqual(display_width(truncate("你好世界你好世界", 7)), 7)


class AlignmentTests(unittest.TestCase):
    def assert_aligned(self, text):
        lines = [line for line in strip_ansi(text).splitlines() if line.strip()]
        self.assertTrue(lines)
        widths = {display_width(line) for line in lines if line.lstrip().startswith(("│", "┌", "└", "├", "║", "╔", "╚"))}
        self.assertEqual(len(widths), 1, widths)

    def test_box_is_aligned_with_colors(self):
        self.assert_aligned(render(True, lambda log: log.box("Summary", ROWS)))

    def test_box_is_aligned_without_colors(self):
        self.assert_aligned(render(False, lambda log: log.box("Summary", ROWS)))

    def test_title_step_and_footer_are_aligned(self):
        for colors in (True, False):
            self.assert_aligned(render(colors, lambda log: log.title("Goethe - German Sentence Audio Extractor")))
            self.assert_aligned(render(colors, lambda log: log.step("Speech Recognition", "🎤")))
            self.assert_aligned(render(colors, lambda log: log.footer()))

    def test_no_color_output_contains_no_escape_codes(self):
        text = render(False, lambda log: (log.box("Summary", ROWS), log.success("done"), log.error("bad")))
        self.assertIsNone(re.search(r"\x1b\[", text))

    def test_color_output_does_contain_escape_codes(self):
        text = render(True, lambda log: log.success("done"))
        self.assertIn("\x1b[", text)


if __name__ == "__main__":
    unittest.main()
