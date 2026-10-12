import os
import sys
import io
import shutil
import subprocess

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul 2>&1")
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

def build():
    print("==========================================================")
    print("🚀 BẮT ĐẦU ĐÓNG GÓI ỨNG DỤNG AI ZALO CSKH THÀNH FILE EXE")
    print("📁 Output Thư Mục: .agents/dist/ & .agents/build/")
    print("==========================================================")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    agents_dir = os.path.join(root_dir, ".agents")
    dist_dir = os.path.join(agents_dir, "dist")
    build_dir = os.path.join(agents_dir, "build")
    icon_path = os.path.join(root_dir, "assets", "app_icon.ico")
    
    os.makedirs(agents_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    if not os.path.exists(icon_path):
        print(f"⚠️ Không tìm thấy icon tại: {icon_path}")
        return

    # Lệnh PyInstaller tối ưu hóa không hiện màn hình đen (No Console)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",                      # Đóng gói dạng thư mục độc lập chạy cực nhanh và ổn định
        "--windowed",                    # Ẩn hoàn toàn cửa sổ dòng lệnh đen (No Console)
        "--name=AI_Zalo_CSKH",
        f"--icon={icon_path}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={build_dir}",
        f"--add-data={os.path.join(root_dir, 'assets')};assets",
        f"--add-data={os.path.join(root_dir, 'config')};config",
        f"--add-data={os.path.join(root_dir, 'knowledge_base')};knowledge_base",
        "--hidden-import=PIL",
        "--hidden-import=PIL._imagingtk",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=google.genai",
        "--hidden-import=google.generativeai",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32process",
        "--hidden-import=win32api",
        "--hidden-import=win32clipboard",
        "--hidden-import=win32timezone",
        "--hidden-import=win32event",
        "--hidden-import=pythoncom",
        "--hidden-import=pywintypes",
        "--hidden-import=psutil",
        "--hidden-import=pyautogui",
        "--hidden-import=cv2",
        "--collect-all=cv2",
        "--hidden-import=pyperclip",
        "--hidden-import=logging.handlers",
        "--hidden-import=ctypes",
        "--hidden-import=ctypes.wintypes",
        "--clean",
        os.path.join(root_dir, "main.py")
    ]

    print("📦 Đang thực thi lệnh PyInstaller...")
    ret = subprocess.call(cmd, cwd=root_dir)
    
    if ret == 0:
        target_app_dir = os.path.join(dist_dir, "AI_Zalo_CSKH")
        
        # Đảm bảo các thư mục cần thiết có sẵn cạnh file .exe để tiện chỉnh sửa
        for folder in ["config", "knowledge_base", "assets", "storage"]:
            src_f = os.path.join(root_dir, folder)
            dst_f = os.path.join(target_app_dir, folder)
            if os.path.exists(src_f) and not os.path.exists(dst_f):
                shutil.copytree(src_f, dst_f)
            elif not os.path.exists(dst_f):
                os.makedirs(dst_f, exist_ok=True)

        # Tạo file ZIP độc lập để tiện gửi qua Zalo / Google Drive / USB
        zip_output = os.path.join(dist_dir, "AI_Zalo_CSKH")
        shutil.make_archive(zip_output, 'zip', target_app_dir)

        # Dọn dẹp thư mục rác ở root nếu có
        for old_dir in [os.path.join(root_dir, "build"), os.path.join(root_dir, "dist")]:
            if os.path.exists(old_dir):
                try:
                    shutil.rmtree(old_dir, ignore_errors=True)
                except Exception:
                    pass

        print("\n==========================================================")
        print("🎉 ĐÓNG GÓI THÀNH CÔNG RỰC RỠ!")
        print(f"📁 Thư mục ứng dụng hoàn chỉnh: {target_app_dir}")
        print(f"⚡ File chạy: {os.path.join(target_app_dir, 'AI_Zalo_CSKH.exe')}")
        print(f"📦 File nén di động: {zip_output}.zip")
        print("💡 Bạn chỉ cần gửi file 'AI_Zalo_CSKH.zip' trong .agents/dist/ sang máy khác, giải nén và chạy ngay!")
        print("==========================================================")
    else:
        print("\n❌ Quá trình đóng gói thất bại. Vui lòng kiểm tra log ở trên.")

if __name__ == "__main__":
    build()
