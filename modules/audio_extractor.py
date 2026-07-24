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
        self.padding_before = config.get('audio', {}).get('padding_before', 0.03)
        self.padding_after = config.get('audio', {}).get('padding_after', 0.03)
        self.bitrate = config.get('audio', {}).get('bitrate', 192)
        
        print(f"🎵 Audio extractor initialized")
        print(f"   Padding: {self.padding_before}s before, {self.padding_after}s after")
        print(f"   Quality: {self.bitrate} kbps")
        print()
    
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
        
        created_files = []
        
        for match in tqdm(matches, desc=f"Extracting from {video_path.name[:20]}...", unit="clip"):
            start = max(0, match['start'] - self.padding_before)
            end = match['end'] + self.padding_after
            duration = end - start
            
            sentence = match['sentence']
            safe_name = self.safe_filename(sentence)
            
            sentence_folder = output_folder / safe_name
            sentence_folder.mkdir(exist_ok=True)
            
            occurrence = match.get('occurrence', len(created_files) + 1)
            mp3_file = sentence_folder / f"{safe_name}_{occurrence:03d}.mp3"
            
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
        
        return created_files
    
    def extract_all(self, video_folder, matches_folder, output_folder):
        video_folder = Path(video_folder)
        matches_folder = Path(matches_folder)
        output_folder = Path(output_folder)
        
        match_file = matches_folder / "all_matches.json"
        
        if not match_file.exists():
            print("❌ No match file found: all_matches.json")
            return []
        
        with open(match_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_matches = data.get('matches', [])
        
        if not all_matches:
            print("❌ No matches found in all_matches.json")
            return []
        
        print(f"📄 Loaded {len(all_matches)} total matches from all videos")
        print()
        
        by_video = {}
        for match in all_matches:
            video_name = match.get('video', '')
            if video_name not in by_video:
                by_video[video_name] = []
            by_video[video_name].append(match)
        
        all_files = []
        
        for video_name, matches in by_video.items():
            print(f"🎬 Processing video: {video_name}")
            print(f"   {len(matches)} matches found in this video")
            
            video_candidates = list(video_folder.glob(f"*{video_name[:30]}*.*"))
            if not video_candidates:
                print(f"   ❌ Video not found for: {video_name}")
                continue
            
            video_path = video_candidates[0]
            print(f"   📁 Using: {video_path.name}")
            print()
            
            files = self.extract_audio(video_path, matches, output_folder)
            all_files.extend(files)
            print()
        
        return all_files

if __name__ == "__main__":
    print("🧪 Testing audio extractor...")
    print("✅ Module ready!")
