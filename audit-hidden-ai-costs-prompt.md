# The "find the waste" prompt: audit your AI workflow for hidden costs

*The exact prompt from my "I had AI audit my own AI workflow" short. — Dara*

**The story:** StackAI (part of Asana) pointed a coding agent at its own browser agent and asked it to find the waste. The agent was re-sending its **entire history, every page and every screenshot, on every request.** Fixing that one caching problem made it **29x cheaper**. Switching to a better-fit model then made it **76x cheaper and 5x faster** overall, at **$0.47 a run**. It took about a week instead of the 1–2 months they'd estimated.

## How to use it

Open your automation's code or workflow export in a coding agent (Claude Code, Codex, Cursor), then paste:

```
Audit this AI workflow for hidden costs. Don't change anything yet.

1. Map every call to an AI model: where it happens, which model,
   and roughly how many input and output tokens each call sends.
2. Find waste, in this order:
   - Context re-sent on every call (full history, documents,
     screenshots, long system prompts) that could be cached,
     trimmed, or summarised
   - Calls using a bigger model or higher reasoning effort than
     the task needs
   - Calls that could be batched, skipped, or replaced with
     plain code (regex, if/else, a lookup)
   - Retries or loops that can run away
3. For each problem give: where it is (file + line), estimated
   cost per run now, estimated cost after the fix, and the fix
   in one sentence.
4. Rank the fixes by savings divided by effort. Biggest easy win first.
5. Then wait. I'll tell you which fixes to apply.
```

## Then

- Apply **one fix at a time** and re-run on the same 5 real inputs. Check that the output didn't get worse.
- Check your provider's usage dashboard before and after, so you see the real numbers, not estimates.
- Run the audit again every time you add a new step to the workflow.

---

Sources: [OpenAI — Asana's browser agent](https://openai.com/index/asana-browser-agent/) · [StackAI — how they cut browser-agent costs](https://www.stackai.com/blog/how-stackai-by-asana-used-astra-codex-and-command-to-reduce-browser-agent-costs)

**Post your before/after numbers in The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
