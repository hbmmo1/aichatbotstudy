# PROMPT ÁP DỤNG DÙNG CHUNG: BỘ LỌC MODEL GEMINI AI >= 3.1 & FALLBACK 404

```text
Khi tích hợp Google Gemini AI vào hệ thống:
1. Mặc định chỉ quét, lấy và hiển thị các model phiên bản >= 3.1 (gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash, gemini-3.1-flash-lite, gemini-flash-latest, gemini-pro-latest).
2. Lọc bỏ hoàn toàn các model cũ legacy (1.0, 1.5, 2.0, 2.5).
3. Khi kiểm tra kết nối API Key, tự động fallback sang gemini-3.6-flash nếu model truyền vào bị rỗng hoặc là model cũ để triệt tiêu lỗi 404 NOT_FOUND.
```