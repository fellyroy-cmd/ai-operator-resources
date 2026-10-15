# Run AI on a $150 board: 3 Liquid AI d1 demos to clone first

*From my "You don't need a GPU server to run AI anymore" short. — Dara*

In Oct 2026 Liquid AI released two free, open-weight models that run fully on-device, with no cloud and no API bill. On an Nvidia Jetson board, d1-3B answers a question in **16–50 ms**.

## The models (free on Hugging Face)

| Model | Inputs | Link |
|---|---|---|
| **d1-3B** | text + images | [huggingface.co/LiquidAI/d1-3b](https://huggingface.co/LiquidAI/d1-3b) |
| **d1-omni-600M** (experimental, smaller) | text + image, or text + audio | [huggingface.co/LiquidAI/d1-omni-600M](https://huggingface.co/LiquidAI/d1-omni-600M) |

Speed for one question on d1-3B: **16 ms** on a Jetson AGX Thor, **50 ms** on a Jetson Orin Nano, **30 ms** on an Apple M5 Pro, **8 ms** on an RTX 4090.

## The 3 easiest to start with

### 1. Play with the System One Arcade (zero setup)
Liquid's own Space has eleven camera, drawing and text demos of d1-3B.
→ [huggingface.co/spaces/LiquidAI/system-one-arcade](https://huggingface.co/spaces/LiquidAI/system-one-arcade)
**Clone it:** hit **⋯ → Duplicate this Space** to get your own copy, and the source code, to edit.

### 2. Support-ticket router (text only, runs on a laptop)
Feed it one customer message and ask several questions at once. Is this a refund? Which team should handle it? How urgent is it, from 1 to 5? This is the worked example in Liquid's launch post, and it's the easiest real business use.
→ Code: the `transformers` example in the [launch post](https://huggingface.co/blog/LiquidAI/open-d1)

### 3. Ask questions about a photo (image + text)
Give it a picture and a multiple-choice question ("how many cats are in this image?"). Swap in your own: "is the shelf empty?" or "is anyone in frame?". Instant cheap computer vision.
→ Same launch post, image example

## Where to run it

- **No hardware?** Start with demo 1 in the browser, then run demos 2–3 on any recent laptop.
- **Want it always-on?** A Jetson Orin Nano-class board (~$149–199) runs d1-3B at 50 ms per question.

---

Sources: [Hugging Face — Liquid AI d1 launch post](https://huggingface.co/blog/LiquidAI/open-d1) · [Liquid AI blog](https://www.liquid.ai/blog/d1-open)

**Show off what you build in The AI Operator, my free Discord: https://discord.gg/ybqAFz6ATR**
