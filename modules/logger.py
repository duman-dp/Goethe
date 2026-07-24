#!/usr/bin/env python3
"""
Clean Output Logger - Makes output professional and clear
"""

import sys
import time

class CleanLogger:
    """Clean, professional output logger"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.start_time = time.time()
    
    def header(self, text):
        """Print a header"""
        print()
        print("=" * 60)
        print(f"  {text}")
        print("=" * 60)
        print()
    
    def section(self, text):
        """Print a section title"""
        print(f"\n▸ {text}")
        print("-" * 40)
    
    def success(self, text):
        """Print success message"""
        print(f"  ✅ {text}")
    
    def info(self, text):
        """Print info message"""
        print(f"  ℹ️  {text}")
    
    def warning(self, text):
        """Print warning message"""
        print(f"  ⚠️  {text}")
    
    def error(self, text):
        """Print error message"""
        print(f"  ❌ {text}")
    
    def progress(self, current, total, text=""):
        """Print simple progress"""
        percent = (current / total) * 100
        bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
        print(f"\r  [{bar}] {percent:.0f}% {text}", end="")
        if current == total:
            print()
    
    def summary(self, items):
        """Print a clean summary"""
        print()
        print("┌" + "─" * 58 + "┐")
        print("│  📊 SUMMARY".ljust(59) + "│")
        print("├" + "─" * 58 + "┤")
        for key, value in items.items():
            print(f"│  {key}: {value}".ljust(59) + "│")
        print("└" + "─" * 58 + "┘")
        print()
    
    def result(self, message):
        """Print final result"""
        print()
        print("✨ " + message)
        print()
    
    def time_elapsed(self):
        """Show time elapsed"""
        elapsed = time.time() - self.start_time
        print(f"  ⏱️  Time: {elapsed:.1f}s")

# Global logger instance
logger = CleanLogger()
