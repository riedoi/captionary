# Captionary

Captionary is a powerful and user-friendly tool for generating subtitles from audio and video files using OpenAI's Whisper models (via `faster-whisper`). It offers both a modern web interface and a robust command-line tool for bulk processing.

> **🔒 Privacy First**: All processing happens locally on your device. Your audio and video files never leave your computer.

## Features

- **Web Interface**: Drag & drop your files, select language and model, and watch the progress in real-time.
- **Bulk Processing**: Transcribe entire directories or multiple files at once using the CLI.
- **Video Support**: Directly upload MP4, MKV, MOV, AVI, and more.
- **High Performance**: Uses `faster-whisper` for up to 4x faster transcription than the original Whisper.
- **Accurate Timing**: Optimized for precise subtitle alignment with spoken words.
- **Automatic Cleanup**: Uploaded files are automatically removed from the server after processing.

## Prerequisites

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available in your system PATH.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/riedoi/captionary.git
   cd captionary
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Web Interface

1. Start the server:
   ```bash
   uvicorn app:app --reload
   ```

2. Open your browser and navigate to `http://127.0.0.1:8000`.

3. Drag and drop your audio or video file, select your settings, and click "Generate Subtitles".

### Command Line Interface (CLI)

You can use `fw_srt.py` directly for batch processing.

**Transcribe a single file:**
```bash
python fw_srt.py audio.mp3 --model medium --lang tr
```

**Transcribe multiple files:**
```bash
python fw_srt.py file1.mp3 file2.mp4 --model large-v2
```

**Transcribe an entire directory:**
```bash
python fw_srt.py /path/to/media/folder --device cuda
```

**Options:**
- `--model`: Model size (tiny, base, small, medium, large-v2, large-v3). Default: `medium`.
- `--lang`: Language code (e.g., en, tr, de, fr). Default: Auto-detect.
- `--device`: Compute device (`cpu` or `cuda`). Default: `cpu`.
- `--compute_type`: Quantization (`int8`, `float16`, etc.). Default: `int8`.
- `--offset`: Time offset for subtitles (e.g., `00:30:00`).

## License

MIT License
