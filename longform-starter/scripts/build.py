"""Job 4 — build the graphics. plan.json -> one Hyperframes project per section (16:9).

    python build.py <video_dir>                 # full-res compositions (1920x1080)
    python build.py <video_dir> --draft         # half-size (960x540) for fast review renders
    python build.py <video_dir> --section s03   # rebuild one section (a section builder's loop)
    python build.py <video_dir> --lint          # plan checks only

Reads:  plan.json, words.json, cut/cut.mp4 (+ cut/cut16k.wav for waveforms), assets/img/*, custom/<beat>.html
Writes: sections/<sid>/{index.html, assets/...}, timeline.json (every beat/event/sfx/rect for render + QA)

Look (default "editorial", references/style-reference.md — rebuilt 2026-10-17 from a full frame-by-frame watch):
white canvas + black contrast beats; the spoken line becomes the HEADLINE on graphic scenes (heavy black grotesk, one
serif-italic accent word, words blur in as they're said); captions only on talking-head shots; the creator shrinks into a
CIRCLE bubble (iris glide, spinning accent ring) or a rounded split panel or a framed shot on black; flat hot-pink
chapter cards with halftone texture, a job tracker and a travelling dot; one colour per chapter; every idea drawn as
a diagram that builds word by word. 
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from lf_common import (FPS, H, LF_ASSETS, SHORTIFY_ASSETS, W, ffmpeg, fmt_t, probe_duration, read_json, snap, toks,
                       video_dir, write_json)
from align import align, correct_words, phrase_time
BUBBLE = (1690, 880, 150)                   # cx, cy, r of the corner bubble
SPLIT = (68, 165, 750, 750)                 # x, y, w, h of the split panel (speaker left)
SPLIT_K = 1.12                              # zoom inside the split panel
FRAMED = (192, 140, 0.8)                    # x, y, scale of the framed shot (on black, label above)
PUNCH = 1.24
HEAD_POS = {"graphic": (150, 78), "bubble": (150, 78), "split": (880, 150)}
STAGE = {
    "graphic": (150, 110, 1620, 860), "graphic_h": (150, 240, 1620, 720),
    "bubble": (150, 110, 1440, 640), "bubble_h": (150, 230, 1620, 500),
    "split": (880, 170, 960, 760), "split_h": (880, 300, 960, 640),
}
SHOTS = {"full", "punch", "overlay", "framed", "bubble", "split", "graphic"}
TALKING = {"full", "punch", "overlay", "framed"}            # captions live here; graphics scenes get headlines
SHADOW = {"light": "drop-shadow(0 22px 40px rgba(0,0,0,.28))",
          "dark": "drop-shadow(0 0 1.5px rgba(245,245,245,.55)) drop-shadow(0 24px 44px rgba(0,0,0,.65))"}
# one colour per chapter, bright enough for obsidian AND white; no orange (the creator, 2026-10-17)
CHAP_COLORS = ["#4C6FFF", "#FF1564", "#8B6CFF", "#22C7E0", "#2BC48A", "#F2B93B"]
CANVAS = {"dark": "#0B0B0B", "light": "#FFFFFF"}
KINDS = {"chapter", "headline", "title", "chips", "list", "tracker", "cards", "stat", "checklist", "steps", "versus", "browser", "quote", "code", "lower", "cta"}
ON_FACE_OK = {"lower", "chips", "title", "cards"}   # kinds allowed on talking-head shots
SFX_FILE = {"whoosh": "hook-whoosh.wav", "click": "click.wav", "shutter": "shutter.wav", "digital": "digital.wav",
            "pop": "card-pop.wav", "tick": "caption-tick.wav", "boom": "hook-boom.wav", "rise": "timeline-rise.wav",
            "write": "caption-write.wav", "flare": "flare-hit.mp3"}
SFX_VOL = {"whoosh": 0.3, "click": 0.4, "shutter": 0.38, "digital": 0.24, "pop": 0.38, "tick": 0.28, "boom": 0.3,
           "rise": 0.24, "write": 0.3, "flare": 0.3}
SFX_MASTER = 0.5                            # rules/09-audio.md — tune the whole bed here, not per effect
E = "expo.out"                              # the house ease: fast start, long glide


def esc(s) -> str:
    return html.escape(str(s))


def rich(text: str) -> str:
    """'every *word*' -> escaped HTML with the starred words in the serif-italic accent."""
    out = esc(text)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)


def acc(text: str, accent=None) -> str:
    out = rich(text)
    for a in ([accent] if isinstance(accent, str) else (accent or [])):
        if a and "<em>" not in out:
            out = re.sub(re.escape(esc(a)), lambda m: f"<em>{m.group(0)}</em>", out, count=1)
    return out


def word_tokens(text: str) -> list[tuple[str, bool]]:
    """Split 'every *word*' into [(word, is_accent)]."""
    out = []
    for part in re.split(r"(\*[^*]+\*)", text):
        if not part:
            continue
        is_acc = part.startswith("*") and part.endswith("*")
        for w in part.strip("*").split():
            out.append((w, is_acc))
    return out


# ───────────────────────────── per-beat context ─────────────────────────────

class Ctx:
    """Everything a template needs for one beat. Times are RELATIVE to the section start."""

    def __init__(self, b, sec0, words, stage, sel, face, vd, extra):
        self.b, self.sec0, self.words, self.sel, self.face, self.vd = b, sec0, words, sel, face, vd
        self.t0 = b["start"] - sec0
        self.t1 = b["end"] - sec0
        self.d = b["dur"]
        self.x, self.y, self.w, self.h = stage
        self.js: list[str] = []
        self.sfx: list[tuple[str, float]] = []
        self.text_events: list[dict] = []
        self.extra = extra                      # chapters list, chapter colour, section info

    def at(self, phrase, default=None):
        if phrase:
            t = phrase_time(phrase, self.b, self.words)
            if t is not None:
                return t - self.sec0
        return self.t0 + 0.08 if default is None else default

    def times(self, items, ats=None, key=None):
        """When each item lands: on its own words if spoken, else spread evenly across the beat."""
        n = len(items)
        lo, hi = self.t0 + 0.2, max(self.t0 + 0.4, self.t1 - 0.6)
        step = (hi - lo) / max(1, n)
        out, spoken = [], {}
        for i, it in enumerate(items):
            ph = (ats[i] if ats and i < len(ats) else None) or (it.get(key) if isinstance(it, dict) and key else it)
            t = None
            if isinstance(ph, str):
                t0 = phrase_time(re.sub(r"\*", "", ph), self.b, self.words)
                t = None if t0 is None else t0 - self.sec0
                if t is not None:
                    spoken[i] = t
            out.append(t if t is not None else lo + step * i)
        for i in range(1, n):
            out[i] = max(out[i], out[i - 1] + 0.16)
        if out and out[-1] > hi:
            print(f"  !! {self.b['id']}: items can't follow the words (last one would land after the cut) — spaced evenly")
            out = [lo + step * i for i in range(n)]
            spoken = {}
        for i, t in enumerate(out):
            ev = {"beat": self.b["id"], "item": i, "appear_t": round(t + self.sec0, 3)}
            if i in spoken:
                ev["word_t"] = round(spoken[i] + self.sec0, 3)
            self.text_events.append(ev)
        return out

    def tl(self, s: str):
        self.js.append(s)

    def box(self, inner: str, cls: str = "") -> str:
        return (f'<div class="stage {cls}" style="left:{self.x}px;top:{self.y}px;width:{self.w}px;height:{self.h}px">'
                f'{inner}</div>')

    def rise(self, sel, t, dur=0.6, dy=40, blur=True):
        f = ', filter:"blur(10px)"' if blur else ""
        f2 = ', filter:"blur(0px)"' if blur else ""
        self.tl(f'tl.fromTo("{sel}", {{opacity:0, y:{dy}{f}}}, {{opacity:1, y:0{f2}, duration:{dur}, ease:"{E}"}}, {t:.3f});')


def countup(c, sel, frm, val, dec, t, dur, comma=True):
    c.tl(f'(function(){{ const el=document.querySelector("{sel}"); const o={{v:{frm}}};'
         f' tl.fromTo(o,{{v:{frm}}},{{v:{val}, duration:{dur:.2f}, ease:"power3.out", onUpdate:()=>{{'
         f' el.textContent = o.v.toLocaleString("en-US",{{minimumFractionDigits:{dec},maximumFractionDigits:{dec},'
         f'useGrouping:{str(comma).lower()}}}); }}}}, {t:.3f}); }})();')


# ───────────────────────────── graphic templates ─────────────────────────────
# Each takes (g, c: Ctx) and returns inner HTML; animation -> c.tl(...), sound -> c.sfx. Never tween the .clip itself.

def k_chapter(g, c):
    """Full-bleed accent card: mono 'PART 03 OF 06', giant numeral, serif-italic title, the job tracker with the
    current chapter lit (its colour underneath), a dotted path whose dot walks to the lit pill. Layout rotates."""
    chapters = c.extra["chapters"]
    n = int(g.get("n", 1))
    total = len(chapters) or n
    lay = g.get("layout") or ["left", "center", "right"][(n - 1) % 3]
    S, t0 = c.sel, c.t0
    out = min(c.t1, t0 + max(3.0, min(4.5, c.d)))   # holds 3–4.5s: the creator, 2026-10-21 "title cards should stay a little longer"
    ttl = "".join(f'<span class="w">{esc(w)}</span>' for w in g.get("title", "").lower().split())
    halftone = " halftone" if lay != "left" else ""
    if lay == "left":
        pos = ('style="left:150px;top:150px"', 'style="left:140px;top:230px"', 'style="left:820px;top:330px"')
    elif lay == "center":
        pos = ('style="left:0;right:0;text-align:center;top:965px"', 'style="left:0;right:0;text-align:center;top:90px"',
               'style="left:0;right:0;text-align:center;top:430px"')
    else:
        pos = ('style="right:160px;top:965px"', 'style="right:140px;top:90px;text-align:right"',
               'style="right:150px;top:420px;text-align:right"')
    ty = 760 if lay == "left" else 690
    tw = W - 300
    pills = []
    for i, ch in enumerate(chapters):
        on = " on" if ch["n"] == n else ""
        pills.append(f'<div class="pill{on}" style="--pc:{CHAP_COLORS[(ch["n"] - 1) % 6]}"><div class="pn">{ch["n"]:02d}</div>'
                     f'<div class="pl">{esc(ch["short"])}</div></div>')
    k_on = next((i for i, ch in enumerate(chapters) if ch["n"] == n), 0)
    pw = (tw - 22 * (len(chapters) - 1)) / max(1, len(chapters))
    px, py = 150 + k_on * (pw + 22) + pw / 2, ty
    path = f"M 40 1080 C 90 {py + 200}, {px - 260} {py - 90}, {px:.0f} {py - 6}"
    c.tl(f'tl.fromTo("{S} .chap", {{clipPath:"inset(0% 0% 0% 55%)"}}, {{clipPath:"inset(0% 0% 0% 0%)", duration:0.42, ease:"{E}"}}, {t0:.3f});')
    c.tl(f'tl.fromTo("{S} .dots", {{opacity:0}}, {{opacity:.5, duration:0.8}}, {t0 + 0.1:.3f});')
    c.tl(f'tl.fromTo("{S} .num", {{y:120, opacity:0}}, {{y:0, opacity:1, duration:0.75, ease:"{E}"}}, {t0 + 0.12:.3f});')
    c.tl(f'tl.fromTo("{S} .kick", {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:0.6, ease:"{E}"}}, {t0 + 0.2:.3f});')
    c.tl(f'tl.fromTo("{S} .ttl .w", {{opacity:0, y:30, filter:"blur(14px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:0.55, ease:"{E}", stagger:0.09}}, {t0 + 0.3:.3f});')
    c.tl(f'tl.fromTo("{S} .pill", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:0.5, ease:"{E}", stagger:0.05}}, {t0 + 0.32:.3f});')
    c.tl(f'tl.fromTo("{S} .pill.on", {{scale:0.86}}, {{scale:1, duration:0.5, ease:"back.out(2)"}}, {t0 + 0.75:.3f});')
    c.tl(f'tl.fromTo("{S} .path path", {{opacity:0}}, {{opacity:1, duration:0.3}}, {t0 + 0.3:.3f});')
    c.tl(f'tl.fromTo("{S} .walker", {{offsetDistance:"0%"}}, {{offsetDistance:"100%", duration:0.9, ease:"power2.inOut"}}, {t0 + 0.3:.3f});')
    c.tl(f'tl.to("{S} .chap", {{clipPath:"inset(0% 100% 0% 0%)", duration:0.42, ease:"expo.in"}}, {out - 0.42:.3f});')
    c.sfx += [("whoosh", t0 - 0.05), ("boom", t0 + 0.15), ("click", t0 + 0.75)]
    c.chapter_out = out
    return (f'<div class="chap"><div class="dots"></div>'
            f'<svg class="path" viewBox="0 0 1920 1080"><path d="{path}"/></svg>'
            f'<div class="walker" style="offset-path:path(\'{path}\');offset-rotate:0deg"></div>'
            f'<div class="kick" {pos[0]}>PART {n:02d} OF {total:02d}</div><div class="num{halftone}" {pos[1]}>{n:02d}</div>'
            f'<div class="ttl" {pos[2]}>{ttl}</div>'
            f'<div class="tracker" style="left:150px;top:{ty}px;width:{tw}px">{"".join(pills)}</div></div>')


def k_headline(g, c):
    """A whole-scene statement: huge centred grotesk with one serif-italic accent; words land as they're said."""
    text = g.get("text", "")
    size = g.get("size") or (190 if len(text) <= 16 else 150 if len(text) <= 28 else 112)
    spans, js = headline_words(text, c, c.t0)
    c.js += js
    sub = f'<div class="sub mono">{esc(g["sub"])}</div>' if g.get("sub") else ""
    if sub:
        c.rise(f"{c.sel} .sub", c.t0 + 0.4, blur=False, dy=10)
    c.sfx.append(("whoosh", c.t0))
    return c.box(f'<div class="t-big" style="font-size:{size}px">{spans}{sub}</div>')


k_title = k_headline


def k_chips(g, c):
    """White pills that pop in around the creator's head as she names things (talking-head shots) or in a scene."""
    items = g.get("items", [])
    ts = c.times(items, g.get("at"))
    chips = []
    rnd = [(-6, 0.0), (5, 0.35), (-3, 0.7), (4, 0.15), (-5, 0.55), (3, 0.85)]
    cols = 1 if c.w < 900 else 2
    rows = math.ceil(len(items) / cols)
    for i, it in enumerate(items):
        r, k = divmod(i, cols)
        x = (k + 0.5) / cols * c.w + rnd[i % 6][0] * 8
        y = (r + 0.5) / max(1, rows) * c.h
        chips.append(f'<div class="chip ch{i}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px">{rich(it)}</div>')
    for i, t in enumerate(ts):
        rot = rnd[i % 6][0] * 0.4                      # centring + tilt live in GSAP, not CSS (lint: css_transform_conflict)
        c.tl(f'tl.fromTo("{c.sel} .ch{i}", {{xPercent:-50, yPercent:-50, rotation:{rot:.1f}, opacity:0, scale:0.6, filter:"blur(8px)"}}, '
             f'{{xPercent:-50, yPercent:-50, rotation:{rot:.1f}, opacity:1, scale:1, filter:"blur(0px)", duration:0.5, ease:"back.out(1.8)"}}, {t:.3f});')
        c.tl(f'tl.to("{c.sel} .ch{i}", {{y:-10, duration:{max(0.5, c.t1 - t - 0.5):.2f}, ease:"sine.inOut"}}, {t + 0.5:.3f});')
        c.sfx.append(("pop", t))
    return c.box(f'<div style="position:relative;width:100%;height:100%">{"".join(chips)}</div>')


def k_list(g, c):
    """'IN THIS VIDEO' — numbered rows, numbers in each chapter's colour, landing as they're said."""
    items = g.get("items", [])
    ts = c.times(items, g.get("at"))
    rows = "".join(f'<div class="row r{i}"><span class="n" style="color:{CHAP_COLORS[i % 6]}">{i + 1:02d}</span>'
                   f'<span class="t">{rich(t)}</span></div>' for i, t in enumerate(items))
    c.rise(f"{c.sel} .kick", c.t0, blur=False, dy=-10)
    for i, t in enumerate(ts):
        c.rise(f"{c.sel} .r{i}", t, 0.5, 24)
        c.sfx.append(("click", t))
    return c.box(f'<div class="ilist" style="width:900px"><div class="kick mono">{esc(g.get("kicker", "in this video"))}</div>{rows}</div>')


def k_tracker(g, c):
    """The job tracker on white: where we are in the video (between chapters, at the recap)."""
    chapters = c.extra["chapters"]
    n = int(g.get("n", c.extra.get("chapter_n") or 1))
    pills = "".join(f'<div class="pill{" on" if ch["n"] == n else ""}" style="--pc:{CHAP_COLORS[(ch["n"] - 1) % 6]}">'
                    f'<div class="pn">{ch["n"]:02d}</div><div class="pl">{esc(ch["short"])}</div></div>' for ch in chapters)
    c.tl(f'tl.fromTo("{c.sel} .pill", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:0.5, ease:"{E}", stagger:0.06}}, {c.t0:.3f});')
    c.tl(f'tl.fromTo("{c.sel} .pill.on", {{y:0}}, {{y:-6, duration:0.4, ease:"back.out(2)"}}, {c.t0 + 0.6:.3f});')
    c.sfx.append(("rise", c.t0))
    return c.box(f'<div class="tracker light" style="position:relative;width:100%">{pills}</div>')


def k_cards(g, c):
    items = [i if isinstance(i, dict) else {"title": i} for i in g.get("items", [])]
    n = len(items)
    cols = min(n, int(g.get("cols", 1 if n == 1 else 2 if n in (2, 4) else 3 if n <= 6 else 4)))
    ts = c.times(items, g.get("at"), "title")
    from_face = c.b["shot"] in TALKING
    fx, fy = c.face["sx"] - c.x, c.face["sy"] - c.y
    cards = []
    for i, it in enumerate(items):
        fill = f' fill" style="--fc:{CHAP_COLORS[i % 6]}' if g.get("fill") else ""
        img = f'<img class="cimg" src="{esc(it["src"])}" alt="">' if it.get("src") else ""
        num = f'<div class="cn">{i + 1:02d}</div>' if g.get("numbered", True) else ""
        sub = f'<div class="sub">{esc(it["sub"])}</div>' if it.get("sub") else ""
        cards.append(f'<div class="card c{i}{fill}">{num}{img}<div class="ct">{acc(it.get("title", ""), it.get("accent"))}</div>{sub}</div>')
    gap = 30
    cw = (c.w - gap * (cols - 1)) / cols
    rows = (n + cols - 1) // cols
    for i, t in enumerate(ts):
        r, k = divmod(i, cols)
        cx, cy = k * (cw + gap) + cw / 2, c.h / 2 + (r - (rows - 1) / 2) * (c.h / max(rows, 1))
        if from_face:
            c.tl(f'tl.fromTo("{c.sel} .c{i}", {{x:{fx - cx:.0f}, y:{fy - cy:.0f}, scale:0.3, opacity:0}}, '
                 f'{{x:0, y:0, scale:1, opacity:1, duration:0.85, ease:"{E}"}}, {t:.3f});')
        else:
            c.tl(f'tl.fromTo("{c.sel} .c{i}", {{y:70, opacity:0, filter:"blur(10px)"}}, {{y:0, opacity:1, filter:"blur(0px)", duration:0.65, ease:"{E}"}}, {t:.3f});')
        c.sfx.append(("pop", t + 0.05))
    return c.box(f'<div class="cards" style="grid-template-columns:repeat({cols},1fr)">{"".join(cards)}</div>')


def k_stat(g, c):
    val, frm, dec = float(g["value"]), float(g.get("from", 0)), int(g.get("decimals", 0))
    final = f"{val:,.{dec}f}"
    t = c.at(g.get("at"))
    cnt = min(1.3, max(0.6, c.d * 0.4))
    countup(c, f"{c.sel} .n", frm, val, dec, t + 0.05, cnt, g.get("format", "comma") == "comma")
    c.rise(f"{c.sel} .num", t, 0.6, 60)
    c.rise(f"{c.sel} .lbl", t + cnt * 0.6, 0.5, 18)
    c.sfx += [("digital", t + 0.05), ("tick", t + cnt)]
    c.text_events.append({"beat": c.b["id"], "item": 0, "appear_t": round(t + c.sec0, 3)})
    pre, suf = esc(g.get("prefix", "")), g.get("suffix", "")
    suf_html = f'<span class="acc">{esc(suf)}</span>' if g.get("suffix_accent", True) and suf else esc(suf)
    return c.box(f'<div class="t-stat"><div class="num">{pre}<span class="n">{final}</span>{suf_html}</div>'
                 f'<div class="lbl">{acc(g.get("label", ""), g.get("accent"))}</div></div>')







def k_checklist(g, c):
    items = g.get("items", [])
    ts = c.times(items, g.get("at"))
    rows = "".join(f'<div class="ck k{i}"><span class="box"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
                   f'<b>{i + 1}</b></span><span class="tx">{rich(t)}</span></div>' for i, t in enumerate(items))
    for i, t in enumerate(ts):
        c.rise(f"{c.sel} .k{i}", t, 0.55, 30)
        c.tl(f'tl.to("{c.sel} .k{i} .box", {{background:"var(--chap)", borderColor:"var(--chap)", duration:0.2}}, {t + 0.25:.3f});')
        c.tl(f'tl.fromTo("{c.sel} .k{i} path", {{strokeDashoffset:30}}, {{strokeDashoffset:0, duration:0.35, ease:"power2.out"}}, {t + 0.3:.3f});')
        c.tl(f'tl.to("{c.sel} .k{i} b", {{opacity:0, duration:0.15}}, {t + 0.25:.3f});')
        if i:
            c.tl(f'tl.to("{c.sel} .k{i - 1} .tx", {{opacity:0.35, duration:0.3}}, {t:.3f});')
        c.sfx.append(("click", t + 0.28))
    return c.box(f'<div class="checklist">{rows}</div>')



def k_steps(g, c):
    items = g.get("items", [])
    n = len(items)
    ts = c.times(items, g.get("at"))
    pad = 120
    span = c.w - 2 * pad
    marks = "".join(f'<div class="sm s{i}" style="left:{pad + span * i / max(1, n - 1):.0f}px"><div class="dot"></div>'
                    f'<div class="sl">{rich(t)}</div></div>' for i, t in enumerate(items))
    c.tl(f'tl.fromTo("{c.sel} .track", {{scaleX:0}}, {{scaleX:1, duration:0.8, ease:"{E}"}}, {c.t0:.3f});')
    c.sfx.append(("rise", c.t0))
    for i, t in enumerate(ts):
        c.rise(f"{c.sel} .s{i}", t, 0.6, 30)
        c.tl(f'tl.{"fromTo" if i == 0 else "to"}("{c.sel} .fill", {"{scaleX:0}, " if i == 0 else ""}{{scaleX:{(i / max(1, n - 1)):.4f}, duration:0.5, ease:"{E}"}}, {t:.3f});')
        c.tl(f'tl.to("{c.sel} .s{i} .dot", {{borderColor:"var(--chap)", scale:1.2, duration:0.3}}, {t:.3f});')
        c.sfx.append(("click", t))
    return c.box(f'<div class="steps" style="--pad:{pad}px"><div class="track"></div><div class="fill"></div>{marks}</div>')


def k_versus(g, c):
    L, R = g.get("left", {}), g.get("right", {})
    tr = c.at(g.get("right_at") or g.get("strike_at"), c.t0 + c.d * 0.5)
    strike = g.get("strike", False)
    c.rise(f"{c.sel} .vl", c.t0 + 0.05, 0.7, 40)
    if strike:
        c.tl(f'tl.fromTo("{c.sel} .vl .strike", {{scaleX:0}}, {{scaleX:1, duration:0.3, ease:"power2.in"}}, {tr - 0.15:.3f});')
        c.sfx.append(("write", tr - 0.15))
    c.tl(f'tl.to("{c.sel} .vl", {{opacity:0.5, duration:0.4}}, {tr:.3f});')
    c.tl(f'tl.fromTo("{c.sel} .vr", {{opacity:0, y:50, scale:0.95}}, {{opacity:1, y:0, scale:1, duration:0.75, ease:"{E}"}}, {tr:.3f});')
    c.sfx.append(("pop", tr))
    return c.box(f'<div class="versus"><div class="vc vl"><div class="vt mono">{esc(L.get("label", "before"))}</div>'
                 f'<div class="vx">{acc(L.get("text", ""), L.get("accent"))}</div>{"<div class=strike></div>" if strike else ""}</div>'
                 f'<div class="vc vr"><div class="vt mono" style="color:var(--accent)">{esc(R.get("label", "now"))}</div>'
                 f'<div class="vx">{acc(R.get("text", ""), R.get("accent"))}</div></div></div>')


def img_wh(p: Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:  # noqa: BLE001
        return 1600, 1000


def k_browser(g, c):
    src = g["src"]
    iw, ih = img_wh(c.vd / src)
    bar = 56 if g.get("chrome", True) else 0
    vw, vh = c.w, c.h - bar
    dw, dh = vw, vw * ih / iw
    t0 = c.t0
    c.tl(f'tl.fromTo("{c.sel} .win", {{y:70, scale:0.94, opacity:0}}, {{y:0, scale:1, opacity:1, duration:0.8, ease:"{E}"}}, {t0:.3f});')
    c.sfx.append(("shutter", t0 + 0.05))
    if g.get("scroll") and dh > vh:
        c.tl(f'tl.to("{c.sel} .pg", {{y:{-(dh - vh) * float(g["scroll"]):.0f}, duration:{max(1.0, c.d - 1.0):.2f}, ease:"sine.inOut"}}, {t0 + 0.7:.3f});')
    f = g.get("focus")
    hl = ""
    if f:
        fx, fy, fw, fh = f["x"] * dw, f["y"] * dh, f["w"] * dw, f["h"] * dh
        s = max(1.2, min(3.0, min(vw / fw, vh / fh) * 0.8))
        tx, ty = vw / 2 - (fx + fw / 2) * s, vh / 2 - (fy + fh / 2) * s
        tp = c.at(g.get("punch_at"), t0 + min(1.0, c.d * 0.35))
        c.tl(f'tl.to("{c.sel} .pg", {{x:{tx:.0f}, y:{ty:.0f}, scale:{s:.3f}, duration:0.7, ease:"expo.inOut"}}, {tp:.3f});')
        hl = (f'<div class="hl" style="left:{fx:.0f}px;top:{fy:.0f}px;width:{fw:.0f}px;height:{fh:.0f}px;'
              f'border-width:{max(2, 6 / s):.1f}px"></div>')
        c.tl(f'tl.fromTo("{c.sel} .hl", {{opacity:0, scale:1.2}}, {{opacity:1, scale:1, duration:0.35, ease:"power2.out"}}, {tp + 0.55:.3f});')
        c.sfx += [("whoosh", tp - 0.05), ("click", tp + 0.55)]
    url = f'<div class="url">{esc(g.get("url", ""))}</div>' if bar else ""
    chrome = f'<div class="bar"><i></i><i></i><i></i>{url}</div>' if bar else ""
    return c.box(f'<div class="win">{chrome}<div class="view" style="height:{vh}px"><div class="pg" '
                 f'style="width:{dw:.0f}px;height:{dh:.0f}px"><img src="{esc(src)}" alt="">{hl}</div></div></div>')



def k_quote(g, c):
    spans = "".join(f'<span class="w">{esc(w)}</span>' for w in g.get("text", "").split())
    c.tl(f'tl.fromTo("{c.sel} .qt .w", {{y:30, opacity:0, filter:"blur(10px)"}}, {{y:0, opacity:1, filter:"blur(0px)", duration:0.55, ease:"{E}", stagger:0.05}}, {c.t0 + 0.1:.3f});')
    c.rise(f"{c.sel} .qb", c.t0 + 0.6, 0.5, 10, False)
    c.sfx.append(("write", c.t0 + 0.1))
    return c.box(f'<div class="t-quote"><div class="qt">“{spans}”</div><div class="qb mono">{esc(g.get("by", ""))}</div></div>')


def k_code(g, c):
    lines = g.get("lines", [])
    ts = c.times(lines, g.get("at"))
    rows = "".join(f'<div class="cl c{i}"><span class="ln">{i + 1}</span><span class="cx">{esc(l)}</span></div>' for i, l in enumerate(lines))
    c.rise(f"{c.sel} .cwin", c.t0, 0.7, 60)
    for i, t in enumerate(ts):
        n = max(2, len(lines[i]))
        c.tl(f'tl.set("{c.sel} .c{i}", {{opacity:1}}, {t:.3f});')
        c.tl(f'tl.fromTo("{c.sel} .c{i} .cx", {{clipPath:"inset(0 100% 0 0)"}}, {{clipPath:"inset(0 0% 0 0)", duration:{min(1.2, 0.03 * n):.2f}, ease:"steps({n})"}}, {t:.3f});')
    c.sfx.append(("digital", c.t0 + 0.2))
    return c.box(f'<div class="cwin"><div class="cbar"><i></i><i></i><i></i><span>{esc(g.get("title", "terminal"))}</span></div>'
                 f'<div class="cbody">{rows}</div></div>')


def k_lower(g, c):
    c.tl(f'tl.fromTo("{c.sel} .lower", {{opacity:0, y:20, filter:"blur(8px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:0.5, ease:"{E}"}}, {c.t0 + 0.1:.3f});')
    c.tl(f'tl.to("{c.sel} .lower", {{opacity:0, y:-10, duration:0.3}}, {max(c.t0 + 1.2, c.t1 - 0.35):.3f});')
    c.sfx.append(("click", c.t0 + 0.1))
    side = "right:90px" if c.face["sx"] < W / 2 else "left:90px"
    return (f'<div class="lower" style="{side}"><span class="dot"></span><div><div class="ln1">{esc(g.get("name", ""))}</div>'
            f'<div class="ln2">{esc(g.get("sub", ""))}</div></div></div>')


def k_cta(g, c):
    spans, js = headline_words(g.get("text", "free in the *Discord*"), c, c.t0)
    c.js += js
    tp = c.at(g.get("pill_at"), c.t0 + 0.8)
    c.tl(f'tl.fromTo("{c.sel} .pill2", {{opacity:0, scale:0.7}}, {{opacity:1, scale:1, duration:0.5, ease:"back.out(2)"}}, {tp:.3f});')
    c.sfx.append(("pop", tp))
    return c.box(f'<div class="cta"><div class="big">{spans}</div><div class="pill2">{esc(g.get("pill", "link in the description"))}</div></div>')




# ───────────────────────────── headline words ─────────────────────────────

def headline_words(text: str, c: Ctx, t_start: float, typed: bool = False) -> tuple[str, list[str]]:
    """Spans for a headline; each word blurs in when it's SAID (falls back to a quick stagger if it isn't)."""
    tw = word_tokens(text)
    js, spans, last = [], [], t_start - 0.08
    cursor = c.b.get("_w0") or 0
    hi = c.b.get("_w1") if c.b.get("_w1") is not None else len(c.words) - 1
    found = []
    for w, _ in tw:                                       # match headline words to speech, in order
        tok = "".join(toks(w))
        t = None
        for k in range(cursor, min(hi + 1, len(c.words))):
            if "".join(toks(c.words[k]["text"])) == tok:
                t = c.words[k]["start"] - c.sec0 - 0.04
                cursor = k + 1
                break
        found.append(t)
    if sum(t is not None for t in found) < 0.6 * len(tw):  # a paraphrase, not the spoken words: just stagger it in
        found = [None] * len(tw)
    t_cap = c.t1 - 0.5
    for i, (w, is_acc) in enumerate(tw):
        t = found[i]
        t = max(last + 0.06, t if t is not None else last + 0.09, t_start)
        t = min(t, max(t_start, t_cap))
        last = t
        inner = f"<em>{esc(w)}</em>" if is_acc else esc(w)
        spans.append(f'<span class="hw w{i}">{inner}</span>')
        sel = f"{c.sel} .w{i}"
        if typed:
            js.append(f'tl.fromTo("{sel}", {{opacity:0}}, {{opacity:1, duration:0.01}}, {t:.3f});')
        else:
            js.append(f'tl.fromTo("{sel}", {{opacity:0, y:14, filter:"blur(12px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:0.38, ease:"{E}"}}, {t:.3f});')
    if typed:
        spans.append('<span class="cur"></span>')
    return "".join(spans), js


# ───────────────────────────── shots (the speaker layer) ─────────────────────────────

def face_px(face) -> tuple[float, float, float, float]:
    return face["x"] * W, face["y"] * H, face["w"] * W, face["h"] * H


def shot_state(shot: str, face, push: float = 0.0, form: str = "inset") -> dict:
    """Transform + clip of #spk for a shot. form = clip-path shape family ('circle' for anything touching the bubble,
    'inset' otherwise), so GSAP can tween between states of the same family."""
    fx, fy, fw, fh = face_px(face)
    cx, cy = fx + fw / 2, fy + fh / 2
    if shot in ("full", "overlay", "punch"):
        s = (PUNCH if shot == "punch" else 1.0) + push
        x = min(0.0, max(W - s * W, cx * (1 - s)))
        y = min(0.0, max(H - s * H, cy * (1 - s)))
        clip = f"circle(2400px at {cx:.0f}px {cy:.0f}px)" if form == "circle" else "inset(0px 0px 0px 0px round 0px)"
        return {"x": round(x, 1), "y": round(y, 1), "scale": round(s, 4), "clipPath": clip, "autoAlpha": 1}
    if shot == "bubble":
        bx, by, r = BUBBLE
        R = min(max(fw, fh) * 0.9, H / 2 - 4)
        cx = min(max(cx, R), W - R)                    # keep the circle inside the frame (face near an edge
        cy = min(max(cy, R), H - R)                    # would otherwise leave half the bubble empty)
        s = r / R
        return {"x": round(bx - cx * s, 1), "y": round(by - cy * s, 1), "scale": round(s, 4),
                "clipPath": f"circle({R:.0f}px at {cx:.0f}px {cy:.0f}px)", "autoAlpha": 1}
    if shot == "split":
        x, y, w, h = SPLIT
        k = SPLIT_K
        cw, ch = w / k, h / k
        L = max(0.0, min(W - cw, cx - cw / 2))
        T = max(0.0, min(H - ch, cy - ch * 0.42))
        return {"x": round(x - L * k, 1), "y": round(y - T * k, 1), "scale": k,
                "clipPath": f"inset({T:.0f}px {W - L - cw:.0f}px {H - T - ch:.0f}px {L:.0f}px round {22 / k:.0f}px)", "autoAlpha": 1}
    if shot == "framed":
        x, y, s = FRAMED
        return {"x": x, "y": y, "scale": s, "clipPath": f"inset(0px 0px 0px 0px round {22 / s:.0f}px)", "autoAlpha": 1}
    return {"autoAlpha": 0}


def gsap_obj(d: dict) -> str:
    return "{" + ", ".join(f'{k}:{json.dumps(v)}' for k, v in d.items()) + "}"


def face_on_screen(shot, face) -> dict:
    fx, fy, fw, fh = face_px(face)
    if shot == "graphic":
        return {}
    st = shot_state(shot, face)
    s = st["scale"]
    return {"x": st["x"] + fx * s, "y": st["y"] + fy * s, "w": fw * s, "h": fh * s}


def overlay_stage(face) -> tuple[int, int, int, int]:
    """Graphic zone beside the creator on talking-head shots: the bigger free side of the face, or the band above her head."""
    fx, fy, fw, fh = face_px(face)
    grow = 0.035
    fx, fy, fw, fh = fx - fw * grow, fy - fh * grow, fw * (1 + 2 * grow), fh * (1 + 2 * grow)
    right = (int(fx + fw + 60), W - 80)
    left = (80, int(fx - 60))
    best = max((right, left), key=lambda r: r[1] - r[0])
    if best[1] - best[0] >= 520:
        return (best[0], 110, best[1] - best[0], 720)
    if fy - 40 - 90 >= 240:
        return (100, 90, W - 200, int(fy - 40 - 90))
    return (best[0], 110, max(300, best[1] - best[0]), 720)


# ───────────────────────────── captions ─────────────────────────────

def chunks(words, cut_idx: set[int], max_words=5, max_chars=34):
    out, cur = [], []
    for i, w in enumerate(words):
        gap = w["start"] - words[i - 1]["end"] if i else 0
        if cur and (i in cut_idx or len(cur) >= max_words or gap > 0.45
                    or len(" ".join(x["text"] for x in cur + [w])) > max_chars):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?:;]$", w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


# ───────────────────────────── lint (rules/05 + rules/06) ─────────────────────────────

def lint(plan, beats, total) -> list[str]:
    errs, warns = [], []
    if not plan.get("speaker", {}).get("face"):
        errs.append("speaker.face missing — read it off cut/frame_grid.jpg")
    prev_g = None
    run_plain = 0.0
    graphic_time = 0.0
    for b in beats:
        g = b.get("graphic")
        shot = b.get("shot")
        if shot not in SHOTS:
            errs.append(f"{b['id']}: shot must be one of {sorted(SHOTS)}")
        if g == "hold":
            if not prev_g:
                errs.append(f"{b['id']}: 'hold' with nothing to hold")
            continue
        if g:
            k = g.get("kind")
            if k not in KINDS:
                errs.append(f"{b['id']}: unknown graphic kind {k!r}")
            if shot in ("full", "punch", "framed") and k not in ON_FACE_OK:
                errs.append(f"{b['id']}: shot {shot} only takes {sorted(ON_FACE_OK)} — use overlay, bubble, split or graphic")
            if k == "chapter" and shot != "graphic":
                errs.append(f"{b['id']}: chapter cards are full-screen (shot graphic)")
            if k in ("checklist", "steps", "list") and len(g.get("items", [])) > 7:
                errs.append(f"{b['id']}: {len(g['items'])} items — max 7 on one picture")
            if b["dur"] < 0.9 and k not in ("lower", "chips"):
                errs.append(f"{b['id']}: graphic on screen {b['dur']:.2f}s — a flash; merge or 'hold' it (QA mistake #2)")
            if prev_g and json.dumps(g, sort_keys=True) == json.dumps(prev_g, sort_keys=True):
                errs.append(f"{b['id']}: same graphic as the beat before — use \"graphic\": \"hold\" (QA mistake #1)")
            if not b.get("reason"):
                warns.append(f"{b['id']}: no reason — every picture must say what the viewer should understand")
            if shot in ("bubble", "split", "graphic") and k not in ("chapter", "headline", "title", "cta", "tracker") and not b.get("headline"):
                warns.append(f"{b['id']}: graphic scene without a headline — the spoken line's key 2–4 words should title it")
            prev_g = g
        else:
            if shot in ("bubble", "split", "graphic", "overlay") and not b.get("headline"):
                errs.append(f"{b['id']}: shot {shot} needs a graphic or a headline")
            prev_g = None
        if shot in ("bubble", "split", "graphic"):
            graphic_time += b["dur"]
        plain = shot in ("full",) and not g
        run_plain = run_plain + b["dur"] if plain else 0.0
        if run_plain > 6.0:
            warns.append(f"{b['id']}: {run_plain:.0f}s of plain talking head — punch in, add chips or cut to a graphic (max ~5s)")
            run_plain = 0.0
        if b["dur"] > 9 and shot not in TALKING:
            warns.append(f"{b['id']}: {b['dur']:.1f}s on one graphic — build it in steps or split where the idea changes")
    for i in range(1, len(beats)):
        if beats[i]["shot"] == beats[i - 1]["shot"] == "punch":
            warns.append(f"{beats[i]['id']}: two punch-ins in a row — alternate full/punch")
    per_min = len(beats) / max(0.1, total / 60)
    if per_min < 14:
        warns.append(f"pace: {per_min:.0f} beats/min — the reference runs ~24 cuts/min; aim for 18+")
    if total > 60 and graphic_time / total < 0.45:
        warns.append(f"only {graphic_time / total:.0%} of the runtime is graphic scenes — the reference is ~65%")
    for w in dict.fromkeys(warns):
        print(f"  warn: {w}")
    for e in dict.fromkeys(errs):
        print(f"  ERROR: {e}")
    return errs


# ───────────────────────────── build ─────────────────────────────

def build(d: Path, draft: bool, only: str | None, lint_only: bool) -> None:
    plan = read_json(d / "plan.json")
    style = plan.get("style", "editorial")
    theme = plan.get("theme", "dark")                 # the creator's default (2026-10-17): dark canvas, hot-pink accent
    if theme not in CANVAS:
        sys.exit("theme must be dark or light")
    css_file = LF_ASSETS / f"{style}.css"
    if not css_file.exists():
        sys.exit(f"unknown style {style!r} — use editorial or operator")
    cut = d / "cut" / "cut.mp4"
    if not cut.exists():
        sys.exit("no cut/cut.mp4 — run cut.py first")
    total = snap(probe_duration(cut))
    words = read_json(d / "words.json")
    for s in plan["sections"]:                         # legacy shot names
        for b in s["beats"]:
            b["shot"] = {"inset": "bubble"}.get(b.get("shot"), b.get("shot"))
    beats = [b for s in plan["sections"] for b in s["beats"]]
    words = correct_words(beats, words)
    align(beats, words, total)
    face = plan.get("speaker", {}).get("face") or {"x": 0.42, "y": 0.18, "w": 0.16, "h": 0.3}
    if lint(plan, beats, total):
        sys.exit("plan has errors — fix plan.json and re-run")
    if lint_only:
        print(f"  {len(beats)} beats OK")
        return

    chapters = [{"n": s["chapter"], "short": s.get("short") or " ".join(w.capitalize() if i == 0 else w for i, w in enumerate(s["title"].split()[:2]))}
                for s in plan["sections"] if s.get("chapter")]
    fsx = face_px(face)
    face_c = {"sx": fsx[0] + fsx[2] / 2, "sy": fsx[1] + fsx[3] / 2}
    css = css_file.read_text(encoding="utf-8")
    music_vol = float(plan.get("music", {}).get("volume", 0.07))
    timeline = {"total": total, "fps": FPS, "draft": draft, "style": style, "face": face, "music_volume": music_vol,
                "sections": [], "beats": [], "sfx": [], "text_events": [], "rects": []}
    secs = plan["sections"]
    starts = [snap(s["beats"][0]["start"]) if i else 0.0 for i, s in enumerate(secs)]
    ends = starts[1:] + [total]
    chap_n = None
    for si, s in enumerate(secs):
        s0, s1 = starts[si], ends[si]
        sd = round(s1 - s0, 4)
        sdir = d / "sections" / s["id"]
        sec_words = [w for w in words if s0 <= w["start"] < s1]
        timeline["sections"].append({"id": s["id"], "start": s0, "end": s1, "dur": sd, "frames": round(sd * FPS)})
        if s.get("chapter"):
            chap_n = s["chapter"]
        chap_color = CHAP_COLORS[(chap_n - 1) % 6] if chap_n else "#FF1564"   # cold open = brand hot pink
        extra = {"chapters": chapters, "chapter_n": chap_n}
        build_this = not only or only == s["id"]
        js, gfx, sfx, uses_at = [], [], [], False
        gfx_start: dict[int, float] = {}
        exits: dict[int, list] = {}
        prev_shot, prev_gclip, chapter_out = None, None, None
        prev_head, prev_head_idx = None, None
        sb = s["beats"]
        for bi, b in enumerate(sb):
            shot = b["shot"]
            t0, t1 = b["start"] - s0, b["end"] - s0
            if bi == len(sb) - 1:
                t1 = sd
            b["end"] = s0 + t1
            b["dur"] = round(t1 - t0, 3)
            g = b.get("graphic")
            # ── canvas
            # base = the theme canvas; "black"/"white"/"mist" = a contrast beat
            bg = b.get("bg") or ("black" if shot == "framed" else "base")
            bgc = {"base": CANVAS[theme], "white": "#FFFFFF", "black": "#000000", "mist": "#F2F2F2"}.get(bg, bg)
            js.append(f'tl.set("#bg", {{backgroundColor:"{bgc}"}}, {t0:.3f});')
            dark = bg == "black" or (bg == "base" and theme == "dark")
            js.append(f'tl.set("#depth", {{opacity:{1 if bg == "base" and theme == "dark" else 0}}}, {t0:.3f});')
            # ── speaker layer
            circ = "bubble" in (prev_shot, shot)
            form = "circle" if circ else "inset"
            st = shot_state(shot, face, form=form)
            movable = {"full", "overlay", "bubble", "split", "framed"}
            moving = (prev_shot in movable and shot in movable and prev_shot != shot
                      and not ({prev_shot, shot} & {"bubble"} and {prev_shot, shot} & {"split", "framed"}))
            if moving:                                     # the speaker glides (iris into the bubble, slide into a panel)
                js.append(f'tl.set("#spk", {gsap_obj(shot_state(prev_shot, face, form=form))}, {t0:.3f});')
                js.append(f'tl.to("#spk", {{...{gsap_obj(st)}, duration:0.6, ease:"expo.inOut"}}, {t0:.3f});')
                sfx.append(("whoosh", t0 - 0.05))
            else:
                js.append(f'tl.set("#spk", {gsap_obj(st)}, {t0:.3f});')
            js.append(f'tl.set("#spk-sh", {{filter:"{SHADOW["dark" if dark else "light"] if shot in ("bubble", "split", "framed") else "none"}"}}, {t0:.3f});')
            js.append(f'tl.{"to" if shot == "bubble" else "set"}("#ring", {{opacity:{1 if shot == "bubble" else 0}'
                      f'{", duration:0.3" if shot == "bubble" else ""}}}, {t0 + (0.45 if shot == "bubble" and moving else 0):.3f});')
            if shot in ("full", "overlay") and b["dur"] > 1.2:  # never static: a slow push toward the face
                push = shot_state(shot, face, 0.035, form=form)
                js.append(f'tl.to("#spk", {{x:{push["x"]}, y:{push["y"]}, scale:{push["scale"]}, duration:{b["dur"] - (0.6 if moving else 0):.3f}, '
                          f'ease:"none"}}, {t0 + (0.6 if moving else 0):.3f});')
            if shot == "graphic" and prev_shot and prev_shot != "graphic":
                sfx.append(("whoosh", t0 - 0.05))
            prev_shot = shot
            # ── framed label
            if shot == "framed" and b.get("label"):
                gfx.append(f'<div id="{b["id"]}-lab" class="clip gfx dark" data-start="{t0:.3f}" data-duration="{t1 - t0:.3f}" data-track-index="5">'
                           f'<div class="frame-label">{rich(b["label"])}</div></div>')
                js.append(f'tl.fromTo("#{b["id"]}-lab .frame-label", {{opacity:0, y:-12}}, {{opacity:1, y:0, duration:0.4, ease:"{E}"}}, {t0 + 0.1:.3f});')
            # ── headline (graphic scenes): the spoken line's key words, landing as they're said
            hl = b.get("headline")
            if hl and shot in ("bubble", "split", "graphic", "overlay"):
                if hl == prev_head and prev_head_idx is not None:
                    gfx[prev_head_idx] = re.sub(r'data-duration="[\d.]+"', lambda m: f'data-duration="{t1 - gfx_start[prev_head_idx]:.3f}"', gfx[prev_head_idx], count=1)
                    exits[prev_head_idx][2] = t1
                else:
                    hx, hy = HEAD_POS.get(shot, (150, 78)) if shot != "overlay" else (overlay_stage(face)[0], 90)
                    hsel = f"#{b['id']}-h"
                    hc = Ctx(b, s0, words, (0, 0, W, H), hsel, face_c, d, extra)
                    size = b.get("headline_size") or (104 if shot != "split" else 92)
                    spans, hjs = headline_words(hl, hc, t0, typed=b.get("headline_style") == "type")
                    gfx.append(f'<div id="{b["id"]}-h" class="clip gfx{" dark" if dark else ""}" data-start="{t0:.3f}" data-duration="{t1 - t0:.3f}" '
                               f'data-track-index="5"><div class="headline" style="left:{hx}px;top:{hy}px;font-size:{size}px">{spans}</div></div>')
                    gfx_start[len(gfx) - 1] = t0
                    exits[len(gfx) - 1] = [hsel, "headline", t1, ".headline"]
                    prev_head, prev_head_idx = hl, len(gfx) - 1
                    js += hjs
                    timeline["text_events"].append({"beat": b["id"], "item": -1, "appear_t": round(b["start"] + 0.02, 3),
                                                    "word_t": round(b["start"], 3), "words": len(word_tokens(hl))})
            else:
                prev_head, prev_head_idx = None, None
            # ── graphic layer
            kind = None
            if g == "hold" and prev_gclip is None:
                print(f"  !! {b['id']}: 'hold' at a section start has nothing to hold — ignored")
                g = None
            if g == "hold":
                gfx[prev_gclip] = re.sub(r'data-duration="[\d.]+"', lambda m: f'data-duration="{t1 - gfx_start[prev_gclip]:.3f}"', gfx[prev_gclip], count=1)
                exits[prev_gclip][2] = t1
                kind = "hold"
            elif g:
                kind = g["kind"]
                has_h = bool(hl)
                if kind in ("chapter", "lower", "subscribe"):
                    stage = (0, 0, W, H)
                elif shot in TALKING:
                    stage = overlay_stage(face)
                else:
                    stage = STAGE[f"{shot}_h" if has_h else shot]
                sel = f"#{b['id']}-g"
                c = Ctx(b, s0, words, stage, sel, face_c, d, extra)
                fn = globals().get(f"k_{kind}")
                inner = fn(g, c)
                # blank-canvas guard (2026-10-17: a stat waited 1s for its word on an empty white frame)
                first = min((float(m) for j in c.js for m in re.findall(r", (-?[\d.]+)\);?\s*(?:\}\)\(\);)?$", j)), default=t0)
                if shot in ("graphic", "bubble", "split") and kind != "chapter" and not hl and first - t0 > 0.6:
                    print(f"  warn: {b['id']}: nothing on screen for {first - t0:.1f}s — start the beat at the visual's word, "
                          f"add a headline, or drop the 'at'")
                uses_at = uses_at or getattr(c, "uses_at", False)
                if kind == "chapter":
                    out_rel = getattr(c, "chapter_out", t1)
                    chapter_out = out_rel + s0
                    if out_rel < t1 - 0.05:                # card wiped off before the beat ends: the creator is back, not an empty frame
                        js.append(f'tl.set("#spk", {gsap_obj(shot_state("full", face))}, {out_rel - 0.2:.3f});')
                        js.append(f'tl.set("#spk-sh", {{filter:"none"}}, {out_rel - 0.2:.3f});')
                        p2 = shot_state("full", face, 0.02)
                        js.append(f'tl.to("#spk", {{scale:{p2["scale"]}, x:{p2["x"]}, y:{p2["y"]}, duration:{t1 - out_rel + 0.2:.3f}, ease:"none"}}, {out_rel - 0.2:.3f});')
                        prev_shot = "full"
                on_dark = dark or (theme == "dark" and shot in TALKING)    # talking-head overlays use dark glass in dark theme
                gfx.append(f'<div id="{b["id"]}-g" class="clip gfx{" dark" if on_dark else ""}" style="--chap:{chap_color}" data-start="{t0:.3f}" '
                           f'data-duration="{t1 - t0:.3f}" data-track-index="3">{inner}</div>')
                gfx_start[len(gfx) - 1] = t0
                exits[len(gfx) - 1] = [sel, kind, t1, ".stage"]
                prev_gclip = len(gfx) - 1
                js += c.js
                sfx += c.sfx
                timeline["text_events"] += c.text_events
                if kind == "lower":
                    stage = (W - 90 - 640 if face_c["sx"] < W / 2 else 90, 770, 640, 120)
                if kind == "subscribe":
                    stage = (W - 520 if face_c["sx"] < W / 2 else 120, 790, 420, 110)
                if kind != "chapter":
                    timeline["rects"].append({"beat": b["id"], "kind": kind, "shot": shot,
                                              "x": stage[0], "y": stage[1], "w": stage[2], "h": stage[3],
                                              "face": face_on_screen(shot, face)})
            else:
                prev_gclip = None
            for e in b.get("sfx", []):
                sfx.append((e["name"], t0 + float(e.get("at", 0))))
            timeline["beats"].append({"id": b["id"], "section": s["id"], "start": round(b["start"], 3), "end": round(b["end"], 3),
                                      "dur": b["dur"], "shot": shot, "kind": kind, "say": b["say"], "headline": hl,
                                      "graphic_hash": hashlib.sha1(json.dumps(g, sort_keys=True).encode()).hexdigest()[:10] if g and g != "hold" else None})
        # exits: graphics + headlines leave with a short blur-fade at the end of their LAST beat (after holds)
        for sel_, kind_, end_, inner_sel in exits.values():
            if kind_ not in ("chapter", "lower", "subscribe") and end_ < sd - 0.05:
                js.append(f'tl.to("{sel_} {inner_sel}", {{opacity:0, filter:"blur(8px)", duration:0.24, ease:"power2.in"}}, {end_ - 0.24:.3f});')
        timeline["sfx"] += [(n, round(t + s0, 3)) for n, t in sfx if n in SFX_FILE and 0 <= t < sd]

        # ── captions: talking-head shots only (graphic scenes are titled by their headline)
        cap_html = []
        if plan.get("captions", True):
            cut_idx = {i for i, w in enumerate(sec_words) for b in sb if abs(w["start"] - b["start"]) < 0.08}
            chs = chunks(sec_words, cut_idx)
            for ci, ch in enumerate(chs):
                bo = next((b for b in sb if b["start"] - 0.01 <= ch[0]["start"] < b["end"]), sb[-1])
                if bo["shot"] not in TALKING:
                    continue
                if chapter_out and ch[0]["start"] < chapter_out and isinstance(bo.get("graphic"), dict) and bo["graphic"].get("kind") == "chapter":
                    continue
                st_ = ch[0]["start"] - s0
                en_ = min(bo["end"] - s0, ch[-1]["end"] - s0 + 0.3)
                if ci + 1 < len(chs):                      # never overlap the next chunk (2026-10-17: "and n-from-of")
                    en_ = min(en_, chs[ci + 1][0]["start"] - s0 - 0.02)
                emph = {"".join(toks(e)) for e in bo.get("emphasis", [])}
                is_em = [bool(re.search(r"[0-9]", w["text"]) or "".join(toks(w["text"])) in emph) for w in ch]
                spans = "".join(f'<span class="cw{" em" if is_em[k] else ""} k{ci}_{k}">{esc(w["text"].strip(",;"))}</span>'
                                for k, w in enumerate(ch))
                cls = " framed" if bo["shot"] == "framed" else ""
                cap_html.append(f'<div class="clip cap{cls}" data-start="{st_:.3f}" data-duration="{max(0.2, en_ - st_):.3f}" '
                                f'data-track-index="6">{spans}</div>')
                for k, w in enumerate(ch):
                    t = max(st_, w["start"] - s0 - 0.02)
                    js.append(f'tl.fromTo(".k{ci}_{k}", {{opacity:0, y:8}}, {{opacity:1, y:0, duration:0.12, ease:"power2.out"}}, {t:.3f});')

        if not build_this:
            continue
        # ── assets
        a = sdir / "assets"
        (a / "fonts").mkdir(parents=True, exist_ok=True)
        for f in [*(SHORTIFY_ASSETS / "fonts").glob("*.ttf"), *(LF_ASSETS / "fonts").glob("*.ttf")]:
            if not (a / "fonts" / f.name).exists():
                shutil.copy(f, a / "fonts" / f.name)
        shutil.copy(SHORTIFY_ASSETS / "gsap.min.js", a / "gsap.min.js")
        page_src = "\n".join(gfx)
        for ref in set(re.findall(r'src="((?:assets|custom)/[^"]+)"', page_src)):
            src_p, dst_p = d / ref, sdir / ref
            if src_p.exists():
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_p, dst_p)
            else:
                print(f"  !! {s['id']}: missing image {ref}")
        foot = a / "footage.mp4"
        stamp = f"{cut.stat().st_mtime_ns}:{s0}:{s1}"
        stamp_f = a / ".footage_stamp"
        if not foot.exists() or not stamp_f.exists() or stamp_f.read_text() != stamp:
            subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{s0:.4f}", "-i", str(cut), "-t", f"{sd:.4f}", "-an",
                            "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "8", "-pix_fmt", "yuv420p",   # near-lossless: the creator saw soft footage (2026-10-21)
                            "-g", "15", str(foot)], check=True)
            stamp_f.write_text(stamp)
        at_js = ""
        if uses_at:
            wl = [["".join(toks(w["text"])), round(w["start"] - s0, 3)] for w in sec_words]
            at_js = (f"const __W={json.dumps(wl)};\n"
                     "function __at(p, lo, hi){ const q=p.toLowerCase().replace(/[^a-z0-9 ]/g,'').split(/\\s+/).filter(Boolean);"
                     " for(let i=0;i<__W.length;i++){ if(__W[i][1]<lo-0.05||__W[i][1]>hi) continue; let ok=true;"
                     " for(let k=0;k<q.length;k++){ if(!__W[i+k]||__W[i+k][0]!==q[k]){ok=false;break;} } if(ok) return __W[i][1]; }"
                     " return lo+0.1; }\n")
        rw, rh = (W // 2, H // 2) if draft else (W, H)
        scale = 0.5 if draft else 1
        bx, by, br = BUBBLE
        page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={rw}, height={rh}" />
<script src="assets/gsap.min.js"></script>
<style>
html, body {{ width:{rw}px; height:{rh}px; margin:0; overflow:hidden; background:{CANVAS[theme]}; }}
#root {{ position:relative; width:{rw}px; height:{rh}px; overflow:hidden; }}
#stage {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; transform:scale({scale}); transform-origin:0 0; }}
{css}
#stage {{ --chap:{chap_color}; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{sd:.3f}" data-width="{rw}" data-height="{rh}" data-fps="{FPS}">
<div id="stage" class="theme-{theme}">
<div id="bg" style="background-color:{CANVAS[theme]}"></div>
<div id="depth"><div class="grid"></div></div>
<div id="spk-sh"><div id="spk"><video id="footage" class="clip" src="assets/footage.mp4" data-start="0" data-duration="{sd:.3f}" data-track-index="1" muted playsinline></video></div></div>
<div id="ring" style="left:{bx - br - 9}px;top:{by - br - 9}px;width:{2 * br + 18}px;height:{2 * br + 18}px"></div>
{page_src}
{chr(10).join(cap_html)}
<div class="grain"></div>
</div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{at_js}tl.fromTo("#ring", {{rotation:0}}, {{rotation:{360 * sd / 7:.0f}, duration:{sd:.3f}, ease:"none"}}, 0);
{chr(10).join(js)}
tl.set({{}}, {{}}, {sd:.3f});
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
        (sdir / "index.html").write_text(page, encoding="utf-8")
        write_json(sdir / "meta.json", {"id": f"{d.name}-{s['id']}", "name": f"{d.name} {s['id']}"})
        write_json(sdir / "hyperframes.json", {"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                              "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}})
        print(f"  {s['id']} {fmt_t(s0)}–{fmt_t(s1)}  {len(sb)} beats · {len(gfx)} layers · {len(cap_html)} captions")
    write_json(d / "timeline.json", timeline)
    print(f"  wrote timeline.json · {len(timeline['beats'])} beats · {len(timeline['sfx'])} sfx · style {style} · "
          f"{'DRAFT 960x540' if draft else 'FULL 1920x1080'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--section")
    ap.add_argument("--lint", action="store_true")
    a = ap.parse_args()
    build(video_dir(a.video_dir), a.draft, a.section, a.lint)


if __name__ == "__main__":
    main()
