"""
draft_editor.py — Post-processing tren draft_content.json sau pycapcut.

3 tinh nang doc lap, co the dung rieng le hoac ket hop:
  1. apply_subtitle_style  — Ap dung dong nhat font/mau/vi tri cho 50 subtitle
  2. add_intro_outro       — Chen Intro truoc / Outro sau noi dung chinh
  3. add_logo              — Them Logo PNG overlay tren track rieng

Tat ca can thiep truc tiep vao draft_content.json, khong can mo CapCut.
Goi DraftEditor.apply_all(config) roi .save() la xong.
"""

import json
import uuid
import copy
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_US = 1_000_000          # micro-giay
_PHOTO_DURATION_US = 10_800 * _US   # 3 gio — CapCut dung cho anh tinh

try:
    from src.config import FFPROBE_BIN
except ImportError:
    FFPROBE_BIN = "ffprobe"


# ── Tien ich ─────────────────────────────────────────────────────────────────

def _gen_id() -> str:
    return str(uuid.uuid4()).upper()


def _hex_to_rgb01(hex_color: str) -> list:
    """'#F0FF00' -> [0.941, 1.0, 0.0]"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return [round(r/255, 8), round(g/255, 8), round(b/255, 8)]


def _rgb01_to_hex(rgb: list) -> str:
    """[0.941, 1.0, 0.0] -> '#F0FF00'"""
    r, g, b = [min(255, max(0, int(x * 255))) for x in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def _get_media_info(path: Path) -> tuple:
    """
    Tra ve (duration_s, width_px, height_px) bang ffprobe.
    Neu la anh (ko co stream video thuc su), duration = 10800s.
    """
    try:
        r = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=15)
        info = json.loads(r.stdout)
    except Exception as e:
        log.warning("ffprobe loi voi %s: %s", path.name, e)
        return 0.0, 0, 0

    duration = float(info.get("format", {}).get("duration", 0))
    width = height = 0
    for st in info.get("streams", []):
        if st.get("codec_type") == "video":
            width  = st.get("width",  0)
            height = st.get("height", 0)
            # Anh tinh: ffprobe bao duration = 0 hoac rat lon
            if duration <= 0 or duration > 86400:
                duration = _PHOTO_DURATION_US / _US
            break

    return duration, width, height


def _font_title_from_path(font_path: str) -> str:
    """
    Tu dong suy ra ten hien thi cua font tu ten file.
    'AntonSC-Regular.ttf' -> 'Anton SC Regular'
    'Roboto-BoldItalic.ttf' -> 'Roboto Bold Italic'
    """
    stem = Path(font_path).stem          # bỏ .ttf
    # Tach theo '-' hoac '_'
    parts = stem.replace("_", "-").split("-")
    # Them khoang trang truoc chu hoa giua tu (CamelCase)
    expanded = []
    for part in parts:
        out = ""
        for i, ch in enumerate(part):
            if ch.isupper() and i > 0 and part[i-1].islower():
                out += " "
            out += ch
        expanded.append(out)
    return " ".join(expanded)


# ── Material factories ────────────────────────────────────────────────────────

def _make_speed(speed_id: str) -> dict:
    return {"curve_speed": None, "id": speed_id,
            "mode": 0, "speed": 1.0, "type": "speed"}


def _make_canvas(canvas_id: str) -> dict:
    return {"album_image": "", "blur": 0.0, "color": "",
            "id": canvas_id, "image": "", "image_id": "",
            "image_name": "", "source_platform": 0,
            "team_id": "", "type": "canvas_color"}


def _make_scm(scm_id: str) -> dict:
    return {"audio_channel_mapping": 0, "id": scm_id}


def _make_vocal_sep(vs_id: str) -> dict:
    return {"choice": 0, "id": vs_id,
            "production_path": "", "removed_audio_path": "",
            "time_range": None}


def _make_sticker_anim(anim_id: str) -> dict:
    return {"animations": [], "id": anim_id,
            "multi_language_current": "none", "type": "sticker_animation"}


def _make_video_material(mat_id: str, path: Path,
                          duration_s: float, width: int, height: int,
                          is_photo: bool = False) -> dict:
    dur_us = int(duration_s * _US)
    return {
        "aigc_type": "none", "audio_fade": None, "cartoon_path": "",
        "category_id": "", "category_name": "", "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0,  "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0,  "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free", "crop_scale": 1.0,
        "duration": dur_us,
        "extra_type_option": 0, "formula_id": "", "freeze": None,
        "has_audio": not is_photo,
        "height": height, "id": mat_id,
        "intensifies_audio_path": "", "intensifies_path": "",
        "is_ai_generate_content": False, "is_copyright": True,
        "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
        "local_id": "", "local_material_id": "", "material_id": "",
        "material_name": path.stem, "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False,
                    "has_use_quick_eraser": False,
                    "interactiveTime": [], "path": "", "strokes": []},
        "media_path": "", "object_locked": None, "origin_material_id": "",
        "path": str(path),
        "picture_from": "none",
        "picture_set_category_id": "", "picture_set_category_name": "",
        "request_id": "", "reverse_intensifies_path": "", "reverse_path": "",
        "smart_motion": None, "source": 0, "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0,
                   "time_range": {"duration": 0, "start": 0}},
        "team_id": "",
        "type": "photo" if is_photo else "video",
        "video_algorithm": {
            "algorithms": [], "complement_frame_config": None,
            "deflicker": None, "gameplay_configs": [],
            "motion_blur_config": None, "noise_reduction": None,
            "path": "", "quality_enhance": None, "time_range": None,
        },
        "width": width,
    }


def _make_video_segment(seg_id: str, mat_id: str,
                         extra_refs: list,
                         target_start: int, target_dur: int,
                         source_start: int = 0, source_dur: int = None,
                         scale_x: float = 1.0, scale_y: float = 1.0,
                         tx: float = 0.0, ty: float = 0.0,
                         volume: float = 1.0) -> dict:
    if source_dur is None:
        source_dur = target_dur
    return {
        "caption_info": None, "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": scale_x, "y": scale_y},
            "transform": {"x": tx, "y": ty},
        },
        "common_keyframes": [],
        "enable_adjust": True, "enable_color_correct_adjust": False,
        "enable_color_curves": True, "enable_color_match_adjust": False,
        "enable_color_wheels": True, "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": extra_refs,
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": seg_id, "intensifies_audio": False,
        "is_placeholder": False, "is_tone_modify": False,
        "keyframe_refs": [], "last_nonzero_volume": 1.0,
        "material_id": mat_id, "render_index": 0,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0,
        },
        "reverse": False,
        "source_timerange": {"duration": source_dur, "start": source_start},
        "speed": 1.0,
        "target_timerange": {"duration": target_dur, "start": target_start},
        "template_id": "", "template_scene": "default",
        "track_attribute": 0, "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True, "volume": volume,
    }


# ═════════════════════════════════════════════════════════════════════════════
class DraftEditor:
    """
    Doc va chinh sua draft_content.json sau khi pycapcut tao ra.

    Cach dung:
        ed = DraftEditor(draft_path / "draft_content.json")
        ed.apply_subtitle_style(config)
        ed.add_intro_outro(config)
        ed.add_logo(config)
        ed.save()

    Moi method tra ve self de co the chain.
    """

    def __init__(self, json_path: Path):
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            raise FileNotFoundError(f"Khong tim thay: {self.json_path}")
        with self.json_path.open("r", encoding="utf-8") as f:
            self.data = json.load(f)
        # Cache
        self._intro_dur_us = 0   # duoc set boi add_intro_outro
        self._outro_dur_us = 0
        log.info("DraftEditor load: %s", self.json_path.name)

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(self, output_path: Path = None) -> Path:
        out = Path(output_path) if output_path else self.json_path
        with out.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, separators=(",", ":"))
        log.info("DraftEditor saved: %s", out)
        return out

    # ── Helper: tim main video track ─────────────────────────────────────────

    def _main_video_track(self) -> dict:
        """Tim video track co nhieu segment nhat."""
        best = None
        for t in self.data.get("tracks", []):
            if t["type"] == "video":
                if best is None or len(t["segments"]) > len(best["segments"]):
                    best = t
        if best is None:
            raise ValueError("Khong tim thay video track nao trong draft.")
        return best

    def _add_extras_video(self) -> list:
        """Them speed/canvas/scm/vocal_sep, tra ve [sp, ca, sc, vs] IDs."""
        mats = self.data.setdefault("materials", {})
        sp, ca, sc, vs = _gen_id(), _gen_id(), _gen_id(), _gen_id()
        mats.setdefault("speeds",                []).append(_make_speed(sp))
        mats.setdefault("canvases",              []).append(_make_canvas(ca))
        mats.setdefault("sound_channel_mappings",[]).append(_make_scm(sc))
        mats.setdefault("vocal_separations",     []).append(_make_vocal_sep(vs))
        return [sp, ca, sc, vs]

    def _add_extras_photo(self) -> list:
        """Them speed/canvas/anim/scm/vocal_sep cho anh (5 refs)."""
        mats = self.data.setdefault("materials", {})
        sp, ca, an, sc, vs = (_gen_id(), _gen_id(), _gen_id(),
                               _gen_id(), _gen_id())
        mats.setdefault("speeds",                []).append(_make_speed(sp))
        mats.setdefault("canvases",              []).append(_make_canvas(ca))
        mats.setdefault("material_animations",   []).append(_make_sticker_anim(an))
        mats.setdefault("sound_channel_mappings",[]).append(_make_scm(sc))
        mats.setdefault("vocal_separations",     []).append(_make_vocal_sep(vs))
        return [sp, ca, an, sc, vs]

    # =========================================================================
    # TINH NANG 1: AP DUNG STYLE PHU DE
    # =========================================================================

    def apply_subtitle_style(self, cfg: dict) -> "DraftEditor":
        """
        Ap dung dong nhat style cho tat ca subtitle segments tren text tracks.

        cfg dict keys:
            font_path      : str  — duong dan den file .ttf/.otf
            font_title     : str  — ten hien thi (co the de '' de tu suy ra)
            text_color     : str  — hex '#F0FF00'
            stroke_color   : str  — hex '#000000'
            stroke_width   : float — 0.0 = tat vien
            pos_y          : float — -1.0 (duoi) -> 1.0 (tren)
            pos_x          : float — mac dinh 0.0 (giua)
            scale          : float — scale cua segment clip
            line_max_width : float — 0.0-1.0
            alignment      : int   — 0=trai 1=giua 2=phai
        """
        font_path  = cfg.get("font_path", "")
        font_title = cfg.get("font_title", "") or _font_title_from_path(font_path)
        text_color    = cfg.get("text_color",   "#FFFFFF").upper()
        stroke_color  = cfg.get("stroke_color", "#000000").upper()
        stroke_width  = float(cfg.get("stroke_width", 0.06))
        font_size     = float(cfg.get("font_size",    5.0))   # CapCut internal unit
        pos_y         = float(cfg.get("pos_y",  -0.893))
        pos_x         = float(cfg.get("pos_x",   0.0))
        scale         = float(cfg.get("scale",   1.0))
        line_max_width= float(cfg.get("line_max_width", 0.82))
        alignment     = int(cfg.get("alignment",  1))

        tc_rgb = _hex_to_rgb01(text_color)
        sc_rgb = _hex_to_rgb01(stroke_color)

        # Tap hop material_id cua tat ca text segments
        text_mat_ids = set()
        for track in self.data.get("tracks", []):
            if track["type"] == "text":
                for seg in track["segments"]:
                    text_mat_ids.add(seg["material_id"])

        n_updated = 0
        for mat in self.data.get("materials", {}).get("texts", []):
            if mat["id"] not in text_mat_ids:
                continue

            # ── Cap nhat top-level fields ─────────────────────────────
            mat["font_path"]    = font_path
            mat["font_title"]   = font_title
            mat["font_id"]      = ""
            mat["font_size"]    = font_size        # top-level font_size
            mat["text_color"]   = text_color.lower()
            mat["border_color"] = stroke_color.lower()
            mat["border_width"] = stroke_width
            mat["alignment"]    = alignment
            mat["line_max_width"] = line_max_width

            # ── Cap nhat content JSON (cau truc style ben trong) ─────
            try:
                c = json.loads(mat.get("content", "{}"))
                for st in c.get("styles", []):
                    st["font"] = {"path": font_path, "id": ""}
                    st["size"] = font_size             # size ben trong content JSON
                    st.setdefault("fill", {})["content"] = {
                        "solid": {"color": tc_rgb}
                    }
                    if stroke_width > 0:
                        st["strokes"] = [{
                            "content": {"solid": {"color": sc_rgb}},
                            "width": stroke_width,
                        }]
                    else:
                        st["strokes"] = []
                mat["content"] = json.dumps(c, ensure_ascii=False,
                                             separators=(",", ":"))
            except Exception as e:
                log.warning("Parse content JSON loi (mat %s): %s",
                             mat["id"][:8], e)

            n_updated += 1

        # ── Cap nhat vi tri va scale tren tung segment ────────────────
        for track in self.data.get("tracks", []):
            if track["type"] == "text":
                for seg in track["segments"]:
                    clip = seg.setdefault("clip", {})
                    clip.setdefault("transform", {})["y"] = pos_y
                    clip.setdefault("transform", {})["x"] = pos_x
                    clip.setdefault("scale", {})["x"] = scale
                    clip.setdefault("scale", {})["y"] = scale

        log.info("apply_subtitle_style: %d materials updated. "
                 "font='%s' color=%s pos_y=%.3f scale=%.3f",
                 n_updated, font_title, text_color, pos_y, scale)
        return self

    # =========================================================================
    # TINH NANG 2: THEM INTRO / OUTRO
    # =========================================================================

    def add_intro_outro(self, cfg: dict) -> "DraftEditor":
        """
        Chen Intro truoc va Outro sau toan bo noi dung.

        cfg dict keys:
            intro_path : str  — duong dan video intro
            outro_path : str  — duong dan video outro
            (duration tu dong detect bang ffprobe)

        Tac dong:
        - DICH CHUYEN tat ca segments tren tat ca track len +intro_dur
        - Them segment intro dau track video chinh
        - Them segment outro cuoi track video chinh
        - Cap nhat data['duration']
        """
        intro_path = Path(cfg["intro_path"])
        outro_path = Path(cfg["outro_path"])

        intro_dur, intro_w, intro_h = _get_media_info(intro_path)
        outro_dur, outro_w, outro_h = _get_media_info(outro_path)

        if intro_dur <= 0:
            raise ValueError(f"Khong doc duoc duration cua intro: {intro_path}")
        if outro_dur <= 0:
            raise ValueError(f"Khong doc duoc duration cua outro: {outro_path}")

        intro_us = int(intro_dur * _US)
        outro_us = int(outro_dur * _US)
        self._intro_dur_us = intro_us
        self._outro_dur_us = outro_us

        # Dich chuyen TAT CA segments tren TAT CA tracks
        for track in self.data.get("tracks", []):
            for seg in track.get("segments", []):
                seg["target_timerange"]["start"] += intro_us

        # Tim main video track (nhieu seg nhat)
        main_track = self._main_video_track()

        # Them intro material + segment
        intro_mat_id = _gen_id()
        self.data.setdefault("materials", {}).setdefault("videos", []).append(
            _make_video_material(intro_mat_id, intro_path,
                                  intro_dur, intro_w, intro_h))
        intro_refs = self._add_extras_video()
        intro_seg = _make_video_segment(
            _gen_id(), intro_mat_id, intro_refs,
            target_start=0, target_dur=intro_us,
            source_start=0, source_dur=intro_us)
        main_track["segments"].insert(0, intro_seg)

        # Tinh diem cuoi hien tai (sau khi da dich)
        content_end = max(
            s["target_timerange"]["start"] + s["target_timerange"]["duration"]
            for t in self.data["tracks"]
            for s in t.get("segments", [])
        )

        # Them outro material + segment
        outro_mat_id = _gen_id()
        self.data.setdefault("materials", {}).setdefault("videos", []).append(
            _make_video_material(outro_mat_id, outro_path,
                                  outro_dur, outro_w, outro_h))
        outro_refs = self._add_extras_video()
        outro_seg = _make_video_segment(
            _gen_id(), outro_mat_id, outro_refs,
            target_start=content_end, target_dur=outro_us,
            source_start=0, source_dur=outro_us)
        main_track["segments"].append(outro_seg)

        # Cap nhat tong duration
        self.data["duration"] = content_end + outro_us

        log.info("add_intro_outro: intro=%.2fs outro=%.2fs | "
                 "draft_duration=%.2fs",
                 intro_dur, outro_dur,
                 self.data["duration"] / _US)
        return self

    # =========================================================================
    # TINH NANG 3: THEM LOGO OVERLAY
    # =========================================================================

    def add_logo(self, cfg: dict) -> "DraftEditor":
        """
        Them logo PNG tren 1 track video rieng.

        cfg dict keys:
            logo_path  : str   — duong dan PNG (nen xoa)
            scale      : float — 0.0-1.0, kich co tuong doi
            pos_x      : float — -1.0 (trai) -> 1.0 (phai)
            pos_y      : float — -1.0 (duoi) -> 1.0 (tren)
            timeline   : str   — 'content' (bo Intro/Outro) | 'full' (ca video)

        Logo duoc dat tren track video co thu tu cao nhat (render_index cao).
        """
        logo_path  = Path(cfg["logo_path"])
        scale      = float(cfg.get("scale",   0.453))
        pos_x      = float(cfg.get("pos_x",  -0.808))
        pos_y      = float(cfg.get("pos_y",   0.805))
        timeline   = cfg.get("timeline", "content")

        logo_dur_s, logo_w, logo_h = _get_media_info(logo_path)
        # Anh tinh: dung toi da 3 gio (CapCut convention)
        if logo_dur_s <= 0 or logo_dur_s > 86400:
            logo_dur_s = _PHOTO_DURATION_US / _US

        logo_mat_dur_us = int(logo_dur_s * _US)

        # Tinh khung thoi gian hien thi logo
        if timeline == "content":
            # Hien thi tu sau Intro den truoc Outro
            logo_start = self._intro_dur_us
            logo_end   = self.data.get("duration", 0) - self._outro_dur_us
            if logo_end <= logo_start:
                # Fallback: toan bo
                logo_start = 0
                logo_end   = self.data.get("duration", 0)
        else:
            logo_start = 0
            logo_end   = self.data.get("duration", 0)

        logo_timeline_dur = logo_end - logo_start
        # Source: lay phan dau file logo, khong vuot qua duration logo
        logo_source_dur = min(logo_timeline_dur, logo_mat_dur_us)

        # Them logo material vao materials.videos
        logo_mat_id = _gen_id()
        self.data.setdefault("materials", {}).setdefault("videos", []).append(
            _make_video_material(logo_mat_id, logo_path,
                                  logo_dur_s, logo_w, logo_h,
                                  is_photo=True))

        # Them extras (5 refs cho photo)
        logo_refs = self._add_extras_photo()

        # Tao segment logo
        logo_seg = _make_video_segment(
            _gen_id(), logo_mat_id, logo_refs,
            target_start=logo_start, target_dur=logo_timeline_dur,
            source_start=0, source_dur=logo_source_dur,
            scale_x=scale, scale_y=scale,
            tx=pos_x, ty=pos_y, volume=0.0)

        # Them track moi cho logo
        logo_track = {
            "attribute":       0,
            "flag":            0,
            "id":              _gen_id(),
            "is_default_name": True,
            "name":            "",
            "segments":        [logo_seg],
            "type":            "video",
        }
        self.data.setdefault("tracks", []).append(logo_track)

        log.info("add_logo: '%s' scale=%.3f pos=(%.3f,%.3f) "
                 "timeline=%s (%.2fs-%.2fs)",
                 logo_path.name, scale, pos_x, pos_y,
                 timeline, logo_start/_US, logo_end/_US)
        return self

    # ── apply_all: ap dung theo dict config ──────────────────────────────────

    def apply_all(self, config: dict) -> "DraftEditor":
        """
        Ap dung tat ca tinh nang duoc bat trong config.

        config = {
            "sub_style":   {"enabled": True/False, ...},
            "intro_outro": {"enabled": True/False, "intro_path":..., "outro_path":...},
            "logo":        {"enabled": True/False, "logo_path":..., ...},
        }

        Thu tu ap dung QUAN TRONG:
          1. sub_style   (khong anh huong timeline)
          2. intro_outro (dich chuyen timeline)
          3. logo        (phu thuoc intro_dur, outro_dur de tinh khung thoi gian)
        """
        if config.get("sub_style", {}).get("enabled"):
            self.apply_subtitle_style(config["sub_style"])
        if config.get("intro_outro", {}).get("enabled"):
            self.add_intro_outro(config["intro_outro"])
        if config.get("logo", {}).get("enabled"):
            self.add_logo(config["logo"])
        return self


# ── Ham tien ich nhanh ────────────────────────────────────────────────────────

def auto_edit(draft_path: Path, config: dict) -> bool:
    """
    Tien ich nhanh: load JSON, ap dung config, save.
    Tra ve True neu co it nhat 1 tinh nang duoc ap dung.
    """
    any_enabled = any(
        v.get("enabled") for v in config.values()
        if isinstance(v, dict))
    if not any_enabled:
        return False
    json_file = Path(draft_path) / "draft_content.json"
    editor = DraftEditor(json_file)
    editor.apply_all(config)
    editor.save()
    return True