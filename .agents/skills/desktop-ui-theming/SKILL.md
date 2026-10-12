---
name: desktop-ui-theming
description: Chuẩn hóa thiết kế giao diện desktop Tailwind CSS Slate Light và Dark Mode, tương phản cao, xử lý đệ quy Canvas và làm mới giao diện động.
---

# KỸ NĂNG: THIẾT KẾ GIAO DIỆN DESKTOP & THEME NHẤT QUÁN (UI THEMING)

Hướng dẫn thiết kế và duy trì giao diện Tkinter tương thích hai chế độ Sáng (Light Theme) và Tối (Dark Theme) chuẩn Tailwind CSS.

---

## 1. Bảng Màu Chuẩn (Color Palette)

### 🔹 1.1. Giao Diện Sáng (Light Theme)
- **Nền tổng thể & Canvas:** `#ffffff` (trắng tinh khiết) hoặc `#f8fafc` (Slate-50) / `#f1f5f9` (Slate-100).
- **Chữ chính / Nhãn / Tên link:** `#0f172a` (Slate-900 - chữ đen đậm, tương phản cao, cực kỳ rõ nét).
- **Điểm nhấn xanh (Accent):** `#0284c7` (Sky-600) hoặc `#2563eb` (Blue-600) - màu xanh nổi bật, dễ đọc trên nền sáng.
- **Hàng xen kẽ trong bảng / danh sách:** `#ffffff` và `#f8fafc`.
- **Checkbox `selectcolor`:** `#ffffff` (ô vuông tích nền trắng sạch, không bị đen).
- **Nút bấm phụ / Inactive:** `bg='#e2e8f0'`, `fg='#334155'`.

### 🔹 1.2. Giao Diện Tối (Dark Theme)
- **Nền tổng thể & Canvas:** `#0f172a` (Slate-900) hoặc `#0b0f19` (Slate-950).
- **Chữ chính / Nhãn / Tên link:** `#f8fafc` (Slate-50 - trắng sáng, sắc nét).
- **Điểm nhấn xanh (Accent):** `#38bdf8` (Sky-400 - xanh dạ quang sáng trên nền tối).
- **Hàng xen kẽ trong bảng:** `#1e293b` và `#0f172a`.
- **Checkbox `selectcolor`:** `#0f172a`.
- **Nút bấm phụ / Inactive:** `bg='#334155'`, `fg='#cbd5e1'`.

---

## 2. Quy Tắc Áp Dụng Theme Động

- Không gán cứng mã màu tối trong các hàm vẽ động (`_render_quick_links_for_category`, `_switch_bundle_subview`, `_open_quick_links_manager_modal`).
- Luôn kiểm tra cờ giao diện:
  ```python
  is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
  ```
- Hàm `_apply_theme_to_widget_recursive` **BẮT BUỘC** bao gồm cả lớp widget `"Canvas"`.
- Trong `_apply_theme()`, luôn gọi lại các hàm cập nhật subview động để giao diện chuyển đổi tức thì 100%.

---

## 3. Thanh Công Cụ Nổi Mini On-Top & Dimming (Floating Mini Toolbar)

- Khi người dùng làm việc song song với Zalo PC, thu nhỏ Dashboard thành thanh mini float nhỏ gọn (500x42px) luôn ghim On-top.
- **Idle Dimming:** Tự động làm mờ thanh nổi khi không có thao tác chuột (sau 3-5 giây) để tránh che khuất nội dung làm việc.
- Khi con trỏ chuột hover vào thanh nổi, ngay lập tức phục hồi 100% độ sáng (opacity 1.0).

---

## 4. Quản Lý Thông Báo Toast (Toast Notification Limiter)

- Giới hạn tối đa 3 Toast cùng lúc (`_ACTIVE_TOASTS`).
- Tự hủy các toast cũ để chống tràn màn hình và giải phóng bộ nhớ RAM.