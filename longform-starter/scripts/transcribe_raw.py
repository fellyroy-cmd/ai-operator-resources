"""Transcribe the RAW recording (all takes) for the take picker.

    python transcribe_raw.py audio16k.wav [model]      # run inside the video's cut/ folder

Writes words.json ({word, text, start, end}) and segments.json in the current folder.
Whisper timestamps are only good for finding takes; the cutter finds exact cut points from the waveform.
"""
import json
import sys

from faster_whisper import WhisperModel

wav = sys.argv[1] if len(sys.argv) > 1 else "audio16k.wav"
model_name = sys.argv[2] if len(sys.argv) > 2 else "small.en"
model = WhisperModel(model_name, device="cpu", compute_type="int8")
segments, _ = model.transcribe(wav, word_timestamps=True, vad_filter=False, beam_size=5, language="en")
words, segs = [], []
for seg in segments:
    segs.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()})
    for w in (seg.words or []):
        words.append({"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word, "text": w.word.strip()})
    print(f"[{seg.start:7.2f} -> {seg.end:7.2f}] {seg.text.strip()}", flush=True)
json.dump(words, open("words.json", "w", encoding="utf-8"), indent=0)
json.dump(segs, open("segments.json", "w", encoding="utf-8"), indent=2)
print(f"\n{len(words)} words, {len(segs)} segments -> words.json / segments.json")
