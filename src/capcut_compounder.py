"""
capcut_compounder.py — Tu dong gop clip thanh Compound Clip tren CapCut PC.
v2.2: Fix toan bo dua tren phan tich JSON thuc te tu CapCut PC.

5 bug da sua:
  1. has_audio=True LUON LUON tren Video Dummy (ke ca video-only)
  2. Inner track co ID MOI (segment giu ID cu)
  3. Compound audio: inner project = [empty_video_track, audio_track]
  4. Mixed: XOA HOAN TOAN track audio khoi outer array (khong chi empty)
  5. Mini project co update_time=0, version=360000 + materials.drafts=[]
"""

import json
import uuid
import copy
import logging
from pathlib import Path

log = logging.getLogger(__name__)

COMPOUND_MODES = ("none", "video", "audio", "mixed", "both")


def gen_id() -> str:
    return str(uuid.uuid4()).upper()


def _make_track(track_type: str, segments: list) -> dict:
    """
    Tao track voi ID MOI.
    Segment duoc truyen vao nguyen xi (da deep-copy tu noi goi).
    """
    return {
        "attribute":       0,
        "flag":            0,
        "id":              gen_id(),
        "is_default_name": True,
        "name":            "",
        "segments":        segments,
        "type":            track_type,
    }


class CapCutCompounder:
    def __init__(self, json_path: Path):
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            raise FileNotFoundError(f"Khong tim thay: {self.json_path}")
        with self.json_path.open("r", encoding="utf-8") as f:
            self.data = json.load(f)
        log.info("Doc draft_content.json (%d tracks)", len(self.data.get("tracks", [])))

    def save(self, output_path: Path = None) -> Path:
        out = Path(output_path) if output_path else self.json_path
        with out.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, separators=(",", ":"))
        log.info("Da luu: %s", out)
        return out

    def _find_track(self, track_type: str) -> tuple:
        """Tim track co nhieu segment nhat voi type cho truoc."""
        best_idx, best_track = None, None
        for i, t in enumerate(self.data.get("tracks", [])):
            if t.get("type") == track_type and t.get("segments"):
                if best_track is None or len(t["segments"]) > len(best_track["segments"]):
                    best_idx, best_track = i, t
        if best_track is None:
            raise ValueError(f"Khong tim thay track type='{track_type}' co segments.")
        return best_idx, best_track

    def _create_mini_project(self, compound_tracks, total_duration,
                              combination_id, combination_material_id):
        """
        Tao mini project va day vao materials.drafts.
        - materials.drafts = [] trong inner project (tranh long cap)
        - Co update_time=0 va version=360000 (chuan CapCut thuc te)
        """
        canvas = copy.deepcopy(
            self.data.get("canvas_config",
                          {"height": 1920, "ratio": "9:16", "width": 1080}))

        inner_materials = copy.deepcopy(self.data.get("materials", {}))
        inner_materials["drafts"] = []   # XOA LONG CAP

        mini = {
            "canvas_config":             canvas,
            "color_space":               self.data.get("color_space", 0),
            "config":                    copy.deepcopy(self.data.get("config", {})),
            "cover":                     None,
            "create_time":               0,
            "duration":                  total_duration,
            "extra_info":                None,
            "fps":                       self.data.get("fps", 30.0),
            "free_render_index_mode_on": False,
            "group_container":           None,
            "id":                        gen_id(),
            "keyframe_graph_list":       [],
            "keyframes": {
                "adjusts": [], "audios": [], "effects": [], "filters": [],
                "handwrites": [], "stickers": [], "texts": [], "videos": [],
            },
            "last_modified_platform":    copy.deepcopy(
                self.data.get("last_modified_platform", {})),
            "materials":                 inner_materials,
            "mutable_config":            None,
            "name":                      "",
            "new_version":               self.data.get("new_version", "110.0.0"),
            "platform":                  copy.deepcopy(self.data.get("platform", {})),
            "relationships":             [],
            "render_index_track_mode_on": True,
            "retouch_cover":             None,
            "source":                    "default",
            "static_cover_image_path":   "",
            "time_marks":                None,
            "tracks":                    compound_tracks,
            "update_time":               0,      # co trong CapCut thuc te
            "version":                   360000, # co trong CapCut thuc te
        }

        mats = self.data.setdefault("materials", {})
        mats.setdefault("drafts", []).append({
            "category_id":            "",
            "category_name":          "",
            "combination_id":         combination_id,
            "draft":                  mini,
            "formula_id":             "",
            "id":                     combination_material_id,
            "name":                   "",
            "precompile_combination": False,
            "type":                   "combination",
        })

    def _make_video_dummy(self, dummy_id, total_duration, name="Compound clip"):
        """
        Dummy video. has_audio=True LUON LUON theo thuc te CapCut PC
        (ke ca khi chi compound video, khong co audio).
        """
        w = self.data.get("canvas_config", {}).get("width",  1080)
        h = self.data.get("canvas_config", {}).get("height", 1920)
        self.data.setdefault("materials", {}).setdefault("videos", []).append({
            "aigc_type": "none", "audio_fade": None, "cartoon_path": "",
            "category_id": "", "category_name": "", "check_flag": 63487,
            "crop": {
                "lower_left_x": 0.0,  "lower_left_y": 1.0,
                "lower_right_x": 1.0, "lower_right_y": 1.0,
                "upper_left_x": 0.0,  "upper_left_y": 0.0,
                "upper_right_x": 1.0, "upper_right_y": 0.0,
            },
            "crop_ratio": "free", "crop_scale": 1.0,
            "duration": total_duration,
            "extra_type_option": 2,   # Co hieu compound video
            "formula_id": "", "freeze": None,
            "has_audio": True,        # LUON True theo CapCut thuc te
            "height": h, "id": dummy_id,
            "intensifies_audio_path": "", "intensifies_path": "",
            "is_ai_generate_content": False, "is_copyright": True,
            "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
            "local_id": "", "local_material_id": "", "material_id": "",
            "material_name": name, "material_url": "",
            "matting": {
                "flag": 0, "has_use_quick_brush": False,
                "has_use_quick_eraser": False,
                "interactiveTime": [], "path": "", "strokes": [],
            },
            "media_path": "", "object_locked": None, "origin_material_id": "",
            "path": "",  # rong = dummy
            "picture_from": "none", "picture_set_category_id": "",
            "picture_set_category_name": "", "request_id": "",
            "reverse_intensifies_path": "", "reverse_path": "",
            "smart_motion": None, "source": 0, "source_platform": 0,
            "stable": {
                "matrix_path": "", "stable_level": 0,
                "time_range": {"duration": 0, "start": 0},
            },
            "team_id": "", "type": "video",
            "video_algorithm": {
                "algorithms": [], "complement_frame_config": None,
                "deflicker": None, "gameplay_configs": [],
                "motion_blur_config": None, "noise_reduction": None,
                "path": "", "quality_enhance": None, "time_range": None,
            },
            "width": w,
        })

    def _make_audio_dummy(self, dummy_id, total_duration, name="Compound clip"):
        """Dummy audio. type='music' bat buoc."""
        self.data.setdefault("materials", {}).setdefault("audios", []).append({
            "app_id": 0, "category_id": "", "category_name": "",
            "check_flag": 1, "copyright_limit_type": "none",
            "duration": total_duration, "effect_id": "", "formula_id": "",
            "id": dummy_id, "intensifies_path": "",
            "is_ai_clone_tone": False, "is_text_edit_overdub": False,
            "is_ugc": False, "local_material_id": "", "music_id": "",
            "name": name,
            "path": "",  # rong = dummy
            "query": "", "request_id": "", "resource_id": "",
            "search_id": "", "source_from": "", "source_platform": 0,
            "team_id": "", "text_id": "", "tone_category_id": "",
            "tone_category_name": "", "tone_effect_id": "",
            "tone_effect_name": "", "tone_platform": "",
            "tone_second_category_id": "", "tone_second_category_name": "",
            "tone_speaker": "", "tone_type": "",
            "type": "music",  # bat buoc "music" khong phai "audio"
            "video_id": "", "wave_points": [],
        })

    def _make_segment(self, seg_id, dummy_id, combo_mat_id,
                      total_duration, global_start, is_video):
        return {
            "caption_info": None, "cartoon": False,
            "clip": {
                "alpha": 1.0,
                "flip": {"horizontal": False, "vertical": False},
                "rotation": 0.0,
                "scale": {"x": 1.0, "y": 1.0},
                "transform": {"x": 0.0, "y": 0.0},
            } if is_video else None,
            "common_keyframes": [],
            "enable_adjust": is_video,
            "enable_color_correct_adjust": False,
            "enable_color_curves": True,
            "enable_color_match_adjust": False,
            "enable_color_wheels": True,
            "enable_lut": is_video,
            "enable_smart_color_adjust": False,
            "extra_material_refs": [
                combo_mat_id,   # [0] = tro den mini project
                gen_id(), gen_id(), gen_id(), gen_id(),  # [1-4] placeholder
            ],
            "group_id": "",
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000} if is_video else None,
            "id": seg_id, "intensifies_audio": False,
            "is_placeholder": False, "is_tone_modify": False,
            "keyframe_refs": [], "last_nonzero_volume": 1.0,
            "material_id": dummy_id, "render_index": 0,
            "responsive_layout": {
                "enable": False, "horizontal_pos_layout": 0,
                "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0,
            },
            "reverse": False,
            "source_timerange": {"duration": total_duration, "start": 0},
            "speed": 1.0,
            "target_timerange": {"duration": total_duration, "start": global_start},
            "template_id": "", "template_scene": "default",
            "track_attribute": 0, "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0} if is_video else None,
            "visible": True, "volume": 1.0,
        }

    # ─── Option 1: Video only ─────────────────────────────────────────────────

    def compound_video_only(self) -> "CapCutCompounder":
        v_idx, v_track = self._find_track("video")
        segs = v_track["segments"]

        g_start = segs[0]["target_timerange"]["start"]
        g_end   = segs[-1]["target_timerange"]["start"] + segs[-1]["target_timerange"]["duration"]
        total   = g_end - g_start

        dummy_id = gen_id(); combo_id = gen_id()
        combo_mat_id = gen_id(); seg_id = gen_id()

        inner_segs = copy.deepcopy(segs)
        for s in inner_segs:
            s["target_timerange"]["start"] -= g_start

        # Inner project: chi 1 track video
        self._create_mini_project([_make_track("video", inner_segs)],
                                   total, combo_id, combo_mat_id)
        self._make_video_dummy(dummy_id, total, "Compound clip")
        v_track["segments"] = [
            self._make_segment(seg_id, dummy_id, combo_mat_id, total, g_start, True)
        ]
        log.info("compound_video_only: %d -> 1 (dur=%d us)", len(segs), total)
        return self

    # ─── Option 2: Audio only ─────────────────────────────────────────────────

    def compound_audio_only(self) -> "CapCutCompounder":
        a_idx, a_track = self._find_track("audio")
        segs = a_track["segments"]

        g_start = segs[0]["target_timerange"]["start"]
        g_end   = segs[-1]["target_timerange"]["start"] + segs[-1]["target_timerange"]["duration"]
        total   = g_end - g_start

        dummy_id = gen_id(); combo_id = gen_id()
        combo_mat_id = gen_id(); seg_id = gen_id()

        inner_segs = copy.deepcopy(segs)
        for s in inner_segs:
            s["target_timerange"]["start"] -= g_start

        # Inner project: [empty_video_placeholder, audio_track]
        # Day la cau truc chuan CapCut cho compound audio (da verify)
        self._create_mini_project(
            [_make_track("video", []),           # empty video placeholder
             _make_track("audio", inner_segs)],  # audio voi segments
            total, combo_id, combo_mat_id)

        self._make_audio_dummy(dummy_id, total, "Compound clip")
        a_track["segments"] = [
            self._make_segment(seg_id, dummy_id, combo_mat_id, total, g_start, False)
        ]
        log.info("compound_audio_only: %d -> 1 (dur=%d us)", len(segs), total)
        return self

    # ─── Option 3: Mixed ──────────────────────────────────────────────────────

    def compound_mixed(self) -> "CapCutCompounder":
        v_idx, v_track = self._find_track("video")
        a_idx, a_track = self._find_track("audio")

        all_segs = v_track["segments"] + a_track["segments"]
        g_start  = min(s["target_timerange"]["start"] for s in all_segs)
        g_end    = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                       for s in all_segs)
        total    = g_end - g_start

        dummy_id = gen_id(); combo_id = gen_id()
        combo_mat_id = gen_id(); seg_id = gen_id()

        inner_v = copy.deepcopy(v_track["segments"])
        for s in inner_v: s["target_timerange"]["start"] -= g_start
        inner_a = copy.deepcopy(a_track["segments"])
        for s in inner_a: s["target_timerange"]["start"] -= g_start

        self._create_mini_project(
            [_make_track("video", inner_v),
             _make_track("audio", inner_a)],
            total, combo_id, combo_mat_id)

        self._make_video_dummy(dummy_id, total, "Compound clip")
        v_track["segments"] = [
            self._make_segment(seg_id, dummy_id, combo_mat_id, total, g_start, True)
        ]

        # XOA HOAN TOAN track audio (KHONG chi empty — da verify tu file 3)
        n_a = len(a_track["segments"])
        self.data["tracks"].pop(a_idx)
        log.info("compound_mixed: v=%d a=%d -> 1 Mixed, audio track removed (dur=%d us)",
                 len(inner_v), n_a, total)
        return self


    # ─── Option 4: Both (Video + Audio rieng le) ─────────────────────────────

    def compound_both(self) -> "CapCutCompounder":
        """
        Tao 2 compound rieng biet trong cung 1 draft:
          - 1 Compound Video (track video chinh)
          - 1 Compound Audio (track audio chinh)

        Ket qua: materials.drafts co 2 entries doc lap.
        Moi track tro dung vao draft cua chinh no qua extra_refs[0].
        (Da verify tu file thuc te CapCut PC)
        """
        self.compound_video_only()
        self.compound_audio_only()
        log.info("compound_both: video + audio compound tao xong (2 drafts)")
        return self

    # ─── Entry point chung ───────────────────────────────────────────────────

    def apply(self, mode: str) -> "CapCutCompounder":
        mode = (mode or "none").strip().lower()
        if mode == "none":    return self
        if mode == "video":   return self.compound_video_only()
        if mode == "audio":   return self.compound_audio_only()
        if mode == "mixed":   return self.compound_mixed()
        if mode == "both":    return self.compound_both()
        raise ValueError(f"mode khong hop le: '{mode}'. Chon trong: {COMPOUND_MODES}")


def apply_compound(draft_path: Path, mode: str) -> bool:
    mode = (mode or "none").strip().lower()
    if mode == "none":
        return False
    json_file = Path(draft_path) / "draft_content.json"
    if not json_file.exists():
        raise FileNotFoundError(f"Khong tim thay draft_content.json: {json_file}")
    try:
        CapCutCompounder(json_file).apply(mode).save()
        log.info("apply_compound('%s') OK: %s", mode, json_file)
        return True
    except Exception as e:
        log.error("apply_compound('%s') FAIL: %s", mode, e)
        raise