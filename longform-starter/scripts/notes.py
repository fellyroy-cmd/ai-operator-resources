"""Job 6 — learning from notes, step 1: put every note on the beat it's about.

    python notes.py <video_dir>

Reads notes.md: open items like "- [ ] 3:12 music too loud here" (timestamps from the draft the creator watched).
Writes qa/notes_map.md: note -> section -> beat -> what was on screen, plus the rulebook it most likely belongs to.
Then Claude: (1) fixes the video, (2) finds the rule that would have prevented it and REWRITES that rule in place
(rules/*.md, or the constant in build.py/operator.css if the rule is code), (3) logs it in rules/CHANGELOG.md,
(4) ticks the note "- [x] ... → fixed + rule 07 updated". See rules/12-learning.md.
"""
from __future__ import annotations

import argparse
import re

from lf_common import fmt_t, parse_t, read_json, video_dir

ROUTES = [  # crude keyword routing: the note's likely rulebook (Claude confirms)
    (r"music|sfx|sound|loud|quiet|whoosh|audio|volume", "09-audio"),
    (r"caption|subtitle|word.*highlight", "08-captions"),
    (r"lip|sync|mouth|late voice", "04-cut"),
    (r"retake|stutter|pause|dead air|repeat|said twice|cut (?:out|this)|ad.?lib", "04-cut"),
    (r"slow|fast|ease|bounce|animat|motion|snappy|timing|lands", "07-motion"),
    (r"face|cover|overlap|panel|corner|split|punch|zoom|two of me", "06-visuals"),
    (r"colou?r|font|type|ugly|cheap|card|style|look", "06-visuals"),
    (r"fact|wrong|number|claim|source", "03-facts"),
    (r"boring|confus|unclear|too long|drag|hook|intro|chapter", "01-script"),
    (r"graphic|show|screen|visual|b-?roll|screenshot|beat", "05-beatmap"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    tl = read_json(d / "timeline.json")
    beats = tl["beats"]
    notes = []
    for line in (d / "notes.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-\s*\[\s\]\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*[-–:]?\s*(.+)", line)
        if m and m.group(2).strip():
            notes.append((parse_t(m.group(1)), m.group(2).strip()))
    md = [f"# Notes map — {d.name}", "", f"{len(notes)} open notes", "",
          "| # | time | note | beat | section | on screen | said | rulebook |", "|---|---|---|---|---|---|---|---|"]
    for i, (t, note) in enumerate(notes, 1):
        b = next((x for x in beats if x["start"] <= t < x["end"]), beats[-1])
        rb = next((r for pat, r in ROUTES if re.search(pat, note, re.I)), "05-beatmap")
        md.append(f"| {i} | {fmt_t(t)} | {note} | {b['id']} | {b['section']} | {b['shot']}"
                  f"{' / ' + b['kind'] if b['kind'] else ''} | {b['say'][:60]} | {rb} |")
        print(f"  {i}. {fmt_t(t)} {b['id']} [{rb}] {note}")
    md += ["", "For every note: fix the video → find the rule that would have prevented it → REWRITE that rule "
           "(don't stack a second one on top) → one line in rules/CHANGELOG.md → tick the note."]
    (d / "qa" / "notes_map.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  wrote {d / 'qa' / 'notes_map.md'}")


if __name__ == "__main__":
    main()
