# ĐẶC TẢ TÍNH NĂNG: THANH CÔNG CỤ NỔI MINI ON-TOP & IDLE DIMMING
- **Mã tính năng**: `FEAT-004`
- **Phiên bản**: `v2.2.0`
- **Lần cập nhật cuối**: `2026-10-08 09:20:00`
- **Bộ điều khiển (Controller)**: `controllers/toolbar_controller.py`
- **Giao diện (Layout)**: `gui/floating_toolbar.py`
- **Đường dẫn tệp áp dụng**: `gui/floating_toolbar.py`, `gui/dashboard.py`

---

## 1. Mục Đích & Yêu Cầu Tính Năng
- Thu nhỏ toàn bộ Dashboard thành thanh công cụ mini float nhỏ gọn (500x42px) luôn ghim On-top trên màn hình để nhân viên CSKH làm việc song song với Zalo PC.
- Tự động làm mờ khi không thao tác chuột để tránh che khuất tầm nhìn của người dùng.

## 2. Giải Pháp Kỹ Thuật
- Cửa sổ frameless `overrideredirect(True)` và `wm_attributes("-topmost", True)`.
- Bộ đếm thời gian kiểm tra sự kiện chuột (`<Enter>`, `<Leave>`, `<Motion>`). Sau 3-5 giây không thao tác, tự giảm độ trong suốt (opacity 0.4 - 0.6). Khi chuột rê vào, ngay lập tức phục hồi độ sáng 100% (opacity 1.0).
- Tích hợp nút gửi nhanh F10 và nút bật/tắt Bot AI CSKH trực tiếp trên thanh nổi.