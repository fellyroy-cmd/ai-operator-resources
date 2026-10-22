# 05 · Beat map

A beat map is every sentence the creator says plus what's on screen while the creator says it. Without one, AI edits look like slides.

## Pace
- **A visual change every ~2.5s**: ~20–25 beats per minute; 10 min ≈ 200–240 beats. A punch-in, a new headline word
  group or a diagram step all count as changes.
- **Talking head never runs past ~5s.** Most talking-head stretches are 1–3s between graphic scenes.
- ~65% of the runtime is graphic scenes (bubble / split / graphic), ~25% talking head, ~10% chapter cards and black beats.

- **Split on the clause, first pass**: a sentence over ~4s splits where its setup ends —
  setup on a talking shot (full/punch, alternating), the list/number on the graphic ("so the system splits editing into
  six jobs" → bubble stat 6, "write the script, cut…" → cards). Chapter cards are the exception: never split them —
  the card holds the creator's whole chapter line.
  Below 14 beats/min is too calm; 15–18 is the floor for the creator's videos.

## Every beat
- `shot`, `graphic` (or null), `reason` = one sentence on what the viewer should understand from this picture.
- **Graphic scenes get a `headline`**: the spoken line's 2–4 key words, with ONE `*accent*` word (the word that carries
  the meaning: "every *word*", "a real *source*", "cutting it *out*"). Use the words the creator actually says, so they land as
  the creator says them.
- Split where the **idea** changes, not where the sentence ends. A diagram can build across beats: same headline =
  it holds, and the next beat adds the next step.
- Never under 0.9s for a graphic (it reads as a flash). The same graphic continuing = `"graphic": "hold"`.
- Don't open a scene on a blank canvas: if the main element waits for a word, start the beat on that word, or let the
  headline carry the first second.

## Choosing the picture
1. **Draw the concept as a literal diagram that builds while the creator talks.** A number → `stat`. Before/after → `versus`. A process → `steps`. A list → `checklist` / `cards`.
   Real proof → `browser` screenshot. Code → `code`. Never a bullet slide.
2. **Real beats fake:** if the real thing exists (repo, dashboard, terminal, article), show it with `browser` + a focus punch.
3. **Talking-head beats aren't empty:** add `chips` beside the head as the creator names things,
   a `lower` the first time a tool is named.
4. **Black beats** (`"bg": "black"`) for contrast: the mistake, the "before", the dramatic number. Maybe one in five scenes.
5. **Framed shots** for a setup line ("most people think…") with a caps `label` above.

## Structure
- After the hook, a `list` ("in this video") of the chapters, numbers in chapter colours.
- Every `## NN ·` chapter opens with its `chapter` card (shot `graphic`). Give sections a `short` name for the tracker pills.
- Between chapters, or when the topic jumps back, a `tracker` scene shows where we are.
- **Set up, then pay off:** plant something early (a number, a prop, a question) and complete it later.
  Reuse the same prop every time the same idea comes back.
- The recap reuses the chapter cards (`cards` with `fill: true`, one colour per chapter).
- End each chapter on the creator's face, not a graphic.

**The creator approves beatmap.md before job 4.** Change the plan, not the pixels.
