#!/usr/bin/env python3
"""
Sentence Matcher Module
Finds sentences in transcripts with fuzzy matching
"""

import json
import re
from pathlib import Path
from fuzzywuzzy import fuzz
from tqdm import tqdm

class SentenceMatcher:
    """Find sentences in transcripts with fuzzy matching"""
    
    def __init__(self, config):
        """Initialize matcher with config"""
        self.config = config
        self.threshold = config.get('matching', {}).get('fuzzy_threshold', 85)
        print(f"🔍 Sentence matcher initialized")
        print(f"   Match threshold: {self.threshold}%")
    
    def clean_text(self, text):
        """Clean text for comparison"""
        # Remove extra spaces
        text = ' '.join(text.split())
        # Remove punctuation for better matching
        text = re.sub(r'[.,!?;:]', '', text)
        # Lowercase for comparison
        text = text.lower()
        return text
    
    def load_sentences(self, sentences_file):
        """Load sentences from file"""
        if not Path(sentences_file).exists():
            print(f"❌ Sentences file not found: {sentences_file}")
            return []
        
        with open(sentences_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by lines and remove empty
        sentences = [s.strip() for s in content.split('\n') if s.strip()]
        
        print(f"📄 Loaded {len(sentences)} sentences from {sentences_file}")
        return sentences
    
    def find_matches(self, transcript_file, sentences):
        """
        Find matches for sentences in transcript
        
        Returns:
            List of matches with timestamps
        """
        print(f"🔎 Searching for {len(sentences)} sentences...")
        print(f"📁 Using transcript: {Path(transcript_file).name}")
        print("-" * 50)
        
        # Load transcript
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        
        segments = transcript.get('segments', [])
        matches = []
        
        print(f"📝 Checking {len(segments)} segments...")
        print()
        
        # For each sentence, search in segments
        for sentence in tqdm(sentences, desc="Searching sentences"):
            sentence_clean = self.clean_text(sentence)
            best_match = None
            best_score = 0
            best_segment = None
            
            for segment in segments:
                segment_text = self.clean_text(segment['text'])
                
                # Calculate similarity
                score = fuzz.ratio(sentence_clean, segment_text)
                
                if score > best_score:
                    best_score = score
                    best_segment = segment
            
            # If match found above threshold
            if best_segment and best_score >= self.threshold:
                match_data = {
                    'sentence': sentence,
                    'match_text': best_segment['text'],
                    'score': best_score,
                    'start': best_segment['start'],
                    'end': best_segment['end'],
                    'words': best_segment.get('words', [])
                }
                matches.append(match_data)
                print(f"   ✅ Found: '{sentence[:40]}...' (score: {best_score}%)")
            else:
                print(f"   ❌ Not found: '{sentence[:40]}...'")
        
        print()
        print(f"✅ Found {len(matches)} matches out of {len(sentences)} sentences")
        return matches
    
    def save_matches(self, matches, output_file):
        """Save matches to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Matches saved: {output_path}")
        return output_path
    
    def print_summary(self, matches):
        """Print summary of matches"""
        print()
        print("=" * 60)
        print("📊 MATCH SUMMARY")
        print("=" * 60)
        
        if not matches:
            print("❌ No matches found!")
            print()
            print("💡 Suggestions:")
            print("   1. Check if sentences exist in the video")
            print("   2. Try simpler sentences")
            print("   3. Lower the threshold in config.yaml")
            return
        
        print(f"✅ Total matches: {len(matches)}")
        print()
        print("📝 Matches found:")
        print("-" * 60)
        
        for i, match in enumerate(matches, 1):
            print(f"{i}. '{match['sentence'][:50]}...'")
            print(f"   📍 Match: {match['match_text'][:50]}...")
            print(f"   ⏱️  {match['start']:.2f}s - {match['end']:.2f}s")
            print(f"   🎯 Score: {match['score']}%")
            print()

if __name__ == "__main__":
    print("🧪 Testing sentence matcher...")
    print("✅ Module ready!")
