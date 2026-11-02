# Tomorrow's short (a Claude mod)

A side panel in the Claude desktop app that shows tomorrow's short and whether it's recorded yet.

Built by Claude from one sentence ("a side panel that shows tomorrow's short and whether it's recorded yet"). This copy
reads a simple `shorts.json` schedule instead of my private content board.

**What it shows:** tomorrow's short · a big ✓ Recorded or ● Not recorded yet · its progress through the stages ·
a warning when fewer than 2 days are filmed ahead · the next shorts still to record. It re-reads every 5 minutes,
on the Refresh button, and with `/tomorrow`.

## Set it up
1. Put `shorts.json` and `shorts_board.py` in your content folder (or leave them here).
2. In `hooks/register.tsx`, set `BOARD_DIR` to that folder (and `POST_TIME` / `FILM_HINT` if you like).
3. Check it reads: `python shorts_board.py` should print your schedule as one line of JSON.
4. In a Code tab session: *"Install the mod in this tomorrows-short folder and adapt it to my setup."*
   Claude asks you to switch mods on before anything runs.

Keep `shorts.json` up to date by hand, or tell Claude *"when I film a short, set its stage to recorded in shorts.json"*.

**Safety:** mods run with your permissions. This one only runs `python shorts_board.py` in `BOARD_DIR` and reads
`shorts.json`. Read any mod before you switch it on.
