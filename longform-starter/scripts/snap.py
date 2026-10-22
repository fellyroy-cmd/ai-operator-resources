"""Stills from one section's composition, no video render (for section builders checking their own work).

    python snap.py <video_dir> s02 b012 b014        # 4 stills per beat: start, 1/3, 2/3, near the end
    python snap.py <video_dir> s02 --at 11.8,15.0   # exact SECTION-relative seconds

Writes <video_dir>/qa/snap/<section>/at-<t>s.png and prints the paths. Then Read them.
Wraps `hyperframes snapshot` with ffmpeg on PATH (the system PATH points at a stale ffmpeg folder).
"""
from __future__ import annotations

import argparse
import sys

from lf_common import read_json, run, video_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("section")
    ap.add_argument("beats", nargs="*")
    ap.add_argument("--at")
    a = ap.parse_args()
    d = video_dir(a.video_dir)
    tl = read_json(d / "timeline.json")
    sec = next((s for s in tl["sections"] if s["id"] == a.section), None)
    if not sec:
        sys.exit(f"no section {a.section}")
    times = [float(x) for x in a.at.split(",")] if a.at else []
    for bid in a.beats:
        b = next((x for x in tl["beats"] if x["id"] == bid), None)
        if not b:
            sys.exit(f"no beat {bid}")
        t0, t1 = b["start"] - sec["start"], b["end"] - sec["start"]
        times += [t0 + 0.35, t0 + (t1 - t0) / 3, t0 + 2 * (t1 - t0) / 3, t1 - 0.35]
    if not times:
        sys.exit("give beat ids or --at times")
    out = d / "qa" / "snap" / a.section
    out.mkdir(parents=True, exist_ok=True)
    run(["npx", "--yes", "hyperframes", "snapshot", str(d / "sections" / a.section), "--at",
         ",".join(f"{max(0.0, t):.2f}" for t in sorted(times)), "--no-end", "--keep", "--describe", "false", "-o", str(out)])
    for p in sorted(out.glob("*.png")):
        print(f"  {p}")


if __name__ == "__main__":
    main()
