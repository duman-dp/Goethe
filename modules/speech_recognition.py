#!/usr/bin/env python3
"""
Speech Recognition Module
Converts video/audio speech to text with timestamps
Uses faster-whisper for German language
"""

import os
import time
import json
from pathlib import Path
from faster_whisper import WhisperModel
from tqdm import tqdm

class SpeechRecognizer:
    """
    Speech recognizer using faster-whisper
    Converts audio to text with word timestamps
    """
    
    def __init__(self, config):
        """
        Initialize the speech recognizer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.model_size = config.get('speech', {}).get('model_size', 'tiny')
        self.device = config.get('speech', {}).get('device', 'cpu')
        self.language = config.get('speech', {}).get('language', 'German')
        
        # ===== ADD THIS LINE =====
        self.quiet = config.get('speech', {}).get('quiet', False)
        # =========================
        
        # Only show these messages if not quiet
        if not self.quiet:
            print(f"🧠 Loading whisper model: {self.model_size}")
            print(f"💻 Using device: {self.device}")
            print(f"🗣️ Language: {self.language}")
            print("⏳ Please wait... (first time may take longer)")
        
        # Load the model
        start_time = time.time()
        self.model = WhisperModel(
            model_size_or_path=self.model_size,
            device=self.device,
            compute_type="int8"
        )
        
        if not self.quiet:
            print(f"✅ Model loaded in {time.time() - start_time:.2f} seconds")
            print()
    
    def transcribe_video(self, video_path):
        """
        Transcribe a video file to text with timestamps
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with transcription results
        """
        if not self.quiet:
            print(f"🎤 Transcribing: {Path(video_path).name}")
            print("⏳ This may take a few minutes...")
            print("-" * 50)
        
        start_time = time.time()
        
        # Convert video path to string
        video_path = str(video_path)
        
        # Run transcription
        segments, info = self.model.transcribe(
            video_path,
            language="de",
            beam_size=5,
            word_timestamps=True,
            vad_filter=True
        )
        
        if not self.quiet:
            print(f"📊 Language: {info.language} (confidence: {info.language_probability:.2f})")
            print()
        
        # Collect all segments and words
        segments_list = []
        words_list = []
        full_text = []
        
        if not self.quiet:
            print("📝 Processing segments...")
        
        # Use tqdm for progress bar
        segment_count = 0
        with tqdm(desc="Processing", unit="segments", disable=self.quiet) as pbar:
            for segment in segments:
                segment_data = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                    'words': []
                }
                
                # Get word-level timestamps
                for word in segment.words:
                    word_data = {
                        'start': word.start,
                        'end': word.end,
                        'word': word.word
                    }
                    segment_data['words'].append(word_data)
                    words_list.append(word_data)
                
                segments_list.append(segment_data)
                full_text.append(segment.text)
                segment_count += 1
                pbar.update(1)
                pbar.set_postfix({"segments": segment_count, "words": len(words_list)})
        
        print()  # New line after progress bar
        
        result = {
            'segments': segments_list,
            'words': words_list,
            'text': ' '.join(full_text),
            'video_path': video_path,
            'processing_time': time.time() - start_time
        }
        
        if not self.quiet:
            print("-" * 50)
            print(f"✅ Transcription complete!")
            print(f"   ⏱️  Time: {result['processing_time']:.2f} seconds")
            print(f"   📝 Segments: {len(segments_list)}")
            print(f"   📝 Words: {len(words_list)}")
            print("-" * 50)
            print()
        
        return result
    
    def save_transcript(self, transcript_data, output_path):
        """
        Save transcript to JSON file
        
        Args:
            transcript_data: Dictionary with transcription results
            output_path: Path to save JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        if not self.quiet:
            print(f"💾 Transcript saved: {output_path}")
        return output_path

if __name__ == "__main__":
    print("🧪 Testing speech recognition module...")
    print("✅ Module ready!")
