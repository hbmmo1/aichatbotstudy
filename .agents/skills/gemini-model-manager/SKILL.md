---
name: gemini-model-manager
description: Quản lý danh mục model Google Gemini AI, quy chuẩn lọc thế hệ mới >= 3.1, loại bỏ model legacy, cơ chế fallback chống 404 khi test API key.
---

# KỸ NĂNG: QUẢN LÝ & LỌC MODEL GEMINI AI (MODEL CATALOG & VERSION FILTER)

Quy chuẩn kiến trúc và xử lý tích hợp Google AI Studio API cho ứng dụng AI Zalo CSKH.

---

## 1. Nguyên Tắc Lọc Model Thế Hệ Mới (Chỉ Lấy >= Gemini 3.1)

### 1.1. Bối Cảnh & Mục Tiêu
- Google AI Studio trả về hàng chục model cũ đã bị suy giảm tốc độ hoặc sắp deprecated (1.0, 1.5, 2.0, 2.5...).
- Mặc định hệ thống **BẮT BUỘC chỉ quét, lấy và hiển thị các model Gemini có phiên bản >= 3.1**:
  - `gemini-3.7-flash`
  - `gemini-3.6-flash`
  - `gemini-3.5-flash`
  - `gemini-3.1-flash-lite`
  - `gemini-flash-latest`
  - `gemini-pro-latest`
  - `gemini-3.1-pro-preview`
- Toàn bộ các model cũ (< 3.1) bị lọc bỏ hoàn toàn, không xuất hiện trên các dropdown hoặc bảng chọn.

---

## 2. Cơ Chế Fallback Chống 404 Khi Kiểm Tra API Key

- Khi kiểm tra API Key (`check_single_key`, `check_all_keys`, `test_connection`):
  - Tuyệt đối không gửi model legacy (< 3.1) vào API test.
  - Nếu `model_name` rỗng hoặc là model legacy, hệ thống **bắt buộc tự động fallback sang `gemini-3.6-flash`** để tránh phát sinh lỗi `404 NOT_FOUND` hoặc `400 BAD_REQUEST`.

---

## 3. Cấu Hình Bộ Lọc Linh Hoạt Cho Admin
- Hỗ trợ cấu hình ngưỡng lọc `min_version` linh hoạt (`3.1`, `3.5`, `3.6`, `3.7`, `3.0`, `2.0`, `0.0/All`).
- Đồng bộ thời gian thực: Khi thay đổi bộ lọc ở Tab Cài Đặt (Tab 10) hoặc Tab API Keys (Tab 7), toàn bộ các dropdown trong Header, Chat, Playground tự động cập nhật ngay lập tức.
- Lưu cấu hình bền vững vào `storage/app_settings.json`.

---

## 4. Mã Nguồn Hàm Lọc Phiên Bản Cốt Lõi (`core/key_manager.py`)

```python
import re
from typing import Optional

def get_gemini_model_version(model_name: str) -> Optional[float]:
    """Trích xuất số phiên bản float chính xác từ tên model Gemini."""
    if not model_name:
        return None
    m = model_name.lower().strip()

    # 1. Trích xuất dạng x.y rõ ràng (ví dụ 3.7, 3.6, 3.1, 2.5, 1.5)
    match_dot = re.search(r"gemini[^\d]*(\d+)\.(\d+)", m)
    if match_dot:
        major = int(match_dot.group(1))
        minor = int(match_dot.group(2))
        return major + (minor / 10.0 if minor < 10 else minor / 100.0)

    # 2. Trích xuất dạng x (ví dụ gemini-3-flash, gemini-2-pro)
    match_single = re.search(r"gemini[^\d]*(\d+)", m)
    if match_single:
        return float(match_single.group(1))

    # 3. Model auto-update không có số phiên bản -> gán 99.0 (mới nhất)
    if any(k in m for k in ("latest", "next", "experimental-latest")):
        return 99.0

    # 4. Model legacy không số -> 1.0
    if "gemini" in m:
        return 1.0
    return None

def is_legacy_gemini_model(model_name: str, min_version: float = 3.1) -> bool:
    """Kiểm tra xem model có nhỏ hơn ngưỡng min_version (mặc định 3.1) hay không."""
    ver = get_gemini_model_version(model_name)
    if ver is None:
        return False
    return ver < min_version
```