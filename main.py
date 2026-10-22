#!/usr/bin/env python3
"""
Goethe - German Sentence Audio Extractor

Pipeline:  videos -> transcripts (faster-whisper) -> matches -> MP3 clips (ffmpeg)

Exit codes: 0 = finished without errors, 1 = finished but something failed or
nothing could be done, 2 = configuration problem, 130 = interrupted with Ctrl+C.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from tqdm import tqdm

    from modules.audio_extractor import AudioExtractor, ExtractionResult
    from modules.beautiful_logger import logger
    from modules.config import CONFIG_FILENAME, PROJECT_ROOT, Config, load_config
    from modules.errors import (
        ConfigError,
        ExtractionError,
        GoetheError,
        SentenceError,
        SpeechError,
        TranscriptError,
    )
    from modules.sentence_matcher import (
        Match,
        SearchTerm,
        SentenceMatcher,
        load_sentences,
        load_transcript,
        save_matches,
    )
    from modules.setup import SENTENCES_FILENAME, ProjectSetup
    from modules.speech_recognition import (
        SpeechRecognizer,
        find_videos,
        save_transcript,
        transcript_path_for,
    )
except ImportError as import_error:
    print(f"❌ A required Python package is missing: {import_error.name}")
    print("   Install the project requirements (requirements.txt) and run this again.")
    print("   Run 'python3 setup.py' for a check of everything Goethe needs.")
    sys.exit(2)

MAX_LISTED = 10


@dataclass
class RunStats:
    videos: int = 0
    transcribed_now: int = 0
    transcripts_used: int = 0
    matches: int = 0
    mp3_created: int = 0
    mp3_skipped: int = 0
    mp3_failed: int = 0
    errors: int = 0


def show_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------- phase 1
def phase_transcribe(config: Config, stats: RunStats) -> List[Path]:
    """Transcribe every video that has no transcript yet. Returns the videos that have one."""
    logger.step("Speech Recognition", "🎤")

    videos, duplicates = find_videos(config.paths.videos, config.video_formats)
    for kept, skipped in duplicates:
        logger.warning(
            f"Skipping {skipped.name}: it has the same name as {kept.name} "
            "(transcripts are named after the video). Rename one of the two files."
        )
    formats = ", ".join("." + fmt for fmt in config.video_formats)
    if not videos:
        logger.error(f"No videos found in {show_path(config.paths.videos, config.root)}/")
        logger.info(f"Add video files ({formats}) to that folder and run Goethe again.")
        stats.errors += 1
        return []

    stats.videos = len(videos)
    logger.info(f"Found {len(videos)} video(s)")
    for video in videos[:3]:
        logger.plain(f"📹 {video.name}")
    if len(videos) > 3:
        logger.plain(f"... and {len(videos) - 3} more")

    pending = [
        video for video in videos if not transcript_path_for(config.paths.transcripts, video).exists()
    ]
    if len(videos) > len(pending):
        logger.info(f"⏩ {len(videos) - len(pending)} video(s) already transcribed - skipping")

    if pending:
        # The model is created (and loaded) only here, when work is really needed.
        recognizer = SpeechRecognizer(config.speech)
        try:
            recognizer.load_model()
        except SpeechError as exc:
            logger.error(str(exc))
            stats.errors += len(pending)
            pending = []
        for number, video in enumerate(pending, 1):
            logger.info(f"🎤 [{number}/{len(pending)}] Transcribing {video.name}")
            try:
                transcript = recognizer.transcribe_video(video)
                save_transcript(transcript, transcript_path_for(config.paths.transcripts, video))
                stats.transcribed_now += 1
            except SpeechError as exc:
                logger.error(str(exc))
                stats.errors += 1

    ready = [
        video for video in videos if transcript_path_for(config.paths.transcripts, video).exists()
    ]
    known = {transcript_path_for(config.paths.transcripts, video).name for video in videos}
    orphans = [
        path for path in config.paths.transcripts.glob("*.json") if path.name not in known
    ]
    if orphans:
        logger.info(f"{len(orphans)} transcript(s) have no video in the videos folder and are ignored")
    stats.transcripts_used = len(ready)
    return ready


# ---------------------------------------------------------------------- phase 2
def phase_match(config: Config, ready: Sequence[Path], stats: RunStats) -> Optional[List[Match]]:
    """Search all transcripts. Returns the matches, or None if matching was not possible."""
    logger.step("Sentence Matching", "🔎")

    try:
        sentences = load_sentences(config.root / SENTENCES_FILENAME)
        matcher = SentenceMatcher(config.speech.language_code, config.matching.fuzzy_threshold)
        terms = matcher.prepare_terms(sentences)
    except SentenceError as exc:
        logger.error(str(exc))
        stats.errors += 1
        return None

    if not ready:
        logger.warning("No transcripts available - nothing to search")
        return None

    if matcher.fuzzy_enabled:
        mode = f"exact, then similar spellings (>= {config.matching.fuzzy_threshold:g}% similarity)"
    else:
        mode = "exact matches only"
    logger.info(f"Searching {len(terms)} word(s)/phrase(s) in {len(ready)} transcript(s) - {mode}")

    matches: List[Match] = []
    for video in tqdm(ready, desc="Searching", unit="video"):
        transcript_file = transcript_path_for(config.paths.transcripts, video)
        try:
            transcript = load_transcript(transcript_file)
        except TranscriptError as exc:
            logger.error(str(exc))
            stats.errors += 1
            continue
        language = transcript.get("language")
        if language and language != config.speech.language_code:
            logger.warning(
                f"{transcript_file.name} was transcribed as '{language}' but config.yaml says "
                f"'{config.speech.language_code}'. Delete it to transcribe again in the configured language."
            )
        matches.extend(matcher.find_in_transcript(transcript, terms, video))

    report_matches(terms, matches)
    stats.matches = len(matches)

    if matches:
        matches_file = config.paths.output / "all_matches.json"
        try:
            save_matches(matches, matches_file, config.speech.language_code)
            logger.info(f"💾 Matches saved: {show_path(matches_file, config.root)}")
        except OSError as exc:
            logger.error(f"Could not save {matches_file}: {exc}")
            stats.errors += 1
    else:
        logger.warning("No matches found in any video")
        logger.info("Tips: check the spelling in sentences.txt, try single words, or see README > Troubleshooting")
    return matches


def report_matches(terms: Sequence[SearchTerm], matches: Sequence[Match]) -> None:
    counts = {term.text: 0 for term in terms}
    for match in matches:
        counts[match.term] = counts.get(match.term, 0) + 1
    rows = [
        (term.text, f"{counts[term.text]} clip(s)" if counts[term.text] else "not found")
        for term in terms[:20]
    ]
    if len(terms) > 20:
        rows.append(f"... and {len(terms) - 20} more terms")
    logger.box(f"Matches: {len(matches)} total", rows, emoji="🔎")


# ---------------------------------------------------------------------- phase 3
def phase_extract(config: Config, matches: Sequence[Match], stats: RunStats) -> None:
    logger.step("Audio Extraction", "🎵")

    try:
        extractor = AudioExtractor(
            padding_before=config.audio.padding_before,
            padding_after=config.audio.padding_after,
            bitrate=config.audio.bitrate,
        )
    except ExtractionError as exc:
        logger.error(str(exc))
        stats.errors += 1
        return

    logger.info(
        f"Quality {config.audio.bitrate} kbps, padding {config.audio.padding_before}s before / "
        f"{config.audio.padding_after}s after"
    )
    result: ExtractionResult = extractor.extract_all(matches, config.mp3_folder)
    stats.mp3_created = len(result.created)
    stats.mp3_skipped = len(result.skipped)
    stats.mp3_failed = len(result.failed)

    if result.created:
        logger.success(f"Created {len(result.created)} MP3 file(s)")
        rows: List[str] = [
            f"{number}. {path.parent.name}/{path.name}"
            for number, path in enumerate(result.created[:MAX_LISTED], 1)
        ]
        if len(result.created) > MAX_LISTED:
            rows.append(f"... and {len(result.created) - MAX_LISTED} more")
        logger.box("MP3 Files Created", rows, emoji="🎵")
    if result.skipped:
        logger.info(f"⏩ {len(result.skipped)} MP3 file(s) already existed - skipped")
    if result.failed:
        logger.warning(f"{len(result.failed)} clip(s) could not be created (see messages above)")
    if not result.created and not result.skipped:
        logger.warning("No MP3 files were created")
    logger.info(f"📁 Saved to: {show_path(config.mp3_folder, config.root)}/")


# ---------------------------------------------------------------------- main
def run() -> int:
    logger.title("Goethe - German Sentence Audio Extractor")

    if not (PROJECT_ROOT / CONFIG_FILENAME).exists():
        logger.info("First-time setup detected! 🚀")
        ProjectSetup(PROJECT_ROOT).run_full_setup()
        return 0

    try:
        config = load_config()
        for message in config.warnings:
            logger.warning(message)
        config.ensure_folders()
    except ConfigError as exc:
        logger.error(str(exc))
        logger.info(f"Fix {CONFIG_FILENAME}, or delete it and run 'python3 setup.py' to get a fresh one.")
        return 2

    logger.attach_file(config.paths.logs / "goethe.log")
    stats = RunStats()

    ready = phase_transcribe(config, stats)
    matches = phase_match(config, ready, stats) if ready else None
    if matches:
        phase_extract(config, matches, stats)

    stats.errors += stats.mp3_failed
    logger.divider()
    logger.box(
        "Summary",
        [
            ("Videos", stats.videos),
            ("Transcribed now", stats.transcribed_now),
            ("Transcripts used", stats.transcripts_used),
            ("Matches", stats.matches),
            ("MP3 created", stats.mp3_created),
            ("MP3 skipped", stats.mp3_skipped),
            ("MP3 failed", stats.mp3_failed),
            ("Output", show_path(config.mp3_folder, config.root)),
        ],
    )
    if stats.errors:
        logger.warning(f"Finished with {stats.errors} problem(s) - see the messages above")
    logger.footer()
    return 1 if stats.errors else 0


def main() -> int:
    try:
        return run()
    except KeyboardInterrupt:
        logger.blank()
        logger.warning("Interrupted. Finished transcripts are kept - run again to continue.")
        return 130
    except GoetheError as exc:
        logger.error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
