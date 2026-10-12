import os
import re
import json
import time
import yaml
import logging
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from core.key_manager import KeyManager, DEFAULT_MODELS, is_legacy_gemini_model
from core.app_paths import get_resource_path

# Tắt các cảnh báo phụ từ thư viện Google GenAI
warnings.filterwarnings("ignore")
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


def clean_chat_formatting(text: str) -> str:
    """
    Làm sạch các ký tự bảng markdown (|---|) và dấu sao (**) 
    để tin nhắn hiển thị chuẩn đoạn chat hội thoại Zalo tự nhiên, dễ đọc.
    """
    if not text:
        return ""
    
    # 1. Bỏ dấu in đậm/nghiêng thô: **chữ** -> chữ, *chữ* -> chữ
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    
    # 2. Thay thế tiêu đề markdown: ### Tiêu đề -> 📌 Tiêu đề
    text = re.sub(r'^#{1,6}\s*(.*)$', r'📌 \1', text, flags=re.MULTILINE)
    
    # 3. Chuyển đổi bảng markdown thô sang danh sách đầu mục rõ ràng
    lines = text.split('\n')
    cleaned_lines = []
    for l in lines:
        # Bỏ dòng kẻ ngang phân cách của markdown table: |:---|:---|
        if re.match(r'^\s*\|?\s*[-:]+\s*\|', l):
            continue
        # Nếu là dòng chứa dữ liệu bảng | A | B | C |
        if l.strip().startswith('|') and l.strip().endswith('|'):
            cells = [c.strip() for c in l.strip().strip('|').split('|') if c.strip()]
            if cells:
                cleaned_lines.append(' • ' + ' | '.join(cells))
        else:
            cleaned_lines.append(l)
            
    return '\n'.join(cleaned_lines).strip()


class GeminiEngine:
    """
    Bộ xử lý trung tâm Google Gemini Multimodal kết hợp Cơ sở tri thức (Tương thích Python 3.12).
    - Nguyên tắc: HỎI GÌ ĐÁP NẤY - TRỰC DIỆN - ĐÚNG TRỌNG TÂM - KHÔNG LAN MAN.
    - Định dạng tin nhắn chuẩn đoạn chat hội thoại Zalo (Không dùng cú pháp bảng Markdown thô |---|).
    - Nắm bắt ngữ cảnh đa lượt (Multi-turn Context) liền mạch, chính xác theo dòng hội thoại.
    - Chỉ trả lời ngày giờ khi khách trực tiếp hỏi ngày giờ (không tự ý chèn thừa).
    - Hỗ trợ Quản lý nhiều API Keys (Multi-Key) và Tự động luân chuyển khi hết Quota (Auto-Rotation).
    - Giới hạn tối đa 5 lần thử chống vòng lặp vô tận.
    """

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-3.6-flash",
        key_manager: Optional[KeyManager] = None,
        allow_general_chat: bool = True,
        state_manager: Optional[Any] = None
    ):
        self.key_mgr = key_manager or KeyManager()
        self.state_manager = state_manager
        
        # Nếu có truyền api_key ban đầu thì nạp vào KeyManager
        if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
            self.key_mgr.add_keys(api_key)

        self.model_name = (model_name or "gemini-3.6-flash").strip()
        if is_legacy_gemini_model(self.model_name, min_version=3.1):
            self.model_name = "gemini-3.6-flash"

        self.allow_general_chat = allow_general_chat  # True: Trò chuyện tự do + CSKH; False: Chỉ giới hạn Sử
        self.client = None
        self.persona = self._load_persona()
        self.faq_data = self._load_faq()
        self.curriculum_data = self._load_curriculum()
        
        self._init_client()

    def set_state_manager(self, state_mgr: Any):
        """Gắn StateManager để đồng bộ bộ nhớ tri thức cá nhân thời gian thực."""
        self.state_manager = state_mgr

    def _get_personal_memory_context(self) -> str:
        """
        Nạp toàn bộ bộ nhớ tri thức cá nhân từ:
        1. Mẫu kịch bản trả lời nhanh Tab 3 (script_templates: câu hỏi, câu trả lời, danh mục, file đính kèm).
        2. Sổ tay sửa giáo án (corrections: phản hồi, lỗi thực tế và cách giải quyết).
        3. Kho link Google Drive & Email cấp quyền.
        4. Quy tắc hỗ trợ kỹ thuật thực tế.
        """
        sections = []
        if not self.state_manager:
            return ""

        try:
            # 1. Tri thức từ Mẫu kịch bản Tab 3
            templates = self.state_manager.get_all_script_templates()
            if templates:
                tpl_lines = ["--- [1. MẪU KỊCH BẢN TRẢ LỜI NHANH (BỘ NHỚ TRI THỨC TAB 3)] ---"]
                for t in templates:
                    lbl = t.get("label", "")
                    cat = t.get("category", "")
                    q = t.get("trigger_question", "")
                    ans = t.get("answer_content", "")
                    files = t.get("file_paths", [])
                    f_info = f" (Đính kèm: {len(files)} file)" if files else ""
                    tpl_lines.append(f"• [Danh mục: {cat}] {lbl}:")
                    if q:
                        tpl_lines.append(f"  - Tình huống / Câu hỏi thường gặp: \"{q}\"")
                    tpl_lines.append(f"  - Nội dung trả lời chuẩn: \"{ans}\"{f_info}")
                sections.append("\n".join(tpl_lines))
        except Exception as e:
            logger.debug(f"[Gemini Memory] Lỗi nạp script templates: {e}")

        try:
            # 2. Tri thức từ Sổ tay sửa giáo án
            corrections = self.state_manager.get_all_corrections()
            if corrections:
                corr_lines = ["--- [2. SỔ TAY SỬA GIÁO ÁN & KINH NGHIỆM THỰC TẾ] ---"]
                for c in corrections[:30]:
                    cust = c.get("customer_name", "Thầy/Cô")
                    grade = c.get("grade", "")
                    fb = c.get("feedback_text", "")
                    status = c.get("status", "")
                    corr_lines.append(f"• [Lớp {grade}] Phản hồi của {cust}: \"{fb}\" -> Trạng thái: {status}")
                sections.append("\n".join(corr_lines))
        except Exception as e:
            logger.debug(f"[Gemini Memory] Lỗi nạp corrections: {e}")

        try:
            # 3. Tri thức từ Google Drive logs
            drive_logs = self.state_manager.get_all_drive_logs()
            if drive_logs:
                drive_lines = ["--- [3. KHO LINK GOOGLE DRIVE ĐÃ CẤP QUYỀN] ---"]
                for d in drive_logs[:20]:
                    grade = d.get("grade_or_level", "")
                    ltype = d.get("link_type", "")
                    link = d.get("drive_link", "")
                    drive_lines.append(f"• Lớp {grade} ({ltype}): {link}")
                sections.append("\n".join(drive_lines))
        except Exception as e:
            logger.debug(f"[Gemini Memory] Lỗi nạp drive logs: {e}")

        try:
            # 4. Tri thức từ Danh sách Khách Hàng & Khối Mua (CRM)
            customers = self.state_manager.get_all_customers_simple()
            if customers:
                crm_lines = ["--- [4. THÔNG TIN KHÁCH HÀNG & KHỐI ĐÃ MUA (CRM)] ---"]
                for c in customers[:30]:
                    c_name = c.get("name", "")
                    c_email = c.get("email", "")
                    c_phone = c.get("phone", "")
                    c_school = c.get("school", "")
                    c_grades = ", ".join(c.get("purchased_grades", [])) or "Chưa ghi nhận"
                    p_info = f" | SĐT: {c_phone}" if c_phone else ""
                    s_info = f" | Trường: {c_school}" if c_school else ""
                    crm_lines.append(f"• Khách hàng {c_name} (Email: {c_email}{p_info}{s_info}) -> Đã mua khối: [{c_grades}]")
                sections.append("\n".join(crm_lines))
        except Exception as e:
            logger.debug(f"[Gemini Memory] Lỗi nạp customer CRM: {e}")

        if sections:
            return "\n\n=== 🧠 BỘ NHỚ TRI THỨC CÁ NHÂN CỦA BẠN (PERSONAL KNOWLEDGE & MEMORY) ===\n" + "\n\n".join(sections)
        return ""

    @property
    def api_key(self) -> str:
        return self.key_mgr.get_active_key() or ""

    def set_general_chat_mode(self, enabled: bool):
        """Bật/Tắt chế độ trò chuyện mở rộng ngoài môn Lịch sử."""
        self.allow_general_chat = enabled
        logger.info(f"[Gemini] Chế độ trò chuyện mở rộng: {'BẬT (Tự do + Thời gian + CSKH)' if enabled else 'TẮT (Chỉ Sử)'}")

    def _load_persona(self) -> str:
        persona_path = get_resource_path(os.path.join("config", "persona.txt"))
        if os.path.exists(persona_path):
            with open(persona_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "Bạn là trợ lý hỗ trợ khách hàng thân thiện, lịch thiệp, xưng Em gọi Thầy/Cô."

    def _load_faq(self) -> Dict[str, Any]:
        faq_path = get_resource_path(os.path.join("knowledge_base", "troubleshooting_faq.json"))
        if os.path.exists(faq_path):
            with open(faq_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"troubleshooting_rules": []}

    def _load_curriculum(self) -> Dict[str, Any]:
        curr_path = get_resource_path(os.path.join("knowledge_base", "curriculum_matrix.json"))
        if os.path.exists(curr_path):
            with open(curr_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _init_client(self):
        """Khởi tạo Google GenAI Client với Key đang active."""
        current_key = self.key_mgr.get_active_key()
        if not current_key or current_key == "YOUR_GEMINI_API_KEY_HERE":
            logger.warning("[Gemini] Chưa có API Key hợp lệ. Đang ở chế độ Rule-based fallback.")
            self.client = None
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=current_key)
            logger.info(f"[Gemini] Khởi tạo thành công với Key {KeyManager.mask_key(current_key)} | Model: {self.model_name}")
        except Exception as e:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=current_key)
                self.client = legacy_genai.GenerativeModel(self.model_name)
                logger.info(f"[Gemini Legacy] Khởi tạo thành công với Key {KeyManager.mask_key(current_key)} | Model: {self.model_name}")
            except Exception as ex:
                logger.error(f"[Gemini] Không thể khởi tạo API: {ex}")
                self.client = None

    def set_model(self, model_name: str):
        """Đổi model AI đang sử dụng."""
        self.model_name = model_name.strip()
        self._init_client()

    def set_api_key(self, api_key: str, model_name: Optional[str] = None):
        """Thêm và kích hoạt 1 API Key mới."""
        if api_key:
            self.key_mgr.add_keys(api_key)
        if model_name:
            self.model_name = model_name
        self._init_client()

    def test_connection(self) -> Tuple[bool, str]:
        """Thử nghiệm gọi Gemini API với prompt ngắn để kiểm tra kết nối."""
        current_key = self.key_mgr.get_active_key()
        if not current_key:
            return False, "Chưa có API Key nào trong danh sách. Hãy nhập ít nhất 1 Key!"

        return self.key_mgr.check_single_key(current_key, model_name=self.model_name)

    def save_api_key_to_config(self, api_key: str) -> bool:
        """Lưu danh sách key vào CSDL và cập nhật config.yaml."""
        if not api_key:
            return False
        self.key_mgr.add_keys(api_key)
        try:
            config_path = get_resource_path(os.path.join("config", "config.yaml"))
            cfg = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}

            if "gemini" not in cfg:
                cfg["gemini"] = {}
            cfg["gemini"]["api_key"] = self.key_mgr.get_active_key() or api_key.strip()
            cfg["gemini"]["model_name"] = self.model_name

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

            self._init_client()
            return True
        except Exception as e:
            logger.error(f"[Gemini] Lỗi khi lưu config: {e}")
            return False

    def _build_system_instruction(self) -> str:
        """Tạo prompt hệ thống chuẩn xác: HỎI GÌ ĐÁP NẤY, CHUẨN ĐOẠN CHAT ZALO, KHÔNG DÙNG BẢNG MARKDOWN."""
        now = datetime.now()
        days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        vn_day = days_vn[now.weekday()]
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d/%m/%Y")

        instruction = f"""
=== QUY TẮC PHẢN HỒI TỐI THƯỢNG (BẮT BUỘC TUÂN THỦ 100%) ===
1. HỎI GÌ ĐÁP NẤY - ĐÚNG TRỌNG TÂM - KHÔNG LAN MAN:
   - Khi người dùng hỏi bất kỳ câu hỏi nào: BẮT BUỘC TRẢ LỜI ĐẦY ĐỦ, CHÍNH XÁC, RÕ RÀNG NGAY VÀO CÂU HỎI ĐÓ.
   - Trả lời đầy đủ dứt điểm xong câu hỏi của khách hàng.

2. ĐỊNH DẠNG TIN NHẮN TỰ NHIÊN (CHUẨN ĐOẠN CHAT ZALO - KHÔNG DÙNG CÚ PHÁP BẢNG MARKDOWN):
   - TUYỆT ĐỐI KHÔNG dùng cú pháp bảng Markdown thô (| Quốc gia | Dân số | hoặc |:---|:---|) vì khi nhắn qua Zalo/App chat sẽ bị hiển thị ký tự gạch đứng thô, rối mắt và rất xấu.
   - TUYỆT ĐỐI KHÔNG dùng các ký tự markdown thô như **in đậm**, ## tiêu đề, *nghiêng*.
   - HÃY TRÌNH BÀY DƯỚI DẠNG ĐOẠN CHAT HỘI THOẠI TỰ NHIÊN, KHOA HỌC:
     Sử dụng các biểu tượng phân cấp rõ ràng (👉, •, 📌, ✨) để liệt kê thông tin.
     Ví dụ mẫu:
     Dạ em gửi Thầy/Cô thông tin chi tiết ạ:

     👉 1. Việt Nam:
     • Dân số: ~100,3 triệu người
     • Ngôn ngữ chính: Tiếng Việt
     • Tỉ lệ người già (trên 65 tuổi): ~8,3% (~17,5 triệu người)

     👉 2. Ấn Độ:
     • Dân số: ~1,43 tỷ người
     • Ngôn ngữ chính: Tiếng Hindi, Tiếng Anh
     • Tỉ lệ người già (trên 65 tuổi): ~7,2% (~172 triệu người)

3. NẮM BẮT NGỮ CẢNH HỘI THOẠI ĐA LƯỢT (MULTI-TURN CONTEXT):
   - Khi có 'Lịch sử trao đổi gần nhất', bạn PHẢI đọc kỹ để hiểu toàn bộ dòng thời gian và chủ đề đang thảo luận.
   - Nếu khách nói 'bổ sung thêm...', 'những nước đã nhắc trên', 'còn cái kia thì sao', 'thế còn bài 5'... bạn PHẢI hiểu là khách đang tiếp tục câu hỏi trước đó.
   - BẮT BUỘC trả lời đúng các đối tượng/nội dung đã thảo luận ở các câu trước, KHÔNG được tự suy diễn sang Việt Nam hoặc chủ đề khác.

4. QUY TẮC VỀ THỜI GIAN:
   - Thời gian thực hệ thống hiện tại là: {time_str}, {vn_day} ngày {date_str} (Giờ Việt Nam).
   - CHỈ NÊU THỜI GIAN khi khách hàng trực tiếp HỎI VỀ THỜI GIAN (mấy giờ, thứ mấy, ngày mấy).
   - TUYỆT ĐỐI KHÔNG tự ý chèn chú thích ngày giờ vào cuối câu trả lời nếu khách không hỏi!

5. TUYỆT ĐỐI CẤM:
   - ❌ KHÔNG hỏi ngược lại người dùng khi chưa cung cấp câu trả lời (ví dụ: CẤM hỏi 'Thầy/Cô cần lớp mấy', 'Thầy/Cô đang soạn bài môn gì').
   - ❌ KHÔNG nói lan man vòng vo ('Bên em đang xây dựng kho dữ liệu...', 'Bên em sẽ soạn file Word gửi sau...').
   - ❌ KHÔNG tự ý chuyển sang chủ đề khác khi yêu cầu hiện tại của khách chưa được giải quyết xong hoàn toàn.

6. PHONG CÁCH GIAO TIẾP:
   - Xưng 'Em', gọi 'Thầy/Cô' hoặc xưng hô lịch sự, tôn trọng, ấm áp.

=== QUY TẮC KIỂM TRA TRẠNG THÁI AI & KHÓA API ===
- Khi khách hàng hoặc quản trị viên gửi câu hỏi kiểm tra tình trạng hệ thống, kiểm tra trạng thái AI, key API còn hoạt động không (ví dụ: 'Kiểm tra trạng thái AI, key api còn hoạt động không?'):
  - Trả lời xác nhận nhanh gọn, thân thiện và rõ ràng:
    Dạ em chào Thầy/Cô ạ!
    
    👉 Tình trạng hệ thống hiện tại:
    • Trạng thái AI: Đang hoạt động bình thường, phản hồi nhanh và ổn định ({self.model_name}).
    • Khóa API (API Key): Vẫn kết nối tốt, sẵn sàng hỗ trợ tra cứu và tư vấn tài liệu bất cứ lúc nào ạ! 😊

=== KIẾN THỨC KỸ THUẬT & XỬ LÝ LỖI FILE ===
- Lỗi thanh màu vàng PowerPoint -> Nhắc bấm nút 'Enable Editing' (Bật tính năng chỉnh sửa).
- Lỗi tải dở dang -> Bấm phím tắt Ctrl + J để bấm 'Tiếp tục' (Resume).
- Lỗi Google Drive -> File nặng có video cần tải về mở bằng máy tính.

=== TÀI LIỆU GIÁO ÁN LỊCH SỬ KẾT NỐI TRI THỨC 6-12 ===
{json.dumps(self.curriculum_data, ensure_ascii=False, indent=2)}
{self._get_personal_memory_context()}
"""
        return instruction

    def generate_response(
        self,
        message_text: str,
        image_path: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_attempts: int = MAX_RETRIES
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Xử lý tin nhắn và hình ảnh của khách hàng.
        - Trả về tin nhắn dạng đoạn chat hội thoại Zalo tự nhiên, không bảng thô markdown.
        - Nắm bắt ngữ cảnh đa lượt (Multi-turn Context) liền mạch.
        - Trả lời trực diện, đúng trọng tâm, giải quyết xong vấn đề.
        - Tự động luân chuyển Key tiếp theo nếu bị quá Quota (429).
        - Tự động fallback model nếu model bị 404 Not Found.
        - Giới hạn tối đa 5 lần thử chống lặp vô tận.
        """
        analysis = {
            "intent": "general_inquiry",
            "is_content_feedback": False,
            "grade_detected": "",
            "lesson_detected": "",
            "is_completed": False
        }

        # 1. Kiểm tra nhanh các từ khóa kết thúc / cảm ơn
        lower_msg = message_text.lower().strip()
        completion_words = ["cảm ơn", "cam on", "ok em", "ok shop", "được rồi", "duoc roi", "mình làm được rồi", "tuyệt vời", "tks", "thanks"]
        if any(w == lower_msg or lower_msg.startswith(w) for w in completion_words) and len(lower_msg) < 30 and not image_path:
            analysis["is_completed"] = True
            return [
                "Dạ vâng ạ! Em chúc Thầy/Cô có những tiết dạy thật thành công và nhiều niềm vui nhé! 😊❤️"
            ], analysis

        # 2. Kiểm tra phản hồi nội dung / thiếu bài
        feedback_keywords = ["sai kiến thức", "thiếu bài", "không đúng sách", "chưa đúng chương trình", "sai nội dung", "sách cánh diều", "kết nối tri thức", "chân trời"]
        if any(kw in lower_msg for kw in feedback_keywords):
            analysis["is_content_feedback"] = True
            for g in ["6", "7", "8", "9", "10", "11", "12"]:
                if f"lớp {g}" in lower_msg or f"lop {g}" in lower_msg or f"sử {g}" in lower_msg:
                    analysis["grade_detected"] = g
                    break

        # 3. Chuẩn bị prompt với Lịch sử hội thoại đa lượt rõ ràng
        prompt_content = []
        prompt_content.append(self._build_system_instruction())
        
        if chat_history and len(chat_history) > 0:
            history_text = "=== LỊCH SỬ HỘI THOẠI TRƯỚC ĐÓ (BẮT BUỘC ĐỌC ĐỂ NẮM NGỮ CẢNH) ===\n"
            for h in chat_history[-8:]:
                history_text += f"- {h['sender']}: {h['text']}\n"
            prompt_content.append(history_text)

        prompt_content.append(f"\nCâu hỏi mới nhất từ khách hàng: \"{message_text}\"\n(Hãy trả lời dưới dạng tin nhắn chat Zalo tự nhiên, rõ ràng, không dùng cú pháp bảng markdown thô)")

        opened_img = None
        if image_path and os.path.exists(image_path):
            try:
                opened_img = Image.open(image_path)
                prompt_content.append(opened_img)
                prompt_content.append("Hãy quan sát kỹ ảnh chụp màn hình này để phát hiện chính xác lỗi và hướng dẫn Thầy/Cô trực tiếp.")
            except Exception as e:
                logger.warning(f"[Gemini] Không thể mở ảnh {image_path}: {e}")

        last_error_type = None
        last_error_msg = ""

        try:
            # 4. Vòng lặp gọi API với cơ chế tự động xoay key khi quá Quota
            for attempt in range(1, max_attempts + 1):
                current_key = self.key_mgr.get_active_key()
                if not current_key:
                    logger.warning("[Gemini] Không có key khả dụng, chuyển Rule-based fallback.")
                    last_error_type = "no_key"
                    last_error_msg = "Không có API Key nào được kích hoạt trong hệ thống."
                    break

                try:
                    from google import genai
                    client = genai.Client(api_key=current_key)
                    
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=prompt_content
                    )
                    raw_text = response.text or ""

                    # Ghi nhận thành công
                    self.key_mgr.record_successful_call(current_key)

                    # Làm sạch cú pháp markdown thô nếu có
                    cleaned_text = clean_chat_formatting(raw_text)

                    # Trả về trọn vẹn 1 câu trả lời hoàn chỉnh duy nhất (không tách nhỏ gây ngắt quãng)
                    final_reply = cleaned_text.strip()
                    if not final_reply:
                        final_reply = "Dạ em chưa nhận được phản hồi từ model. Thầy/Cô thử lại giúp em nhé ạ!"
                    return [final_reply], analysis

                except Exception as e:
                    err_str = str(e)
                    last_error_msg = err_str
                    logger.warning(f"[Gemini] [Lần thử {attempt}/{max_attempts}] Lỗi gọi API với Key {KeyManager.mask_key(current_key)}: {err_str[:120]}")

                    # Trường hợp 1: Quá Quota (429 / Resource Exhausted) -> Xoay sang Key tiếp theo
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                        last_error_type = "quota"
                        logger.warning(f"[Gemini] ⚠️ Key {KeyManager.mask_key(current_key)} bị quá Quota. Đang tự động đổi sang Key khác...")
                        self.key_mgr.mark_quota_exceeded(current_key, err_str[:100])
                        new_key = self.key_mgr.rotate_to_next_key()
                        if not new_key:
                            logger.error("[Gemini] Tất cả các Key đã hết Quota!")
                            break
                        continue

                    # Trường hợp 2: Model 404 Not Found -> Tự động chuyển sang gemini-3.6-flash
                    elif "404" in err_str or "NOT_FOUND" in err_str:
                        last_error_type = "not_found"
                        logger.warning(f"[Gemini] Model '{self.model_name}' không tìm thấy (404). Tự động chuyển sang 'gemini-3.6-flash'...")
                        self.model_name = "gemini-3.6-flash"
                        continue

                    # Trường hợp 3: Key không hợp lệ (400 / 403) -> Đánh dấu INVALID và đổi key
                    elif "400" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                        last_error_type = "invalid_key"
                        self.key_mgr.mark_invalid_key(current_key, err_str[:100])
                        new_key = self.key_mgr.rotate_to_next_key()
                        if not new_key:
                            break
                        continue

                    else:
                        last_error_type = "api_error"
                        if attempt < max_attempts:
                            time.sleep(1.0)

            # Fallback sau các lần thử thất bại
            logger.error(f"[Gemini] ⚠️ Đã thử {max_attempts} lần thất bại ({last_error_type}). Chuyển sang Rule-based Knowledge Base an toàn.")
            return self._fallback_rule_based_reply(message_text, image_path, last_error_type=last_error_type, last_error_msg=last_error_msg), analysis
        finally:
            if opened_img:
                try:
                    opened_img.close()
                except Exception:
                    pass

    def _fallback_rule_based_reply(
        self,
        message_text: str,
        image_path: Optional[str] = None,
        last_error_type: Optional[str] = None,
        last_error_msg: Optional[str] = None
    ) -> List[str]:
        """Tự động trả lời theo bộ quy tắc nếu không có mạng hoặc API Key gặp sự cố/quá Quota."""
        lower = message_text.lower()

        # Kiểm tra nếu người dùng yêu cầu kiểm tra trạng thái AI / API Key / Quota
        is_status_check = any(w in lower for w in [
            "trạng thái", "trang thai", "key api", "api key", "hoạt động không", "hoat dong khong",
            "còn sống không", "con song khong", "quota", "hết hạn", "het han"
        ])

        if is_status_check or last_error_type in ("quota", "invalid_key", "no_key"):
            if last_error_type == "quota":
                return [
                    "⚠️ THÔNG BÁO TÌNH TRẠNG HỆ THỐNG AI & KHÓA API:\n\n"
                    "• Trạng thái AI: Tạm thời không thể nhận phản hồi từ máy chủ Google Gemini.\n"
                    "• Nguyên nhân lỗi: API Key đã bị QUÁ HẠN MỨC (429 Quota Exceeded / Resource Exhausted) do gửi quá nhiều yêu cầu liên tục hoặc đã sử dụng hết hạn mức miễn phí trong ngày của Google AI Studio.\n\n"
                    "• Hướng dẫn khắc phục:\n"
                    "  1. Thêm hoặc thay API Key mới: Mở Tab Cài Đặt (Tab 10) hoặc Tab Quản Lý Key (Tab 7) để thêm Key dự phòng.\n"
                    "  2. Tạm chờ: Đợi khoảng 1 - 5 phút để Google tự động mở lại hạn mức Quota.\n"
                    "  3. Nâng cấp API: Chuyển sang gói trả phí Pay-as-you-go trên Google AI Studio để không bị giới hạn số lượng tin nhắn."
                ]
            elif last_error_type == "invalid_key":
                return [
                    "⚠️ THÔNG BÁO TÌNH TRẠNG HỆ THỐNG AI & KHÓA API:\n\n"
                    "• Trạng thái AI: Không thể kết nối API Key.\n"
                    "• Nguyên nhân lỗi: Khóa API (API Key) không hợp lệ, đã bị thu hồi hoặc cấu hình sai (400/403 Invalid API Key).\n\n"
                    "• Hướng dẫn khắc phục: Vui lòng vào Tab Cài Đặt (Tab 10) để nạp và kích hoạt API Key Gemini hợp lệ."
                ]
            elif last_error_type == "no_key":
                return [
                    "⚠️ THÔNG BÁO TÌNH TRẠNG HỆ THỐNG AI & KHÓA API:\n\n"
                    "• Trạng thái AI: Chưa cấu hình API Key nào trong hệ thống.\n\n"
                    "• Hướng dẫn khắc phục: Vui lòng vào Tab Cài Đặt (Tab 10) -> Thẻ API Key để thêm và kích hoạt API Key."
                ]
            elif is_status_check:
                return [
                    "⚠️ THÔNG BÁO TÌNH TRẠNG HỆ THỐNG AI & KHÓA API:\n\n"
                    "• Trạng thái AI: Không thể kết nối đến máy chủ Google Gemini (Mất kết nối mạng hoặc phản hồi timeout).\n\n"
                    "• Hướng dẫn khắc phục: Vui lòng kiểm tra lại đường truyền Internet và thử lại sau vài giây."
                ]

        # Trả lời nhanh ngày giờ nếu không có mạng
        if any(w in lower for w in ["mấy giờ", "may gio", "thứ mấy", "thu may", "ngày mấy", "ngay may"]):
            now = datetime.now()
            days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
            return [f"Dạ bây giờ là {now.strftime('%H:%M')}, {days_vn[now.weekday()]} ngày {now.strftime('%d/%m/%Y')} ạ! 😊"]

        for rule in self.faq_data.get("troubleshooting_rules", []):
            if any(kw in lower for kw in rule.get("keywords", [])):
                rep = rule.get("sample_reply", ["Dạ bên em hỗ trợ Thầy/Cô ngay đây ạ!"])
                if isinstance(rep, list):
                    return ["\n\n".join(rep)]
                return [str(rep)]

        if image_path:
            return [
                "Dạ em đã nhận được hình ảnh của Thầy/Cô rồi ạ!\n\nNếu là lỗi mở file, Thầy/Cô bấm nút 'Enable Editing' màu vàng phía trên giúp em; còn nếu là lỗi tải dở dang Thầy/Cô bấm phím Ctrl + J để bấm 'Tiếp tục' (Resume) nhé ạ! 😊"
            ]

        return [
            "Dạ em chào Thầy/Cô ạ! Thầy/Cô đang cần em hỗ trợ giải đáp thông tin hoặc tài liệu nào nhắn em ngay nhé ạ! ✨"
        ]
