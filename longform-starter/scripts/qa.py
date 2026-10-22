"""Job 5 — check the work the way a viewer watches: 10 frames a second, not 1.

    python qa.py <video_dir>                 # newest render (final if any, else draft)
    python qa.py <video_dir> --video renders/draft_v2.mp4
    python qa.py <video_dir> --no-transcribe # skip the re-listen (repeat check) for a quick pass

Machine checks for the six mistakes (rules/11-qa.md):
  1 animation plays twice        same graphic on neighbouring beats without "hold"; same graphic re-used within 20s
  2 graphic flashes              any graphic on screen < 0.9s
  3 text too late / too short    item text lands > 0.25s after its word; text gone before it can be read
  4 graphic covers the face      graphic stage overlaps the on-screen face box
  5 word said twice              re-transcribe the render, flag repeated 1-6 word phrases
  6 lips drift from voice        video vs audio duration, section frame counts vs plan, sync.json residual
+ loudness (-14 ±1 LUFS), true peak, dead air > 1.2s, resolution.
Visual pass: qa/strips/<beat>.jpg = 10 frames over the first second of every cut / graphic entrance (10 fps),
qa/sheet_<section>.jpg = all strips of a section stacked. Claude (or the longform-qa agent) READS the sheets.
Writes qa/report.md. Exit 1 on any FAIL.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from lf_common import FPS, SHORTIFY_SCRIPTS, ffmpeg, fmt_t, latest, probe_duration, read_json, run, video_dir, whisper_python
from cut import repeated_phrases

READ_WPS = 3.2       # words per second a viewer reads on screen


def strip(video: Path, t: float, out: Path, label: str) -> None:
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(video), "-t", "1.0",
                    "-vf", "fps=10,scale=256:-2,tile=10x1", "-frames:v", "1", str(out)], check=True)
    im = Image.open(out)
    ImageDraw.Draw(im).text((6, 4), label, fill=(255, 220, 0))
    im.save(out, quality=85)


def overlap(a, b) -> float:
    if not b:
        return 0.0
    x0, y0 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x1, y1 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    return inter / max(1.0, b["w"] * b["h"])


def loudness(video: Path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(i[-1]) if i else -99.0), (float(p[-1]) if p else 0.0)


def dead_air(video: Path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(video), "-af", "silencedetect=noise=-42dB:d=1.2", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(s, e))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--video")
    ap.add_argument("--no-transcribe", action="store_true")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    video = Path(a.video) if a.video else (latest(d / "renders", "final_v*.mp4") or latest(d / "renders", "draft_v*.mp4"))
    if not video or not video.exists():
        sys.exit("no render found — run render.py")
    tl = read_json(d / "timeline.json")
    beats = tl["beats"]
    qa = d / "qa"
    (qa / "strips").mkdir(parents=True, exist_ok=True)
    fails, warns, notes = [], [], []

    # 1 — animation plays twice
    for i in range(1, len(beats)):
        if beats[i]["graphic_hash"] and beats[i]["graphic_hash"] == beats[i - 1]["graphic_hash"]:
            fails.append(f"#1 {beats[i]['id']} @ {fmt_t(beats[i]['start'])}: same graphic as {beats[i - 1]['id']} re-animates — use \"hold\"")
    seen = {}
    for b in beats:
        h = b["graphic_hash"]
        if h and h in seen and 0 < b["start"] - seen[h]["start"] < 20 and seen[h]["id"] != beats[beats.index(b) - 1]["id"]:
            warns.append(f"#1 {b['id']} @ {fmt_t(b['start'])}: repeats the graphic from {seen[h]['id']} {b['start'] - seen[h]['start']:.0f}s earlier")
        if h:
            seen[h] = b
    # 2 — flashes
    for b in beats:
        if b["kind"] and b["kind"] not in ("hold", "lower") and b["dur"] < 0.9:
            fails.append(f"#2 {b['id']} @ {fmt_t(b['start'])}: {b['kind']} on screen {b['dur']:.2f}s — a flash")
    # 3 — late / unreadable text
    for ev in tl.get("text_events", []):
        if "appear_t" in ev and "word_t" in ev and ev["appear_t"] - ev["word_t"] > 0.25:
            fails.append(f"#3 {ev['beat']} item {ev['item'] + 1} @ {fmt_t(ev['word_t'])}: text lands "
                         f"{ev['appear_t'] - ev['word_t']:.2f}s after the word")
    bmap = {b["id"]: b for b in beats}
    for ev in tl.get("text_events", []):                   # an item that lands after its beat ends never shows at all
        b = bmap.get(ev["beat"])
        if b and ev.get("appear_t", 0) > b["end"] - 0.3:
            fails.append(f"#3 {b['id']} item {ev['item'] + 1} @ {fmt_t(b['start'])}: lands {ev['appear_t'] - b['end']:+.2f}s "
                         f"from the cut — it never gets seen")
    for ev in tl.get("text_events", []):
        b = bmap.get(ev["beat"])
        if b and ev.get("words") and (b["end"] - ev.get("appear_t", b["start"])) < ev["words"] / READ_WPS + 0.4:
            warns.append(f"#3 {b['id']} @ {fmt_t(b['start'])}: {ev['words']} words get {b['end'] - ev.get('appear_t', b['start']):.1f}s — too short to read")
    # 4 — face covered
    for r in tl.get("rects", []):
        ov = overlap(r, r.get("face"))
        if ov > 0.08:
            fails.append(f"#4 {r['beat']} ({r['kind']} on {r['shot']}): graphic covers {ov:.0%} of the face")
    # 6 — sync
    vd = probe_duration(video)
    if abs(vd - tl["total"]) > 2 / FPS:
        fails.append(f"#6 render is {vd:.3f}s but the cut is {tl['total']:.3f}s — picture and voice will drift")
    sj = d / "cut" / "sync.json"
    if sj.exists():
        s = read_json(sj)
        if s.get("residual_ms", 0) > 1000 / FPS:
            fails.append(f"#6 camera/mic sync residual {s['residual_ms']:.0f} ms (> 1 frame) — re-run sync_av.py, check drift")
        else:
            notes.append(f"camera/mic sync: lag {s['lag'] * 1000:+.0f} ms, drift {s['drift_ppm']:+.0f} ppm, residual {s['residual_ms']:.0f} ms ✓")
    else:
        notes.append("single-device recording — no camera/mic sync to verify (watch a 'p'/'b' in the strips)")
    # 5 — repeated words (re-listen)
    if not a.no_transcribe:
        wav = qa / "render16k.wav"
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        run([whisper_python(), str(SHORTIFY_SCRIPTS / "transcribe.py"), str(wav), str(qa / "render_words.json"), "small.en"])
        for t, ph in repeated_phrases(read_json(qa / "render_words.json")):
            if " " in ph:                                  # a phrase twice = duplicated audio at a splice
                fails.append(f"#5 @ {fmt_t(t)}: '{ph}' said twice in a row")
            else:                                          # one word twice = stutter or whisper noise: listen
                warns.append(f"#5 @ {fmt_t(t)}: '{ph} {ph}' — stutter or mishearing? check by ear")
    # audio
    lufs, peak = loudness(video)
    if abs(lufs + 14) > 1.0:
        fails.append(f"loudness {lufs:.1f} LUFS (target -14)")
    if peak > -1.0:
        warns.append(f"true peak {peak:.1f} dBFS (target ≤ -1.5)")
    for s0, s1 in dead_air(video):
        warns.append(f"dead air {fmt_t(s0)}–{fmt_t(s1)} ({s1 - s0:.1f}s)")
    if tl.get("music_volume", 0) > 0.1:
        warns.append(f"music volume {tl['music_volume']} — above 0.10 it fights the voice (rules/09-audio.md)")

    # visual: 10 fps strips at every cut / graphic entrance
    for f in (qa / "strips").glob("*.jpg"):
        f.unlink()
    by_sec = {}
    for b in beats:
        lbl = f"{b['id']} {fmt_t(b['start'])} {b['shot']}{' / ' + b['kind'] if b['kind'] else ''}"
        p = qa / "strips" / f"{b['id']}.jpg"
        strip(video, b["start"] - 0.1, p, lbl)
        by_sec.setdefault(b["section"], []).append(p)
    sheets = []
    for sid, ps in by_sec.items():
        ims = [Image.open(p) for p in ps]
        w = max(i.width for i in ims)
        for k in range(0, len(ims), 12):                    # ≤ 12 strips per sheet so they stay readable
            chunk = ims[k:k + 12]
            sheet = Image.new("RGB", (w, sum(i.height + 6 for i in chunk)), (20, 20, 20))
            y = 0
            for im in chunk:
                sheet.paste(im, (0, y))
                y += im.height + 6
            sp = qa / f"sheet_{sid}_{k // 12 + 1}.jpg"
            sheet.save(sp, quality=85)
            sheets.append(sp)

    md = [f"# QA — {video.name}", "", f"{len(beats)} beats · {fmt_t(vd)} · {lufs:.1f} LUFS · peak {peak:.1f} dBFS", ""]
    md += ["## FAIL (fix before the creator sees it)", ""] + ([f"- {x}" for x in fails] or ["- none"])
    md += ["", "## warn", ""] + ([f"- {x}" for x in dict.fromkeys(warns)] or ["- none"])
    md += ["", "## notes", ""] + [f"- {x}" for x in notes]
    md += ["", "## Visual pass — read every sheet (10 frames = the first second after each cut)", "",
           "Tick each one. Any ✗ is a fix in plan.json or a custom fragment, then rebuild that section only.", "",
           "- [ ] no graphic or text covers the creator's face; nothing sits on top of the captions",
           "- [ ] every graphic arrives with motion (no pop-in on frame 1, no frozen first frames)",
           "- [ ] nothing animates in twice; nothing flashes for a frame or two at a cut",
           "- [ ] text is on screen BEFORE or AS the word is said, never after",
           "- [ ] the corner panel / split never shows an empty frame or two the creators at once",
           "- [ ] chapter cards: number + title fully readable, no captions over them",
           "- [ ] lips match the voice on hard consonants (p, b, m) at the start of strips",
           "- [ ] editorial look: white canvas, black headline with ONE serif-italic accent, captions only on talking head",
           "- [ ] no scene opens on a blank canvas; the bubble is a full circle with its ring",
           "- [ ] pace: no talking head longer than ~5s", ""]
    md += [f"- `{p.relative_to(d).as_posix()}`" for p in sheets]
    (qa / "report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  {len(fails)} FAIL · {len(warns)} warn · {len(sheets)} sheets → {qa / 'report.md'}")
    for x in fails[:20]:
        print(f"  FAIL {x}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
