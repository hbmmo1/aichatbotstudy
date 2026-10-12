# 🚀 BẢN CẬP NHẬT TÍNH NĂNG MỚI: BÔI ĐEN COPY TỪNG PHẦN, NÚT GHI CHÚ & SỔ TAY GHI CHÚ NHANH (UPDATE5)

## 📌 1. TỔNG QUAN TÍNH NĂNG ĐƯỢC BỔ SUNG

### 🔹 1.1. Bôi Đen & Copy Từng Phần Linh Hoạt (Selection Copy & Context Menu):
- **Khung Chat AI & Khung Nhập Liệu:** Cho phép người dùng dùng chuột click kéo bôi đen bất kỳ một từ, một câu, một đoạn văn bản hoặc toàn bộ câu trả lời của AI / tin nhắn người dùng.
- **Phím Tắt Toàn Cục:** Bấm `Ctrl + C` khi đang bôi đen sẽ tự động sao chép chính xác đoạn văn bản đó vào Windows Clipboard kèm thông báo Toast nổi.
- **Menu Chuột Phải Đa Năng (Right-Click Context Menu):** Khi click chuột phải vào vùng bôi đen hoặc bất kỳ vị trí nào trong khung chat:
  - 📋 **Sao Chép Đoạn Bôi Đen (Ctrl+C)**
  - 📝 **Thêm Đoạn Bôi Đen Vào Sổ Tay Ghi Chú...**
  - ⚡ **Chuyển Đoạn Bôi Đen Sang Mẫu Kịch Bản (Tab 3)...**
  - 🚀 **Bắn Đoạn Bôi Đen Vào Zalo PC Ngay (F10)**
  - 🤖 **Copy Câu Trả Lời AI Gần Nhất**
  - 👤 **Copy Câu Hỏi Người Dùng Gần Nhất**
  - 📝 **Thêm Câu Trả Lời AI Vào Sổ Tay Ghi Chú**
  - ⭐ **Mở Sổ Tay Ghi Chú & Lưu Trữ AI (Quick Notes)**
  - 📑 **Sao Chép Toàn Bộ Cuộc Trò Chuyện**
  - 🔍 **Chọn Tất Cả Nội Dung (Ctrl+A)**
  - 🧹 **Xóa Tin Nhắn Phiên Này**

---

### 🔹 1.2. Nút Copy & Nút Ghi Chú Trên Từng Bong Bóng Tin Nhắn:
- **Tin Nhắn Người Dùng (Tôi - Căn Phải):**
  - Nút **`📋 Copy`**: Sao chép nội dung câu hỏi.
  - Nút **`📝 Ghi Chú`**: Lưu ngay câu hỏi/ghi chú của mình vào CSDL Sổ Tay Ghi Chú.
- **Tin Nhắn AI Gemini (Căn Trái):**
  - Nút **`📋 Copy`**: Sao chép toàn bộ nội dung câu trả lời AI.
  - Nút **`📝 Ghi Chú`**: Lưu ngay câu trả lời này vào Sổ Tay Ghi Chú để tra cứu và mở xem lại bất cứ lúc nào.
  - Nút **`⚡ Kịch Bản`**: Nạp câu trả lời AI sang Tab 3 (Mẫu Kịch Bản Trả Lời Nhanh) chỉ với 1-Click.

---

### 🔹 1.3. Modal "Sổ Tay Ghi Chú & Lưu Trữ AI" (Quick Notes Manager):
- **Nút Mở Nhanh Trên Header Tab 1:** Nút tím nổi bật **`📝 Sổ Tay Ghi Chú`** được tích hợp ngay trên thanh công cụ trên cùng.
- **Giao Diện Modal Hiện Đại & Trực Quan:**
  - **Thanh Tìm Kiếm Realtime:** Tìm kiếm nhanh ghi chú theo từ khóa bất kỳ.
  - **Phân Loại Danh Mục:** Lọc theo danh mục: `Tất Cả`, `Ghi Chú Nhanh`, `Hướng Dẫn Kỹ Thuật`, `Báo Giá & Tư Vấn`, `Mẹo Hay`, `Khác`.
  - **Danh Sách Thẻ (Note Cards):** Hiển thị Badge người gửi (`🤖 AI` / `👤 Bạn`), Danh mục, Tiêu đề, Mốc thời gian (UTC+7) và Nội dung đầy đủ (hỗ trợ bôi đen copy trực tiếp).
  - **Bộ Nút Hành Động Trên Mỗi Thẻ:**
    - `📋 Copy Nội Dung`: Sao chép nhanh vào Clipboard.
    - `🚀 Bắn Zalo`: Gửi trực tiếp nội dung ghi chú sang cửa sổ Zalo PC.
    - `⚡ Sang Kịch Bản (Tab 3)`: Chuyển sang Tab 3 làm mẫu phản hồi nhanh.
    - `✏️ Sửa`: Chỉnh sửa tiêu đề, danh mục, nội dung ghi chú.
    - `🗑️ Xóa`: Xóa ghi chú khỏi sổ tay.
  - **Thao Tác Tổng Thể:** Nút `➕ Thêm Mới`, `🧹 Xóa Hết Ghi Chú`, `✕ Đóng`.

---

### 🔹 1.4. CSDL SQLite Bền Vững (`quick_notes`):
- Tự động khởi tạo bảng `quick_notes` với chỉ mục `idx_quick_notes_created` trong CSDL SQLite WAL Mode.
- Mọi ghi chú được lưu trữ an toàn, tự động đồng bộ múi giờ Việt Nam (UTC+7).
- Hỗ trợ đầy đủ các hàm CRUD: `add_quick_note`, `get_all_quick_notes`, `update_quick_note`, `delete_quick_note`, `clear_all_quick_notes`.
