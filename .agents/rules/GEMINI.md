# 🌟 HỆ THỐNG QUY TẮC, BẢO MẬT & NGUYÊN TẮC TỐI ƯU HÓA TOÀN DIỆN (ZALO PC AI AUTOMATION)

Tài liệu này ghi nhận và lưu trữ toàn bộ nguyên lý kiến trúc, bài học kinh nghiệm, quy tắc bảo mật và chuẩn mực lập trình cho hệ thống để AI và lập trình viên luôn tuân thủ, không bao giờ gây lỗi, giật lag hay đơ ứng dụng ("Not Responding").

---

## 📌 1. BÀI HỌC KINH NGHIỆM CỐT LÕI (CRITICAL LESSONS LEARNED)

### ⚠️ 1.1. Lỗi Tự Target Chính Mình (Self-Window Target Bug):
* **Nguyên nhân:** Tiêu đề ứng dụng là `⚡ AI ZALO CSKH...`. Nếu quét cửa sổ chỉ bằng từ khóa `"zalo" in title.lower()`, hệ thống sẽ nhận nhầm chính Dashboard là Zalo PC (`found HWND` trỏ vào chính Dashboard) và paste dữ liệu vào chính mình.
* **Quy tắc bất biến:**
  1. Trong tất cả các hàm dò tìm (`find_zalo_hwnd`, `scan_active_windows`, `pick_window_1click`), **BẮT BUỘC** loại trừ PID của chính Dashboard:
     ```python
     my_pid = os.getpid()
     _, pid = win32process.GetWindowThreadProcessId(hwnd)
     if pid == my_pid:
         return  # TUYỆT ĐỐI BỎ QUA CỬA SỔ CỦA DASHBOARD NÀY!
     if "AI Zalo CSKH" in title or "AI ZALO CSKH" in title or "Quản Lý Giáo Án" in title:
         return
     ```
  2. Ưu tiên khớp theo Process Name chính chủ `zalo.exe` (hoặc lớp `Chrome_WidgetWin_1`) thay vì chỉ quét tiêu đề lỏng lẻo.

### ⚠️ 1.2. Lỗi Đơ Ứng Dụng & Khóa Luồng GUI ("Not Responding" / Thread Lock):
* **Nguyên nhân:**
  1. Khi dùng `AttachThreadInput(curr_thread, fore_thread, True)` mà không detach trong khối `finally`, Windows sẽ gắn chặt hàng đợi tin nhắn của luồng xử lý với ứng dụng ngoài. Khi luồng xử lý ngủ hoặc kết thúc, Dashboard bị khóa cứng thành **"Not Responding"**.
  2. Các hàm từ tiến trình nền (`threading.Thread`) hoặc phím tắt (`HotkeyManager`) gọi trực tiếp hàm Tkinter (`widget.configure`, `widget.insert`, `widget.delete`, `show_toast`, `messagebox`) mà không thông qua `self.after(0, ...)`.
* **Quy tắc bất biến:**
  1. Trong `force_focus_window` và `_restore_foreground`, **BẮT BUỘC** phải có khối `finally` để luôn luôn detach luồng:
     ```python
     finally:
         if attached_thread and curr_thread:
             try:
                 win32process.AttachThreadInput(curr_thread, attached_thread, False)
             except Exception:
                 pass
     ```
  2. Mọi thao tác cập nhật giao diện từ tiến trình nền (`_worker`, `_scan`, `progress_callback`) phải được điều phối qua `self.after(0, ...)` kèm khối `try...except`.
  3. Đặt `pyautogui.FAILSAFE = False` để chống ngắt quãng đột ngột khi con trỏ chuột chạm góc màn hình.

---

## ⚡ 2. NGUYÊN TẮC TỐI ƯU HÓA CPU, RAM & HIỆU NĂNG CAO (HIGH PERFORMANCE)

### 🔹 2.1. Bộ Đệm Process Name (`get_proc_name_cached`):
* **Vấn đề:** Hàm `psutil.Process(pid).name()` tốn rất nhiều chu kỳ CPU của Kernel. Gọi liên tục khi `EnumWindows` duyệt 100+ cửa sổ sẽ làm CPU nhảy vọt 20-30%.
* **Quy tắc:** Luôn dùng `get_proc_name_cached(pid)` với TTL cache 8 giây trong `find_zalo_hwnd`, `scan_active_windows`, `pick_window_1click`. 1.000 truy vấn chỉ tốn **0.19ms** (giảm 99.9% CPU).

### 🔹 2.2. Tối Ưu CSDL SQLite: WAL Mode & RAM Cache:
* **Quy tắc:** Tất cả kết nối SQLite trong `StateManager` phải kích hoạt:
  ```python
  conn = sqlite3.connect(self.db_path, timeout=15.0)
  conn.execute("PRAGMA journal_mode=WAL;")        # Đọc ghi đồng thời không khóa file
  conn.execute("PRAGMA synchronous=NORMAL;")      # Giảm tải đĩa 80%
  conn.execute("PRAGMA cache_size=-64000;")       # Bộ nhớ đệm 64MB RAM
  conn.execute("PRAGMA temp_store=MEMORY;")
  ```
* **Chỉ mục (Indices):** Đảm bảo tạo index trên `chat_messages(session_id)`, `chat_sessions(is_archived, updated_at)`, `users(username)`, `group_broadcast_logs(group_name)`, `conversations(user_id)`, `message_history(user_id)`.

### 🔹 2.3. Chống Rò Rỉ Bộ Nhớ RAM (Anti-Memory Leak):
* **Toast Notification Limiter:** Giới hạn tối đa 3 Toast cùng lúc (`_ACTIVE_TOASTS`), tự hủy các toast cũ để chống tràn màn hình và RAM.
* **PIL Image Handles:** Luôn bọc việc mở ảnh (`Image.open()`) trong `try...finally: if img: img.close()` trong `GeminiEngine` để giải phóng RAM ngay sau khi gửi API.
* **Dọn Rác Định Kỳ:** Kích hoạt `gc.collect()` mỗi 60 giây trong `_track_foreground_window`.
* **Sleep Không Khóa Luồng:** Trong daemon threads (`BroadcastScheduler`), dùng `self._stop_event.wait(timeout=20)` thay vì `time.sleep(20)`.

### 🔹 2.4. Windows Clipboard An Toàn (`safe_clipboard_copy` / `safe_clipboard_paste`):
* Bọc `pyperclip.copy` và `pyperclip.paste` bằng vòng lặp thử lại có delay nhỏ để chống lỗi khi ứng dụng khác tạm thời giữ lock clipboard.

---

## 🔐 3. BẢO MẬT & QUẢN LÝ ĐĂNG NHẬP (SECURITY & AUTHENTICATION)

1. **Bật / Tắt Xác Thực Đăng Nhập (Mặc định BẬT):**
   - Cấu hình `require_login`: Mặc định khi cài đặt hệ thống luôn **BẬT** yêu cầu đăng nhập.
   - Khi người dùng tắt xác thực trong Cài Đặt (Tab 10), Dashboard tự động đăng nhập với vai trò Admin mà không hiển thị modal Login.
2. **Tài Khoản Mặc Định Chuẩn & Chống Lộ Gợi Ý:**
   - Tài khoản mặc định: `admin` / `admin` (mã hóa SHA-256 trong CSDL SQLite).
   - Mặc định khi khởi động, ô Tên đăng nhập và Mật khẩu luôn để **TRỐNG 100%**, tuyệt đối không điền sẵn hay hiển thị placeholder/gợi ý.
   - Chỉ tự động điền khi người dùng trước đó đã chủ động tích chọn `💾 Lưu thông tin đăng nhập`.
3. **Mã Hóa Mật Khẩu Đã Lưu (`saved_login.json`):**
   - TUYỆT ĐỐI KHÔNG lưu mật khẩu dạng Plaintext thô.
   - Sử dụng `_obfuscate_secret` (XOR + Base64 muối bí mật `enc_...`) và `_deobfuscate_secret`.
4. **Nhật Ký Đăng Nhập & Theo Dõi Tương Tác:**
   - Tự động ghi nhận số lần đăng nhập (`login_count`), mốc thời gian đăng nhập cuối (`last_login_at`) và lưu log `user_login_logs` (thành công/thất bại).
   - Hỗ trợ đầy đủ Thêm, Sửa thông tin, Đổi mật khẩu, Xóa tài khoản (bảo vệ tài khoản Admin duy nhất) và Xem lịch sử đăng nhập.
5. **Cơ Chế Xác Thực 2 Bước (2FA / Mã PIN Bảo Mật & TOTP):**
   - Hỗ trợ Bật/Tắt 2FA linh hoạt trong Tab Cài Đặt (Tab 10) lưu vào `storage/app_settings.json` (`enable_2fa`, `security_pin_2fa`).
   - Hỗ trợ đồng thời 2 phương thức: Mã PIN tùy chỉnh (4-8 số) và mã OTP 6 số từ Google/Microsoft Authenticator (`verify_totp_or_pin`).
   - Màn hình đăng nhập chuyển đổi mượt mà 2 giai đoạn: Giai đoạn 1 (Tài khoản/Mật khẩu) -> Giai đoạn 2 (Nhập Mã PIN 2FA) có nút quay lại.
6. **Nút Bỏ Lưu Thông Tin (Forget Credentials):**
   - Hỗ trợ xóa sạch thông tin đăng nhập cả ở màn hình Login và Tab Cài Đặt (CARD 1.5).

---

## ⚡ 4. CƠ CHẾ GỬI NGẦM KHÔNG CHIẾM CHUỘT / BÀN PHÍM (SILENT BACKGROUND AUTOMATION)

### 🔹 Chế Độ 1: Gửi Trực Tiếp / Active Window (Free Mode & F10)
* Gửi trực tiếp clipboard (`safe_clipboard_copy`), kích hoạt `Ctrl+V` và `Enter` vào cửa sổ đang active.
* Không di chuyển con trỏ chuột vật lý của Windows.

### 🔹 Chế Độ 2: Khóa Nền Zalo PC Gửi Ngầm (Target Locked Background Mode)
* **Silent Deep PostMessage Click:** Gửi `WM_LBUTTONDOWN` / `WM_LBUTTONUP` trực tiếp qua Win32 API.
* **Quick Focus & Restore (<150ms):** Lưu HWND cũ, focus Zalo, paste + Enter, trả lại cửa sổ cũ cho người dùng tiếp tục làm việc.

### 🔹 Chế Độ 3: Gửi Nhóm & Điều Khiển Từ Xa (UltraViewer / AnyDesk Broadcast)
* Tự động phát hiện `UltraViewer.exe`, `AnyDesk.exe`, `TeamViewer.exe`, `mstsc.exe`.
* Tự động đệm độ trễ mạng (`+1.0s`) đảm bảo máy đích nhận đủ clipboard.
* Tìm phòng chat bằng phím tắt toàn cục `Ctrl+F` -> Paste -> `Down` + `Enter`.

---

## ⌨️ 5. BẢNG PHÍM TẮT TOÀN CỤC (GLOBAL HOTKEYS MAPPING)

| Phím Tắt | Chức Năng | Chi Tiết |
| :--- | :--- | :--- |
| **`F10`** | **⚡ GỬI NHANH VÀO ZALO** | Gửi ngay mẫu kịch bản (Tab 3) hoặc mẫu tin nhắn (Tab 2) vào Zalo PC / cửa sổ đang mở. |
| **`F8`** | **🟢/⏸ BẬT / TẠM DỪNG BOT** | Bật hoặc tạm dừng lắng nghe và trả lời tự động của Bot AI CSKH. |
| **`F9`** | **🛑 HỦY MỌI THAO TÁC KHẨN CẤP** | Dừng ngay lập tức mọi tiến trình gửi ngầm, hủy gửi nhóm, trả lại toàn quyền kiểm soát. |
| **`F6`** | **⏸/▶ TẠM DỪNG / TIẾP TỤC GỬI NHÓM** | Tạm dừng hoặc tiếp tục chiến dịch gửi tin nhóm đang chạy. |
| **`F7`** | **⏹ HỦY CHIẾN DỊCH GỬI NHÓM** | Hủy bỏ đợt gửi tin nhóm hiện tại. |
| **`Ctrl+S`** | **💾 LƯU MẪU THEO NGỮ CẢNH** | Tự động lưu Mẫu kịch bản (Tab 3), Khách hàng (Tab 4), Cài đặt (Tab 10). |

---

## 🛠️ 6. BẢNG MÃ NGUỒN CÁC HÀM CỐT LÕI (`zalo_layer/zalo_automation.py`)

### 1. Dò Tìm HWND Zalo PC An Toàn & Tối Ưu Cache:
```python
@staticmethod
def find_zalo_hwnd() -> Optional[int]:
    if not HAS_WIN32:
        return None
    my_pid = os.getpid()
    locked_hwnd = BACKGROUND_TARGET_INFO.get("top_hwnd")
    if locked_hwnd and win32gui.IsWindow(locked_hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(locked_hwnd)
            if pid != my_pid:
                return locked_hwnd
        except Exception:
            pass

    found_hwnds = []
    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
            if owner != 0:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == my_pid:
                    return  # LOẠI TRỪ DASHBOARD
            except Exception:
                pid = 0
            if "AI Zalo CSKH" in title or "Quản Lý Giáo Án" in title:
                return

            proc_name = get_proc_name_cached(pid) if pid else ""

            if "zalo" in proc_name:
                rect = win32gui.GetWindowRect(hwnd)
                if (rect[2] - rect[0]) > 350 and (rect[3] - rect[1]) > 350:
                    found_hwnds.append((hwnd, title or "Zalo Main Window", 100))
    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
    if found_hwnds:
        found_hwnds.sort(key=lambda x: x[2], reverse=True)
        return found_hwnds[0][0]
    return None
```

### 2. Click Chuột Ngầm Silent PostMessage:
```python
@staticmethod
def send_deep_background_click(top_hwnd: int, x: int, y: int, btn: str = "left") -> bool:
    if not top_hwnd or not win32gui.IsWindow(top_hwnd):
        return False
    try:
        pt = wintypes.POINT(int(x), int(y))
        user32.ScreenToClient(top_hwnd, ctypes.byref(pt))
        cx, cy = pt.x, pt.y
        lparam = (cy << 16) | (cx & 0xFFFF)
        
        win32gui.PostMessage(top_hwnd, win32con.WM_MOUSEACTIVATE, top_hwnd, (win32con.WM_LBUTTONDOWN << 16) | 1)
        win32gui.PostMessage(top_hwnd, win32con.WM_SETCURSOR, top_hwnd, (win32con.WM_LBUTTONDOWN << 16) | 1)
        win32gui.PostMessage(top_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.02)
        
        if "right" in btn.lower():
            win32gui.PostMessage(top_hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
            time.sleep(0.03)
            win32gui.PostMessage(top_hwnd, win32con.WM_RBUTTONUP, 0, lparam)
        else:
            win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
            time.sleep(0.03)
            win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        return True
    except Exception:
        return False
```

---

## 🤖 7. QUY CHUẨN QUẢN LÝ & LỌC MODEL GEMINI AI (MODEL CATALOG & VERSION FILTER)

### 🔹 7.1. Nguyên Tắc Lọc Model Thế Hệ Mới (Chỉ Lấy >= Gemini 3.1):
* **Bối cảnh:** Google AI Studio trả về hàng chục model cũ đã bị giảm tốc độ hoặc sắp deprecated (1.0, 1.5, 2.0, 2.5...). Nếu hiển thị toàn bộ sẽ gây rối cho người dùng và giảm chất lượng suy luận.
* **Quy tắc bất biến:**
  1. Mặc định hệ thống **BẮT BUỘC chỉ quét, lấy và hiển thị các model Gemini có phiên bản >= 3.1** (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-flash-latest`, `gemini-pro-latest`, `gemini-3.1-pro-preview`...).
  2. Toàn bộ các model cũ (`1.0`, `1.5`, `2.0`, `2.5`...) bị lọc bỏ hoàn toàn, không xuất hiện trên bất kỳ dropdown hoặc bảng chọn nào.
  3. Các model auto-update mới nhất (`gemini-flash-latest`, `gemini-pro-latest`) luôn được giữ lại.

### 🔹 7.2. Nguyên Tắc An Toàn Khi Check API Key (Anti-404 Fallback):
* **Quy tắc:** Trong các hàm kiểm tra API Key (`check_single_key`, `check_all_keys`, `test_connection`):
  - Tuyệt đối không gửi model legacy (`< 3.1`) vào API để test.
  - Nếu `model_name` truyền vào bị trống hoặc là model legacy, hệ thống **BẮT BUỘC tự động fallback sang `gemini-3.6-flash`** để tránh phát sinh lỗi `404 NOT_FOUND` hoặc `400 BAD_REQUEST`.

### 🔹 7.3. Cấu Hình Bộ Lọc Linh Hoạt Cho Admin:
* Hỗ trợ cấu hình ngưỡng lọc `min_version` linh hoạt (`3.1`, `3.5`, `3.6`, `3.7`, `3.0`, `2.0`, `0.0/All`).
* Đồng bộ thời gian thực: Khi thay đổi bộ lọc ở Tab Cài Đặt (Tab 10), Tab API Keys (Tab 7) hoặc Modal chọn model, toàn bộ các dropdown trong Header, Chat, Playground tự động cập nhật ngay lập tức.
* Lưu bền vững vào `storage/app_settings.json`.

### 🔹 7.4. Mã Nguồn Hàm Lọc Phiên Bản Cốt Lõi (`core/key_manager.py`):
```python
def get_gemini_model_version(model_name: str) -> Optional[float]:
    """Trích xuất số phiên bản float chính xác từ tên model Gemini."""
    if not model_name:
        return None
    m = model_name.lower().strip()

    # 1. Trích xuất dạng x.y rõ ràng (ví dụ 3.7, 3.6, 3.1, 2.5, 1.5)
    match_dot = re.search(r"gemini[^\d]*(\d+)\.(\d+)", m)
    if match_dot:
        major = int(match_dot.group(1))
        minor = int(match_dot.group(2))
        return major + (minor / 10.0 if minor < 10 else minor / 100.0)

    # 2. Trích xuất dạng x (ví dụ gemini-3-flash, gemini-2-pro)
    match_single = re.search(r"gemini[^\d]*(\d+)", m)
    if match_single:
        return float(match_single.group(1))

    # 3. Model auto-update không có số phiên bản -> gán 99.0 (mới nhất)
    if any(k in m for k in ("latest", "next", "experimental-latest")):
        return 99.0

    # 4. Model legacy không số -> 1.0
    if "gemini" in m:
        return 1.0
    return None


def is_legacy_gemini_model(model_name: str, min_version: float = 3.1) -> bool:
    """Kiểm tra xem model có nhỏ hơn ngưỡng min_version (mặc định 3.1) hay không."""
    ver = get_gemini_model_version(model_name)
    if ver is None:
        return False
    return ver < min_version
```

---

## 🔗 8. QUY CHUẨN ĐÍNH KÈM LINK KHỐI & KHO TỆP (TAB 3 QUICK LINKS & FILE BUNDLES)

### 🔹 8.1. Nguyên Tắc Cấu Trúc Link Khối (9 Khối & 8 Link/Khối):
* **Cấu trúc dữ liệu:** Danh mục gồm 9 khối cố định: `Khối 6`, `Khối 7`, `Khối 8`, `Khối 9`, `Khối 10`, `Khối 11`, `Khối 12`, `Link THCS`, `Link THPT`.
* **8 Link linh hoạt mỗi khối:** Gồm `Link 1 (Chính)`, `Link 2 (Dự phòng 1)`, `Link 3 (Dự phòng 2)`, `Link 4 (Dự phòng 3)`, `Link 5 (PPCT & Đề)`, `Link Group 1 (Zalo CSKH)`, `Link Group 2 (Zalo Trao Đổi)`, `Link Group 3 (Zalo Tài Liệu)`.
* **Định dạng gửi tin chuẩn:** Mỗi link được định dạng trên **1 dòng riêng biệt** (`\n`).
  - Khi bật `include_label = True`: `f"[{grade} - {name}]: {url}"`
  - Khi tắt `include_label = False`: `f"{url}"`

### 🔹 8.2. Quy Tắc Gộp Link Vào Nội Dung Tin Nhắn:
* **Quy tắc bất biến khi gửi hoặc sao chép:**
  ```python
  links_str = self._get_checked_quick_links_formatted()
  if links_str:
      if ans:
          final_content = f"{ans}\n\n{links_str}"
      else:
          final_content = links_str
  ```
* Cho phép gửi khi có nội dung kịch bản HOẶC có link khối đính kèm HOẶC có file đính kèm (chỉ chặn khi cả 3 đều rỗng).

### 🔹 8.3. Lưu Trữ Bền Vững & Khôi Phục Gốc:
* Lưu cấu hình link vào `storage/quick_links.json`.
* Luôn cung cấp nút `🔄 Khôi Phục Gốc Khối Này` để người dùng có thể khôi phục lại bộ link mặc định chuẩn từ `DEFAULT_QUICK_LINKS` bất kỳ lúc nào nếu nhập sai hoặc hỏng link.

---

## 🛡️ 9. QUY CHUẨN XỬ LÝ UNICODE, WINDOWS TERMINAL & EXCEPTION SAFETY

### 🔹 9.1. Tránh Lỗi `UnicodeEncodeError` Trên Windows Console (CP1252 / CP437):
* **Vấn đề:** Khi in các ký tự Emoji (✅, ❌, ⚡, 🚀...) ra console PowerShell / CMD trên Windows mà không cấu hình encoding UTF-8, Python sẽ văng lỗi `UnicodeEncodeError: 'charmap' codec can't encode character...`.
* **Quy tắc:**
  1. Trong các script kiểm tra hoặc entry points: luôn cấu hình `sys.stdout.reconfigure(encoding='utf-8')`.
  2. Trong các hàm format string và ghi log: luôn chỉ định `encoding='utf-8'` khi mở file (`open(path, 'w', encoding='utf-8')`).

### 🔹 9.2. Bảo Vệ Callback Giao Diện Khi Widget Bị Hủy (`winfo_exists()`):
* **Vấn đề:** Khi background worker thread hoàn thành tác vụ sau khi người dùng đã đóng một Modal hoặc Dialog, việc gọi các hàm Tkinter trên widget đã bị hủy sẽ sinh ra ngoại lệ `_tkinter.TclError: bad window path name`.
* **Quy tắc:** Luôn kiểm tra `if self.winfo_exists():` và `if hasattr(self, 'widget_name') and self.widget_name.winfo_exists():` trước khi cập nhật widget từ `self.after(0, ...)`.

---

## 🧩 10. QUY CHUẨN AN TOÀN IMPORT MODULE & VÒNG ĐỜI WIDGET GIAO DIỆN

### 🔹 10.1. Khai Báo Module Thư Viện Chuẩn (Standard Library Imports):
* **Vấn đề:** Khi sử dụng các hàm như `copy.deepcopy()`, `json.dumps()`, `re.search()`, `math.ceil()`, nếu quên khai báo `import copy` hoặc import ở đầu file, ứng dụng sẽ crash ngay lập tức khi khởi động (`NameError: name 'copy' is not defined`).
* **Quy tắc:**
  1. Mọi module tiện ích (`copy`, `json`, `re`, `os`, `sys`, `time`, `logging`, `threading`, `shutil`) **BẮT BUỘC** phải được import rõ ràng ở đầu tệp mã nguồn (`gui/dashboard.py`, `core/*.py`, `main.py`).
  2. Tuyệt đối không gọi các module chuẩn trong các hàm con mà không có import ở cấp module.

### 🔹 10.2. Khởi Tạo Khung Chứa Widget Trước Khi Gắn Phần Tử Con (Widget Parent Container Safety):
* **Vấn đề:** Khi xây dựng Modal/Dialog (ví dụ `_open_model_selection_modal`), việc gọi `tk.Label(act_bar, ...)` hoặc `tk.Button(act_bar, ...)` trước khi `act_bar = tk.Frame(...)` được tạo sẽ gây crash `UnboundLocalError` hoặc `NameError: name 'act_bar' is not defined`.
* **Quy tắc:** Luôn khởi tạo và `pack()` / `grid()` khung cha (`act_bar`, `btn_bar`, `hdr`, `content_frame`) trước khi truyền biến khung cha đó vào bất kỳ widget con nào.

### 🔹 10.3. Kiểm Tra Tự Động Ký Hiệu Biến Toàn Cục (Symtable Pre-flight Verification):
* **Quy tắc:** Trước khi bàn giao mã hoặc đóng gói bản phát hành, chạy script kiểm tra `symtable` để đảm bảo 100% không có biến toàn cục hoặc module nào bị thiếu sót (`undefined global / builtin`).

---

## 🎨 11. QUY CHUẨN ĐỒNG BỘ GIAO DIỆN SÁNG / TỐI & ĐỘ TƯƠNG PHẢN (THEME CONSISTENCY & READABILITY)

### 🔹 11.1. Không Dùng Màu Cố Định Trong Các Hàm Vẽ Giao Diện Động:
* **Vấn đề:** Khi người dùng chuyển sang Giao diện Sáng (Light Theme), các khung vẽ động (`_render_quick_links_for_category`, `_switch_bundle_subview`, `_open_quick_links_manager_modal`, ...) nếu bị gán cứng màu nền tối (`#0f172a`, `#1e293b`) sẽ gây ra tình trạng "nửa sáng nửa tối", chữ bị chìm hoặc khó nhìn.
* **Quy tắc:** Mọi hàm vẽ lại giao diện động **BẮT BUỘC** phải kiểm tra `is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")` để nạp màu sắc tương thích.

### 🔹 11.2. Bảng Màu Chuẩn Cho Giao Diện Sáng (Light Theme):
* **Nền tổng thể & Canvas:** `#ffffff` (trắng tinh khiết) hoặc `#f8fafc` (Slate-50) / `#f1f5f9` (Slate-100).
* **Chữ chính / Nhãn / Tên link:** `#0f172a` (Slate-900 - chữ đen đậm, tương phản cao, cực kỳ rõ nét).
* **Đường dẫn URL / Điểm nhấn xanh:** `#0284c7` (Sky-600) hoặc `#2563eb` (Blue-600) - màu xanh nổi bật, dễ đọc trên nền sáng.
* **Hàng xen kẽ trong bảng / danh sách:** `#ffffff` và `#f8fafc`.
* **Checkbox `selectcolor`:** `#ffffff` (ô vuông tích nền trắng sạch, không bị đen).
* **Nút bấm phụ / Inactive:** `bg="#e2e8f0"`, `fg="#334155"`.

### 🔹 11.3. Bảng Màu Chuẩn Cho Giao Diện Tối (Dark Theme):
* **Nền tổng thể & Canvas:** `#0f172a` (Slate-900) hoặc `#0b0f19` (Slate-950).
* **Chữ chính / Nhãn / Tên link:** `#f8fafc` (Slate-50 - trắng sáng, sắc nét).
* **Đường dẫn URL:** `#38bdf8` (Sky-400 - xanh dạ quang sáng trên nền tối).
* **Hàng xen kẽ:** `#1e293b` và `#0f172a`.
* **Checkbox `selectcolor`:** `#0f172a`.
* **Nút bấm phụ / Inactive:** `bg="#334155"`, `fg="#cbd5e1"`.

### 🔹 11.4. Đệ Quy Quét `Canvas` & Làm Mới Subviews Khi Đổi Theme:
* Hàm `_apply_theme_to_widget_recursive` **BẮT BUỘC** bao gồm cả lớp widget `"Canvas"`.
* Trong `_apply_theme()`, luôn gọi lại các hàm cập nhật subview động (`_switch_bundle_subview`, `_render_quick_links_for_category`) để giao diện được chuyển đổi tức thì 100%.

---

## 🪟 12. QUY CHUẨN FLOAT MINI TOOLBAR, TOAST NOTIFICATION & CÔNG THÁI HỌC HEADER

### 🔹 12.1. Thanh Công Cụ Nổi Mini On-Top (Floating Mini Toolbar):
* **Nguyên lý thiết kế:** Khi người dùng làm việc song song với Zalo PC hoặc phần mềm khác, thu nhỏ Dashboard thành thanh mini float nhỏ gọn (500x42px) luôn ghim On-top.
* **Cơ chế Idle Dimming chống che khuất tầm nhìn (Tùy chỉnh % trong Cài Đặt):**
  - Khi không thao tác hoặc rời chuột: `alpha` mờ theo tỷ lệ người dùng cấu hình trong `app_settings.json` (`float_idle_alpha`: 15%, 25%, 35% mặc định, 50%, 65%, 80%, 100% không mờ).
  - Khi rê chuột vào hoặc click: `alpha = 1.0` (sáng rõ 100% tức thì).
  - Cung cấp nút `👁️ Thử Mức Này` trong Tab Cài Đặt (Tab 10) để người dùng xem trước và điều chỉnh thời gian thực.
* **Nút Mở Rộng To Rõ:** Luôn bố trí nút `🗖 Mở Rộng` nổi bật (màu tím `#8b5cf6`) và bind sự kiện `<Double-Button-1>` trên container/drag handle để mở rộng lại cửa sổ chính.

### 🔹 12.2. Xếp Tầng & Vị Trí Thông Báo Toast (Toast Stacking & Positioning):
* **Vị trí chuẩn mặc định:** Luôn ưu tiên **Góc phải dưới cùng màn hình** (Bottom-Right), cách mép dưới 55px để nằm trên thanh Taskbar Windows.
* **Công thức xếp tầng không đè lấp (Smart Multi-Toast Offset):**
  ```python
  stack_idx = max(0, len(_ACTIVE_TOASTS) - 1)
  offset_y = stack_idx * (toast_h + 10)
  # Với bottom_right:
  y = max(10, scr_h - toast_h - 55 - offset_y)
  ```
* **Lưu bền vững:** Mọi thay đổi vị trí Toast trong Cài đặt phải được lưu vào `storage/app_settings.json` và nạp tự động khi khởi động.

### 🔹 12.3. Công Thái Học Header & Nhãn Nút Tối Giản (Anti-Overflow Layout):
* **Quy tắc phân vùng Header (Dòng 1):**
  - Cột bên trái: Logo / Nhãn ứng dụng nhỏ gọn (`⚡ AI CSKH`).
  - Cột bên phải: Toàn bộ trạng thái Bot (`● BOT CHẠY (F8)` / `● TẠM DỪNG (F8)`) cùng cụm nút hành động và tài khoản (`[🔄 Reset]`, `[🛑 Hủy]`, `[⏸ Dừng Bot]`, `[🪟 Nổi]`, `[📌 Ghim]`, `[👤 admin]`, `[🚪 Thoát]`).
* **Quy tắc Header Sub-bar (Dòng 2):**
  - Cụm Model bên trái: `🎯 Model:`, `Combobox` (width=16), `[⭐ Mặc Định]`, `[📋 Models]`.
  - Cụm chức năng bên phải: `● X/Y Keys (...)` (rút gọn không lặp lại tên model), `[⚙️ Cài Đặt]`, `[☀️ Sáng]` / `[🌙 Tối]`, `[🌐 AI]`.
* **Quy tắc rút gọn nhãn nút:**
  - Tuyệt đối không dùng văn bản dài lê thê khiến các nút bị đẩy tràn ra khỏi mép màn hình khi cửa sổ thu nhỏ (Split Screen 50% / 650px).
  - Giảm padding của các nút Header xuống `padx=5` hoặc `padx=6`, `pady=2`.

### 🔹 12.4. Thanh Điều Hướng Tab Bar Siêu Gọn & Nút Xem Thêm:
* **Tối ưu hiển thị trên màn hình nhỏ:**
  - Nhóm 6 Tab chính luôn hiển thị: `[💬 Chat]`, `[📢 Gửi Nhóm]`, `[⚡ Kịch Bản]`, `[🖼️ Drive]`, `[👥 CRM]`, `[📝 Sổ Tay]`.
  - Nhóm 8 Tab mở rộng được gom vào nút `[🛠️ Thêm (8) ▾]` với Popup Menu.
  - Tổng chiều rộng toàn bộ thanh Tab Bar chỉ ~510px, đảm bảo nút `🛠️ Thêm ▾` luôn luôn nhìn thấy rõ và không bao giờ bị cắt cụt trên màn hình hẹp.

---

## 💾 13. QUY CHUẨN SAO LƯU, PHỤC HỒI DỮ LIỆU & GIAO DIỆN ĐÁP ỨNG (BACKUP, RESTORE & RESPONSIVE UI)

### 🔹 13.1. Phục Hồi CSDL Tự Động Thích Ứng Cấu Trúc (Dynamic Schema Introspection):
* **Vấn đề:** Khi sao lưu CSDL ra file JSON và nạp lại vào phiên bản mới hoặc cũ hơn, nếu các bảng có thêm hoặc bớt cột (schema migration), câu lệnh `INSERT INTO table (col1, col2...)` cố định sẽ văng lỗi `sqlite3.OperationalError: table X has no column named Y`.
* **Quy tắc bất biến:**
  - Khi import, **BẮT BUỘC** dùng `PRAGMA table_info(table_name)` để quét danh sách cột thực tế của bảng trong CSDL.
  - Chỉ lọc và nạp các trường dữ liệu khớp 100% với cột thực tế hiện có:
    ```python
    cursor.execute(f"PRAGMA table_info({table_name})")
    actual_cols = set([r[1] for r in cursor.fetchall()])
    valid_keys = [k for k in row.keys() if k in actual_cols]
    ```

### 🔹 13.2. Chuyển Đổi Nhãn Thích Ứng (Responsive Adaptive Labels):
* **Nguyên lý:**
  - Cửa sổ rộng (`width >= 1050px` hoặc Maximize): Tự động hiển thị nhãn nút đầy đủ, chi tiết (`💬 Chat Live`, `📢 Gửi Tin Nhóm`, `⚡ Kịch Bản Nhanh`, `🖼️ Fake Ảnh Drive`, `👥 Khách Hàng (CRM)`, `📝 Sổ Tay Sửa`, `⏸ Tạm Dừng Bot (F8)`, `🛑 Hủy (F9)`, `🔄 Reset Lỗi`, `🪟 Nổi On-Top`, `📌 Ghim Top`, `🚪 Đăng Xuất`...).
  - Cửa sổ hẹp (`width < 1050px` hoặc Split Screen): Tự động thu gọn nhãn nút về dạng tối giản (`💬 Chat`, `📢 Gửi Nhóm`, `⚡ Kịch Bản`, `🖼️ Drive`, `👥 CRM`, `📝 Sổ Tay`, `⏸ Dừng Bot`, `🛑 Hủy`, `🔄 Reset`, `🪟 Nổi`, `📌 Ghim`, `🚪 Thoát`...).
* **Triển khai an toàn:** Bắt sự kiện `<Configure>` trên root window, lọc `if event.widget == self:` và so sánh `_is_wide_mode` trước khi cập nhật widget để tránh giật lag layout.

### 🔹 13.3. Tự Động Gửi Sao Lưu Qua Telegram Không Tiếng Chuông (Silent Backup Dispatch):
* **Quy tắc:** Khi người dùng bấm Xuất dữ liệu (Export), hệ thống tự động tải file `.json` lên Telegram Bot API (`sendDocument`) trong luồng nền `threading.Thread` kèm `disable_notification=True` để sao lưu âm thầm, không phát âm thanh chuông làm phiền người dùng.

---

## 🛡️ 14. BẢNG MẪU CODE CHUẨN ĐỊNH HÌNH & CHỐNG TÁI DIỄN LỖI (ZERO-BUG TEMPLATES)

### 🔹 14.1. Bảo Vệ Tài Khoản Admin Duy Nhất (Single Admin Protection):
```python
# Kiểm tra chặn hạ quyền hoặc xóa nếu chỉ còn đúng 1 Admin hoạt động:
cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
admin_count = cursor.fetchone()['count']
if target_role != 'admin' and admin_count <= 1:
    raise ValueError("Không thể hạ quyền hoặc xóa tài khoản Admin duy nhất của hệ thống!")
```

### 🔹 14.2. Khôi Phục CSDL Tương Thích Mọi Cột (Dynamic Schema Import Guard):
```python
cursor.execute(f"PRAGMA table_info({table_name})")
actual_cols = set([r[1] for r in cursor.fetchall()])
valid_keys = [k for k in row.keys() if k in actual_cols]
if not valid_keys:
    continue
placeholders = ", ".join(["?"] * len(valid_keys))
col_names = ", ".join(valid_keys)
cursor.execute(f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})", [row[k] for k in valid_keys])
```

### 🔹 14.3. Xác Thực 2 Bước (Custom PIN & Google Authenticator TOTP):
```python
def verify_totp_or_pin(input_code: str, custom_pin: str, totp_secret: str = "") -> bool:
    code_clean = input_code.strip()
    if not code_clean:
        return False
    if custom_pin and code_clean == custom_pin.strip():
        return True
    if totp_secret and len(code_clean) == 6 and code_clean.isdigit():
        try:
            import hmac, hashlib, struct, time, base64
            secret_bytes = base64.b32decode(totp_secret.strip().upper(), casefold=True)
            for offset in (-1, 0, 1):
                interval = int(time.time() // 30) + offset
                msg = struct.pack(">Q", interval)
                h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
                o = h[19] & 15
                totp_val = ((struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000)
                if code_clean == f"{totp_val:06d}":
                    return True
        except Exception:
            pass
    return False
```

### 🔹 14.4. Cập Nhật Giao Diện An Toàn Từ Luồng Nền (Thread-Safe GUI Dispatch):
```python
def _safe_gui_update(self, callback_fn):
    """Điều phối cập nhật GUI từ background thread an toàn tuyệt đối."""
    if self.winfo_exists():
        try:
            self.after(0, callback_fn)
        except Exception:
            pass
```

---

## 📁 15. QUY CHUẨN CẤU TRÚC THƯ MỤC & ĐÓNG GÓI .AGENTS (CLEAN WORKSPACE ARCHITECTURE)

### 🔹 15.1. Sơ Đồ Cấu Trúc Dự Án Đồng Bộ Chuẩn .agents:
```
100AISupport/
│
├── main.py                     # Entry point khởi động ứng dụng & cấu hình UTF-8 toàn diện
├── build_exe.bat               # Script đóng gói EXE tự động (output .agents/dist/ & .agents/build/)
├── build_exe.py                # Script PyInstaller tối ưu No-Console & tạo ZIP di động
├── config/                     # Cấu hình hệ thống YAML, ma trận giáo án & Google Drive
├── knowledge_base/             # Bộ tri thức kỹ thuật & giáo án Lịch sử 6-12
├── core/
│   ├── app_paths.py            # Quản lý đường dẫn tài nguyên tuyệt đối (hỗ trợ đóng gói EXE)
│   ├── broadcast_scheduler.py  # Bộ lập lịch tự động gửi tin nhóm theo các mốc giờ
│   ├── drive_manager.py        # Quản lý phân quyền Google Drive & chống tràn 500 email/link
│   ├── drive_share_mockup.py   # Tạo ảnh giả lập cấp quyền Google Drive cực nét
│   ├── file_searcher.py        # Tìm kiếm tài liệu giáo án nhanh trong ổ đĩa cục bộ
│   ├── gemini_engine.py        # Xử lý ngôn ngữ tự nhiên Gemini AI Multimodal & xoay vòng Key
│   ├── hotkey_manager.py       # Quản lý phím tắt toàn cục Windows (F8, F9, F10, F6, F7...)
│   ├── key_manager.py          # Quản lý danh sách Multi-Key Gemini, đo độ trễ & lọc model >= 3.1
│   ├── state_manager.py        # CSDL SQLite WAL Mode, quản lý khách hàng, hội thoại & múi giờ UTC+7
│   └── telegram_notifier.py    # Thông báo khẩn cấp & sao lưu dữ liệu qua Telegram Bot API
├── gui/
│   └── dashboard.py            # Toàn bộ giao diện 10 Tabs, Header, Float Toolbar & Widgets
├── storage/                    # CSDL SQLite (database.sqlite), app_settings.json & Logs
├── zalo_layer/
│   ├── zalo_automation.py      # Module Win32 API tự động hóa Zalo PC, UltraViewer, AnyDesk
│   └── zalo_handler.py         # Pipeline phân loại ý định khách hàng & điều phối tin nhắn
└── .agents/
    ├── GEMINI.md               # Hệ thống quy tắc, bảo mật, tối ưu hóa & bài học kinh nghiệm AI
    ├── rules/                  # Quy chuẩn, quy tắc & kỹ năng cho AI (SKILL.md, zalo_automation_rules.md, GEMINI.md)
    ├── guide/                  # Hướng dẫn chi tiết, walkthroughs & tài liệu chuẩn .md
    ├── update/                 # Nhật ký chi tiết toàn bộ tính năng và phiên bản (UPDATE.md, Update1.md)
    ├── autobackups/            # Bản sao lưu mã nguồn và cơ sở dữ liệu (Git ignored)
    ├── build/                  # Thư mục build tạm thời của PyInstaller (Git ignored)
    └── dist/                   # File thực thi AI_Zalo_CSKH.exe & AI_Zalo_CSKH.zip độc lập (Git ignored)
```

### 🔹 15.2. Nguyên Tắc Đóng Gói EXE Không Rác Thư Mục Gốc:
1. Mọi tệp sinh ra trong quá trình build (`.spec`, `build/`, `dist/`) **BẮT BUỘC** nằm gọn gàng bên trong `.agents/build` và `.agents/dist`.
2. Lệnh gọi PyInstaller trong `build_exe.py` luôn chỉ định:
   ```python
   f"--distpath={os.path.join(root_dir, '.agents', 'dist')}",
   f"--workpath={os.path.join(root_dir, '.agents', 'build')}",
   f"--specpath={os.path.join(root_dir, '.agents', 'build')}",
   ```
3. Sau khi đóng gói, tự động nén thành `.agents/dist/AI_Zalo_CSKH.zip` và dọn dẹp sạch mọi thư mục rác ở root.

---

## 🎨 16. QUY TẮC BẤT BIẾN VỀ PHỐI MÀU GIAO DIỆN SÁNG / TỐI & TƯƠNG PHẢN CHỮ

### ⚠️ 16.1. Quy Tắc Bất Biến Về Độ Tương Phản (High Contrast Rule):
* **Yêu Cầu Tối Thượng:** Mọi tính năng code mới hoặc chỉnh sửa giao diện **BẮT BUỘC PHẢI TƯƠNG THÍCH ĐỒNG THỜI VỚI CẢ GIAO DIỆN SÁNG (LIGHT THEME) VÀ GIAO DIỆN TỐI (DARK THEME)**. Chữ viết phải luôn nhìn thấy rõ ràng 100%, có độ tương phản cao, tuyệt đối không bị chìm hoặc hòa lẫn vào màu nền.
* **Quy chuẩn Giao diện Tối (Dark Theme):**
  - Khung nền: Sẫm màu (`#0f172a`, `#1e293b`, `#090d16`).
  - Màu chữ: Trắng sáng (`#f8fafc`), Xanh dạ quang (`#38bdf8`), Xanh ngọc (`#34d399`), Vàng kim (`#fbbf24`).
  - Viền card & widget: `#334155` hoặc `#1e293b`.
* **Quy chuẩn Giao diện Sáng (Light Theme):**
  - Khung nền: Trắng tinh khiết (`#ffffff`), Xám sáng (`#f8fafc`, `#f1f5f9`, `#e2e8f0`).
  - Màu chữ: Đen đậm (`#0f172a`, `#1e293b`), Xanh đậm sắc nét (`#0284c7`, `#1d4ed8`), Xanh lá đậm (`#059669`).
  - **CẤM:** Không được dùng chữ trắng, xám nhạt (`#cbd5e1`, `#94a3b8`) trên nền trắng/xám sáng vì sẽ gây mù mắt, không đọc được.

### 🔹 16.2. Kiểm Tra Chế Độ Sáng Trong Mọi Hàm Vẽ Subview Động:
```python
is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
bg_card = "#ffffff" if is_light else "#0f172a"
fg_text = "#0f172a" if is_light else "#f8fafc"
fg_accent = "#0284c7" if is_light else "#38bdf8"
```

---

## ⏰ 17. QUY CHUẨN MÚI GIỜ VIỆT NAM (UTC+7) & BỐ CỤC 50/50 RESPONSIVE GRID

### 🔹 17.1. Múi Giờ Việt Nam (UTC+7) Trong Toàn Bộ Hệ Thống:
1. SQLite mặc định dùng UTC nếu dùng `CURRENT_TIMESTAMP`.
2. Bắt buộc sử dụng `(datetime('now', 'localtime'))` trong Schema SQLite và luôn truyền thời gian thực `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` từ Python khi ghi dữ liệu `chat_messages`, `chat_sessions`, `conversations`, `message_history`, `users`, `user_login_logs`.
3. Hàm `format_smart_timestamp` luôn phân giải đúng múi giờ UTC+7 cho mọi định dạng ISO và chuỗi thời gian.

### 🔹 17.2. Bố Cục Tab Cài Đặt Chia Đôi 50/50 Hoàn Hảo (1:1 Ratio):
1. Sử dụng Grid responsive 2 cột đồng dạng:
   ```python
   content_frame.grid_columnconfigure(0, weight=1, uniform="settings_col")
   content_frame.grid_columnconfigure(1, weight=1, uniform="settings_col")
   left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
   right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
   ```
2. Mọi phần tử con (Combobox, Entry, Treeview) cấu hình co giãn tự động `fill="x"`, `expand=True`, `stretch=True` để đảm bảo 2 bên luôn cân xứng 50% - 50% hoàn hảo trên mọi kích thước màn hình.







