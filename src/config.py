"""
config.py — Cau hinh duong dan va thong so du an.
(pycapcut edition — khong con API_BASE / VectCutAPI)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# ── Duong dan input / output ──────────────────────────────────────────────────
INPUTS        = BASE_DIR / "inputs"
VIDEO_PATH    = INPUTS   / "video_goc.mp4"
SRT_PATH      = INPUTS   / "subtitle.srt"
AUDIO_FOLDER  = INPUTS   / "audios"

OUTPUTS        = BASE_DIR / "outputs"
ADJUSTED_CLIPS = OUTPUTS  / "adjusted_clips"

# ── Thong so video ────────────────────────────────────────────────────────────
WIDTH  = 1080
HEIGHT = 1920
FPS    = 30

MIN_SPEED = 0.1
MAX_SPEED = 10.0

# ── FFmpeg ────────────────────────────────────────────────────────────────────
FFMPEG_BIN  = os.getenv("FFMPEG_BIN",  "ffmpeg")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", "ffprobe")


# ── Thu muc Drafts cua CapCut ─────────────────────────────────────────────────
def _find_capcut_drafts() -> "Path | None":
    """
    Tim thu muc Drafts cua CapCut PC theo thu tu uu tien:
      1. Bien moi truong CAPCUT_DRAFTS_DIR (dat boi user hoac GUI)
      2. %LOCALAPPDATA%\\CapCut\\User Data\\Projects
      3. %LOCALAPPDATA%\\CapCut Pro\\User Data\\Projects
      4. None — neu khong tim thay
    """
    env_val = os.environ.get("CAPCUT_DRAFTS_DIR", "")
    if env_val:
        p = Path(env_val)
        if p.is_dir():
            return p

    appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    for sub in ["CapCut", "CapCut Pro"]:
        p = appdata / sub / "User Data" / "Projects"
        if p.is_dir():
            return p

    return None


CAPCUT_DRAFTS_DIR: "Path | None" = _find_capcut_drafts()
