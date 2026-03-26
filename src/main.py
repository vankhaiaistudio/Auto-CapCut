"""
main.py — Auto CapCut Video Sync v2.1 (pycapcut edition)
Ghi thang vao CapCut Drafts — KHONG can server.
v2.1: Ho tro --compound {none|video|audio|mixed}
"""

import argparse, logging, sys, time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

import src.config as cfg
from src.video_processor import parse_srt, batch_process, collect_audio_files
from src.capcut_client   import CapCutClient


def _banner(msg):
    print("\n" + "-"*60)
    print(f"  {msg}")
    print("-"*60)


def _check_inputs():
    errors = []
    if not cfg.VIDEO_PATH.exists():
        errors.append(f"Khong tim thay video: {cfg.VIDEO_PATH}")
    if not cfg.SRT_PATH.exists():
        errors.append(f"Khong tim thay subtitle: {cfg.SRT_PATH}")
    audio_files = collect_audio_files(cfg.AUDIO_FOLDER)
    if not audio_files:
        errors.append(f"Khong co audio trong: {cfg.AUDIO_FOLDER}")
    if not cfg.CAPCUT_DRAFTS_DIR or not Path(cfg.CAPCUT_DRAFTS_DIR).is_dir():
        errors.append(
            f"Thu muc Drafts cua CapCut chua duoc cai dat.\n"
            f"  Trong CapCut: Settings → General → Draft Location\n"
            f"  Hoac dat bien moi truong CAPCUT_DRAFTS_DIR.")
    if errors:
        for e in errors: print(f"  [ERROR] {e}")
        sys.exit(1)
    return audio_files


def main(add_subtitles=False, dry_run=False, compound="none", **_):
    """
    Tham so:
        add_subtitles : them subtitle vao timeline
        dry_run       : chi kiem tra input, khong xu ly
        compound      : che do gop clip: 'none' | 'video' | 'audio' | 'mixed'
        **_           : bo qua tham so cu (copy_to_capcut, ...) de tuong thich
    """
    _banner("Auto CapCut Video Sync  v2.1  [pycapcut — no server]")
    t0 = time.perf_counter()

    # 1. Kiem tra input
    print("\nKiem tra input...")
    audio_files = _check_inputs()
    print(f"  Video       : {cfg.VIDEO_PATH}")
    print(f"  SRT         : {cfg.SRT_PATH}")
    print(f"  Audios      : {len(audio_files)} files")
    print(f"  Drafts dir  : {cfg.CAPCUT_DRAFTS_DIR}")
    print(f"  Compound    : {compound}")

    # 2. Parse SRT
    segments = parse_srt(cfg.SRT_PATH)
    print(f"  Segments    : {len(segments)}")
    if len(audio_files) < len(segments):
        print(f"[ERROR] Thieu audio: can {len(segments)}, co {len(audio_files)}")
        sys.exit(1)

    if dry_run:
        print("\nDRY RUN - Input hop le!")
        for i, seg in enumerate(segments):
            print(f"  [{i+1:03d}] {seg['start']:.2f}s | {audio_files[i].name}")
        sys.exit(0)

    # 3. Xu ly video clips (FFmpeg)
    cfg.ADJUSTED_CLIPS.mkdir(parents=True, exist_ok=True)
    _banner("Buoc 1/3 - Xu ly video clips (FFmpeg)")
    results = batch_process(
        segments=segments,
        audio_files=audio_files[:len(segments)],
        video_path=cfg.VIDEO_PATH,
        out_dir=cfg.ADJUSTED_CLIPS,
    )
    print(f"\n  Xong {len(results)} clips [{time.perf_counter()-t0:.1f}s]")

    # 4. Tao draft CapCut
    _banner("Buoc 2/3 - Tao draft CapCut (pycapcut)")
    draft_name = f"AutoSync_{cfg.SRT_PATH.stem}_{int(time.time())}"
    print(f"  Draft       : {draft_name}")
    print(f"  Luu tai     : {cfg.CAPCUT_DRAFTS_DIR}")

    client = CapCutClient(drafts_dir=cfg.CAPCUT_DRAFTS_DIR)
    client.create_draft(name=draft_name,
                        width=cfg.WIDTH, height=cfg.HEIGHT, fps=cfg.FPS)
    total_dur  = client.build_timeline(draft_id=draft_name,
                                       segments=results,
                                       add_subtitles=add_subtitles)
    draft_path = client.save_draft(draft_name)

    # 5. Ap dung Compound Clip (neu chon)
    if compound != "none":
        _banner(f"Buoc 3/3 - Ap dung Compound Clip (mode={compound})")
        try:
            applied = client.compound_draft(mode=compound)
            if applied:
                label = {
                    "video": "Compound Video",
                    "audio": "Compound Audio",
                    "both":  "Video + Audio (2 Compound rieng)",
                "mixed": "Mixed Compound (Video + Audio)",
                }.get(compound, compound)
                print(f"  ✓ Da gop thanh: {label}")
        except Exception as e:
            print(f"  [WARN] Compound that bai: {e}")
            print("         Draft van duoc luu binh thuong (chua gop clip).")
    else:
        _banner("Buoc 3/3 - (Bo qua Compound)")

    # Tong ket
    _banner("Hoan thanh!")
    print(f"  Clips       : {len(results)}")
    print(f"  Timeline    : {total_dur:.2f}s")
    print(f"  Draft       : {draft_path}")
    print(f"  Compound    : {compound}")
    print(f"  Thoi gian   : {time.perf_counter()-t0:.1f}s")
    print()
    print("  → Mo CapCut → Projects → tim ban nhap vua tao.")
    print("  (Neu chua thay: vao 1 draft khac roi quay lai)\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto CapCut Video Sync v2.1 — pycapcut edition")
    parser.add_argument("--subtitles", action="store_true",
                        help="Them subtitle vao timeline")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Chi kiem tra input, khong xu ly")
    parser.add_argument("--debug",     action="store_true",
                        help="Bat debug log")
    parser.add_argument(
        "--compound",
        choices=["none", "video", "audio", "both", "mixed"],
        default="none",
        metavar="MODE",
        help=(
            "Gop clip sau khi tao draft:\n"
            "  none  = Khong gop (mac dinh)\n"
            "  video = Gop chi Track Video\n"
            "  audio = Gop chi Track Audio\n"
            "  both  = 2 Compound rieng (Video + Audio doc lap)
  mixed = Gop ca Video + Audio vao 1 khoi (khuyen dung)"
        ),
    )
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    main(add_subtitles=args.subtitles,
         dry_run=args.dry_run,
         compound=args.compound)