"""Job 1 setup — create a longform video folder.

    python new_video.py "claude edited my video"            # -> content/longform/YYYY-MM-DD-claude-edited-my-video/
    python new_video.py "topic" --date 2026-10-24

Creates: script.md (from the template), facts.md, notes.md, raw/ (drop the camera file here), assets/img/, custom/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil

from lf_common import LF_DIR, VIDEOS_ROOT


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    slug = re.sub(r"[^a-z0-9]+", "-", a.topic.lower()).strip("-")[:60]
    d = VIDEOS_ROOT / f"{a.date}-{slug}"
    if d.exists():
        print(f"exists: {d}")
        return
    for sub in ("raw", "cut", "assets/img", "custom", "renders", "qa"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    tpl = LF_DIR / "templates"
    shutil.copy(tpl / "script.md", d / "script.md")
    shutil.copy(tpl / "facts.md", d / "facts.md")
    (d / "notes.md").write_text(
        "# Notes on the cut\n\n"
        "Write one note per line with the timestamp from the draft you watched, exactly like you'd brief a human editor.\n"
        "`python notes.py <this folder>` maps every note to its beat. Claude fixes the video AND rewrites the rule that\n"
        "would have prevented it (rules/), so the next video doesn't need the same note.\n\n"
        "## draft v1\n- [ ] 0:00 \n", encoding="utf-8")
    print(f"created {d}\n  next: write script.md (hook from references/hook-library.md), fill facts.md, then\n"
          f"  python script_lint.py \"{d}\"")


if __name__ == "__main__":
    main()
