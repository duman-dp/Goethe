#!/usr/bin/env python3
"""
Speech Recognition Module
Converts video speech to text with word-level timestamps (faster-whisper).

The heavy `faster_whisper` package is imported and the model is loaded only
when a video really has to be transcribed (see SpeechRecognizer.load_model).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from tqdm import tqdm

from modules.beautiful_logger import logger
from modules.config import SpeechConfig
from modules.errors import SpeechError

TRANSCRIPT_VERSION = 2


def find_videos(folder: Path, formats: Iterable[str]) -> Tuple[List[Path], List[Tuple[Path, Path]]]:
    """
    Find video files directly inside `folder` whose extension is in `formats`.

    Returns (videos, duplicates). Transcripts are named after the video's stem
    (lesson.mp4 -> lesson.json), so two videos with the same stem (lesson.mp4
    and lesson.mkv) cannot both be used; the second one is reported in
    `duplicates` as (kept_video, skipped_video).
    """
    folder = Path(folder)
    if not folder.is_dir():
        return [], []
    wanted = {fmt.lower().lstrip(".") for fmt in formats}
    candidates = sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and not path.name.startswith(".")
            and path.suffix.lower().lstrip(".") in wanted
        ),
        key=lambda path: path.name.casefold(),
    )
    videos: List[Path] = []
    duplicates: List[Tuple[Path, Path]] = []
    by_stem: Dict[str, Path] = {}
    for path in candidates:
        if path.stem in by_stem:
            duplicates.append((by_stem[path.stem], path))
            continue
        by_stem[path.stem] = path
        videos.append(path)
    return videos, duplicates


def transcript_path_for(transcripts_folder: Path, video: Path) -> Path:
    return Path(transcripts_folder) / f"{Path(video).stem}.json"


def save_transcript(data: Dict[str, Any], path: Path) -> Path:
    """Write a transcript atomically, so an interrupted run never leaves a half-written file."""
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError as exc:
        raise SpeechError(f"Could not save transcript {path}: {exc}") from exc
    return path


class SpeechRecognizer:
    def __init__(self, settings: SpeechConfig) -> None:
        self.settings = settings
        self._model: Any = None

    @property
    def compute_type(self) -> str:
        return {"cpu": "int8", "cuda": "float16"}.get(self.settings.device, "default")

    def load_model(self) -> None:
        """Load the Whisper model (once). Imports faster_whisper lazily."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SpeechError(
                "The package 'faster-whisper' is not installed. "
                "Install the project requirements (requirements.txt) and try again."
            ) from exc

        if not self.settings.quiet:
            logger.info(
                f"🧠 Loading Whisper model '{self.settings.model_size}' on {self.settings.device} "
                "(the first run downloads it - this can take a while)"
            )
        started = time.time()
        try:
            self._model = WhisperModel(
                self.settings.model_size,
                device=self.settings.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:  # download, memory, GPU and corrupt-cache errors all end up here
            raise SpeechError(
                f"Could not load Whisper model '{self.settings.model_size}': {exc}. "
                "Check your internet connection (first download), free disk space and memory, "
                "or choose a smaller speech.model_size in config.yaml."
            ) from exc
        if not self.settings.quiet:
            logger.success(f"Model loaded in {time.time() - started:.1f} seconds")

    def transcribe_video(self, video_path: Path) -> Dict[str, Any]:
        """Transcribe one video and return the transcript data (see TRANSCRIPT_VERSION)."""
        video_path = Path(video_path)
        self.load_model()
        started = time.time()

        try:
            segments, info = self._model.transcribe(
                str(video_path),
                language=self.settings.language_code,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                condition_on_previous_text=True,
            )
        except Exception as exc:
            raise SpeechError(f"Could not read audio from {video_path.name}: {exc}") from exc

        duration = float(getattr(info, "duration", 0) or 0)
        bar = tqdm(
            total=round(duration, 1) if duration > 0 else None,
            desc=f"Transcribing {video_path.name[:30]}",
            unit="s",
            disable=self.settings.quiet,
        )
        segment_list: List[Dict[str, Any]] = []
        word_count = 0
        try:
            for segment in segments:
                words = [
                    {"start": float(word.start), "end": float(word.end), "word": word.word}
                    for word in (segment.words or [])
                ]
                word_count += len(words)
                segment_list.append(
                    {
                        "start": float(segment.start),
                        "end": float(segment.end),
                        "text": segment.text,
                        "words": words,
                    }
                )
                if duration > 0:
                    bar.n = min(float(segment.end), duration)
                    bar.refresh()
        except Exception as exc:
            raise SpeechError(f"Transcription of {video_path.name} failed: {exc}") from exc
        finally:
            bar.close()

        if word_count == 0:
            logger.warning(f"No speech found in {video_path.name} (transcript will be empty)")
        elif not self.settings.quiet:
            logger.success(
                f"Transcribed {video_path.name}: {len(segment_list)} segments, {word_count} words "
                f"in {time.time() - started:.1f} seconds"
            )

        return {
            "version": TRANSCRIPT_VERSION,
            "video_name": video_path.name,
            "video_path": str(video_path),
            "language": self.settings.language_code,
            "model_size": self.settings.model_size,
            "duration": duration,
            "created": datetime.now().isoformat(timespec="seconds"),
            "processing_time": round(time.time() - started, 2),
            "segments": segment_list,
        }
