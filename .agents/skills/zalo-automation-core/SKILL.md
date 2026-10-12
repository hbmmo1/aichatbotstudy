---
name: zalo-automation-core
description: Hướng dẫn kỹ thuật chuẩn hóa tự động hóa Zalo PC, Win32 API HWND detection, cơ chế gửi ngầm không chiếm chuột (Silent Deep PostMessage), quick focus & restore <150ms, và chống đơ Not Responding.
---

# KỸ NĂNG: TỰ ĐỘNG HÓA ZALO PC & WIN32 API CORE AUTOMATION

Quy chuẩn kiến trúc và giải pháp kỹ thuật tự động hóa tương tác cửa sổ Zalo PC và điều khiển từ xa (UltraViewer, AnyDesk, TeamViewer) bằng Win32 API trên Windows.

---

## 1. Nguyên Tắc Cách Ly Tiến Trình (Process Isolation & Anti-Self Target)

### 1.1. Lỗi Tự Target Chính Mình (Self-Window Target Bug)
- **Nguyên nhân:** Khi quét cửa sổ bằng từ khóa tiêu đề `"zalo" in title.lower()`, hệ thống nhận nhầm chính Dashboard AI CSKH và paste dữ liệu vào chính mình.
- **Quy tắc bắt buộc:**
  ```python
  my_pid = os.getpid()
  _, pid = win32process.GetWindowThreadProcessId(hwnd)
  if pid == my_pid:
      return  # TUYỆT ĐỐI BỎ QUA CỬA SỔ CỦA DASHBOARD NÀY!
  if "AI Zalo CSKH" in title or "Quản Lý Giáo Án" in title:
      return
  ```
- Luôn ưu tiên đối soát theo tên tiến trình thực tế (`zalo.exe` hoặc lớp `Chrome_WidgetWin_1`).

---

## 2. Tối Ưu Hóa CPU Khi Quét Cửa Sổ (Process Name Caching)

- **Vấn đề:** Hàm `psutil.Process(pid).name()` tốn chu kỳ CPU Kernel rất lớn khi duyệt hàng trăm cửa sổ trong `EnumWindows`.
- **Giải pháp:** Sử dụng hàm cache `get_proc_name_cached(pid)` với thời gian sống (TTL) 8 giây: 1.000 truy vấn chỉ tốn 0.19ms (giảm 99.9% CPU).

---

## 3. An Toàn Đa Luồng & Chống Khóa GUI (Tkinter Thread-Safety & Anti-Freeze)

### 3.1. Detach Thread Input
- Khi sử dụng `win32process.AttachThreadInput(curr_thread, fore_thread, True)`, **BẮT BUỘC** phải đặt lệnh detach trong khối `finally`:
  ```python
  finally:
      if attached_thread and curr_thread:
          try:
              win32process.AttachThreadInput(curr_thread, attached_thread, False)
          except Exception:
              pass
  ```
- Nếu không detach, hàng đợi tin nhắn của Dashboard sẽ bị dính chặt vào ứng dụng ngoài, gây lỗi **"Not Responding"**.

### 3.2. Cập Nhật GUI Từ Background Worker
- Mọi thao tác cập nhật giao diện Tkinter (`widget.configure`, `widget.insert`, `show_toast`) từ background thread phải được điều phối qua `self.after(0, ...)`.
- Đặt `pyautogui.FAILSAFE = False` để chống ngắt quãng đột ngột khi con trỏ chạm góc màn hình.

---

## 4. Ba Chế Độ Gửi & Tương Tác Cửa Sổ

### 🔹 Chế Độ 1: Gửi Trực Tiếp / Active Window (Free Mode & F10)
- Gửi trực tiếp clipboard (`safe_clipboard_copy`), kích hoạt `Ctrl+V` và `Enter` vào cửa sổ đang active.
- Không di chuyển con trỏ chuột vật lý của Windows.

### 🔹 Chế Độ 2: Khóa Nền Zalo PC Gửi Ngầm (Target Locked Background Mode)
- **Silent Deep PostMessage Click:** Gửi `WM_LBUTTONDOWN` / `WM_LBUTTONUP` trực tiếp qua Win32 API vào tọa độ client của HWND mục tiêu:
  ```python
  pt = wintypes.POINT(int(x), int(y))
  user32.ScreenToClient(top_hwnd, ctypes.byref(pt))
  lparam = (pt.y << 16) | (pt.x & 0xFFFF)
  win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
  time.sleep(0.03)
  win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
  ```
- **Quick Focus & Restore (<150ms):** Lưu HWND cũ, focus Zalo, paste + Enter, trả lại cửa sổ cũ ngay lập tức cho người dùng làm việc.

### 🔹 Chế Độ 3: Gửi Nhóm & Điều Khiển Từ Xa (UltraViewer / AnyDesk Broadcast)
- Tự động phát hiện `UltraViewer.exe`, `AnyDesk.exe`, `TeamViewer.exe`, `mstsc.exe`.
- Tự động đệm độ trễ mạng (+1.0s) đảm bảo máy đích nhận đủ clipboard.
- Tìm phòng chat bằng phím tắt `Ctrl+F` -> Paste -> `Down` + `Enter`.

---

## 5. Bảng Phím Tắt Toàn Cục (Global Hotkeys)

| Phím Tắt | Chức Năng | Chi Tiết |
| :--- | :--- | :--- |
| **`F10`** | **⚡ Gửi Nhanh Vào Zalo** | Gửi ngay mẫu kịch bản (Tab 3) hoặc mẫu tin nhắn (Tab 2) vào Zalo PC / cửa sổ đang mở. |
| **`F8`** | **🟢/⏸ Bật / Tạm Dừng Bot** | Bật hoặc tạm dừng lắng nghe và trả lời tự động của Bot AI CSKH. |
| **`F9`** | **🛑 Hủy Mọi Thao Tác Khẩn Cấp** | Dừng ngay lập tức mọi tiến trình gửi ngầm, trả lại toàn quyền kiểm soát. |
| **`F6`** | **⏸/▶ Tạm Dừng / Tiếp Tục Gửi Nhóm** | Tạm dừng hoặc tiếp tục chiến dịch gửi tin nhóm đang chạy. |
| **`F7`** | **⏹ Hủy Chiến Dịch Gửi Nhóm** | Hủy bỏ đợt gửi tin nhóm hiện tại. |
| **`Ctrl+S`** | **💾 Lưu Mẫu Theo Ngữ Cảnh** | Tự động lưu Mẫu kịch bản (Tab 3), Khách hàng (Tab 4), Cài đặt (Tab 10). |