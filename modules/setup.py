#!/usr/bin/env python3
"""
Setup Module - Creates everything needed for first run
"""

import sys
import subprocess
from pathlib import Path
from modules.beautiful_logger import logger, Colors

class ProjectSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.folders = ['videos', 'transcripts', 'output', 'logs', 'output/mp3']
    
    def create_folders(self):
        logger.info("📁 Creating project folders...")
        for folder in self.folders:
            folder_path = self.project_root / folder
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"     {Colors.GREEN}✅ Created:{Colors.RESET} {folder}/")
            else:
                print(f"     {Colors.DIM}ℹ️  Exists:{Colors.RESET} {folder}/")
        print()
        return True
    
    def check_dependencies(self):
        logger.info("🔍 Checking dependencies...")
        
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            print(f"     {Colors.RED}❌ Python 3.8+ required (you have {python_version.major}.{python_version.minor}){Colors.RESET}")
            return False
        print(f"     {Colors.GREEN}✅ Python:{Colors.RESET} {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0].split(' ')[2]
                print(f"     {Colors.GREEN}✅ FFmpeg:{Colors.RESET} {version}")
            else:
                print(f"     {Colors.YELLOW}⚠️  FFmpeg not found{Colors.RESET}")
                print(f"     {Colors.DIM}   Install: sudo apt install ffmpeg{Colors.RESET}")
        except FileNotFoundError:
            print(f"     {Colors.YELLOW}⚠️  FFmpeg not found{Colors.RESET}")
            print(f"     {Colors.DIM}   Install: sudo apt install ffmpeg{Colors.RESET}")
        
        print()
        return True
    
    def _create_config(self):
        config_content = """# Goethe - German Sentence Audio Extractor
# Configuration File

# Audio settings
audio:
  padding_before: 0.03
  padding_after: 0.03
  output_format: mp3
  bitrate: 192

# Paths
paths:
  videos: ./videos
  transcripts: ./transcripts
  output: ./output
  logs: ./logs

# Speech recognition
speech:
  language: German
  model_size: tiny
  device: cpu
  quiet: false

# Matching
matching:
  fuzzy_threshold: 60

# Video formats
video_formats:
  - mp4
  - mkv
  - avi
  - mov
"""
        config_path = self.project_root / 'config.yaml'
        if not config_path.exists():
            with open(config_path, 'w') as f:
                f.write(config_content)
            print(f"     {Colors.GREEN}✅ Created:{Colors.RESET} config.yaml")
        else:
            print(f"     {Colors.DIM}ℹ️  Exists:{Colors.RESET} config.yaml")
        return config_path
    
    def _create_sentences(self):
        sentences_content = """# German Words and Phrases to Search
# Mix single words AND phrases!
# Add one per line

# Single words (extract just the word)
ich
du
heiße
wohne
hobby

# Phrases (extract just the phrase)
Ich heiße
Wie heißt du
Woher kommst du
Ich komme aus
Ich wohne in
"""
        sentences_path = self.project_root / 'sentences.txt'
        if not sentences_path.exists():
            with open(sentences_path, 'w', encoding='utf-8') as f:
                f.write(sentences_content)
            print(f"     {Colors.GREEN}✅ Created:{Colors.RESET} sentences.txt (with examples)")
        else:
            print(f"     {Colors.DIM}ℹ️  Exists:{Colors.RESET} sentences.txt")
        return sentences_path
    
    def _check_requirements(self):
        req_path = self.project_root / 'requirements.txt'
        if not req_path.exists():
            req_content = """faster-whisper==1.0.3
pyyaml==6.0.2
ffmpeg-python==0.2.0
pandas==2.2.2
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.1
ctranslate2==4.4.0
requests==2.32.3
huggingface_hub==0.24.0
tokenizers==0.19.1
tqdm==4.66.4
"""
            with open(req_path, 'w') as f:
                f.write(req_content)
            print(f"     {Colors.GREEN}✅ Created:{Colors.RESET} requirements.txt")
        else:
            print(f"     {Colors.DIM}ℹ️  Exists:{Colors.RESET} requirements.txt")
        return req_path
    
    def run_full_setup(self):
        print()
        logger.title("Project Setup")
        self.create_folders()
        self._create_config()
        self._create_sentences()
        self._check_requirements()
        self.check_dependencies()
        self.show_next_steps()
        return True
    
    def show_next_steps(self):
        print()
        print("  " + "┌" + "─" * 66 + "┐")
        print(f"  │ {Colors.BOLD}{Colors.GREEN}✅ Setup Complete!{Colors.RESET}".ljust(68) + "│")
        print("  " + "├" + "─" * 66 + "┤")
        print(f"  │  {Colors.CYAN}📹 1. Add videos to:{Colors.RESET} videos/")
        print(f"  │  {Colors.CYAN}📝 2. Add sentences to:{Colors.RESET} sentences.txt")
        print(f"  │  {Colors.CYAN}⚙️  3. Edit config:{Colors.RESET} config.yaml (optional)")
        print(f"  │  {Colors.CYAN}🚀 4. Run:{Colors.RESET} python3 main.py")
        print("  " + "└" + "─" * 66 + "┘")
        print()

def run_setup():
    setup = ProjectSetup()
    return setup.run_full_setup()

if __name__ == "__main__":
    run_setup()
