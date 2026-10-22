"""Word-level transcript with faster-whisper.

    python transcribe.py <audio.wav> <out words.json> [model]

Output: [{"text": "This", "word": "This", "start": 0.08, "end": 0.24}, ...]
"""
import json
import sys

from faster_whisper import WhisperModel

audio, out = sys.argv[1], sys.argv[2]
model_name = sys.argv[3] if len(sys.argv) > 3 else "small.en"
model = WhisperModel(model_name, device="cpu", compute_type="int8")
segments, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False, beam_size=5)
words = [{"text": w.word.strip(), "word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
         for s in segments for w in s.words if w.word.strip()]
with open(out, "w", encoding="utf-8") as f:
    json.dump(words, f, indent=1, ensure_ascii=False)
print(f"{len(words)} words -> {out}")
