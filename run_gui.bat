@echo off
chcp 65001 > nul

if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat

python -c "import PyQt5" 2>nul || pip install PyQt5

set FFMPEG_ENCODER=h264_nvenc
set FFMPEG_CPU_THREADS=
set CUT_WORKERS=2
set ENCODE_WORKERS=2

python gui.py
pause
