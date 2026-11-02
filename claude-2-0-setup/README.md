# My Claude 2.0 setup for creators (+ the mod I built)

*From my video "Claude 2.0 for Creators: How I Run My Whole Business In It". — Dara*

This is everything from the video, ready to copy: how I set up a team of sessions for every video, the side-chat shortcut, the two doctor commands, the dashboard prompt, the one rule, and the mod I built by describing it.

Everything runs in the **Claude desktop app, in the Code tab**, on the normal Claude Pro plan. You don't need to write code.

---

## 1 · A team for every video (nested sessions)

One main session per video. You talk to it like a manager, and it starts one session per job. Paste this into a **new** session in the Code tab and fill in the brackets:

```
You're the manager for my next video: [topic, in one line]. Audience: [who it's for].

Start 4 sessions, one job each, and run them at the same time:
1. Research: what's new, what competitors posted, every claim with a source I can open.
2. Script: the hook and the full script, in my voice, under [X] minutes.
3. Title + thumbnail: 8 title options and 3 thumbnail ideas, checked against what's winning in this niche.
4. Shorts: 3 short-form cut-downs from the script.

Each session writes only to its own file. When one finishes, check its work, then give me ONE summary:
what's done, what's still running, and anything that changed another session's work.
If I change the angle, you pass the change to every session it affects.
```

The manager's summary is the only thing you need to read. Each session is a full chat: open any of them from the sidebar and talk to it directly.

---

## 2 · Side chats

While Claude is halfway through a long job, open a side chat to ask questions without stopping it:

- **Windows:** `Ctrl` + `;`
- **Or type:** `/btw`

Good questions: *"What have you found so far?"* · *"How long will this take?"* · *"Is this any good?"*

A side chat can read everything the main chat has done, but it only looks. The main job carries on untouched.

---

## 3 · The doctor

Run these in a new session in your project folder:

| Command | What it does |
|---|---|
| `/doctor` | A quick checkup on your setup |
| `/doctor prompt-audit` | Reads all your instruction files and skills (brand voice, formats, do's and don'ts) and flags rules that are out of date or that fight each other |
| `/skill-doctor` | Shows what each skill costs every session, and which ones you never use |

Run the first run as-is. On mine, the doctor found an agent with a typo in its header (it failed every time it was called), 6 skills I hadn't used in 4 months, and a skill that still said to do something I banned weeks ago.

---

## 4 · A live dashboard

```
Build me a dashboard from [the app or file my data lives in, e.g. my Gmail sponsor label].
Show: [3 things, e.g. new sponsor emails, deals in progress, what's waiting on me].
Keep it current, and tell me honestly whether it's live or a snapshot.
```

**The honest part:** a dashboard only stays live when the data comes from a **connected app** (a connector, like Gmail). If your data lives in a file on your computer, it's a snapshot. Ask Claude to refresh it.

---

## 5 · The mod: "Tomorrow's short"

A mod changes the Claude app itself. You build one by describing it. Here's the one sentence I gave Claude:

```
Build me a mod: a side panel that shows tomorrow's short and whether it's recorded yet.
```

**Easiest way to get your own:** paste that sentence (with your own details) into a new session in the Code tab. Claude builds the mod for your setup and asks you to switch mods on before it runs.

**Want mine as a starting point?** The folder [`tomorrows-short/`](tomorrows-short/) is the mod from the video, changed so it reads a simple schedule file instead of my private board:

- `shorts.json` is your schedule (one line per short, with its post date and stage). Edit it by hand, or ask Claude to keep it updated.
- `shorts_board.py` reads that file and hands it to the panel.
- In `hooks/register.tsx`, set `BOARD_DIR` to the folder where `shorts.json` lives.

Then, in a Code tab session: *"Install the mod in this tomorrows-short folder and adapt it to my setup."*

The panel shows tomorrow's short, a big green **✓ Recorded** or a pink **● Not recorded yet**, its progress through the stages, and a warning when you're running out of filmed shorts. It refreshes every 5 minutes, or on demand with `/tomorrow`.

> **One catch:** mods run with your permissions. Only install mods you trust, and read what one does before you switch it on. This one only runs `python shorts_board.py` in the folder you choose.

---

## The one rule

**One chat, one job.** Every time you need something unrelated, start a new session instead of piling it into the chat you're in. A chat juggling five jobs starts mixing them up. A session with one job stays sharp. And you don't do it by hand: just tell Claude *"start a new session for this"*.

---

Questions, or want to show me your setup? Come hang out in **The AI Operator**, my free Discord: https://discord.gg/ybqAFz6ATR
