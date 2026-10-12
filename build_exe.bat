@echo off
chcp 65001 >nul
echo ========================================================
echo  🚀 TIẾN TRÌNH BUILD EXE ỨNG DỤNG AI ZALO CSKH
echo  📁 Thư mục xuất bản: .agents\dist\ & .agents\build\
echo ========================================================
python build_exe.py
echo.
echo ========================================================
echo  Hoàn tất! Kiểm tra thư mục: .agents\dist\
echo ========================================================
echo Nhấn phím bất kỳ để thoát...
pause >nul
