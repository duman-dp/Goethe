# 📚 Goethe - German Sentence Audio Extractor

**Build your own Anki audio library from German videos.**

You put German videos in a folder and write down the words and phrases you want to practice. Goethe finds every place where they are spoken and cuts each one out as a small MP3 file.

---

## 🎯 What it does

```
📹 videos/lesson.mp4
      ↓  faster-whisper (speech recognition, word-level timestamps)
📝 transcripts/lesson.json
      ↓  find your words and phrases (sentences.txt)
🔎 every occurrence, in every video
      ↓  ffmpeg
🎵 output/mp3/Ich_heisse/Ich_heisse__lesson__00h02m15s_7d11d715.mp3
```

---

## ✨ Features (all of these are real)

| Feature | How it works |
|---------|--------------|
| 🎤 **Speech recognition** | faster-whisper transcribes each video with a timestamp for every word. The language comes from `config.yaml`. |
| 🔍 **Exact matching** | Finds single words and whole phrases. Case, punctuation and extra spaces do not matter; `ß`/`ss` and umlauts are handled. Only whole words match (`ich` does not match inside `mich`). |
| 🔗 **Phrases across segments** | Whisper sometimes splits a sentence into two segments. Goethe searches the whole word stream, so these phrases are found too. |
| 🧩 **Optional fuzzy fallback** | Off by default. See [Matching](#-matching). |
| 🎵 **MP3 extraction** | One MP3 per occurrence, cut with ffmpeg, at the bitrate you choose (32-320 kbps). |
| 📁 **Organized output** | `output/mp3/<search term>/`, with file names that are unique across all videos (important for Anki). |
| 🔄 **Resume** | Videos that already have a transcript are skipped **without loading the Whisper model**. MP3 files that already exist are skipped too. |
| 🎞️ **Video formats** | Whatever you list under `video_formats` in `config.yaml` (default: mp4, mkv, avi, mov). |
| 🌍 **Languages** | German, English, French, Spanish, Italian, Portuguese, Chinese (see below). |
| 🎨 **Readable output** | Colored boxes that stay aligned. Colors turn off automatically when output is not a terminal or `NO_COLOR` is set. |
| 📝 **Log file** | Everything shown on screen is also written (without colors) to `logs/goethe.log`. |

---

## 📋 Requirements

| Requirement | Version | How to check |
|-------------|---------|--------------|
| **Python** | 3.8 or newer | `python3 --version` |
| **FFmpeg** | any recent version | `ffmpeg -version` |
| **Disk space** | the Whisper model is downloaded on first use: small for `tiny`, a few GB for `large-v3` | `df -h` |

Developed and tested on Ubuntu. Other Linux systems and macOS should work as well, but this was not tested.

---

## 🚀 Installation

```bash
# 1. Get the project
git clone https://github.com/duman-dp/Goethe.git
cd Goethe

# 2. Install FFmpeg (Ubuntu)
sudo apt update
sudo apt install ffmpeg

# 3. Create a virtual environment and install the Python packages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. First-time setup: creates folders, config.yaml and sentences.txt
#    (existing files are never overwritten) and checks your system
python3 setup.py
```

## ▶️ Usage

1. Copy your videos into `videos/`.
2. Write the words and phrases you want into `sentences.txt`, one per line.
3. Run:

```bash
python3 main.py
```

Your MP3 files are in `output/mp3/`.

### `sentences.txt`

```
# Lines starting with # are comments. Empty lines are ignored.
Ich heiße
Wie heißt du?
Woher
malen
```

- Single words and phrases can be mixed.
- A phrase matches only when its words are spoken one after another. Words more than 1.5 seconds apart are not treated as one phrase.
- Duplicates (same words, different capitalization or punctuation) are ignored with a warning.
- The file must be saved as UTF-8 (the default in almost every editor).

---

## 📁 Project structure

```
Goethe/
├── videos/               ← your videos
├── transcripts/          ← speech-to-text results (JSON), one per video
├── output/
│   ├── all_matches.json  ← every match with video, timestamps and context
│   └── mp3/              ← your MP3 library
│       └── Ich_heisse/
│           └── Ich_heisse__lesson__00h02m15s_7d11d715.mp3
├── logs/goethe.log
├── modules/
│   ├── beautiful_logger.py     terminal output and log file
│   ├── config.py               loading and checking config.yaml
│   ├── errors.py               error types with readable messages
│   ├── speech_recognition.py   video discovery and transcription
│   ├── sentence_matcher.py     finding words and phrases
│   ├── audio_extractor.py      cutting MP3 clips, file names
│   └── setup.py                first-time setup
├── tests/                ← automatic tests
├── main.py               ← run this
├── setup.py              ← first-time setup
├── config.yaml
├── sentences.txt
└── requirements.txt
```

### MP3 file names

```
<search term>__<video name>__<hh>h<mm>m<ss>s_<id>.mp3
Ich_heisse__Lektion_Ae__00h00m00s_e7c3db2f.mp3
```

- Umlauts are transliterated: `ä→ae`, `ö→oe`, `ü→ue`, `ß→ss`. Names only contain `A-Z a-z 0-9 _`.
- The `<id>` is derived from video name, search term and exact time. The same match always gets the same name; matches from different videos never collide.
- Text without any Latin letters (for example Chinese search terms) gets a name like `term_a1b2c3`, because it cannot be transliterated without extra software.
- If two different search terms would end up with the same folder name, the second gets `_2`.

---

## ⚙️ Configuration (`config.yaml`)

All settings are optional. Missing values use the defaults shown here. Invalid values stop the program with a message that says what to change. Settings that do not exist (for example `audio.output_format` from older versions) are ignored with a warning.

| Setting | Default | Meaning |
|---------|---------|---------|
| `audio.padding_before` | `0.03` | Seconds added before each match (0-5) |
| `audio.padding_after` | `0.03` | Seconds added after each match (0-5) |
| `audio.bitrate` | `192` | MP3 quality in kbps (32-320) |
| `paths.videos` | `./videos` | Where your videos are |
| `paths.transcripts` | `./transcripts` | Where transcripts are stored |
| `paths.output` | `./output` | MP3 files go to `<output>/mp3/` |
| `paths.logs` | `./logs` | Folder for `goethe.log` |
| `speech.language` | `German` | Language spoken in the videos (see below) |
| `speech.model_size` | `small` | `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` (`large` = `large-v3`) |
| `speech.device` | `cpu` | `cpu`, `cuda` (NVIDIA GPU) or `auto` |
| `speech.quiet` | `false` | `true` = less output while transcribing |
| `matching.fuzzy_threshold` | `100` | `100` = exact only. `50`-`99` = fuzzy fallback (see below) |
| `video_formats` | `mp4, mkv, avi, mov` | File extensions that are processed (not case-sensitive) |

Relative paths are relative to the project folder.

### Model sizes

| Model | Speed | Accuracy | Memory |
|-------|-------|----------|--------|
| `tiny` | fastest | lowest | lowest |
| `base` | very fast | low | low |
| `small` *(default)* | fast | good for clear speech | moderate |
| `medium` | slower | better | high |
| `large-v2` / `large-v3` | slowest | best | highest |

`small` is the default because it works on most laptops. If words are misrecognized, try `medium`; if your computer runs out of memory, try `base` or `tiny`. Models are downloaded the first time they are used.

### Languages

| Name | Code |
|------|------|
| German | `de` |
| English | `en` |
| French | `fr` |
| Spanish | `es` |
| Italian | `it` |
| Portuguese | `pt` |
| Chinese | `zh` |

Write the name (`German`, `german`) or the code (`de`). Any other value stops the program and lists the supported languages. Other Whisper languages can be added to the `LANGUAGES` list in `modules/config.py`.

Chinese has no spaces between words, so it is matched character by character. A clip then covers the complete recognized words that contain the characters you searched for.

---

## 🔎 Matching

**Exact matching (default).** Goethe compares words after lower-casing and removing punctuation. `Wie heißt du?` finds "Wie heißt du", "wie heißt du!" and "wie heisst du".

**Fuzzy fallback (optional).** If you set `matching.fuzzy_threshold` below 100 (for example `80`):

- Goethe first searches exactly, as usual.
- Only if a term has **no exact match in a video**, it looks in that video for the most similar word sequences with at least that percentage of similarity (using Python's `difflib`). This helps when Whisper misspells a word.
- Fuzzy matches are marked in `output/all_matches.json` (`"exact": false` and a `score`).
- Terms shorter than 4 characters are never matched fuzzily.
- Lower values find more, but also more wrong clips. Start with `80`-`90`.

> ⚠️ **Upgrading note:** older versions shipped `fuzzy_threshold: 60`, which had no effect. In this version it is real. If your `config.yaml` still says `60`, change it to `100` unless you want fuzzy matching.

---

## 🎨 Example output

This is a real run (two short test videos; colors removed):

```
  ┌────────────────────────────────────────────────────────────────────┐
  │ 🎤 Step 1: Speech Recognition                                      │
  └────────────────────────────────────────────────────────────────────┘
  ℹ️ Found 2 video(s)
  📹 Lektion 2.MOV
  📹 Lektion_Ä.mp4
  ℹ️ ⏩ 2 video(s) already transcribed - skipping

  ┌────────────────────────────────────────────────────────────────────┐
  │ 🔎 Step 2: Sentence Matching                                       │
  └────────────────────────────────────────────────────────────────────┘
  ℹ️ Searching 13 word(s)/phrase(s) in 2 transcript(s) - exact matches only

  ┌────────────────────────────────────────────────────────────────────┐
  │ 🔎 Matches: 11 total                                               │
  ├────────────────────────────────────────────────────────────────────┤
  │ Ich heiße:           2 clip(s)                                     │
  │ Wie heißt du:        1 clip(s)                                     │
  │ Woher kommst du?:    not found                                     │
  │ ...                                                                │
  └────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────┐
  │ 🎵 Step 3: Audio Extraction                                        │
  └────────────────────────────────────────────────────────────────────┘
  ✅ Created 11 MP3 file(s)

  ┌────────────────────────────────────────────────────────────────────┐
  │ 📊 Summary                                                         │
  ├────────────────────────────────────────────────────────────────────┤
  │ Videos:           2                                                │
  │ Transcribed now:  0                                                │
  │ Transcripts used: 2                                                │
  │ Matches:          11                                               │
  │ MP3 created:      11                                               │
  │ MP3 skipped:      0                                                │
  │ MP3 failed:       0                                                │
  │ Output:           output/mp3                                       │
  └────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Resume and re-running

- **Transcripts:** a video is transcribed once. If `transcripts/<video name>.json` exists, the video is skipped and Whisper is not even loaded.
  To transcribe a video again (different language or model, or you replaced the video), delete its transcript file.
- **Transcript names:** transcripts are named after the video without extension (`lesson.mp4` → `lesson.json`). Two videos with the same name but different extensions (`lesson.mp4` and `lesson.mkv`) cannot both be used; the second is skipped with a warning. Rename one of them.
- **MP3 files:** clips that already exist are not created again. After changing padding or bitrate, delete `output/mp3/` to create all clips fresh.
- **Interrupting** with Ctrl+C is safe: finished transcripts are kept and files are written atomically, so no half-written transcript or MP3 is left behind.
- Transcripts from older Goethe versions are still understood.

---

## 🛠️ Troubleshooting

### "ffmpeg was not found"

Goethe needs ffmpeg to cut MP3 files.

```bash
sudo apt update
sudo apt install ffmpeg
ffmpeg -version        # should print a version
```

Transcription still works without ffmpeg, but no MP3 files are created.

### The Whisper model does not download / "Could not load Whisper model"

The model is downloaded from Hugging Face the first time it is used.

1. Check your internet connection and that there is enough free disk space.
2. Run Goethe again; interrupted downloads continue where they stopped.
3. The warning *"You are sending unauthenticated requests to the HF Hub"* is harmless. Optionally create a free token at https://huggingface.co/settings/tokens and set `export HF_TOKEN="hf_..."` for faster downloads.
4. Behind a proxy or offline? Download the model on another machine and put its folder path into `speech.model_size`.

### Out of memory / computer freezes while transcribing

Use a smaller model: set `speech.model_size` to `base` or `tiny`. Close other programs, and process fewer or shorter videos at once. (Videos that are already transcribed are skipped, so you can run Goethe repeatedly with a few videos each time.) Speech recognition uses the CPU heavily, so a laptop getting warm is normal.

### No matches found

1. Check the spelling in `sentences.txt`. Look into `transcripts/<video>.json` to see what Whisper actually heard.
2. Try single words first, then phrases. A phrase only matches if Whisper recognized every word of it.
3. Make sure `speech.language` matches the language in the videos. If you changed it, delete the old transcripts.
4. A bigger model (`medium`) usually recognizes more words correctly.
5. Optionally set `matching.fuzzy_threshold` to `80` (see [Matching](#-matching)).

### "Transcript ... is corrupted"

The transcript file is damaged (for example the computer was switched off while writing in an old version). Delete that file; Goethe will transcribe the video again.

### "No videos found"

Videos must be directly inside `videos/` (not in sub-folders) and have an extension listed in `video_formats`.

### "No such file or directory" / wrong folder

Goethe uses the folder it lives in, no matter where you start it from. Make sure `main.py` and the `modules/` folder are together.

### Python packages missing

```bash
source venv/bin/activate
pip install -r requirements.txt
python3 setup.py        # checks everything and reports what is missing
```

---

## 🧪 Tests

The tests need no extra packages:

```bash
python3 -m unittest discover -s tests -t . -v
```

They cover matching (including phrases across segments, umlauts, fuzzy fallback), file names, MP3 extraction (with ffmpeg replaced by a stand-in), configuration, video discovery and terminal alignment.

---

## ⚠️ Known limitations

- Only video files directly inside `videos/` are processed (no sub-folders).
- Matching is only as good as the recognized text. Whisper can mishear or skip words, especially with background music or noise.
- Clip boundaries come from Whisper's word timestamps, which can be off by a fraction of a second. Increase `audio.padding_before` / `audio.padding_after` if clips start or end too abruptly.
- Fuzzy matching works on spelling similarity, not on sound.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run the tests
4. Submit a pull request

## 📄 License

MIT License - free to use, modify, and share.

## 🙏 Acknowledgements

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - speech recognition
- [FFmpeg](https://ffmpeg.org/) - audio extraction
- [Hugging Face](https://huggingface.co/) - model hosting

## 📬 Contact

- **GitHub**: [@duman-dp](https://github.com/duman-dp)
- **Issues**: [Report a bug](https://github.com/duman-dp/Goethe/issues)
