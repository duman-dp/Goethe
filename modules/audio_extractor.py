#!/usr/bin/env python3
"""
Audio Extractor Module
Cuts MP3 clips out of videos with ffmpeg, using the timestamps of each match.

Output layout:   output/mp3/<term>/<term>__<video>__<hh>h<mm>m<ss>s_<id>.mp3

The file name contains the search term, the video name, the start time and the
stable match ID, so names are unique across all videos and Anki never sees two
different clips with the same file name.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from tqdm import tqdm

from modules.beautiful_logger import logger
from modules.errors import ExtractionError
from modules.sentence_matcher import Match

_TRANSLITERATION = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "ẞ": "SS",
}


def transliterate(text: str) -> str:
    """German-aware ASCII transliteration: ä->ae, ö->oe, ü->ue, ß->ss; other accents are dropped."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(_TRANSLITERATION.get(char, char) for char in text)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def safe_filename(text: str, max_length: int = 60, fallback: str = "item") -> str:
    """
    Turn any text into a readable file/folder name made of A-Z, a-z, 0-9 and "_".

    * "Ich heiße Müller!" -> "Ich_heisse_Mueller"
    * Text without any Latin letters or digits (for example Chinese) becomes
      "<fallback>_<hash>", so different texts never collapse into the same name.
    * Names longer than max_length are cut and get a short hash appended, so two
      long texts with the same beginning stay different.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "_", transliterate(text)).strip("_")
    digest = hashlib.sha1(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()[:6]
    if not slug:
        return f"{fallback}_{digest}"
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_") + "_" + digest
    return slug


def format_timestamp(seconds: float) -> str:
    total = int(max(seconds, 0))
    return f"{total // 3600:02d}h{(total % 3600) // 60:02d}m{total % 60:02d}s"


class FolderNamer:
    """Gives every search term its own folder name, even if two terms sanitize to the same name."""

    def __init__(self) -> None:
        self._by_term: Dict[str, str] = {}
        self._owner: Dict[str, str] = {}  # case-folded folder name -> term

    def folder_for(self, term: str) -> str:
        if term in self._by_term:
            return self._by_term[term]
        base = safe_filename(term, max_length=60, fallback="term")
        name = base
        counter = 2
        while self._owner.get(name.casefold(), term) != term:
            name = f"{base}_{counter}"
            counter += 1
        self._owner[name.casefold()] = term
        self._by_term[term] = name
        return name


@dataclass
class ExtractionResult:
    created: List[Path] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)  # clips that already existed
    failed: List[Tuple[Match, str]] = field(default_factory=list)


class AudioExtractor:
    def __init__(
        self,
        padding_before: float = 0.03,
        padding_after: float = 0.03,
        bitrate: int = 192,
        ffmpeg: Optional[str] = None,
        timeout: int = 300,
    ) -> None:
        self.ffmpeg = ffmpeg or shutil.which("ffmpeg")
        if not self.ffmpeg:
            raise ExtractionError(
                "ffmpeg was not found, so MP3 clips cannot be created. "
                "Install ffmpeg (Ubuntu: 'sudo apt install ffmpeg') and run Goethe again."
            )
        self.padding_before = padding_before
        self.padding_after = padding_after
        self.bitrate = bitrate
        self.timeout = timeout

    # ------------------------------------------------------------------ naming and commands
    def build_filename(self, match: Match, term_folder: str) -> str:
        video = safe_filename(match.video, max_length=40, fallback="video")
        return f"{term_folder}__{video}__{format_timestamp(match.start)}_{match.id}.mp3"

    def clip_window(self, match: Match) -> Tuple[float, float]:
        """Return (start, duration) in seconds including the configured padding."""
        start = max(0.0, match.start - self.padding_before)
        end = match.end + self.padding_after
        return start, max(end - start, 0.01)

    def build_command(self, video_path: Path, start: float, duration: float, output: Path) -> List[str]:
        return [
            str(self.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.3f}",
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            f"{self.bitrate}k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output),
        ]

    # ------------------------------------------------------------------ extraction
    def _run_ffmpeg(self, command: List[str], output: Path) -> Tuple[bool, str]:
        """Run ffmpeg into a temporary file and move it into place only on success."""
        part = output.with_name(output.stem + ".part.mp3")
        command = command[:-1] + [str(part)]
        try:
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired:
                return False, f"ffmpeg timed out after {self.timeout} seconds"
            except OSError as exc:
                return False, f"ffmpeg could not be started: {exc}"

            if completed.returncode != 0:
                lines = [line for line in (completed.stderr or "").strip().splitlines() if line.strip()]
                detail = lines[-1] if lines else "no error message"
                return False, f"ffmpeg exited with code {completed.returncode}: {detail}"
            if not part.is_file() or part.stat().st_size == 0:
                return False, "ffmpeg finished but produced no audio (does the video have a sound track?)"
            os.replace(part, output)
            return True, ""
        finally:
            if part.exists():
                try:
                    part.unlink()
                except OSError:
                    pass

    def extract_all(self, matches: Sequence[Match], mp3_folder: Path) -> ExtractionResult:
        """Create one MP3 per match. Clips that already exist are skipped (resume)."""
        mp3_folder = Path(mp3_folder)
        mp3_folder.mkdir(parents=True, exist_ok=True)
        result = ExtractionResult()
        namer = FolderNamer()
        missing_videos = set()

        for match in tqdm(matches, desc="Extracting clips", unit="clip"):
            video_path = Path(match.video_path)
            if match.video_path in missing_videos:
                result.failed.append((match, f"video not found: {video_path}"))
                continue
            if not video_path.is_file():
                missing_videos.add(match.video_path)
                logger.error(f"Video not found: {video_path}")
                result.failed.append((match, f"video not found: {video_path}"))
                continue

            folder = mp3_folder / namer.folder_for(match.term)
            folder.mkdir(parents=True, exist_ok=True)
            output = folder / self.build_filename(match, folder.name)
            if output.is_file() and output.stat().st_size > 0:
                result.skipped.append(output)
                continue

            start, duration = self.clip_window(match)
            ok, message = self._run_ffmpeg(self.build_command(video_path, start, duration, output), output)
            if ok:
                result.created.append(output)
            else:
                logger.error(f"Could not create clip for '{match.term}' in {video_path.name}: {message}")
                result.failed.append((match, message))
        return result
