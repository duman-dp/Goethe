#!/usr/bin/env python3
"""
Beautiful Output Logger - Professional & Colorful
"""

import sys
import time
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    WHITE = '\033[97m'

class BeautifulLogger:
    def __init__(self):
        self.start_time = time.time()
        self.step_count = 0
        self.width = 70
    
    def _line(self, char="─", length=None):
        if length is None:
            length = self.width
        print(f"  {char * length}")
    
    def title(self, text):
        print()
        print("  " + "╔" + "═" * (self.width - 2) + "╗")
        print("  " + "║" + " " * (self.width - 2) + "║")
        
        title_text = f"📚 {text} 📚"
        padding = self.width - len(title_text) - 4
        left_pad = padding // 2
        right_pad = padding - left_pad
        print(f"  ║{Colors.BOLD}{Colors.CYAN}{' ' * left_pad}{title_text}{' ' * right_pad}{Colors.RESET}║")
        
        print("  " + "║" + " " * (self.width - 2) + "║")
        print("  " + "╚" + "═" * (self.width - 2) + "╝")
        print()
    
    def step(self, text, emoji="📌"):
        self.step_count += 1
        print()
        print(f"  {Colors.BOLD}{Colors.BLUE}┌{''.join(['─'] * (self.width - 2))}┐{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.BLUE}│{Colors.RESET}  {Colors.BOLD}{emoji} Step {self.step_count}: {text}{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.BLUE}└{''.join(['─'] * (self.width - 2))}┘{Colors.RESET}")
    
    def info(self, text, emoji="ℹ️"):
        print(f"  {Colors.DIM}{emoji}{Colors.RESET} {text}")
    
    def success(self, text, emoji="✅"):
        print(f"  {Colors.GREEN}{emoji}{Colors.RESET} {text}")
    
    def warning(self, text, emoji="⚠️"):
        print(f"  {Colors.YELLOW}{emoji}{Colors.RESET} {text}")
    
    def error(self, text, emoji="❌"):
        print(f"  {Colors.RED}{emoji}{Colors.RESET} {text}")
    
    def progress_bar(self, current, total, text=""):
        percent = (current / total) * 100
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)
        color = Colors.GREEN if percent < 70 else Colors.YELLOW if percent < 90 else Colors.RED
        print(f"\r  {color}{bar}{Colors.RESET} {percent:3.0f}% {text}", end="")
        if current == total:
            print()
    
    def box(self, title, items):
        print()
        print("  " + "┌" + "─" * (self.width - 2) + "┐")
        print(f"  │ {Colors.BOLD}{Colors.CYAN}📊 {title}{Colors.RESET}".ljust(self.width - 1) + "│")
        print("  " + "├" + "─" * (self.width - 2) + "┤")
        
        for key, value in items.items():
            key_str = str(key)
            value_str = str(value)
            if len(key_str) > 20:
                key_str = key_str[:17] + "..."
            if len(value_str) > 20:
                value_str = value_str[:17] + "..."
            
            line = f"  │  {key_str}:".ljust(25) + f"{Colors.GREEN}{value_str}{Colors.RESET}".ljust(self.width - 25)
            print(line)
        
        print("  " + "└" + "─" * (self.width - 2) + "┘")
        print()
    
    def divider(self):
        print(f"  {Colors.DIM}{'─' * self.width}{Colors.RESET}")
    
    def footer(self):
        print()
        print("  " + "┌" + "─" * (self.width - 2) + "┐")
        print(f"  │ {Colors.BOLD}{Colors.GREEN}✨ Processing Complete!{Colors.RESET}".ljust(self.width - 1) + "│")
        print("  " + "└" + "─" * (self.width - 2) + "┘")
        
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            time_str = f"{elapsed:.1f} seconds"
        elif elapsed < 3600:
            time_str = f"{elapsed/60:.1f} minutes"
        else:
            time_str = f"{elapsed/3600:.1f} hours"
        print(f"  {Colors.DIM}⏱️  Total time: {time_str}{Colors.RESET}")
        print()

logger = BeautifulLogger()
