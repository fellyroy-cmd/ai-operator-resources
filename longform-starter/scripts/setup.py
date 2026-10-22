"""One-time setup check for the Longform Starter.   python setup.py

Checks Python packages, ffmpeg (7+), Node/npx (Hyperframes runs through npx), and downloads GSAP (the animation
library) into assets/. Prints exactly what to install if something's missing.
"""
import importlib
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

try:                                                   # Windows terminals default to cp1252: ✓/✗ would crash
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
GSAP_URL = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"
ok = True

for mod, pip in (("numpy", "numpy"), ("PIL", "pillow"), ("faster_whisper", "faster-whisper")):
    try:
        importlib.import_module(mod)
        print(f"  ✓ {pip}")
    except ImportError:
        alt = os.environ.get("LONGFORM_PYTHON")          # whisper may live in another Python (a venv)
        if mod == "faster_whisper" and alt and subprocess.run([alt, "-c", "import faster_whisper"],
                                                              capture_output=True).returncode == 0:
            print(f"  ✓ {pip} (in LONGFORM_PYTHON)")
            continue
        ok = False
        print(f"  ✗ {pip:16s} →  python -m pip install {pip}")

sys.path.insert(0, str(HERE))
try:
    from lf_common import ffmpeg
    out = subprocess.run([ffmpeg(), "-version"], capture_output=True, text=True).stdout
    ver = re.search(r"ffmpeg version (\d+)", out)
    if ver and int(ver.group(1)) >= 7:
        print(f"  ✓ ffmpeg {ver.group(1)}")
    else:
        ok = False
        print("  ✗ ffmpeg is older than 7 →  update it (Windows: winget install Gyan.FFmpeg · Mac: brew install ffmpeg)")
except SystemExit as e:
    ok = False
    print(f"  ✗ {e}")

if shutil.which("npx") or shutil.which("npx.cmd"):
    print("  ✓ node / npx (Hyperframes installs itself on first render)")
else:
    ok = False
    print("  ✗ Node.js →  install the LTS from https://nodejs.org")

g = ASSETS / "gsap.min.js"
if not g.exists():
    try:
        urllib.request.urlretrieve(GSAP_URL, g)
        print("  ✓ downloaded GSAP into assets/")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  ✗ couldn't download GSAP ({e}) →  save {GSAP_URL} as {g}")
else:
    print("  ✓ GSAP")

print("\n  READY — open Claude Code in your project and say: \"start a new longform video about <topic>\"" if ok
      else "\n  Fix the ✗ items above, then run setup.py again.")
