# claude-mem: make Claude Code remember your project

*The setup note from my "Stop losing all your context" short. — Dara*

**What it is:** [claude-mem](https://github.com/thedotmack/claude-mem) is a free plugin (100k+ GitHub stars) that saves what happened in your Claude Code sessions and feeds the useful bits back in next time. Close the tab, come back tomorrow, and it still knows your project.

## You need

- Node.js 20 or newer (`node -v` to check)
- The latest Claude Code (with plugin support)

## Install (2 commands inside Claude Code)

```
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```

Then **restart Claude Code.** That's it.

Prefer the terminal? `npx claude-mem install` does the same and walks you through setup.

> Heads up: `npm install -g claude-mem` only installs the library, not the plugin. Use the commands above.

## The one setting that matters: the provider

claude-mem uses an AI model in the background to summarise your sessions. During setup you choose **who runs that model**:

- **your Anthropic / Claude plan**
- **your own OpenRouter or Gemini key**
- **claude-mem's own hosted observer** (this is the one that asks you to sign in)

Pick on purpose. It decides **where your session notes are processed and who pays for it.** If you want to skip the sign-in, set `CLAUDE_MEM_ONLINE_OPTIN` to `false`, or pass `--provider` with your choice when you install.

Settings live in `~/.claude-mem/settings.json`. Restart Claude Code after you change anything.

## Check it works

1. Start a session, do some real work, close it.
2. Open a new session and ask: *"What did we work on last time?"*
3. If it answers with specifics, you're done.

---

Source: [github.com/thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) (as of Oct 2026)

**More Claude Code setups for non-coders → The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
