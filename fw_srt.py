import argparse, math, os, re
from faster_whisper import WhisperModel

# Translation support — argos-translate only has xx↔en packages,
# so we chain through English as a pivot (e.g. de→en→fr).
TRANSLATION_PAIRS = {
    ("de", "fr"), ("de", "it"),
    ("fr", "de"), ("it", "de"),
}

def _get_translation_chain(from_code, to_code):
    """Return the chain of (src, tgt) pairs needed. Goes through 'en' pivot if needed."""
    if from_code == "en" or to_code == "en":
        return [(from_code, to_code)]
    # Chain through English
    return [(from_code, "en"), ("en", to_code)]

def ensure_translation_package(from_code, to_code):
    """Download and install the argos-translate language packages for the chain."""
    import argostranslate.package

    chain = _get_translation_chain(from_code, to_code)
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    for src, tgt in chain:
        # Check if already installed
        installed = argostranslate.package.get_installed_packages()
        already = any(p.from_code == src and p.to_code == tgt for p in installed)
        if already:
            continue

        pkg = next(
            (p for p in available if p.from_code == src and p.to_code == tgt),
            None
        )
        if pkg is None:
            raise ValueError(f"No argos-translate package found for {src} -> {tgt}")
        pkg.install()

def translate_text(text, from_code, to_code):
    """Translate a string using argos-translate, chaining through English if needed."""
    import argostranslate.translate
    chain = _get_translation_chain(from_code, to_code)
    result = text
    for src, tgt in chain:
        result = argostranslate.translate.translate(result, src, tgt)
    return result

def ts(t):
    ms = int(round((t - int(t)) * 1000))
    t = int(t)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_offset(s):
    if not s:
        return 0.0
    parts = [float(p) for p in s.split(":")]
    if len(parts) == 3:
        h, m, sec = parts
        return h * 3600 + m * 60 + sec
    if len(parts) == 2:
        m, sec = parts
        return m * 60 + sec
    return float(s)

def transcribe_file(audio_path, model_size="large-v3-turbo", lang=None, offset_str="", device="cpu", compute_type="int8", translate_to=None):
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
    
    # Determine source language for translation
    source_lang = lang if lang else (info.language if info.language else None)
    
    # Setup translation if requested
    do_translate = False
    translated_path = None
    if translate_to and source_lang:
        pair = (source_lang, translate_to)
        if pair in TRANSLATION_PAIRS:
            yield {"type": "status", "message": f"Installing translation package ({source_lang} → {translate_to})..."}
            ensure_translation_package(source_lang, translate_to)
            do_translate = True
            translated_path = audio_path.rsplit(".", 1)[0] + f"_{translate_to}.srt"
            yield {"type": "status", "message": f"Translation ready ({source_lang} → {translate_to})."}
        else:
            yield {"type": "status", "message": f"Translation pair {source_lang} → {translate_to} not supported. Skipping translation."}
    
    total_duration = info.duration
    
    trans_file = open(translated_path, "w", encoding="utf-8") if do_translate else None
    
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
                if trans_file:
                    translated = translate_text(text, source_lang, translate_to)
                    trans_file.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{translated}\n\n")
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
                        if trans_file:
                            translated = translate_text(text, source_lang, translate_to)
                            trans_file.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{translated}\n\n")
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
                    if trans_file:
                        translated = translate_text(text, source_lang, translate_to)
                        trans_file.write(f"{srt_index}\n{ts(start)} --> {ts(end)}\n{translated}\n\n")
                    srt_index += 1
    
    if trans_file:
        trans_file.close()
    
    result = {"type": "complete", "path": out_path}
    if do_translate and translated_path:
        result["translated_path"] = translated_path
    yield result

def main():
    ap = argparse.ArgumentParser(description="Captionary CLI - Auto-generate subtitles for audio/video files.")
    ap.add_argument("input_path", nargs="+", help="Audio file(s) or directory to transcribe")
    ap.add_argument("--model", default="large-v3-turbo", help="Model size: tiny, base, small, medium, large-v2, large-v3, large-v3-turbo. (Default: large-v3-turbo)")
    ap.add_argument("--lang", default=None, help="Language code (e.g. en, tr). (Default: Auto-detect)")
    ap.add_argument("--offset", default="", help="Time offset for subtitles, e.g. 00:30:00. (Default: None)")
    ap.add_argument("--device", default="cpu", help="Compute device: cpu or cuda. (Default: cpu)")
    ap.add_argument("--compute_type", default="int8", help="Quantization: int8, int8_float16, float16, float32. (Default: int8)")
    ap.add_argument("--translate_to", default=None, help="Translate subtitles to language code. Supported: de->fr, de->it, fr->de, it->de. (Default: None)")
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
        generator = transcribe_file(audio_file, args.model, args.lang, args.offset, args.device, args.compute_type, args.translate_to)
        out = None
        for item in generator:
            if item["type"] == "complete":
                if "translated_path" in item:
                    print(f"  ✓ Translated SRT: {item['translated_path']}")
                out = item["path"]
            elif item["type"] == "progress":
                print(f"Progress: {item['value']:.1%}", end="\r")
            elif item["type"] == "status":
                print(f"Status: {item['message']}")
                
        print(f"\n✓ SRT written: {out}")

if __name__ == "__main__":
    main()