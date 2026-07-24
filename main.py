#!/usr/bin/env python3
"""
Goethe - German Sentence Audio Extractor
Professional & Beautiful Version
"""

import sys
import yaml
from pathlib import Path
from modules.beautiful_logger import logger, Colors
from modules.setup import ProjectSetup

# Import modules
from modules.speech_recognition import SpeechRecognizer
from modules.sentence_matcher import SentenceMatcher
from modules.audio_extractor import AudioExtractor

def check_and_setup():
    """Check if setup is needed and run it"""
    config_file = Path("config.yaml")
    
    if not config_file.exists():
        logger.info("First time setup detected! 🚀")
        logger.info("Creating project structure...")
        setup = ProjectSetup()
        setup.run_full_setup()
        return True
    
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
        return load_config()
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    """Main function"""
    logger.title("Goethe - German Sentence Audio Extractor")
    
    check_and_setup()
    print()
    
    config = load_config()
    if not config:
        return 1
    
    folders = {
        'videos': Path(config.get('paths', {}).get('videos', './videos')),
        'transcripts': Path(config.get('paths', {}).get('transcripts', './transcripts')),
        'output': Path(config.get('paths', {}).get('output', './output'))
    }
    
    for folder in folders.values():
        folder.mkdir(exist_ok=True)
    
    # === PHASE 2: Speech Recognition ===
    logger.step("Speech Recognition", "🎤")
    
    video_files = list(folders['videos'].glob("*.mp4")) + \
                  list(folders['videos'].glob("*.mkv")) + \
                  list(folders['videos'].glob("*.avi"))
    
    if not video_files:
        logger.error("No videos found in videos/ folder")
        logger.info("Please add .mp4 or .mkv files to the videos/ folder")
        return 1
    
    logger.info(f"Found {len(video_files)} video(s)")
    
    for video in video_files[:3]:
        print(f"     {Colors.DIM}📹{Colors.RESET} {video.name}")
    if len(video_files) > 3:
        print(f"     {Colors.DIM}... and {len(video_files) - 3} more{Colors.RESET}")
    
    recognizer = SpeechRecognizer(config)
    processed = 0
    skipped = 0
    
    for video in video_files:
        transcript_path = folders['transcripts'] / f"{video.stem}.json"
        
        if transcript_path.exists():
            logger.info(f"⏩ Skipping: {video.name}")
            skipped += 1
            continue
        
        logger.info(f"🎤 Processing: {video.name}")
        transcript = recognizer.transcribe_video(video)
        recognizer.save_transcript(transcript, transcript_path)
        processed += 1
    
    if processed > 0:
        logger.success(f"Processed {processed} video(s)")
    if skipped > 0:
        logger.info(f"Skipped {skipped} video(s) (transcripts already exist)")
    
    # === PHASE 3: Sentence Matching ===
    logger.step("Sentence Matching", "🔎")
    
    sentences_file = Path("sentences.txt")
    if not sentences_file.exists():
        logger.warning("sentences.txt not found")
        logger.info("Create sentences.txt with German sentences to search")
    else:
        matcher = SentenceMatcher(config)
        sentences = matcher.load_sentences(sentences_file)
        
        if sentences:
            logger.info(f"Searching for {len(sentences)} sentences")
            
            transcript_files = list(folders['transcripts'].glob("*.json"))
            all_matches = []
            
            for transcript_file in transcript_files:
                logger.info(f"📄 {transcript_file.name}")
                matches = matcher.find_matches(transcript_file, sentences)
                all_matches.extend(matches)
                
                matches_file = folders['output'] / f"{transcript_file.stem}_matches.json"
                matcher.save_matches(matches, matches_file)
            
            if all_matches:
                logger.success(f"Found {len(all_matches)} matches!")
                print()
                print("  " + "┌" + "─" * 66 + "┐")
                print(f"  │ {Colors.BOLD}📝 Matches Found{Colors.RESET}".ljust(68) + "│")
                print("  " + "├" + "─" * 66 + "┤")
                
                for i, match in enumerate(all_matches, 1):
                    sentence = match['sentence']
                    if len(sentence) > 45:
                        sentence = sentence[:42] + "..."
                    
                    if match['score'] >= 90:
                        emoji = "🌟"
                        color = Colors.GREEN
                    elif match['score'] >= 70:
                        emoji = "📘"
                        color = Colors.YELLOW
                    else:
                        emoji = "📄"
                        color = Colors.DIM
                    
                    print(f"  │  {color}{emoji} {i:2d}. {sentence}{Colors.RESET}")
                    print(f"  │     {Colors.DIM}⏱️  {match['start']:.1f}s  •  Score: {match['score']}%{Colors.RESET}")
                    
                    if i == 5 and len(all_matches) > 5:
                        print(f"  │  {Colors.DIM}... and {len(all_matches) - 5} more{Colors.RESET}")
                        break
                
                print("  " + "└" + "─" * 66 + "┘")
            else:
                logger.warning("No matches found")
                logger.info("Try different sentences or lower the threshold in config.yaml")
    
    # === PHASE 4: Audio Extraction ===
    logger.step("Audio Extraction", "🎵")
    
    match_files = list(folders['output'].glob("*_matches.json"))
    
    if match_files:
        extractor = AudioExtractor(config)
        mp3_folder = folders['output'] / "mp3"
        
        extracted = extractor.extract_all(
            folders['videos'],
            folders['output'],
            mp3_folder
        )
        
        if extracted:
            logger.success(f"Created {len(extracted)} MP3 files!")
            print()
            print("  " + "┌" + "─" * 66 + "┐")
            print(f"  │ {Colors.BOLD}🎵 MP3 Files Created{Colors.RESET}".ljust(68) + "│")
            print("  " + "├" + "─" * 66 + "┤")
            
            for i, mp3 in enumerate(extracted[:5], 1):
                print(f"  │  {i}. {Colors.CYAN}{mp3.parent.name}{Colors.RESET}/{mp3.name}")
            
            if len(extracted) > 5:
                print(f"  │  {Colors.DIM}... and {len(extracted) - 5} more{Colors.RESET}")
            
            print("  " + "└" + "─" * 66 + "┘")
            print()
            
            logger.info(f"📁 Saved to: {mp3_folder}")
        else:
            logger.warning("No MP3 files created")
    else:
        logger.warning("No match files found - run Phase 3 first")
    
    # === Final Summary ===
    logger.divider()
    
    summary_items = {
        "🎬 Videos": len(video_files),
        "📝 Transcripts": len(list(folders['transcripts'].glob("*.json"))),
        "🔎 Matches": len(all_matches) if 'all_matches' in locals() else 0,
        "🎵 MP3 Files": len(extracted) if 'extracted' in locals() else 0,
        "📁 Output": str(folders['output'] / "mp3")
    }
    
    logger.box("Summary", summary_items)
    logger.footer()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
