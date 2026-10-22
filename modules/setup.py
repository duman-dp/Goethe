#!/usr/bin/env python3
"""
Setup Module - creates everything needed for the first run.

It never overwrites existing files: config.yaml and sentences.txt are only
created when they are missing.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from modules.beautiful_logger import logger
from modules.config import (
    CONFIG_FILENAME,
    DEFAULT_CONFIG_YAML,
    PROJECT_ROOT,
    load_config,
)
from modules.errors import ConfigError

SENTENCES_FILENAME = "sentences.txt"

DEFAULT_SENTENCES = """\
# German words and phrases to find in your videos.
# One entry per line. Lines starting with # are ignored.
# Single words and whole phrases can be mixed.

# Single words
ich
du
heiße
wohne
Hobby

# Phrases
Ich heiße
Wie heißt du
Woher kommst du
Ich komme aus
Ich wohne in
"""

# (importable module name, pip package name)
REQUIRED_PACKAGES = (
    ("yaml", "pyyaml"),
    ("tqdm", "tqdm"),
    ("faster_whisper", "faster-whisper"),
)


class ProjectSetup:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else PROJECT_ROOT

    def create_default_files(self) -> None:
        for filename, content in (
            (CONFIG_FILENAME, DEFAULT_CONFIG_YAML),
            (SENTENCES_FILENAME, DEFAULT_SENTENCES),
        ):
            path = self.root / filename
            if path.exists():
                logger.info(f"Exists:  {filename}")
            else:
                path.write_text(content, encoding="utf-8")
                logger.success(f"Created: {filename}")

    def create_folders(self) -> None:
        """Create the project folders named in config.yaml."""
        config = load_config(root=self.root)
        for message in config.warnings:
            logger.warning(message)
        existing = {
            folder: folder.exists()
            for folder in (
                config.paths.videos,
                config.paths.transcripts,
                config.paths.output,
                config.mp3_folder,
                config.paths.logs,
            )
        }
        config.ensure_folders()
        for folder, existed in existing.items():
            label = self._display(folder)
            if existed:
                logger.info(f"Exists:  {label}/")
            else:
                logger.success(f"Created: {label}/")

    def _display(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def check_dependencies(self) -> bool:
        """Report problems with Python, ffmpeg and packages. Returns True if everything is fine."""
        all_ok = True

        version = sys.version_info
        if (version.major, version.minor) < (3, 8):
            logger.error(f"Python 3.8 or newer is required (you have {version.major}.{version.minor})")
            all_ok = False
        else:
            logger.success(f"Python {version.major}.{version.minor}.{version.micro}")

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            logger.warning("ffmpeg not found - install it with: sudo apt install ffmpeg")
            all_ok = False
        else:
            try:
                output = subprocess.run(
                    [ffmpeg, "-version"], capture_output=True, text=True, timeout=20
                ).stdout.splitlines()
                words = output[0].split() if output else []
                logger.success(f"ffmpeg {words[2] if len(words) > 2 else '(version unknown)'}")
            except (OSError, subprocess.SubprocessError):
                logger.warning("ffmpeg was found but could not be started")
                all_ok = False

        missing = []
        for module_name, pip_name in REQUIRED_PACKAGES:
            if importlib.util.find_spec(module_name) is None:
                missing.append(pip_name)
        if missing:
            logger.warning(f"Missing Python packages: {', '.join(missing)}")
            logger.info("Install them with: pip install -r requirements.txt")
            all_ok = False
        else:
            logger.success("Python packages: " + ", ".join(pip for _, pip in REQUIRED_PACKAGES))
        return all_ok

    def run_full_setup(self) -> bool:
        logger.title("Project Setup")
        logger.info("📁 Creating project files and folders...")
        self.create_default_files()
        try:
            self.create_folders()
        except ConfigError as exc:
            logger.error(str(exc))
            return False
        logger.blank()
        logger.info("🔍 Checking requirements...")
        ready = self.check_dependencies()
        self.show_next_steps(ready)
        return ready

    def show_next_steps(self, ready: bool = True) -> None:
        heading = "Setup complete!" if ready else "Setup finished - please fix the warnings above"
        logger.box(
            heading,
            [
                "1. Add your videos to the videos/ folder",
                "2. Write the words/phrases you want in sentences.txt",
                "3. Adjust config.yaml if you like (optional)",
                "4. Run: python3 main.py",
            ],
            emoji="✅" if ready else "⚠️",
        )


def run_setup() -> bool:
    return ProjectSetup().run_full_setup()


if __name__ == "__main__":
    sys.exit(0 if run_setup() else 1)
