#!/usr/bin/env python3
"""
Quick Setup Script for New Users
Run this first: python3 setup.py

Creates the project folders, config.yaml and sentences.txt (only if they are
missing) and checks that Python, ffmpeg and the required packages are available.
"""

import sys

from modules.setup import ProjectSetup


def main() -> int:
    ready = ProjectSetup().run_full_setup()
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
