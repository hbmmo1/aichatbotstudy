# ĐẶC TẢ TÍNH NĂNG: BÔI ĐEN COPY TỪNG PHẦN & SỔ TAY GHI CHÚ
- **Mã tính năng**: `FEAT-005`
- **Phiên bản**: `v2.5.0`
- **Lần cập nhật cuối**: `2026-10-12 10:15:00`
- **Bộ điều khiển (Controller)**: `controllers/notes_controller.py`
- **Giao diện (Layout)**: `gui/tabs/tab1_chat.py`, `gui/notes_drawer.py`
- **Đường dẫn tệp áp dụng**: `gui/tabs/tab1_chat.py`, `core/notes_manager.py`

---

## 1. Mục Đích & Yêu Cầu Tính Năng
- Người dùng có thể bôi đen bất kỳ đoạn văn bản nào trong câu trả lời tư vấn của AI và sao chép trực tiếp qua menu chuột phải.
- Tích hợp thanh Sổ tay ghi chú nhanh ngay bên cạnh vùng chat để lưu các thông tin quan trọng của khách hàng.

## 2. Giải Pháp Kỹ Thuật
- Bắt sự kiện `<Button-3>` trên widget chat, trích xuất vùng lựa chọn `tag_ranges("sel")`.
- Cung cấp nút ghi chú 1-click đưa nội dung đã chọn vào Sổ tay, tự động lưu vào SQLite với mốc thời gian UTC+7.