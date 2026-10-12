import os
import re
import sqlite3
import yaml
import logging
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

warnings.filterwarnings("ignore")
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "app_data.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")

# Danh sách các Model mới nhất và phổ biến nhất từ Google AI Studio
DEFAULT_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest"
]


def get_gemini_model_version(model_name: str) -> Optional[float]:
    """
    Trích xuất số phiên bản (float) từ tên model Gemini để so sánh.
    Ví dụ:
      - 'gemini-3.7-flash' -> 3.7
      - 'gemini-3.6-flash' -> 3.6
      - 'gemini-3.5-flash' -> 3.5
      - 'gemini-3.1-flash-lite' -> 3.1
      - 'gemini-3.1-pro-preview' -> 3.1
      - 'gemini-3.0-flash' -> 3.0
      - 'gemini-2.5-flash' -> 2.5
      - 'gemini-2.0-flash' -> 2.0
      - 'gemini-1.5-flash' -> 1.5
      - 'gemini-1.0-pro', 'gemini-pro' -> 1.0
      - 'gemini-flash-latest', 'gemini-pro-latest' -> 99.0 (Luôn coi là mới nhất)
    """
    if not model_name:
        return None
    m = model_name.lower().strip()

    # 1. Trích xuất dạng x.y rõ ràng (ví dụ 3.7, 3.6, 3.1, 2.5, 2.0, 1.5)
    match_dot = re.search(r"gemini[^\d]*(\d+)\.(\d+)", m)
    if match_dot:
        major = int(match_dot.group(1))
        minor = int(match_dot.group(2))
        return major + (minor / 10.0 if minor < 10 else minor / 100.0)

    # 2. Trích xuất dạng x (ví dụ gemini-3-flash, gemini-2-pro)
    match_single = re.search(r"gemini[^\d]*(\d+)", m)
    if match_single:
        return float(match_single.group(1))

    # 3. Các model auto-update không có số phiên bản (gemini-flash-latest, gemini-pro-latest) -> gán 99.0 (mới nhất)
    if any(k in m for k in ("latest", "next", "experimental-latest")):
        return 99.0

    # 4. Model legacy không số: gemini-pro, gemini-ultra, gemini-vision
    if "gemini" in m:
        return 1.0

    return None


def is_legacy_gemini_model(model_name: str, min_version: float = 3.1) -> bool:
    """
    Kiểm tra xem model có phải là phiên bản cũ dưới ngưỡng min_version (mặc định 3.1) hay không.
    Trả về True nếu model < min_version (cần ẩn), False nếu model >= min_version (hợp lệ).
    """
    ver = get_gemini_model_version(model_name)
    if ver is None:
        return False
    return ver < min_version


class KeyManager:
    """
    Quản lý danh sách Gemini API Keys hàng loạt:
    - Thêm nhiều API Key (mỗi dòng 1 key).
    - Tự động luân chuyển (Auto-Rotate) khi bị quá Quota (429 / Resource Exhausted).
    - Kích hoạt thủ công từng Key.
    - Kiểm tra (Check) trạng thái / Quota từng key hoặc tất cả key.
    - Reset trạng thái Quota cho từng key hoặc toàn bộ danh sách.
    - Quét và lấy danh sách Models thực tế từ Google AI Studio.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._sync_initial_keys()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Khởi tạo bảng lưu trữ API Keys trong SQLite."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gemini_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT UNIQUE,
                    status TEXT DEFAULT 'AVAILABLE',
                    is_active INTEGER DEFAULT 0,
                    request_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_status_msg TEXT DEFAULT '',
                    last_checked_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _sync_initial_keys(self):
        """Đồng bộ API key từ config.yaml vào database nếu chưa có."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    single_key = cfg.get("gemini", {}).get("api_key", "").strip()
                    if single_key and single_key != "YOUR_GEMINI_API_KEY_HERE":
                        self.add_keys(single_key)
        except Exception:
            pass

    @staticmethod
    def mask_key(key: str) -> str:
        """Che bớt ký tự của API Key để hiển thị an toàn trên giao diện."""
        if not key:
            return ""
        if len(key) <= 12:
            return key[:4] + "..." + key[-3:]
        return key[:8] + "..." + key[-6:]

    def add_keys(self, raw_text: str) -> Tuple[int, int]:
        """
        Nhập danh sách API Key hàng loạt (mỗi dòng 1 key).
        Tự động lọc trùng lặp và khoảng trắng.
        Trả về: (số key mới thêm thành công, tổng số key hiện có).
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        added = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for line in lines:
                if line.startswith("#") or line == "YOUR_GEMINI_API_KEY_HERE":
                    continue
                match = re.search(r"[A-Za-z0-9_\-]{30,}", line)
                key_clean = match.group(0) if match else line.strip()

                try:
                    cursor.execute("""
                        INSERT INTO gemini_api_keys (api_key, status, is_active)
                        VALUES (?, 'AVAILABLE', 0)
                    """, (key_clean,))
                    added += 1
                except sqlite3.IntegrityError:
                    pass  # Đã tồn tại

            # Nếu chưa có key nào active -> Kích hoạt key đầu tiên
            cursor.execute("SELECT COUNT(*) FROM gemini_api_keys WHERE is_active = 1")
            active_count = cursor.fetchone()[0]
            if active_count == 0:
                cursor.execute("""
                    UPDATE gemini_api_keys 
                    SET is_active = 1, status = 'ACTIVE' 
                    WHERE id = (SELECT MIN(id) FROM gemini_api_keys WHERE status != 'INVALID')
                """)

            conn.commit()

        total = self.get_total_keys_count()
        return added, total

    def get_all_keys(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh sách API Keys."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gemini_api_keys ORDER BY is_active DESC, id ASC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["masked_key"] = self.mask_key(d["api_key"])
                result.append(d)
            return result

    def get_total_keys_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM gemini_api_keys")
            return cursor.fetchone()[0]

    def get_active_key(self) -> Optional[str]:
        """Lấy API Key đang được chọn làm active."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT api_key FROM gemini_api_keys WHERE is_active = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row["api_key"]
            
            cursor.execute("SELECT api_key FROM gemini_api_keys WHERE status != 'INVALID' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row["api_key"]
        return None

    def set_active_key(self, key_id: int) -> bool:
        """Kích hoạt thủ công một API Key làm key chính."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE gemini_api_keys SET is_active = 0, status = CASE WHEN status = 'ACTIVE' THEN 'AVAILABLE' ELSE status END")
            cursor.execute("UPDATE gemini_api_keys SET is_active = 1, status = 'ACTIVE' WHERE id = ?", (key_id,))
            conn.commit()
            
            # Cập nhật vào config.yaml
            cursor.execute("SELECT api_key FROM gemini_api_keys WHERE id = ?", (key_id,))
            row = cursor.fetchone()
            if row:
                self._update_config_file(row["api_key"])
            return True

    def _update_config_file(self, active_key: str):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                if "gemini" not in cfg:
                    cfg["gemini"] = {}
                cfg["gemini"]["api_key"] = active_key
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
        except Exception:
            pass

    def mark_quota_exceeded(self, key: str, err_msg: str = "429 Quota Exceeded"):
        """Đánh dấu một key đã hết Quota và tự động ghi log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE gemini_api_keys
                SET status = 'QUOTA_EXCEEDED',
                    is_active = 0,
                    error_count = error_count + 1,
                    last_status_msg = ?,
                    last_checked_at = CURRENT_TIMESTAMP
                WHERE api_key = ?
            """, (err_msg, key))
            conn.commit()
        logger.warning(f"[KeyManager] Key {self.mask_key(key)} đã bị đánh dấu QUOTA_EXCEEDED.")

    def mark_invalid_key(self, key: str, err_msg: str = "Invalid API Key"):
        """Đánh dấu key bị sai / không hợp lệ."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE gemini_api_keys
                SET status = 'INVALID',
                    is_active = 0,
                    error_count = error_count + 1,
                    last_status_msg = ?,
                    last_checked_at = CURRENT_TIMESTAMP
                WHERE api_key = ?
            """, (err_msg, key))
            conn.commit()
        logger.error(f"[KeyManager] Key {self.mask_key(key)} bị lỗi INVALID.")

    def record_successful_call(self, key: str):
        """Ghi nhận 1 lượt gọi thành công cho key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE gemini_api_keys
                SET request_count = request_count + 1,
                    last_checked_at = CURRENT_TIMESTAMP
                WHERE api_key = ?
            """, (key,))
            conn.commit()

    def rotate_to_next_key(self) -> Optional[str]:
        """
        Tự động chuyển sang API Key khả dụng tiếp theo khi key hiện tại hết Quota hoặc lỗi.
        Trả về API Key mới hoặc None nếu hết tất cả các key.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, api_key FROM gemini_api_keys
                WHERE status IN ('AVAILABLE', 'ACTIVE')
                ORDER BY error_count ASC, id ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                next_id, next_key = row["id"], row["api_key"]
                cursor.execute("UPDATE gemini_api_keys SET is_active = 0 WHERE is_active = 1")
                cursor.execute("UPDATE gemini_api_keys SET is_active = 1, status = 'ACTIVE' WHERE id = ?", (next_id,))
                conn.commit()
                self._update_config_file(next_key)
                logger.info(f"[KeyManager] 🔄 Đã tự động chuyển sang Key #{next_id} ({self.mask_key(next_key)}).")
                return next_key

        logger.error("[KeyManager] ⚠️ Tất cả các API Key đều đã hết Quota hoặc bị lỗi!")
        return None

    def reset_quota(self, key_id: Optional[int] = None) -> int:
        """
        Reset trạng thái Quota về AVAILABLE.
        Nếu key_id = None -> Reset toàn bộ danh sách key.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if key_id is not None:
                cursor.execute("""
                    UPDATE gemini_api_keys
                    SET status = 'AVAILABLE',
                        last_status_msg = 'Đã reset quota'
                    WHERE id = ?
                """, (key_id,))
            else:
                cursor.execute("""
                    UPDATE gemini_api_keys
                    SET status = 'AVAILABLE',
                        last_status_msg = 'Đã reset toàn bộ quota'
                    WHERE status != 'INVALID'
                """)
                cursor.execute("SELECT COUNT(*) FROM gemini_api_keys WHERE is_active = 1")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        UPDATE gemini_api_keys 
                        SET is_active = 1, status = 'ACTIVE' 
                        WHERE id = (SELECT MIN(id) FROM gemini_api_keys WHERE status != 'INVALID')
                    """)

            conn.commit()
            return cursor.rowcount

    def delete_key(self, key_id: int) -> bool:
        """Xóa 1 API Key khỏi hệ thống."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM gemini_api_keys WHERE id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0

    def check_single_key(self, key_id_or_key: Any, model_name: str = "gemini-3.6-flash") -> Tuple[bool, str]:
        """
        Kiểm tra trạng thái thực tế của 1 API Key với Google AI Studio.
        Tự động bảo vệ chỉ sử dụng model >= 3.1 để kiểm tra (tránh lỗi do model legacy).
        """
        # Nếu model_name là model cũ dưới 3.1, tự động dùng model chuẩn gemini-3.6-flash
        if not model_name or is_legacy_gemini_model(model_name, min_version=3.1):
            model_name = "gemini-3.6-flash"

        key_str = ""
        key_id = None
        is_active = False

        if isinstance(key_id_or_key, int) or str(key_id_or_key).isdigit():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, api_key, is_active FROM gemini_api_keys WHERE id = ?", (int(key_id_or_key),))
                row = cursor.fetchone()
                if row:
                    key_id = row["id"]
                    key_str = row["api_key"]
                    is_active = bool(row["is_active"])
        else:
            key_str = str(key_id_or_key).strip()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, is_active FROM gemini_api_keys WHERE api_key = ?", (key_str,))
                row = cursor.fetchone()
                if row:
                    key_id = row["id"]
                    is_active = bool(row["is_active"])

        if not key_str:
            return False, "Không tìm thấy API Key để kiểm tra."

        success = False
        msg = ""
        status_to_set = "AVAILABLE"

        try:
            from google import genai
            client = genai.Client(api_key=key_str)
            res = client.models.generate_content(
                model=model_name,
                contents="Hello, reply with 1 word: OK"
            )
            success = True
            msg = f"✅ Hoạt động tốt ({model_name})"
            status_to_set = "ACTIVE" if is_active else "AVAILABLE"
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                status_to_set = "QUOTA_EXCEEDED"
                msg = f"⚠️ Hết Quota (429): {err_str[:80]}"
            elif "400" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str or "not valid" in err_str.lower():
                status_to_set = "INVALID"
                msg = f"❌ Key không hợp lệ: {err_str[:80]}"
            elif "404" in err_str or "NOT_FOUND" in err_str:
                status_to_set = "AVAILABLE"
                msg = f"⚠️ Model '{model_name}' không hỗ trợ trên key này. Hãy chọn model khác."
                success = True
            else:
                status_to_set = "ERROR"
                msg = f"❌ Lỗi: {err_str[:80]}"

        if key_id:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE gemini_api_keys
                    SET status = ?,
                        last_status_msg = ?,
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status_to_set, msg, key_id))
                conn.commit()

        return success, msg

    def check_all_keys(self, model_name: str = "gemini-3.6-flash") -> List[Dict[str, Any]]:
        """Kiểm tra toàn bộ danh sách API Keys với model >= 3.1."""
        if not model_name or is_legacy_gemini_model(model_name, min_version=3.1):
            model_name = "gemini-3.6-flash"
        keys = self.get_all_keys()
        results = []
        for k in keys:
            ok, msg = self.check_single_key(k["id"], model_name=model_name)
            results.append({
                "id": k["id"],
                "masked_key": k["masked_key"],
                "success": ok,
                "status_msg": msg
            })
        return results

    def list_available_models(
        self,
        api_key: Optional[str] = None,
        hide_below_3_1: bool = True,
        min_version: float = 3.1,
        custom_filter: Optional[str] = None
    ) -> List[str]:
        """
        Quét và lấy danh sách các Models thực tế mà API Key có quyền sử dụng từ Google AI Studio.
        - hide_below_3_1: Nếu True, tự động ẩn các model thế hệ cũ dưới min_version (mặc định 3.1).
        - min_version: Ngưỡng phiên bản tối thiểu muốn lấy (ví dụ 3.1, 3.5, 3.6, 2.0...).
        - custom_filter: Chuỗi lọc tùy chọn (ví dụ: 'flash', 'pro', 'lite'...).
        """
        key = api_key or self.get_active_key()
        if not key:
            res = list(DEFAULT_MODELS)
            if hide_below_3_1 and min_version > 0:
                res = [m for m in res if not is_legacy_gemini_model(m, min_version=min_version)]
            if custom_filter:
                cf = custom_filter.lower().strip()
                res = [m for m in res if cf in m.lower()]
            return res or ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]

        models = []
        try:
            from google import genai
            client = genai.Client(api_key=key)
            for m in client.models.list():
                m_name = getattr(m, "name", "")
                if m_name:
                    clean_name = m_name.replace("models/", "")
                    # Chỉ lấy các model gemini sinh nội dung văn bản / multimodal, loại trừ embedding / tts / aqa
                    if "gemini" in clean_name and not any(ex in clean_name for ex in ("embedding", "aqa", "tts", "imagen", "veo")):
                        models.append(clean_name)
        except Exception as e:
            logger.warning(f"[KeyManager] Không thể quét danh sách model từ API: {e}")

        if not models:
            res = list(DEFAULT_MODELS)
            if hide_below_3_1 and min_version > 0:
                res = [m for m in res if not is_legacy_gemini_model(m, min_version=min_version)]
            if custom_filter:
                cf = custom_filter.lower().strip()
                res = [m for m in res if cf in m.lower()]
            return res or ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]

        # Lọc theo ngưỡng phiên bản min_version (mặc định 3.1)
        if hide_below_3_1 and min_version > 0:
            models = [m for m in models if not is_legacy_gemini_model(m, min_version=min_version)]

        # Lọc theo custom_filter nếu có
        if custom_filter:
            cf = custom_filter.lower().strip()
            models = [m for m in models if cf in m.lower()]

        # Đặt các model thông dụng và tối ưu nhất lên đầu
        preferred = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-pro-latest",
            "gemini-3.1-pro-preview"
        ]
        ordered = [m for m in preferred if m in models]
        for m in models:
            if m not in ordered:
                ordered.append(m)

        return ordered or ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]
