---
name: python-build-exe
description: Hướng dẫn chuẩn hoá quy trình đóng gói ứng dụng Python GUI (CustomTkinter, Tkinter, PyQt, PySide) sang file thực thi (.exe) bằng PyInstaller với cấu trúc thư mục sạch trong .agents/dist và .agents/build.
---

# Kỹ năng: Đóng Gói Ứng Dụng Python Sang EXE Chuẩn Chuyên Nghiệp (PyInstaller Clean Output)

Kỹ năng này cung cấp tiêu chuẩn đóng gói ứng dụng Python sang file thực thi `.exe` độc lập cho hệ điều hành Windows, chuyển toàn bộ thư mục xuất bản (`dist`) và thư mục tạm (`build`) vào trong `.agents/` để giữ không gian thư mục gốc của dự án luôn sạch sẽ.

---

## 1. Nguyên Tắc Cốt Lõi (Architecture Rules)

### 1.1. Không can thiệp sửa code nghiệp vụ / UI
- Ứng dụng khi chạy dưới dạng `.exe` cần xác định đường dẫn động thông qua hàm chuẩn `get_app_dir()` và `get_resource_path()`:
  - Khi chạy code trực tiếp (`python main.py`): Lấy `__file__`.
  - Khi chạy `.exe` đóng gói: Lấy `sys.executable` (hoặc `sys._MEIPASS` cho tài nguyên tạm).
- Do đó, **vị trí thư mục build không làm ảnh hưởng đến code logic bên trong ứng dụng**.

### 1.2. Chuẩn hoá thư mục đầu ra
- Thư mục thành phẩm (Dist): `.agents/dist/`
- Thư mục làm việc tạm (Work/Build): `.agents/build/`
- Giúp thư mục gốc dự án gọn gàng, không bị rác bởi các file `.obj`, `.toc`, `.tlog`.

---

## 2. Các Lựa Chọn Đóng Gói (3 Chế độ tiêu chuẩn)

Khi triển khai đóng gói cho bất kỳ ứng dụng nào, luôn cung cấp 3 chế độ này:

### [Lựa chọn 1] Đóng gói 1 FILE EXE DUY NHẤT (Single Portable File - `--onefile`)
- **Đầu ra**: `.agents/dist/[AppName].exe`
- **Đặc điểm**:
  - Toàn bộ thư viện, Python runtime và file nén vào đúng 1 file duy nhất.
  - Rất tiện copy nhanh gửi cho người khác, không sợ thiếu file phụ thuộc.
  - Tự động đồng bộ các thư mục cấu hình đi kèm (ví dụ: `presets/`, `config/`) đặt cùng cấp với `.exe`.

### [Lựa chọn 2] Đóng gói THƯ MỤC PORTABLE (Fast Startup - `--onedir`)
- **Đầu ra**: `.agents/dist/[AppName]/[AppName].exe`
- **Đặc điểm**:
  - Tốc độ khởi động tức thì (không mất thời gian giải nén mỗi lần mở).
  - Thích hợp cho các app lớn có nhiều tài nguyên âm thanh, hình ảnh, model AI.

### [Lựa chọn 3] Đóng gói THƯ MỤC PORTABLE + NÉN ZIP SẴN SÀNG CHIA SẺ
- **Đầu ra**: `.agents/dist/[AppName]_Portable.zip`
- **Đặc điểm**:
  - Tự động đóng gói thư mục Portable và nén lại thành file `.zip` hoàn chỉnh.
  - Người dùng tải về giải nén ra là sử dụng ngay.

---

## 3. Template Code Mẫu: `app/utils.py` (Định Tuyến Đường Dẫn Runtime)

Bất kỳ dự án nào cũng cần hàm này trong `utils.py` để tương thích 100% với cả môi trường dev và `.exe`:

```python
import os
import sys

def get_app_dir() -> str:
    """Trả về thư mục gốc của ứng dụng (dù chạy file .py hay file .exe)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path: str) -> str:
    """Lấy đường dẫn tuyệt đối đến tài nguyên (hỗ trợ cả PyInstaller _MEIPASS)."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_path):
            return meipass_path
    return os.path.join(get_app_dir(), relative_path)
```

---

## 4. Template Code Mẫu: `build_exe.py` (Universal Builder cho mọi App)

Đặt file `build_exe.py` tại thư mục gốc dự án:

```python
import os
import sys
import subprocess
import shutil
import argparse

# Force UTF-8 on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# CẤU HÌNH DỰ ÁN
# ==============================================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "MyAppName"  # Đổi tên ứng dụng tại đây
ENTRY_POINT = os.path.join(ROOT_DIR, "app", "main.py") # File bootstrap chính

# Thư mục đích chuẩn hóa vào .agents
DIST_DIR = os.path.join(ROOT_DIR, ".agents", "dist")
BUILD_DIR = os.path.join(ROOT_DIR, ".agents", "build")
ICON_FILE = os.path.join(ROOT_DIR, "app_icon.ico")
ASSETS_DIR = os.path.join(ROOT_DIR, "presets") # Hoặc thư mục data, assets


def kill_existing_processes():
    """Tắt tiến trình cũ để tránh lỗi file đang bị khoá khi ghi đè."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe", "/T"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def clean_artifacts():
    """Dọn dẹp thư mục build tạm và cache."""
    print("[*] Đang dọn dẹp thư mục build tạm và cache...")
    dirs_to_clean = [
        BUILD_DIR,
        os.path.join(ROOT_DIR, "build"),
        os.path.join(ROOT_DIR, "__pycache__"),
    ]
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    print("    [OK] Đã dọn dẹp sạch sẽ.")


def sync_assets(target_dir):
    """Đồng bộ các file cấu hình và icon vào thư mục đích."""
    os.makedirs(target_dir, exist_ok=True)
    
    if os.path.exists(ASSETS_DIR):
        dst_assets = os.path.join(target_dir, os.path.basename(ASSETS_DIR))
        os.makedirs(dst_assets, exist_ok=True)
        for item in os.listdir(ASSETS_DIR):
            s = os.path.join(ASSETS_DIR, item)
            d = os.path.join(dst_assets, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
            elif os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)

    if os.path.exists(ICON_FILE):
        shutil.copy2(ICON_FILE, os.path.join(target_dir, os.path.basename(ICON_FILE)))


def build_app(mode="onedir", make_zip=False, clean=True):
    print("=" * 70)
    print(f"  ⚡ {APP_NAME} - EXECUTABLE BUILDER (PyInstaller) ⚡")
    print(f"  - Chế độ:    {mode.upper()}")
    print(f"  - Dist Path: {DIST_DIR}")
    print(f"  - Work Path: {BUILD_DIR}")
    print("=" * 70)

    kill_existing_processes()
    if clean:
        clean_artifacts()

    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "-y",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--name={APP_NAME}",
        "--noconsole",
        # Khai báo các hidden-import thường gặp:
        "--collect-all=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
    ]

    if os.path.exists(ICON_FILE):
        cmd.append(f"--icon={ICON_FILE}")
        cmd.append(f"--add-data={ICON_FILE};.")

    if os.path.exists(ASSETS_DIR):
        cmd.append(f"--add-data={ASSETS_DIR};{os.path.basename(ASSETS_DIR)}")

    if mode == "onefile":
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.append(ENTRY_POINT)

    print("\n[*] Đang thực thi lệnh đóng gói...")
    res = subprocess.run(cmd, cwd=ROOT_DIR)

    if res.returncode != 0:
        print(f"\n[ERROR] Đóng gói thất bại với mã lỗi: {res.returncode}")
        return False

    print("\n[*] Đang đồng bộ tài nguyên đi kèm...")
    if mode == "onefile":
        exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
        sync_assets(DIST_DIR)
        print("\n" + "=" * 70)
        print(f"  🎉 ĐÓNG GÓI THÀNH CÔNG (1 File EXE duy nhất)!")
        print(f"  - File chạy: {exe_path}")
        print("=" * 70)
    else:
        app_dir = os.path.join(DIST_DIR, APP_NAME)
        exe_path = os.path.join(app_dir, f"{APP_NAME}.exe")
        sync_assets(app_dir)

        zip_path = None
        if make_zip:
            print("\n[*] Đang nén file ZIP Portable...")
            zip_base = os.path.join(DIST_DIR, f"{APP_NAME}_Portable")
            shutil.make_archive(zip_base, "zip", DIST_DIR, APP_NAME)
            zip_path = f"{zip_base}.zip"

        print("\n" + "=" * 70)
        print(f"  🎉 ĐÓNG GÓI THÀNH CÔNG (Thư mục Portable)!")
        print(f"  - Thư mục app: {app_dir}")
        print(f"  - File chạy:   {exe_path}")
        if zip_path:
            print(f"  - File ZIP:    {zip_path}")
        print("=" * 70)

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Application Exe Packager")
    parser.add_argument("--mode", choices=["onefile", "onedir", "1", "2"], default=None)
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    if args.clean:
        clean_artifacts()
    elif args.mode:
        m = "onefile" if args.mode in ["onefile", "1"] else "onedir"
        build_app(mode=m, make_zip=args.zip)
    else:
        # Chạy mặc định hoặc hiển thị menu
        build_app(mode="onedir", make_zip=False)
```

---

## 5. Cập Nhật `.gitignore`

Luôn thêm các dòng sau vào `.gitignore` của dự án để tránh đẩy các file build nặng lên git:

```gitignore
build/
dist/
.agents/build/
.agents/dist/
__pycache__/
*.pyc
*.spec
```

---

## 6. Lệnh Triển Khai Nhanh Khi Người Dùng Yêu Cầu

Khi người dùng yêu cầu: *"Đóng gói app này sang exe"* hoặc *"Áp dụng skill python-build-exe"*, bạn thực hiện:
1. Kiểm tra entry point chính và các thư mục tài nguyên (`presets`, `assets`, `icons`).
2. Tạo file `build_exe.py` và `build_exe.bat` với đường dẫn xuất vào `.agents/dist` và `.agents/build`.
3. Cập nhật `.gitignore`.
4. Chạy kiểm tra lệnh build:
   - `python build_exe.py --mode=onefile`
   - `python build_exe.py --mode=onedir --zip`

   
   
   ---
name: python-mvc-refactor
description: Hướng dẫn cấu trúc và bóc tách dự án Python GUI (Tkinter, CustomTkinter, PyQt) sang mô hình Kế thừa MVC và Clean Architecture.
---


<!-- Với bộ quy tắc này, lợi ích lớn nhất là anh sẽ không bao giờ rơi vào tình cảnh một file code dài tới 5.000 - 10.000 dòng nữa. Code ngắn gọn, chia theo đúng chức năng (Mạng đi đường Mạng, Giao diện đi đường Giao diện) nên:

Rất hiếm khi bị lỗi vặt (như lỗi gọi nhầm biến, lỗi giao diện đơ vì kẹt vòng lặp).
Nếu có lỗi, anh khoanh vùng và sửa chỉ mất vài giây thay vì phải cuộn chuột tìm kiếm mỏi mắt.
Khi anh làm một dự án hoàn toàn mới: Anh chỉ cần đưa ra yêu cầu (Prompt) với trợ lý AI như sau:

"Hãy tạo cho tôi một ứng dụng tên là [Tên Ứng Dụng], sử dụng CustomTkinter. Hãy áp dụng ngay từ đầu Hướng 4 trong skill python-mvc-refactor để dựng khung dự án nhé."

Lập tức AI sẽ tạo sẵn cho anh thư mục ui/, controllers/, file main.py tách biệt cực kỳ chuyên nghiệp ngay từ dòng code đầu tiên. Anh chỉ việc đắp thêm tính năng vào là xong, rất nhàn hạ và chuẩn kỹ sư phần mềm -->


# Kỹ năng: Tái Cấu Trúc & Xây Dựng Ứng Dụng Python (MVC & Clean Architecture)

Kỹ năng này cung cấp các hướng dẫn chi tiết để thiết lập cấu trúc cho một dự án Python GUI mới, hoặc bóc tách một dự án cũ đang bị phình to (God Object). 

Khi người dùng gọi kỹ năng này, **bạn HÃY đưa ra 5 Hướng bóc tách/cấu trúc dưới đây để người dùng LỰA CHỌN** trước khi tiến hành thực thi.

## Mục Tiêu Cấu Trúc Tổng Thể

```text
app/
├── core/                # Trái tim của ứng dụng (Thread chạy nền, tương tác OS)
├── services/            # Các kết nối ngoài (API, Database, Logic bên thứ 3)
├── auth/                # Hệ thống quản lý người dùng, phân quyền, mã hoá
├── ui/
│   ├── components/      # Các thành phần UI nhỏ dùng chung (Toast, Button...)
│   └── main_window.py   # Chỉ chuyên vẽ giao diện chính (View)
├── controllers/
│   └── main_controller.py # Điều phối sự kiện từ giao diện (Controller)
├── utils.py             # Các hàm tiện ích dùng chung (get_resource_path)
└── main.py              # File Bootstrap duy nhất (Chỉ 15 dòng)
```

## Các Lựa Chọn Triển Khai (Trình bày cho người dùng chọn)

### Hướng Tách 1: Hệ thống Xác thực & Dịch vụ (Auth System & Services)
- **Mục đích**: Cô lập logic người dùng và kết nối mạng khỏi giao diện chính.
- **Hành động**:
  - Tạo `app/services/` chứa logic gọi API, Database.
  - Tạo `app/auth/` (hoặc `app/services/auth.py`) chứa logic mã hoá, đăng nhập, JWT, phân quyền.
  - Tạo `app/ui/auth/` chứa các màn hình giao diện liên quan (Form Đăng nhập, Setup 2FA, Quản lý tài khoản).

### Hướng Tách 2: Module Core (Trái tim của ứng dụng)
- **Mục đích**: Cô lập các luồng xử lý nặng, đa luồng (Threading), và tương tác phần cứng/OS.
- **Hành động**:
  - Tạo thư mục `app/core/`.
  - Gom toàn bộ hàm tương tác hệ điều hành, API gốc vào `app/core/os_helper.py` (hoặc `win32_helper.py`).
  - Tách các class chạy Thread/Worker (Background Tasks) vào `app/core/worker.py`.

### Hướng Tách 3: UI Components (Thành phần giao diện phụ)
- **Mục đích**: Tái sử dụng code giao diện, giảm tải cho file chính.
- **Hành động**:
  - Tạo thư mục `app/ui/components/`.
  - Đưa các thành phần độc lập (Toast Notification, Custom Dialog, Modal phụ, Floating Toolbar) sang các file riêng biệt (ví dụ: `app/ui/components/toast.py`).

### Hướng Tách 4: Tách Kiến trúc chính theo Kế thừa đa tầng (Inheritance-based MVC)
- **Mục đích**: Giải quyết triệt để vấn đề "God Object" nơi class chính vừa vẽ UI (Grid, Layout, Widget) vừa xử lý logic (On Click, Vòng lặp).
- **Phân tích chi tiết**:
  - Thông thường, việc tách View và Controller độc lập (truyền Controller vào View qua tham số) sẽ làm gãy hàng loạt các biến tham chiếu `self.widget_name` hoặc `self.function()` trong các code cũ/code kế thừa.
  - Giải pháp cấu trúc an toàn 100% (và linh hoạt cho cả dự án mới) là sử dụng **Kế thừa đa tầng (Inheritance-based MVC)**:
    1. **Phần Giao Diện (View) - `app/ui/main_window.py`**: Đổi tên class chính thành `MainWindowUI` (Kế thừa từ thư viện GUI gốc, ví dụ CustomTkinter). File này **tuyệt đối chỉ chứa** hàm `__init__` thiết lập giao diện và các hàm khởi tạo layout (như `create_header`, `render_dashboard`). Bóc và xoá bỏ mọi logic tính toán khỏi đây.
    2. **Phần Não Bộ (Controller) - `app/controllers/main_controller.py`**: Tạo class `MainController(MainWindowUI)`. Vì kế thừa trực tiếp từ View, Controller sở hữu nguyên vẹn toàn bộ giao diện đã vẽ. File này sẽ chứa **toàn bộ các hàm xử lý logic** (như `start_macro`, `on_button_click`). Nhờ việc kế thừa, Controller gọi lệnh cập nhật giao diện (VD: `self.label.configure(...)`) hoàn toàn hợp lệ mà không cần định tuyến phức tạp.
    3. **Phần Khởi Chạy (Bootstrap) - `main.py`**: File gốc bị gọt sạch cả logic và UI, chỉ còn vai trò gọi khởi động Controller:
       ```python
       from controllers.main_controller import MainController
       if __name__ == "__main__":
           app = MainController()
           app.mainloop()
       ```

### Hướng Tách 5: Dọn dẹp toàn diện (Kết hợp Hướng 1, 2 và 3)
- **Mục đích**: Dọn dẹp vệ sinh xung quanh file chính một cách triệt để mà chưa cần động chạm đến lõi UI/Logic (Hướng 4). 
- **Hành động**: Thực hiện đồng thời Hướng 1 (Tách Auth/Service), Hướng 2 (Tách Core/Thread), và Hướng 3 (Tách Component). File chính sẽ lập tức giảm được hàng ngàn dòng code râu ria, tạo tiền đề cực kỳ gọn gàng và an toàn tuyệt đối trước khi bước vào Hướng 4 (cuộc đại phẫu thuật chia tách View và Controller).
