# Shots, headlines, graphic kinds + plan.json schema

```jsonc
{
  "title": "...", "style": "editorial", "theme": "dark",       // theme: dark | light
  "speaker": {"face": {"x": 0.42, "y": 0.18, "w": 0.16, "h": 0.30}},   // fractions of the frame, from cut/frame_grid.jpg
  "music": {"file": "", "volume": 0.07},
  "captions": true,
  "sections": [
    {"id": "s02", "title": "the cut", "short": "Cut", "chapter": 2, "beats": [   // "short" = the tracker pill label
      {"id": "b031", "say": "exact words from the script", "shot": "bubble",
       "headline": "every *word*",                    // the spoken line's key words; *star* = serif-italic accent
       "headline_style": "type",                      // optional: typewriter with cursor instead of blur-in
       "bg": "base",                                  // base = theme canvas (default) | white / black / mist = contrast beat
       "graphic": {"kind": "stat", "value": 231}, "reason": "what the viewer should understand",
       "label": "MOST PEOPLE THINK...",               // framed shots only: the caps header above the frame
       "emphasis": ["word"], "sfx": [{"name": "pop", "at": 0.4}]}
    ]}
  ]
}
```
`say` texts must concatenate to the script. `graphic` = object | `null` | `"hold"` (keep the previous graphic, no
re-animation). Identical consecutive `headline`s also hold automatically. Accent markup `*word*` works in every text field.

## Shots
| shot | speaker | text | use for |
|---|---|---|---|
| `full` | full frame, slow push | captions | talking, story; add `chips`/`lower`/`cards` beside the head |
| `punch` | 1.24x on the face, hard cut | captions | the twist, the punchline |
| `overlay` | full frame | captions | graphics in the free space beside/above the face (auto) |
| `framed` | ~80% in a rounded frame on black | `label` + captions | a "most people think…" setup, a story beat |
| `bubble` | circle bottom-right, accent ring | headline | **the default for graphic scenes** |
| `split` | rounded panel left | headline (right) | a stat, a screenshot, a card next to the creator's face |
| `graphic` | hidden, voice continues | headline or the kind's own text | chapter cards, big diagrams, statements |
The speaker glides between full/overlay/bubble/split/framed (an iris into the bubble). Bubble ↔ split/framed is a hard cut.

## Kinds
| kind | fields | when |
|---|---|---|
| `chapter` | `n`, `title`, `layout` (left/center/right, auto-rotates) | first beat of every `## NN ·` chapter, shot `graphic` |
| `headline` (`title`) | `text`, `sub`, `size` | a whole-scene statement ("everything I learn, I *build*") |
| `chips` | `items`, `at` | white pills popping beside the head as things are named (talking-head shots) |
| `list` | `items`, `kicker` ("in this video") | the roadmap; numbers in each chapter's colour |
| `tracker` | `n` | where we are: the job pills on white, current one lit |
| `cards` | `items: [{title, sub, src}]`, `fill` (colour each card), `numbered`, `cols`, `at` | named things; `fill: true` = the recap |
| `stat` | `value`, `from`, `prefix`, `suffix`, `decimals`, `label`, `at` | one hero number (counts up; suffix in serif accent) |
| `checklist` | `items` (≤ 7), `at` | mistakes, requirements, ticked in the chapter colour |
| `steps` | `items`, `at` | a sequence / pipeline |
| `versus` | `left: {label, text}`, `right: {label, text}`, `right_at`, `strike` | belief vs reality |
| `browser` | `src`, `url`, `scroll`, `focus: {x,y,w,h}`, `punch_at` | real sites, repos, dashboards |
| `quote` | `text`, `by` | a comment, a tweet |
| `code` | `title`, `lines`, `at` | terminal output, config |
| `lower` | `name`, `sub` | name a tool/person the first time |
| `cta` | `text`, `pill`, `pill_at` | the community offer ("free in the *Discord*") |

`at` = phrases (one per item) that trigger each item when the creator says it. **Don't put the first element of a scene on a
late word**: build.py warns when a graphic scene would sit blank for more than 0.6s.
