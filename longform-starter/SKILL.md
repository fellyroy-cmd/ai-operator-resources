---
name: longform-starter
description: YouTube long-form editing with Claude Code, one job at a time — script → cut (last clean take of every line, dead air out) → beat map (every sentence → what's on screen, approved first) → build (Hyperframes, dark editorial look: bold headlines with one serif-italic accent word, circle speaker bubble, gradient chapter cards with a progress tracker) → render (one section at a time, half-size drafts) → check (10 frames a second, six common mistakes) → notes become rules. TRIGGER on "longform", "edit my YouTube video", "I recorded the video", "new longform video about…", "beat map". From The AI Operator (free starter).
---

# Longform Starter

Don't ask AI for a finished video in one go. Give it **one job at a time**, each with its own rulebook and its own check,
and turn every note you give into a rule so the next video needs fewer notes.

Every video lives in `videos/YYYY-MM-DD-slug/` in your project. Scripts are in this skill's `scripts/` folder; run them from
there with the video folder as the argument: `python <script>.py <video_dir>`. First time: `python setup.py`.

| Job | Run | Rulebook | Who says go |
|---|---|---|---|
| 1 · Script | `new_video.py "topic"` → write script.md + facts.md → `script_lint.py` | 01, 02, 03 | you approve the script |
| — · Record | read `teleprompter.md`; mess up = pause + restart the whole line | — | file in `raw/` |
| 2 · Cut | `cut.py` → check `cut/takes.md` | 04 | flags look fine |
| 3 · Plan | `beatmap.py` → Claude fills shots, headlines, graphics, reasons → `build.py --lint` → `beatmap.py --table` | 05, 06 | **you approve beatmap.md** |
| 4 · Build | `build.py --draft` → `render.py --draft` (final: no `--draft`, run overnight) | 06–10 | — |
| 5 · Check | `qa.py` → read every `qa/sheet_*.jpg`; `snap.py` for stills | 11 | 0 FAIL before you watch |
| 6 · Learn | write timestamped notes in `notes.md` → `notes.py` → fix + rewrite the rule | 12 | every note closed |

**Read the job's rulebook in `rules/` before each job.** Graphic types and the plan format: `references/graphic-kinds.md`.

## Job 1 — script
Hook first (`rules/02-hooks.md`, `references/hook-library.md`): copy a proven opening shape, fill in your subject.
Write `script.md` (`## 01 · lowercase title` = a chapter card; `>` lines = notes, never spoken). Every number gets a source
in `facts.md` or the line gets cut. `script_lint.py` enforces it and writes `teleprompter.md`.

## Job 2 — the cut
`cut.py` transcribes the raw take, matches every script line, keeps the **last clean take**, merges lines said in one
breath, and cuts at the real speech edges from the waveform. Flags in `cut/takes.md`: ROUGH (listen), MISSING, GAP-FILL
(whisper misheard; the speech was kept), REPEAT (two takes overlap — fix `cut/keepers.json`, then `cut.py --render`).

## Job 3 — the plan
Read `cut/frame_grid.jpg`, set `speaker.face` in plan.json. Split sentences where the idea changes. Every beat: `shot`,
`graphic`, `reason`; graphic scenes get a `headline` (the words being said, one `*accent*`). Aim for a visual change every
~2.5 s and never more than ~5 s of plain talking head. Approve the beat map before building — changing a plan is free.

## Job 4 — build + render
`build.py --draft` writes one Hyperframes project per section; `render.py --draft` renders them one at a time (parallel
renders crash machines), skips unchanged sections and masters the audio (-14 LUFS). Optional: drop your own sound effects
into `assets/sfx/` (names in `assets/sfx/README.md`) and a music bed at `assets/music/bed.mp3`.

## Job 5 — check
`qa.py` checks the six mistakes (re-animation, flashes, late text, graphics on the face, repeated words, sync) plus loudness
and dead air, and writes 10-frames-per-second strips of the first second after every cut. Look at every sheet.

## Job 6 — learn
For each note: fix the video, then find the rule that would have prevented it and **rewrite it in place** (don't stack a
new rule on top), and log it in `rules/CHANGELOG.md`.
