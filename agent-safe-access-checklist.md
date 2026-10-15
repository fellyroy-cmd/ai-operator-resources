# The safe-access checklist for AI agents

*From my "Apple just locked AI agents out of your Mac files" short. — Dara*

On Oct 2, 2026 Apple tightened macOS Full Disk Access specifically because AI agents could quietly read your mail, messages and browsing history. The lesson: **more access makes an agent more useful AND more dangerous.** Run this before you give any agent access to anything.

## Before you install

- [ ] **Do I know who made it?** Real company or a repo with a track record (stars, recent commits, issues being answered).
- [ ] **Can I say in one sentence what it needs access to, and why?** If not, don't install it yet.
- [ ] **Is there a sandbox or "ask before acting" mode?** Turn it on first.

## When it asks for permission

- [ ] **Give it a folder, not your whole drive.** Make a dedicated `agent-workspace` folder and point it there.
- [ ] **Never grant Full Disk Access** just to make a warning go away.
- [ ] **Read-only first.** Let it read before you let it write, delete, send or buy.
- [ ] **No passwords, banking, or the main email inbox** unless that IS the job, and then use a separate account.
- [ ] **Use scoped API keys** with a spending limit, never your main account key.

## While it's running

- [ ] **Watch the first 3 runs.** Read what it actually did, not just what it reported.
- [ ] **Keep "send", "delete", "pay" and "post" behind a confirm step.**
- [ ] **Check the logs** — does it touch files you never mentioned?

## Every month

- [ ] **Audit permissions.** macOS: System Settings → Privacy & Security → Full Disk Access / Files and Folders. Remove anything you don't use.
- [ ] **Rotate keys** for agents you've stopped using.
- [ ] **Uninstall** agents you haven't opened in 30 days.

**Rule of thumb:** give an agent the access you'd give a new freelancer on day one, not the keys to the house.

---

Source: [The Verge — Apple limits Mac disk access for AI agents](https://www.theverge.com/tech/1004295/apple-limit-mac-disk-access-ai-agents)

**Talk agents with other builders in The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
