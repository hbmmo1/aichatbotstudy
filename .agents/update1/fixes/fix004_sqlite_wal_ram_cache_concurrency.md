# BÁO CÁO FIX LỖI: KHẮC PHỤC KHÓA FILE SQLITE BẰNG WAL MODE
- **Mã lỗi**: `FIX-004`
- **Phân loại**: `CSDL & Truy Vấn Đồng Thời`
- **Phiên bản khắc phục**: `v2.2.0`
- **Thời gian fix**: `2026-10-08`

---

## 1. Mô Tả Hiện Tượng
Khi Bot AI đang ghi nhật ký chat đồng thời người dùng đang tra cứu lịch sử ở Tab 6, hệ thống văng lỗi `sqlite3.OperationalError: database is locked`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
SQLite mặc định ở chế độ Journal Mode Rollback khóa toàn bộ tệp database khi có một luồng ghi.

## 3. Giải Pháp Khắc Phục (Solution Architecture)
Kích hoạt WAL Mode (Write-Ahead Logging) và tăng cache RAM 64MB:
```python
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA cache_size=-64000;")
conn.execute("PRAGMA temp_store=MEMORY;")
```

## 4. Bài Học & Đề Xuất Tránh Lặp Lại Khi Code Mới
- Luôn kích hoạt WAL mode cho mọi kết nối SQLite đa luồng.