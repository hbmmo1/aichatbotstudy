# BÁO CÁO FIX LỖI: LOẠI TRỪ TIẾN TRÌNH CHÍNH DASHBOARD (ANTI-SELF TARGET)
- **Mã lỗi**: `FIX-001`
- **Phân loại**: `Lỗi Định Tuyến Tự Động Hóa & Win32`
- **Phiên bản khắc phục**: `v2.0.0`
- **Thời gian fix**: `2026-10-04`

---

## 1. Mô Tả Hiện Tượng
Hệ thống tự động tìm kiếm cửa sổ Zalo bằng từ khóa `"zalo" in title.lower()`. Khi tiêu đề ứng dụng Dashboard là `⚡ AI ZALO CSKH...`, hàm nhận nhầm chính Dashboard là cửa sổ Zalo và paste dữ liệu vào chính mình.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
Quét cửa sổ chỉ dựa trên chuỗi tiêu đề mờ mà không kiểm tra Process ID (`PID`) của tiến trình hiện tại.

## 3. Giải Pháp Khắc Phục (Solution Architecture)
```python
my_pid = os.getpid()
_, pid = win32process.GetWindowThreadProcessId(hwnd)
if pid == my_pid:
    return  # TUYỆT ĐỐI BỎ QUA CỬA SỔ CỦA DASHBOARD NÀY!
if "AI Zalo CSKH" in title or "Quản Lý Giáo Án" in title:
    return
```

## 4. Bài Học & Đề Xuất Tránh Lặp Lại Khi Code Mới
- Mọi hàm tìm kiếm cửa sổ Win32 (`find_zalo_hwnd`, `scan_active_windows`) BẮT BUỘC phải lọc `pid == os.getpid()`.
- Luôn ưu tiên bắt theo tên file thực thi `zalo.exe` thay vì chỉ quét tiêu đề cửa sổ lỏng lẻo.