# The context window: one-page cheat sheet

*From my "What a context window actually is" short. — Dara*

Why your AI "forgets" the start of a long chat, and what to do about it.

---

## 1. What it is
The **context window** is the AI's **working memory**: everything it can "see" at once.

Three things share it:
- **What you paste in**: your prompt, files, earlier messages
- **What it thinks**: its reasoning, on models that think before answering
- **What it writes back**: the answer itself

If all three don't fit, something gets dropped.

## 2. Tokens, not words
AI doesn't count words. It counts **tokens**: chunks of text.

| Rule of thumb (English) | |
|---|---|
| 1 token | ≈ ¾ of a word (≈ 4 characters) |
| 100 tokens | ≈ 75 words |
| 1,000 tokens | ≈ 750 words, about 1.5 pages |
| 1,000,000 tokens | ≈ 750,000 words: a whole codebase, or several books |

Code, numbers and non-English text usually take **more** tokens per word.

## 3. How big are windows now?
| Model | Window |
|---|---|
| Gemini 4 Argon (Google) | ~1.05M tokens, shared across input, thinking and output |
| DeepSeek V4.1 Flash | 1M tokens |

Window sizes change fast. Check the model's docs for the current number.

## 4. What happens when it fills
The **oldest content falls out first** (or the tool quietly summarises it). That's why the instructions you gave at the start of a long chat stop being followed an hour later.

## 5. Five habits that fix "my AI forgot"
1. **One task, one chat.** Start fresh when you switch topics.
2. **Put the important stuff last.** Restate key rules near the end of a long prompt.
3. **Paste what's needed, not everything.** A relevant excerpt beats a 200-page dump.
4. **Summarise and restart.** Ask for a summary of decisions so far, then paste it into a new chat.
5. **Watch the thinking.** Heavy reasoning uses the same window, so a huge prompt plus deep thinking can crowd out the answer.

---

More free resources and weekly AI breakdowns in the Discord, The AI Operator: https://discord.gg/ybqAFz6ATR
