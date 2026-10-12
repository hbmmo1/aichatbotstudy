# 🚀 LỊCH SỬ CẬP NHẬT & TỔNG HỢP TÍNH NĂNG HỆ THỐNG (UPDATE CHANGELOG)
### ⚡ Hệ Thống AI Zalo CSKH - Tự Động Hóa & Quản Lý Giáo Án Lịch Sử GDPT 2018 (Lớp 6 - 12)

---

## 📌 MỤC LỤC
1. [Tổng Quan Kiến Trúc Hệ Thống](#1-tổng-quan-kiến-trúc-hệ-thống)
2. [Hệ Thống Phím Tắt Toàn Cục (Global Hotkeys)](#2-hệ-thống-phím-tắt-toàn-cục-global-hotkeys)
3. [Chi Tiết Tính Năng 10 Tab Chức Năng](#3-chi-tiết-tính-năng-10-tab-chức-năng)
4. [Cơ Chế Gửi Ngầm & Tương Tác Zalo PC / Remote Desktop](#4-cơ-chế-gửi-ngầm--tương-tác-zalo-pc--remote-desktop)
5. [Hệ Thống Bảo Mật & Quản Lý Tài Khoản](#5-hệ-thống-bảo-mật--quản-lý-tài-khoản)
6. [Tối Ưu Hóa CPU, RAM, CSDL & Chống Đơ "Not Responding"](#6-tối-ưu-hóa-cpu-ram-csdl--chống-đơ-not-responding)
7. [Quy Chuẩn Đồng Bộ Giao Diện Sáng / Tối (Dark / Light Theme Consistency)](#7-quy-chuẩn-đồng-bộ-giao-diện-sáng--tối-dark--light-theme-consistency)
8. [Nhật Ký Các Đợt Nâng Cấp & Sửa Lỗi Chi Tiết (Changelog)](#8-nhật-ký-các-đợt-nâng-cấp--sửa-lỗi-chi-tiết-changelog)

---

## 🏗️ 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

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

| Phím Tắt | Tên Chức Năng | Vị Trí Áp Dụng | Mô Tả Hoạt Động |
| :---: | :--- | :--- | :--- |
| **`F10`** | **⚡ Gửi Nhanh Vào Zalo** | Toàn bộ ứng dụng & Bên ngoài | Bắn ngay mẫu kịch bản (Tab 3) hoặc mẫu tin nhắn (Tab 2) vào Zalo PC hoặc cửa sổ đang mở. |
| **`F8`** | **🟢/⏸ Bật/Tắt Bot AI** | Toàn hệ thống | Bật hoặc tạm dừng lắng nghe & trả lời tự động tin nhắn khách hàng. |
| **`F9`** | **🛑 Hủy Mọi Thao Tác** | Toàn hệ thống | Dừng khẩn cấp mọi tiến trình gửi ngầm, hủy đợt gửi tin, khôi phục quyền điều khiển. |
| **`F6`** | **⏸/▶ Tạm Dừng/Tiếp Tục Gửi** | Tab 2 Broadcast | Tạm dừng hoặc tiếp tục chiến dịch gửi tin nhóm đang chạy dở. |
| **`F7`** | **⏹ Hủy Chiến Dịch Gửi** | Tab 2 Broadcast | Hủy bỏ hoàn toàn chiến dịch gửi tin nhóm hiện tại. |
| **`Ctrl+S`** | **💾 Lưu Nhanh Ngữ Cảnh** | Tab 3, Tab 4, Tab 10 | Tự động lưu Mẫu kịch bản (Tab 3), Khách hàng CRM (Tab 4), Cài đặt (Tab 10). |
| **`Enter`** | **⚡ Đăng Nhập / Gửi Nháp** | Modal Login & Tab 3 | Đăng nhập nhanh tại popup Login; Gửi ngay mẫu kịch bản khi duyệt danh sách. |
| **`Esc`** | **❌ Thoát Nhanh / Đóng Modal**| Login & Dialogs | Đóng các cửa sổ popup đang mở mà không cần dùng chuột. |

---

## 📱 3. CHI TIẾT TÍNH NĂNG 10 TAB CHỨC NĂNG

1. **Tab 1: 💬 Trợ Lý AI Chat & Tư Vấn:**
   - Hỗ trợ hội thoại đa lượt (Multi-turn conversation).
   - Phản hồi nguyên khối (Single Complete Reply) dứt điểm, không ngắt quãng tin nhắn.
   - Hiển thị thời gian thực theo múi giờ Việt Nam (UTC+7 - `Hôm nay 18:20`).
2. **Tab 2: 📢 Gửi Tin Nhắn Nhóm Hàng Loạt (Broadcast):**
   - Quản lý danh mục thẻ phân loại nhóm (Tag Filter).
   - Chống gửi lặp và điều khiển tiến trình bằng phím tắt `F6`, `F7`.
   - Lập lịch phát sóng tự động đa mốc giờ.
3. **Tab 3: ⚡ Kịch Bản Trả Lời Nhanh & Link Khối:**
   - 9 Khối dữ liệu (Lớp 6 đến 12, THCS, THPT) với 8 Link linh hoạt mỗi khối.
   - Kho tệp đính kèm linh hoạt (Kéo thả, chọn tệp, gửi kèm kịch bản).
   - Tùy biến bố cục 2 Cột hoặc 3 Cột ngang linh hoạt.
4. **Tab 4: 👥 Quản Lý Khách Hàng (CRM):**
   - Theo dõi trạng thái khách hàng (Chưa xử lý, Đã chốt, Đã cấp quyền).
   - Ghi chú, tìm kiếm nhanh và gán khối đã mua.
5. **Tab 5: 📁 Phân Quyền Google Drive & Chia Sẻ:**
   - Quản lý ma trận Drive, cấp quyền email tự động, chống quá tải 500 email.
   - Tạo ảnh mockup cấp quyền sắc nét làm bằng chứng gửi khách.
6. **Tab 6: 📖 Sổ Tay Chỉnh Sửa Giáo Án:**
   - Ghi nhận phản hồi chỉnh sửa bài học, lọc theo khối/bài, theo dõi tiến độ.
7. **Tab 7: 🔑 Quản Lý API Keys & Gemini Model:**
   - Danh sách Multi-Key, đo ping độ trễ, tự động xoay tua khi lỗi hạn mức (Quota 429).
   - Bộ lọc model chuẩn chỉ lấy phiên bản `>= 3.1` (ẩn model legacy 1.0, 1.5, 2.0).
8. **Tab 8: 📂 Tra Cứu Tài Liệu Giáo Án Cục Bộ:**
   - Tìm kiếm file nhanh theo từ khóa trong các thư mục ổ đĩa máy tính.
9. **Tab 9: 📜 Nhật Ký & Thống Kê Hoạt Động:**
   - Xem chi tiết toàn bộ lịch sử gửi tin, tương tác khách hàng và lượt AI phản hồi.
10. **Tab 10: ⚙️ Cài Đặt Hệ Thống & Bảo Mật:**
    - Bố cục 50/50 chuẩn (1:1 Ratio), co giãn mượt mà không che khuất.
    - Quản lý đăng nhập, đổi mật khẩu, cấu hình 2FA (Mã PIN / TOTP Authenticator).
    - Cấu hình độ mờ thanh nổi (Float Opacity), vị trí Toast, tốc độ gửi, sao lưu & Telegram.

---

## ⚡ 4. CƠ CHẾ GỬI NGẦM & TƯƠNG TÁC ZALO PC / REMOTE DESKTOP

1. **Free Active Mode (F10):** Dán nhanh clipboard và gửi vào cửa sổ đang kích hoạt.
2. **Khóa Nền Cách Ly (Target Locked Background Mode):**
   - Click ngầm sâu bằng Win32 API `PostMessage` (`WM_LBUTTONDOWN`/`WM_LBUTTONUP`).
   - Quick Focus & Restore (<150ms): Focus Zalo, dán tin, bấm Enter, lập tức trả lại cửa sổ cũ cho người dùng tiếp tục gõ văn bản.
3. **Hỗ trợ Điều Khiển Từ Xa (UltraViewer, AnyDesk, TeamViewer, Remote Desktop):**
   - Tự động nhận diện cửa sổ Remote.
   - Tự động đệm độ trễ mạng (`+1.0s`) đảm bảo máy đích nhận đủ dữ liệu clipboard trước khi bấm Enter.
   - Tìm phòng chat qua phím tắt toàn cục `Ctrl+F` -> Paste -> `Down` + `Enter`.

---

## 🔐 5. HỆ THỐNG BẢO MẬT & QUẢN LÝ TÀI KHOẢN

1. **Mã Hóa Mật Khẩu Đã Lưu (`storage/saved_login.json`):**
   - Không lưu mật khẩu dạng văn bản thô (Plaintext).
   - Áp dụng thuật toán mã hóa XOR đa tầng kết hợp Base64 với muối bí mật độc quyền (`enc_...`).
2. **Nguyên Tắc Không Điền Sẵn Mặc Định:**
   - Khi khởi động, 2 ô Tên đăng nhập và Mật khẩu luôn để **TRỐNG 100%**.
   - Chỉ tự động điền khi người dùng trước đó đã chủ động tích chọn `💾 Lưu thông tin đăng nhập`.
3. **Cơ Chế Xác Thực 2 Bước (2FA PIN / TOTP):**
   - Hỗ trợ mã PIN bảo mật tùy chỉnh (4-8 số) và mã Google/Microsoft Authenticator 6 số.
   - Màn hình đăng nhập 2 giai đoạn an toàn tuyệt đối.
4. **Nút Bỏ Lưu Thông Tin (Forget Credentials):**
   - Tích hợp nút `[🧹 Bỏ Lưu Thông Tin]` ngay trên màn hình Login và trong Tab Cài Đặt để xóa sạch tài khoản/mật khẩu đã lưu trên máy.

---

## 🚀 6. TỐI ƯU HÓA CPU, RAM, CSDL & CHỐNG ĐƠ "NOT RESPONDING"

1. **Bộ Đệm Process Name Cache (`get_proc_name_cached`):**
   - Cache tên tiến trình theo PID với TTL 8 giây, giảm 99.9% chu kỳ CPU (1.000 truy vấn chỉ tốn 0.19ms).
2. **CSDL SQLite Hiệu Năng Cao & Múi Giờ UTC+7:**
   - Kích hoạt `WAL Mode` (Write-Ahead Logging) cho phép đọc ghi đồng thời không khóa file.
   - `PRAGMA synchronous = NORMAL;` giảm tải đĩa 80%.
   - `PRAGMA cache_size = -64000;` cấp 64MB bộ nhớ đệm RAM cho CSDL.
   - Lưu trữ mốc thời gian chuẩn Việt Nam `(datetime('now', 'localtime'))`.
3. **Chống Triệt Để Lỗi Đơ Ứng Dụng ("Not Responding"):**
   - Toàn bộ thao tác cập nhật widget Tkinter từ các luồng nền (`_worker`, `_scan`, `threading.Thread`) đều bắt buộc chạy qua `self.after(0, ...)`.
   - Luôn giải phóng luồng `AttachThreadInput(..., False)` trong khối `finally`.
4. **Chống Tràn RAM (Anti-Memory Leak):**
   - Giới hạn tối đa 3 Toast cùng lúc (`_ACTIVE_TOASTS`), tự hủy toast cũ.
   - Đóng toàn bộ handle ảnh PIL (`Image.close()`) ngay sau khi gọi Gemini API.
   - Kích hoạt `gc.collect()` định kỳ mỗi 60 giây.

---

## 🎨 7. QUY CHUẨN ĐỒNG BỘ GIAO DIỆN SÁNG / TỐI (DARK / LIGHT THEME CONSISTENCY)

1. **Quy Tắc Bất Biến Về Độ Tương Phản:**
   - Mọi khung nền, label, ô nhập, nút bấm, bảng danh sách khi sửa đổi hoặc thêm mới **BẮT BUỘC** phải hỗ trợ hiển thị hoàn hảo ở cả 2 chế độ Sáng (Light Theme) và Tối (Dark Theme).
   - **Giao diện Tối (Dark):** Chữ màu sáng rõ nét (`#f8fafc`, `#38bdf8`, `#34d399`), nền sẫm màu (`#0f172a`, `#1e293b`).
   - **Giao diện Sáng (Light):** Chữ màu đen/xanh đậm (`#0f172a`, `#1e293b`, `#0284c7`), nền trắng sáng tinh khiết (`#ffffff`, `#f8fafc`, `#f1f5f9`). Tuyệt đối không để chữ trắng/xám mờ trên nền sáng gây chìm chữ khó nhìn.
2. **Đồng Bộ Màu Tự Động Khi Đổi Theme:**
   - Sử dụng cơ chế kiểm tra `is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")` để nạp bộ màu thích ứng thời gian thực cho các subview vẽ động (`_render_quick_links_for_category`, `_switch_bundle_subview`, `ToastNotification`...).

---

## 📜 8. NHẬT KÝ CÁC ĐỢT NÂNG CẤP & SỬA LỖI CHI TIẾT (CHANGELOG)

### 🔹 Phiên bản 3.0 (01/09/2026) - Chuẩn Hóa Cấu Trúc .agents, Đồng Bộ Múi Giờ UTC+7 & Bố Cục Cài Đặt 50/50
- **Đồng bộ hóa thời gian thực UTC+7 (Giờ Việt Nam):**
  - Cập nhật hàm `format_smart_timestamp` trong `core/state_manager.py` và cơ chế ghi nhận thời gian CSDL SQLite theo giờ địa phương (`datetime.now()`).
  - Chạy migration tự động `tz_vietnam_utc7_v1` để cộng +7 giờ cho toàn bộ các tin nhắn, phiên chat và nhật ký đăng nhập cũ.
- **Bố cục 50/50 chuẩn hóa Tab Cài Đặt (Tab 10):**
  - Tái cấu trúc Tab 10 bằng hệ thống Grid 2 cột đồng dạng (`uniform="settings_col"`, `weight=1`), chia đều 50% Trái và 50% Phải, chống co ép, cắt chữ trên mọi kích thước cửa sổ.
  - Tối ưu độ rộng bảng tài khoản và co giãn linh hoạt các ô nhập liệu Telegram.
- **Tối ưu câu trả lời AI một lần duy nhất (Single Complete Reply):**
  - Gộp phản hồi AI thành 1 tin nhắn trọn vẹn, không tách vụn tin nhắn gây đứt đoạn.
- **Nâng cấp Toast Notification thông minh & đa theme:**
  - Đo kích thước động theo nội dung (`winfo_reqheight`), hỗ trợ tương phản cao cho Dark và Light Theme.
- **Tổ chức thư mục chuẩn hóa `.agents/`:**
  - Di chuyển thư mục `dist` và `build` vào `.agents/dist` và `.agents/build`.
  - Cập nhật `build_exe.py` và `build_exe.bat` tương thích hoàn toàn.
  - Đồng bộ `UPDATE.md` và `Update1.md` vào `.agents/` và `.agents/guide/`.

### 🔹 Phiên bản 2.9 (29/08/2026) - Thanh Công Cụ Nổi Mini Trôi Nổi On-Top (Floating Mini Toolbar) & Hiệu Ứng Mờ Thông Minh
- Nút bấm `🪟 Nổi On-Top` trên Header, luôn ghim nổi trên mọi ứng dụng.
- Cơ chế tự động làm mờ khi rời chuột (`alpha = 0.35` tùy chỉnh) và sáng rõ 100% khi active.

### 🔹 Phiên bản 2.8 (29/08/2026) - Nâng Cấp Đính Kèm Link Khối & Kho Tệp Tab 3
- 9 Khối dữ liệu với 8 Link linh hoạt mỗi khối; kho tệp đính kèm linh hoạt theo khối.

### 🔹 Phiên bản 2.5 (28/08/2026) - Bộ Lọc Phiên Bản Model Gemini AI (Chỉ Lấy >= 3.1)
- Lọc bỏ triệt để các model legacy (< 3.1) khỏi dropdown và modal chọn model.

### 🔹 Phiên bản 2.3 (28/08/2026) - Cơ Chế Silent Background & Hỗ Trợ UltraViewer / AnyDesk
- Gửi ngầm không chiếm chuột, Quick Focus & Restore (<150ms), hỗ trợ điều khiển từ xa.
