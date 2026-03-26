@echo off
chcp 65001 > nul
echo Xoa clip cu (da bi trung lap vi bug cu)...
echo.

set CLIPS=outputs\adjusted_clips

if exist "%CLIPS%" (
    echo Dang xoa: %CLIPS%\*.mp4
    del /Q "%CLIPS%\*.mp4" 2>nul
    del /Q /S "%CLIPS%\_raw\*" 2>nul
    rd /S /Q "%CLIPS%\_raw" 2>nul
    rd /S /Q "%CLIPS%\_raw_cuts" 2>nul
    echo Xong. Folder %CLIPS% da sach.
) else (
    echo Khong tim thay folder %CLIPS% - OK, khong can xoa.
)

echo.
echo Bay gio chay lai gui.py de tao clip moi (chinh xac).
pause
