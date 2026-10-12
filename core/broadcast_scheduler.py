import time
import threading
import logging
from datetime import datetime
from typing import Optional, Callable
from core.state_manager import StateManager
from zalo_layer.zalo_automation import ZaloAutomation

logger = logging.getLogger(__name__)


class BroadcastScheduler:
    """
    Bộ lập lịch gửi tin nhắn & file tự động đến toàn bộ nhóm Zalo theo các mốc giờ (7h, 10h, 17h, 20h,...).
    - Tự động quét theo phút, chạy đúng giờ đã cài đặt.
    - Hỗ trợ chọn Mẫu 1, Mẫu 2, Mẫu 3 hoặc Mẫu Mặc Định.
    - Chống gửi lặp trong cùng một ngày.
    """

    def __init__(self, state_manager: StateManager, on_broadcast_started: Optional[Callable] = None, on_broadcast_finished: Optional[Callable] = None):
        self.state = state_manager
        self.on_started = on_broadcast_started
        self.on_finished = on_broadcast_finished
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """Bắt đầu chạy tiến trình kiểm tra lịch ngầm."""
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("[Scheduler] ⏰ Bộ lập lịch tự động gửi tin nhóm đã BẬT!")

    def stop(self):
        """Tạm dừng bộ lập lịch."""
        self.is_running = False
        self._stop_event.set()
        logger.info("[Scheduler] ⏸ Bộ lập lịch tự động gửi tin nhóm đã TẮT.")

    def _scheduler_loop(self):
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                current_time_str = now.strftime("%H:%M")
                today_str = now.strftime("%Y-%m-%d")

                schedules = self.state.get_all_schedules()
                for sch in schedules:
                    if sch['is_active'] == 1 and sch['schedule_time'] == current_time_str:
                        if sch['last_run_date'] != today_str:
                            logger.info(f"[Scheduler] 🎯 Khớp mốc giờ lên lịch: {current_time_str}! Bắt đầu gửi tự động (Mẫu #{sch['template_num']})...")
                            self.state.update_schedule_last_run(sch['id'], today_str)
                            self._execute_scheduled_broadcast(sch)

            except Exception as e:
                logger.error(f"[Scheduler] Lỗi trong vòng lặp lập lịch: {e}")

            # Chờ 20 giây một cách thông minh (ngắt ngay khi stop_event được kích hoạt)
            self._stop_event.wait(timeout=20)

    def _execute_scheduled_broadcast(self, schedule_info: dict):
        tpl_num = schedule_info.get('template_num', 1)
        tag_filter = schedule_info.get('tag_filter', 'Gửi mẫu quảng cáo')
        
        tpl = self.state.get_template(tpl_num)
        if not tpl:
            tpl = self.state.get_default_template()

        if not tpl:
            logger.warning("[Scheduler] Không tìm thấy mẫu tin nhắn nào để gửi!")
            return

        msg_content = tpl.get('content', '')
        files = tpl.get('files', [])

        if self.on_started:
            try:
                self.on_started(schedule_info['schedule_time'], tpl_num, tag_filter)
            except Exception:
                pass

        def _worker():
            batch_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            results = ZaloAutomation.broadcast_to_groups_in_tag(
                tag_name=tag_filter,
                messages=[msg_content] if msg_content else [],
                file_paths=files,
                state_mgr=self.state,
                batch_id=batch_id,
                template_num=tpl_num,
                max_groups=50,
                delay_between=4.0
            )
            if self.on_finished:
                try:
                    self.on_finished(results)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
