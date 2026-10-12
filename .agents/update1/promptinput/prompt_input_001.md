# BỘ SƯU TẬP PROMPT ĐẦU VÀO DỰ ÁN AI ZALO CSKH (PROMPT REGISTRY)

Tài liệu này lưu trữ toàn bộ các câu lệnh Prompt yêu cầu kỹ thuật đã nhập từ đầu đoạn chat tới giờ, được chuẩn hóa câu từ, sửa lỗi chính tả nhưng tuân thủ 100% nội dung gốc, sắp xếp theo thứ tự **mới nhất đầu tiên**.

---

### [PROMPT-003] Cấu Trúc Toàn Diện Updatedone, SPA Index & Gộp Rules/Skills
- **Thời gian nhập**: `2026-10-12 15:35:19`
- **Nhãn phân loại**: `[Kiến trúc / Hệ thống]`, `[Giao diện / UI]`, `[Code xử lý]`
- **Mục tiêu**: Bỏ tạo thư mục lồng trong update1, update2; liệt kê tính năng vào index; xây dựng SPA dashboard lấy nội dung từ markdown; tạo thư mục features, fixes, promptinput, prompt_all; hỗ trợ dark/light mode và khung kỹ thuật (Tech Box) ghi nhớ trạng thái.

```text
không cần phải tạo thư mục rồi mới file md trong update1, update2
- liệt kê nó ra file chức năng index

### Tổng hợp update sau mỗi prompt
- Update trong updatedone trong .agents của project đang làm, loại bỏ trùng lặp yêu cầu gửi lên, trùng lặp nội dung trong 1 tính năng lớn, chức năng lớn nếu có, bỏ qua tính năng, yêu cầu đã có trước đó nếu như lặp, mỗi chức năng/link 1 file hoặc thêm file _001 _002 nếu quá dài định dạng lưu .md, hiển thị ra trình duyệt là .html chứa lấy nội dung từ .md hiển thị.
- Phân loại theo link hay chức năng lớn để dễ quản lý kiểm soát phiên bản, tìm kiếm, tra cứu, truy vấn, hiện thời gian, lần cập nhật cuối, phiên bản.
- Từ file .md build ra file HTML để với mỗi tính năng có một trang riêng để xem, làm nổi bật từng phiên bản và những thay đổi của tính năng theo từng phiên bản, nội dung đầy đủ chi tiết hơn, hiện thời gian, prompt nhập vào là gì, plan, walkthrough, kết quả cho mỗi phiên bản, lần cập nhật cuối hiện ở đầu, có mục lục hoặc thêm tìm kiếm nhanh.
- Thiết kế 1 file fix001.md, fix002.md... mỗi file nặng không quá 100KB để lưu trữ những lỗi hay gặp, hướng xử lý, đề xuất cho AI khi code mới để tránh lặp lỗi tương tự.
- Tổng hợp 1 trang danh sách câu lệnh người dùng nhập vào lưu trong ./promptinput/prompt_input_001.md kèm nút copy từng prompt và copy tất cả prompt.
- Thêm các quy chuẩn dùng chung vào ./prompt_all/prompt_apply_all_001.md,...
- Thêm khung riêng ở mỗi chức năng hiện controller, layout, router, file áp dụng kèm đường dẫn tương đối, có nút copy, có thể thu nhỏ/mở rộng và ghi nhớ trạng thái.
```

---

### [PROMPT-002] Di Chuyển Update1, Update2 Vào Updatedone & Gộp Rules Với Skills
- **Thời gian nhập**: `2026-10-12 15:00:18`
- **Nhãn phân loại**: `[Kiến trúc / Hệ thống]`, `[Cấu trúc thư mục]`
- **Mục tiêu**: Di chuyển toàn bộ file ở update1, update2 vào updatedone; gộp rules và skills làm một, loại bỏ hoàn toàn các nội dung trùng lặp.

```text
- di chuyển file ở update1, update2, liệt kê chức năng phiên bản cập nhật vào index, vào updatedone
- gộp rules skills làm 1, gộp nội dung, xóa bỏ nội dung lặp
```

---

### [PROMPT-001] Tái Cấu Trúc .agents Dựa Trên Mẫu Skills & Updatedone Của AutoKeyboadMouse
- **Thời gian nhập**: `2026-10-12 14:47:16`
- **Nhãn phân loại**: `[Cấu trúc thư mục]`, `[Tài liệu & Kỹ thuật]`
- **Mục tiêu**: Dựa vào cấu trúc thư mục skills và updatedone của dự án AutoKeyboadMouse để thiết lập lại cấu trúc trong .agents của dự án hiện tại, đảm bảo mở xem được file markdown và không rút gọn nội dung.

```text
Dựa vào cấu trúc của 2 thư mục này
làm cho tôi lại cấu trúc cho thư mục sau ở trong .agent của phần mềm này:
C:\Intel\Laragon\www\300_Python\001_AutoKeyboadMouse\.agents\skills
C:\Intel\Laragon\www\300_Python\001_AutoKeyboadMouse\.agents\updatedone
thư mục con áp dụng, cho file 1 md riêng 1 thư mục để mở xem file md và tuân thủ xem được nó, hạn chế rút gọn quá mức nội dung file md: rules, update1, update2
```