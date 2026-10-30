# 06 · Visuals ("editorial" look, dark theme)

Reference: `references/style-reference.md` (measured from the full reference video). Tokens: `assets/editorial.css`.

- **The creator's call: dark mode + the creator's hot pink.** `"theme": "dark"` (default): the reference's layout grammar on
  the creator's palette: obsidian #0B0B0B canvas with a faint pink glow and grid, bone #F5F5F5 type, #161616 surfaces with
  hairline borders. `"bg": "white"` gives a light contrast beat; `"theme": "light"` gives the reference's white look.
- **Accent = the creator's hot pink** (#FF1564, `--grad`) for the accent words and chapter cards;
  **hot pink #FF1564** (`--accent`) for solid accents (ring, strikes, toggles, buttons, totals). No orange tones
  anywhere.
- **Type:** Inter 800–900 for headlines and numbers (tight tracking, lowercase-leaning) · Instrument Serif italic for the
  ONE accent word per headline and for chapter titles · JetBrains Mono, uppercase and letter-spaced, for small labels
  ("IN THIS VIDEO", "PART 02 OF 06", axis labels).
- **Chapter colours:** blue #4C6FFF · hot pink #FF1564 · purple #8B6CFF · cyan #22C7E0 · green #2BC48A · gold #F2B93B (cold open = hot pink),
  one per chapter in order (`--chap`), bright enough for obsidian. They appear only inside their own chapter, plus the
  tracker and the recap.
- Physical props stay physical on dark: the receipt is white paper, chips on the talking head are bone pills.
- **Speaker:** the creator's real room, no background removal. The bubble (circle, ring),
  split panel (rounded, shadow) and framed shot (on black) give depth. Graphics never cover the face: the overlay zone
  is computed from the face box, and QA fails any overlap over 8%.
- **Surfaces:** white cards with 18px radius and a soft shadow; pills for chips. Coloured fills only for the recap cards.
- **Chapter cards** are the one loud moment per part: the hot pink, halftone dots, giant cream numeral, serif title,
  the job tracker. The layout rotates (left / centre / right) so they never feel templated.
- **Scale:** headline 92–110px, takeover statements 110–190px, numbers up to 300px, body text never under 34px at 1080p.
- One focal point per frame. ≤ 7 list items, ≤ 6 cards.
- Never: gradients on type, emoji, stock "AI brain" imagery, two accent words in one headline, black shadows as the only
  edge on dark (use the light hairline: the bubble/panel shadow switches automatically).
