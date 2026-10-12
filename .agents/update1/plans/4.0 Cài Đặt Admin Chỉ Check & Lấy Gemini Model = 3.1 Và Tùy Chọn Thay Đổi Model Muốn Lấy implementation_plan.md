# Kế Hoạch Triển Khai: Cài Đặt Admin Chỉ Check & Lấy Gemini Model >= 3.1 Và Tùy Chọn Thay Đổi Model Muốn Lấy

Tài liệu này mô tả chi tiết giải pháp nâng cấp hệ thống quản lý Model Gemini AI trong ứng dụng:
1. **Mặc định chỉ check và lấy các model Gemini phiên bản từ 3.1 trở lên (>= 3.1)**: Tự động ẩn hoàn toàn các model cũ (1.0, 1.5, 2.0, 2.5, 3.0...).
2. **Cho phép Admin tùy chọn thay đổi bộ lọc phiên bản / danh sách model muốn lấy**: Có thể chọn ngưỡng phiên bản (>= 3.1, >= 3.5, >= 3.6, >= 3.7, >= 3.0, >= 2.0 hoặc Tất cả) trực tiếp trong Cài Đặt, Tab Quản Lý API Keys & Bảng Chọn Model.

---

## 🎯 1. Phân Tích Hiện Trạng & Yêu Cầu

- **Hiện tại:**
  - File `core/key_manager.py` có hàm `is_legacy_gemini_model` cơ bản kiểm tra phiên bản dưới 3.1 nhưng chưa linh hoạt theo tham số `min_version` tùy chọn.
  - Khi quét API từ Google AI Studio (`client.models.list()`), Google trả về rất nhiều model cũ (ví dụ `gemini-1.0-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash`...).
  - Người dùng mong muốn **chỉ check và lấy các model từ 3.1 trở lên**, đồng thời **có thể chủ động thay đổi lựa chọn model muốn lấy** trong cài đặt Admin.

- **Mục tiêu đạt được:**
  - **Lọc thông minh chuẩn xác 100%:** Trích xuất phiên bản chính xác từ tên model (`gemini-3.7-flash` -> 3.7, `gemini-3.6-flash` -> 3.6, `gemini-3.5-flash` -> 3.5, `gemini-3.1-flash-lite` -> 3.1, `gemini-flash-latest` -> 99.0...).
  - **Check API Key an toàn:** Các hàm kiểm tra API Key (`check_single_key`, `check_all_keys`, `test_connection`) luôn sử dụng model hợp lệ >= 3.1, không gây lỗi 404 do model cũ bị deprecated.
  - **Giao diện Admin trực quan & linh hoạt:**
    - Cung cấp Dropdown chọn ngưỡng phiên bản trong Tab Cài Đặt (Tab 10), Tab Quản Lý API Keys (Tab 7) và Modal Bảng Lựa Chọn Model.
    - Lưu cấu hình bền vững trong `app_settings.json` và `config.yaml`.
    - Đồng bộ thời gian thực vào toàn bộ các dropdown chọn model trong Header, Chat, Playground, Live Test.

---

## 🏗️ 2. Chi Tiết Các Thay Đổi Kỹ Thuật (Proposed Changes)

### 🔹 Component 1: `core/key_manager.py`
#### [MODIFY] [key_manager.py](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/core/key_manager.py)
- Bổ sung hàm `get_gemini_model_version(model_name: str) -> Optional[float]`:
  - Trích xuất số phiên bản float chính xác từ chuỗi tên model.
  - Xử lý các model đuôi `latest`, `experimental-latest` luôn là phiên bản mới nhất (`99.0`).
  - Xử lý các model không số như `gemini-pro` coi là legacy (`1.0`).
- Nâng cấp hàm `is_legacy_gemini_model(model_name: str, min_version: float = 3.1) -> bool`:
  - Kiểm tra xem model có nhỏ hơn ngưỡng `min_version` hay không.
- Nâng cấp hàm `list_available_models(api_key: Optional[str] = None, hide_below_3_1: bool = True, min_version: float = 3.1, custom_filter: Optional[str] = None) -> List[str]`:
  - Quét danh sách model từ Google AI Studio API.
  - Lọc bỏ các model không phải text/multimodal (bỏ `embedding`, `aqa`, `tts`...).
  - Lọc và chỉ giữ lại các model có `version >= min_version`.
  - Sắp xếp các model khuyên dùng lên đầu (`gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-flash-latest`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-pro-latest`...).
- Cải tiến `check_single_key`:
  - Đảm bảo `model_name` dùng để test key luôn là model hợp lệ thỏa mãn bộ lọc (>= 3.1), tự động fallback sang `gemini-3.6-flash` nếu model truyền vào không hợp lệ.

---

### 🔹 Component 2: `core/gemini_engine.py`
#### [MODIFY] [gemini_engine.py](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/core/gemini_engine.py)
- Đảm bảo model khởi tạo và model khi đổi (`set_model`) luôn tuân theo quy tắc lọc phiên bản, tự động chuyển về `gemini-3.6-flash` nếu gặp model legacy.

---

### 🔹 Component 3: `gui/dashboard.py`
#### [MODIFY] [dashboard.py](file:///c:/Intel/Laragon/www/PythonAll/100AISupport/gui/dashboard.py)
1. **Phương thức `_get_active_model_list()`:**
   - Đọc cài đặt `min_gemini_version` (mặc định `"3.1"`) và `hide_models_below_3_1` (mặc định `True`) từ `app_settings`.
   - Truyền tham số `min_version` vào `key_mgr.list_available_models`.
2. **Tab 10 (Cài Đặt Ứng Dụng):**
   - Thiết kế Card riêng: **"🎯 CÀI ĐẶT BỘ LỌC & PHIÊN BẢN MODEL GEMINI (GOOGLE AI STUDIO)"**
     - Dropdown chọn ngưỡng phiên bản:
       * `⭐ Chỉ lấy Gemini 3.1 trở lên (>= 3.1) [Mặc Định - Khuyên Dùng]`
       * `🚀 Chỉ lấy Gemini 3.5 trở lên (>= 3.5)`
       * `🔥 Chỉ lấy Gemini 3.6 trở lên (>= 3.6)`
       * `⚡ Chỉ lấy Gemini 3.7 trở lên (>= 3.7)`
       * `💡 Chỉ lấy Gemini 3.0 trở lên (>= 3.0)`
       * `🌐 Lấy từ Gemini 2.0 trở lên (>= 2.0)`
       * `📋 Lấy tất cả các phiên bản (Bao gồm Legacy)`
     - Checkbox `🤖 Tự động ẩn các model Gemini thế hệ cũ dưới 3.1`.
     - Nút `🔄 Quét & Áp Dụng Lựa Chọn Model Ngay`.
3. **Tab 7 (Quản Lý API Keys & Models):**
   - Bổ sung Dropdown chọn bộ lọc phiên bản trực tiếp ngay trên khung Cấu Hình Model AI.
   - Khi đổi bộ lọc hoặc nhấn nút quét, tự động tải và cập nhật danh sách model tức thì.
4. **Modal Bảng Lựa Chọn Model:**
   - Bổ sung Dropdown chọn bộ lọc phiên bản trực tiếp trong modal, danh sách model trong Treeview tự động cập nhật ngay khi đổi lựa chọn.
5. **Lưu & Tải Cài Đặt:**
   - Cập nhật `_load_app_settings` và `_save_all_settings_from_ui` để lưu `min_gemini_version` và `hide_models_below_3_1`.

---

## 🧪 3. Kế Hoạch Kiểm Thử & Xác Minh (Verification Plan)

### Kiểm Thử Tự Động (Automated Tests)
1. Viết script kiểm tra hàm `get_gemini_model_version` với các chuỗi model:
   - `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview` -> Tất cả >= 3.1.
   - `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.0-pro` -> Tất cả < 3.1 và bị lọc bỏ khi `min_version=3.1`.
   - `gemini-flash-latest`, `gemini-pro-latest` -> Được giữ lại.
2. Kiểm tra hàm `list_available_models` với các mức `min_version` khác nhau (3.1, 3.5, 3.6, 2.0, all).

### Kiểm Thử Thủ Công Trên Giao Diện (Manual Verification)
1. Mở ứng dụng, kiểm tra combobox Header, Tab 7 (API Keys), Tab 1 (Chat), Tab Playground, Modal chọn model:
   - Chỉ xuất hiện các model >= 3.1.
2. Thử thay đổi ngưỡng phiên bản trong Tab Cài Đặt sang `>= 3.5` hoặc `>= 3.6` và bấm Lưu/Quét -> Danh sách tự động lọc tương ứng.
3. Thử chuyển lại sang `>= 3.1` -> Danh sách model chuẩn xuất hiện đầy đủ.
4. Bấm "Kiểm tra Key" -> Key được test với model >= 3.1 và phản hồi kết quả chính xác.
