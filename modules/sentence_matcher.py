#!/usr/bin/env python3
"""
Sentence Matcher Module
Finds words and phrases in transcripts and returns their exact word-level timestamps.

How matching works
------------------
* Each transcript is flattened into ONE stream of words with timestamps, so a
  phrase that Whisper split across two segments is still found.
* Words are compared after normalization: Unicode NFKC, case-folded, and with
  everything except letters and digits removed (punctuation, spaces). So
  "Heißt," matches "heisst", and umlauts are compared correctly.
* Whole words only: the term "ich" does not match inside "mich".
* Matches whose words are more than MAX_WORD_GAP seconds apart are rejected
  (that is not one spoken phrase, only the same words far apart).
* Exact matching is the default. If matching.fuzzy_threshold < 100 and a term
  has NO exact match in a video, a fuzzy fallback (difflib similarity) looks for
  similar word sequences in that video. Fuzzy matching needs at least
  MIN_FUZZY_CHARS characters in the term.
* Languages written without spaces between words (Chinese) are matched
  character by character; a clip then covers the whole words that contain the
  matched characters.
"""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Sequence, Tuple

from modules.beautiful_logger import logger
from modules.errors import SentenceError, TranscriptError

CHAR_LEVEL_LANGUAGES = frozenset({"zh"})
MIN_FUZZY_CHARS = 4
MAX_WORD_GAP = 1.5  # seconds between two neighbouring words of one phrase
MAX_CONTEXT_CHARS = 200
MATCHES_FORMAT_VERSION = 2


def normalize_token(text: str) -> str:
    """Lower-case a word and drop everything that is not a letter or digit."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in folded if char.isalnum())


@dataclass(frozen=True)
class SearchTerm:
    text: str  # as written in sentences.txt
    tokens: Tuple[str, ...]  # normalized tokens used for matching


@dataclass
class Match:
    id: str
    term: str
    video: str  # video file name without extension
    video_path: str  # exact path of the source video
    start: float
    end: float
    matched_text: str
    context: str
    score: float
    exact: bool
    word_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class _Unit(NamedTuple):
    token: str
    start: float
    end: float
    word_index: int
    segment_index: int


def make_match_id(video: str, term_key: str, start: float, end: float) -> str:
    """Stable ID: the same match in the same video always gets the same ID."""
    raw = f"{video}|{term_key}|{round(start * 1000)}|{round(end * 1000)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def load_sentences(path: Path) -> List[str]:
    """Read sentences.txt: one term per line; empty lines and lines starting with # are ignored."""
    path = Path(path)
    if not path.is_file():
        raise SentenceError(
            f"{path.name} not found. Create it in the project folder with one German "
            "word or phrase per line."
        )
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SentenceError(f"{path.name} must be saved as UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise SentenceError(f"Cannot read {path}: {exc}") from exc

    sentences = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not sentences:
        raise SentenceError(
            f"{path.name} is empty. Add one word or phrase per line "
            "(lines starting with # are comments)."
        )
    return sentences


def load_transcript(path: Path) -> Dict[str, Any]:
    """Read a transcript JSON file. Raises TranscriptError if it is corrupted."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise TranscriptError(
            f"Transcript {path.name} is corrupted ({exc}). Delete it to transcribe the video again."
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise TranscriptError(f"Cannot read transcript {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        raise TranscriptError(
            f"Transcript {path.name} has an unexpected format. Delete it to transcribe the video again."
        )
    return data


def save_matches(matches: Sequence[Match], path: Path, language: str) -> Path:
    """Write all matches to a JSON file (atomically)."""
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    payload = {
        "version": MATCHES_FORMAT_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "total_matches": len(matches),
        "matches": [match.to_dict() for match in matches],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)
    return path


class SentenceMatcher:
    def __init__(
        self,
        language_code: str = "de",
        fuzzy_threshold: float = 100.0,
        max_word_gap: float = MAX_WORD_GAP,
    ) -> None:
        self.language_code = language_code
        self.char_level = language_code in CHAR_LEVEL_LANGUAGES
        self.fuzzy_threshold = float(fuzzy_threshold)
        self.max_word_gap = max_word_gap

    @property
    def fuzzy_enabled(self) -> bool:
        return self.fuzzy_threshold < 100

    # ------------------------------------------------------------------ search terms
    def tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        for piece in text.split():
            normalized = normalize_token(piece)
            if not normalized:
                continue
            if self.char_level:
                tokens.extend(normalized)
            else:
                tokens.append(normalized)
        return tokens

    def prepare_terms(self, sentences: Sequence[str]) -> List[SearchTerm]:
        """Turn lines from sentences.txt into search terms (duplicates are dropped)."""
        terms: List[SearchTerm] = []
        seen: Dict[Tuple[str, ...], str] = {}
        for text in sentences:
            tokens = tuple(self.tokenize(text))
            if not tokens:
                logger.warning(f"Ignoring search term without letters or digits: {text!r}")
                continue
            if tokens in seen:
                logger.warning(f"Duplicate search term ignored: {text!r} (same as {seen[tokens]!r})")
                continue
            seen[tokens] = text
            terms.append(SearchTerm(text=text, tokens=tokens))
        if not terms:
            raise SentenceError("sentences.txt contains no usable search terms.")
        return terms

    # ------------------------------------------------------------------ transcript -> word stream
    def _build_stream(
        self, transcript: Dict[str, Any]
    ) -> Tuple[List[_Unit], List[Tuple[str, int]], List[str]]:
        segments = transcript.get("segments")
        if not isinstance(segments, list):
            raise TranscriptError("Transcript has no 'segments' list.")

        units: List[_Unit] = []
        raw_words: List[Tuple[str, int]] = []
        segment_texts: List[str] = []
        skipped = 0
        for segment_index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                segment_texts.append("")
                continue
            segment_texts.append(str(segment.get("text", "")).strip())
            for word in segment.get("words") or []:
                try:
                    start = float(word["start"])
                    end = float(word["end"])
                    raw = str(word["word"])
                except (KeyError, TypeError, ValueError):
                    skipped += 1
                    continue
                normalized = normalize_token(raw)
                if not normalized:
                    continue  # pure punctuation
                word_index = len(raw_words)
                raw_words.append((raw, segment_index))
                pieces = list(normalized) if self.char_level else [normalized]
                for piece in pieces:
                    units.append(_Unit(piece, start, end, word_index, segment_index))
        if skipped:
            logger.warning(f"Ignored {skipped} malformed word entries in a transcript")
        return units, raw_words, segment_texts

    def _gap_ok(self, units: Sequence[_Unit], pos: int, length: int) -> bool:
        for index in range(pos + 1, pos + length):
            if units[index].start - units[index - 1].end > self.max_word_gap:
                return False
        return True

    # ------------------------------------------------------------------ matching
    def _exact_spans(
        self,
        term: SearchTerm,
        tokens: Sequence[str],
        units: Sequence[_Unit],
        index: Dict[str, List[int]],
    ) -> List[Tuple[int, int, float]]:
        needle = list(term.tokens)
        length = len(needle)
        spans: List[Tuple[int, int, float]] = []
        next_free = 0
        for pos in index.get(needle[0], ()):
            if pos < next_free:
                continue  # overlaps the previous occurrence of the same term
            if pos + length > len(tokens):
                break
            if list(tokens[pos : pos + length]) == needle and self._gap_ok(units, pos, length):
                spans.append((pos, length, 100.0))
                next_free = pos + length
        return spans

    def _fuzzy_spans(
        self, term: SearchTerm, tokens: Sequence[str], units: Sequence[_Unit]
    ) -> List[Tuple[int, int, float]]:
        separator = "" if self.char_level else " "
        term_text = separator.join(term.tokens)
        if len(term_text.replace(" ", "")) < MIN_FUZZY_CHARS:
            return []

        threshold = self.fuzzy_threshold / 100.0
        matcher = SequenceMatcher(None, autojunk=False)
        matcher.set_seq2(term_text)
        length = len(term.tokens)
        candidates: List[Tuple[float, int, int]] = []
        for size in sorted({max(1, length - 1), length, length + 1}):
            for pos in range(0, len(tokens) - size + 1):
                if not self._gap_ok(units, pos, size):
                    continue
                matcher.set_seq1(separator.join(tokens[pos : pos + size]))
                if matcher.real_quick_ratio() < threshold or matcher.quick_ratio() < threshold:
                    continue
                ratio = matcher.ratio()
                if ratio >= threshold:
                    candidates.append((ratio, pos, size))

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        used = set()
        spans: List[Tuple[int, int, float]] = []
        for ratio, pos, size in candidates:
            positions = range(pos, pos + size)
            if any(p in used for p in positions):
                continue
            used.update(positions)
            spans.append((pos, size, round(ratio * 100, 1)))
        spans.sort(key=lambda item: item[0])
        return spans

    def _build_match(
        self,
        term: SearchTerm,
        video_stem: str,
        video_path: Path,
        units: Sequence[_Unit],
        raw_words: Sequence[Tuple[str, int]],
        segment_texts: Sequence[str],
        span: Tuple[int, int, float],
        exact: bool,
    ) -> Match:
        pos, length, score = span
        first, last = units[pos], units[pos + length - 1]
        words = raw_words[first.word_index : last.word_index + 1]
        if self.char_level:
            matched_text = "".join(raw for raw, _ in words).strip()
        else:
            matched_text = " ".join(raw.strip() for raw, _ in words)
        context = " ".join(
            text for text in segment_texts[first.segment_index : last.segment_index + 1] if text
        )
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[: MAX_CONTEXT_CHARS - 1] + "…"
        start = first.start
        end = max(last.end, start)
        term_key = " ".join(term.tokens)
        return Match(
            id=make_match_id(video_stem, term_key, start, end),
            term=term.text,
            video=video_stem,
            video_path=str(video_path),
            start=start,
            end=end,
            matched_text=matched_text,
            context=context,
            score=score,
            exact=exact,
            word_count=last.word_index - first.word_index + 1,
        )

    def find_in_transcript(
        self,
        transcript: Dict[str, Any],
        terms: Sequence[SearchTerm],
        video_path: Path,
    ) -> List[Match]:
        """Find all occurrences of all terms in one transcript. Returns matches grouped by term."""
        video_path = Path(video_path)
        video_stem = video_path.stem
        units, raw_words, segment_texts = self._build_stream(transcript)
        if not units:
            return []

        tokens = [unit.token for unit in units]
        index: Dict[str, List[int]] = defaultdict(list)
        for pos, token in enumerate(tokens):
            index[token].append(pos)

        matches: List[Match] = []
        for term in terms:
            spans = self._exact_spans(term, tokens, units, index)
            exact = True
            if not spans and self.fuzzy_enabled:
                spans = self._fuzzy_spans(term, tokens, units)
                exact = False
            for span in spans:
                matches.append(
                    self._build_match(
                        term, video_stem, video_path, units, raw_words, segment_texts, span, exact
                    )
                )
        return matches
