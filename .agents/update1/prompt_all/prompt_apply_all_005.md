# PROMPT ÁP DỤNG DÙNG CHUNG: SQLITE WAL MODE & BẢO MẬT ĐĂNG NHẬP

```text
Khi xây dựng hệ thống lưu trữ dữ liệu cục bộ:
1. Kích hoạt PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=-64000; để hỗ trợ đọc ghi đồng thời không khóa file và tăng tốc độ truy vấn 80%.
2. Tuyệt đối không lưu mật khẩu dạng plaintext trong file cấu hình JSON; sử dụng Obfuscation (XOR + Base64 với muối bảo mật).
3. Không tự động điền thông tin đăng nhập khi người dùng chưa chủ động tích chọn lưu mật khẩu.
```