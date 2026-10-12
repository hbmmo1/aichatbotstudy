import sqlite3
import os
import json
import csv
import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from core.app_paths import get_storage_path

logger = logging.getLogger(__name__)

DB_PATH = get_storage_path("database.sqlite")

ICONS_POOL = ["✨", "⭐", "💫", "🍀", "🎁", "💎", "🌟", "📚", "🔥", "⚡"]
GREETINGS_POOL = [
    "Kính gửi Quý Thầy/Cô!",
    "Kính chào Thầy/Cô ạ!",
    "Kính gửi Thầy/Cô nhóm mình!",
    "Chào Thầy/Cô!",
    "Thông tin gửi đến Quý Thầy/Cô:"
]

def apply_anti_spam_randomizer(
    content: str,
    append_time: bool = True,
    append_random_code: bool = False,
    append_random_icon: bool = False,
    random_greeting: bool = False
) -> str:
    """
    Chống spam & chống gửi lặp Zalo bằng cách chèn thêm mốc thời gian, mã số hoặc icon ngẫu nhiên.
    Mặc định kích hoạt: Chèn mốc thời gian giờ phút (HH:MM).
    """
    result = content.strip()
    if random_greeting:
        greeting = random.choice(GREETINGS_POOL)
        result = f"{greeting}\n\n{result}"

    suffixes = []
    if append_time:
        now_str = datetime.now().strftime("%H:%M")
        suffixes.append(f"⏱ [{now_str}]")
    if append_random_code:
        rand_code = f"#{random.randint(1000, 9999)}"
        suffixes.append(rand_code)
    if append_random_icon:
        rand_icon = random.choice(ICONS_POOL)
        suffixes.append(rand_icon)

    if suffixes:
        result += "\n\n" + " ".join(suffixes)

    return result


def format_smart_timestamp(dt_input: Union[str, datetime, None]) -> str:
    """
    Định dạng thời gian thông minh theo múi giờ Việt Nam (UTC+7):
    - Nếu là hôm nay: "Hôm nay 18:20"
    - Nếu là hôm qua: "Hôm qua 18:20"
    - Nếu trong năm nay: "28/08 09:15"
    - Nếu lâu hơn: "25/08/2026 09:15"
    """
    if not dt_input:
        return datetime.now().strftime("Hôm nay %H:%M")

    if isinstance(dt_input, str):
        dt_str = dt_input.strip()
        try:
            # Xử lý chuỗi có múi giờ ISO (Z hoặc +00:00) -> chuyển sang UTC+7
            if "Z" in dt_str or "+00:00" in dt_str:
                from datetime import timezone, timedelta
                vn_tz = timezone(timedelta(hours=7))
                parsed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                dt = parsed_dt.astimezone(vn_tz).replace(tzinfo=None)
            elif "T" in dt_str:
                clean_s = dt_str[:19].replace("T", " ")
                dt = datetime.strptime(clean_s, "%Y-%m-%d %H:%M:%S")
            else:
                clean_s = dt_str[:19]
                dt = datetime.strptime(clean_s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                dt = datetime.fromisoformat(dt_str)
            except Exception:
                return dt_input
    else:
        dt = dt_input

    now = datetime.now()
    today = now.date()
    msg_date = dt.date()
    delta_days = (today - msg_date).days

    time_str = dt.strftime("%H:%M")

    if delta_days == 0:
        return f"Hôm nay {time_str}"
    elif delta_days == 1:
        return f"Hôm qua {time_str}"
    elif dt.year == now.year:
        return f"{dt.strftime('%d/%m')} {time_str}"
    else:
        return f"{dt.strftime('%d/%m/%Y')} {time_str}"


class StateManager:
    """Quản lý trạng thái khách hàng, sổ tay sửa giáo án, phân quyền Drive & Lên lịch gửi tin nhóm."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache in RAM for ultra-fast queries
            conn.execute("PRAGMA temp_store=MEMORY;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Bảng Hội thoại khách hàng
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    status TEXT DEFAULT 'PENDING',
                    unresolved_count INTEGER DEFAULT 0,
                    is_manual_override INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    last_message_text TEXT,
                    last_message_sender TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)
            
            # 2. Bảng lưu lịch sử tin nhắn chi tiết
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    sender TEXT,
                    message_text TEXT,
                    has_image INTEGER DEFAULT 0,
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY(user_id) REFERENCES conversations(user_id)
                )
            """)

            # 3. Bảng 'Sổ tay chỉnh sửa giáo án'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    customer_name TEXT,
                    grade TEXT,
                    lesson_title TEXT,
                    feedback_text TEXT,
                    status TEXT DEFAULT 'PENDING',
                    admin_notes TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 4. Bảng 'Nhật ký cấp quyền Google Drive'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drive_access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    grade_or_level TEXT,
                    link_type TEXT DEFAULT 'primary',
                    drive_link TEXT,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 5. Bảng 'Mẫu Tin Nhắn Soạn Sẵn Gửi Nhóm' (Hỗ trợ vô số mẫu linh hoạt)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_num INTEGER UNIQUE,
                    title TEXT,
                    content TEXT,
                    file_paths TEXT DEFAULT '[]',
                    is_default INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 6. Bảng 'Danh Mục Thẻ Phân Loại Nhóm Tùy Chỉnh'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 7. Bảng 'Cài Đặt Lên Lịch Gửi Tin Nhóm Tự Động'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_time TEXT,
                    template_num INTEGER DEFAULT 1,
                    tag_filter TEXT DEFAULT 'Gửi mẫu quảng cáo',
                    is_active INTEGER DEFAULT 1,
                    last_run_date TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 8. Bảng 'Nhật Ký Gửi Tin Nhóm & Chống Gửi Lặp'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_broadcast_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT,
                    tag_name TEXT,
                    template_num INTEGER,
                    message_preview TEXT,
                    file_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'COMPLETED',
                    batch_id TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 9. Bảng Mẫu kịch bản trả lời nhanh (Script Templates Tab 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    category TEXT DEFAULT 'Tư Vấn Mua',
                    trigger_question TEXT,
                    answer_content TEXT NOT NULL,
                    file_paths TEXT DEFAULT '[]',
                    shortcut_key TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # Khởi tạo 3 mẫu tin nhắn mặc định nếu chưa có
            cursor.execute("SELECT COUNT(*) as count FROM broadcast_templates")
            if cursor.fetchone()['count'] == 0:
                default_tpls = [
                    (1, "Mẫu 1: Gửi Bộ Mới Giáo Án Kèm Link Drive & File", 
                     "Dạ em gửi Thầy/Cô bộ giáo án Lịch sử Kết Nối Tri Thức mới nhất ạ!\n\n👉 Thầy/Cô check mail hoặc mở trực tiếp link tải bên dưới nhé ạ:\nhttps://drive.google.com/drive/folders/giao-an-lich-su-kntt\n\nThầy/Cô cần hỗ trợ thêm cứ nhắn em nhé ạ! 😊✨", 
                     "[]", 1),
                    (2, "Mẫu 2: Thông Báo Cập Nhật Đề Kiểm Tra & PPCT Mới", 
                     "📢 [THÔNG BÁO CẬP NHẬT]\nBộ Đề kiểm tra định kỳ & Phân phối chương trình Lịch sử 6-12 đã được cập nhật trọn bộ.\n\n👉 Kính mời Thầy/Cô tải về máy tính để sử dụng cho năm học mới ạ! 📚✨", 
                     "[]", 0),
                    (3, "Mẫu 3: Hướng Dẫn Tải & Mở Khóa File PowerPoint (Protected View)", 
                     "💡 [HƯỚNG DẪN KỸ THUẬT]\nKhi mở file PowerPoint tải về nếu thấy thanh màu vàng Protected View, Thầy/Cô bấm nút 'Enable Editing' (Bật tính năng chỉnh sửa) để mở rộng toàn màn hình nhé ạ! 😊", 
                     "[]", 0)
                ]
                for num, title, content, files, is_def in default_tpls:
                    cursor.execute("""
                        INSERT INTO broadcast_templates (template_num, title, content, file_paths, is_default)
                        VALUES (?, ?, ?, ?, ?)
                    """, (num, title, content, files, is_def))

            # Khởi tạo danh sách thẻ phân loại Zalo mặc định nếu chưa có
            cursor.execute("SELECT COUNT(*) as count FROM broadcast_tags")
            if cursor.fetchone()['count'] == 0:
                default_tags = [
                    "Gửi mẫu quảng cáo",
                    "MUA NHÓM THCS",
                    "MUA NHÓM THPT",
                    "Mua giáo án AI mới",
                    "Cần ghép THPT",
                    "Nguyễn Hữu Cảnh",
                    "Sáng kiến 2026 - 2027",
                    "chưa gửi bài",
                    "cần giải quyết"
                ]
                for t in default_tags:
                    cursor.execute("INSERT OR IGNORE INTO broadcast_tags (tag_name) VALUES (?)", (t,))

            # Khởi tạo 4 mốc giờ lịch tự động mặc định (7h, 10h, 17h, 20h) nếu chưa có
            cursor.execute("SELECT COUNT(*) as count FROM broadcast_schedules")
            if cursor.fetchone()['count'] == 0:
                default_schedules = [
                    ("07:00", 1, "Gửi mẫu quảng cáo", 1),
                    ("10:00", 1, "Gửi mẫu quảng cáo", 1),
                    ("17:00", 2, "Gửi mẫu quảng cáo", 1),
                    ("20:00", 3, "Gửi mẫu quảng cáo", 1)
                ]
                for t, tpl, tag, act in default_schedules:
                    cursor.execute("""
                        INSERT INTO broadcast_schedules (schedule_time, template_num, tag_filter, is_active)
                        VALUES (?, ?, ?, ?)
                    """, (t, tpl, tag, act))

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    category TEXT DEFAULT 'Tư Vấn Mua',
                    trigger_question TEXT,
                    answer_content TEXT NOT NULL,
                    file_paths TEXT DEFAULT '[]',
                    shortcut_key TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Khởi tạo 5 mẫu kịch bản trả lời nhanh mẫu nếu chưa có
            cursor.execute("SELECT COUNT(*) as count FROM script_templates")
            if cursor.fetchone()['count'] == 0:
                default_scripts = [
                    (
                        "📌 [Hỏi Mua Chung Nhóm 3-4 Người]",
                        "Tư Vấn Mua Nhóm",
                        "Cô ơi em mua chung 3 người có được cấp quyền theo từng mail không? Có được hỗ trợ chỉnh sửa không?",
                        "Dạ được nhé Thầy/Cô ơi! 😊\nKhi mua chung nhóm 3-4 người:\n1. Bên em sẽ cấp quyền truy cập Drive tải giáo án cho từng địa chỉ Gmail của từng Thầy/Cô riêng biệt.\n2. Tất cả các thành viên đều được bảo hành cập nhật tài liệu và hỗ trợ kỹ thuật suốt năm học.\n3. File Word và PowerPoint tải về đều được chỉnh sửa 100% không bị khóa ạ!\n\nThầy/Cô gửi em danh sách Gmail của nhóm để em kích hoạt quyền ngay nhé ạ! ✨",
                        "[]"
                    ),
                    (
                        "💡 [Hướng Dẫn Mở Khóa File PowerPoint]",
                        "Hỗ Trợ Kỹ Thuật",
                        "Mở file PowerPoint bị báo Protected View / Read-Only không sửa được thì làm sao?",
                        "Dạ Thầy/Cô xử lý nhanh theo 2 cách này là mở được ngay ạ:\n\n👉 Cách 1: Khi mở PowerPoint thấy thanh màu vàng 'Protected View', Thầy/Cô bấm nút 'Enable Editing' (Bật tính năng chỉnh sửa) ở góc trên bên phải thanh màu vàng.\n\n👉 Cách 2: Nhấp chuột phải vào file -> Chọn Properties -> Tích chọn ô 'Unblock' ở góc dưới cùng -> Bấm Apply -> OK.\n\nEm có gửi kèm hướng dẫn chi tiết để Thầy/Cô thao tác nhé ạ! 😊",
                        "[]"
                    ),
                    (
                        "💰 [Báo Giá Trọn Bộ Lịch Sử 6-12]",
                        "Báo Giá Giáo Án",
                        "Báo giá trọn bộ giáo án Lịch sử Kết Nối Tri Thức khối THCS và THPT",
                        "Dạ em gửi Thầy/Cô thông tin bảng giá ưu đãi trọn bộ Giáo án Lịch sử Kết Nối Tri Thức (KNTT) ạ:\n\n📚 Khối THCS (Lớp 6, 7, 8, 9): Giáo án Word chuẩn CV 5512 + Slide PPT sinh động + Đề kiểm tra ma trận + PPCT.\n📚 Khối THPT (Lớp 10, 11, 12): Đầy đủ bài dạy chuyên đề + Ôn thi TN THPT mới nhất.\n\n🎁 Ưu đãi đặc biệt: Tặng kèm kho tư liệu video lịch sử sắc nét và hỗ trợ cập nhật miễn phí cả năm học ạ!",
                        "[]"
                    ),
                    (
                        "🔗 [Link Tải Google Drive & Cấp Quyền]",
                        "Gửi Link Drive",
                        "Xin link Drive tải tài liệu giáo án và cách xin quyền truy cập",
                        "Dạ em gửi Thầy/Cô link Google Drive tài liệu giáo án Lịch Sử Kết Nối Tri Thức mới nhất ạ:\n\n🔗 Link Drive: https://drive.google.com/drive/folders/giao-an-lich-su-kntt\n\n👉 Thầy/Cô bấm vào link trên, nếu chưa thấy file vui lòng gửi em địa chỉ Gmail để em phân quyền ngay trong 1 phút nhé ạ! ✨",
                        "[]"
                    ),
                    (
                        "🔄 [Hỏi Đổi Sang Môn Khác Hoặc Khối Khác]",
                        "Tư Vấn Chung",
                        "Em chuyển lớp/khối khác có được đổi tài liệu sang khối mới không?",
                        "Dạ hoàn toàn được ạ! Trong năm học nếu Thầy/Cô có phân công chuyển đổi khối dạy hoặc chuyển trường, bên em sẽ hỗ trợ chuyển đổi link Drive sang khối lớp mới hoàn toàn miễn phí nhé ạ! 😊",
                        "[]"
                    )
                ]
                for lbl, cat, q, ans, f_str in default_scripts:
                    cursor.execute("""
                        INSERT INTO script_templates (label, category, trigger_question, answer_content, file_paths)
                        VALUES (?, ?, ?, ?, ?)
                    """, (lbl, cat, q, ans, f_str))

            # 5.5 Bảng Quản Lý Kho Tệp Đính Kèm Nhanh Theo Nhóm (Script File Bundles)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_file_bundles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    file_paths TEXT DEFAULT '[]',
                    sort_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. Bảng Quản Lý Khách Hàng / Thông Tin Người Dùng & Khối Mua (CRM)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT DEFAULT '',
                    school TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    purchased_grades TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Thêm mẫu khách hàng ban đầu nếu bảng trống
            cursor.execute("SELECT COUNT(*) as count FROM customers")
            if cursor.fetchone()['count'] == 0:
                default_customers = [
                    ("Cô Lê Mai Anh", "lemaianh@gmail.com", "0912345678", "THCS Chu Văn An", "Hà Nội", "Mua chung nhóm 3 người", json.dumps(["6", "7", "8", "9"])),
                    ("Thầy Trần Văn Tuấn", "tuantran.hist@gmail.com", "0987654321", "THPT Chuyên Hà Nội - Amsterdam", "Hà Nội", "Khối 10, 11 KNTT", json.dumps(["10", "11"])),
                    ("Cô Nguyễn Thị Lan", "lannguyen.thcs@gmail.com", "0905123456", "THCS Nguyễn Huệ", "Đà Nẵng", "Đã cấp quyền Drive trọn bộ", json.dumps(["6", "7", "8", "9", "10", "11", "12"]))
                ]
                for n, em, p, sch, addr, nots, gr in default_customers:
                    cursor.execute("""
                        INSERT INTO customers (name, email, phone, school, address, notes, purchased_grades)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (n, em, p, sch, addr, nots, gr))

            # 7. Bảng Quản Lý Phiên Trò Chuyện & Lịch Sử Chat (Chat Sessions & Messages)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT 'Hội thoại mới',
                    is_archived INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    sender_type TEXT NOT NULL, -- 'USER', 'AI', 'SYS'
                    sender_name TEXT DEFAULT '',
                    message_text TEXT NOT NULL,
                    img_name TEXT DEFAULT '',
                    model_name TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)

            # 8. Bảng Quản Lý Người Dùng & Đăng Nhập (Users & Authentication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT DEFAULT '',
                    role TEXT DEFAULT 'admin',
                    is_active INTEGER DEFAULT 1,
                    login_count INTEGER DEFAULT 0,
                    last_login_at TIMESTAMP DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Thêm cột cho bảng users nếu CSDL cũ chưa có
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP DEFAULT NULL;")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;")
            except Exception:
                pass

            # 8.5 Bảng Nhật Ký Đăng Nhập (User Login Logs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT NOT NULL,
                    status TEXT DEFAULT 'SUCCESS', -- 'SUCCESS' hoặc 'FAILED'
                    ip_address TEXT DEFAULT '127.0.0.1',
                    login_time TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 14. Bảng Sổ Tay Ghi Chú Nhanh & Lưu Trữ AI (Quick Notes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quick_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'Ghi Chú Nhanh',
                    sender_type TEXT DEFAULT 'AI',
                    source_session_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quick_notes_created ON quick_notes(created_at DESC);")

            cursor.execute("SELECT COUNT(*) as count FROM users")
            if cursor.fetchone()['count'] == 0:
                import hashlib
                admin_hash = hashlib.sha256("admin".encode('utf-8')).hexdigest()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, login_count)
                    VALUES (?, ?, ?, ?, 0)
                """, ("admin", admin_hash, "Quản Trị Viên (Admin)", "admin"))

            # 9. Tạo các Index tăng tốc truy vấn CSDL 10x
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_archived ON chat_sessions(is_archived, updated_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_bc_logs_group ON group_broadcast_logs(group_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_user ON message_history(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_logs_user ON user_login_logs(username, login_time);")

            # 10. Migration đồng bộ múi giờ Việt Nam (UTC+7) cho toàn bộ dữ liệu lịch sử
            cursor.execute("CREATE TABLE IF NOT EXISTS _schema_migrations (version TEXT PRIMARY KEY);")
            cursor.execute("SELECT version FROM _schema_migrations WHERE version = 'tz_vietnam_utc7_v1'")
            if not cursor.fetchone():
                try:
                    cursor.execute("UPDATE chat_messages SET created_at = datetime(created_at, '+7 hours') WHERE created_at IS NOT NULL;")
                    cursor.execute("UPDATE chat_sessions SET created_at = datetime(created_at, '+7 hours'), updated_at = datetime(updated_at, '+7 hours') WHERE created_at IS NOT NULL;")
                    cursor.execute("UPDATE conversations SET created_at = datetime(created_at, '+7 hours'), updated_at = datetime(updated_at, '+7 hours') WHERE created_at IS NOT NULL;")
                    cursor.execute("UPDATE message_history SET created_at = datetime(created_at, '+7 hours') WHERE created_at IS NOT NULL;")
                    cursor.execute("UPDATE users SET created_at = datetime(created_at, '+7 hours'), updated_at = datetime(updated_at, '+7 hours') WHERE created_at IS NOT NULL;")
                    cursor.execute("UPDATE users SET last_login_at = datetime(last_login_at, '+7 hours') WHERE last_login_at IS NOT NULL;")
                    cursor.execute("UPDATE user_login_logs SET login_time = datetime(login_time, '+7 hours') WHERE login_time IS NOT NULL;")
                    cursor.execute("INSERT INTO _schema_migrations (version) VALUES ('tz_vietnam_utc7_v1');")
                except Exception as e:
                    logger.warning(f"[DB] Lỗi migration timezone: {e}")

            conn.commit()

    # ================= QUẢN LÝ PHIÊN TRÒ CHUYỆN & LỊCH SỬ CHAT (SESSIONS & HISTORY) =================
    def get_or_create_chat_session(self, session_id: Optional[int] = None, default_title: str = "Hội thoại mới") -> Dict[str, Any]:
        """Lấy phiên trò chuyện theo ID hoặc phiên hoạt động gần nhất, nếu chưa có thì tạo mới."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)

            cursor.execute("SELECT * FROM chat_sessions WHERE is_archived = 0 ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)

            cursor.execute("INSERT INTO chat_sessions (title, is_archived) VALUES (?, 0)", (default_title,))
            new_id = cursor.lastrowid
            conn.commit()
            return {"id": new_id, "title": default_title, "is_archived": 0, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}

    def list_chat_sessions(self, is_archived: bool = False) -> List[Dict[str, Any]]:
        """Lấy danh sách các phiên trò chuyện (kèm số lượng tin nhắn)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            arch_flag = 1 if is_archived else 0
            query = """
                SELECT s.*, COUNT(m.id) as msg_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                WHERE s.is_archived = ?
                GROUP BY s.id
                ORDER BY s.updated_at DESC
            """
            cursor.execute(query, (arch_flag,))
            return [dict(r) for r in cursor.fetchall()]

    def create_chat_session(self, title: str = "Hội thoại mới") -> int:
        """Tạo một phiên trò chuyện mới theo giờ Việt Nam (UTC+7)."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_sessions (title, is_archived, created_at, updated_at) VALUES (?, 0, ?, ?)", (title.strip() or "Hội thoại mới", now_str, now_str))
            new_id = cursor.lastrowid
            conn.commit()
            return new_id

    def rename_chat_session(self, session_id: int, new_title: str) -> bool:
        """Đổi tên phiên trò chuyện."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?", (new_title.strip(), now_str, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def archive_chat_session(self, session_id: int, is_archived: bool = True) -> bool:
        """Lưu trữ hoặc bỏ lưu trữ phiên trò chuyện."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            arch_val = 1 if is_archived else 0
            cursor.execute("UPDATE chat_sessions SET is_archived = ?, updated_at = ? WHERE id = ?", (arch_val, now_str, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_chat_session(self, session_id: int) -> bool:
        """Xóa hoàn toàn phiên trò chuyện và tin nhắn liên quan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_chat_sessions(self, is_archived: Optional[bool] = None) -> int:
        """Xóa toàn bộ các phiên trò chuyện."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if is_archived is None:
                cursor.execute("DELETE FROM chat_messages")
                cursor.execute("DELETE FROM chat_sessions")
            else:
                arch_val = 1 if is_archived else 0
                cursor.execute("DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE is_archived = ?)", (arch_val,))
                cursor.execute("DELETE FROM chat_sessions WHERE is_archived = ?", (arch_val,))
            count = cursor.rowcount
            conn.commit()
            return count

    def add_chat_message(
        self,
        session_id: int,
        sender_type: str,
        sender_name: str,
        message_text: str,
        img_name: Optional[str] = None,
        model_name: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> int:
        """Thêm tin nhắn vào phiên trò chuyện với mốc thời gian Việt Nam (UTC+7)."""
        if not created_at:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (session_id, sender_type, sender_name, message_text, img_name, model_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, sender_type, sender_name, message_text, img_name, model_name, created_at))
            msg_id = cursor.lastrowid

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Cập nhật title tự động nếu là câu hỏi đầu tiên
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages WHERE session_id = ?", (session_id,))
            cnt = cursor.fetchone()['count']
            if cnt <= 2 and sender_type == "USER":
                clean_title = message_text.strip().replace("\n", " ")[:35]
                if clean_title:
                    cursor.execute("UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?", (clean_title, now_str, session_id))
            else:
                cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_str, session_id))
            conn.commit()
            return msg_id

    def get_chat_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """Lấy toàn bộ tin nhắn của một phiên trò chuyện theo thứ tự thời gian."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
            return [dict(r) for r in cursor.fetchall()]

    def clear_session_messages(self, session_id: int) -> bool:
        """Xóa toàn bộ tin nhắn của một phiên trò chuyện."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_str, session_id))
            conn.commit()
            return True

    # ================= QUẢN LÝ HỘI THOẠI & TIN NHẮN ZALO =================
    def get_or_create_conversation(self, user_id: str, display_name: str = "Thầy/Cô") -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            cursor.execute("""
                INSERT INTO conversations (user_id, display_name, status, unresolved_count, updated_at)
                VALUES (?, ?, 'PENDING', 0, CURRENT_TIMESTAMP)
            """, (user_id, display_name))
            conn.commit()
            return {
                "user_id": user_id,
                "display_name": display_name,
                "status": "PENDING",
                "unresolved_count": 0,
                "is_manual_override": 0,
                "tags": "[]"
            }

    def update_conversation_status(self, user_id: str, status: str, unresolved_delta: int = 0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations
                SET status = ?,
                    unresolved_count = CASE WHEN ? = 'RESOLVED' THEN 0 ELSE MAX(0, unresolved_count + ?) END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (status, status, unresolved_delta, user_id))
            conn.commit()

    def set_manual_override(self, user_id: str, override: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations
                SET is_manual_override = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (1 if override else 0, user_id))
            conn.commit()

    def log_message(self, user_id: str, sender: str, text: str, has_image: bool = False, image_path: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_history (user_id, sender, message_text, has_image, image_path)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, sender, text, 1 if has_image else 0, image_path))
            
            cursor.execute("""
                UPDATE conversations
                SET last_message_text = ?,
                    last_message_sender = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (text, sender, user_id))
            conn.commit()

    def get_recent_messages(self, user_id: str, limit: int = 8) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sender, message_text 
                FROM message_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            messages = []
            for r in reversed(rows):
                s_name = "Khách hàng" if r["sender"] == "customer" else "AI Trợ lý"
                messages.append({"sender": s_name, "text": r["message_text"]})
            return messages

    # ================= SỔ TAY SỬA GIÁO ÁN =================
    def add_content_correction(self, user_id: str, customer_name: str, grade: str, lesson_title: str, feedback_text: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO content_corrections (user_id, customer_name, grade, lesson_title, feedback_text, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (user_id, customer_name, grade, lesson_title, feedback_text))
            
            cursor.execute("SELECT tags FROM conversations WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            tags = json.loads(row['tags']) if row and row['tags'] else []
            if "CẦN_SỬA_NỘI_DUNG" not in tags:
                tags.append("CẦN_SỬA_NỘI_DUNG")
                cursor.execute("UPDATE conversations SET tags = ? WHERE user_id = ?", (json.dumps(tags), user_id))
            
            conn.commit()

    def get_all_corrections(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute("SELECT * FROM content_corrections WHERE status = ? ORDER BY created_at DESC", (status_filter,))
            else:
                cursor.execute("SELECT * FROM content_corrections ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def update_correction_status(self, correction_id: int, status: str, admin_notes: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE content_corrections
                SET status = ?, admin_notes = ?
                WHERE id = ?
            """, (status, admin_notes, correction_id))
            conn.commit()

    # ================= QUẢN LÝ EMAIL & PHÂN QUYỀN DRIVE =================
    def log_drive_access(self, email: str, grade_or_level: str, link_type: str, drive_link: str, user_id: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO drive_access_logs (email, grade_or_level, link_type, drive_link, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (email.strip().lower(), grade_or_level, link_type, drive_link, user_id))
            conn.commit()

    def get_email_count_for_link(self, grade_or_level: str, link_type: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT email) as count FROM drive_access_logs
                WHERE grade_or_level = ? AND link_type = ?
            """, (grade_or_level, link_type))
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_all_drive_logs(self, grade_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if grade_filter:
                cursor.execute("SELECT * FROM drive_access_logs WHERE grade_or_level = ? ORDER BY created_at DESC", (grade_filter,))
            else:
                cursor.execute("SELECT * FROM drive_access_logs ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def export_emails_to_file(self, file_path: str, grade_or_level: Optional[str] = None, link_type: Optional[str] = None) -> int:
        logs = self.get_all_drive_logs()
        filtered = []
        for l in logs:
            if grade_or_level and l['grade_or_level'] != grade_or_level:
                continue
            if link_type and l['link_type'] != link_type:
                continue
            filtered.append(l)

        if file_path.endswith(".csv"):
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Email", "Khối/Lớp", "Loại Link", "Đường Dẫn Drive", "Thời Gian Cấp"])
                for r in filtered:
                    writer.writerow([r['id'], r['email'], r['grade_or_level'], r['link_type'], r['drive_link'], r['created_at']])
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                unique_emails = sorted(list(set(r['email'] for r in filtered if r['email'])))
                for em in unique_emails:
                    f.write(f"{em}\n")

        return len(filtered)

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # ================= QUẢN LÝ NHIỀU MẪU TIN NHẮN GỬI NHÓM (BROADCAST TEMPLATES) =================
    def get_all_templates(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM broadcast_templates ORDER BY template_num ASC")
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d['files'] = json.loads(d['file_paths']) if d.get('file_paths') else []
                results.append(d)
            return results

    def get_template(self, template_num: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM broadcast_templates WHERE template_num = ?", (template_num,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d['files'] = json.loads(d['file_paths']) if d.get('file_paths') else []
                return d
            return None

    def get_default_template(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM broadcast_templates WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT * FROM broadcast_templates ORDER BY template_num ASC LIMIT 1")
                row = cursor.fetchone()
            if row:
                d = dict(row)
                d['files'] = json.loads(d['file_paths']) if d.get('file_paths') else []
                return d
            return None

    def get_random_active_template(self) -> Optional[Dict[str, Any]]:
        """Lấy ngẫu nhiên 1 trong các Mẫu tin nhắn đang kích hoạt."""
        all_tpls = self.get_all_templates()
        if not all_tpls:
            return None
        return random.choice(all_tpls)

    def save_template(self, template_num: int, title: str, content: str, file_paths: List[str], is_default: bool = False):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if is_default:
                cursor.execute("UPDATE broadcast_templates SET is_default = 0")

            cursor.execute("""
                INSERT INTO broadcast_templates (template_num, title, content, file_paths, is_default, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(template_num) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    file_paths = excluded.file_paths,
                    is_default = excluded.is_default,
                    updated_at = CURRENT_TIMESTAMP
            """, (template_num, title, content, json.dumps(file_paths, ensure_ascii=False), 1 if is_default else 0))
            conn.commit()

    def add_new_template(self, title: str = "", content: str = "", file_paths: List[str] = None) -> int:
        """Tạo thêm 1 Mẫu tin nhắn mới (Tự tăng template_num)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(template_num) as max_num FROM broadcast_templates")
            row = cursor.fetchone()
            next_num = (row['max_num'] or 0) + 1
            t_title = title.strip() if title else f"Mẫu {next_num}: Tin nhắn mới"
            t_content = content.strip() if content else "Dạ em chào Thầy/Cô! Em gửi tài liệu tham khảo ạ. 😊"
            files_json = json.dumps(file_paths or [], ensure_ascii=False)
            cursor.execute("""
                INSERT INTO broadcast_templates (template_num, title, content, file_paths, is_default)
                VALUES (?, ?, ?, ?, 0)
            """, (next_num, t_title, t_content, files_json))
            conn.commit()
            return next_num

    def delete_template(self, template_num: int) -> bool:
        """Xóa 1 Mẫu tin nhắn (Nếu có ít nhất 2 mẫu trở lên)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM broadcast_templates")
            if cursor.fetchone()['count'] <= 1:
                return False
            cursor.execute("DELETE FROM broadcast_templates WHERE template_num = ?", (template_num,))
            conn.commit()
            return True

    # ================= QUẢN LÝ THẺ PHÂN LOẠI NHÓM (BROADCAST TAGS) =================
    def get_all_tags(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tag_name FROM broadcast_tags ORDER BY id ASC")
            return [row['tag_name'] for row in cursor.fetchall()]

    def add_broadcast_tag(self, tag_name: str) -> bool:
        tag_clean = tag_name.strip()
        if not tag_clean:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO broadcast_tags (tag_name) VALUES (?)", (tag_clean,))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_broadcast_tag(self, old_tag_name: str, new_tag_name: str) -> bool:
        """Đổi tên / Cập nhật Thẻ phân loại Zalo."""
        old_clean = old_tag_name.strip()
        new_clean = new_tag_name.strip()
        if not old_clean or not new_clean:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE broadcast_tags SET tag_name = ? WHERE tag_name = ?", (new_clean, old_clean))
                cursor.execute("UPDATE broadcast_schedules SET tag_filter = ? WHERE tag_filter = ?", (new_clean, old_clean))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_broadcast_tag(self, tag_name: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM broadcast_tags WHERE tag_name = ?", (tag_name.strip(),))
            conn.commit()
            return True

    # ================= CÀI ĐẶT LÊN LỊCH TỰ ĐỘNG (BROADCAST SCHEDULES) =================
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM broadcast_schedules ORDER BY schedule_time ASC")
            return [dict(row) for row in cursor.fetchall()]

    def save_schedule(self, schedule_time: str, template_num: int, tag_filter: str = "Gửi mẫu quảng cáo", is_active: bool = True):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO broadcast_schedules (schedule_time, template_num, tag_filter, is_active)
                VALUES (?, ?, ?, ?)
            """, (schedule_time.strip(), template_num, tag_filter.strip(), 1 if is_active else 0))
            conn.commit()

    def update_schedule_status(self, schedule_id: int, is_active: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE broadcast_schedules SET is_active = ? WHERE id = ?", (1 if is_active else 0, schedule_id))
            conn.commit()

    def update_schedule_last_run(self, schedule_id: int, date_str: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE broadcast_schedules SET last_run_date = ? WHERE id = ?", (date_str, schedule_id))
            conn.commit()

    def delete_schedule(self, schedule_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM broadcast_schedules WHERE id = ?", (schedule_id,))
            conn.commit()

    # ================= LỊCH SỬ GỬI TIN & CHỐNG GỬI LẶP / CHECK THIẾU =================
    def is_group_sent_in_batch(self, group_name: str, batch_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM group_broadcast_logs
                WHERE group_name = ? AND batch_id = ? AND status = 'COMPLETED'
            """, (group_name.strip(), batch_id))
            row = cursor.fetchone()
            return row['count'] > 0 if row else False

    def is_group_sent_today(self, group_name: str, tag_name: str) -> bool:
        today_str = datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM group_broadcast_logs
                WHERE group_name = ? AND tag_name = ? AND status = 'COMPLETED' AND date(created_at) = ?
            """, (group_name.strip(), tag_name.strip(), today_str))
            row = cursor.fetchone()
            return row['count'] > 0 if row else False

    def log_group_broadcast(
        self,
        group_name: str,
        tag_name: str,
        template_num: int,
        message_preview: str,
        file_count: int = 0,
        status: str = "COMPLETED",
        batch_id: str = ""
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO group_broadcast_logs (group_name, tag_name, template_num, message_preview, file_count, status, batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (group_name.strip(), tag_name.strip(), template_num, message_preview[:120], file_count, status, batch_id))
            conn.commit()

    def get_broadcast_logs(self, limit: int = 60) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM group_broadcast_logs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def audit_broadcast_batch(self, tag_name: str = "", batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Kiểm tra rà soát đợt gửi tin: Đếm số lượng thành công, thất bại, trùng lặp và tính toàn vẹn.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM group_broadcast_logs"
            params = []
            if batch_id:
                query += " WHERE batch_id = ?"
                params.append(batch_id)
            elif tag_name:
                query += " WHERE tag_name = ?"
                params.append(tag_name)
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, params)
            logs = [dict(r) for r in cursor.fetchall()]

            total_entries = len(logs)
            successful_groups = set()
            duplicates = []
            failed = []

            for l in logs:
                g_name = l['group_name']
                if l['status'] == 'COMPLETED':
                    if g_name in successful_groups:
                        duplicates.append(g_name)
                    else:
                        successful_groups.add(g_name)
                else:
                    failed.append(g_name)

            is_perfect = len(duplicates) == 0 and len(failed) == 0 and len(successful_groups) > 0

            return {
                "total_logs": total_entries,
                "sent_count": len(successful_groups),
                "duplicate_count": len(duplicates),
                "failed_count": len(failed),
                "duplicate_groups": duplicates,
                "failed_groups": failed,
                "is_perfect": is_perfect,
                "summary_text": (
                    f"✅ CHUẨN XÁC 100%: Đã gửi thành công {len(successful_groups)} nhóm. KHÔNG BỊ GỬI LẶP HOẶC BỎ SÓT NHÓM NÀO!"
                    if is_perfect else
                    f"⚠️ Báo cáo: {len(successful_groups)} nhóm thành công, {len(duplicates)} gửi lặp, {len(failed)} lỗi."
                )
            }

    def delete_broadcast_log_entry(self, group_name: str, created_at: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if created_at:
                cursor.execute("DELETE FROM group_broadcast_logs WHERE group_name = ? AND created_at = ?", (group_name.strip(), created_at))
            else:
                cursor.execute("DELETE FROM group_broadcast_logs WHERE group_name = ?", (group_name.strip(),))
            conn.commit()

    def clear_broadcast_history(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM group_broadcast_logs")
            conn.commit()

    def delete_conversation_by_name(self, display_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM conversations WHERE display_name = ?", (display_name.strip(),))
            row = cursor.fetchone()
            if row:
                u_id = row['user_id']
                cursor.execute("DELETE FROM message_history WHERE user_id = ?", (u_id,))
                cursor.execute("DELETE FROM conversations WHERE user_id = ?", (u_id,))
            else:
                cursor.execute("DELETE FROM conversations WHERE display_name = ?", (display_name.strip(),))
            conn.commit()

    def clear_all_chat_history(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM message_history")
            cursor.execute("DELETE FROM conversations")
            conn.commit()

    # ================= QUẢN LÝ MẪU KỊCH BẢN TRẢ LỜI NHANH (SCRIPT TEMPLATES) =================
    def get_all_script_templates(self, search_query: str = "", category_filter: str = "") -> List[Dict[str, Any]]:
        """Lấy danh sách các mẫu kịch bản, có hỗ trợ tìm kiếm và lọc theo danh mục."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM script_templates WHERE 1=1"
            params = []

            if category_filter and category_filter != "Tất Cả Danh Mục":
                query += " AND category = ?"
                params.append(category_filter)

            if search_query:
                s = f"%{search_query.strip()}%"
                query += " AND (label LIKE ? OR trigger_question LIKE ? OR answer_content LIKE ?)"
                params.extend([s, s, s])

            query += " ORDER BY sort_order ASC, id DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item['file_paths'] = json.loads(item['file_paths'])
                except Exception:
                    item['file_paths'] = []
                results.append(item)
            return results

    def get_script_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết 1 mẫu kịch bản theo ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM script_templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item['file_paths'] = json.loads(item['file_paths'])
            except Exception:
                item['file_paths'] = []
            return item

    def save_script_template(
        self,
        label: str,
        trigger_question: str,
        answer_content: str,
        file_paths: List[str],
        category: str = "Tư Vấn Mua",
        template_id: Optional[int] = None
    ) -> int:
        """Thêm mới hoặc cập nhật 1 mẫu kịch bản."""
        f_json = json.dumps(file_paths, ensure_ascii=False)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if template_id:
                cursor.execute("""
                    UPDATE script_templates
                    SET label = ?, category = ?, trigger_question = ?, answer_content = ?, file_paths = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (label, category, trigger_question, answer_content, f_json, template_id))
                conn.commit()
                return template_id
            else:
                cursor.execute("""
                    INSERT INTO script_templates (label, category, trigger_question, answer_content, file_paths)
                    VALUES (?, ?, ?, ?, ?)
                """, (label, category, trigger_question, answer_content, f_json))
                conn.commit()
                return cursor.lastrowid

    def delete_script_template(self, template_id: int) -> bool:
        """Xóa 1 mẫu kịch bản."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_templates WHERE id = ?", (template_id,))
            conn.commit()
            return cursor.rowcount > 0

    def duplicate_script_template(self, template_id: int) -> int:
        """Nhân bản 1 mẫu kịch bản."""
        item = self.get_script_template(template_id)
        if not item:
            return 0
        new_label = f"{item['label']} (Bản Sao)"
        return self.save_script_template(
            label=new_label,
            trigger_question=item.get('trigger_question', ''),
            answer_content=item.get('answer_content', ''),
            file_paths=item.get('file_paths', []),
            category=item.get('category', 'Tư Vấn Mua')
        )

    def get_script_categories(self) -> List[str]:
        """Lấy danh sách các danh mục kịch bản hiện có."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM script_templates ORDER BY category ASC")
            rows = cursor.fetchall()
            cats = [r['category'] for r in rows if r['category']]
            default_cats = ["Hỗ Trợ Kỹ Thuật", "Tư Vấn Mua Nhóm", "Báo Giá Giáo Án", "Gửi Link Drive", "Tư Vấn Chung"]
            for dc in default_cats:
                if dc not in cats:
                    cats.append(dc)
            if "Hỗ Trợ Kỹ Thuật" in cats:
                cats.remove("Hỗ Trợ Kỹ Thuật")
                cats.insert(0, "Hỗ Trợ Kỹ Thuật")
            return cats

    def rename_script_category(self, old_name: str, new_name: str) -> bool:
        """Đổi tên 1 danh mục và cập nhật toàn bộ mẫu kịch bản thuộc danh mục đó."""
        if not old_name or not new_name or old_name.strip() == new_name.strip():
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE script_templates
                SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE category = ?
            """, (new_name.strip(), old_name.strip()))
            conn.commit()
            return cursor.rowcount >= 0

    def delete_script_category(self, cat_name: str, fallback_cat: str = "Tư Vấn Chung") -> bool:
        """Xóa 1 danh mục và chuyển các mẫu kịch bản thuộc danh mục đó sang danh mục mặc định."""
        if not cat_name:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE script_templates
                SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE category = ?
            """, (fallback_cat.strip(), cat_name.strip()))
            conn.commit()
            return True

    # ================= XUẤT (EXPORT) & NẠP (IMPORT) MẪU KỊCH BẢN & DANH MỤC =================
    def export_script_templates_to_file(self, file_path: str, category_filter: Optional[str] = None) -> int:
        """Xuất danh sách mẫu kịch bản (kèm danh mục, câu hỏi, câu trả lời, files) ra file JSON hoặc CSV."""
        templates = self.get_all_script_templates(category_filter=category_filter or "")
        ext = os.path.splitext(file_path)[1].lower()

        data_to_export = []
        for t in templates:
            data_to_export.append({
                "label": t.get("label", ""),
                "category": t.get("category", "Tư Vấn Chung"),
                "trigger_question": t.get("trigger_question", ""),
                "answer_content": t.get("answer_content", ""),
                "file_paths": t.get("file_paths", [])
            })

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        if ext == ".csv":
            import csv
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["label", "category", "trigger_question", "answer_content", "file_paths"])
                writer.writeheader()
                for row in data_to_export:
                    row_copy = dict(row)
                    row_copy["file_paths"] = json.dumps(row_copy["file_paths"], ensure_ascii=False)
                    writer.writerow(row_copy)
        else:
            # Mặc định file JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_templates": len(data_to_export),
                    "templates": data_to_export
                }, f, ensure_ascii=False, indent=2)

        return len(data_to_export)

    def import_script_templates_from_file(self, file_path: str, mode: str = "merge") -> Dict[str, Any]:
        """
        Nạp danh sách mẫu kịch bản từ file JSON hoặc CSV.
        - mode: 'merge' (Gộp thêm vào danh sách hiện tại) hoặc 'replace' (Xóa hết rồi nạp mới).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        items_to_import = []

        if ext == ".csv":
            import csv
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    f_paths = []
                    if row.get("file_paths"):
                        try:
                            f_paths = json.loads(row["file_paths"])
                        except Exception:
                            f_paths = [p.strip() for p in row["file_paths"].split(";") if p.strip()]
                    items_to_import.append({
                        "label": row.get("label", "Mẫu Nạp Mới"),
                        "category": row.get("category", "Tư Vấn Chung"),
                        "trigger_question": row.get("trigger_question", ""),
                        "answer_content": row.get("answer_content", ""),
                        "file_paths": f_paths
                    })
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    items_to_import = data
                elif isinstance(data, dict):
                    items_to_import = data.get("templates", [])

        if not items_to_import:
            return {"imported_count": 0, "mode": mode}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if mode == "replace":
                cursor.execute("DELETE FROM script_templates")

            imported_count = 0
            for item in items_to_import:
                lbl = item.get("label", "").strip()
                if not lbl:
                    continue
                cat = item.get("category", "Tư Vấn Chung").strip() or "Tư Vấn Chung"
                q = item.get("trigger_question", "").strip()
                ans = item.get("answer_content", "").strip()
                f_list = item.get("file_paths", [])
                if not isinstance(f_list, list):
                    f_list = []
                f_json = json.dumps(f_list, ensure_ascii=False)

                cursor.execute("""
                    INSERT INTO script_templates (label, category, trigger_question, answer_content, file_paths)
                    VALUES (?, ?, ?, ?, ?)
                """, (lbl, cat, q, ans, f_json))
                imported_count += 1

            conn.commit()

        return {"imported_count": imported_count, "mode": mode}

    def export_script_categories_to_file(self, file_path: str) -> int:
        """Xuất danh sách các danh mục kịch bản ra file JSON hoặc TXT."""
        cats = self.get_script_categories()
        ext = os.path.splitext(file_path)[1].lower()
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        if ext == ".txt":
            with open(file_path, "w", encoding="utf-8") as f:
                for c in cats:
                    f.write(c + "\n")
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "categories": cats
                }, f, ensure_ascii=False, indent=2)

        return len(cats)

    def import_script_categories_from_file(self, file_path: str) -> int:
        """Nạp danh sách các danh mục kịch bản từ file JSON hoặc TXT."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        cats_to_import = []

        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    c = line.strip()
                    if c and c not in cats_to_import:
                        cats_to_import.append(c)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cats_to_import = data
                elif isinstance(data, dict):
                    cats_to_import = data.get("categories", [])

        current_cats = self.get_script_categories()
        added_count = 0
        for c in cats_to_import:
            c_clean = str(c).strip()
            if c_clean and c_clean not in current_cats:
                # Tạo mẫu đại diện cho danh mục mới để lưu vào DB
                self.save_script_template(
                    label=f"📝 [Mẫu Mới - {c_clean}]",
                    trigger_question="",
                    answer_content="Dạ em gửi Thầy/Cô thông tin ạ! 😊",
                    file_paths=[],
                    category=c_clean
                )
                current_cats.append(c_clean)
                added_count += 1

        return added_count

    # ================= QUẢN LÝ KHO TỆP ĐÍNH KÈM NHANH THEO NHÓM (SCRIPT FILE BUNDLES) =================
    def get_all_file_bundles(self) -> List[Dict[str, Any]]:
        """Lấy tất cả các nhóm file đính kèm nhanh, sắp xếp theo sort_order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM script_file_bundles WHERE is_active = 1 ORDER BY sort_order ASC, id ASC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    raw_paths = json.loads(item.get('file_paths') or '[]')
                    # Chuẩn hóa danh sách file
                    norm_files = []
                    for f in raw_paths:
                        if isinstance(f, str):
                            norm_files.append({"path": f, "name": os.path.basename(f), "checked": True})
                        elif isinstance(f, dict):
                            norm_files.append({
                                "path": f.get("path", ""),
                                "name": f.get("name") or os.path.basename(f.get("path", "")),
                                "checked": bool(f.get("checked", True))
                            })
                    item['file_paths'] = norm_files
                except Exception:
                    item['file_paths'] = []
                results.append(item)
            return results

    def save_file_bundle(
        self,
        group_name: str,
        file_paths: List[Any],
        bundle_id: Optional[int] = None,
        sort_order: int = 0
    ) -> int:
        """Tạo mới hoặc cập nhật 1 nhóm tệp đính kèm."""
        f_json = json.dumps(file_paths, ensure_ascii=False)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bundle_id:
                cursor.execute("""
                    UPDATE script_file_bundles
                    SET group_name = ?, file_paths = ?, sort_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (group_name.strip(), f_json, sort_order, bundle_id))
                conn.commit()
                return bundle_id
            else:
                cursor.execute("""
                    INSERT INTO script_file_bundles (group_name, file_paths, sort_order)
                    VALUES (?, ?, ?)
                """, (group_name.strip(), f_json, sort_order))
                conn.commit()
                return cursor.lastrowid

    def delete_file_bundle(self, bundle_id: int):
        """Xóa hẳn 1 nhóm tệp đính kèm."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_file_bundles WHERE id = ?", (bundle_id,))
            conn.commit()

    def update_file_bundles_order(self, bundle_ids: List[int]):
        """Cập nhật thứ tự hiển thị sắp xếp của các nhóm tệp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for idx, b_id in enumerate(bundle_ids):
                cursor.execute("UPDATE script_file_bundles SET sort_order = ? WHERE id = ?", (idx, b_id))
            conn.commit()

    def export_file_bundles_to_file(self, file_path: str) -> int:
        """Xuất danh sách các nhóm tệp đính kèm ra file JSON."""
        bundles = self.get_all_file_bundles()
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"script_file_bundles": bundles}, f, ensure_ascii=False, indent=2)
        return len(bundles)

    def import_file_bundles_from_file(self, file_path: str, mode: str = "merge") -> Dict[str, Any]:
        """Nạp danh sách các nhóm tệp đính kèm từ file JSON."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        bundles_to_import = data.get("script_file_bundles", data) if isinstance(data, dict) else data
        if not isinstance(bundles_to_import, list):
            raise ValueError("Định dạng file không hợp lệ.")

        imported_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if mode == "replace":
                cursor.execute("DELETE FROM script_file_bundles")

            for item in bundles_to_import:
                if not isinstance(item, dict):
                    continue
                g_name = item.get("group_name", "").strip()
                if not g_name:
                    continue
                f_list = item.get("file_paths", [])
                if not isinstance(f_list, list):
                    f_list = []
                f_json = json.dumps(f_list, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO script_file_bundles (group_name, file_paths, sort_order)
                    VALUES (?, ?, ?)
                """, (g_name, f_json, item.get("sort_order", 0)))
                imported_count += 1
            conn.commit()
        return {"imported_count": imported_count, "mode": mode}

    # ================= QUẢN LÝ THÔNG TIN KHÁCH HÀNG & KHỐI MUA (CRM) =================
    def get_customers(
        self,
        search_query: str = "",
        grade_filter: Any = "",
        sort_by: str = "created_desc",
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lấy danh sách khách hàng có tìm kiếm, lọc khối mua (hỗ trợ 1 khối, nhiều khối hoặc combo), sắp xếp và phân trang.
        Trả về (danh_sách_khách_hàng, tổng_số_bản_ghi).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []

            if search_query and search_query.strip():
                kw = f"%{search_query.strip().lower()}%"
                conditions.append("(LOWER(name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(school) LIKE ? OR LOWER(notes) LIKE ?)")
                params.extend([kw, kw, kw, kw, kw])

            if grade_filter:
                if isinstance(grade_filter, (list, tuple, set)):
                    g_list = [str(g).replace("Lớp", "").replace("lớp", "").strip() for g in grade_filter if str(g).strip()]
                    if g_list:
                        sub_conds = []
                        for g in g_list:
                            sub_conds.append("purchased_grades LIKE ?")
                            params.append(f"%\"{g}\"%")
                        conditions.append("(" + " OR ".join(sub_conds) + ")")
                elif isinstance(grade_filter, str) and grade_filter.strip() and grade_filter != "Tất Cả Khối":
                    gf = grade_filter.strip()
                    if "," in gf or ";" in gf:
                        import re
                        raw_parts = [p.replace("Lớp", "").replace("lớp", "").strip() for p in re.split(r"[,;]+", gf) if p.strip()]
                        if raw_parts:
                            sub_conds = []
                            for g in raw_parts:
                                sub_conds.append("purchased_grades LIKE ?")
                                params.append(f"%\"{g}\"%")
                            conditions.append("(" + " OR ".join(sub_conds) + ")")
                    elif gf == "K6789 (Khối THCS)":
                        conditions.append("(purchased_grades LIKE '%6%' OR purchased_grades LIKE '%7%' OR purchased_grades LIKE '%8%' OR purchased_grades LIKE '%9%' OR purchased_grades LIKE '%K6789%')")
                    elif gf == "K101112 (Khối THPT)":
                        conditions.append("(purchased_grades LIKE '%10%' OR purchased_grades LIKE '%11%' OR purchased_grades LIKE '%12%' OR purchased_grades LIKE '%K101112%')")
                    elif gf == "K6-12 (Trọn Bộ)":
                        conditions.append("(purchased_grades LIKE '%6%' AND purchased_grades LIKE '%12%')")
                    else:
                        clean_g = gf.replace("Lớp", "").replace("lớp", "").strip()
                        conditions.append("purchased_grades LIKE ?")
                        params.append(f"%\"{clean_g}\"%")

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            # Đếm tổng số bản ghi phù hợp
            count_sql = f"SELECT COUNT(*) as total FROM customers {where_clause}"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()['total']

            # Sắp xếp
            sort_map = {
                "created_desc": "created_at DESC",
                "created_asc": "created_at ASC",
                "name_asc": "name ASC",
                "name_desc": "name DESC",
                "email_asc": "email ASC"
            }
            order_by = sort_map.get(sort_by, "created_at DESC")

            # Phân trang
            offset = max(0, (page - 1) * page_size)
            query_sql = f"""
                SELECT * FROM customers
                {where_clause}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            query_params = list(params) + [page_size, offset]
            cursor.execute(query_sql, query_params)

            customers = []
            for row in cursor.fetchall():
                c_dict = dict(row)
                try:
                    c_dict['purchased_grades'] = json.loads(c_dict.get('purchased_grades') or '[]')
                except Exception:
                    c_dict['purchased_grades'] = []
                customers.append(c_dict)

            return customers, total_count

    def get_all_customers_simple(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ khách hàng để phục vụ AI Memory & Export nhanh."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers ORDER BY created_at DESC")
            items = []
            for row in cursor.fetchall():
                c_dict = dict(row)
                try:
                    c_dict['purchased_grades'] = json.loads(c_dict.get('purchased_grades') or '[]')
                except Exception:
                    c_dict['purchased_grades'] = []
                items.append(c_dict)
            return items

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            if not row:
                return None
            c_dict = dict(row)
            try:
                c_dict['purchased_grades'] = json.loads(c_dict.get('purchased_grades') or '[]')
            except Exception:
                c_dict['purchased_grades'] = []
            return c_dict

    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if not email:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE LOWER(email) = ?", (email.strip().lower(),))
            row = cursor.fetchone()
            if not row:
                return None
            c_dict = dict(row)
            try:
                c_dict['purchased_grades'] = json.loads(c_dict.get('purchased_grades') or '[]')
            except Exception:
                c_dict['purchased_grades'] = []
            return c_dict

    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        if not phone or not phone.strip():
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE phone = ?", (phone.strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            c_dict = dict(row)
            try:
                c_dict['purchased_grades'] = json.loads(c_dict.get('purchased_grades') or '[]')
            except Exception:
                c_dict['purchased_grades'] = []
            return c_dict

    def save_customer(
        self,
        name: str,
        email: str,
        phone: str = "",
        school: str = "",
        address: str = "",
        notes: str = "",
        purchased_grades: Optional[List[str]] = None,
        customer_id: Optional[int] = None,
        overwrite_on_duplicate: bool = True
    ) -> Tuple[bool, str, int]:
        """
        Lưu hoặc cập nhật thông tin khách hàng.
        Kiểm tra trùng Email và SĐT.
        Trả về (thành_công, thông_báo, id_khách_hàng).
        """
        if not name or not name.strip():
            return False, "Vui lòng nhập họ và tên khách hàng!", 0
        if not email or not email.strip() or "@" not in email:
            return False, "Vui lòng nhập địa chỉ Email hợp lệ!", 0

        clean_name = name.strip()
        clean_email = email.strip().lower()
        clean_phone = phone.strip()
        clean_school = school.strip()
        clean_address = address.strip()
        clean_notes = notes.strip()
        grades_json = json.dumps(purchased_grades or [], ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Nếu đang cập nhật theo ID cụ thể
            if customer_id:
                # Kiểm tra email có bị trùng với người khác không
                cursor.execute("SELECT id FROM customers WHERE LOWER(email) = ? AND id != ?", (clean_email, customer_id))
                if cursor.fetchone():
                    return False, f"Email '{clean_email}' đã được sử dụng bởi khách hàng khác!", customer_id

                cursor.execute("""
                    UPDATE customers
                    SET name = ?, email = ?, phone = ?, school = ?, address = ?, notes = ?, purchased_grades = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (clean_name, clean_email, clean_phone, clean_school, clean_address, clean_notes, grades_json, customer_id))
                conn.commit()
                return True, f"Đã cập nhật thông tin khách hàng '{clean_name}' thành công!", customer_id

            # 2. Nếu là tạo mới -> Kiểm tra trùng Email
            cursor.execute("SELECT * FROM customers WHERE LOWER(email) = ?", (clean_email,))
            existing = cursor.fetchone()
            if existing:
                exist_id = existing['id']
                if overwrite_on_duplicate:
                    # Gộp khối mua (Merge grades) nếu đã có
                    try:
                        old_grades = json.loads(existing['purchased_grades'] or '[]')
                    except Exception:
                        old_grades = []
                    merged_grades = list(set(old_grades + (purchased_grades or [])))
                    merged_grades.sort()

                    merged_phone = clean_phone or existing['phone']
                    merged_school = clean_school or existing['school']
                    merged_address = clean_address or existing['address']
                    merged_notes = clean_notes or existing['notes']

                    cursor.execute("""
                        UPDATE customers
                        SET name = ?, phone = ?, school = ?, address = ?, notes = ?, purchased_grades = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (clean_name, merged_phone, merged_school, merged_address, merged_notes, json.dumps(merged_grades, ensure_ascii=False), exist_id))
                    conn.commit()
                    return True, f"Email đã tồn tại! Đã tự động bổ sung/cập nhật thông tin cho khách hàng '{clean_name}'.", exist_id
                else:
                    return False, f"Email '{clean_email}' đã tồn tại trong hệ thống!", exist_id

            # 3. Thêm mới hoàn toàn
            cursor.execute("""
                INSERT INTO customers (name, email, phone, school, address, notes, purchased_grades)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (clean_name, clean_email, clean_phone, clean_school, clean_address, clean_notes, grades_json))
            conn.commit()
            new_id = cursor.lastrowid
            return True, f"Đã thêm mới khách hàng '{clean_name}' thành công!", new_id

    def delete_customer(self, customer_id: int) -> bool:
        """Xóa 1 khách hàng theo ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            conn.commit()
            return cursor.rowcount > 0

    def batch_import_customers(self, customer_list: List[Dict[str, Any]], on_duplicate: str = "merge") -> Tuple[int, int]:
        """
        Nhập hàng loạt danh sách khách hàng.
        on_duplicate: 'merge' (gộp thông tin & khối mua), 'skip' (bỏ qua), 'overwrite' (ghi đè).
        Trả về (số_lượng_thêm_mới, số_lượng_cập_nhật).
        """
        added_cnt = 0
        updated_cnt = 0

        for item in customer_list:
            name = item.get("name", "").strip()
            email = item.get("email", "").strip().lower()
            if not name or not email or "@" not in email:
                continue

            phone = item.get("phone", "").strip()
            school = item.get("school", "").strip()
            address = item.get("address", "").strip()
            notes = item.get("notes", "").strip()
            grades = item.get("purchased_grades", [])
            if isinstance(grades, str):
                try:
                    grades = json.loads(grades)
                except Exception:
                    grades = [g.strip() for g in grades.replace(",", ";").split(";") if g.strip()]

            existing = self.get_customer_by_email(email)
            if existing:
                if on_duplicate == "skip":
                    continue
                # Merge or overwrite
                old_grades = existing.get("purchased_grades", [])
                merged_grades = list(set(old_grades + grades))
                merged_grades.sort()
                self.save_customer(
                    name=name,
                    email=email,
                    phone=phone or existing.get("phone", ""),
                    school=school or existing.get("school", ""),
                    address=address or existing.get("address", ""),
                    notes=notes or existing.get("notes", ""),
                    purchased_grades=merged_grades if on_duplicate == "merge" else grades,
                    customer_id=existing['id']
                )
                updated_cnt += 1
            else:
                self.save_customer(
                    name=name,
                    email=email,
                    phone=phone,
                    school=school,
                    address=address,
                    notes=notes,
                    purchased_grades=grades
                )
                added_cnt += 1

        return added_cnt, updated_cnt

    def export_customers_to_file(self, file_path: str, grade_filter: str = "") -> int:
        """Xuất danh sách khách hàng ra file CSV hoặc JSON."""
        customers, total = self.get_customers(grade_filter=grade_filter, page=1, page_size=100000)
        ext = os.path.splitext(file_path)[1].lower()

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        if ext == ".csv":
            import csv
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                fields = ["name", "email", "phone", "school", "address", "purchased_grades", "notes", "created_at"]
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for c in customers:
                    row = {
                        "name": c.get("name", ""),
                        "email": c.get("email", ""),
                        "phone": c.get("phone", ""),
                        "school": c.get("school", ""),
                        "address": c.get("address", ""),
                        "purchased_grades": ", ".join(c.get("purchased_grades", [])),
                        "notes": c.get("notes", ""),
                        "created_at": c.get("created_at", "")
                    }
                    writer.writerow(row)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(customers),
                    "customers": customers
                }, f, ensure_ascii=False, indent=2)

        return len(customers)

    def import_customers_from_file(self, file_path: str, on_duplicate: str = "merge") -> Tuple[int, int]:
        """Nạp danh sách khách hàng từ file CSV hoặc JSON."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        items_to_import = []

        if ext == ".csv":
            import csv
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    g_raw = row.get("purchased_grades", "")
                    g_list = [g.strip() for g in str(g_raw).replace(",", ";").split(";") if g.strip()]
                    items_to_import.append({
                        "name": row.get("name", "").strip(),
                        "email": row.get("email", "").strip(),
                        "phone": row.get("phone", "").strip(),
                        "school": row.get("school", "").strip(),
                        "address": row.get("address", "").strip(),
                        "notes": row.get("notes", "").strip(),
                        "purchased_grades": g_list
                    })
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    items_to_import = data
                elif isinstance(data, dict):
                    items_to_import = data.get("customers", [])

        return self.batch_import_customers(items_to_import, on_duplicate=on_duplicate)

    # ================= QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG & ĐĂNG NHẬP (USERS & AUTH) =================
    @staticmethod
    def hash_password(password: str) -> str:
        """Băm mật khẩu bằng thuật toán SHA-256."""
        import hashlib
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def authenticate_user(self, username: str, password: str, ip_address: str = "127.0.0.1") -> Optional[Dict[str, Any]]:
        """
        Xác thực tài khoản và mật khẩu đăng nhập.
        Tự động ghi nhận số lần đăng nhập, mốc thời gian đăng nhập cuối và lưu log vào user_login_logs.
        """
        u_clean = username.strip()
        p_clean = password.strip()
        if not u_clean or not p_clean:
            return None
        p_hash = self.hash_password(p_clean)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND is_active = 1", (u_clean,))
            row = cursor.fetchone()
            if not row:
                # Ghi log đăng nhập thất bại (không tìm thấy tài khoản)
                cursor.execute("""
                    INSERT INTO user_login_logs (user_id, username, status, ip_address)
                    VALUES (NULL, ?, 'FAILED', ?)
                """, (u_clean, ip_address))
                conn.commit()
                return None

            u_data = dict(row)
            # Kiểm tra mật khẩu (hỗ trợ cả hash SHA256 và fallback plain text)
            if u_data.get("password_hash") == p_hash or u_data.get("password_hash") == p_clean:
                user_id = u_data["id"]
                # Cập nhật số lần đăng nhập & mốc thời gian đăng nhập cuối cùng
                cursor.execute("""
                    UPDATE users
                    SET login_count = COALESCE(login_count, 0) + 1,
                        last_login_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                
                # Ghi log đăng nhập thành công
                cursor.execute("""
                    INSERT INTO user_login_logs (user_id, username, status, ip_address)
                    VALUES (?, ?, 'SUCCESS', ?)
                """, (user_id, u_clean, ip_address))
                conn.commit()

                # Lấy lại thông tin user đã cập nhật
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                updated_row = cursor.fetchone()
                return dict(updated_row) if updated_row else u_data
            else:
                # Ghi log đăng nhập thất bại (sai mật khẩu)
                cursor.execute("""
                    INSERT INTO user_login_logs (user_id, username, status, ip_address)
                    VALUES (?, ?, 'FAILED', ?)
                """, (u_data["id"], u_clean, ip_address))
                conn.commit()
                return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Lấy danh sách toàn bộ người dùng kèm số lần đăng nhập và lần đăng nhập cuối."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, role, is_active, login_count, last_login_at, created_at, updated_at
                FROM users
                ORDER BY id ASC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def create_user(self, username: str, password: str, full_name: str = "", role: str = "admin") -> int:
        """Tạo tài khoản người dùng mới."""
        u_clean = username.strip()
        if not u_clean or not password.strip():
            raise ValueError("Tên đăng nhập và mật khẩu không được để trống.")
        p_hash = self.hash_password(password.strip())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role, login_count)
                VALUES (?, ?, ?, ?, 0)
            """, (u_clean, p_hash, full_name.strip(), role.strip()))
            conn.commit()
            return cursor.lastrowid

    def update_user_info(self, user_id: int, full_name: str, role: str, new_password: Optional[str] = None) -> bool:
        """Sửa thông tin tài khoản người dùng (tên hiển thị, vai trò, mật khẩu mới nếu có)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Kiểm tra nếu hạ quyền admin duy nhất
            if role != "admin":
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
                admin_count = cursor.fetchone()['count']
                cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
                target = cursor.fetchone()
                if target and target['role'] == 'admin' and admin_count <= 1:
                    raise ValueError("Không thể hạ quyền tài khoản Admin duy nhất của hệ thống!")

            if new_password and new_password.strip():
                p_hash = self.hash_password(new_password.strip())
                cursor.execute("""
                    UPDATE users
                    SET full_name = ?, role = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (full_name.strip(), role.strip(), p_hash, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET full_name = ?, role = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (full_name.strip(), role.strip(), user_id))
            conn.commit()
            return cursor.rowcount > 0

    def change_user_password(self, username: str, new_password: str) -> bool:
        """Đổi mật khẩu cho người dùng theo username."""
        if not new_password.strip():
            raise ValueError("Mật khẩu mới không được để trống.")
        p_hash = self.hash_password(new_password.strip())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(username) = LOWER(?)
            """, (p_hash, username.strip()))
            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Xóa tài khoản người dùng (không cho phép xóa nếu chỉ còn 1 admin)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
            admin_count = cursor.fetchone()['count']
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            target_u = cursor.fetchone()
            if target_u and target_u['role'] == 'admin' and admin_count <= 1:
                raise ValueError("Không thể xóa tài khoản Admin duy nhất của hệ thống!")
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_login_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lấy danh sách nhật ký các lần đăng nhập gần nhất."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, username, status, ip_address, login_time
                FROM user_login_logs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def clear_login_logs(self) -> bool:
        """Xóa toàn bộ lịch sử đăng nhập."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_login_logs")
            conn.commit()
            return True
    # ================= SAO LƯU & PHỤC HỒI DỮ LIỆU TOÀN BỘ HỆ THỐNG (BACKUP & RESTORE) =================
    def export_full_database_backup(self) -> Dict[str, Any]:
        """
        Xuất toàn bộ dữ liệu của mọi bảng trong CSDL SQLite và cấu hình lưu trữ ra dict chuẩn JSON.
        Bao gồm: CRM khách hàng, kịch bản, mẫu tin gửi nhóm, sổ tay sửa giáo án, lịch sử chat, phân quyền drive, cấu hình.
        """
        tables = [
            "conversations",
            "message_history",
            "content_corrections",
            "drive_access_logs",
            "broadcast_templates",
            "broadcast_tags",
            "broadcast_schedules",
            "group_broadcast_logs",
            "script_templates",
            "script_file_bundles",
            "customers",
            "chat_sessions",
            "chat_messages",
            "users",
            "user_login_logs"
        ]
        
        db_dump = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for t in tables:
                try:
                    cursor.execute(f"SELECT * FROM {t}")
                    rows = [dict(r) for r in cursor.fetchall()]
                    db_dump[t] = rows
                except Exception as e:
                    logger.warning(f"[Backup] Không thể đọc bảng {t}: {e}")
                    db_dump[t] = []

        # Đọc các file JSON cấu hình lưu trữ
        storage_dump = {}
        settings_p = get_storage_path("app_settings.json")
        if os.path.exists(settings_p):
            try:
                with open(settings_p, "r", encoding="utf-8") as f:
                    storage_dump["app_settings"] = json.load(f)
            except Exception:
                pass

        links_p = get_storage_path("quick_links.json")
        if os.path.exists(links_p):
            try:
                with open(links_p, "r", encoding="utf-8") as f:
                    storage_dump["quick_links"] = json.load(f)
            except Exception:
                pass

        return {
            "app": "AI_ZALO_CSKH",
            "app_name": "⚡ Hệ Thống AI Zalo CSKH & Quản Lý Giáo Án Lịch Sử",
            "version": "2.0",
            "exported_at": datetime.now().isoformat(),
            "exported_timestamp": int(time.time()),
            "database": db_dump,
            "storage_files": storage_dump
        }

    def import_full_database_backup(self, backup_data: Dict[str, Any], merge_mode: bool = False) -> Tuple[bool, str, Dict[str, int]]:
        """
        Nhập / Phục hồi dữ liệu từ bản sao lưu JSON vào CSDL SQLite một cách an toàn và tự động tương thích cấu trúc bảng.
        - merge_mode: False (ghi đè / làm sạch và nạp lại), True (chỉ thêm mới / cập nhật).
        """
        if not isinstance(backup_data, dict):
            return False, "Dữ liệu bản sao lưu không hợp lệ (không phải định dạng JSON Dictionary).", {}

        db_data = backup_data.get("database")
        if not db_data or not isinstance(db_data, dict):
            return False, "Bản sao lưu không chứa cấu trúc dữ liệu 'database'.", {}

        counts = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                for table_name, rows in db_data.items():
                    if not isinstance(rows, list) or not rows:
                        counts[table_name] = 0
                        continue

                    # Kiểm tra xem bảng có tồn tại trong CSDL không
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if not cursor.fetchone():
                        continue

                    # Lấy danh sách các cột thực tế của bảng trong CSDL hiện tại
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    actual_cols = set([r[1] for r in cursor.fetchall()])
                    if not actual_cols:
                        continue

                    if not merge_mode:
                        try:
                            cursor.execute(f"DELETE FROM {table_name}")
                        except Exception:
                            pass

                    inserted_count = 0
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        # Lọc các trường khớp với cột thực tế
                        valid_keys = [k for k in row.keys() if k in actual_cols]
                        if not valid_keys:
                            continue

                        col_str = ", ".join(valid_keys)
                        placeholders = ", ".join(["?"] * len(valid_keys))
                        vals = []
                        for k in valid_keys:
                            v = row[k]
                            if isinstance(v, (list, dict)):
                                v = json.dumps(v, ensure_ascii=False)
                            vals.append(v)

                        cursor.execute(f"INSERT OR REPLACE INTO {table_name} ({col_str}) VALUES ({placeholders})", vals)
                        inserted_count += 1

                    counts[table_name] = inserted_count

                conn.commit()

                # Phục hồi storage files nếu có
                sf = backup_data.get("storage_files", {})
                if "quick_links" in sf and isinstance(sf["quick_links"], dict):
                    try:
                        with open(get_storage_path("quick_links.json"), "w", encoding="utf-8") as f:
                            json.dump(sf["quick_links"], f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                return True, "Phục hồi toàn bộ CSDL và cấu hình thành công!", counts
            except Exception as e:
                conn.rollback()
                logger.error(f"[Backup] Lỗi phục hồi CSDL: {e}")
                return False, f"Lỗi trong quá trình phục hồi: {e}", counts

    # ================= QUẢN LÝ SỔ TAY GHI CHÚ NHANH & LƯU TRỮ AI (QUICK NOTES) =================
    def add_quick_note(
        self,
        content: str,
        title: str = "",
        category: str = "Ghi Chú Nhanh",
        sender_type: str = "AI",
        session_id: Optional[int] = None
    ) -> int:
        """Lưu một mẩu ghi chú/câu trả lời AI vào Sổ Tay Ghi Chú."""
        c_clean = content.strip()
        if not c_clean:
            return 0
        if not title:
            # Tự động trích xuất tiêu đề ngắn gọn từ câu đầu tiên
            first_line = c_clean.split("\n")[0].strip()
            title = first_line[:45] + ("..." if len(first_line) > 45 else "")
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO quick_notes (title, content, category, sender_type, source_session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, c_clean, category, sender_type, session_id, now_str, now_str))
            conn.commit()
            return cursor.lastrowid

    def get_all_quick_notes(self, search_kw: str = "", category: str = "") -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh sách ghi chú với bộ lọc tìm kiếm và danh mục."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM quick_notes WHERE 1=1"
            params = []
            if search_kw:
                query += " AND (title LIKE ? OR content LIKE ?)"
                kw_param = f"%{search_kw.strip()}%"
                params.extend([kw_param, kw_param])
            if category and category not in ("Tất Cả", "Tất cả", "ALL"):
                query += " AND category = ?"
                params.append(category)
            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def update_quick_note(self, note_id: int, title: str, content: str, category: str = "Ghi Chú Nhanh") -> bool:
        """Cập nhật nội dung/tiêu đề của một ghi chú."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE quick_notes
                SET title = ?, content = ?, category = ?, updated_at = ?
                WHERE id = ?
            """, (title.strip(), content.strip(), category.strip(), now_str, note_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_quick_note(self, note_id: int) -> bool:
        """Xóa 1 ghi chú khỏi sổ tay."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quick_notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_quick_notes(self) -> bool:
        """Xóa sạch toàn bộ ghi chú."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quick_notes")
            conn.commit()
            return True



