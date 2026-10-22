"""Job 4b — render. Sections go through ONE queue, one at a time (parallel renders max out the machine and
kill each other), unchanged sections are skipped, then everything is stitched and the audio is mastered.

    python render.py <video_dir> --draft          # half-size, fast: for watching the cut and writing notes
    python render.py <video_dir>                  # full quality (run it overnight: it locks the machine for a while)
    python render.py <video_dir> --section s03    # re-render one section only (still re-stitches)
    python render.py <video_dir> --workers 4      # Hyperframes workers per section render (default: auto)

build.py must have been run in the same mode (--draft or not) first; this checks.
Audio is NOT rendered in Hyperframes: the master is voice (from the cut) + an SFX bed (built here from timeline.json)
+ music ducked under the voice, normalised to -14 LUFS / -1.5 dBTP.
Writes renders/draft_vN.mp4 or renders/final_vN.mp4.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

from lf_common import FPS, SHORTIFY_ASSETS, ffmpeg, probe_duration, read_json, run, video_dir
from build import SFX_FILE, SFX_MASTER, SFX_VOL

SR = 48000


def clear_extract_cache() -> None:
    """Hyperframes caches every extracted source frame and never cleans up: at full quality (PNG) that's ~85 MB per second
    of footage, and it filled drive D mid-render on 2026-10-21. The cache only helps a re-render of the same section,
    so wipe it after each section — peak disk use = one section's frames."""
    cache = os.environ.get("HYPERFRAMES_EXTRACT_CACHE_DIR")
    if cache and Path(cache).is_dir():
        for p in Path(cache).iterdir():
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)


def section_hash(sdir: Path, quality: str) -> str:
    h = hashlib.sha1(quality.encode())
    for p in sorted(sdir.rglob("*")):
        if p.is_file() and not ({"renders", ".hyperframes"} & set(p.parts)) and p.name != ".footage_stamp":   # .hyperframes = render state, rewritten every render
            h.update(str(p.relative_to(sdir)).encode())
            h.update(str(p.stat().st_size).encode())
            if p.suffix in (".html", ".json", ".css", ".js"):
                h.update(p.read_bytes())
            else:
                h.update(str(p.stat().st_mtime_ns).encode())
    return h.hexdigest()[:16]


def decode(path: Path) -> np.ndarray:
    out = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def sfx_bed(events, total: float, out: Path) -> int:
    bed = np.zeros(int(total * SR) + SR, dtype=np.float32)
    cache = {}
    for name, t in events:
        if name not in cache:
            f = SHORTIFY_ASSETS / "sfx" / SFX_FILE[name]
            cache[name] = decode(f) * SFX_VOL[name] * SFX_MASTER if f.exists() else None   # missing sound = silent
        s = cache[name]
        if s is None:
            continue
        i = int(max(0.0, t) * SR)
        j = min(len(bed), i + len(s))
        bed[i:j] += s[: j - i]
    bed = np.clip(bed[: int(total * SR)], -1, 1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((bed * 32767).astype(np.int16).tobytes())
    return len(events)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--section")
    ap.add_argument("--workers", default="auto")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    tl = read_json(d / "timeline.json")
    if bool(tl.get("draft")) != a.draft:
        sys.exit(f"timeline.json was built {'DRAFT' if tl.get('draft') else 'FULL'} — re-run build.py "
                 f"{'--draft' if a.draft else '(no --draft)'} first")
    quality = "draft" if a.draft else "high"
    tag = "draft" if a.draft else "final"
    rdir = d / "renders"
    sec_out = rdir / "sections"
    sec_out.mkdir(parents=True, exist_ok=True)

    # ── the queue: one section at a time
    parts, t_all = [], time.time()
    for s in tl["sections"]:
        sdir = d / "sections" / s["id"]
        out = sec_out / f"{s['id']}_{tag}.mp4"
        hfile = sec_out / f"{s['id']}_{tag}.hash"
        h = section_hash(sdir, quality)
        fresh = out.exists() and hfile.exists() and hfile.read_text() == h
        if (a.section and a.section != s["id"]) or (fresh and not a.section):
            if not out.exists():
                sys.exit(f"{s['id']} has never been rendered in {tag} mode — render without --section first")
            print(f"  {s['id']}: {'unchanged — skipped' if fresh else 'kept'}")
            parts.append(out)
            continue
        print(f"  {s['id']}: rendering {s['dur']:.1f}s ({s['frames']} frames) ...")
        t = time.time()
        cmd = ["npx", "--yes", "hyperframes", "render", "--output", out, "--quality", quality, "--workers", a.workers]
        if not a.draft:   # full quality: PNG source frames (auto = JPEG, softens the talking head) + CRF 12 (the creator, 2026-10-21)
            cmd += ["--video-frame-format", "png", "--crf", "12"]
        try:
            run(cmd, cwd=sdir)
        except Exception:                                   # Hyperframes sometimes loses a browser worker — retry once
            print("  render failed, retrying once with 1 worker...")
            run([x if x != a.workers else "1" for x in cmd], cwd=sdir)
        hfile.write_text(h)
        clear_extract_cache()
        got = probe_duration(out)
        if abs(got - s["dur"]) > 1.5 / FPS:
            print(f"  !! {s['id']}: rendered {got:.3f}s but expected {s['dur']:.3f}s — sync will drift; check the composition")
        print(f"     done in {time.time() - t:.0f}s")
        parts.append(out)

    # ── stitch video (identical encoder settings per section -> stream copy)
    lst = rdir / "_concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    vid = rdir / "_video.mp4"
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-map", "0:v:0",
                    "-c", "copy", str(vid)], check=True)

    # ── audio master: voice + sfx bed + ducked music
    total = tl["total"]
    bed = rdir / "_sfx.wav"
    n = sfx_bed(tl["sfx"], total, bed)
    plan = read_json(d / "plan.json")
    music = (plan.get("music") or {}).get("file") or ""
    music_p = (d / music) if music else (SHORTIFY_ASSETS / "music" / "bed.mp3")
    mv = float(tl.get("music_volume", 0.07))
    cut = d / "cut" / "cut.mp4"
    inputs = ["-i", str(vid), "-i", str(cut), "-i", str(bed)]
    # voice: high-pass + gentle compression so loudness stays even (the reference measures LRA 2 LU — very steady)
    fc = ("[1:a]aresample=48000,highpass=f=80,acompressor=threshold=-22dB:ratio=3:attack=8:release=160:makeup=3,"
          "asplit=2[voice][key];[2:a]aresample=48000[sfx];")
    if music_p.exists() and mv > 0:
        inputs += ["-stream_loop", "-1", "-i", str(music_p)]
        fc += (f"[3:a]aresample=48000,volume={mv},afade=t=in:d=1.5,afade=t=out:st={max(0, total - 3):.2f}:d=3[mus];"
               "[mus][key]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=450[duck];"
               "[voice][sfx][duck]amix=inputs=3:normalize=0:duration=first[mix];")
    else:
        fc += "[key]anullsink;[voice][sfx]amix=inputs=2:normalize=0:duration=first[mix];"   # no music: drop the ducking key
    fc += "[mix]anull[aout]"
    # pass 1: mix to PCM; pass 2: two-pass loudnorm (single-pass undershoots by ~1 LU on speech)
    mix = rdir / "_mix.wav"
    subprocess.run([ffmpeg(), "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[aout]", "-c:a", "pcm_s16le",
                    "-ar", "48000", "-t", f"{total:.3f}", str(mix)], check=True)
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(mix), "-af", "loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    import json as _json
    import re as _re
    m = _json.loads(_re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)[-1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=7:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          "aresample=48000,alimiter=limit=0.66:attack=1:release=60:level=false")   # -3.6 dB ceiling: linear loudnorm + AAC overshoot TP (v1 -0.4, v3 -0.7 at 0.79)
    k = len(list(rdir.glob(f"{tag}_v*.mp4"))) + 1
    final = rdir / f"{tag}_v{k}.mp4"
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(vid), "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0",
                    "-af", ln, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", f"{total:.3f}",
                    "-movflags", "+faststart", str(final)], check=True)
    for p in (vid, bed, lst, mix):
        p.unlink(missing_ok=True)
    vd, ad = probe_duration(final), total
    print(f"  {final}  ({vd:.1f}s · {n} sfx · music {'on' if music_p.exists() and mv > 0 else 'off'} · "
          f"{(time.time() - t_all) / 60:.1f} min)")
    if abs(vd - ad) > 2 / FPS:
        print(f"  !! video {vd:.3f}s vs voice {ad:.3f}s — lips will drift; investigate before shipping")
    print(f"  next: python qa.py \"{d}\"")


if __name__ == "__main__":
    main()
