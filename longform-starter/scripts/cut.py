"""Job 2 — the cut. Raw recording -> last clean take of every script line, dead air gone.

    python cut.py <video_dir>              # transcribe + pick takes -> cut/takes.md (REVIEW IT) -> render cut/cut.mp4
    python cut.py <video_dir> --pick-only  # stop after takes.md / keepers.json (edit keepers.json by hand, then...)
    python cut.py <video_dir> --render     # ...render from the existing keepers.json
    python cut.py <video_dir> --model medium   # whisper model for the RAW pass (default small.en; medium is slower, steadier)

Input: cut/synced.mp4 (from sync_av.py) if it exists, else the newest video in raw/.
How it picks: every script sentence is fuzzy-matched against the raw transcript. Of all the takes of a line, it keeps
the LAST one that reads clean (≥ 85% word match) before the next line starts. Lines the creator said in one breath stay one
window (fewer cuts = better flow). Unscripted stretches are listed in takes.md so ad-libs can be rescued.
Cutting itself is waveform_cut.py (inward onset scan, micro-fades, hard video cuts).
Then the cut is re-transcribed -> words.json (the timing source for everything after) + a repeated-phrase check.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lf_common import (FPS, SHORTIFY_SCRIPTS, VIDEO_CUT, ffmpeg, fmt_t, parse_script, probe_duration, read_json,
                       run, toks, video_dir, whisper_python, write_json)

CLEAN = 0.85          # a take counts as clean at this word-match ratio
FOUND = 0.62          # ...and counts as an attempt at the line at this ratio
JOIN_GAP = 0.9        # consecutive keepers closer than this in the source = one continuous take


def source_video(d: Path) -> Path:
    if (d / "cut" / "synced.mp4").exists():
        return d / "cut" / "synced.mp4"
    vids = [p for p in sorted((d / "raw").glob("*")) if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".m4v")]
    if not vids:
        sys.exit("no video in raw/ — drop the camera file there (camera.mp4)")
    if len(vids) > 1:
        print(f"  several raw videos — using {vids[-1].name}. Join multi-file recordings first or pass the right one.")
    return vids[-1]


def transcribe_raw(d: Path, src: Path, model: str) -> list[dict]:
    c = d / "cut"
    wav = c / "audio16k.wav"
    if not wav.exists():
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    if not (c / "words.json").exists():
        print(f"  transcribing raw take with {model} (a 20-min take is ~10-20 min on CPU)...")
        run([whisper_python(), str(VIDEO_CUT / "transcribe_raw.py"), "audio16k.wav", model], cwd=c)
    return json.loads((c / "words.json").read_text(encoding="utf-8"))


def find_takes(sent: list[str], rt: list[str], lo: int) -> list[tuple[int, int, float]]:
    """All (start_tok, end_tok, ratio) windows in rt[lo:] that read like this sentence."""
    n = len(sent)
    if n == 0:
        return []
    heads = set(sent[:3])
    out = []
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(sent)
    i = lo
    while i < len(rt):
        if rt[i] not in heads:
            i += 1
            continue
        best = (0.0, i + n)
        for L in {max(1, int(n * 0.8)), n, int(n * 1.2) + 1}:
            sm.set_seq1(rt[i:i + L])
            r = sm.ratio()
            if r > best[0]:
                best = (r, i + L)
        if best[0] >= FOUND:
            # trim the window end to the last token that matches the sentence's last word
            j = best[1]
            for k in range(min(len(rt), best[1] + 2) - 1, i, -1):
                if rt[k] == sent[-1]:
                    j = k + 1
                    break
            out.append((i, j, round(best[0], 3)))
            i += max(1, n // 2)
        else:
            i += 1
    return out


def pick(d: Path, model: str) -> None:
    sc = parse_script(d / "script.md")
    src = source_video(d)
    words = transcribe_raw(d, src, model)
    # flatten words -> tokens with owner word index
    rt, owner = [], []
    for wi, w in enumerate(words):
        for t in toks(w["word"]):
            rt.append(t)
            owner.append(wi)
    lines = [(s["id"], x) for s in sc["sections"] for x in s["sentences"]]
    takes = [find_takes(toks(x), rt, 0) for _, x in lines]

    chosen, report, cursor = [], [], 0
    for li, (sid, text) in enumerate(lines):
        cands = [t for t in takes[li] if t[0] >= cursor]
        nxt = next((t for t in (takes[li + 1] if li + 1 < len(lines) else []) if t[0] >= cursor and t[2] >= CLEAN), None)
        bound = nxt[0] if nxt else len(rt)
        before = [t for t in cands if t[0] < bound]
        clean = [t for t in before if t[2] >= CLEAN]
        pickd = clean[-1] if clean else (max(before, key=lambda t: t[2]) if before else None)
        flag = "" if clean else ("MISSING" if not pickd else f"ROUGH {pickd[2]:.0%}")
        if pickd:
            a, b = words[owner[pickd[0]]]["start"], words[owner[pickd[1] - 1]]["end"]
            chosen.append({"line": li, "sid": sid, "a": a, "b": b, "w0": owner[pickd[0]], "w1": owner[pickd[1] - 1],
                           "ratio": pickd[2], "text": text})
            cursor = pickd[1]
        report.append((li, sid, text, len(before), pickd, flag))

    # gap-fill: a MISSING line with unclaimed speech between its neighbours' takes is almost always the line itself,
    # misheard by whisper ("real builds" -> "reboots"). Keep that speech instead of silently dropping the line.
    attempted_by = {}
    for lj in range(len(lines)):
        for t in takes[lj]:
            for k in range(t[0], min(t[1], len(owner))):
                attempted_by.setdefault(owner[k], set()).add(lj)
    by_line = {c["line"]: c for c in chosen}
    for li, sid, text, n, p, flag in list(report):
        if flag != "MISSING":
            continue
        prev = max((c for c in chosen if c["line"] < li), key=lambda c: c["line"], default=None)
        nxt = min((c for c in chosen if c["line"] > li), key=lambda c: c["line"], default=None)
        if not prev or not nxt:
            continue
        span = [wi for wi in range(prev["w1"] + 1, nxt["w0"]) if not (attempted_by.get(wi, set()) - {li})]
        runs, cur = [], []
        for wi in span:
            if cur and wi != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(wi)
        if cur:
            runs.append(cur)
        best = max(runs, key=len, default=None)
        if best and len(best) >= max(2, len(toks(text)) // 3):
            c = {"line": li, "sid": sid, "a": words[best[0]]["start"], "b": words[best[-1]]["end"], "w0": best[0],
                 "w1": best[-1], "ratio": 0.0, "text": text}
            chosen.append(c)
            by_line[li] = c
            report[li] = (li, sid, text, 0, None, "GAP-FILL — whisper garbled it, check by ear")
    chosen.sort(key=lambda c: c["line"])

    # merge lines said in one breath (contiguous in the source) into one keeper window
    keepers = []
    for c in chosen:
        if keepers and c["w0"] == keepers[-1]["_w1"] + 1 and c["a"] - keepers[-1]["b"] < JOIN_GAP:
            k = keepers[-1]
            k["b"], k["_w1"] = c["b"], c["w1"]
            k["label"] += f"+L{c['line'] + 1}"
            continue
        # tight windows: the cutter picks words by midpoint inside [a, b], so a fat pad would drag in a false start
        keepers.append({"a": round(max(0.0, c["a"] - 0.05), 3), "b": round(c["b"] + 0.05, 3), "label": f"L{c['line'] + 1}",
                        "_w0": c["w0"], "_w1": c["w1"]})
    for i in range(len(keepers) - 1):                       # padded windows must not overlap (duplicate audio)
        if keepers[i]["b"] > keepers[i + 1]["a"]:
            mid = round((keepers[i]["b"] + keepers[i + 1]["a"]) / 2, 3)
            keepers[i]["b"], keepers[i + 1]["a"] = mid, mid
    write_json(d / "cut" / "keepers.json", [{k: v for k, v in x.items() if not k.startswith("_")} for x in keepers])

    # unscripted stretches (ad-libs worth rescuing?)
    used = set()
    for c in chosen:
        used.update(range(c["w0"], c["w1"] + 1))
    attempted = set()
    for li in range(len(lines)):
        for t in takes[li]:
            attempted.update(owner[k] for k in range(t[0], min(t[1], len(owner))))
    extra, run_ = [], []
    for wi in range(len(words)):
        if wi not in used and wi not in attempted:
            run_.append(wi)
        elif run_:
            extra.append(run_)
            run_ = []
    if run_:
        extra.append(run_)
    extra = [r for r in extra if words[r[-1]]["end"] - words[r[0]]["start"] > 3.0]

    md = [f"# Takes — {d.name}", "", f"Source: `{src.name}` · {len(lines)} script lines · {len(keepers)} keeper windows "
          f"(lines said in one breath are merged)", "",
          "Swap a take: edit `cut/keepers.json` (a/b are rough seconds in the source), then `python cut.py <dir> --render`.", "",
          "| line | takes | kept (source) | match | flag | text |", "|---|---|---|---|---|---|"]
    for li, sid, text, n, p, flag in report:
        if p:
            md.append(f"| L{li + 1} | {n} | {fmt_t(words[owner[p[0]]]['start'])} | {p[2]:.0%} | {flag} | {text[:80]} |")
        elif li in by_line:
            md.append(f"| L{li + 1} | — | {fmt_t(by_line[li]['a'])} | — | **{flag}** | {text[:80]} |")
        else:
            md.append(f"| L{li + 1} | 0 | — | — | **{flag}** | {text[:80]} |")
    if extra:
        md += ["", "## Unscripted stretches (dropped — rescue any good ad-lib by adding a window to keepers.json)", ""]
        for r in extra:
            md.append(f"- {fmt_t(words[r[0]]['start'])}–{fmt_t(words[r[-1]]['end'])}: "
                      f"\"{''.join(words[k]['word'] for k in r).strip()[:160]}\"")
    (d / "cut" / "takes.md").write_text("\n".join(md), encoding="utf-8")
    flags = [r for r in report if r[5]]
    print(f"  {len(lines)} lines -> {len(keepers)} keeper windows · {len(flags)} flagged · {len(extra)} unscripted stretches")
    for li, sid, text, n, p, flag in flags[:15]:
        print(f"    L{li + 1} {flag}: {text[:70]}")
    print(f"  review: {d / 'cut' / 'takes.md'}")


def render_cut(d: Path, head: float, tail: float) -> None:
    c = d / "cut"
    src = source_video(d)
    out = c / "cut.mp4"
    r = run([sys.executable, str(Path(__file__).resolve().parent / "waveform_cut.py"), "--input", str(src), "--audio", "audio16k.wav",
             "--words", "words.json", "--keepers", "keepers.json", "--out", str(out),
             "--head", str(head), "--tail", str(tail), "--end-tail", "0.6", "--crf", "16"], cwd=c, check=False)
    if r.returncode != 0 or not out.exists():
        sys.exit("cut failed — see the cutter output above")
    # constant frame rate on the frame grid so sections split cleanly later
    cfr = c / "cut_cfr.mp4"
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(out), "-r", str(FPS), "-c:v", "libx264", "-preset", "fast",
                    "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    "-movflags", "+faststart", str(cfr)], check=True)
    shutil.move(str(cfr), str(out))
    print(f"  cut: {out}  ({probe_duration(out):.1f}s)")

    # the cut's own word timings (source of truth for every later job) + repeat check
    wav = c / "cut16k.wav"
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(out), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    run([whisper_python(), str(SHORTIFY_SCRIPTS / "transcribe.py"), str(wav), str(d / "words.json"), "small.en"])
    words = read_json(d / "words.json")
    hits = repeated_phrases(words)
    reps = [(t, ph) for t, ph in hits if " " in ph]          # 2+ words twice = a splice duplicated audio (the real bug)
    for t, ph in reps:
        print(f"  !! REPEAT at {fmt_t(t)}: '{ph}' — a take overlapped its neighbour; fix keepers.json and re-render")
    for t, ph in hits:
        if " " not in ph:
            print(f"  warn: '{ph} {ph}' at {fmt_t(t)} — a stutter or whisper noise; listen, re-pick the take if real")
    # a frame with a 10% grid so the face box can be read off it (plan.json "speaker.face")
    grid_frame(out, c / "frame_grid.jpg", min(20.0, probe_duration(out) / 3))
    print(f"  words.json ({len(words)} words) · {'REPEATS FOUND' if reps else 'content clean'} · face grid: {c / 'frame_grid.jpg'}")


def repeated_phrases(words: list[dict], max_n: int = 6) -> list[tuple[float, str]]:
    tk = [(toks(w["text"]), w["start"]) for w in words]
    seq = [(t, s) for ts, s in tk for t in ts]
    hits = []
    i = 0
    while i < len(seq):
        found = False
        for n in range(max_n, 0, -1):
            a = [x for x, _ in seq[i:i + n]]
            b = [x for x, _ in seq[i + n:i + 2 * n]]
            if len(a) == n and a == b and (n > 1 or a[0] not in {"that", "had", "very", "really", "no", "so"}):
                hits.append((seq[i][1], " ".join(a)))
                i += 2 * n
                found = True
                break
        if not found:
            i += 1
    return hits


def grid_frame(video: Path, out: Path, t: float) -> None:
    vf = ("drawgrid=w=iw/10:h=ih/10:t=2:c=white@0.5,"
          "drawtext=text='face box\\: read x y w h as fractions of the frame (grid = 0.1)':x=20:y=20:fontsize=28:fontcolor=yellow")
    r = subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", vf,
                        str(out)], capture_output=True)
    if r.returncode != 0:                                   # drawtext needs a font on some builds — grid alone is fine
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "drawgrid=w=iw/10:h=ih/10:t=2:c=white@0.5", str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--pick-only", action="store_true")
    ap.add_argument("--render", action="store_true", help="render from existing keepers.json")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--head", type=float, default=0.04)
    ap.add_argument("--tail", type=float, default=0.09)
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    (d / "cut").mkdir(exist_ok=True)
    if not a.render:
        pick(d, a.model)
        if a.pick_only:
            return
    render_cut(d, a.head, a.tail)


if __name__ == "__main__":
    main()
