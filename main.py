import os
import sys
import io
import yaml
import logging
from typing import Optional, Dict, Any, List

# =====================================================================
# TỰ ĐỘNG CẤU HÌNH CHUẨN UTF-8 TOÀN DIỆN CHO WINDOWS CMD / POWERSHELL
# =====================================================================
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

if sys.platform == "win32":
    try:
        # Đặt bảng mã của Console Windows thành UTF-8 (Code Page 65001)
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass
    
    try:
        # Cấu hình lại luồng xuất stdout và stderr chuẩn UTF-8
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# Nạp helper đường dẫn trước để cấu hình File Logger
from core.app_paths import get_resource_path, get_app_dir, get_storage_path
from logging.handlers import RotatingFileHandler

# Cấu hình Logger hệ thống xuất UTF-8 đồng thời ra Console và File log xoay vòng
log_dir = get_storage_path("logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "app.log")

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

# 1. Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S")
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# 2. File Handler (Ghi log liên tục, tối đa 10MB x 5 file lưu trữ)
try:
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
except Exception as ex:
    print(f"Không thể khởi tạo FileHandler cho log: {ex}")

# Tự động bắt và ghi log mọi lỗi Crash / Uncaught Exception
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("💥 UNCAUGHT EXCEPTION CRASH:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_uncaught_exception

logger = logging.getLogger("ZaloAISupport")
logger.info(f"📁 Log ứng dụng được lưu tại: {log_file_path}")

# Nạp các module dự án sau khi đã kích hoạt UTF-8
from core.state_manager import StateManager
from core.gemini_engine import GeminiEngine
from core.telegram_notifier import TelegramNotifier
from core.drive_manager import DriveManager
from core.hotkey_manager import HotkeyManager
from zalo_layer.zalo_handler import ZaloHandler
# =====================================================================
# PATCH AN TOÀN CHO OPENCV / PYSCREEZE / PYAUTOGUI
# =====================================================================
try:
    import cv2
    if not hasattr(cv2, '__version__') or cv2.__version__ is None:
        cv2.__version__ = '5.0.0'
except Exception:
    pass

from gui.dashboard import AIDashboard, LoginDialog

def load_config(config_path: Optional[str] = None) -> dict:
    if not config_path:
        config_path = get_resource_path("config/config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    logger.warning(f"Không tìm thấy file {config_path}. Sử dụng cấu hình mặc định.")
    return {}

def main():
    logger.info("==================================================")
    logger.info("   HỆ THỐNG AI CSKH ZALO - GIÁO ÁN LỊCH SỬ 6-12   ")
    logger.info("   (BỘ SÁCH KẾT NỐI TRI THỨC VỚI CUỘC SỐNG)      ")
    logger.info("==================================================")

    config = load_config()

    # 1. Khởi tạo State Manager (SQLite)
    state_mgr = StateManager()

    # 2. Khởi tạo Gemini Engine (Tích hợp Bộ Nhớ Tri Thức Cá Nhân Tab 3 & Sổ Tay Sửa)
    gemini_cfg = config.get("gemini", {})
    gemini_engine = GeminiEngine(
        api_key=gemini_cfg.get("api_key", ""),
        model_name=gemini_cfg.get("model_name", "gemini-3.6-flash"),
        allow_general_chat=gemini_cfg.get("allow_general_chat", True),
        state_manager=state_mgr
    )

    # 3. Khởi tạo Telegram Notifier
    tele_cfg = config.get("telegram", {})
    tele_notifier = TelegramNotifier(
        bot_token=tele_cfg.get("bot_token", ""),
        chat_id=tele_cfg.get("chat_id", ""),
        enabled=tele_cfg.get("enabled", False)
    )

    # 4. Khởi tạo Google Drive Manager
    drive_cfg = config.get("google_drive", {})
    drive_mgr = DriveManager(
        credentials_path=get_resource_path(drive_cfg.get("credentials_file", "config/service_account.json")),
        enabled=drive_cfg.get("enabled", False),
        state_manager=state_mgr
    )

    # 5. Khởi tạo Zalo Layer Handler
    zalo_handler = ZaloHandler(
        gemini_engine=gemini_engine,
        state_manager=state_mgr,
        telegram_notifier=tele_notifier,
        drive_manager=drive_mgr,
        config=config
    )

    app = None

    # 6. Khởi tạo Hotkey Manager (F8: Bật/Tắt Bot AI, F9: HỦY MỌI THAO TÁC, F10: Gửi Nhanh Mẫu vào Zalo, F6: Tạm dừng Gửi Nhóm, F7: Hủy Gửi Nhóm, Ctrl+Space: Can thiệp tay)
    hotkeys = HotkeyManager(
        on_start=lambda: (app.after(0, app._toggle_bot_running_state_from_hotkey) if app else zalo_handler.resume_bot()),
        on_pause=lambda: (app.after(0, app.emergency_cancel_all_operations) if app else zalo_handler.pause_bot()),
        on_resume=lambda: (app.after(0, app._toggle_bot_running_state_from_hotkey) if app else zalo_handler.resume_bot()),
        on_manual_override=lambda: logger.info("[Hotkey] Yêu cầu can thiệp thủ công."),
        on_broadcast_pause_resume=lambda: (app.after(0, app._toggle_broadcast_pause_from_hotkey) if app else None),
        on_broadcast_cancel=lambda: (app.after(0, app.emergency_cancel_all_operations) if app else None),
        on_quick_send_f10=lambda: (app.after(0, app._on_f10_quick_send) if app else None),
        hotkey_config=config.get("hotkeys", {})
    )
    hotkeys.start_listening()

    # 7. Khởi chạy Giao diện điều khiển Desktop (GUI)
    app = AIDashboard(
        zalo_handler=zalo_handler,
        state_manager=state_mgr,
        gemini_engine=gemini_engine,
        hotkey_manager=hotkeys,
        drive_manager=drive_mgr
    )

    try:
        app.mainloop()
    finally:
        hotkeys.stop_listening()
        logger.info("Đã đóng hệ thống an toàn.")

if __name__ == "__main__":
    main()
