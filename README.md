# 📚 AI CSKH Zalo - Hỗ Trợ Kỹ Thuật & Cấp Quyền Giáo Án Lịch Sử 6-12

Hệ thống phần mềm tự động hóa chăm sóc khách hàng và bán giáo án/tài liệu Lịch sử (Lớp 6 đến Lớp 12) trên Zalo bằng **Python** kết hợp **Google Gemini Multimodal (Google AI Studio)**.

---

## 🌟 Tính Năng Nổi Bật

1. **Đọc hiểu Đa phương thức (Multimodal):**
   - Đọc tin nhắn văn bản và phân tích **ảnh chụp màn hình lỗi** do thầy/cô gửi đến (lỗi không tải được, lỗi mở file PowerPoint trên mạng, lỗi không sửa được do thanh Protected View màu vàng...).
2. **Bộ tri thức chuyên sâu (Knowledge Base):**
   - Tự động hướng dẫn phím tắt `Ctrl + J` để bấm **Tiếp tục (Resume)** tải file nặng khi mạng yếu.
   - Hướng dẫn bấm **Cho phép (Allow)** khi trình duyệt chặn tải hàng loạt.
   - Hướng dẫn lưu sang ổ `D:` hoặc `E:` khi ổ `C:` bị đầy.
   - Hướng dẫn bấm nút **Enable Editing** màu vàng trên Word/PowerPoint để mở khóa chỉnh sửa.
   - Hướng dẫn xóa số điện thoại, thông tin liên hệ trong **Slide Master** / **Header & Footer**.
   - Nói khéo léo và ghi nhận khi gặp các icon/hình khối đang cập nhật hoặc thầy/cô phản hồi bài thiếu/sai kiến thức sách mới (GDPT 2018).
3. **Sổ tay sửa Giáo án tự động (Notebook):**
   - Tự động ghi chép các góp ý của thầy/cô về lỗi bài/sách vào một bảng danh sách riêng trên phần mềm để bạn mở ra rà soát và chỉnh sửa lúc rảnh.
4. **Cảnh báo khẩn cấp qua Telegram:**
   - Khi một khách hàng hỏi lại hoặc chưa hài lòng đến **lần thứ 3**, bot sẽ tự động gửi thông báo báo động về điện thoại của bạn qua Telegram kèm Tên khách + Link Zalo + Vấn đề để bạn vào hỗ trợ trực tiếp.
5. **Hệ thống phím tắt toàn cục (Global Hotkeys):**
   - `F8`: Bắt đầu bot.
   - `F9`: Tạm dừng khẩn cấp.
   - `F10`: Tiếp tục bot.
   - `Ctrl + Space`: Can thiệp tay (nhường quyền cho chủ shop tự chat).
6. **Phân quyền Google Drive tự động:**
   - Tự động cấp quyền "Chỉ xem (Viewer)" vào đúng thư mục Khối THCS (6-7-8-9), Khối THPT (10-11-12) hoặc từng lớp lẻ khi khách gửi Gmail.

---

## 🛠️ Cài Đặt & Chạy Phần Mềm

### 1. Cài đặt các thư viện cần thiết:
Mở Terminal hoặc PowerShell tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình API Key:
Mở file `config/config.yaml`:
- **Gemini API Key:** Điền key lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/).
- **Telegram (Tùy chọn):** Điền `bot_token` (tạo qua `@BotFather`) và `chat_id` (lấy qua `@userinfobot`).

### 3. Khởi chạy Dashboard:
```bash
python main.py
```

---

## 📂 Cấu Trúc Dự Án
```
100AISupport/
├── main.py                     # Entry point khởi động ứng dụng & cấu hình UTF-8 toàn diện
├── build_exe.bat               # Script đóng gói EXE tự động (output .agents/dist/ & .agents/build/)
├── build_exe.py                # Script PyInstaller tối ưu No-Console & tạo ZIP di động
├── config/                     # Cấu hình hệ thống YAML, ma trận giáo án & Google Drive
├── knowledge_base/             # Bộ quy tắc xử lý lỗi kỹ thuật & dữ liệu giáo án
├── core/                       # Các module logic nghiệp vụ nền tảng (Gemini AI, State, Hotkey...)
├── gui/                        # Giao diện người dùng Tkinter 10 Tabs đa theme
├── storage/                    # CSDL SQLite (database.sqlite), app_settings.json & Logs
├── zalo_layer/                 # Module Win32 API tự động hóa Zalo PC, UltraViewer, AnyDesk
└── .agents/
    ├── GEMINI.md               # Hệ thống quy tắc, bảo mật, tối ưu hóa & bài học kinh nghiệm AI
    ├── rules/                  # Quy chuẩn, quy tắc & kỹ năng cho AI (SKILL.md, zalo_automation_rules.md, GEMINI.md)
    ├── guide/                  # Hướng dẫn chi tiết, walkthroughs & tài liệu chuẩn .md
    ├── update/                 # Nhật ký chi tiết toàn bộ tính năng và phiên bản (UPDATE.md, Update1.md)
    ├── autobackups/            # Bản sao lưu mã nguồn và cơ sở dữ liệu (Git ignored)
    ├── build/                  # Thư mục build tạm thời của PyInstaller (Git ignored)
    └── dist/                   # File thực thi AI_Zalo_CSKH.exe & AI_Zalo_CSKH.zip độc lập (Git ignored)
```
