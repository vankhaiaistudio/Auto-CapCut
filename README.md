# Auto CapCut Video Sync v1.0

Tự động cắt video, điều chỉnh tốc độ theo audio, và sync vào draft CapCut — **không cần mở tay**.

---

## Cấu trúc thư mục

```
auto-capcut-video-sync/
├── capcut_api/          ← Clone VectCutAPI vào đây
├── inputs/
│   ├── video_goc.mp4
│   ├── subtitle.srt
│   └── audios/
│       ├── audio_001.mp3
│       └── ...
├── outputs/
│   ├── adjusted_clips/
│   └── final_drafts/
├── src/
│   ├── config.py
│   ├── video_processor.py
│   ├── capcut_client.py
│   └── main.py
├── requirements.txt
├── run_server.bat
└── run_project.bat
```

## Yêu cầu hệ thống

- Python 3.10+
- FFmpeg (thêm vào PATH)
- CapCut PC (để mở draft)
- Git

## Setup (lần đầu)

```bash
# 1. Clone dự án
git clone <your-repo> auto-capcut-video-sync
cd auto-capcut-video-sync

# 2. Clone VectCutAPI
git clone https://github.com/sun-guannan/VectCutAPI.git capcut_api

# 3. Tạo virtualenv
python -m venv venv
venv\Scripts\activate   # Windows

# 4. Cài dependencies
pip install -r requirements.txt
pip install -r capcut_api/requirements.txt

# 5. Config VectCutAPI
copy capcut_api\config.json.example capcut_api\config.json
```

## Cách dùng

```bash
# Terminal 1 — khởi động server
python capcut_api/capcut_server.py

# Terminal 2 — chạy dự án
python src/main.py

# Tùy chọn
python src/main.py --subtitles           # thêm subtitle vào timeline
python src/main.py --copy-to-capcut      # auto-copy draft vào CapCut Projects
python src/main.py --dry-run             # kiểm tra input không xử lý
python src/main.py --debug               # log chi tiết
```

## Quy ước đặt tên audio

File audio phải đặt tên theo thứ tự khớp với segments trong SRT:

```
audio_001.mp3  ← segment 1
audio_002.mp3  ← segment 2
...
```

(Sort theo tên file — đảm bảo sort đúng bằng cách dùng 3 chữ số)
