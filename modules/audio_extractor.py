#!/usr/bin/env python3
"""
Audio Extractor Module
Extracts MP3 clips from video using timestamps
"""

import json
import subprocess
from pathlib import Path
from tqdm import tqdm

class AudioExtractor:
    def __init__(self, config):
        self.config = config
        self.padding_before = config.get('audio', {}).get('padding_before', 0.5)
        self.padding_after = config.get('audio', {}).get('padding_after', 0.5)
        self.bitrate = config.get('audio', {}).get('bitrate', 192)
        
        print(f"🎵 Audio extractor initialized")
        print(f"   Padding: {self.padding_before}s before, {self.padding_after}s after")
        print(f"   Quality: {self.bitrate} kbps")
        print()
    
    def load_matches(self, matches_file):
        if not Path(matches_file).exists():
            print(f"❌ Matches file not found: {matches_file}")
            return []
        
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        print(f"📄 Loaded {len(matches)} matches from {Path(matches_file).name}")
        return matches
    
    def safe_filename(self, text):
        filename = text.replace(' ', '_')
        filename = ''.join(c for c in filename if c.isalnum() or c in '_-')
        if len(filename) > 50:
            filename = filename[:50]
        if not filename:
            filename = "sentence"
        return filename
    
    def extract_audio(self, video_path, matches, output_folder):
        video_path = Path(video_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        if not video_path.exists():
            print(f"❌ Video not found: {video_path}")
            return []
        
        print(f"🎬 Extracting audio from: {video_path.name}")
        print(f"📁 Output folder: {output_folder}")
        print("-" * 50)
        
        created_files = []
        
        for i, match in enumerate(tqdm(matches, desc="Extracting MP3s", unit="clip"), 1):
            start = max(0, match['start'] - self.padding_before)
            end = match['end'] + self.padding_after
            duration = end - start
            
            sentence = match['sentence']
            safe_name = self.safe_filename(sentence)
            
            sentence_folder = output_folder / safe_name
            sentence_folder.mkdir(exist_ok=True)
            
            mp3_file = sentence_folder / f"{safe_name}_{i:03d}.mp3"
            
            try:
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-ss', str(start),
                    '-t', str(duration),
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-ab', f'{self.bitrate}k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-y',
                    str(mp3_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    created_files.append(mp3_file)
                else:
                    print(f"   ❌ Error for '{sentence[:30]}...'")
                
            except Exception as e:
                print(f"   ❌ Error for '{sentence[:30]}...': {e}")
        
        print("-" * 50)
        print(f"✅ Created {len(created_files)} MP3 files")
        return created_files
    
    def extract_all(self, video_folder, matches_folder, output_folder):
        video_folder = Path(video_folder)
        matches_folder = Path(matches_folder)
        output_folder = Path(output_folder)
        
        match_files = list(matches_folder.glob("*_matches.json"))
        
        if not match_files:
            print("❌ No match files found")
            return []
        
        all_files = []
        
        for match_file in match_files:
            print(f"📄 Processing matches: {match_file.name}")
            print("-" * 40)
            
            matches = self.load_matches(match_file)
            
            if not matches:
                print("   No matches to process")
                continue
            
            video_name = match_file.stem.replace('_matches', '')
            video_candidates = list(video_folder.glob(f"*{video_name[:20]}*.*"))
            
            if not video_candidates:
                print(f"   ❌ Video not found for: {video_name}")
                continue
            
            video_path = video_candidates[0]
            files = self.extract_audio(video_path, matches, output_folder)
            all_files.extend(files)
            print()
        
        return all_files

if __name__ == "__main__":
    print("🧪 Testing audio extractor...")
    print("✅ Module ready!")
