# Reasoning effort in 60 seconds

*The one-pager from my "GPT-6 setting that moves your bill 100x" short. — Dara*

## The one idea

**Your AI bill = price per token × how many tokens the model uses.**

- The **model** you pick sets the price per token.
- The **reasoning effort** you set decides how many tokens it burns "thinking" before it answers.

Most people only think about the first one. The second one is a dial you control on every single request.

## The price gap

From OpenAI's GPT-6 guide (Oct 2026), per million tokens (input / output):

| Model | Built for | Price |
|---|---|---|
| Astra | the hardest reasoning | $10 / $50 |
| Luna | high-volume everyday tasks | $0.10 / $0.50 |

That's a 100x gap. Thinking tokens are billed as output, so a high-effort answer on an expensive model stacks both multipliers.

## The four levels

| Effort | What happens | Use it for |
|---|---|---|
| **low** | answers almost straight away | rewriting, summarising, formatting, classifying, quick replies |
| **medium** | thinks a bit first | most everyday work: drafts, simple code, research summaries |
| **high** | thinks a lot | tricky bugs, multi-step plans, analysis where being wrong costs you |
| **xhigh** | thinks as long as it needs | hard maths, deep debugging, problems you'd give an expert |

## How to pick (the 3-question test)

1. **Would a smart intern get this right first try?** → low.
2. **Does it need a few steps, but nothing hidden?** → medium.
3. **Would a wrong answer cost me real time or money?** → high. Go to xhigh only if high fails.

## Three habits that save money

- **Start low, step up.** Only raise effort when the answer is actually wrong, not "could be better".
- **Cheap model + higher effort often beats expensive model + low effort** for logic tasks. Test both on 5 real examples.
- **Cache your repeated context.** Cached input tokens cost up to 95% less (same guide). If you resend the same instructions every call, that's free money.

---

Source: [OpenAI — A practical guide to building with GPT-6](https://openai.com/index/practical-guide-building-gpt-6)

**More plain-English AI breakdowns → join The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
