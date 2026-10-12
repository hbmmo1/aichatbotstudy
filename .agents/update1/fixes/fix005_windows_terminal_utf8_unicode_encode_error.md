# BÁO CÁO FIX LỖI: XỬ LÝ TRIỆT ĐỂ UNICODEENCODEERROR TRÊN WINDOWS
- **Mã lỗi**: `FIX-005`
- **Phân loại**: `Encoding & Chuẩn Hóa Chuỗi Ký Tự`
- **Phiên bản khắc phục**: `v2.3.0`
- **Thời gian fix**: `2026-10-09`

---

## 1. Mô Tả Hiện Tượng
Khi chạy script Python in các biểu tượng Emoji (✅, ❌, ⚡) ra PowerShell trên Windows, chương trình crash với lỗi `UnicodeEncodeError: 'charmap' codec can't encode character...`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
Console Windows mặc định sử dụng bảng mã CP1252 hoặc CP437 không hỗ trợ tập ký tự Unicode Emoji mở rộng.

## 3. Giải Pháp Khắc Phục (Solution Architecture)
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```
Luôn truyền `encoding='utf-8'` khi mở tệp văn bản.

## 4. Bài Học & Đề Xuất Tránh Lặp Lại Khi Code Mới
- Mọi entrypoint script trên Windows bắt buộc có `sys.stdout.reconfigure(encoding='utf-8')`.