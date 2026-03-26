"""
gui.py  —  Auto CapCut Video Sync  v2.1 (pyCapCut edition)
Giao diện Light Mode - Square Design (Không bo góc, viền vuông vức).
"""

import sys, os, json, time, queue, logging, threading, subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QCheckBox, QTextEdit,
    QFrame, QFileDialog, QGridLayout, QMessageBox, QLineEdit,
    QProgressBar, QSizePolicy, QScrollArea, QTabWidget, QButtonGroup, QRadioButton,
    QComboBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon
from PyQt5.QtWidgets import QColorDialog

# ── Danh sách phiên bản CapCut hỗ trợ ────────────────────────────────────────
CAPCUT_VERSIONS = [
    # (label hiển thị,   app_version, new_version)
    ("3.9.0",  "4.0.0",  "110.0.0"),
    ("4.0.0",  "4.0.0",  "112.0.0"),
    ("4.1.0",  "4.1.0",  "114.0.0"),
    ("4.3.0",  "4.3.0",  "116.0.0"),
    ("4.6.0",  "4.6.0",  "119.0.0"),
    ("4.8.0",  "4.8.0",  "121.0.0"),
    ("5.3.0",  "5.3.0",  "126.0.0"),
    ("5.6.0",  "5.6.0",  "129.0.0"),
    ("5.8.0",  "5.8.0",  "131.0.0"),
    ("5.9.0",  "5.9.0",  "132.0.0"),
    ("5.9.1",  "5.9.1",  "132.0.0"),
    ("6.0.0",  "6.0.0",  "133.0.0"),
    ("6.7.0",  "6.7.0",  "140.0.0"),
    ("7.3.0",  "7.3.0",  "146.0.0"),
]
_CAPCUT_VERSION_DEFAULT = "5.9.1"  # mặc định hiển thị khi mở lần đầu

ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SETTINGS_FILE = ROOT / ".gui_settings.json"
LOG_Q: queue.Queue = queue.Queue()
UI_Q:  queue.Queue = queue.Queue()

class _QH(logging.Handler):
    def emit(self, r): LOG_Q.put(("log", self.format(r), "info"))

_qh = _QH()
_qh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%H:%M:%S"))
logging.getLogger().addHandler(_qh)
logging.getLogger().setLevel(logging.INFO)

def load_cfg():
    try:    return json.loads(SETTINGS_FILE.read_text("utf-8"))
    except: return {}

def save_cfg(d):
    try:    SETTINGS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")
    except: pass


# ── Stylesheet Mới (Light Mode + Square) ──────────────────────────────────────
APP_STYLE = """
QMainWindow, QWidget { 
    background-color: #F0F2F5; 
    font-family: 'Segoe UI', Arial, sans-serif; 
    font-size: 13px; 
    color: #1C1E21; 
}
QLineEdit { 
    background-color: #FFFFFF; 
    border: 1px solid #CCD0D5; 
    border-radius: 0px; 
    padding: 6px 10px; 
    font-family: Consolas; 
    font-size: 12px; 
    color: #1C1E21;
}
QLineEdit:focus { 
    border: 1px solid #007BFF; 
    background-color: #FFFFFF;
}
QLineEdit:disabled {
    background-color: #E4E6EB;
    color: #8D949E;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator { 
    width: 18px; 
    height: 18px; 
    border: 1px solid #CCD0D5; 
    border-radius: 0px; 
    background-color: #FFFFFF; 
}
QCheckBox::indicator:hover {
    border: 1px solid #007BFF; 
}
QCheckBox::indicator:checked { 
    background-color: #007BFF; 
    border-color: #007BFF; 
}
QRadioButton::indicator {
    width: 16px; 
    height: 16px; 
    border: 1px solid #CCD0D5; 
    border-radius: 0px;
    background-color: #FFFFFF; 
}
QRadioButton::indicator:checked {
    background-color: #007BFF;
    border: 3px solid #FFFFFF;
}
QProgressBar { 
    border: 1px solid #CCD0D5; 
    border-radius: 0px; 
    background-color: #E4E6EB; 
    height: 12px; 
    text-align: center; 
}
QProgressBar::chunk { 
    background-color: #007BFF;
    border-radius: 0px; 
}
QScrollBar:vertical { 
    background: #F0F2F5; 
    width: 10px; 
    margin: 0px; 
}
QScrollBar::handle:vertical { 
    background: #BCC0C4; 
    border-radius: 0px; 
    min-height: 20px; 
}
QScrollBar::handle:vertical:hover {
    background: #8D949E;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

def btn(bg, hover, fg="white", pad="8px 16px", radius="0px"):
    return (f"QPushButton {{ background-color:{bg}; color:{fg}; border:none; border-radius:{radius};"
            f" font-weight:bold; padding:{pad}; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color:{hover}; }}"
            f"QPushButton:pressed {{ background-color:{bg}; opacity: 0.8; }}"
            f"QPushButton:disabled {{ background-color:#E4E6EB; color:#8D949E; }}")


# ── PathRow ───────────────────────────────────────────────────────────────────
class PathRow(QWidget):
    def __init__(self, icon, label, mode="file", filetypes=None, parent=None):
        super().__init__(parent)
        self.mode      = mode
        self.filetypes = filetypes or "All (*.*)"
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        
        self._badge = QLabel(icon)
        self._badge.setFixedSize(36, 36); self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setStyleSheet("background-color:#E4E6EB; border-radius:0px; font-size:16px; border:1px solid #CCD0D5;")
        lay.addWidget(self._badge)
        
        lbl = QLabel(label); lbl.setFixedWidth(120)
        lbl.setStyleSheet("font-weight:bold; color:#1C1E21; border:none; background:transparent;")
        lay.addWidget(lbl)
        
        self.entry = QLineEdit(); self.entry.setPlaceholderText("Chưa chọn...")
        self.entry.setMinimumHeight(36); self.entry.textChanged.connect(self._validate)
        lay.addWidget(self.entry, 1)
        
        b = QPushButton("📁 Duyệt"); b.setFixedSize(90, 36)
        b.setStyleSheet(btn("#E4E6EB", "#D8DADF", fg="#1C1E21", pad="4px 10px"))
        b.clicked.connect(self._browse); lay.addWidget(b)

    def _browse(self):
        if self.mode == "file":
            p, _ = QFileDialog.getOpenFileName(self, "Chọn file", "", self.filetypes)
        else:
            p = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if p: self.set(p)

    def _validate(self):
        v = self.entry.text()
        if not v:
            self._badge.setStyleSheet("background-color:#E4E6EB; border-radius:0px; font-size:16px; border:1px solid #CCD0D5;"); return
        ok = Path(v).exists() if self.mode == "file" else Path(v).is_dir()
        if ok:
            self._badge.setStyleSheet("background-color:#D4EDDA; border-radius:0px; font-size:16px; border:1px solid #C3E6CB;")
        else:
            self._badge.setStyleSheet("background-color:#F8D7DA; border-radius:0px; font-size:16px; border:1px solid #F5C6CB;")

    def get(self): return self.entry.text().strip()
    def set(self, v):
        self.entry.setText(v); self._validate()


# ── StatCard ──────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, icon, label, accent="#007BFF", parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame{background-color:#FFFFFF; border:1px solid #CCD0D5; border-radius:0px;}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.setMinimumHeight(88)
        lay = QVBoxLayout(self); lay.setContentsMargins(10,12,10,10); lay.setSpacing(4)
        
        top_lay = QHBoxLayout()
        self._icon = QLabel(icon); self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet(f"font-size:18px; border:none; color:{accent}; background:transparent;")
        top_lay.addWidget(self._icon)
        top_lay.addStretch()
        lay.addLayout(top_lay)
        
        self._val = QLabel("—"); self._val.setAlignment(Qt.AlignLeft)
        self._val.setStyleSheet(f"font-family:Consolas; font-size:22px; font-weight:bold; border:none; color:{accent}; background:transparent;")
        lay.addWidget(self._val)
        
        lbl = QLabel(label); lbl.setAlignment(Qt.AlignLeft)
        lbl.setStyleSheet("font-size:11px; color:#606770; border:none; background:transparent;")
        lay.addWidget(lbl)
        
        self._accent = accent

    def set_value(self, v, color=None):
        self._val.setText(str(v))
        self._val.setStyleSheet(
            f"font-family:Consolas; font-size:22px; font-weight:bold; border:none; background:transparent; color:{color or self._accent};")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═════════════════════════════════════════════════════════════════════════════
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self._cfg         = load_cfg()
        self._running     = False
        self._stop_event  = threading.Event()
        self._start_time  = 0.0
        self._vcp_entry   = None   # pre-init

        self._build_ui()
        self._restore()

        self._timer_log = QTimer(self); self._timer_log.timeout.connect(self._pump_log); self._timer_log.start(200)
        self._timer_ui  = QTimer(self); self._timer_ui.timeout.connect(self._pump_ui);   self._timer_ui.start(200)
        self._last_ui_update = 0.0
        self._timer_el  = QTimer(self); self._timer_el.timeout.connect(self._tick_elapsed); self._timer_el.start(1000)

        # Auto-detect CapCut Drafts dir
        self.after(300, self._detect_drafts_dir)

    def after(self, ms, fn):
        QTimer.singleShot(ms, fn)

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Auto CapCut Video Sync  v2.1  by Văn Khải")
        self.resize(1280, 900); self.setMinimumSize(1024, 768)
        
        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        
        self._build_topbar(main)
        
        body = QWidget(); body.setStyleSheet("background-color:#F0F2F5;")
        bl = QHBoxLayout(body); bl.setContentsMargins(16,16,16,16); bl.setSpacing(16)
        main.addWidget(body, 1)
        
        self._build_left(bl)
        self._build_right(bl)
        self._build_footer(main)

    def _build_topbar(self, main):
        bar = QFrame(); bar.setFixedHeight(56)
        bar.setStyleSheet("QFrame{background-color:#FFFFFF; border-bottom:1px solid #CCD0D5;}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(24, 0, 24, 0); lay.setAlignment(Qt.AlignVCenter)
        
        title = QLabel("🎬  Auto CapCut Video Sync")
        title.setStyleSheet("font-family:'Segoe UI'; font-size:20px; font-weight:bold; color:#007BFF; border:none;")
        lay.addWidget(title)
        
        v = QLabel("v2.1  by Văn Khải")
        v.setStyleSheet("color:#606770; font-size:13px; border:none; font-weight:bold;")
        lay.addWidget(v); lay.addStretch()
        
        main.addWidget(bar)

    def _card(self, title_text, color="#007BFF"):
        f = QFrame()
        f.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #CCD0D5; border-radius: 0px; }")
        
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)
        
        h_box = QWidget()
        h_box.setStyleSheet(".QWidget { background: transparent; border: none; }")
        hl = QHBoxLayout(h_box); hl.setContentsMargins(0,0,0,0)
        
        t = QLabel(title_text)
        t.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        hl.addWidget(t)
        hl.addStretch()
        lay.addWidget(h_box)
        
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #CCD0D5; border: none;")
        lay.addWidget(div)
        
        return f, lay

    def _build_left(self, bl):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CCD0D5; border-radius: 0px; background: #FFFFFF; top: -1px; }
            QTabBar::tab { background: #E4E6EB; border: 1px solid #CCD0D5; border-bottom: none; border-radius: 0px; padding: 9px 16px; font-weight: bold; font-size: 12px; color: #606770; margin-right: 3px; min-width: 0px; }
            QTabBar::tab:selected { background: #FFFFFF; color: #007BFF; border-top: 2px solid #007BFF; }
            QTabBar::tab:hover:!selected { background: #D8DADF; color: #1C1E21; }
        """)

        def _make_scroll_tab():
            tab = QWidget(); tab.setStyleSheet(".QWidget { background:transparent; }")
            tl  = QVBoxLayout(tab); tl.setContentsMargins(0,10,0,0); tl.setSpacing(0)
            sc  = QScrollArea(); sc.setWidgetResizable(True)
            sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            sc.setStyleSheet("QScrollArea{background:transparent; border:none;}")
            c   = QWidget(); c.setStyleSheet(".QWidget { background:transparent; }")
            lay = QVBoxLayout(c); lay.setContentsMargins(4,4,12,12); lay.setSpacing(14)
            sc.setWidget(c); tl.addWidget(sc)
            return tab, lay

        # ── TAB 1: Tệp & Draft ────────────────────────────────────────────
        tab1, lay1 = _make_scroll_tab()
        self._build_grp_inputs(lay1)
        self._build_grp_draft_dir(lay1)
        lay1.addStretch()
        self._tabs.addTab(tab1, "📁  Tệp & Draft")

        # ── TAB 2: Cấu hình ───────────────────────────────────────────────
        tab2, lay2 = _make_scroll_tab()
        self._build_grp_settings(lay2)
        self._build_grp_perf(lay2)
        self._build_grp_options(lay2)
        lay2.addStretch()
        self._tabs.addTab(tab2, "⚙️  Cấu hình")

        # ── TAB 3: Gộp Clip ───────────────────────────────────────────────
        tab3, lay3 = _make_scroll_tab()
        self._build_grp_compound(lay3)
        lay3.addStretch()
        self._tabs.addTab(tab3, "🔗  Gộp Clip")

        # ── TAB 4: Phân tích Draft ────────────────────────────────────────
        tab4, lay4 = _make_scroll_tab()
        self._build_tab_analyzer(lay4)
        lay4.addStretch()
        self._tabs.addTab(tab4, "🔍  Phân tích Draft")

        # ── TAB 5: Auto Edit ──────────────────────────────────────────────
        tab5, lay5 = _make_scroll_tab()
        self._build_ae_grp_subtitle(lay5)
        self._build_ae_grp_intro_outro(lay5)
        self._build_ae_grp_logo(lay5)
        lay5.addStretch()
        self._tabs.addTab(tab5, "✏️  Auto Edit")

        bl.addWidget(self._tabs, 6)

    def _field(self, parent_lay, row, col, lbl_text, val, last=False):
        f = QWidget()
        f.setStyleSheet(".QWidget { background: transparent; border: none; }")
        fl = QVBoxLayout(f); fl.setContentsMargins(0,0,0,0); fl.setSpacing(6)
        parent_lay.addWidget(f, row, col, 1, 1)
        
        lb = QLabel(lbl_text); lb.setStyleSheet("font-weight:bold; color:#606770; font-size: 12px; background: transparent; border: none;")
        fl.addWidget(lb)
        var = QLineEdit(str(val)); var.setMinimumHeight(34); fl.addWidget(var)
        return var

    def _build_grp_inputs(self, lay):
        card, v = self._card("🎬  Quản lý tệp đầu vào", "#007BFF")
        self._pv = PathRow("🎞️","Video gốc",   filetypes="Video (*.mp4 *.mov *.avi *.mkv);;All (*.*)")
        self._ps = PathRow("📝","Phụ đề (.srt)",filetypes="SRT (*.srt);;All (*.*)")
        self._pa = PathRow("🎧","Thư mục Audio",mode="directory")
        v.addWidget(self._pv); v.addWidget(self._ps); v.addWidget(self._pa)
        lay.addWidget(card)

    def _build_grp_settings(self, lay):
        card, main_v = self._card("🎛️  Cấu hình Video", "#6F42C1")
        
        g_widget = QWidget()
        g_widget.setStyleSheet(".QWidget { background: transparent; border: none; }")
        grid = QGridLayout(g_widget); grid.setContentsMargins(0,0,0,0); grid.setSpacing(12)
        
        self._vw   = self._field(grid, 0, 0, "Rộng (px)", 1080)
        self._vh   = self._field(grid, 0, 1, "Cao (px)",  1920)
        self._vfps = self._field(grid, 0, 2, "FPS",       30)
        self._vmn  = self._field(grid, 1, 0, "Tốc độ tối thiểu", 0.1)
        self._vmx  = self._field(grid, 1, 1, "Tốc độ tối đa", 10.0)
        main_v.addWidget(g_widget)
        lay.addWidget(card)

    def _build_grp_draft_dir(self, lay):
        card, main_v = self._card("📁  Drafts & Phiên bản CapCut", "#007BFF")

        cp_lbl = QLabel("📁  Thư mục Drafts của CapCut")
        cp_lbl.setStyleSheet("font-weight:bold; color:#1C1E21; background: transparent; border: none;")
        main_v.addWidget(cp_lbl)

        cp_hint = QLabel("Tìm trong CapCut: Settings → General → Draft Location")
        cp_hint.setStyleSheet("color:#606770; font-size:11px; background: transparent; border: none;")
        main_v.addWidget(cp_hint)

        cp_row = QWidget()
        cp_row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        cp_lay = QHBoxLayout(cp_row); cp_lay.setContentsMargins(0,0,0,0); cp_lay.setSpacing(10)
        
        self._vcp_entry = QLineEdit()
        self._vcp_entry.setPlaceholderText("VD: C:\\Users\\...\\CapCut\\User Data\\Projects")
        self._vcp_entry.setMinimumHeight(36)
        cp_lay.addWidget(self._vcp_entry, 1)
        
        cp_btn = QPushButton("Duyệt"); cp_btn.setFixedSize(90, 36)
        cp_btn.setStyleSheet(btn("#E4E6EB", "#D8DADF", fg="#1C1E21", pad="4px 10px"))
        cp_btn.clicked.connect(self._browse_drafts); cp_lay.addWidget(cp_btn)
        main_v.addWidget(cp_row)

        self._cp_status = QLabel("")
        self._cp_status.setStyleSheet("font-size:11px; color:#28A745; background: transparent; border: none;")
        main_v.addWidget(self._cp_status)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color:#CCD0D5; border:none; margin: 4px 0;")
        main_v.addWidget(sep2)

        ver_lbl = QLabel("🏷️  Phiên bản CapCut (patch version)")
        ver_lbl.setStyleSheet("font-weight:bold; color:#1C1E21; background: transparent; border: none;")
        main_v.addWidget(ver_lbl)

        ver_hint = QLabel("Chọn đúng phiên bản CapCut đang dùng để tránh lỗi tương thích.")
        ver_hint.setStyleSheet("color:#606770; font-size:11px; background: transparent; border: none;")
        ver_hint.setWordWrap(True)
        main_v.addWidget(ver_hint)

        ver_row = QWidget()
        ver_row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        ver_lay = QHBoxLayout(ver_row); ver_lay.setContentsMargins(0,0,0,0); ver_lay.setSpacing(12)

        self._ver_combo = QComboBox()
        self._ver_combo.setMinimumHeight(36)
        self._ver_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF; border: 1px solid #CCD0D5; border-radius: 0px;
                padding: 4px 10px; font-size: 13px; color: #1C1E21;
            }
            QComboBox:focus { border: 1px solid #007BFF; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow { width: 12px; height: 12px; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF; border: 1px solid #CCD0D5;
                selection-background-color: #007BFF; selection-color: #FFFFFF;
                font-size: 13px;
            }
        """)
        for label, app_v, new_v in CAPCUT_VERSIONS:
            self._ver_combo.addItem(f"CapCut  {label}", userData=(app_v, new_v))
        self._set_version_combo(_CAPCUT_VERSION_DEFAULT)
        ver_lay.addWidget(self._ver_combo, 1)
        main_v.addWidget(ver_row)

        self._ver_combo.currentIndexChanged.connect(self._update_ver_badge)
        lay.addWidget(card)

    def _set_version_combo(self, label: str):
        """Chọn combo theo label phiên bản (vd: '5.9.1'). Fallback về default nếu không tìm thấy."""
        for i in range(self._ver_combo.count()):
            data = self._ver_combo.itemData(i)
            item_label = self._ver_combo.itemText(i).replace("CapCut  ", "").strip()
            if item_label == label:
                self._ver_combo.setCurrentIndex(i)
                return
        # fallback: chọn item có app_version khớp
        for i in range(self._ver_combo.count()):
            item_label = self._ver_combo.itemText(i).replace("CapCut  ", "").strip()
            if item_label == _CAPCUT_VERSION_DEFAULT:
                self._ver_combo.setCurrentIndex(i)
                return

    def _update_ver_badge(self):
        """Placeholder — badge đã bị ẩn, giữ lại để signal không lỗi."""
        pass

    def _get_patch_versions(self) -> tuple:
        """Trả về (app_version, new_version) từ dropdown hiện tại."""
        data = self._ver_combo.currentData()
        if data:
            return data[0], data[1]
        return "5.9.1", "132.0.0"  # fallback cứng

    def _build_grp_perf(self, lay):
        card, main_v = self._card("⚡  Hiệu năng (Giảm tải CPU)", "#FD7E14")
        
        cpu_lbl = QLabel("🧵  Số luồng CPU cho FFmpeg")
        cpu_lbl.setStyleSheet("font-weight:bold; color:#1C1E21; background: transparent; border: none;")
        main_v.addWidget(cpu_lbl)

        cpu_hint = QLabel(f"Số nhân CPU FFmpeg được dùng (máy có {os.cpu_count()} nhân). Giá trị nhỏ = máy ít giật hơn, xử lý chậm hơn.")
        cpu_hint.setStyleSheet("color:#606770; font-size:11px; background: transparent; border: none;")
        cpu_hint.setWordWrap(True)
        main_v.addWidget(cpu_hint)

        g_widget = QWidget()
        g_widget.setStyleSheet(".QWidget { background: transparent; border: none; }")
        grid = QGridLayout(g_widget); grid.setContentsMargins(0,6,0,6); grid.setSpacing(12)
        self._vcpu = self._field(grid, 0, 0, "CPU Threads", max(2, (os.cpu_count() or 4) - 2))
        self._venc_w = self._field(grid, 0, 1, "Encode Workers", 2)
        self._vcut_w = self._field(grid, 0, 2, "Cut Workers",    2)
        main_v.addWidget(g_widget)

        preset_row = QWidget()
        preset_row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        pr_lay = QHBoxLayout(preset_row); pr_lay.setContentsMargins(0,4,0,0); pr_lay.setSpacing(10)

        for label, cpu, enc, cut, bg, hover in [
            ("🐢  Nhẹ nhất", max(2, (os.cpu_count() or 4) - 2), 1, 1, "#28A745", "#218838"),
            ("⚖️  Cân bằng", max(2, (os.cpu_count() or 4) - 1), 2, 2, "#FD7E14", "#E37012"),
            ("🚀  Nhanh nhất", os.cpu_count() or 4, 4, 4, "#DC3545", "#C82333"),
        ]:
            b = QPushButton(label); b.setFixedHeight(34)
            b.setStyleSheet(btn(bg, hover, pad="4px 12px"))
            b.clicked.connect(lambda _, c=cpu, e=enc, ct=cut: (
                self._vcpu.setText(str(c)),
                self._venc_w.setText(str(e)),
                self._vcut_w.setText(str(ct)),
            ))
            pr_lay.addWidget(b)
        pr_lay.addStretch()
        main_v.addWidget(preset_row)
        
        lay.addWidget(card)

    def _build_grp_compound(self, lay):
        card, v = self._card("🔗  Gộp Clip (Compound)", "#007BFF")

        desc = QLabel(
            "Gộp các clip nhỏ thành Compound Clip sau khi xuất draft.\n"
            "Có thể tích Video, Audio, hoặc cả 2 cùng lúc.")
        desc.setStyleSheet("color:#606770; font-size:12px; background: transparent; border: none;")
        desc.setWordWrap(True)
        v.addWidget(desc)

        self._cb_compound_video = QCheckBox("🎞️  Compound Video")
        self._cb_compound_video.setStyleSheet("QCheckBox { color:#007BFF; font-weight:bold; background: transparent; }")
        v_hint1 = QLabel("  Gộp tất cả clip video thành 1 khối. Track audio giữ nguyên.")
        v_hint1.setStyleSheet("font-size:11px; color:#606770; margin-left:26px; background: transparent; border: none;")
        v.addWidget(self._cb_compound_video); v.addWidget(v_hint1)

        self._cb_compound_audio = QCheckBox("🎧  Compound Audio")
        self._cb_compound_audio.setStyleSheet("QCheckBox { color:#17A2B8; font-weight:bold; background: transparent; }")
        v_hint2 = QLabel("  Gộp tất cả clip audio thành 1 khối. Track video giữ nguyên.")
        v_hint2.setStyleSheet("font-size:11px; color:#606770; margin-left:26px; background: transparent; border: none;")
        v.addWidget(self._cb_compound_audio); v.addWidget(v_hint2)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color:#CCD0D5; border:none; margin: 6px 0;"); v.addWidget(sep2)

        self._cb_compound_mixed = QCheckBox("✨  Mixed Compound  (Khuyên dùng)")
        self._cb_compound_mixed.setStyleSheet("QCheckBox { color:#6F42C1; font-weight:bold; background: transparent; }")
        v_hint3 = QLabel("  Gộp cả Video + Audio vào chung 1 khối duy nhất. Gọn nhất.")
        v_hint3.setStyleSheet("font-size:11px; color:#606770; margin-left:26px; background: transparent; border: none;")
        v.addWidget(self._cb_compound_mixed); v.addWidget(v_hint3)

        def on_mixed_changed(state):
            if state:
                self._cb_compound_video.setChecked(False)
                self._cb_compound_audio.setChecked(False)

        def on_va_changed(state):
            if state:
                self._cb_compound_mixed.setChecked(False)

        self._cb_compound_mixed.stateChanged.connect(on_mixed_changed)
        self._cb_compound_video.stateChanged.connect(on_va_changed)
        self._cb_compound_audio.stateChanged.connect(on_va_changed)

        warn = QLabel("⚠  Sau khi áp dụng, mở CapCut → bấm Refresh Draft nếu chưa thấy hiệu lực.")
        warn.setStyleSheet(
            "font-size:11px; color:#856404; background-color:#FFF3CD; "
            "border:1px solid #FFEEBA; border-radius:0px; padding:6px 8px;")
        warn.setWordWrap(True)
        v.addWidget(warn)
        lay.addWidget(card)

    def _get_compound_mode(self) -> str:
        if self._cb_compound_mixed.isChecked(): return "mixed"
        v = self._cb_compound_video.isChecked()
        a = self._cb_compound_audio.isChecked()
        if v and a:  return "both"
        if v:        return "video"
        if a:        return "audio"
        return "none"

    def _build_grp_options(self, lay):
        card, v = self._card("🛠️  Tuỳ chọn", "#6F42C1")
        self._o_sub  = QCheckBox("📌  Thêm Subtitle vào timeline")
        self._o_dbg  = QCheckBox("🐛  Bật Debug (log chi tiết)")
        for cb in (self._o_sub, self._o_dbg):
            cb.setStyleSheet("font-size:14px; color:#1C1E21; background: transparent;")
            v.addWidget(cb)
        lay.addWidget(card)

    def _color_btn(self, hex_val: str, on_change):
        row = QWidget()
        row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        rl  = QHBoxLayout(row); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(8)
        
        entry = QLineEdit(hex_val); entry.setFixedWidth(80); entry.setMinimumHeight(34)
        entry.setStyleSheet("font-family:Consolas; font-size:12px; background-color:#FFFFFF; color:#1C1E21;")
        
        swatch = QPushButton(); swatch.setFixedSize(34, 34)
        swatch.setStyleSheet(f"QPushButton{{background-color:{hex_val}; border:1px solid #CCD0D5; border-radius:0px;}}")
        
        def _update_swatch(text):
            if len(text) == 7 and text.startswith("#"):
                swatch.setStyleSheet(f"QPushButton{{background-color:{text}; border:1px solid #CCD0D5; border-radius:0px;}}")
                on_change(text)
        def _open_picker():
            col = QColorDialog.getColor(QColor(entry.text()), None, "Chọn màu")
            if col.isValid(): entry.setText(col.name().upper())
            
        entry.textChanged.connect(_update_swatch)
        swatch.clicked.connect(_open_picker)
        rl.addWidget(entry); rl.addWidget(swatch)
        return row, entry

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: PHÂN TÍCH DRAFT MẪU
    # ═════════════════════════════════════════════════════════════════════════

    def _build_tab_analyzer(self, lay):
        """Xây dựng tab Phân tích Draft — hoạt động hoàn toàn độc lập."""

        # ── Card: chọn thư mục draft ─────────────────────────────────────
        card_src, v_src = self._card("📂  Chọn Draft mẫu", "#007BFF")

        hint = QLabel(
            "Chọn thư mục draft CapCut (chứa draft_content.json). "
            "Tool sẽ đọc và trích xuất toàn bộ thông số style phụ đề và logo.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#606770; font-size:12px; background:transparent; border:none;")
        v_src.addWidget(hint)

        row_path = QWidget(); row_path.setStyleSheet(".QWidget{background:transparent;border:none;}")
        rpl = QHBoxLayout(row_path); rpl.setContentsMargins(0,0,0,0); rpl.setSpacing(10)

        self._ana_path = QLineEdit()
        self._ana_path.setPlaceholderText("VD: C:\\...\\CapCut\\User Data\\Projects\\MyDraft")
        self._ana_path.setMinimumHeight(36)
        rpl.addWidget(self._ana_path, 1)

        btn_browse = QPushButton("📁 Duyệt"); btn_browse.setFixedSize(100, 36)
        btn_browse.setStyleSheet(btn("#E4E6EB","#D8DADF",fg="#1C1E21",pad="4px 10px"))
        btn_browse.clicked.connect(self._ana_browse)
        rpl.addWidget(btn_browse)

        btn_analyze = QPushButton("🔍 Phân tích"); btn_analyze.setFixedSize(110, 36)
        btn_analyze.setStyleSheet(btn("#007BFF","#0069D9",pad="4px 10px"))
        btn_analyze.clicked.connect(self._ana_run)
        rpl.addWidget(btn_analyze)

        v_src.addWidget(row_path)
        lay.addWidget(card_src)

        # ── Card: kết quả phân tích ──────────────────────────────────────
        card_res, v_res = self._card("📊  Kết quả phân tích", "#6F42C1")

        self._ana_status = QLabel("⏳  Chưa phân tích — chọn thư mục draft và bấm Phân tích.")
        self._ana_status.setStyleSheet(
            "font-size:12px; color:#606770; background:transparent; border:none;")
        self._ana_status.setWordWrap(True)
        v_res.addWidget(self._ana_status)

        # ── Sub-card: Phụ đề ─────────────────────────────────────────────
        sub_sub = QFrame()
        sub_sub.setStyleSheet(
            "QFrame{background:#F8F9FA; border:1px solid #CCD0D5; border-radius:0px;}")
        sub_sub_lay = QVBoxLayout(sub_sub)
        sub_sub_lay.setContentsMargins(12,10,12,10); sub_sub_lay.setSpacing(8)

        sub_title = QLabel("✏️  Style Phụ đề")
        sub_title.setStyleSheet(
            "font-weight:bold; font-size:13px; color:#007BFF; background:transparent; border:none;")
        sub_sub_lay.addWidget(sub_title)

        grid_sub = QWidget(); grid_sub.setStyleSheet(".QWidget{background:transparent;border:none;}")
        gsub_lay = QGridLayout(grid_sub)
        gsub_lay.setContentsMargins(0,0,0,0); gsub_lay.setSpacing(8)

        def _info_row(grid, row, label, attr):
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "font-size:12px; font-weight:bold; color:#606770; "
                "background:transparent; border:none; min-width:110px;")
            val = QLabel("—")
            val.setStyleSheet(
                "font-family:Consolas; font-size:12px; color:#1C1E21; "
                "background:transparent; border:none;")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            setattr(self, attr, val)

        _info_row(gsub_lay, 0,  "Font file:",     "_ana_r_font_path")
        _info_row(gsub_lay, 1,  "Tên font:",      "_ana_r_font_title")
        _info_row(gsub_lay, 2,  "Màu chữ:",       "_ana_r_text_color")
        _info_row(gsub_lay, 3,  "Màu viền:",      "_ana_r_stroke_color")
        _info_row(gsub_lay, 4,  "Độ rộng viền:",  "_ana_r_stroke_w")
        _info_row(gsub_lay, 5,  "Font size:",     "_ana_r_font_size")
        _info_row(gsub_lay, 6,  "Scale:",         "_ana_r_scale")
        _info_row(gsub_lay, 7,  "Vị trí Y:",      "_ana_r_pos_y")
        _info_row(gsub_lay, 8,  "Max width:",     "_ana_r_lmw")
        _info_row(gsub_lay, 9,  "Canh lề:",       "_ana_r_align")

        sub_sub_lay.addWidget(grid_sub)
        v_res.addWidget(sub_sub)

        # ── Sub-card: Logo ───────────────────────────────────────────────
        sub_logo = QFrame()
        sub_logo.setStyleSheet(
            "QFrame{background:#F8F9FA; border:1px solid #CCD0D5; border-radius:0px;}")
        sub_logo_lay = QVBoxLayout(sub_logo)
        sub_logo_lay.setContentsMargins(12,10,12,10); sub_logo_lay.setSpacing(8)

        logo_title = QLabel("🖼️  Logo Overlay")
        logo_title.setStyleSheet(
            "font-weight:bold; font-size:13px; color:#6F42C1; background:transparent; border:none;")
        sub_logo_lay.addWidget(logo_title)

        grid_logo = QWidget(); grid_logo.setStyleSheet(".QWidget{background:transparent;border:none;}")
        glogo_lay = QGridLayout(grid_logo)
        glogo_lay.setContentsMargins(0,0,0,0); glogo_lay.setSpacing(8)

        _info_row(glogo_lay, 0, "File logo:",   "_ana_r_logo_path")
        _info_row(glogo_lay, 1, "Scale:",        "_ana_r_logo_scale")
        _info_row(glogo_lay, 2, "Tọa độ X:",     "_ana_r_logo_x")
        _info_row(glogo_lay, 3, "Tọa độ Y:",     "_ana_r_logo_y")

        sub_logo_lay.addWidget(grid_logo)
        v_res.addWidget(sub_logo)

        lay.addWidget(card_res)

        # ── Card: áp dụng ────────────────────────────────────────────────
        card_apply, v_apply = self._card("✅  Áp dụng vào Auto Edit", "#28A745")

        note = QLabel(
            "Sau khi phân tích, bấm nút bên dưới để tự động điền tất cả thông số "
            "vào đúng các trường trong tab Auto Edit.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#606770; font-size:12px; background:transparent; border:none;")
        v_apply.addWidget(note)

        row_btns = QWidget(); row_btns.setStyleSheet(".QWidget{background:transparent;border:none;}")
        rbl = QHBoxLayout(row_btns); rbl.setContentsMargins(0,0,0,0); rbl.setSpacing(12)

        self._btn_apply_sub = QPushButton("✏️  Áp dụng Phụ đề")
        self._btn_apply_sub.setFixedHeight(38)
        self._btn_apply_sub.setStyleSheet(btn("#007BFF","#0069D9",pad="6px 16px"))
        self._btn_apply_sub.setEnabled(False)
        self._btn_apply_sub.clicked.connect(lambda: self._ana_apply("sub"))
        rbl.addWidget(self._btn_apply_sub)

        self._btn_apply_logo = QPushButton("🖼️  Áp dụng Logo")
        self._btn_apply_logo.setFixedHeight(38)
        self._btn_apply_logo.setStyleSheet(btn("#6F42C1","#5A32A3",pad="6px 16px"))
        self._btn_apply_logo.setEnabled(False)
        self._btn_apply_logo.clicked.connect(lambda: self._ana_apply("logo"))
        rbl.addWidget(self._btn_apply_logo)

        self._btn_apply_all = QPushButton("🚀  Áp dụng Tất cả")
        self._btn_apply_all.setFixedHeight(38)
        self._btn_apply_all.setStyleSheet(btn("#28A745","#218838",pad="6px 16px"))
        self._btn_apply_all.setEnabled(False)
        self._btn_apply_all.clicked.connect(lambda: self._ana_apply("all"))
        rbl.addWidget(self._btn_apply_all)

        rbl.addStretch()
        v_apply.addWidget(row_btns)

        self._ana_apply_status = QLabel("")
        self._ana_apply_status.setStyleSheet(
            "font-size:12px; color:#28A745; font-weight:bold; "
            "background:transparent; border:none;")
        v_apply.addWidget(self._ana_apply_status)

        lay.addWidget(card_apply)

        # Lưu kết quả parse
        self._ana_result: dict = {}

    # ── Analyzer: browse ─────────────────────────────────────────────────────
    def _ana_browse(self):
        p = QFileDialog.getExistingDirectory(self, "Chọn thư mục Draft CapCut")
        if p:
            self._ana_path.setText(p)

    # ── Analyzer: parse draft_content.json ───────────────────────────────────
    def _ana_run(self):
        import json as _json

        path_str = self._ana_path.text().strip()
        if not path_str:
            self._ana_set_status("⚠  Vui lòng chọn thư mục draft trước.", "#FD7E14")
            return

        draft_dir = Path(path_str)
        json_file = draft_dir / "draft_content.json"
        if not json_file.exists():
            self._ana_set_status(
                f"❌  Không tìm thấy draft_content.json trong:\n{draft_dir}", "#DC3545")
            return

        try:
            data = _json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as e:
            self._ana_set_status(f"❌  Lỗi đọc JSON: {e}", "#DC3545")
            return

        result = {}

        # ── 1. Trích xuất style phụ đề ────────────────────────────────
        text_mat_ids = set()
        text_seg_by_mat: dict = {}
        for track in data.get("tracks", []):
            if track.get("type") == "text":
                for seg in track.get("segments", []):
                    mid = seg.get("material_id", "")
                    text_mat_ids.add(mid)
                    text_seg_by_mat[mid] = seg

        sub_info = {}
        for mat in data.get("materials", {}).get("texts", []):
            if mat.get("id") not in text_mat_ids:
                continue
            sub_info["font_path"]    = mat.get("font_path", "")
            sub_info["font_title"]   = mat.get("font_title", "")
            sub_info["text_color"]   = mat.get("text_color", "#ffffff").upper()
            sub_info["stroke_color"] = mat.get("border_color", "#000000").upper()
            sub_info["stroke_width"] = mat.get("border_width", 0.06)
            sub_info["font_size"]    = mat.get("font_size", 5.0)
            sub_info["alignment"]    = mat.get("alignment", 1)
            sub_info["line_max_width"]= mat.get("line_max_width", 0.82)
            # Lấy pos và scale từ segment đầu tiên
            seg = text_seg_by_mat.get(mat["id"], {})
            clip = seg.get("clip", {})
            sub_info["pos_y"]  = clip.get("transform", {}).get("y", -0.893)
            sub_info["pos_x"]  = clip.get("transform", {}).get("x", 0.0)
            sub_info["scale"]  = clip.get("scale", {}).get("x", 1.0)
            break  # chỉ cần 1 mẫu

        result["sub"] = sub_info

        # ── 2. Trích xuất logo ────────────────────────────────────────
        # Logo: track video có 1 segment duy nhất với material là photo
        logo_info = {}
        video_mats = {m["id"]: m for m in data.get("materials",{}).get("videos",[])}
        main_track_segs = 0
        for track in data.get("tracks", []):
            if track.get("type") == "video":
                main_track_segs = max(main_track_segs, len(track.get("segments", [])))

        for track in data.get("tracks", []):
            if track.get("type") != "video":
                continue
            segs = track.get("segments", [])
            if len(segs) != 1:
                continue  # logo chỉ có 1 segment
            if len(segs) == main_track_segs:
                continue  # bỏ main track
            seg = segs[0]
            mat = video_mats.get(seg.get("material_id", ""), {})
            if mat.get("type") != "photo":
                continue
            clip = seg.get("clip", {})
            logo_info["logo_path"] = mat.get("path", "")
            logo_info["scale"]     = clip.get("scale", {}).get("x", 0.453)
            logo_info["pos_x"]     = clip.get("transform", {}).get("x", -0.808)
            logo_info["pos_y"]     = clip.get("transform", {}).get("y",  0.805)
            break

        result["logo"] = logo_info

        self._ana_result = result
        self._ana_populate_ui(result)

    def _ana_populate_ui(self, result: dict):
        """Điền kết quả lên các label hiển thị."""
        def _fmt(v, decimals=3):
            try:   return f"{float(v):.{decimals}f}"
            except: return str(v)

        def _hex_display(hex_str: str, label: QLabel):
            """Hiển thị hex + ô màu nhỏ inline bằng HTML."""
            h = hex_str.upper().lstrip("#")
            if len(h) == 6:
                label.setText(
                    f'<span style="background:#{h};'
                    f'border:1px solid #aaa;'
                    f'padding:0 10px;">&nbsp;&nbsp;&nbsp;&nbsp;</span>'
                    f'  #{h}')
                label.setTextFormat(Qt.RichText)
            else:
                label.setText(hex_str)

        sub = result.get("sub", {})
        logo = result.get("logo", {})
        has_sub  = bool(sub)
        has_logo = bool(logo)

        # Subtitle fields
        if has_sub:
            fp = sub.get("font_path", "")
            self._ana_r_font_path.setText(Path(fp).name if fp else "— (không có)")
            self._ana_r_font_title.setText(sub.get("font_title", "—") or "—")
            _hex_display(sub.get("text_color",   "#FFFFFF"), self._ana_r_text_color)
            _hex_display(sub.get("stroke_color", "#000000"), self._ana_r_stroke_color)
            self._ana_r_stroke_w.setText(_fmt(sub.get("stroke_width", 0.06)))
            self._ana_r_font_size.setText(_fmt(sub.get("font_size", 5.0), 1))
            self._ana_r_scale.setText(_fmt(sub.get("scale", 1.0)))
            self._ana_r_pos_y.setText(_fmt(sub.get("pos_y", -0.893)))
            self._ana_r_lmw.setText(_fmt(sub.get("line_max_width", 0.82)))
            align_map = {0: "◀ Trái", 1: "■ Giữa", 2: "Phải ▶"}
            self._ana_r_align.setText(align_map.get(int(sub.get("alignment", 1)), "—"))
        else:
            for attr in ["_ana_r_font_path","_ana_r_font_title","_ana_r_text_color",
                         "_ana_r_stroke_color","_ana_r_stroke_w","_ana_r_font_size",
                         "_ana_r_scale","_ana_r_pos_y","_ana_r_lmw","_ana_r_align"]:
                getattr(self, attr).setText("— (không tìm thấy phụ đề)")

        # Logo fields
        if has_logo:
            lp = logo.get("logo_path", "")
            self._ana_r_logo_path.setText(Path(lp).name if lp else "— (không rõ)")
            self._ana_r_logo_scale.setText(_fmt(logo.get("scale",   0.453)))
            self._ana_r_logo_x.setText(_fmt(logo.get("pos_x", -0.808)))
            self._ana_r_logo_y.setText(_fmt(logo.get("pos_y",  0.805)))
        else:
            for attr in ["_ana_r_logo_path","_ana_r_logo_scale","_ana_r_logo_x","_ana_r_logo_y"]:
                getattr(self, attr).setText("— (không tìm thấy logo)")

        # Status
        parts = []
        if has_sub:  parts.append("✅ Phụ đề")
        if has_logo: parts.append("✅ Logo")
        if not parts:
            self._ana_set_status(
                "⚠  Không tìm thấy dữ liệu phụ đề hay logo trong draft này.", "#FD7E14")
        else:
            self._ana_set_status(
                f"✅  Phân tích hoàn tất — tìm thấy: {', '.join(parts)}", "#28A745")

        self._btn_apply_sub.setEnabled(has_sub)
        self._btn_apply_logo.setEnabled(has_logo)
        self._btn_apply_all.setEnabled(has_sub or has_logo)
        self._ana_apply_status.setText("")

    def _ana_set_status(self, msg: str, color: str = "#606770"):
        self._ana_status.setText(msg)
        self._ana_status.setStyleSheet(
            f"font-size:12px; color:{color}; background:transparent; border:none;")

    # ── Analyzer: áp dụng vào Auto Edit ─────────────────────────────────────
    def _ana_apply(self, mode: str):
        """mode: 'sub' | 'logo' | 'all'"""
        result = self._ana_result
        applied = []

        if mode in ("sub", "all"):
            sub = result.get("sub", {})
            if sub:
                fp = sub.get("font_path", "")
                if fp: self._ae_font.set(fp)
                ft = sub.get("font_title", "")
                if ft: self._ae_font_title.setText(ft)
                self._ae_text_color.setText(
                    sub.get("text_color", "#FFFFFF").upper())
                self._ae_stroke_color.setText(
                    sub.get("stroke_color", "#000000").upper())
                self._ae_stroke_w.setText(
                    f"{float(sub.get('stroke_width', 0.06)):.3f}")
                self._ae_font_size.setText(
                    f"{float(sub.get('font_size', 5.0)):.1f}")
                self._ae_scale.setText(
                    f"{float(sub.get('scale', 1.0)):.3f}")
                self._ae_pos_y.setText(
                    f"{float(sub.get('pos_y', -0.893)):.3f}")
                self._ae_lmw.setText(
                    f"{float(sub.get('line_max_width', 0.82)):.2f}")
                align = int(sub.get("alignment", 1))
                if 0 <= align < len(self._ae_align_btns):
                    self._ae_align_btns[align].setChecked(True)
                self._ae_cb_sub.setChecked(True)
                applied.append("Phụ đề")

        if mode in ("logo", "all"):
            logo = result.get("logo", {})
            if logo:
                lp = logo.get("logo_path", "")
                if lp and Path(lp).exists():
                    self._ae_logo.set(lp)
                self._ae_logo_scale.setText(
                    f"{float(logo.get('scale',   0.453)):.3f}")
                self._ae_logo_x.setText(
                    f"{float(logo.get('pos_x', -0.808)):.3f}")
                self._ae_logo_y.setText(
                    f"{float(logo.get('pos_y',  0.805)):.3f}")
                self._ae_cb_logo.setChecked(True)
                applied.append("Logo")

        if applied:
            self._ana_apply_status.setText(
                f"✅  Đã điền: {', '.join(applied)} → chuyển sang tab Auto Edit để kiểm tra.")
            self._ana_apply_status.setStyleSheet(
                "font-size:12px; color:#28A745; font-weight:bold; "
                "background:transparent; border:none;")
            # Tự chuyển sang tab Auto Edit
            self._tabs.setCurrentIndex(self._tabs.count() - 1)
        else:
            self._ana_apply_status.setText("⚠  Không có dữ liệu để áp dụng.")
            self._ana_apply_status.setStyleSheet(
                "font-size:12px; color:#FD7E14; font-weight:bold; "
                "background:transparent; border:none;")

    def _build_ae_grp_subtitle(self, lay):
        card, v = self._card("✏️  Style Phụ đề", "#007BFF")

        self._ae_cb_sub = QCheckBox("Áp dụng style phụ đề")
        self._ae_cb_sub.setStyleSheet("QCheckBox{font-size:14px; font-weight:bold; color:#007BFF; background: transparent; border: none;}")
        v.addWidget(self._ae_cb_sub)

        self._ae_font = PathRow("🔤", "File Font (.ttf)", filetypes="Font (*.ttf *.otf);;All (*.*)")
        v.addWidget(self._ae_font)

        gw = QWidget()
        gw.setStyleSheet(".QWidget { background: transparent; border: none; }")
        gl = QGridLayout(gw); gl.setContentsMargins(0,0,0,0); gl.setSpacing(12)

        lbl_ft = QLabel("Tên font:"); lbl_ft.setStyleSheet("color:#606770; font-weight:bold; background: transparent; border: none;")
        self._ae_font_title = QLineEdit(); self._ae_font_title.setPlaceholderText("Anton SC Regular")
        self._ae_font_title.setMinimumHeight(34)
        gl.addWidget(lbl_ft, 0, 0); gl.addWidget(self._ae_font_title, 0, 1, 1, 3)

        def _auto_title(path):
            if path and not self._ae_font_title.text():
                try:
                    from src.draft_editor import _font_title_from_path
                    self._ae_font_title.setText(_font_title_from_path(path))
                except: pass
        self._ae_font.entry.textChanged.connect(_auto_title)

        lbl_tc = QLabel("Màu chữ:"); lbl_tc.setStyleSheet("color:#606770; font-weight:bold; background: transparent; border: none;")
        r1, self._ae_text_color = self._color_btn("#F0FF00", lambda _: None)
        gl.addWidget(lbl_tc, 1, 0); gl.addWidget(r1, 1, 1)

        lbl_sc = QLabel("Màu viền:"); lbl_sc.setStyleSheet("color:#606770; font-weight:bold; background: transparent; border: none;")
        r2, self._ae_stroke_color = self._color_btn("#000000", lambda _: None)
        gl.addWidget(lbl_sc, 1, 2); gl.addWidget(r2, 1, 3)

        self._ae_stroke_w = self._field(gl, 2, 0, "Độ rộng viền", "0.060")
        self._ae_font_size = self._field(gl, 2, 1, "Font Size", "5.0")
        self._ae_scale = self._field(gl, 2, 2, "Scale segment", "1.490")
        
        self._ae_pos_y = self._field(gl, 3, 0, "Vị trí Y", "-0.893")
        self._ae_lmw = self._field(gl, 3, 1, "Max width", "0.82")

        v.addWidget(gw)

        align_row = QWidget()
        align_row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        al = QHBoxLayout(align_row); al.setContentsMargins(0, 0, 0, 0); al.setSpacing(16)
        lbl_al = QLabel("Canh lề:"); lbl_al.setStyleSheet("color:#606770; font-weight:bold; background: transparent; border: none;"); al.addWidget(lbl_al)
        
        self._ae_align_grp = QButtonGroup(self)
        self._ae_align_btns = []
        for i, label in enumerate(["◀ Trái", "■ Giữa", "Phải ▶"]):
            rb = QRadioButton(label)
            rb.setStyleSheet("color:#1C1E21;")
            if i == 1: rb.setChecked(True)
            self._ae_align_grp.addButton(rb, i)
            al.addWidget(rb)
            self._ae_align_btns.append(rb)
        al.addStretch()
        v.addWidget(align_row)

        lay.addWidget(card)

    def _build_ae_grp_intro_outro(self, lay):
        card, v = self._card("🎬  Intro / Outro", "#17A2B8")

        self._ae_cb_io = QCheckBox("Thêm Intro / Outro tự động")
        self._ae_cb_io.setStyleSheet("QCheckBox{font-size:14px; font-weight:bold; color:#17A2B8; background: transparent; border: none;}")
        v.addWidget(self._ae_cb_io)

        self._ae_intro = PathRow("🎞️", "Video Intro", filetypes="Video (*.mp4 *.mov *.avi);;All (*.*)")
        self._ae_outro = PathRow("🎞️", "Video Outro", filetypes="Video (*.mp4 *.mov *.avi);;All (*.*)")
        v.addWidget(self._ae_intro)
        v.addWidget(self._ae_outro)

        hint = QLabel("Duration tự động đọc bằng ffprobe — không cần nhập tay.")
        hint.setStyleSheet("font-size:11px; color:#606770; background: transparent; border: none;")
        v.addWidget(hint)
        lay.addWidget(card)

    def _build_ae_grp_logo(self, lay):
        card, v = self._card("🖼️  Logo Overlay", "#6F42C1")

        self._ae_cb_logo = QCheckBox("Thêm Logo overlay (ảnh PNG xoá nền)")
        self._ae_cb_logo.setStyleSheet("QCheckBox{font-size:14px; font-weight:bold; color:#6F42C1; background: transparent; border: none;}")
        v.addWidget(self._ae_cb_logo)

        self._ae_logo = PathRow("🖼️", "Logo PNG", filetypes="Image (*.png *.jpg *.jpeg);;All (*.*)")
        v.addWidget(self._ae_logo)

        gw = QWidget()
        gw.setStyleSheet(".QWidget { background: transparent; border: none; }")
        gl = QGridLayout(gw); gl.setContentsMargins(0,0,0,0); gl.setSpacing(12)
        
        self._ae_logo_scale = self._field(gl, 0, 0, "Scale", "0.453")
        self._ae_logo_x = self._field(gl, 0, 1, "Tọa độ X", "-0.808")
        self._ae_logo_y = self._field(gl, 0, 2, "Tọa độ Y", "0.805")
        v.addWidget(gw)

        tl_row = QWidget()
        tl_row.setStyleSheet(".QWidget { background: transparent; border: none; }")
        tll = QHBoxLayout(tl_row); tll.setContentsMargins(0, 0, 0, 0); tll.setSpacing(16)
        lbl_tl = QLabel("Timeline:"); lbl_tl.setStyleSheet("color:#606770; font-weight:bold; background: transparent; border: none;"); tll.addWidget(lbl_tl)
        
        self._ae_logo_tl_grp = QButtonGroup(self)
        self._ae_logo_rb_content = QRadioButton("Theo nội dung (bỏ Intro/Outro)")
        self._ae_logo_rb_full    = QRadioButton("Toàn bộ video")
        self._ae_logo_rb_content.setChecked(True)
        self._ae_logo_rb_content.setStyleSheet("color:#1C1E21;")
        self._ae_logo_rb_full.setStyleSheet("color:#1C1E21;")
        
        self._ae_logo_tl_grp.addButton(self._ae_logo_rb_content, 0)
        self._ae_logo_tl_grp.addButton(self._ae_logo_rb_full,    1)
        tll.addWidget(self._ae_logo_rb_content)
        tll.addWidget(self._ae_logo_rb_full)
        tll.addStretch()
        v.addWidget(tl_row)

        hint = QLabel("X/Y chuẩn hoá: -1.0 = trái/dưới · 0.0 = giữa · 1.0 = phải/trên")
        hint.setStyleSheet("font-size:11px; color:#606770; background: transparent; border: none;")
        v.addWidget(hint)
        lay.addWidget(card)

    def _get_auto_edit_config(self) -> dict:
        align_id = self._ae_align_grp.checkedId()
        return {
            "sub_style": {
                "enabled":       self._ae_cb_sub.isChecked(),
                "font_path":     self._ae_font.get(),
                "font_title":    self._ae_font_title.text().strip(),
                "text_color":    self._ae_text_color.text().strip() or "#FFFFFF",
                "stroke_color":  self._ae_stroke_color.text().strip() or "#000000",
                "stroke_width":  float(self._ae_stroke_w.text() or "0.06"),
                "font_size":     float(self._ae_font_size.text() or "5.0"),
                "scale":         float(self._ae_scale.text()    or "1.0"),
                "pos_y":         float(self._ae_pos_y.text()    or "-0.893"),
                "pos_x":         0.0,
                "line_max_width":float(self._ae_lmw.text()      or "0.82"),
                "alignment":     align_id if align_id >= 0 else 1,
            },
            "intro_outro": {
                "enabled":    self._ae_cb_io.isChecked(),
                "intro_path": self._ae_intro.get(),
                "outro_path": self._ae_outro.get(),
            },
            "logo": {
                "enabled":   self._ae_cb_logo.isChecked(),
                "logo_path": self._ae_logo.get(),
                "scale":     float(self._ae_logo_scale.text() or "0.453"),
                "pos_x":     float(self._ae_logo_x.text()     or "-0.808"),
                "pos_y":     float(self._ae_logo_y.text()     or "0.805"),
                "timeline":  "content" if self._ae_logo_rb_content.isChecked() else "full",
            },
        }

    def _any_auto_edit_enabled(self) -> bool:
        return (self._ae_cb_sub.isChecked() or
                self._ae_cb_io.isChecked()  or
                self._ae_cb_logo.isChecked())

    def _browse_drafts(self):
        p = QFileDialog.getExistingDirectory(self, "Chọn thư mục Drafts của CapCut")
        if p:
            self._vcp_entry.setText(p)
            self._cp_status.setText(f"✓ Đã chọn: {p}")
            self._cp_status.setStyleSheet("font-size:11px; color:#28A745; background: transparent;")

    def _detect_drafts_dir(self):
        try:
            import src.config as cfg
            cfg.CAPCUT_DRAFTS_DIR = cfg._find_capcut_drafts()
            if cfg.CAPCUT_DRAFTS_DIR and cfg.CAPCUT_DRAFTS_DIR.exists():
                if not self._vcp_entry.text():
                    self._vcp_entry.setText(str(cfg.CAPCUT_DRAFTS_DIR))
                self._cp_status.setText(f"✓ Tìm thấy tự động: {cfg.CAPCUT_DRAFTS_DIR}")
                self._cp_status.setStyleSheet("font-size:11px; color:#28A745; background: transparent;")
            else:
                self._cp_status.setText("⚠ Không tìm thấy tự động — vui lòng chọn thủ công")
                self._cp_status.setStyleSheet("font-size:11px; color:#FD7E14; background: transparent;")
        except Exception:
            pass

    def _build_right(self, bl):
        right = QFrame()
        right.setStyleSheet("QFrame{background-color:#FFFFFF; border:1px solid #CCD0D5; border-radius:0px;}")
        pv = QVBoxLayout(right); pv.setContentsMargins(0,0,0,0); pv.setSpacing(0)
        bl.addWidget(right, 4)

        hdr = QFrame(); hdr.setFixedHeight(48)
        hdr.setStyleSheet("QFrame{background-color:#F8F9FA; border-radius:0px; border-bottom:1px solid #CCD0D5;}")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(16,0,16,0)
        
        lh = QLabel("📊  Tiến độ & Log Console")
        lh.setStyleSheet("font-weight:bold; font-size:14px; color:#1C1E21; border:none; background:transparent;"); hh.addWidget(lh)
        hh.addStretch()
        
        bc = QPushButton("🗑️  Xoá Log"); bc.setFixedHeight(30)
        bc.setStyleSheet(btn("#DC3545", "#C82333", pad="4px 12px", radius="0px"))
        bc.clicked.connect(lambda: self._log.clear()); hh.addWidget(bc)
        pv.addWidget(hdr)

        sf = QWidget(); sf.setStyleSheet(".QWidget { background:transparent; }")
        sh = QHBoxLayout(sf); sh.setContentsMargins(12,10,12,6); sh.setSpacing(10)
        self._sc_clips   = StatCard("🎞️","Clips xong",  "#007BFF")
        self._sc_elapsed = StatCard("⏱️","Thời gian",   "#17A2B8")
        self._sc_speed   = StatCard("⚡","Tốc độ TB",   "#FD7E14")
        sh.addWidget(self._sc_clips); sh.addWidget(self._sc_elapsed); sh.addWidget(self._sc_speed)
        pv.addWidget(sf)

        self._log = QTextEdit(); self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "QTextEdit{background-color:#F8F9FA; color:#212529; "
            "font-family:Consolas; font-size:11px; border:none; padding:8px; "
            "border-top:1px solid #CCD0D5;}")
        pv.addWidget(self._log, 1)

        pf = QFrame(); pf.setFixedHeight(64)
        pf.setStyleSheet("QFrame{background-color:#FFFFFF; border-top:1px solid #CCD0D5; border-radius:0px;}")
        pl = QVBoxLayout(pf); pl.setContentsMargins(16,12,16,12); pl.setSpacing(6)
        
        self._prog = QProgressBar()
        self._prog.setValue(0); self._prog.setFixedHeight(8); self._prog.setTextVisible(False)
        pl.addWidget(self._prog)
        
        self._status_lbl = QLabel("✨  Sẵn sàng")
        self._status_lbl.setStyleSheet("font-weight:bold; font-size:13px; color:#606770; border:none; background:transparent;")
        pl.addWidget(self._status_lbl)
        
        pv.addWidget(pf)

    def _build_footer(self, main):
        ft = QFrame(); ft.setFixedHeight(80)
        ft.setStyleSheet("QFrame{background-color:#FFFFFF; border-top:1px solid #CCD0D5;}")
        fl = QHBoxLayout(ft); fl.setContentsMargins(24,16,24,16); fl.setSpacing(16)

        self._btn_run = QPushButton("✨  BẮT ĐẦU CHẠY")
        self._btn_run.setFixedHeight(48); self._btn_run.setMinimumWidth(200)
        self._btn_run.setStyleSheet(btn("#007BFF", "#0069D9", pad="10px 24px", radius="0px"))
        self._btn_run.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self._btn_run.clicked.connect(self._run)

        self._btn_stop = QPushButton("🛑  Dừng lại")
        self._btn_stop.setFixedHeight(48); self._btn_stop.setMinimumWidth(140)
        self._btn_stop.setStyleSheet(btn("#DC3545", "#C82333", pad="10px 16px", radius="0px"))
        self._btn_stop.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._btn_stop.setEnabled(False); self._btn_stop.clicked.connect(self._stop)

        self._btn_rebuild = QPushButton("🔄  Tạo lại Draft")
        self._btn_rebuild.setFixedHeight(48); self._btn_rebuild.setMinimumWidth(160)
        self._btn_rebuild.setStyleSheet(btn("#FD7E14", "#E37012", pad="10px 16px", radius="0px"))
        self._btn_rebuild.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._btn_rebuild.clicked.connect(self._rebuild_draft)

        self._btn_out = QPushButton("📂  Mở Output")
        self._btn_out.setFixedHeight(48); self._btn_out.setMinimumWidth(140)
        self._btn_out.setStyleSheet(btn("#17A2B8", "#138496", pad="10px 16px", radius="0px"))
        self._btn_out.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._btn_out.clicked.connect(self._open_out)

        fl.addWidget(self._btn_run); fl.addWidget(self._btn_stop)
        fl.addWidget(self._btn_rebuild); fl.addWidget(self._btn_out)
        fl.addStretch()

        hint = QLabel("© 2025 Văn Khải")
        hint.setStyleSheet("font-style:italic; color:#606770; font-size:12px; border:none; font-weight:bold; background:transparent;")
        fl.addWidget(hint)
        main.addWidget(ft)

    # ── Pumps ─────────────────────────────────────────────────────────────────
    def _pump_log(self):
        MAX_LINES = 500
        lines = []
        try:
            for _ in range(50):
                _, msg, _ = LOG_Q.get_nowait()
                lines.append(msg)
        except queue.Empty:
            pass
        if not lines:
            return
        self._log.moveCursor(QTextCursor.End)
        self._log.insertPlainText("\n".join(lines) + "\n")
        self._log.moveCursor(QTextCursor.End)
        doc = self._log.document()
        while doc.blockCount() > MAX_LINES:
            cursor = QTextCursor(doc.begin())
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

    def _pump_ui(self):
        last_fn = None
        try:
            for _ in range(200):
                last_fn = UI_Q.get_nowait()
        except queue.Empty:
            pass
        if last_fn is not None:
            last_fn()

    def _tick_elapsed(self):
        if self._running and self._start_time:
            s = int(time.perf_counter() - self._start_time)
            m, sc = divmod(s, 60)
            self._sc_elapsed.set_value(f"{m:02d}:{sc:02d}", "#17A2B8")

    def _ui(self, fn):   UI_Q.put(fn)
    def _emit(self, msg, tag="info"): LOG_Q.put(("log", msg, tag))
    def _set_status(self, txt, color="#007BFF"):
        self._ui(lambda: self._status_lbl.setText(f"  {txt}"))
        self._ui(lambda: self._status_lbl.setStyleSheet(
            f"font-weight:bold; font-size:13px; color:{color}; border:none; background:transparent;"))

    # ── Run / Stop ────────────────────────────────────────────────────────────
    def _validate(self):
        errs = []
        if not self._pv.get() or not Path(self._pv.get()).exists(): errs.append("Video gốc")
        if not self._ps.get() or not Path(self._ps.get()).exists(): errs.append("Tệp .srt")
        if not self._pa.get() or not Path(self._pa.get()).is_dir(): errs.append("Thư mục audios")
        cp = self._vcp_entry.text().strip() if self._vcp_entry else ""
        if not cp or not Path(cp).is_dir(): errs.append("Thư mục Drafts của CapCut")
        if errs:
            QMessageBox.warning(self, "Thiếu dữ liệu",
                                "Vui lòng kiểm tra lại:\n" + "\n".join(f"  • {e}" for e in errs))
            return False
        return True

    def _apply_cfg(self):
        try:
            import src.config as cfg
            if self._pv.get(): cfg.VIDEO_PATH   = Path(self._pv.get())
            if self._ps.get(): cfg.SRT_PATH     = Path(self._ps.get())
            if self._pa.get(): cfg.AUDIO_FOLDER = Path(self._pa.get())
            cfg.WIDTH     = int(self._vw.text().strip())
            cfg.HEIGHT    = int(self._vh.text().strip())
            cfg.FPS       = int(self._vfps.text().strip())
            cfg.MIN_SPEED = float(self._vmn.text().strip())
            cfg.MAX_SPEED = float(self._vmx.text().strip())
            cp = self._vcp_entry.text().strip() if self._vcp_entry else ""
            if cp: cfg.CAPCUT_DRAFTS_DIR = Path(cp)

            os.environ["FFMPEG_CPU_THREADS"] = self._vcpu.text().strip()
            os.environ["ENCODE_WORKERS"]     = self._venc_w.text().strip()
            os.environ["CUT_WORKERS"]        = self._vcut_w.text().strip()

        except Exception as e:
            self._emit(f"[WARN] cấu hình: {e}", "warn")

    def _run(self, dry=False):
        if self._running: return
        if not self._validate(): return
        self._running = True; self._stop_event.clear()
        self._start_time = time.perf_counter()
        self._btn_run.setEnabled(False); self._btn_run.setText("⏳  ĐANG XỬ LÝ...")
        self._btn_stop.setEnabled(True)
        self._prog.setValue(4)
        self._set_status("Đang khởi tạo...", "#007BFF")
        self._sc_clips.set_value("0"); self._sc_elapsed.set_value("00:00"); self._sc_speed.set_value("—")
        if self._o_dbg.isChecked(): logging.getLogger().setLevel(logging.DEBUG)
        self._apply_cfg(); self._save()

        def worker():
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetThreadPriority(
                        ctypes.windll.kernel32.GetCurrentThread(), -1)
                except Exception:
                    pass

            try:
                import src.config as cfg

                import importlib, src.video_processor as vp
                importlib.reload(vp)

                from src.capcut_client import CapCutClient

                cp_entry = getattr(self, "_vcp_entry", None)
                if cp_entry and cp_entry.text().strip():
                    cfg.CAPCUT_DRAFTS_DIR = Path(cp_entry.text().strip())

                # ── BUOC 1/3: Doc SRT + Audio ─────────────────────────────
                self._ui(lambda: (
                    self._prog.setValue(2),
                    self._set_status("Bước 1/3 — Đọc SRT và Audio...", "#007BFF")))
                self._emit("=" * 48, "info")
                self._emit("BƯỚC 1/3 — Đọc file đầu vào", "info")

                audio_files = vp.collect_audio_files(cfg.AUDIO_FOLDER)
                segments    = vp.parse_srt(cfg.SRT_PATH)
                total       = len(segments)

                if len(audio_files) < total:
                    raise RuntimeError(
                        f"Thiếu audio: cần {total}, có {len(audio_files)}")

                self._emit(f"  SRT        : {total} segments", "info")
                self._emit(f"  Audio      : {len(audio_files)} files", "info")
                self._emit(f"  Encoder    : {vp._ENCODER_LABEL}", "info")
                self._emit(f"  CPU Threads: {vp._FFMPEG_CPU_THREADS} / {os.cpu_count()} nhân", "info")
                self._emit(f"  Enc Workers : {vp.ENCODE_WORKERS}", "info")
                self._ui(lambda: (
                    self._prog.setValue(5),
                    self._set_status(f"Bước 1/3 xong — {total} segments", "#28A745")))

                if dry:
                    self._emit("DRY RUN — Input hop le!", "ok")
                    self._ui(lambda: self._on_done(True))
                    return

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ"))
                    return

                # ── BUOC 2A/3: Cat clips (stream copy) ────────────────────
                self._emit("=" * 48, "info")
                self._emit("BƯỚC 2A/3 — Cắt clips (stream copy)...", "info")
                self._ui(lambda: (
                    self._prog.setValue(5),
                    self._set_status("Bước 2A — Đang cắt clips...", "#007BFF"),
                    self._sc_clips.set_value(f"0/{total}"),
                    self._sc_speed.set_value("CUT")))

                cfg.ADJUSTED_CLIPS.mkdir(parents=True, exist_ok=True)
                raw_dir = cfg.ADJUSTED_CLIPS / "_raw_cuts"

                _cut_last_ui = [0.0]
                def on_cut(done, tot, name, skipped):
                    if self._stop_event.is_set(): return
                    pct = 5 + int(done / tot * 35)
                    if done % 100 == 0 or done == tot:
                        self._emit(
                            f"  Cat [{done:03d}/{tot:03d}] {'SKIP' if skipped else ' OK '}  {name}", "clip")
                    now = time.perf_counter()
                    if now - _cut_last_ui[0] >= 0.5 or done == tot:
                        _cut_last_ui[0] = now
                        self._ui(lambda p=pct, d=done, t=tot: (
                            self._prog.setValue(p),
                            self._sc_clips.set_value(
                                f"{d}/{t}", "#FD7E14" if d < t else "#28A745"),
                            self._set_status(f"Cắt clip {d}/{t}  ({p}%)", "#FD7E14")))

                infos = vp.cut_all_clips(
                    segments, audio_files[:total],
                    cfg.VIDEO_PATH, raw_dir,
                    skip_existing=True,
                    progress_cb=on_cut,
                    stop_event=self._stop_event,
                )

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ")); return

                self._emit(f"  Cắt xong {total} clips", "ok")

                # ── BUOC 2B/3: Encode clips (GPU/CPU) ─────────────────────
                self._emit("=" * 48, "info")
                self._emit(f"BƯỚC 2B/3 — Encode clips ({vp._ENCODER_LABEL})...", "info")
                self._ui(lambda: (
                    self._prog.setValue(40),
                    self._set_status(f"Bước 2B — Encode ({vp._ENCODER_LABEL})...", "#6F42C1"),
                    self._sc_clips.set_value(f"0/{total}"),
                    self._sc_speed.set_value("ENC")))

                _enc_last_ui = [0.0]
                def on_encode(done, tot, name, skipped):
                    if self._stop_event.is_set(): return
                    spd  = infos[done-1]["speed"] if (infos[done-1] if done <= len(infos) else None) else 1.0
                    pct  = 40 + int(done / tot * 40)
                    if done % 100 == 0 or done == tot:
                        tag = "SKIP" if skipped else " ENC"
                        self._emit(
                            f"  Enc [{done:03d}/{tot:03d}] [{tag}]  "
                            f"speed={spd:.2f}x  {name}", "clip")
                    now = time.perf_counter()
                    if now - _enc_last_ui[0] >= 0.5 or done == tot:
                        _enc_last_ui[0] = now
                        self._ui(lambda p=pct, d=done, t=tot, s=spd: (
                            self._prog.setValue(p),
                            self._sc_clips.set_value(
                                f"{d}/{t}", "#28A745" if d == t else "#6F42C1"),
                            self._sc_speed.set_value(f"{s:.2f}x"),
                            self._set_status(f"Encode clip {d}/{t}  ({p}%)", "#6F42C1")))

                results = vp.encode_all_clips(
                    infos, cfg.ADJUSTED_CLIPS,
                    skip_existing=True,
                    progress_cb=on_encode,
                    stop_event=self._stop_event,
                )

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ")); return

                import shutil as _shutil
                try: _shutil.rmtree(raw_dir)
                except Exception: pass

                self._emit(f"  Encode xong {total} clips", "ok")

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ")); return

                # ── BUOC 3/3: Tao CapCut draft ────────────────────────────
                self._emit("=" * 48, "info")
                self._emit("BƯỚC 3/3 — Tạo CapCut draft (pycapcut)", "info")
                self._ui(lambda: (
                    self._prog.setValue(82),
                    self._set_status("Bước 3/3 — Đang tạo draft...", "#6F42C1")))

                import time as _time
                draft_name = f"AutoSync_{cfg.SRT_PATH.stem}_{int(_time.time())}"
                client = CapCutClient(drafts_dir=cfg.CAPCUT_DRAFTS_DIR)
                client.create_draft(
                    name=draft_name,
                    width=cfg.WIDTH, height=cfg.HEIGHT, fps=cfg.FPS)

                self._ui(lambda: self._prog.setValue(88))
                total_dur = client.build_timeline(
                    draft_id=draft_name,
                    segments=results,
                    add_subtitles=self._o_sub.isChecked())

                self._ui(lambda: self._prog.setValue(95))
                draft_path = client.save_draft(draft_name)

                self._emit(f"  Draft  : {draft_path}", "ok")
                self._emit(f"  Du lieu: {total_dur:.2f}s", "ok")

                # ── BUOC 4 (tuy chon): Compound Clip ──────────────────────
                compound_mode = self._get_compound_mode()
                if compound_mode != "none":
                    mode_label = {
                        "video": "Compound Video",
                        "audio": "Compound Audio",
                        "both":  "Video + Audio (2 Compound)",
                        "mixed": "Mixed Compound (V+A)",
                    }.get(compound_mode, compound_mode)
                    self._emit("=" * 48, "info")
                    self._emit(f"BUOC 4 — Gop Clip: {mode_label}", "info")
                    self._ui(lambda: (
                        self._prog.setValue(97),
                        self._set_status(f"Đang gộp clip ({mode_label})...", "#007BFF")))
                    try:
                        applied = client.compound_draft(mode=compound_mode)
                        if applied:
                            self._emit(f"  ✓ Đã gộp thành công: {mode_label}", "ok")
                        self._ui(lambda: self._prog.setValue(99))
                    except Exception as ce:
                        self._emit(f"  [WARN] Compound that bai: {ce}", "warn")
                        self._emit("  Draft vẫn được lưu bình thường (chưa gộp).", "warn")
                else:
                    self._ui(lambda: self._prog.setValue(99))

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ"))
                else:
                    # ── BUOC 5 (tuy chon): Auto Edit ──────────────────
                    if self._any_auto_edit_enabled():
                        ae_cfg = self._get_auto_edit_config()
                        self._emit("=" * 48, "info")
                        self._emit("BƯỚC 5 — Auto Edit...", "info")
                        self._ui(lambda: (
                            self._prog.setValue(99),
                            self._set_status("Bước 5 — Auto Edit...", "#FD7E14")))
                        try:
                            from src.draft_editor import auto_edit
                            labels = []
                            if ae_cfg["sub_style"]["enabled"]:
                                labels.append("Style Sub")
                            if ae_cfg["intro_outro"]["enabled"]:
                                labels.append("Intro/Outro")
                            if ae_cfg["logo"]["enabled"]:
                                labels.append("Logo")
                            self._emit(f"  Ap dung: {', '.join(labels)}", "info")
                            auto_edit(draft_path, ae_cfg)
                            self._emit(f"  ✓ Auto Edit hoan tat: {', '.join(labels)}", "ok")
                        except Exception as ae_e:
                            self._emit(f"  [WARN] Auto Edit that bai: {ae_e}", "warn")
                            self._emit("  Draft vẫn được lưu bình thường.", "warn")
                            logging.getLogger("gui").error("Auto Edit error: %s", ae_e, exc_info=True)
                    self._ui(lambda: self._on_done(True))

            except Exception as e:
                logging.getLogger("gui").error("%s", e, exc_info=True)
                err = str(e)
                self._ui(lambda: self._on_done(False, err))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _rebuild_draft(self):
        if self._running: return
        if not self._validate(): return

        import src.config as cfg
        import importlib, sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        import src.video_processor as _vp
        clips_dir = cfg.ADJUSTED_CLIPS
        existing  = _vp.natural_sorted(clips_dir.glob("clip_*.mp4"))
        if not existing:
            QMessageBox.warning(self, "Không có clips",
                f"Không tìm thấy clip nào trong:\n{clips_dir}\n\n"
                "Hãy chạy 'Bắt đầu chạy' để cắt và encode clips trước.")
            return

        reply = QMessageBox.question(
            self, "Tạo lại Draft",
            f"Tìm thấy {len(existing)} clips trong:\n{clips_dir}\n\n"
            "Chương trình sẽ TẠO MỚI DRAFT từ clips này\n"
            "(bỏ qua cắt video, encode).\n\n"
            "Tiếp tục?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply != QMessageBox.Yes:
            return

        self._running = True; self._stop_event.clear()
        self._start_time = time.perf_counter()
        self._btn_run.setEnabled(False)
        self._btn_rebuild.setEnabled(False); self._btn_rebuild.setText("⏳  Đang tạo...")
        self._btn_stop.setEnabled(True)
        self._prog.setValue(2)
        self._set_status("Đang tạo lại draft...", "#FD7E14")
        self._sc_clips.set_value("0"); self._sc_elapsed.set_value("00:00")
        if self._o_dbg.isChecked(): logging.getLogger().setLevel(logging.DEBUG)
        self._apply_cfg(); self._save()

        def worker():
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetThreadPriority(
                        ctypes.windll.kernel32.GetCurrentThread(), -1)
                except Exception: pass

            try:
                import src.config as cfg
                import src.video_processor as vp
                import importlib; importlib.reload(vp)
                from src.capcut_client import CapCutClient

                cp_entry = getattr(self, "_vcp_entry", None)
                if cp_entry and cp_entry.text().strip():
                    cfg.CAPCUT_DRAFTS_DIR = Path(cp_entry.text().strip())

                self._emit("=" * 48, "info")
                self._emit("TẠO LẠI DRAFT — Đọc SRT và Audio...", "info")
                self._ui(lambda: self._prog.setValue(5))

                audio_files = vp.collect_audio_files(cfg.AUDIO_FOLDER)
                segments    = vp.parse_srt(cfg.SRT_PATH)
                total       = len(segments)

                if len(audio_files) < total:
                    raise RuntimeError(f"Thiếu audio: cần {total}, có {len(audio_files)}")

                clips_dir = cfg.ADJUSTED_CLIPS
                clip_files = vp.natural_sorted(clips_dir.glob("clip_*.mp4"))
                n_clips    = len(clip_files)
                self._emit(f"  Clips co san : {n_clips}", "info")
                self._emit(f"  SRT segments : {total}", "info")

                if n_clips < total:
                    raise RuntimeError(f"Clips ({n_clips}) ít hơn segments ({total}). Chạy 'Bắt đầu chạy' để cắt lại.")

                audio_durs = {}
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=8) as ex:
                    fmap = {ex.submit(vp.get_duration, audio_files[i]): i for i in range(total)}
                    for fut in as_completed(fmap):
                        audio_durs[fmap[fut]] = fut.result()

                results = []
                for i, seg in enumerate(segments):
                    orig  = seg["end"] - seg["start"]
                    adur  = audio_durs[i]
                    speed = max(vp.MIN_SPEED, min(vp.MAX_SPEED, orig / adur))
                    results.append({
                        **seg,
                        "clip_path":  clip_files[i],
                        "audio_path": audio_files[i],
                        "audio_dur":  adur,
                        "speed":      speed,
                    })

                self._emit(f"  Dùng {n_clips} clips có sẵn (bỏ qua FFmpeg)", "ok")
                self._ui(lambda: (
                    self._prog.setValue(50),
                    self._set_status(f"Đang tạo draft từ {n_clips} clips...", "#FD7E14")))

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ")); return

                self._emit("=" * 48, "info")
                self._emit("Tạo CapCut draft (pycapcut)...", "info")
                import time as _time
                draft_name = f"AutoSync_{cfg.SRT_PATH.stem}_{int(_time.time())}"
                client = CapCutClient(drafts_dir=cfg.CAPCUT_DRAFTS_DIR)
                client.create_draft(
                    name=draft_name,
                    width=cfg.WIDTH, height=cfg.HEIGHT, fps=cfg.FPS)

                self._ui(lambda: self._prog.setValue(70))
                total_dur = client.build_timeline(
                    draft_id=draft_name,
                    segments=results,
                    add_subtitles=self._o_sub.isChecked())

                self._ui(lambda: self._prog.setValue(85))
                _app_ver, _new_ver = self._get_patch_versions()
                draft_path = client.save_draft(
                    draft_name,
                    target_version=_app_ver,
                    target_new_version=_new_ver,
                )
                self._emit(f"  Draft  : {draft_path}", "ok")
                self._emit(f"  Du lieu: {total_dur:.2f}s", "ok")

                if self._stop_event.is_set():
                    self._ui(lambda: self._on_done(False, "ĐÃ HUỶ")); return

                compound_mode = self._get_compound_mode()
                if compound_mode != "none":
                    mode_label = {
                        "video": "Compound Video", "audio": "Compound Audio",
                        "both":  "Video + Audio (2 Compound)",
                        "mixed": "Mixed Compound (V+A)",
                    }.get(compound_mode, compound_mode)
                    self._emit(f"Gop Clip: {mode_label}...", "info")
                    self._ui(lambda: self._prog.setValue(90))
                    try:
                        client.compound_draft(mode=compound_mode)
                        self._emit(f"  ✓ {mode_label}", "ok")
                    except Exception as ce:
                        self._emit(f"  [WARN] Compound that bai: {ce}", "warn")

                if self._any_auto_edit_enabled():
                    ae_cfg = self._get_auto_edit_config()
                    labels = []
                    if ae_cfg["sub_style"]["enabled"]:   labels.append("Style Sub")
                    if ae_cfg["intro_outro"]["enabled"]: labels.append("Intro/Outro")
                    if ae_cfg["logo"]["enabled"]:        labels.append("Logo")
                    self._emit(f"Auto Edit: {', '.join(labels)}...", "info")
                    self._ui(lambda: self._prog.setValue(95))
                    try:
                        from src.draft_editor import auto_edit
                        auto_edit(draft_path, ae_cfg)
                        self._emit(f"  ✓ Auto Edit: {', '.join(labels)}", "ok")
                    except Exception as ae_e:
                        self._emit(f"  [WARN] Auto Edit that bai: {ae_e}", "warn")
                        logging.getLogger("gui").error("Auto Edit error: %s", ae_e, exc_info=True)

                self._ui(lambda: self._on_done(True))

            except Exception as e:
                logging.getLogger("gui").error("%s", e, exc_info=True)
                err = str(e)
                self._ui(lambda: self._on_done(False, err))

        threading.Thread(target=worker, daemon=True).start()

    def _stop(self):
        if not self._running: return
        self._stop_event.set()
        self._set_status("Đang dừng...", "#FD7E14")
        self._emit("[STOP] Yêu cầu dừng...", "stop")
        self._btn_stop.setEnabled(False); self._btn_stop.setText("Đang dừng...")

    def _on_done(self, ok, err=""):
        self._running = False
        self._btn_run.setEnabled(True); self._btn_run.setText("✨  BẮT ĐẦU CHẠY")
        self._btn_stop.setEnabled(False); self._btn_stop.setText("🛑  Dừng lại")
        self._btn_rebuild.setEnabled(True); self._btn_rebuild.setText("🔄  Tạo lại Draft")
        if ok:
            self._prog.setValue(100); self._set_status("✅  Hoàn thành!", "#28A745")
            elapsed = int(time.perf_counter() - self._start_time); m, s = divmod(elapsed, 60)
            self._sc_elapsed.set_value(f"{m:02d}:{s:02d}", "#28A745")
            QMessageBox.information(self, "Hoàn Thành!",
                "Draft CapCut đã sẵn sàng!\n"
                "Mở CapCut → làm mới danh sách draft\n"
                "(Nếu chưa thấy: vào 1 draft khác rồi quay lại)")
        elif err == "ĐÃ HUỶ":
            self._prog.setValue(0); self._set_status("Đã dừng", "#FD7E14")
        else:
            self._prog.setValue(0); self._set_status("Lỗi", "#DC3545")
            QMessageBox.critical(self, "Lỗi", f"{err}\n\nXem Log de biet chi tiet.")

    # ── Misc ──────────────────────────────────────────────────────────────────
    def _open_out(self):
        out = ROOT / "outputs"; out.mkdir(exist_ok=True)
        if sys.platform == "win32": os.startfile(str(out))
        else: subprocess.Popen(["xdg-open", str(out)])

    def _restore(self):
        s = self._cfg
        if s.get("v"):    self._pv.set(s["v"])
        if s.get("s"):    self._ps.set(s["s"])
        if s.get("a"):    self._pa.set(s["a"])
        if s.get("w"):    self._vw.setText(str(s["w"]))
        if s.get("h"):    self._vh.setText(str(s["h"]))
        if s.get("fps"):  self._vfps.setText(str(s["fps"]))
        if s.get("mn"):   self._vmn.setText(str(s["mn"]))
        if s.get("mx"):   self._vmx.setText(str(s["mx"]))
        if s.get("sub"):  self._o_sub.setChecked(bool(s["sub"]))
        if s.get("cpu"):  self._vcpu.setText(str(s["cpu"]))
        if s.get("encw"): self._venc_w.setText(str(s["encw"]))
        if s.get("cutw"): self._vcut_w.setText(str(s["cutw"]))
        
        cm = s.get("compound", "none")
        self._cb_compound_video.setChecked(cm in ("video", "both"))
        self._cb_compound_audio.setChecked(cm in ("audio", "both"))
        self._cb_compound_mixed.setChecked(cm == "mixed")
        if s.get("cp_dir") and getattr(self, "_vcp_entry", None):
            self._vcp_entry.setText(s["cp_dir"])

        if s.get("capcut_ver"):
            self._set_version_combo(s["capcut_ver"])
            self._update_ver_badge()
            
        ae = s.get("ae", {})
        if ae.get("sub_en"):     self._ae_cb_sub.setChecked(True)
        if ae.get("font"):       self._ae_font.set(ae["font"])
        if ae.get("font_title"): self._ae_font_title.setText(ae["font_title"])
        if ae.get("tc"):         self._ae_text_color.setText(ae["tc"])
        if ae.get("sc"):         self._ae_stroke_color.setText(ae["sc"])
        if ae.get("sw"):         self._ae_stroke_w.setText(ae["sw"])
        if ae.get("font_size"):  self._ae_font_size.setText(ae["font_size"])
        if ae.get("scale"):      self._ae_scale.setText(ae["scale"])
        if ae.get("pos_y"):      self._ae_pos_y.setText(ae["pos_y"])
        if ae.get("lmw"):        self._ae_lmw.setText(ae["lmw"])
        if ae.get("align") is not None:
            idx = ae["align"]
            if 0 <= idx < len(self._ae_align_btns):
                self._ae_align_btns[idx].setChecked(True)
        if ae.get("io_en"):    self._ae_cb_io.setChecked(True)
        if ae.get("intro"):    self._ae_intro.set(ae["intro"])
        if ae.get("outro"):    self._ae_outro.set(ae["outro"])
        if ae.get("logo_en"):  self._ae_cb_logo.setChecked(True)
        if ae.get("logo"):     self._ae_logo.set(ae["logo"])
        if ae.get("logo_sc"):  self._ae_logo_scale.setText(ae["logo_sc"])
        if ae.get("logo_x"):   self._ae_logo_x.setText(ae["logo_x"])
        if ae.get("logo_y"):   self._ae_logo_y.setText(ae["logo_y"])
        if ae.get("logo_tl") == "full":
            self._ae_logo_rb_full.setChecked(True)

    def _save(self):
        save_cfg({
            "v":   self._pv.get(),
            "s":   self._ps.get(),
            "a":   self._pa.get(),
            "w":   self._vw.text(),
            "h":   self._vh.text(),
            "fps": self._vfps.text(),
            "mn":  self._vmn.text(),
            "mx":  self._vmx.text(),
            "sub": self._o_sub.isChecked(),
            "cpu": self._vcpu.text(),
            "encw":self._venc_w.text(),
            "cutw":self._vcut_w.text(),
            "compound": self._get_compound_mode(),
            "cp_dir": (self._vcp_entry.text().strip() if getattr(self, "_vcp_entry", None) else ""),
            "capcut_ver": self._ver_combo.currentText().replace("CapCut  ", "").strip(),
            "ae": {
                "sub_en":    self._ae_cb_sub.isChecked(),
                "font":      self._ae_font.get(),
                "font_title":self._ae_font_title.text(),
                "tc":        self._ae_text_color.text(),
                "sc":        self._ae_stroke_color.text(),
                "sw":        self._ae_stroke_w.text(),
                "font_size": self._ae_font_size.text(),
                "scale":     self._ae_scale.text(),
                "pos_y":     self._ae_pos_y.text(),
                "lmw":       self._ae_lmw.text(),
                "align":     self._ae_align_grp.checkedId(),
                "io_en":     self._ae_cb_io.isChecked(),
                "intro":     self._ae_intro.get(),
                "outro":     self._ae_outro.get(),
                "logo_en":   self._ae_cb_logo.isChecked(),
                "logo":      self._ae_logo.get(),
                "logo_sc":   self._ae_logo_scale.text(),
                "logo_x":    self._ae_logo_x.text(),
                "logo_y":    self._ae_logo_y.text(),
                "logo_tl":   ("full" if self._ae_logo_rb_full.isChecked() else "content"),
            },
        })

    def closeEvent(self, event):
        self._save(); event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    app.setStyleSheet(APP_STYLE)
    win = App(); win.show()
    sys.exit(app.exec_())