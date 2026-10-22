#!/usr/bin/env python3
"""
Beautiful Output Logger - colorful, aligned and readable without colors.

* Boxes are aligned by VISIBLE width: ANSI color codes are ignored and wide
  characters (emoji, CJK) count as two columns.
* Colors are switched off automatically when output is not a terminal, when the
  NO_COLOR environment variable is set, or when TERM=dumb. Set FORCE_COLOR=1
  to force them on.
* If a log file is attached, every message is also written there (no colors).
"""

from __future__ import annotations

import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

try:  # tqdm is only used so messages do not break progress bars
    from tqdm import tqdm
except ImportError:  # pragma: no cover - setup.py runs before packages are installed
    tqdm = None  # type: ignore

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_BOX_CHARS = set("│┌┐└┘├┤─═╔╗╚╝║ ")

_CODES = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "WHITE": "\033[97m",
}


def _detect_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    stream = sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


class Colors:
    """ANSI color codes. All attributes become empty strings when colors are off."""

    HEADER = ""
    BLUE = ""
    CYAN = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    RESET = ""
    BOLD = ""
    DIM = ""
    WHITE = ""

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        for name, code in _CODES.items():
            setattr(cls, name, code if enabled else "")


Colors.set_enabled(_detect_color())


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def display_width(text: str) -> int:
    """Number of terminal columns the text occupies (ANSI codes are ignored)."""
    chars = list(strip_ansi(text))
    width = 0
    for index, char in enumerate(chars):
        if unicodedata.category(char) in ("Mn", "Me", "Cf"):
            continue  # combining marks and variation selectors take no space
        if unicodedata.east_asian_width(char) in ("W", "F"):
            width += 2
        elif index + 1 < len(chars) and chars[index + 1] == "️" and ord(char) > 0x2000:
            width += 2  # emoji written as symbol + variation selector
        else:
            width += 1
    return width


def truncate(text: str, width: int) -> str:
    """Shorten plain text (no ANSI codes) to at most `width` columns, adding an ellipsis."""
    if display_width(text) <= width:
        return text
    kept = ""
    used = 0
    for char in text:
        char_width = display_width(char)
        if used + char_width > width - 1:
            break
        kept += char
        used += char_width
    return kept + "…"


def pad(text: str, width: int) -> str:
    return text + " " * max(width - display_width(text), 0)


Row = Union[str, Tuple[str, object]]


class BeautifulLogger:
    def __init__(self, width: int = 70) -> None:
        self.width = width
        self.start_time = time.time()
        self.step_count = 0
        self._log_file: Optional[Path] = None

    # ------------------------------------------------------------------ plumbing
    def attach_file(self, path: Union[str, Path]) -> None:
        """Also write all messages (without colors) to a log file."""
        log_path = Path(path)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"\n=== Goethe run started {datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
        except OSError as exc:
            self.warning(f"Cannot write log file {log_path}: {exc}")
            return
        self._log_file = log_path

    def _write_file(self, line: str) -> None:
        if self._log_file is None:
            return
        text = strip_ansi(line).strip()
        if not text or all(char in _BOX_CHARS for char in text):
            return
        try:
            with open(self._log_file, "a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now():%H:%M:%S} {text}\n")
        except OSError as exc:
            self._log_file = None
            print(f"  Log file disabled: {exc}")

    def _emit(self, line: str = "") -> None:
        if tqdm is not None:
            tqdm.write(line)
        else:
            print(line)
        self._write_file(line)

    # ------------------------------------------------------------------ boxes
    def _bar(self, left: str, fill: str, right: str, color: str = "") -> str:
        return f"  {color}{left}{fill * (self.width - 2)}{right}{Colors.RESET}"

    def _row(self, content: str = "", align: str = "left", border: str = "│", color: str = "") -> str:
        inner = self.width - 2
        gap = max(inner - display_width(content), 0)
        if align == "center":
            left = gap // 2
        else:
            left = min(1, gap)
        right = gap - left
        edge = f"{color}{border}{Colors.RESET}"
        return f"  {edge}{' ' * left}{content}{' ' * right}{edge}"

    def title(self, text: str) -> None:
        inner = self.width - 2
        label = truncate(f"📚 {text} 📚", inner - 2)
        self._emit()
        self._emit(self._bar("╔", "═", "╗", Colors.CYAN))
        self._emit(self._row("", border="║", color=Colors.CYAN))
        self._emit(
            self._row(f"{Colors.BOLD}{Colors.CYAN}{label}{Colors.RESET}", align="center", border="║", color=Colors.CYAN)
        )
        self._emit(self._row("", border="║", color=Colors.CYAN))
        self._emit(self._bar("╚", "═", "╝", Colors.CYAN))
        self._emit()

    def step(self, text: str, emoji: str = "📌") -> None:
        self.step_count += 1
        label = truncate(f"{emoji} Step {self.step_count}: {text}", self.width - 4)
        self._emit()
        self._emit(self._bar("┌", "─", "┐", Colors.BLUE))
        self._emit(self._row(f"{Colors.BOLD}{label}{Colors.RESET}", color=Colors.BLUE))
        self._emit(self._bar("└", "─", "┘", Colors.BLUE))

    def box(self, title: str, rows: Sequence[Row], emoji: str = "📊") -> None:
        """Print a table box. Rows are either plain strings or (label, value) pairs."""
        inner = self.width - 2
        label_width = 0
        for row in rows:
            if isinstance(row, tuple):
                label_width = max(label_width, display_width(str(row[0])))
        label_width = min(label_width, 24)

        self._emit()
        self._emit(self._bar("┌", "─", "┐"))
        heading = truncate(f"{emoji} {title}", inner - 2)
        self._emit(self._row(f"{Colors.BOLD}{Colors.CYAN}{heading}{Colors.RESET}"))
        self._emit(self._bar("├", "─", "┤"))
        for row in rows:
            if isinstance(row, tuple):
                label = truncate(str(row[0]), label_width)
                value = truncate(str(row[1]), max(inner - label_width - 4, 8))
                content = f"{pad(label + ':', label_width + 1)} {Colors.GREEN}{value}{Colors.RESET}"
            else:
                content = truncate(str(row), inner - 2)
            self._emit(self._row(content))
        self._emit(self._bar("└", "─", "┘"))
        self._emit()

    def divider(self) -> None:
        self._emit(f"  {Colors.DIM}{'─' * self.width}{Colors.RESET}")

    def footer(self, message: str = "Processing complete!") -> None:
        self._emit()
        self._emit(self._bar("┌", "─", "┐"))
        self._emit(self._row(f"{Colors.BOLD}{Colors.GREEN}✨ {message}{Colors.RESET}"))
        self._emit(self._bar("└", "─", "┘"))
        self._emit(f"  {Colors.DIM}⏱️  Total time: {self.format_elapsed(time.time() - self.start_time)}{Colors.RESET}")
        self._emit()

    @staticmethod
    def format_elapsed(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        if seconds < 3600:
            return f"{seconds / 60:.1f} minutes"
        return f"{seconds / 3600:.1f} hours"

    # ------------------------------------------------------------------ messages
    def blank(self) -> None:
        self._emit()

    def plain(self, text: str) -> None:
        self._emit(f"  {text}")

    def info(self, text: str, emoji: str = "ℹ️") -> None:
        self._emit(f"  {Colors.DIM}{emoji}{Colors.RESET} {text}")

    def success(self, text: str, emoji: str = "✅") -> None:
        self._emit(f"  {Colors.GREEN}{emoji}{Colors.RESET} {text}")

    def warning(self, text: str, emoji: str = "⚠️") -> None:
        self._emit(f"  {Colors.YELLOW}{emoji}{Colors.RESET} {text}")

    def error(self, text: str, emoji: str = "❌") -> None:
        self._emit(f"  {Colors.RED}{emoji}{Colors.RESET} {text}")


logger = BeautifulLogger()
