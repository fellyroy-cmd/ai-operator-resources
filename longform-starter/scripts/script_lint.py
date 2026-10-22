"""Job 1 gate — lint script.md and export the teleprompter.

    python script_lint.py <video_dir>

Checks (rules/01-script.md + rules/03-facts.md):
  ERROR  placeholder [brackets] left in a spoken line
  ERROR  a sentence with a number/$/% that has no matching row in facts.md (no proof -> cut the line)
  ERROR  no chapters, or the cold open runs past ~20s
  warn   runtime outside 8-13 min, sentence > 28 words, chapter > 2.5 min, < 2 chapters, no Discord CTA,
         no open loop in the intro
Writes teleprompter.md: one sentence per line, chapter breaks, big gaps — read it off a phone or a prompter app.
Exit 1 on errors.
"""
from __future__ import annotations

import argparse
import re
import sys

from lf_common import WPM, parse_script, toks, video_dir


def fact_rows(path) -> list[str]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1] and not set(cells[1]) <= {"-"} and cells[1].lower() != "claim (as spoken)":
            rows.append(" ".join(cells[1:3]).lower())
    return rows


NUM_RE = re.compile(r"[$£€₦]?\d[\d,.]*\s*(?:%|x|k|m|b|billion|million|thousand|hours?|days?|months?|years?|minutes?)?",
                    re.I)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    sc = parse_script(d / "script.md")
    facts = fact_rows(d / "facts.md")
    errs, warns = [], []

    secs = sc["sections"]
    chapters = [s for s in secs if s["chapter"]]
    all_sents = [x for s in secs for x in s["sentences"]]
    words = sum(len(x.split()) for x in all_sents)
    runtime = words / WPM
    print(f"  {sc['title'] or '(no title)'}\n  {len(secs)} sections · {len(chapters)} chapters · {words} words · "
          f"~{runtime:.1f} min at {WPM} wpm")

    if not chapters:
        errs.append("no chapters — use '## 01 · title' headings so each part gets a chapter card")
    elif len(chapters) < 2:
        warns.append("only 1 chapter — a longform needs a spine of 3-7 parts")
    if not 8 <= runtime <= 13:
        warns.append(f"runtime ~{runtime:.1f} min — aim for 9-11")
    if secs and not secs[0]["chapter"]:
        cold = sum(len(x.split()) for x in secs[0]["sentences"]) / WPM * 60
        if cold > 22:
            errs.append(f"cold open is ~{cold:.0f}s — the hook must land in ≤ 15-20s")
    for s in secs:
        sw = sum(len(x.split()) for x in s["sentences"])
        if s["chapter"] and sw / WPM > 2.5:
            warns.append(f"chapter {s['chapter']:02d} '{s['title']}' is ~{sw / WPM:.1f} min — one idea per chapter, split it")
        for x in s["sentences"]:
            if "[" in x and "]" in x:
                errs.append(f"placeholder left in [{s['title']}]: {x[:70]}")
            n = len(x.split())
            if n > 28:
                warns.append(f"{n}-word sentence (hard to read to camera): {x[:70]}...")
            for num in NUM_RE.findall(x):
                core = re.sub(r"[^\d.]", "", num).strip(".")
                if not core or not re.search(r"\d", core):
                    continue
                if core in {"1", "2", "3"} and not re.search(r"[$%]", num):
                    continue                                   # "one job", "two things" — counting, not claims
                if not any(core in r.replace(",", "") or num.strip().lower() in r for r in facts):
                    errs.append(f"unproven number '{num.strip()}' — add a facts.md row with a source, or cut: {x[:70]}")
    text = " ".join(all_sents).lower()
    if not re.search(r"discord|community|newsletter|description|subscribe", text):
        warns.append("no call to action — tell viewers where to go next (community, link, subscribe)")
    intro = " ".join(x for s in secs[:2] for x in s["sentences"]).lower()
    if not re.search(r"at the end|along the way|later in|by the end|stick around", intro):
        warns.append("no open loop in the intro ('at the end, I'll show you...') — give them a reason to stay")

    # teleprompter
    out = [f"# {sc['title']}", ""]
    for s in secs:
        out += ["", f"——— {('%02d · ' % s['chapter']) if s['chapter'] else ''}{s['title'].upper()} ———", ""]
        for x in s["sentences"]:
            out += [x, ""]
    (d / "teleprompter.md").write_text("\n".join(out), encoding="utf-8")

    for w in dict.fromkeys(warns):
        print(f"  warn: {w}")
    for e in dict.fromkeys(errs):
        print(f"  ERROR: {e}")
    print(f"  wrote {d / 'teleprompter.md'}")
    if errs:
        sys.exit(1)
    print("  SCRIPT OK — record it (references/recording-guide.md)")


if __name__ == "__main__":
    main()
