# Longform Starter — edit YouTube videos with Claude Code

Free from **The AI Operator** (Discord). This is the starter version of the system that edits my long-form videos
without me touching a timeline.

You record. Claude does the rest, one job at a time: cuts your best takes, plans every shot, builds the motion graphics,
renders, checks its own work, and turns your notes into rules so it gets better every video.

## What you need
- **Claude Code** (any paid Claude plan works; I'm on the $20/month plan)
- **Python 3.10+**, **ffmpeg 7+**, **Node.js** (free)
- A 16:9 recording of you reading your script

## Install (5 minutes)
1. Unzip this folder into your project at `.claude/skills/longform-starter/`
2. Install the Python bits: `python -m pip install numpy pillow faster-whisper`
3. Run the setup check: `python .claude/skills/longform-starter/scripts/setup.py`
4. Open Claude Code in your project and say: **"start a new longform video about <your topic>"**

## How a video goes
1. Claude helps you write the script (proven hook, every fact sourced) and gives you a teleprompter file.
2. You record. Mess up a line? Pause, then say the whole line again. Drop the file in the video's `raw/` folder.
3. Say **"I recorded it"**. Claude cuts it and writes a beat map. You approve the plan.
4. Claude builds and renders a half-size draft, checks it at 10 frames a second, and only then shows you.
5. You give notes with timestamps in `notes.md`. Claude fixes the video and rewrites its own rules.
6. Final render overnight.

## What's in the starter
- The full six-job pipeline and all 12 rulebooks
- The dark "editorial" look: bold headlines with one serif-italic accent word, a circle speaker bubble, a split panel,
  gradient chapter cards with a progress tracker, word-by-word captions on talking-head shots
- 15 graphic types: chapter cards, headlines, chips, "in this video" list, tracker, cards, stats, checklists, steps,
  before/after, browser screenshots, quotes, code, name labels, call-to-action

Change the colours in one place: the top of `assets/editorial.css`.

## Fonts & licences
Inter, Instrument Serif and JetBrains Mono are under the SIL Open Font License (see `assets/fonts/OFL.txt`).
GSAP is downloaded by `setup.py` from its CDN. Hyperframes is HeyGen's free open-source renderer, run through npx.

Questions, results, bugs: post them in The AI Operator. Show me what you make.
