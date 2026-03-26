"""
video_processor.py -- Video processing voi FFmpeg.

Pipeline 2 pha tach biet:
  cut_all_clips   : Pha 1 -- stream copy, CPU nhe, song song
  encode_all_clips: Pha 2 -- GPU/CPU encode, tung clip mot

FIX v2.1:
  - Giam priority cua tat ca tien trinh FFmpeg xuong Below Normal (Windows)
    hoac nice +10 (Linux/Mac) -> may khong bi lag khi xu ly
  - Them -threads N vao FFmpeg encode de han che so CPU core su dung
  - Worker count mac dinh bao thu hon (2 thay vi 4)
  - CPU_THREADS env var: so luong CPU thread FFmpeg duoc phep dung
  - Them stop_event vao cut/encode de huy nhanh hon
"""

import os, re, json, subprocess, logging, threading, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from src.config import (
    ADJUSTED_CLIPS, VIDEO_PATH,
    FFMPEG_BIN, FFPROBE_BIN,
    MIN_SPEED, MAX_SPEED, FPS,
)

log = logging.getLogger(__name__)

# ── Worker count ──────────────────────────────────────────────────────────────
CUT_WORKERS = int(os.environ.get("CUT_WORKERS", 2))

def _default_encode_workers():
    forced = os.environ.get("ENCODE_WORKERS", "").strip()
    if forced.isdigit():
        return int(forced)
    return 2   # bao thu hon: 2 (giam xuong tu 4) tranh full CPU

ENCODE_WORKERS = _default_encode_workers()
MAX_WORKERS    = ENCODE_WORKERS

# ── So CPU thread FFmpeg duoc phep dung ──────────────────────────────────────
# Mac dinh: de lai 2 core cho OS/app khac
# Dat FFMPEG_CPU_THREADS=0 de FFmpeg tu quyet dinh (max, de het CPU)
def _cpu_threads() -> int:
    env = os.environ.get("FFMPEG_CPU_THREADS", "").strip()
    if env.isdigit():
        return int(env)
    cores = os.cpu_count() or 4
    # De lai 2 core cho may, toi thieu 2 thread cho FFmpeg
    return max(2, cores - 2)

_FFMPEG_CPU_THREADS = _cpu_threads()


# ── GPU encoder auto-detect ───────────────────────────────────────────────────
def _detect_encoder(ffmpeg_bin="ffmpeg"):
    forced = os.environ.get("FFMPEG_ENCODER", "").strip()
    if forced:
        log.info("Encoder: %s (ep buoc)", forced)
        return forced, forced.upper()
    for enc, label in [
        ("h264_nvenc", "NVIDIA GPU"),
        ("h264_amf",   "AMD GPU"),
        ("h264_qsv",   "Intel GPU"),
    ]:
        try:
            r = subprocess.run(
                [ffmpeg_bin, "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1",
                 "-c:v", enc, "-f", "null", "-"],
                capture_output=True, timeout=8)
            if r.returncode == 0:
                log.info("GPU encoder: %s (%s)", enc, label)
                return enc, label
        except Exception:
            continue
    log.info("Dung CPU encoder: libx264")
    return "libx264", "CPU"

_ENCODER, _ENCODER_LABEL = _detect_encoder()

# Tinh lai ENCODE_WORKERS dua vao encoder thuc su (neu chua override)
if not os.environ.get("ENCODE_WORKERS", "").strip():
    if _ENCODER == "h264_nvenc":
        ENCODE_WORKERS = 2   # 2 NVENC session la du (giam tai CPU filter)
    elif _ENCODER in ("h264_amf", "h264_qsv"):
        ENCODE_WORKERS = 1   # 1 la an toan
    else:
        # CPU encoder: 1 process de khong nghen may
        ENCODE_WORKERS = 1
    MAX_WORKERS = ENCODE_WORKERS


# ── Subprocess helpers — priority thap ───────────────────────────────────────

def _low_priority_kwargs() -> dict:
    """
    Tra ve kwargs cho subprocess.run / Popen de chay FFmpeg o priority thap.
    - Windows : BELOW_NORMAL_PRIORITY_CLASS + CREATE_NO_WINDOW
    - Linux/Mac: preexec_fn = os.nice(10)
    """
    kw: dict = {}
    if sys.platform == "win32":
        # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        # CREATE_NO_WINDOW            = 0x08000000
        kw["creationflags"] = 0x00004000 | 0x08000000
    else:
        kw["preexec_fn"] = lambda: os.nice(10)
    return kw


def _run_ffmpeg(cmd: list, label: str = "") -> tuple[bool, str]:
    """Chay FFmpeg voi priority thap. Tra ve (ok, error_tail)."""
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",      # Fix: Windows dung cp1252 mac dinh, FFmpeg xuat UTF-8
            errors="replace",      # Thay ky tu loi bang ? thay vi crash
            **_low_priority_kwargs()
        )
        if r.returncode == 0:
            return True, ""
        stderr = (r.stderr or "").strip()
        lines  = [l for l in stderr.splitlines() if l.strip()]
        tail   = "\n".join(lines[-5:]) if lines else f"exit={r.returncode}"
        if label:
            log.error("[FFMPEG] %s loi (exit %d):\n%s", label, r.returncode, tail)
        return False, tail
    except Exception as e:
        return False, str(e)


# ── ffprobe cache ─────────────────────────────────────────────────────────────
_dur_cache: dict[str, float] = {}
_dur_lock = threading.Lock()

def get_duration(p: Path) -> float:
    key = str(p.resolve())
    with _dur_lock:
        if key in _dur_cache:
            return _dur_cache[key]
    r = subprocess.run(
        [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
         "-show_format", str(p)],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=True,
        **_low_priority_kwargs()
    )
    dur = float(json.loads(r.stdout)["format"]["duration"])
    with _dur_lock:
        _dur_cache[key] = dur
    return dur


# ── Natural sort ──────────────────────────────────────────────────────────────
def _natural_key(p: Path):
    return [int(x) if x.isdigit() else x.lower()
            for x in re.split(r"(\d+)", p.stem)]

def natural_sorted(files): return sorted(files, key=_natural_key)

def collect_audio_files(audio_folder: Path) -> list[Path]:
    files  = list(audio_folder.glob("*.mp3")) + list(audio_folder.glob("*.wav"))
    result = natural_sorted(files)
    log.info("Tim thay %d audio files trong %s", len(result), audio_folder)
    return result


# ── SRT parser ────────────────────────────────────────────────────────────────
def _ts(t: str) -> float:
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h)*3600 + int(m)*60 + float(s)

def parse_srt(srt_path: Path) -> list[dict]:
    text = Path(srt_path).read_text(encoding="utf-8-sig")
    pat  = re.compile(
        r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})"
        r"\s*\n([\s\S]*?)(?=\n\d+\n|\Z)", re.MULTILINE)
    segs = [
        {"index": int(m[1]), "start": _ts(m[2]),
         "end":   _ts(m[3]), "text": m[4].strip()}
        for m in pat.finditer(text)
    ]
    if not segs:
        raise ValueError(f"Khong co segment trong: {srt_path}")
    log.info("Doc %d segments tu %s", len(segs), srt_path)
    return segs


# ── Helpers ───────────────────────────────────────────────────────────────────
def _clip_valid(path: Path, min_bytes: int = 4096) -> bool:
    try:
        return path.exists() and path.stat().st_size >= min_bytes
    except OSError:
        return False


# ── Pha 1: cat chinh xac (double-ss + ultrafast encode) ──────────────────────
def _do_cut(video_path: Path, start: float, duration: float,
            out: Path) -> bool:
    """
    Cat chinh xac dung phan video tu 'start' den 'start+duration'.

    BUG CU: -ss TRUOC -i dung fast-seek -> FFmpeg tua ve keyframe truoc start
            -> moi clip bat dau SOM HON start that -> noi dung bi TRUNG LAP.

    FIX: Ky thuat double-ss:
      1. -ss (truoc -i): fast-seek den 'start - pre' (keyframe-aligned, nhanh)
      2. -ss (sau -i)  : precise-seek them 'pre' giay (decode chinh xac)
      3. -t duration   : lay dung so giay can thiet
      4. libx264 ultrafast thay stream copy: tranh van de keyframe-boundary
         (stream copy bat buoc phai bat dau tai keyframe, khong the bat dau
          giua GOP -> gay trung lap neu start khong nam tren keyframe)

    Ket qua: clip bat dau DUNG TAI 'start', dai DUNG 'duration' giay.
    Performance: libx264 ultrafast ~200fps cho 1080p -> < 0.2s cho clip 5 giay.
    """
    out.parent.mkdir(parents=True, exist_ok=True)

    # Decode buffer: tua fast-seek lui 'pre' giay truoc target
    # roi precise-seek them 'pre' giay de cat chinh xac
    pre  = min(4.0, start)            # toi da 4s decode buffer
    seek = round(start - pre, 6)      # vi tri fast-seek (>= 0)

    cmd = [
        FFMPEG_BIN,
        "-ss", f"{seek:.6f}",         # 1. fast seek (keyframe-aligned, nhanh)
        "-i",  str(video_path),
        "-ss", f"{pre:.6f}",          # 2. precise seek them 'pre' giay
        "-t",  f"{duration:.6f}",     # 3. lay dung 'duration' giay
        "-c:v", "libx264",            # 4. encode (khong stream copy)
        "-preset", "ultrafast",       #    ultrafast: ~200fps, chi mat < 0.2s/clip
        "-crf", "16",                 #    CRF 16: chat luong cao cho raw cut
        "-pix_fmt", "yuv420p",
        "-an",
        "-avoid_negative_ts", "make_zero",
        "-y", str(out),
    ]
    ok, err = _run_ffmpeg(cmd, label=out.name)
    if not ok:
        log.error("Cut loi: %s | %s", out.name, err)
    return ok


def cut_all_clips(
    segments, audio_files, video_path: Path, raw_dir: Path,
    skip_existing: bool = True,
    progress_cb: Optional[Callable] = None,
    stop_event: Optional[threading.Event] = None,
) -> list:
    """
    Pha 1: Cat toan bo clip bang stream copy.
    Tra ve list[dict] chua: seg info + raw_path + audio_path + audio_dur + speed.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    total = len(segments)

    # Pre-fetch audio durations
    audio_durs = {}
    with ThreadPoolExecutor(max_workers=min(8, total)) as ex:
        fmap = {ex.submit(get_duration, audio_files[i]): i
                for i in range(total)}
        for fut in as_completed(fmap):
            audio_durs[fmap[fut]] = fut.result()

    infos      = [None] * total
    done_count = [0]
    lock       = threading.Lock()

    def do_one(i):
        if stop_event and stop_event.is_set():
            return i, None

        seg   = segments[i]
        af    = audio_files[i]
        adur  = audio_durs[i]
        orig  = seg["end"] - seg["start"]
        speed = max(MIN_SPEED, min(MAX_SPEED, orig / adur))
        raw   = raw_dir / f"raw_{i+1:04d}.mp4"

        skipped = skip_existing and _clip_valid(raw)
        if not skipped and not (stop_event and stop_event.is_set()):
            ok = _do_cut(video_path, seg["start"], orig, raw)
            if not ok:
                log.error("Cut that bai segment %d", i + 1)

        with lock:
            done_count[0] += 1
            done = done_count[0]

        if progress_cb:
            progress_cb(done, total, raw.name, skipped)

        return i, {**seg, "raw_path": raw, "audio_path": af,
                   "audio_dur": adur, "speed": speed}

    w = min(CUT_WORKERS, total)
    with ThreadPoolExecutor(max_workers=w) as ex:
        fmap = {ex.submit(do_one, i): i for i in range(total)}
        for fut in as_completed(fmap):
            idx, info = fut.result()
            if info is not None:
                infos[idx] = info

    return infos


# ── Pha 2: encode (GPU/CPU) ───────────────────────────────────────────────────

def _do_encode(raw_path: Path, speed: float, out_path: Path) -> bool:
    """
    Encode 1 clip voi speed da tinh.
    -threads {N} de gioi han CPU cores -> may khong bi full tai.
    """
    vf = f"setpts=PTS/{speed},fps={FPS}"
    t  = str(_FFMPEG_CPU_THREADS)  # so thread CPU cho filter/mux

    if _ENCODER == "h264_nvenc":
        cmd = [
            FFMPEG_BIN, "-threads", t,
            "-i", str(raw_path), "-vf", vf, "-an",
            "-c:v", "h264_nvenc", "-pix_fmt", "yuv420p",
            "-rc", "vbr", "-cq", "23", "-b:v", "0",
            "-movflags", "+faststart", "-y", str(out_path),
        ]
    elif _ENCODER == "h264_amf":
        cmd = [
            FFMPEG_BIN, "-threads", t,
            "-i", str(raw_path), "-vf", vf, "-an",
            "-c:v", "h264_amf", "-pix_fmt", "yuv420p",
            "-quality", "speed", "-qp_i", "23", "-qp_p", "23",
            "-movflags", "+faststart", "-y", str(out_path),
        ]
    elif _ENCODER == "h264_qsv":
        cmd = [
            FFMPEG_BIN, "-threads", t,
            "-i", str(raw_path), "-vf", vf, "-an",
            "-c:v", "h264_qsv", "-pix_fmt", "yuv420p",
            "-global_quality", "23",
            "-movflags", "+faststart", "-y", str(out_path),
        ]
    else:
        # libx264 — CPU encoder, gioi han thread la quan trong nhat
        cmd = [
            FFMPEG_BIN, "-threads", t,
            "-i", str(raw_path), "-vf", vf, "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "23",
            "-x264-params", f"threads={t}",
            "-movflags", "+faststart", "-y", str(out_path),
        ]

    ok, err = _run_ffmpeg(cmd, label=out_path.name)
    if not ok:
        log.error("Encode loi: %s | %s", out_path.name, err)
    return ok


def encode_all_clips(
    infos: list, out_dir: Path,
    skip_existing: bool = True,
    progress_cb: Optional[Callable] = None,
    workers: int = None,
    stop_event: Optional[threading.Event] = None,
) -> list:
    """
    Pha 2: Encode toan bo clip.
    workers mac dinh = ENCODE_WORKERS (bao thu hon de khong nghen CPU).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    total   = len(infos)
    results = [None] * total
    w       = workers if workers is not None else ENCODE_WORKERS
    lock    = threading.Lock()

    def encode_one(i):
        if stop_event and stop_event.is_set():
            return i, None, False

        info = infos[i]
        if info is None:
            return i, None, False

        out_path = out_dir / f"clip_{i+1:03d}.mp4"
        skipped  = skip_existing and _clip_valid(out_path)

        if not skipped and not (stop_event and stop_event.is_set()):
            ok = _do_encode(info["raw_path"], info["speed"], out_path)
            if not ok:
                log.error("Encode that bai segment %d", i + 1)
                return i, None, False
            raw = Path(info["raw_path"])
            if raw.exists():
                raw.unlink(missing_ok=True)

        return i, {**info, "clip_path": out_path}, skipped

    if w <= 1:
        # Tuan tu: an toan nhat cho CPU
        for i in range(total):
            if stop_event and stop_event.is_set():
                break
            idx, result, skipped = encode_one(i)
            results[idx] = result
            if progress_cb and result is not None:
                progress_cb(idx + 1, total,
                            out_dir / f"clip_{idx+1:03d}.mp4", skipped)
    else:
        # Da luong co gioi han
        with ThreadPoolExecutor(max_workers=w) as ex:
            fmap = {ex.submit(encode_one, i): i for i in range(total)}
            for fut in as_completed(fmap):
                idx, result, skipped = fut.result()
                with lock:
                    results[idx] = result
                    done = sum(1 for r in results if r is not None)
                if progress_cb and result is not None:
                    progress_cb(done, total,
                                out_dir / f"clip_{idx+1:03d}.mp4", skipped)

    return [r for r in results if r is not None]


# ── adjust_clip_speed: giu API cu ────────────────────────────────────────────
def adjust_clip_speed(
    video_path: Path, start: float, duration: float,
    audio_dur: float, output_path: Path,
    skip_existing: bool = True,
) -> float:
    if audio_dur <= 0:
        raise ValueError(f"audio_dur phai > 0, nhan: {audio_dur}")
    raw   = duration / audio_dur
    speed = max(MIN_SPEED, min(MAX_SPEED, raw))
    if skip_existing and _clip_valid(output_path):
        return speed
    tmp = output_path.with_suffix(".cut.mp4")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not _do_cut(video_path, start, duration, tmp):
            raise RuntimeError(f"Cut that bai: {output_path.name}")
        if not _do_encode(tmp, speed, output_path):
            raise RuntimeError(f"Encode that bai: {output_path.name}")
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    log.info("Clip %s | start=%.2f dur=%.2f speed=%.3f [%s]",
             output_path.name, start, duration, speed, _ENCODER_LABEL)
    return speed


# ── batch_process: giu API cu ─────────────────────────────────────────────────
def batch_process(segments, audio_files, video_path=None, out_dir=None,
                  workers=None, skip_existing=True):
    import src.config as _cfg
    if video_path is None: video_path = _cfg.VIDEO_PATH
    if out_dir    is None: out_dir    = _cfg.ADJUSTED_CLIPS
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw"
    total   = len(segments)

    print(f"  Encoder      : {_ENCODER_LABEL}")
    print(f"  Encode workers: {ENCODE_WORKERS}")
    print(f"  CPU threads   : {_FFMPEG_CPU_THREADS} (tren {os.cpu_count()} core)")
    print(f"  Cut method    : double-ss + libx264 ultrafast (chinh xac, khong trung lap)")

    infos = cut_all_clips(
        segments, audio_files[:total], video_path, raw_dir,
        skip_existing=skip_existing,
        progress_cb=lambda d, t, n, s: print(
            f"  Cut [{d:03d}/{t:03d}] {'SKIP' if s else ' OK '}  {n}"),
    )
    results = encode_all_clips(
        infos, out_dir, skip_existing=skip_existing,
        progress_cb=lambda d, t, n, s: print(
            f"  Enc [{d:03d}/{t:03d}] {'SKIP' if s else ' OK '}  {n}"),
    )
    try:
        raw_dir.rmdir()
    except OSError:
        pass
    return results
