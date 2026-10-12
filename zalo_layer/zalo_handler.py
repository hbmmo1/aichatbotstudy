import time
import re
import logging
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)

class ZaloHandler:
    """Bộ điều phối xử lý tin nhắn Zalo, kết nối StateManager, GeminiEngine, TelegramNotifier và DriveManager."""

    def __init__(
        self,
        gemini_engine,
        state_manager,
        telegram_notifier,
        drive_manager,
        config: Dict[str, Any]
    ):
        self.gemini = gemini_engine
        self.state = state_manager
        self.tele = telegram_notifier
        self.drive = drive_manager
        self.config = config
        
        self.is_active = True
        self.escalation_threshold = config.get("telegram", {}).get("escalation_threshold", 3)
        self.reply_delay = config.get("app", {}).get("reply_delay_seconds", 2.0)
        self.auto_reply = config.get("app", {}).get("auto_reply", True)

        self.on_message_received_callback: Optional[Callable] = None
        self.on_reply_sent_callback: Optional[Callable] = None
        self.on_step_log_callback: Optional[Callable] = None

    def _log_step(self, step_no: int, step_title: str, detail: str, level: str = "INFO"):
        msg = f"[BƯỚC {step_no}/5 - {step_title}] {detail}"
        if level == "WARNING":
            logger.warning(msg)
        elif level == "ERROR":
            logger.error(msg)
        else:
            logger.info(msg)
        if self.on_step_log_callback:
            try:
                self.on_step_log_callback(step_no, step_title, detail, level)
            except Exception:
                pass

    def pause_bot(self):
        self.is_active = False
        logger.info("[Bot Control] Đã TẠM DỪNG bot.")

    def resume_bot(self):
        self.is_active = True
        logger.info("[Bot Control] Đã TIẾP TỤC bot.")

    def pause(self):
        self.pause_bot()

    def resume(self):
        self.resume_bot()

    @property
    def is_running(self) -> bool:
        return self.is_active

    def _extract_grade(self, text: str) -> Optional[str]:
        """Trích xuất khối lớp từ tin nhắn: 6, 7, 8, 9, 10, 11, 12, THCS, THPT."""
        upper = text.upper()
        if "THCS" in upper or "CẤP 2" in upper or "CAP 2" in upper:
            return "THCS"
        if "THPT" in upper or "CẤP 3" in upper or "CAP 3" in upper:
            return "THPT"

        for g in ["12", "11", "10", "9", "8", "7", "6"]:
            patterns = [f"LỚP {g}", f"LOP {g}", f"L{g}", f"SỬ {g}", f"SU {g}", f"KHỐI {g}", f"KHOI {g}"]
            if any(p in upper for p in patterns) or re.search(rf"\b{g}\b", text):
                return g
        return None

    def _extract_material_type(self, text: str) -> Optional[str]:
        """Trích xuất loại tài liệu khách đang xin."""
        lower = text.lower()
        if "ppct" in lower or "phân phối chương trình" in lower or "phan phoi" in lower:
            return "ppct"
        if "đề kiểm tra" in lower or "trắc nghiệm" in lower or "de kiem tra" in lower or "đề thi" in lower:
            return "de_kiem_tra"
        if "phiếu học tập" in lower or "phieu hoc tap" in lower:
            return "phieu_hoc_tap"
        if "phiếu nhóm" in lower or "phieu nhom" in lower or "hoạt động nhóm" in lower:
            return "phieu_nhom"
        if "chuyên đề" in lower or "chuyen de" in lower:
            return "chuyen_de"
        return None

    def handle_incoming_message(
        self,
        user_id: str,
        display_name: str,
        message_text: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Xử lý khi có tin nhắn hoặc ảnh mới từ khách hàng Zalo theo 5 bước chuẩn hóa.
        """
        # =========================================================================
        # BƯỚC 1: TIẾP NHẬN & LƯU VÀO DATABASE
        # =========================================================================
        attach_info = f" (kèm ảnh: {image_path})" if image_path else ""
        self._log_step(1, "TIẾP NHẬN", f"Nhận tin nhắn từ Thầy/Cô '{display_name}' (ID: {user_id}): \"{message_text}\"{attach_info}")
        
        self.state.log_message(user_id, sender="customer", text=message_text, has_image=bool(image_path), image_path=image_path or "")
        conv = self.state.get_or_create_conversation(user_id, display_name)

        if self.on_message_received_callback:
            self.on_message_received_callback(user_id, display_name, message_text, image_path)

        # =========================================================================
        # BƯỚC 2: KIỂM TRA TRẠNG THÁI HỆ THỐNG & CHẾ ĐỘ CAN THIỆP TAY
        # =========================================================================
        if not self.is_active:
            self._log_step(2, "KIỂM TRA TRẠNG THÁI", f"Bot đang ở trạng thái TẠM DỪNG (F9). Bỏ qua phản hồi tự động cho '{display_name}'.", "WARNING")
            return {"status": "bot_paused", "replies": []}

        if conv.get("is_manual_override") == 1:
            self._log_step(2, "KIỂM TRA TRẠNG THÁI", f"Khách '{display_name}' đang ở chế độ CAN THIỆP TAY (Manual Mode). Bot giữ nguyên để Admin xử lý.", "WARNING")
            return {"status": "manual_override", "replies": []}

        self._log_step(2, "KIỂM TRA TRẠNG THÁI", f"Hệ thống đang hoạt động TỰ ĐỘNG bình thường. Bắt đầu phân tích dữ liệu.")

        # =========================================================================
        # BƯỚC 3: PHÂN TÍCH Ý ĐỊNH (INTENT) & BÓC TÁCH THÔNG TIN
        # =========================================================================
        grade = self._extract_grade(message_text)
        material_type = self._extract_material_type(message_text)
        self._log_step(3, "PHÂN TÍCH Ý ĐỊNH", f"Bóc tách thông tin: Khối Lớp = {grade or 'Chưa xác định'} | Loại Tài Liệu = {material_type or 'Chung/Khác'}")

        # Trường hợp 3.1: Khách gửi Email xin cấp quyền Google Drive
        if "@gmail.com" in message_text.lower():
            words = message_text.split()
            email = next((w.strip(",.;()[]") for w in words if "@gmail.com" in w.lower()), "")
            target_grade = grade or "THPT"
            if email:
                self._log_step(3, "PHÂN TÍCH Ý ĐỊNH", f"Phát hiện yêu cầu cấp quyền Google Drive cho email: {email} (Khối: {target_grade})")
                grant_res = self.drive.grant_view_permission(email, target_grade, user_id=user_id)
                reply_text = [grant_res["message"]]
                self._dispatch_reply(user_id, display_name, reply_text)
                self.state.update_conversation_status(user_id, "RESOLVED")
                self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"Đã cấp quyền Drive & gửi hướng dẫn thành công cho {email}.")
                return {"status": "drive_permission_granted", "replies": reply_text}

        # Trường hợp 3.2: Khách xin tài liệu cụ thể (PPCT, Đề kiểm tra, Phiếu học tập)
        if material_type:
            if not grade:
                self._log_step(3, "PHÂN TÍCH Ý ĐỊNH", f"Khách xin {material_type} nhưng chưa rõ Khối Lớp. Tự động phản hồi hỏi lại lớp.")
                ask_grade_reply = [
                    "Dạ bên em có đầy đủ tài liệu chuẩn theo bộ sách Kết Nối Tri Thức Với Cuộc Sống ạ! 😊",
                    f"Dạ Thầy/Cô đang cần lấy tài liệu của Khối/Lớp mấy (Lớp 6, 7, 8, 9, 10, 11 hay 12) để em gửi link hoặc file ngay cho Thầy/Cô nhé ạ? ✨"
                ]
                self._dispatch_reply(user_id, display_name, ask_grade_reply)
                return {"status": "asking_grade", "replies": ask_grade_reply}
            else:
                self._log_step(3, "PHÂN TÍCH Ý ĐỊNH", f"Khách xin {material_type} Lớp {grade}. Lấy link trực tiếp từ DriveMatrix.")
                mat_link = self.drive.get_material_link(grade, material_type)
                type_names = {
                    "ppct": "Phân phối chương trình (PPCT)",
                    "de_kiem_tra": "Bộ Đề kiểm tra định kỳ & Trắc nghiệm",
                    "phieu_hoc_tap": "Phiếu học tập bài học",
                    "phieu_nhom": "Phiếu hoạt động nhóm",
                    "chuyen_de": "Chuyên đề dạy học"
                }
                mat_name = type_names.get(material_type, "Tài liệu")
                if mat_link:
                    mat_reply = [
                        f"Dạ em gửi Thầy/Cô đường dẫn tải {mat_name} Lịch sử Lớp {grade} (Bộ Kết Nối Tri Thức) ạ:\n👉 Link tải: {mat_link}\n\nThầy/Cô mở xem hoặc tải về máy tính để sử dụng nhé ạ! 😊"
                    ]
                else:
                    mat_reply = [
                        f"Dạ {mat_name} của Lịch sử Lớp {grade} (Bộ Kết Nối Tri Thức) đã có sẵn trọn bộ rồi ạ!\nEm đã ghi chú gửi thầy/cô ngay trong thư mục tổng của lớp nhé ạ! ✨"
                    ]
                self._dispatch_reply(user_id, display_name, mat_reply)
                return {"status": "material_sent", "replies": mat_reply}

        # =========================================================================
        # BƯỚC 4: SUY LUẬN & TẠO CÂU TRẢ LỜI BẰNG GEMINI MULTIMODAL + RAG FAQ
        # =========================================================================
        self._log_step(4, "SUY LUẬN AI", "Chuyển dữ liệu sang GeminiEngine (kèm Lịch sử hội thoại đa lượt & Knowledge Base)...")
        recent_history = self.state.get_recent_messages(user_id, limit=8)
        replies, analysis = self.gemini.generate_response(message_text, image_path, chat_history=recent_history)
        self._log_step(4, "SUY LUẬN AI", f"Kết quả phân tích AI: Intent={analysis.get('intent')} | IsFeedback={analysis.get('is_content_feedback')} | IsCompleted={analysis.get('is_completed')}")

        # Ghi nhận góp ý nội dung nếu có
        if analysis.get("is_content_feedback"):
            g_save = grade or analysis.get("grade_detected") or "Chung"
            self._log_step(4, "SUY LUẬN AI", f"Phát hiện góp ý nội dung giáo án Lớp {g_save}. Lưu vào Sổ tay sửa giáo án & Bắn tin Telegram.", "WARNING")
            self.state.add_content_correction(
                user_id=user_id,
                customer_name=display_name,
                grade=g_save,
                lesson_title="Chưa rõ bài",
                feedback_text=message_text
            )
            self.tele.send_content_correction_alert(
                customer_name=display_name,
                grade=g_save,
                lesson="Góp ý nội dung",
                feedback_text=message_text
            )

        # Kiểm tra hoàn thành (Khách cảm ơn, đã xong việc)
        if analysis.get("is_completed"):
            self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"Khách hàng gửi lời cảm ơn/kết thúc. Đánh dấu hội thoại RESOLVED.")
            self.state.update_conversation_status(user_id, "RESOLVED")
            self._dispatch_reply(user_id, display_name, replies)
            return {"status": "completed", "replies": replies}

        # =========================================================================
        # BƯỚC 5: KIỂM DUYỆT AN TOÀN (ESCALATION) & ĐIỀU PHỐI GỬI TIN NHẮN
        # =========================================================================
        current_unresolved = conv.get("unresolved_count", 0) + 1
        if current_unresolved >= self.escalation_threshold:
            self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"CẢNH BÁO ESCALATION: Khách hỏi lại {current_unresolved} lần! Chuyển can thiệp tay & Bắn Telegram khẩn cấp.", "ERROR")
            self.tele.send_escalation_alert(
                customer_name=display_name,
                user_id=user_id,
                issue_summary=f"Khách hỏi lại {current_unresolved} lần về lỗi/tài liệu",
                unresolved_count=current_unresolved,
                last_customer_message=message_text
            )
            self.state.update_conversation_status(user_id, "ESCALATED", unresolved_delta=1)
            self.state.set_manual_override(user_id, True)

            escalation_reply = [
                "Dạ em đã chuyển thông tin trường hợp của Thầy/Cô sang Chuyên viên Kỹ thuật chính của bên em rồi ạ! 🙏\nChuyên viên bên em sẽ nhắn tin hoặc hỗ trợ Ultraviewer trực tiếp cho Thầy/Cô ngay bây giờ nhé ạ!"
            ]
            self._dispatch_reply(user_id, display_name, escalation_reply)
            return {"status": "escalated_to_telegram", "replies": escalation_reply}

        # Gửi phản hồi bình thường & cập nhật trạng thái
        self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"AI đã tạo xong câu trả lời hoàn chỉnh ({len(replies)} tin). Bắt đầu gửi...")
        self.state.update_conversation_status(user_id, "IN_PROGRESS", unresolved_delta=1)
        if self.auto_reply:
            self._dispatch_reply(user_id, display_name, replies)

        return {"status": "replied", "replies": replies}

    def _dispatch_reply(self, user_id: str, display_name: str, replies: List[str], force_send_pc: bool = False) -> bool:
        """Gửi các tin nhắn phản hồi, ghi log CSDL và tự động gõ vào Zalo PC (tối đa 5 lần thử)."""
        from zalo_layer.zalo_automation import ZaloAutomation
        
        # 1. Ghi nhận log và gọi callbacks
        for idx, msg in enumerate(replies, 1):
            time.sleep(self.reply_delay)
            self.state.log_message(user_id, sender="shop", text=msg)
            logger.info(f"[Zalo Outgoing -> {display_name}] (Tin {idx}/{len(replies)}): {msg}")
            if self.on_reply_sent_callback:
                self.on_reply_sent_callback(user_id, display_name, msg)

        # 2. Nếu được kích hoạt gửi vào Zalo PC
        send_pc = force_send_pc or self.config.get("app", {}).get("send_to_zalo_pc", False)
        if send_pc:
            try:
                self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"Đang gửi trực tiếp vào Zalo PC cho '{display_name}' (Tối đa 5 lần thử)...")
                ok = ZaloAutomation.send_messages_to_contact(display_name, replies, delay_between=self.reply_delay, max_attempts=5)
                if not ok:
                    self._log_step(
                        5,
                        "ĐIỀU PHỐI & PHẢN HỒI",
                        f"⚠️ Gửi tin Zalo PC thất bại sau 5 lần thử. Tự động chuyển '{display_name}' sang chế độ Can thiệp tay để tránh lặp vô tận.",
                        "WARNING"
                    )
                    self.state.set_manual_override(user_id, True)
                    return False
                else:
                    self._log_step(5, "ĐIỀU PHỐI & PHẢN HỒI", f"✅ Đã gửi thành công {len(replies)} tin nhắn vào Zalo của '{display_name}'.")
                    return True
            except Exception as e:
                logger.warning(f"[Zalo PC Auto] Không thể tự động gửi Zalo PC: {e}")
                self.state.set_manual_override(user_id, True)
                return False

        return True

    def send_direct_to_zalo_pc(self, contact_name: str, messages: List[str]) -> bool:
        """Hàm công khai cho phép GUI hoặc người dùng gửi tin nhắn trực tiếp đến Zalo PC (tối đa 5 lần thử)."""
        from zalo_layer.zalo_automation import ZaloAutomation
        return ZaloAutomation.send_messages_to_contact(contact_name, messages, delay_between=self.reply_delay, max_attempts=5)

