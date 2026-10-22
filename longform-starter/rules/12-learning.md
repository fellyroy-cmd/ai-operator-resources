# 12 · Learning from notes

Every note the creator gives is a note the creator should never have to give again.

1. `python notes.py <dir>` puts each note on its beat and suggests a rulebook.
2. Fix the video (plan.json / custom fragment / keepers.json).
3. **Find the rule that would have prevented it.** If one exists, REWRITE it so it would have caught this case. Don't add
   a second rule on top: stacked rules drift, bloat and contradict each other. If none exists, add it to the rulebook it
   belongs in. If the rule is mechanical, change the code (a constant in build.py / operator.css, or a lint check) so it's
   enforced, not just written down.
4. One line in `rules/CHANGELOG.md`: date · video · note → rule changed.
5. Tick the note: `- [x] 3:12 music too loud → ducking threshold 0.03 (09-audio)`.
6. One-off taste calls ("I don't like this particular card") get fixed without a rule. Only patterns become rules.

Video 1 will take the most notes. Each video after should be faster and cheaper, because the rules carry the notes forward.
