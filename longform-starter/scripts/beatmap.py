"""Job 3 — the plan, step 1: the beat map.

    python beatmap.py <video_dir>            # words.json + script.md -> plan.json skeleton + beatmap.md
    python beatmap.py <video_dir> --force    # overwrite an existing plan.json (careful: loses your visual plan)
    python beatmap.py <video_dir> --table    # just re-render beatmap.md from the current plan.json (timed)

A beat map = every sentence the creator says + what's on screen while she says it. The skeleton gives one beat per
sentence, timed to the cut, with chapter cards already placed. Claude then does the creative pass (rules/05-beatmap.md):
split sentences where the IDEA changes, give every beat a shot + graphic + reason. the creator approves beatmap.md
BEFORE anything is built — a plan is cheap to change, a finished graphic isn't.
"""
from __future__ import annotations

import argparse
import sys

from lf_common import fmt_t, parse_script, read_json, video_dir, write_json
from align import align, correct_words


def skeleton(d) -> dict:
    sc = parse_script(d / "script.md")
    plan = {
        "title": sc["title"],
        "style": "editorial",
        "theme": "dark",
        "speaker": {"face": {"x": 0.42, "y": 0.18, "w": 0.16, "h": 0.30}},   # READ IT OFF cut/frame_grid.jpg
        "music": {"file": "", "volume": 0.07},
        "captions": True,
        "sections": [],
    }
    bi = 0
    for s in sc["sections"]:
        sec = {"id": s["id"], "title": s["title"], "short": s["title"].split()[0].capitalize() if s["chapter"] else "",
               "chapter": s["chapter"], "beats": []}
        for k, x in enumerate(s["sentences"]):
            bi += 1
            b = {"id": f"b{bi:03d}", "say": x, "shot": "full", "graphic": None, "reason": ""}
            if k == 0 and s["chapter"]:
                b.update(shot="graphic", graphic={"kind": "chapter", "n": s["chapter"], "title": s["title"]},
                         reason="chapter card: tells the viewer a new part starts and where we are in the spine")
            sec["beats"].append(b)
        plan["sections"].append(sec)
    return plan


def timed(d, plan) -> list[dict]:
    words = read_json(d / "words.json")
    beats = [b for s in plan["sections"] for b in s["beats"]]
    words = correct_words(beats, words)
    total = words[-1]["end"] + 0.5
    align(beats, words, total)
    return beats


def table(d, plan) -> None:
    beats = timed(d, plan)
    sec_of = {b["id"]: s for s in plan["sections"] for b in s["beats"]}
    md = [f"# Beat map — {plan.get('title') or d.name}", "",
          f"{len(beats)} beats over {fmt_t(beats[-1]['end'])}. Approve this before anything is built.", "",
          "| id | time | dur | shot | headline | graphic | say | reason |", "|---|---|---|---|---|---|---|---|"]
    last = None
    for b in beats:
        s = sec_of[b["id"]]
        if s["id"] != last:
            md.append(f"| **{s['id']}** | | | | | | **{('%02d · ' % s['chapter']) if s.get('chapter') else ''}{s['title']}** | |")
            last = s["id"]
        g = b.get("graphic") or {}
        if g == "hold":
            g = {"kind": "hold"}
        gdesc = g.get("kind", "—")
        if g.get("kind") == "custom":
            gdesc = f"custom: {g.get('brief', '')[:50]}"
        elif g:
            gdesc += ": " + str(g.get("title") or g.get("text") or g.get("label") or ", ".join(
                str(i.get("title", i) if isinstance(i, dict) else i) for i in g.get("items", [])[:4]))[:50]
        md.append(f"| {b['id']} | {fmt_t(b['start'])} | {b['dur']:.1f}s | {b['shot']} | {b.get('headline') or ''} | {gdesc} | {b['say'][:90]} | "
                  f"{b.get('reason', '')[:70]} |")
    (d / "beatmap.md").write_text("\n".join(md), encoding="utf-8")
    plain = sum(1 for b in beats if b["shot"] == "full" and not b.get("graphic"))
    print(f"  {len(beats)} beats · {plain} plain talking-head · wrote {d / 'beatmap.md'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--table", action="store_true")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    if not (d / "words.json").exists():
        sys.exit("no words.json — run cut.py first (it transcribes the cut)")
    p = d / "plan.json"
    if a.table:
        table(d, read_json(p))
        return
    if p.exists() and not a.force:
        sys.exit("plan.json exists — use --table to refresh beatmap.md, or --force to start over")
    plan = skeleton(d)
    write_json(p, plan)
    print(f"  wrote {p}")
    table(d, plan)


if __name__ == "__main__":
    main()
