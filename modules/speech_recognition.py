#!/usr/bin/env python3
"""
Speech Recognition Module
Converts video/audio speech to text with timestamps
"""

import time
import json
from pathlib import Path
from faster_whisper import WhisperModel
from tqdm import tqdm

class SpeechRecognizer:
    def __init__(self, config):
        self.config = config
        self.model_size = config.get('speech', {}).get('model_size', 'tiny')
        self.device = config.get('speech', {}).get('device', 'cpu')
        self.language = config.get('speech', {}).get('language', 'German')
        self.quiet = config.get('speech', {}).get('quiet', False)
        
        if not self.quiet:
            print(f"🧠 Loading whisper model: {self.model_size}")
            print(f"💻 Using device: {self.device}")
            print(f"🗣️ Language: {self.language}")
            print("⏳ Please wait... (first time may take longer)")
        
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
        if not self.quiet:
            print(f"🎤 Transcribing: {Path(video_path).name}")
            print("⏳ This may take a few minutes...")
            print("-" * 50)
        
        start_time = time.time()
        video_path = str(video_path)
        
        segments, info = self.model.transcribe(
            video_path,
            language="de",
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=True
        )
        
        if not self.quiet:
            print(f"📊 Language: {info.language} (confidence: {info.language_probability:.2f})")
            print()
        
        segments_list = []
        words_list = []
        full_text = []
        all_segments = []
        
        for segment in segments:
            all_segments.append(segment)
        
        if not self.quiet:
            pbar = tqdm(total=len(all_segments), desc="Processing", unit="segments")
        
        for segment in all_segments:
            segment_data = {
                'start': float(segment.start),
                'end': float(segment.end),
                'text': segment.text,
                'words': []
            }
            
            for word in segment.words:
                word_data = {
                    'start': float(word.start),
                    'end': float(word.end),
                    'word': word.word
                }
                segment_data['words'].append(word_data)
                words_list.append(word_data)
            
            segments_list.append(segment_data)
            full_text.append(segment.text)
            
            if not self.quiet:
                pbar.update(1)
                pbar.set_postfix({"segments": len(segments_list), "words": len(words_list)})
        
        if not self.quiet:
            pbar.close()
            print()
        
        result = {
            'segments': segments_list,
            'words': words_list,
            'text': ' '.join(full_text),
            'video_path': video_path,
            'processing_time': time.time() - start_time,
            'total_segments': len(segments_list),
            'total_words': len(words_list)
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
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        if not self.quiet:
            print(f"💾 Transcript saved: {output_path}")
            print(f"   Saved {len(transcript_data.get('segments', []))} segments")
            print(f"   Saved {len(transcript_data.get('words', []))} words")
        
        return output_path

if __name__ == "__main__":
    print("🧪 Testing speech recognition module...")
    print("✅ Module ready!")
