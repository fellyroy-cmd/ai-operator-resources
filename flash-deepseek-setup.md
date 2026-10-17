# DeepSeek V4.1 Flash: setup guide + price cheat sheet

*From my "A free model now beats Opus 5 at real-world coding" short. — Dara*

DeepSeek-V4.1-Flash-1017 came out on Oct 17, 2026. On DeepSWE, a real-world coding benchmark, it scores **77.0**, ahead of Claude Opus 5 (**74.0**) and GPT-5.6 Sol (**73.0**). The weights are open under an MIT license, it has a 1M-token context window, and the API costs cents. Here's how to try it in 10 minutes, plus what it really costs.

**Honest bit first:** it doesn't win everything. Opus 5 still leads most of the other benchmarks on the model card (HLE, Terminal-Bench 4.0, ProgramBench, NL2Repo). Treat Flash as the cheap, fast default for coding-agent work, and test it on *your* tasks before you switch anything important.

---

## Step 1: Get an API key (2 min)

1. Sign up at **https://platform.deepseek.com**
2. Top up a small balance. $2–5 is plenty to test with.
3. Create a key at **https://platform.deepseek.com/api_keys** and copy it somewhere safe. You only see it once.

The model name everywhere is **`deepseek-flash`**. The old names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` still work, and they now run V4.1-Flash-1017 too.

## Step 2, option A: Run Claude Code on DeepSeek (best for coding agents)

Claude Code can talk to DeepSeek through DeepSeek's Anthropic-compatible endpoint. These variables only apply to the terminal you set them in, so your normal Claude Code setup stays untouched. Close the terminal and you're back to normal.

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
$env:ANTHROPIC_AUTH_TOKEN="<your DeepSeek API key>"
$env:ANTHROPIC_MODEL="deepseek-flash[1m]"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-flash[1m]"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-flash[1m]"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-flash"
$env:CLAUDE_CODE_SUBAGENT_MODEL="deepseek-flash"
$env:CLAUDE_CODE_EFFORT_LEVEL="max"
$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW="786432"
cd C:\path\to\your-project
claude
```

**macOS / Linux:**
```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=<your DeepSeek API key>
export ANTHROPIC_MODEL="deepseek-flash[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-flash[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-flash[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-flash
export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-flash
export CLAUDE_CODE_EFFORT_LEVEL=max
export CLAUDE_CODE_AUTO_COMPACT_WINDOW=786432
cd /path/to/your-project
claude
```

Don't have Claude Code yet? You need Node.js 18+ (and Git for Windows on Windows), then `npm install -g @anthropic-ai/claude-code`.

## Step 2, option B: Call it from your own code (OpenAI-compatible)

```bash
pip install openai
```
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

reply = client.chat.completions.create(
    model="deepseek-flash",
    messages=[{"role": "user", "content": "Write a Python function that removes duplicate emails from a CSV."}],
)
print(reply.choices[0].message.content)
```
Already using the OpenAI SDK somewhere (n8n, Make, a script)? Swap the `base_url` and the key, and set the model to `deepseek-flash`. That's the whole migration.

## Step 3: The 15-minute test before you switch

Run the same 3 real tasks through Flash and through your current model:
1. **A bug you fixed last week.** Give it the broken file and the error message.
2. **A small feature** in a real project, like "add a CSV export button".
3. **A refactor:** "split this 300-line file into modules".

For each one, score whether it worked on the first try (yes/no), how many follow-ups it needed, and what it cost (check the usage page). If Flash gets 2 of 3 right at a fraction of the price, make it your default and keep the expensive model for the hard stuff.

---

## Price cheat sheet (official, per 1M tokens)

| | Off-peak | Peak |
|---|---|---|
| Input, cache hit | $0.003 | $0.006 |
| Input, cache miss | **$0.15** | **$0.30** |
| Output | **$0.60** | **$1.20** |

**Peak hours** are 01:00–04:00 and 06:00–10:00 UTC, Monday to Friday (that's **02:00–05:00 and 07:00–11:00 Lagos time**). Everything else is off-peak and half price, **including all weekend hours**.

**What that looks like:** a heavy coding session that reads 1M tokens and writes 200K costs about **$0.54 at peak and $0.27 off-peak**.

**Cheaper still:** repeated context (the same files and system prompt on every turn) is billed at the cache-hit rate, 50× cheaper. Long agent sessions on one project get cheap fast.

---

## Before you use it for client work

- **The API runs on DeepSeek's servers.** Don't send secrets, client data or `.env` files you wouldn't send to any third-party API.
- **"Free weights" doesn't mean free to run at home.** It's a 763B-parameter model, which needs a serious GPU cluster. For most people, the cheap API is the free part that matters.
- **Benchmarks aren't your work.** That's why Step 3 exists.

---

Sources: [DeepSeek-V4.1-Flash-1017 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) · [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing) · [DeepSeek + Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code) · [DeepSeek API docs](https://api-docs.deepseek.com/)

**Testing it this week and sharing results in The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
