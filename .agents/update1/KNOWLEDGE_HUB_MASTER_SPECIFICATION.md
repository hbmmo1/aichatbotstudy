# ĐẶC TẢ KỸ THUẬT TOÀN DIỆN: HỆ THỐNG KNOWLEDGE & UPDATEDONE HUB (SPA)
> **Mã quy chuẩn:** `SPEC-LOG-HUB-V2.9.2`  
> **Phiên bản:** `v2.9.2`  
> **Phạm vi áp dụng:** Mọi thư mục dự án, tệp văn bản thô (.txt ngăn cách bằng `==`) hoặc thư mục tài liệu (.md) cần chuyển đổi thành Dashboard tra cứu chuyên nghiệp không cần máy chủ (Zero-reload Offline SPA).

---

## 1. TỔNG QUAN & MỤC TIÊU HỆ THỐNG

Hệ thống **Knowledge & Updatedone Hub** là một giải pháp tài liệu hóa kỹ thuật số độc lập:
1. **Không cần cài đặt backend phức tạp:** Toàn bộ dữ liệu được quản lý qua JSON và tệp Markdown thuần, hiển thị qua 1 file `index.html` duy nhất.
2. **Khả năng chạy đa môi trường (Hybrid Offline / Online):** Chạy mượt mà trên máy chủ web cục bộ (`http://localhost/...`) lẫn mở trực tiếp từ tệp tin (`file:///...`) mà không bị lỗi chính sách bảo mật CORS.
3. **Trải nghiệm phần mềm Desktop (Zero-Reload SPA):** Chuyển đổi tài liệu tức thì, lưu lịch sử hash router, phân loại đa tầng, tìm kiếm full-text bằng phím tắt `/`.
4. **Hệ thống điều hướng nổi siêu tốc (Quick Nav Dock):** 5 nút chức năng, hỗ trợ nhảy nhanh Top/Middle/Bottom và **nhấn giữ (Hold-to-scroll) để cuộn trang liên tục**, tự động thu nhỏ thành biểu tượng la bàn (`Compass`) theo thời gian định sẵn.

---

## 2. KIẾN TRÚC THƯ MỤC CHUẨN MỰC

Bất kỳ dự án nào khi áp dụng tiêu chuẩn này đều tuân thủ cấu trúc sau:

```text
[PROJECT_ROOT]/
│
├── index.html                              # File giao diện SPA chính chạy ngoài thư mục gốc
├── generate_knowledge_hub.py               # Công cụ CLI tự động hóa cho mọi thư mục/tệp
│
└── .agents/
    └── updatedone/
        ├── index.html                      # File giao diện SPA phụ đồng bộ bản sao
        ├── changelog_data.json             # Cơ sở dữ liệu JSON danh mục, tài liệu, thẻ tag
        ├── architecture_spec.md            # Đặc tả kiến trúc kỹ thuật của dự án
        │
        ├── knowledge/                      # Thư mục chứa các chủ đề kỹ thuật cốt lõi
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
        ├── plans/                          # Kế hoạch và lộ trình phát triển
        ├── walkthroughs/                   # Hướng dẫn từng bước và quy trình vận hành
        ├── features/                       # Đặc tả tính năng và phân quyền
        └── fixes/                          # Báo cáo xử lý lỗi và tối ưu hiệu năng
```

---

## 3. QUY TRÌNH XỬ LÝ & BÓC TÁCH NỘI DUNG ĐẦU VÀO

Hệ thống hỗ trợ 2 hình thức đầu vào:

### A. Đầu vào là 1 Tệp Văn Bản Thô (VD: `Hoi Dap.txt`)
- **Quy tắc phân vùng:** Sử dụng biểu thức chính quy (Regex) bắt tất cả các dòng chỉ chứa dấu bằng:
  ```python
  pattern = r'(?m)^\s*(?:\d+)?={2,}\s*$'
  ```
- **Lọc sạch rác phân vùng:**
  - Tự động loại bỏ các ký tự thừa như `2====`, `=====`, `==========`, `===**React**...`.
  - Tách triệt để các phần bị dính nội dung của chủ đề khác (ví dụ: phần kiến trúc đa nền tảng bị nối vào cuối phần full-stack).
- **Trích xuất thuộc tính:**
  - **Tiêu đề:** Lấy dòng `# Tiêu đề` đầu tiên hoặc dòng in đậm `**...**`.
  - **Tóm tắt (Summary):** Tự động bóc tách 160 ký tự đầu tiên của đoạn văn bản có nghĩa.
  - **Phân loại (Category):** Phân loại thông minh dựa trên từ khóa (Python, PHP, Node.js, React, Windows, Cross-Platform, Architecture).

### B. Đầu vào là 1 Thư Mục Chứa Các File `.md` / `.txt`
- Quét toàn bộ cây thư mục, đọc các tệp Markdown hiện có.
- Chuẩn hóa tên tệp theo số thứ tự: `01_ten_tai_lieu.md`, `02_ten_tai_lieu.md`.
- Trích xuất tiêu đề từ Frontmatter YAML hoặc dòng đầu tiên.

---

## 4. ĐẶC TẢ CƠ SỞ DỮ LIỆU `changelog_data.json`

Cơ sở dữ liệu được cấu trúc dưới định dạng JSON tiêu chuẩn:

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
      "content": "# Nội dung Markdown đầy đủ..."
    }
  ]
}
```

> **Cơ chế Khắc Phục CORS (In-Memory Embedding):**  
> Dữ liệu JSON trên được nhúng trực tiếp vào tệp `index.html` trong thẻ:
> ```html
> <script id="embedded-dataset" type="application/json">
>   { ... JSON DỮ LIỆU ĐƯỢC NHÚNG TRỰC TIẾP ... }
> </script>
> ```
> Khi mở file bằng `file:///`, JavaScript phân tích cú pháp từ thẻ này thay vì gọi `fetch()`, đảm bảo **không bao giờ bị lỗi CORS hay phụ thuộc máy chủ**.

---

## 5. ĐẶC TẢ GIAO DIỆN & TÍNH NĂNG SPA

### 5.1. Hệ Thống Thanh Dock Nổi Thông Minh (Quick Navigation Dock)
- **Vị trí cố định:** Góc dưới cùng bên phải (`bottom: 24px; right: 24px; z-index: 50`).
- **5 Nút Chức Năng:**
  1. **Nút Toàn Cảnh (Màu Cam Gradient):** Mở cửa sổ Modal Mục Lục Toàn Cảnh toàn bộ dự án (`openMasterTocModal()`).
  2. **Nút Cuộn Lên Đầu Trang (`fa-angles-up`):**
     - *Nhấp chuột:* Cuộn mượt về đầu trang (`top: 0`).
     - *Nhấn giữ chuột / chạm giữ (`mousedown` / `touchstart`):* Kích hoạt vòng lặp cuộn trang liên tục siêu tốc (`step = -28px`).
  3. **Nút Cuộn Giữa Trang (`fa-arrows-up-down`):** Cuộn mượt đến chính giữa nội dung tài liệu (`50%`).
  4. **Nút Cuộn Xuống Cuối Trang (`fa-angles-down`):**
     - *Nhấp chuột:* Cuộn mượt xuống cuối trang (`scrollHeight`).
     - *Nhấn giữ chuột / chạm giữ:* Kích hoạt vòng lặp cuộn trang liên tục xuống dưới (`step = +28px`).
  5. **Nút La Bàn / Đóng Mở (Tím Gradient):**
     - Thu gọn menu dọc thành 1 nút la bàn nhỏ duy nhất hoặc mở rộng trở lại.
     - Khi mở: Hiện biểu tượng dấu `X`.
     - Khi đóng: Hiện biểu tượng `Compass`.

- **Cơ chế tự động ẩn (Idle Auto-Hide Timer):**
  - Dropdown trên thanh tiêu đề cho phép chọn: `30s`, `60s`, `120s`, `5 phút`, `Không ẩn`.
  - Khi người dùng không di chuột qua khu vực thanh dock trong khoảng thời gian đã chọn, dock sẽ tự động thu gọn về biểu tượng la bàn.
  - Thiết lập được lưu vĩnh viễn vào `localStorage.getItem('hub_autohide')`.

### 5.2. Khung Thông Số Kỹ Thuật (Kiến Trúc & Tệp Nguồn Áp Dụng - MVC)
Nằm ngay dưới thanh tiêu đề tài liệu, cung cấp thông tin kỹ thuật rõ ràng:
- **Tiêu đề thanh:** `Kiến Trúc & Tệp Nguồn Áp Dụng (MVC)` kèm nút `Chép Toàn Bộ`.
- **3 Thẻ Chỉ Số Đo Lường (High-Contrast Metrics Cards):**
  1. **Chuyên Mục (Màu Tím):** Tên phân loại + nút sao chép nhanh.
  2. **Tệp Nguồn MD (Màu Cyan):** Đường dẫn tương đối tệp Markdown + nút sao chép.
  3. **Router / URL (Màu Vàng Hổ Phách):** Mã Hash Router (`#KB-001`) + nút sao chép liên kết trực tiếp.
- **Thanh Tác Vụ Mở File:**
  - Hiển thị đường dẫn tương đối `.agents/update1/...`.
  - Nút **Copy** đường dẫn vào bộ nhớ tạm.
  - Nút **Mở** (`target="_blank"`) để xem trực tiếp tệp nguồn trên trình duyệt.
- **Nút bật/tắt (Toggle):** `Khung Tệp (Bật)` / `Khung Tệp (Tắt)` trên toolbar giúp người dùng chủ động ẩn để tiết kiệm diện tích đọc.

### 5.3. Trình Hiển Thị Nội Dung & Bộ Phân Tích Cú Pháp (Markdown Parser)
- Sử dụng **Marked.js v12+** với cơ chế giải nén Token Object an toàn:
  ```javascript
  renderer.code = function(tokenOrCode, language) {
      let codeText = (typeof tokenOrCode === 'object' && tokenOrCode !== null)
          ? (tokenOrCode.text || tokenOrCode.raw || '')
          : (typeof tokenOrCode === 'string' ? tokenOrCode : '');
      let lang = (typeof tokenOrCode === 'object' && tokenOrCode.lang) ? tokenOrCode.lang : (language || 'plaintext');
      // Highlight.js rendering...
  };
  ```
- **Hộp Mã Nguồn (Code Block Container):**
  - Tự động tô màu cú pháp (Syntax Highlighting) qua **Highlight.js**.
  - Tích hợp sẵn nút **Copy** ở góc trên bên phải mỗi khối mã nguồn, tự động đổi icon check xanh khi sao chép thành công.
- **Chế độ Xem Mã Nguồn Thô (View .MD Raw):**
  - Cho phép người dùng chuyển đổi 1 chạm giữa Giao diện Rendered và Mã nguồn gốc Markdown.

### 5.4. Chế Độ Sidebar Đa Năng
Hỗ trợ 3 chế độ chuyển đổi linh hoạt:
1. **Cột Đầy Đủ (Expanded - 340px / 380px):** Hiện danh sách card tài liệu, thẻ tag, tóm tắt và ô tìm kiếm.
2. **Chỉ Hiện Icon (Rail - 56px):** Thu gọn thanh sidebar chỉ còn dãy icon đại diện cho từng tài liệu để tối đa hóa không gian đọc.
3. **Ẩn Hoàn Toàn (Hidden):** Ẩn thanh sidebar để tập trung 100% màn hình cho nội dung.

---

## 6. HƯỚNG DẪN SỬ DỤNG CÔNG CỤ TỰ ĐỘNG HÓA CLI (`generate_knowledge_hub.py`)

Công cụ [generate_knowledge_hub.py](file:///c:/Intel/Laragon/www/LOG/generate_knowledge_hub.py) có thể chạy ở bất kỳ máy tính hoặc thư mục nào có cài đặt Python 3.

### Cách 1: Chạy Tương Tác (Dễ nhất - Tự hỏi đáp)
Mở terminal tại thư mục bất kỳ và gõ:
```bash
python generate_knowledge_hub.py
```
Hệ thống sẽ lần lượt hỏi:
```text
1. Nhập đường dẫn tệp nguồn (vd: Hoi Dap.txt hoặc thư mục docs): C:\du_an\tai_lieu.txt
2. Nhập thư mục lưu kết quả (để trống nếu dùng thư mục hiện tại): C:\du_an\web
3. Nhập tiêu đề hiển thị: Tài Liệu Dự Án ABC
```
Chương trình sẽ tự động phân tích, tạo cấu trúc thư mục, bóc tách Markdown và tạo file `index.html`.

### Cách 2: Chạy Bằng Dòng Lệnh 1 Lệnh Duy Nhất (Command-Line Arguments)
```bash
# Ví dụ 1: Tạo từ 1 file văn bản thô Hoi Dap.txt
python generate_knowledge_hub.py -s "c:/du_an/Hoi Dap.txt" -o "c:/du_an/web_hub" -t "Hệ Thống Tri Thức" -v "v2.9.2"

# Ví dụ 2: Tạo từ 1 thư mục chứa sẵn nhiều file Markdown
python generate_knowledge_hub.py -s "c:/du_an/docs" -o "c:/du_an/portal" -t "Portal Hướng Dẫn Kỹ Thuật"
```

### Các Tham Số Hỗ Trợ:
| Tham số | Viết tắt | Ý nghĩa | Mặc định |
| :--- | :--- | :--- | :--- |
| `--source` | `-s` | Đường dẫn tệp `.txt`/`.md` hoặc thư mục nguồn | *Bắt buộc* |
| `--output` | `-o` | Thư mục đích lưu trữ kết quả và file `index.html` | Thư mục hiện tại |
| `--title` | `-t` | Tiêu đề hiển thị trên Header của Hub | `Updatedone Logs` |
| `--version`| `-v` | Mã phiên bản hệ thống | `v2.9.2` |

---

## 7. BẢNG KIỂM TRA CHẤT LƯỢNG (CHECKLIST XÁC NHẬN)

Mỗi khi tạo mới một Hub tài liệu cho dự án, kiểm tra danh sách sau để đảm bảo đạt chuẩn 100%:
- [x] Không còn ký tự phân cách thô `==`, `====`, `======` trong nội dung tài liệu.
- [x] Không bị nối nhầm nội dung của chuyên mục này vào chuyên mục khác.
- [x] Mở trực tiếp `file:///.../index.html` tải mượt mà không có lỗi CORS trên Console F12.
- [x] Bấm nút Cuộn lên / giữa / xuống hoạt động chính xác.
- [x] Nhấn giữ nút Cuộn lên / xuống kích hoạt cuộn liên tục.
- [x] Nút Copy trên Khung Tệp và khối mã nguồn hoạt động chính xác.
- [x] Chuyển đổi Dark / Light Mode hiển thị độ tương phản cao, chữ không bị mờ hay chìm màu.
- [x] Bấm phím `/` tự động focus vào thanh tìm kiếm.
- [x] Escape chuẩn JSON nhúng: Không có lỗi `Bad control character in string literal` trên Console.
- [x] Đường dẫn tương đối động (`getRelativeFilePath`): Mở file .md mượt mà khi đổi tên thư mục.
- [x] Đồng bộ đủ 2 file `index.html` (Thư mục gốc và `.agents/update1/`).

---

## 8. ⚠️ CÁC LƯU Ý KỸ THUẬT TRỌNG YẾU ĐỂ KHÔNG BỊ LỖI KHI TẠO TRANG

Trong quá trình khởi tạo hoặc cập nhật Dashboard SPA, bắt buộc tuân thủ 3 nguyên tắc phòng chống lỗi sau:

### 1. Lỗi Cú Pháp JSON Nhúng (Data Syntax Crash - Bad Control Character)
- **Hiện tượng lỗi:** Trang `index.html` mở lên bị trắng rỗng hoàn toàn, không có dải chuyên mục phân loại, sidebar bên trái trống và bài viết bên phải không hiển thị. Bật F12 Console thấy lỗi đỏ:
  `Uncaught SyntaxError: Bad control character in string literal in JSON at position ...`
- **Nguyên nhân:** Nội dung Markdown trong trường `"content"` chứa các ký tự xuống dòng thô thực tế (literal newlines `\n`) không được escape thành chuỗi hợp lệ (`\n`).
- **Biện pháp bắt buộc:** Luôn sử dụng thư viện chuẩn (`json.dumps(dataset, ensure_ascii=False)` trong Python hoặc `JSON.stringify(dataset)` trong Node.js) để nhúng dữ liệu vào thẻ `<script id="embedded-dataset" type="application/json">`.

### 2. Thiếu File Thư Mục Gốc Khi Chạy Qua Máy Chủ Web (Web Server 404 Routing)
- **Hiện tượng lỗi:** Khi mở trực tiếp qua máy chủ ảo (Laragon, Apache: `http://localhost/tên_dự_án/index.html` hoặc `http://tên_dự_án.test/index.html`), trình duyệt báo `404 Not Found` hoặc hiện danh sách thư mục rỗng.
- **Nguyên nhân:** Web server luôn tìm kiếm `index.html` tại thư mục gốc của dự án. Nếu chỉ sinh file trong `.agents/update1/index.html`, đường dẫn `/index.html` sẽ không tồn tại.
- **Biện pháp bắt buộc:** Luôn duy trì đồng bộ 2 bản sao:
  1. `[PROJECT_ROOT]/index.html` (chạy Web Server).
  2. `[PROJECT_ROOT]/.agents/update1/index.html` (chạy offline `file:///`).

### 3. Hardcoded Đường Dẫn Tuyệt Đối (Gây Chết Link Khi Đổi Thư Mục)
- **Hiện tượng lỗi:** Nút "Mở" file .md hoặc sao chép đường dẫn bị trỏ vào đường dẫn cứng không tồn tại (vd: `file:///C:/Intel/Laragon/www/LOG/...`), gây lỗi `File Not Found` khi đổi tên folder hoặc chuyển máy.
- **Biện pháp bắt buộc:** Sử dụng hàm helper động:
  ```javascript
  function getRelativeFilePath(itemFile) {
      const pathname = window.location.pathname.replace(/\\/g, '/');
      const isInsideAgents = pathname.includes('/.agents/update1');
      return isInsideAgents ? itemFile : `.agents/update1/${itemFile}`;
  }
  ```
  Thẻ link mở file: `<a href="${relPath}" target="_blank">` để trình duyệt tự động resolve theo vị trí hiện hành.
