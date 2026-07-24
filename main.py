#!/usr/bin/env python3
"""
🇩🇪 German Sentence Audio Extractor
Beautiful & Professional Version
"""

import sys
import yaml
from pathlib import Path
from modules.beautiful_logger import logger, Colors
from modules.setup import ProjectSetup  # ← ADD THIS

# Import modules
from modules.speech_recognition import SpeechRecognizer
from modules.sentence_matcher import SentenceMatcher
from modules.audio_extractor import AudioExtractor

def check_and_setup():
    """Check if setup is needed and run it"""
    config_file = Path("config.yaml")
    
    # If config doesn't exist or videos folder is empty, run setup
    if not config_file.exists():
        logger.info("First time setup detected! 🚀")
        logger.info("Creating project structure...")
        setup = ProjectSetup()
        setup.run_full_setup()
        return True
    
    # Also check if folders exist
    folders = ['videos', 'transcripts', 'output']
    missing_folders = [f for f in folders if not Path(f).exists()]
    
    if missing_folders:
        logger.info("Creating missing folders...")
        setup = ProjectSetup()
        setup.create_folders()
        return True
    
    return False

def load_config():
    """Load configuration"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        logger.error("config.yaml not found")
        logger.info("Running setup...")
        check_and_setup()
        return load_config()  # Try again
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    """Main function"""
    logger.title("German Sentence Audio Extractor")
    
    # ===== CHECK SETUP FIRST =====
    check_and_setup()
    print()
    # =============================
    
    # Load config
    config = load_config()
    if not config:
        return 1
    
    # Rest of the code continues...
    # ... (your existing main function code)

if __name__ == "__main__":
    sys.exit(main())
