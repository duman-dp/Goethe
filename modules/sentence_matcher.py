#!/usr/bin/env python3
"""
Sentence Matcher Module
EXACT word/phrase extraction with word-level timestamps
"""

import json
import re
from pathlib import Path
from fuzzywuzzy import fuzz
from tqdm import tqdm

class SentenceMatcher:
    def __init__(self, config):
        self.config = config
        self.threshold = config.get('matching', {}).get('fuzzy_threshold', 60)
        
        print(f"🔍 Sentence matcher initialized")
        print(f"   Mode: EXACT word/phrase extraction")
        print(f"   Threshold: {self.threshold}%")
    
    def clean_text(self, text):
        text = ' '.join(text.split())
        text = re.sub(r'[.,!?;:]', '', text)
        text = text.lower()
        text = ' '.join(text.split())
        return text
    
    def load_sentences(self, sentences_file):
        if not Path(sentences_file).exists():
            print(f"❌ Sentences file not found: {sentences_file}")
            return []
        
        with open(sentences_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sentences = [s.strip() for s in content.split('\n') if s.strip()]
        print(f"📄 Loaded {len(sentences)} sentences from {sentences_file}")
        return sentences
    
    def find_matches(self, transcript_file, sentences):
        print(f"🔎 Searching for {len(sentences)} words/phrases...")
        print(f"📁 Using transcript: {Path(transcript_file).name}")
        print("-" * 50)
        
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        
        segments = transcript.get('segments', [])
        matches = []
        
        print(f"📝 Checking {len(segments)} segments...")
        print()
        
        for search_term in tqdm(sentences, desc="Searching"):
            search_clean = self.clean_text(search_term)
            search_words = search_clean.split()
            word_count = len(search_words)
            is_single_word = (word_count == 1)
            
            found_match = None
            best_score = 0
            
            for segment in segments:
                segment_clean = self.clean_text(segment['text'])
                segment_words = segment.get('words', [])
                
                if is_single_word:
                    # ============================================
                    # SINGLE WORD - Find EXACT word
                    # ============================================
                    word_lower = search_clean
                    
                    for word_data in segment_words:
                        word_text = self.clean_text(word_data.get('word', ''))
                        if word_text == word_lower:
                            # EXACT WORD FOUND!
                            found_match = {
                                'sentence': search_term,
                                'match_text': segment['text'],
                                'score': 100,
                                'start': word_data['start'],
                                'end': word_data['end'],
                                'matched_word': word_data['word'],
                                'is_word': True,
                                'exact': True
                            }
                            break
                    
                    if found_match:
                        break
                else:
                    # ============================================
                    # MULTIPLE WORDS - Find EXACT phrase
                    # ============================================
                    phrase_lower = ' '.join(search_words)
                    segment_text_lower = segment_clean
                    
                    # Check if phrase exists in this segment
                    if phrase_lower in segment_text_lower:
                        # Find the exact word positions
                        phrase_found = []
                        for i, word_data in enumerate(segment_words):
                            word_text = self.clean_text(word_data.get('word', ''))
                            if word_text == search_words[0]:
                                # Check if rest matches
                                match_count = 0
                                for j in range(len(search_words)):
                                    if i + j < len(segment_words):
                                        w_text = self.clean_text(segment_words[i + j].get('word', ''))
                                        if w_text == search_words[j]:
                                            match_count += 1
                                        else:
                                            break
                                
                                if match_count == len(search_words):
                                    # EXACT PHRASE FOUND!
                                    start_word = segment_words[i]
                                    end_word = segment_words[i + len(search_words) - 1]
                                    phrase_text = ' '.join([w.get('word', '') for w in segment_words[i:i+len(search_words)]])
                                    
                                    found_match = {
                                        'sentence': search_term,
                                        'match_text': segment['text'],
                                        'score': 100,
                                        'start': start_word['start'],
                                        'end': end_word['end'],
                                        'matched_word': phrase_text,
                                        'is_word': False,
                                        'exact': True
                                    }
                                    break
                        
                        if found_match:
                            break
                    
                    # If not exact, try fuzzy matching (fallback)
                    if not found_match:
                        score = fuzz.ratio(search_clean, segment_clean)
                        if score > best_score:
                            best_score = score
                            # For fallback, use segment-level timestamps
                            found_match = {
                                'sentence': search_term,
                                'match_text': segment['text'],
                                'score': best_score,
                                'start': segment['start'],
                                'end': segment['end'],
                                'matched_word': None,
                                'is_word': False,
                                'exact': False
                            }
            
            # Check if we found a match
            if found_match and found_match['score'] >= self.threshold:
                matches.append(found_match)
                
                if found_match.get('exact', False):
                    if is_single_word:
                        print(f"   ✅ EXACT word: '{search_term}' → '{found_match['matched_word']}'")
                    else:
                        print(f"   ✅ EXACT phrase: '{search_term}' → '{found_match['matched_word']}'")
                else:
                    print(f"   ⚠️  Fuzzy match: '{search_term}' (score: {found_match['score']}%)")
            else:
                if is_single_word:
                    print(f"   ❌ Word not found: '{search_term}'")
                else:
                    print(f"   ❌ Phrase not found: '{search_term[:35]}...'")
        
        print()
        print(f"✅ Found {len(matches)} matches out of {len(sentences)} searches")
        return matches
    
    def save_matches(self, matches, output_file):
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Matches saved: {output_path}")
        return output_path
    
    def print_summary(self, matches):
        print()
        print("=" * 60)
        print("📊 MATCH SUMMARY")
        print("=" * 60)
        
        if not matches:
            print("❌ No matches found!")
            print()
            print("💡 Suggestions:")
            print("   1. Check if the word/phrase exists in the video")
            print("   2. Try simpler words")
            print("   3. Lower threshold in config.yaml")
            return
        
        exact = [m for m in matches if m.get('exact', False)]
        fuzzy = [m for m in matches if not m.get('exact', False)]
        words = [m for m in matches if m.get('is_word', False)]
        phrases = [m for m in matches if not m.get('is_word', False)]
        
        print(f"✅ Total matches: {len(matches)}")
        print(f"   🎯 Exact matches: {len(exact)}")
        print(f"   📝 Fuzzy matches: {len(fuzzy)}")
        print(f"   🔤 Words: {len(words)}")
        print(f"   📄 Phrases: {len(phrases)}")
        print()
        print("📝 Matches found:")
        print("-" * 60)
        
        for i, match in enumerate(matches[:20], 1):
            if match.get('exact', False):
                if match.get('is_word', False):
                    print(f"🔤 {i}. '{match['sentence']}' → EXACT word: '{match.get('matched_word', '')}'")
                else:
                    print(f"📄 {i}. '{match['sentence'][:40]}' → EXACT phrase: '{match.get('matched_word', '')}'")
            else:
                print(f"⚠️  {i}. '{match['sentence'][:40]}' → Fuzzy match (score: {match['score']}%)")
            
            print(f"   ⏱️  {match['start']:.2f}s - {match['end']:.2f}s")
            print(f"   📍 In: {match['match_text'][:40]}...")
            print()

if __name__ == "__main__":
    print("🧪 Testing sentence matcher...")
    print("✅ Module ready!")
