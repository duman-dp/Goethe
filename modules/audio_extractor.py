#!/usr/bin/env python3
"""
Audio Extractor Module
Extracts MP3 clips from video using timestamps
Uses FFmpeg for audio processing
"""

import json
import subprocess
import os
from pathlib import Path
from tqdm import tqdm

class AudioExtractor:
    """Extract audio clips from video files"""
    
    def __init__(self, config):
        """Initialize audio extractor with config"""
        self.config = config
        self.padding_before = config.get('audio', {}).get('padding_before', 0.5)
        self.padding_after = config.get('audio', {}).get('padding_after', 0.5)
        self.bitrate = config.get('audio', {}).get('bitrate', 192)
        self.output_format = config.get('audio', {}).get('output_format', 'mp3')
        
        print(f"🎵 Audio extractor initialized")
        print(f"   Padding: {self.padding_before}s before, {self.padding_after}s after")
        print(f"   Quality: {self.bitrate} kbps")
        print()
    
    def load_matches(self, matches_file):
        """Load matches from JSON file"""
        if not Path(matches_file).exists():
            print(f"❌ Matches file not found: {matches_file}")
            return []
        
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        print(f"📄 Loaded {len(matches)} matches from {Path(matches_file).name}")
        return matches
    
    def safe_filename(self, text):
        """
        Convert text to safe filename for Linux
        Removes special characters and spaces
        """
        # Replace spaces with underscores
        filename = text.replace(' ', '_')
        # Remove special characters (keep letters, numbers, underscore, hyphen)
        filename = ''.join(c for c in filename if c.isalnum() or c in '_-')
        # Limit length
        if len(filename) > 50:
            filename = filename[:50]
        # If empty, use default name
        if not filename:
            filename = "sentence"
        return filename
    
    def extract_audio(self, video_path, matches, output_folder):
        """
        Extract audio clips for all matches
        
        Args:
            video_path: Path to video file
            matches: List of matches with timestamps
            output_folder: Where to save MP3 files
        
        Returns:
            List of created MP3 files
        """
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
        
        # Use tqdm for progress bar
        for i, match in enumerate(tqdm(matches, desc="Extracting MP3s", unit="clip"), 1):
            # Get timestamps with padding
            start = max(0, match['start'] - self.padding_before)
            end = match['end'] + self.padding_after
            duration = end - start
            
            # Create safe filename from sentence
            sentence = match['sentence']
            safe_name = self.safe_filename(sentence)
            
            # Create folder for this sentence
            sentence_folder = output_folder / safe_name
            sentence_folder.mkdir(exist_ok=True)
            
            # Create MP3 filename with counter
            mp3_file = sentence_folder / f"{safe_name}_{i:03d}.mp3"
            
            # Extract audio using FFmpeg
            try:
                self._extract_with_ffmpeg(
                    video_path, 
                    mp3_file, 
                    start, 
                    duration
                )
                created_files.append(mp3_file)
                
                # Show success (only if not in tqdm)
                if i % 5 == 0 or i == len(matches):
                    print(f"   📁 Created: {mp3_file.parent.name}/{mp3_file.name}")
                
            except Exception as e:
                print(f"   ❌ Error for '{sentence[:30]}...': {e}")
        
        print("-" * 50)
        print(f"✅ Created {len(created_files)} MP3 files")
        return created_files
    
    def _extract_with_ffmpeg(self, video_path, output_path, start, duration):
        """
        Extract audio using FFmpeg
        
        Args:
            video_path: Input video file
            output_path: Output MP3 file
            start: Start time in seconds
            duration: Duration in seconds
        """
        # FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),           # Input file
            '-ss', str(start),               # Start time
            '-t', str(duration),             # Duration
            '-vn',                           # No video
            '-acodec', 'libmp3lame',         # MP3 codec
            '-ab', f'{self.bitrate}k',       # Bitrate
            '-ar', '44100',                  # Sample rate (44.1 kHz)
            '-ac', '2',                      # Stereo
            '-y',                            # Overwrite if exists
            str(output_path)                 # Output file
        ]
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr[:200]}")
    
    def extract_all(self, video_folder, matches_folder, output_folder):
        """
        Extract audio for all videos and matches
        
        Args:
            video_folder: Folder with videos
            matches_folder: Folder with match JSON files
            output_folder: Where to save MP3s
        """
        video_folder = Path(video_folder)
        matches_folder = Path(matches_folder)
        output_folder = Path(output_folder)
        
        # Find all match files
        match_files = list(matches_folder.glob("*_matches.json"))
        
        if not match_files:
            print("❌ No match files found in:", matches_folder)
            print("💡 Run Phase 3 first to create matches")
            return []
        
        all_files = []
        
        for match_file in match_files:
            print(f"📄 Processing matches: {match_file.name}")
            print("-" * 40)
            
            # Load matches
            matches = self.load_matches(match_file)
            
            if not matches:
                print("   No matches to process")
                continue
            
            # Find video file (match file name without _matches)
            video_name = match_file.stem.replace('_matches', '')
            video_candidates = list(video_folder.glob(f"{video_name}.*"))
            
            # Also try with original filename
            if not video_candidates:
                # Try to find any video that contains the name
                video_candidates = list(video_folder.glob(f"*{video_name[:20]}*.*"))
            
            if not video_candidates:
                print(f"   ❌ Video not found for: {video_name}")
                print(f"   Available videos: {[v.name for v in video_folder.glob('*')]}")
                continue
            
            video_path = video_candidates[0]
            
            # Extract audio
            print()
            files = self.extract_audio(video_path, matches, output_folder)
            all_files.extend(files)
            print()
        
        return all_files

if __name__ == "__main__":
    print("🧪 Testing audio extractor...")
    print("✅ Module ready!")
