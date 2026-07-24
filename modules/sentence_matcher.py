#!/usr/bin/env python3
"""
Sentence Matcher Module
EXACT word/phrase extraction with word-level timestamps
Supports multiple videos and tracks ALL occurrences
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
        self.all_matches = []
        
        print(f"🔍 Sentence matcher initialized")
        print(f"   Mode: EXACT word/phrase extraction (ALL occurrences)")
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
        
        sentences = [s.strip() for s in content.split('\n') if s.strip() and not s.strip().startswith('#')]
        print(f"📄 Loaded {len(sentences)} sentences from {sentences_file}")
        return sentences
    
    def find_matches_in_video(self, transcript_file, sentences, video_name):
        """Find matches in a single video"""
        print(f"🔎 Searching in: {video_name}")
        print(f"📁 Using transcript: {Path(transcript_file).name}")
        print("-" * 50)
        
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        
        segments = transcript.get('segments', [])
        video_matches = []
        
        for search_term in tqdm(sentences, desc=f"Searching in {video_name[:20]}..."):
            search_clean = self.clean_text(search_term)
            search_words = search_clean.split()
            word_count = len(search_words)
            is_single_word = (word_count == 1)
            
            term_matches = []
            
            for segment in segments:
                segment_clean = self.clean_text(segment['text'])
                segment_words = segment.get('words', [])
                
                if is_single_word:
                    word_lower = search_clean
                    
                    for word_data in segment_words:
                        word_text = self.clean_text(word_data.get('word', ''))
                        if word_text == word_lower:
                            term_matches.append({
                                'sentence': search_term,
                                'match_text': segment['text'],
                                'score': 100,
                                'start': word_data['start'],
                                'end': word_data['end'],
                                'matched_word': word_data['word'],
                                'is_word': True,
                                'exact': True,
                                'video': video_name,
                                'occurrence': len(term_matches) + 1
                            })
                else:
                    phrase_lower = ' '.join(search_words)
                    segment_text_lower = segment_clean
                    
                    if phrase_lower in segment_text_lower:
                        for i, word_data in enumerate(segment_words):
                            word_text = self.clean_text(word_data.get('word', ''))
                            if word_text == search_words[0]:
                                match_count = 0
                                for j in range(len(search_words)):
                                    if i + j < len(segment_words):
                                        w_text = self.clean_text(segment_words[i + j].get('word', ''))
                                        if w_text == search_words[j]:
                                            match_count += 1
                                        else:
                                            break
                                
                                if match_count == len(search_words):
                                    start_word = segment_words[i]
                                    end_word = segment_words[i + len(search_words) - 1]
                                    phrase_text = ' '.join([w.get('word', '') for w in segment_words[i:i+len(search_words)]])
                                    
                                    term_matches.append({
                                        'sentence': search_term,
                                        'match_text': segment['text'],
                                        'score': 100,
                                        'start': start_word['start'],
                                        'end': end_word['end'],
                                        'matched_word': phrase_text,
                                        'is_word': False,
                                        'exact': True,
                                        'video': video_name,
                                        'occurrence': len(term_matches) + 1
                                    })
            
            if term_matches:
                print(f"   ✅ Found {len(term_matches)} occurrences of '{search_term}' in {video_name}")
                video_matches.extend(term_matches)
            else:
                print(f"   ❌ No occurrences of '{search_term}' in {video_name}")
        
        return video_matches
    
    def find_matches(self, transcript_files, sentences):
        print()
        print("=" * 60)
        print("🔍 SEARCHING ACROSS ALL VIDEOS")
        print("=" * 60)
        print()
        
        all_matches = []
        total_found = {}
        
        for transcript_file in transcript_files:
            video_name = transcript_file.stem
            matches = self.find_matches_in_video(transcript_file, sentences, video_name)
            all_matches.extend(matches)
            
            for match in matches:
                term = match['sentence']
                if term not in total_found:
                    total_found[term] = 0
                total_found[term] += 1
        
        self.all_matches = all_matches
        
        print()
        print("=" * 60)
        print("📊 TOTAL OCCURRENCES ACROSS ALL VIDEOS")
        print("=" * 60)
        for term, count in total_found.items():
            print(f"   {term}: {count} occurrence(s)")
        print()
        print(f"✅ Found {len(all_matches)} total matches across all videos")
        
        return all_matches
    
    def save_matches(self, matches, output_file):
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
            'total_matches': len(matches),
            'matches': matches
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Matches saved: {output_path}")
        return output_path
    
    def print_summary(self, matches):
        print()
        print("=" * 60)
        print("📊 MATCH SUMMARY")
        print("=" * 60)
        
        if not matches:
            print("❌ No matches found!")
            return
        
        by_term = {}
        by_video = {}
        
        for match in matches:
            term = match['sentence']
            video = match.get('video', 'Unknown')
            
            if term not in by_term:
                by_term[term] = []
            by_term[term].append(match)
            
            if video not in by_video:
                by_video[video] = []
            by_video[video].append(match)
        
        print(f"✅ Total matches: {len(matches)}")
        print()
        
        print("📝 By search term:")
        print("-" * 40)
        for term, term_matches in sorted(by_term.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {term}: {len(term_matches)} occurrence(s)")
        print()
        
        print("📁 By video:")
        print("-" * 40)
        for video, video_matches in by_video.items():
            print(f"   {video[:40]}: {len(video_matches)} occurrence(s)")
        print()
        
        print("📝 First 10 matches:")
        print("-" * 40)
        for i, match in enumerate(matches[:10], 1):
            if match.get('is_word', False):
                print(f"   {i}. '{match['sentence']}' → '{match['matched_word']}'")
            else:
                print(f"   {i}. '{match['sentence']}' → '{match['matched_word']}'")
            print(f"      ⏱️  {match['start']:.2f}s - {match['end']:.2f}s")
            print(f"      📁 {match.get('video', 'Unknown')}")
        if len(matches) > 10:
            print(f"   ... and {len(matches) - 10} more")

if __name__ == "__main__":
    print("🧪 Testing sentence matcher...")
    print("✅ Module ready!")
