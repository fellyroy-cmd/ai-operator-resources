"""Reads shorts.json (next to this file) and prints it for the "Tomorrow's short" panel.

    python shorts_board.py

shorts.json is a list of shorts:
  {"id": "S012", "title": "My hook", "post_date": "2026-11-03", "stage": "recorded", "pillar": "Tutorial"}
Stages, in order: scripted, recorded, production, review, ready, scheduled, published.
Everything from "recorded" on counts as filmed.
"buffer" = how many days in a row, starting tomorrow, already have a filmed short.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

STAGES = ["scripted", "recorded", "production", "review", "ready", "scheduled", "published"]
BUFFER_MIN = 2          # the panel warns when fewer days than this are filmed ahead


def main() -> None:
    shorts = json.loads((Path(__file__).resolve().parent / "shorts.json").read_text(encoding="utf-8"))
    today = date.today()
    filmed = {s.get("post_date") for s in shorts
              if s.get("stage") in STAGES and STAGES.index(s["stage"]) >= STAGES.index("recorded")}
    buffer, d = 0, today + timedelta(days=1)
    while d.isoformat() in filmed:
        buffer += 1
        d += timedelta(days=1)
    out = {"today": today.isoformat(), "buffer": buffer, "buffer_min": BUFFER_MIN,
           "shorts": [{"id": s.get("id", ""), "title": s.get("title", ""), "stage": s.get("stage", "scripted"),
                       "post_date": s.get("post_date"), "fresh_until": s.get("fresh_until"),
                       "pillar": s.get("pillar"), "lane": None} for s in shorts]}
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
