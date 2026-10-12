# 🚀 Hướng Dẫn Sử Dụng & Tổng Kết Dự Án AI CSKH Zalo Giáo Án Lịch Sử 6-12

Dự án đã được thiết kế và xây dựng hoàn chỉnh tại thư mục:
📂 `c:/Intel/Laragon/www/PythonAll/100AISupport/`

---

## 🌟 Các Tính Năng Đã Triển Khai Hoàn Chỉnh

### 1. Bộ Tri Thức Kỹ Thuật (Knowledge Base) Giải Quyết Đúng Vấn Đề Thầy/Cô Hay Gặp
* **Lỗi tải file dở dang do mạng yếu / file video nặng:** AI nhắc bấm `Ctrl + J` để xem danh sách tải và bấm nút **"Tiếp tục" (Resume)**.
* **Lỗi thiếu file khi tải hàng loạt:** AI hướng dẫn bấm **"Cho phép" (Allow)** trên góc phải trình duyệt để tải đủ các file.
* **Lỗi ổ đĩa C bị đầy:** AI hướng dẫn chuột phải vào link -> chọn *"Lưu liên kết thành..."* để lưu sang ổ `D:` hoặc `E:`.
* **Lỗi mở file PowerPoint nặng trực tiếp trên web:** AI giải thích file có video và hiệu ứng nên cần tải về mở bằng PowerPoint trên máy tính.
* **Lỗi không sửa được chữ (Protected View):** AI hướng dẫn bấm nút **"Enable Editing" / "Bật tính năng chỉnh sửa"** màu vàng trên Word/PowerPoint.
* **Xóa số điện thoại / thông tin quảng cáo:** AI hướng dẫn vào thẻ `View` -> `Slide Master` hoặc `Insert` -> `Header & Footer`.
* **Hình khối/icon đang cập nhật:** AI nói khéo léo để cố định khung chuẩn cho máy chiếu trường học và hẹn gửi bản cập nhật sau.

---

### 2. Xử Lý Phản Hồi Nội Dung & "Sổ Tay Sửa Giáo Án" Tự Động
* Khi thầy/cô phản hồi thiếu bài, sai kiến thức hoặc chưa đúng chuẩn 3 bộ sách mới (*Cánh Diều, Kết Nối Tri Thức, Chân Trời Sáng Tạo*):
  * **AI trả lời cực kỳ khiêm tốn, kính trọng và cảm ơn đóng góp chuyên môn của thầy/cô.**
  * **Tự động trích xuất thông tin:** Lớp mấy, bài nào, nội dung cần chỉnh sửa.
  * **Lưu vào Sổ tay kỹ thuật (SQLite):** Hiển thị ngay trên Tab *"Sổ Tay Sửa Giáo Án"* trên giao diện để bạn mở ra xem danh sách cần sửa lúc rảnh.
  * Bạn có thể bấm nút **"Đã Sửa Xong Giáo Án Này"** hoặc gắn nhãn chỉ bằng 1 cú click chuột.

---

### 3. Cảnh Báo Khẩn Cấp Qua Telegram (Sau 3 Lần Chưa Hài Lòng)
* Khi khách hàng hỏi lại hoặc gặp vấn đề lặp lại đến **lần thứ 3**:
  * Bot tự động bắn thông báo khẩn cấp tới Telegram của bạn kèm: **Tên khách + Zalo ID + Tóm tắt vấn đề + Tin nhắn gần nhất**.
  * Bot tự động **tạm dừng** cho khách này và gửi lời nhắn *"Dạ em đã chuyển thông tin sang Chuyên viên Kỹ thuật hỗ trợ trực tiếp..."* để bạn vào can thiệp.

---

### 4. Hệ Thống Phím Tắt Toàn Cục (Global Hotkeys)
* **`F8`**: Bắt đầu Bot.
* **`F9`**: Tạm dừng Bot khẩn cấp.
* **`F10`**: Tiếp tục Bot.
* **`Ctrl + Space`**: Bật chế độ can thiệp thủ công (nhường bạn tự chat).

---

### 5. Phân Quyền Google Drive Tự Động (Lớp 6 đến 12)
* Quản lý ma trận phân quyền: Khối THCS (6-7-8-9), Khối THPT (10-11-12) hoặc từng lớp lẻ.
* Tự động cấp quyền *"Chỉ xem (Viewer)"* qua email Gmail của thầy/cô.

---

## 🖥️ Cách Chạy Ứng Dụng

1. **Mở Terminal / PowerShell** tại thư mục dự án:
   ```bash
   cd c:\Intel\Laragon\www\PythonAll\100AISupport
   ```
2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Cấu hình API Key (Nếu có):**
   * Mở file [config/config.yaml](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/config/config.yaml) và điền `api_key` của Gemini (lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/)).
4. **Khởi động Giao diện Bảng Điều Khiển:**
   ```bash
   python main.py
   ```
