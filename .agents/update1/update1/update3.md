# 🚀 TỔNG HỢP TOÀN BỘ CHỨC NĂNG & KIẾN TRÚC HỆ THỐNG (UPDATE1)
### ⚡ Hệ Thống AI Zalo CSKH - Tự Động Hóa & Quản Lý Giáo Án Lịch Sử GDPT 2018 (Lớp 6 - 12)
*(Bộ Sách Kết Nối Tri Thức Với Cuộc Sống & Mở Rộng Đa Môn Học)*

---

## 📌 MỤC LỤC TỔNG QUAN
1. [Tổng Quan Kiến Trúc & Cấu Trúc Dự Án](#1-tổng-quan-kiến-trúc--cấu-trúc-dự-án)
2. [Hệ Thống Phím Tắt Toàn Cục (Global Hotkeys)](#2-hệ-thống-phím-tắt-toàn-cục-global-hotkeys)
3. [Chi Tiết Toàn Bộ Tính Năng Các Tab Chuyên Sâu](#3-chi-tiết-toàn-bộ-tính-năng-các-tab-chuyên-sâu)
4. [Thanh Công Cụ Nổi Mini On-Top (Floating Mini Toolbar)](#4-thanh-công-cụ-nổi-mini-on-top-floating-mini-toolbar)
5. [Cơ Chế Gửi Ngầm Không Chiếm Chuột & Remote Desktop](#5-cơ-chế-gửi-ngầm-không-chiếm-chuột--remote-desktop)
6. [Hệ Thống Thông Báo Toast Notification Thông Minh](#6-hệ-thống-thông-báo-toast-notification-thông-minh)
7. [Chuẩn Hóa Quản Lý Model Gemini AI (Lọc Thế Hệ Mới >= 3.1)](#7-chuẩn-hóa-quản-lý-model-gemini-ai-lọc-thế-hệ-mới--31)
8. [Bảo Mật, Quản Trị Người Dùng, Nhật Ký Đăng Nhập & 2FA](#8-bảo-mật-quản-trị-người-dùng-nhật-ký-đăng-nhập--2fa)
9. [Sao Lưu, Phục Hồi Dữ Liệu & Tích Hợp Telegram Cloud](#9-sao-lưu-phục-hồi-dữ-liệu--tích-hợp-telegram-cloud)
10. [Tối Ưu Hóa CPU, RAM, CSDL SQLite WAL & Múi Giờ UTC+7](#10-tối-ưu-hóa-cpu-ram-csdl-sqlite-wal--múi-giờ-utc7)
11. [Quy Chuẩn Đồng Bộ Giao Diện Sáng / Tối (Dark / Light Theme Consistency)](#11-quy-chuẩn-đồng-bộ-giao-diện-sáng--tối-dark--light-theme-consistency)
12. [Bảng Tổng Hợp Toàn Bộ Lỗi Đã Khắc Phục, Nguyên Nhân & Code Mẫu Chuẩn](#12-bảng-tổng-hợp-toàn-bộ-lỗi-đã-khắc-phục-nguyên-nhân--code-mẫu-chuẩn)

---

## 🏗️ 1. TỔNG QUAN KIẾN TRÚC & CẤU TRÚC DỰ ÁN

Hệ thống được phát triển theo mô hình đa tầng chuyên nghiệp, tối ưu hóa trên nền tảng **Python 3.12** kết hợp giao diện **Tkinter** tùy biến theo chuẩn **Tailwind CSS Slate Dark & Light Theme**:

```
100AISupport/
│
├── main.py                     # Entry point khởi động ứng dụng & cấu hình UTF-8 toàn diện
├── GEMINI.md                   # Hệ thống quy tắc, bảo mật, tối ưu hóa & bài học kinh nghiệm AI
├── build_exe.bat               # Script đóng gói EXE tự động (output .agents/dist/ & .agents/build/)
├── build_exe.py                # Script PyInstaller tối ưu No-Console & tạo ZIP di động
├── config/                     # Cấu hình hệ thống YAML, ma trận giáo án & Google Drive
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
    ├── UPDATE.md               # Nhật ký chi tiết toàn bộ tính năng và phiên bản
    ├── Update1.md              # Tài liệu tổng hợp toàn diện chức năng từ đầu đến nay
    ├── rules/                  # Quy chuẩn, quy tắc & kỹ năng cho AI (SKILL.md, zalo_automation_rules.md)
    ├── guide/                  # Hướng dẫn chi tiết, walkthroughs & kế hoạch triển khai
    ├── backups/                # Bản sao lưu mã nguồn và cơ sở dữ liệu
    ├── build/                  # Thư mục build tạm thời của PyInstaller
    └── dist/                   # File thực thi AI_Zalo_CSKH.exe & AI_Zalo_CSKH.zip độc lập
```

---

## ⌨️ 2. HỆ THỐNG PHÍM TẮT TOÀN CỤC (GLOBAL HOTKEYS)

| Phím Tắt | Tên Chức Năng | Phạm Vi Hoạt Động | Mô Tả Hoạt Động Chi Tiết |
| :---: | :--- | :--- | :--- |
| **`F10`** | **⚡ Gửi Nhanh Vào Zalo** | Toàn bộ ứng dụng & Bên ngoài | Bắn ngay mẫu kịch bản (Tab 3) hoặc nội dung đã chọn vào Zalo PC hoặc cửa sổ đang mở. |
| **`F8`** | **🟢/⏸ Bật/Tắt Bot AI** | Toàn hệ thống | Bật hoặc tạm dừng lắng nghe & trả lời tự động tin nhắn khách hàng (đổi màu thời gian thực). |
| **`F9`** | **🛑 Hủy Mọi Thao Tác** | Toàn hệ thống | Dừng khẩn cấp mọi tiến trình gửi ngầm, hủy đợt gửi tin, khôi phục quyền điều khiển. |
| **`F6`** | **⏸/▶ Tạm Dừng/Tiếp Tục Gửi** | Tab 2 Broadcast | Tạm dừng hoặc tiếp tục chiến dịch gửi tin nhóm đang chạy dở. |
| **`F7`** | **⏹ Hủy Chiến Dịch Gửi** | Tab 2 Broadcast | Hủy bỏ hoàn toàn chiến dịch gửi tin nhóm hiện tại. |
| **`Ctrl+S`** | **💾 Lưu Nhanh Ngữ Cảnh** | Tab 3, Tab 4, Tab 10 | Tự động lưu Mẫu kịch bản (Tab 3), Khách hàng CRM (Tab 4), Cài đặt (Tab 10). |
| **`Enter`** | **⚡ Đăng Nhập / Gửi Nháp** | Modal Login & Tab 3 | Đăng nhập nhanh tại popup Login; Gửi ngay mẫu kịch bản khi duyệt danh sách. |
| **`Esc`** | **❌ Thoát Nhanh / Đóng Modal**| Login & Dialogs | Đóng các cửa sổ popup đang mở mà không cần dùng chuột. |

---

## 📱 3. CHI TIẾT TOÀN BỘ TÍNH NĂNG CÁC TAB CHUYÊN SÂU

1. **Tab 1: 💬 Trợ Lý AI Chat & Tư Vấn:**
   - Trả lời đa lượt theo ngữ cảnh với Gemini AI.
   - Trả lời trọn vẹn trong 1 tin nhắn duy nhất, không tách rời vụn vặt.
   - Hiển thị thời gian thực theo chuẩn Việt Nam UTC+7 (`Hôm nay 18:20`).
2. **Tab 2: 📢 Gửi Tin Nhắn Nhóm Hàng Loạt (Broadcast):**
   - Hỗ trợ gửi văn bản, ảnh, tệp đính kèm.
   - Lọc nhóm theo Thẻ phân loại (Tags).
   - Điều khiển tiến trình gửi bằng `F6` và `F7`.
3. **Tab 3: ⚡ Kịch Bản Trả Lời Nhanh & Link Khối:**
   - 9 Khối dữ liệu (Lớp 6 - 12, THCS, THPT) với 8 Link linh hoạt mỗi khối.
   - Tùy biến bố cục 2 Cột hoặc 3 Cột ngang.
   - Kho tệp đính kèm linh hoạt theo khối.
4. **Tab 4: 👥 Quản Lý Khách Hàng (CRM):**
   - Quản lý danh sách, số điện thoại, trường học, khối đã mua.
   - Thống kê doanh thu và phân loại trạng thái.
5. **Tab 5: 📁 Phân Quyền Google Drive & Chia Sẻ:**
   - Cấp quyền email tự động, chống quá tải 500 email.
   - Tạo ảnh mockup cấp quyền sắc nét làm bằng chứng.
6. **Tab 6: 📖 Sổ Tay Chỉnh Sửa Giáo Án:**
   - Ghi nhận yêu cầu chỉnh sửa bài giảng, phân loại theo khối/bài.
7. **Tab 7: 🔑 Quản Lý API Keys & Gemini Model:**
   - Multi-Key xoay vòng khi chạm hạn mức Quota (429).
   - Bộ lọc model chuẩn chỉ lấy phiên bản `>= 3.1`.
8. **Tab 8: 📂 Tra Cứu Tài Liệu Giáo Án Cục Bộ:**
   - Tìm kiếm nhanh tài liệu trên ổ đĩa máy tính.
9. **Tab 9: 📜 Nhật Ký & Thống Kê Hoạt Động:**
   - Xem toàn bộ lịch sử tương tác và hoạt động của bot.
10. **Tab 10: ⚙️ Cài Đặt Hệ Thống & Bảo Mật:**
    - Bố cục 50/50 chuẩn (1:1 Ratio) chia đều 2 bên, tự động co giãn.
    - Quản lý tài khoản, mật khẩu mã hóa, 2FA (Mã PIN & TOTP).
    - Tùy chỉnh độ mờ thanh nổi, vị trí Toast, tốc độ gửi, sao lưu & Telegram.

---

## 🪟 4. THANH CÔNG CỤ NỔI MINI ON-TOP (FLOATING MINI TOOLBAR)

- **Kích thước nhỏ gọn:** Chỉ 500x42px, luôn ghim nổi trên cùng màn hình (Always-On-Top).
- **Cơ chế Idle Dimming:** Khi không chạm hoặc rời chuột, thanh tự động làm mờ theo tỷ lệ người dùng cấu hình (`float_idle_alpha`: 15%, 25%, 35% mặc định, 50%, 65%, 80%, 100%). Khi hover chuột hoặc click, sáng rõ 100% tức thì.
- **Nút Mở Rộng `🗖`:** Khôi phục lại toàn bộ cửa sổ Dashboard bất kỳ lúc nào.

---

## ⚡ 5. CƠ CHẾ GỬI NGẦM KHÔNG CHIẾM CHUỘT & REMOTE DESKTOP

- **Silent Deep PostMessage Click:** Gửi tin nhắn và click Win32 API ngầm không làm di chuyển con trỏ chuột vật lý của người dùng.
- **Quick Focus & Restore (<150ms):** Tự động lưu cửa sổ đang làm việc, focus Zalo, paste + enter và trả lại cửa sổ cũ cho người dùng tiếp tục làm việc.
- **Tương thích Remote Desktop:** Hỗ trợ UltraViewer, AnyDesk, TeamViewer, Remote Desktop Connection với cơ chế tự động bù độ trễ mạng (`+1.0s`).

---

## 🍞 6. HỆ THỐNG THÔNG BÁO TOAST NOTIFICATION THÔNG MINH

- **Kích thước động:** Tự động tính toán chiều cao theo độ dài văn bản (`winfo_reqheight()`), không bị cắt chữ hay co hẹp.
- **Vị trí linh hoạt:** 5 vị trí tùy chọn (Mặc định góc phải dưới cùng).
- **Tương thích Theme:** Nền tối chữ trắng sáng sắc nét ở Dark Theme; nền sáng viền xám chữ đen đậm ở Light Theme.

---

## 🤖 7. CHUẨN HÓA QUẢN LÝ MODEL GEMINI AI (LỌC THẾ HỆ MỚI >= 3.1)

- Mặc định chỉ lấy các model Gemini thế hệ mới có phiên bản `>= 3.1` (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.1-flash-lite`, `gemini-flash-latest`, `gemini-pro-latest`...).
- Lọc bỏ hoàn toàn các model cũ (1.0, 1.5, 2.0, 2.5).
- Tự động fallback sang `gemini-3.6-flash` khi kiểm tra kết nối API Key để chống lỗi `404 NOT_FOUND`.

---

## 🔐 8. BẢO MẬT, QUẢN TRỊ NGƯỜI DÙNG, NHẬT KÝ ĐĂNG NHẬP & 2FA

- **Mật khẩu mã hóa:** Lưu trữ SHA-256 trong CSDL và mã hóa XOR + Base64 muối trong `saved_login.json`.
- **Ô nhập để trống mặc định:** Chống lộ thông tin tài khoản.
- **Xác thực 2 bước 2FA:** Hỗ trợ mã PIN bảo mật 4-8 số và mã TOTP 6 số từ Google Authenticator.
- **Nhật ký đăng nhập:** Ghi nhận số lần đăng nhập, thời gian đăng nhập cuối và lịch sử đăng nhập.

---

## 💾 9. SAO LƯU, PHỤC HỒI DỮ LIỆU & TÍCH HỢP TELEGRAM CLOUD

- **Sao lưu toàn diện 100%:** Khách hàng CRM, Kịch bản, Sổ tay, Cài đặt, Lịch sử chat và API keys.
- **Đồng bộ Telegram:** Tự động gửi file backup về Telegram cá nhân/nhóm qua Bot Token & Chat ID âm thầm.

---

## ⚡ 10. TỐI ƯU HÓA CPU, RAM, CSDL SQLITE WAL & MÚI GIỜ UTC+7

- **SQLite WAL Mode:** Đọc ghi đồng thời không khóa file, cache 64MB RAM.
- **Múi giờ Việt Nam (UTC+7):** Toàn bộ tin nhắn và phiên chat được lưu và hiển thị chuẩn theo giờ địa phương (`datetime.now()`). Tự động chạy migration cho dữ liệu cũ.
- **Cache Process Name:** Giảm 99.9% tải CPU khi dò tìm cửa sổ Zalo.
- **Chống Đơ UI ("Not Responding"):** Bắt buộc điều phối cập nhật GUI qua `self.after(0, ...)` và luôn detach luồng trong `finally`.

---

## 🎨 11. QUY CHUẨN ĐỒNG BỘ GIAO DIỆN SÁNG / TỐI (DARK / LIGHT THEME CONSISTENCY)

- **Nguyên tắc tương phản cao:** Mọi widget, chữ viết và khung viền khi tạo mới hoặc chỉnh sửa phải luôn rõ nét, dễ đọc trên cả 2 theme Sáng và Tối.
- **Dark Theme:** Chữ trắng/xanh sáng (`#f8fafc`, `#38bdf8`) trên nền sẫm (`#0f172a`, `#1e293b`).
- **Light Theme:** Chữ đen đậm/xanh đậm (`#0f172a`, `#0284c7`) trên nền trắng sáng (`#ffffff`, `#f8fafc`). Tuyệt đối không để chữ trắng/xám mờ trên nền sáng.
- **Làm mới động:** Khi chuyển theme, các subview vẽ động tự động được refresh lại màu sắc ngay lập tức.

---

## 🛠️ 12. BẢNG TỔNG HỢP TOÀN BỘ LỖI ĐÃ KHẮC PHỤC, NGUYÊN NHÂN & CODE MẪU CHUẨN

| Lỗi Gặp Phải | Nguyên Nhân | Cách Khắc Phục & Code Mẫu Chuẩn |
| :--- | :--- | :--- |
| **Self-Window Target Bug** | Tiêu đề app có từ khóa "Zalo", app nhận nhầm chính mình là Zalo PC. | Loại trừ PID của chính Dashboard: `if pid == os.getpid(): return`. |
| **Not Responding / Thread Lock** | `AttachThreadInput` không detach khi kết thúc; gọi hàm GUI trực tiếp từ background thread. | Luôn detach trong `finally`; cập nhật GUI qua `self.after(0, ...)`. |
| **Sai Giờ Chat (Bị chậm 7 tiếng)** | SQLite mặc định lưu `CURRENT_TIMESTAMP` (UTC). | Lưu giờ địa phương `(datetime('now', 'localtime'))` và dùng `format_smart_timestamp` UTC+7. |
| **Bảng Cài Đặt Bị Co Hẹp Mép Phải** | Dùng `PanedWindow` với `minsize` cứng. | Dùng Grid 2 cột đồng dạng: `columnconfigure(0, weight=1, uniform="settings_col")`. |
| **Toast Bị Cắt Chữ Khi Nội Dung Dài** | Chiều cao Toast cố định `80px`. | Dùng `winfo_reqheight()` đo kích thước động: `toast_h = max(74, req_h + 6)`. |
| **AI Trả Lời Ngắt Quãng Vụn Vặt** | Code cũ dùng `split("\n\n")` tách thành nhiều tin con. | Trả lời nguyên khối trong 1 tin nhắn duy nhất: `[final_reply]`. |
| **Lỗi 404 Check API Key** | Check API Key bằng model legacy đã bị khai tử. | Tự động fallback sang `gemini-3.6-flash` khi test API Key. |
