# 10 · Render

- **One render at a time.** Builders work in parallel; renders queue. Parallel renders max out the machine and kill each
  other's renders (Duncan hit this with 9 at once).
- **The creator reviews full quality, never a half-size draft**.
  `--draft` is for Claude's own checks only (one section, contact sheets). The full render keeps the creator's footage sharp:
  near-lossless section proxy (CRF 8), PNG source frames (`--video-frame-format png`; `auto` = JPEG and softens skin),
  CRF 12 encode. If the creator hands over a pre-cut recording ("use it the way it is"), the cut is a straight copy — no re-encode.
- Unchanged sections are skipped (content hash). Fixing one section re-renders only that section.
- The full render runs overnight because it locks the machine.
- Hyperframes sometimes loses a browser worker, so render.py retries once with 1 worker.
- Section boundaries snap to the 30 fps frame grid; render.py warns if a section's rendered length is off by > 1.5 frames.
- Measured 2026-10-17 (draft, 4 workers): ~2s of render per 1s of video.
