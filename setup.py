#!/usr/bin/env python3
"""
Quick Setup Script for New Users
Run this first: python3 setup.py
"""

import sys
from pathlib import Path
from modules.setup import ProjectSetup

def main():
    print()
    print("  " + "=" * 68)
    print("  " + "  🚀  Goethe - German Sentence Audio Extractor Setup")
    print("  " + "=" * 68)
    print()
    
    setup = ProjectSetup()
    setup.run_full_setup()
    
    print()
    print("  " + "=" * 68)
    print("  " + "  ✨  Setup complete! Run: python3 main.py")
    print("  " + "=" * 68)
    print()

if __name__ == "__main__":
    main()
