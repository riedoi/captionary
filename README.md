# Captionary - Automated Audio & Video Transcription
![CI](https://github.com/riedoi/captionary/actions/workflows/ci.yml/badge.svg)

Captionary is a local, privacy-focused tool that automatically generates subtitles for your audio and video files using OpenAI's Whisper model (via [faster-whisper](https://github.com/guillaumekln/faster-whisper)).

## Features

- **Local Processing**: All transcription happens on your machine. No data is sent to the cloud.
- **Bulk Support**: Transcribe entire directories of media files at once.
- **Auto-Cleanup**: Automatically cleans up temporary files after processing.
- **Docker Support**: Run easily anywhere with Docker.
- **Web Interface**: Drag & drop your files, select language and model, and watch the progress in real-time.
- **Bulk Processing**: Transcribe entire directories or multiple files at once using the CLI.
- **Video Support**: Directly upload MP4, MKV, MOV, AVI, and more.
- **High Performance**: Uses `faster-whisper` for up to 4x faster transcription than the original Whisper.
- **Accurate Timing**: Optimized for precise subtitle alignment with spoken words.
- **Automatic Cleanup**: Uploaded files are automatically removed from the server after processing.

## Prerequisites

- Python 3.8+ (for source)
- [ffmpeg](https://ffmpeg.org/download.html) (for source)

## Installation

### Option 1: Desktop App (Recommended)
Download the latest installer for your system from the [Releases](https://github.com/riedoi/captionary/releases) page.
- **Windows**: Download `Captionary-Windows.exe` and run it.
- **macOS**: Download `Captionary-macOS.dmg`, drag the app to Applications, and run it.
  *Note: Since the app is not signed, you might need to Right Click > Open to bypass the security warning on macOS.*

### Option 2: Run with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/riedoi/captionary.git
   cd captionary
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```


## Running with Docker

You can run Captionary easily using Docker. This handles all dependencies (including ffmpeg) for you.

### Option 1: Use the Pre-built Image (Recommended)
You can pull the latest image directly from GitHub Container Registry:

```bash
docker run -d -p 8000:8000 -v huggingface_cache:/root/.cache/huggingface --name captionary ghcr.io/riedoi/captionary:latest
```
*Note: We mount a volume so models don't need to re-download every time.*

### Option 2: Build from Source
If you want to build it yourself or modify the code:

1. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

2. Open your browser and navigate to `http://localhost:8000`.

The Docker setup includes a persistent volume for the Hugging Face model cache, so models are only downloaded once.

### Option 3: Run CLI with Docker (One-off)
You can also use the Docker image to run the CLI tool directly on your files without installing Python:

```bash
# Mount current directory to /data in container and process video.mkv
docker run --rm -v $(pwd):/data -v huggingface_cache:/root/.cache/huggingface ghcr.io/riedoi/captionary:latest python fw_srt.py /data/video.mkv --model medium
```
*Note: Make sure to use `/data/filename` so the container can find your mounted file.*

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
python fw_srt.py video.mkv --model medium --lang tr
```

**Transcribe multiple files:**
```bash
python fw_srt.py part1.mkv part2.mkv --model large-v2
```

**Transcribe an entire directory:**
```bash
python fw_srt.py /path/to/media/folder --device cuda
```

**Options:**
- `--model`: Model size (tiny, base, small, medium, large-v2, large-v3) or `nebi/whisper-large-v3-turbo-swiss-german-ct2-int8`. Default: `medium`.
- `--lang`: Language code (e.g., en, tr, de, fr). Default: Auto-detect.
- `--device`: Compute device (`cpu` or `cuda`). Default: `cpu`.
- `--compute_type`: Quantization (`int8`, `float16`, etc.). Default: `int8`.
- `--offset`: Time offset for subtitles (e.g., `00:30:00`).

## Development

### Running Tests
To run the tests locally:

1. Install test dependencies:
   ```bash
   pip install pytest httpx
   ```
2. Run pytest:
   ```bash
   python -m pytest
   ```

## License

MIT License
