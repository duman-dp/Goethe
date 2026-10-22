#!/usr/bin/env python3
"""
Configuration loading and validation.

The single source of truth for default values is DEFAULT_CONFIG_YAML below.
The shipped config.yaml and the file created by `python3 setup.py` both
contain exactly this text, so defaults can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from modules.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILENAME = "config.yaml"

# Language code -> display name. These are Whisper language codes.
# To support another language, add it here (and, if its words are not
# separated by spaces like Chinese, see CHAR_LEVEL_LANGUAGES in
# sentence_matcher.py).
LANGUAGES: Dict[str, str] = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
}

# Extra spellings that are accepted in config.yaml (all lower case).
_LANGUAGE_ALIASES: Dict[str, str] = {
    "deutsch": "de",
    "francais": "fr",
    "français": "fr",
    "espanol": "es",
    "español": "es",
    "italiano": "it",
    "portugues": "pt",
    "português": "pt",
    "mandarin": "zh",
    "中文": "zh",
}

MODEL_SIZES: Tuple[str, ...] = ("tiny", "base", "small", "medium", "large-v2", "large-v3")
DEVICES: Tuple[str, ...] = ("cpu", "cuda", "auto")

DEFAULT_CONFIG_YAML = """\
# Goethe - German Sentence Audio Extractor
# Configuration file. The values below are the defaults.
# Relative paths are relative to the project folder.

# Audio settings (MP3 clips)
audio:
  padding_before: 0.03   # seconds of audio added before each match (0 - 5)
  padding_after: 0.03    # seconds of audio added after each match (0 - 5)
  bitrate: 192           # MP3 quality in kbps (32 - 320)

# Folders
paths:
  videos: ./videos
  transcripts: ./transcripts
  output: ./output       # MP3 clips are written to <output>/mp3/
  logs: ./logs           # a log file (goethe.log) is written here

# Speech recognition (faster-whisper)
speech:
  language: German       # German, English, French, Spanish, Italian, Portuguese, Chinese
                         # (language codes such as de, en, fr, es, it, pt, zh also work)
  model_size: small      # tiny | base | small | medium | large-v2 | large-v3
                         # small = good balance for a first run; bigger = slower, more accurate
  device: cpu            # cpu | cuda (NVIDIA GPU) | auto
  quiet: false           # true = less output while transcribing

# Matching
matching:
  fuzzy_threshold: 100   # 100 = exact matches only (recommended)
                         # 50 - 99 = if a term is not found exactly in a video,
                         #           also accept similar-sounding spellings

# Video file extensions that are processed (not case-sensitive)
video_formats:
  - mp4
  - mkv
  - avi
  - mov
"""

_KNOWN_KEYS: Dict[str, Tuple[str, ...]] = {
    "audio": ("padding_before", "padding_after", "bitrate"),
    "paths": ("videos", "transcripts", "output", "logs"),
    "speech": ("language", "model_size", "device", "quiet"),
    "matching": ("fuzzy_threshold",),
}
_KNOWN_TOP_LEVEL = tuple(_KNOWN_KEYS) + ("video_formats",)


@dataclass
class AudioConfig:
    padding_before: float = 0.03
    padding_after: float = 0.03
    bitrate: int = 192


@dataclass
class PathsConfig:
    videos: Path
    transcripts: Path
    output: Path
    logs: Path


@dataclass
class SpeechConfig:
    language_code: str = "de"
    language_name: str = "German"
    model_size: str = "small"
    device: str = "cpu"
    quiet: bool = False


@dataclass
class MatchingConfig:
    fuzzy_threshold: float = 100.0


@dataclass
class Config:
    root: Path
    audio: AudioConfig
    paths: PathsConfig
    speech: SpeechConfig
    matching: MatchingConfig
    video_formats: List[str]
    warnings: List[str] = field(default_factory=list)

    @property
    def mp3_folder(self) -> Path:
        return self.paths.output / "mp3"

    def ensure_folders(self) -> None:
        """Create all project folders that do not exist yet."""
        for folder in (
            self.paths.videos,
            self.paths.transcripts,
            self.paths.output,
            self.mp3_folder,
            self.paths.logs,
        ):
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigError(f"Cannot create folder {folder}: {exc}") from exc


def supported_languages_text() -> str:
    return ", ".join(f"{name} ({code})" for code, name in LANGUAGES.items())


def resolve_language(value: Any) -> Tuple[str, str]:
    """Return (code, name) for a language name or code, or raise ConfigError."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            "speech.language must be a language name such as 'German' or a code "
            f"such as 'de'. Supported: {supported_languages_text()}."
        )
    key = value.strip().casefold()
    code = key if key in LANGUAGES else None
    if code is None:
        by_name = {name.casefold(): c for c, name in LANGUAGES.items()}
        code = by_name.get(key) or _LANGUAGE_ALIASES.get(key)
    if code is None:
        raise ConfigError(
            f"Unsupported language {value!r} in speech.language. "
            f"Supported: {supported_languages_text()}."
        )
    return code, LANGUAGES[code]


def _section(raw: Dict[str, Any], name: str) -> Dict[str, Any]:
    value = raw.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(
            f"'{name}' in config.yaml must contain settings (key: value lines), "
            f"but it is {value!r}."
        )
    return value


def _number(
    section: Dict[str, Any],
    key: str,
    default: float,
    low: float,
    high: float,
    label: str,
    integer: bool = False,
) -> Any:
    value = section.get(key)
    if value is None:
        value = default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{label} must be a number, but it is {value!r}.")
    if integer and float(value) != int(value):
        raise ConfigError(f"{label} must be a whole number, but it is {value!r}.")
    if not low <= value <= high:
        raise ConfigError(f"{label} must be between {low} and {high}, but it is {value!r}.")
    return int(value) if integer else float(value)


def _path(section: Dict[str, Any], key: str, default: str, root: Path, label: str) -> Path:
    value = section.get(key)
    if value is None:
        value = default
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label} must be a folder path such as {default!r}, but it is {value!r}.")
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _video_formats(raw: Dict[str, Any]) -> List[str]:
    value = raw.get("video_formats")
    if value is None:
        value = ["mp4", "mkv", "avi", "mov"]
    if not isinstance(value, list) or not value:
        raise ConfigError("video_formats must be a list of file extensions, e.g. mp4, mkv, avi, mov.")
    formats: List[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip().lstrip("."):
            raise ConfigError(f"video_formats contains an invalid entry: {item!r}.")
        fmt = item.strip().lstrip(".").lower()
        if "/" in fmt or "\\" in fmt or " " in fmt:
            raise ConfigError(f"video_formats entry {item!r} must be a plain extension such as 'mp4'.")
        if fmt not in formats:
            formats.append(fmt)
    return formats


def parse_config(raw: Any, root: Path = PROJECT_ROOT) -> Config:
    """Validate the parsed YAML data and build a Config (missing values use defaults)."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must contain settings in 'key: value' form.")

    warnings: List[str] = []
    for key in raw:
        if key not in _KNOWN_TOP_LEVEL:
            warnings.append(f"Ignoring unknown setting '{key}' in config.yaml.")

    sections = {name: _section(raw, name) for name in _KNOWN_KEYS}
    for name, section in sections.items():
        for key in section:
            if key not in _KNOWN_KEYS[name]:
                warnings.append(
                    f"Ignoring unknown setting '{name}.{key}' in config.yaml (not used by this version)."
                )

    audio_raw, paths_raw = sections["audio"], sections["paths"]
    speech_raw, matching_raw = sections["speech"], sections["matching"]

    audio = AudioConfig(
        padding_before=_number(audio_raw, "padding_before", 0.03, 0, 5, "audio.padding_before"),
        padding_after=_number(audio_raw, "padding_after", 0.03, 0, 5, "audio.padding_after"),
        bitrate=_number(audio_raw, "bitrate", 192, 32, 320, "audio.bitrate", integer=True),
    )

    paths = PathsConfig(
        videos=_path(paths_raw, "videos", "./videos", root, "paths.videos"),
        transcripts=_path(paths_raw, "transcripts", "./transcripts", root, "paths.transcripts"),
        output=_path(paths_raw, "output", "./output", root, "paths.output"),
        logs=_path(paths_raw, "logs", "./logs", root, "paths.logs"),
    )

    language_code, language_name = resolve_language(
        speech_raw.get("language") if speech_raw.get("language") is not None else "German"
    )

    model_size = speech_raw.get("model_size")
    if model_size is None:
        model_size = "small"
    if not isinstance(model_size, str) or not model_size.strip():
        raise ConfigError(f"speech.model_size must be one of: {', '.join(MODEL_SIZES)}.")
    model_size = model_size.strip()
    if model_size == "large":
        model_size = "large-v3"
    if model_size not in MODEL_SIZES and not Path(model_size).expanduser().is_dir():
        raise ConfigError(
            f"speech.model_size {model_size!r} is not valid. Use one of: {', '.join(MODEL_SIZES)}."
        )

    device = speech_raw.get("device")
    if device is None:
        device = "cpu"
    if not isinstance(device, str) or device.strip().lower() not in DEVICES:
        raise ConfigError(f"speech.device must be one of: {', '.join(DEVICES)} (it is {device!r}).")

    quiet = speech_raw.get("quiet")
    if quiet is None:
        quiet = False
    if not isinstance(quiet, bool):
        raise ConfigError(f"speech.quiet must be true or false (it is {quiet!r}).")

    speech = SpeechConfig(
        language_code=language_code,
        language_name=language_name,
        model_size=model_size,
        device=device.strip().lower(),
        quiet=quiet,
    )

    matching = MatchingConfig(
        fuzzy_threshold=_number(
            matching_raw, "fuzzy_threshold", 100, 1, 100, "matching.fuzzy_threshold"
        )
    )

    return Config(
        root=root,
        audio=audio,
        paths=paths,
        speech=speech,
        matching=matching,
        video_formats=_video_formats(raw),
        warnings=warnings,
    )


def load_config(path: Any = None, root: Path = PROJECT_ROOT) -> Config:
    """Read and validate config.yaml. Raises ConfigError with a helpful message."""
    config_path = Path(path) if path is not None else root / CONFIG_FILENAME
    if not config_path.is_file():
        raise ConfigError(
            f"Config file not found: {config_path}. Run 'python3 setup.py' to create it."
        )
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_path.name} is not valid YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Cannot read {config_path}: {exc}") from exc
    return parse_config(raw, root)
