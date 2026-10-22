"""Line the plan's words up with the transcript: script = spelling, whisper = timing."""
from __future__ import annotations

import difflib
import re


def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'").replace("'", ""))


def correct_words(moments: list[dict], words: list[dict]) -> list[dict]:
    """The plan's `say` text is the source of truth for SPELLING; whisper is the source of truth for TIMING.
    Rewrite the transcript's words from the plan ("Shagipity" -> "ChatGPT", "Cloud code" -> "Claude Code",
    "90 %" -> "90%") while keeping whisper's timestamps. Whisper-only words (fillers) are dropped."""
    def norm(s: str) -> str:
        return "".join(toks(s))
    pw = [w for m in moments for w in m["say"].split()]
    a, b = [norm(x) for x in pw], [norm(w["text"]) for w in words]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    if sm.ratio() < 0.6:
        print(f"  !! script only matches the audio {sm.ratio():.0%} — captions left as transcribed")
        return words
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += [{**words[j1 + k], "text": pw[i1 + k]} for k in range(i2 - i1)]
        elif tag == "replace":                      # respell, spreading the span's time by word length
            t0, t1 = words[j1]["start"], words[j2 - 1]["end"]
            chunk = pw[i1:i2]
            weights = [max(1, len(x)) for x in chunk]
            cur = t0
            for x, wt in zip(chunk, weights):
                d = (t1 - t0) * wt / sum(weights)
                out.append({"text": x, "start": round(cur, 3), "end": round(cur + d, 3)})
                cur += d
        elif tag == "delete":                       # in the script but not heard — keep it, zero-length
            t = out[-1]["end"] if out else 0.0
            out += [{"text": x, "start": t, "end": t + 0.05} for x in pw[i1:i2]]
    return out


def align(moments: list[dict], words: list[dict], total: float) -> None:
    """Give each moment start/end on the audio timeline by matching its `say` text to the transcript."""
    wtok, widx = [], []
    for i, w in enumerate(words):
        for t in toks(w["text"]):
            wtok.append(t)
            widx.append(i)
    ptok, powner = [], []
    for mi, m in enumerate(moments):
        for t in toks(m["say"]):
            ptok.append(t)
            powner.append(mi)
    sm = difflib.SequenceMatcher(a=ptok, b=wtok, autojunk=False)
    p2w = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            p2w[a + k] = widx[b + k]
    ratio = sm.ratio()
    if ratio < 0.75:
        print(f"  !! plan text only matches the transcript {ratio:.0%} — did the script change after the avatar render?")

    firsts, lasts = {}, {}
    for pi, mi in enumerate(powner):
        if pi in p2w:
            firsts.setdefault(mi, p2w[pi])
            lasts[mi] = p2w[pi]
    for mi, m in enumerate(moments):
        m["_w0"], m["_w1"] = firsts.get(mi), lasts.get(mi)
    # interpolate moments with no matched words
    starts = []
    for mi, m in enumerate(moments):
        if mi == 0:
            starts.append(0.0)
        elif m["_w0"] is not None:
            # cut a hair before the first word so the new picture lands with the word
            starts.append(max(0.0, words[m["_w0"]]["start"] - 0.06))
        else:
            starts.append(None)
    for mi in range(len(starts)):
        if starts[mi] is None:
            prev = starts[mi - 1]
            nxt = next((s for s in starts[mi + 1:] if s is not None), total)
            starts[mi] = prev + (nxt - prev) / 2
    for mi, m in enumerate(moments):
        m["start"] = round(starts[mi], 3)
        m["end"] = round(starts[mi + 1] if mi + 1 < len(moments) else total, 3)
        m["dur"] = round(m["end"] - m["start"], 3)


def phrase_time(phrase: str, m: dict, words: list[dict]) -> float | None:
    """Absolute time a phrase is spoken inside moment m (for list items / path steps landing on the word)."""
    if m.get("_w0") is None:
        return None
    target = toks(phrase)
    if not target:
        return None
    lo, hi = m["_w0"], (m["_w1"] if m["_w1"] is not None else len(words) - 1)
    seq = [(i, t) for i in range(lo, hi + 1) for t in toks(words[i]["text"])]
    for k in range(len(seq)):
        if [t for _, t in seq[k:k + len(target)]] == target:
            return max(m["start"], words[seq[k][0]]["start"] - 0.05)
    for k, (i, t) in enumerate(seq):                       # fall back to the first word
        if t == target[0]:
            return max(m["start"], words[i]["start"] - 0.05)
    return None
