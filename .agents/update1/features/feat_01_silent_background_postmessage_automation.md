# ĐẶC TẢ TÍNH NĂNG: GỬI NGẦM KHÔNG CHIẾM CHUỘT (SILENT WIN32 AUTOMATION)
- **Mã tính năng**: `FEAT-001`
- **Phiên bản**: `v2.0.0`
- **Lần cập nhật cuối**: `2026-10-05 14:00:00`
- **Bộ điều khiển (Controller)**: `controllers/broadcast_controller.py`, `core/zalo_automation.py`
- **Giao diện (Layout)**: `gui/tabs/tab2_broadcast.py`, `gui/tabs/tab3_scripts.py`
- **Đường dẫn tệp áp dụng**: `zalo_layer/zalo_automation.py`, `gui/dashboard.py`

---

## 1. Mục Đích & Yêu Cầu Tính Năng
- Cho phép gửi tin nhắn, kịch bản chăm sóc khách hàng hoặc broadcast vào cửa sổ Zalo PC mà không làm dịch chuyển con trỏ chuột vật lý của Windows.
- Người dùng có thể tiếp tục lướt web, soạn thảo văn bản hoặc làm việc trên các phần mềm khác mà không bị giật con trỏ chuột.

## 2. Giải Pháp Kỹ Thuật (Architecture & Implementation)
- **Silent Deep PostMessage Click**: Chuyển đổi tọa độ màn hình sang Client Point của cửa sổ đích, gửi `WM_LBUTTONDOWN` và `WM_LBUTTONUP` qua Win32 API.
- **Quick Focus & Restore (<150ms)**: Lưu HWND hiện tại của người dùng, focus nhanh vào Zalo, gửi Clipboard (Ctrl+V, Enter) và phục hồi ngay lập tức cửa sổ cũ cho người dùng.
- **Điều khiển từ xa (Remote Desktop)**: Tự động phát hiện UltraViewer, AnyDesk, TeamViewer để đệm trễ mạng (+1.0s) chống mất dữ liệu.

## 3. Kết Quả Sau Khi Triển Khai
- 100% không di chuột vật lý khi gửi tin nhắn ngầm.
- Phục hồi cửa sổ làm việc ban đầu cực nhanh (<150ms), người dùng không cảm nhận thấy độ gián đoạn.