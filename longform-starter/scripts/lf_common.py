"""Shared helpers for the Longform Starter (self-contained)."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LF_DIR = Path(__file__).resolve().parent.parent                       # .claude/skills/longform-starter
HQ_ROOT = LF_DIR.parents[2] if LF_DIR.parent.name == "skills" else Path.cwd()   # your project folder
VIDEOS_ROOT = HQ_ROOT / "videos"                                       # one folder per video
RULES = LF_DIR / "rules"
LF_ASSETS = LF_DIR / "assets"
SHORTIFY_ASSETS = LF_ASSETS                                            # fonts, gsap, optional sfx/ + music/
SHORTIFY_SCRIPTS = VIDEO_CUT = LF_DIR / "scripts"


def find_ffmpeg_dir() -> Path | None:
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    on_path = shutil.which("ffmpeg")
    if on_path and shutil.which("ffprobe"):
        return Path(on_path).parent
    cands = [Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin"), Path(r"C:\ffmpeg\bin"),
             Path(r"C:\ProgramData\chocolatey\bin"), Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"]
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget.exists():
        cands = sorted(winget.glob("Gyan.FFmpeg*/ffmpeg-*/bin"), reverse=True) + cands
    return next((d for d in cands if (d / exe).exists()), None)


def tool_env() -> dict:
    env = dict(os.environ)
    d = find_ffmpeg_dir()
    if d:
        env["PATH"] = str(d) + os.pathsep + env.get("PATH", "")
    return env


def ffmpeg() -> str:
    d = find_ffmpeg_dir()
    if not d:
        sys.exit("ffmpeg not found. Install it (Windows: winget install Gyan.FFmpeg · Mac: brew install ffmpeg)")
    return str(d / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))


def ffprobe() -> str:
    return ffmpeg().replace("ffmpeg.exe", "ffprobe.exe").replace("/ffmpeg", "/ffprobe")


def whisper_python() -> str:
    """A Python that can import faster_whisper (set LONGFORM_PYTHON to point at another one)."""
    for py in [os.environ.get("LONGFORM_PYTHON"), sys.executable]:
        if py and subprocess.run([py, "-c", "import faster_whisper"], capture_output=True).returncode == 0:
            return py
    sys.exit("faster-whisper not found. Install it:  python -m pip install faster-whisper")


def load_env() -> None:
    return None


def run(cmd, cwd=None, check=True):
    print("  $", " ".join(str(c) for c in cmd))
    use_shell = os.name == "nt" and cmd and cmd[0] in ("npx", "npm", "node")
    return subprocess.run([str(c) for c in cmd] if not use_shell else subprocess.list2cmdline([str(c) for c in cmd]),
                          cwd=cwd, env=tool_env(), check=check, shell=use_shell)


def probe_duration(path) -> float:
    out = subprocess.run([ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, data) -> None:
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


W, H, FPS = 1920, 1080, 30
WPM = 155                                                       # the creator's read-to-camera pace (tune after video 1)


def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'").replace("'", ""))


def snap(t: float) -> float:
    """Round a time to the frame grid so section boundaries never drift."""
    return round(round(t * FPS) / FPS, 4)


def fmt_t(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:05.2f}"


def parse_t(s: str) -> float:
    parts = [float(p) for p in s.split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


# ───────────────────────────── script.md ─────────────────────────────
# Format (see templates/script.md):
#   # Title
#   ## Cold open                 ← section, no chapter card
#   ## 01 · research and script  ← chapter: gets a full-screen chapter card
#   Spoken lines. One sentence or more per line.
#   > direction / b-roll idea    ← never spoken, never on the teleprompter
#   <!-- comments -->            ← ignored

CHAPTER_RE = re.compile(r"^##\s+(\d{1,2})\s*[·.\-:|]\s*(.+?)\s*$")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    # split after . ! ? (keep "3.5", "e.g." intact-ish), and on em-dash pauses only if long
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'“A-Z0-9])", text)
    return [p.strip() for p in parts if p.strip()]


def parse_script(path: Path) -> dict:
    """-> {"title", "sections": [{"id","title","chapter": n|None, "sentences": [...]}]}"""
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    title, sections, cur = "", [], None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("# ") and not title:
            title = s[2:].strip()
            continue
        if s.startswith("## "):
            m = CHAPTER_RE.match(s)
            cur = {"title": (m.group(2) if m else s[3:]).strip(), "chapter": int(m.group(1)) if m else None,
                   "lines": []}
            sections.append(cur)
            continue
        if not s or s.startswith(">") or s.startswith("#") or s.startswith("|") or s.startswith("---"):
            continue
        if s.startswith("**") and s.endswith("**") and ":" in s:     # metadata lines like **Title:** ...
            continue
        if cur is None:
            cur = {"title": "cold open", "chapter": None, "lines": []}
            sections.append(cur)
        cur["lines"].append(s)
    out = []
    for i, sec in enumerate(sections):
        sents = [x for ln in sec["lines"] for x in split_sentences(ln)]
        if not sents:
            continue
        out.append({"id": f"s{len(out):02d}", "title": sec["title"], "chapter": sec["chapter"], "sentences": sents})
    return {"title": title, "sections": out}


def video_dir(arg: str) -> Path:
    p = Path(arg)
    if not p.exists():
        p = VIDEOS_ROOT / arg
    if not p.exists():
        sys.exit(f"video folder not found: {arg}")
    return p.resolve()


def latest(d: Path, pattern: str) -> Path | None:
    files = sorted(d.glob(pattern), key=lambda p: [int(x) for x in re.findall(r"\d+", p.stem)] or [0])
    return files[-1] if files else None
