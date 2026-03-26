"""
capcut_client.py — Wrapper pycapcut (ghi thang vao CapCut Drafts, KHONG can server).

v2.1: Them phuong thuc compound_draft() de gop clip sau khi luu.
pip install pycapcut>=0.0.3
"""

import logging
from pathlib import Path

from pycapcut import DraftFolder
from pycapcut.local_materials import VideoMaterial, AudioMaterial
from pycapcut.video_segment import VideoSegment
from pycapcut.audio_segment import AudioSegment
from pycapcut.text_segment import TextSegment
from pycapcut.track import TrackType
from pycapcut.time_util import Timerange

log = logging.getLogger(__name__)

_US = 1_000_000  # so micro-giay trong 1 giay


def _us(seconds: float) -> int:
    """Chuyen doi giay -> micro-giay (don vi cua pycapcut)."""
    return int(seconds * _US)


class CapCutClient:
    """
    Wrapper pycapcut — ghi thang vao thu muc Drafts cua CapCut.
    Khong ket noi mang, khong can server.

    v2.1: Ho tro compound_draft() — gop clip bang can thiep JSON sau khi luu.
    """

    def __init__(self, drafts_dir: Path):
        self._drafts_dir = Path(drafts_dir)
        if not self._drafts_dir.is_dir():
            raise FileNotFoundError(
                f"Thu muc Drafts khong ton tai: {self._drafts_dir}\n"
                "Kiem tra lai cai dat CAPCUT_DRAFTS_DIR."
            )
        self._folder     = DraftFolder(str(self._drafts_dir))
        self._script     = None
        self._draft_name: str | None = None
        self._fps: int   = 30
        self._draft_path: Path | None = None  # duoc dat sau save_draft()
        log.info("pycapcut DraftFolder: %s", self._drafts_dir)

    # ── Compatibility shims ───────────────────────────────────────────────────

    def wait_for_server(self, *_, **__) -> bool:
        log.info("pycapcut mode: khong can server, bo qua kiem tra port.")
        return True

    ping = wait_for_server

    # ── Core API ──────────────────────────────────────────────────────────────

    def create_draft(self, name="AutoSync Draft",
                     width=1080, height=1920, fps=30) -> str:
        """Tao draft moi. Tra ve ten draft (dung lam draft_id)."""
        self._draft_name = name
        self._fps        = fps
        log.info("Tao draft: '%s' (%dx%d @ %d fps)", name, width, height, fps)

        self._script = self._folder.create_draft(
            draft_name=name,
            width=width,
            height=height,
            fps=fps,
            allow_replace=True,
        )
        self._script.add_track(TrackType.video)
        self._script.add_track(TrackType.audio)
        return name

    def build_timeline(self, draft_id: str, segments: list,
                       add_subtitles: bool = False) -> float:
        """
        Xay dung timeline tu danh sach segments.
        Moi segment can: clip_path, audio_path, audio_dur, text (optional).
        Tra ve tong thoi luong (giay).
        """
        if self._script is None:
            raise RuntimeError("Chua tao draft — goi create_draft() truoc.")

        if add_subtitles:
            self._script.add_track(TrackType.text)

        frame_us   = _US // (self._fps or 30)
        current_us = 0

        for i, seg in enumerate(segments):
            dur_us = _us(seg["audio_dur"])

            v_material = VideoMaterial(str(Path(seg["clip_path"]).resolve()))
            v_dur_us   = min(dur_us, v_material.duration)

            a_material = AudioMaterial(str(Path(seg["audio_path"]).resolve()))
            a_dur_us   = min(dur_us, a_material.duration)

            raw_dur    = min(v_dur_us, a_dur_us)
            seg_dur_us = (raw_dur // frame_us) * frame_us
            if seg_dur_us <= 0:
                seg_dur_us = frame_us

            self._script.add_segment(VideoSegment(
                material=v_material,
                target_timerange=Timerange(current_us, seg_dur_us),
                volume=0.0,
            ))
            self._script.add_segment(AudioSegment(
                material=a_material,
                target_timerange=Timerange(current_us, seg_dur_us),
                volume=1.0,
            ))

            if add_subtitles and seg.get("text"):
                self._script.add_segment(TextSegment(
                    text=seg["text"],
                    timerange=Timerange(current_us, seg_dur_us),
                ))

            current_us += seg_dur_us
            t_start = (current_us - seg_dur_us) / _US
            t_end   = current_us / _US
            print(f"  [timeline {i+1:03d}] "
                  f"t={t_start:.2f}s -> {t_end:.2f}s  "
                  f"| {Path(seg['audio_path']).name}")

        total_sec = current_us / _US
        log.info("Timeline hoan thanh. Tong: %.2fs", total_sec)
        return total_sec

    def save_draft(self, draft_id: str,
                   target_version: str = "3.9.0",
                   target_new_version: str = "110.0.0") -> Path:
        """
        Luu draft xuong dia. Tra ve duong dan thu muc draft.
        Sau khi goi ham nay, co the goi compound_draft() de gop clip.
        """
        if self._script is None:
            raise RuntimeError("Chua co draft nao de luu.")
        self._script.save()
        draft_path       = self._drafts_dir / (self._draft_name or draft_id)
        self._draft_path = draft_path          # luu lai de compound_draft dung
        log.info("Da luu draft tai: %s", draft_path)
        self._patch_version(draft_path, target_version, target_new_version)
        return draft_path

    # ── TINH NANG MOI: Compound Clip ─────────────────────────────────────────

    def compound_draft(self, mode: str, draft_path: Path = None) -> bool:
        """
        Gop toan bo clips thanh Compound Clip bang can thiep truc tiep JSON.
        Goi sau save_draft().

        mode:
            'none'  — Khong gop (bo qua)
            'video' — Gop chi Track Video
            'audio' — Gop chi Track Audio
            'mixed' — Gop ca Video + Audio (khuyen dung, gon nhat)

        draft_path: tu dong lay tu save_draft() neu de None.
        Tra ve True neu da ap dung, False neu mode='none'.
        """
        from src.capcut_compounder import apply_compound, COMPOUND_MODES

        path = Path(draft_path) if draft_path else self._draft_path
        if path is None:
            raise RuntimeError(
                "Chua biet draft_path — goi save_draft() truoc hoac truyen vao.")

        mode = (mode or "none").strip().lower()
        if mode not in COMPOUND_MODES:
            raise ValueError(
                f"mode khong hop le: '{mode}'. Chon trong: {COMPOUND_MODES}")

        if mode == "none":
            log.info("compound_draft: mode=none, bo qua.")
            return False

        log.info("compound_draft mode='%s' tren: %s", mode, path)
        applied = apply_compound(path, mode)
        if applied:
            log.info("compound_draft hoan tat.")
        return applied

    # ── Version patch ─────────────────────────────────────────────────────────

    @staticmethod
    def _patch_version(draft_path: Path, app_ver: str, new_ver: str):
        """Patch app_version / new_version trong draft_content.json."""
        json_file = draft_path / "draft_content.json"
        if not json_file.exists():
            log.warning("Khong tim thay draft_content.json: %s", json_file)
            return
        try:
            import re
            text = json_file.read_text(encoding="utf-8")
            text = re.sub(
                r'("app_version"\s*:\s*)"[^"]*"',
                lambda m: m.group(1) + '"' + app_ver + '"', text)
            text = re.sub(
                r'("new_version"\s*:\s*)"[^"]*"',
                lambda m: m.group(1) + '"' + new_ver + '"', text)
            json_file.write_text(text, encoding="utf-8")
            log.info("Patch version -> app=%s new=%s", app_ver, new_ver)
        except Exception as e:
            log.warning("Patch version that bai: %s", e)

    def install_to_capcut(self, *_, **__):
        log.info("pycapcut: draft da san sang (khong can copy).")
        return None

    def add_video(self, *_, **__): pass
    def add_audio(self, *_, **__): pass
    def add_text(self,  *_, **__): pass
