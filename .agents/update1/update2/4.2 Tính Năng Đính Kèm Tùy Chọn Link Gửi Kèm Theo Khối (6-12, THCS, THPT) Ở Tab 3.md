# Kế Hoạch Triển Khai: Tính Năng Đính Kèm Tùy Chọn Link Gửi Kèm Theo Khối (6-12, THCS, THPT) Ở Tab 3

Tài liệu này mô tả chi tiết thiết kế và giải pháp triển khai tính năng **Đính kèm Link gửi kèm theo Khối** trong Tab 3 (Kịch Bản Trả Lời Nhanh).

---

## 🎯 1. Phân Tích Yêu Cầu

1. **Vị trí tính năng:** Tab 3 - Kịch Bản Trả Lời Nhanh.
2. **Cấu trúc Link theo Khối:**
   - Hỗ trợ đầy đủ các khối: **Khối 6, Khối 7, Khối 8, Khối 9, Khối 10, Khối 11, Khối 12, Link THCS, Link THPT**.
   - Mỗi khối có các link linh hoạt: **Link 1, Link 2, Link 3, Link 4, Link 5, Link Group 1, Link Group 2, Link Group 3...** (Bao gồm link chính, các link dự phòng và link nhóm Zalo).
3. **Cơ chế chọn & gửi link:**
   - Mỗi link có Checkbox để người dùng tích chọn gửi kèm hay không.
   - Định dạng mỗi link 1 dòng.
   - Tùy chọn bật/tắt ghi chú / nhãn phía trước link (Ví dụ: `Khối 6 - Link 1: https://...` hoặc chỉ gửi link trần `https://...` khi tắt nhãn).
   - Tự động gộp nội dung các link được tích chọn vào tin nhắn khi bấm **"🚀 GỬI VÀO ZALO"**, **"📝 Chèn Nháp"** hoặc **"📋 Copy"**.
4. **Quản lý & Chỉnh sửa Link:**
   - Lưu trữ danh sách link bền vững vào file `storage/quick_links.json`.
   - Có Modal **"⚙️ Quản Lý & Chỉnh Sửa Link Các Khối"** để người dùng dễ dàng cập nhật link Google Drive / Nhóm Zalo bất cứ lúc nào.
5. **Cập nhật tài liệu:** Cập nhật `UPDATE.md` và `GEMINI.md`.

---

## 🏗️ 2. Chi Tiết Các Thay Đổi Kỹ Thuật

### 🔹 Component 1: `gui/dashboard.py`
#### [MODIFY] [dashboard.py](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/gui/dashboard.py)
1. **Khởi tạo dữ liệu Link các Khối (`_load_quick_links`, `_save_quick_links`):**
   - Khởi tạo mặc định đầy đủ 9 khối: `Khối 6`, `Khối 7`, `Khối 8`, `Khối 9`, `Khối 10`, `Khối 11`, `Khối 12`, `Link THCS`, `Link THPT`.
   - Mỗi khối chứa danh sách link: `Link 1 (Chính)`, `Link 2 (Dự phòng 1)`, `Link 3 (Dự phòng 2)`, `Link 4 (Dự phòng 3)`, `Link 5`, `Link Group 1 (Nhóm Zalo 1)`, `Link Group 2 (Nhóm Zalo 2)`, `Link Group 3 (Nhóm Zalo 3)`.
   - Lưu bền vững trong `storage/quick_links.json`.
2. **Giao diện Đính Kèm Link trong Tab 3:**
   - Tích hợp khung điều khiển Link thông minh trong Tab 3:
     * Segmented Switcher / Selector Khối: `[Khối 6]`, `[Khối 7]`, `[Khối 8]`, `[Khối 9]`, `[Khối 10]`, `[Khối 11]`, `[Khối 12]`, `[Link THCS]`, `[Link THPT]`.
     * Danh sách checkbox từng link của khối đang chọn: `☑️ Link 1`, `☑️ Link 2`, `☑️ Link 3`, `☑️ Link 4`, `☑️ Link 5`, `☑️ Link Group 1`, `☑️ Link Group 2`, `☑️ Link Group 3`.
     * Checkbox `🏷️ Kèm nhãn ghi chú trước link` (Bật / Tắt).
     * Nút `☑️ Chọn Hết`, `☐ Bỏ Chọn`, `⚙️ Sửa Link Khối...`.
     * Badge đếm realtime: `🔗 Đang chọn: X link`.
3. **Nâng cấp hàm gửi `_send_current_script_to_zalo` & `_copy_current_script_answer`:**
   - Tự động lấy danh sách link đang được tích chọn.
   - Ghép vào nội dung tin nhắn kịch bản (mỗi link 1 hàng, có/không kèm nhãn theo cài đặt).
4. **Modal Quản Lý Link Khối (`_open_quick_links_manager_modal`):**
   - Cho phép người dùng chỉnh sửa URL và tên ghi chú của từng link cho tất cả các khối và lưu lại.

---

### 🔹 Component 2: `UPDATE.md`
#### [MODIFY] [UPDATE.md](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/UPDATE.md)
- Ghi nhận tính năng mới vào mục Phiên bản 2.6: Đính kèm tùy chọn Link gửi kèm theo Khối 6-12, THCS, THPT trong Tab 3.

---

## 🧪 3. Kế Hoạch Kiểm Thử (Verification Plan)

### Automated / Syntax Tests
- Chạy lệnh kiểm tra cú pháp và logic khởi tạo dữ liệu link của `dashboard.py`.

### Manual Tests
1. Mở Tab 3, chuyển qua lại giữa các Khối (Khối 6 -> 12, THCS, THPT).
2. Tích chọn một số link (ví dụ Khối 6: Link 1, Link Group 1).
3. Thử bật/tắt checkbox "Kèm nhãn ghi chú".
4. Bấm "Copy" hoặc "Chèn Nháp" -> Kiểm tra nội dung tạo ra có đúng định dạng từng link 1 dòng.
5. Mở Modal "Sửa Link Khối", thay đổi URL và lưu lại -> Kiểm tra link mới được áp dụng chính xác.
