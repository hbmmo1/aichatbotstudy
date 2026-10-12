# ĐẶC TẢ KỸ THUẬT & PROMPT MẪU CHUẨN: HỆ THỐNG KNOWLEDGE & UPDATEDONE HUB (SPA)
> **Mã quy chuẩn:** `SPEC-PROMPT-HUB-V2.9.2`  
> **Phiên bản:** `v2.9.2`  
> **Vị trí lưu trữ:** `C:\Intel\Laragon\www\300_Python\300_AISupport\.agents\update1\Prompt_Ki_Thuat.md`  
> **Mục đích:** Đặc tả kỹ thuật và Prompt mẫu hoàn chỉnh để tạo, sao chép hoặc triển khai hệ thống Knowledge Hub / Updatedone cho **bất kỳ tệp văn bản thô nào, bất kỳ thư mục nào và bất kỳ dự án nào** (Ví dụ: `C:\Intel\Laragon\www\info\.agents\updatedone`, `C:\Intel\Laragon\www\LOG`, hoặc bất kỳ dự án nào khác).

---

## 📋 MỤC LỤC
1. [Khung Prompt Sẵn Sàng Giao Việc Cho AI Agent (Copy-Paste Prompt)](#1-khung-prompt-sẵn-sàng-giao-việc-cho-ai-agent-copy-paste-prompt)
2. [Mục Tiêu & Tiêu Chuẩn Trọng Tâm Hệ Thống](#2-mục-tiêu--tiêu-chuẩn-trọng-tâm-hệ-thống)
3. [Quy Tắc Quản Lý & Bóc Tách Dữ Liệu Từ `Hoi Dap.txt` (Ngăn Bởi Dấu `==`)](#3-quy-tắc-quản-lý--bóc-tách-dữ-liệu-từ-hoi-daptxt-ngăn-bởi-dấu-)
4. [Kiến Trúc Thư Mục Tiêu Chuẩn Toàn Dự Án](#4-kiến-trúc-thư-mục-tiêu-chuẩn-toàn-dự-án)
5. [Đặc Tả Cơ Sở Dữ Liệu `changelog_data.json` & Cơ Chế Hybrid Offline (Không CORS)](#5-đặc-tả-cơ-sở-dữ-liệu-changelog_datajson--cơ-chế-hybrid-offline-không-cors)
   - [5.1. Cấu Trúc Schema Chuẩn Của `changelog_data.json`](#51-cấu-trúc-schema-chuẩn-của-changelog_datajson)
   - [5.2. Kỹ Thuật Hybrid Offline (Khắc Phục Lỗi CORS Trình Duyệt)](#52-kỹ-thuật-hybrid-offline-khắc-phục-lỗi-cors-trình-duyệt)
   - [5.3. ⚠️ Lưu Ý Trọng Yếu: Escape Chuỗi JSON Nhúng (Chống Lỗi Data Syntax Crash)](#53-️-lưu-ý-trọng-yếu-escape-chuỗi-json-nhúng-chống-lỗi-data-syntax-crash)
6. [Đặc Tả Chi Tiết Giao Diện & Tính Năng SPA (index.html)](#6-đặc-tả-chi-tiết-giao-diện--tính-năng-spa-indexhtml)
   - [6.1. Cụm Nút Điều Hướng Nổi (Floating Nav Dock 5 Nút)](#61-cụm-nút-điều-hướng-nổi-floating-nav-dock-5-nút)
   - [6.2. Bộ Hẹn Giờ Tự Động Ẩn Dock (Auto-Hide Idle Timer)](#62-bộ-hẹn-giờ-tự-động-ẩn-dock-auto-hide-idle-timer)
   - [6.3. Bảng Khung Tệp & Đường Dẫn Kỹ Thuật (MVC & Path Info - Relative Path)](#63-bảng-khung-tệp--đường-dẫn-kỹ-thuật-mvc--path-info)
   - [6.4. Chuẩn Hóa Màu Sắc Giao Diện Sáng & Tối (Light / Dark Mode Contrast)](#64-chuẩn-hóa-màu-sắc-giao-diện-sáng--tối-light--dark-mode-contrast)
   - [6.5. Trình Phân Tích Cú Pháp Markdown & Khắc Phục Lỗi Marked.js v12+](#65-trình-phân-tích-cú-pháp-markdown--khắc-phục-lỗi-markedjs-v12)
   - [6.6. Cơ Chế Cuộn Đa Mục Tiêu & Nhấn Giữ (Hold to Scroll / Long-Press)](#66-cơ-chế-cuộn-đa-mục-tiêu--nhấn-giữ-hold-to-scroll--long-press)
   - [6.7. Quy Tắc Đồng Bộ 2 File index.html & Định Tuyến Web Server](#67-quy-tắc-đồng-bộ-2-file-indexhtml--dọn-dẹp-file-thừa)
7. [Quy Trình Triển Khai Từng Bước Cho Dự Án Mới (Step-by-Step Execution)](#7-quy-trình-triển-khai-từng-bước-cho-dự-án-mới-step-by-step-execution)
8. [Bộ Kiểm Tra Chất Lượng Nghiệm Thu (Quality Assurance Checklist)](#8-bộ-kiểm-tra-chất-lượng-nghiệm-thu-quality-assurance-checklist)

---

## 1. KHUNG PROMPT SẴN SÀNG GIAO VIỆC CHO AI AGENT (COPY-PASTE PROMPT)

> *Khi cần thực hiện cho một dự án mới (ví dụ `C:\Intel\Laragon\www\info\.agents\updatedone` hoặc bất kỳ dự án nào), chỉ cần sao chép đoạn Prompt bên dưới, thay đổi đường dẫn nguồn và đích rồi giao cho AI Agent thực hiện:*

```markdown
Bạn hãy đóng vai trò là Chuyên Gia Kỹ Sư Phần Mềm Full-Stack.
Nhiệm vụ của bạn là xây dựng Hệ Thống Tài Liệu Tri Thức & Updatedone Hub (Zero-Reload Offline SPA) chuẩn 100% theo đặc tả SPEC-PROMPT-HUB-V2.9.2:

1. DỰ ÁN THỰC HIỆN:
   - Thư mục nguồn (dữ liệu thô): [ĐƯỜNG_DẪN_TỆP_HOIDAP_HOẶC_THƯ_MỤC_NGUỒN] 
     (Ví dụ: C:\Intel\Laragon\www\LOG\.agents\updatedone\Hoi Dap.txt)
   - Thư mục dự án đích: [ĐƯỜNG_DẪN_PROJECT_ĐÍCH] 
     (Ví dụ: C:\Intel\Laragon\www\info\.agents\updatedone và C:\Intel\Laragon\www\info)
   - Tiêu đề hệ thống: [TÊN_TIÊU_ĐỀ_HUB] (Ví dụ: "AI Zalo CSKH - Technical Architecture & Knowledge Hub")
   - Phiên bản: v2.9.2

2. QUẢN LÝ DỮ LIỆU ĐẦU VÀO:
   - Nếu nguồn là file text như "Hoi Dap.txt", phân tích từng mục được ngăn cách bởi dấu `==` (regex `(?m)^\s*(?:\d+)?={2,}\s*$`).
   - Xóa sạch 100% các ký tự phân cách thô như `==`, `====`, `======`, `===**React**...`.
   - Tuyệt đối không để dính nội dung của chủ đề này vào chủ đề khác.
   - Bóc tách thành các file .md con độc lập lưu trong thư mục: [PROJECT_ĐÍCH]/.agents/update1/knowledge/ (đánh số thứ tự 01_, 02_, ...).
   - Biên dịch toàn bộ thành file dữ liệu trung tâm changelog_data.json.

3. XÂY DỰNG GIAO DIỆN SPA (index.html):
   - Tạo Single Page Application không cần load lại trang để xem mô tả từng phần trong các file .md.
   - Cơ chế Hybrid Offline: Nhúng toàn bộ dữ liệu vào thẻ <script id="embedded-dataset" type="application/json"> trong index.html để mở trực tiếp qua file:/// không bị lỗi CORS.
   - Chỉ duy trì đúng 2 file index.html đồng bộ mã nguồn 100%: 1 file ở thư mục gốc dự án và 1 file ở .agents/update1/index.html. Xóa sạch file thừa (như index1.html, index2.html).

4. CÁC TÍNH NĂNG BẮT BUỘC ĐẠT CHUẨN 100%:
   a. Cụm Nút Điều Hướng Nổi (Floating Nav Dock 5 nút):
      - Nút Cam: Mở Modal Mục Lục Toàn Cảnh (Master TOC).
      - Nút Cuộn Lên (fa-angles-up): Click cuộn mượt về đầu; Nhấn giữ (mousedown/touchstart) cuộn liên tục.
      - Nút Cuộn Giữa (fa-arrows-up-down): Cuộn nhanh đến giữa trang (50%).
      - Nút Cuộn Xuống (fa-angles-down): Click cuộn mượt về cuối; Nhấn giữ cuộn liên tục.
      - Nút Tím (Trigger): Đóng mở dock; khi đóng tự gom gọn thành Icon La Bàn Tròn Màu Tím (fa-compass).
   b. Hẹn giờ tự động ẩn (Idle Auto-hide Timer):
      - Dropdown chọn 30s / 60s (mặc định) / 120s / 5 phút / Không ẩn.
      - Tự động thu gọn về icon la bàn khi không tương tác. Tự reset khi rê chuột hoặc click. Lưu vào localStorage.
   c. Khung Tệp & Đường Dẫn Kỹ Thuật (MVC & Path Info):
      - 3 Thẻ chỉ số: CHUYÊN MỤC | TỆP NGUỒN MD | ROUTER/URL kèm nút Copy.
      - Đường dẫn tệp có nút Copy và nút Mở trực tiếp file.
      - Nút bật/tắt hiển thị Khung Tệp trên toolbar.
   d. Chuẩn hóa màu sắc Light / Dark Mode:
      - Nền thẻ, chữ, viền rõ nét, tương phản cao, không bị chìm chữ trong cả 2 chế độ.
   e. Trình hiển thị Markdown:
      - Tương thích thư viện marked.js v12+ (xử lý token dạng object { text, lang }), kết hợp highlight.js tô màu code và nút Copy mã nguồn.

Hãy tiến hành thực hiện toàn diện theo đúng cấu trúc và báo cáo kết quả chi tiết kèm đường dẫn clickable links.
```

---

## 2. MỤC TIÊU & TIÊU CHUẨN TRỌNG TÂM HỆ THỐNG

Một hệ thống Knowledge & Updatedone Hub chuẩn đạt chuẩn phải đáp ứng trọn vẹn 5 nguyên tắc kỹ thuật sau:
1. **Zero-Reload SPA (Trải nghiệm ứng dụng Desktop mượt mà):**
   - Không chuyển hướng trang (no page reload).
   - Sử dụng Hash Routing (`#KB-001`, `#KB-002`,...) giúp lưu lại trạng thái khi refresh và hỗ trợ Back/Forward trên trình duyệt.
   - Tìm kiếm thời gian thực (Full-Text Search) với phím tắt nhanh `/`.
2. **Hybrid Offline-First (Không lỗi CORS):**
   - Hoạt động bình thường cả khi mở trực tiếp file nội bộ qua đường dẫn `file:///c:/.../index.html` (không cần NodeJS, không cần máy chủ Apache/Nginx).
   - Chạy hoàn hảo trên máy chủ web cục bộ (`http://localhost/...`) hoặc production hosting.
3. **Phân Rã Tri Thức Mô-đun Hóa (Modular Knowledge Base):**
   - Mỗi chủ đề tri thức kỹ thuật được lưu trong 1 tệp Markdown độc lập (`01_...md`, `02_...md`,...).
   - Được ánh xạ trong cơ sở dữ liệu `changelog_data.json` với đầy đủ metadata: ID, Danh mục, Biểu tượng FontAwesome, Phiên bản, Thẻ tag, Tóm tắt và Nội dung Markdown.
4. **Điều Hướng & Cuộn Tối Ưu (Next-Gen Navigation):**
   - Dock nổi đa năng có chức năng nhấn giữ (Long-Press / Hold to Scroll) và hẹn giờ tự động thu gọn về icon La Bàn (`Compass`).
5. **Tính Nhất Quán & Đồng Bộ 100%:**
   - Luôn duy trì đồng bộ 2 tệp `index.html` (Thư mục gốc và thư mục `.agents/update1/index.html`).

---

## 3. QUY TẮC QUẢN LÝ & BÓC TÁCH DỮ LIỆU TỪ `Hoi Dap.txt` (NGĂN BỞI DẤU `==`)

Khi chuyển đổi dữ liệu từ tệp hỏi đáp thô như `Hoi Dap.txt`:

### 3.1. Thuật Toán Nhận Diện Dấu Phân Cách
Sử dụng biểu thức chính quy (Regex) quét dòng phân cách:
```python
pattern = r'(?m)^\s*(?:\d+)?={2,}\s*$'
```
*Giải thích:*
- Khớp với tất cả các dòng chỉ chứa từ 2 dấu bằng trở lên (`==`, `====`, `======`).
- Khớp với cả các dòng có tiền tố số do sao chép nhầm như `2====`, `10====`.

### 3.2. Quy Tắc Làm Sạch 100% Dữ Liệu Rác
1. **Loại bỏ phân cách thừa:** Tước sạch mọi chuỗi `==`, `====`, `======` khỏi đầu và cuối văn bản sau khi cắt.
2. **Xử lý dính câu phân cách:** Kiểm tra và cắt sạch các tiêu đề bị dính ký tự bằng như `===**React**...` chuyển thành `**React**...` hoặc `# React`.
3. **Chống gộp nhầm chuyên mục (Content Overlap Protection):**
   - Kiểm tra các đoạn chuyển tiếp quan trọng. Ví dụ: khi gặp đoạn văn bản nói về *"Kiến trúc hệ thống duy nhất chạy Web + Windows + Android + iPhone..."*, phải bóc tách thành một tệp tài liệu riêng biệt (`09_unified_multiplatform_system_architecture.md`), không được để dính vào phần frontend/backend trước đó.

### 3.3. Quy Tắc Đặt Tên Tệp Markdown Con
Các tệp bóc tách được lưu vào `.agents/update1/knowledge/` với quy tắc:
`[Số_Thứ_Tự_2_Chữ_Số]_[tên_slug_tieng_anh_khong_dau].md`

*Ví dụ chuẩn từ file `Hoi Dap.txt`:*
1. `01_python_frameworks_guide.md`: Hướng dẫn toàn diện Python Frameworks.
2. `02_php_frameworks_guide.md`: Hướng dẫn tổng quan PHP Frameworks.
3. `03_nodejs_frameworks_overview.md`: Tổng quan Node.js Frameworks & Backend.
4. `04_react_ecosystem_and_ui.md`: React Library & Hệ sinh thái UI.
5. `05_windows_desktop_exe_apps.md`: Lập trình ứng dụng Windows Desktop (.EXE).
6. `06_web_app_frameworks_spa_mpa_ssr.md`: Web App Frameworks: SPA, MPA & SSR.
7. `07_cross_platform_frameworks_overview.md`: Framework đa nền tảng (Cross-Platform).
8. `08_frontend_backend_fullstack_guide.md`: Phân tách Frontend, Backend & Full-Stack.
9. `09_unified_multiplatform_system_architecture.md`: Kiến trúc hệ thống đa nền tảng hợp nhất.

---

## 4. KIẾN TRÚC THƯ MỤC TIÊU CHUẨN TOÀN DỰ ÁN

Áp dụng cho mọi dự án (`LOG`, `info`, hoặc bất kỳ dự án nào):

```text
[PROJECT_ROOT]/ (Ví dụ: C:/Intel/Laragon/www/info hoặc www/LOG)
│
├── index.html                                 # SPA chính chạy trực tiếp ngoài thư mục gốc
├── generate_knowledge_hub.py                  # Script CLI tự động hóa cho dự án
│
└── .agents/
    └── updatedone/
        ├── index.html                         # Bản sao đồng bộ 100% của SPA chính
        ├── changelog_data.json                # Cơ sở dữ liệu JSON toàn bộ tài liệu & thẻ
        ├── architecture_spec.md               # Bản vẽ kiến trúc hệ thống
        ├── Prompt_Ki_Thuat.md                 # Tệp đặc tả kỹ thuật & Prompt mẫu này
        │
        ├── knowledge/                         # Thư mục chứa các tệp Markdown tri thức cốt lõi
        │   ├── 01_python_frameworks_guide.md
        │   ├── 02_php_frameworks_guide.md
        │   ├── 03_nodejs_frameworks_overview.md
        │   ├── 04_react_ecosystem_and_ui.md
        │   ├── 05_windows_desktop_exe_apps.md
        │   ├── 06_web_app_frameworks_spa_mpa_ssr.md
        │   ├── 07_cross_platform_frameworks_overview.md
        │   ├── 08_frontend_backend_fullstack_guide.md
        │   └── 09_unified_multiplatform_system_architecture.md
        │
        ├── plans/                             # Kế hoạch phát triển, lộ trình nâng cấp
        ├── walkthroughs/                      # Hướng dẫn chi tiết từng bước & kiểm thử
        ├── features/                          # Danh sách tính năng và phân quyền
        └── fixes/                             # Nhật ký sửa lỗi và tối ưu hóa
```

---

## 5. ĐẶC TẢ CƠ SỞ DỮ LIỆU `changelog_data.json` & CƠ CHẾ HYBRID OFFLINE (KHÔNG CORS)

### 5.1. Định Dạng JSON Chuẩn
```json
{
  "version": "v2.9.2",
  "title": "AI Zalo CSKH - Technical Architecture & Knowledge Hub",
  "updated_at": "2026-09-27",
  "categories": [
    { "id": "all", "name": "Tất Cả", "icon": "fa-solid fa-border-all" },
    { "id": "backend", "name": "Backend & Core", "icon": "fa-solid fa-server" },
    { "id": "frontend", "name": "Frontend & UI", "icon": "fa-solid fa-palette" },
    { "id": "crossplatform", "name": "Đa Nền Tảng", "icon": "fa-solid fa-laptop-mobile" },
    { "id": "architecture", "name": "Kiến Trúc", "icon": "fa-solid fa-cubes" }
  ],
  "items": [
    {
      "id": "KB-001",
      "file": "knowledge/01_python_frameworks_guide.md",
      "title": "Hướng Dẫn Toàn Diện Về Python Frameworks",
      "category": "backend",
      "category_name": "Backend & Core",
      "icon": "fa-brands fa-python",
      "version": "v2.9.2",
      "summary": "Tổng quan khung làm việc Python (Django, Flask, FastAPI, Tkinter)...",
      "tags": ["Python", "Django", "FastAPI", "Backend"],
      "content": "# Nội dung Markdown đầy đủ của tệp..."
    }
  ]
}
```

### 5.2. Kỹ Thuật Hybrid Offline (Khắc Phục Lỗi CORS Trình Duyệt)
Khi người dùng kích đúp vào tệp `index.html` để mở bằng đường dẫn tệp cục bộ (`file:///C:/.../index.html`), cơ chế bảo mật của trình duyệt sẽ chặn hàm `fetch('changelog_data.json')` do vi phạm chính sách CORS (Cross-Origin Resource Sharing).

**Giải pháp kỹ thuật bắt buộc:**
Nhúng toàn bộ nội dung của `changelog_data.json` vào chính `index.html` trong thẻ script đặc biệt:
```html
<script id="embedded-dataset" type="application/json">
  { ... DỮ LIỆU JSON ĐẦY ĐỦ Ở ĐÂY ... }
</script>
```

Trong đoạn mã khởi tạo JavaScript của `index.html`:
```javascript
async function loadDataset() {
    // 1. Ưu tiên đọc dữ liệu In-Memory nhúng sẵn (Chạy hoàn hảo với file:///)
    const embeddedEl = document.getElementById('embedded-dataset');
    if (embeddedEl && embeddedEl.textContent.trim().length > 10) {
        try {
            return JSON.parse(embeddedEl.textContent);
        } catch (e) {
            console.warn("Lỗi phân tích cú pháp dataset nhúng, thử tải qua fetch...", e);
        }
    }
    // 2. Dự phòng: Tải qua fetch nếu đang chạy trên Web Server (http://, https://)
    try {
        const res = await fetch('.agents/update1/changelog_data.json');
        if (res.ok) return await res.json();
    } catch (err) {
        console.error("Không thể tải dataset:", err);
    }
    return null;
}
```

---

### 5.3. ⚠️ Lưu Ý Trọng Yếu: Quy Chuẩn Escape Chuỗi JSON Nhúng (Chống Lỗi Data Syntax Crash - Bad Control Character)

> **Cảnh báo lỗi nghiêm trọng:** Nếu đoạn văn bản Markdown thô chứa các ký tự xuống dòng thực tế (literal newlines `\n`) mà được dán trực tiếp vào thuộc tính `"content": "..."` trong chuỗi JSON, trình duyệt khi chạy lệnh `JSON.parse()` lập tức ném ra ngoại lệ:
> ```text
> Uncaught SyntaxError: Bad control character in string literal in JSON at position ...
> ```
> Khi gặp lỗi này, toàn bộ tiến trình nạp JavaScript trong `loadDataset()` bị dừng ngay lập tức, dẫn đến hiện tượng: **Trang `index.html` hiển thị trắng rỗng (không hiện phân loại chuyên mục, danh sách bên trái trống, bài viết bên phải không hiển thị)**.

**Quy tắc kỹ thuật bắt buộc:**
1. **Tuyệt đối không ghép chuỗi thủ công:** Không bao giờ tự ghép nối thủ công chuỗi Markdown vào thẻ `<script id="embedded-dataset">`.
2. **Luôn sử dụng bộ tuần tự hóa chuẩn (Serializer):**
   - Trong Python: `json.dumps(dataset, ensure_ascii=False)`
   - Trong Node.js: `JSON.stringify(dataset)`
   Các bộ mã hóa này sẽ tự động escape toàn bộ ký tự xuống dòng thành `\n`, ký tự nháy kép thành `\"`, giúp `JSON.parse()` chạy trơn tru với độ trễ 0ms.
3. **Kiểm tra cú pháp trước khi xuất bản:** Chạy kiểm tra cú pháp JSON bằng lệnh `JSON.parse()` qua headless browser hoặc console trước khi bàn giao.

---

## 6. ĐẶC TẢ CHI TIẾT GIAO DIỆN & TÍNH NĂNG SPA (index.html)

### 6.1. Cụm Nút Điều Hướng Nổi (Floating Nav Dock 5 Nút)
Nằm cố định ở góc dưới cùng bên phải màn hình (`bottom: 24px; right: 24px; z-index: 50`).

```
┌───────────────────────────────┐
│  [📁] Nút Cam: Master TOC    │
│  [⏫] Nút Cuộn Lên            │
│  [↕️] Nút Cuộn Giữa          │
│  [⏬] Nút Cuộn Xuống          │
│  [🟣] Nút Tím: Trigger/Compass│
└───────────────────────────────┘
```

1. **Nút Cam Trên Cùng (Orange Gradient - `fa-folder-open`):**
   - Click: Mở nhanh cửa sổ Modal **Mục Lục Toàn Cảnh** (`Master TOC`) hiển thị toàn bộ tài liệu trong hệ thống.
2. **Nút Cuộn Lên (`fa-angles-up`):**
   - **Click 1 chạm:** Cuộn mượt lên vị trí đầu tiên của nội dung bài viết (`top: 0`).
   - **Nhấn giữ (Hold to scroll / Long-press):** Khi nhấn chuột giữ nguyên (`mousedown`) hoặc chạm giữ ngón tay trên màn hình cảm ứng (`touchstart`), kích hoạt vòng lặp cuộn liên tục siêu tốc lên trên (`step = -28px`). Thả tay (`mouseup`, `mouseleave`, `touchend`) dừng lại ngay lập tức.
3. **Nút Cuộn Giữa (`fa-arrows-up-down`):**
   - **Click 1 chạm:** Cuộn nhanh đến chính giữa nội dung tài liệu (`top: scrollHeight * 0.5`).
4. **Nút Cuộn Xuống (`fa-angles-down`):**
   - **Click 1 chạm:** Cuộn mượt xuống cuối bài viết & thanh chuyển bài (`top: scrollHeight`).
   - **Nhấn giữ (Hold to scroll / Long-press):** Tương tự nút cuộn lên, nhấn giữ kích hoạt cuộn liên tục siêu mượt xuống dưới (`step = +28px`).
5. **Nút Tím Đóng/Mở (Compass / Xmark Trigger - `fa-compass` / `fa-xmark`):**
   - Khi mở: Menu xếp dọc hiện đầy đủ các nút, nút kích hoạt chuyển thành dấu `X` (`fa-xmark`).
   - Khi thu nhỏ: Toàn bộ cụm nút thu gọn lại thành **Icon La Bàn Tròn Màu Tím** (`fa-compass`) nổi nhẹ nhàng ở góc màn hình.

---

### 6.2. Bộ Hẹn Giờ Tự Động Ẩn Dock (Auto-Hide Idle Timer)
- Thêm dropdown cài đặt thời gian ẩn ngay trên thanh công cụ Header:
  - `30s` (30 giây)
  - `60s` (60 giây - Mặc định)
  - `120s` (2 phút)
  - `5 phút` (300 giây)
  - `Không ẩn` (Tắt tự động ẩn)
- **Cơ chế hoạt động:**
  - Nếu người dùng không tương tác chuột với thanh Dock trong khoảng thời gian đã chọn, dock sẽ tự động thu nhỏ thành biểu tượng **La Bàn Tím**.
  - Khi người dùng rê chuột lại vào dock hoặc bấm vào la bàn, dock mở ra và bộ đếm thời gian được reset.
  - Giá trị cấu hình được lưu vào `localStorage.getItem('hub_autohide_timer')` để duy trì qua các phiên làm việc.

---

### 6.3. Bảng Khung Tệp & Đường Dẫn Kỹ Thuật (MVC & Path Info - Relative Path)
Nằm ở đầu mỗi bài viết chi tiết, dưới tiêu đề chính:
- **Tiêu đề khung:** `Kiến Trúc & Tệp Nguồn Áp Dụng (MVC)` kèm nút `Chép Đường Dẫn`.
- **3 Thẻ Thông Số (High-Contrast Metric Cards):**
  1. **CHUYÊN MỤC (Màu Tím):** Tên phân loại (ví dụ: `Backend & Core`) kèm nút Copy.
  2. **TỆP NGUỒN MD (Màu Cyan):** Tên file markdown (ví dụ: `01_python_frameworks_guide.md`) kèm nút Copy.
  3. **ROUTER / HASH (Màu Vàng Hổ Phách):** Hash router (ví dụ: `#KB-001`) kèm nút Copy liên kết URL trực tiếp.
- **Hàng Đường Dẫn Tệp Nguồn (Đường Dẫn Tương Đối):**
  - Hiển thị đường dẫn tương đối động (`${relPath}`).
  - Nút **Copy** đường dẫn tương đối một chạm.
  - Nút **Mở** (`target="_blank"`) để xem trực tiếp tệp nguồn.
- **Nút Bật/Tắt (Toggle):** Nút `Khung Tệp (Bật/Tắt)` trên toolbar phía trên cho phép người dùng ẩn/hiện khung này tùy ý.

> **⚠️ Lưu Ý Trọng Yếu: Dùng Đường Dẫn Tương Đối Cho Nút "Mở" File .MD (Chống Lỗi Khi Đổi Thư Mục):**  
> - **Tuyệt đối không hardcode đường dẫn tuyệt đối** như `file:///C:/Intel/Laragon/www/LOG/...`. Nếu thư mục dự án bị đổi tên (ví dụ từ `LOG` sang `002_Log`, `003_Project`), chuyển sang máy tính khác hoặc ổ đĩa khác (`D:\`, `E:\`), toàn bộ liên kết mở file sẽ bị chết (`File Not Found`).  
> - **Quy tắc bắt buộc:** Sử dụng hàm helper động:
>   ```javascript
>   function getRelativeFilePath(itemFile) {
>       const pathname = window.location.pathname.replace(/\\/g, '/');
>       const isInsideAgents = pathname.includes('/.agents/update1');
>       return isInsideAgents ? itemFile : `.agents/update1/${itemFile}`;
>   }
>   ```
>   - Khi mở từ `.agents/update1/index.html`: đường dẫn là `knowledge/02_php_frameworks_guide.md`.
>   - Khi mở từ gốc dự án `[PROJECT_ROOT]/index.html`: đường dẫn là `.agents/update1/knowledge/02_php_frameworks_guide.md`.
>   - Thẻ liên kết: `<a href="${relPath}" target="_blank">` để trình duyệt tự động resolve theo vị trí hiện hành.

---

### 6.4. Chuẩn Hóa Màu Sắc Giao Diện Sáng & Tối (Light / Dark Mode Contrast)
- **Chế độ Sáng (Light Mode):**
  - Khung chứa chính: Nền sáng dịu `bg-slate-100/90`, viền `border-slate-200`, chữ `text-slate-800`.
  - 3 Thẻ thông số: Nền trắng tinh `bg-white`, viền `border-slate-200`, nhãn màu đậm độ tương phản cao (`text-purple-700`, `text-cyan-700`, `text-amber-700`).
  - Thanh Dock Nổi: Chuyển sang nền kính mờ trắng `bg-white/95`, viền `border-slate-200`, icon xám đậm rõ nét.
- **Chế độ Tối (Dark Mode):**
  - Khung chứa chính: Nền tối `dark:bg-slate-900/90`, viền `dark:border-slate-800`, chữ sáng `dark:text-slate-200`.
  - 3 Thẻ thông số: Nền tối `dark:bg-slate-900`, viền `dark:border-slate-800`, chữ sáng rõ ràng.
  - Thanh Dock Nổi: Nền tối kính mờ `dark:bg-slate-900/95`, viền `dark:border-slate-700`.

---

### 6.5. Trình Phân Tích Cú Pháp Markdown & Khắc Phục Lỗi Marked.js v12+
- **Vấn đề kỹ thuật:** Các phiên bản thư viện `marked.js` từ v12 trở lên truyền vào hàm `renderer.code(tokenOrCode, language)` một đối tượng token `{ text, lang, raw }` thay vì chuỗi text thuần túy. Nếu render trực tiếp sẽ gây lỗi xuất chuỗi `[object Object]`.
- **Đoạn mã xử lý chuẩn bắt buộc:**
```javascript
const renderer = new marked.Renderer();

renderer.code = function(tokenOrCode, language) {
    let codeText = '';
    let lang = '';

    if (typeof tokenOrCode === 'object' && tokenOrCode !== null) {
        codeText = tokenOrCode.text || tokenOrCode.raw || '';
        lang = tokenOrCode.lang || language || 'plaintext';
    } else if (typeof tokenOrCode === 'string') {
        codeText = tokenOrCode;
        lang = language || 'plaintext';
    }

    let highlighted = '';
    if (lang && hljs.getLanguage(lang)) {
        try {
            highlighted = hljs.highlight(codeText, { language: lang }).value;
        } catch (err) {
            highlighted = escapeHtml(codeText);
        }
    } else {
        highlighted = escapeHtml(codeText);
    }

    return `
    <div class="relative group my-4 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-900 shadow-md">
        <div class="flex items-center justify-between px-4 py-2 bg-slate-950/80 border-b border-slate-800 text-xs text-slate-400">
            <span class="font-mono font-semibold text-purple-400 uppercase tracking-wider">${lang || 'CODE'}</span>
            <button onclick="copyCodeBlock(this)" class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-purple-600 text-slate-300 hover:text-white transition-all text-xs">
                <i class="fa-regular fa-copy"></i>
                <span>Copy</span>
            </button>
        </div>
        <pre class="p-4 overflow-x-auto text-sm font-mono text-slate-100 leading-relaxed"><code>${highlighted}</code></pre>
    </div>`;
};
```

---

### 6.6. Cơ Chế Cuộn Đa Mục Tiêu & Nhấn Giữ (Hold to Scroll / Long-Press)
- **Container cuộn chính:** Trong cấu trúc layout SPA, phần hiển thị nội dung là vùng `#doc-content-container` có `overflow-y: auto`.
- **Cơ chế tác động đồng thời:** Các thao tác cuộn phải nhắm vào cả 4 mục tiêu để tránh lỗi layout không cuộn:
```javascript
function scrollAllTargets(options) {
    const container = document.getElementById('doc-content-container');
    if (container) container.scrollTo(options);
    window.scrollTo(options);
    document.documentElement.scrollTo(options);
    document.body.scrollTo(options);
}
```
- **Xử lý nhấn giữ (Hold-to-scroll):**
```javascript
let scrollInterval = null;

function startContinuousScroll(step) {
    stopContinuousScroll();
    scrollInterval = setInterval(() => {
        const container = document.getElementById('doc-content-container') || window;
        if (container.scrollBy) {
            container.scrollBy({ top: step, behavior: 'instant' });
        }
    }, 16); // 60fps
}

function stopContinuousScroll() {
    if (scrollInterval) {
        clearInterval(scrollInterval);
        scrollInterval = null;
    }
}
```

---

### 6.7. Quy Tắc Đồng Bộ 2 File index.html & Định Tuyến Web Server (Tránh Lỗi /index.html Không Hiển Thị)
Trong bất kỳ thư mục dự án nào:
1. **Chỉ duy trì đúng 2 file `index.html`:**
   - File 1: `[PROJECT_ROOT]/index.html` (Phục vụ truy cập qua máy chủ web Laragon/Apache: `http://localhost/tên_dự_án/index.html` hoặc `http://tên_dự_án.test/index.html`).
   - File 2: `[PROJECT_ROOT]/.agents/update1/index.html` (Phục vụ mở trực tiếp offline qua giao thức `file:///`).
   - Cả 2 file có nội dung JavaScript, CSS, HTML và embedded dataset đồng nhất 100%.
2. **Quy tắc dọn dẹp:**
   - Xóa bỏ triệt để các file thử nghiệm cũ như `index1.html`, `index2.html`, `test.html` để tránh phân tán dữ liệu và nhầm lẫn.
3. **⚠️ Lưu Ý Trọng Yếu: Nguyên Nhân Gốc Rễ Khi `/index.html` Không Hiển Thị:**
   - Khi chạy qua máy chủ web Laragon/Apache, web server luôn tìm kiếm tệp mặc định tại thư mục gốc `[PROJECT_ROOT]/index.html`.
   - Nếu chỉ sinh file ở `.agents/update1/index.html` mà quên copy ra thư mục gốc, người dùng truy cập `/index.html` sẽ bị lỗi `404 Not Found` hoặc trang trống.
   - BẮT BUỘC: Mỗi lần xuất bản hoặc cập nhật giao diện, phải copy bản sao hoàn chỉnh sang cả 2 vị trí trên.

---

## 7. QUY TRÌNH TRIỂN KHAI TỪNG BƯỚC CHO DỰ ÁN MỚI (STEP-BY-STEP EXECUTION)

Khi nhận lệnh tạo Knowledge Hub cho bất kỳ thư mục dự án nào (ví dụ: `C:\Intel\Laragon\www\info\.agents\updatedone`):

### Bước 1: Khởi Tạo Cây Thư Mục Chuẩn
Tạo cấu trúc thư mục hoàn chỉnh:
- `[PROJECT_ROOT]/.agents/update1/knowledge/`
- `[PROJECT_ROOT]/.agents/update1/plans/`
- `[PROJECT_ROOT]/.agents/update1/walkthroughs/`
- `[PROJECT_ROOT]/.agents/update1/features/`
- `[PROJECT_ROOT]/.agents/update1/fixes/`

### Bước 2: Bóc Tách Nội Dung & Làm Sạch Markdown
- Đọc tệp dữ liệu nguồn (ví dụ `Hoi Dap.txt`).
- Tách từng mục theo dấu `==` bằng Regex.
- Xóa sạch dấu `==` thừa, loại bỏ các ký tự rác.
- Ghi từng chủ đề thành các file `.md` độc lập trong thư mục `knowledge/`.

### Bước 3: Biên Tập & Xuất `changelog_data.json`
- Lập chỉ mục toàn bộ các file `.md` đã tạo.
- Gán ID chuẩn (`KB-001`, `KB-002`,...).
- Tự động phân loại category (`backend`, `frontend`, `crossplatform`, `architecture`).
- Trích xuất tiêu đề, tóm tắt, biểu tượng FontAwesome tương ứng và mảng thẻ tag.
- Ghi ra tệp `[PROJECT_ROOT]/.agents/update1/changelog_data.json`.

### Bước 4: Tạo Và Đồng Bộ 2 File `index.html`
- Lấy template SPA đạt chuẩn (chứa Floating Dock 5 nút, Hẹn giờ tự động ẩn, Khung MVC, bộ parser Marked.js v12+, chế độ Dark/Light tương phản cao).
- Đọc nội dung JSON từ `changelog_data.json` và chèn trực tiếp vào thẻ `<script id="embedded-dataset" type="application/json">` trong file `index.html`.
- Lưu 1 bản vào `[PROJECT_ROOT]/index.html`.
- Lưu 1 bản vào `[PROJECT_ROOT]/.agents/update1/index.html`.

### Bước 5: Dọn Dẹp & Kiểm Tra
- Quét và xóa toàn bộ file rác (`index1.html`, `index2.html`).
- Kiểm tra bằng checklist nghiệm thu.

---

## 8. BỘ KIỂM TRA CHẤT LƯỢNG NGHIỆM THU (QUALITY ASSURANCE CHECKLIST)

Trước khi bàn giao kết quả cho người dùng, người thực hiện hoặc AI Agent phải kiểm tra và xác nhận đạt 100% các tiêu chí sau:

- [ ] **1. Độ Sạch Của Nội Dung:** Không còn bất kỳ ký tự phân cách thô dạng `==`, `====`, `======` nào trong tất cả các tệp `.md` và trên giao diện.
- [ ] **2. Phân Tách Độc Lập:** Không bị nối dính nội dung của chủ đề này vào chủ đề khác (ví dụ: mục kiến trúc đa nền tảng hợp nhất đã được tách riêng).
- [ ] **3. Chạy Mượt Không Lỗi CORS (Hybrid Offline):** Mở trực tiếp bằng `file:///.../index.html` trên trình duyệt hiển thị đầy đủ danh sách bài viết, không báo lỗi đỏ `CORS` trên Console F12.
- [ ] **4. Cụm Dock Nổi 5 Nút:**
  - Nút Cam: Mở đúng Modal Mục Lục Toàn Cảnh (Master TOC).
  - Nút Cuộn Lên: Click cuộn mượt về đỉnh; Nhấn giữ cuộn liên tục.
  - Nút Cuộn Giữa: Cuộn đến chính giữa nội dung.
  - Nút Cuộn Xuống: Click cuộn mượt về đáy; Nhấn giữ cuộn liên tục.
  - Nút Tím: Thu gọn về icon la bàn tím (`fa-compass`) và mở rộng lại thành dấu `X`.
- [ ] **5. Hẹn Giờ Tự Động Ẩn:** Tự động thu gọn dock về la bàn khi không tương tác sau khoảng thời gian đã chọn (mặc định 60s), lưu cấu hình vào `localStorage`.
- [ ] **6. Khung Thông Số Kỹ Thuật (MVC):** Hiển thị rõ ràng 3 thẻ CHUYÊN MỤC, TỆP NGUỒN MD, ROUTER/URL. Nút Copy và nút Mở file hoạt động chính xác.
- [ ] **7. Độ Tương Phản Dark / Light Mode:** Nền thẻ sáng rõ ràng, chữ không bị chìm hay mờ trong cả 2 chế độ.
- [ ] **8. Cú Pháp Code:** Các khối mã nguồn (Python, PHP, React, Bash, Flowcharts) hiển thị màu sắc chuẩn xác, không bị lỗi `[object Object]`, nút Copy code đổi icon check xanh khi bấm.
- [ ] **9. Số Lượng File Chuẩn:** Chỉ duy trì đúng 2 file `index.html` đồng bộ (thư mục gốc và `.agents/update1/index.html`), không còn các file rác cũ.
- [ ] **10. Escape Chuỗi JSON Nhúng Chuẩn (Chống Crash Render):** Khối `<script id="embedded-dataset">` không chứa ký tự xuống dòng thô không hợp lệ, không gây lỗi `Bad control character in string literal` trên Console F12, toàn bộ 14 mục và các dải danh mục hiển thị đầy đủ.
- [ ] **11. Đường Dẫn Tương Đối & Khả Năng Di Động:** Nút "Mở" file .md và nút sao chép đường dẫn dùng relative path động (`getRelativeFilePath`), không hardcode bất kỳ thư mục tuyệt đối nào, đảm bảo đổi tên thư mục hoặc di chuyển dự án vẫn hoạt động 100%.
- [ ] **12. Đủ 2 File index.html Cho Mọi Môi Trường Chạy:** Cả môi trường máy chủ web (`http://localhost/.../index.html` hoặc Laragon) lẫn mở trực tiếp offline (`file:///.../index.html`) đều hiển thị hoàn hảo.



---

### 9 🌟 Tóm Tắt Nội Dung Tệp `Prompt_Ki_Thuat.md`

Tệp đặc tả được thiết kế theo mã quy chuẩn **`SPEC-PROMPT-HUB-V2.9.2`**, cho phép bạn hoặc bất kỳ AI Agent nào tái tạo lại chính xác hệ thống tài liệu Zero-Reload SPA cho **bất kỳ tệp văn bản thô nào, bất kỳ thư mục nào và bất kỳ dự án nào** (chẳng hạn như `C:\Intel\Laragon\www\info\.agents\updatedone`):

1. **Khung Prompt Mẫu Sẵn Sàng Giao Việc Cho AI Agent (Copy-Paste Ready):**
   - Đóng gói đầy đủ yêu cầu từ tiếp nhận nguồn (như `Hoi Dap.txt`), phân tách dữ liệu, biên dịch JSON đến khởi tạo 2 file `index.html`.
   - Có sẵn các biến số tùy biến: `[ĐƯỜNG_DẪN_TỆP_NGUỒN]`, `[ĐƯỜNG_DẪN_PROJECT_ĐÍCH]`, `[TÊN_TIÊU_ĐỀ_HUB]`.

2. **Quy Tắc Quản Lý & Bóc Tách Dữ Liệu Từ `Hoi Dap.txt`:**
   - Thuật toán Regex nhận diện dòng phân cách: `(?m)^\s*(?:\d+)?={2,}\s*$`.
   - Cơ chế loại bỏ 100% rác phân vùng thô (`==`, `====`, `======`, `===**React**...`).
   - Cơ chế phòng chống dính chéo nội dung (Content Overlap Protection) giữa các chuyên mục (đã tách riêng phần kiến trúc đa nền tảng hợp nhất Web + Windows + Mobile).
   - Đánh số và đặt tên slug chuẩn cho các file `.md` con trong thư mục `knowledge/`.

3. **Kiến Trúc Thư Mục Tiêu Chuẩn Cho Mọi Dự Án:**
   - Cấu trúc chuẩn hóa: `[PROJECT_ROOT]/index.html` và `[PROJECT_ROOT]/.agents/update1/` gồm các thư mục `knowledge/`, `plans/`, `walkthroughs/`, `features/`, `fixes/` cùng tệp `changelog_data.json`.

4. **Cơ Chế Hybrid Offline Chống Lỗi CORS:**
   - Nhúng dữ liệu In-Memory JSON vào `<script id="embedded-dataset" type="application/json">` trong `index.html`.
   - Giúp SPA hoạt động mượt mà cả khi click đúp mở trực tiếp qua `file:///` lẫn máy chủ web `localhost`.

5. **Đặc Tả Chi Tiết Giao Diện & Tính Năng SPA:**
   - **Cụm Nút Điều Hướng Nổi (Floating Nav Dock 5 Nút):** Nút Cam (Master TOC), Cuộn Lên (`fa-angles-up`), Cuộn Giữa (`fa-arrows-up-down`), Cuộn Xuống (`fa-angles-down`), Nút Tím (Trigger thu gọn về Icon La Bàn `fa-compass`).
   - **Tính năng Nhấn Giữ (Hold to Scroll / Long-press):** Giữ chuột/chạm tay để cuộn liên tục siêu tốc ở cả nút Cuộn Lên và Cuộn Xuống.
   - **Hẹn giờ tự động ẩn:** Dropdown `30s / 60s / 120s / 5 phút / Không ẩn`, tự động reset khi tương tác và lưu vào `localStorage`.
   - **Khung Thông Số Kỹ Thuật (MVC):** 3 thẻ CHUYÊN MỤC, TỆP NGUỒN MD, ROUTER/URL; nút Copy và Mở file trực tiếp; nút bật/tắt trên toolbar.
   - **Chuẩn hóa màu sắc Light / Dark Mode:** Tương phản cao, chữ không bị chìm màu.
   - **Khắc phục lỗi Marked.js v12+:** Bóc tách object token `{ text, lang }` tránh lỗi `[object Object]`, tích hợp highlight.js và nút Copy code.

6. **Quy Trình Triển Khai Từng Bước & Checklist Nghiệm Thu 9 Tiêu Chuẩn Vàng.**