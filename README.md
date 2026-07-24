# 📚 Goethe - German Sentence Audio Extractor

**Learn German by building your own audio library from videos!**

---

## 🎯 What is Goethe?

Goethe is a tool that helps you learn German by extracting specific sentences from your videos and saving them as MP3 files.

**The Problem**  
You have hours of German learning videos. You want to practice specific sentences, but you don't want to watch the whole video again just to hear one sentence.

**The Solution**  
Goethe finds the sentences you want in your videos and cuts them into individual MP3 files. You get a personal audio library organized by sentence!

```
📹 German Lesson (30 min)
        ↓
🔍 Search for: "Ich habe keine Zeit"
        ↓
✂️ Cut audio at 2:15 - 2:18
        ↓
🎵 Ich_habe_keine_Zeit.mp3 (3 seconds)
        ↓
📱 Listen anytime, anywhere!
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎤 **Speech Recognition** | Converts video speech to text with timestamps |
| 🔍 **Smart Search** | Finds sentences even with small differences (fuzzy matching) |
| 🎵 **MP3 Extraction** | Creates high-quality audio clips (192 kbps) |
| 📁 **Organized Output** | MP3 files organized by sentence in individual folders |
| 🎨 **Beautiful Interface** | Colorful, professional output in your terminal |
| 🔄 **Resume Support** | Won't reprocess videos you've already done |
| ⚡ **Fast Processing** | Uses optimized whisper models for speed |
| 🚀 **Auto-Setup** | Everything created automatically on first run |
| 🇩🇪 **German Optimized** | Handles ä, ö, ü, ß and German grammar |

---

## 📋 Requirements

Before you start, make sure you have:

| Requirement | Version | How to check |
|-------------|---------|--------------|
| **Ubuntu** | 22.04 or later | `lsb_release -a` |
| **Python** | 3.8 or later | `python3 --version` |
| **FFmpeg** | Latest | `ffmpeg -version` |
| **Disk Space** | 10+ GB free | `df -h` |

---

## 🚀 Quick Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/duman-dp/Goethe.git
cd Goethe
```

### Step 2: Install FFmpeg (if not installed)

```bash
sudo apt update
sudo apt install ffmpeg
```

### Step 3: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Run Auto-Setup

```bash
python3 setup.py
```

This creates all necessary folders and configuration files automatically.

### Step 5: Add Your Content

```bash
# Add videos to the videos folder
cp /path/to/your/german_video.mp4 videos/

# Add sentences to sentences.txt
nano sentences.txt
```

### Step 6: Start Extracting

```bash
python3 main.py
```

### Step 7: Listen to Your MP3s

```bash
# List your MP3 files
ls output/mp3/

# Play the first one
ffplay output/mp3/*/*.mp3
```

---

## 📁 Project Structure

```
Goethe/
│
├── 📁 videos/              ← Put your videos here (.mp4, .mkv, .avi)
│   └── german_lesson.mp4
│
├── 📁 transcripts/         ← Speech-to-text results (JSON)
│   └── german_lesson.json
│
├── 📁 output/              ← All generated files
│   └── 📁 mp3/             ← Your MP3 library! 🎵
│       ├── 📁 Ich_habe_keine_Zeit/
│       │   └── 🎵 Ich_habe_keine_Zeit_001.mp3
│       ├── 📁 Wie_geht_es_dir/
│       │   └── 🎵 Wie_geht_es_dir_002.mp3
│       └── 📁 Das_ist_kein_Problem/
│           └── 🎵 Das_ist_kein_Problem_003.mp3
│
├── 📁 modules/             ← Python modules (don't edit unless you know)
│   ├── speech_recognition.py
│   ├── sentence_matcher.py
│   ├── audio_extractor.py
│   ├── beautiful_logger.py
│   └── setup.py
│
├── 📄 config.yaml          ← Configuration settings
├── 📄 sentences.txt        ← Sentences you want to find
├── 📄 main.py              ← Main program (run this)
├── 📄 setup.py             ← First-time setup
├── 📄 requirements.txt     ← Python dependencies
└── 📄 README.md            ← This file
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize how Goethe works:

```yaml
# ============================================
# Goethe Configuration
# ============================================

# Audio Settings
audio:
  padding_before: 0.5    # Add 0.5s before each sentence (natural sound)
  padding_after: 0.5     # Add 0.5s after each sentence
  bitrate: 192           # MP3 quality: 128, 192, 256

# Speech Recognition
speech:
  model_size: tiny       # tiny (fastest) | small | medium | large (best)
  language: German       # Language to transcribe
  device: cpu            # cpu or cuda (GPU)
  quiet: true            # Less output in terminal

# Sentence Matching
matching:
  fuzzy_threshold: 60    # 0-100 (lower = more matches, but less accurate)

# Paths
paths:
  videos: ./videos
  transcripts: ./transcripts
  output: ./output
  logs: ./logs
```

### Model Size Guide

| Model | Speed | Accuracy | Memory | Best For |
|-------|-------|----------|--------|----------|
| **tiny** | 🚀 Fastest | 70% | ~1 GB | Testing, short videos |
| **small** | ⚡ Fast | 85% | ~2 GB | Daily use (recommended) |
| **medium** | 🐢 Medium | 92% | ~5 GB | Better accuracy |
| **large** | 🐌 Slow | 95% | ~10 GB | Best quality (if you have RAM) |

---

## 📝 How to Use

### Adding Videos

```bash
# Copy videos to the videos folder
cp /path/to/video.mp4 videos/

# Supported formats:
# .mp4, .mkv, .avi, .mov
```

### Adding Sentences

Open `sentences.txt`:

```bash
nano sentences.txt
```

Add one sentence per line:

```
Ich habe keine Zeit.
Wie geht es dir?
Das ist kein Problem.
Guten Morgen!
Hallo, wie heißt du?
Ich liebe Deutsch.
Wo ist der Bahnhof?
Ich verstehe nicht.
Kannst du mir helfen?
Was ist das?
```

**Tip:** Use shorter sentences for better matches!

### Running the Program

```bash
python3 main.py
```

### Finding Your MP3s

```bash
# List all MP3 files
ls -R output/mp3/

# Play all MP3s
for f in output/mp3/*/*.mp3; do ffplay -autoexit "$f"; done
```

---

## 🎨 Example Output

```
  ╔════════════════════════════════════════════════════════════════════╗
  ║          📚 Goethe - German Sentence Audio Extractor              ║
  ╚════════════════════════════════════════════════════════════════════╝

  ┌────────────────────────────────────────────────────────────────────┐
  │  🎤 Step 1: Speech Recognition                                    │
  └────────────────────────────────────────────────────────────────────┘
  ℹ️ Found 1 video(s)
     📹 german_lesson.mp4
  ℹ️ ⏩ Skipping: german_lesson.mp4 (transcript exists)

  ┌────────────────────────────────────────────────────────────────────┐
  │  🔎 Step 2: Sentence Matching                                     │
  └────────────────────────────────────────────────────────────────────┘
  ℹ️ Searching for 9 sentences
  ✅ Found 6 matches!

  ┌──────────────────────────────────────────────────────────────────┐
  │  📝 Matches Found                                              │
  ├──────────────────────────────────────────────────────────────────┤
  │  🌟  1. Ich habe keine Zeit                                    │
  │     ⏱️  2:15 - 2:18  •  Score: 92%                            │
  │  🌟  2. Wie geht es dir                                        │
  │     ⏱️  5:30 - 5:33  •  Score: 88%                            │
  │  🌟  3. Das ist kein Problem                                   │
  │     ⏱️  8:45 - 8:48  •  Score: 85%                            │
  └──────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────┐
  │  🎵 Step 3: Audio Extraction                                     │
  └────────────────────────────────────────────────────────────────────┘
  ✅ Created 6 MP3 files!
  📁 Saved to: output/mp3/

  ┌──────────────────────────────────────────────────────────────────┐
  │  📊 Summary                                                    │
  ├──────────────────────────────────────────────────────────────────┤
  │  🎬 Videos:          1                                        │
  │  📝 Transcripts:      1                                        │
  │  🔎 Matches:          6                                        │
  │  🎵 MP3 Files:        6                                        │
  │  ⏱️  Total time:      5.2 seconds                             │
  └──────────────────────────────────────────────────────────────────┘
```

---

## ❓ Frequently Asked Questions

### How long does it take?

| Video Length | tiny model | small model |
|--------------|------------|-------------|
| 1 minute | ~30 seconds | ~1 minute |
| 5 minutes | ~2 minutes | ~5 minutes |
| 10 minutes | ~4 minutes | ~10 minutes |

**First time:** Longer (downloads AI model ~1GB)

### Can I use this for other languages?

Yes! Change `language: German` to:
- `French`, `Spanish`, `Italian`, `Portuguese`
- `English`, `Chinese`, `Japanese`, `Korean`
- Any language supported by Whisper

### Where do I get German videos?

- **YouTube**: Download with `yt-dlp`
- **Deutsche Welle**: Free German lessons
- **Easy German**: YouTube channel
- **Your own recordings**: Record yourself speaking
- **German movies/TV**: With subtitles

### My laptop is getting hot!

Normal! Speech recognition uses a lot of CPU. To reduce heat:
1. Use `model_size: tiny` (fastest, coolest)
2. Process shorter videos (2-3 minutes)
3. Take breaks between processing
4. Put laptop on a hard surface for airflow

### No matches found?

Try these fixes:
1. Lower `fuzzy_threshold` to 50 in config.yaml
2. Use shorter sentences
3. Check if sentences actually appear in your video
4. Use simpler sentences first

### Can I process multiple videos?

Yes! Put all videos in the `videos/` folder. Goethe will process them all.

---

## 🛠️ Troubleshooting

### FFmpeg not found

```bash
sudo apt update
sudo apt install ffmpeg
```

### Python packages missing

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Can't see videos folder

```bash
# Run setup to create folders
python3 setup.py
```

### Hugging Face token warning

```
Warning: You are sending unauthenticated requests to the HF Hub
```

This is **normal**. To speed up downloads:
1. Create free account at: https://huggingface.co/join
2. Get token: https://huggingface.co/settings/tokens
3. Set token: `export HF_TOKEN="hf_xxxxxxxxxx"`
4. Or just wait - it works without token (slower)

### Memory error

```bash
# Use tiny model
# Edit config.yaml and set:
# model_size: tiny
```

### Error: No such file or directory

```bash
# Make sure you're in the right folder
cd ~/Goethe

# Check folder structure
ls -la
```

---

## 💡 Pro Tips

| Tip | Benefit |
|-----|---------|
| Use **short videos** (2-5 min) | Faster processing |
| Use **tiny model** first | Quick testing |
| **Clear audio** = better results | Higher accuracy |
| Add **simple sentences** first | Higher match rate |
| Lower **threshold to 50** | More matches |
| Process **one video at a time** | Less memory usage |
| **Close other apps** | More CPU for processing |

---

## 🎯 Complete Example

Here's a full example from start to finish:

```bash
# 1. Download a German video (example using yt-dlp)
yt-dlp "https://www.youtube.com/watch?v=example" -o videos/german_lesson.mp4

# 2. Create sentences.txt
cat > sentences.txt << EOF
Ich habe keine Zeit.
Wie geht es dir?
Das ist kein Problem.
Guten Morgen!
Hallo, wie heißt du?
Ich liebe Deutsch.
Wo ist der Bahnhof?
Ich verstehe nicht.
Kannst du mir helfen?
Was ist das?
EOF

# 3. Activate environment
source venv/bin/activate

# 4. Run Goethe
python3 main.py

# 5. Find your MP3s
ls output/mp3/

# 6. Listen to them!
ffplay output/mp3/*/*.mp3
```

---

## 📤 Sharing Your MP3 Library

### To your phone

```bash
# Via USB
cp -r output/mp3/ /media/phone/Music/German/

# Via cloud
rsync -av output/mp3/ ~/Dropbox/German_Library/
```

### To friends

```bash
# Create ZIP archive
zip -r german_mp3_library.zip output/mp3/

# Share the file
```

### To other devices

```bash
# Via SSH
scp -r output/mp3/ user@192.168.1.100:~/Music/German/

# Via USB drive
cp -r output/mp3/ /media/usb/German_MP3s/
```

---

## 🤝 Contributing

Want to help improve Goethe?

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

**Areas that need help:**
- Better documentation
- More language support
- GUI interface
- Batch processing improvements
- Performance optimizations

---

## 📄 License

MIT License — Free to use, modify, and share!

---

## 🙏 Acknowledgements

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Speech recognition
- [FFmpeg](https://ffmpeg.org/) — Audio extraction
- [Hugging Face](https://huggingface.co/) — Model hosting
- [Johann Wolfgang von Goethe](https://en.wikipedia.org/wiki/Johann_Wolfgang_von_Goethe) — Inspiration

---

## 📬 Contact

- **GitHub**: [@duman-dp](https://github.com/duman-dp)
- **Project**: [Goethe](https://github.com/duman-dp/Goethe)
- **Issues**: [Report a bug](https://github.com/duman-dp/Goethe/issues)

---

## ⭐ Support

If Goethe helped you learn German, please star ⭐ this repository!

---

**Happy Learning! 🇩🇪🎧**
