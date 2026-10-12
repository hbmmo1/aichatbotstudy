# BÁO CÁO FIX LỖI: CHỐNG ĐƠ ỨNG DỤNG BẰNG FINALLY DETACH THREAD INPUT
- **Mã lỗi**: `FIX-002`
- **Phân loại**: `Ổn Định Hệ Thống & Chống Treo GUI`
- **Phiên bản khắc phục**: `v2.1.0`
- **Thời gian fix**: `2026-10-06`

---

## 1. Mô Tả Hiện Tượng
Sau khi gửi tin ngầm, Dashboard bị đóng băng hoàn toàn thành trạng thái **"Not Responding"**, người dùng không thể bấm chuột hoặc thao tác trên bất kỳ nút nào.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
Lệnh `win32process.AttachThreadInput(curr_thread, fore_thread, True)` gắn hàng đợi thông điệp của Dashboard vào cửa sổ ngoài nhưng không được detach khi có lỗi hoặc khi kết thúc hàm. Khi luồng ngoài kết thúc hoặc ngủ, hàng đợi bị khóa cứng.

## 3. Giải Pháp Khắc Phục (Solution Architecture)
Bắt buộc bọc lệnh detach trong khối `finally`:
```python
finally:
    if attached_thread and curr_thread:
        try:
            win32process.AttachThreadInput(curr_thread, attached_thread, False)
        except Exception:
            pass
```

## 4. Bài Học & Đề Xuất Tránh Lặp Lại Khi Code Mới
- Không bao giờ gọi AttachThreadInput mà không có khối `try...finally`.
- Mọi hàm cập nhật widget từ background worker bắt buộc điều phối qua `self.after(0, ...)`.