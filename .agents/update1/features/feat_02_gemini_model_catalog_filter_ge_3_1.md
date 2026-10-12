# ĐẶC TẢ TÍNH NĂNG: QUẢN LÝ & LỌC MODEL GEMINI AI >= 3.1
- **Mã tính năng**: `FEAT-002`
- **Phiên bản**: `v2.3.0`
- **Lần cập nhật cuối**: `2026-10-10 11:30:00`
- **Bộ điều khiển (Controller)**: `core/key_manager.py`, `core/gemini_engine.py`
- **Giao diện (Layout)**: `gui/tabs/tab7_api_keys.py`, `gui/tabs/tab10_settings.py`
- **Đường dẫn tệp áp dụng**: `core/key_manager.py`, `gui/dashboard.py`

---

## 1. Mục Đích & Yêu Cầu Tính Năng
- Google AI Studio trả về hàng chục model cũ đã bị giảm tốc độ hoặc sắp deprecated (1.0, 1.5, 2.0, 2.5...).
- Mặc định hệ thống chỉ quét, lấy và hiển thị các model Gemini có phiên bản >= 3.1 (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-flash-latest`, `gemini-pro-latest`).

## 2. Giải Pháp Kỹ Thuật (Anti-404 Fallback & Regex Extraction)
- Sử dụng Regex bóc tách số phiên bản `major.minor` chính xác.
- Khi kiểm tra kết nối API Key (`check_single_key`, `check_all_keys`), nếu model test bị trống hoặc là model legacy, hệ thống tự động fallback sang `gemini-3.6-flash` để triệt tiêu lỗi 404 NOT_FOUND.
- Cho phép Admin thay đổi ngưỡng `min_version` linh hoạt và tự động đồng bộ real-time sang tất cả các dropdown.