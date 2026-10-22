# 04 · The cut

- Keep the **last clean take** of every script line (≥ 85% word match). Lines the creator said in one breath stay one window,
  because fewer cuts flow better.
- Cut points come from the **waveform**, not whisper (the cutter: inward onset scan, 14 ms micro-fades, hard video cuts).
- `ROUGH` is usually whisper mishearing a clean take, not a bad take. Listen before swapping.
- `GAP-FILL` = a line whisper couldn't match, but the speech between its neighbours was kept. Listen once.
- `REPEAT` (2+ words twice) is a splice bug: two windows share source audio. Fix keepers.json; never ship it.
- **In-take restarts are the #1 real-world repeat.** The creator often restarts a line mid-breath with no pause ("the cards,
  the cards", "April 2027 and, April 2027 and", three tries at "so if you use Claude"). They sit INSIDE one keeper window,
  and whisper small.en often drops the repeated words from the raw transcript, so the picker can't see them. Every
  REPEAT the cut transcript finds must be fixed: map its cut time back to the source (align cut words.json ↔ raw
  words.json), zoom-transcribe those seconds with `medium.en`, read the loudness map for the breath between attempts,
  then split the window there. If whisper's word start is late, retime that word in `cut/words.json` so the onset
  scan starts in the breath.
  One word twice ("and and") is a stutter or mishearing, so listen.
- The cut is re-encoded at a constant 30 fps so sections split on exact frames later.
