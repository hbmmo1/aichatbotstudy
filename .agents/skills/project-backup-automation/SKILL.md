---
name: project-backup-automation
description: Quản lý tối ưu SQLite (WAL mode, RAM cache), bảo mật thông tin đăng nhập bằng mã hóa obfuscation, và sao lưu tự động mã nguồn, dữ liệu vào .agents/autobackups/.
---

# KỸ NĂNG: SAO LƯU DỰ ÁN, BẢO MẬT & CƠ SỞ DỮ LIỆU (BACKUP, SECURITY & DB)

---

## 1. Tối Ưu CSDL SQLite: WAL Mode & RAM Cache (High Performance)

```python
conn = sqlite3.connect(self.db_path, timeout=15.0)
conn.execute("PRAGMA journal_mode=WAL;")        # Đọc ghi đồng thời không khóa file
conn.execute("PRAGMA synchronous=NORMAL;")      # Giảm tải đĩa 80%
conn.execute("PRAGMA cache_size=-64000;")       # Bộ nhớ đệm 64MB RAM
conn.execute("PRAGMA temp_store=MEMORY;")
```

- **Chỉ mục (Indices):** Luôn duy trì index trên `chat_messages(session_id)`, `chat_sessions(is_archived, updated_at)`, `users(username)`, `group_broadcast_logs(group_name)`, `conversations(user_id)`.

---

## 2. Bảo Mật & Quản Lý Đăng Nhập (Security & Authentication)

1. **Mặc định BẬT xác thực đăng nhập:**
   - Khi cài đặt hệ thống luôn bật xác thực. Chỉ tự động đăng nhập khi người dùng chủ động tắt trong Cài Đặt.
2. **Tài khoản mặc định & Chống lộ gợi ý:**
   - Tài khoản mặc định: `admin` / `admin` (mã hóa SHA-256 trong CSDL SQLite).
   - Ô Tên đăng nhập và Mật khẩu luôn để **TRỐNG 100%** khi khởi động, tuyệt đối không điền sẵn trừ khi người dùng đã tích chọn `💾 Lưu thông tin đăng nhập`.
3. **Mã hóa thông tin lưu trữ (`saved_login.json`):**
   - TUYỆT ĐỐI KHÔNG lưu mật khẩu dạng Plaintext thô.
   - Sử dụng `_obfuscate_secret` (XOR + Base64 muối bí mật `enc_...`) và `_deobfuscate_secret`.
4. **Xác thực 2 bước (2FA / PIN & TOTP):**
   - Hỗ trợ đồng thời 2 phương thức: Mã PIN tùy chỉnh (4-8 số) và mã OTP 6 số từ Google/Microsoft Authenticator (`verify_totp_or_pin`).

---

## 3. Chống Rò Rỉ Bộ Nhớ RAM (Anti-Memory Leak)

- **PIL Image Handles:** Luôn bọc mở ảnh trong `try...finally: if img: img.close()` để giải phóng RAM ngay sau khi gửi API.
- **Dọn Rác Định Kỳ:** Kích hoạt `gc.collect()` mỗi 60 giây.
- **Sleep Không Khóa Luồng:** Trong daemon threads (`BroadcastScheduler`), dùng `self._stop_event.wait(timeout=20)` thay vì `time.sleep(20)`.
- **Clipboard An Toàn:** Dùng `safe_clipboard_copy` / `safe_clipboard_paste` với vòng lặp thử lại tránh xung đột với ứng dụng khác.

---

## 4. Quy Trình Sao Lưu Dự Án (.agents/autobackups/)

- Toàn bộ các bản nén sao lưu định kỳ hoặc trước khi cập nhật được nén ZIP vào `.agents/autobackups/`.
- Tự động bỏ qua các thư mục tạm (`__pycache__`, `.agents/build/`, `.venv`) để đảm bảo dung lượng file sao lưu gọn nhẹ.