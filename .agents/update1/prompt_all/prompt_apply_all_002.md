# PROMPT ÁP DỤNG DÙNG CHUNG: AN TOÀN ĐA LUỒNG WIN32 & CHỐNG KHÓA GUI

```text
Khi lập trình ứng dụng Desktop tương tác Win32 API hoặc điều khiển cửa sổ ngoài:
1. Bắt buộc đặt win32process.AttachThreadInput(curr, target, False) trong khối finally để luôn luôn detach luồng, chống triệt để lỗi Not Responding.
2. Mọi thao tác cập nhật giao diện Tkinter từ background worker thread phải được điều phối qua self.after(0, ...) kèm khối try...except.
3. Đặt pyautogui.FAILSAFE = False để chống dừng đột ngột khi con trỏ chạm góc màn hình.
4. Quét cửa sổ Win32 bắt buộc loại trừ PID của chính ứng dụng hiện tại (pid == os.getpid()).
```