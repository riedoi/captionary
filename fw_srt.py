import argparse, math, os
from faster_whisper import WhisperModel

def ts(t):
    ms = int(round((t - int(t)) * 1000)); t = int(t)
    h = t//3600; m = (t%3600)//60; s = t%60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_offset(s):
    if not s: return 0.0
    parts = [float(p) for p in s.split(":")]
    if len(parts)==3: h,m,sec = parts; return h*3600+m*60+sec
    if len(parts)==2: m,sec = parts;  return m*60+sec
    return float(s)

def transcribe_file(audio_path, model_size="medium", lang=None, offset_str="", device="cpu", compute_type="int8"):
    yield {"type": "status", "message": "Loading model..."}
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    
    yield {"type": "status", "message": "Starting transcription..."}
    segments, info = model.transcribe(
        audio_path,
        language=lang,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
        word_timestamps=True
    )

    off = parse_offset(offset_str)
    out_path = audio_path.rsplit(".", 1)[0] + ".srt"
    
    total_duration = info.duration
    
    with open(out_path, "w", encoding="utf-8") as f:
        srt_index = 1
        for seg in segments:
            # Yield progress
            if total_duration > 0:
                progress = min(seg.end / total_duration, 1.0)
                yield {"type": "progress", "value": progress}

            words = seg.words if seg.words else []
            
            # Fallback if no word timestamps
            if not words:
                text = (seg.text or "").strip()
                if not text: continue
                start = seg.start + off
                end = seg.end + off
                f.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{text}\n\n")
                srt_index += 1
                continue

            # Split on silence logic with orphan fix
            buffer_words = []
            for word in words:
                if not buffer_words:
                    buffer_words.append(word)
                    continue
                
                # Check gap between previous word end and current word start
                last_word = buffer_words[-1]
                gap = word.start - last_word.end
                
                if gap > 2.0 and len(buffer_words) <= 2:
                    # Orphan detected! Shift buffered words forward to merge with current word
                    # Calculate shift amount: move last_word.end to word.start (minus a small buffer)
                    shift_amount = word.start - last_word.end - 0.1 # 100ms spacing
                    if shift_amount > 0:
                        for w in buffer_words:
                            w.start += shift_amount
                            w.end += shift_amount
                    buffer_words.append(word)
                elif gap > 1.0:
                    # Flush buffer
                    start = buffer_words[0].start + off
                    end = buffer_words[-1].end + off
                    text = "".join([w.word for w in buffer_words]).strip()
                    if text:
                        f.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{text}\n\n")
                        srt_index += 1
                    buffer_words = [word]
                else:
                    buffer_words.append(word)
            
            # Flush remaining words in buffer
            if buffer_words:
                start = buffer_words[0].start + off
                end = buffer_words[-1].end + off
                text = "".join([w.word for w in buffer_words]).strip()
                if text:
                    f.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{text}\n\n")
                    srt_index += 1
    
    
    yield {"type": "complete", "path": out_path}

def main():
    ap = argparse.ArgumentParser(description="Captionary CLI - Auto-generate subtitles for audio/video files.")
    ap.add_argument("input_path", nargs="+", help="Audio file(s) or directory to transcribe")
    ap.add_argument("--model", default="medium", help="Model size: tiny, base, small, medium, large-v2, large-v3 (Default: medium)")
    ap.add_argument("--lang", default=None, help="Language code (e.g. en, tr). (Default: Auto-detect)")
    ap.add_argument("--offset", default="", help="Time offset for subtitles, e.g. 00:30:00. (Default: None)")
    ap.add_argument("--device", default="cpu", help="Compute device: cpu or cuda. (Default: cpu)")
    ap.add_argument("--compute_type", default="int8", help="Quantization: int8, int8_float16, float16, float32. (Default: int8)")
    args = ap.parse_args()

    files_to_process = []
    for path in args.input_path:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(('.mp3', '.wav', '.m4a', '.mp4', '.mkv', '.mov', '.avi', '.flac', '.ogg', '.webm')):
                        files_to_process.append(os.path.join(root, file))
        else:
            files_to_process.append(path)

    print(f"Found {len(files_to_process)} file(s) to process.")

    for i, audio_file in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}] Processing: {audio_file}")
        generator = transcribe_file(audio_file, args.model, args.lang, args.offset, args.device, args.compute_type)
        out = None
        for item in generator:
            if item["type"] == "complete":
                out = item["path"]
            elif item["type"] == "progress":
                print(f"Progress: {item['value']:.1%}", end="\r")
            elif item["type"] == "status":
                print(f"Status: {item['message']}")
                
        print(f"\n✓ SRT written: {out}")

if __name__ == "__main__":
    main()