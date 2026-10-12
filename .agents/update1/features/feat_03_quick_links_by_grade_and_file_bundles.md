# ĐẶC TẢ TÍNH NĂNG: ĐÍNH KÈM LINK THEO KHỐI & KHO TỆP GIÁO ÁN
- **Mã tính năng**: `FEAT-003`
- **Phiên bản**: `v2.4.0`
- **Lần cập nhật cuối**: `2026-10-11 16:45:00`
- **Bộ điều khiển (Controller)**: `controllers/script_controller.py`
- **Giao diện (Layout)**: `gui/tabs/tab3_scripts.py`
- **Đường dẫn tệp áp dụng**: `storage/quick_links.json`, `gui/tabs/tab3_scripts.py`

---

## 1. Mục Đích & Yêu Cầu Tính Năng
- Hỗ trợ gửi nhanh đường dẫn tài liệu giáo án Google Drive/OneDrive và nhóm Zalo CSKH theo từng khối lớp (Khối 6-12, Link THCS, Link THPT).
- Mỗi khối gồm 8 link linh hoạt (Link chính, 3 Link dự phòng, Link PPCT & Đề, 3 Link Group Zalo).

## 2. Giải Pháp Kỹ Thuật
- Định dạng mỗi link trên 1 dòng riêng biệt (`\n`), hỗ trợ tùy chọn bật/tắt nhãn tiêu đề link.
- Cho phép gửi tin khi có nội dung kịch bản HOẶC có link khối đính kèm HOẶC có tệp đính kèm.
- Cung cấp nút khôi phục link gốc mặc định từ `DEFAULT_QUICK_LINKS` bất kỳ lúc nào nếu nhập sai.