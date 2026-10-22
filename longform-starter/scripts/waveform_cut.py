"""Cut the keeper takes out of a raw recording at the TRUE speech edges (from the waveform, not whisper).

    python waveform_cut.py --input raw.mp4 --audio audio16k.wav --words words.json --keepers keepers.json --out cut.mp4

keepers.json: [{"a": 12.3, "b": 17.9, "label": "L4"}, ...]  rough seconds around each take you keep.
For each window: find its words, scan FORWARD from just before the first word to the first sustained sound above
the threshold (that skips the breath), and BACKWARD from just after the last word. Pad a little, add tiny audio fades
so cuts don't click, keep the video cuts hard, and join everything. Warns if two windows share audio (that would
play a phrase twice).
"""
import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lf_common import ffmpeg  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--audio", default="audio16k.wav")
ap.add_argument("--words", default="words.json")
ap.add_argument("--keepers", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--head", type=float, default=0.04)
ap.add_argument("--tail", type=float, default=0.09)
ap.add_argument("--end-tail", type=float, default=0.6, help="extra hold after the very last line")
ap.add_argument("--thr", type=float, default=0.005, help="speech energy threshold (breath < thr < word)")
ap.add_argument("--fade", type=float, default=0.014)
ap.add_argument("--crf", type=int, default=16)
a = ap.parse_args()

words = json.load(open(a.words, encoding="utf-8"))
keepers = json.load(open(a.keepers, encoding="utf-8"))
with wave.open(a.audio, "rb") as w:
    sr = w.getframerate()
    sig = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
win, hop, sus = int(0.02 * sr), 0.004, 0.04


def rms(t):
    i = int(t * sr)
    s = sig[max(0, i - win // 2): i + win // 2]
    return float(np.sqrt(np.mean(s ** 2))) if len(s) else 0.0


def loud_for(t, d=sus):
    k = t
    while k < t + d:
        if rms(k) < a.thr:
            return False
        k += hop
    return True


def onset(t_word):
    t = t_word - 0.35
    while t < t_word + 1.0:
        if rms(t) >= a.thr and loud_for(t):
            return t
        t += hop
    return t_word


def offset(t_word):
    t = t_word + 0.35
    while t > t_word - 1.0:
        if rms(t) >= a.thr and loud_for(t - sus):
            return t
        t -= hop
    return t_word


segs = []
for k in keepers:
    ws = [x for x in words if k["a"] <= (x["start"] + x["end"]) / 2 <= k["b"]]
    if not ws and "on" in k and "off" in k:
        segs.append({"label": k.get("label", ""), "on": k["on"], "off": k["off"]})
        continue
    if not ws:
        print(f'!! no words in {k["a"]}-{k["b"]} ({k.get("label", "")}) — check keepers.json')
        continue
    # exact "on"/"off" (seconds, read off a loudness map) override the scan — for restarts whisper can't time
    segs.append({"label": k.get("label", ""), "on": k.get("on", onset(ws[0]["start"]) if ws else None),
                 "off": k.get("off", offset(ws[-1]["end"]) if ws else None)})
for i in range(len(segs)):
    for j in range(i + 1, len(segs)):
        lo, hi = max(segs[i]["on"], segs[j]["on"]), min(segs[i]["off"], segs[j]["off"])
        if hi - lo > 0.05:
            print(f'!! OVERLAP {segs[i]["label"]} & {segs[j]["label"]}: {hi - lo:.2f}s of shared audio — merge them')

parts, labels = [], ""
total = 0.0
for n, s in enumerate(segs):
    st = max(0.0, s["on"] - a.head)
    en = s["off"] + (max(a.tail, a.end_tail) if n == len(segs) - 1 else a.tail)
    d = en - st
    total += d
    parts.append(f"[0:v]trim=start={st:.3f}:end={en:.3f},setpts=PTS-STARTPTS[v{n}];"
                 f"[0:a]atrim=start={st:.3f}:end={en:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:st=0:d={a.fade},afade=t=out:st={max(0, d - a.fade):.3f}:d={a.fade}[a{n}]")
    labels += f"[v{n}][a{n}]"
    print(f'{s["label"]:24s} {st:8.3f} - {en:8.3f}  ({d:5.2f}s)')
fc = ";".join(parts) + f";{labels}concat=n={len(segs)}:v=1:a=1[vout][aout]"
script = Path(a.out).with_suffix(".filter.txt")
script.write_text(fc, encoding="utf-8")
print(f"\n~{total:.1f}s across {len(segs)} segments -> {a.out}")
r = subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", a.input, "-/filter_complex", str(script), "-map", "[vout]",
                    "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out], capture_output=True, text=True)
script.unlink(missing_ok=True)
if r.returncode:
    sys.exit(r.stderr[-1500:])
print("done")
