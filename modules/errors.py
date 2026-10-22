#!/usr/bin/env python3
"""
Goethe exceptions.

Every exception message is written for the user: it says what went wrong
and, where possible, what to do about it. main.py prints these messages as-is.
"""


class GoetheError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(GoetheError):
    """config.yaml is missing, unreadable or contains invalid values."""


class SentenceError(GoetheError):
    """sentences.txt is missing, unreadable or contains no search terms."""


class TranscriptError(GoetheError):
    """A transcript JSON file is corrupted or has an unexpected format."""


class SpeechError(GoetheError):
    """Speech recognition failed (model could not load, audio unreadable...)."""


class ExtractionError(GoetheError):
    """MP3 extraction cannot run (for example ffmpeg is not installed)."""
