import os
import time
import requests
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class TelegramNotifier:
    """
    Gửi cảnh báo khẩn cấp tới chủ shop qua Telegram khi khách hàng cần hỗ trợ thủ công.
    Hỗ trợ xuất & gửi tệp sao lưu dữ liệu toàn bộ hệ thống (.json) tự động qua Telegram Bot.
    Tương thích Python 3.12, tự động dừng lại sau tối đa 5 lần thử (chống lặp vô tận).
    """
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token.strip() if bot_token else ""
        self.chat_id = chat_id.strip() if chat_id else ""
        self.enabled = enabled and bool(self.bot_token) and bool(self.chat_id) and self.bot_token != "YOUR_TELEGRAM_BOT_TOKEN"
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _post_with_retry(self, payload: Dict[str, Any], max_attempts: int = MAX_RETRIES) -> bool:
        """Gửi request tới Telegram API với tối đa max_attempts lần thử."""
        if not self.bot_token or not self.chat_id:
            return False
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(self.api_url, json=payload, timeout=8)
                if response.status_code == 200:
                    return True
                elif 400 <= response.status_code < 500:
                    # Lỗi Client (Token sai, chat_id sai,...) -> Dừng ngay không thử lại
                    logger.error(f"[Telegram] Lỗi client ({response.status_code}): {response.text}")
                    return False
                else:
                    # Lỗi Server (5xx) -> Thử lại
                    logger.warning(f"[Telegram] [Lần thử {attempt}/{max_attempts}] Máy chủ Telegram phản hồi mã {response.status_code}")
            except Exception as e:
                logger.warning(f"[Telegram] [Lần thử {attempt}/{max_attempts}] Lỗi kết nối API: {e}")

            if attempt < max_attempts:
                time.sleep(1.0)

        logger.error(f"[Telegram] ⚠️ [DỪNG LẠI] Đã thử {max_attempts} lần gửi tin Telegram thất bại. Dừng lại.")
        return False

    def send_document(
        self,
        file_path: str,
        caption: str = "",
        disable_notification: bool = True,
        max_attempts: int = MAX_RETRIES
    ) -> Tuple[bool, str]:
        """Gửi tệp sao lưu dữ liệu (.json, .zip,...) về Telegram."""
        if not self.bot_token or not self.chat_id or self.bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
            return False, "Chưa cấu hình Telegram Bot Token hoặc Chat ID!"
        if not os.path.exists(file_path):
            return False, f"Tệp không tồn tại: {file_path}"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        for attempt in range(1, max_attempts + 1):
            try:
                with open(file_path, "rb") as f:
                    files = {"document": (os.path.basename(file_path), f)}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "disable_notification": disable_notification,
                        "parse_mode": "HTML"
                    }
                    response = requests.post(url, data=data, files=files, timeout=30)
                    if response.status_code == 200:
                        logger.info(f"[Telegram] Đã gửi file {file_path} thành công về Telegram.")
                        return True, "Gửi file về Telegram thành công!"
                    elif 400 <= response.status_code < 500:
                        err_msg = f"Lỗi Telegram ({response.status_code}): {response.text}"
                        logger.error(f"[Telegram] {err_msg}")
                        return False, err_msg
                    else:
                        logger.warning(f"[Telegram] [Lần {attempt}] Server error {response.status_code}")
            except Exception as e:
                logger.warning(f"[Telegram] [Lần {attempt}] Lỗi kết nối: {e}")
            if attempt < max_attempts:
                time.sleep(1.0)
        return False, "Không thể kết nối đến máy chủ Telegram sau nhiều lần thử."

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra kết nối Telegram Bot Token và Chat ID."""
        if not self.bot_token or not self.chat_id or self.bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
            return False, "Vui lòng nhập Bot Token và Chat ID trước khi kiểm tra!"
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": "🤖 <b>AI ZALO CSKH - TEST KẾT NỐI TELEGRAM THÀNH CÔNG!</b>\n\n✅ Đã kết nối thông suốt với tài khoản/nhóm của bạn.\n⚙️ Hệ thống sẵn sàng nhận tệp sao lưu dữ liệu định kỳ.",
            "parse_mode": "HTML",
            "disable_notification": True
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                return True, "✅ Kết nối Telegram thành công! Tin nhắn test đã gửi đến nhóm/chat của bạn."
            else:
                return False, f"❌ Lỗi từ Telegram ({res.status_code}): {res.text}"
        except Exception as e:
            return False, f"❌ Lỗi kết nối mạng: {e}"

    def send_escalation_alert(
        self,
        customer_name: str,
        user_id: str,
        issue_summary: str,
        unresolved_count: int,
        last_customer_message: str
    ) -> bool:
        """Gửi thông báo khi khách hỏi lại >= 3 lần hoặc chưa hài lòng."""
        if not self.enabled:
            logger.info(f"[Telegram Mock Alert] Cần hỗ trợ khách {customer_name} ({user_id}) - Vấn đề: {issue_summary}")
            return False

        text = (
            f"🚨 <b>CẦN CHỦ SHOP HỖ TRỢ THỦ CÔNG!</b>\n\n"
            f"👤 <b>Khách hàng:</b> {customer_name}\n"
            f"🆔 <b>Zalo ID:</b> <code>{user_id}</code>\n"
            f"🔄 <b>Số lần hỏi lại:</b> {unresolved_count} lần liên tiếp\n"
            f"❓ <b>Vấn đề phát hiện:</b> {issue_summary}\n\n"
            f"💬 <b>Tin nhắn gần nhất của khách:</b>\n"
            f"<i>\"{last_customer_message}\"</i>\n\n"
            f"⚙️ <i>Hệ thống AI đã tạm dừng cho khách này. Mời bạn vào Zalo kiểm tra trực tiếp!</i>"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        success = self._post_with_retry(payload, max_attempts=MAX_RETRIES)
        if success:
            logger.info(f"[Telegram] Đã gửi cảnh báo hỗ trợ khách {customer_name} thành công.")
        return success

    def send_content_correction_alert(
        self,
        customer_name: str,
        grade: str,
        lesson: str,
        feedback_text: str
    ) -> bool:
        """Gửi thông báo khi thầy/cô báo lỗi nội dung/kiến thức giáo án để lưu ý sửa chữa."""
        if not self.enabled:
            return False

        text = (
            f"📝 <b>GHI NHẬN GÓP Ý NỘI DUNG GIÁO ÁN!</b>\n\n"
            f"👤 <b>Thầy/Cô:</b> {customer_name}\n"
            f"📚 <b>Khối/Lớp:</b> Lịch sử {grade}\n"
            f"📖 <b>Bài học:</b> {lesson}\n"
            f"📌 <b>Nội dung cần sửa:</b>\n"
            f"<i>\"{feedback_text}\"</i>\n\n"
            f"💾 <i>Đã tự động lưu vào Sổ tay chỉnh sửa giáo án trên Dashboard.</i>"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        return self._post_with_retry(payload, max_attempts=MAX_RETRIES)
