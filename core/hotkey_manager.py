import threading
import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)

class HotkeyManager:
    """Quản lý các phím tắt toàn cục để điều khiển Bot, Can thiệp thủ công & Điều khiển Gửi tin nhóm (F6/F7)."""

    def __init__(
        self,
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_manual_override: Callable[[], None],
        on_broadcast_pause_resume: Optional[Callable[[], None]] = None,
        on_broadcast_cancel: Optional[Callable[[], None]] = None,
        on_quick_send_f10: Optional[Callable[[], None]] = None,
        hotkey_config: Dict[str, str] = None
    ):
        self.on_start = on_start
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_manual_override = on_manual_override
        self.on_broadcast_pause_resume = on_broadcast_pause_resume
        self.on_broadcast_cancel = on_broadcast_cancel
        self.on_quick_send_f10 = on_quick_send_f10
        
        self.config = hotkey_config or {
            "start_bot": "f8",
            "pause_bot": "f9",
            "resume_bot": "f8",
            "quick_send_f10": "f10",
            "manual_override": "ctrl+space",
            "broadcast_pause_resume": "f6",
            "broadcast_cancel": "f7"
        }
        self.is_running = False
        self._listener_thread = None

    def start_listening(self):
        """Bắt đầu lắng nghe phím tắt trong luồng nền."""
        if self.is_running:
            return

        self.is_running = True
        self._listener_thread = threading.Thread(target=self._listen_worker, daemon=True)
        self._listener_thread.start()
        logger.info(f"[Hotkey] Đã kích hoạt phím tắt: F8 (Bật/Tắt Bot), F9 (Hủy Thao Tác), F10 (Gửi Nhanh Mẫu vào Zalo), F6 (Tạm dừng/Tiếp tục gửi nhóm), F7 (Hủy gửi nhóm), Ctrl+Space (Can thiệp tay)")

    def _listen_worker(self):
        """Sử dụng thư viện keyboard để bắt phím tắt toàn hệ thống."""
        try:
            import keyboard

            keyboard.add_hotkey(self.config.get("start_bot", "f8"), self.on_start)
            keyboard.add_hotkey(self.config.get("pause_bot", "f9"), self.on_pause)
            keyboard.add_hotkey(self.config.get("manual_override", "ctrl+space"), self.on_manual_override)

            if self.on_quick_send_f10:
                keyboard.add_hotkey(self.config.get("quick_send_f10", "f10"), self.on_quick_send_f10)
            elif self.on_resume:
                keyboard.add_hotkey(self.config.get("quick_send_f10", "f10"), self.on_resume)

            if self.on_broadcast_pause_resume:
                keyboard.add_hotkey(self.config.get("broadcast_pause_resume", "f6"), self.on_broadcast_pause_resume)
            if self.on_broadcast_cancel:
                keyboard.add_hotkey(self.config.get("broadcast_cancel", "f7"), self.on_broadcast_cancel)

            keyboard.wait()
        except ImportError:
            logger.warning("[Hotkey] Thư viện 'keyboard' chưa cài đặt hoặc thiếu quyền Administrator. Sử dụng chế độ bấm nút trên Dashboard.")
        except Exception as e:
            logger.warning(f"[Hotkey] Không thể đăng ký Global Hotkey: {e}")

    def stop_listening(self):
        """Hủy đăng ký phím tắt."""
        self.is_running = False
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
