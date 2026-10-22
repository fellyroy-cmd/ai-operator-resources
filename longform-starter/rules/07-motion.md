# 07 · Motion

- House ease: `expo.out` for entrances (fast start, long glide); `expo.inOut` for the speaker moving between shots;
  `expo.in` / `power2.in` for exits. Small `back.out` overshoot only for pops (chips, buttons, pills).
- **Text blurs in** (blur 12px → 0, rise 14px, ~0.38s), word by word, on the word it's said. Headlines may type instead
  (`headline_style: "type"`).
- **Scenes leave with a short blur-fade** (0.24s). Blur is allowed only on short text/element entrances and exits,
  never as motion blur on moving layers: that makes every frame render several times. Renders ran ~3x faster without it.
- The speaker **iris-shrinks into the bubble** and slides into the split panel (0.6s expo.inOut); the ring spins slowly.
- Cards on talking-head shots fly out from the creator's head; in graphic scenes they rise in.
- Diagrams build step by step on their words: bars grow, count-ups count, tags pop on a waveform, checks tick, lines draw.
- Nothing holds still: a slow push on full shots, gentle float on chips, the grid drifts.
- Chapter wipe starts 45% across (no black frames at the section seam); number rises, title blurs in, tracker pills
  stagger up, the lit pill pops, the dot walks the dotted path to it.
- **Only transforms, opacity, clip-path and short filters animate.** `left/top/width/letter-spacing` tweens stutter
  under frame-by-frame capture.
