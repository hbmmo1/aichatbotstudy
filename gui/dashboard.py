import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import json
import copy
import os
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from core.file_searcher import LocalFileSearcher
from zalo_layer.zalo_automation import ZaloAutomation
from core.key_manager import KeyManager, DEFAULT_MODELS, is_legacy_gemini_model, get_gemini_model_version
from core.broadcast_scheduler import BroadcastScheduler
from core.state_manager import format_smart_timestamp
from core.app_paths import get_resource_path, get_storage_path, get_app_dir
from core.drive_share_mockup import render_drive_share_image
from core.telegram_notifier import TelegramNotifier
from PIL import Image, ImageTk

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)

# Danh sách các tùy chọn bộ lọc phiên bản Model Gemini cho Admin
GEMINI_VERSION_FILTER_OPTIONS = [
    "⭐ Chỉ lấy Gemini 3.1 trở lên (>= 3.1) [Mặc Định - Khuyên Dùng]",
    "🚀 Chỉ lấy Gemini 3.5 trở lên (>= 3.5)",
    "🔥 Chỉ lấy Gemini 3.6 trở lên (>= 3.6)",
    "⚡ Chỉ lấy Gemini 3.7 trở lên (>= 3.7)",
    "💡 Chỉ lấy Gemini 3.0 trở lên (>= 3.0)",
    "🌐 Lấy từ Gemini 2.0 trở lên (>= 2.0)",
    "📋 Lấy tất cả các phiên bản (Bao gồm Legacy)"
]


def parse_gemini_min_version(val: Any) -> float:
    """Trích xuất ngưỡng phiên bản tối thiểu float từ chuỗi cấu hình."""
    if not val:
        return 3.1
    s = str(val).lower().strip()
    if "tất cả" in s or "all" in s:
        return 0.0
    import re
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return 3.1
    return 3.1


# Catalog thông tin chi tiết các model Gemini chính thức
MODEL_CATALOG = {
    "gemini-3.6-flash": ("v3.6 Flash (Khuyên Dùng)", "⚡ Siêu Nhanh (0.3s)", "Tối ưu nhất cho Chat Zalo, tự nhiên, đọc ảnh chụp lỗi chuẩn xác.", "⭐ KHUYÊN DÙNG"),
    "gemini-3.7-flash": ("v3.7 Flash Mới Nhất", "🚀 Rất Nhanh (0.5s)", "Thế hệ mới nhất của Google, sáng tạo cao, tư duy đa phương thức.", "🔥 MỚI NHẤT"),
    "gemini-flash-latest": ("Flash Auto-Update", "⚡ Siêu Nhanh", "Tự động trỏ tới bản Flash mới nhất và ổn định nhất từ Google.", "🔄 TỰ ĐỘNG"),
    "gemini-3.5-flash": ("v3.5 Flash", "⚡ Siêu Nhanh (0.4s)", "Bản Flash 3.5 ổn định cao cho tác vụ CSKH doanh nghiệp.", "🛡️ ỔN ĐỊNH"),
    "gemini-3.1-flash-lite": ("v3.1 Flash Lite", "💨 Cực Nhanh (0.2s)", "Bản siêu nhẹ, tiết kiệm tối đa quota/token khi gửi tin hàng loạt.", "💡 TIẾT KIỆM"),
    "gemini-pro-latest": ("Pro Latest", "🧠 Chuyên Sâu (1.2s)", "Phân tích tài liệu phức tạp, đọc hiểu giáo án dài & PPCT nặng.", "🧠 CHUYÊN SÂU"),
    "gemini-3.1-pro-preview": ("v3.1 Pro Preview", "🔬 Chuyên Sâu (1.5s)", "Bản thử nghiệm Pro với năng lực suy luận sư phạm chuyên sâu.", "🔬 THỬ NGHIỆM")
}


# Danh mục các khối link đính kèm nhanh
QUICK_LINK_GRADES = [
    "Khối 6", "Khối 7", "Khối 8", "Khối 9", "Khối 10", "Khối 11", "Khối 12", "Link THCS", "Link THPT"
]

DEFAULT_QUICK_LINKS = {
    "Khối 6": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop6-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop6-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop6-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop6-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt6-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop6-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop6-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop6-group3", "note": "", "checked": False}
    ],
    "Khối 7": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop7-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop7-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop7-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop7-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt7-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop7-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop7-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop7-group3", "note": "", "checked": False}
    ],
    "Khối 8": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop8-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop8-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop8-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop8-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt8-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop8-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop8-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop8-group3", "note": "", "checked": False}
    ],
    "Khối 9": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop9-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop9-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop9-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop9-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt9-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop9-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop9-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop9-group3", "note": "", "checked": False}
    ],
    "Khối 10": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop10-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop10-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop10-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop10-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt10-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop10-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop10-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop10-group3", "note": "", "checked": False}
    ],
    "Khối 11": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop11-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop11-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop11-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop11-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt11-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop11-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop11-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop11-group3", "note": "", "checked": False}
    ],
    "Khối 12": [
        {"id": "link1", "name": "Link 1 (Chính)", "url": "https://drive.google.com/drive/folders/kntt-lop12-main", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/kntt-lop12-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/kntt-lop12-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/kntt-lop12-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (PPCT & Đề)", "url": "https://drive.google.com/drive/folders/kntt12-ppct", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Zalo CSKH)", "url": "https://zalo.me/g/history-lop12-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Zalo Trao Đổi)", "url": "https://zalo.me/g/history-lop12-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Zalo Tài Liệu)", "url": "https://zalo.me/g/history-lop12-group3", "note": "", "checked": False}
    ],
    "Link THCS": [
        {"id": "link1", "name": "Link 1 (Toàn Bộ THCS 6-9)", "url": "https://drive.google.com/drive/folders/thcs-ketnoi-all-primary", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/thcs-ketnoi-all-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/thcs-ketnoi-all-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/thcs-ketnoi-all-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (Kho Tài Liệu THCS)", "url": "https://drive.google.com/drive/folders/thcs-ketnoi-all-docs", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Nhóm Zalo THCS)", "url": "https://zalo.me/g/history-thcs-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Nhóm Zalo Giáo Viên THCS)", "url": "https://zalo.me/g/history-thcs-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Nhóm Zalo Giáo Án THCS)", "url": "https://zalo.me/g/history-thcs-group3", "note": "", "checked": False}
    ],
    "Link THPT": [
        {"id": "link1", "name": "Link 1 (Toàn Bộ THPT 10-12)", "url": "https://drive.google.com/drive/folders/thpt-ketnoi-all-primary", "note": "", "checked": False},
        {"id": "link2", "name": "Link 2 (Dự phòng 1)", "url": "https://drive.google.com/drive/folders/thpt-ketnoi-all-backup1", "note": "", "checked": False},
        {"id": "link3", "name": "Link 3 (Dự phòng 2)", "url": "https://drive.google.com/drive/folders/thpt-ketnoi-all-backup2", "note": "", "checked": False},
        {"id": "link4", "name": "Link 4 (Dự phòng 3)", "url": "https://drive.google.com/drive/folders/thpt-ketnoi-all-backup3", "note": "", "checked": False},
        {"id": "link5", "name": "Link 5 (Kho Tài Liệu THPT)", "url": "https://drive.google.com/drive/folders/thpt-ketnoi-all-docs", "note": "", "checked": False},
        {"id": "group1", "name": "Link Group 1 (Nhóm Zalo THPT)", "url": "https://zalo.me/g/history-thpt-group1", "note": "", "checked": False},
        {"id": "group2", "name": "Link Group 2 (Nhóm Zalo Giáo Viên THPT)", "url": "https://zalo.me/g/history-thpt-group2", "note": "", "checked": False},
        {"id": "group3", "name": "Link Group 3 (Nhóm Zalo Giáo Án THPT)", "url": "https://zalo.me/g/history-thpt-group3", "note": "", "checked": False}
    ]
}


_ACTIVE_TOASTS = []


class ToastNotification(tk.Toplevel):
    """Modern floating Toast notification widget styled with Tailwind aesthetics and dynamic auto-sizing."""
    def __init__(self, master, title: str, message: str, toast_type: str = "success", duration_ms: int = 3500):
        global _ACTIVE_TOASTS
        _ACTIVE_TOASTS = [t for t in _ACTIVE_TOASTS if t.winfo_exists()]
        while len(_ACTIVE_TOASTS) >= 3:
            oldest = _ACTIVE_TOASTS.pop(0)
            try:
                oldest.destroy()
            except Exception:
                pass

        super().__init__(master)
        _ACTIVE_TOASTS.append(self)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        is_light = False
        if hasattr(master, "current_theme"):
            is_light = master.current_theme in ("tailwind_light", "light_theme", "light")

        if is_light:
            colors = {
                "success": {"bg": "#f0fdf4", "border": "#22c55e", "icon": "✅", "fg": "#14532d", "accent": "#15803d"},
                "error":   {"bg": "#fef2f2", "border": "#ef4444", "icon": "❌", "fg": "#7f1d1d", "accent": "#b91c1c"},
                "warning": {"bg": "#fffbeb", "border": "#f59e0b", "icon": "⚠️", "fg": "#78350f", "accent": "#b45309"},
                "info":    {"bg": "#eff6ff", "border": "#3b82f6", "icon": "ℹ️", "fg": "#1e3a8a", "accent": "#1d4ed8"}
            }
        else:
            colors = {
                "success": {"bg": "#064e3b", "border": "#10b981", "icon": "✅", "fg": "#ecfdf5", "accent": "#34d399"},
                "error":   {"bg": "#7f1d1d", "border": "#ef4444", "icon": "❌", "fg": "#fef2f2", "accent": "#f87171"},
                "warning": {"bg": "#78350f", "border": "#f59e0b", "icon": "⚠️", "fg": "#fffbeb", "accent": "#fbbf24"},
                "info":    {"bg": "#1e3a8a", "border": "#3b82f6", "icon": "ℹ️", "fg": "#eff6ff", "accent": "#60a5fa"}
            }
        theme = colors.get(toast_type, colors["info"])

        # Vị trí hiển thị (Mặc định: góc phải dưới cùng màn hình)
        toast_pos = "bottom_right"
        if hasattr(master, "app_settings") and isinstance(master.app_settings, dict):
            toast_pos = master.app_settings.get("toast_position", "bottom_right")

        self.configure(bg=theme["border"])

        inner = tk.Frame(self, bg=theme["bg"], padx=14, pady=10)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        icon_lbl = tk.Label(inner, text=theme["icon"], font=("Segoe UI", 15), bg=theme["bg"], fg=theme["accent"])
        icon_lbl.pack(side="left", anchor="nw", padx=(0, 12), pady=(1, 0))

        btn_close = tk.Label(inner, text="✕", font=("Segoe UI", 10, "bold"), bg=theme["bg"], fg="#94a3b8" if not is_light else "#64748b", cursor="hand2")
        btn_close.pack(side="right", anchor="ne", padx=(6, 0))
        btn_close.bind("<Button-1>", lambda e: self._fade_out())
        btn_close.bind("<Enter>", lambda e: btn_close.configure(fg="#ffffff" if not is_light else "#0f172a"))
        btn_close.bind("<Leave>", lambda e: btn_close.configure(fg="#94a3b8" if not is_light else "#64748b"))

        text_frame = tk.Frame(inner, bg=theme["bg"])
        text_frame.pack(side="left", fill="both", expand=True)

        t_lbl = tk.Label(text_frame, text=title, font=("Segoe UI", 9, "bold"), bg=theme["bg"], fg=theme["accent"], anchor="w")
        t_lbl.pack(fill="x", anchor="w")

        msg_clean = message[:280] + "..." if len(message) > 280 else message
        m_lbl = tk.Label(text_frame, text=msg_clean, font=("Segoe UI", 9), bg=theme["bg"], fg=theme["fg"], anchor="w", justify="left", wraplength=340)
        m_lbl.pack(fill="x", anchor="w", pady=(3, 0))

        # Tự động tính toán kích thước động dựa trên độ dài nội dung thực tế (chống co hẹp/cắt chữ)
        self.update_idletasks()
        try:
            req_w = self.winfo_reqwidth()
            req_h = self.winfo_reqheight()
            toast_w = max(420, min(500, req_w + 10))
            toast_h = max(74, req_h + 6)
            self.toast_h = toast_h

            scr_w = self.winfo_screenwidth()
            scr_h = self.winfo_screenheight()

            # Xác định index xếp tầng (stacking) giữa các toast đang mở
            active_prev = [t for t in _ACTIVE_TOASTS if t != self and t.winfo_exists()]
            offset_y = sum(getattr(t, "toast_h", 80) + 8 for t in active_prev)

            if toast_pos == "top_right":
                x = max(10, scr_w - toast_w - 24)
                y = max(10, 40 + offset_y)
            elif toast_pos == "bottom_left":
                x = 24
                y = max(10, scr_h - toast_h - 55 - offset_y)
            elif toast_pos == "top_left":
                x = 24
                y = max(10, 40 + offset_y)
            elif toast_pos == "bottom_center":
                x = max(10, (scr_w - toast_w) // 2)
                y = max(10, scr_h - toast_h - 55 - offset_y)
            else:  # "bottom_right" (Mặc định chuẩn)
                x = max(10, scr_w - toast_w - 24)
                y = max(10, scr_h - toast_h - 55 - offset_y)
        except Exception:
            x, y = 100, 100
            toast_w, toast_h = 430, 84
            self.toast_h = toast_h

        self.geometry(f"{toast_w}x{toast_h}+{x}+{y}")
        self.after(duration_ms, self._fade_out)

    def _fade_out(self):
        global _ACTIVE_TOASTS
        if self in _ACTIVE_TOASTS:
            try:
                _ACTIVE_TOASTS.remove(self)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass


class GuiLogHandler(logging.Handler):
    """Custom Logging Handler đẩy log realtime vào giao diện GUI."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            self.callback(msg, level)
        except Exception:
            pass


def setup_app_window_icon(window):
    """
    Thiết lập Icon hiện đại cho cửa sổ Tkinter và tất cả cửa sổ con (Modal).
    Đồng thời đăng ký AppUserModelID để Windows Taskbar hiển thị đúng icon tùy chỉnh.
    """
    try:
        import ctypes
        app_id = 'ai.zalo.cskh.100aisupport.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

    icon_ico = get_resource_path(os.path.join("assets", "app_icon.ico"))
    icon_png = get_resource_path(os.path.join("assets", "app_icon.png"))

    if os.path.exists(icon_ico):
        try:
            window.iconbitmap(icon_ico)
        except Exception:
            pass

    if os.path.exists(icon_png):
        try:
            from PIL import ImageTk, Image
            photo_img = ImageTk.PhotoImage(Image.open(icon_png))
            window._app_photo_icon = photo_img
            window.iconphoto(True, photo_img)
        except Exception:
            pass


def apply_windows_dark_titlebar(window, bg_hex="#0f172a", text_hex="#f8fafc"):
    """
    Đồng bộ màu sắc thanh tiêu đề Windows (Title Bar) trùng khớp 100% với màu nền ứng dụng
    (Phong cách VS Code / Modern IDE) và áp dụng icon hiện đại.
    """
    setup_app_window_icon(window)
    try:
        import ctypes
        from ctypes import windll, byref, c_int, sizeof

        window.update_idletasks()
        hwnd = windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        use_dark = c_int(1)
        windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(use_dark), sizeof(use_dark))

        # Helper đổi màu HEX #RRGGBB -> COLORREF (0x00BBGGRR)
        def hex_to_colorref(hex_str):
            hex_str = hex_str.lstrip('#')
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (b << 16) | (g << 8) | r

        # DWMWA_CAPTION_COLOR = 35 (Windows 11) - Đổi màu nền Title Bar
        DWMWA_CAPTION_COLOR = 35
        caption_color = c_int(hex_to_colorref(bg_hex))
        windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(caption_color), sizeof(caption_color))

        # DWMWA_TEXT_COLOR = 36 (Windows 11) - Đổi màu chữ Title Bar
        DWMWA_TEXT_COLOR = 36
        text_color = c_int(hex_to_colorref(text_hex))
        windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))

    except Exception:
        pass


def _obfuscate_secret(text: str) -> str:
    """Mã hóa cơ bản mật khẩu lưu trong file để chống lộ thông tin thô (XOR + Base64)."""
    if not text:
        return ""
    import base64
    salt = "AIZaloCSKH_2026_SecureKey"
    combined = "".join(chr(ord(c) ^ ord(salt[i % len(salt)])) for i, c in enumerate(text))
    return "enc_" + base64.b64encode(combined.encode('latin1')).decode('ascii')


def _deobfuscate_secret(encoded: str) -> str:
    """Giải mã mật khẩu đã lưu."""
    if not encoded:
        return ""
    if not encoded.startswith("enc_"):
        return encoded  # Plain text fallback
    import base64
    try:
        raw = base64.b64decode(encoded[4:].encode('ascii')).decode('latin1')
        salt = "AIZaloCSKH_2026_SecureKey"
        return "".join(chr(ord(c) ^ ord(salt[i % len(salt)])) for i, c in enumerate(raw))
    except Exception:
        return encoded


def load_saved_login_credentials() -> Dict[str, Any]:
    """Đọc thông tin đăng nhập đã lưu từ storage/saved_login.json với giải mã bảo mật."""
    p = get_storage_path("saved_login.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                pwd = _deobfuscate_secret(data.get("password", ""))
                return {
                    "remember": bool(data.get("remember", False)),
                    "username": data.get("username", ""),
                    "password": pwd
                }
        except Exception:
            pass
    return {"remember": False, "username": "", "password": ""}


def save_login_credentials(username: str, password: str, remember: bool):
    """Lưu hoặc xóa thông tin đăng nhập vào storage/saved_login.json có mã hóa bảo mật."""
    p = get_storage_path("saved_login.json")
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if remember:
            enc_pwd = _obfuscate_secret(password)
            data = {"remember": True, "username": username, "password": enc_pwd}
        else:
            data = {"remember": False, "username": "", "password": ""}
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[Auth] Lỗi lưu saved_login.json: {e}")


def clear_saved_login_credentials():
    """Xóa sạch file thông tin đăng nhập đã lưu."""
    p = get_storage_path("saved_login.json")
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


def verify_totp_or_pin(input_code: str, custom_pin: str, totp_secret: str = "") -> bool:
    """
    Kiểm tra mã xác thực 2FA (khớp với Mã PIN bảo mật hoặc mã OTP Google Authenticator).
    """
    code_clean = input_code.strip()
    if not code_clean:
        return False
    # 1. Khớp với Mã PIN tùy chỉnh (4-8 số)
    if custom_pin and code_clean == custom_pin.strip():
        return True
    
    # 2. Khớp với mã TOTP 6 số từ Google / Microsoft Authenticator (nếu có cấu hình)
    if totp_secret and len(code_clean) == 6 and code_clean.isdigit():
        try:
            import hmac, hashlib, struct, time, base64
            secret_bytes = base64.b32decode(totp_secret.strip().upper(), casefold=True)
            for offset in (-1, 0, 1):
                interval = int(time.time() // 30) + offset
                msg = struct.pack(">Q", interval)
                h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
                o = h[19] & 15
                totp_val = ((struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000)
                totp_str = f"{totp_val:06d}"
                if code_clean == totp_str:
                    return True
        except Exception:
            pass

    return False


class LoginDialog(tk.Toplevel):
    """Cửa sổ đăng nhập bảo mật có hỗ trợ Xác Thực 2 Bước (2FA / Mã PIN)."""
    def __init__(self, parent, state_manager, on_login_success, on_cancel=None, app_settings: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.state = state_manager
        self.on_login_success = on_login_success
        self.on_cancel = on_cancel
        self.app_settings = app_settings or {}
        if not self.app_settings:
            try:
                p = get_storage_path("app_settings.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        self.app_settings = json.load(f)
            except Exception:
                self.app_settings = {}

        self._pending_user_data = None
        self.title("🔐 Đăng Nhập - Hệ Thống AI Zalo CSKH")
        self.geometry("440x530")
        self.resizable(False, False)
        self.configure(bg="#0f172a")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.update_idletasks()
        w = 440
        h = 530
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Header banner
        hdr = tk.Frame(self, bg="#1e293b", padx=20, pady=14)
        hdr.pack(fill="x")
        
        tk.Label(hdr, text="⚡ AI ZALO CSKH", font=("Segoe UI", 15, "bold"), fg="#38bdf8", bg="#1e293b").pack()
        tk.Label(hdr, text="HỆ THỐNG QUẢN TRỊ & TỰ ĐỘNG HÓA CHĂM SÓC KHÁCH HÀNG", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1e293b").pack(pady=(2, 0))

        # Container Bước 1 (Nhập Tài Khoản & Mật Khẩu)
        self.step1_frame = tk.Frame(self, bg="#0f172a", padx=24, pady=14)
        self.step1_frame.pack(fill="both", expand=True)

        tk.Label(self.step1_frame, text="🔐 Vui lòng đăng nhập để tiếp tục", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w", pady=(0, 10))

        # Username
        tk.Label(self.step1_frame, text="Tên Đăng Nhập:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        self.ent_user = tk.Entry(self.step1_frame, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.ent_user.pack(fill="x", pady=(2, 8), ipady=3)

        # Password
        tk.Label(self.step1_frame, text="Mật Khẩu:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        self.ent_pwd = tk.Entry(self.step1_frame, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white", show="*")
        self.ent_pwd.pack(fill="x", pady=(2, 6), ipady=3)

        # Đọc thông tin đã lưu (nếu người dùng trước đó đã chọn Lưu)
        saved_cred = load_saved_login_credentials()
        is_saved = saved_cred.get("remember", False)
        self.remember_var = tk.BooleanVar(value=is_saved)

        # KHÔNG ĐIỀN SẴN NẾU CHƯA LƯU! Chỉ điền khi người dùng đã chủ động lưu trước đó.
        if is_saved and saved_cred.get("username"):
            self.ent_user.insert(0, saved_cred.get("username", ""))
            self.ent_pwd.insert(0, saved_cred.get("password", ""))

        # Checkbox Row 1: [✓] Lưu thông tin đăng nhập + [👁️] Hiện mật khẩu
        opt_row = tk.Frame(self.step1_frame, bg="#0f172a")
        opt_row.pack(fill="x", pady=(2, 6))

        chk_rem = tk.Checkbutton(
            opt_row,
            text="💾 Lưu thông tin đăng nhập",
            variable=self.remember_var,
            bg="#0f172a",
            fg="#f8fafc",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 8, "bold")
        )
        chk_rem.pack(side="left")

        self.show_pwd_var = tk.BooleanVar(value=False)
        chk_show = tk.Checkbutton(
            opt_row,
            text="👁️ Hiện pass",
            variable=self.show_pwd_var,
            command=self._toggle_show_pwd,
            bg="#0f172a",
            fg="#94a3b8",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 8)
        )
        chk_show.pack(side="right")

        # Row 2: Nút Bỏ Lưu Thông Tin Đăng Nhập
        forget_row = tk.Frame(self.step1_frame, bg="#0f172a")
        forget_row.pack(fill="x", pady=(0, 6))

        btn_forget = tk.Button(
            forget_row,
            text="🧹 Bỏ Lưu Thông Tin",
            bg="#1e293b",
            fg="#fca5a5",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._clear_saved_credentials
        )
        btn_forget.pack(side="left")

        tk.Label(
            forget_row,
            text="(Xóa tài khoản & mật khẩu đã lưu)",
            font=("Segoe UI", 7, "italic"),
            fg="#64748b",
            bg="#0f172a"
        ).pack(side="left", padx=4)

        # Error / Status Message Label
        self.lbl_err = tk.Label(self.step1_frame, text="", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#0f172a", wraplength=380, justify="left")
        self.lbl_err.pack(fill="x", pady=(0, 8))

        # Login button
        btn_login = tk.Button(
            self.step1_frame,
            text="🚀 ĐĂNG NHẬP (Enter)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._do_login
        )
        btn_login.pack(fill="x", pady=(0, 6))

        # Exit button
        btn_exit = tk.Button(
            self.step1_frame,
            text="❌ Thoát Ứng Dụng (Esc)",
            bg="#334155",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._on_close
        )
        btn_exit.pack(fill="x")

        # Container Bước 2 (Xác Thực 2 Bước / 2FA PIN - Ẩn mặc định)
        self.step2_frame = tk.Frame(self, bg="#0f172a", padx=24, pady=16)

        tk.Label(self.step2_frame, text="🛡️ BƯỚC 2: XÁC THỰC 2 BƯỚC (2FA)", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(0, 4))
        
        self.lbl_2fa_target = tk.Label(self.step2_frame, text="Tài khoản: admin", font=("Segoe UI", 8, "italic"), fg="#94a3b8", bg="#0f172a")
        self.lbl_2fa_target.pack(anchor="w", pady=(0, 12))

        tk.Label(self.step2_frame, text="🔑 Nhập Mã PIN 2FA hoặc Mã OTP Authenticator:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")

        self.ent_2fa_pin = tk.Entry(self.step2_frame, font=("Segoe UI", 14, "bold"), bg="#1e293b", fg="#34d399", insertbackground="white", justify="center", show="*")
        self.ent_2fa_pin.pack(fill="x", pady=(4, 6), ipady=4)

        row_2fa_opt = tk.Frame(self.step2_frame, bg="#0f172a")
        row_2fa_opt.pack(fill="x", pady=(0, 8))

        self.show_2fa_pin_var = tk.BooleanVar(value=False)
        def _toggle_show_2fa_pin():
            if self.show_2fa_pin_var.get():
                self.ent_2fa_pin.configure(show="")
            else:
                self.ent_2fa_pin.configure(show="*")

        chk_show_2fa = tk.Checkbutton(
            row_2fa_opt,
            text="👁️ Hiện mã PIN",
            variable=self.show_2fa_pin_var,
            command=_toggle_show_2fa_pin,
            bg="#0f172a",
            fg="#94a3b8",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 8)
        )
        chk_show_2fa.pack(side="right")

        self.lbl_2fa_err = tk.Label(self.step2_frame, text="", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#0f172a", wraplength=380, justify="left")
        self.lbl_2fa_err.pack(fill="x", pady=(0, 8))

        btn_verify_2fa = tk.Button(
            self.step2_frame,
            text="✅ XÁC NHẬN 2FA (Enter)",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._do_verify_2fa
        )
        btn_verify_2fa.pack(fill="x", pady=(0, 6))

        btn_back = tk.Button(
            self.step2_frame,
            text="⬅️ Quay Lại Bước 1 (Esc)",
            bg="#334155",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._back_to_step1
        )
        btn_back.pack(fill="x")

        # Key bindings
        self.bind("<Return>", lambda e: self._do_login())
        self.bind("<Escape>", lambda e: self._on_close())

        if is_saved and saved_cred.get("password"):
            self.ent_pwd.focus_set()
            self.ent_pwd.select_range(0, tk.END)
        else:
            self.ent_user.focus_set()

    def _toggle_show_pwd(self):
        if self.show_pwd_var.get():
            self.ent_pwd.configure(show="")
        else:
            self.ent_pwd.configure(show="*")

    def _clear_saved_credentials(self):
        """Xóa sạch thông tin đăng nhập đã lưu."""
        clear_saved_login_credentials()
        self.remember_var.set(False)
        self.ent_user.delete(0, tk.END)
        self.ent_pwd.delete(0, tk.END)
        self.ent_user.focus_set()
        self.lbl_err.configure(text="🧹 Đã bỏ lưu & xóa sạch thông tin đăng nhập!", fg="#38bdf8")

    def _do_login(self):
        u = self.ent_user.get().strip()
        p = self.ent_pwd.get().strip()
        if not u or not p:
            self.lbl_err.configure(text="⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!", fg="#ef4444")
            return

        user_data = self.state.authenticate_user(u, p)
        if user_data:
            # Kiểm tra xem có kích hoạt 2FA / Mã PIN 2 bước không
            is_2fa_enabled = self.app_settings.get("enable_2fa", False)
            if is_2fa_enabled:
                # Chuyển sang Bước 2: Nhập Mã PIN 2FA / OTP
                self._pending_user_data = user_data
                self.step1_frame.pack_forget()
                self.step2_frame.pack(fill="both", expand=True)
                self.lbl_2fa_target.configure(text=f"Tài khoản: {user_data.get('full_name', user_data['username'])} ({user_data.get('username')})")
                self.ent_2fa_pin.delete(0, tk.END)
                self.ent_2fa_pin.focus_set()
                self.lbl_2fa_err.configure(text="")
                self.bind("<Return>", lambda e: self._do_verify_2fa())
                self.bind("<Escape>", lambda e: self._back_to_step1())
            else:
                # Không bật 2FA -> Đăng nhập thành công ngay
                rem = self.remember_var.get()
                save_login_credentials(u, p, rem)
                self.lbl_err.configure(text="✅ Đăng nhập thành công!", fg="#34d399")
                self.update_idletasks()
                self.after(100, lambda: (self.destroy(), self.on_login_success(user_data)))
        else:
            self.lbl_err.configure(text="❌ Sai tên đăng nhập hoặc mật khẩu!", fg="#ef4444")
            self.ent_pwd.delete(0, tk.END)
            self.ent_pwd.focus_set()

    def _do_verify_2fa(self):
        """Xác thực Mã PIN 2FA hoặc mã OTP Authenticator ở Bước 2."""
        pin_code = self.ent_2fa_pin.get().strip()
        if not pin_code:
            self.lbl_2fa_err.configure(text="⚠️ Vui lòng nhập Mã PIN 2FA!", fg="#ef4444")
            return

        custom_pin = self.app_settings.get("security_pin_2fa", "123456")
        totp_sec = self.app_settings.get("totp_secret_key", "")

        if verify_totp_or_pin(pin_code, custom_pin, totp_sec):
            # Lưu credentials nếu có chọn
            u = self.ent_user.get().strip()
            p = self.ent_pwd.get().strip()
            rem = self.remember_var.get()
            save_login_credentials(u, p, rem)

            self.lbl_2fa_err.configure(text="✅ Xác thực 2FA thành công!", fg="#34d399")
            self.update_idletasks()
            self.after(100, lambda: (self.destroy(), self.on_login_success(self._pending_user_data)))
        else:
            self.lbl_2fa_err.configure(text="❌ Mã PIN 2FA / OTP không chính xác!", fg="#ef4444")
            self.ent_2fa_pin.delete(0, tk.END)
            self.ent_2fa_pin.focus_set()

    def _back_to_step1(self):
        """Quay lại bước 1 nhập tài khoản mật khẩu."""
        self.step2_frame.pack_forget()
        self.step1_frame.pack(fill="both", expand=True)
        self.bind("<Return>", lambda e: self._do_login())
        self.bind("<Escape>", lambda e: self._on_close())
        self.ent_pwd.focus_set()

    def _on_close(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()


class AIDashboard(tk.Tk):
    """Giao diện điều khiển trung tâm AI CSKH & Quản lý Giáo án Lịch sử (Tailwind CSS Slate Dark Theme)."""

    def __init__(self, zalo_handler, state_manager, gemini_engine, hotkey_manager, drive_manager):
        super().__init__()
        self.handler = zalo_handler
        self.state = state_manager
        self.gemini = gemini_engine
        self.key_mgr = gemini_engine.key_mgr
        self.hotkeys = hotkey_manager
        self.drive = drive_manager
        self.searcher = LocalFileSearcher(root_dir=self.drive.matrix.get("local_root_directory", "C:/GiaoAnLichSu"))
        self.auto_scroll_console = True
        self.playground_chat_history = []
        self.tab1_chat_history = []
        self.current_chat_session_id = None
        self.chat_view_mode = "active"
        # Tải cài đặt ứng dụng đã lưu
        self.app_settings = self._load_app_settings()
        self.current_logged_user = None
        self.script_tab_layout = self.app_settings.get("script_tab_layout", "3_columns")
        self.quick_links_data = self._load_quick_links()
        self.quick_links_selected_grade = "Khối 6"
        self.quick_links_include_label_var = tk.BooleanVar(value=True)
        self.script_bundle_view_mode = "files"
        self.current_theme = self.app_settings.get("theme", "light_theme")  # Mặc định Giao diện Sáng
        ZaloAutomation.set_max_retries(self.app_settings.get("max_retries", 5))
        self.last_user_question = ""
        self.last_ai_response = ""
        self.playground_img_path = None
        self.tab1_img_path = None

        self.title("⚡ AI Zalo CSKH - Hệ Thống Tự Động Hóa & Chăm Sóc Khách Hàng")
        
        # Nạp cài đặt người dùng và tự động áp dụng Vị trí cửa sổ & Giao diện
        self._apply_saved_window_geometry()
        self.minsize(650, 550)
        self.configure(bg="#f1f5f9" if self.current_theme in ("light_theme", "light") else "#0b0f19")

        self.selected_tpl_num = 1
        self.current_attached_files = []
        self.scheduler = BroadcastScheduler(
            self.state,
            on_broadcast_started=self._on_scheduled_broadcast_start,
            on_broadcast_finished=self._on_scheduled_broadcast_end
        )
        self.scheduler.start()

        self._setup_styles()
        self._apply_font_scale(self.app_settings.get("font_size", "normal"))
        self._build_header()
        self._build_footer_status_bar()
        self._build_main_tabs()

        # Kiểm tra yêu cầu Đăng Nhập khi khởi động (Mặc định BẬT)
        is_sso = os.environ.get("HB_AUTH_BYPASS") == "1" or "--sso" in sys.argv or "--bypass-login" in sys.argv
        require_login = False if is_sso else self.app_settings.get("require_login", True)
        if require_login:
            self.withdraw()
            self.after(60, lambda: self._show_login_dialog(is_startup=True))
        else:
            self.current_logged_user = {"username": "admin", "full_name": "Quản Trị Viên (Admin)", "role": "admin"}
            self._update_header_user_display()

        # Áp dụng Theme đã chọn (Sáng hoặc Tối)
        self.after(50, lambda: self._apply_theme(self.current_theme, show_toast_msg=False))

        # Đồng bộ màu sắc thanh tiêu đề Windows với giao diện ứng dụng
        apply_windows_dark_titlebar(self, "#0f172a", "#f8fafc")
        self.after(50, lambda: apply_windows_dark_titlebar(self, "#0f172a", "#f8fafc"))
        self.after(300, lambda: apply_windows_dark_titlebar(self, "#0f172a", "#f8fafc"))

        # Callbacks từ ZaloHandler
        self.handler.on_message_received_callback = self._on_msg_received
        self.handler.on_reply_sent_callback = self._on_reply_sent
        self.handler.on_step_log_callback = self._on_step_log

        # Kết nối Python Logging vào GUI Console
        self.gui_log_handler = GuiLogHandler(self._append_console_log)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        self.gui_log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.gui_log_handler)

        self.refresh_all_data()

        # Theo dõi cửa sổ Foreground bên ngoài để hỗ trợ gửi UltraViewer / AnyDesk / Zalo
        self._track_foreground_window()

        # Phím tắt toàn cục Ctrl+S để lưu mẫu kịch bản khi đang mở Tab 3
        self.bind_all("<Control-s>", self._on_global_ctrl_s)
        self.bind_all("<Control-S>", self._on_global_ctrl_s)

        # Phím tắt F9 để Hủy Mọi Thao Tác Khẩn Cấp
        self.bind_all("<F9>", lambda e: self.emergency_cancel_all_operations())

        # Phím tắt F10 để Gửi Nhanh Mẫu Tin / Kịch Bản vào Zalo
        self.bind_all("<F10>", lambda e: self._on_f10_quick_send())

        # Theo dõi kích thước cửa sổ để tự động chuyển đổi giao diện rộng (Wide) vs siêu gọn (Compact)
        self._is_wide_mode = False
        self.bind("<Configure>", self._on_root_configure)

    def _build_footer_status_bar(self):
        """
        Thanh bar ở dưới chân giao diện hiển thị trạng thái đang hoạt động,
        tiến trình đang làm, model AI, phím tắt và đồng hồ thời gian thực.
        """
        self.footer_frame = tk.Frame(self, bg="#0f172a", height=32, padx=14, pady=4, highlightbackground="#1e293b", highlightthickness=1)
        self.footer_frame.pack(side="bottom", fill="x")

        # Cụm bên trái: Trạng thái & Tiến trình đang làm
        left_foot = tk.Frame(self.footer_frame, bg="#0f172a")
        left_foot.pack(side="left", fill="y")

        self.footer_status_lbl = tk.Label(
            left_foot,
            text="🟢 Đang hoạt động (F8)",
            font=("Segoe UI", 9, "bold"),
            fg="#34d399",
            bg="#0f172a"
        )
        self.footer_status_lbl.pack(side="left", padx=(0, 8))

        tk.Label(left_foot, text="|", fg="#334155", bg="#0f172a").pack(side="left", padx=2)

        self.footer_model_lbl = tk.Label(
            left_foot,
            text=f"⚡ Model: {self.gemini.model_name}",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        self.footer_model_lbl.pack(side="left", padx=6)

        tk.Label(left_foot, text="|", fg="#334155", bg="#0f172a").pack(side="left", padx=2)

        self.footer_task_lbl = tk.Label(
            left_foot,
            text="📡 Tiến trình: Sẵn sàng nhận lệnh & lắng nghe Zalo PC...",
            font=("Segoe UI", 8),
            fg="#cbd5e1",
            bg="#0f172a"
        )
        self.footer_task_lbl.pack(side="left", padx=6)

        # Cụm bên phải: Phím tắt & Đồng hồ
        right_foot = tk.Frame(self.footer_frame, bg="#0f172a")
        right_foot.pack(side="right", fill="y")

        self.footer_hotkeys_lbl = tk.Label(
            right_foot,
            text="⌨️ F8: Chạy | F9: Dừng | F10: Gửi Nhanh | F6: Tạm dừng gửi | F7: Hủy",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.footer_hotkeys_lbl.pack(side="left", padx=8)

        tk.Label(right_foot, text="|", fg="#334155", bg="#0f172a").pack(side="left", padx=2)

        self.footer_clock_lbl = tk.Label(
            right_foot,
            text="",
            font=("Consolas", 8, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        self.footer_clock_lbl.pack(side="left", padx=(4, 0))

        self._update_footer_clock()

    def _update_footer_clock(self):
        now_str = datetime.now().strftime("🕒 %H:%M:%S - %d/%m/%Y")
        if hasattr(self, "footer_clock_lbl") and self.footer_clock_lbl.winfo_exists():
            self.footer_clock_lbl.configure(text=now_str)
            self.after(1000, self._update_footer_clock)

    def set_footer_task(self, task_description: str, fg_color: str = "#cbd5e1"):
        """Cập nhật nhanh nội dung tiến trình đang thực hiện trên thanh Footer."""
        def _update():
            try:
                if hasattr(self, "footer_task_lbl") and self.footer_task_lbl.winfo_exists():
                    self.footer_task_lbl.configure(text=f"📡 Tiến trình: {task_description}", fg=fg_color)
            except Exception:
                pass
        self.after(0, _update)

    def _on_step_log(self, step_text: str, progress_pct: float = 0.0):
        self.set_footer_task(step_text)

    def show_toast(self, title: str, message: str, toast_type: str = "success", duration_ms: Optional[int] = None):
        """Hiển thị Toast Notification nổi bật theo phong cách Tailwind với thời gian hiển thị cài đặt được."""
        if duration_ms is None:
            try:
                sec = float(self.app_settings.get("toast_duration_sec", 3.5))
                duration_ms = max(500, int(sec * 1000))
            except Exception:
                duration_ms = 3500

        def _do():
            try:
                ToastNotification(self, title, message, toast_type, duration_ms)
            except Exception:
                pass
        self.after(0, _do)

    def _get_active_model_list(self) -> List[str]:
        """Lấy danh sách các model khả dụng, tự động lọc model cũ dưới 3.1 hoặc theo cấu hình Admin."""
        hide_below_3_1 = self.app_settings.get("hide_models_below_3_1", True)
        min_ver_raw = self.app_settings.get("min_gemini_version", "3.1")
        min_ver = parse_gemini_min_version(min_ver_raw)
        models = self.key_mgr.list_available_models(hide_below_3_1=hide_below_3_1, min_version=min_ver)
        if not models:
            models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-pro-latest"]
        return models

    def _refresh_all_model_comboboxes(self):
        """Cập nhật lại danh sách model trong tất cả các dropdown và modal."""
        models = self._get_active_model_list()
        cur_m = self.gemini.model_name
        if cur_m not in models and models:
            cur_m = models[0]
            self.gemini.set_model(cur_m)

        if hasattr(self, 'hdr_model_cb') and self.hdr_model_cb.winfo_exists():
            self.hdr_model_cb.configure(values=models)
            self.hdr_model_cb.set(cur_m)

        if hasattr(self, 'pg_model_cb') and self.pg_model_cb.winfo_exists():
            self.pg_model_cb.configure(values=models)
            self.pg_model_cb.set(cur_m)

        if hasattr(self, 'api_model_cb') and self.api_model_cb.winfo_exists():
            self.api_model_cb.configure(values=models)
            self.api_model_cb.set(cur_m)

        if hasattr(self, 'footer_model_lbl') and self.footer_model_lbl.winfo_exists():
            self.footer_model_lbl.configure(text=f"⚡ Model: {cur_m}")

        self._update_header_status_label()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Style Treeview phong cách Tailwind Slate Dark
        style.configure("Treeview.Heading", font=("Segoe UI", 8, "bold"), background="#1e293b", foreground="#38bdf8", relief="flat")
        style.configure("Treeview", font=("Segoe UI", 8), rowheight=24, background="#0f172a", foreground="#f8fafc", fieldbackground="#0f172a", borderwidth=0)
        style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        # Style Notebook Tabs (Ẩn tab bar mặc định để dùng thanh Segmented Nav Bar siêu đẹp)
        style.layout("Hidden.TNotebook.Tab", [])
        style.configure("Hidden.TNotebook", background="#0b0f19", borderwidth=0)
        style.configure("TNotebook", background="#0b0f19", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 8, "bold"), padding=[10, 6], background="#1e293b", foreground="#94a3b8", borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

    def _build_header(self):
        self.header_frame = tk.Frame(self, bg="#0f172a", height=44, padx=10, pady=4)
        self.header_frame.pack(fill="x")
        header_frame = self.header_frame

        # Tiêu Đề / Logo Thu Gọn Bên Trái
        self.hdr_title_lbl = tk.Label(
            header_frame,
            text="⚡ AI CSKH",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        self.hdr_title_lbl.pack(side="left", padx=(2, 6))

        # CỤM BÊN PHẢI (RIGHT SIDE): TOÀN BỘ TRẠNG THÁI VÀ CÁC NÚT ĐIỀU KHIỂN
        # 1. Thông Tin Tài Khoản Đăng Nhập & Nút Đăng Xuất
        user_f = tk.Frame(header_frame, bg="#0f172a")
        user_f.pack(side="right", padx=(4, 0))
        
        self.btn_header_logout = tk.Button(
            user_f,
            text="🚪 Thoát",
            font=("Segoe UI", 7, "bold"),
            bg="#334155",
            fg="#fca5a5",
            relief="flat",
            padx=4,
            pady=2,
            cursor="hand2",
            command=self._logout_user
        )
        self.btn_header_logout.pack(side="right", padx=(3, 0))

        self.header_user_lbl = tk.Label(
            user_f,
            text="👤 admin",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        self.header_user_lbl.pack(side="right")

        # 2. Nút Ghim Cửa Sổ Luôn Nổi Trên Cùng (Always on Top)
        self.is_always_on_top = self.app_settings.get("always_on_top", False)
        self.btn_pin_top = tk.Button(
            header_frame,
            text="📌 ĐÃ GHIM" if self.is_always_on_top else "📌 Ghim",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7" if self.is_always_on_top else "#334155",
            fg="#ffffff" if self.is_always_on_top else "#94a3b8",
            relief="flat",
            padx=5,
            pady=2,
            cursor="hand2",
            command=self._toggle_always_on_top
        )
        self.btn_pin_top.pack(side="right", padx=3)
        if self.is_always_on_top:
            self.attributes("-topmost", True)

        # 3. Nút Thu Nhỏ Nổi On-Top (Floating Mini Toolbar)
        self.btn_float_mini = tk.Button(
            header_frame,
            text="🪟 Nổi",
            font=("Segoe UI", 8, "bold"),
            bg="#8b5cf6",
            fg="#ffffff",
            activebackground="#7c3aed",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=2,
            cursor="hand2",
            command=self.shrink_to_floating_toolbar
        )
        self.btn_float_mini.pack(side="right", padx=3)

        # 4. Nút Điều Khiển Bật/Tắt Bot AI (F8)
        self.btn_toggle_bot = tk.Button(
            header_frame,
            text="⏸ Dừng Bot",
            font=("Segoe UI", 8, "bold"),
            bg="#e11d48",
            fg="white",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._toggle_bot_running_state
        )
        self.btn_toggle_bot.pack(side="right", padx=3)

        # 5. Nút Hủy Mọi Thao Tác (F9)
        self.btn_emergency_cancel = tk.Button(
            header_frame,
            text="🛑 Hủy",
            font=("Segoe UI", 8, "bold"),
            bg="#dc2626",
            fg="white",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.emergency_cancel_all_operations
        )
        self.btn_emergency_cancel.pack(side="right", padx=3)

        # 6. Nút Khôi Phục / Reset Lỗi
        self.btn_header_reset_retries = tk.Button(
            header_frame,
            text="🔄 Reset",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.reset_all_retry_and_error_states
        )
        self.btn_header_reset_retries.pack(side="right", padx=3)

        # 7. Trạng Thái Hoạt Động Của Bot AI Đưa Sang Bên Phải
        self.status_lbl = tk.Label(
            header_frame,
            text="● BOT CHẠY (F8)",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#0f172a"
        )
        self.status_lbl.pack(side="right", padx=(2, 6))

        # Toolbar Header Sub-bar (Model + Modal Bảng Models bên trái; Chức năng bên phải)
        self.header_sub_bar = tk.Frame(self, bg="#1e293b", padx=8, pady=4)
        self.header_sub_bar.pack(fill="x")
        top_bar = self.header_sub_bar

        # CỤM BÊN TRÁI: CHỌN MODEL, MẶC ĐỊNH & MODAL BẢNG MODELS
        self.hdr_model_lbl = tk.Label(
            top_bar,
            text="🎯 Model:",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        self.hdr_model_lbl.pack(side="left")

        available_models = self._get_active_model_list()
        self.hdr_model_cb = ttk.Combobox(top_bar, values=available_models, width=16, state="readonly")
        self.hdr_model_cb.set(self.gemini.model_name if self.gemini.model_name in available_models else (available_models[0] if available_models else "gemini-3.6-flash"))
        self.hdr_model_cb.pack(side="left", padx=4)
        self.hdr_model_cb.bind("<<ComboboxSelected>>", self._on_header_model_selected)

        self.btn_set_def = tk.Button(
            top_bar,
            text="⭐ Mặc Định",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=5,
            pady=2,
            cursor="hand2",
            command=self._activate_default_model_from_header
        )
        self.btn_set_def.pack(side="left", padx=2)

        self.btn_modal = tk.Button(
            top_bar,
            text="📋 Models",
            font=("Segoe UI", 8, "bold"),
            bg="#6366f1",
            fg="white",
            relief="flat",
            padx=5,
            pady=2,
            cursor="hand2",
            command=self._open_model_selection_modal
        )
        self.btn_modal.pack(side="left", padx=3)

        # CỤM BÊN PHẢI: STATUS KEY + CÀI ĐẶT + SÁNG/TỐI + CHẾ ĐỘ AI
        self.gemini_status_lbl = tk.Label(
            top_bar,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#1e293b"
        )
        self.gemini_status_lbl.pack(side="right", padx=6)

        # Nút chuyển nhanh đến Tab Cài Đặt
        self.btn_quick_settings = tk.Button(
            top_bar,
            text="⚙️ Cài Đặt",
            font=("Segoe UI", 8, "bold"),
            bg="#334155",
            fg="#38bdf8",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._switch_to_settings_tab
        )
        self.btn_quick_settings.pack(side="right", padx=3)

        # Nút chuyển nhanh Giao Diện Sáng / Tối trực tiếp trên Header (Rút gọn nhãn chỉ hiện ☀️ Sáng / 🌙 Tối)
        is_l = getattr(self, 'current_theme', 'light_theme') in ('light_theme', 'light', 'tailwind_light')
        self.btn_theme_toggle = tk.Button(
            top_bar,
            text="☀️ Sáng" if is_l else "🌙 Tối",
            font=("Segoe UI", 8, "bold"),
            bg="#f59e0b" if is_l else "#334155",
            fg="black" if is_l else "#f8fafc",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._toggle_theme_quick
        )
        self.btn_theme_toggle.pack(side="right", padx=3)

        # NÚT GẠT BẬT/TẮT GIỚI HẠN CHỦ ĐỀ (Chế Độ AI)
        self.btn_scope_toggle = tk.Button(
            top_bar,
            text="🌐 AI",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_general_chat_scope
        )
        self.btn_scope_toggle.pack(side="right", padx=3)

        self._update_header_status_label()

    def _toggle_always_on_top(self):
        """Bật/tắt ghim cửa sổ luôn nổi lên trên cùng (Topmost)."""
        self.is_always_on_top = not getattr(self, 'is_always_on_top', False)
        self.attributes("-topmost", self.is_always_on_top)
        if self.is_always_on_top:
            self.btn_pin_top.configure(
                text="📌 ĐÃ GHIM",
                bg="#0284c7",
                fg="#ffffff"
            )
            self.show_toast("Ghim Top", "Đã ghim cửa sổ luôn nổi trên cùng màn hình!", "info")
        else:
            self.btn_pin_top.configure(
                text="📌 Ghim",
                bg="#334155",
                fg="#94a3b8"
            )
            self.show_toast("Bỏ Ghim", "Đã tắt chế độ ghim trên cùng.", "info")

    # =========================================================================
    # CHẾ ĐỘ THU NHỎ NỔI TRÊN CÙNG (FLOATING MINI TOOLBAR ON-TOP)
    # =========================================================================
    def shrink_to_floating_toolbar(self):
        """
        Thu nhỏ toàn bộ màn hình Dashboard thành một thanh công cụ nổi mini trôi nổi (Floating Toolbar) on-top.
        - Luôn hiển thị trên cùng (Topmost).
        - Làm mờ khi không kích hoạt / rời chuột (alpha = 0.35), sáng rõ 100% khi rê chuột hoặc click vào (alpha = 1.0).
        - Kéo thả tự do di chuyển mọi vị trí trên màn hình.
        - Cung cấp các nút truy cập nhanh: F10 Gửi, F8 Bot, Drive Fake, F9 Hủy, Mở Rộng & Đóng.
        - Nút '🗖 Mở Rộng' (hoặc double-click) để khôi phục lại màn hình ban đầu.
        """
        self._saved_main_geometry = self.geometry()
        self._saved_was_topmost = self.attributes("-topmost")
        self.withdraw()

        if hasattr(self, "_float_win") and self._float_win and self._float_win.winfo_exists():
            try:
                self._float_win.destroy()
            except Exception:
                pass

        fw = tk.Toplevel(self)
        self._float_win = fw
        fw.overrideredirect(True)
        # Lấy mức độ mờ khi idle từ cài đặt người dùng (mặc định 0.35 = 35%)
        def _get_configured_idle_alpha():
            try:
                a_val = float(self.app_settings.get("float_idle_alpha", 0.35))
                return max(0.1, min(1.0, a_val))
            except Exception:
                return 0.35

        fw.attributes("-topmost", True)
        fw.attributes("-alpha", _get_configured_idle_alpha())  # Làm mờ theo tỷ lệ cài đặt khi không kích hoạt

        # Đặt vị trí ban đầu ở góc trên bên phải màn hình
        scr_w = fw.winfo_screenwidth()
        fw_w, fw_h = 500, 42
        init_x = max(50, scr_w - fw_w - 60)
        init_y = 60
        fw.geometry(f"{fw_w}x{fw_h}+{init_x}+{init_y}")
        fw.configure(bg="#0b0f19")

        # Container với viền sáng hiện đại
        container = tk.Frame(fw, bg="#1e293b", highlightbackground="#38bdf8", highlightthickness=1)
        container.pack(fill="both", expand=True)

        # Drag grip & Title
        drag_lbl = tk.Label(
            container,
            text="⋮⋮ ⚡ Mini Float",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
            cursor="fleur"
        )
        drag_lbl.pack(side="left", padx=(8, 4))

        # Kéo thả di chuyển vị trí thanh nổi
        def _start_drag(event):
            fw._drag_x = event.x_root - fw.winfo_x()
            fw._drag_y = event.y_root - fw.winfo_y()

        def _on_drag(event):
            new_x = event.x_root - getattr(fw, "_drag_x", 0)
            new_y = event.y_root - getattr(fw, "_drag_y", 0)
            fw.geometry(f"+{new_x}+{new_y}")

        drag_lbl.bind("<Button-1>", _start_drag)
        drag_lbl.bind("<B1-Motion>", _on_drag)
        container.bind("<Button-1>", _start_drag)
        container.bind("<B1-Motion>", _on_drag)

        # Hiệu ứng làm mờ khi không kích hoạt / rời chuột (Hover = 1.0, Idle = _get_configured_idle_alpha())
        def _on_enter(event=None):
            if fw.winfo_exists():
                fw.attributes("-alpha", 1.0)

        def _on_leave(event=None):
            def _check():
                if not fw.winfo_exists():
                    return
                try:
                    px, py = fw.winfo_pointerxy()
                    wx, wy = fw.winfo_x(), fw.winfo_y()
                    ww, wh = fw.winfo_width(), fw.winfo_height()
                    if not (wx <= px <= wx + ww and wy <= py <= wy + wh):
                        fw.attributes("-alpha", _get_configured_idle_alpha())
                except Exception:
                    pass
            fw.after(80, _check)

        container.bind("<Enter>", _on_enter)
        container.bind("<Leave>", _on_leave)
        drag_lbl.bind("<Enter>", _on_enter)
        drag_lbl.bind("<Leave>", _on_leave)
        fw.bind("<Enter>", _on_enter)
        fw.bind("<Leave>", _on_leave)

        # Cụm nút hành động nhanh trên thanh Float
        btn_style = {"font": ("Segoe UI", 8, "bold"), "relief": "flat", "padx": 6, "pady": 2, "cursor": "hand2"}

        # Nút F10 Gửi nhanh
        tk.Button(
            container,
            text="⚡ F10 Gửi",
            bg="#0284c7",
            fg="white",
            activebackground="#0369a1",
            activeforeground="white",
            command=self._on_f10_quick_send,
            **btn_style
        ).pack(side="left", padx=2)

        # Nút F8 Bot AI
        is_running = getattr(self, "bot_is_running", True)
        self.btn_float_bot = tk.Button(
            container,
            text="🟢 Bot (F8)" if is_running else "⏸ Bot (F8)",
            bg="#059669" if is_running else "#e11d48",
            fg="white",
            activebackground="#047857" if is_running else "#be123c",
            activeforeground="white",
            command=self._toggle_bot_running_state,
            **btn_style
        )
        self.btn_float_bot.pack(side="left", padx=2)

        # Nút Bắn Drive Mockup
        tk.Button(
            container,
            text="🖼️ Drive",
            bg="#ea580c",
            fg="white",
            activebackground="#c2410c",
            activeforeground="white",
            command=self._send_fake_drive_to_zalo,
            **btn_style
        ).pack(side="left", padx=2)

        # Nút F9 Hủy
        tk.Button(
            container,
            text="🛑 F9",
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            command=self.emergency_cancel_all_operations,
            **btn_style
        ).pack(side="left", padx=2)

        # NÚT MỞ RỘNG / PHỤC HỒI MÀN HÌNH BAN ĐẦU
        btn_restore = tk.Button(
            container,
            text="🗖 Mở Rộng",
            bg="#8b5cf6",
            fg="white",
            activebackground="#7c3aed",
            activeforeground="white",
            command=self.restore_from_floating_toolbar,
            **btn_style
        )
        btn_restore.pack(side="left", padx=(4, 2))

        # Nút Đóng
        btn_close = tk.Button(
            container,
            text="✕",
            bg="#334155",
            fg="#f87171",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=6,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(side="right", padx=(2, 6))

        # Double-click vào bất kỳ vùng trống nào để Mở Rộng lại cửa sổ
        container.bind("<Double-Button-1>", lambda e: self.restore_from_floating_toolbar())
        drag_lbl.bind("<Double-Button-1>", lambda e: self.restore_from_floating_toolbar())

        self.show_toast("Đã Thu Nhỏ Nổi", "Đã thu nhỏ thành thanh Float On-Top! Rê chuột để sáng 100%, rời chuột tự làm mờ. Bấm '🗖 Mở Rộng' để mở lại.", "info", duration_ms=4000)

    def restore_from_floating_toolbar(self):
        """Khôi phục lại màn hình ứng dụng đầy đủ như ban đầu trước khi thu nhỏ."""
        if hasattr(self, "_float_win") and self._float_win and self._float_win.winfo_exists():
            try:
                self._float_win.destroy()
            except Exception:
                pass
            self._float_win = None

        self.deiconify()
        if hasattr(self, "_saved_main_geometry") and self._saved_main_geometry:
            try:
                self.geometry(self._saved_main_geometry)
            except Exception:
                pass

        if hasattr(self, "_saved_was_topmost"):
            try:
                self.attributes("-topmost", self._saved_was_topmost)
            except Exception:
                pass

        self.attributes("-alpha", 1.0)
        self.lift()
        self.focus_force()
        self.show_toast("Đã Phục Hồi", "Đã khôi phục lại màn hình ứng dụng ban đầu!", "success")


    def _on_root_configure(self, event):
        """Xử lý sự kiện thay đổi kích thước cửa sổ để tự động chuyển đổi giữa giao diện rộng và siêu gọn."""
        if event.widget == self:
            w = self.winfo_width()
            is_w = w >= 1050
            if getattr(self, "_is_wide_mode", None) != is_w:
                self._is_wide_mode = is_w
                self._update_adaptive_ui_labels()

    def _update_adaptive_ui_labels(self):
        """Tự động chuyển đổi giữa nhãn đầy đủ (Wide Mode) và nhãn siêu gọn (Compact Mode)."""
        is_w = getattr(self, "_is_wide_mode", False)
        is_running = not getattr(self.handler, 'is_paused', False)

        # 1. Header Row 1
        if hasattr(self, 'hdr_title_lbl') and self.hdr_title_lbl.winfo_exists():
            self.hdr_title_lbl.configure(text="⚡ AI Zalo CSKH - Tự Động Hóa & Quản Lý Giáo Án" if is_w else "⚡ AI CSKH")
        if hasattr(self, 'btn_header_reset_retries') and self.btn_header_reset_retries.winfo_exists():
            self.btn_header_reset_retries.configure(text="🔄 Reset Lỗi" if is_w else "🔄 Reset", padx=8 if is_w else 5)
        if hasattr(self, 'btn_emergency_cancel') and self.btn_emergency_cancel.winfo_exists():
            self.btn_emergency_cancel.configure(text="🛑 Hủy (F9)" if is_w else "🛑 Hủy", padx=8 if is_w else 5)
        if hasattr(self, 'btn_toggle_bot') and self.btn_toggle_bot.winfo_exists():
            self.btn_toggle_bot.configure(
                text=("⏸ Tạm Dừng Bot (F8)" if is_running else "▶ Tiếp Tục Bot (F8)") if is_w else ("⏸ Dừng Bot" if is_running else "▶ Bật Bot"),
                padx=10 if is_w else 6
            )
        if hasattr(self, 'btn_float_mini') and self.btn_float_mini.winfo_exists():
            self.btn_float_mini.configure(text="🪟 Nổi On-Top" if is_w else "🪟 Nổi", padx=7 if is_w else 5)
        if hasattr(self, 'btn_pin_top') and self.btn_pin_top.winfo_exists():
            if getattr(self, 'is_always_on_top', False):
                self.btn_pin_top.configure(text="📌 ĐÃ GHIM", padx=6 if is_w else 5)
            else:
                self.btn_pin_top.configure(text="📌 Ghim Top" if is_w else "📌 Ghim", padx=6 if is_w else 5)
        if hasattr(self, 'btn_header_logout') and self.btn_header_logout.winfo_exists():
            self.btn_header_logout.configure(text="🚪 Đăng Xuất" if is_w else "🚪 Thoát")
        if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
            self.status_lbl.configure(
                text=("● BOT ĐANG CHẠY (F8)" if is_running else "● ĐÃ TẠM DỪNG (F8)") if is_w else ("● BOT CHẠY (F8)" if is_running else "● TẠM DỪNG (F8)")
            )
        if hasattr(self, 'header_user_lbl') and self.header_user_lbl.winfo_exists() and self.current_logged_user:
            u_name = self.current_logged_user.get("username", "admin")
            role = "Admin" if self.current_logged_user.get("role") == "admin" else "User"
            self.header_user_lbl.configure(text=f"👤 {u_name} ({role})" if is_w else f"👤 {u_name}")

        # 2. Header Row 2 (Sub-bar)
        if hasattr(self, 'hdr_model_lbl') and self.hdr_model_lbl.winfo_exists():
            self.hdr_model_lbl.configure(text="🎯 MODEL:" if is_w else "🎯 Model:")
        if hasattr(self, 'btn_modal') and self.btn_modal.winfo_exists():
            self.btn_modal.configure(text="📋 Bảng Models" if is_w else "📋 Models", padx=8 if is_w else 5)
        if hasattr(self, 'btn_scope_toggle') and self.btn_scope_toggle.winfo_exists():
            allow_gen = getattr(self.gemini, 'allow_general_chat', True)
            self.btn_scope_toggle.configure(
                text=("🌐 Chế Độ AI" if allow_gen else "🔒 Chế Độ Giới Hạn Sử") if is_w else ("🌐 AI" if allow_gen else "🔒 Sử"),
                padx=12 if is_w else 7
            )
        if hasattr(self, 'gemini_status_lbl') and self.gemini_status_lbl.winfo_exists():
            self._update_header_status_label()

        # 3. Nav Tab Bar
        tab_names_wide = {
            "chat": "💬 Chat Live",
            "broadcast": "📢 Gửi Tin Nhóm",
            "script": "⚡ Kịch Bản Nhanh",
            "fake_drive": "🖼️ Fake Ảnh Drive",
            "crm": "👥 Khách Hàng (CRM)",
            "corrections": "📝 Sổ Tay Sửa"
        }
        tab_names_compact = {
            "chat": "💬 Chat",
            "broadcast": "📢 Gửi Nhóm",
            "script": "⚡ Kịch Bản",
            "fake_drive": "🖼️ Drive",
            "crm": "👥 CRM",
            "corrections": "📝 Sổ Tay"
        }
        if hasattr(self, 'tab_buttons'):
            for k, btn in self.tab_buttons.items():
                if btn.winfo_exists():
                    target_name = tab_names_wide.get(k) if is_w else tab_names_compact.get(k)
                    if target_name:
                        btn.configure(text=target_name, padx=10 if is_w else 6)

        if hasattr(self, 'btn_more_tabs') and self.btn_more_tabs.winfo_exists():
            cur_txt = self.btn_more_tabs.cget("text")
            if "▾" in cur_txt:
                is_sub = False
                for mk, mst, _, _ in getattr(self, 'MORE_TABS_CONFIG', []):
                    if mst in cur_txt:
                        is_sub = True
                        break
                if not is_sub:
                    self.btn_more_tabs.configure(text="🛠️ Xem Thêm (8) ▾" if is_w else "🛠️ Thêm (8) ▾", padx=10 if is_w else 6)

        if hasattr(self, 'btn_toggle_compact_mode') and self.btn_toggle_compact_mode.winfo_exists():
            if not self.header_is_compact:
                self.btn_toggle_compact_mode.configure(text="📐 Thu Gọn Header" if is_w else "📐 Thu Gọn", padx=8 if is_w else 5)
            else:
                self.btn_toggle_compact_mode.configure(text="📐 Mở Rộng Header" if is_w else "📐 Mở Rộng", padx=8 if is_w else 5)

    def _toggle_general_chat_scope(self):
        new_state = not self.gemini.allow_general_chat
        self.gemini.set_general_chat_mode(new_state)
        is_w = getattr(self, "_is_wide_mode", False)
        if new_state:
            self.btn_scope_toggle.config(
                text="🌐 Chế Độ AI" if is_w else "🌐 AI",
                bg="#059669"
            )
            self.show_toast("Chế Độ AI (BẬT)", "AI hiện có thể trả lời ngày giờ, thứ mấy, kiến thức tổng hợp và CSKH!", "success")
        else:
            self.btn_scope_toggle.config(
                text="🔒 Chế Độ Giới Hạn Sử" if is_w else "🔒 Sử",
                bg="#475569"
            )
            self.show_toast("Chế Độ Giới Hạn (TẮT)", "AI sẽ chỉ tập trung trả lời Giáo án Lịch sử 6-12.", "info")

    def _update_header_status_label(self):
        all_keys = self.key_mgr.get_all_keys()
        active_k = self.key_mgr.get_active_key() or ""
        total_k = len(all_keys)
        avail_k = sum(1 for k in all_keys if k["status"] in ("ACTIVE", "AVAILABLE"))
        is_w = getattr(self, "_is_wide_mode", False)
        if total_k > 0:
            masked = KeyManager.mask_key(active_k)
            if is_w:
                self.gemini_status_lbl.config(
                    text=f"● Key: {masked} | {avail_k}/{total_k} Keys Khả Dụng ({self.gemini.model_name})",
                    fg="#34d399"
                )
            else:
                self.gemini_status_lbl.config(
                    text=f"● {avail_k}/{total_k} Keys ({masked})",
                    fg="#34d399"
                )
        else:
            self.gemini_status_lbl.config(
                text="⚠️ Chưa có API Key (Vào Tab '🔑 Quản Lý API Keys & Models' để dán danh sách Key)" if is_w else "⚠️ Chưa có Key",
                fg="#fbbf24"
            )

    def _on_header_model_selected(self, event=None):
        selected_model = self.hdr_model_cb.get().strip()
        if selected_model:
            self.gemini.set_model(selected_model)
            if hasattr(self, "api_model_cb"):
                self.api_model_cb.set(selected_model)
            if hasattr(self, "pg_model_cb"):
                self.pg_model_cb.set(selected_model)
            if hasattr(self, "footer_model_lbl"):
                self.footer_model_lbl.configure(text=f"⚡ Model: {selected_model}")
            self._update_header_status_label()
            self.show_toast("Đổi Model", f"Đã chuyển tạm thời sang model '{selected_model}'", "info")

    def _activate_default_model_from_header(self):
        selected_model = self.hdr_model_cb.get().strip()
        if not selected_model:
            return
        self.gemini.set_model(selected_model)
        self.gemini.save_api_key_to_config(self.gemini.api_key)
        self._update_header_status_label()
        if hasattr(self, "api_model_cb"):
            self.api_model_cb.set(selected_model)
        if hasattr(self, "pg_model_cb"):
            self.pg_model_cb.set(selected_model)
        if hasattr(self, "footer_model_lbl"):
            self.footer_model_lbl.configure(text=f"⚡ Model: {selected_model}")
        self.show_toast("Thành Công", f"Đã lưu '{selected_model}' làm Model Mặc Định!", "success")

    def _open_model_selection_modal(self):
        modal = tk.Toplevel(self)
        modal.title("🎯 Bảng Lựa Chọn Model & Phiên Bản Gemini (Google AI Studio)")
        modal.geometry("920x580")
        modal.minsize(760, 490)
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()
        apply_windows_dark_titlebar(modal, "#0f172a", "#f8fafc")

        hdr = tk.Frame(modal, bg="#1e293b", padx=18, pady=14)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="🤖 DANH SÁCH CÁC PHIÊN BẢN MODEL GEMINI (GOOGLE AI STUDIO)",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        ).pack(anchor="w")

        table_frame = tk.Frame(modal, bg="#0f172a", padx=12, pady=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("name", "version", "speed", "desc", "status")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        tree.heading("name", text="Mã Model")
        tree.heading("version", text="Phiên Bản / Thế Hệ")
        tree.heading("speed", text="Tốc Độ")
        tree.heading("desc", text="Đặc Điểm & Ứng Dụng")
        tree.heading("status", text="Trạng Thái")

        tree.column("name", width=150)
        tree.column("version", width=140)
        tree.column("speed", width=120, anchor="center")
        tree.column("desc", width=340)
        tree.column("status", width=110, anchor="center")
        tree.pack(fill="both", expand=True)

        def _populate_table():
            for item in tree.get_children():
                tree.delete(item)
            all_models = self._get_active_model_list()
            for m in all_models:
                if m in MODEL_CATALOG:
                    ver, spd, desc, badge = MODEL_CATALOG[m]
                else:
                    ver, spd, desc, badge = ("Phiên bản API", "⚡ Tiêu chuẩn", "Model hỗ trợ tạo nội dung từ Google AI Studio.", "✅ KHẢ DỤNG")
                is_cur = "🟢 ĐANG DÙNG" if m == self.gemini.model_name else badge
                tree.insert("", "end", iid=m, values=(m, ver, spd, desc, is_cur))

        _populate_table()

        # Khung chứa các nút điều khiển & bộ lọc phía dưới modal
        act_bar = tk.Frame(modal, bg="#1e293b", padx=14, pady=10)
        act_bar.pack(fill="x", side="bottom")

        # Dropdown bộ lọc phiên bản model
        tk.Label(act_bar, text="🔍 Bộ lọc:", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b").pack(side="left", padx=(0, 4))
        cur_min_v = self.app_settings.get("min_gemini_version", GEMINI_VERSION_FILTER_OPTIONS[0])
        modal_filter_cb = ttk.Combobox(
            act_bar,
            values=GEMINI_VERSION_FILTER_OPTIONS,
            state="readonly",
            width=28
        )
        matched_opt = GEMINI_VERSION_FILTER_OPTIONS[0]
        for opt in GEMINI_VERSION_FILTER_OPTIONS:
            if str(cur_min_v) in opt or opt in str(cur_min_v):
                matched_opt = opt
                break
        modal_filter_cb.set(matched_opt)
        modal_filter_cb.pack(side="left", padx=(0, 10))

        def _on_modal_filter_changed(event=None):
            self.app_settings["min_gemini_version"] = modal_filter_cb.get()
            self._save_app_settings(self.app_settings)
            self._refresh_all_model_comboboxes()
            _populate_table()

        modal_filter_cb.bind("<<ComboboxSelected>>", _on_modal_filter_changed)

        btn_rescan = tk.Button(
            act_bar,
            text="🔄 Quét Lại",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=_populate_table
        )
        btn_rescan.pack(side="left", padx=(0, 8))

        def _do_activate_selected():
            sel = tree.selection()
            if not sel:
                self.show_toast("Thông Báo", "Vui lòng chọn 1 Model trong bảng!", "warning")
                return
            chosen = sel[0]
            self.gemini.set_model(chosen)
            self.gemini.save_api_key_to_config(self.gemini.api_key)
            self.hdr_model_cb.set(chosen)
            if hasattr(self, "api_model_cb"):
                self.api_model_cb.set(chosen)
            if hasattr(self, "pg_model_cb"):
                self.pg_model_cb.set(chosen)
            self._update_header_status_label()
            self.show_toast("Thành Công", f"Đã kích hoạt Model '{chosen}' làm Mặc Định!", "success")
            modal.destroy()

        btn_act = tk.Button(act_bar, text="⭐ Kích Hoạt & Đặt Làm Mặc Định", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=_do_activate_selected)
        btn_act.pack(side="left", padx=5)

        btn_cls = tk.Button(act_bar, text="Đóng", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=12, pady=4, cursor="hand2", command=modal.destroy)
        btn_cls.pack(side="right", padx=5)

    def _build_main_tabs(self):
        """
        Xây dựng Thanh Điều Hướng Cao Cấp (Modern Segmented Navigation Bar):
        - Đưa Tab 1 (Chat), Tab 2 (Gửi Nhóm), Tab 3 (Kịch Bản) và các tính năng hay dùng nhất (CRM, Sổ Tay, Drive) lên đầu dạng Pill buttons.
        - Rút gọn các công cụ mở rộng vào nút "🛠️ Thêm ▾" với Popup Menu trực quan.
        - Nút "📐 Thu Gọn" để tối ưu hóa không gian làm việc.
        """
        # 1. Khung Thanh Điều Hướng Nav Bar Cao Cấp
        self.nav_frame = tk.Frame(self, bg="#0f172a", padx=8, pady=4, highlightbackground="#1e293b", highlightthickness=1)
        self.nav_frame.pack(fill="x", padx=10, pady=(3, 0))

        # 2. Khởi tạo Notebook ẩn thanh tab mặc định
        self.main_notebook = ttk.Notebook(self, style="Hidden.TNotebook")
        self.main_notebook.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        self.tab_frames = {}
        self.tab_buttons = {}
        self.tab_indices = {}
        self.active_main_tab = "chat"

        # 3. DANH SÁCH 6 TAB CHÍNH (ĐƯA TAB 1, 2, 3 VÀ CHỨC NĂNG HAY DÙNG LÊN ĐẦU, TÊN SIÊU GỌN)
        self.CORE_TABS_CONFIG = [
            ("chat", "💬 Chat", "💬 Hội Thoại & Chat Trực Tiếp", self._build_chat_tab, "#0284c7"),
            ("broadcast", "📢 Gửi Nhóm", "📢 Gửi Tin Nhóm & Lên Lịch (Broadcast)", self._build_broadcast_tab, "#059669"),
            ("script", "⚡ Kịch Bản", "⚡ Kịch Bản Trả Lời Nhanh", self._build_script_templates_tab, "#8b5cf6"),
            ("fake_drive", "🖼️ Drive", "🖼️ Fake Ảnh Mockup Drive & Bắn Zalo", self._build_fake_drive_tab, "#ea580c"),
            ("crm", "👥 CRM", "👥 Khách Hàng & Khối Mua", self._build_customers_tab, "#0d9488"),
            ("corrections", "📝 Sổ Tay", "📝 Sổ Tay Sửa Giáo Án", self._build_corrections_tab, "#f59e0b"),
        ]

        # 4. DANH SÁCH 8 TAB MỞ RỘNG (GỌI QUA NÚT 'XEM THÊM' THU GỌN GIAO DIỆN)
        self.MORE_TABS_CONFIG = [
            ("drive", "🔗 Google Drive", "🔗 Link & Phân Quyền Drive", self._build_drive_tab),
            ("keys", "🔑 Quản Lý API Keys", "🔑 Quản Lý API Keys & Models", self._build_api_keys_tab),
            ("playground", "🧠 AI Playground", "🧠 AI Playground & Test Suy Luận", self._build_playground_tab),
            ("live_test", "🎯 Test Zalo PC", "🎯 Test Zalo PC (Test 1 -> 5)", self._build_live_test_tab),
            ("search", "🔍 Tìm Nhanh File", "🔍 Tìm Nhanh File Máy Tính", self._build_search_tab),
            ("sim", "🧪 Giả Lập Kịch Bản", "🧪 Giả Lập Kịch Bản Mẫu", self._build_simulator_tab),
            ("console", "📟 Console Live", "📟 Console Live Pipeline", self._build_console_tab),
            ("settings", "⚙️ Cài Đặt Ứng Dụng", "⚙️ Cài Đặt Ứng Dụng", self._build_settings_tab),
        ]

        # 5. Xây dựng các Tab Frames trong Notebook
        all_tabs = [(k, st, ft, bldr) for k, st, ft, bldr, _ in self.CORE_TABS_CONFIG] + self.MORE_TABS_CONFIG
        for idx, (key, short_title, full_title, builder) in enumerate(all_tabs):
            tab_f = tk.Frame(self.main_notebook, bg="#0f172a", padx=8, pady=8)
            self.main_notebook.add(tab_f, text=full_title)
            self.tab_frames[key] = tab_f
            self.tab_indices[key] = idx
            builder(tab_f)

        # 6. Render các nút điều hướng trên Thanh Nav Bar
        nav_left = tk.Frame(self.nav_frame, bg="#0f172a")
        nav_left.pack(side="left", fill="y")

        for key, short_title, _, _, color in self.CORE_TABS_CONFIG:
            btn = tk.Button(
                nav_left,
                text=short_title,
                font=("Segoe UI", 8, "bold" if key == "chat" else "normal"),
                bg=color if key == "chat" else "#1e293b",
                fg="white" if key == "chat" else "#cbd5e1",
                activebackground=color,
                activeforeground="white",
                relief="flat",
                padx=6,
                pady=3,
                cursor="hand2",
                command=lambda k=key: self._switch_main_tab(k)
            )
            btn.pack(side="left", padx=2)
            self.tab_buttons[key] = btn

        # Nút "🛠️ Thêm (8) ▾"
        self.btn_more_tabs = tk.Button(
            nav_left,
            text="🛠️ Thêm (8) ▾",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#0284c7",
            activeforeground="white",
            relief="flat",
            padx=6,
            pady=3,
            cursor="hand2",
            command=self._show_more_tabs_dropdown
        )
        self.btn_more_tabs.pack(side="left", padx=(3, 2))

        # Nút Thu Gọn / Mở Rộng Header phía bên phải
        self.header_is_compact = False
        self.btn_toggle_compact_mode = tk.Button(
            self.nav_frame,
            text="📐 Thu Gọn",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=6,
            pady=3,
            cursor="hand2",
            command=self._toggle_compact_header
        )
        self.btn_toggle_compact_mode.pack(side="right", padx=2)

        # Mặc định kích hoạt tab Chat
        self._switch_main_tab("chat")

    def _switch_main_tab(self, target_key: str):
        """Chuyển đổi tab hiển thị và cập nhật giao diện thanh điều hướng."""
        if target_key not in self.tab_indices:
            return

        idx = self.tab_indices[target_key]
        self.main_notebook.select(idx)
        self.active_main_tab = target_key

        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        inact_bg = "#f1f5f9" if is_light else "#1e293b"
        inact_fg = "#475569" if is_light else "#cbd5e1"

        # 1. Cập nhật trạng thái màu sắc cho các nút Core Tabs
        for key, short_title, _, _, color in self.CORE_TABS_CONFIG:
            btn = self.tab_buttons.get(key)
            if btn:
                if key == target_key:
                    btn.configure(bg=color, fg="white", font=("Segoe UI", 8, "bold"))
                else:
                    btn.configure(bg=inact_bg, fg=inact_fg, font=("Segoe UI", 8))

        # 2. Cập nhật nút "Xem Thêm"
        is_more = False
        for key, short_title, _, _ in self.MORE_TABS_CONFIG:
            if key == target_key:
                is_more = True
                self.btn_more_tabs.configure(text=f"🛠️ {short_title} ▾", bg="#8b5cf6", fg="white", font=("Segoe UI", 8, "bold"))
                break

        if not is_more:
            self.btn_more_tabs.configure(text="🛠️ Thêm (8) ▾", bg=inact_bg, fg=inact_fg, font=("Segoe UI", 8))

        if hasattr(self, 'btn_toggle_compact_mode') and self.btn_toggle_compact_mode.winfo_exists():
            self.btn_toggle_compact_mode.configure(bg=inact_bg, fg=inact_fg)

    def _show_more_tabs_dropdown(self):
        """Hiển thị Popup Menu danh sách các công cụ mở rộng khi bấm nút Xem Thêm."""
        menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", font=("Segoe UI", 9))
        for key, short_title, full_title, _ in self.MORE_TABS_CONFIG:
            menu.add_command(
                label=f"  {short_title}  ",
                command=lambda k=key: self._switch_main_tab(k)
            )
        try:
            x = self.btn_more_tabs.winfo_rootx()
            y = self.btn_more_tabs.winfo_rooty() + self.btn_more_tabs.winfo_height() + 2
            menu.post(x, y)
        except Exception:
            pass
        except Exception:
            pass

    def _toggle_compact_header(self):
        """Thu gọn hoặc mở rộng Header để tiết kiệm tối đa diện tích làm việc."""
        if not hasattr(self, 'header_is_compact'):
            self.header_is_compact = False

        is_light = getattr(self, "current_theme", "light_theme") in ("light_theme", "light")
        btn_bg = "#e2e8f0" if is_light else "#1e293b"

        if not self.header_is_compact:
            if hasattr(self, 'header_frame'):
                self.header_frame.pack_forget()
            if hasattr(self, 'header_sub_bar'):
                self.header_sub_bar.pack_forget()
            self.btn_toggle_compact_mode.configure(text="📐 Mở Rộng", fg="#0284c7" if is_light else "#38bdf8", bg=btn_bg)
            self.header_is_compact = True
            self.show_toast("Chế Độ Thu Gọn", "Đã thu gọn Header để mở rộng tối đa diện tích làm việc!", "info", duration_ms=2000)
        else:
            if hasattr(self, 'header_frame'):
                self.header_frame.pack(side="top", fill="x", before=self.nav_frame)
            if hasattr(self, 'header_sub_bar'):
                self.header_sub_bar.pack(side="top", fill="x", before=self.nav_frame)
            self.btn_toggle_compact_mode.configure(text="📐 Thu Gọn", fg="#475569" if is_light else "#94a3b8", bg=btn_bg)
            self.header_is_compact = False
            self.show_toast("Chế Độ Đầy Đủ", "Đã mở lại Header!", "info", duration_ms=2000)

    def _switch_to_settings_tab(self):
        """Chuyển nhanh đến Tab Cài Đặt Ứng Dụng."""
        self._switch_main_tab("settings")

    def _toggle_theme_quick(self):
        """Chuyển đổi nhanh giữa các chế độ Giao diện Sáng và Tối (Tailwind / Slate)."""
        if self.current_theme in ("tailwind_light", "light_theme", "light"):
            new_theme = "tailwind_dark" if self.current_theme == "tailwind_light" else "slate_dark"
        else:
            new_theme = "tailwind_light" if self.current_theme == "tailwind_dark" else "light_theme"
        self._apply_theme(new_theme, show_toast_msg=True)

    def _apply_theme(self, theme_name: str, show_toast_msg: bool = True):
        """
        Áp dụng toàn diện Giao diện Sáng (Light / Tailwind Light) hoặc Giao diện Tối (Dark Slate / Tailwind Dark).
        Đảm bảo 100% các thành phần, khung nền, bong bóng chat, bảng biểu và nút bấm đồng bộ màu sắc hài hòa.
        """
        if not theme_name:
            theme_name = "tailwind_light"
        self.current_theme = theme_name

        if theme_name in ("tailwind_light", "light_theme", "light"):
            is_light = True
            if theme_name == "tailwind_light":
                app_bg = "#f8fafc"           # Tailwind Slate-50
                card_bg = "#ffffff"          # Pure White
                card_border = "#e2e8f0"      # Tailwind Slate-200
                header_bg = "#ffffff"        # Pure White
                sub_bar_bg = "#f1f5f9"       # Tailwind Slate-100
                nav_bg = "#ffffff"           # Pure White
                text_main = "#0f172a"        # Tailwind Slate-900
                text_sub = "#475569"         # Tailwind Slate-600
                text_accent = "#4f46e5"      # Tailwind Indigo-600
                input_bg = "#ffffff"         # Pure White
                input_fg = "#0f172a"         # Tailwind Slate-900
                btn_inactive_bg = "#f1f5f9"  # Tailwind Slate-100
                btn_inactive_fg = "#334155"  # Tailwind Slate-700
                tree_head_bg = "#f1f5f9"
                tree_head_fg = "#4f46e5"
                titlebar_bg = "#ffffff"
                titlebar_fg = "#0f172a"
            else:  # light_theme
                app_bg = "#f1f5f9"           # Slate-100
                card_bg = "#ffffff"          # Pure White
                card_border = "#cbd5e1"      # Slate-300
                header_bg = "#ffffff"        # Pure White
                sub_bar_bg = "#f8fafc"       # Slate-50
                nav_bg = "#ffffff"           # Pure White
                text_main = "#0f172a"        # Slate-900
                text_sub = "#475569"         # Slate-600
                text_accent = "#0284c7"      # Sky-600
                input_bg = "#ffffff"         # Pure White
                input_fg = "#0f172a"         # Slate-900
                btn_inactive_bg = "#e2e8f0"  # Slate-200
                btn_inactive_fg = "#1e293b"  # Slate-800
                tree_head_bg = "#e2e8f0"
                tree_head_fg = "#0369a1"
                titlebar_bg = "#ffffff"
                titlebar_fg = "#0f172a"
        else:
            is_light = False
            if theme_name == "tailwind_dark":
                app_bg = "#09090b"           # Tailwind Zinc-950
                card_bg = "#18181b"          # Tailwind Zinc-900
                card_border = "#27272a"      # Tailwind Zinc-800
                header_bg = "#18181b"        # Tailwind Zinc-900
                sub_bar_bg = "#27272a"       # Tailwind Zinc-800
                nav_bg = "#18181b"           # Tailwind Zinc-900
                text_main = "#fafafa"        # Tailwind Zinc-50
                text_sub = "#a1a1aa"         # Tailwind Zinc-400
                text_accent = "#a855f7"      # Tailwind Purple-500
                input_bg = "#27272a"         # Tailwind Zinc-800
                input_fg = "#fafafa"         # Tailwind Zinc-50
                btn_inactive_bg = "#27272a"  # Tailwind Zinc-800
                btn_inactive_fg = "#d4d4d8"  # Tailwind Zinc-300
                tree_head_bg = "#27272a"
                tree_head_fg = "#c084fc"
                titlebar_bg = "#18181b"
                titlebar_fg = "#fafafa"
            elif theme_name == "midnight_black":
                app_bg = "#000000"
                card_bg = "#0a0a0a"
                card_border = "#1f1f1f"
                header_bg = "#0a0a0a"
                sub_bar_bg = "#171717"
                nav_bg = "#0a0a0a"
                text_main = "#ffffff"
                text_sub = "#a3a3a3"
                text_accent = "#38bdf8"
                input_bg = "#171717"
                input_fg = "#ffffff"
                btn_inactive_bg = "#171717"
                btn_inactive_fg = "#e5e5e5"
                tree_head_bg = "#171717"
                tree_head_fg = "#38bdf8"
                titlebar_bg = "#000000"
                titlebar_fg = "#ffffff"
            elif theme_name == "ocean_blue":
                app_bg = "#0c1829"
                card_bg = "#112240"
                card_border = "#1d3557"
                header_bg = "#112240"
                sub_bar_bg = "#1b335a"
                nav_bg = "#112240"
                text_main = "#e6f1ff"
                text_sub = "#8892b0"
                text_accent = "#64ffda"
                input_bg = "#1b335a"
                input_fg = "#e6f1ff"
                btn_inactive_bg = "#1b335a"
                btn_inactive_fg = "#ccd6f6"
                tree_head_bg = "#1b335a"
                tree_head_fg = "#64ffda"
                titlebar_bg = "#0c1829"
                titlebar_fg = "#e6f1ff"
            else:  # slate_dark
                app_bg = "#0b0f19"           # Slate-950
                card_bg = "#0f172a"          # Slate-900
                card_border = "#1e293b"      # Slate-800
                header_bg = "#0f172a"        # Slate-900
                sub_bar_bg = "#1e293b"       # Slate-800
                nav_bg = "#0f172a"           # Slate-900
                text_main = "#f8fafc"        # Slate-50
                text_sub = "#94a3b8"         # Slate-400
                text_accent = "#38bdf8"      # Sky-400
                input_bg = "#1e293b"         # Slate-800
                input_fg = "#f8fafc"         # Slate-50
                btn_inactive_bg = "#1e293b"  # Slate-800
                btn_inactive_fg = "#cbd5e1"  # Slate-300
                tree_head_bg = "#1e293b"
                tree_head_fg = "#38bdf8"
                titlebar_bg = "#0f172a"
                titlebar_fg = "#f8fafc"

        # 1. Cập nhật cửa sổ gốc
        self.configure(bg=app_bg)

        # 2. Cập nhật ttk.Style
        try:
            style = ttk.Style(self)
            style.configure("Treeview", background=input_bg, foreground=input_fg, fieldbackground=input_bg)
            style.configure("Treeview.Heading", background=tree_head_bg, foreground=tree_head_fg)
            style.configure("TNotebook", background=app_bg)
            style.configure("CustomNav.TNotebook", background=app_bg)
            style.configure("Hidden.TNotebook", background=app_bg)
        except Exception:
            pass

        # 3. Quét đệ quy toàn bộ widget để áp dụng màu sắc
        self._apply_theme_to_widget_recursive(
            self,
            is_light=is_light,
            card_bg=card_bg,
            app_bg=app_bg,
            header_bg=header_bg,
            sub_bar_bg=sub_bar_bg,
            nav_bg=nav_bg,
            text_main=text_main,
            text_sub=text_sub,
            input_bg=input_bg,
            input_fg=input_fg,
            btn_inactive_bg=btn_inactive_bg,
            btn_inactive_fg=btn_inactive_fg
        )

        # 4. Cập nhật các khung chính
        if hasattr(self, 'header_frame') and self.header_frame.winfo_exists():
            self.header_frame.configure(bg=header_bg)
        if hasattr(self, 'header_sub_bar') and self.header_sub_bar.winfo_exists():
            self.header_sub_bar.configure(bg=sub_bar_bg)
        if hasattr(self, 'nav_frame') and self.nav_frame.winfo_exists():
            self.nav_frame.configure(bg=nav_bg, highlightbackground=card_border)
        if hasattr(self, 'footer_frame') and self.footer_frame.winfo_exists():
            self.footer_frame.configure(bg=card_bg, highlightbackground=card_border)

        # 5. Cập nhật Tags và màu sắc cho Khung Chat Log Text
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.configure(bg=input_bg, fg=input_fg, insertbackground=input_fg)
            if is_light:
                self.log_text.tag_config("TIME", foreground="#64748b", font=("Consolas", 8))
                self.log_text.tag_config("USER_HDR", foreground="#4338ca", font=("Segoe UI", 9, "bold"), justify="right")
                self.log_text.tag_config("USER_BUBBLE", background="#4f46e5", foreground="#ffffff", justify="right", lmargin1=120, lmargin2=120, rmargin=12, spacing1=4, spacing3=8)
                self.log_text.tag_config("AI_HDR", foreground="#065f46", font=("Segoe UI", 9, "bold"), justify="left")
                self.log_text.tag_config("AI_BUBBLE", background="#f1f5f9", foreground="#0f172a", justify="left", lmargin1=12, lmargin2=12, rmargin=120, spacing1=4, spacing3=8)
                self.log_text.tag_config("SYS_BADGE", foreground="#7c3aed", font=("Segoe UI", 8, "italic"), justify="center")
            else:
                self.log_text.tag_config("TIME", foreground="#64748b", font=("Consolas", 8))
                self.log_text.tag_config("USER_HDR", foreground="#818cf8", font=("Segoe UI", 9, "bold"), justify="right")
                self.log_text.tag_config("USER_BUBBLE", background="#3730a3", foreground="#ffffff", justify="right", lmargin1=120, lmargin2=120, rmargin=12, spacing1=4, spacing3=8)
                self.log_text.tag_config("AI_HDR", foreground="#34d399", font=("Segoe UI", 9, "bold"), justify="left")
                self.log_text.tag_config("AI_BUBBLE", background="#064e3b", foreground="#ecfdf5", justify="left", lmargin1=12, lmargin2=12, rmargin=120, spacing1=4, spacing3=8)
                self.log_text.tag_config("SYS_BADGE", foreground="#a78bfa", font=("Segoe UI", 8, "italic"), justify="center")

        # 6. Cập nhật nút bấm Theme trong Header (Chỉ hiện ☀️ Sáng / 🌙 Tối)
        if hasattr(self, 'btn_theme_toggle') and self.btn_theme_toggle.winfo_exists():
            if is_light:
                self.btn_theme_toggle.configure(text="☀️ Sáng", bg="#f59e0b", fg="black")
            else:
                self.btn_theme_toggle.configure(text="🌙 Tối", bg="#334155", fg="#f8fafc")

        if hasattr(self, 'setting_theme_var'):
            self.setting_theme_var.set(theme_name)

        # 7. Đồng bộ lại thanh tiêu đề Windows
        apply_windows_dark_titlebar(self, titlebar_bg, titlebar_fg)

        # 8. Cập nhật thanh tab navigation bar và danh sách hội thoại
        if hasattr(self, 'active_main_tab'):
            self._switch_main_tab(self.active_main_tab)

        if hasattr(self, 'chat_sessions_tree') and self.chat_sessions_tree.winfo_exists():
            self._refresh_chat_sessions_list(keep_current=True)

        if hasattr(self, 'current_chat_session_id') and self.current_chat_session_id:
            self._load_chat_session(self.current_chat_session_id)

        # 8.5. Đồng bộ giao diện Kho Tệp Đính Kèm & Link Khối (Tab 3)
        if hasattr(self, 'btn_switch_bundle_files') and hasattr(self, 'btn_switch_bundle_links'):
            v_mode = getattr(self, 'script_bundle_view_mode', 'files')
            act_b = self.btn_switch_bundle_files if v_mode == 'files' else self.btn_switch_bundle_links
            inact_b = self.btn_switch_bundle_links if v_mode == 'files' else self.btn_switch_bundle_files
            act_b.configure(bg="#0284c7", fg="white")
            inact_b.configure(bg=btn_inactive_bg, fg=btn_inactive_fg)
        if hasattr(self, 'quick_links_selected_grade'):
            self._render_quick_links_for_category(self.quick_links_selected_grade)

        # 9. Lưu vào cấu hình
        self.app_settings["theme"] = theme_name
        self._save_app_settings_to_file(self.app_settings)

        if show_toast_msg:
            theme_title = "Giao Diện Sáng" if is_light else "Giao Diện Tối"
            self.show_toast("Đổi Giao Diện", f"Đã áp dụng thành công: {theme_title}!", "success")

    def _apply_theme_to_widget_recursive(
        self,
        w,
        is_light: bool,
        card_bg: str,
        app_bg: str,
        header_bg: str,
        sub_bar_bg: str,
        nav_bg: str,
        text_main: str,
        text_sub: str,
        input_bg: str,
        input_fg: str,
        btn_inactive_bg: str,
        btn_inactive_fg: str
    ):
        """Đệ quy quét và điều chỉnh màu sắc cho từng loại widget để đồng bộ 100% sáng/tối."""
        w_class = w.winfo_class()

        ALL_THEME_BGS = {
            "#0b0f19", "#0f172a", "#1e293b", "#334155", "#475569",
            "#09090b", "#18181b", "#27272a", "#000000", "#0a0a0a",
            "#0d0d0d", "#171717", "#1f1f1f", "#0c1829", "#112240",
            "#1b335a", "#1d3557", "#233554",
            "#ffffff", "#f8fafc", "#f1f5f9", "#e2e8f0", "#cbd5e1",
            "#f9fafb", "#f3f4f6", "#e5e7eb"
        }

        PRESERVED_BUTTON_COLORS = [
            "#dc2626", "#e11d48", "#ef4444",  # Red
            "#059669", "#10b981", "#22c55e",  # Green
            "#0284c7", "#0ea5e9", "#2563eb", "#3b82f6",  # Blue
            "#6366f1", "#8b5cf6", "#7c3aed", "#9333ea",  # Purple / Indigo
            "#0d9488", "#14b8a6",              # Teal
            "#d97706", "#f59e0b", "#b45309"   # Amber
        ]

        try:
            if w_class in ("Frame", "Panedwindow", "Canvas"):
                cur_bg = w.cget("bg")
                if cur_bg in ALL_THEME_BGS:
                    target_bg = card_bg if cur_bg not in ("#0b0f19", "#09090b", "#000000", "#0c1829", "#f8fafc", "#f1f5f9") else app_bg
                    w.configure(bg=target_bg)

            elif w_class == "Labelframe":
                w.configure(bg=card_bg, fg=text_main)

            elif w_class == "Label":
                cur_bg = w.cget("bg")
                cur_fg = w.cget("fg")
                if cur_bg in ALL_THEME_BGS:
                    w.configure(bg=card_bg)
                if is_light:
                    if cur_fg in ("#f8fafc", "#f1f5f9", "#ffffff", "#fafafa", "#e2e8f0"):
                        w.configure(fg=text_main)
                    elif cur_fg in ("#94a3b8", "#cbd5e1", "#64748b", "#a1a1aa", "#8892b0"):
                        w.configure(fg=text_sub)
                    elif cur_fg in ("#38bdf8", "#64ffda", "#00f2fe"):
                        w.configure(fg="#0284c7")
                    elif cur_fg in ("#34d399", "#86efac"):
                        w.configure(fg="#059669")
                    elif cur_fg in ("#fbbf24", "#fde047"):
                        w.configure(fg="#d97706")
                    elif cur_fg in ("#a78bfa", "#c084fc", "#d8b4fe"):
                        w.configure(fg="#7c3aed")
                else:
                    if cur_fg in ("#0f172a", "#1e293b", "#000000", "#18181b", "#334155"):
                        w.configure(fg=text_main)
                    elif cur_fg in ("#475569", "#64748b"):
                        w.configure(fg=text_sub)
                    elif cur_fg in ("#0284c7", "#0369a1"):
                        w.configure(fg="#38bdf8")
                    elif cur_fg in ("#059669", "#047857"):
                        w.configure(fg="#34d399")
                    elif cur_fg in ("#d97706", "#b45309"):
                        w.configure(fg="#fbbf24")
                    elif cur_fg in ("#7c3aed", "#6d28d9"):
                        w.configure(fg="#a78bfa")

            elif w_class in ("Entry", "Spinbox"):
                w.configure(bg=input_bg, fg=input_fg, insertbackground=input_fg)

            elif w_class == "Text":
                if not hasattr(self, 'log_text') or w != self.log_text:
                    w.configure(bg=input_bg, fg=input_fg, insertbackground=input_fg)

            elif w_class == "Listbox":
                w.configure(bg=input_bg, fg=input_fg)

            elif w_class in ("Checkbutton", "Radiobutton"):
                sel_bg = "#ffffff" if is_light else btn_inactive_bg
                w.configure(bg=card_bg, selectcolor=sel_bg, activebackground=card_bg)
                if is_light:
                    if w.cget("fg") in ("#f8fafc", "#ffffff", "#fafafa", "#cbd5e1", "#94a3b8"):
                        w.configure(fg=text_main)
                else:
                    if w.cget("fg") in ("#0f172a", "#1e293b", "#334155"):
                        w.configure(fg=text_main)

            elif w_class == "Button":
                cur_bg = w.cget("bg")
                is_preserved = False
                for p_col in PRESERVED_BUTTON_COLORS:
                    if p_col.lower() in cur_bg.lower():
                        is_preserved = True
                        w.configure(fg="white")
                        break
                if not is_preserved:
                    if cur_bg in ALL_THEME_BGS:
                        w.configure(bg=btn_inactive_bg, fg=btn_inactive_fg)
        except Exception:
            pass

        try:
            for child in w.winfo_children():
                self._apply_theme_to_widget_recursive(
                    child,
                    is_light,
                    card_bg,
                    app_bg,
                    header_bg,
                    sub_bar_bg,
                    nav_bg,
                    text_main,
                    text_sub,
                    input_bg,
                    input_fg,
                    btn_inactive_bg,
                    btn_inactive_fg
                )
        except Exception:
            pass

    # ---------------- TAB 1: CHAT REALTIME & LỊCH SỬ TRÒ CHUYỆN (TAILWIND BUBBLES + COPY BUTTON + SESSIONS) ----------------
    def _build_chat_tab(self, parent):
        paned = tk.PanedWindow(parent, orient="horizontal", bg="#1e293b", sashwidth=4)
        paned.pack(fill="both", expand=True)

        # ==================== CỘT TRÁI: LỊCH SỬ TRÒ CHUYỆN (SESSIONS / HỘI THOẠI) ====================
        left_frame = tk.Frame(paned, bg="#0f172a", padx=6, pady=6)
        paned.add(left_frame, minsize=360, width=410)

        # Header: Tiêu đề + Nút Tạo Chat Mới
        left_top_bar = tk.Frame(left_frame, bg="#0f172a")
        left_top_bar.pack(fill="x", pady=(0, 4))

        tk.Label(left_top_bar, text="💬 LỊCH SỬ HỘI THOẠI", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(side="left")

        btn_new_chat = tk.Button(
            left_top_bar,
            text="➕ Chat Mới",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._create_new_chat_session
        )
        btn_new_chat.pack(side="right")

        # Thanh chuyển đổi Danh Mục: [ 💬 Đang Mở ] vs [ 📦 Đã Lưu Trữ ]
        mode_f = tk.Frame(left_frame, bg="#0f172a")
        mode_f.pack(fill="x", pady=(2, 5))

        self.btn_chat_mode_active = tk.Button(
            mode_f,
            text="💬 Đang Mở",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self._set_chat_view_mode("active")
        )
        self.btn_chat_mode_active.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_chat_mode_archived = tk.Button(
            mode_f,
            text="📦 Đã Lưu Trữ",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self._set_chat_view_mode("archived")
        )
        self.btn_chat_mode_archived.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Bảng Treeview danh sách phiên trò chuyện
        tree_f = tk.Frame(left_frame, bg="#0f172a")
        tree_f.pack(fill="both", expand=True)

        cols = ("id", "title", "count", "time")
        self.chat_sessions_tree = ttk.Treeview(tree_f, columns=cols, show="headings", height=14, selectmode="browse")
        self.chat_sessions_tree.heading("id", text="ID")
        self.chat_sessions_tree.heading("title", text="Chủ Đề Cuộc Trò Chuyện")
        self.chat_sessions_tree.heading("count", text="Tin")
        self.chat_sessions_tree.heading("time", text="Cập Nhật")

        self.chat_sessions_tree.column("id", width=30, anchor="center")
        self.chat_sessions_tree.column("title", width=185, anchor="w")
        self.chat_sessions_tree.column("count", width=42, anchor="center")
        self.chat_sessions_tree.column("time", width=110, anchor="center")

        sb_tree_y = tk.Scrollbar(tree_f, orient="vertical", command=self.chat_sessions_tree.yview)
        self.chat_sessions_tree.configure(yscrollcommand=sb_tree_y.set)
        self.chat_sessions_tree.pack(side="left", fill="both", expand=True)
        sb_tree_y.pack(side="right", fill="y")

        self.chat_sessions_tree.bind("<<TreeviewSelect>>", self._on_chat_session_selected)
        self.chat_sessions_tree.bind("<Double-1>", lambda e: self._open_selected_chat_session())
        self.chat_sessions_tree.bind("<Button-3>", self._show_chat_session_context_menu)

        # Thanh công cụ thao tác nhanh phiên trò chuyện
        action_bar = tk.Frame(left_frame, bg="#0f172a", pady=5)
        action_bar.pack(fill="x")

        btn_open = tk.Button(action_bar, text="📂 Mở", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._open_selected_chat_session)
        btn_open.pack(side="left", padx=1)

        btn_rename = tk.Button(action_bar, text="✏️ Đổi Tên", bg="#334155", fg="#38bdf8", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._rename_selected_chat_session)
        btn_rename.pack(side="left", padx=1)

        self.btn_archive_toggle = tk.Button(action_bar, text="📦 Lưu Trữ", bg="#334155", fg="#fbbf24", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._toggle_archive_selected_chat_session)
        self.btn_archive_toggle.pack(side="left", padx=1)

        btn_del = tk.Button(action_bar, text="🗑️ Xóa", bg="#334155", fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._delete_selected_chat_session)
        btn_del.pack(side="left", padx=1)

        btn_clear_all = tk.Button(action_bar, text="🧹 Xóa Hết", bg="#dc2626", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._clear_all_chat_sessions_from_ui)
        btn_clear_all.pack(side="right", padx=1)

        # Context Menu chuột phải
        self.chat_session_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", activeforeground="white")
        self.chat_session_menu.add_command(label="📂 Mở Cuộc Trò Chuyện Này", command=self._open_selected_chat_session)
        self.chat_session_menu.add_command(label="✏️ Đổi Tên Cuộc Trò Chuyện...", command=self._rename_selected_chat_session)
        self.chat_session_menu.add_command(label="📦 Chuyển Vào Lưu Trữ / Bỏ Lưu Trữ", command=self._toggle_archive_selected_chat_session)
        self.chat_session_menu.add_separator()
        self.chat_session_menu.add_command(label="🗑️ Xóa Cuộc Trò Chuyện Này", command=self._delete_selected_chat_session)

        # ==================== CỘT PHẢI: KHUNG TRÒ CHUYỆN AI & BUBBLE COPY ====================
        right_frame = tk.Frame(paned, bg="#0f172a", padx=8, pady=5)
        paned.add(right_frame, minsize=520)

        top_chat_bar = tk.Frame(right_frame, bg="#0f172a")
        top_chat_bar.pack(fill="x", pady=(0, 4))
        
        self.chat_current_title_lbl = tk.Label(top_chat_bar, text="💬 Cuộc Trò Chuyện Hiện Tại", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#38bdf8")
        self.chat_current_title_lbl.pack(side="left")

        # Nút Copy, Ghi Chú & Xóa trên thanh công cụ (bố cục cân đối, chữ rõ ràng)
        btn_clear_chat = tk.Button(
            top_chat_bar,
            text="🧹 Xóa Chat",
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._clear_current_session_messages
        )
        btn_clear_chat.pack(side="right", padx=2)

        btn_copy_all = tk.Button(
            top_chat_bar,
            text="📋 Copy Hết",
            bg="#475569",
            fg="#f8fafc",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._copy_all_tab1_chat
        )
        btn_copy_all.pack(side="right", padx=2)

        btn_copy_sel = tk.Button(
            top_chat_bar,
            text="✂️ Copy Đoạn Chọn",
            bg="#0284c7",
            fg="#f8fafc",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._on_log_text_copy(None)
        )
        btn_copy_sel.pack(side="right", padx=2)

        btn_quick_notes = tk.Button(
            top_chat_bar,
            text="📝 Sổ Tay Ghi Chú",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_quick_notes_modal
        )
        btn_quick_notes.pack(side="right", padx=2)

        btn_copy_ai = tk.Button(
            top_chat_bar,
            text="🤖 Copy AI",
            bg="#059669",
            fg="#f8fafc",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._copy_last_ai_reply
        )
        btn_copy_ai.pack(side="right", padx=2)

        btn_copy_user = tk.Button(
            top_chat_bar,
            text="👤 Copy Hỏi",
            bg="#475569",
            fg="#f8fafc",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._copy_last_user_question
        )
        btn_copy_user.pack(side="right", padx=2)

        # Chat Text Container với Tag Styles hiện đại
        chat_container = tk.Frame(right_frame, bg="#1e293b", relief="flat", bd=1)
        chat_container.pack(fill="both", expand=True)

        scroll = tk.Scrollbar(chat_container)
        scroll.pack(side="right", fill="y")

        self.log_text = tk.Text(
            chat_container,
            font=("Segoe UI", 10),
            wrap="word",
            bg="#0b0f19",
            fg="#f8fafc",
            padx=14,
            pady=12,
            selectbackground="#0284c7",
            selectforeground="#ffffff",
            inactiveselectbackground="#0369a1",
            exportselection=False,
            cursor="xterm",
            yscrollcommand=scroll.set,
            insertbackground="white"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.log_text.yview)

        # Tạo Context Menu khi bấm chuột phải vào khung chat
        self._setup_chat_context_menu(self.log_text)

        # Định nghĩa các tags phong cách Chat Bubbles phân biệt Người Dùng (Bên phải) vs AI (Bên trái)
        self.log_text.tag_config("TIME", foreground="#64748b", font=("Consolas", 8))
        
        # USER (Bên Phải): Căn phải, màu Indigo nổi bật
        self.log_text.tag_config("USER_HDR", foreground="#818cf8", font=("Segoe UI", 9, "bold"), justify="right", spacing1=8, spacing3=2)
        self.log_text.tag_config("USER_BUBBLE", background="#3730a3", foreground="#ffffff", justify="right", lmargin1=120, lmargin2=120, rmargin=12, spacing1=4, spacing3=8)

        # AI (Bên Trái): Căn trái, màu Emerald / Slate Card
        self.log_text.tag_config("AI_HDR", foreground="#34d399", font=("Segoe UI", 9, "bold"), justify="left", spacing1=8, spacing3=2)
        self.log_text.tag_config("AI_BUBBLE", background="#064e3b", foreground="#ecfdf5", justify="left", lmargin1=12, lmargin2=12, rmargin=120, spacing1=4, spacing3=8)

        # SYSTEM (Ở Giữa)
        self.log_text.tag_config("SYS_BADGE", foreground="#a78bfa", font=("Segoe UI", 8, "italic"), justify="center", spacing1=6, spacing3=6)

        # Cấu hình thẻ lựa chọn văn bản 'sel' luôn nổi lên trên cùng (bôi đen rõ nét 100%)
        self.log_text.tag_config("sel", background="#0284c7", foreground="#ffffff")
        self.log_text.tag_raise("sel")

        # Khung Gõ Tin Nhắn Chat Nhanh Với AI Ngay Tại Tab 1
        chat_input_box = tk.Frame(right_frame, bg="#1e293b", padx=8, pady=6)
        chat_input_box.pack(fill="x", pady=(6, 0))

        # Gợi ý câu hỏi 1-click
        suggest_bar = tk.Frame(chat_input_box, bg="#1e293b")
        suggest_bar.pack(fill="x", pady=(0, 4))
        
        tab1_prompts = [
            ("⚡ Kiểm Tra AI & Key", "Kiểm tra trạng thái AI, key api còn hoạt động không?"),
            ("⏰ Mấy Giờ & Thứ Mấy", "Bây giờ là mấy giờ em ơi, hôm nay thứ mấy ngày bao nhiêu?"),
            ("🟡 Lỗi PowerPoint", "Em ơi mở file PowerPoint tải về bị thanh màu vàng Enable Editing"),
            ("📥 Xin Quyền Drive", "Email của cô là: lemaianh@gmail.com, cấp quyền Drive lớp 10 giúp cô nhé em"),
            ("📚 Xin PPCT Sử 10", "Gửi giúp tôi link PPCT và Đề kiểm tra Lịch sử 10 Kết Nối Tri Thức với"),
            ("🌍 Hỏi Tự Do", "Thủ đô của nước Pháp là gì và diện tích là bao nhiêu?")
        ]
        for lbl_p, txt_p in tab1_prompts:
            btn_p = tk.Button(
                suggest_bar,
                text=lbl_p,
                font=("Segoe UI", 8, "bold"),
                bg="#0f172a",
                fg="#38bdf8",
                relief="flat",
                padx=5,
                pady=1,
                cursor="hand2",
                command=lambda t=txt_p: self._fill_tab1_prompt(t)
            )
            btn_p.pack(side="left", padx=2)

        # Status text cho Tab 1
        self.tab1_metric_lbl = tk.Label(
            suggest_bar,
            text=f"⚡ Sẵn sàng | Model: {self.gemini.model_name}",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#1e293b"
        )
        self.tab1_metric_lbl.pack(side="right", padx=4)

        input_row = tk.Frame(chat_input_box, bg="#1e293b")
        input_row.pack(fill="x")

        self.tab1_msg_entry = tk.Entry(input_row, font=("Segoe UI", 10), bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.tab1_msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.tab1_msg_entry.insert(0, "Kiểm tra trạng thái AI, key api còn hoạt động không?")
        self.tab1_msg_entry.bind("<Return>", lambda e: self._send_tab1_interactive_message())

        btn_ask_ai = tk.Button(
            input_row,
            text="⚡ Hỏi AI Trực Tiếp",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._send_tab1_interactive_message
        )
        btn_ask_ai.pack(side="left", padx=2)

        # Thanh công cụ gửi tin trực tiếp đến Zalo PC
        zalo_pc_bar = tk.Frame(parent, bg="#1e293b", padx=10, pady=8)
        zalo_pc_bar.pack(fill="x", pady=(8, 0))

        tk.Label(zalo_pc_bar, text="⚡ BẮN TRỰC TIẾP VÀO ZALO PC:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")

        tk.Label(zalo_pc_bar, text="Tên Nick (Thầy/Cô):", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(10, 2))
        self.direct_nick_entry = tk.Entry(zalo_pc_bar, font=("Segoe UI", 9), width=16, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.direct_nick_entry.pack(side="left", padx=2)
        self.direct_nick_entry.insert(0, "Thầy Nam (Ví dụ)")

        tk.Label(zalo_pc_bar, text="Tin nhắn:", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(10, 2))
        self.direct_msg_entry = tk.Entry(zalo_pc_bar, font=("Segoe UI", 9), width=45, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.direct_msg_entry.pack(side="left", padx=2)
        self.direct_msg_entry.insert(0, "Dạ em chào Thầy/Cô ạ! Em hỗ trợ giáo án Lịch sử Kết Nối Tri Thức đây ạ. 😊")

        btn_send_direct = tk.Button(
            zalo_pc_bar,
            text="🚀 Bắn Vào Zalo Ngay",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._send_direct_zalo_from_ui
        )
        btn_send_direct.pack(side="left", padx=5)

        btn_auto_pilot = tk.Button(
            zalo_pc_bar,
            text="🤖 Đọc Màn Hình & Trả Lời (1-Click)",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._auto_pilot_read_and_reply
        )
        btn_auto_pilot.pack(side="left", padx=4)

        btn_deep_context = tk.Button(
            zalo_pc_bar,
            text="📜 Cuộn Lên & Đọc Ngữ Cảnh 20 Tin (Deep Context AI)",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._deep_context_read_and_reply
        )
        btn_deep_context.pack(side="left", padx=4)

        # Hàng 2: Thanh Phân Loại & Lọc Chưa Đọc Zalo PC
        filter_bar = tk.Frame(parent, bg="#0f172a", padx=10, pady=6)
        filter_bar.pack(fill="x", pady=(4, 0))

        tk.Label(filter_bar, text="🏷️ PHÂN LOẠI & THẺ ZALO PC:", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#0f172a").pack(side="left")

        btn_flt_unread = tk.Button(
            filter_bar,
            text="🔴 Lọc Tin Chưa Đọc",
            bg="#dc2626",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._filter_unread_zalo
        )
        btn_flt_unread.pack(side="left", padx=4)

        btn_flt_need = tk.Button(
            filter_bar,
            text="🏷️ Lọc Thẻ 'Cần Giải Quyết'",
            bg="#d97706",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._filter_need_resolution_zalo
        )
        btn_flt_need.pack(side="left", padx=4)

        btn_assign_tag = tk.Button(
            filter_bar,
            text="📌 Gắn Thẻ 'Cần Giải Quyết'",
            bg="#b45309",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._assign_need_resolution_zalo
        )
        btn_assign_tag.pack(side="left", padx=4)

        btn_batch_scan = tk.Button(
            filter_bar,
            text="🚀 Tự Động Quét & Trả Lời Hàng Loạt Chưa Đọc (Auto-Scan All)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=2,
            cursor="hand2",
            command=self._batch_scan_unread_zalo
        )
        btn_batch_scan.pack(side="right", padx=5)

        # Nạp dữ liệu danh sách phiên hội thoại ban đầu
        self.after(100, self._refresh_chat_sessions_list)

    # ================= QUẢN LÝ PHIÊN TRÒ CHUYỆN (SESSIONS & HISTORY) =================
    def _refresh_chat_sessions_list(self, keep_current: bool = True):
        """Cập nhật danh sách các phiên trò chuyện từ CSDL SQLite."""
        if not hasattr(self, 'chat_sessions_tree') or not self.chat_sessions_tree.winfo_exists():
            return

        for item in self.chat_sessions_tree.get_children():
            self.chat_sessions_tree.delete(item)

        is_arch = (self.chat_view_mode == "archived")
        sessions = self.state.list_chat_sessions(is_archived=is_arch)

        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        sec_bg = "#f1f5f9" if is_light else "#1e293b"
        sec_fg = "#475569" if is_light else "#94a3b8"

        # Cập nhật nút bấm mode và toolbar
        if is_arch:
            self.btn_chat_mode_archived.configure(bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"))
            self.btn_chat_mode_active.configure(bg=sec_bg, fg=sec_fg, font=("Segoe UI", 8))
            self.btn_archive_toggle.configure(text="📤 Bỏ Lưu Trữ", fg="#059669" if is_light else "#34d399", bg=sec_bg)
        else:
            self.btn_chat_mode_active.configure(bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"))
            self.btn_chat_mode_archived.configure(bg=sec_bg, fg=sec_fg, font=("Segoe UI", 8))
            self.btn_archive_toggle.configure(text="📦 Lưu Trữ", fg="#d97706" if is_light else "#fbbf24", bg=sec_bg)

        target_row_to_select = None
        for s in sessions:
            sid = s['id']
            time_formatted = format_smart_timestamp(s.get('updated_at'))
            self.chat_sessions_tree.insert(
                "",
                "end",
                iid=str(sid),
                values=(
                    sid,
                    s.get('title', 'Hội thoại mới'),
                    s.get('msg_count', 0),
                    time_formatted
                )
            )
            if self.current_chat_session_id and sid == self.current_chat_session_id:
                target_row_to_select = str(sid)

        if sessions:
            if not target_row_to_select or not keep_current:
                target_row_to_select = str(sessions[0]['id'])
            self.chat_sessions_tree.selection_set(target_row_to_select)
            self._load_chat_session(int(target_row_to_select))
        else:
            if not is_arch:
                # Nếu trống ở chế độ Active, tự động tạo 1 hội thoại mặc định
                new_id = self.state.create_chat_session("Hội thoại tư vấn giáo án")
                self.current_chat_session_id = new_id
                self._refresh_chat_sessions_list()
            else:
                self.current_chat_session_id = None
                self.log_text.delete("1.0", tk.END)
                self.chat_current_title_lbl.configure(text="📦 Mục lưu trữ đang trống", fg="#94a3b8")

    def _set_chat_view_mode(self, mode: str):
        """Chuyển đổi giữa chế độ 'Đang Mở' và 'Đã Lưu Trữ'."""
        self.chat_view_mode = mode
        self._refresh_chat_sessions_list(keep_current=False)

    def _create_new_chat_session(self):
        """Tạo một cuộc trò chuyện mới."""
        new_id = self.state.create_chat_session("Hội thoại mới")
        self.current_chat_session_id = new_id
        if self.chat_view_mode != "active":
            self.chat_view_mode = "active"
        self._refresh_chat_sessions_list(keep_current=True)
        self.tab1_msg_entry.delete(0, tk.END)
        self.tab1_msg_entry.focus_set()
        self.show_toast("Tạo Chat Mới", "Đã tạo cuộc trò chuyện mới thành công!", "success")

    def _open_selected_chat_session(self):
        """Mở cuộc trò chuyện đang chọn trong danh sách."""
        sel = self.chat_sessions_tree.selection() if hasattr(self, 'chat_sessions_tree') else ()
        if sel:
            self._load_chat_session(int(sel[0]))

    def _on_chat_session_selected(self, event=None):
        """Sự kiện chọn dòng trong bảng phiên trò chuyện."""
        sel = self.chat_sessions_tree.selection() if hasattr(self, 'chat_sessions_tree') else ()
        if sel:
            self._load_chat_session(int(sel[0]))

    def _show_chat_session_context_menu(self, event):
        """Hiển thị menu chuột phải khi bấm vào một phiên trò chuyện."""
        row_id = self.chat_sessions_tree.identify_row(event.y)
        if row_id:
            self.chat_sessions_tree.selection_set(row_id)
            self._load_chat_session(int(row_id))
            self.chat_session_menu.post(event.x_root, event.y_root)

    def _rename_selected_chat_session(self):
        """Đổi tên phiên trò chuyện đang chọn."""
        sel = self.chat_sessions_tree.selection() if hasattr(self, 'chat_sessions_tree') else ()
        if not sel:
            if not self.current_chat_session_id:
                self.show_toast("Chưa Chọn", "Vui lòng chọn 1 cuộc trò chuyện để đổi tên!", "warning")
                return
            sid = self.current_chat_session_id
        else:
            sid = int(sel[0])

        cur_title = "Hội thoại"
        try:
            item_vals = self.chat_sessions_tree.item(str(sid), "values")
            if item_vals and len(item_vals) > 1:
                cur_title = item_vals[1]
        except Exception:
            pass

        new_title = simpledialog.askstring("Đổi Tên Hội Thoại", "Nhập tên mới cho cuộc trò chuyện:", initialvalue=cur_title, parent=self)
        if new_title and new_title.strip():
            self.state.rename_chat_session(sid, new_title.strip())
            self.show_toast("Đổi Tên", f"Đã đổi tên hội thoại thành: '{new_title.strip()}'", "success")
            self._refresh_chat_sessions_list(keep_current=True)

    def _toggle_archive_selected_chat_session(self):
        """Chuyển phiên trò chuyện vào lưu trữ hoặc bỏ lưu trữ."""
        sel = self.chat_sessions_tree.selection() if hasattr(self, 'chat_sessions_tree') else ()
        if not sel:
            if not self.current_chat_session_id:
                self.show_toast("Chưa Chọn", "Vui lòng chọn 1 cuộc trò chuyện!", "warning")
                return
            sid = self.current_chat_session_id
        else:
            sid = int(sel[0])

        is_currently_arch = (self.chat_view_mode == "archived")
        new_arch_state = not is_currently_arch
        self.state.archive_chat_session(sid, is_archived=new_arch_state)

        if new_arch_state:
            self.show_toast("Đã Lưu Trữ", "Đã chuyển cuộc trò chuyện vào mục Lưu Trữ!", "info")
        else:
            self.show_toast("Đã Bỏ Lưu Trữ", "Đã đưa cuộc trò chuyện trở lại danh sách Đang Mở!", "success")

        self._refresh_chat_sessions_list(keep_current=False)

    def _delete_selected_chat_session(self):
        """Xóa hoàn toàn phiên trò chuyện đang chọn."""
        sel = self.chat_sessions_tree.selection() if hasattr(self, 'chat_sessions_tree') else ()
        if not sel:
            if not self.current_chat_session_id:
                self.show_toast("Chưa Chọn", "Vui lòng chọn 1 cuộc trò chuyện để xóa!", "warning")
                return
            sid = self.current_chat_session_id
        else:
            sid = int(sel[0])

        if messagebox.askyesno("Xác Nhận Xóa", "Bạn có chắc chắn muốn xóa vĩnh viễn cuộc trò chuyện này và toàn bộ tin nhắn bên trong?"):
            self.state.delete_chat_session(sid)
            self.show_toast("Đã Xóa", "Đã xóa cuộc trò chuyện thành công!", "info")
            if self.current_chat_session_id == sid:
                self.current_chat_session_id = None
            self._refresh_chat_sessions_list(keep_current=False)

    def _clear_all_chat_sessions_from_ui(self):
        """Xóa toàn bộ các phiên trò chuyện trong danh mục hiện tại."""
        mode_str = "ĐÃ LƯU TRỮ" if self.chat_view_mode == "archived" else "ĐANG MỞ"
        if messagebox.askyesno("Xác Nhận Xóa Toàn Bộ", f"Bạn có chắc chắn muốn XÓA TẤT CẢ các cuộc trò chuyện trong mục [{mode_str}]?"):
            self.state.clear_all_chat_sessions(is_archived=(self.chat_view_mode == "archived"))
            self.show_toast("Đã Xóa Hết", f"Đã xóa sạch toàn bộ lịch sử trò chuyện mục [{mode_str}]!", "info")
            self.current_chat_session_id = None
            self._refresh_chat_sessions_list(keep_current=False)

    def _load_chat_session(self, session_id: int):
        """Tải toàn bộ tin nhắn của phiên trò chuyện vào khung Chat với phong cách bong bóng hiện đại."""
        self.current_chat_session_id = session_id
        messages = self.state.get_chat_messages(session_id)

        # Lấy tiêu đề session
        sess_info = self.state.get_or_create_chat_session(session_id)
        title = sess_info.get('title', 'Hội thoại')
        self.chat_current_title_lbl.configure(
            text=f"💬 {title}  ({len(messages)} tin nhắn)",
            fg="#38bdf8"
        )

        self.log_text.delete("1.0", tk.END)
        self.tab1_chat_history.clear()
        self.last_user_question = ""
        self.last_ai_response = ""

        if not messages:
            self.log_text.insert(tk.END, "── ⚡ Cuộc trò chuyện mới. Hãy nhập câu hỏi hoặc chọn gợi ý bên dưới để bắt đầu! ──\n", "SYS_BADGE")
            return

        for m in messages:
            stype = m.get('sender_type', 'USER')
            sname = m.get('sender_name', 'Bạn')
            mtext = m.get('message_text', '')
            img = m.get('img_name')
            ctime = m.get('created_at')
            mname = m.get('model_name')

            self._append_chat_message(
                sender_type=stype,
                sender_name=sname,
                message=mtext,
                img_name=img,
                created_at=ctime,
                model_name=mname
            )

            # Cập nhật lịch sử ngữ cảnh cho AI
            if stype == "USER":
                self.tab1_chat_history.append({"sender": "Khách hàng", "text": mtext})
                self.last_user_question = mtext
            elif stype == "AI":
                self.tab1_chat_history.append({"sender": "AI Trợ lý", "text": mtext})
                self.last_ai_response = mtext

    # ================= HIỂN THỊ TIN NHẮN & NÚT COPY TỪNG TIN =================
    def _append_chat_message(
        self,
        sender_type: str,
        sender_name: str,
        message: str,
        img_name: Optional[str] = None,
        created_at: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Hiển thị tin nhắn với thiết kế:
        - Người Dùng: Hiện bên PHẢI (Căn phải, Bubble Indigo, chữ trắng, nút Copy riêng).
        - AI Gemini: Hiện bên TRÁI (Căn trái, Bubble Emerald/Slate, nút Copy riêng).
        - Thời gian chi tiết thông minh: Hôm nay 14:35, Hôm qua 18:20, 28/08 09:15...
        """
        def _do():
            if not hasattr(self, "log_text") or not self.log_text.winfo_exists():
                return

            smart_time = format_smart_timestamp(created_at) if created_at else datetime.now().strftime("Hôm nay %H:%M")

            is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
            user_cp_bg = "#e0e7ff" if is_light else "#312e81"
            user_cp_fg = "#4338ca" if is_light else "#38bdf8"
            user_cp_act = "#c7d2fe" if is_light else "#4338ca"

            ai_cp_bg = "#d1fae5" if is_light else "#064e3b"
            ai_cp_fg = "#065f46" if is_light else "#34d399"
            ai_cp_act = "#a7f3d0" if is_light else "#047857"

            if sender_type == "USER":
                self.last_user_question = message
                
                # Format tên người gửi: Mặc định hiển thị 'Tôi' thay cho 'Bạn / Khách Hàng - Bạn'
                sender_label = "Tôi" if sender_name in ("Bạn", "Khách hàng", "Khách Hàng", "User", "Admin", "Tôi", "", None) else sender_name

                # Header dòng Người Dùng (Căn Phải) kèm nút Copy & Ghi Chú
                self.log_text.insert(tk.END, f"\n[{smart_time}]  👤 [{sender_label}]  ", "USER_HDR")
                
                btn_cp = tk.Button(
                    self.log_text,
                    text="📋 Copy",
                    font=("Segoe UI", 7, "bold"),
                    bg=user_cp_bg,
                    fg=user_cp_fg,
                    activebackground=user_cp_act,
                    activeforeground="white" if not is_light else user_cp_fg,
                    relief="flat",
                    padx=4,
                    pady=0,
                    cursor="hand2",
                    command=lambda t=message: self._copy_single_chat_msg(t)
                )
                self.log_text.window_create(tk.END, window=btn_cp)

                btn_note = tk.Button(
                    self.log_text,
                    text="📝 Ghi Chú",
                    font=("Segoe UI", 7, "bold"),
                    bg="#fef3c7" if is_light else "#78350f",
                    fg="#92400e" if is_light else "#fbbf24",
                    activebackground="#fde68a" if is_light else "#92400e",
                    activeforeground="white" if not is_light else "#92400e",
                    relief="flat",
                    padx=4,
                    pady=0,
                    cursor="hand2",
                    command=lambda t=message, s=sender_label: self._save_msg_to_quick_notes(t, s, "USER")
                )
                self.log_text.window_create(tk.END, window=btn_note)
                self.log_text.insert(tk.END, "\n", "USER_HDR")

                # Thân tin nhắn Người Dùng (Căn Phải, Bubble Màu Nổi Bật)
                body = message
                if img_name:
                    body += f"\n📷 [Đính kèm ảnh: {img_name}]"
                self.log_text.insert(tk.END, f"  {body}  \n", "USER_BUBBLE")

            elif sender_type == "AI":
                self.last_ai_response = message
                m_tag = f" ({model_name})" if model_name and f"({model_name})" not in sender_name else ""
                
                # Header dòng AI (Căn Trái) kèm nút Copy, Ghi Chú & Kịch Bản
                self.log_text.insert(tk.END, f"\n🤖 [{sender_name}{m_tag}]  •  [{smart_time}]  ", "AI_HDR")
                
                btn_cp = tk.Button(
                    self.log_text,
                    text="📋 Copy",
                    font=("Segoe UI", 7, "bold"),
                    bg=ai_cp_bg,
                    fg=ai_cp_fg,
                    activebackground=ai_cp_act,
                    activeforeground="white" if not is_light else ai_cp_fg,
                    relief="flat",
                    padx=4,
                    pady=0,
                    cursor="hand2",
                    command=lambda t=message: self._copy_single_chat_msg(t)
                )
                self.log_text.window_create(tk.END, window=btn_cp)

                btn_note = tk.Button(
                    self.log_text,
                    text="📝 Ghi Chú",
                    font=("Segoe UI", 7, "bold"),
                    bg="#f3e8ff" if is_light else "#581c87",
                    fg="#6b21a8" if is_light else "#c084fc",
                    activebackground="#e9d5ff" if is_light else "#6b21a8",
                    activeforeground="white" if not is_light else "#6b21a8",
                    relief="flat",
                    padx=4,
                    pady=0,
                    cursor="hand2",
                    command=lambda t=message, s=sender_name: self._save_msg_to_quick_notes(t, s, "AI")
                )
                self.log_text.window_create(tk.END, window=btn_note)

                btn_tpl = tk.Button(
                    self.log_text,
                    text="⚡ Kịch Bản",
                    font=("Segoe UI", 7, "bold"),
                    bg="#e0f2fe" if is_light else "#075985",
                    fg="#0369a1" if is_light else "#38bdf8",
                    activebackground="#bae6fd" if is_light else "#0369a1",
                    activeforeground="white" if not is_light else "#0369a1",
                    relief="flat",
                    padx=4,
                    pady=0,
                    cursor="hand2",
                    command=lambda t=message: self._send_to_script_templates(t)
                )
                self.log_text.window_create(tk.END, window=btn_tpl)
                self.log_text.insert(tk.END, "\n", "AI_HDR")

                # Thân tin nhắn AI (Căn Trái, Bubble Nền Slate/Emerald)
                self.log_text.insert(tk.END, f"  {message}  \n", "AI_BUBBLE")

            # Quản lý bộ nhớ RAM: Giới hạn tối đa 350 dòng trong khung log chat để tránh nặng máy
            try:
                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > 350:
                    self.log_text.delete("1.0", f"{line_count - 300}.0")
            except Exception:
                pass

            # Luôn đảm bảo thẻ bôi đen 'sel' hiển thị sắc nét trên cùng mọi bong bóng
            try:
                self.log_text.tag_raise("sel")
            except Exception:
                pass

            self.log_text.see(tk.END)

        self.after(0, _do)

    def _setup_chat_context_menu(self, text_widget: tk.Text):
        """Thiết lập menu chuột phải, phím tắt Ctrl+C, Ctrl+A và thao tác bôi đen cho khung chat."""
        self.chat_right_click_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", activeforeground="white")
        
        def _show_menu(event):
            try:
                self.chat_right_click_menu.delete(0, tk.END)
                
                # Đảm bảo thẻ sel luôn nằm trên cùng
                try:
                    text_widget.tag_raise("sel")
                except Exception:
                    pass

                has_selection = False
                selected_text = ""
                try:
                    selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                    if selected_text:
                        has_selection = True
                except Exception:
                    has_selection = False

                if has_selection:
                    short_preview = selected_text.replace("\n", " ")[:30] + ("..." if len(selected_text) > 30 else "")
                    self.chat_right_click_menu.add_command(
                        label=f"📋 Sao Chép Đoạn Bôi Đen: \"{short_preview}\" (Ctrl+C)",
                        font=("Segoe UI", 9, "bold"),
                        command=lambda: self._on_log_text_copy(None)
                    )
                    self.chat_right_click_menu.add_command(label="📝 Thêm Đoạn Bôi Đen Vào Ghi Chú...", command=self._save_selection_to_quick_notes)
                    self.chat_right_click_menu.add_command(label="⚡ Chuyển Đoạn Bôi Đen Sang Kịch Bản (Tab 3)...", command=self._send_selection_to_script_templates)
                    self.chat_right_click_menu.add_command(label="🚀 Bắn Đoạn Bôi Đen Vào Zalo (F10)", command=self._send_selection_to_zalo)
                    self.chat_right_click_menu.add_separator()
                
                # Các lệnh thao tác nhanh trên câu trả lời AI hoặc toàn bộ hội thoại
                if hasattr(self, "last_ai_response") and self.last_ai_response:
                    self.chat_right_click_menu.add_command(label="🤖 Copy Toàn Bộ Câu Trả Lời AI", command=self._copy_last_ai_reply)
                    self.chat_right_click_menu.add_command(label="📝 Thêm Câu Trả Lời AI Vào Ghi Chú", command=lambda: self._save_msg_to_quick_notes(self.last_ai_response, "AI Gemini", "AI"))
                    self.chat_right_click_menu.add_command(label="⚡ Chuyển Câu Trả Lời AI Sang Kịch Bản (Tab 3)", command=lambda: self._send_to_script_templates(self.last_ai_response))
                
                if hasattr(self, "last_user_question") and self.last_user_question:
                    self.chat_right_click_menu.add_command(label="👤 Copy Câu Hỏi Gần Nhất", command=self._copy_last_user_question)
                
                self.chat_right_click_menu.add_separator()
                self.chat_right_click_menu.add_command(label="📝 Mở Sổ Tay Ghi Chú & Lưu Trữ AI", command=self._open_quick_notes_modal)
                self.chat_right_click_menu.add_command(label="📋 Sao Chép Toàn Bộ Cuộc Trò Chuyện", command=self._copy_all_tab1_chat)
                self.chat_right_click_menu.add_command(label="🔍 Chọn Tất Cả (Ctrl+A)", command=lambda: (text_widget.tag_add(tk.SEL, "1.0", tk.END), text_widget.tag_raise("sel"), "break"))
                self.chat_right_click_menu.add_separator()
                self.chat_right_click_menu.add_command(label="🧹 Xóa Tin Nhắn Phiên Này", command=self._clear_current_session_messages)

                self.chat_right_click_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass

        # Gán phím tắt và sự kiện chuột
        text_widget.bind("<Button-3>", _show_menu)
        text_widget.bind("<Control-c>", self._on_log_text_copy)
        text_widget.bind("<Control-C>", self._on_log_text_copy)
        text_widget.bind("<Control-a>", lambda e: (text_widget.tag_add(tk.SEL, "1.0", tk.END), text_widget.tag_raise("sel"), "break"))
        text_widget.bind("<Control-A>", lambda e: (text_widget.tag_add(tk.SEL, "1.0", tk.END), text_widget.tag_raise("sel"), "break"))
        text_widget.bind("<ButtonRelease-1>", lambda e: text_widget.tag_raise("sel"))

    def _on_log_text_copy(self, event=None):
        """Sao chép đoạn bôi đen, hoặc nếu không bôi đen thì sao chép câu trả lời AI gần nhất."""
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                try:
                    sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                    if sel and sel.strip():
                        import pyperclip
                        pyperclip.copy(sel)
                        self.show_toast("Đã Sao Chép 📋", "Đã sao chép đoạn văn bản được chọn vào Clipboard!", "success")
                        return "break"
                except Exception:
                    pass
                
                # Nếu không bôi đen, ưu tiên sao chép câu trả lời AI gần nhất hoặc toàn bộ chat
                if hasattr(self, "last_ai_response") and self.last_ai_response:
                    self._copy_last_ai_reply()
                    return "break"
                else:
                    self._copy_all_tab1_chat()
                    return "break"
        except Exception:
            pass
        return "break"

    def _copy_single_chat_msg(self, text_to_copy: str):
        """Sao chép riêng lẻ nội dung của 1 tin nhắn vào Clipboard."""
        if not text_to_copy:
            return
        try:
            import pyperclip
            pyperclip.copy(text_to_copy)
            self.show_toast("Đã Sao Chép 📋", "Đã sao chép tin nhắn vào Clipboard!", "success")
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            self.show_toast("Đã Sao Chép 📋", "Đã sao chép tin nhắn vào Clipboard!", "success")

    def _copy_all_tab1_chat(self):
        """Sao chép toàn bộ nội dung trò chuyện của phiên hiện tại vào Clipboard."""
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                content = self.log_text.get("1.0", tk.END).strip()
                if content:
                    import pyperclip
                    pyperclip.copy(content)
                    self.show_toast("Đã Sao Chép Toàn Bộ 📑", "Đã sao chép toàn bộ cuộc trò chuyện vào Clipboard!", "success")
                else:
                    self.show_toast("Trống", "Chưa có nội dung cuộc trò chuyện để sao chép!", "warning")
        except Exception as e:
            self.show_toast("Lỗi Sao Chép", str(e), "error")

    def _copy_last_ai_reply(self):
        """Sao chép câu trả lời AI gần nhất."""
        if hasattr(self, "last_ai_response") and self.last_ai_response:
            self._copy_single_chat_msg(self.last_ai_response)
        else:
            self.show_toast("Chưa Có", "Chưa có phản hồi nào từ AI trong phiên này!", "warning")

    def _copy_last_user_question(self):
        """Sao chép câu hỏi người dùng gần nhất."""
        if hasattr(self, "last_user_question") and self.last_user_question:
            self._copy_single_chat_msg(self.last_user_question)
        else:
            self.show_toast("Chưa Có", "Chưa có câu hỏi nào từ người dùng trong phiên này!", "warning")

    def _clear_current_session_messages(self):
        """Xóa toàn bộ tin nhắn của phiên trò chuyện hiện tại."""
        if not self.current_chat_session_id:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                self.log_text.delete("1.0", tk.END)
            self.show_toast("Đã Xóa", "Đã làm trống khung chat!", "info")
            return
        
        if messagebox.askyesno("Xác Nhận Xóa", "Thầy/Cô có chắc muốn xóa sạch toàn bộ tin nhắn trong cuộc trò chuyện này không?"):
            self.state.clear_session_messages(self.current_chat_session_id)
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert(tk.END, "── ⚡ Cuộc trò chuyện đã được làm trống. Hãy nhập câu hỏi mới bên dưới! ──\n", "SYS_BADGE")
            self.tab1_chat_history.clear()
            self.last_user_question = ""
            self.last_ai_response = ""
            self._refresh_chat_sessions_list(keep_current=True)
            self.show_toast("Đã Xóa Sạch", "Đã xóa toàn bộ tin nhắn trong phiên này thành công!", "success")

    def _save_selection_to_quick_notes(self):
        """Lưu đoạn văn bản đang bôi đen vào Sổ Tay Ghi Chú."""
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if sel:
                    self._save_msg_to_quick_notes(sel, "Đoạn Trích", "SNIPPET")
                else:
                    self.show_toast("Chưa Chọn", "Vui lòng bôi đen đoạn văn bản cần lưu vào ghi chú!", "warning")
        except Exception:
            self.show_toast("Chưa Chọn", "Vui lòng bôi đen đoạn văn bản cần lưu vào ghi chú!", "warning")

    def _save_msg_to_quick_notes(self, text: str, sender: str = "AI", sender_type: str = "AI"):
        """Lưu tin nhắn/ghi chú vào SQLite database và thông báo toast."""
        c_clean = text.strip()
        if not c_clean:
            return
        try:
            title = c_clean.split("\n")[0].strip()[:40] + ("..." if len(c_clean.split("\n")[0].strip()) > 40 else "")
            note_id = self.state.add_quick_note(
                content=c_clean,
                title=title,
                category="Ghi Chú Nhanh",
                sender_type=sender_type,
                session_id=getattr(self, "current_chat_session_id", None)
            )
            self.show_toast(
                "Đã Thêm Vào Ghi Chú ⭐",
                f"Đã lưu vào Sổ Tay: '{title}'!\nBấm nút [📝 Sổ Tay Ghi Chú] trên thanh công cụ để mở xem.",
                "success"
            )
        except Exception as e:
            self.show_toast("Lỗi Lưu Ghi Chú", str(e), "error")

    def _send_selection_to_zalo(self):
        """Bắn trực tiếp đoạn văn bản đang bôi đen vào Zalo PC."""
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if sel:
                    ZaloAutomation.send_text_to_active_or_zalo(sel)
                    self.show_toast("Đã Bắn Vào Zalo 🚀", "Đã gửi đoạn văn bản được chọn vào Zalo PC!", "success")
        except Exception as e:
            self.show_toast("Lỗi Gửi Zalo", str(e), "error")

    def _send_selection_to_script_templates(self):
        """Chuyển đoạn văn bản đang bôi đen sang Mẫu Kịch Bản (Tab 3)."""
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if sel:
                    self._send_to_script_templates(sel)
        except Exception:
            pass

    def _send_to_script_templates(self, text: str):
        """Chuyển nội dung sang Tab 3 (Mẫu Kịch Bản Trả Lời Nhanh)."""
        if not text:
            return
        try:
            if hasattr(self, "notebook"):
                self.notebook.select(2)
            if hasattr(self, "script_ans_text") and self.script_ans_text.winfo_exists():
                self.script_ans_text.delete("1.0", tk.END)
                self.script_ans_text.insert("1.0", text)
            self.show_toast("Đã Chuyển Sang Tab 3 ⚡", "Đã nạp nội dung vào Mẫu Kịch Bản Trả Lời Nhanh!", "success")
        except Exception as e:
            self.show_toast("Thông Báo", f"Đã sao chép nội dung kịch bản: {e}", "info")

    def _open_quick_notes_modal(self):
        """Mở Modal Sổ Tay Ghi Chú & Lưu Trữ AI (Quick Notes Manager)."""
        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        bg_main = "#ffffff" if is_light else "#0f172a"
        bg_card = "#f8fafc" if is_light else "#1e293b"
        bg_input = "#ffffff" if is_light else "#0b0f19"
        fg_text = "#0f172a" if is_light else "#f8fafc"
        fg_sub = "#475569" if is_light else "#94a3b8"

        modal = tk.Toplevel(self)
        modal.title("📝 SỔ TAY GHI CHÚ NHANH & LƯU TRỮ AI (QUICK NOTES)")
        modal.geometry("780x600")
        modal.minsize(680, 480)
        modal.configure(bg=bg_main)
        modal.transient(self)
        modal.grab_set()

        # Căn giữa màn hình
        self.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() - 780) // 2
            y = self.winfo_y() + (self.winfo_height() - 600) // 2
            modal.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        # 1. Header Modal
        hdr = tk.Frame(modal, bg=bg_card, padx=16, pady=12, relief="flat", bd=1)
        hdr.pack(fill="x")

        tk.Label(
            hdr,
            text="📝 SỔ TAY GHI CHÚ & LƯU TRỮ TRỢ LÝ AI",
            font=("Segoe UI", 12, "bold"),
            fg="#8b5cf6" if not is_light else "#6d28d9",
            bg=bg_card
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text="Lưu trữ câu trả lời mẫu, mẹo kỹ thuật, hướng dẫn giải đáp để tra cứu và tái sử dụng nhanh chóng",
            font=("Segoe UI", 8),
            fg=fg_sub,
            bg=bg_card
        ).pack(anchor="w", pady=(2, 0))

        # 2. Search & Filter Bar
        filter_bar = tk.Frame(modal, bg=bg_main, padx=16, pady=10)
        filter_bar.pack(fill="x")

        tk.Label(filter_bar, text="🔍 Tìm:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(side="left")
        
        search_var = tk.StringVar()
        search_ent = tk.Entry(filter_bar, textvariable=search_var, font=("Segoe UI", 9), bg=bg_input, fg=fg_text, insertbackground=fg_text, relief="solid", bd=1)
        search_ent.pack(side="left", fill="x", expand=True, padx=(4, 10))

        tk.Label(filter_bar, text="📁 Mục:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(side="left")
        
        cat_var = tk.StringVar(value="Tất Cả")
        cat_cb = ttk.Combobox(filter_bar, textvariable=cat_var, values=["Tất Cả", "Ghi Chú Nhanh", "Hướng Dẫn Kỹ Thuật", "Báo Giá & Tư Vấn", "Mẹo Hay", "Khác"], state="readonly", width=16)
        cat_cb.pack(side="left", padx=(4, 10))

        count_lbl = tk.Label(filter_bar, text="📊 0 ghi chú", font=("Segoe UI", 8, "bold"), fg="#38bdf8" if not is_light else "#0284c7", bg=bg_main)
        count_lbl.pack(side="left", padx=(0, 10))

        btn_add = tk.Button(
            filter_bar,
            text="➕ Thêm Mới",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_add.pack(side="right")

        # 3. Main List: Scrollable Canvas Frame chứa các Card Ghi Chú
        content_container = tk.Frame(modal, bg=bg_main, padx=16, pady=4)
        content_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(content_container, bg=bg_main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=bg_main)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Hỗ trợ cuộn chuột
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 4. Render danh sách thẻ ghi chú
        def _render_notes():
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            kw = search_var.get().strip()
            cat = cat_var.get().strip()
            notes = self.state.get_all_quick_notes(search_kw=kw, category=cat)
            count_lbl.config(text=f"📊 {len(notes)} ghi chú")

            if not notes:
                empty_box = tk.Frame(scrollable_frame, bg=bg_card, padx=20, pady=30, relief="solid", bd=1)
                empty_box.pack(fill="x", pady=20)
                tk.Label(
                    empty_box,
                    text="📭 Chưa có ghi chú nào phù hợp!\n\nHãy bấm nút [📝 Ghi Chú] trên tin nhắn chat để lưu lại các câu trả lời hay.",
                    font=("Segoe UI", 10),
                    fg=fg_sub,
                    bg=bg_card,
                    justify="center"
                ).pack()
                return

            for note in notes:
                nid = note["id"]
                ntitle = note.get("title", "Ghi chú")
                ncontent = note.get("content", "")
                ncat = note.get("category", "Ghi Chú Nhanh")
                nsender = note.get("sender_type", "AI")
                ntime = format_smart_timestamp(note.get("created_at", ""))

                card = tk.Frame(scrollable_frame, bg=bg_card, padx=12, pady=10, relief="solid", bd=1)
                card.pack(fill="x", pady=5)

                # Header của Card
                card_hdr = tk.Frame(card, bg=bg_card)
                card_hdr.pack(fill="x")

                sender_badge = "🤖 AI" if nsender == "AI" else "👤 Bạn"
                sender_bg = "#065f46" if (nsender == "AI" and not is_light) else ("#d1fae5" if nsender == "AI" else ("#312e81" if not is_light else "#e0e7ff"))
                sender_fg = "#34d399" if (nsender == "AI" and not is_light) else ("#065f46" if nsender == "AI" else ("#818cf8" if not is_light else "#4338ca"))

                badge_lbl = tk.Label(card_hdr, text=f" {sender_badge} ", font=("Segoe UI", 7, "bold"), bg=sender_bg, fg=sender_fg)
                badge_lbl.pack(side="left", padx=(0, 6))

                cat_badge = tk.Label(card_hdr, text=f" 📁 {ncat} ", font=("Segoe UI", 7), bg="#334155" if not is_light else "#e2e8f0", fg="#f8fafc" if not is_light else "#334155")
                cat_badge.pack(side="left", padx=(0, 8))

                title_lbl = tk.Label(card_hdr, text=ntitle, font=("Segoe UI", 9, "bold"), fg="#38bdf8" if not is_light else "#0284c7", bg=bg_card, anchor="w")
                title_lbl.pack(side="left", fill="x", expand=True)

                time_lbl = tk.Label(card_hdr, text=f"🕒 {ntime}", font=("Segoe UI", 8), fg=fg_sub, bg=bg_card)
                time_lbl.pack(side="right")

                # Body text của Card (cho phép bôi đen chọn và copy)
                body_f = tk.Frame(card, bg=bg_input, padx=8, pady=6, relief="solid", bd=1)
                body_f.pack(fill="x", pady=(6, 8))

                txt_widget = tk.Text(body_f, font=("Segoe UI", 9), height=min(6, max(2, ncontent.count("\n") + 1)), bg=bg_input, fg=fg_text, wrap="word", relief="flat", insertbackground=fg_text)
                txt_widget.insert("1.0", ncontent)
                txt_widget.pack(fill="x", expand=True)
                
                # Context menu cho text widget trong note
                self._setup_chat_context_menu(txt_widget)

                # Nút thao tác trên Card
                card_actions = tk.Frame(card, bg=bg_card)
                card_actions.pack(fill="x")

                btn_cp_note = tk.Button(
                    card_actions,
                    text="📋 Copy Nội Dung",
                    font=("Segoe UI", 8, "bold"),
                    bg="#0284c7",
                    fg="white",
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    command=lambda c=ncontent: self._copy_single_chat_msg(c)
                )
                btn_cp_note.pack(side="left", padx=(0, 4))

                btn_zalo_note = tk.Button(
                    card_actions,
                    text="🚀 Bắn Zalo",
                    font=("Segoe UI", 8),
                    bg="#059669",
                    fg="white",
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    command=lambda c=ncontent: (ZaloAutomation.send_text_to_active_or_zalo(c), self.show_toast("Đã Bắn Zalo 🚀", "Đã gửi ghi chú vào Zalo PC!", "success"))
                )
                btn_zalo_note.pack(side="left", padx=(0, 4))

                btn_tab3_note = tk.Button(
                    card_actions,
                    text="⚡ Sang Kịch Bản (Tab 3)",
                    font=("Segoe UI", 8),
                    bg="#475569",
                    fg="#f8fafc",
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    command=lambda c=ncontent: (self._send_to_script_templates(c), modal.destroy())
                )
                btn_tab3_note.pack(side="left", padx=(0, 4))

                btn_del_note = tk.Button(
                    card_actions,
                    text="🗑️ Xóa",
                    font=("Segoe UI", 8),
                    bg="#ef4444",
                    fg="white",
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    command=lambda i=nid: (_delete_single_note(i))
                )
                btn_del_note.pack(side="right")

                btn_edit_note = tk.Button(
                    card_actions,
                    text="✏️ Sửa",
                    font=("Segoe UI", 8),
                    bg="#334155" if not is_light else "#e2e8f0",
                    fg="#f8fafc" if not is_light else "#334155",
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    command=lambda i=nid, t=ntitle, c=ncontent, cat=ncat: (_open_edit_note_modal(i, t, c, cat))
                )
                btn_edit_note.pack(side="right", padx=4)

        def _delete_single_note(note_id: int):
            if messagebox.askyesno("Xác Nhận Xóa", "Thầy/Cô có chắc chắn muốn xóa ghi chú này khỏi sổ tay?", parent=modal):
                self.state.delete_quick_note(note_id)
                self.show_toast("Đã Xóa", "Đã xóa ghi chú thành công!", "info")
                _render_notes()

        def _open_edit_note_modal(note_id: int, old_title: str, old_content: str, old_cat: str):
            edit_win = tk.Toplevel(modal)
            edit_win.title("✏️ CHỈNH SỬA GHI CHÚ")
            edit_win.geometry("540x420")
            edit_win.configure(bg=bg_main)
            edit_win.transient(modal)
            edit_win.grab_set()

            try:
                x = modal.winfo_x() + (modal.winfo_width() - 540) // 2
                y = modal.winfo_y() + (modal.winfo_height() - 420) // 2
                edit_win.geometry(f"+{max(10, x)}+{max(10, y)}")
            except Exception:
                pass

            p = tk.Frame(edit_win, bg=bg_main, padx=16, pady=12)
            p.pack(fill="both", expand=True)

            tk.Label(p, text="Tiêu đề ghi chú:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_title = tk.Entry(p, font=("Segoe UI", 10), bg=bg_input, fg=fg_text, insertbackground=fg_text)
            e_title.insert(0, old_title)
            e_title.pack(fill="x", pady=(2, 8))

            tk.Label(p, text="Danh mục:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_cat_cb = ttk.Combobox(p, values=["Ghi Chú Nhanh", "Hướng Dẫn Kỹ Thuật", "Báo Giá & Tư Vấn", "Mẹo Hay", "Khác"])
            e_cat_cb.set(old_cat)
            e_cat_cb.pack(fill="x", pady=(2, 8))

            tk.Label(p, text="Nội dung:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_txt = tk.Text(p, font=("Segoe UI", 9), height=9, bg=bg_input, fg=fg_text, insertbackground=fg_text)
            e_txt.insert("1.0", old_content)
            e_txt.pack(fill="both", expand=True, pady=(2, 10))

            btn_box = tk.Frame(p, bg=bg_main)
            btn_box.pack(fill="x")

            def _save():
                nt = e_title.get().strip()
                nc = e_txt.get("1.0", tk.END).strip()
                nct = e_cat_cb.get().strip() or "Ghi Chú Nhanh"
                if not nc:
                    messagebox.showwarning("Thiếu Nội Dung", "Nội dung ghi chú không được để trống!", parent=edit_win)
                    return
                self.state.update_quick_note(note_id, nt or old_title, nc, nct)
                self.show_toast("Đã Cập Nhật", "Đã lưu thay đổi ghi chú thành công!", "success")
                edit_win.destroy()
                _render_notes()

            tk.Button(btn_box, text="💾 Lưu Thay Đổi", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2", command=_save).pack(side="left")
            tk.Button(btn_box, text="✕ Hủy", bg="#64748b", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=3, cursor="hand2", command=edit_win.destroy).pack(side="right")

        def _open_new_note_modal():
            new_win = tk.Toplevel(modal)
            new_win.title("➕ THÊM GHI CHÚ MỚI")
            new_win.geometry("540x420")
            new_win.configure(bg=bg_main)
            new_win.transient(modal)
            new_win.grab_set()

            try:
                x = modal.winfo_x() + (modal.winfo_width() - 540) // 2
                y = modal.winfo_y() + (modal.winfo_height() - 420) // 2
                new_win.geometry(f"+{max(10, x)}+{max(10, y)}")
            except Exception:
                pass

            p = tk.Frame(new_win, bg=bg_main, padx=16, pady=12)
            p.pack(fill="both", expand=True)

            tk.Label(p, text="Tiêu đề ghi chú:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_title = tk.Entry(p, font=("Segoe UI", 10), bg=bg_input, fg=fg_text, insertbackground=fg_text)
            e_title.pack(fill="x", pady=(2, 8))

            tk.Label(p, text="Danh mục:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_cat_cb = ttk.Combobox(p, values=["Ghi Chú Nhanh", "Hướng Dẫn Kỹ Thuật", "Báo Giá & Tư Vấn", "Mẹo Hay", "Khác"])
            e_cat_cb.set("Ghi Chú Nhanh")
            e_cat_cb.pack(fill="x", pady=(2, 8))

            tk.Label(p, text="Nội dung ghi chú:", font=("Segoe UI", 9, "bold"), fg=fg_text, bg=bg_main).pack(anchor="w")
            e_txt = tk.Text(p, font=("Segoe UI", 9), height=9, bg=bg_input, fg=fg_text, insertbackground=fg_text)
            e_txt.pack(fill="both", expand=True, pady=(2, 10))

            btn_box = tk.Frame(p, bg=bg_main)
            btn_box.pack(fill="x")

            def _create():
                nt = e_title.get().strip()
                nc = e_txt.get("1.0", tk.END).strip()
                nct = e_cat_cb.get().strip() or "Ghi Chú Nhanh"
                if not nc:
                    messagebox.showwarning("Thiếu Nội Dung", "Nội dung ghi chú không được để trống!", parent=new_win)
                    return
                self.state.add_quick_note(content=nc, title=nt, category=nct, sender_type="USER")
                self.show_toast("Đã Thêm Mới", "Đã thêm ghi chú mới vào sổ tay thành công!", "success")
                new_win.destroy()
                _render_notes()

            tk.Button(btn_box, text="➕ Thêm Ghi Chú", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2", command=_create).pack(side="left")
            tk.Button(btn_box, text="✕ Hủy", bg="#64748b", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=3, cursor="hand2", command=new_win.destroy).pack(side="right")

        btn_add.config(command=_open_new_note_modal)
        search_var.trace_add("write", lambda *args: _render_notes())
        cat_cb.bind("<<ComboboxSelected>>", lambda e: _render_notes())

        # 5. Bottom Action Bar
        bottom_bar = tk.Frame(modal, bg=bg_card, padx=16, pady=10)
        bottom_bar.pack(fill="x")

        def _clear_all():
            if messagebox.askyesno("Xác Nhận Xóa Hết", "Thầy/Cô có chắc muốn xóa toàn bộ ghi chú trong sổ tay không?", parent=modal):
                self.state.clear_all_quick_notes()
                self.show_toast("Đã Xóa Hết", "Đã dọn sạch toàn bộ ghi chú!", "info")
                _render_notes()

        tk.Button(
            bottom_bar,
            text="🧹 Xóa Hết Ghi Chú",
            font=("Segoe UI", 8),
            bg="#ef4444",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=_clear_all
        ).pack(side="left")

        tk.Button(
            bottom_bar,
            text="✕ Đóng",
            font=("Segoe UI", 8, "bold"),
            bg="#475569",
            fg="white",
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=modal.destroy
        ).pack(side="right")

        # Tải danh sách lần đầu
        _render_notes()

        # Dọn dẹp binding khi đóng modal
        def _on_close():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            modal.destroy()
        modal.protocol("WM_DELETE_WINDOW", _on_close)

    def _send_tab1_interactive_message(self):
        """Gửi câu hỏi tới AI Gemini, lưu vào CSDL phiên trò chuyện và hiển thị bong bóng chat."""
        msg = self.tab1_msg_entry.get().strip()
        if not msg:
            # Nếu input không có nội dung, tự động đề xuất câu hỏi kiểm tra trạng thái AI & Key
            msg = "Kiểm tra trạng thái AI, key api còn hoạt động không?"
        
        self.tab1_msg_entry.delete(0, tk.END)

        # Đảm bảo có session đang mở
        if not self.current_chat_session_id:
            self.current_chat_session_id = self.state.create_chat_session("Hội thoại mới")

        sid = self.current_chat_session_id
        now_iso = datetime.now().isoformat()

        # Lưu tin nhắn người dùng vào CSDL SQLite với tên 'Tôi'
        self.state.add_chat_message(sid, "USER", "Tôi", msg)
        self._append_chat_message("USER", "Tôi", msg, created_at=now_iso)

        if hasattr(self, "tab1_metric_lbl"):
            self.tab1_metric_lbl.config(text="⏳ AI đang suy luận & tạo câu trả lời...", fg="#fbbf24")

        def _worker():
            try:
                t0 = time.time()
                replies, analysis = self.gemini.generate_response(msg, chat_history=self.tab1_chat_history)
                elapsed = time.time() - t0

                if not replies:
                    replies = ["Dạ em chưa nhận được phản hồi từ model. Thầy/Cô thử lại giúp em nhé ạ!"]
                
                ai_iso = datetime.now().isoformat()
                for r in replies:
                    # Lưu tin nhắn AI vào CSDL SQLite
                    self.state.add_chat_message(sid, "AI", "AI Gemini", r, model_name=self.gemini.model_name)
                    self._append_chat_message("AI", "AI Gemini", r, created_at=ai_iso, model_name=self.gemini.model_name)
                
                # Ghi nhớ ngữ cảnh hội thoại đa lượt
                self.tab1_chat_history.append({"sender": "Khách hàng", "text": msg})
                self.tab1_chat_history.append({"sender": "AI Trợ lý", "text": " ".join(replies)})

                # Cập nhật lại danh sách hội thoại bên trái để cập nhật tiêu đề, số tin nhắn và thời gian mới nhất
                self.after(0, lambda: self._refresh_chat_sessions_list(keep_current=True))

                if hasattr(self, "tab1_metric_lbl"):
                    self.after(0, lambda: self.tab1_metric_lbl.config(text=f"⚡ Độ trễ: {elapsed:.2f}s | Model: {self.gemini.model_name}", fg="#34d399"))

            except Exception as e:
                logger.error(f"[GUI] Lỗi xử lý tin nhắn: {e}")
                err_iso = datetime.now().isoformat()
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    diag_msg = (
                        "⚠️ LỖI QUÁ QUOTA API (429 Resource Exhausted):\n"
                        "• Nguyên nhân: Đã vượt quá hạn mức yêu cầu hoặc hết quota miễn phí của Google AI Studio do gửi quá nhiều yêu cầu.\n"
                        "• Khắc phục: Vui lòng đổi sang API Key khác trong Tab Cài Đặt (Tab 10), đợi 1-5 phút hoặc nâng cấp gói trả phí (Pay-as-you-go)."
                    )
                elif "400" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                    diag_msg = (
                        "⚠️ LỖI API KEY KHÔNG HỢP LỆ (400/403 Invalid Key):\n"
                        "• Nguyên nhân: Khóa API Key không hợp lệ hoặc đã bị vô hiệu hóa.\n"
                        "• Khắc phục: Vui lòng kiểm tra và thay API Key mới trong Tab Cài Đặt (Tab 10)."
                    )
                else:
                    diag_msg = f"❌ Lỗi xử lý AI: {err_str}"

                self._append_chat_message("SYS", "Hệ Thống", diag_msg, created_at=err_iso)
                if hasattr(self, "tab1_metric_lbl"):
                    self.after(0, lambda: self.tab1_metric_lbl.config(text="⚠️ Lỗi kết nối / Quota", fg="#f87171"))

        threading.Thread(target=_worker, daemon=True).start()

    def _clear_current_session_messages(self):
        """Xóa toàn bộ tin nhắn trong cuộc trò chuyện hiện tại."""
        if not self.current_chat_session_id:
            self.show_toast("Chưa Chọn", "Chưa có cuộc trò chuyện nào đang mở!", "warning")
            return

        if messagebox.askyesno("Xác Nhận Xóa", "Bạn có chắc chắn muốn xóa toàn bộ tin nhắn trong cuộc trò chuyện này?"):
            self.state.clear_session_messages(self.current_chat_session_id)
            self._load_chat_session(self.current_chat_session_id)
            self._refresh_chat_sessions_list(keep_current=True)
            self.show_toast("Đã Xóa", "Đã xóa toàn bộ tin nhắn của phiên trò chuyện!", "info")

    def _clear_realtime_chat(self):
        self._clear_current_session_messages()

    def _setup_chat_context_menu(self, text_widget):
        """Tạo menu chuột phải để Copy nhanh."""
        menu = tk.Menu(text_widget, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", activeforeground="#ffffff")
        
        def _copy_selection():
            try:
                sel = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    self.clipboard_clear()
                    self.clipboard_append(sel)
                    self.show_toast("Đã Copy", "Đã copy đoạn văn bản đang bôi đen!", "info")
            except Exception:
                pass

        menu.add_command(label="📋 Copy Đoạn Đang Chọn (Ctrl+C)", command=_copy_selection)
        menu.add_command(label="📋 Copy Câu Trả Lời AI Mới Nhất", command=self._copy_last_ai_reply)
        menu.add_command(label="📋 Copy Câu Hỏi Mới Nhất", command=self._copy_last_user_question)
        menu.add_separator()
        menu.add_command(label="📋 Copy Toàn Bộ Đoạn Chat", command=self._copy_all_tab1_chat)
        menu.add_command(label="🧹 Xóa Toàn Bộ Tin Nhắn", command=self._clear_current_session_messages)

        def _popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        text_widget.bind("<Button-3>", _popup)

    def _copy_last_ai_reply(self):
        """Copy câu trả lời AI vừa tạo vào Clipboard."""
        if hasattr(self, "last_ai_response") and self.last_ai_response:
            self.clipboard_clear()
            self.clipboard_append(self.last_ai_response)
            self.show_toast("Đã Copy", "Đã copy câu trả lời AI vào Clipboard!", "success")
        else:
            self.show_toast("Thông Báo", "Chưa có câu trả lời AI nào để copy!", "warning")

    def _copy_last_user_question(self):
        """Copy câu hỏi của khách hàng vào Clipboard."""
        if hasattr(self, "last_user_question") and self.last_user_question:
            self.clipboard_clear()
            self.clipboard_append(self.last_user_question)
            self.show_toast("Đã Copy", "Đã copy câu hỏi vào Clipboard!", "success")
        else:
            self.show_toast("Thông Báo", "Chưa có câu hỏi nào để copy!", "warning")

    def _copy_all_tab1_chat(self):
        """Copy toàn bộ nội dung trong khung chat."""
        content = self.log_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.show_toast("Đã Copy", "Đã copy toàn bộ nội dung chat!", "info")

    def _fill_tab1_prompt(self, text: str):
        self.tab1_msg_entry.delete(0, tk.END)
        self.tab1_msg_entry.insert(0, text)
        self.tab1_msg_entry.focus_set()

    # ---------------- TAB 2: AI PLAYGROUND (TEST CHAT & SUY LUẬN MODEL) ----------------
    def _build_playground_tab(self, parent):
        top_ctrl = tk.Frame(parent, bg="#1e293b", padx=12, pady=10, relief="flat")
        top_ctrl.pack(fill="x", pady=(0, 6))

        tk.Label(top_ctrl, text="🎯 Chọn Model Test:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")
        self.pg_model_cb = ttk.Combobox(top_ctrl, values=self._get_active_model_list(), width=20, state="readonly")
        self.pg_model_cb.set(self.gemini.model_name)
        self.pg_model_cb.pack(side="left", padx=6)
        self.pg_model_cb.bind("<<ComboboxSelected>>", self._on_pg_model_change)

        tk.Label(top_ctrl, text="🎭 Phong Cách:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(10, 0))
        self.pg_persona_cb = ttk.Combobox(
            top_ctrl,
            values=[
                "1. Trợ Lý Giáo Án Sử 6-12 (Chuẩn)",
                "2. Kỹ Thuật Viên Máy Tính (Sửa lỗi PPT/Drive)",
                "3. Chuyên Gia Sử Học GDPT 2018 (Học thuật)",
                "4. Trợ Lý AI Tự Do (General Assistant)"
            ],
            width=26,
            state="readonly"
        )
        self.pg_persona_cb.set("1. Trợ Lý Giáo Án Sử 6-12 (Chuẩn)")
        self.pg_persona_cb.pack(side="left", padx=6)

        self.btn_pg_img = tk.Button(top_ctrl, text="📷 Kèm Ảnh Lỗi", bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._select_playground_image)
        self.btn_pg_img.pack(side="left", padx=8)

        self.pg_reasoning_var = tk.BooleanVar(value=True)
        chk_reasoning = tk.Checkbutton(
            top_ctrl,
            text="🧠 Phân Tích Ý Định",
            variable=self.pg_reasoning_var,
            bg="#1e293b",
            fg="#a78bfa",
            activebackground="#1e293b",
            font=("Segoe UI", 9, "bold"),
            selectcolor="#0f172a"
        )
        chk_reasoning.pack(side="left", padx=5)

        self.pg_metric_lbl = tk.Label(top_ctrl, text=f"⚡ Sẵn sàng | Model: {self.gemini.model_name}", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b")
        self.pg_metric_lbl.pack(side="right", padx=5)

        # Quick Prompt Suggestions (1-Click Template)
        quick_frame = tk.Frame(parent, bg="#0f172a", pady=4)
        quick_frame.pack(fill="x")

        tk.Label(quick_frame, text="💡 Gợi ý câu hỏi test nhanh:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a").pack(side="left", padx=(0, 6))

        prompts = [
            ("⚡ Kiểm Tra AI & Key", "Kiểm tra trạng thái AI, key api còn hoạt động không?"),
            ("⏰ Mấy Giờ & Thứ Mấy", "Bây giờ là mấy giờ em ơi, hôm nay thứ mấy ngày bao nhiêu?"),
            ("🟡 Lỗi Protected View", "Em ơi mở file PowerPoint tải về bị thanh màu vàng không sửa được"),
            ("📥 Xin Quyền Drive", "Email của cô là: lemaianh@gmail.com, cấp quyền Drive lớp 10 giúp cô nhé em"),
            ("📚 Hỏi PPCT Sử 10", "Gửi cho thầy phân phối chương trình và đề kiểm tra Lịch sử 10 Kết Nối Tri Thức với"),
            ("📝 Góp Ý Lỗi Bài 5", "Bài 5 Lịch sử 11 phần bảng số liệu có số chưa đúng sách mới nhé em"),
            ("🧠 Suy Luận Sư Phạm", "Tại sao giáo án Lịch sử 7 Kết Nối Tri Thức bài 1 lại chia thành 3 tiết, hãy giải thích sư phạm")
        ]
        for label, text_content in prompts:
            btn = tk.Button(
                quick_frame,
                text=label,
                font=("Segoe UI", 8, "bold"),
                bg="#1e293b",
                fg="#38bdf8",
                relief="flat",
                padx=6,
                pady=2,
                cursor="hand2",
                command=lambda t=text_content: self._fill_playground_prompt(t)
            )
            btn.pack(side="left", padx=2)

        # Chat Bubble Area for Playground
        paned = tk.PanedWindow(parent, orient="vertical", bg="#1e293b", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=4)

        pg_chat_box = tk.Frame(paned, bg="#0b0f19")
        paned.add(pg_chat_box, minsize=260)

        pg_scroll = tk.Scrollbar(pg_chat_box)
        pg_scroll.pack(side="right", fill="y")

        self.pg_chat_text = tk.Text(
            pg_chat_box,
            font=("Segoe UI", 10),
            wrap="word",
            bg="#0b0f19",
            fg="#f8fafc",
            padx=14,
            pady=12,
            yscrollcommand=pg_scroll.set,
            insertbackground="white"
        )
        self.pg_chat_text.pack(side="left", fill="both", expand=True)
        pg_scroll.config(command=self.pg_chat_text.yview)

        # Style tags for Playground
        self.pg_chat_text.tag_config("PG_TIME", foreground="#64748b", font=("Consolas", 8))
        self.pg_chat_text.tag_config("PG_USER_HDR", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        self.pg_chat_text.tag_config("PG_USER_TXT", foreground="#e0f2fe", lmargin1=15, lmargin2=25, rmargin=60, spacing1=3, spacing3=6)
        self.pg_chat_text.tag_config("PG_AI_HDR", foreground="#34d399", font=("Segoe UI", 10, "bold"))
        self.pg_chat_text.tag_config("PG_AI_TXT", foreground="#ecfdf5", lmargin1=30, lmargin2=40, rmargin=15, spacing1=3, spacing3=6)
        self.pg_chat_text.tag_config("PG_THOUGHT", foreground="#fbbf24", font=("Consolas", 9, "italic"), lmargin1=30, lmargin2=40, rmargin=20)

        banner = (
            "✨ [AI PLAYGROUND] KHÔNG GIAN THỬ NGHIỆM CHAT & SUY LUẬN TRỰC TIẾP CÁC MODEL GEMINI\n"
            "   - Hỗ trợ trả lời ngày giờ thực, trò chuyện tự do VÀ am hiểu sâu Giáo án Lịch sử 6-12 Kết Nối Tri Thức.\n"
            "------------------------------------------------------------------------------------------------------\n\n"
        )
        self.pg_chat_text.insert(tk.END, banner, "PG_AI_HDR")

        # Bottom Input Area
        pg_input_frame = tk.Frame(paned, bg="#1e293b", padx=8, pady=8)
        paned.add(pg_input_frame, minsize=110)

        self.pg_entry = tk.Text(pg_input_frame, height=3, font=("Segoe UI", 10), wrap="word", bg="#0f172a", fg="#f8fafc", padx=8, pady=6, insertbackground="white")
        self.pg_entry.pack(fill="both", expand=True, side="left", padx=(0, 8))
        self.pg_entry.bind("<Return>", self._on_pg_enter_pressed)

        pg_btn_col = tk.Frame(pg_input_frame, bg="#1e293b")
        pg_btn_col.pack(side="right", fill="y")

        btn_send_pg = tk.Button(
            pg_btn_col,
            text="🚀 GỬI TEST (Enter)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._send_playground_message
        )
        btn_send_pg.pack(fill="x", pady=(0, 4))

        btn_clear_pg = tk.Button(
            pg_btn_col,
            text="🧹 Xóa Lịch Sử Chat",
            bg="#475569",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._clear_playground_history
        )
        btn_clear_pg.pack(fill="x")

    def _on_pg_model_change(self, event=None):
        m = self.pg_model_cb.get().strip()
        if m:
            self.gemini.set_model(m)
            self.hdr_model_cb.set(m)
            if hasattr(self, "api_model_cb"):
                self.api_model_cb.set(m)
            self._update_header_status_label()
            self.pg_metric_lbl.config(text=f"⚡ Sẵn sàng | Model: {m}")
            self.show_toast("Đổi Model Test", f"Đã chuyển model test sang '{m}'", "info")

    def _fill_playground_prompt(self, text: str):
        self.pg_entry.delete("1.0", tk.END)
        self.pg_entry.insert("1.0", text)
        self.pg_entry.focus_set()

    def _select_playground_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.webp")])
        if path:
            self.playground_img_path = path
            self.btn_pg_img.config(text=f"📷 Đã chọn: {os.path.basename(path)}", bg="#059669")
            self.show_toast("Đính Kèm Ảnh", f"Đã đính kèm ảnh: {os.path.basename(path)}", "info")

    def _clear_playground_history(self):
        self.playground_chat_history.clear()
        self.pg_chat_text.delete("1.0", tk.END)
        self.pg_chat_text.insert(tk.END, "--- Đã làm mới lịch sử chat của Playground ---\n\n", "PG_AI_HDR")
        self.playground_img_path = None
        self.btn_pg_img.config(text="📷 Kèm Ảnh Lỗi", bg="#3b82f6")

    def _on_pg_enter_pressed(self, event):
        if not event.state & 0x0001:
            self._send_playground_message()
            return "break"

    def _send_playground_message(self):
        msg = self.pg_entry.get("1.0", tk.END).strip()
        if not msg and not self.playground_img_path:
            return

        self.pg_entry.delete("1.0", tk.END)
        now_str = datetime.now().strftime("%H:%M:%S")

        img_info = f" [📷 {os.path.basename(self.playground_img_path)}]" if self.playground_img_path else ""
        self.pg_chat_text.insert(tk.END, f"\n👤 [Tôi] ", "PG_USER_HDR")
        self.pg_chat_text.insert(tk.END, f"[{now_str}]\n", "PG_TIME")
        self.pg_chat_text.insert(tk.END, f"   {msg}{img_info}\n", "PG_USER_TXT")
        self.pg_chat_text.see(tk.END)

        cur_model = self.pg_model_cb.get().strip() or self.gemini.model_name
        cur_img = self.playground_img_path
        self.playground_img_path = None
        self.btn_pg_img.config(text="📷 Kèm Ảnh Lỗi", bg="#3b82f6")

        self.pg_metric_lbl.config(text="⏳ Đang suy luận & tạo câu trả lời...", fg="#fbbf24")

        def _worker():
            try:
                t0 = time.time()
                replies, analysis = self.gemini.generate_response(
                    message_text=msg,
                    image_path=cur_img,
                    chat_history=self.playground_chat_history
                )
                elapsed = time.time() - t0
                now_reply = datetime.now().strftime("%H:%M:%S")

                def _update_ui():
                    if self.pg_reasoning_var.get():
                        thought_summary = (
                            f"   🧠 [Phân Tích]: Ý định: '{analysis.get('intent')}' | "
                            f"Góp ý sách: {analysis.get('is_content_feedback')} | "
                            f"Lớp: {analysis.get('grade_detected') or 'Chung'} | "
                            f"Hoàn thành: {analysis.get('is_completed')}\n"
                        )
                        self.pg_chat_text.insert(tk.END, thought_summary, "PG_THOUGHT")

                    self.pg_chat_text.insert(tk.END, f"🤖 [AI GEMINI - {cur_model}] ", "PG_AI_HDR")
                    self.pg_chat_text.insert(tk.END, f"[{now_reply} | {elapsed:.2f}s]\n", "PG_TIME")
                    
                    for idx, r in enumerate(replies, 1):
                        prefix = f"👉 [Tin {idx}]: " if len(replies) > 1 else "👉 "
                        self.pg_chat_text.insert(tk.END, f"   {prefix}{r}\n", "PG_AI_TXT")

                    self.pg_chat_text.insert(tk.END, "\n")
                    self.pg_chat_text.see(tk.END)

                    self.playground_chat_history.append({"sender": "Khách hàng", "text": msg})
                    self.playground_chat_history.append({"sender": "AI Trợ lý", "text": " ".join(replies)})
                    self.pg_metric_lbl.config(text=f"⚡ Độ trễ: {elapsed:.2f}s | {len(replies)} tin nhắn | Model: {cur_model}", fg="#34d399")

                self.after(0, _update_ui)
            except Exception as ex:
                self.after(0, lambda: self.pg_metric_lbl.config(text=f"⚠️ Lỗi: {str(ex)[:60]}", fg="#f87171"))

        threading.Thread(target=_worker, daemon=True).start()

    # ---------------- TAB 3: TRUNG TÂM TEST ZALO PC THỰC TẾ ----------------
    def _build_live_test_tab(self, parent):
        header = tk.Frame(parent, bg="#1e293b", padx=12, pady=10)
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text="🎯 TRUNG TÂM TEST GỬI TRỰC TIẾP VÀO ZALO PC (5 BÀI TEST THỰC CHIẾN LIVE)",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        ).pack(side="left")

        tk.Label(
            header,
            text="⚙️ Giới hạn tối đa 5 lần thử (Dừng lại an toàn nếu không tìm thấy)",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(side="right")

        paned = tk.PanedWindow(parent, orient="horizontal", bg="#1e293b", sashwidth=4)
        paned.pack(fill="both", expand=True)

        left_scroll_frame = tk.Frame(paned, bg="#0f172a")
        paned.add(left_scroll_frame, minsize=620)

        canvas = tk.Canvas(left_scroll_frame, bg="#0f172a", highlightthickness=0)
        scrollbar = tk.Scrollbar(left_scroll_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0f172a", padx=8, pady=8)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Card 1: Test 1
        c1 = tk.LabelFrame(scrollable_frame, text=" 🧪 TEST 1: Gửi 1 Người Đơn Lẻ (Như đã test thành công) ", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b", padx=10, pady=8)
        c1.pack(fill="x", pady=5)

        r1 = tk.Frame(c1, bg="#1e293b")
        r1.pack(fill="x", pady=2)
        tk.Label(r1, text="Tên Nick / Khách:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t1_nick = tk.Entry(r1, font=("Segoe UI", 9), width=25, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t1_nick.pack(side="left", padx=5)
        self.t1_nick.insert(0, "Thầy Nam (Ví dụ)")

        r2 = tk.Frame(c1, bg="#1e293b")
        r2.pack(fill="x", pady=2)
        tk.Label(r2, text="Tin nhắn gửi:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t1_msg = tk.Entry(r2, font=("Segoe UI", 9), width=48, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t1_msg.pack(side="left", padx=5)
        self.t1_msg.insert(0, "Dạ em chào Thầy/Cô ạ! Em hỗ trợ giáo án Lịch sử Kết Nối Tri Thức đây ạ. 😊")

        btn_t1 = tk.Button(c1, text="🚀 CHẠY TEST 1 (Gửi 1 Người)", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._run_test_1)
        btn_t1.pack(anchor="e", pady=(4, 0))

        # Card 2: Test 2
        c2 = tk.LabelFrame(scrollable_frame, text=" 👥 TEST 2: Gửi Cho 2 Người Đầu Tiên (Batch 2 Khách) ", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b", padx=10, pady=8)
        c2.pack(fill="x", pady=5)

        r2_1 = tk.Frame(c2, bg="#1e293b")
        r2_1.pack(fill="x", pady=2)
        tk.Label(r2_1, text="Người thứ 1:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t2_nick1 = tk.Entry(r2_1, font=("Segoe UI", 9), width=18, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t2_nick1.pack(side="left", padx=2)
        self.t2_nick1.insert(0, "Thầy Nam (Ví dụ)")
        tk.Label(r2_1, text="Tin nhắn 1:", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(6, 2))
        self.t2_msg1 = tk.Entry(r2_1, font=("Segoe UI", 9), width=28, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t2_msg1.pack(side="left", padx=2)
        self.t2_msg1.insert(0, "Dạ em chào Thầy/Cô ạ! Em hỗ trợ giáo án Lịch sử 6-12 Kết Nối Tri Thức đây ạ.")

        r2_2 = tk.Frame(c2, bg="#1e293b")
        r2_2.pack(fill="x", pady=2)
        tk.Label(r2_2, text="Người thứ 2:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t2_nick2 = tk.Entry(r2_2, font=("Segoe UI", 9), width=18, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t2_nick2.pack(side="left", padx=2)
        self.t2_nick2.insert(0, "My Documents")
        tk.Label(r2_2, text="Tin nhắn 2:", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(6, 2))
        self.t2_msg2 = tk.Entry(r2_2, font=("Segoe UI", 9), width=28, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t2_msg2.pack(side="left", padx=2)
        self.t2_msg2.insert(0, "Chúc Thầy/Cô một ngày làm việc tràn đầy năng lượng và niềm vui! ✨")

        btn_t2 = tk.Button(c2, text="👥 CHẠY TEST 2 (Gửi 2 Người Đầu Tiên)", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._run_test_2)
        btn_t2.pack(anchor="e", pady=(4, 0))

        # Card 3: Test 3
        c3 = tk.LabelFrame(scrollable_frame, text=" ⏳ TEST 3: Gửi Cho Nhóm Hoặc Người Dùng Chưa Phản Hồi ", font=("Segoe UI", 9, "bold"), fg="#fbbf24", bg="#1e293b", padx=10, pady=8)
        c3.pack(fill="x", pady=5)

        r3_1 = tk.Frame(c3, bg="#1e293b")
        r3_1.pack(fill="x", pady=2)
        tk.Label(r3_1, text="Tên Nick / Nhóm:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t3_target = tk.Entry(r3_1, font=("Segoe UI", 9), width=25, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t3_target.pack(side="left", padx=5)
        self.t3_target.insert(0, "HỎI ĐỂ LÀM [MGP]")

        r3_2 = tk.Frame(c3, bg="#1e293b")
        r3_2.pack(fill="x", pady=2)
        tk.Label(r3_2, text="Tin nhắn chăm sóc:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t3_msg = tk.Entry(r3_2, font=("Segoe UI", 9), width=48, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t3_msg.pack(side="left", padx=5)
        self.t3_msg.insert(0, "Dạ Thầy/Cô ơi, Thầy/Cô đã tải được file giáo án chưa ạ? Nếu cần em hỗ trợ mở khoá Enable Editing nhắn em nhé! ✨")

        btn_t3 = tk.Button(c3, text="⏳ CHẠY TEST 3 (Gửi Nhắc Người Chưa Phản Hồi)", bg="#d97706", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._run_test_3)
        btn_t3.pack(anchor="e", pady=(4, 0))

        # Card 4: Test 4
        c4 = tk.LabelFrame(scrollable_frame, text=" 📢 TEST 4: Gửi Vào Nhóm Bất Kỳ Để Test (Group Chat) ", font=("Segoe UI", 9, "bold"), fg="#c084fc", bg="#1e293b", padx=10, pady=8)
        c4.pack(fill="x", pady=5)

        r4_1 = tk.Frame(c4, bg="#1e293b")
        r4_1.pack(fill="x", pady=2)
        tk.Label(r4_1, text="Tên Nhóm Zalo:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t4_group = tk.Entry(r4_1, font=("Segoe UI", 9), width=25, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t4_group.pack(side="left", padx=5)
        self.t4_group.insert(0, "P1.Nhóm AI")

        r4_2 = tk.Frame(c4, bg="#1e293b")
        r4_2.pack(fill="x", pady=2)
        tk.Label(r4_2, text="Tin nhắn thông báo:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t4_msg = tk.Entry(r4_2, font=("Segoe UI", 9), width=48, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t4_msg.pack(side="left", padx=5)
        self.t4_msg.insert(0, "🤖 [AI Bot Thông Báo]: Bộ giáo án Lịch sử 6-12 Kết Nối Tri Thức đã được cập nhật đầy đủ PPCT và Đề kiểm tra mới nhất!")

        btn_t4 = tk.Button(c4, text="📢 CHẠY TEST 4 (Gửi Vào Nhóm Bất Kỳ)", bg="#9333ea", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._run_test_4)
        btn_t4.pack(anchor="e", pady=(4, 0))

        # Card 5: Test 5
        c5 = tk.LabelFrame(scrollable_frame, text=" 🧠 TEST 5: Mở Thẻ 'FILE' & Gửi Tin Nhắn AI Tự Soạn ", font=("Segoe UI", 9, "bold"), fg="#f43f5e", bg="#1e293b", padx=10, pady=8)
        c5.pack(fill="x", pady=5)

        r5_1 = tk.Frame(c5, bg="#1e293b")
        r5_1.pack(fill="x", pady=2)
        tk.Label(r5_1, text="Thẻ phân loại:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t5_tag = tk.Entry(r5_1, font=("Segoe UI", 9), width=10, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t5_tag.pack(side="left", padx=5)
        self.t5_tag.insert(0, "FILE")

        tk.Label(r5_1, text="Nick nhận:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b").pack(side="left", padx=(10, 2))
        self.t5_nick = tk.Entry(r5_1, font=("Segoe UI", 9), width=18, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t5_nick.pack(side="left", padx=2)
        self.t5_nick.insert(0, "Thầy Nam (Ví dụ)")

        r5_2 = tk.Frame(c5, bg="#1e293b")
        r5_2.pack(fill="x", pady=2)
        tk.Label(r5_2, text="Câu hỏi để AI soạn:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", width=16, anchor="w").pack(side="left")
        self.t5_prompt = tk.Entry(r5_2, font=("Segoe UI", 9), width=48, bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.t5_prompt.pack(side="left", padx=5)
        self.t5_prompt.insert(0, "Em ơi file PowerPoint tải về mở ra hiện thanh màu vàng Protected View không chỉnh sửa được")

        btn_t5 = tk.Button(c5, text="🧠 CHẠY TEST 5 (Mở Thẻ FILE & AI Tự Soạn + Bắn Zalo)", bg="#e11d48", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._run_test_5)
        btn_t5.pack(anchor="e", pady=(4, 0))

        # Right Frame: Test Console
        right_frame = tk.Frame(paned, bg="#0b0f19", padx=10, pady=8)
        paned.add(right_frame, minsize=420)

        top_r = tk.Frame(right_frame, bg="#0b0f19")
        top_r.pack(fill="x", pady=(0, 5))
        tk.Label(top_r, text="📊 NHẬT KÝ THỰC THI TEST ZALO PC:", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0b0f19").pack(side="left")

        btn_clear_tlog = tk.Button(top_r, text="🧹 Xóa", bg="#334155", fg="#94a3b8", font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._clear_test_log)
        btn_clear_tlog.pack(side="right")

        self.test_log_text = tk.Text(
            right_frame,
            bg="#0b0f19",
            fg="#f8fafc",
            font=("Consolas", 9),
            wrap="word",
            padx=10,
            pady=8,
            insertbackground="white"
        )
        self.test_log_text.pack(fill="both", expand=True)

        self.test_log_text.tag_config("TIME", foreground="#64748b")
        self.test_log_text.tag_config("INFO", foreground="#38bdf8")
        self.test_log_text.tag_config("SUCCESS", foreground="#34d399", font=("Consolas", 9, "bold"))
        self.test_log_text.tag_config("WARNING", foreground="#fbbf24", font=("Consolas", 9, "bold"))
        self.test_log_text.tag_config("ERROR", foreground="#f87171", font=("Consolas", 9, "bold"))
        self.test_log_text.tag_config("HIGHLIGHT", foreground="#fde047", font=("Consolas", 9, "bold"))

    def _append_test_log(self, text: str, level: str = "INFO"):
        def _do():
            if not hasattr(self, "test_log_text") or not self.test_log_text.winfo_exists():
                return
            now_str = datetime.now().strftime("%H:%M:%S")
            self.test_log_text.insert(tk.END, f"[{now_str}] ", "TIME")
            self.test_log_text.insert(tk.END, f"{text}\n", level)
            self.test_log_text.see(tk.END)
        self.after(0, _do)

    def _clear_test_log(self):
        self.test_log_text.delete("1.0", tk.END)
        self.test_log_text.insert(tk.END, "--- Đã xóa sạch nhật ký Test ---\n\n", "INFO")

    def _run_test_1(self):
        nick = self.t1_nick.get().strip()
        msg = self.t1_msg.get().strip()
        if not nick or not msg:
            self.show_toast("Thiếu Thông Tin", "Vui lòng nhập tên Nick và Tin nhắn cho Test 1!", "warning")
            return

        def _worker():
            self._append_test_log(f"🚀 [TEST 1] Bắt đầu gửi 1 tin nhắn cho '{nick}'...", "HIGHLIGHT")
            self._append_test_log(f"   - Tin nhắn: \"{msg}\"", "INFO")
            ok = ZaloAutomation.send_messages_to_contact(nick, [msg], max_attempts=5)
            if ok:
                self._append_test_log(f"✅ [TEST 1 THÀNH CÔNG] Đã bắn tin nhắn vào Zalo của '{nick}'!", "SUCCESS")
                self._append_chat_message("AI", f"Gửi Test 1 cho '{nick}'", msg)
                self.show_toast("Test 1 Thành Công", f"Đã gửi tin nhắn đến '{nick}' trên Zalo PC!", "success")
            else:
                self._append_test_log(f"❌ [TEST 1 THẤT BẠI] Đã thử 5 lần nhưng không gửi được cho '{nick}'. Đã dừng lại.", "ERROR")
                self.show_toast("Test 1 Thất Bại", f"Không gửi được cho '{nick}' sau 5 lần thử.", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_test_2(self):
        nick1 = self.t2_nick1.get().strip()
        msg1 = self.t2_msg1.get().strip()
        nick2 = self.t2_nick2.get().strip()
        msg2 = self.t2_msg2.get().strip()

        if not nick1 or not msg1 or not nick2 or not msg2:
            self.show_toast("Thiếu Thông Tin", "Vui lòng nhập đầy đủ Người 1 và Người 2 cho Test 2!", "warning")
            return

        def _worker():
            self._append_test_log(f"👥 [TEST 2] Bắt đầu gửi lần lượt cho 2 người: '{nick1}' và '{nick2}'...", "HIGHLIGHT")
            self._append_test_log(f"   👉 Đang gửi cho người thứ 1: '{nick1}'...", "INFO")
            ok1 = ZaloAutomation.send_messages_to_contact(nick1, [msg1], max_attempts=5)
            if ok1:
                self._append_test_log(f"   ✅ Đã gửi xong cho người 1: '{nick1}'. Chờ 2 giây...", "SUCCESS")
                self._append_chat_message("AI", f"Người 1 ({nick1})", msg1)
            else:
                self._append_test_log(f"   ⚠️ Thử 5 lần gửi cho người 1 '{nick1}' thất bại.", "WARNING")

            time.sleep(2.0)

            self._append_test_log(f"   👉 Đang gửi cho người thứ 2: '{nick2}'...", "INFO")
            ok2 = ZaloAutomation.send_messages_to_contact(nick2, [msg2], max_attempts=5)
            if ok2:
                self._append_test_log(f"   ✅ Đã gửi xong cho người 2: '{nick2}'.", "SUCCESS")
                self._append_chat_message("AI", f"Người 2 ({nick2})", msg2)
            else:
                self._append_test_log(f"   ⚠️ Thử 5 lần gửi cho người 2 '{nick2}' thất bại.", "WARNING")

            if ok1 and ok2:
                self._append_test_log(f"🎉 [TEST 2 HOÀN TẤT] Đã gửi thành công cho cả 2 người đầu tiên!", "SUCCESS")
                self.show_toast("Test 2 Thành Công", f"Đã gửi thành công cho '{nick1}' và '{nick2}'!", "success")
            else:
                self._append_test_log(f"⚠️ [TEST 2 XONG] Kết quả: Người 1={ok1}, Người 2={ok2}", "WARNING")
                self.show_toast("Test 2 Hoàn Tất", f"Kết quả gửi: Người 1={ok1}, Người 2={ok2}", "warning")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_test_3(self):
        target = self.t3_target.get().strip()
        msg = self.t3_msg.get().strip()
        if not target or not msg:
            self.show_toast("Thiếu Thông Tin", "Vui lòng nhập đối tượng và tin nhắn cho Test 3!", "warning")
            return

        def _worker():
            self._append_test_log(f"⏳ [TEST 3] Bắt đầu gửi tin chăm sóc người/nhóm chưa phản hồi: '{target}'...", "HIGHLIGHT")
            self._append_test_log(f"   - Tin nhắn nhắc: \"{msg}\"", "INFO")
            ok = ZaloAutomation.send_messages_to_contact(target, [msg], max_attempts=5)
            if ok:
                self._append_test_log(f"✅ [TEST 3 THÀNH CÔNG] Đã gửi tin nhắn chăm sóc tới '{target}'!", "SUCCESS")
                self._append_chat_message("AI", f"Chăm sóc ({target})", msg)
                self.show_toast("Test 3 Thành Công", f"Đã gửi tin chăm sóc tới '{target}'!", "success")
            else:
                self._append_test_log(f"❌ [TEST 3 THẤT BẠI] Đã thử 5 lần không gửi được cho '{target}'. Đã dừng lại.", "ERROR")
                self.show_toast("Test 3 Thất Bại", f"Không gửi được cho '{target}' sau 5 lần thử.", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_test_4(self):
        group_name = self.t4_group.get().strip()
        msg = self.t4_msg.get().strip()
        if not group_name or not msg:
            self.show_toast("Thiếu Thông Tin", "Vui lòng nhập tên nhóm và tin nhắn cho Test 4!", "warning")
            return

        def _worker():
            self._append_test_log(f"📢 [TEST 4] Bắt đầu gửi tin vào nhóm: '{group_name}'...", "HIGHLIGHT")
            self._append_test_log(f"   - Tin thông báo nhóm: \"{msg}\"", "INFO")
            ok = ZaloAutomation.send_messages_to_contact(group_name, [msg], max_attempts=5)
            if ok:
                self._append_test_log(f"✅ [TEST 4 THÀNH CÔNG] Đã bắn tin nhắn thông báo vào nhóm '{group_name}'!", "SUCCESS")
                self._append_chat_message("AI", f"Nhóm ({group_name})", msg)
                self.show_toast("Test 4 Thành Công", f"Đã gửi tin nhắn vào nhóm '{group_name}'!", "success")
            else:
                self._append_test_log(f"❌ [TEST 4 THẤT BẠI] Đã thử 5 lần không tìm thấy/gửi được vào nhóm '{group_name}'. Đã dừng lại.", "ERROR")
                self.show_toast("Test 4 Thất Bại", f"Không gửi được vào nhóm '{group_name}' sau 5 lần thử.", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_test_5(self):
        tag = self.t5_tag.get().strip() or "FILE"
        nick = self.t5_nick.get().strip() or "Em Việt"
        prompt = self.t5_prompt.get().strip()

        if not prompt:
            self.show_toast("Thiếu Thông Tin", "Vui lòng nhập câu hỏi để AI sinh câu trả lời cho Test 5!", "warning")
            return

        def _worker():
            self._append_test_log(f"🧠 [TEST 5] Bắt đầu quy trình mở Thẻ '{tag}' & gọi AI sinh phản hồi...", "HIGHLIGHT")
            
            self._append_test_log(f"   👉 Bước 1: Kích hoạt Zalo & bấm lọc Thẻ '{tag}'...", "INFO")
            ZaloAutomation.click_tag_file_filter(max_attempts=2)
            
            self._append_test_log(f"   👉 Bước 2: Chuyển câu hỏi sang AI Gemini Multimodal ({self.gemini.model_name})...", "INFO")
            self._append_test_log(f"      Câu hỏi: \"{prompt}\"", "INFO")
            replies, analysis = self.gemini.generate_response(prompt)
            self._append_test_log(f"   👉 Bước 3: AI đã soạn xong {len(replies)} tin nhắn phản hồi chuẩn xác!", "SUCCESS")
            for i, r in enumerate(replies, 1):
                self._append_test_log(f"      [Tin {i}]: {r}", "INFO")

            self._append_test_log(f"   👉 Bước 4: Đang mở nick '{nick}' và bắn tin nhắn vào Zalo...", "INFO")
            ok = ZaloAutomation.send_messages_to_contact(nick, replies, delay_between=self.handler.reply_delay, max_attempts=5)
            if ok:
                self._append_test_log(f"🎉 [TEST 5 THÀNH CÔNG] Đã mở thẻ '{tag}' và gửi thành công câu trả lời AI cho '{nick}'!", "SUCCESS")
                for r in replies:
                    self._append_chat_message("AI", f"{nick} (Thẻ {tag})", r)
                self.show_toast("Test 5 Thành Công", f"Đã mở thẻ '{tag}' và gửi thành công {len(replies)} tin AI cho '{nick}'!", "success")
            else:
                self._append_test_log(f"❌ [TEST 5 THẤT BẠI] Đã thử 5 lần không gửi được vào Zalo PC. Đã dừng lại.", "ERROR")
                self.show_toast("Test 5 Thất Bại", f"Đã thử 5 lần gửi tin AI vào Zalo PC thất bại.", "error")

        threading.Thread(target=_worker, daemon=True).start()

    # ---------------- TAB 4: QUẢN LÝ ĐA API KEYS & MODELS GEMINI ----------------
    def _build_api_keys_tab(self, parent):
        top_frame = tk.Frame(parent, bg="#0f172a", pady=5)
        top_frame.pack(fill="x")

        # Box 1: Chọn Model & Quét Models từ Google AI Studio
        model_box = tk.LabelFrame(top_frame, text=" 🎯 Cấu Hình & Bộ Lọc Model AI Gemini (Google AI Studio) ", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", padx=10, pady=8)
        model_box.pack(fill="x", pady=4)

        row_m1 = tk.Frame(model_box, bg="#1e293b")
        row_m1.pack(fill="x", pady=2)

        tk.Label(row_m1, text="Model đang dùng:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b").pack(side="left")
        self.api_model_cb = ttk.Combobox(row_m1, values=self._get_active_model_list(), width=22, state="readonly")
        self.api_model_cb.set(self.gemini.model_name)
        self.api_model_cb.pack(side="left", padx=8)

        btn_apply_model = tk.Button(row_m1, text="💾 Đổi Model Này", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._apply_selected_model)
        btn_apply_model.pack(side="left", padx=4)

        tk.Label(row_m1, text="🔍 Bộ lọc phiên bản:", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b").pack(side="left", padx=(14, 4))
        self.api_model_filter_cb = ttk.Combobox(
            row_m1,
            values=GEMINI_VERSION_FILTER_OPTIONS,
            width=32,
            state="readonly"
        )
        cur_min_v = self.app_settings.get("min_gemini_version", GEMINI_VERSION_FILTER_OPTIONS[0])
        matched_opt = GEMINI_VERSION_FILTER_OPTIONS[0]
        for opt in GEMINI_VERSION_FILTER_OPTIONS:
            if str(cur_min_v) in opt or opt in str(cur_min_v):
                matched_opt = opt
                break
        self.api_model_filter_cb.set(matched_opt)
        self.api_model_filter_cb.pack(side="left", padx=4)
        self.api_model_filter_cb.bind("<<ComboboxSelected>>", self._on_api_filter_combobox_changed)

        btn_scan_models = tk.Button(row_m1, text="🔄 Quét & Tải Models", bg="#8b5cf6", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2, cursor="hand2", command=self._scan_available_models)
        btn_scan_models.pack(side="left", padx=8)

        # Box 2: Nhập hàng loạt API Keys (Mỗi dòng 1 key)
        import_box = tk.LabelFrame(top_frame, text=" 📥 Nhập Hàng Loạt API Key (Mỗi Key 1 Dòng - Chống Quá Quota 429 Tự Động) ", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", padx=10, pady=8)
        import_box.pack(fill="x", pady=4)

        self.multi_keys_text = tk.Text(import_box, height=4, font=("Consolas", 9), bg="#0f172a", fg="#f8fafc", insertbackground="white", padx=8, pady=6)
        self.multi_keys_text.pack(fill="x", pady=2)
        self.multi_keys_text.insert("1.0", "# Dán danh sách API Key vào đây (mỗi dòng 1 key):\nAIzaSy...")

        btn_import_keys = tk.Button(import_box, text="📥 Nhập & Thêm Danh Sách Key Này Vào Hệ Thống", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2", command=self._import_multi_keys)
        btn_import_keys.pack(anchor="e", pady=4)

        # Bảng Danh Sách API Keys
        list_lbl = tk.Label(parent, text="📋 Danh Sách Các API Keys Đang Quản Lý (Tự động chuyển Key khi hết Quota):", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#38bdf8")
        list_lbl.pack(anchor="w", pady=(10, 4))

        cols = ("id", "active", "masked_key", "status", "requests", "errors", "msg", "checked_at")
        self.keys_tree = ttk.Treeview(parent, columns=cols, show="headings", height=9)
        self.keys_tree.heading("id", text="ID")
        self.keys_tree.heading("active", text="Đang Dùng")
        self.keys_tree.heading("masked_key", text="API Key")
        self.keys_tree.heading("status", text="Trạng Thái Quota")
        self.keys_tree.heading("requests", text="Lượt Gọi")
        self.keys_tree.heading("errors", text="Lỗi")
        self.keys_tree.heading("msg", text="Chi Tiết / Phản Hồi Test")
        self.keys_tree.heading("checked_at", text="Kiểm Tra Gần Nhất")

        self.keys_tree.column("id", width=40, anchor="center")
        self.keys_tree.column("active", width=90, anchor="center")
        self.keys_tree.column("masked_key", width=160, anchor="center")
        self.keys_tree.column("status", width=140, anchor="center")
        self.keys_tree.column("requests", width=80, anchor="center")
        self.keys_tree.column("errors", width=60, anchor="center")
        self.keys_tree.column("msg", width=340)
        self.keys_tree.column("checked_at", width=130)
        self.keys_tree.pack(fill="both", expand=True, pady=4)

        # Thanh Thao Tác Bảng Keys
        btn_bar = tk.Frame(parent, bg="#0f172a", pady=8)
        btn_bar.pack(fill="x")

        tk.Label(btn_bar, text="Thao tác Key được chọn:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a").pack(side="left", padx=(0, 5))

        btn_set_active = tk.Button(btn_bar, text="⭐ Kích Hoạt Key Này", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._set_active_key_from_ui)
        btn_set_active.pack(side="left", padx=3)

        btn_check_one = tk.Button(btn_bar, text="🧪 Kiểm Tra Key Này", bg="#3b82f6", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=2, cursor="hand2", command=self._check_selected_key)
        btn_check_one.pack(side="left", padx=3)

        btn_reset_one = tk.Button(btn_bar, text="🔄 Reset Quota Key Này", bg="#d97706", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=2, cursor="hand2", command=self._reset_selected_quota)
        btn_reset_one.pack(side="left", padx=3)

        btn_del_one = tk.Button(btn_bar, text="🗑️ Xóa Key", bg="#ef4444", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=2, cursor="hand2", command=self._delete_selected_key)
        btn_del_one.pack(side="left", padx=3)

        sep = ttk.Separator(btn_bar, orient="vertical")
        sep.pack(side="left", fill="y", padx=10)

        btn_check_all = tk.Button(btn_bar, text="🧪 Kiểm Tra TẤT CẢ Key", bg="#6366f1", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._check_all_keys)
        btn_check_all.pack(side="left", padx=4)

        btn_reset_all = tk.Button(btn_bar, text="🔄 Reset Quota TẤT CẢ Key", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._reset_all_quota)
        btn_reset_all.pack(side="left", padx=4)

        btn_refresh_table = tk.Button(btn_bar, text="🔄 Làm Mới", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=2, cursor="hand2", command=self._refresh_api_keys_table)
        btn_refresh_table.pack(side="right", padx=4)

    def _refresh_api_keys_table(self):
        for row in self.keys_tree.get_children():
            self.keys_tree.delete(row)
        
        all_keys = self.key_mgr.get_all_keys()
        for k in all_keys:
            active_badge = "⭐ ĐANG DÙNG" if k["is_active"] == 1 else ""
            status_display = {
                "ACTIVE": "🟢 ĐANG DÙNG",
                "AVAILABLE": "🔵 SẴN SÀNG",
                "QUOTA_EXCEEDED": "🟡 HẾT QUOTA (429)",
                "INVALID": "🔴 LỖI (INVALID)",
                "ERROR": "⚠️ LỖI KẾT NỐI"
            }.get(k["status"], k["status"])

            self.keys_tree.insert("", "end", iid=str(k["id"]), values=(
                k["id"],
                active_badge,
                k["masked_key"],
                status_display,
                k["request_count"],
                k["error_count"],
                k["last_status_msg"] or "-",
                k["last_checked_at"] or "-"
            ))

        self._update_header_status_label()

    def _import_multi_keys(self):
        raw = self.multi_keys_text.get("1.0", tk.END).strip()
        if not raw or raw.startswith("#"):
            self.show_toast("Cảnh Báo", "Vui lòng dán ít nhất 1 API Key vào khung nhập!", "warning")
            return

        added, total = self.key_mgr.add_keys(raw)
        self.multi_keys_text.delete("1.0", tk.END)
        self.multi_keys_text.insert("1.0", "# Dán thêm API Key khác vào đây...")
        self._refresh_api_keys_table()
        self.show_toast("Thành Công", f"Đã thêm thành công {added} API Key mới! (Tổng: {total} Keys)", "success")

    def _set_active_key_from_ui(self):
        sel = self.keys_tree.selection()
        if not sel:
            self.show_toast("Thông Báo", "Vui lòng chọn 1 Key trong bảng để kích hoạt!", "warning")
            return
        key_id = int(sel[0])
        self.key_mgr.set_active_key(key_id)
        self.gemini._init_client()
        self._refresh_api_keys_table()
        self.show_toast("Thành Công", f"Đã đặt Key #{key_id} làm API Key chính!", "success")

    def _check_selected_key(self):
        sel = self.keys_tree.selection()
        if not sel:
            self.show_toast("Thông Báo", "Vui lòng chọn 1 Key trong bảng để kiểm tra!", "warning")
            return
        key_id = int(sel[0])

        def _worker():
            ok, msg = self.key_mgr.check_single_key(key_id, model_name=self.gemini.model_name)
            self._refresh_api_keys_table()
            if ok:
                self.show_toast("Kết Quả Test", f"Key #{key_id} hoạt động tốt!", "success")
            else:
                self.show_toast("Kết Quả Test", f"Key #{key_id} lỗi: {msg[:100]}", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _check_all_keys(self):
        def _worker():
            results = self.key_mgr.check_all_keys(model_name=self.gemini.model_name)
            self._refresh_api_keys_table()
            success_count = sum(1 for r in results if r["success"])
            self.show_toast("Hoàn Tất Kiểm Tra", f"Kiểm tra xong {len(results)} Keys (Sống: {success_count}, Hết Quota/Lỗi: {len(results)-success_count})", "info")

        threading.Thread(target=_worker, daemon=True).start()

    def _reset_selected_quota(self):
        sel = self.keys_tree.selection()
        if not sel:
            self.show_toast("Thông Báo", "Vui lòng chọn 1 Key trong bảng để Reset Quota!", "warning")
            return
        key_id = int(sel[0])
        self.key_mgr.reset_quota(key_id)
        self._refresh_api_keys_table()
        self.show_toast("Thành Công", f"Đã Reset trạng thái Quota cho Key #{key_id} về Sẵn Sàng!", "success")

    def _reset_all_quota(self):
        count = self.key_mgr.reset_quota()
        self._refresh_api_keys_table()
        self.show_toast("Thành Công", f"Đã Reset Quota cho toàn bộ {count} Keys!", "success")

    def _delete_selected_key(self):
        sel = self.keys_tree.selection()
        if not sel:
            self.show_toast("Thông Báo", "Vui lòng chọn 1 Key để xóa!", "warning")
            return
        key_id = int(sel[0])
        self.key_mgr.delete_key(key_id)
        self._refresh_api_keys_table()
        self.show_toast("Đã Xóa", f"Đã xóa Key #{key_id} khỏi hệ thống.", "info")

    def _apply_selected_model(self):
        model = self.api_model_cb.get().strip()
        if not model:
            return
        self.gemini.set_model(model)
        self.gemini.save_api_key_to_config(self.gemini.api_key)
        self.hdr_model_cb.set(model)
        if hasattr(self, "pg_model_cb"):
            self.pg_model_cb.set(model)
        self._refresh_api_keys_table()
        self.show_toast("Thành Công", f"Đã đổi Model AI thành: '{model}'!", "success")

    def _on_api_filter_combobox_changed(self, event=None):
        """Khi Admin thay đổi bộ lọc phiên bản model trong Tab API Keys."""
        new_val = self.api_model_filter_cb.get().strip()
        self.app_settings["min_gemini_version"] = new_val
        self._save_app_settings(self.app_settings)
        self._refresh_all_model_comboboxes()
        if hasattr(self, "setting_min_version_cb") and self.setting_min_version_cb.winfo_exists():
            self.setting_min_version_cb.set(new_val)
        self.show_toast("Bộ Lọc Model", f"Đã áp dụng bộ lọc: {new_val}!", "info")

    def _scan_available_models(self):
        def _worker():
            active_key = self.key_mgr.get_active_key()
            if not active_key:
                self.show_toast("Cảnh Báo", "Chưa có API Key nào được kích hoạt để quét!", "warning")
                return
            min_ver = parse_gemini_min_version(self.app_settings.get("min_gemini_version", "3.1"))
            hide_below_3_1 = self.app_settings.get("hide_models_below_3_1", True)
            models = self.key_mgr.list_available_models(api_key=active_key, hide_below_3_1=hide_below_3_1, min_version=min_ver)
            if models:
                self.after(0, lambda: self._refresh_all_model_comboboxes())
                self.show_toast("Quét Thành Công", f"Đã quét và lọc được {len(models)} Models hợp lệ (>= {min_ver}) từ Google AI Studio!", "success")
            else:
                self.show_toast("Cảnh Báo", "Không thể lấy danh sách model từ API.", "warning")

        threading.Thread(target=_worker, daemon=True).start()

    # ---------------- TAB 5: SỔ TAY SỬA GIÁO ÁN ----------------
    def _build_corrections_tab(self, parent):
        lbl_info = tk.Label(
            parent,
            text="📌 Danh sách các phản hồi về nội dung, bài thiếu, góp ý từ Thầy/Cô được AI tự động ghi nhận:",
            font=("Segoe UI", 10, "bold"),
            bg="#0f172a",
            fg="#38bdf8"
        )
        lbl_info.pack(anchor="w", pady=(0, 10))

        cols = ("id", "teacher", "grade", "feedback", "status", "date")
        self.corr_tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        self.corr_tree.heading("id", text="ID")
        self.corr_tree.heading("teacher", text="Thầy/Cô")
        self.corr_tree.heading("grade", text="Khối/Lớp")
        self.corr_tree.heading("feedback", text="Nội Dung Cần Sửa/Bổ Sung")
        self.corr_tree.heading("status", text="Trạng Thái")
        self.corr_tree.heading("date", text="Thời Gian")

        self.corr_tree.column("id", width=40, anchor="center")
        self.corr_tree.column("teacher", width=120)
        self.corr_tree.column("grade", width=80, anchor="center")
        self.corr_tree.column("feedback", width=450)
        self.corr_tree.column("status", width=110, anchor="center")
        self.corr_tree.column("date", width=130)
        self.corr_tree.pack(fill="both", expand=True)

        btn_bar = tk.Frame(parent, bg="#0f172a", pady=10)
        btn_bar.pack(fill="x")

        btn_mark_fixed = tk.Button(
            btn_bar,
            text="✨ Đã Sửa Xong Giáo Án Này",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._mark_correction_fixed
        )
        btn_mark_fixed.pack(side="left", padx=5)

        btn_refresh_corr = tk.Button(
            btn_bar,
            text="🔄 Làm Mới Danh Sách",
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._refresh_corrections
        )
        btn_refresh_corr.pack(side="left", padx=5)

    # ---------------- TAB 6: QUẢN LÝ LINK & EMAIL DRIVE ----------------
    def _build_drive_tab(self, parent):
        top_filter = tk.Frame(parent, bg="#0f172a", pady=5)
        top_filter.pack(fill="x")

        tk.Label(top_filter, text="Lọc theo Khối/Lớp:", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left")
        self.drive_filter_grade = ttk.Combobox(top_filter, values=["Tất cả", "THCS", "THPT", "6", "7", "8", "9", "10", "11", "12"], width=10, state="readonly")
        self.drive_filter_grade.set("Tất cả")
        self.drive_filter_grade.pack(side="left", padx=10)
        self.drive_filter_grade.bind("<<ComboboxSelected>>", lambda e: self._refresh_drive_logs())

        btn_reload = tk.Button(top_filter, text="🔄 Tải Lại", bg="#475569", fg="white", relief="flat", padx=8, cursor="hand2", command=self._refresh_drive_logs)
        btn_reload.pack(side="left", padx=5)

        cols = ("id", "email", "grade", "link_type", "drive_link", "time")
        self.drive_tree = ttk.Treeview(parent, columns=cols, show="headings", height=13)
        self.drive_tree.heading("id", text="ID")
        self.drive_tree.heading("email", text="Email Gmail")
        self.drive_tree.heading("grade", text="Khối/Lớp")
        self.drive_tree.heading("link_type", text="Loại Link (Chính/Phụ)")
        self.drive_tree.heading("drive_link", text="Đường Dẫn Drive Đã Cấp")
        self.drive_tree.heading("time", text="Thời Gian")

        self.drive_tree.column("id", width=40, anchor="center")
        self.drive_tree.column("email", width=220)
        self.drive_tree.column("grade", width=80, anchor="center")
        self.drive_tree.column("link_type", width=120, anchor="center")
        self.drive_tree.column("drive_link", width=380)
        self.drive_tree.column("time", width=130)
        self.drive_tree.pack(fill="both", expand=True, pady=5)

        drive_action_bar = tk.Frame(parent, bg="#0f172a", pady=10)
        drive_action_bar.pack(fill="x")

        btn_copy_one = tk.Button(drive_action_bar, text="📋 Copy 1 Email Đã Chọn", bg="#3b82f6", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=3, cursor="hand2", command=self._copy_selected_email)
        btn_copy_one.pack(side="left", padx=5)

        btn_copy_all = tk.Button(drive_action_bar, text="📋 Copy Toàn Bộ Email Đang Lọc (Dán chia sẻ)", bg="#8b5cf6", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2", command=self._copy_all_filtered_emails)
        btn_copy_all.pack(side="left", padx=5)

        btn_export = tk.Button(drive_action_bar, text="💾 Xuất File (CSV / TXT)", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2", command=self._export_emails)
        btn_export.pack(side="left", padx=5)

    # ---------------- TAB 7: TÌM KIẾM NHANH TÀI LIỆU ----------------
    def _build_search_tab(self, parent):
        search_bar = tk.Frame(parent, bg="#0f172a", pady=10)
        search_bar.pack(fill="x")

        tk.Label(search_bar, text="Khối/Lớp:", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left")
        self.search_grade_cb = ttk.Combobox(search_bar, values=["Tất cả", "6", "7", "8", "9", "10", "11", "12"], width=8, state="readonly")
        self.search_grade_cb.set("Tất cả")
        self.search_grade_cb.pack(side="left", padx=5)

        tk.Label(search_bar, text="Loại tài liệu:", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left", padx=(10, 0))
        self.search_type_cb = ttk.Combobox(search_bar, values=["Tất cả", "PPCT", "Đề kiểm tra", "Phiếu học tập", "Bài giảng (PPT)"], width=14, state="readonly")
        self.search_type_cb.set("Tất cả")
        self.search_type_cb.pack(side="left", padx=5)

        tk.Label(search_bar, text="Từ khóa:", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left", padx=(10, 0))
        self.search_entry = tk.Entry(search_bar, font=("Segoe UI", 10), width=25, bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self._perform_local_search())

        btn_search = tk.Button(search_bar, text="🔍 Tìm Kiếm", bg="#0284c7", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=10, pady=2, cursor="hand2", command=self._perform_local_search)
        btn_search.pack(side="left", padx=10)

        cols = ("name", "size", "dir")
        self.search_tree = ttk.Treeview(parent, columns=cols, show="headings", height=13)
        self.search_tree.heading("name", text="Tên File Tài Liệu")
        self.search_tree.heading("size", text="Dung Lượng (MB)")
        self.search_tree.heading("dir", text="Đường Dẫn Trong Máy Tính")

        self.search_tree.column("name", width=350)
        self.search_tree.column("size", width=120, anchor="center")
        self.search_tree.column("dir", width=500)
        self.search_tree.pack(fill="both", expand=True, pady=5)

        search_actions = tk.Frame(parent, bg="#0f172a", pady=10)
        search_actions.pack(fill="x")

        btn_open_folder = tk.Button(search_actions, text="📂 Mở Thư Mục Chứa File (Để kéo thả Zalo)", bg="#d97706", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2", command=self._open_selected_folder)
        btn_open_folder.pack(side="left", padx=5)

        btn_copy_path = tk.Button(search_actions, text="📋 Copy Đường Dẫn File", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=3, cursor="hand2", command=self._copy_selected_file_path)
        btn_copy_path.pack(side="left", padx=5)

    # ---------------- TAB 8: GIẢ LẬP KỊCH BẢN MẪU ----------------
    def _build_simulator_tab(self, parent):
        top_guide = tk.Label(
            parent,
            text="🧪 TRÌNH GIẢ LẬP KỊCH BẢN TỪ ĐẦU ĐẾN CUỐI (Tự động cập nhật Database, Drive, Sổ tay & Chat):",
            font=("Segoe UI", 10, "bold"),
            bg="#0f172a",
            fg="#38bdf8"
        )
        top_guide.pack(anchor="w", pady=(0, 5))

        scenario_frame = tk.Frame(parent, bg="#1e293b", padx=10, pady=8, relief="flat")
        scenario_frame.pack(fill="x", pady=5)

        tk.Label(scenario_frame, text="📌 Chọn Kịch Bản Mẫu Thực Tế:", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#f8fafc").pack(side="left")

        self.scenario_combobox = ttk.Combobox(
            scenario_frame,
            values=[
                "1. Khách gửi Email xin cấp quyền Google Drive Lớp 10",
                "2. Khách xin tài liệu PPCT & Đề kiểm tra Lớp 11",
                "3. Khách báo lỗi mở file PowerPoint bị khóa 'Enable Editing'",
                "4. Khách phản hồi góp ý nội dung bài (Lưu Sổ tay & Bắn Telegram)",
                "5. Khách hỏi lại 3 lần (Kích hoạt Escalation + Telegram + Can thiệp tay)",
                "6. Khách cảm ơn & hoàn thành hội thoại (RESOLVED)"
            ],
            width=55,
            state="readonly"
        )
        self.scenario_combobox.set("1. Khách gửi Email xin cấp quyền Google Drive Lớp 10")
        self.scenario_combobox.pack(side="left", padx=10)
        self.scenario_combobox.bind("<<ComboboxSelected>>", self._on_scenario_selected)

        info_frame = tk.Frame(parent, bg="#0f172a", pady=5)
        info_frame.pack(fill="x")

        tk.Label(info_frame, text="Tên Thầy/Cô:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.sim_name_entry = tk.Entry(info_frame, font=("Segoe UI", 9), width=25, bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.sim_name_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.sim_name_entry.insert(0, "Cô Nguyễn Thị Mai")

        tk.Label(info_frame, text="Mã Khách (Zalo ID):", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").grid(row=0, column=2, sticky="w", padx=15, pady=2)
        self.sim_uid_entry = tk.Entry(info_frame, font=("Segoe UI", 9), width=20, bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.sim_uid_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.sim_uid_entry.insert(0, "zalo_gv_mai_10")

        input_frame = tk.Frame(parent, bg="#0f172a", pady=5)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="Nội dung tin nhắn:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left", padx=5)
        self.sim_entry = tk.Entry(input_frame, font=("Segoe UI", 10), width=50, bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.sim_entry.pack(side="left", padx=5)
        self.sim_entry.insert(0, "Email của cô là: nguyenthimai@gmail.com, cấp quyền Drive lớp 10 giúp cô nhé em")

        self.selected_img_path = ""
        self.btn_select_img = tk.Button(input_frame, text="📷 Chọn Ảnh Lỗi", bg="#3b82f6", fg="white", font=("Segoe UI", 9), relief="flat", padx=6, cursor="hand2", command=self._select_test_image)
        self.btn_select_img.pack(side="left", padx=5)

        self.sim_send_zalo_pc_var = tk.BooleanVar(value=False)
        chk_pc = tk.Checkbutton(
            input_frame,
            text="⚡ Bắn trực tiếp vào Zalo PC",
            variable=self.sim_send_zalo_pc_var,
            bg="#0f172a",
            fg="#38bdf8",
            activebackground="#0f172a",
            font=("Segoe UI", 9, "bold"),
            selectcolor="#1e293b"
        )
        chk_pc.pack(side="left", padx=5)

        btn_run_sim = tk.Button(
            input_frame,
            text="▶ CHẠY GIẢ LẬP KỊCH BẢN NÀY",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._run_simulation
        )
        btn_run_sim.pack(side="left", padx=5)

        tk.Label(parent, text="📊 Kết quả mô phỏng chi tiết từng hệ thống:", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#38bdf8").pack(anchor="w", pady=(10, 5))
        self.sim_result_text = tk.Text(parent, font=("Segoe UI", 10), height=14, bg="#0b0f19", fg="#f8fafc", padx=12, pady=10, insertbackground="white")
        self.sim_result_text.pack(fill="both", expand=True)

    # ---------------- TAB 9: CONSOLE HỆ THỐNG & LIVE PIPELINE ----------------
    def _build_console_tab(self, parent):
        pipeline_frame = tk.Frame(parent, bg="#1e293b", padx=10, pady=8)
        pipeline_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            pipeline_frame,
            text="🚀 QUY TRÌNH 5 BƯỚC:",
            font=("Segoe UI", 9, "bold"),
            fg="#fbbf24",
            bg="#1e293b"
        ).pack(side="left", padx=(0, 5))

        steps = [
            ("1. Tiếp nhận", "#38bdf8"),
            ("➔", "#64748b"),
            ("2. Trạng thái Bot", "#a855f7"),
            ("➔", "#64748b"),
            ("3. Phân tích Intent", "#06b6d4"),
            ("➔", "#64748b"),
            ("4. Gemini & RAG FAQ", "#ec4899"),
            ("➔", "#64748b"),
            ("5. Gửi & Escalation", "#34d399")
        ]
        for txt, color in steps:
            tk.Label(pipeline_frame, text=txt, font=("Segoe UI", 9, "bold" if txt != "➔" else "normal"), fg=color, bg="#1e293b").pack(side="left", padx=2)

        toolbar = tk.Frame(parent, bg="#0f172a", pady=4)
        toolbar.pack(fill="x")

        btn_clear = tk.Button(toolbar, text="🧹 Xóa Màn Hình", bg="#334155", fg="#f8fafc", font=("Segoe UI", 9), relief="flat", padx=8, cursor="hand2", command=self._clear_console_log)
        btn_clear.pack(side="left", padx=4)

        btn_copy = tk.Button(toolbar, text="📋 Copy Toàn Bộ Log", bg="#3b82f6", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, cursor="hand2", command=self._copy_console_log)
        btn_copy.pack(side="left", padx=4)

        self.auto_scroll_var = tk.BooleanVar(value=True)
        chk_scroll = tk.Checkbutton(
            toolbar,
            text="Tự động cuộn xuống cuối (Auto-scroll)",
            variable=self.auto_scroll_var,
            bg="#0f172a",
            fg="#94a3b8",
            activebackground="#0f172a",
            font=("Segoe UI", 9),
            selectcolor="#1e293b",
            command=self._toggle_auto_scroll
        )
        chk_scroll.pack(side="left", padx=15)

        btn_test_pipeline = tk.Button(
            toolbar,
            text="⚡ Chạy Test 1 Lượt Quy Trình AI Mẫu",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._test_pipeline_flow
        )
        btn_test_pipeline.pack(side="right", padx=4)

        console_container = tk.Frame(parent, bg="#0b0f19")
        console_container.pack(fill="both", expand=True, pady=5)

        scrollbar = tk.Scrollbar(console_container)
        scrollbar.pack(side="right", fill="y")

        self.console_text = tk.Text(
            console_container,
            bg="#0b0f19",
            fg="#f8fafc",
            font=("Consolas", 10),
            wrap="word",
            padx=12,
            pady=10,
            yscrollcommand=scrollbar.set,
            insertbackground="white"
        )
        self.console_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.console_text.yview)

        self.console_text.tag_config("TIME", foreground="#64748b")
        self.console_text.tag_config("INFO", foreground="#38bdf8")
        self.console_text.tag_config("STEP", foreground="#c084fc", font=("Consolas", 10, "bold"))
        self.console_text.tag_config("SUCCESS", foreground="#34d399", font=("Consolas", 10, "bold"))
        self.console_text.tag_config("WARNING", foreground="#fbbf24", font=("Consolas", 9, "bold"))
        self.console_text.tag_config("ERROR", foreground="#f87171", font=("Consolas", 10, "bold"))
        self.console_text.tag_config("CUSTOMER", foreground="#67e8f9")
        self.console_text.tag_config("OUTGOING", foreground="#86efac")
        self.console_text.tag_config("TITLE", foreground="#fde047", font=("Consolas", 10, "bold"))

        welcome_banner = (
            "========================================================================================\n"
            "   🤖 HỆ THỐNG AI CSKH ZALO - GIÁO ÁN LỊCH SỬ KẾT NỐI TRI THỨC (6-12) - LIVE CONSOLE\n"
            "========================================================================================\n"
            " [Hệ thống] Trạng thái: Sẵn sàng nhận và phân tích tin nhắn thời gian thực.\n"
            "----------------------------------------------------------------------------------------\n\n"
        )
        self.console_text.insert(tk.END, welcome_banner, "TITLE")

    def _append_console_log(self, msg: str, level: str):
        def _do_append():
            if not hasattr(self, "console_text") or not self.console_text.winfo_exists():
                return
            now_str = datetime.now().strftime("%H:%M:%S")
            self.console_text.insert(tk.END, f"[{now_str}] ", "TIME")

            if "BƯỚC" in msg:
                self.console_text.insert(tk.END, f"{msg}\n", "STEP")
            elif level == "WARNING" or "TẠM DỪNG" in msg or "CAN THIỆP" in msg:
                self.console_text.insert(tk.END, f"{msg}\n", "WARNING")
            elif level == "ERROR" or "ESCALATION" in msg:
                self.console_text.insert(tk.END, f"{msg}\n", "ERROR")
            elif "Outgoing" in msg or "thành công" in msg.lower():
                self.console_text.insert(tk.END, f"{msg}\n", "SUCCESS")
            elif "Incoming" in msg or "Khách" in msg:
                self.console_text.insert(tk.END, f"{msg}\n", "CUSTOMER")
            else:
                self.console_text.insert(tk.END, f"{msg}\n", "INFO")

            if self.auto_scroll_console:
                self.console_text.see(tk.END)

        self.after(0, _do_append)

    def _on_step_log(self, step_no: int, step_title: str, detail: str, level: str):
        def _do_step():
            if not hasattr(self, "console_text") or not self.console_text.winfo_exists():
                return
            now_str = datetime.now().strftime("%H:%M:%S")
            step_icons = {1: "📥", 2: "⚙️", 3: "🔍", 4: "🧠", 5: "🚀"}
            icon = step_icons.get(step_no, "📌")
            line = f"[{now_str}] {icon} [BƯỚC {step_no}/5: {step_title}] {detail}\n"
            tag = "ERROR" if level == "ERROR" else ("WARNING" if level == "WARNING" else "STEP")
            self.console_text.insert(tk.END, line, tag)
            if self.auto_scroll_console:
                self.console_text.see(tk.END)

        self.after(0, _do_step)

    def _clear_console_log(self):
        self.console_text.delete("1.0", tk.END)
        self.console_text.insert(tk.END, "--- Đã xóa sạch nhật ký Console ---\n\n", "INFO")

    def _copy_console_log(self):
        content = self.console_text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(content)
        self.show_toast("Đã Copy", "Đã copy toàn bộ nội dung Console vào Clipboard!", "info")

    def _toggle_auto_scroll(self):
        self.auto_scroll_console = self.auto_scroll_var.get()

    def _test_pipeline_flow(self):
        def _worker():
            sample_tests = [
                ("GV_NguyenVanA", "Thầy Nguyễn Văn A", "Cô gửi giúp tôi link PPCT và Đề kiểm tra Lớp 10 sách Kết Nối Tri Thức với"),
                ("GV_TranThiB", "Cô Trần Thị B", "Email của cô là: nguyenthimai@gmail.com, cấp quyền Drive lớp 12 giúp cô nhé"),
                ("GV_LeVanC", "Thầy Lê Văn C", "Bài 5 Lịch sử lớp 11 phần khởi nghĩa Lam Sơn hình như bị lỗi font chữ không đọc được em ơi")
            ]
            import random
            uid, name, msg = random.choice(sample_tests)
            self.handler.handle_incoming_message(uid, name, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scenario_selected(self, event=None):
        val = self.scenario_combobox.get()
        self.selected_img_path = ""
        self.btn_select_img.config(text="📷 Chọn Ảnh Lỗi")

        if "1. Khách gửi Email" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Cô Nguyễn Thị Mai")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_mai_10")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Email của cô là: nguyenthimai@gmail.com, cấp quyền Drive lớp 10 giúp cô nhé em")

        elif "2. Khách xin tài liệu" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Thầy Trần Văn Bình")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_binh_11")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Chào em, gửi giúp thầy file PPCT và Đề kiểm tra Lớp 11 sách Kết Nối Tri Thức với")

        elif "3. Khách báo lỗi mở file" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Cô Lê Thu Hà")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_ha_12")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Em ơi file PowerPoint tải về mở ra hiện thanh màu vàng Protected View không chỉnh sửa được")

        elif "4. Khách phản hồi góp ý" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Thầy Phạm Đức Minh")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_minh_12")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Bài 5 Lịch sử 12 phần ASEAN có bảng số liệu hình như chưa cập nhật theo sách mới, em xem lại nhé")

        elif "5. Khách hỏi lại 3 lần" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Cô Đỗ Hoàng Yến")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_yen_escalate")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Cô vẫn chưa tải được file giáo án em ơi, làm theo mãi không được")
            self.state.update_conversation_status("zalo_gv_yen_escalate", "IN_PROGRESS", unresolved_delta=2)

        elif "6. Khách cảm ơn" in val:
            self.sim_name_entry.delete(0, tk.END)
            self.sim_name_entry.insert(0, "Thầy Vũ Quốc Tuấn")
            self.sim_uid_entry.delete(0, tk.END)
            self.sim_uid_entry.insert(0, "zalo_gv_tuan_done")
            self.sim_entry.delete(0, tk.END)
            self.sim_entry.insert(0, "Cảm ơn em nhiều nhé, thầy đã tải và mở dạy được rồi!")

    def _select_test_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.webp")])
        if path:
            self.selected_img_path = path
            self.btn_select_img.config(text=f"📷 Đã chọn: {os.path.basename(path)}")
            self.show_toast("Đã Chọn Ảnh", f"Đã nạp file: {os.path.basename(path)}", "info")

    def _run_simulation(self):
        name = self.sim_name_entry.get().strip() or "Thầy/Cô Giáo"
        uid = self.sim_uid_entry.get().strip() or "test_user_sim"
        msg = self.sim_entry.get().strip()
        img = self.selected_img_path or None

        if not msg and not img:
            self.show_toast("Cảnh Báo", "Vui lòng nhập nội dung tin nhắn hoặc chọn ảnh lỗi!", "warning")
            return

        self.sim_result_text.delete("1.0", tk.END)
        self.sim_result_text.insert(tk.END, f"⏳ Đang thực thi quy trình giả lập trọn gói cho '{name}' ({uid})...\n\n")

        def _worker():
            try:
                res = self.handler.handle_incoming_message(
                    user_id=uid,
                    display_name=name,
                    message_text=msg,
                    image_path=img
                )
                replies = res.get("replies", [])
                status = res.get("status", "unknown")

                def _ui_update():
                    try:
                        self.sim_result_text.delete("1.0", tk.END)
                        banner = f"========================================================================\n"
                        banner += f"   ✅ KẾT QUẢ THỰC THI QUY TRÌNH TỪ ĐẦU ĐẾN CUỐI (END-TO-END)\n"
                        banner += f"========================================================================\n\n"
                        self.sim_result_text.insert(tk.END, banner)

                        self.sim_result_text.insert(tk.END, f"1️⃣ THÔNG TIN TIẾP NHẬN:\n")
                        self.sim_result_text.insert(tk.END, f"   - Khách hàng: {name} (Mã ID: {uid})\n")
                        self.sim_result_text.insert(tk.END, f"   - Tin nhắn Zalo: \"{msg}\"\n")
                        if img:
                            self.sim_result_text.insert(tk.END, f"   - File ảnh đính kèm: {os.path.basename(img)}\n")
                        self.sim_result_text.insert(tk.END, f"\n2️⃣ KẾT QUẢ PHÂN LOẠI & XỬ LÝ (PIPELINE):\n")
                        self.sim_result_text.insert(tk.END, f"   - Phân loại nghiệp vụ: [{status.upper()}]\n")

                        conv = self.state.get_or_create_conversation(uid, name)
                        self.sim_result_text.insert(tk.END, f"   - CSDL Trạng thái: {conv.get('status')} | Số lần hỏi: {conv.get('unresolved_count')} | Can thiệp tay: {bool(conv.get('is_manual_override'))}\n")

                        if "drive" in status:
                            self.sim_result_text.insert(tk.END, f"   - Google Drive: Đã ghi nhận cấp quyền thành công & lưu vào danh sách bảo vệ 500 email/link.\n")
                        elif "feedback" in status or "correction" in status or self.state.get_all_corrections():
                            corrs = [c for c in self.state.get_all_corrections() if c['user_id'] == uid]
                            if corrs:
                                self.sim_result_text.insert(tk.END, f"   - Sổ tay giáo án: Đã tự động lưu góp ý mới vào Tab '📝 Sổ Tay Sửa Giáo Án'!\n")

                        self.sim_result_text.insert(tk.END, "\n3️⃣ NỘI DUNG AI TỰ ĐỘNG SOẠN THẢO VÀ GỬI CHO KHÁCH (ZALO):\n")
                        self.sim_result_text.insert(tk.END, "-"*65 + "\n")
                        for idx, r in enumerate(replies, 1):
                            self.sim_result_text.insert(tk.END, f"👉 [Tin {idx}/{len(replies)}]: {r}\n\n")
                    except Exception:
                        pass
                self.after(0, _ui_update)

                if self.sim_send_zalo_pc_var.get() and replies:
                    def _ui_pre_send():
                        try:
                            self.sim_result_text.insert(tk.END, f"🚀 [ZALO PC] Đang kết nối và gõ tin nhắn trực tiếp cho '{name}' trên Zalo PC (Tối đa 5 lần thử)...\n")
                        except Exception:
                            pass
                    self.after(0, _ui_pre_send)

                    ok = ZaloAutomation.send_messages_to_contact(name, replies, delay_between=self.handler.reply_delay, max_attempts=5)

                    def _ui_post_send():
                        try:
                            if ok:
                                self.sim_result_text.insert(tk.END, f"✅ [ZALO PC] Đã gửi thành công {len(replies)} tin nhắn vào Zalo của '{name}'!\n")
                            else:
                                self.sim_result_text.insert(tk.END, f"⚠️ [ZALO PC] Đã thử 5 lần không thành công -> DỪNG LẠI (Stop) để tránh lặp vô tận.\n")
                        except Exception:
                            pass
                    self.after(0, _ui_post_send)

                self.after(0, self.refresh_all_data)
            except Exception as ex:
                logger.error(f"[Simulation Error] {ex}")

        threading.Thread(target=_worker, daemon=True).start()

    def _send_direct_zalo_from_ui(self):
        nick = self.direct_nick_entry.get().strip()
        msg = self.direct_msg_entry.get().strip()
        if not nick or not msg:
            self.show_toast("Cảnh Báo", "Vui lòng nhập tên nick Zalo và nội dung tin nhắn!", "warning")
            return

        def _worker():
            try:
                self._append_chat_message("SYS", "Hệ Thống", f"Đang kết nối Zalo PC để gửi cho '{nick}' (Tối đa 5 lần thử)...")
                ok = ZaloAutomation.send_messages_to_contact(nick, [msg], max_attempts=5)
                if ok:
                    self._append_chat_message("AI", f"Gửi trực tiếp ({nick})", msg)
                    self.show_toast("Gửi Zalo Thành Công", f"Đã gửi tin nhắn trực tiếp đến '{nick}'!", "success")
                else:
                    self._append_chat_message("SYS", "Hệ Thống", f"⚠️ Thử 5 lần gửi cho '{nick}' thất bại. Đã DỪNG LẠI.")
                    self.show_toast("Dừng Lại (Sau 5 lần)", f"Không thể gửi tin nhắn đến '{nick}'. Hãy kiểm tra Zalo PC!", "error")
            except Exception as e:
                logger.error(f"[Direct Send Error] {e}")
                self.show_toast("Lỗi Gửi", f"Lỗi khi gửi trực tiếp: {e}", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _perform_local_search(self):
        grade = self.search_grade_cb.get()
        grade_val = None if grade == "Tất cả" else grade
        
        type_map = {
            "PPCT": "ppct",
            "Đề kiểm tra": "de_kiem_tra",
            "Phiếu học tập": "phieu_hoc_tap",
            "Bài giảng (PPT)": "bai_giang"
        }
        mat_type = type_map.get(self.search_type_cb.get())
        query = self.search_entry.get().strip()

        for row in self.search_tree.get_children():
            self.search_tree.delete(row)

        results = self.searcher.search(query=query, grade=grade_val, material_type=mat_type)
        if not results:
            self.search_tree.insert("", "end", values=("Không tìm thấy file phù hợp (Hãy kiểm tra thư mục C:/GiaoAnLichSu)", "-", "-"))
            return

        for r in results:
            self.search_tree.insert("", "end", values=(r['filename'], f"{r['size_mb']} MB", r['filepath']))

    def _open_selected_folder(self):
        sel = self.search_tree.selection()
        if not sel:
            return
        item = self.search_tree.item(sel[0])
        filepath = item['values'][2]
        if os.path.exists(filepath):
            folder = os.path.dirname(filepath).replace("/", "\\")
            subprocess.Popen(f'explorer "{folder}"')

    def _copy_selected_file_path(self):
        sel = self.search_tree.selection()
        if not sel:
            return
        item = self.search_tree.item(sel[0])
        filepath = item['values'][2]
        self.clipboard_clear()
        self.clipboard_append(filepath)
        self.show_toast("Đã Copy", f"Đã copy đường dẫn: {filepath}", "info")

    def _copy_selected_email(self):
        sel = self.drive_tree.selection()
        if not sel:
            return
        item = self.drive_tree.item(sel[0])
        email = item['values'][1]
        self.clipboard_clear()
        self.clipboard_append(email)
        self.show_toast("Đã Copy", f"Đã copy email: {email}", "info")

    def _copy_all_filtered_emails(self):
        emails = []
        for row in self.drive_tree.get_children():
            item = self.drive_tree.item(row)
            em = item['values'][1]
            if em:
                emails.append(em)
        if not emails:
            self.show_toast("Thông Báo", "Không có email nào trong danh sách!", "warning")
            return
        all_text = ", ".join(list(set(emails)))
        self.clipboard_clear()
        self.clipboard_append(all_text)
        self.show_toast("Đã Copy Hàng Loạt", f"Đã copy {len(set(emails))} email để dán chia sẻ Drive!", "success")

    def _export_emails(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV file (*.csv)", "*.csv"), ("Text file (*.txt)", "*.txt")]
        )
        if not path:
            return
        grade_filter = self.drive_filter_grade.get()
        grade_val = None if grade_filter == "Tất cả" else grade_filter
        count = self.state.export_emails_to_file(path, grade_or_level=grade_val)
        self.show_toast("Thành Công", f"Đã xuất thành công {count} email ra file!", "success")

    def _refresh_drive_logs(self):
        for row in self.drive_tree.get_children():
            self.drive_tree.delete(row)
        grade_filter = self.drive_filter_grade.get()
        grade_val = None if grade_filter == "Tất cả" else grade_filter
        logs = self.state.get_all_drive_logs(grade_filter=grade_val)
        for l in logs:
            self.drive_tree.insert("", "end", values=(
                l['id'],
                l['email'],
                f"Lớp {l['grade_or_level']}",
                l['link_type'],
                l['drive_link'],
                l['created_at']
            ))

    def _toggle_bot_running_state(self):
        """Bật/tắt trạng thái Bot AI (Chạy <-> Tạm Dừng) chỉ bằng 1 nút duy nhất."""
        if getattr(self.handler, 'is_paused', False):
            self._ui_resume_bot()
        else:
            self._ui_pause_bot()

    def _ui_pause_bot(self):
        self.handler.pause_bot()
        is_w = getattr(self, "_is_wide_mode", False)
        self.status_lbl.config(text="● ĐÃ TẠM DỪNG (F8)" if is_w else "● TẠM DỪNG (F8)", fg="#f87171")
        if hasattr(self, "btn_toggle_bot"):
            self.btn_toggle_bot.configure(text="▶ Tiếp Tục Bot (F8)" if is_w else "▶ Bật Bot", bg="#059669")
        if hasattr(self, "footer_status_lbl"):
            self.footer_status_lbl.configure(text="⏸ Đang tạm dừng (F8)", fg="#f87171")
        self.set_footer_task("Bot AI đã tạm dừng nhận diện tự động.")
        self.show_toast("Tạm Dừng Bot", "Bot AI đã tạm dừng nhận diện tự động (F8).", "warning")

    def _ui_resume_bot(self):
        self.handler.resume_bot()
        is_w = getattr(self, "_is_wide_mode", False)
        self.status_lbl.config(text="● BOT ĐANG CHẠY (F8)" if is_w else "● BOT CHẠY (F8)", fg="#34d399")
        if hasattr(self, "btn_toggle_bot"):
            self.btn_toggle_bot.configure(text="⏸ Tạm Dừng Bot (F8)" if is_w else "⏸ Dừng Bot", bg="#e11d48")
        if hasattr(self, "footer_status_lbl"):
            self.footer_status_lbl.configure(text="🟢 Đang hoạt động (F8)", fg="#34d399")
        self.set_footer_task("Lắng nghe tin nhắn & sẵn sàng tiếp nhận Zalo PC...")
        self.show_toast("Tiếp Tục Bot", "Bot AI đang hoạt động bình thường (F8).", "success")

    def _toggle_bot_running_state_from_hotkey(self):
        self.after(0, self._toggle_bot_running_state)

    def _mark_selected_done(self):
        if not hasattr(self, 'conv_tree') or not self.conv_tree.winfo_exists():
            return
        sel = self.conv_tree.selection()
        if not sel:
            return
        user_id = sel[0]
        self.state.update_conversation_status(user_id, "RESOLVED")
        self.refresh_all_data()
        self.show_toast("Đã Xong", "Đã đánh dấu phiên chat hoàn tất (RESOLVED).", "success")

    def _toggle_selected_manual(self):
        if not hasattr(self, 'conv_tree') or not self.conv_tree.winfo_exists():
            return
        sel = self.conv_tree.selection()
        if not sel:
            return
        user_id = sel[0]
        self.state.set_manual_override(user_id, True)
        self.refresh_all_data()
        self.show_toast("Can Thiệp Tay", "Đã bật chế độ nhường quyền chat thủ công!", "warning")

    def _mark_correction_fixed(self):
        if not hasattr(self, 'corr_tree') or not self.corr_tree.winfo_exists():
            return
        sel = self.corr_tree.selection()
        if not sel:
            self.show_toast("Thông Báo", "Vui lòng chọn 1 dòng giáo án trong danh sách!", "warning")
            return
        item = self.corr_tree.item(sel[0])
        corr_id = item['values'][0]
        self.state.update_correction_status(corr_id, "COMPLETED", "Đã cập nhật bài giảng mới")
        self._refresh_corrections()
        self.show_toast("Thành Công", "Đã đánh dấu đã sửa xong giáo án này!", "success")

    def _refresh_corrections(self):
        if not hasattr(self, 'corr_tree') or not self.corr_tree.winfo_exists():
            return
        for row in self.corr_tree.get_children():
            self.corr_tree.delete(row)
        for corr in self.state.get_all_corrections():
            status_display = "✅ ĐÃ SỬA" if corr['status'] == "COMPLETED" else "⏳ CHỜ SỬA"
            self.corr_tree.insert("", "end", values=(
                corr['id'],
                corr['customer_name'],
                f"Lớp {corr['grade']}",
                corr['feedback_text'],
                status_display,
                corr['created_at']
            ))

    def refresh_all_data(self):
        """Làm mới toàn bộ dữ liệu trên các Tab."""
        if hasattr(self, 'chat_sessions_tree') and self.chat_sessions_tree.winfo_exists():
            self._refresh_chat_sessions_list(keep_current=True)
        if hasattr(self, 'conv_tree') and self.conv_tree.winfo_exists():
            for row in self.conv_tree.get_children():
                self.conv_tree.delete(row)
            for c in self.state.get_all_conversations():
                status_text = c['status']
                if c['is_manual_override'] == 1:
                    status_text = "✋ Can thiệp tay"
                self.conv_tree.insert("", "end", iid=c['user_id'], values=(
                    c['display_name'],
                    status_text,
                    c['unresolved_count'],
                    c['last_message_text'] or ""
                ))
        self._refresh_corrections()
        self._refresh_drive_logs()
        self._refresh_api_keys_table()
        if hasattr(self, '_refresh_customers_list'):
            self._refresh_customers_list()
        if hasattr(self, '_refresh_script_templates_list'):
            self._refresh_script_templates_list()
        if hasattr(self, '_refresh_template_combobox'):
            self._refresh_template_combobox()
        if hasattr(self, '_refresh_tags_combobox'):
            self._refresh_tags_combobox()
        if hasattr(self, '_refresh_schedules_ui'):
            self._refresh_schedules_ui()
        if hasattr(self, '_refresh_broadcast_logs_table'):
            self._refresh_broadcast_logs_table()
        if hasattr(self, '_refresh_file_bundles_tree'):
            self._refresh_file_bundles_tree()
        if hasattr(self, '_refresh_users_tree'):
            self._refresh_users_tree()

    def _on_msg_received(self, user_id: str, display_name: str, text: str, img_path: Optional[str]):
        img_name = os.path.basename(img_path) if img_path else None
        self._append_chat_message("USER", display_name, text, img_name)
        if hasattr(self, 'chat_sessions_tree') and self.chat_sessions_tree.winfo_exists():
            self._refresh_chat_sessions_list(keep_current=True)

    def _on_reply_sent(self, user_id: str, display_name: str, text: str):
        self._append_chat_message("AI", f"Gửi {display_name}", text)
        if hasattr(self, 'chat_sessions_tree') and self.chat_sessions_tree.winfo_exists():
            self._refresh_chat_sessions_list(keep_current=True)

    def _send_direct_zalo_from_ui(self):
        """Gửi trực tiếp tin nhắn vào Zalo PC theo tên Nick đã nhập."""
        nick = self.direct_nick_entry.get().strip()
        msg = self.direct_msg_entry.get().strip()
        if not nick or not msg:
            self.show_toast("Cảnh Báo", "Vui lòng nhập tên Nick và Tin nhắn!", "warning")
            return

        def _worker():
            self._append_chat_message("SYS", "Hệ Thống", f"Đang gửi tin nhắn cho '{nick}' trên Zalo PC...")
            ok = ZaloAutomation.send_messages_to_contact(nick, [msg], max_attempts=5)
            if ok:
                self._append_chat_message("AI", f"Gửi Zalo ({nick})", msg)
                self.show_toast("Gửi Thành Công", f"Đã bắn tin nhắn vào Zalo của '{nick}'!", "success")
            else:
                self._append_chat_message("SYS", "Hệ Thống", f"⚠️ Thử 5 lần gửi cho '{nick}' thất bại. Đã dừng lại.")
                self.show_toast("Thất Bại", f"Không gửi được cho '{nick}' sau 5 lần thử.", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _auto_pilot_read_and_reply(self):
        """Kích hoạt Zalo PC, chụp ảnh tin nhắn khách, Gemini đọc và tự động gửi câu trả lời."""
        self._append_chat_message("SYS", "Hệ Thống", "🤖 [Auto-Pilot] Đang đọc màn hình Zalo PC & phân tích tin nhắn khách...")
        self.show_toast("Auto-Pilot", "Đang đọc tin nhắn Zalo & sinh câu trả lời AI...", "info")

        def _worker():
            ok, msg, replies = ZaloAutomation.auto_read_and_reply_current_chat(
                self.gemini,
                delay_between=self.handler.reply_delay,
                max_attempts=5
            )
            if ok:
                for r in replies:
                    self._append_chat_message("AI", "Auto-Pilot Zalo PC", r)
                self.show_toast("Thành Công", f"Đã đọc tin nhắn và gửi {len(replies)} tin phản hồi vào Zalo PC!", "success")
            else:
                self._append_chat_message("SYS", "Hệ Thống", f"⚠️ Auto-Pilot dừng: {msg}")
                self.show_toast("Thông Báo", f"Auto-Pilot: {msg}", "warning")

        threading.Thread(target=_worker, daemon=True).start()

    def _filter_unread_zalo(self):
        """Bấm nút Phân loại và chọn lọc Chưa Đọc trên Zalo PC."""
        self.show_toast("Đang Lọc", "Đang mở menu và chọn lọc tin nhắn Chưa Đọc...", "info")
        def _worker():
            ok = ZaloAutomation.filter_by_status("unread", max_attempts=3)
            if ok:
                self.show_toast("Thành Công", "Đã bật chế độ lọc tin nhắn Chưa Đọc trên Zalo PC!", "success")
            else:
                self.show_toast("Thất Bại", "Không thể chọn mục Chưa Đọc trên Zalo PC.", "error")
        threading.Thread(target=_worker, daemon=True).start()

    def _filter_need_resolution_zalo(self):
        """Bấm nút Phân loại và chọn lọc Thẻ 'Cần Giải Quyết' trên Zalo PC."""
        self.show_toast("Đang Lọc", "Đang lọc các cuộc hội thoại Thẻ 'Cần Giải Quyết'...", "info")
        def _worker():
            ok = ZaloAutomation.filter_by_tag_name("cần giải quyết", max_attempts=3)
            if ok:
                self.show_toast("Thành Công", "Đã lọc danh sách Thẻ 'Cần Giải Quyết' trên Zalo PC!", "success")
            else:
                self.show_toast("Thất Bại", "Không thể lọc Thẻ trên Zalo PC.", "error")
        threading.Thread(target=_worker, daemon=True).start()

    def _assign_need_resolution_zalo(self):
        """Click phải vào hội thoại và gán Thẻ 'Cần Giải Quyết'."""
        self.show_toast("Gắn Thẻ", "Đang gán Thẻ 'Cần Giải Quyết' cho hội thoại Zalo...", "info")
        def _worker():
            ok = ZaloAutomation.assign_tag_to_current_chat("cần giải quyết", max_attempts=3)
            if ok:
                self.show_toast("Thành Công", "Đã gán Thẻ 'Cần Giải Quyết' cho hội thoại thành công!", "success")
            else:
                self.show_toast("Thất Bại", "Không thể gán thẻ tự động.", "warning")
        threading.Thread(target=_worker, daemon=True).start()

    def _batch_scan_unread_zalo(self):
        """Tự động duyệt tất cả tin nhắn chưa đọc và trả lời hàng loạt."""
        self._append_chat_message("SYS", "Hệ Thống", "🚀 [Batch Auto] Bắt đầu tự động quét & trả lời tất cả tin nhắn CHƯA ĐỌC...")
        self.show_toast("Bắt Đầu Quét", "Đang lọc tin chưa đọc & tự động gửi phản hồi hàng loạt...", "info")
        def _worker():
            results = ZaloAutomation.auto_scan_and_reply_unread(self.gemini, max_chats=5, delay_between=self.handler.reply_delay, max_attempts=3)
            success_count = sum(1 for r in results if r["success"])
            self._append_chat_message("SYS", "Hệ Thống", f"🎉 [Batch Auto] Hoàn tất! Đã trả lời tự động cho {success_count}/{len(results)} khách hàng chưa đọc.")
            self.show_toast("Hoàn Tất Quét", f"Đã quét & trả lời xong {success_count} khách hàng chưa đọc!", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def _deep_context_read_and_reply(self):
        """Cuộn chuột lên để chụp & phân tích sâu 20 tin nhắn gần nhất và tự động phản hồi."""
        self._append_chat_message("SYS", "Hệ Thống", "📜 [Deep Context] Đang cuộn chuột lên & phân tích sâu 20 tin nhắn gần nhất...")
        self.show_toast("Deep Context", "Đang cuộn lên & phân tích toàn bộ mạch đối thoại 20 tin nhắn...", "info")
        def _worker():
            ok, msg, replies = ZaloAutomation.read_deep_context_and_reply(
                self.gemini,
                scroll_up=True,
                delay_between=self.handler.reply_delay,
                max_attempts=5
            )
            if ok:
                for r in replies:
                    self._append_chat_message("AI", "Deep Context Zalo PC", r)
                self.show_toast("Thành Công", f"Đã hiểu ngữ cảnh sâu và gửi thành công {len(replies)} tin phản hồi!", "success")
            else:
                self._append_chat_message("SYS", "Hệ Thống", f"⚠️ Deep Context dừng: {msg}")
                self.show_toast("Thông Báo", f"Deep Context: {msg}", "warning")
        threading.Thread(target=_worker, daemon=True).start()

    # ================= TAB: GỬI TIN NHÓM & LÊN LỊCH TỰ ĐỘNG (BROADCAST & SCHEDULER) =================
    def _build_broadcast_tab(self, parent):
        paned = tk.PanedWindow(parent, orient="horizontal", bg="#1e293b", sashwidth=4)
        paned.pack(fill="both", expand=True)

        # CỘT TRÁI: QUẢN LÝ NHIỀU MẪU TIN NHẮN (ĐỘNG) & ĐÍNH KÈM FILE
        left_frame = tk.Frame(paned, bg="#0f172a", padx=8, pady=6)
        paned.add(left_frame, minsize=400, width=480)

        # Thanh chọn mẫu tin nhắn (Combobox linh hoạt hỗ trợ vô số mẫu)
        tpl_bar = tk.Frame(left_frame, bg="#1e293b", padx=6, pady=6)
        tpl_bar.pack(fill="x", pady=(0, 6))

        tk.Label(tpl_bar, text="📝 MẪU TIN:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")

        self.tpl_select_cb = ttk.Combobox(tpl_bar, state="readonly", width=14)
        self.tpl_select_cb.pack(side="left", padx=4)
        self.tpl_select_cb.bind("<<ComboboxSelected>>", lambda e: self._on_template_cb_selected())

        btn_add_tpl = tk.Button(tpl_bar, text="➕ Tạo Mẫu", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._create_new_template_dialog)
        btn_add_tpl.pack(side="left", padx=2)

        btn_del_tpl = tk.Button(tpl_bar, text="🗑️ Xóa", bg="#475569", fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=4, pady=2, cursor="hand2", command=self._delete_current_template)
        btn_del_tpl.pack(side="left", padx=2)

        self.lbl_default_badge = tk.Label(tpl_bar, text="⭐ MẶC ĐỊNH", font=("Segoe UI", 8, "bold"), fg="#fbbf24", bg="#1e293b")
        self.lbl_default_badge.pack(side="right", padx=4)

        # Tiêu đề mẫu
        tk.Label(left_frame, text="Tiêu đề mẫu tin:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        self.tpl_title_entry = tk.Entry(left_frame, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.tpl_title_entry.pack(fill="x", pady=(0, 4))

        # Nội dung tin nhắn
        tk.Label(left_frame, text="Nội dung tin nhắn (gửi vào từng nhóm Zalo):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        self.tpl_content_txt = tk.Text(left_frame, font=("Segoe UI", 9), height=7, bg="#1e293b", fg="#f8fafc", insertbackground="white", wrap="word")
        self.tpl_content_txt.pack(fill="x", pady=(0, 4))

        # Danh sách file đính kèm: Nút Thêm File / Thêm Thư Mục nằm ĐẦU TIÊN BÊN TRÁI, chữ Label nằm BÊN PHẢI
        file_header = tk.Frame(left_frame, bg="#0f172a")
        file_header.pack(fill="x", pady=(4, 1))

        btn_add_files = tk.Button(file_header, text="➕ Thêm File", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._add_files_to_template)
        btn_add_files.pack(side="left", padx=(0, 4))

        btn_add_dir = tk.Button(file_header, text="📂 Thêm Thư Mục", bg="#0d9488", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._add_folder_to_template)
        btn_add_dir.pack(side="left", padx=(0, 6))

        tk.Label(file_header, text="📁 File / Thư mục đính kèm gửi cùng tin:", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a").pack(side="left")

        # Dòng nhãn thống kê & đếm số lượng từng loại file (Word, PPT, PDF, Video, Image...)
        self.lbl_file_count_summary = tk.Label(
            left_frame,
            text="📊 Đính kèm: 0 file (Chưa chọn file)",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            anchor="w"
        )
        self.lbl_file_count_summary.pack(fill="x", pady=(1, 2))

        # Danh sách file hiện ra chiều cao khoảng 4 file
        self.tpl_files_listbox = tk.Listbox(left_frame, font=("Segoe UI", 8), height=4, bg="#1e293b", fg="#f8fafc", selectbackground="#0284c7")
        self.tpl_files_listbox.pack(fill="x", pady=(0, 3))

        file_act_bar = tk.Frame(left_frame, bg="#0f172a")
        file_act_bar.pack(fill="x", pady=(0, 3))

        btn_del_file = tk.Button(file_act_bar, text="🗑️ Xóa File Chọn", bg="#475569", fg="white", font=("Segoe UI", 7), relief="flat", padx=5, pady=1, cursor="hand2", command=self._remove_selected_file_from_template)
        btn_del_file.pack(side="left", padx=2)

        btn_clear_files = tk.Button(file_act_bar, text="🧹 Xóa Hết File", bg="#334155", fg="#94a3b8", font=("Segoe UI", 7), relief="flat", padx=5, pady=1, cursor="hand2", command=self._clear_all_template_files)
        btn_clear_files.pack(side="left", padx=2)

        # Lưu mẫu & Đặt mặc định
        bot_act_bar = tk.Frame(left_frame, bg="#1e293b", padx=6, pady=3)
        bot_act_bar.pack(fill="x", pady=(1, 0))

        btn_save_tpl = tk.Button(bot_act_bar, text="💾 Lưu Mẫu", bg="#22c55e", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._save_current_template_from_ui)
        btn_save_tpl.pack(side="left", padx=2)

        btn_set_def = tk.Button(bot_act_bar, text="⭐ Mặc Định", bg="#f59e0b", fg="black", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._set_current_template_as_default)
        btn_set_def.pack(side="left", padx=2)

        # GỬI TRỰC TIẾP MẪU TIN VÀO KHUNG CHAT ĐANG MỞ (ZALO / GỬI FREE BẤT KỲ APP NÀO)
        direct_card = tk.Frame(left_frame, bg="#1e293b", padx=6, pady=4)
        direct_card.pack(fill="x", pady=(3, 0))

        self.bc_direct_target_mode = "target_locked"
        self.btn_bc_target_mode = tk.Button(
            direct_card,
            text="🔒 Khóa Nền Zalo",
            font=("Segoe UI", 7, "bold"),
            bg="#8b5cf6",
            fg="white",
            relief="flat",
            padx=5,
            pady=2,
            cursor="hand2",
            command=self._toggle_bc_target_mode
        )
        self.btn_bc_target_mode.pack(side="left", padx=(0, 4))

        btn_send_bc_direct = tk.Button(
            direct_card,
            text="🚀 Gửi Vào Khung Chat (Enter)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._send_broadcast_template_to_chat(auto_enter=True)
        )
        btn_send_bc_direct.pack(side="left", padx=2)

        btn_draft_bc_direct = tk.Button(
            direct_card,
            text="📝 Chèn Nháp (Draft)",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._send_broadcast_template_to_chat(auto_enter=False)
        )
        btn_draft_bc_direct.pack(side="left", padx=2)

        btn_reset_bc = tk.Button(
            direct_card,
            text="🔄 Reset Lỗi",
            bg="#334155",
            fg="#38bdf8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.reset_all_retry_and_error_states
        )
        btn_reset_bc.pack(side="right", padx=2)

        # =========================================================================
        # KHUNG 3: NHẬT KÝ GỬI TIN NHÓM (CHỐNG GỬI LẶP) - ĐẶT Ở CỘT TRÁI ĐỂ CÂN BẰNG GIAO DIỆN
        # =========================================================================
        log_card = tk.LabelFrame(left_frame, text=" 📊 NHẬT KÝ GỬI NHÓM ĐÃ HOÀN THÀNH (ĐÃ ĐÁNH DẤU CHỐNG LẶP) ", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a", padx=6, pady=4)
        log_card.pack(fill="both", expand=True, pady=(4, 0))

        cols = ("group", "tag", "tpl", "files", "status", "time")
        self.bc_tree = ttk.Treeview(log_card, columns=cols, show="headings", height=5)
        self.bc_tree.heading("group", text="Tên Nhóm / Người Nhận")
        self.bc_tree.heading("tag", text="Phân Loại")
        self.bc_tree.heading("tpl", text="Mẫu")
        self.bc_tree.heading("files", text="File")
        self.bc_tree.heading("status", text="Trạng Thái")
        self.bc_tree.heading("time", text="Thời Gian Gửi")

        self.bc_tree.column("group", width=120)
        self.bc_tree.column("tag", width=95)
        self.bc_tree.column("tpl", width=45, anchor="center")
        self.bc_tree.column("files", width=60, anchor="center")
        self.bc_tree.column("status", width=70, anchor="center")
        self.bc_tree.column("time", width=105, anchor="center")
        self.bc_tree.pack(fill="both", expand=True)

        log_act = tk.Frame(log_card, bg="#0f172a")
        log_act.pack(fill="x", pady=(2, 0))

        btn_ref_bc = tk.Button(log_act, text="🔄 Làm Mới", bg="#334155", fg="#f8fafc", font=("Segoe UI", 7), relief="flat", padx=5, pady=1, cursor="hand2", command=self._refresh_broadcast_logs_table)
        btn_ref_bc.pack(side="left", padx=2)

        btn_del_sel_bc = tk.Button(log_act, text="🗑️ Xóa Dòng", bg="#475569", fg="#fca5a5", font=("Segoe UI", 7), relief="flat", padx=5, pady=1, cursor="hand2", command=self._delete_selected_broadcast_log)
        btn_del_sel_bc.pack(side="left", padx=2)

        btn_clr_bc = tk.Button(log_act, text="🧹 Xóa Toàn Bộ", bg="#ef4444", fg="white", font=("Segoe UI", 7, "bold"), relief="flat", padx=6, pady=1, cursor="hand2", command=self._clear_broadcast_batch_history)
        btn_clr_bc.pack(side="right", padx=2)


        # CỘT PHẢI: KHÓA CHẶT ỨNG DỤNG ĐÍCH + GỬI NGAY + CHỐNG SPAM + LÊN LỊCH + AUDIT CHECK
        right_frame = tk.Frame(paned, bg="#0f172a", padx=8, pady=6)
        paned.add(right_frame, minsize=480)

        # =========================================================================
        # CARD 0: 🔒 KHÓA CHẶT ỨNG DỤNG ĐÍCH (CÁCH LY 100% GỬI NGẦM THEO HÌNH 3)
        # =========================================================================
        lock_card = tk.LabelFrame(
            right_frame,
            text=" 🔒 KHÓA CHẶT ỨNG DỤNG ĐÍCH (CÁCH LY 100% GỬI NGẦM) ",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#0f172a",
            padx=8,
            pady=4
        )
        lock_card.pack(fill="x", pady=(0, 6))

        # Dòng 1: Switch Bật Khóa Chạy Nền
        row_lock_sw = tk.Frame(lock_card, bg="#0f172a")
        row_lock_sw.pack(fill="x", pady=(0, 3))

        self.target_window_enabled_var = tk.BooleanVar(value=True)  # MẶC ĐỊNH BẬT KHÓA NỀN
        chk_lock = tk.Checkbutton(
            row_lock_sw,
            text="🟢 Bật Khóa Chạy Nền (Không nhảy phím/chuột sang app khác)",
            variable=self.target_window_enabled_var,
            bg="#0f172a", fg="#34d399", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8, "bold"),
            command=self._on_target_switch_toggle
        )
        chk_lock.pack(side="left")

        # Dòng 2: Nút 1-Click Chọn Cửa Sổ & Thử Gõ Phím
        row_lock_btns = tk.Frame(lock_card, bg="#1e293b", padx=4, pady=3)
        row_lock_btns.pack(fill="x", pady=(0, 3))

        self.btn_pick_target = tk.Button(
            row_lock_btns,
            text="🎯 CLICK VÀO CỬA SỔ CẦN GẮN (1-CLICK)",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._start_target_window_picker
        )
        self.btn_pick_target.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_test_key = tk.Button(
            row_lock_btns,
            text="🪄 Thử Gõ 1 Phím",
            font=("Segoe UI", 8, "bold"),
            bg="#8b5cf6",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._test_target_key_press
        )
        self.btn_test_key.pack(side="right")

        # Dòng 3: Chọn cửa sổ từ combobox + Nút quét lại
        row_lock_cb = tk.Frame(lock_card, bg="#0f172a")
        row_lock_cb.pack(fill="x", pady=(0, 2))

        tk.Label(row_lock_cb, text="Hoặc chọn cửa sổ trong danh sách:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(side="left")

        btn_scan_wins = tk.Button(
            row_lock_cb,
            text="🔄 Quét lại",
            font=("Segoe UI", 7, "bold"),
            bg="#475569",
            fg="#f8fafc",
            relief="flat",
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._refresh_target_windows_list
        )
        btn_scan_wins.pack(side="right")

        self.target_window_cb = ttk.Combobox(
            lock_card,
            values=["(Đang quét danh sách cửa sổ...)"],
            font=("Segoe UI", 8),
            state="readonly"
        )
        self.target_window_cb.pack(fill="x", pady=(0, 2))
        self.target_window_cb.bind("<<ComboboxSelected>>", self._on_target_window_combo_selected)

        # Dòng 4: Status label
        self.target_lock_status_lbl = tk.Label(
            lock_card,
            text="Trạng thái: 🔒 ĐÃ KHÓA NỀN [Zalo.exe] Zalo - 100% gửi ngầm độc lập",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#0f172a",
            anchor="w"
        )
        self.target_lock_status_lbl.pack(fill="x", pady=(1, 1))

        # =========================================================================
        # KHUNG 1: GỬI NGAY ĐẾN DANH SÁCH NHÓM / NGƯỜI NHẬN
        # =========================================================================
        send_card = tk.LabelFrame(right_frame, text=" 🎯 GỬI NGAY ĐẾN DANH SÁCH NHÓM / NGƯỜI DÙNG (CHỐNG LẶP & RANDOM SPAM) ", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#0f172a", padx=8, pady=4)
        send_card.pack(fill="x", pady=(0, 6))

        # Hàng 0: Chọn Chế độ Người nhận (Mặc định: Danh sách Tên tự nhập)
        row_target_mode = tk.Frame(send_card, bg="#1e293b", padx=6, pady=3)
        row_target_mode.pack(fill="x", pady=(0, 4))

        tk.Label(row_target_mode, text="🎯 CHẾ ĐỘ:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")

        self.target_mode_var = tk.StringVar(value="custom_list")  # MẶC ĐỊNH LÀ DANH SÁCH TỰ NHẬP
        rb_tgt_list = tk.Radiobutton(row_target_mode, text="📝 Nhập Danh Sách Tên (Chuẩn 100%)", variable=self.target_mode_var, value="custom_list", bg="#1e293b", fg="#34d399", selectcolor="#0f172a", font=("Segoe UI", 8, "bold"), command=self._on_target_mode_changed)
        rb_tgt_list.pack(side="left", padx=4)

        rb_tgt_tag = tk.Radiobutton(row_target_mode, text="🏷️ Theo Thẻ Zalo", variable=self.target_mode_var, value="tag", bg="#1e293b", fg="#94a3b8", selectcolor="#0f172a", font=("Segoe UI", 8), command=self._on_target_mode_changed)
        rb_tgt_tag.pack(side="left", padx=4)

        self.anti_dup_var = tk.BooleanVar(value=True)
        chk_dup = tk.Checkbutton(row_target_mode, text="Chống lặp", variable=self.anti_dup_var, bg="#1e293b", fg="#34d399", selectcolor="#0f172a", activebackground="#1e293b", font=("Segoe UI", 8, "bold"))
        chk_dup.pack(side="right", padx=2)

        # KHUNG CON A: NHẬP DANH SÁCH TÊN TỰ DO (HIỂN THỊ MẶC ĐỊNH)
        self.frame_custom_targets = tk.Frame(send_card, bg="#0f172a")
        self.frame_custom_targets.pack(fill="x", pady=1)

        # Dòng 1: Tiêu đề danh sách & nút xóa trắng
        hdr_targets = tk.Frame(self.frame_custom_targets, bg="#0f172a")
        hdr_targets.pack(fill="x", pady=(0, 2))

        self.lbl_target_count = tk.Label(hdr_targets, text="📋 Danh sách Nhóm / Người:  [0 mục]", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a")
        self.lbl_target_count.pack(side="left")

        btn_clr_tgt = tk.Button(hdr_targets, text="🧹 Xóa Trắng", bg="#334155", fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=6, pady=1, cursor="hand2", command=self._clear_targets_txt)
        btn_clr_tgt.pack(side="right", padx=2)

        # Dòng 2: Thanh công cụ thao tác danh sách (Lấy Tên Từ Thẻ Zalo, Nạp File, Dán Nhanh, Xuất File)
        bar_tgt_tools = tk.Frame(self.frame_custom_targets, bg="#1e293b", padx=4, pady=2)
        bar_tgt_tools.pack(fill="x", pady=(0, 3))

        btn_scan_tag_targets = tk.Button(
            bar_tgt_tools,
            text="📥 LẤY TỪ THẺ ZALO",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._extract_targets_from_zalo_tag_dialog
        )
        btn_scan_tag_targets.pack(side="left", padx=(0, 3))

        btn_load_tgt = tk.Button(
            bar_tgt_tools,
            text="📂 Nạp File",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._import_targets_from_file
        )
        btn_load_tgt.pack(side="left", padx=3)

        btn_paste_tgt = tk.Button(
            bar_tgt_tools,
            text="📋 Dán Nhanh",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._paste_targets_from_clipboard
        )
        btn_paste_tgt.pack(side="left", padx=3)

        # Ô Text nhập danh sách nhóm/người
        txt_scroll_frame = tk.Frame(self.frame_custom_targets, bg="#0f172a")
        txt_scroll_frame.pack(fill="x", pady=(0, 3))

        self.target_names_txt = tk.Text(txt_scroll_frame, font=("Segoe UI", 9), height=3, bg="#1e293b", fg="#f8fafc", insertbackground="white", wrap="none")
        self.target_names_txt.pack(side="left", fill="x", expand=True)

        tgt_sb = tk.Scrollbar(txt_scroll_frame, orient="vertical", command=self.target_names_txt.yview)
        tgt_sb.pack(side="right", fill="y")
        self.target_names_txt.configure(yscrollcommand=tgt_sb.set)

        self.target_names_txt.bind("<KeyRelease>", lambda e: self._update_target_count_badge())
        self.target_names_txt.bind("<FocusOut>", lambda e: self._on_target_text_focus_out())

        # KHUNG CON B: THEO THẺ PHÂN LOẠI (ẨN KHI Ở CHẾ ĐỘ MẶC ĐỊNH)
        self.frame_tag_targets = tk.Frame(send_card, bg="#0f172a")

        tk.Label(self.frame_tag_targets, text="Thẻ Zalo:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a").pack(side="left")
        self.bc_tag_cb = ttk.Combobox(self.frame_tag_targets, state="readonly", width=14)
        self.bc_tag_cb.pack(side="left", padx=3)

        btn_add_tag = tk.Button(self.frame_tag_targets, text="➕ Thêm", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._add_custom_tag_dialog)
        btn_add_tag.pack(side="left", padx=1)

        btn_edit_tag = tk.Button(self.frame_tag_targets, text="✏️ Sửa", bg="#f59e0b", fg="black", font=("Segoe UI", 8, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._edit_custom_tag_dialog)
        btn_edit_tag.pack(side="left", padx=1)

        btn_del_tag = tk.Button(self.frame_tag_targets, text="🗑️ Xóa", bg="#ef4444", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._delete_custom_tag)
        btn_del_tag.pack(side="left", padx=1)

        btn_extract_from_tag_tab = tk.Button(self.frame_tag_targets, text="📥 Lấy Tên", bg="#8b5cf6", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=1, cursor="hand2", command=self._extract_targets_from_zalo_tag_dialog)
        btn_extract_from_tag_tab.pack(side="left", padx=3)

        tk.Label(self.frame_tag_targets, text="Số nhóm:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(side="left", padx=(4, 2))
        self.bc_count_var = tk.IntVar(value=5)
        self.bc_count_sp = tk.Spinbox(self.frame_tag_targets, from_=1, to=200, textvariable=self.bc_count_var, width=4, font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#34d399", buttonbackground="#334155")
        self.bc_count_sp.pack(side="left", padx=1)

        # Hàng 2: Tùy chọn Mẫu gửi (Mẫu đang chọn, Mẫu mặc định, hoặc 🎲 Random ngẫu nhiên)
        self.row_mode_frame = tk.Frame(send_card, bg="#1e293b", padx=4, pady=3)
        self.row_mode_frame.pack(fill="x", pady=(3, 3))

        tk.Label(self.row_mode_frame, text="Mẫu gửi:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")

        self.send_mode_var = tk.StringVar(value="selected")
        rb_sel = tk.Radiobutton(self.row_mode_frame, text="Đang chọn", variable=self.send_mode_var, value="selected", bg="#1e293b", fg="#f8fafc", selectcolor="#0f172a", font=("Segoe UI", 8))
        rb_sel.pack(side="left", padx=4)

        rb_def = tk.Radiobutton(self.row_mode_frame, text="⭐ Mặc Định", variable=self.send_mode_var, value="default", bg="#1e293b", fg="#fbbf24", selectcolor="#0f172a", font=("Segoe UI", 8, "bold"))
        rb_def.pack(side="left", padx=4)

        rb_rnd = tk.Radiobutton(self.row_mode_frame, text="🎲 Random Mẫu", variable=self.send_mode_var, value="random", bg="#1e293b", fg="#a855f7", selectcolor="#0f172a", font=("Segoe UI", 8, "bold"))
        rb_rnd.pack(side="left", padx=4)

        # Hàng 3: Tùy chọn Chống Spam Zalo (Thời gian giờ phút [HH:MM] mặc định BẬT, Mã số, Icon)
        self.row_anti = tk.Frame(send_card, bg="#0f172a")
        self.row_anti.pack(fill="x", pady=(2, 2))

        tk.Label(self.row_anti, text="Chống Spam:", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#0f172a").pack(side="left")

        self.anti_time_var = tk.BooleanVar(value=True)  # Mặc định kích hoạt thời gian
        chk_time = tk.Checkbutton(self.row_anti, text="⏱ Chèn Giờ [HH:MM] (Mặc định)", variable=self.anti_time_var, bg="#0f172a", fg="#34d399", selectcolor="#1e293b", font=("Segoe UI", 8, "bold"))
        chk_time.pack(side="left", padx=4)

        self.anti_code_var = tk.BooleanVar(value=False)
        chk_code = tk.Checkbutton(self.row_anti, text="🔢 Mã [#xxxx]", variable=self.anti_code_var, bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", font=("Segoe UI", 8))
        chk_code.pack(side="left", padx=2)

        self.anti_icon_var = tk.BooleanVar(value=False)
        chk_icon = tk.Checkbutton(self.row_anti, text="✨ Icon", variable=self.anti_icon_var, bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", font=("Segoe UI", 8))
        chk_icon.pack(side="left", padx=2)

        # Hàng 3.5: Cài đặt Tốc độ gửi tin nhắn & Độ trễ ngẫu nhiên (Delay Min - Max)
        self.row_delay = tk.Frame(send_card, bg="#1e293b", padx=6, pady=4)
        self.row_delay.pack(fill="x", pady=(2, 3))

        tk.Label(self.row_delay, text="⚡ Tốc Độ:", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#1e293b").pack(side="left")

        self.speed_preset_cb = ttk.Combobox(
            self.row_delay,
            values=[
                "Siêu Nhanh",
                "Nhanh",
                "Vừa",
                "Hơi Chậm",
                "Chậm",
                "Siêu Chậm (Mặc Định)",
                "Cực Chậm"
            ],
            width=20,
            state="readonly"
        )
        self.speed_preset_cb.set("Siêu Chậm (Mặc Định)")
        self.speed_preset_cb.pack(side="left", padx=(3, 6))
        self.speed_preset_cb.bind("<<ComboboxSelected>>", self._on_speed_preset_changed)

        tk.Label(self.row_delay, text="⏱️ Trễ:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")

        tk.Label(self.row_delay, text="Từ", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(3, 1))
        self.delay_min_var = tk.IntVar(value=15)
        self.delay_min_sp = tk.Spinbox(self.row_delay, from_=1, to=600, textvariable=self.delay_min_var, width=4, font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#34d399", buttonbackground="#334155")
        self.delay_min_sp.pack(side="left", padx=1)

        tk.Label(self.row_delay, text="đến", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=1)
        self.delay_max_var = tk.IntVar(value=50)
        self.delay_max_sp = tk.Spinbox(self.row_delay, from_=1, to=600, textvariable=self.delay_max_var, width=4, font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#34d399", buttonbackground="#334155")
        self.delay_max_sp.pack(side="left", padx=1)

        tk.Label(self.row_delay, text="s", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#1e293b").pack(side="left", padx=2)

        self.speed_desc_lbl = tk.Label(self.row_delay, text="(15-50s: Siêu an toàn chống chặn Zalo)", font=("Segoe UI", 8, "italic"), fg="#94a3b8", bg="#1e293b")
        self.speed_desc_lbl.pack(side="left", padx=2)

        # Hàng 4: Các nút điều khiển thực thi (Chỉ 1 nút chính Gửi/Tạm dừng/Tiếp tục + 1 nút Hủy)
        row_ctrl = tk.Frame(send_card, bg="#0f172a")
        row_ctrl.pack(fill="x", pady=(3, 1))

        self.btn_start_bc = tk.Button(
            row_ctrl,
            text="🚀 BẮT ĐẦU GỬI (F6)",
            bg="#dc2626",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._on_broadcast_action_clicked
        )
        self.btn_start_bc.pack(side="left", padx=2)

        self.btn_cancel_bc = tk.Button(
            row_ctrl,
            text="⏹ Hủy (F7)",
            bg="#475569",
            fg="#fca5a5",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._cancel_broadcast
        )
        self.btn_cancel_bc.pack(side="left", padx=2)

        btn_reset_bc_ctrl = tk.Button(
            row_ctrl,
            text="🔄 Reset Lỗi",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=3,
            cursor="hand2",
            command=self.reset_all_retry_and_error_states
        )
        btn_reset_bc_ctrl.pack(side="left", padx=2)

        self.btn_tab2_quick_send_f10 = tk.Button(
            row_ctrl,
            text="⚡ GỬI VÀO ZALO (F10)",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._send_direct_current_template_to_zalo(auto_enter=True)
        )
        self.btn_tab2_quick_send_f10.pack(side="left", padx=2)

        btn_audit = tk.Button(
            row_ctrl,
            text="🔍 Kiểm Tra Lặp/Thiếu",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=3,
            cursor="hand2",
            command=self._show_audit_report_modal
        )
        btn_audit.pack(side="left", padx=3)

        self.bc_status_lbl = tk.Label(row_ctrl, text="Sẵn sàng.", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        self.bc_status_lbl.pack(side="left", padx=4)


        # KHUNG 2: CÀI ĐẶT LÊN LỊCH TỰ ĐỘNG (7h, 10h, 17h, 20h...)
        sch_card = tk.LabelFrame(right_frame, text=" ⏰ CÀI ĐẶT LÊN LỊCH TỰ ĐỘNG THEO GIỜ (7h, 10h, 17h, 20h...) ", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#0f172a", padx=10, pady=6)
        sch_card.pack(fill="x", pady=(0, 8))

        sch_top = tk.Frame(sch_card, bg="#0f172a")
        sch_top.pack(fill="x", pady=2)

        self.sch_enable_var = tk.BooleanVar(value=True)
        chk_sch_enable = tk.Checkbutton(sch_top, text="🟢 BẬT TIẾN TRÌNH LẬP LỊCH TỰ ĐỘNG CHẠY NGẦM", variable=self.sch_enable_var, bg="#0f172a", fg="#22c55e", selectcolor="#1e293b", activebackground="#0f172a", font=("Segoe UI", 8, "bold"), command=self._toggle_scheduler_daemon)
        chk_sch_enable.pack(side="left")

        self.sch_container = tk.Frame(sch_card, bg="#1e293b", padx=6, pady=4)
        self.sch_container.pack(fill="x", pady=4)

        add_sch_row = tk.Frame(sch_card, bg="#0f172a")
        add_sch_row.pack(fill="x", pady=(2, 2))

        tk.Label(add_sch_row, text="Thêm giờ (HH:MM):", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(side="left")
        self.new_time_entry = tk.Entry(add_sch_row, font=("Segoe UI", 9), width=7, bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.new_time_entry.pack(side="left", padx=3)
        self.new_time_entry.insert(0, "08:30")

        tk.Label(add_sch_row, text="Dùng mẫu:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(side="left", padx=(4, 2))
        self.sch_tpl_cb = ttk.Combobox(add_sch_row, state="readonly", width=8)
        self.sch_tpl_cb.pack(side="left", padx=2)

        btn_add_time = tk.Button(add_sch_row, text="➕ Thêm Giờ", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=1, cursor="hand2", command=self._add_custom_schedule_time)
        btn_add_time.pack(side="left", padx=4)


        # Nạp dữ liệu ban đầu
        self._refresh_template_combobox()
        self._refresh_tags_combobox()
        self._refresh_schedules_ui()
        self._refresh_broadcast_logs_table()
        self._load_custom_targets_from_storage()
        self._on_target_mode_changed()
        self.after(300, self._refresh_target_windows_list)

    # ================= CÁC HÀM XỬ LÝ DANH SÁCH NGƯỜI NHẬN TỰ NHẬP =================
    def _on_target_mode_changed(self):
        mode = self.target_mode_var.get()
        if mode == "custom_list":
            self.frame_tag_targets.pack_forget()
            self.frame_custom_targets.pack(fill="x", pady=2, before=self.row_mode_frame)
        else:
            self.frame_custom_targets.pack_forget()
            self.frame_tag_targets.pack(fill="x", pady=2, before=self.row_mode_frame)

    def _get_custom_targets_filepath(self) -> str:
        return get_storage_path("custom_broadcast_targets.txt")

    def _load_custom_targets_from_storage(self):
        try:
            fp = self._get_custom_targets_filepath()
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self.target_names_txt.delete("1.0", tk.END)
                    self.target_names_txt.insert("1.0", content)
            else:
                sample_targets = "Nhóm Lịch Sử 6 - KNTT\nNhóm Lịch Sử 7 - KNTT\nNhóm Giáo Viên THCS\nCô Nguyễn Thị Mai"
                self.target_names_txt.delete("1.0", tk.END)
                self.target_names_txt.insert("1.0", sample_targets)
                self._save_custom_targets_to_storage()
        except Exception as e:
            logger.debug(f"Lỗi load custom targets: {e}")
        self._update_target_count_badge()

    def _save_custom_targets_to_storage(self):
        try:
            fp = self._get_custom_targets_filepath()
            content = self.target_names_txt.get("1.0", tk.END).strip()
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.debug(f"Lỗi save custom targets: {e}")

    def _save_custom_targets_to_file(self):
        """Bí danh tương thích cho _save_custom_targets_to_storage."""
        return self._save_custom_targets_to_storage()

    def _update_target_count_badge(self):
        raw = self.target_names_txt.get("1.0", tk.END)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        count = len(lines)
        if hasattr(self, 'lbl_target_count'):
            self.lbl_target_count.configure(text=f"📋 Danh sách Tên Nhóm / Người Nhận (Mỗi dòng 1 tên):  [{count} nhóm/người]")

    def _on_target_text_focus_out(self):
        self._update_target_count_badge()
        self._save_custom_targets_to_storage()

    def _clear_targets_txt(self):
        self.target_names_txt.delete("1.0", tk.END)
        self._update_target_count_badge()
        self._save_custom_targets_to_storage()
        self.show_toast("Đã Xóa", "Đã xóa trắng danh sách người nhận!", "info")

    def _paste_targets_from_clipboard(self):
        try:
            import pyperclip
            clip_text = pyperclip.paste()
            if clip_text and clip_text.strip():
                cur = self.target_names_txt.get("1.0", tk.END).strip()
                if cur:
                    new_text = cur + "\n" + clip_text.strip()
                else:
                    new_text = clip_text.strip()
                self.target_names_txt.delete("1.0", tk.END)
                self.target_names_txt.insert("1.0", new_text)
                self._update_target_count_badge()
                self._save_custom_targets_to_storage()
                self.show_toast("Đã Dán", "Đã dán danh sách từ Clipboard!", "success")
            else:
                self.show_toast("Clipboard Trống", "Không có nội dung trong bộ nhớ tạm!", "warning")
        except Exception as e:
            self.show_toast("Lỗi", f"Lỗi dán từ clipboard: {e}", "error")

    def _import_targets_from_file(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Chọn File Danh Sách Nhóm / Người Nhận",
            filetypes=[("Text / CSV files", "*.txt *.csv"), ("All files", "*.*")]
        )
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    cur = self.target_names_txt.get("1.0", tk.END).strip()
                    if cur:
                        new_content = cur + "\n" + "\n".join(lines)
                    else:
                        new_content = "\n".join(lines)
                    self.target_names_txt.delete("1.0", tk.END)
                    self.target_names_txt.insert("1.0", new_content)
                    self._update_target_count_badge()
                    self._save_custom_targets_to_storage()
                    self.show_toast("Nạp Thành Công", f"Đã nạp {len(lines)} nhóm/người từ file!", "success")
                else:
                    self.show_toast("File Trống", "File không có dữ liệu hợp lệ!", "warning")
            except Exception as e:
                self.show_toast("Lỗi Nạp File", f"Không thể đọc file: {e}", "error")

    # ================= CÁC HÀM XỬ LÝ MẪU TIN NHẮN (DYNAMIC TEMPLATES) =================
    def _refresh_template_combobox(self):
        tpls = self.state.get_all_templates()
        vals = [f"Mẫu {t['template_num']}: {t['title'][:20]}" for t in tpls]
        self.tpl_select_cb['values'] = vals
        self.sch_tpl_cb['values'] = [f"Mẫu {t['template_num']}" for t in tpls] + ["🎲 Random"]

        if tpls:
            cur_idx = 0
            for i, t in enumerate(tpls):
                if t['template_num'] == getattr(self, "selected_tpl_num", 1):
                    cur_idx = i
                    break
            self.tpl_select_cb.current(cur_idx)
            self._load_template_by_obj(tpls[cur_idx])
            if not self.sch_tpl_cb.get():
                self.sch_tpl_cb.set(f"Mẫu {tpls[0]['template_num']}")

    def _on_template_cb_selected(self):
        sel_text = self.tpl_select_cb.get()
        if sel_text.startswith("Mẫu "):
            try:
                num = int(sel_text.split(":")[0].replace("Mẫu ", "").strip())
                self.selected_tpl_num = num
                tpl = self.state.get_template(num)
                if tpl:
                    self._load_template_by_obj(tpl)
            except Exception:
                pass

    def _load_template_by_obj(self, tpl: dict):
        self.selected_tpl_num = tpl.get('template_num', 1)
        self.tpl_title_entry.delete(0, tk.END)
        self.tpl_title_entry.insert(0, tpl.get("title", f"Mẫu {self.selected_tpl_num}"))

        self.tpl_content_txt.delete("1.0", tk.END)
        self.tpl_content_txt.insert(tk.END, tpl.get("content", ""))

        self.current_attached_files = tpl.get("files", [])
        self._update_files_listbox_ui()

        is_def = tpl.get("is_default", 0) == 1
        self.lbl_default_badge.configure(text="⭐ MẶC ĐỊNH" if is_def else "")

    def _create_new_template_dialog(self):
        new_num = self.state.add_new_template(
            title=f"Mẫu {self.selected_tpl_num + 1}: Tin nhắn soạn mới",
            content="Dạ em gửi Thầy/Cô thông tin và tài liệu ạ! 😊",
            file_paths=[]
        )
        self.selected_tpl_num = new_num
        self._refresh_template_combobox()
        self.show_toast("Tạo Thành Công", f"Đã tạo thêm Mẫu {new_num} mới!", "success")

    def _delete_current_template(self):
        ok = self.state.delete_template(self.selected_tpl_num)
        if ok:
            self.selected_tpl_num = 1
            self._refresh_template_combobox()
            self.show_toast("Đã Xóa", "Đã xóa mẫu tin nhắn thành công!", "info")
        else:
            self.show_toast("Không Thể Xóa", "Hệ thống cần giữ lại ít nhất 1 Mẫu tin nhắn!", "warning")

    def _update_files_listbox_ui(self):
        self.tpl_files_listbox.delete(0, tk.END)
        count_word = 0
        count_ppt = 0
        count_pdf = 0
        count_excel = 0
        count_video = 0
        count_img = 0
        count_dir = 0
        count_other = 0
        missing_count = 0

        for f in self.current_attached_files:
            exists = os.path.exists(f)
            if not exists:
                missing_count += 1
                missing_flag = "⚠️ [THIẾU TRÊN MÁY NÀY] "
            else:
                missing_flag = ""

            if os.path.isdir(f):
                count_dir += 1
                icon = "📂 [Thư mục]"
            else:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".3gp", ".m4v", ".ts"]:
                    count_video += 1
                    icon = "🎬 [Video]"
                elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff"]:
                    count_img += 1
                    icon = "🖼️ [Ảnh]"
                elif ext in [".docx", ".doc", ".rtf", ".txt", ".md"]:
                    count_word += 1
                    icon = "📄 [Word/Doc]"
                elif ext in [".pptx", ".ppt", ".pps", ".ppsx"]:
                    count_ppt += 1
                    icon = "📊 [PowerPoint]"
                elif ext in [".xlsx", ".xls", ".csv"]:
                    count_excel += 1
                    icon = "📈 [Excel]"
                elif ext in [".pdf"]:
                    count_pdf += 1
                    icon = "📑 [PDF]"
                elif ext in [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"]:
                    count_other += 1
                    icon = "📦 [Nén Zip/Rar/7z]"
                elif ext in [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]:
                    count_other += 1
                    icon = "🎵 [Audio]"
                else:
                    count_other += 1
                    icon = "📎 [Tệp]"
            self.tpl_files_listbox.insert(tk.END, f"{missing_flag}{icon} {os.path.basename(f)}  ({f})")

        # Cập nhật dòng nhãn thống kê & đếm số lượng chi tiết từng loại file
        if hasattr(self, 'lbl_file_count_summary'):
            total_items = len(self.current_attached_files)
            if total_items == 0:
                self.lbl_file_count_summary.configure(
                    text="📊 Đính kèm: 0 file (Chưa chọn file/thư mục nào)",
                    fg="#94a3b8"
                )
            else:
                parts = []
                if count_word: parts.append(f"📄 {count_word} Word")
                if count_ppt: parts.append(f"📊 {count_ppt} PPT")
                if count_pdf: parts.append(f"📑 {count_pdf} PDF")
                if count_excel: parts.append(f"📈 {count_excel} Excel")
                if count_video: parts.append(f"🎬 {count_video} Video")
                if count_img: parts.append(f"🖼️ {count_img} Ảnh")
                if count_dir: parts.append(f"📂 {count_dir} Thư mục")
                if count_other: parts.append(f"📎 {count_other} File khác")

                sum_text = f"📊 Tổng: {total_items} mục"
                if parts:
                    sum_text += " (" + ", ".join(parts) + ")"
                if missing_count > 0:
                    sum_text += f" | ⚠️ Có {missing_count} file không tìm thấy trên ổ đĩa máy này!"
                    self.lbl_file_count_summary.configure(text=sum_text, fg="#f87171")
                else:
                    self.lbl_file_count_summary.configure(text=sum_text, fg="#38bdf8")

    def _add_files_to_template(self):
        file_filters = [
            ("Tất cả định dạng hỗ trợ (Video, Ảnh, Office, Zip, Rar, 7z, PDF)", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.png *.jpg *.jpeg *.gif *.webp *.bmp *.docx *.doc *.pptx *.ppt *.xlsx *.xls *.pdf *.txt *.csv *.zip *.rar *.7z *.tar *.gz *.mp3 *.wav"),
            ("🎬 Video / Media (*.mp4, *.mov, *.avi, *.mkv...)", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.3gp *.m4v *.ts"),
            ("🖼️ Hình ảnh (*.png, *.jpg, *.jpeg, *.gif, *.webp...)", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg *.ico *.tiff"),
            ("📄 Văn phòng & PDF (*.docx, *.pptx, *.xlsx, *.pdf...)", "*.docx *.doc *.pptx *.ppt *.xlsx *.xls *.pdf *.txt *.csv *.rtf *.md"),
            ("📦 File Nén (*.zip, *.rar, *.7z, *.tar, *.gz...)", "*.zip *.rar *.7z *.tar *.gz *.bz2 *.iso"),
            ("🎵 Âm thanh / Audio (*.mp3, *.wav, *.m4a...)", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
            ("🌐 Tất cả các loại file (*.*)", "*.*")
        ]
        file_paths = filedialog.askopenfilenames(
            title="Chọn các file đính kèm (Video, Ảnh, Word, PPT, Excel, Zip, Rar, 7z, PDF...)",
            filetypes=file_filters
        )
        if file_paths:
            for p in file_paths:
                if p not in self.current_attached_files:
                    self.current_attached_files.append(p)
            self._update_files_listbox_ui()
            self.show_toast("Đã Thêm File", f"Đã thêm {len(file_paths)} file/media vào Mẫu {self.selected_tpl_num}!", "info")

    def _add_folder_to_template(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục chứa tài liệu để gửi vào nhóm")
        if folder_path and folder_path not in self.current_attached_files:
            self.current_attached_files.append(folder_path)
            self._update_files_listbox_ui()
            self.show_toast("Đã Thêm Thư Mục", f"Đã thêm thư mục '{os.path.basename(folder_path)}'!", "info")

    def _remove_selected_file_from_template(self):
        sel = self.tpl_files_listbox.curselection()
        if sel:
            idx = sel[0]
            del self.current_attached_files[idx]
            self._update_files_listbox_ui()

    def _clear_all_template_files(self):
        self.current_attached_files.clear()
        self._update_files_listbox_ui()

    def _save_current_template_from_ui(self):
        title = self.tpl_title_entry.get().strip()
        content = self.tpl_content_txt.get("1.0", tk.END).strip()
        if not title:
            title = f"Mẫu {self.selected_tpl_num}"

        tpl = self.state.get_template(self.selected_tpl_num)
        is_def = tpl.get("is_default", 0) == 1 if tpl else (self.selected_tpl_num == 1)

        self.state.save_template(
            template_num=self.selected_tpl_num,
            title=title,
            content=content,
            file_paths=self.current_attached_files,
            is_default=is_def
        )
        self._refresh_template_combobox()
        self.show_toast("Thành Công", f"Đã lưu thành công Mẫu {self.selected_tpl_num}!", "success")

    def _set_current_template_as_default(self):
        self._save_current_template_from_ui()
        title = self.tpl_title_entry.get().strip()
        content = self.tpl_content_txt.get("1.0", tk.END).strip()
        self.state.save_template(
            template_num=self.selected_tpl_num,
            title=title,
            content=content,
            file_paths=self.current_attached_files,
            is_default=True
        )
        self._refresh_template_combobox()
        self.lbl_default_badge.configure(text="⭐ MẶC ĐỊNH")
        self.show_toast("Mặc Định", f"Đã đặt Mẫu {self.selected_tpl_num} làm Mẫu Mặc Định!", "success")

    # ================= QUẢN LÝ THẺ PHÂN LOẠI NHÓM TÙY CHỈNH =================
    def _refresh_tags_combobox(self):
        tags = self.state.get_all_tags()
        self.bc_tag_cb['values'] = tags
        if tags and not self.bc_tag_cb.get():
            self.bc_tag_cb.set(tags[0])

    def _add_custom_tag_dialog(self):
        modal = tk.Toplevel(self)
        modal.title("➕ Thêm Thẻ Phân Loại Zalo")
        modal.geometry("400x170")
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()
        apply_windows_dark_titlebar(modal, "#0f172a", "#f8fafc")

        tk.Label(modal, text="Nhập tên Thẻ phân loại mới:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w", padx=15, pady=(15, 5))
        tag_ent = tk.Entry(modal, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        tag_ent.pack(fill="x", padx=15, pady=5)
        tag_ent.focus_set()

        def _do_add():
            val = tag_ent.get().strip()
            if not val:
                return
            ok = self.state.add_broadcast_tag(val)
            if ok:
                self._refresh_tags_combobox()
                self.bc_tag_cb.set(val)
                self.show_toast("Đã Thêm Thẻ", f"Đã thêm thẻ '{val}' vào danh mục!", "success")
                modal.destroy()
            else:
                self.show_toast("Trùng Lặp", f"Thẻ '{val}' đã tồn tại!", "warning")

        btn_box = tk.Frame(modal, bg="#0f172a")
        btn_box.pack(fill="x", padx=15, pady=12)
        tk.Button(btn_box, text="Thêm Ngay", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=_do_add).pack(side="left")
        tk.Button(btn_box, text="Hủy", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=modal.destroy).pack(side="right")

    def _edit_custom_tag_dialog(self):
        cur_tag = self.bc_tag_cb.get().strip()
        if not cur_tag:
            self.show_toast("Chưa Chọn Thẻ", "Vui lòng chọn Thẻ cần sửa trong danh sách!", "warning")
            return

        modal = tk.Toplevel(self)
        modal.title("✏️ Đổi Tên / Sửa Thẻ Phân Loại Zalo")
        modal.geometry("400x170")
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()
        apply_windows_dark_titlebar(modal, "#0f172a", "#f8fafc")

        tk.Label(modal, text=f"Chỉnh sửa tên Thẻ (Hiện tại: '{cur_tag}'):", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w", padx=15, pady=(15, 5))
        tag_ent = tk.Entry(modal, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        tag_ent.insert(0, cur_tag)
        tag_ent.pack(fill="x", padx=15, pady=5)
        tag_ent.focus_set()
        tag_ent.select_range(0, tk.END)

        def _do_update():
            new_val = tag_ent.get().strip()
            if not new_val:
                self.show_toast("Tên Rỗng", "Tên thẻ không được để trống!", "warning")
                return
            if new_val == cur_tag:
                modal.destroy()
                return

            ok = self.state.update_broadcast_tag(cur_tag, new_val)
            if ok:
                self._refresh_tags_combobox()
                self.bc_tag_cb.set(new_val)
                self.show_toast("Đã Cập Nhật", f"Đã đổi tên thẻ thành '{new_val}'!", "success")
                modal.destroy()
            else:
                self.show_toast("Lỗi Đổi Tên", f"Tên thẻ '{new_val}' đã tồn tại hoặc không hợp lệ!", "error")

        btn_box = tk.Frame(modal, bg="#0f172a")
        btn_box.pack(fill="x", padx=15, pady=12)
        tk.Button(btn_box, text="💾 Lưu Thay Đổi", bg="#f59e0b", fg="black", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=_do_update).pack(side="left")
        tk.Button(btn_box, text="Hủy", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=modal.destroy).pack(side="right")

    def _delete_custom_tag(self):
        cur_tag = self.bc_tag_cb.get().strip()
        if not cur_tag:
            self.show_toast("Chưa Chọn Thẻ", "Vui lòng chọn Thẻ cần xóa!", "warning")
            return
        
        all_tags = self.state.get_all_tags()
        if len(all_tags) <= 1:
            self.show_toast("Không Thể Xóa", "Cần giữ ít nhất 1 Thẻ trong hệ thống!", "warning")
            return

        self.state.delete_broadcast_tag(cur_tag)
        self._refresh_tags_combobox()
        new_tags = self.state.get_all_tags()
        if new_tags:
            self.bc_tag_cb.set(new_tags[0])
        self.show_toast("Đã Xóa", f"Đã xóa thẻ '{cur_tag}' thành công!", "info")

    # ================= ĐIỀU KHIỂN GỬI NHÓM & PHÍM TẮT F6 / F7 =================
    def _on_broadcast_action_clicked(self):
        """Xử lý nút bấm duy nhất của Tab Gửi Nhóm: Bắt Đầu / Tạm Dừng / Tiếp Tục."""
        if not getattr(self, '_is_broadcasting', False):
            self._start_group_broadcast_now()
        else:
            self._toggle_broadcast_pause()

    def _start_group_broadcast_now(self):
        from zalo_layer.zalo_automation import BroadcastController, ZaloAutomation
        target_mode = self.target_mode_var.get()
        is_anti_dup = self.anti_dup_var.get()
        mode = self.send_mode_var.get()

        use_random = (mode == "random")
        tpl_num = self.selected_tpl_num
        if mode == "default":
            def_tpl = self.state.get_default_template()
            if def_tpl:
                tpl_num = def_tpl.get('template_num', 1)

        tpl = self.state.get_template(tpl_num)
        content = tpl.get('content', '') if tpl else self.tpl_content_txt.get("1.0", tk.END).strip()
        files = tpl.get('files', []) if tpl else list(self.current_attached_files)

        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if is_anti_dup else f"run_{time.time()}"
        
        self._is_broadcasting = True
        self.btn_start_bc.configure(text="⏸ TẠM DỪNG (F6)", bg="#d97706")

        def _progress(idx, name, status):
            def _ui_update():
                self.bc_status_lbl.configure(text=f"Đã xử lý: {name} ({status})")
                self._refresh_broadcast_logs_table()
            self.after(0, _ui_update)

        try:
            min_d = float(self.delay_min_var.get())
            max_d = float(self.delay_max_var.get())
            if min_d > max_d:
                min_d, max_d = max_d, min_d
        except Exception:
            min_d, max_d = 5.0, 15.0

        if target_mode == "custom_list":
            raw_text = self.target_names_txt.get("1.0", tk.END).strip()
            targets = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not targets:
                self._is_broadcasting = False
                self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
                self.show_toast("Chưa Nhập Danh Sách", "Vui lòng nhập ít nhất 1 Tên Nhóm hoặc Tên Người Dùng vào danh sách!", "warning")
                self.bc_status_lbl.configure(text="⚠️ Chưa nhập danh sách người nhận.", fg="#f59e0b")
                return

            self._save_custom_targets_to_storage()
            target_count = len(targets)
            self.bc_status_lbl.configure(text=f"Đang gửi {target_count} nhóm/người (Delay: {min_d:.0f}-{max_d:.0f}s)...", fg="#fbbf24")
            self._append_chat_message("SYS", "Hệ Thống", f"📢 [Broadcast] Bắt đầu gửi {target_count} nhóm/người theo Danh Sách (Delay: {min_d:.0f}-{max_d:.0f}s, Mode: {mode})...")
            self.show_toast("Bắt Đầu Gửi", f"Đang gửi {target_count} nhóm/người theo danh sách...", "info")

            def _worker_custom():
                try:
                    results = ZaloAutomation.broadcast_to_custom_target_list(
                        target_names=targets,
                        messages=[content] if content else [],
                        file_paths=files,
                        state_mgr=self.state,
                        batch_id=batch_id,
                        template_num=tpl_num,
                        min_delay=min_d,
                        max_delay=max_d,
                        progress_callback=_progress,
                        use_random_template=use_random,
                        anti_spam_time=self.anti_time_var.get(),
                        anti_spam_code=self.anti_code_var.get(),
                        anti_spam_icon=self.anti_icon_var.get(),
                        background_mode=self.target_window_enabled_var.get()
                    )
                    success_count = sum(1 for r in results if r["status"] == "COMPLETED")
                    def _on_done():
                        self._is_broadcasting = False
                        self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
                        self.bc_status_lbl.configure(text=f"🎉 Hoàn tất: {success_count}/{len(results)} nhóm/người!", fg="#34d399")
                        self._append_chat_message("SYS", "Hệ Thống", f"🎉 [Broadcast] Đã gửi thành công vào {success_count}/{len(results)} nhóm/người theo danh sách.")
                        self.show_toast("Hoàn Tất Gửi", f"Đã gửi thành công vào {success_count}/{len(results)} nhóm/người!", "success")
                        self._refresh_broadcast_logs_table()
                    self.after(0, _on_done)
                except Exception as e:
                    logger.error(f"[Broadcast Error] Lỗi khi gửi theo danh sách: {e}", exc_info=True)
                    def _on_err():
                        self._is_broadcasting = False
                        self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
                        self.bc_status_lbl.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")
                        self._append_chat_message("SYS", "Hệ Thống", f"❌ [Lỗi Broadcast] {e}")
                        self.show_toast("Lỗi Gửi Tin", f"Đã xảy ra lỗi: {e}", "error")
                    self.after(0, _on_err)

            threading.Thread(target=_worker_custom, daemon=True).start()

        else:  # Mode "tag"
            tag_name = self.bc_tag_cb.get().strip()
            try:
                target_count = int(self.bc_count_var.get())
            except Exception:
                target_count = 5
            target_count = max(1, min(target_count, 100))

            self.bc_status_lbl.configure(text=f"Đang gửi {target_count} nhóm trong Thẻ '{tag_name}' (Delay: {min_d:.0f}-{max_d:.0f}s)...", fg="#fbbf24")
            self._append_chat_message("SYS", "Hệ Thống", f"📢 [Broadcast] Bắt đầu gửi {target_count} nhóm trong Thẻ '{tag_name}' (Delay: {min_d:.0f}-{max_d:.0f}s, Mode: {mode})...")
            self.show_toast("Bắt Đầu Gửi", f"Đang gửi {target_count} nhóm trong Thẻ '{tag_name}'...", "info")

            def _worker_tag():
                try:
                    results = ZaloAutomation.broadcast_to_groups_in_tag(
                        tag_name=tag_name,
                        messages=[content] if content else [],
                        file_paths=files,
                        state_mgr=self.state,
                        batch_id=batch_id,
                        template_num=tpl_num,
                        max_groups=target_count,
                        min_delay=min_d,
                        max_delay=max_d,
                        progress_callback=_progress,
                        use_random_template=use_random,
                        anti_spam_time=self.anti_time_var.get(),
                        anti_spam_code=self.anti_code_var.get(),
                        anti_spam_icon=self.anti_icon_var.get(),
                        background_mode=self.target_window_enabled_var.get()
                    )
                    success_count = sum(1 for r in results if r["status"] == "COMPLETED")
                    def _on_done_tag():
                        self._is_broadcasting = False
                        self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
                        self.bc_status_lbl.configure(text=f"🎉 Hoàn tất: {success_count}/{len(results)} nhóm!", fg="#34d399")
                        self._append_chat_message("SYS", "Hệ Thống", f"🎉 [Broadcast] Đã gửi thành công vào {success_count}/{len(results)} nhóm trong Thẻ '{tag_name}'.")
                        self.show_toast("Hoàn Tất Gửi Nhóm", f"Đã gửi thành công vào {success_count}/{len(results)} nhóm!", "success")
                        self._refresh_broadcast_logs_table()
                    self.after(0, _on_done_tag)
                except Exception as e:
                    logger.error(f"[Broadcast Error] Lỗi khi gửi tin nhóm theo Thẻ: {e}", exc_info=True)
                    def _on_err_tag():
                        self._is_broadcasting = False
                        self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
                        self.bc_status_lbl.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")
                        self._append_chat_message("SYS", "Hệ Thống", f"❌ [Lỗi Broadcast] {e}")
                        self.show_toast("Lỗi Gửi Tin", f"Đã xảy ra lỗi: {e}", "error")
                    self.after(0, _on_err_tag)

            threading.Thread(target=_worker_tag, daemon=True).start()


    def _toggle_broadcast_pause(self):
        from zalo_layer.zalo_automation import BroadcastController
        is_paused = BroadcastController.toggle_pause()
        if is_paused:
            self.btn_start_bc.configure(text="▶ TIẾP TỤC (F6)", bg="#059669")
            self.bc_status_lbl.configure(text="⏸ ĐANG TẠM DỪNG GỬI (F6)", fg="#f59e0b")
            self.show_toast("Tạm Dừng", "Đã TẠM DỪNG tiến trình gửi nhóm (F6)!", "warning")
        else:
            self.btn_start_bc.configure(text="⏸ TẠM DỪNG (F6)", bg="#d97706")
            self.bc_status_lbl.configure(text="Đang tiếp tục gửi...", fg="#34d399")
            self.show_toast("Tiếp Tục", "Đang TIẾP TỤC tiến trình gửi nhóm (F6)!", "success")

    def _cancel_broadcast(self):
        from zalo_layer.zalo_automation import BroadcastController
        BroadcastController.cancel()
        self._is_broadcasting = False
        self.btn_start_bc.configure(text="🚀 BẮT ĐẦU GỬI (F6)", bg="#dc2626")
        self.bc_status_lbl.configure(text="⏹ ĐÃ HỦY GỬI (F7)", fg="#ef4444")
        self.show_toast("Đã Hủy Gửi", "Đã HỦY BỎ đợt gửi tin nhóm hiện tại (F7)!", "error")

    def _toggle_broadcast_pause_from_hotkey(self):
        self.after(0, self._toggle_broadcast_pause)

    def _cancel_broadcast_from_hotkey(self):
        self.after(0, self._cancel_broadcast)

    # ================= AUDIT CHECK GỬI LẶP & GỬI THIẾU =================
    def _show_audit_report_modal(self):
        tag_name = self.bc_tag_cb.get().strip()
        report = self.state.audit_broadcast_batch(tag_name=tag_name)

        modal = tk.Toplevel(self)
        modal.title("🔍 Báo Cáo Rà Soát Gửi Lặp & Gửi Thiếu")
        modal.geometry("520x340")
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()
        apply_windows_dark_titlebar(modal, "#0f172a", "#f8fafc")

        hdr = tk.Frame(modal, bg="#1e293b", padx=12, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📊 KẾT QUẢ KIỂM TRA TOÀN VẸN CHIẾN DỊCH GỬI NHÓM", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")

        body = tk.Frame(modal, bg="#0f172a", padx=15, pady=12)
        body.pack(fill="both", expand=True)

        res_color = "#22c55e" if report["is_perfect"] else "#f59e0b"
        tk.Label(body, text=report["summary_text"], font=("Segoe UI", 9, "bold"), fg=res_color, bg="#0f172a", wraplength=480, justify="left").pack(anchor="w", pady=(0, 10))

        detail_box = tk.Frame(body, bg="#1e293b", padx=10, pady=8)
        detail_box.pack(fill="x", pady=4)

        tk.Label(detail_box, text=f"• Tổng số lượt ghi nhận: {report['total_logs']}", font=("Segoe UI", 9), fg="#f8fafc", bg="#1e293b").pack(anchor="w")
        tk.Label(detail_box, text=f"• Nhóm đã gửi thành công: {report['sent_count']} nhóm", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b").pack(anchor="w")
        tk.Label(detail_box, text=f"• Nhóm bị gửi lặp: {report['duplicate_count']} (Chuẩn an toàn: 0)", font=("Segoe UI", 9, "bold"), fg="#ef4444" if report['duplicate_count'] > 0 else "#34d399", bg="#1e293b").pack(anchor="w")
        tk.Label(detail_box, text=f"• Nhóm gửi lỗi / thiếu: {report['failed_count']}", font=("Segoe UI", 9), fg="#f8fafc", bg="#1e293b").pack(anchor="w")

        tk.Button(body, text="Đóng", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=14, pady=4, cursor="hand2", command=modal.destroy).pack(side="bottom", pady=10)

    # ================= LÊN LỊCH TỰ ĐỘNG & NHẬT KÝ =================
    def _refresh_schedules_ui(self):
        for widget in self.sch_container.winfo_children():
            widget.destroy()

        schedules = self.state.get_all_schedules()
        for sch in schedules:
            row = tk.Frame(self.sch_container, bg="#1e293b", pady=2)
            row.pack(fill="x")

            is_act_var = tk.BooleanVar(value=(sch["is_active"] == 1))
            chk = tk.Checkbutton(
                row,
                text=f"⏰ {sch['schedule_time']} (Mẫu #{sch['template_num']})",
                variable=is_act_var,
                bg="#1e293b",
                fg="#f8fafc" if sch["is_active"] == 1 else "#64748b",
                selectcolor="#0f172a",
                activebackground="#1e293b",
                font=("Segoe UI", 8, "bold"),
                command=lambda s_id=sch["id"], v=is_act_var: self._toggle_schedule_active(s_id, v.get())
            )
            chk.pack(side="left")

            last_run = sch.get("last_run_date")
            if last_run:
                tk.Label(row, text=f"• Chạy gần nhất: {last_run}", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=10)

            btn_del = tk.Button(row, text="✕", bg="#334155", fg="#ef4444", font=("Segoe UI", 8, "bold"), relief="flat", padx=4, cursor="hand2", command=lambda s_id=sch["id"]: self._delete_schedule_time(s_id))
            btn_del.pack(side="right", padx=2)

    def _toggle_bot_running_state(self):
        """Bật / Tạm dừng lắng nghe và trả lời tự động của Bot AI (F8)."""
        if hasattr(self, 'handler') and self.handler:
            if getattr(self.handler, 'is_running', False):
                self.handler.pause()
                self._update_bot_ui_state(is_running=False)
                self.show_toast("Tạm Dừng Bot (F8)", "Đã tạm dừng bot AI CSKH.", "warning")
            else:
                self.handler.resume()
                self._update_bot_ui_state(is_running=True)
                self.show_toast("Bật Bot (F8)", "Bot AI CSKH đang lắng nghe và sẵn sàng trả lời tự động!", "success")

    def _toggle_bot_running_state_from_hotkey(self):
        self._toggle_bot_running_state()

    def _update_bot_ui_state(self, is_running: bool):
        """Cập nhật giao diện nút bấm và thanh trạng thái theo trạng thái của Bot."""
        if is_running:
            if hasattr(self, 'btn_toggle_bot') and self.btn_toggle_bot.winfo_exists():
                self.btn_toggle_bot.configure(text="⏸ Dừng Bot", bg="#e11d48")
            if hasattr(self, 'btn_float_bot') and self.btn_float_bot.winfo_exists():
                self.btn_float_bot.configure(text="🟢 Bot (F8)", bg="#059669")
            if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                self.status_lbl.configure(text="● BOT CHẠY (F8)", fg="#34d399")
            if hasattr(self, 'footer_status_lbl') and self.footer_status_lbl.winfo_exists():
                self.footer_status_lbl.configure(text="🟢 Đang hoạt động (F8)", fg="#34d399")
        else:
            if hasattr(self, 'btn_toggle_bot') and self.btn_toggle_bot.winfo_exists():
                self.btn_toggle_bot.configure(text="▶ Bật Bot", bg="#059669")
            if hasattr(self, 'btn_float_bot') and self.btn_float_bot.winfo_exists():
                self.btn_float_bot.configure(text="⏸ Bot (F8)", bg="#e11d48")
            if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                self.status_lbl.configure(text="● TẠM DỪNG (F8)", fg="#f87171")
            if hasattr(self, 'footer_status_lbl') and self.footer_status_lbl.winfo_exists():
                self.footer_status_lbl.configure(text="⏸ Đã tạm dừng (F8)", fg="#f87171")

    def _toggle_scheduler_daemon(self):
        if self.sch_enable_var.get():
            self.scheduler.start()
            self.show_toast("Lập Lịch Bật", "Đã BẬT tiến trình tự động gửi tin nhóm theo giờ!", "success")
        else:
            self.scheduler.stop()
            self.show_toast("Lập Lịch Tắt", "Đã TẮT tiến trình tự động gửi tin nhóm.", "warning")

    def _toggle_schedule_active(self, sch_id: int, is_active: bool):
        self.state.update_schedule_status(sch_id, is_active)
        self._refresh_schedules_ui()

    def _delete_schedule_time(self, sch_id: int):
        self.state.delete_schedule(sch_id)
        self._refresh_schedules_ui()
        self.show_toast("Đã Xóa", "Đã xóa mốc giờ lập lịch!", "info")

    def _add_custom_schedule_time(self):
        t_str = self.new_time_entry.get().strip()
        tpl_name = self.sch_tpl_cb.get()
        tpl_num = 1
        try:
            if "Mẫu " in tpl_name:
                tpl_num = int(tpl_name.replace("Mẫu ", "").strip())
        except Exception:
            tpl_num = 1

        if not t_str or len(t_str) < 4:
            self.show_toast("Cảnh Báo", "Vui lòng nhập định dạng giờ HH:MM (ví dụ 07:00, 10:00)!", "warning")
            return

        self.state.save_schedule(schedule_time=t_str, template_num=tpl_num, tag_filter="Gửi mẫu quảng cáo", is_active=True)
        self._refresh_schedules_ui()
        self.show_toast("Thành Công", f"Đã thêm mốc giờ tự động gửi {t_str} (Mẫu #{tpl_num})!", "success")

    def _refresh_broadcast_logs_table(self):
        for row in self.bc_tree.get_children():
            self.bc_tree.delete(row)
        logs = self.state.get_broadcast_logs(limit=40)
        for l in logs:
            st = "✅ ĐÃ GỬI" if l["status"] == "COMPLETED" else "❌ LỖI"
            self.bc_tree.insert("", "end", values=(
                l["group_name"],
                l["tag_name"],
                f"Mẫu {l['template_num']}",
                f"{l['file_count']} files",
                st,
                l["created_at"]
            ))

    def _delete_selected_broadcast_log(self):
        sel = self.bc_tree.selection()
        if not sel:
            self.show_toast("Chưa Chọn", "Vui lòng click chọn dòng nhật ký cần xóa!", "warning")
            return
        for item in sel:
            vals = self.bc_tree.item(item, "values")
            if vals:
                group_name = vals[0]
                created_at = vals[5] if len(vals) > 5 else None
                self.state.delete_broadcast_log_entry(group_name, created_at)
        self._refresh_broadcast_logs_table()
        self.show_toast("Đã Xóa", "Đã xóa dòng nhật ký gửi nhóm được chọn!", "info")

    def _clear_broadcast_batch_history(self):
        self.state.clear_broadcast_history()
        self._refresh_broadcast_logs_table()
        self.show_toast("Đã Xóa Nhật Ký", "Đã xóa sạch toàn bộ nhật ký gửi nhóm!", "info")

    def _delete_selected_conversation(self):
        if not hasattr(self, 'conv_tree') or not self.conv_tree.winfo_exists():
            return self._delete_selected_chat_session()
        sel = self.conv_tree.selection()
        if not sel:
            self.show_toast("Chưa Chọn", "Vui lòng chọn khách hàng cần xóa trong danh sách!", "warning")
            return
        for item in sel:
            vals = self.conv_tree.item(item, "values")
            if vals:
                display_name = vals[0]
                self.state.delete_conversation_by_name(display_name)
        self.refresh_all_data()
        self.show_toast("Đã Xóa", "Đã xóa hội thoại khách hàng được chọn!", "info")

    def _clear_all_conversations(self):
        if not hasattr(self, 'conv_tree') or not self.conv_tree.winfo_exists():
            return self._clear_all_chat_sessions_from_ui()
        self.state.clear_all_chat_history()
        self.refresh_all_data()
        self.log_text.delete("1.0", tk.END)
        self.show_toast("Đã Xóa Hết", "Đã xóa toàn bộ danh sách khách hàng và nhật ký chat!", "info")

    def _on_scheduled_broadcast_start(self, time_str, tpl_num, tag):
        self._append_chat_message("SYS", "Hệ Thống", f"⏰ [Tự Động Lập Lịch {time_str}] Đang bắt đầu gửi Mẫu #{tpl_num} vào Thẻ '{tag}'...")
        self.show_toast("Lập Lịch Tự Động", f"Đang tự động gửi Mẫu #{tpl_num} theo lịch {time_str}!", "info")

    def _on_scheduled_broadcast_end(self, results):
        success_count = sum(1 for r in results if r["status"] == "COMPLETED")
        self._append_chat_message("SYS", "Hệ Thống", f"🎉 [Lập Lịch Tự Động] Hoàn tất gửi tin vào {success_count}/{len(results)} nhóm.")
        self.show_toast("Lập Lịch Hoàn Tất", f"Đã gửi tự động vào {success_count}/{len(results)} nhóm!", "success")
        self._refresh_broadcast_logs_table()

    def _on_speed_preset_changed(self, event=None):
        preset = self.speed_preset_cb.get().strip()
        speed_map = {
            "Siêu Nhanh": (1, 3, "(1-3s: Rất nhanh, dành cho việc gửi gấp)", 1.0),
            "Nhanh": (2, 5, "(2-5s: Nhanh nhưng vẫn ổn định)", 1.5),
            "Vừa": (4, 8, "(4-8s: Cân bằng tốc độ & chống chặn)", 2.0),
            "Hơi Chậm": (6, 20, "(6-20s: An toàn khi gửi nhiều nhóm liên tục)", 3.5),
            "Chậm": (10, 30, "(10-30s: Dành cho gửi file nặng / mạng yếu)", 5.0),
            "Siêu Chậm (Mặc Định)": (15, 50, "(15-50s: Siêu an toàn chống chặn Zalo)", 8.0),
            "Cực Chậm": (30, 90, "(30-90s: Cực kỳ an toàn 100% chống chặn)", 12.0)
        }
        if preset in speed_map:
            min_d, max_d, desc, reply_d = speed_map[preset]
            self.delay_min_var.set(min_d)
            self.delay_max_var.set(max_d)
            if hasattr(self, "speed_desc_lbl"):
                self.speed_desc_lbl.configure(text=desc)
            if hasattr(self.handler, 'reply_delay'):
                self.handler.reply_delay = reply_d
            self.set_footer_task(f"Đã chuyển Tốc độ gửi: {preset} ({min_d}-{max_d}s)")
            self.show_toast("Tốc Độ Gửi", f"Đã chuyển tốc độ: {preset} ({min_d}-{max_d}s)", "info")

    def _send_direct_current_template_to_zalo(self, auto_enter: bool = True):
        """Gửi trực tiếp mẫu tin nhắn và file đang chọn ở Tab 2 vào Zalo PC hoặc Cửa sổ đang mở (Phím F10)."""
        content = self.tpl_content_txt.get("1.0", tk.END).strip() if hasattr(self, "tpl_content_txt") else ""
        files = list(self.current_attached_files) if hasattr(self, "current_attached_files") else []

        if not content and not files:
            self.show_toast("Nội Dung Trống", "Mẫu tin chưa có nội dung hoặc file để gửi!", "warning")
            return

        is_bg = self.target_window_enabled_var.get() if hasattr(self, "target_window_enabled_var") else True
        retries_cfg = int(self.app_settings.get("max_retries", 5))
        target_name = "Zalo Khóa Nền" if is_bg else "Khung Nhập Free (Cửa Sổ Active)"
        action_desc = f"Đang gửi nhanh vào {target_name} (F10)..." if auto_enter else f"Đang chèn nháp vào {target_name}..."
        self.set_footer_task(action_desc)

        def _worker():
            try:
                ZaloAutomation.reset_abort()
                ok = ZaloAutomation.send_script_template_to_current_chat(
                    content=content,
                    file_paths=files,
                    background_mode=is_bg,
                    auto_press_enter=auto_enter,
                    max_attempts=retries_cfg
                )
                def _ui_done():
                    try:
                        if not self.winfo_exists():
                            return
                        if ok:
                            msg = f"🎉 Đã gửi thành công vào {target_name}!" if auto_enter else f"📝 Đã chèn nháp vào {target_name}!"
                            self.show_toast("Thành Công (F10)", msg, "success")
                            self.set_footer_task("Sẵn sàng.")
                        else:
                            self.show_toast("Dừng Lại", f"Gửi thất bại sau {retries_cfg} lần thử liên tiếp. Hãy kiểm tra cửa sổ làm việc!", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_done)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"[Tab 2 Direct Send Error] Lỗi: {e}", exc_info=True)
                def _ui_err():
                    try:
                        if self.winfo_exists():
                            self.show_toast("Lỗi Gửi Tin", f"Đã xảy ra lỗi: {e}", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_err)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _on_f10_quick_send(self):
        """Phím tắt toàn cục F10: Gửi nhanh kịch bản Tab 3 hoặc mẫu Tab 2 trực tiếp vào Zalo PC đang mở."""
        active_tab = getattr(self, "active_main_tab", "chat")
        if active_tab == "script":
            self._send_current_script_to_zalo(auto_enter=True)
        elif active_tab == "broadcast":
            self._send_direct_current_template_to_zalo(auto_enter=True)
        else:
            # Nếu đang ở Tab khác: Ưu tiên gửi kịch bản Tab 3 nếu đã chọn, hoặc gửi mẫu Tab 2
            if hasattr(self, "current_script_id") and self.current_script_id:
                self._send_current_script_to_zalo(auto_enter=True)
            else:
                self._send_direct_current_template_to_zalo(auto_enter=True)

    # =========================================================================
    # CÁC HÀM XỬ LÝ KHÓA CHẶT ỨNG DỤNG ĐÍCH (CÁCH LY 100% GỬI NGẦM)
    # =========================================================================
    def _on_target_switch_toggle(self):
        """Bật/tắt chế độ khóa chạy nền độc lập."""
        is_on = self.target_window_enabled_var.get()
        target = ZaloAutomation.get_target_window()
        ZaloAutomation.set_target_window(
            target.get("top_hwnd"),
            target.get("leaf_hwnd"),
            target.get("proc_name", "Zalo.exe"),
            target.get("title", "Zalo"),
            enabled=is_on
        )
        if is_on:
            p_name = target.get("proc_name", "Zalo.exe")
            t_name = target.get("title", "Zalo")
            self.target_lock_status_lbl.configure(
                text=f"Trạng thái: 🔒 ĐÃ KHÓA NỀN [{p_name}] {t_name[:25]} - Cách ly 100% không ảnh hưởng app khác",
                fg="#34d399"
            )
            self.show_toast("Khóa Nền (BẬT)", f"Đã bật khóa chạy nền [{p_name}]. Gửi ngầm 100% không cướp chuột/phím!", "success")
        else:
            self.target_lock_status_lbl.configure(
                text="Trạng thái: 🌐 Đang tắt khóa nền (Gửi lên cửa sổ đang active)",
                fg="#94a3b8"
            )
            self.show_toast("Khóa Nền (TẮT)", "Đã tắt khóa chạy nền độc lập.", "warning")

    def _start_target_window_picker(self):
        """Bắt đầu cơ chế 1-Click bắt cửa sổ đích bằng chuột."""
        if getattr(self, '_is_picking_window', False):
            return
        self._is_picking_window = True
        self.btn_pick_target.configure(
            text="🖱️ Click chuột vào cửa sổ bạn muốn gắn...",
            bg="#ef4444"
        )
        self.show_toast("Gắn Cửa Sổ (1-Click)", "Hãy CLICK CHUỘT vào cửa sổ (Zalo, Game, App) bạn muốn ghim!", "info")

        def _on_picked(top_hwnd, leaf_hwnd, proc_name, title):
            def _ui():
                self._is_picking_window = False
                self.btn_pick_target.configure(
                    text="🎯 CLICK VÀO CỬA SỔ CẦN GẮN (1-CLICK)",
                    bg="#0284c7"
                )
                if top_hwnd and HAS_WIN32 and win32gui.IsWindow(top_hwnd):
                    ZaloAutomation.set_target_window(top_hwnd, leaf_hwnd, proc_name, title, enabled=True)
                    self.target_window_enabled_var.set(True)
                    display_str = f"[{proc_name}] {title[:45]}"
                    # Cập nhật combobox
                    cur_vals = list(self.target_window_cb['values'])
                    if display_str not in cur_vals:
                        cur_vals.insert(0, display_str)
                        self.target_window_cb.configure(values=cur_vals)
                    self.target_window_cb.set(display_str)
                    self.target_lock_status_lbl.configure(
                        text=f"Trạng thái: 🔒 ĐÃ KHÓA NỀN [{proc_name}] {title[:25]} - Cách ly 100% không ảnh hưởng app khác",
                        fg="#34d399"
                    )
                    self.show_toast("Đã Khóa Cửa Sổ", f"Đã khóa chặt vào [{proc_name}] {title}!\n100% phím & chuột chỉ gửi vào ứng dụng này.", "success")
                else:
                    self.show_toast("Chưa Nhận Diện", "Không nhận diện được cửa sổ được click. Vui lòng thử lại!", "warning")
            try:
                self.after(0, _ui)
            except Exception:
                pass

        ZaloAutomation.pick_window_1click(_on_picked)

    def _refresh_target_windows_list(self):
        """Quét lại toàn bộ danh sách cửa sổ đang mở trên Windows."""
        def _scan():
            wins = ZaloAutomation.scan_active_windows()
            self._target_windows_cache = wins
            combo_vals = [w[1] for w in wins]
            
            def _apply():
                if combo_vals:
                    self.target_window_cb.configure(values=combo_vals)
                    cur_val = self.target_window_cb.get().strip()
                    if not cur_val or cur_val.startswith("(") or cur_val not in combo_vals:
                        # Tìm cửa sổ Zalo hoặc Remote App thực sự (TUYỆT ĐỐI KHÔNG tự động khóa IDE/Code)
                        def is_valid_target(w):
                            n = (w[2] + " " + w[3]).lower()
                            return any(k in n for k in ["zalo", "ultraviewer", "anydesk", "teamviewer", "remote desktop", "mstsc"])

                        target_win = next((w for w in wins if is_valid_target(w)), None)

                        if target_win:
                            self.target_window_cb.set(target_win[1])
                            ZaloAutomation.set_target_window(target_win[0], target_win[0], target_win[2], target_win[3], enabled=True)
                            self.target_lock_status_lbl.configure(
                                text=f"Trạng thái: 🔒 ĐÃ KHÓA NỀN [{target_win[2]}] {target_win[3][:25]} - Cách ly 100% không ảnh hưởng app khác",
                                fg="#34d399"
                            )
                        else:
                            # Không có Zalo / Remote app nào đang mở: Để trạng thái chờ, KHÔNG khóa bừa IDE
                            self.target_window_cb.set("(Chưa phát hiện Zalo PC / UltraViewer - Hãy mở Zalo)")
                            ZaloAutomation.set_target_window(None, None, "", "", enabled=False)
                            self.target_lock_status_lbl.configure(
                                text="Trạng thái: ⚠️ Chưa mở Zalo PC / UltraViewer (Hãy mở Zalo hoặc chọn từ danh sách)",
                                fg="#fbbf24"
                            )
                else:
                    self.target_window_cb.configure(values=["(Không tìm thấy cửa sổ nào)"])
                    self.target_window_cb.set("(Không tìm thấy cửa sổ nào)")
                    ZaloAutomation.set_target_window(None, None, "", "", enabled=False)
                    self.target_lock_status_lbl.configure(
                        text="Trạng thái: ⚠️ Chưa tìm thấy cửa sổ Zalo nào",
                        fg="#94a3b8"
                    )
            try:
                self.after(0, _apply)
            except Exception:
                pass

        threading.Thread(target=_scan, daemon=True).start()

    def _on_target_window_combo_selected(self, event=None):
        """Xử lý khi người dùng chọn 1 cửa sổ từ dropdown danh sách."""
        selected_str = self.target_window_cb.get().strip()
        cache = getattr(self, '_target_windows_cache', [])
        for hwnd, d_str, p_name, t_str in cache:
            if d_str == selected_str:
                ZaloAutomation.set_target_window(hwnd, hwnd, p_name, t_str, enabled=True)
                self.target_window_enabled_var.set(True)
                self.target_lock_status_lbl.configure(
                    text=f"Trạng thái: 🔒 ĐÃ KHÓA NỀN [{p_name}] {t_str[:25]} - Cách ly 100% không ảnh hưởng app khác",
                    fg="#34d399"
                )
                self.show_toast("Đã Khóa Ứng Dụng", f"Đã khóa chặt vào [{p_name}] {t_str}!", "success")
                break

    def _test_target_key_press(self):
        """Gửi thử 1 phím ngầm (Space) vào ứng dụng đích để kiểm tra kết nối."""
        ok = ZaloAutomation.test_single_background_key()
        target = ZaloAutomation.get_target_window()
        p_name = target.get("proc_name", "Zalo")
        if ok:
            self.show_toast("Thử Phím Ngầm", f"✅ Đã gửi phím ngầm (Space) thành công vào [{p_name}]!", "success")
        else:
            self.show_toast("Lỗi Gửi Phím", f"⚠️ Không gửi được phím ngầm vào [{p_name}]. Hãy kiểm tra ứng dụng đang mở!", "warning")

    def _extract_targets_from_zalo_tag_dialog(self):
        """
        Mở hộp thoại hỗ trợ quét và tự động trích xuất toàn bộ Tên Nhóm / Tên Người
        đang thuộc một Thẻ phân loại trên Zalo PC.
        """
        modal = tk.Toplevel(self)
        modal.title("📥 Quét & Trích Xuất Danh Sách Tên Nhóm Từ Thẻ Zalo")
        modal.geometry("480x280")
        modal.minsize(440, 260)
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()
        apply_windows_dark_titlebar(modal, "#0f172a", "#f8fafc")

        hdr = tk.Frame(modal, bg="#1e293b", padx=14, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍 TỰ ĐỘNG LẤY TOÀN BỘ TÊN NHÓM / NGƯỜI DÙNG TỪ THẺ ZALO", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")

        body = tk.Frame(modal, bg="#0f172a", padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Chọn Thẻ phân loại Zalo cần quét:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w", pady=(0, 4))
        
        tags = self.state.get_all_tags()
        current_tag = self.bc_tag_cb.get().strip() or (tags[0] if tags else "Gửi mẫu quảng cáo")
        tag_cb = ttk.Combobox(body, values=tags, font=("Segoe UI", 9), state="readonly")
        tag_cb.set(current_tag)
        tag_cb.pack(fill="x", pady=(0, 10))

        row_opt = tk.Frame(body, bg="#0f172a")
        row_opt.pack(fill="x", pady=(0, 10))

        tk.Label(row_opt, text="Số lần cuộn quét tối đa:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(side="left")
        scroll_var = tk.IntVar(value=4)
        sp_scroll = tk.Spinbox(row_opt, from_=1, to=15, textvariable=scroll_var, width=4, font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#34d399")
        sp_scroll.pack(side="left", padx=6)
        tk.Label(row_opt, text="trang (khoảng 10-40 nhóm)", font=("Segoe UI", 8, "italic"), fg="#64748b", bg="#0f172a").pack(side="left")

        status_lbl = tk.Label(body, text="💡 Nhấn 'Bắt Đầu Quét' để bot tự động đọc và lấy toàn bộ tên nhóm trên Zalo PC.", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a", wraplength=440, justify="left")
        status_lbl.pack(fill="x", pady=(0, 10))

        btn_bar = tk.Frame(body, bg="#0f172a")
        btn_bar.pack(fill="x", pady=(5, 0))

        def _safe_update_status(text_val, color_val="#fbbf24"):
            def _ui():
                try:
                    if status_lbl.winfo_exists():
                        status_lbl.configure(text=text_val, fg=color_val)
                except Exception:
                    pass
            self.after(0, _ui)

        def _do_scan():
            sel_tag = tag_cb.get().strip()
            max_s = int(scroll_var.get())
            if not sel_tag:
                self.show_toast("Chưa Chọn Thẻ", "Vui lòng chọn Thẻ Zalo cần quét!", "warning")
                return

            _safe_update_status(f"⏳ Đang kích hoạt Zalo PC và đọc danh sách nhóm trong Thẻ '{sel_tag}'...", "#fbbf24")
            self.set_footer_task(f"Đang quét danh sách nhóm từ Thẻ '{sel_tag}'...")

            def _worker():
                try:
                    names = ZaloAutomation.extract_target_names_from_tag(
                        tag_name=sel_tag,
                        gemini_engine=self.gemini,
                        max_scrolls=max_s,
                        progress_callback=lambda st: _safe_update_status(f"⏳ {st}", "#fbbf24")
                    )

                    def _on_finish():
                        try:
                            if not names:
                                _safe_update_status("⚠️ Không trích xuất được tên nhóm nào. Vui lòng kiểm tra lại Zalo PC!", "#f87171")
                                self.show_toast("Không Tìm Thấy", "Không trích xuất được tên nhóm nào từ Thẻ này!", "warning")
                                return

                            existing_text = self.target_names_txt.get("1.0", tk.END).strip()
                            existing_list = [x.strip() for x in existing_text.splitlines() if x.strip()]
                            
                            combined = list(dict.fromkeys(existing_list + names))
                            
                            self.target_names_txt.delete("1.0", tk.END)
                            self.target_names_txt.insert("1.0", "\n".join(combined))
                            self._save_custom_targets_to_file()
                            self._update_target_count_badge()
                            self.set_footer_task(f"Đã trích xuất thành công {len(names)} tên nhóm từ Thẻ '{sel_tag}'.")
                            self.show_toast("Quét Thành Công", f"Đã lấy thành công {len(names)} tên nhóm từ Thẻ '{sel_tag}'!", "success")
                            if modal.winfo_exists():
                                modal.destroy()
                        except Exception as ex:
                            logger.warning(f"[Tag Scanner] Lỗi cập nhật giao diện: {ex}")

                    self.after(0, _on_finish)
                except Exception as e:
                    def _on_err():
                        _safe_update_status(f"❌ Lỗi: {e}", "#f87171")
                        self.show_toast("Lỗi Quét", f"Đã xảy ra lỗi khi quét: {e}", "error")
                    self.after(0, _on_err)

            threading.Thread(target=_worker, daemon=True).start()

        btn_run = tk.Button(btn_bar, text="🚀 Bắt Đầu Quét Tên Từ Zalo", bg="#8b5cf6", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=5, cursor="hand2", command=_do_scan)
        btn_run.pack(side="left")

        btn_cancel = tk.Button(btn_bar, text="Đóng", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2", command=modal.destroy)
        btn_cancel.pack(side="right")


    def _load_quick_links(self) -> Dict[str, List[Dict[str, Any]]]:
        """Tải danh sách link các khối từ file JSON hoặc khởi tạo mặc định nếu chưa có."""
        path = get_storage_path("quick_links.json")
        data = copy.deepcopy(DEFAULT_QUICK_LINKS)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        for g in QUICK_LINK_GRADES:
                            if g in saved and isinstance(saved[g], list):
                                data[g] = saved[g]
            except Exception as e:
                logger.error(f"[Quick Links Load Error] Lỗi đọc {path}: {e}")
        return data

    def _save_quick_links_to_file(self):
        """Lưu danh sách link các khối vào file JSON bền vững."""
        path = get_storage_path("quick_links.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.quick_links_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[Quick Links Save Error] Lỗi lưu {path}: {e}")

    def _get_checked_quick_links_formatted(self) -> str:
        """
        Lấy danh sách tất cả các link đang được tích chọn trên tất cả các khối,
        định dạng mỗi link 1 dòng.
        Tùy chọn kèm nhãn ghi chú phía trước hoặc chỉ gửi link trần.
        """
        include_label = self.quick_links_include_label_var.get() if hasattr(self, 'quick_links_include_label_var') else True
        lines = []
        for grade in QUICK_LINK_GRADES:
            items = getattr(self, "quick_links_data", {}).get(grade, [])
            for it in items:
                if it.get("checked", False):
                    url = it.get("url", "").strip()
                    name = it.get("name", "").strip()
                    if url:
                        if include_label:
                            lines.append(f"[{grade} - {name}]: {url}")
                        else:
                            lines.append(url)
        return "\n".join(lines)

    def _get_checked_quick_links_count(self) -> int:
        """Đếm tổng số link đang được tích chọn trên tất cả các khối."""
        count = 0
        for grade in QUICK_LINK_GRADES:
            items = getattr(self, "quick_links_data", {}).get(grade, [])
            for it in items:
                if it.get("checked", False):
                    count += 1
        return count

    def _update_quick_links_badge(self):
        """Cập nhật badge đếm số link đang tích chọn."""
        total = self._get_checked_quick_links_count()
        if hasattr(self, 'lbl_links_checked_count') and self.lbl_links_checked_count.winfo_exists():
            self.lbl_links_checked_count.configure(text=f"✨ Đang tích: {total} link")
        if hasattr(self, 'lbl_script_links_count_summary') and self.lbl_script_links_count_summary.winfo_exists():
            self.lbl_script_links_count_summary.configure(
                text=f"🔗 Đính kèm: {total} link khối" if total > 0 else "🔗 Đính kèm: 0 link khối"
            )

    # =========================================================================
    # TAB 10: ⚙️ CÀI ĐẶT ỨNG DỤNG, VỊ TRÍ CỬA SỔ & GIAO DIỆN SÁNG/TỐI
    # =========================================================================
    def _switch_to_settings_tab(self):
        """Chuyển nhanh đến Tab Cài Đặt."""
        self._switch_main_tab("settings")

    def _get_settings_filepath(self) -> str:
        return get_storage_path("app_settings.json")

    def _load_app_settings(self) -> Dict[str, Any]:
        p = self._get_settings_filepath()
        defaults = {
            "window_position": "right_half",
            "theme": "slate_dark",
            "font_size": "normal",
            "script_send_mode": "Gửi Ngay Vào Zalo (Enter)",
            "always_on_top": False,
            "default_speed": "Siêu Chậm (Mặc Định)",
            "delay_min": 15,
            "delay_max": 50,
            "max_retries": 5,
            "toast_duration_sec": 3.5,
            "toast_position": "bottom_right",
            "hide_models_below_3_1": True,
            "min_gemini_version": "⭐ Chỉ lấy Gemini 3.1 trở lên (>= 3.1) [Mặc Định - Khuyên Dùng]",
            "auto_target_lock": True,
            "anti_spam_time": True,
            "anti_spam_code": True,
            "anti_spam_icon": False,
            "target_allowed_keywords": "zalo, ultraviewer, anydesk, teamviewer, remote desktop, mstsc",
            "target_exclusion_keywords": "antigravity, cursor, vscode, code.exe, pycharm, powershell, cmd.exe, windowsterminal, laragon",
            "require_login": True,
            "script_tab_layout": "3_columns",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "telegram_auto_send_backup": True,
            "float_idle_alpha": 0.35,
            "enable_2fa": False,
            "security_pin_2fa": "123456"
        }
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                logger.warning(f"[Settings] Lỗi đọc app_settings.json: {e}")

        # Đồng bộ từ khóa khóa đích & loại trừ vào module ZaloAutomation
        ZaloAutomation.set_target_keywords(
            defaults.get("target_allowed_keywords", "zalo, ultraviewer, anydesk, teamviewer, remote desktop, mstsc"),
            defaults.get("target_exclusion_keywords", "antigravity, cursor, vscode, code.exe, pycharm, powershell, cmd.exe, windowsterminal, laragon")
        )
        return defaults

    def _save_app_settings_to_file(self, settings_dict: Dict[str, Any]):
        p = self._get_settings_filepath()
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[Settings] Lỗi lưu app_settings.json: {e}")

    _save_app_settings = _save_app_settings_to_file

    def _apply_saved_window_geometry(self, pos_key: Optional[str] = None):
        """Áp dụng vị trí & kích thước cửa sổ khởi động."""
        if not pos_key:
            settings = self._load_app_settings()
            pos_key = settings.get("window_position", "right_half")
        
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            
            if pos_key == "right_half":
                win_w = max(680, screen_w // 2)
                win_h = max(600, screen_h - 40)
                win_x = screen_w - win_w
                win_y = 0
                self.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
            elif pos_key == "left_half":
                win_w = max(680, screen_w // 2)
                win_h = max(600, screen_h - 40)
                win_x = 0
                win_y = 0
                self.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
            elif pos_key == "maximized":
                self.state('zoomed')
            elif pos_key == "center":
                win_w = min(1200, screen_w - 60)
                win_h = min(750, screen_h - 80)
                win_x = (screen_w - win_w) // 2
                win_y = max(0, (screen_h - win_h - 40) // 2)
                self.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
        except Exception as e:
            logger.warning(f"[Settings] Lỗi gán geometry cửa sổ: {e}")
            self.geometry("1200x750")

    def _build_settings_tab(self, parent):
        """Xây dựng giao diện Tab 10: Cài Đặt Ứng Dụng Toàn Diện với thanh cuộn tự động ẩn/hiện thông minh."""
        # Khung chứa cuộn thông minh (Chỉ hiện thanh cuộn khi nội dung dài hơn màn hình)
        container = tk.Frame(parent, bg="#0f172a")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="#0f172a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        content_frame = tk.Frame(canvas, bg="#0f172a")
        canvas_win = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        def _update_scroll_visibility(event=None):
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            canvas.configure(scrollregion=bbox)
            content_h = bbox[3] - bbox[1]
            canvas_h = canvas.winfo_height()

            # Chỉ hiện thanh cuộn khi nội dung thực tế dài hơn chiều cao canvas
            if content_h > canvas_h and canvas_h > 120:
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_win, width=event.width)
            _update_scroll_visibility()

        canvas.bind("<Configure>", _on_canvas_configure)
        content_frame.bind("<Configure>", _update_scroll_visibility)

        # Hỗ trợ lăn chuột mượt mà khi hover vào khu vực Cài Đặt
        def _on_mousewheel(event):
            try:
                canvas_h = canvas.winfo_height()
                bbox = canvas.bbox("all")
                if bbox and (bbox[3] - bbox[1]) > canvas_h:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _bind_mousewheel(event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event=None):
            canvas.unbind_all("<MouseWheel>")

        container.bind("<Enter>", _bind_mousewheel)
        container.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)

        # Bố cục 2 Cột chia đôi 50/50 hoàn hảo (1:1 Ratio)
        content_frame.grid_columnconfigure(0, weight=1, uniform="settings_col")
        content_frame.grid_columnconfigure(1, weight=1, uniform="settings_col")

        left_col = tk.Frame(content_frame, bg="#0f172a", padx=8, pady=8)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        right_col = tk.Frame(content_frame, bg="#0f172a", padx=8, pady=8)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        saved = self._load_app_settings()

        # =========================================================================
        # CARD 1: 🖥️ VỊ TRÍ & KÍCH THƯỚC CỬA SỔ KHỞI ĐỘNG (THEO YÊU CẦU)
        # =========================================================================
        card_pos = tk.LabelFrame(
            left_col,
            text=" 🖥️ VỊ TRÍ & KÍCH THƯỚC CỬA SỔ KHỞI ĐỘNG (WINDOW GEOMETRY) ",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_pos.pack(fill="x", pady=(0, 10))

        self.setting_win_pos_var = tk.StringVar(value=saved.get("window_position", "right_half"))

        pos_options = [
            ("right_half", "📌 Nửa Phải Màn Hình (Mặc Định Khuyên Dùng)", "Chiếm 1/2 chiều rộng bên phải màn hình, 100% full chiều cao (trừ Taskbar).\nThuận tiện mở Zalo / tài liệu bên trái và thao tác app bên phải."),
            ("left_half", "📌 Nửa Trái Màn Hình", "Chiếm 1/2 chiều rộng bên trái màn hình, 100% full chiều cao (trừ Taskbar).\nThuận tiện mở Zalo / tài liệu bên phải."),
            ("maximized", "📌 Toàn Màn Hình (Maximized Fullscreen)", "Mở cực đại toàn bộ màn hình khi khởi động."),
            ("center", "📌 Chính Giữa Màn Hình (Center 1200x750)", "Mở cửa sổ kích thước tiêu chuẩn 1200x750 nằm ngay giữa màn hình.")
        ]

        for val, title, desc in pos_options:
            rf = tk.Frame(card_pos, bg="#0f172a")
            rf.pack(fill="x", pady=3)
            rb = tk.Radiobutton(
                rf,
                text=title,
                value=val,
                variable=self.setting_win_pos_var,
                bg="#0f172a",
                fg="#f8fafc",
                selectcolor="#1e293b",
                activebackground="#0f172a",
                font=("Segoe UI", 9, "bold")
            )
            rb.pack(anchor="w")
            tk.Label(rf, text=desc, font=("Segoe UI", 8, "italic"), fg="#94a3b8", bg="#0f172a", justify="left").pack(anchor="w", padx=(24, 0))

        pos_act = tk.Frame(card_pos, bg="#0f172a")
        pos_act.pack(fill="x", pady=(8, 2))
        btn_apply_pos = tk.Button(
            pos_act,
            text="🎯 Thử Áp Dụng Vị Trí Này Ngay",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self._apply_saved_window_geometry(self.setting_win_pos_var.get())
        )
        btn_apply_pos.pack(side="left")

        # =========================================================================
        # CARD 1.5: 🔐 BẢO MẬT & QUẢN LÝ TÀI KHOẢN ĐĂNG NHẬP (AUTH & USERS)
        # =========================================================================
        card_auth = tk.LabelFrame(
            left_col,
            text=" 🔐 BẢO MẬT & QUẢN LÝ TÀI KHOẢN ĐĂNG NHẬP (AUTH & USERS) ",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_auth.pack(fill="x", pady=(0, 6))

        # Checkbox yêu cầu đăng nhập khi mở app
        self.setting_require_login_var = tk.BooleanVar(value=saved.get("require_login", True))
        chk_req_login = tk.Checkbutton(
            card_auth,
            text="🔐 Bắt buộc Đăng Nhập khi mở ứng dụng (Mặc định BẬT)",
            variable=self.setting_require_login_var,
            bg="#0f172a",
            fg="#f8fafc",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 9, "bold")
        )
        chk_req_login.pack(anchor="w")
        tk.Label(
            card_auth,
            text="💡 Nếu BỎ TÍCH, ứng dụng sẽ vào thẳng Dashboard mà không yêu cầu nhập mật khẩu.",
            font=("Segoe UI", 8, "italic"),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor="w", padx=(24, 0), pady=(0, 4))

        # Khung Cấu hình Xác Thực 2 Bước (2FA / Mã PIN)
        f_2fa_box = tk.Frame(card_auth, bg="#1e293b", padx=8, pady=6, highlightbackground="#38bdf8", highlightthickness=1)
        f_2fa_box.pack(fill="x", pady=(2, 6))

        self.setting_enable_2fa_var = tk.BooleanVar(value=saved.get("enable_2fa", False))
        chk_enable_2fa = tk.Checkbutton(
            f_2fa_box,
            text="🛡️ Kích hoạt Xác Thực 2 Bước (2FA / Mã PIN 2 Bước)",
            variable=self.setting_enable_2fa_var,
            bg="#1e293b",
            fg="#38bdf8",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            font=("Segoe UI", 9, "bold")
        )
        chk_enable_2fa.pack(anchor="w")

        row_pin = tk.Frame(f_2fa_box, bg="#1e293b")
        row_pin.pack(fill="x", pady=(3, 2))

        tk.Label(row_pin, text="Mã PIN 2FA (4-8 số):", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#1e293b").pack(side="left")

        self.setting_2fa_pin_entry = tk.Entry(row_pin, font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#34d399", insertbackground="white", width=12, show="*")
        self.setting_2fa_pin_entry.pack(side="left", padx=6)
        self.setting_2fa_pin_entry.insert(0, str(saved.get("security_pin_2fa", "123456")))

        self.show_setting_2fa_var = tk.BooleanVar(value=False)
        def _toggle_show_setting_2fa():
            if self.show_setting_2fa_var.get():
                self.setting_2fa_pin_entry.configure(show="")
            else:
                self.setting_2fa_pin_entry.configure(show="*")

        tk.Checkbutton(
            row_pin,
            text="👁️ Hiện PIN",
            variable=self.show_setting_2fa_var,
            command=_toggle_show_setting_2fa,
            bg="#1e293b",
            fg="#94a3b8",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            font=("Segoe UI", 8)
        ).pack(side="left", padx=2)

        tk.Label(
            f_2fa_box,
            text="💡 Khi BẬT 2FA, sau khi nhập đúng tài khoản & mật khẩu, người dùng bắt buộc nhập đúng Mã PIN này (hoặc mã OTP 6 số) mới có thể vào hệ thống.",
            font=("Segoe UI", 7, "italic"),
            fg="#94a3b8",
            bg="#1e293b",
            justify="left",
            wraplength=480
        ).pack(anchor="w", pady=(2, 0))

        # Toolbar hành động quản lý tài khoản
        auth_tb = tk.Frame(card_auth, bg="#0f172a")
        auth_tb.pack(fill="x", pady=(2, 4))

        btn_add_user = tk.Button(
            auth_tb,
            text="➕ Thêm User",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_create_user_modal
        )
        btn_add_user.pack(side="left", padx=(0, 4))

        btn_edit_user = tk.Button(
            auth_tb,
            text="✏️ Sửa User",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_edit_user_modal
        )
        btn_edit_user.pack(side="left", padx=4)

        btn_chg_pwd = tk.Button(
            auth_tb,
            text="🔑 Đổi Pass",
            bg="#334155",
            fg="#f8fafc",
            font=("Segoe UI", 8),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._change_selected_user_password
        )
        btn_chg_pwd.pack(side="left", padx=4)

        btn_logs = tk.Button(
            auth_tb,
            text="📜 Lịch Sử ĐN",
            bg="#7c3aed",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._open_login_logs_modal
        )
        btn_logs.pack(side="left", padx=4)

        btn_del_user = tk.Button(
            auth_tb,
            text="🗑️ Xóa User",
            bg="#475569",
            fg="#fca5a5",
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._delete_selected_user
        )
        btn_del_user.pack(side="right", padx=2)

        # Bảng danh sách tài khoản
        user_cols = ("username", "fullname", "role", "login_count", "last_login_at", "created_at")
        self.users_tree = ttk.Treeview(card_auth, columns=user_cols, show="headings", height=4, selectmode="browse")
        self.users_tree.heading("username", text="Tên ĐN")
        self.users_tree.heading("fullname", text="Tên Hiển Thị")
        self.users_tree.heading("role", text="Vai Trò")
        self.users_tree.heading("login_count", text="Lần ĐN")
        self.users_tree.heading("last_login_at", text="ĐN Cuối")
        self.users_tree.heading("created_at", text="Ngày Tạo")

        self.users_tree.column("username", width=65, stretch=True)
        self.users_tree.column("fullname", width=90, stretch=True)
        self.users_tree.column("role", width=50, anchor="center", stretch=True)
        self.users_tree.column("login_count", width=45, anchor="center", stretch=True)
        self.users_tree.column("last_login_at", width=90, anchor="center", stretch=True)
        self.users_tree.column("created_at", width=75, anchor="center", stretch=True)
        self.users_tree.pack(fill="x", pady=(2, 2))

        # Nút xóa thông tin đăng nhập đã lưu
        auth_bot_row = tk.Frame(card_auth, bg="#0f172a")
        auth_bot_row.pack(fill="x", pady=(4, 0))

        btn_clr_saved_creds = tk.Button(
            auth_bot_row,
            text="🧹 Bỏ Lưu Thông Tin Đăng Nhập Trên Máy (Forget Saved Login)",
            bg="#1e293b",
            fg="#fca5a5",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._clear_saved_login_credentials_from_settings
        )
        btn_clr_saved_creds.pack(side="left")

        self._refresh_users_tree()

        # =========================================================================
        # CARD 2: 🎨 CÀI ĐẶT GIAO DIỆN SÁNG / TỐI (THEME & APPEARANCE)
        # =========================================================================
        card_theme = tk.LabelFrame(
            left_col,
            text=" 🎨 CÀI ĐẶT GIAO DIỆN SÁNG / TỐI (THEME & APPEARANCE) ",
            font=("Segoe UI", 9, "bold"),
            fg="#f59e0b",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_theme.pack(fill="x", pady=(0, 6))

        self.setting_theme_var = tk.StringVar(value=saved.get("theme", "tailwind_light"))

        themes = [
            ("tailwind_light", "✨ Tailwind CSS Sáng (Modern Tailwind Light - Khuyên Dùng)", "Màu nền Slate-50 & Trắng tinh khiết, viền Slate-200, điểm nhấn Indigo & Emerald cực kỳ sắc nét."),
            ("tailwind_dark", "🌌 Tailwind CSS Tối (Modern Tailwind Dark)", "Màu nền Zinc-950 & 900 huyền bí, viền Zinc-800, điểm nhấn Violet & Cyan công nghệ cao."),
            ("light_theme", "☀️ Giao Diện Sáng Tiêu Chuẩn (Light Elegance Theme)", "Màu nền xám sáng thanh lịch, chữ đen đậm, đọc rõ ban ngày."),
            ("slate_dark", "🌙 Tối Slate Hiện Đại (Dark Slate)", "Màu nền đen xám Tailwind Slate 950 dịu mắt, chống mỏi mắt."),
            ("midnight_black", "🌑 Đen Huyền Bí (Midnight OLED Black)", "Màu nền đen tuyền sang trọng, tiết kiệm điện màn hình OLED."),
            ("ocean_blue", "🌊 Xanh Biển Sâu (Ocean Deep Blue)", "Màu nền xanh Navy công nghệ hiện đại, phối màu sắc nét.")
        ]

        for val, title, desc in themes:
            tf = tk.Frame(card_theme, bg="#0f172a")
            tf.pack(fill="x", pady=3)
            rb = tk.Radiobutton(
                tf,
                text=title,
                value=val,
                variable=self.setting_theme_var,
                bg="#0f172a",
                fg="#f8fafc",
                selectcolor="#1e293b",
                activebackground="#0f172a",
                font=("Segoe UI", 9, "bold")
            )
            rb.pack(anchor="w")
            tk.Label(tf, text=desc, font=("Segoe UI", 8, "italic"), fg="#94a3b8", bg="#0f172a", justify="left").pack(anchor="w", padx=(24, 0))

        theme_act = tk.Frame(card_theme, bg="#0f172a")
        theme_act.pack(fill="x", pady=(8, 2))
        btn_apply_theme = tk.Button(
            theme_act,
            text="🎨 Áp Dụng Theme Ngay",
            bg="#d97706",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self._apply_theme(self.setting_theme_var.get())
        )
        btn_apply_theme.pack(side="left")

        # =========================================================================
        # CARD 2.5: 🎯 DANH SÁCH KHÓA ĐÍCH & LOẠI TRỪ (TARGET & EXCLUSION KEYWORDS)
        # =========================================================================
        card_keywords = tk.LabelFrame(
            left_col,
            text=" 🎯 DANH SÁCH TỪ KHÓA KHÓA ĐÍCH & LOẠI TRỪ ",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_keywords.pack(fill="x", pady=(0, 10))

        tk.Label(
            card_keywords,
            text="✅ Danh sách từ khóa CHO PHÉP KHÓA & ƯU TIÊN (cách nhau bằng dấu phẩy):",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#0f172a"
        ).pack(anchor="w", pady=(2, 2))
        
        self.setting_allowed_kw_entry = tk.Entry(card_keywords, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.setting_allowed_kw_entry.pack(fill="x", pady=(0, 6))
        self.setting_allowed_kw_entry.insert(0, saved.get("target_allowed_keywords", "zalo, ultraviewer, anydesk, teamviewer, remote desktop, mstsc"))

        tk.Label(
            card_keywords,
            text="🚫 Danh sách từ khóa TUYỆT ĐỐI LOẠI TRỪ / BLACKLIST (cách nhau bằng dấu phẩy):",
            font=("Segoe UI", 8, "bold"),
            fg="#f87171",
            bg="#0f172a"
        ).pack(anchor="w", pady=(2, 2))
        
        self.setting_exclusion_kw_entry = tk.Entry(card_keywords, font=("Segoe UI", 9), bg="#1e293b", fg="#fca5a5", insertbackground="white")
        self.setting_exclusion_kw_entry.pack(fill="x", pady=(0, 6))
        self.setting_exclusion_kw_entry.insert(0, saved.get("target_exclusion_keywords", "antigravity, cursor, vscode, code.exe, pycharm, powershell, cmd.exe, windowsterminal, laragon"))

        kw_act_bar = tk.Frame(card_keywords, bg="#0f172a")
        kw_act_bar.pack(fill="x", pady=(2, 0))

        btn_reset_kw = tk.Button(
            kw_act_bar,
            text="🔄 Nạp Từ Khóa Mặc Định",
            bg="#334155",
            fg="#cbd5e1",
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._reset_target_keywords_ui
        )
        btn_reset_kw.pack(side="left")

        btn_scan_now = tk.Button(
            kw_act_bar,
            text="🔍 Áp Dụng & Quét Lại Cửa Sổ",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._apply_and_test_keywords_now
        )
        btn_scan_now.pack(side="right")

        # =========================================================================
        # CARD 3: ⚡ THÔNG SỐ HOẠT ĐỘNG HỆ THỐNG & ĐƯỜNG DẪN DỮ LIỆU
        # =========================================================================
        card_sys = tk.LabelFrame(
            right_col,
            text=" ⚡ THÔNG SỐ HOẠT ĐỘNG HỆ THỐNG & ĐƯỜNG DẪN ",
            font=("Segoe UI", 9, "bold"),
            fg="#34d399",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_sys.pack(fill="x", pady=(0, 10))

        # Tốc độ gửi tin mặc định
        row_s = tk.Frame(card_sys, bg="#0f172a")
        row_s.pack(fill="x", pady=3)
        tk.Label(row_s, text="Tốc độ gửi tin mặc định khi khởi động:", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        self.setting_speed_cb = ttk.Combobox(
            row_s,
            values=[
                "Siêu Nhanh (1-3s)",
                "Nhanh (2-5s)",
                "Vừa (4-8s)",
                "Hơi Chậm (6-20s)",
                "Chậm (10-30s)",
                "Siêu Chậm (Mặc Định) (15-50s)",
                "Cực Chậm (30-90s)"
            ],
            state="readonly"
        )
        self.setting_speed_cb.set(saved.get("default_speed", "Siêu Chậm (Mặc Định)"))
        self.setting_speed_cb.pack(fill="x", pady=(2, 4))

        # CÀI ĐẶT: THỜI GIAN HIỂN THỊ TOAST NOTIFICATION
        row_toast = tk.Frame(card_sys, bg="#0f172a")
        row_toast.pack(fill="x", pady=3)
        tk.Label(row_toast, text="⏱️ Thời gian hiển thị thông báo Toast:", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        self.setting_toast_duration_cb = ttk.Combobox(
            row_toast,
            values=[
                "1.5 giây (Nhanh)",
                "2.5 giây",
                "3.5 giây (Tiêu Chuẩn)",
                "5.0 giây (Vừa)",
                "7.0 giây (Lâu)",
                "10.0 giây (Rất Lâu)"
            ],
            state="readonly"
        )
        cur_toast_sec = saved.get("toast_duration_sec", 3.5)
        toast_val_str = f"{cur_toast_sec} giây (Tiêu Chuẩn)" if cur_toast_sec == 3.5 else f"{cur_toast_sec} giây"
        for opt in self.setting_toast_duration_cb["values"]:
            if str(cur_toast_sec) in opt:
                toast_val_str = opt
                break
        self.setting_toast_duration_cb.set(toast_val_str)
        self.setting_toast_duration_cb.pack(fill="x", pady=(2, 4))

        # CÀI ĐẶT: VỊ TRÍ HIỂN THỊ TOAST NOTIFICATION
        row_toast_pos = tk.Frame(card_sys, bg="#0f172a")
        row_toast_pos.pack(fill="x", pady=3)
        tk.Label(row_toast_pos, text="📍 Vị trí hiển thị thông báo Toast:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        self.setting_toast_pos_cb = ttk.Combobox(
            row_toast_pos,
            values=[
                "↘️ Góc Phải Dưới Cùng (Mặc Định)",
                "↗️ Góc Phải Trên Cùng",
                "↙️ Góc Trái Dưới Cùng",
                "↖️ Góc Trái Trên Cùng",
                "⬇️ Giữa Màn Hình Phía Dưới"
            ],
            state="readonly"
        )
        cur_pos_key = saved.get("toast_position", "bottom_right")
        pos_map = {
            "bottom_right": "↘️ Góc Phải Dưới Cùng (Mặc Định)",
            "top_right": "↗️ Góc Phải Trên Cùng",
            "bottom_left": "↙️ Góc Trái Dưới Cùng",
            "top_left": "↖️ Góc Trái Trên Cùng",
            "bottom_center": "⬇️ Giữa Màn Hình Phía Dưới"
        }
        self.setting_toast_pos_cb.set(pos_map.get(cur_pos_key, "↘️ Góc Phải Dưới Cùng (Mặc Định)"))
        self.setting_toast_pos_cb.pack(fill="x", pady=(2, 4))

        # CÀI ĐẶT: PHẦN TRĂM ĐỘ MỜ CỦA THANH NỔI (FLOAT IDLE OPACITY)
        row_float_alpha = tk.Frame(card_sys, bg="#0f172a")
        row_float_alpha.pack(fill="x", pady=3)
        tk.Label(
            row_float_alpha,
            text="🪟 Phần trăm độ mờ của Thanh Nổi khi không kích hoạt (%):",
            font=("Segoe UI", 8, "bold"),
            fg="#c084fc",
            bg="#0f172a"
        ).pack(anchor="w")

        alpha_f = tk.Frame(row_float_alpha, bg="#0f172a")
        alpha_f.pack(fill="x", pady=(2, 4))

        self.setting_float_alpha_cb = ttk.Combobox(
            alpha_f,
            values=[
                "15% (Rất mờ - Trong suốt 85%)",
                "25% (Mờ nhiều - Trong suốt 75%)",
                "35% (Mờ vừa - Mặc Định - Khuyên Dùng)",
                "50% (Mờ 50% - Cân bằng)",
                "65% (Hơi mờ - Trong suốt 35%)",
                "80% (Rõ nét - Trong suốt 20%)",
                "100% (Không làm mờ - Sáng 100% liên tục)"
            ],
            state="readonly"
        )
        cur_alpha = int(round(float(saved.get("float_idle_alpha", 0.35)) * 100))
        alpha_val_str = "35% (Mờ vừa - Mặc Định - Khuyên Dùng)"
        for opt in self.setting_float_alpha_cb["values"]:
            if f"{cur_alpha}%" in opt:
                alpha_val_str = opt
                break
        self.setting_float_alpha_cb.set(alpha_val_str)
        self.setting_float_alpha_cb.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.setting_float_alpha_cb.bind("<<ComboboxSelected>>", self._on_float_alpha_combobox_selected)

        btn_test_alpha = tk.Button(
            alpha_f,
            text="👁️ Thử Mức Này",
            bg="#7c3aed",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._test_float_alpha_preview
        )
        btn_test_alpha.pack(side="right")

        # CÀI ĐẶT: BỘ LỌC PHIÊN BẢN MODEL GEMINI (ADMIN FILTER)
        row_mfilter = tk.Frame(card_sys, bg="#0f172a")
        row_mfilter.pack(fill="x", pady=3)
        tk.Label(row_mfilter, text="🎯 Bộ lọc phiên bản Model AI muốn lấy (Admin Filter):", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        self.setting_min_version_cb = ttk.Combobox(
            row_mfilter,
            values=GEMINI_VERSION_FILTER_OPTIONS,
            state="readonly"
        )
        cur_min_v = saved.get("min_gemini_version", GEMINI_VERSION_FILTER_OPTIONS[0])
        matched_v = GEMINI_VERSION_FILTER_OPTIONS[0]
        for opt in GEMINI_VERSION_FILTER_OPTIONS:
            if str(cur_min_v) in opt or opt in str(cur_min_v):
                matched_v = opt
                break
        self.setting_min_version_cb.set(matched_v)
        self.setting_min_version_cb.pack(fill="x", pady=(2, 4))
        self.setting_min_version_cb.bind("<<ComboboxSelected>>", self._on_min_version_combobox_toggled)

        self.setting_hide_below_3_1_var = tk.BooleanVar(value=saved.get("hide_models_below_3_1", True))
        chk_hide_3_1 = tk.Checkbutton(
            card_sys,
            text="🤖 Tự động ẩn các model Gemini thế hệ cũ dưới 3.1 (Ẩn 1.0, 1.5, 2.0...)",
            variable=self.setting_hide_below_3_1_var,
            bg="#0f172a", fg="#38bdf8", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8, "bold"),
            command=self._on_hide_below_3_1_toggled
        )
        chk_hide_3_1.pack(anchor="w", pady=3)

        # Hành động gửi kịch bản mẫu
        row_sm = tk.Frame(card_sys, bg="#0f172a")
        row_sm.pack(fill="x", pady=3)
        tk.Label(row_sm, text="Khi chọn mẫu kịch bản & nhấn Enter / Bấm đúp:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        self.setting_script_send_mode_cb = ttk.Combobox(
            row_sm,
            values=[
                "Gửi Ngay Vào Zalo (Enter)",
                "Chèn Nháp Vào Ô Chat (Draft Mode)"
            ],
            state="readonly"
        )
        self.setting_script_send_mode_cb.set(saved.get("script_send_mode", "Gửi Ngay Vào Zalo (Enter)"))
        self.setting_script_send_mode_cb.pack(fill="x", pady=(2, 4))

        # Checkboxes tùy chọn tự động
        self.setting_auto_lock_var = tk.BooleanVar(value=saved.get("auto_target_lock", True))
        chk_lock = tk.Checkbutton(
            card_sys,
            text="🔒 Tự động bật Khóa Nền Cách Ly (Không cướp chuột/phím) khi mở app",
            variable=self.setting_auto_lock_var,
            bg="#0f172a", fg="#34d399", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8, "bold")
        )
        chk_lock.pack(anchor="w", pady=3)

        self.setting_anti_time_var = tk.BooleanVar(value=saved.get("anti_spam_time", True))
        chk_time = tk.Checkbutton(
            card_sys,
            text="⏰ Mặc định tự động chèn Giờ [HH:MM] vào đuôi tin nhắn (Chống spam)",
            variable=self.setting_anti_time_var,
            bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8)
        )
        chk_time.pack(anchor="w", pady=2)

        self.setting_anti_code_var = tk.BooleanVar(value=saved.get("anti_spam_code", True))
        chk_code = tk.Checkbutton(
            card_sys,
            text="🔢 Mặc định tự động chèn Mã Ngẫu Nhiên [#xxxx] vào tin nhắn (Chống spam)",
            variable=self.setting_anti_code_var,
            bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8)
        )
        chk_code.pack(anchor="w", pady=2)

        self.setting_always_on_top_var = tk.BooleanVar(value=saved.get("always_on_top", False))
        chk_top = tk.Checkbutton(
            card_sys,
            text="📌 Tự động ghim cửa sổ luôn nổi trên cùng khi mở app (Mặc định TẮT)",
            variable=self.setting_always_on_top_var,
            bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", activebackground="#0f172a",
            font=("Segoe UI", 8)
        )
        chk_top.pack(anchor="w", pady=2)

        # Tiện ích mở thư mục dữ liệu
        card_paths = tk.LabelFrame(
            right_col,
            text=" 📁 TRUY CẬP NHANH DỮ LIỆU & LOGS ỨNG DỤNG ",
            font=("Segoe UI", 9, "bold"),
            fg="#a78bfa",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_paths.pack(fill="x", pady=(0, 10))

        row_btns = tk.Frame(card_paths, bg="#0f172a")
        row_btns.pack(fill="x", pady=3)

        btn_open_log = tk.Button(
            row_btns,
            text="📄 Mở File Log (app.log)",
            bg="#334155",
            fg="#38bdf8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._open_log_file
        )
        btn_open_log.pack(side="left", padx=(0, 6))

        btn_open_storage = tk.Button(
            row_btns,
            text="📁 Mở Thư Mục Storage",
            bg="#334155",
            fg="#f8fafc",
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._open_storage_folder
        )
        btn_open_storage.pack(side="left")

        # =========================================================================
        # CARD 3.5: 🔤 CÀI ĐẶT CỠ CHỮ TO / NHỎ (FONT SIZE SCALING THEO YÊU CẦU)
        # =========================================================================
        card_font = tk.LabelFrame(
            right_col,
            text=" 🔤 CÀI ĐẶT CỠ CHỮ TO / NHỎ (FONT SIZE SCALING) ",
            font=("Segoe UI", 9, "bold"),
            fg="#c084fc",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_font.pack(fill="x", pady=(0, 10))

        self.setting_font_size_var = tk.StringVar(value=saved.get("font_size", "normal"))

        font_options = [
            ("small", "🔤 Nhỏ (Small - 8pt)", "Cỡ chữ nhỏ gọn, hiển thị tối đa nhiều thông tin trên màn hình bé."),
            ("semi_small", "🔤 Hơi Vừa (Semi-Small - 8.5pt)", "Cỡ chữ nhỏ vừa phải, thanh thoát."),
            ("normal", "🔤 Bình Thường (Normal - 9pt - Mặc Định)", "Cỡ chữ chuẩn sắc nét, cân đối hoàn hảo."),
            ("medium", "🔤 Vừa (Medium - 10pt)", "Cỡ chữ to vừa phải, đọc nội dung thoải mái hơn."),
            ("semi_large", "🔤 Hơi Lớn (Semi-Large - 11pt)", "Cỡ chữ to rõ ràng, mắt yếu hoặc ngồi xa nhìn rất rõ."),
            ("large", "🔤 Lớn (Large - 12pt)", "Cỡ chữ lớn nhất, cực kỳ rõ ràng, chống mỏi mắt tối đa.")
        ]

        for val, title, desc in font_options:
            ff = tk.Frame(card_font, bg="#0f172a")
            ff.pack(fill="x", pady=2)
            rb = tk.Radiobutton(
                ff,
                text=title,
                value=val,
                variable=self.setting_font_size_var,
                bg="#0f172a",
                fg="#f8fafc",
                selectcolor="#1e293b",
                activebackground="#0f172a",
                font=("Segoe UI", 9, "bold")
            )
            rb.pack(anchor="w")
            tk.Label(ff, text=desc, font=("Segoe UI", 8, "italic"), fg="#94a3b8", bg="#0f172a", justify="left").pack(anchor="w", padx=(24, 0))

        font_act = tk.Frame(card_font, bg="#0f172a")
        font_act.pack(fill="x", pady=(6, 2))
        btn_apply_font = tk.Button(
            font_act,
            text="🔤 Thử Áp Dụng Cỡ Chữ Này Ngay",
            bg="#9333ea",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self._apply_font_scale(self.setting_font_size_var.get())
        )
        btn_apply_font.pack(side="left")

        # =========================================================================
        # CARD 3.8: 🛡️ CÀI ĐẶT THỬ LẠI & DỪNG BẮT BUỘC KHI LỖI (FAIL-SAFE RETRY)
        # =========================================================================
        card_retry = tk.LabelFrame(
            right_col,
            text=" 🛡️ CÀI ĐẶT THỬ LẠI & DỪNG BẮT BUỘC KHI LỖI (RETRY POLICY) ",
            font=("Segoe UI", 9, "bold"),
            fg="#f87171",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_retry.pack(fill="x", pady=(0, 10))

        row_ret = tk.Frame(card_retry, bg="#0f172a")
        row_ret.pack(fill="x", pady=2)
        tk.Label(row_ret, text="Số lần thử lại tối đa khi gửi lỗi (1 - 10 lần):", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left")
        self.setting_max_retries_sp = tk.Spinbox(row_ret, from_=1, to=10, width=5, font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", insertbackground="white", justify="center")
        self.setting_max_retries_sp.delete(0, tk.END)
        self.setting_max_retries_sp.insert(0, str(saved.get("max_retries", 5)))
        self.setting_max_retries_sp.pack(side="right")

        tk.Label(
            card_retry,
            text="💡 Nếu gửi ngầm hoặc kết nối Zalo / UltraViewer bị lỗi liên tiếp vượt quá số lần này,\nhệ thống sẽ BẮT BUỘC DỪNG LẠI (không chạy lặp vô tận) và thông báo lỗi rõ ràng.",
            font=("Segoe UI", 8, "italic"),
            fg="#94a3b8",
            bg="#0f172a",
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # =========================================================================
        # CARD 3.9: 💾 SAO LƯU, PHỤC HỒI TOÀN BỘ DỮ LIỆU & ĐỒNG BỘ TELEGRAM
        # =========================================================================
        card_backup = tk.LabelFrame(
            right_col,
            text=" 💾 SAO LƯU, PHỤC HỒI TOÀN BỘ DỮ LIỆU & ĐỒNG BỘ TELEGRAM ",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=10,
            pady=8
        )
        card_backup.pack(fill="x", pady=(0, 10))

        # Telegram Configuration Row 1: Bot Token (Secret Key)
        t_row1 = tk.Frame(card_backup, bg="#0f172a")
        t_row1.pack(fill="x", pady=2)
        tk.Label(t_row1, text="Telegram Bot Token:", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left")
        self.setting_telegram_token_entry = tk.Entry(t_row1, font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8", insertbackground="white")
        self.setting_telegram_token_entry.insert(0, saved.get("telegram_bot_token", ""))
        self.setting_telegram_token_entry.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Telegram Configuration Row 2: Chat ID
        t_row2 = tk.Frame(card_backup, bg="#0f172a")
        t_row2.pack(fill="x", pady=2)
        tk.Label(t_row2, text="Telegram Chat ID:", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(side="left")
        self.setting_telegram_chat_id_entry = tk.Entry(t_row2, font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8", insertbackground="white")
        self.setting_telegram_chat_id_entry.insert(0, saved.get("telegram_chat_id", ""))
        self.setting_telegram_chat_id_entry.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Checkbox: Tự động gửi file backup về Telegram khi xuất
        self.setting_telegram_auto_send_var = tk.BooleanVar(value=saved.get("telegram_auto_send_backup", True))
        chk_tg_auto = tk.Checkbutton(
            card_backup,
            text="⚡ Tự động gửi file backup về Telegram (không chuông) khi Xuất",
            variable=self.setting_telegram_auto_send_var,
            bg="#0f172a",
            fg="#f8fafc",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 8, "bold")
        )
        chk_tg_auto.pack(anchor="w", pady=(2, 6))

        # Cụm nút hành động Backup / Restore / Telegram
        btn_bk_row1 = tk.Frame(card_backup, bg="#0f172a")
        btn_bk_row1.pack(fill="x", pady=2)

        btn_export = tk.Button(
            btn_bk_row1,
            text="📤 Xuất Sao Lưu Toàn Bộ (Export)",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._do_export_backup_all
        )
        btn_export.pack(side="left", padx=(0, 3), expand=True, fill="x")

        btn_import = tk.Button(
            btn_bk_row1,
            text="📥 Nhập & Phục Hồi Dữ Liệu (Import)",
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._do_import_backup_all
        )
        btn_import.pack(side="right", padx=(3, 0), expand=True, fill="x")

        btn_bk_row2 = tk.Frame(card_backup, bg="#0f172a")
        btn_bk_row2.pack(fill="x", pady=(4, 2))

        btn_tg_test = tk.Button(
            btn_bk_row2,
            text="⚡ Test Kết Nối Telegram",
            bg="#334155",
            fg="#38bdf8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._do_test_telegram
        )
        btn_tg_test.pack(side="left", padx=(0, 3), expand=True, fill="x")

        btn_tg_send_now = tk.Button(
            btn_bk_row2,
            text="🚀 Gửi File Về Telegram Ngay",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._do_send_backup_to_telegram_now
        )
        btn_tg_send_now.pack(side="right", padx=(3, 0), expand=True, fill="x")

        tk.Label(
            card_backup,
            text="💡 Sao lưu 100% dữ liệu: Khách hàng CRM, Kịch bản, Sổ tay sửa giáo án, Tin nhóm, Lịch sử chat & Cài đặt.\nKhi xuất, tệp sẽ được lưu vào máy và tự động gửi về Telegram của bạn (âm thầm).",
            font=("Segoe UI", 8, "italic"),
            fg="#94a3b8",
            bg="#0f172a",
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # =========================================================================
        # CARD 4: 💾 HÀNH ĐỘNG CÀI ĐẶT
        # =========================================================================
        card_act = tk.Frame(right_col, bg="#1e293b", padx=10, pady=8)
        card_act.pack(fill="x", pady=(4, 0))

        btn_save_all = tk.Button(
            card_act,
            text="💾 LƯU CÀI ĐẶT LÀM MẶC ĐỊNH CHO MỌI LẦN KHỞI ĐỘNG",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._save_all_settings_from_ui
        )
        btn_save_all.pack(fill="x", pady=(0, 6))

        btn_reset_def = tk.Button(
            card_act,
            text="🔄 Khôi Phục Cài Đặt Gốc Ban Đầu",
            bg="#475569",
            fg="#fca5a5",
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._reset_settings_to_default
        )
        btn_reset_def.pack(fill="x")

    def _apply_font_scale(self, font_level: Optional[str] = None):
        """Thay đổi kích cỡ font chữ toàn bộ ứng dụng."""
        if not font_level:
            settings = self._load_app_settings()
            font_level = settings.get("font_size", "normal")

        font_map = {
            "small": {"base": 8, "delta": -1, "name": "Nhỏ (8pt)"},
            "semi_small": {"base": 8.5, "delta": -0.5, "name": "Hơi Vừa (8.5pt)"},
            "normal": {"base": 9, "delta": 0, "name": "Bình Thường (9pt)"},
            "medium": {"base": 10, "delta": 1, "name": "Vừa (10pt)"},
            "semi_large": {"base": 11, "delta": 2, "name": "Hơi Lớn (11pt)"},
            "large": {"base": 12, "delta": 3, "name": "Lớn (12pt)"}
        }
        cfg = font_map.get(font_level, font_map["normal"])
        base_sz = int(round(cfg["base"]))
        delta = cfg["delta"]

        # 1. Cập nhật các named fonts mặc định của Tk
        try:
            import tkinter.font as tkfont
            for fn in ["TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont"]:
                try:
                    tkfont.nametofont(fn).configure(size=base_sz)
                except Exception:
                    pass
        except Exception:
            pass

        # 2. Cập nhật ttk styles
        try:
            style = ttk.Style(self)
            style.configure("Treeview.Heading", font=("Segoe UI", max(7, base_sz - 1), "bold"))
            style.configure("Treeview", font=("Segoe UI", max(7, base_sz - 1)), rowheight=max(22, int(base_sz * 2.6)))
            style.configure("TNotebook.Tab", font=("Segoe UI", max(7, base_sz - 1), "bold"), padding=[10, max(4, base_sz - 3)])
        except Exception:
            pass

        # 3. Quét và cập nhật font toàn bộ widgets con
        self._scale_widget_fonts(self, delta)
        self.show_toast("Cỡ Chữ", f"Đã áp dụng cỡ chữ: {cfg['name']}!", "success")

    def _scale_widget_fonts(self, widget, delta: float):
        """Đệ quy quét và điều chỉnh cỡ chữ của mọi widget con."""
        try:
            if hasattr(widget, "cget"):
                try:
                    f = widget.cget("font")
                    if isinstance(f, tuple) and len(f) >= 2:
                        family = f[0]
                        orig_size = getattr(widget, "_orig_font_size", None)
                        if orig_size is None:
                            orig_size = f[1]
                            widget._orig_font_size = orig_size
                        new_size = max(7, int(round(orig_size + delta)))
                        if len(f) == 3:
                            widget.configure(font=(family, new_size, f[2]))
                        else:
                            widget.configure(font=(family, new_size))
                except Exception:
                    pass
        except Exception:
            pass

        try:
            for child in widget.winfo_children():
                self._scale_widget_fonts(child, delta)
        except Exception:
            pass

    def _on_min_version_combobox_toggled(self, event=None):
        """Khi Admin thay đổi bộ lọc phiên bản model trong Tab Cài Đặt."""
        new_val = self.setting_min_version_cb.get().strip()
        self.app_settings["min_gemini_version"] = new_val
        self._save_app_settings(self.app_settings)
        self._refresh_all_model_comboboxes()
        if hasattr(self, "api_model_filter_cb") and self.api_model_filter_cb.winfo_exists():
            self.api_model_filter_cb.set(new_val)
        min_v = parse_gemini_min_version(new_val)
        status_txt = f"Đã áp dụng bộ lọc: Chỉ lấy Gemini >= {min_v}!" if min_v > 0 else "Đã áp dụng bộ lọc: Hiển thị tất cả model!"
        self.show_toast("Bộ Lọc Model", status_txt, "info")

    def _on_hide_below_3_1_toggled(self):
        """Khi người dùng bật/tắt checkbox ẩn model cũ dưới 3.1 trong Cài đặt."""
        val = self.setting_hide_below_3_1_var.get()
        self.app_settings["hide_models_below_3_1"] = val
        self._save_app_settings(self.app_settings)
        self._refresh_all_model_comboboxes()
        status_txt = "Đã ẨN các model dưới Gemini 3.1!" if val else "Đã HIỆN lại toàn bộ danh sách model!"
        self.show_toast("Bộ Lọc Model", status_txt, "info")

    def _on_float_alpha_combobox_selected(self, event=None):
        """Khi người dùng chọn mức độ mờ mới cho Thanh Nổi."""
        raw = self.setting_float_alpha_cb.get()
        try:
            import re
            m = re.search(r"(\d+)", raw)
            pct = int(m.group(1)) if m else 35
            alpha = max(0.1, min(1.0, pct / 100.0))
        except Exception:
            alpha = 0.35
            pct = 35
        self.app_settings["float_idle_alpha"] = alpha
        if hasattr(self, "_float_win") and self._float_win and self._float_win.winfo_exists():
            self._float_win.attributes("-alpha", alpha)

    def _test_float_alpha_preview(self):
        """Thử nghiệm nhanh mức độ mờ của thanh nổi theo thiết lập."""
        raw = self.setting_float_alpha_cb.get()
        try:
            import re
            m = re.search(r"(\d+)", raw)
            pct = int(m.group(1)) if m else 35
            alpha = max(0.1, min(1.0, pct / 100.0))
        except Exception:
            alpha = 0.35
            pct = 35

        self.app_settings["float_idle_alpha"] = alpha
        if hasattr(self, "_float_win") and self._float_win and self._float_win.winfo_exists():
            self._float_win.attributes("-alpha", alpha)
            self.show_toast("Độ Mờ Thanh Nổi", f"Đã áp dụng độ mờ {pct}% lên Thanh Nổi đang mở!", "info")
        else:
            self.show_toast("Độ Mờ Thanh Nổi", f"Mức độ mờ đã chọn: {pct}% (Sẽ áp dụng khi bấm '🪟 Nổi' trên Header)!", "info")

    def _save_all_settings_from_ui(self):
        """Lưu toàn bộ cài đặt từ UI vào file JSON bền vững."""
        speed_val = self.setting_speed_cb.get().strip()
        for s_name in ["Siêu Chậm (Mặc Định)", "Cực Chậm", "Siêu Nhanh", "Nhanh", "Vừa", "Hơi Chậm", "Chậm"]:
            if s_name in speed_val:
                speed_val = s_name
                break

        try:
            max_ret = int(self.setting_max_retries_sp.get())
        except Exception:
            max_ret = 5

        # Đọc thời gian toast
        toast_raw = self.setting_toast_duration_cb.get()
        try:
            import re
            m = re.search(r"([\d\.]+)", toast_raw)
            toast_sec = float(m.group(1)) if m else 3.5
        except Exception:
            toast_sec = 3.5

        # Đọc vị trí toast
        toast_pos_raw = self.setting_toast_pos_cb.get().strip() if hasattr(self, 'setting_toast_pos_cb') else "bottom_right"
        toast_pos_code = "bottom_right"
        if "Phải Trên" in toast_pos_raw or "top_right" in toast_pos_raw:
            toast_pos_code = "top_right"
        elif "Trái Dưới" in toast_pos_raw or "bottom_left" in toast_pos_raw:
            toast_pos_code = "bottom_left"
        elif "Trái Trên" in toast_pos_raw or "top_left" in toast_pos_raw:
            toast_pos_code = "top_left"
        elif "Giữa" in toast_pos_raw or "bottom_center" in toast_pos_raw:
            toast_pos_code = "bottom_center"
        else:
            toast_pos_code = "bottom_right"

        # Đọc % độ mờ của thanh nổi khi idle
        alpha_raw = self.setting_float_alpha_cb.get() if hasattr(self, 'setting_float_alpha_cb') else "35%"
        try:
            import re
            m = re.search(r"(\d+)", alpha_raw)
            alpha_pct = int(m.group(1)) if m else 35
            float_alpha = max(0.1, min(1.0, alpha_pct / 100.0))
        except Exception:
            float_alpha = 0.35

        min_ver_str = self.setting_min_version_cb.get().strip() if hasattr(self, 'setting_min_version_cb') else self.app_settings.get("min_gemini_version", GEMINI_VERSION_FILTER_OPTIONS[0])
        allowed_kw = self.setting_allowed_kw_entry.get().strip() if hasattr(self, 'setting_allowed_kw_entry') else "zalo, ultraviewer, anydesk, teamviewer, remote desktop, mstsc"
        excl_kw = self.setting_exclusion_kw_entry.get().strip() if hasattr(self, 'setting_exclusion_kw_entry') else "antigravity, cursor, vscode, code.exe, pycharm, powershell, cmd.exe, windowsterminal, laragon"
        req_login = self.setting_require_login_var.get() if hasattr(self, 'setting_require_login_var') else self.app_settings.get("require_login", True)
        tab_layout = getattr(self, "script_tab_layout", self.app_settings.get("script_tab_layout", "3_columns"))
        tg_token = self.setting_telegram_token_entry.get().strip() if hasattr(self, 'setting_telegram_token_entry') else self.app_settings.get("telegram_bot_token", "")
        tg_chat_id = self.setting_telegram_chat_id_entry.get().strip() if hasattr(self, 'setting_telegram_chat_id_entry') else self.app_settings.get("telegram_chat_id", "")
        tg_auto = self.setting_telegram_auto_send_var.get() if hasattr(self, 'setting_telegram_auto_send_var') else self.app_settings.get("telegram_auto_send_backup", True)

        enable_2fa = self.setting_enable_2fa_var.get() if hasattr(self, 'setting_enable_2fa_var') else self.app_settings.get("enable_2fa", False)
        sec_pin = self.setting_2fa_pin_entry.get().strip() if hasattr(self, 'setting_2fa_pin_entry') else self.app_settings.get("security_pin_2fa", "123456")

        cfg = {
            "window_position": self.setting_win_pos_var.get(),
            "theme": self.setting_theme_var.get(),
            "font_size": self.setting_font_size_var.get(),
            "script_send_mode": self.setting_script_send_mode_cb.get().strip(),
            "always_on_top": self.setting_always_on_top_var.get(),
            "default_speed": speed_val,
            "max_retries": max_ret,
            "toast_duration_sec": toast_sec,
            "toast_position": toast_pos_code,
            "float_idle_alpha": float_alpha,
            "hide_models_below_3_1": self.setting_hide_below_3_1_var.get(),
            "min_gemini_version": min_ver_str,
            "auto_target_lock": self.setting_auto_lock_var.get(),
            "anti_spam_time": self.setting_anti_time_var.get(),
            "anti_spam_code": self.setting_anti_code_var.get(),
            "anti_spam_icon": False,
            "target_allowed_keywords": allowed_kw,
            "target_exclusion_keywords": excl_kw,
            "require_login": req_login,
            "enable_2fa": enable_2fa,
            "security_pin_2fa": sec_pin or "123456",
            "script_tab_layout": tab_layout,
            "telegram_bot_token": tg_token,
            "telegram_chat_id": tg_chat_id,
            "telegram_auto_send_backup": tg_auto
        }

        self._save_app_settings_to_file(cfg)
        self.app_settings = cfg
        ZaloAutomation.set_max_retries(max_ret)
        ZaloAutomation.set_target_keywords(allowed_kw, excl_kw)
        self._apply_saved_window_geometry(cfg["window_position"])
        self._apply_theme(cfg["theme"])
        self._apply_font_scale(cfg["font_size"])
        if hasattr(self, "_float_win") and self._float_win and self._float_win.winfo_exists():
            self._float_win.attributes("-alpha", float_alpha)
        self.show_toast("Đã Lưu Cài Đặt", "Đã lưu cài đặt, bảo mật 2FA, Telegram và thông số thành công!\nMọi tùy chọn sẽ được tự động áp dụng khi khởi động ứng dụng.", "success")

    # =========================================================================
    # HÀNH ĐỘNG SAO LƯU, PHỤC HỒI & ĐỒNG BỘ TELEGRAM (BACKUP, IMPORT, EXPORT)
    # =========================================================================
    def _do_export_backup_all(self):
        """Xuất bản sao lưu toàn bộ hệ thống ra tệp JSON và tự động gửi về Telegram nếu có cấu hình."""
        try:
            backup_data = self.state.export_full_database_backup()
            default_fname = f"backup_ai_zalo_cskh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            save_path = filedialog.asksaveasfilename(
                parent=self,
                title="💾 Chọn Nơi Lưu Bản Sao Lưu Toàn Bộ Dữ Liệu (Backup)",
                initialfile=default_fname,
                defaultextension=".json",
                filetypes=[("Tệp Sao Lưu JSON", "*.json"), ("Tất Cả Tệp", "*.*")]
            )
            if not save_path:
                return

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            file_size_kb = round(os.path.getsize(save_path) / 1024, 1)
            msg_success = f"Đã xuất tệp sao lưu thành công ({file_size_kb} KB) tại:\n{save_path}"

            # Tự động gửi về Telegram nếu được bật (không thông báo chuông)
            tg_token = self.setting_telegram_token_entry.get().strip() if hasattr(self, 'setting_telegram_token_entry') else self.app_settings.get("telegram_bot_token", "")
            tg_chat = self.setting_telegram_chat_id_entry.get().strip() if hasattr(self, 'setting_telegram_chat_id_entry') else self.app_settings.get("telegram_chat_id", "")
            tg_auto = self.setting_telegram_auto_send_var.get() if hasattr(self, 'setting_telegram_auto_send_var') else self.app_settings.get("telegram_auto_send_backup", True)

            if tg_auto and tg_token and tg_chat:
                def _tg_worker():
                    notifier = TelegramNotifier(tg_token, tg_chat)
                    ok, tg_res = notifier.send_document(
                        save_path,
                        caption=f"📦 <b>BẢN SAO LƯU DỮ LIỆU TỰ ĐỘNG ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})</b>\n\n⚡ <i>AI Zalo CSKH Database Backup</i>",
                        disable_notification=True
                    )
                    if ok:
                        logger.info(f"[Telegram] Đã gửi backup tự động về Telegram: {save_path}")
                    else:
                        logger.warning(f"[Telegram] Gửi backup tự động thất bại: {tg_res}")

                threading.Thread(target=_tg_worker, daemon=True).start()
                self.show_toast("Sao Lưu Thành Công", f"Đã xuất backup ({file_size_kb} KB) & tự động gửi về Telegram!", "success")
            else:
                self.show_toast("Sao Lưu Thành Công", f"Đã xuất backup thành công ({file_size_kb} KB)!", "success")

            messagebox.showinfo("Xuất Sao Lưu Thành Công", msg_success, parent=self)
        except Exception as e:
            logger.error(f"[Backup] Lỗi xuất sao lưu: {e}")
            self.show_toast("Lỗi Sao Lưu", f"Không thể xuất file: {e}", "error")
            messagebox.showerror("Lỗi Xuất Sao Lưu", f"Lỗi: {e}", parent=self)

    def _do_import_backup_all(self):
        """Nhập và phục hồi dữ liệu từ bản sao lưu JSON."""
        file_path = filedialog.askopenfilename(
            parent=self,
            title="📥 Chọn Tệp Sao Lưu JSON Để Phục Hồi Dữ Liệu",
            filetypes=[("Tệp Sao Lưu JSON", "*.json"), ("Tất Cả Tệp", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            app_tag = backup_data.get("app", "")
            exp_time = backup_data.get("exported_at", "Không rõ")
            if "AI_ZALO_CSKH" not in app_tag and "database" not in backup_data:
                messagebox.showerror("Tệp Không Hợp Lệ", "Tệp đã chọn không đúng định dạng bản sao lưu của ứng dụng AI Zalo CSKH!", parent=self)
                return

            c_count = len(backup_data.get("database", {}).get("customers", []))
            s_count = len(backup_data.get("database", {}).get("script_templates", []))
            cc_count = len(backup_data.get("database", {}).get("content_corrections", []))

            confirm_msg = (
                f"Bạn có chắc chắn muốn phục hồi dữ liệu từ bản sao lưu này?\n\n"
                f"📅 Thời gian tạo: {exp_time}\n"
                f"👥 Khách hàng CRM: {c_count} bản ghi\n"
                f"⚡ Mẫu kịch bản: {s_count} bản ghi\n"
                f"📝 Sổ tay sửa giáo án: {cc_count} bản ghi\n\n"
                f"⚠️ Lưu ý: Thao tác này sẽ đồng bộ và cập nhật lại toàn bộ CSDL của hệ thống."
            )
            if not messagebox.askyesno("Xác Nhận Phục Hồi Dữ Liệu", confirm_msg, parent=self):
                return

            ok, msg, counts = self.state.import_full_database_backup(backup_data, merge_mode=False)
            if ok:
                self.refresh_all_data()
                summary_txt = ", ".join([f"{k}: {v}" for k, v in counts.items()])
                self.show_toast("Phục Hồi Thành Công", f"Đã phục hồi thành công: {summary_txt}", "success")
                messagebox.showinfo("Phục Hồi Dữ Liệu Thành Công", f"✅ Phục hồi hoàn tất!\n\nChi tiết: {summary_txt}", parent=self)
            else:
                self.show_toast("Lỗi Phục Hồi", msg, "error")
                messagebox.showerror("Lỗi Phục Hồi", msg, parent=self)
        except Exception as e:
            logger.error(f"[Backup] Lỗi nhập sao lưu: {e}")
            self.show_toast("Lỗi Nhập File", f"Lỗi đọc file: {e}", "error")
            messagebox.showerror("Lỗi Nhập File", f"Lỗi đọc file: {e}", parent=self)

    def _do_test_telegram(self):
        """Kiểm tra kết nối Telegram Bot Token và Chat ID."""
        tg_token = self.setting_telegram_token_entry.get().strip() if hasattr(self, 'setting_telegram_token_entry') else self.app_settings.get("telegram_bot_token", "")
        tg_chat = self.setting_telegram_chat_id_entry.get().strip() if hasattr(self, 'setting_telegram_chat_id_entry') else self.app_settings.get("telegram_chat_id", "")
        if not tg_token or not tg_chat:
            self.show_toast("Chưa Nhập Thông Tin", "Vui lòng nhập Bot Token và Chat ID!", "warning")
            messagebox.showwarning("Thiếu Thông Tin", "Vui lòng nhập Telegram Bot Token và Chat ID trước khi kiểm tra!", parent=self)
            return

        def _test_worker():
            notifier = TelegramNotifier(tg_token, tg_chat)
            ok, res_msg = notifier.test_connection()
            if ok:
                self.after(0, lambda: (
                    self.show_toast("Telegram Kết Nối Tốt", "Đã gửi tin nhắn test thành công!", "success"),
                    messagebox.showinfo("Kết Nối Telegram Thành Công", res_msg, parent=self)
                ))
            else:
                self.after(0, lambda: (
                    self.show_toast("Lỗi Telegram", res_msg, "error"),
                    messagebox.showerror("Lỗi Kết Nối Telegram", res_msg, parent=self)
                ))

        threading.Thread(target=_test_worker, daemon=True).start()

    def _do_send_backup_to_telegram_now(self):
        """Tạo bản sao lưu tạm thời và gửi thẳng về Telegram ngay lập tức (không chuông)."""
        tg_token = self.setting_telegram_token_entry.get().strip() if hasattr(self, 'setting_telegram_token_entry') else self.app_settings.get("telegram_bot_token", "")
        tg_chat = self.setting_telegram_chat_id_entry.get().strip() if hasattr(self, 'setting_telegram_chat_id_entry') else self.app_settings.get("telegram_chat_id", "")
        if not tg_token or not tg_chat:
            self.show_toast("Chưa Cấu Hình", "Vui lòng nhập Bot Token và Chat ID!", "warning")
            messagebox.showwarning("Thiếu Thông Tin", "Vui lòng nhập Telegram Bot Token và Chat ID!", parent=self)
            return

        def _send_worker():
            try:
                backup_data = self.state.export_full_database_backup()
                temp_dir = get_storage_path("backups")
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f"backup_ai_zalo_cskh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)

                notifier = TelegramNotifier(tg_token, tg_chat)
                ok, res_msg = notifier.send_document(
                    temp_file,
                    caption=f"📦 <b>BẢN SAO LƯU DỮ LIỆU TỨC THỜI ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})</b>\n\n⚡ <i>Gửi thủ công từ Tab Cài Đặt Dashboard</i>",
                    disable_notification=True
                )
                if ok:
                    self.after(0, lambda: (
                        self.show_toast("Đã Gửi Telegram", "Đã gửi tệp backup thành công về Telegram!", "success"),
                        messagebox.showinfo("Thành Công", "Đã gửi tệp sao lưu toàn bộ dữ liệu thành công về Telegram của bạn!", parent=self)
                    ))
                else:
                    self.after(0, lambda: (
                        self.show_toast("Lỗi Gửi Telegram", res_msg, "error"),
                        messagebox.showerror("Lỗi Gửi Telegram", res_msg, parent=self)
                    ))
            except Exception as e:
                self.after(0, lambda: (
                    self.show_toast("Lỗi", str(e), "error"),
                    messagebox.showerror("Lỗi", str(e), parent=self)
                ))

        threading.Thread(target=_send_worker, daemon=True).start()

    # =========================================================================
    # QUẢN LÝ TÀI KHOẢN ĐĂNG NHẬP & BẢO MẬT (AUTH & USERS)
    # =========================================================================
    def _refresh_users_tree(self):
        """Nạp lại danh sách tài khoản người dùng vào Treeview trong Tab Cài Đặt kèm số lần & thời gian đăng nhập."""
        if not hasattr(self, 'users_tree'):
            return
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        users = self.state.get_all_users()
        for u in users:
            role_lbl = "👑 Admin" if u.get("role") == "admin" else "👤 Nhân Viên"
            login_cnt = u.get("login_count", 0) or 0
            last_l = u.get("last_login_at", "")
            last_l_str = last_l[:19] if last_l else "Chưa ĐN"
            created_str = u.get("created_at", "")[:10] if u.get("created_at") else ""
            self.users_tree.insert(
                "",
                "end",
                iid=f"u_{u['id']}",
                values=(u.get("username", ""), u.get("full_name", ""), role_lbl, f"{login_cnt} lần", last_l_str, created_str)
            )

    def _show_login_dialog(self, is_startup: bool = False):
        """Hiển thị cửa sổ đăng nhập bảo mật."""
        def _on_ok(u_data):
            self.current_logged_user = u_data
            self._update_header_user_display()
            self.deiconify()
            self._apply_saved_window_geometry()
            self.show_toast(
                "Đăng Nhập Thành Công",
                f"Xin chào {u_data.get('full_name', u_data['username'])} ({u_data.get('role', 'admin')})!",
                "success"
            )

        def _on_cancel():
            if is_startup or not self.current_logged_user:
                self.destroy()
            else:
                self.deiconify()

        LoginDialog(self, self.state, _on_ok, _on_cancel, app_settings=self.app_settings)

    def _logout_user(self):
        """Đăng xuất tài khoản hiện tại và hiển thị lại màn hình đăng nhập."""
        if messagebox.askyesno("Xác Nhận Đăng Xuất", "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản hiện tại?", parent=self):
            self.current_logged_user = None
            self.withdraw()
            self._show_login_dialog(is_startup=False)

    def _update_header_user_display(self):
        """Cập nhật hiển thị tên tài khoản trên thanh Header."""
        if hasattr(self, 'header_user_lbl') and self.current_logged_user:
            u_name = self.current_logged_user.get("username", "admin")
            self.header_user_lbl.configure(text=f"👤 {u_name}")

    def _open_change_password_modal(self, target_username: Optional[str] = None):
        """Mở modal đổi mật khẩu cho tài khoản admin hoặc tài khoản chỉ định."""
        u_target = target_username or (self.current_logged_user.get("username", "admin") if self.current_logged_user else "admin")

        dlg = tk.Toplevel(self)
        dlg.title(f"🔑 Đổi Mật Khẩu - {u_target}")
        dlg.geometry("380x280")
        dlg.resizable(False, False)
        dlg.configure(bg="#0f172a")
        dlg.attributes("-topmost", True)

        dlg.update_idletasks()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"380x280+{(sw-380)//2}+{(sh-280)//2}")

        body = tk.Frame(dlg, bg="#0f172a", padx=20, pady=15)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"🔑 Đổi Mật Khẩu Cho: '{u_target}'", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="Mật khẩu mới:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_new = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white", show="*")
        ent_new.pack(fill="x", pady=(2, 8), ipady=2)
        ent_new.focus_set()

        tk.Label(body, text="Xác nhận mật khẩu mới:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_confirm = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white", show="*")
        ent_confirm.pack(fill="x", pady=(2, 10), ipady=2)

        lbl_msg = tk.Label(body, text="", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#0f172a")
        lbl_msg.pack(fill="x", pady=(0, 8))

        def _do_save():
            p1 = ent_new.get().strip()
            p2 = ent_confirm.get().strip()
            if not p1:
                lbl_msg.configure(text="⚠️ Vui lòng nhập mật khẩu mới!", fg="#ef4444")
                return
            if p1 != p2:
                lbl_msg.configure(text="❌ Mật khẩu xác nhận không khớp!", fg="#ef4444")
                return

            try:
                self.state.change_user_password(u_target, p1)
                dlg.destroy()
                self.show_toast("Đổi Mật Khẩu", f"Đã đổi mật khẩu cho tài khoản '{u_target}' thành công!", "success")
            except Exception as e:
                lbl_msg.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")

        btn_f = tk.Frame(body, bg="#0f172a")
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="💾 Lưu Mật Khẩu", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=_do_save).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(btn_f, text="Đóng", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=8, pady=4, cursor="hand2", command=dlg.destroy).pack(side="right", padx=(4, 0))

        dlg.bind("<Return>", lambda e: _do_save())

    def _open_create_user_modal(self):
        """Mở modal tạo tài khoản người dùng mới."""
        dlg = tk.Toplevel(self)
        dlg.title("➕ Thêm Tài Khoản Người Dùng Mới")
        dlg.geometry("400x350")
        dlg.resizable(False, False)
        dlg.configure(bg="#0f172a")
        dlg.attributes("-topmost", True)

        dlg.update_idletasks()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"400x350+{(sw-400)//2}+{(sh-350)//2}")

        body = tk.Frame(dlg, bg="#0f172a", padx=20, pady=15)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="➕ THÊM NGƯỜI DÙNG MỚI", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="Tên đăng nhập (username):", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_u = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        ent_u.pack(fill="x", pady=(2, 6), ipady=2)
        ent_u.focus_set()

        tk.Label(body, text="Mật khẩu khởi tạo:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_p = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white", show="*")
        ent_p.pack(fill="x", pady=(2, 6), ipady=2)

        tk.Label(body, text="Tên hiển thị / Họ và tên:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_fn = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        ent_fn.pack(fill="x", pady=(2, 6), ipady=2)

        tk.Label(body, text="Vai trò (Role):", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        role_cb = ttk.Combobox(body, values=["Admin", "Nhân Viên"], state="readonly")
        role_cb.set("Admin")
        role_cb.pack(fill="x", pady=(2, 10))

        lbl_msg = tk.Label(body, text="", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#0f172a")
        lbl_msg.pack(fill="x", pady=(0, 6))

        def _do_create():
            u = ent_u.get().strip()
            p = ent_p.get().strip()
            fn = ent_fn.get().strip()
            r = "admin" if role_cb.get() == "Admin" else "user"

            if not u or not p:
                lbl_msg.configure(text="⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!", fg="#ef4444")
                return

            try:
                self.state.create_user(u, p, full_name=fn or u, role=r)
                dlg.destroy()
                self._refresh_users_tree()
                self.show_toast("Tạo Tài Khoản", f"Đã tạo tài khoản '{u}' thành công!", "success")
            except Exception as e:
                lbl_msg.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")

        btn_f = tk.Frame(body, bg="#0f172a")
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="➕ Tạo Tài Khoản", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=_do_create).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(btn_f, text="Hủy", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=8, pady=4, cursor="hand2", command=dlg.destroy).pack(side="right", padx=(4, 0))

        dlg.bind("<Return>", lambda e: _do_create())

    def _open_edit_user_modal(self):
        """Mở modal sửa thông tin tài khoản (Tên hiển thị, vai trò, mật khẩu mới)."""
        sel = self.users_tree.selection() if hasattr(self, 'users_tree') else ()
        if not sel:
            self.show_toast("Chưa Chọn User", "Vui lòng chọn 1 tài khoản trong danh sách để sửa thông tin!", "warning")
            return
        iid = sel[0]
        u_id = int(iid.replace("u_", ""))
        item_vals = self.users_tree.item(iid, "values")
        if not item_vals:
            return
        u_name = item_vals[0]
        u_fullname = item_vals[1]
        u_role = "Admin" if "Admin" in item_vals[2] else "Nhân Viên"

        dlg = tk.Toplevel(self)
        dlg.title(f"✏️ Sửa Thông Tin Tài Khoản - {u_name}")
        dlg.geometry("420x380")
        dlg.resizable(False, False)
        dlg.configure(bg="#0f172a")
        dlg.attributes("-topmost", True)

        dlg.update_idletasks()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"420x380+{(sw-420)//2}+{(sh-380)//2}")

        body = tk.Frame(dlg, bg="#0f172a", padx=20, pady=15)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"✏️ SỬA THÔNG TIN: '{u_name}'", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(0, 8))

        tk.Label(body, text="Tên hiển thị / Họ và tên:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        ent_fn = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        ent_fn.pack(fill="x", pady=(2, 6), ipady=2)
        ent_fn.insert(0, u_fullname)
        ent_fn.focus_set()

        tk.Label(body, text="Vai trò (Role):", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        role_cb = ttk.Combobox(body, values=["Admin", "Nhân Viên"], state="readonly")
        role_cb.set(u_role)
        role_cb.pack(fill="x", pady=(2, 8))

        tk.Label(body, text="Mật khẩu mới (Để trống nếu không muốn đổi):", font=("Segoe UI", 9, "bold"), fg="#c084fc", bg="#0f172a").pack(anchor="w")
        ent_p = tk.Entry(body, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white", show="*")
        ent_p.pack(fill="x", pady=(2, 10), ipady=2)

        lbl_msg = tk.Label(body, text="", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#0f172a")
        lbl_msg.pack(fill="x", pady=(0, 6))

        def _do_update():
            fn = ent_fn.get().strip()
            r = "admin" if role_cb.get() == "Admin" else "user"
            p = ent_p.get().strip()

            try:
                self.state.update_user_info(u_id, full_name=fn or u_name, role=r, new_password=p if p else None)
                dlg.destroy()
                self._refresh_users_tree()
                self.show_toast("Cập Nhật Thành Công", f"Đã cập nhật thông tin tài khoản '{u_name}'!", "success")
            except Exception as e:
                lbl_msg.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")

        btn_f = tk.Frame(body, bg="#0f172a")
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="💾 Lưu Thay Đổi", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=_do_update).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(btn_f, text="Hủy", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=8, pady=4, cursor="hand2", command=dlg.destroy).pack(side="right", padx=(4, 0))

        dlg.bind("<Return>", lambda e: _do_update())

    def _open_login_logs_modal(self):
        """Mở modal xem toàn bộ nhật ký các lần đăng nhập (thời gian, username, trạng thái)."""
        dlg = tk.Toplevel(self)
        dlg.title("📜 Nhật Ký Đăng Nhập Hệ Thống")
        dlg.geometry("620x440")
        dlg.resizable(True, True)
        dlg.configure(bg="#0f172a")
        dlg.attributes("-topmost", True)

        dlg.update_idletasks()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"620x440+{(sw-620)//2}+{(sh-440)//2}")

        body = tk.Frame(dlg, bg="#0f172a", padx=16, pady=12)
        body.pack(fill="both", expand=True)

        hdr_row = tk.Frame(body, bg="#0f172a")
        hdr_row.pack(fill="x", pady=(0, 8))
        tk.Label(hdr_row, text="📜 LỊCH SỬ CÁC LẦN ĐĂNG NHẬP", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(side="left")

        cols = ("id", "username", "status", "ip", "time")
        tree_frame = tk.Frame(body, bg="#0f172a")
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12, selectmode="browse")
        tree.heading("id", text="STT")
        tree.heading("username", text="Tên Đăng Nhập")
        tree.heading("status", text="Trạng Thái")
        tree.heading("ip", text="IP / Nguồn")
        tree.heading("time", text="Thời Gian Đăng Nhập")

        tree.column("id", width=45, anchor="center")
        tree.column("username", width=120)
        tree.column("status", width=105, anchor="center")
        tree.column("ip", width=95, anchor="center")
        tree.column("time", width=170, anchor="center")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        def _refresh_logs():
            for item in tree.get_children():
                tree.delete(item)
            logs = self.state.get_login_logs(limit=100)
            for idx, log in enumerate(logs, 1):
                status_txt = "✅ Thành công" if log.get("status") == "SUCCESS" else "❌ Thất bại"
                t_str = log.get("login_time", "")[:19] if log.get("login_time") else ""
                tree.insert(
                    "",
                    "end",
                    values=(idx, log.get("username", ""), status_txt, log.get("ip_address", "127.0.0.1"), t_str)
                )

        _refresh_logs()

        def _clear_logs():
            if messagebox.askyesno("Xóa Lịch Sử", "Bạn có chắc chắn muốn xóa toàn bộ nhật ký đăng nhập?", parent=dlg):
                self.state.clear_login_logs()
                _refresh_logs()
                self.show_toast("Đã Xóa Log", "Đã dọn dẹp sạch nhật ký đăng nhập!", "info")

        bot_f = tk.Frame(dlg, bg="#0f172a", padx=16, pady=8)
        bot_f.pack(fill="x")
        tk.Button(bot_f, text="🔄 Làm Mới", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=_refresh_logs).pack(side="left", padx=(0, 4))
        tk.Button(bot_f, text="🧹 Xóa Lịch Sử", bg="#475569", fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=8, pady=2, cursor="hand2", command=_clear_logs).pack(side="left", padx=4)
        tk.Button(bot_f, text="Đóng", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 8), relief="flat", padx=8, pady=2, cursor="hand2", command=dlg.destroy).pack(side="right")

    def _change_selected_user_password(self):
        """Đổi mật khẩu cho user đang chọn trong bảng."""
        sel = self.users_tree.selection() if hasattr(self, 'users_tree') else ()
        if not sel:
            self.show_toast("Chưa Chọn User", "Vui lòng chọn 1 tài khoản trong danh sách để đổi mật khẩu!", "warning")
            return
        item_vals = self.users_tree.item(sel[0], "values")
        if item_vals:
            u_name = item_vals[0]
            self._open_change_password_modal(u_name)

    def _delete_selected_user(self):
        """Xóa tài khoản người dùng đang chọn."""
        sel = self.users_tree.selection() if hasattr(self, 'users_tree') else ()
        if not sel:
            self.show_toast("Chưa Chọn User", "Vui lòng chọn 1 tài khoản trong danh sách để xóa!", "warning")
            return
        iid = sel[0]
        u_id = int(iid.replace("u_", ""))
        item_vals = self.users_tree.item(iid, "values")
        u_name = item_vals[0] if item_vals else f"ID {u_id}"

        if messagebox.askyesno("Xác Nhận Xóa", f"Bạn có chắc chắn muốn XÓA tài khoản '{u_name}'?", parent=self):
            try:
                self.state.delete_user(u_id)
                self._refresh_users_tree()
                self.show_toast("Đã Xóa", f"Đã xóa tài khoản '{u_name}' thành công!", "info")
            except Exception as e:
                self.show_toast("Không Thể Xóa", f"Lỗi: {e}", "error")

    def _clear_saved_login_credentials_from_settings(self):
        """Xóa sạch thông tin tài khoản và mật khẩu đã lưu từ Cài Đặt."""
        clear_saved_login_credentials()
        self.show_toast("Đã Xóa Thông Tin Đăng Nhập", "Đã xóa toàn bộ tài khoản và mật khẩu đã lưu trên máy!", "info")

    def reset_all_retry_and_error_states(self):
        """Khôi phục và đặt lại toàn bộ bộ đếm lỗi 5 lần, cờ abort và kết nối gửi tin nhắn."""
        from zalo_layer.zalo_automation import BroadcastController, ZaloAutomation
        # 1. Reset cờ abort và lock trong ZaloAutomation
        ZaloAutomation.reset_abort()

        # 2. Reset trạng thái BroadcastController
        BroadcastController.reset()

        # 3. Quét lại HWND Zalo PC và reset cache
        if hasattr(ZaloAutomation, '_last_external_hwnd'):
            ZaloAutomation._last_external_hwnd = None
        ZaloAutomation.find_zalo_hwnd()

        # 4. Cập nhật nhãn trạng thái các tab
        msg = "✨ Đã reset lượt thử & sẵn sàng gửi tin nhắn!"
        if hasattr(self, 'script_send_status_lbl'):
            self.script_send_status_lbl.configure(text=msg, fg="#34d399")
        if hasattr(self, 'bc_status_lbl'):
            self.bc_status_lbl.configure(text=msg, fg="#34d399")

        self.set_footer_task("✨ Đã khôi phục trạng thái sẵn sàng gửi tin (Reset Retry Count).")
        self.show_toast("Khôi Phục Gửi Tin", "Đã đặt lại bộ đếm lỗi 5 lần & khôi phục trạng thái gửi tin nhắn thành công!", "success")

    def _reset_target_keywords_ui(self):
        """Nạp danh sách từ khóa mặc định vào ô nhập."""
        def_allowed = "zalo, ultraviewer, anydesk, teamviewer, remote desktop, mstsc"
        def_excl = "antigravity, cursor, vscode, code.exe, pycharm, powershell, cmd.exe, windowsterminal, laragon"
        if hasattr(self, 'setting_allowed_kw_entry'):
            self.setting_allowed_kw_entry.delete(0, tk.END)
            self.setting_allowed_kw_entry.insert(0, def_allowed)
        if hasattr(self, 'setting_exclusion_kw_entry'):
            self.setting_exclusion_kw_entry.delete(0, tk.END)
            self.setting_exclusion_kw_entry.insert(0, def_excl)
        self.show_toast("Nạp Từ Khóa", "Đã nạp danh sách từ khóa mặc định!", "info")

    def _apply_and_test_keywords_now(self):
        """Áp dụng ngay từ khóa mới và quét lại cửa sổ."""
        allowed_str = self.setting_allowed_kw_entry.get().strip() if hasattr(self, 'setting_allowed_kw_entry') else ""
        excl_str = self.setting_exclusion_kw_entry.get().strip() if hasattr(self, 'setting_exclusion_kw_entry') else ""
        ZaloAutomation.set_target_keywords(allowed_str, excl_str)
        self._refresh_target_windows_list()
        self.show_toast("Áp Dụng Từ Khóa", "Đã cập nhật từ khóa và quét lại danh sách cửa sổ thành công!", "success")

    def _reset_settings_to_default(self):
        """Khôi phục cài đặt mặc định ban đầu."""
        self.setting_win_pos_var.set("right_half")
        self.setting_theme_var.set("slate_dark")
        self.setting_font_size_var.set("normal")
        self.setting_script_send_mode_cb.set("Gửi Ngay Vào Zalo (Enter)")
        self.setting_always_on_top_var.set(False)
        self.setting_speed_cb.set("Siêu Chậm (Mặc Định)")
        self.setting_max_retries_sp.delete(0, tk.END)
        self.setting_max_retries_sp.insert(0, "5")
        self.setting_auto_lock_var.set(True)
        self.setting_anti_time_var.set(True)
        self.setting_anti_code_var.set(True)
        self.setting_hide_below_3_1_var.set(True)
        if hasattr(self, "setting_min_version_cb") and self.setting_min_version_cb.winfo_exists():
            self.setting_min_version_cb.set(GEMINI_VERSION_FILTER_OPTIONS[0])
        self._reset_target_keywords_ui()
        self._save_all_settings_from_ui()
        self.show_toast("Khôi Phục Gốc", "Đã khôi phục cài đặt mặc định ban đầu!", "info")

    def _open_log_file(self):
        """Mở file app.log bằng trình xem mặc định."""
        log_p = get_storage_path("logs/app.log")
        if os.path.exists(log_p):
            try:
                os.startfile(log_p)
            except Exception as e:
                self.show_toast("Không Thể Mở", f"Lỗi mở file: {e}", "error")
        else:
            self.show_toast("Chưa Có Log", "File log chưa được tạo!", "warning")

    def _open_storage_folder(self):
        """Mở thư mục storage bằng Windows Explorer."""
        st_p = get_storage_path("")
        if os.path.exists(st_p):
            try:
                os.startfile(st_p)
            except Exception as e:
                self.show_toast("Không Thể Mở", f"Lỗi mở thư mục: {e}", "error")

    # =========================================================================
    # TAB: ⚡ KỊCH BẢN TRẢ LỜI NHANH (QUICK SCRIPT TEMPLATES VÀO ZALO ĐANG MỞ)
    # =========================================================================
    def _build_script_templates_tab(self, parent):
        """Xây dựng Tab Kịch Bản Trả Lời Nhanh (Gửi mẫu vào vùng soạn thảo Zalo PC đang mở hoặc UltraViewer/AnyDesk)."""
        self.current_script_id = None
        self.current_script_attached_files = []
        self.script_target_mode = "active_window"  # Mặc định: Gửi đến Cửa Sổ Đang Active (Ultraviewer/AnyDesk/Zalo)

        # Top Bar: Khung chứa 2 hàng công cụ rõ ràng, không bao giờ bị tràn hoặc ẩn nút
        top_bar_container = tk.Frame(parent, bg="#1e293b", padx=10, pady=6)
        top_bar_container.pack(fill="x", pady=(0, 6))

        # HÀNG 1: TÌM KIẾM + LỌC DANH MỤC + NÚT BỐ CỤC NỔI BẬT + KHÓA NỀN + RESET LỖI
        r1 = tk.Frame(top_bar_container, bg="#1e293b")
        r1.pack(fill="x", pady=(0, 4))

        tk.Label(r1, text="🔍 Tìm Kiếm:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")
        self.script_search_var = tk.StringVar()
        self.script_search_var.trace_add("write", lambda *args: self._on_script_search_changed())
        ent_search = tk.Entry(r1, textvariable=self.script_search_var, font=("Segoe UI", 9), bg="#0f172a", fg="#f8fafc", insertbackground="white", width=16)
        ent_search.pack(side="left", padx=(4, 8))

        tk.Label(r1, text="📁 Lọc Danh Mục:", font=("Segoe UI", 9, "bold"), fg="#a855f7", bg="#1e293b").pack(side="left")
        self.script_category_cb = ttk.Combobox(r1, state="readonly", width=16)
        self.script_category_cb.pack(side="left", padx=(4, 8))
        self.script_category_cb.bind("<<ComboboxSelected>>", self._on_script_category_filter_changed)

        # NÚT CHUYỂN ĐỔI BỐ CỤC 3 CỘT / 2 CỘT (NỔI BẬT, DỄ NHÌN THẤY NGAY)
        self.script_tab_layout = self.app_settings.get("script_tab_layout", "3_columns")
        layout_btn_txt = "🔲 Bố Cục: 3 Cột Ngang" if self.script_tab_layout == "3_columns" else "🔳 Bố Cục: 2 Cột (Kho Tệp Dưới)"
        self.btn_script_layout_toggle = tk.Button(
            r1,
            text=layout_btn_txt,
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._toggle_script_tab_layout
        )
        self.btn_script_layout_toggle.pack(side="left", padx=(6, 8))

        # Nút Khôi Phục / Reset Lỗi
        btn_script_reset_top = tk.Button(
            r1,
            text="🔄 Reset Lỗi",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.reset_all_retry_and_error_states
        )
        btn_script_reset_top.pack(side="right", padx=(4, 0))

        # NÚT CHUYỂN ĐỔI CHẾ ĐỘ GỬI: KHÓA NỀN ZALO VS GỬI FREE (BẤT KỲ APP NÀO)
        self.script_target_mode = "target_locked"
        self.btn_script_target_mode = tk.Button(
            r1,
            text="🔒 KHÓA NỀN ZALO PC (Gửi Ngầm)",
            font=("Segoe UI", 8, "bold"),
            bg="#8b5cf6",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._toggle_script_target_mode
        )
        self.btn_script_target_mode.pack(side="right", padx=(0, 4))

        # HÀNG 2: THANH CÔNG CỤ THAO TÁC MẪU (THÊM, NHÂN BẢN, XUẤT, NẠP, XÓA, QUẢN LÝ DANH MỤC)
        r2 = tk.Frame(top_bar_container, bg="#1e293b")
        r2.pack(fill="x")

        btn_add = tk.Button(r2, text="➕ Thêm Mẫu Mới", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._create_new_script_template)
        btn_add.pack(side="left", padx=(0, 4))

        btn_manage_cat = tk.Button(r2, text="📁 Quản Lý Danh Mục...", bg="#6366f1", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._open_script_category_manager_modal)
        btn_manage_cat.pack(side="left", padx=4)

        btn_dup = tk.Button(r2, text="📋 Nhân Bản Mẫu", bg="#475569", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._duplicate_current_script_template)
        btn_dup.pack(side="left", padx=4)

        btn_export = tk.Button(r2, text="📤 Xuất JSON", bg="#0284c7", fg="white", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._export_script_templates)
        btn_export.pack(side="left", padx=4)

        btn_import = tk.Button(r2, text="📥 Nạp JSON", bg="#0d9488", fg="white", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._import_script_templates)
        btn_import.pack(side="left", padx=4)

        btn_del = tk.Button(r2, text="🗑️ Xóa Mẫu Đang Chọn", bg="#334155", fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._delete_current_script_template)
        btn_del.pack(side="left", padx=4)

        # Container chứa PanedWindow linh hoạt
        self.script_paned_container = tk.Frame(parent, bg="#0f172a")
        self.script_paned_container.pack(fill="both", expand=True)

        # ==================== KHUNG 1: DANH SÁCH MẪU ====================
        left_f = tk.Frame(parent, bg="#0f172a", padx=6, pady=6)
        self.script_left_frame = left_f

        left_hdr = tk.Frame(left_f, bg="#0f172a")
        left_hdr.pack(fill="x", pady=(0, 4))
        self.lbl_script_count = tk.Label(left_hdr, text="📋 Mẫu Kịch Bản", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a")
        self.lbl_script_count.pack(side="left")

        # Treeview danh sách mẫu (selectmode='extended' hỗ trợ chọn nhiều bằng Shift+Up/Down, Ctrl+Click)
        cols = ("label", "cat", "q", "files")
        self.script_tree = ttk.Treeview(left_f, columns=cols, show="headings", height=15, selectmode="extended")
        self.script_tree.heading("label", text="Tên Mẫu Kịch Bản")
        self.script_tree.heading("cat", text="Danh Mục")
        self.script_tree.heading("q", text="Câu Hỏi")
        self.script_tree.heading("files", text="File")

        self.script_tree.column("label", width=120)
        self.script_tree.column("cat", width=85)
        self.script_tree.column("q", width=110)
        self.script_tree.column("files", width=35, anchor="center")
        self.script_tree.pack(fill="both", expand=True)

        # Event bindings
        self.script_tree.bind("<<TreeviewSelect>>", self._on_script_template_selected)
        self.script_tree.bind("<Double-1>", self._on_script_tree_double_click)
        self.script_tree.bind("<Return>", self._on_script_tree_enter_key)
        self.script_tree.bind("<Control-Return>", self._on_script_tree_ctrl_enter_key)
        self.script_tree.bind("<Control-c>", self._on_script_tree_ctrl_c)
        self.script_tree.bind("<Control-C>", self._on_script_tree_ctrl_c)
        self.script_tree.bind("<Button-3>", self._on_script_tree_right_click)

        # Right-Click Context Menu
        self.script_tree_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", activeforeground="white")
        self.script_tree_menu.add_command(label="🚀 Gửi Ngay Vào Cửa Sổ (Enter)", command=lambda: self._send_current_script_to_zalo(auto_enter=True))
        self.script_tree_menu.add_command(label="📝 Chèn Nháp Vào Ô Chat (Ctrl+Enter)", command=lambda: self._send_current_script_to_zalo(auto_enter=False))
        self.script_tree_menu.add_separator()
        self.script_tree_menu.add_command(label="📋 Sao Chép Câu Trả Lời (Ctrl+C)", command=lambda: self._copy_current_script_answer("answer"))
        self.script_tree_menu.add_command(label="❓ Sao Chép Câu Hỏi Tình Huống", command=lambda: self._copy_current_script_answer("question"))
        self.script_tree_menu.add_command(label="📄 Sao Chép Cả Câu Hỏi & Trả Lời", command=lambda: self._copy_current_script_answer("both"))
        self.script_tree_menu.add_separator()
        self.script_tree_menu.add_command(label="➕ Thêm Mẫu Mới Nhanh", command=self._create_new_script_template)
        self.script_tree_menu.add_command(label="📋 Nhân Bản Mẫu Này", command=self._duplicate_current_script_template)
        self.script_tree_menu.add_command(label="📁 Đổi Danh Mục Của Mẫu...", command=self._change_category_for_current_template)
        self.script_tree_menu.add_command(label="📤 Xuất Mẫu Này Ra File...", command=self._export_selected_template)
        self.script_tree_menu.add_separator()
        self.script_tree_menu.add_command(label="🗑️ Xóa Mẫu Đang Chọn", command=self._delete_current_script_template)

        hint_bar = tk.Label(left_f, text="💡 Shift+Up/Down: Chọn nhiều | Ctrl+C: Copy", font=("Segoe UI", 7, "italic"), fg="#94a3b8", bg="#0f172a", anchor="w")
        hint_bar.pack(fill="x", pady=(4, 0))

        # ==================== KHUNG 2: XEM TRƯỚC / SOẠN THẢO & GỬI NGAY ====================
        mid_f = tk.Frame(parent, bg="#0f172a", padx=8, pady=6)
        self.script_mid_frame = mid_f

        # 1. Nhãn & Danh mục
        row_lbl_cat = tk.Frame(mid_f, bg="#0f172a")
        row_lbl_cat.pack(fill="x", pady=(0, 3))

        f_lbl = tk.Frame(row_lbl_cat, bg="#0f172a")
        f_lbl.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Label(f_lbl, text="Nhãn hiển thị ngắn gọn:", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        self.script_label_entry = tk.Entry(f_lbl, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.script_label_entry.pack(fill="x", pady=(1, 0))
        self.script_label_entry.bind("<Control-s>", lambda e: (self._save_current_script_template(), "break")[1])
        self.script_label_entry.bind("<Control-S>", lambda e: (self._save_current_script_template(), "break")[1])

        f_cat = tk.Frame(row_lbl_cat, bg="#0f172a")
        f_cat.pack(side="right", padx=(4, 0))
        tk.Label(f_cat, text="Danh mục:", font=("Segoe UI", 8, "bold"), fg="#a855f7", bg="#0f172a").pack(anchor="w")
        self.script_cat_cb = ttk.Combobox(f_cat, width=18)
        self.script_cat_cb.pack(fill="x", pady=(1, 0))
        self.script_cat_cb.bind("<Control-s>", lambda e: (self._save_current_script_template(), "break")[1])
        self.script_cat_cb.bind("<Control-S>", lambda e: (self._save_current_script_template(), "break")[1])

        # 2. Câu hỏi tình huống
        tk.Label(mid_f, text="Câu hỏi tình huống / Thắc mắc thường gặp:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(3, 1))
        self.script_q_entry = tk.Entry(mid_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.script_q_entry.pack(fill="x", pady=(0, 3))
        self.script_q_entry.bind("<Control-s>", lambda e: (self._save_current_script_template(), "break")[1])
        self.script_q_entry.bind("<Control-S>", lambda e: (self._save_current_script_template(), "break")[1])

        # 3. Nội dung trả lời
        tk.Label(mid_f, text="Nội dung tin nhắn trả lời giải đáp (sẽ gửi vào Zalo):", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a").pack(anchor="w", pady=(2, 1))
        self.script_ans_txt = tk.Text(mid_f, font=("Segoe UI", 9), height=7, bg="#1e293b", fg="#f8fafc", insertbackground="white", wrap="word")
        self.script_ans_txt.pack(fill="x", pady=(0, 3))
        self.script_ans_txt.bind("<Control-s>", lambda e: (self._save_current_script_template(), "break")[1])
        self.script_ans_txt.bind("<Control-S>", lambda e: (self._save_current_script_template(), "break")[1])

        # 4. File / Thư mục đính kèm cố định của mẫu
        file_hdr = tk.Frame(mid_f, bg="#0f172a")
        file_hdr.pack(fill="x", pady=(2, 1))
        btn_add_f = tk.Button(file_hdr, text="➕ File", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=1, cursor="hand2", command=self._add_files_to_script_template)
        btn_add_f.pack(side="left", padx=(0, 4))
        btn_add_d = tk.Button(file_hdr, text="📂 Thư Mục", bg="#0d9488", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=1, cursor="hand2", command=self._add_folder_to_script_template)
        btn_add_d.pack(side="left", padx=(0, 6))
        tk.Label(file_hdr, text="📁 Tệp cố định của mẫu:", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a").pack(side="left")

        # Dòng thống kê đếm file & link realtime
        self.lbl_script_file_count_summary = tk.Label(mid_f, text="📊 Cố định: 0 file", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a", anchor="w")
        self.lbl_script_file_count_summary.pack(fill="x", pady=(0, 1))

        self.lbl_script_links_count_summary = tk.Label(mid_f, text="🔗 Đính kèm: 0 link khối", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a", anchor="w")
        self.lbl_script_links_count_summary.pack(fill="x", pady=(0, 2))

        self.script_files_listbox = tk.Listbox(mid_f, font=("Segoe UI", 8), height=3, bg="#1e293b", fg="#f8fafc", selectbackground="#0284c7")
        self.script_files_listbox.pack(fill="x", pady=(0, 2))

        f_act = tk.Frame(mid_f, bg="#0f172a")
        f_act.pack(fill="x", pady=(0, 4))
        tk.Button(f_act, text="🗑️ Xóa File", bg="#475569", fg="white", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=self._remove_selected_file_from_script).pack(side="left", padx=2)
        tk.Button(f_act, text="🧹 Xóa Hết", bg="#334155", fg="#94a3b8", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=self._clear_all_script_files).pack(side="left", padx=2)
        tk.Button(f_act, text="💾 Lưu Mẫu (Ctrl+S)", bg="#22c55e", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=1, cursor="hand2", command=self._save_current_script_template).pack(side="right", padx=2)
        tk.Button(f_act, text="📋 Copy (Ctrl+C)", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=1, cursor="hand2", command=self._copy_current_script_answer).pack(side="right", padx=2)

        # 5. CỤM NÚT GỬI VÀO ZALO / CỬA SỔ ĐANG MỞ
        send_card = tk.Frame(mid_f, bg="#1e293b", padx=8, pady=6)
        send_card.pack(fill="x", pady=(2, 0))

        btn_send_now = tk.Button(
            send_card,
            text="🚀 GỬI VÀO ZALO (Enter / F10)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: self._send_current_script_to_zalo(auto_enter=True)
        )
        btn_send_now.pack(side="left", padx=(0, 4))

        btn_insert_draft = tk.Button(
            send_card,
            text="📝 Chèn Nháp",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=4,
            cursor="hand2",
            command=lambda: self._send_current_script_to_zalo(auto_enter=False)
        )
        btn_insert_draft.pack(side="left")

        btn_cancel_action = tk.Button(
            send_card,
            text="🛑 Hủy (F9)",
            bg="#dc2626",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=4,
            cursor="hand2",
            command=self.emergency_cancel_all_operations
        )
        btn_cancel_action.pack(side="left", padx=(4, 0))

        btn_reset_script = tk.Button(
            send_card,
            text="🔄 Reset Lỗi",
            bg="#334155",
            fg="#38bdf8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=4,
            cursor="hand2",
            command=self.reset_all_retry_and_error_states
        )
        btn_reset_script.pack(side="left", padx=(4, 0))

        self.script_send_status_lbl = tk.Label(send_card, text="Sẵn sàng gửi.", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b")
        self.script_send_status_lbl.pack(side="right", padx=4)

        # ==================== KHUNG 3: KHO TỆP & LINK ĐÍNH KÈM NHANH ====================
        bundle_f = tk.Frame(parent, bg="#0f172a", padx=6, pady=6)
        self.script_bundle_frame = bundle_f

        # Top Switcher Bar: 📦 Kho Tệp vs 🔗 Đính Kèm Link Khối
        bundle_switcher_bar = tk.Frame(bundle_f, bg="#0f172a")
        bundle_switcher_bar.pack(fill="x", pady=(0, 4))

        self.script_bundle_view_mode = "files"

        self.btn_switch_bundle_files = tk.Button(
            bundle_switcher_bar,
            text="📦 Kho Tệp Đính Kèm",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._switch_bundle_subview("files")
        )
        self.btn_switch_bundle_files.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_switch_bundle_links = tk.Button(
            bundle_switcher_bar,
            text="🔗 Đính Kèm Link Khối",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._switch_bundle_subview("links")
        )
        self.btn_switch_bundle_links.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # --- SUBFRAME 1: KHO TỆP (FILE BUNDLES) ---
        self.script_files_subframe = tk.Frame(bundle_f, bg="#0f172a")
        self.script_files_subframe.pack(fill="both", expand=True)

        # Header Kho Tệp
        bundle_hdr = tk.Frame(self.script_files_subframe, bg="#0f172a")
        bundle_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(bundle_hdr, text="📦 Kho Tệp Đính Kèm Nhanh", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(side="left")
        self.lbl_bundle_checked_count = tk.Label(bundle_hdr, text="✨ Đang tích: 0 tệp", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a")
        self.lbl_bundle_checked_count.pack(side="right")

        # Toolbar Row 1: Thao tác nhóm & file
        tb1 = tk.Frame(self.script_files_subframe, bg="#0f172a")
        tb1.pack(fill="x", pady=(0, 2))
        tk.Button(tb1, text="➕ Nhóm", bg="#059669", fg="white", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._create_new_file_bundle).pack(side="left", padx=1)
        tk.Button(tb1, text="➕ File", bg="#0284c7", fg="white", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._add_files_to_selected_bundle).pack(side="left", padx=1)
        tk.Button(tb1, text="📂 Folder", bg="#0d9488", fg="white", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._add_folder_to_selected_bundle).pack(side="left", padx=1)
        tk.Button(tb1, text="▲", bg="#334155", fg="#f8fafc", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._move_bundle_or_file_up).pack(side="left", padx=1)
        tk.Button(tb1, text="▼", bg="#334155", fg="#f8fafc", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=self._move_bundle_or_file_down).pack(side="left", padx=1)
        tk.Button(tb1, text="✏️", bg="#475569", fg="#f8fafc", font=("Segoe UI", 7), relief="flat", padx=3, pady=1, cursor="hand2", command=self._rename_bundle_or_file).pack(side="left", padx=1)
        tk.Button(tb1, text="🗑️", bg="#475569", fg="#fca5a5", font=("Segoe UI", 7), relief="flat", padx=3, pady=1, cursor="hand2", command=self._delete_bundle_or_file).pack(side="left", padx=1)

        # Toolbar Row 2: Chọn hết / Bỏ chọn / Nạp / Xuất
        tb2 = tk.Frame(self.script_files_subframe, bg="#0f172a")
        tb2.pack(fill="x", pady=(0, 4))
        tk.Button(tb2, text="☑️ Chọn Hết", bg="#334155", fg="#34d399", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._check_all_bundle_files(True)).pack(side="left", padx=1)
        tk.Button(tb2, text="☐ Bỏ Chọn", bg="#334155", fg="#94a3b8", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._check_all_bundle_files(False)).pack(side="left", padx=1)
        tk.Button(tb2, text="📥 Nạp", bg="#334155", fg="#38bdf8", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=self._import_file_bundles).pack(side="right", padx=1)
        tk.Button(tb2, text="📤 Xuất", bg="#334155", fg="#cbd5e1", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=self._export_file_bundles).pack(side="right", padx=1)

        # Treeview Kho Tệp Đính Kèm
        bundle_cols = ("size",)
        self.bundle_tree = ttk.Treeview(self.script_files_subframe, columns=bundle_cols, selectmode="browse")
        self.bundle_tree.heading("#0", text="Tệp / Nhóm Đính Kèm", anchor="w")
        self.bundle_tree.heading("size", text="Dung Lượng", anchor="e")
        self.bundle_tree.column("#0", width=220, stretch=True)
        self.bundle_tree.column("size", width=80, anchor="e")
        self.bundle_tree.pack(fill="both", expand=True)

        # Event bindings
        self.bundle_tree.bind("<Button-1>", self._on_bundle_tree_click)
        self.bundle_tree.bind("<Double-1>", self._on_bundle_tree_double_click)
        self.bundle_tree.bind("<space>", self._on_bundle_tree_space_key)
        self.bundle_tree.bind("<Button-3>", self._on_bundle_tree_right_click)

        # Right-Click Context Menu
        self.bundle_tree_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", activeforeground="white")
        self.bundle_tree_menu.add_command(label="☑️/☐ Bật / Tắt Tích Chọn (Space / Click)", command=self._toggle_selected_bundle_check)
        self.bundle_tree_menu.add_separator()
        self.bundle_tree_menu.add_command(label="➕ Thêm File Vào Nhóm Này...", command=self._add_files_to_selected_bundle)
        self.bundle_tree_menu.add_command(label="📂 Thêm Thư Mục Vào Nhóm Này...", command=self._add_folder_to_selected_bundle)
        self.bundle_tree_menu.add_command(label="✏️ Đổi Tên Nhóm / Tên Hiển Thị File...", command=self._rename_bundle_or_file)
        self.bundle_tree_menu.add_command(label="▲ Di Chuyển Lên Trên", command=self._move_bundle_or_file_up)
        self.bundle_tree_menu.add_command(label="▼ Di Chuyển Xuống Dưới", command=self._move_bundle_or_file_down)
        self.bundle_tree_menu.add_separator()
        self.bundle_tree_menu.add_command(label="📄 Mở File Bằng Ứng Dụng Mặc Định", command=self._open_selected_bundle_file)
        self.bundle_tree_menu.add_command(label="📁 Mở Thư Mục Chứa File (Explorer)", command=self._open_selected_bundle_folder)
        self.bundle_tree_menu.add_separator()
        self.bundle_tree_menu.add_command(label="🗑️ Xóa Mục Này", command=self._delete_bundle_or_file)

        tk.Label(self.script_files_subframe, text="💡 Click dòng để Tích [✓] / Bỏ [ ] | Space: Chọn | Chuột phải: Menu", font=("Segoe UI", 7, "italic"), fg="#94a3b8", bg="#0f172a", anchor="w").pack(fill="x", pady=(3, 0))

        # --- SUBFRAME 2: ĐÍNH KÈM LINK KHỐI (QUICK LINKS BY GRADE - MULTI SELECT) ---
        self.script_links_subframe = tk.Frame(bundle_f, bg="#0f172a")

        # Header Link Khối
        links_top_bar = tk.Frame(self.script_links_subframe, bg="#0f172a")
        links_top_bar.pack(fill="x", pady=(0, 3))
        tk.Label(links_top_bar, text="🔗 Đính Kèm Link Khối:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(side="left")
        self.lbl_links_checked_count = tk.Label(links_top_bar, text="✨ Đang tích: 0 link", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a")
        self.lbl_links_checked_count.pack(side="right")

        # Hàng 1: Nút Menu Chọn Nhiều Khối + Nút Quản Lý Sửa Link
        links_grade_row = tk.Frame(self.script_links_subframe, bg="#0f172a")
        links_grade_row.pack(fill="x", pady=(0, 3))

        self.btn_multi_grade_dropdown = tk.Button(
            links_grade_row,
            text="📚 Chọn Khối (Đa Chọn): [Khối 6] ▾",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._show_multi_grade_dropdown_menu
        )
        self.btn_multi_grade_dropdown.pack(side="left")

        btn_edit_links = tk.Button(
            links_grade_row,
            text="⚙️ Sửa / Thêm Link...",
            font=("Segoe UI", 7, "bold"),
            bg="#6366f1",
            fg="white",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._open_quick_links_manager_modal
        )
        btn_edit_links.pack(side="right")

        # Hàng 2: Thanh Toggle Buttons 9 Khối (K6 -> K12, THCS, THPT)
        self.grade_chip_buttons = {}
        chips_row = tk.Frame(self.script_links_subframe, bg="#0f172a")
        chips_row.pack(fill="x", pady=(0, 3))

        grade_abbrs = [
            ("Khối 6", "K6"),
            ("Khối 7", "K7"),
            ("Khối 8", "K8"),
            ("Khối 9", "K9"),
            ("Khối 10", "K10"),
            ("Khối 11", "K11"),
            ("Khối 12", "K12"),
            ("Link THCS", "THCS"),
            ("Link THPT", "THPT"),
        ]

        for g_full, g_abbr in grade_abbrs:
            b = tk.Button(
                chips_row,
                text=g_abbr,
                font=("Segoe UI", 7, "bold"),
                relief="flat",
                padx=2,
                pady=1,
                cursor="hand2",
                command=lambda g=g_full: self._toggle_quick_link_grade(g)
            )
            b.pack(side="left", padx=1, fill="x", expand=True)
            self.grade_chip_buttons[g_full] = b

        # Hàng 3: Toolbar thao tác (Nhãn, Chọn nhanh Cấp 2, Cấp 3, Tất Cả, Bỏ Hết)
        links_tb_row = tk.Frame(self.script_links_subframe, bg="#0f172a")
        links_tb_row.pack(fill="x", pady=(0, 4))

        chk_incl_label = tk.Checkbutton(
            links_tb_row,
            text="🏷️ Ghi chú nhãn trước link",
            variable=self.quick_links_include_label_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            font=("Segoe UI", 7, "bold")
        )
        chk_incl_label.pack(side="left")

        tk.Button(
            links_tb_row,
            text="☑️ Tất Cả Link",
            bg="#334155",
            fg="#34d399",
            font=("Segoe UI", 7, "bold"),
            relief="flat",
            padx=4,
            pady=1,
            cursor="hand2",
            command=lambda: self._check_all_links_global(True)
        ).pack(side="right", padx=(2, 0))

        tk.Button(
            links_tb_row,
            text="☐ Bỏ Hết Link",
            bg="#334155",
            fg="#94a3b8",
            font=("Segoe UI", 7),
            relief="flat",
            padx=4,
            pady=1,
            cursor="hand2",
            command=lambda: self._check_all_links_global(False)
        ).pack(side="right", padx=2)

        tk.Button(
            links_tb_row,
            text="⚡ Cấp 3",
            bg="#1e293b",
            fg="#a855f7",
            font=("Segoe UI", 7),
            relief="flat",
            padx=3,
            pady=1,
            cursor="hand2",
            command=self._select_thpt_quick_grades
        ).pack(side="right", padx=1)

        tk.Button(
            links_tb_row,
            text="⚡ Cấp 2",
            bg="#1e293b",
            fg="#38bdf8",
            font=("Segoe UI", 7),
            relief="flat",
            padx=3,
            pady=1,
            cursor="hand2",
            command=self._select_thcs_quick_grades
        ).pack(side="right", padx=1)

        # Scrollable Canvas chứa danh sách các link
        links_scroll_f = tk.Frame(self.script_links_subframe, bg="#0f172a")
        links_scroll_f.pack(fill="both", expand=True)

        self.quick_links_canvas = tk.Canvas(links_scroll_f, bg="#0f172a", highlightthickness=0)
        self.quick_links_scrollbar = ttk.Scrollbar(links_scroll_f, orient="vertical", command=self.quick_links_canvas.yview)
        self.quick_links_items_frame = tk.Frame(self.quick_links_canvas, bg="#0f172a")

        self.quick_links_items_frame.bind(
            "<Configure>",
            lambda e: self.quick_links_canvas.configure(scrollregion=self.quick_links_canvas.bbox("all"))
        )
        self._quick_links_canvas_window = self.quick_links_canvas.create_window(
            (0, 0), window=self.quick_links_items_frame, anchor="nw"
        )
        self.quick_links_canvas.configure(yscrollcommand=self.quick_links_scrollbar.set)

        def _on_links_canvas_resize(event):
            self.quick_links_canvas.itemconfig(self._quick_links_canvas_window, width=event.width)
        self.quick_links_canvas.bind("<Configure>", _on_links_canvas_resize)

        self.quick_links_canvas.pack(side="left", fill="both", expand=True)
        self.quick_links_scrollbar.pack(side="right", fill="y")

        tk.Label(
            self.script_links_subframe,
            text="💡 Tích [✓] link để tự động đính kèm khi Gửi hoặc Copy",
            font=("Segoe UI", 7, "italic"),
            fg="#94a3b8",
            bg="#0f172a",
            anchor="w"
        ).pack(fill="x", pady=(3, 0))

        # Hiển thị bố cục Paned ban đầu theo cấu hình
        self._render_script_tab_layout()

        # Nạp dữ liệu danh sách mẫu ban đầu & Kho tệp / Link đính kèm nhanh
        self._refresh_script_categories_cb()
        self._refresh_script_templates_list()
        self._refresh_file_bundles_tree()
        self._render_quick_links_for_category(self.quick_links_selected_grade)

    def _render_script_tab_layout(self):
        """Render bố cục Tab 3 theo cấu hình: 3 cột ngang HOẶC 2 cột (kho tệp ở dưới cột 2)."""
        if not hasattr(self, 'script_paned_container'):
            return

        if hasattr(self, 'script_paned_main') and self.script_paned_main.winfo_exists():
            try:
                for f in (self.script_left_frame, self.script_mid_frame, self.script_bundle_frame):
                    try:
                        self.script_paned_main.forget(f)
                    except Exception:
                        pass
                self.script_paned_main.destroy()
            except Exception:
                pass

        mode = getattr(self, "script_tab_layout", "3_columns")

        if mode == "2_columns_bottom":
            # Bố Cục 2 Cột: Cột 1 (Trái - Mẫu), Cột 2 (Phải - Chia trên dưới: Soạn thảo + Kho Tệp)
            paned_main = tk.PanedWindow(self.script_paned_container, orient="horizontal", bg="#1e293b", sashwidth=4)
            paned_main.pack(fill="both", expand=True)
            self.script_paned_main = paned_main

            paned_main.add(self.script_left_frame, minsize=260, width=340)

            paned_right_vert = tk.PanedWindow(paned_main, orient="vertical", bg="#1e293b", sashwidth=4)
            paned_main.add(paned_right_vert, minsize=380)

            paned_right_vert.add(self.script_mid_frame, minsize=260, height=350)
            paned_right_vert.add(self.script_bundle_frame, minsize=180, height=250)
        else:
            # Bố Cục 3 Cột Ngang (Mặc định)
            paned_main = tk.PanedWindow(self.script_paned_container, orient="horizontal", bg="#1e293b", sashwidth=4)
            paned_main.pack(fill="both", expand=True)
            self.script_paned_main = paned_main

            paned_main.add(self.script_left_frame, minsize=240, width=310)
            paned_main.add(self.script_mid_frame, minsize=320, width=420)
            paned_main.add(self.script_bundle_frame, minsize=250, width=330)

    def _toggle_script_tab_layout(self):
        """Chuyển đổi linh hoạt giữa Bố Cục 3 Cột Ngang và Bố Cục 2 Cột (Kho Tệp Dưới)."""
        current_mode = getattr(self, "script_tab_layout", "3_columns")
        if current_mode == "3_columns":
            self.script_tab_layout = "2_columns_bottom"
            btn_txt = "🔳 Bố Cục: 2 Cột (Kho Tệp Dưới)"
            msg = "Đã chuyển sang Bố Cục 2 Cột: Kho Tệp Đính Kèm hiển thị ở dưới ô soạn thảo!"
        else:
            self.script_tab_layout = "3_columns"
            btn_txt = "🔲 Bố Cục: 3 Cột Ngang"
            msg = "Đã chuyển sang Bố Cục 3 Cột Ngang song song trực quan!"

        if hasattr(self, 'btn_script_layout_toggle'):
            self.btn_script_layout_toggle.configure(text=btn_txt)

        self.app_settings["script_tab_layout"] = self.script_tab_layout
        self._save_app_settings(self.app_settings)
        self._render_script_tab_layout()
        self.show_toast("Bố Cục Tab 3", msg, "info")

    def _toggle_bc_target_mode(self):
        """Chuyển đổi giữa chế độ Khóa Nền Zalo và Gửi Free ở Tab 2."""
        if getattr(self, "bc_direct_target_mode", "target_locked") == "target_locked":
            self.bc_direct_target_mode = "free_mode"
            self.btn_bc_target_mode.configure(
                text="🌐 Gửi Free (Bất Kỳ App)",
                bg="#0284c7"
            )
            self.show_toast("Gửi Free (Tab 2)", "Đã chuyển sang: Gửi Free vào bất kỳ khung nhập văn bản nào đang mở!", "info")
        else:
            self.bc_direct_target_mode = "target_locked"
            self.btn_bc_target_mode.configure(
                text="🔒 Khóa Nền Zalo",
                bg="#8b5cf6"
            )
            self.show_toast("Khóa Nền Zalo (Tab 2)", "Đã chuyển sang: Khóa Nền gửi ngầm vào Zalo PC đang mở!", "info")

    def _send_broadcast_template_to_chat(self, auto_enter: bool = True):
        """Gửi trực tiếp nội dung mẫu tin ở Tab 2 vào khung chat Zalo / Cửa sổ Free đang mở."""
        content = self.tpl_content_txt.get("1.0", tk.END).strip() if hasattr(self, "tpl_content_txt") else ""
        files = list(self.current_attached_files) if hasattr(self, "current_attached_files") else []

        if not content and not files:
            self.show_toast("Nội Dung Trống", "Mẫu tin chưa có nội dung hoặc file để gửi!", "warning")
            return

        is_bg = (getattr(self, "bc_direct_target_mode", "target_locked") == "target_locked")
        target_name = "Zalo Khóa Nền" if is_bg else "Khung Nhập Free (App Bất Kỳ)"
        action_desc = f"Đang gửi vào {target_name}..." if auto_enter else f"Đang chèn nháp vào {target_name}..."
        self.set_footer_task(action_desc)

        retries_cfg = int(self.app_settings.get("max_retries", 5))

        def _worker():
            try:
                ok = ZaloAutomation.send_script_template_to_current_chat(
                    content=content,
                    file_paths=files,
                    background_mode=is_bg,
                    auto_press_enter=auto_enter,
                    max_attempts=retries_cfg
                )

                def _ui_done():
                    try:
                        if not self.winfo_exists():
                            return
                        if ok:
                            msg = f"🎉 Đã gửi thành công vào {target_name}!" if auto_enter else f"📝 Đã chèn nháp vào {target_name}!"
                            self.show_toast("Thành Công", msg, "success")
                            self.set_footer_task("Sẵn sàng.")
                        else:
                            self.show_toast("Dừng Lại Bắt Buộc", f"Gửi thất bại sau {retries_cfg} lần thử liên tiếp. Hãy kiểm tra cửa sổ làm việc!", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_done)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"[Tab 2 Direct Send Error] Lỗi: {e}", exc_info=True)
                def _ui_err():
                    try:
                        if self.winfo_exists():
                            self.show_toast("Lỗi Gửi Tin", f"Đã xảy ra lỗi: {e}", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_err)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_script_target_mode(self):
        """Chuyển đổi giữa chế độ Khóa Nền Zalo và Gửi Free (Bất Kỳ Ứng Dụng Nào)."""
        if self.script_target_mode == "target_locked":
            self.script_target_mode = "free_mode"
            self.btn_script_target_mode.configure(
                text="🌐 GỬI FREE (BẤT KỲ APP NÀO)",
                bg="#0284c7"
            )
            self.show_toast("Chế Độ Gửi Free", "Đã chuyển sang: Gửi Free vào bất kỳ khung nhập văn bản / app nào đang mở trên máy tính!", "info")
        else:
            self.script_target_mode = "target_locked"
            self.btn_script_target_mode.configure(
                text="🔒 KHÓA NỀN ZALO PC (Gửi Ngầm)",
                bg="#8b5cf6"
            )
            self.show_toast("Khóa Nền Zalo", "Đã chuyển sang: Khóa Nền gửi ngầm vào Zalo PC đang mở!", "info")

    def _refresh_script_categories_cb(self):
        """Nạp danh sách Category vào Combobox bộ lọc và Combobox trong trình soạn thảo."""
        cats = self.state.get_script_categories()
        all_cats = ["Tất Cả Danh Mục"] + cats
        if hasattr(self, 'script_category_cb'):
            cur = self.script_category_cb.get()
            self.script_category_cb.configure(values=all_cats)
            if not cur or cur not in all_cats:
                default_choice = "Hỗ Trợ Kỹ Thuật" if "Hỗ Trợ Kỹ Thuật" in all_cats else "Tất Cả Danh Mục"
                self.script_category_cb.set(default_choice)
            else:
                self.script_category_cb.set(cur)

        if hasattr(self, 'script_cat_cb'):
            self.script_cat_cb.configure(values=cats)
            cur_cat = self.script_cat_cb.get()
            if not cur_cat or cur_cat not in cats:
                default_ed = "Hỗ Trợ Kỹ Thuật" if "Hỗ Trợ Kỹ Thuật" in cats else (cats[0] if cats else "Hỗ Trợ Kỹ Thuật")
                self.script_cat_cb.set(default_ed)

    def _open_script_category_manager_modal(self):
        """Mở Modal Quản Lý Danh Mục (Thêm, Đổi tên, Xóa danh mục)."""
        modal = tk.Toplevel(self)
        modal.title("📁 Quản Lý Danh Mục Kịch Bản")
        modal.geometry("450x380")
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()

        tk.Label(modal, text="📁 DANH SÁCH DANH MỤC KỊCH BẢN", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(pady=(12, 6))

        list_f = tk.Frame(modal, bg="#0f172a", padx=14)
        list_f.pack(fill="both", expand=True)

        cat_lb = tk.Listbox(list_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", selectbackground="#0284c7", height=8)
        cat_lb.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(list_f, orient="vertical", command=cat_lb.yview)
        sb.pack(side="right", fill="y")
        cat_lb.configure(yscrollcommand=sb.set)

        def _refresh_modal_cats():
            cat_lb.delete(0, tk.END)
            for c in self.state.get_script_categories():
                cat_lb.insert(tk.END, c)

        _refresh_modal_cats()

        act_f = tk.Frame(modal, bg="#0f172a", padx=14, pady=10)
        act_f.pack(fill="x")

        def _do_add_cat():
            from tkinter import simpledialog
            name = simpledialog.askstring("Thêm Danh Mục", "Nhập tên danh mục mới:", parent=modal)
            if name and name.strip():
                name = name.strip()
                cats = self.state.get_script_categories()
                if name in cats:
                    messagebox.showwarning("Đã Tồn Tại", "Danh mục này đã có trong danh sách!", parent=modal)
                    return
                # Create a sample template with new category so it persists
                self.state.save_script_template(
                    label=f"📝 [Mẫu Mới - {name}]",
                    trigger_question="",
                    answer_content="Dạ em gửi Thầy/Cô thông tin ạ! 😊",
                    file_paths=[],
                    category=name
                )
                _refresh_modal_cats()
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                self.show_toast("Thành Công", f"Đã thêm danh mục '{name}'!", "success")

        def _do_rename_cat():
            sel = cat_lb.curselection()
            if not sel:
                messagebox.showwarning("Chưa Chọn", "Vui lòng chọn 1 danh mục để đổi tên!", parent=modal)
                return
            old_name = cat_lb.get(sel[0])
            from tkinter import simpledialog
            new_name = simpledialog.askstring("Đổi Tên Danh Mục", f"Đổi tên danh mục '{old_name}' thành:", initialvalue=old_name, parent=modal)
            if new_name and new_name.strip() and new_name.strip() != old_name:
                self.state.rename_script_category(old_name, new_name.strip())
                _refresh_modal_cats()
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                self.show_toast("Thành Công", f"Đã đổi tên danh mục thành '{new_name.strip()}'!", "success")

        def _do_delete_cat():
            sel = cat_lb.curselection()
            if not sel:
                messagebox.showwarning("Chưa Chọn", "Vui lòng chọn 1 danh mục để xóa!", parent=modal)
                return
            cat_name = cat_lb.get(sel[0])
            if messagebox.askyesno("Xác Nhận Xóa", f"Bạn có chắc muốn xóa danh mục '{cat_name}'?\nCác mẫu kịch bản thuộc danh mục này sẽ được chuyển sang 'Tư Vấn Chung'.", parent=modal):
                self.state.delete_script_category(cat_name, fallback_cat="Tư Vấn Chung")
                _refresh_modal_cats()
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                self.show_toast("Đã Xóa", f"Đã xóa danh mục '{cat_name}'!", "info")

        tk.Button(act_f, text="➕ Thêm Mới", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=3, cursor="hand2", command=_do_add_cat).pack(side="left", padx=2)
        tk.Button(act_f, text="✏️ Đổi Tên", bg="#0284c7", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=3, cursor="hand2", command=_do_rename_cat).pack(side="left", padx=2)
        tk.Button(act_f, text="🗑️ Xóa", bg="#dc2626", fg="white", font=("Segoe UI", 9), relief="flat", padx=8, pady=3, cursor="hand2", command=_do_delete_cat).pack(side="left", padx=2)

        def _do_export_cats():
            f_path = filedialog.asksaveasfilename(
                title="Xuất Danh Sách Danh Mục",
                defaultextension=".json",
                filetypes=[("JSON File (*.json)", "*.json"), ("Text File (*.txt)", "*.txt")],
                initialfile="script_categories.json",
                parent=modal
            )
            if f_path:
                cnt = self.state.export_script_categories_to_file(f_path)
                messagebox.showinfo("Xuất Thành Công", f"Đã xuất thành công {cnt} danh mục ra file:\n{f_path}", parent=modal)

        def _do_import_cats():
            f_path = filedialog.askopenfilename(
                title="Nạp Danh Sách Danh Mục",
                filetypes=[("JSON/Text File (*.json, *.txt)", "*.json *.txt"), ("Tất cả (*.*)", "*.*")],
                parent=modal
            )
            if f_path:
                cnt = self.state.import_script_categories_from_file(f_path)
                _refresh_modal_cats()
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                messagebox.showinfo("Nạp Thành Công", f"Đã nạp thêm {cnt} danh mục mới vào hệ thống!", parent=modal)

        act_f2 = tk.Frame(modal, bg="#0f172a", padx=14, pady=4)
        act_f2.pack(fill="x")
        tk.Button(act_f2, text="📤 Xuất Danh Mục", bg="#0284c7", fg="white", font=("Segoe UI", 8), relief="flat", padx=8, pady=3, cursor="hand2", command=_do_export_cats).pack(side="left", padx=2)
        tk.Button(act_f2, text="📥 Nạp Danh Mục", bg="#0d9488", fg="white", font=("Segoe UI", 8), relief="flat", padx=8, pady=3, cursor="hand2", command=_do_import_cats).pack(side="left", padx=2)
        tk.Button(act_f2, text="Đóng", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=12, pady=3, cursor="hand2", command=modal.destroy).pack(side="right", padx=2)

    def _refresh_script_templates_list(self):
        """Quét và nạp lại danh sách mẫu kịch bản lên Treeview."""
        query = self.script_search_var.get().strip() if hasattr(self, 'script_search_var') else ""
        cat = self.script_category_cb.get().strip() if hasattr(self, 'script_category_cb') else ""

        items = self.state.get_all_script_templates(search_query=query, category_filter=cat)
        
        # Xóa dữ liệu cũ
        for item in self.script_tree.get_children():
            self.script_tree.delete(item)

        for s in items:
            f_count = len(s.get('file_paths', []))
            f_str = f"📁 {f_count}" if f_count > 0 else "-"
            q_short = s.get('trigger_question', '')
            if len(q_short) > 40:
                q_short = q_short[:38] + "..."
            self.script_tree.insert(
                "",
                "end",
                iid=str(s['id']),
                values=(
                    s['label'],
                    s.get('category', 'Tư Vấn Mua'),
                    q_short,
                    f_str
                )
            )

        if hasattr(self, 'lbl_script_count'):
            self.lbl_script_count.configure(text=f"📋 Danh Sách Mẫu Kịch Bản [{len(items)} mẫu]")

        # Tự động chọn dòng đầu tiên nếu chưa chọn
        children = self.script_tree.get_children()
        if children:
            if not self.current_script_id or str(self.current_script_id) not in children:
                self.script_tree.selection_set(children[0])
                self.script_tree.focus(children[0])
                self._load_script_to_editor(int(children[0]))

    def _on_script_search_changed(self, event=None):
        self._refresh_script_templates_list()

    def _on_script_category_filter_changed(self, event=None):
        self._refresh_script_templates_list()

    def _on_script_template_selected(self, event=None):
        sel = self.script_tree.selection()
        if sel:
            t_id = int(sel[0])
            self._load_script_to_editor(t_id)

    def _on_script_tree_right_click(self, event):
        """Click chuột phải vào dòng trong danh sách: Nếu chưa chọn thì chọn dòng đó, hiển thị context menu."""
        row_id = self.script_tree.identify_row(event.y)
        if row_id:
            current_sel = self.script_tree.selection()
            if row_id not in current_sel:
                self.script_tree.selection_set(row_id)
                self.script_tree.focus(row_id)
                self._load_script_to_editor(int(row_id))
            try:
                self.script_tree_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.script_tree_menu.grab_release()

    def _change_category_for_current_template(self):
        """Đổi nhanh danh mục cho mẫu kịch bản đang chọn."""
        if not self.current_script_id:
            return
        item = self.state.get_script_template(self.current_script_id)
        if not item:
            return
        from tkinter import simpledialog
        cats = self.state.get_script_categories()
        prompt_txt = f"Các danh mục hiện có: {', '.join(cats)}\n\nNhập danh mục mới cho mẫu '{item['label']}':"
        new_cat = simpledialog.askstring("Đổi Danh Mục", prompt_txt, initialvalue=item.get('category', 'Tư Vấn Mua'), parent=self)
        if new_cat and new_cat.strip():
            self.state.save_script_template(
                label=item['label'],
                trigger_question=item.get('trigger_question', ''),
                answer_content=item.get('answer_content', ''),
                file_paths=item.get('file_paths', []),
                category=new_cat.strip(),
                template_id=self.current_script_id
            )
            self._refresh_script_categories_cb()
            self._refresh_script_templates_list()
            self._load_script_to_editor(self.current_script_id)
            self.show_toast("Thành Công", f"Đã chuyển mẫu sang danh mục '{new_cat.strip()}'!", "success")

    def _export_script_templates(self):
        """Xuất danh sách mẫu kịch bản ra file JSON hoặc CSV."""
        cat_filter = self.script_category_cb.get().strip() if hasattr(self, 'script_category_cb') else ""
        if cat_filter == "Tất Cả Danh Mục":
            cat_filter = None

        default_fname = f"script_templates_{cat_filter or 'all'}.json".replace(" ", "_")
        f_path = filedialog.asksaveasfilename(
            title="Xuất Mẫu Kịch Bản Trả Lời Nhanh",
            defaultextension=".json",
            filetypes=[("JSON File (*.json)", "*.json"), ("CSV File (*.csv)", "*.csv")],
            initialfile=default_fname
        )
        if f_path:
            try:
                cnt = self.state.export_script_templates_to_file(f_path, category_filter=cat_filter)
                self.show_toast("Xuất Thành Công", f"Đã xuất {cnt} mẫu kịch bản ra file:\n{os.path.basename(f_path)}", "success")
            except Exception as e:
                self.show_toast("Lỗi Xuất File", f"Đã xảy ra lỗi khi xuất file: {e}", "error")

    def _import_script_templates(self):
        """Nạp danh sách mẫu kịch bản từ file JSON hoặc CSV."""
        f_path = filedialog.askopenfilename(
            title="Nạp Mẫu Kịch Bản Từ File",
            filetypes=[("JSON / CSV File (*.json, *.csv)", "*.json *.csv"), ("Tất Cả File (*.*)", "*.*")]
        )
        if not f_path:
            return

        # Hỏi chế độ nạp: Gộp thêm hay Ghi đè
        answer = messagebox.askyesnocancel(
            "Tùy Chọn Nạp Mẫu",
            "Bạn có muốn GỘP THÊM (Append) vào danh sách mẫu hiện có?\n\n- Chọn 'Yes': Gộp thêm vào danh sách mẫu hiện tại.\n- Chọn 'No': XÓA HẾT MẪU CŨ và thay bằng mẫu từ file.\n- Chọn 'Cancel': Hủy bỏ không nạp.",
            icon="question"
        )
        if answer is None:
            return

        mode = "merge" if answer is True else "replace"
        try:
            res = self.state.import_script_templates_from_file(f_path, mode=mode)
            cnt = res.get("imported_count", 0)
            self._refresh_script_categories_cb()
            self._refresh_script_templates_list()
            mode_str = "Gộp thêm" if mode == "merge" else "Ghi đè thay thế"
            self.show_toast("Nạp Thành Công", f"Đã {mode_str} thành công {cnt} mẫu kịch bản từ file!", "success")
        except Exception as e:
            self.show_toast("Lỗi Nạp File", f"Đã xảy ra lỗi khi nạp file: {e}", "error")

    def _export_selected_template(self):
        """Xuất riêng 1 mẫu kịch bản đang chọn ra file JSON."""
        if not self.current_script_id:
            self.show_toast("Chưa Chọn", "Vui lòng chọn 1 mẫu kịch bản để xuất!", "warning")
            return
        item = self.state.get_script_template(self.current_script_id)
        if not item:
            return
        safe_name = "".join([c for c in item['label'] if c.isalnum() or c in (' ', '_', '-')]).strip()
        f_path = filedialog.asksaveasfilename(
            title="Xuất Mẫu Kịch Bản Đang Chọn",
            defaultextension=".json",
            filetypes=[("JSON File (*.json)", "*.json")],
            initialfile=f"template_{safe_name}.json"
        )
        if f_path:
            try:
                with open(f_path, "w", encoding="utf-8") as f:
                    json.dump({"template": item}, f, ensure_ascii=False, indent=2)
                self.show_toast("Xuất Thành Công", f"Đã xuất mẫu '{item['label']}' ra file!", "success")
            except Exception as e:
                self.show_toast("Lỗi Xuất File", f"Đã xảy ra lỗi: {e}", "error")

    def _load_script_to_editor(self, template_id: int):
        """Nạp dữ liệu mẫu kịch bản vào khung soạn thảo / xem trước bên phải."""
        item = self.state.get_script_template(template_id)
        if not item:
            return

        self.current_script_id = item['id']
        self.script_label_entry.delete(0, tk.END)
        self.script_label_entry.insert(0, item.get('label', ''))

        self.script_cat_cb.set(item.get('category', 'Tư Vấn Mua'))

        self.script_q_entry.delete(0, tk.END)
        self.script_q_entry.insert(0, item.get('trigger_question', ''))

        self.script_ans_txt.delete("1.0", tk.END)
        self.script_ans_txt.insert("1.0", item.get('answer_content', ''))

        self.current_script_attached_files = list(item.get('file_paths', []))
        self._update_script_files_listbox_ui()
        self.script_send_status_lbl.configure(text=f"Đã nạp: {item.get('label', '')[:25]}", fg="#34d399")

    def _update_script_files_listbox_ui(self):
        """Cập nhật Listbox file đính kèm và thống kê số lượng loại file."""
        self.script_files_listbox.delete(0, tk.END)
        count_word = 0
        count_ppt = 0
        count_pdf = 0
        count_excel = 0
        count_video = 0
        count_img = 0
        count_dir = 0
        count_other = 0
        missing_count = 0

        for f in self.current_script_attached_files:
            exists = os.path.exists(f)
            if not exists:
                missing_count += 1
                missing_flag = "⚠️ [THIẾU TRÊN MÁY NÀY] "
            else:
                missing_flag = ""

            if os.path.isdir(f):
                count_dir += 1
                icon = "📂 [Thư mục]"
            else:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".3gp"]:
                    count_video += 1
                    icon = "🎬 [Video]"
                elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"]:
                    count_img += 1
                    icon = "🖼️ [Ảnh]"
                elif ext in [".docx", ".doc", ".rtf", ".txt", ".md"]:
                    count_word += 1
                    icon = "📄 [Word/Doc]"
                elif ext in [".pptx", ".ppt", ".pps", ".ppsx"]:
                    count_ppt += 1
                    icon = "📊 [PowerPoint]"
                elif ext in [".xlsx", ".xls", ".csv"]:
                    count_excel += 1
                    icon = "📈 [Excel]"
                elif ext in [".pdf"]:
                    count_pdf += 1
                    icon = "📑 [PDF]"
                else:
                    count_other += 1
                    icon = "📎 [Tệp]"
            self.script_files_listbox.insert(tk.END, f"{missing_flag}{icon} {os.path.basename(f)}  ({f})")

        total_items = len(self.current_script_attached_files)
        if total_items == 0:
            self.lbl_script_file_count_summary.configure(
                text="📊 Đính kèm: 0 file (Chưa chọn file)",
                fg="#94a3b8"
            )
        else:
            parts = []
            if count_word: parts.append(f"📄 {count_word} Word")
            if count_ppt: parts.append(f"📊 {count_ppt} PPT")
            if count_pdf: parts.append(f"📑 {count_pdf} PDF")
            if count_excel: parts.append(f"📈 {count_excel} Excel")
            if count_video: parts.append(f"🎬 {count_video} Video")
            if count_img: parts.append(f"🖼️ {count_img} Ảnh")
            if count_dir: parts.append(f"📂 {count_dir} Thư mục")
            if count_other: parts.append(f"📎 {count_other} File khác")

            sum_text = f"📊 Tổng: {total_items} mục"
            if parts:
                sum_text += " (" + ", ".join(parts) + ")"
            if missing_count > 0:
                sum_text += f" | ⚠️ Có {missing_count} file không tìm thấy trên ổ đĩa máy này!"
                self.lbl_script_file_count_summary.configure(text=sum_text, fg="#f87171")
            else:
                self.lbl_script_file_count_summary.configure(text=sum_text, fg="#38bdf8")

    def _add_files_to_script_template(self):
        file_filters = [
            ("Tất cả định dạng hỗ trợ (Video, Ảnh, Office, Zip, Rar, 7z, PDF)", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.png *.jpg *.jpeg *.gif *.webp *.bmp *.docx *.doc *.pptx *.ppt *.xlsx *.xls *.pdf *.txt *.csv *.zip *.rar *.7z *.tar *.gz *.mp3 *.wav"),
            ("🎬 Video / Media (*.mp4, *.mov, *.avi...)", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.3gp"),
            ("🖼️ Hình ảnh (*.png, *.jpg, *.jpeg...)", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg"),
            ("📄 Văn phòng & PDF (*.docx, *.pptx, *.xlsx, *.pdf...)", "*.docx *.doc *.pptx *.ppt *.xlsx *.xls *.pdf *.txt *.csv *.rtf"),
            ("🌐 Tất cả các loại file (*.*)", "*.*")
        ]
        file_paths = filedialog.askopenfilenames(
            title="Chọn file đính kèm cho Kịch Bản Trả Lời Nhanh",
            filetypes=file_filters
        )
        if file_paths:
            for p in file_paths:
                if p not in self.current_script_attached_files:
                    self.current_script_attached_files.append(p)
            self._update_script_files_listbox_ui()
            self.show_toast("Đã Thêm File", f"Đã thêm {len(file_paths)} file vào kịch bản!", "info")

    def _add_folder_to_script_template(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục chứa tài liệu để đính kèm vào kịch bản")
        if folder_path and folder_path not in self.current_script_attached_files:
            self.current_script_attached_files.append(folder_path)
            self._update_script_files_listbox_ui()
            self.show_toast("Đã Thêm Thư Mục", f"Đã thêm thư mục '{os.path.basename(folder_path)}'!", "info")

    def _remove_selected_file_from_script(self):
        sel = self.script_files_listbox.curselection()
        if sel:
            idx = sel[0]
            del self.current_script_attached_files[idx]
            self._update_script_files_listbox_ui()

    def _clear_all_script_files(self):
        self.current_script_attached_files.clear()
        self._update_script_files_listbox_ui()

    def _create_new_script_template(self):
        """Tạo mới 1 mẫu kịch bản trống và focus con trỏ vào ô nhập liệu."""
        current_filter_cat = self.script_category_cb.get().strip() if hasattr(self, 'script_category_cb') else ""
        if not current_filter_cat or current_filter_cat == "Tất Cả Danh Mục":
            current_filter_cat = "Hỗ Trợ Kỹ Thuật"

        # Xóa tìm kiếm để đảm bảo mẫu mới hiển thị ngay
        if hasattr(self, 'script_search_var'):
            self.script_search_var.set("")

        new_id = self.state.save_script_template(
            label="📝 [Mẫu Mới]: Nhập tiêu đề mẫu",
            trigger_question="",
            answer_content="",
            file_paths=[],
            category=current_filter_cat
        )
        self._refresh_script_categories_cb()
        self._refresh_script_templates_list()
        if str(new_id) in self.script_tree.get_children():
            self.script_tree.selection_set(str(new_id))
            self.script_tree.focus(str(new_id))
            self._load_script_to_editor(new_id)

        # Focus con trỏ vào ô nhập nhãn để người dùng gõ ngay
        if hasattr(self, 'script_label_entry'):
            self.script_label_entry.focus_set()
            self.script_label_entry.select_range(0, tk.END)

        self.show_toast("Tạo Mẫu Mới", "Đã tạo mẫu mới thành công! Hãy nhập nhãn và nội dung ở khung bên phải.", "success")

    def _duplicate_current_script_template(self):
        """Nhân bản mẫu kịch bản đang chọn."""
        if not self.current_script_id:
            self.show_toast("Chưa Chọn", "Vui lòng chọn 1 mẫu kịch bản cần nhân bản!", "warning")
            return
        new_id = self.state.duplicate_script_template(self.current_script_id)
        if new_id:
            self._refresh_script_templates_list()
            if str(new_id) in self.script_tree.get_children():
                self.script_tree.selection_set(str(new_id))
                self.script_tree.focus(str(new_id))
                self._load_script_to_editor(new_id)
            self.show_toast("Nhân Bản", "Đã nhân bản mẫu kịch bản thành công!", "success")

    def _delete_current_script_template(self):
        """Xóa các mẫu kịch bản đang chọn (hỗ trợ xóa 1 hoặc nhiều mẫu cùng lúc)."""
        sel = self.script_tree.selection() if hasattr(self, 'script_tree') else ()
        if not sel:
            if not self.current_script_id:
                self.show_toast("Chưa Chọn", "Vui lòng chọn ít nhất 1 mẫu kịch bản cần xóa!", "warning")
                return
            sel = [str(self.current_script_id)]

        all_items = self.state.get_all_script_templates()
        if len(all_items) <= len(sel):
            self.show_toast("Không Thể Xóa", "Cần giữ lại ít nhất 1 mẫu kịch bản trong hệ thống!", "warning")
            return

        count = len(sel)
        if count == 1:
            sid = int(sel[0])
            tpl = self.state.get_script_template(sid)
            lbl = tpl.get("label", "này") if tpl else "này"
            if messagebox.askyesno("Xác Nhận Xóa", f"Bạn có chắc chắn muốn xóa mẫu kịch bản '{lbl}'?"):
                self.state.delete_script_template(sid)
                self.current_script_id = None
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                self.show_toast("Đã Xóa", f"Đã xóa mẫu '{lbl}' thành công!", "info")
        else:
            if messagebox.askyesno("Xác Nhận Xóa Nhiều", f"Bạn có chắc chắn muốn XÓA {count} mẫu kịch bản đang chọn?"):
                for iid in sel:
                    try:
                        self.state.delete_script_template(int(iid))
                    except Exception:
                        pass
                self.current_script_id = None
                self._refresh_script_categories_cb()
                self._refresh_script_templates_list()
                self.show_toast("Đã Xóa", f"Đã xóa {count} mẫu kịch bản thành công!", "info")

    def _save_current_script_template(self):
        """Lưu các thay đổi của mẫu kịch bản hiện tại."""
        lbl = self.script_label_entry.get().strip()
        cat = self.script_cat_cb.get().strip()
        q = self.script_q_entry.get().strip()
        ans = self.script_ans_txt.get("1.0", tk.END).strip()

        if not lbl:
            lbl = "Mẫu Kịch Bản Chưa Đặt Tên"
        if not cat:
            cat = "Tư Vấn Chung"

        t_id = self.state.save_script_template(
            label=lbl,
            trigger_question=q,
            answer_content=ans,
            file_paths=self.current_script_attached_files,
            category=cat,
            template_id=self.current_script_id
        )
        self.current_script_id = t_id
        self._refresh_script_categories_cb()
        self._refresh_script_templates_list()
        self.show_toast("Đã Lưu (Ctrl+S)", f"Đã lưu thành công mẫu '{lbl}'!", "success")

    def _track_foreground_window(self):
        """Định kỳ ghi nhận cửa sổ làm việc bên ngoài (AnyDesk, UltraViewer, Zalo...) tối ưu hóa CPU & RAM."""
        if HAS_WIN32:
            try:
                curr = win32gui.GetForegroundWindow()
                last_h = getattr(self, '_last_tracked_hwnd', None)
                if curr and curr != last_h and win32gui.IsWindow(curr):
                    self._last_tracked_hwnd = curr
                    title = win32gui.GetWindowText(curr)
                    if "AI Zalo CSKH" not in title and "Quản Lý Danh Mục" not in title and title.strip():
                        ZaloAutomation._last_external_hwnd = curr
            except Exception:
                pass

        # Quản lý RAM: Kích hoạt dọn rác bộ nhớ (gc.collect) mỗi 60 giây
        self._gc_tick_count = getattr(self, '_gc_tick_count', 0) + 1
        if self._gc_tick_count >= 60:
            self._gc_tick_count = 0
            try:
                import gc
                gc.collect()
            except Exception:
                pass

        self.after(1000, self._track_foreground_window)

    def _on_global_ctrl_s(self, event=None):
        """Phím tắt Ctrl+S thông minh theo ngữ cảnh riêng biệt của từng Tab."""
        cur_tab = getattr(self, "active_main_tab", "chat")
        if cur_tab == "script":
            self._save_current_script_template()
            return "break"
        elif cur_tab == "crm":
            self._save_current_customer()
            return "break"
        elif cur_tab == "settings":
            self._save_all_settings_from_ui()
            return "break"
        elif cur_tab == "corrections":
            if hasattr(self, '_save_current_correction'):
                self._save_current_correction()
            return "break"

    def emergency_cancel_all_operations(self):
        """HỦY KHẨN CẤP MỌI THAO TÁC TỰ ĐỘNG, GỬI NGẦM, CHIẾN DỊCH GỬI NHÓM & TẠM DỪNG BOT (F9)."""
        # 1. Bật cờ dừng khẩn cấp cho ZaloAutomation
        ZaloAutomation.request_abort()

        # 2. Tạm dừng Bot CSKH nếu đang chạy
        if hasattr(self, 'handler') and self.handler:
            try:
                self.handler.pause()
            except Exception:
                pass

        # 3. Hủy chiến dịch gửi tin nhóm nếu đang chạy
        if hasattr(self, 'broadcast_in_progress') and self.broadcast_in_progress:
            self.broadcast_in_progress = False
            if hasattr(self, 'btn_broadcast_pause'):
                self.btn_broadcast_pause.configure(text="⏸️ Tạm Dừng Gửi", state="disabled")
            if hasattr(self, 'btn_broadcast_cancel'):
                self.btn_broadcast_cancel.configure(state="disabled")

        # 4. Cập nhật UI trạng thái Tab 3
        if hasattr(self, 'script_send_status_lbl'):
            self.script_send_status_lbl.configure(text="🛑 Đã hủy mọi thao tác!", fg="#f87171")

        # 5. Cập nhật UI Header & Footer
        self._update_bot_ui_state(is_running=False)
        self.set_footer_task("🛑 Đã hủy toàn bộ thao tác tự động (F9).")

        # 6. Hiển thị Toast thông báo nổi bật
        self.show_toast("🛑 ĐÃ HỦY MỌI THAO TÁC (F9)", "Đã lập tức dừng gửi ngầm, dừng bot và khôi phục quyền kiểm soát!", "error", duration_ms=3500)

        # 7. Tự động reset lại cờ abort sau 1.2s để người dùng có thể gửi lại bình thường
        self.after(1200, lambda: ZaloAutomation.reset_abort())

    def _send_current_script_to_zalo(self, auto_enter: bool = True):
        """
        Gửi nội dung mẫu kịch bản, link khối đính kèm và files vào vùng soạn thảo Zalo PC đang mở hiện tại hoặc UltraViewer/AnyDesk.
        Tự động gộp:
        1. Nội dung mẫu kịch bản.
        2. Các link khối đang được tích chọn (mỗi link 1 hàng, có/không nhãn theo tùy chọn).
        3. Các file đính kèm cố định của mẫu + các file đang được tích chọn trong Kho Tệp Linh Hoạt.
        - auto_enter = True: Gửi luôn (Enter).
        - auto_enter = False: Chèn vào ô chat (Draft) để người dùng xem trước.
        """
        ans = self.script_ans_txt.get("1.0", tk.END).strip() if hasattr(self, 'script_ans_txt') else ""
        fixed_files = list(getattr(self, 'current_script_attached_files', []))
        bundle_files = self._get_checked_bundle_file_paths()
        files = list(dict.fromkeys(fixed_files + bundle_files))

        # Tự động gộp các link khối đang được tích chọn
        links_str = self._get_checked_quick_links_formatted()
        if links_str:
            if ans:
                ans = f"{ans}\n\n{links_str}"
            else:
                ans = links_str

        if not ans and not files:
            self.show_toast("Nội Dung Rỗng", "Mẫu kịch bản chưa có nội dung, link khối hoặc tệp đính kèm để gửi!", "warning")
            return

        is_bg = (getattr(self, 'script_target_mode', 'target_locked') == "target_locked")
        retries_cfg = int(self.app_settings.get("max_retries", 5))
        target_name = "Zalo PC Khóa Nền" if is_bg else "Khung Nhập Free (App Bất Kỳ)"
        file_desc = f" ({len(files)} tệp)" if files else ""
        links_count = self._get_checked_quick_links_count()
        links_desc = f" ({links_count} link)" if links_count else ""
        action_desc = f"Đang gửi vào {target_name}{links_desc}{file_desc}..." if auto_enter else f"Đang chèn nháp vào {target_name}{links_desc}{file_desc}..."
        if hasattr(self, 'script_send_status_lbl'):
            self.script_send_status_lbl.configure(text=action_desc, fg="#fbbf24")
        self.set_footer_task(action_desc)

        def _worker():
            try:
                ZaloAutomation.reset_abort()
                ok = ZaloAutomation.send_script_template_to_current_chat(
                    content=ans,
                    file_paths=files,
                    background_mode=is_bg,
                    auto_press_enter=auto_enter,
                    max_attempts=retries_cfg
                )

                def _ui_done():
                    try:
                        if not self.winfo_exists():
                            return
                        if ok:
                            note_parts = []
                            if links_count:
                                note_parts.append(f"{links_count} link khối")
                            if files:
                                note_parts.append(f"{len(files)} tệp")
                            note = f" kèm {', '.join(note_parts)}" if note_parts else ""
                            msg = f"🎉 Đã gửi thành công vào {target_name}{note}!" if auto_enter else f"📝 Đã chèn nháp vào {target_name}{note}!"
                            if hasattr(self, 'script_send_status_lbl'):
                                self.script_send_status_lbl.configure(text=msg, fg="#34d399")
                            self.show_toast("Thành Công", msg, "success")
                            self.set_footer_task("Sẵn sàng.")
                        else:
                            if hasattr(self, 'script_send_status_lbl'):
                                self.script_send_status_lbl.configure(text=f"🛑 Đã dừng lại sau {retries_cfg} lần thử lỗi!", fg="#f87171")
                            self.show_toast("Dừng Lại Bắt Buộc", f"Gửi thất bại sau {retries_cfg} lần thử liên tiếp. Đã dừng lại bắt buộc để tránh lặp!", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_done)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"[Script Send Error] Lỗi khi gửi kịch bản: {e}", exc_info=True)
                def _ui_err():
                    try:
                        if self.winfo_exists():
                            if hasattr(self, 'script_send_status_lbl'):
                                self.script_send_status_lbl.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")
                            self.show_toast("Lỗi Gửi Kịch Bản", f"Đã xảy ra lỗi: {e}", "error")
                    except Exception:
                        pass
                try:
                    self.after(0, _ui_err)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _on_script_tree_double_click(self, event=None):
        """Bấm đúp chuột vào mẫu: Gửi ngay hoặc chèn nháp tùy theo cài đặt."""
        mode = self.app_settings.get("script_send_mode", "Gửi Ngay Vào Zalo (Enter)")
        auto_enter = "Gửi Ngay" in mode
        self._send_current_script_to_zalo(auto_enter=auto_enter)

    def _on_script_tree_enter_key(self, event=None):
        """Nhấn Enter trên bàn phím: Gửi ngay hoặc chèn nháp tùy theo cài đặt."""
        mode = self.app_settings.get("script_send_mode", "Gửi Ngay Vào Zalo (Enter)")
        auto_enter = "Gửi Ngay" in mode
        self._send_current_script_to_zalo(auto_enter=auto_enter)
        return "break"

    def _on_script_tree_ctrl_enter_key(self, event=None):
        """Nhấn Ctrl+Enter trên bàn phím: Luôn chèn nháp vào Zalo / Cửa sổ."""
        self._send_current_script_to_zalo(auto_enter=False)
        return "break"

    def _on_script_tree_ctrl_c(self, event=None):
        """Sao chép nhanh câu trả lời hoặc câu hỏi từ các mẫu đang chọn trong Treeview (Shift+Up/Down, Ctrl+Click)."""
        self._copy_current_script_answer(copy_mode="answer")
        return "break"

    def _copy_current_script_answer(self, copy_mode: str = "answer"):
        """
        Sao chép nội dung câu trả lời / câu hỏi / cả hai từ các mẫu kịch bản đang chọn vào Clipboard.
        Tự động gộp các link khối đang được tích chọn nếu sao chép câu trả lời.
        """
        links_str = self._get_checked_quick_links_formatted() if copy_mode in ("answer", "both") else ""
        sel = self.script_tree.selection() if hasattr(self, 'script_tree') else ()
        if not sel:
            ans = self.script_ans_txt.get("1.0", tk.END).strip() if hasattr(self, 'script_ans_txt') else ""
            if links_str:
                ans = f"{ans}\n\n{links_str}" if ans else links_str
            if not ans:
                self.show_toast("Chưa Chọn Mẫu", "Vui lòng chọn ít nhất 1 mẫu kịch bản hoặc tích chọn link để sao chép!", "warning")
                return
            try:
                import pyperclip
                pyperclip.copy(ans)
            except Exception:
                self.clipboard_clear()
                self.clipboard_append(ans)
            self.show_toast("Đã Sao Chép (Ctrl+C)", "Đã sao chép nội dung câu trả lời và link đính kèm vào Clipboard!", "success")
            return

        items = []
        for iid in sel:
            try:
                tpl = self.state.get_script_template(int(iid))
                if tpl:
                    items.append(tpl)
            except Exception:
                pass

        if not items:
            self.show_toast("Thông Báo", "Không tìm thấy dữ liệu mẫu kịch bản để sao chép!", "warning")
            return

        texts = []
        for tpl in items:
            q = tpl.get("trigger_question", "").strip()
            ans = tpl.get("answer_content", "").strip()
            lbl = tpl.get("label", "").strip()
            if links_str and copy_mode in ("answer", "both"):
                ans = f"{ans}\n\n{links_str}" if ans else links_str

            if copy_mode == "question":
                texts.append(q if q else f"[{lbl}]")
            elif copy_mode == "both":
                header = f"=== 📌 {lbl} ==="
                q_part = f"❓ Câu hỏi: {q}" if q else ""
                ans_part = f"💬 Trả lời:\n{ans}" if ans else ""
                full = "\n".join([p for p in [header, q_part, ans_part] if p])
                texts.append(full)
            else:
                texts.append(ans if ans else f"[{lbl} - Chưa có nội dung câu trả lời]")

        joined = "\n\n----------------------------------------\n\n".join(texts) if len(texts) > 1 else texts[0]

        try:
            import pyperclip
            pyperclip.copy(joined)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(joined)

        mode_name = "câu trả lời" if copy_mode == "answer" else ("câu hỏi" if copy_mode == "question" else "toàn bộ câu hỏi & trả lời")
        if len(items) == 1:
            lbl_short = items[0].get("label", "")[:30]
            self.show_toast("Đã Sao Chép (Ctrl+C)", f"Đã sao chép {mode_name} của mẫu '{lbl_short}'!", "success")
        else:
            self.show_toast("Đã Sao Chép (Ctrl+C)", f"Đã sao chép {mode_name} của {len(items)} mẫu kịch bản đã chọn!", "success")

    # =========================================================================
    # KHO TỆP ĐÍNH KÈM NHANH LINH HOẠT THEO NHÓM (TAB 3 QUICK FILE BUNDLES)
    # =========================================================================
    def _format_bundle_file_size(self, f_path: str) -> str:
        """Định dạng dung lượng tệp ngắn gọn."""
        try:
            if os.path.isfile(f_path):
                sz = os.path.getsize(f_path)
                if sz < 1024:
                    return f"{sz} B"
                elif sz < 1024 * 1024:
                    return f"{sz / 1024:.1f} KB"
                else:
                    return f"{sz / (1024 * 1024):.1f} MB"
            elif os.path.isdir(f_path):
                return "📁 Thư mục"
        except Exception:
            pass
        return ""

    def _refresh_file_bundles_tree(self):
        """Nạp lại danh sách nhóm và file trong Kho Tệp Đính Kèm Nhanh."""
        if not hasattr(self, 'bundle_tree'):
            return

        bundles = self.state.get_all_file_bundles()
        # Nếu chưa có nhóm nào, tạo 3 nhóm mẫu ban đầu
        if not bundles:
            self.state.save_file_bundle("[Lớp 10]", [])
            self.state.save_file_bundle("[Lớp 11]", [])
            self.state.save_file_bundle("[PPCT & Đề Thi]", [])
            bundles = self.state.get_all_file_bundles()

        self._file_bundles_data = bundles
        for item in self.bundle_tree.get_children():
            self.bundle_tree.delete(item)

        total_checked_files = 0

        for b in bundles:
            b_id = b["id"]
            g_name = b["group_name"]
            files = b.get("file_paths", [])
            
            # Tính số lượng file được tích chọn trong nhóm
            chk_count = sum(1 for f in files if isinstance(f, dict) and f.get("checked", True))
            total_checked_files += chk_count

            if not files:
                grp_icon = "[ ]"
            elif chk_count == len(files):
                grp_icon = "[✓]"
            elif chk_count > 0:
                grp_icon = "[~]"
            else:
                grp_icon = "[ ]"

            g_iid = f"g_{b_id}"
            g_text = f"{grp_icon} 📁 {g_name} ({len(files)} tệp)"
            self.bundle_tree.insert("", "end", iid=g_iid, text=g_text, values=(f"{len(files)} tệp",), open=True)

            for idx, f in enumerate(files):
                f_path = f.get("path", "") if isinstance(f, dict) else str(f)
                f_name = f.get("name") if isinstance(f, dict) else os.path.basename(f_path)
                f_chk = "[✓]" if (isinstance(f, dict) and f.get("checked", True)) else "[ ]"
                f_size = self._format_bundle_file_size(f_path)
                f_iid = f"f_{b_id}_{idx}"
                f_text = f"  {f_chk} 📄 {f_name}"
                self.bundle_tree.insert(g_iid, "end", iid=f_iid, text=f_text, values=(f_size,))

        if hasattr(self, 'lbl_bundle_checked_count'):
            self.lbl_bundle_checked_count.configure(text=f"✨ Đang tích: {total_checked_files} tệp")

    def _get_checked_bundle_file_paths(self) -> List[str]:
        """Lấy danh sách tất cả đường dẫn tệp đang được tích chọn [✓] trong Kho Tệp."""
        checked = []
        for b in getattr(self, "_file_bundles_data", []):
            for f in b.get("file_paths", []):
                p = f.get("path", "") if isinstance(f, dict) else str(f)
                is_chk = f.get("checked", True) if isinstance(f, dict) else True
                if is_chk and p:
                    checked.append(p)
        return checked

    def _on_bundle_tree_click(self, event):
        """Xử lý khi nhấp chuột vào dòng trong Treeview để bật/tắt tích chọn [✓] / [ ]."""
        iid = self.bundle_tree.identify_row(event.y)
        if not iid:
            return

        if iid.startswith("g_"):
            # Click vào nhóm: Toggle toàn bộ file trong nhóm
            try:
                b_id = int(iid.split("_")[1])
                target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
                if target_b:
                    files = target_b.get("file_paths", [])
                    if files:
                        all_chk = all(f.get("checked", True) for f in files)
                        new_chk = not all_chk
                        for f in files:
                            if isinstance(f, dict):
                                f["checked"] = new_chk
                        self.state.save_file_bundle(target_b["group_name"], files, bundle_id=b_id, sort_order=target_b.get("sort_order", 0))
                        self._refresh_file_bundles_tree()
            except Exception as e:
                logger.warning(f"[Bundle Click] Lỗi toggle nhóm: {e}")

        elif iid.startswith("f_"):
            # Click vào file: Toggle file này
            try:
                parts = iid.split("_")
                b_id = int(parts[1])
                f_idx = int(parts[2])
                target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
                if target_b:
                    files = target_b.get("file_paths", [])
                    if 0 <= f_idx < len(files):
                        cur_f = files[f_idx]
                        if isinstance(cur_f, dict):
                            cur_f["checked"] = not cur_f.get("checked", True)
                        self.state.save_file_bundle(target_b["group_name"], files, bundle_id=b_id, sort_order=target_b.get("sort_order", 0))
                        self._refresh_file_bundles_tree()
            except Exception as e:
                logger.warning(f"[Bundle Click] Lỗi toggle file: {e}")

    def _on_bundle_tree_space_key(self, event=None):
        """Bấm phím Space để bật/tắt tích chọn mục đang chọn."""
        self._toggle_selected_bundle_check()
        return "break"

    def _toggle_selected_bundle_check(self):
        """Bật/tắt trạng thái tích chọn của mục đang chọn."""
        sel = self.bundle_tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("g_"):
            try:
                b_id = int(iid.split("_")[1])
                target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
                if target_b:
                    files = target_b.get("file_paths", [])
                    if files:
                        all_chk = all(f.get("checked", True) for f in files)
                        new_chk = not all_chk
                        for f in files:
                            if isinstance(f, dict):
                                f["checked"] = new_chk
                        self.state.save_file_bundle(target_b["group_name"], files, bundle_id=b_id, sort_order=target_b.get("sort_order", 0))
                        self._refresh_file_bundles_tree()
            except Exception:
                pass
        elif iid.startswith("f_"):
            try:
                parts = iid.split("_")
                b_id = int(parts[1])
                f_idx = int(parts[2])
                target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
                if target_b:
                    files = target_b.get("file_paths", [])
                    if 0 <= f_idx < len(files):
                        cur_f = files[f_idx]
                        if isinstance(cur_f, dict):
                            cur_f["checked"] = not cur_f.get("checked", True)
                        self.state.save_file_bundle(target_b["group_name"], files, bundle_id=b_id, sort_order=target_b.get("sort_order", 0))
                        self._refresh_file_bundles_tree()
            except Exception:
                pass

    def _on_bundle_tree_double_click(self, event=None):
        """Bấm đúp chuột vào file: Mở file trên máy tính hoặc toggle."""
        sel = self.bundle_tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("f_"):
            try:
                parts = iid.split("_")
                b_id = int(parts[1])
                f_idx = int(parts[2])
                target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
                if target_b:
                    files = target_b.get("file_paths", [])
                    if 0 <= f_idx < len(files):
                        p = files[f_idx].get("path", "")
                        if os.path.exists(p):
                            os.startfile(p)
                            return
            except Exception:
                pass
        self._toggle_selected_bundle_check()

    def _on_bundle_tree_right_click(self, event):
        """Mở menu chuột phải cho Kho Tệp Đính Kèm."""
        iid = self.bundle_tree.identify_row(event.y)
        if iid:
            self.bundle_tree.selection_set(iid)
            self.bundle_tree_menu.post(event.x_root, event.y_root)

    def _get_selected_bundle_target(self) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Trả về (bundle_dict, file_index) của mục đang chọn trong treeview."""
        sel = self.bundle_tree.selection()
        if not sel:
            if getattr(self, "_file_bundles_data", []):
                return self._file_bundles_data[0], None
            return None, None

        iid = sel[0]
        if iid.startswith("g_"):
            b_id = int(iid.split("_")[1])
            target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
            return target_b, None
        elif iid.startswith("f_"):
            parts = iid.split("_")
            b_id = int(parts[1])
            f_idx = int(parts[2])
            target_b = next((b for b in self._file_bundles_data if b["id"] == b_id), None)
            return target_b, f_idx
        return None, None

    def _create_new_file_bundle(self):
        """Tạo một nhóm tệp đính kèm mới với tên ngắn gọn."""
        name = simpledialog.askstring("Tạo Nhóm Tệp Mới", "Nhập tên nhóm tệp ngắn gọn (ví dụ: [Lớp 12], [Đề Thi], [Khóa Học]):", parent=self)
        if not name or not name.strip():
            return
        g_name = name.strip()
        max_order = max([b.get("sort_order", 0) for b in getattr(self, "_file_bundles_data", [])] + [0])
        new_id = self.state.save_file_bundle(g_name, [], sort_order=max_order + 1)
        self._refresh_file_bundles_tree()
        self.show_toast("Tạo Nhóm", f"Đã tạo nhóm tệp '{g_name}' thành công!", "success")

    def _add_files_to_selected_bundle(self):
        """Thêm 1 hoặc nhiều file từ máy tính vào nhóm đang chọn."""
        target_b, _ = self._get_selected_bundle_target()
        if not target_b:
            self._create_new_file_bundle()
            target_b, _ = self._get_selected_bundle_target()
            if not target_b:
                return

        file_paths = filedialog.askopenfilenames(
            title=f"Chọn các tệp để thêm vào nhóm '{target_b['group_name']}'",
            filetypes=[
                ("Tất Cả Tệp Hỗ Trợ", "*.docx;*.doc;*.pptx;*.ppt;*.xlsx;*.xls;*.pdf;*.png;*.jpg;*.jpeg;*.mp4;*.zip;*.rar"),
                ("Tất Cả Các Loại File (*.*)", "*.*")
            ]
        )
        if not file_paths:
            return

        cur_files = list(target_b.get("file_paths", []))
        existing_paths = {f.get("path") for f in cur_files if isinstance(f, dict)}
        added_cnt = 0

        for p in file_paths:
            p_norm = os.path.abspath(p)
            if p_norm not in existing_paths:
                cur_files.append({
                    "path": p_norm,
                    "name": os.path.basename(p_norm),
                    "checked": True
                })
                existing_paths.add(p_norm)
                added_cnt += 1

        self.state.save_file_bundle(target_b["group_name"], cur_files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
        self._refresh_file_bundles_tree()
        self.show_toast("Thêm Tệp", f"Đã thêm {added_cnt} tệp vào nhóm '{target_b['group_name']}'!", "success")

    def _add_folder_to_selected_bundle(self):
        """Thêm tất cả các file trong một thư mục vào nhóm đang chọn."""
        target_b, _ = self._get_selected_bundle_target()
        if not target_b:
            self._create_new_file_bundle()
            target_b, _ = self._get_selected_bundle_target()
            if not target_b:
                return

        folder_p = filedialog.askdirectory(title=f"Chọn thư mục để thêm vào nhóm '{target_b['group_name']}'")
        if not folder_p:
            return

        cur_files = list(target_b.get("file_paths", []))
        existing_paths = {f.get("path") for f in cur_files if isinstance(f, dict)}
        added_cnt = 0

        for root, _, files in os.walk(folder_p):
            for fname in files:
                full_p = os.path.abspath(os.path.join(root, fname))
                if full_p not in existing_paths:
                    cur_files.append({
                        "path": full_p,
                        "name": fname,
                        "checked": True
                    })
                    existing_paths.add(full_p)
                    added_cnt += 1

        self.state.save_file_bundle(target_b["group_name"], cur_files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
        self._refresh_file_bundles_tree()
        self.show_toast("Thêm Thư Mục", f"Đã nạp {added_cnt} tệp từ thư mục vào nhóm '{target_b['group_name']}'!", "success")

    def _rename_bundle_or_file(self):
        """Đổi tên nhóm hoặc tên hiển thị của file."""
        target_b, f_idx = self._get_selected_bundle_target()
        if not target_b:
            return

        if f_idx is None:
            # Đổi tên nhóm
            old_name = target_b["group_name"]
            new_name = simpledialog.askstring("Đổi Tên Nhóm", f"Nhập tên mới cho nhóm '{old_name}':", initialvalue=old_name, parent=self)
            if new_name and new_name.strip() and new_name.strip() != old_name:
                self.state.save_file_bundle(new_name.strip(), target_b.get("file_paths", []), bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
                self._refresh_file_bundles_tree()
                self.show_toast("Đổi Tên", f"Đã đổi tên nhóm thành '{new_name.strip()}'!", "info")
        else:
            # Đổi tên hiển thị file
            files = target_b.get("file_paths", [])
            if 0 <= f_idx < len(files):
                old_f_name = files[f_idx].get("name", "")
                new_f_name = simpledialog.askstring("Đổi Tên Hiển Thị Tệp", f"Nhập tên hiển thị mới:", initialvalue=old_f_name, parent=self)
                if new_f_name and new_f_name.strip() and new_f_name.strip() != old_f_name:
                    files[f_idx]["name"] = new_f_name.strip()
                    self.state.save_file_bundle(target_b["group_name"], files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
                    self._refresh_file_bundles_tree()
                    self.show_toast("Đổi Tên", f"Đã đổi tên tệp thành '{new_f_name.strip()}'!", "info")

    def _move_bundle_or_file_up(self):
        """Di chuyển nhóm hoặc file lên trên 1 bậc."""
        target_b, f_idx = self._get_selected_bundle_target()
        if not target_b:
            return

        if f_idx is None:
            bundles = list(self._file_bundles_data)
            idx = next((i for i, b in enumerate(bundles) if b["id"] == target_b["id"]), -1)
            if idx > 0:
                bundles[idx], bundles[idx - 1] = bundles[idx - 1], bundles[idx]
                b_ids = [b["id"] for b in bundles]
                self.state.update_file_bundles_order(b_ids)
                self._refresh_file_bundles_tree()
        else:
            files = list(target_b.get("file_paths", []))
            if f_idx > 0 and f_idx < len(files):
                files[f_idx], files[f_idx - 1] = files[f_idx - 1], files[f_idx]
                self.state.save_file_bundle(target_b["group_name"], files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
                self._refresh_file_bundles_tree()

    def _move_bundle_or_file_down(self):
        """Di chuyển nhóm hoặc file xuống dưới 1 bậc."""
        target_b, f_idx = self._get_selected_bundle_target()
        if not target_b:
            return

        if f_idx is None:
            bundles = list(self._file_bundles_data)
            idx = next((i for i, b in enumerate(bundles) if b["id"] == target_b["id"]), -1)
            if 0 <= idx < len(bundles) - 1:
                bundles[idx], bundles[idx + 1] = bundles[idx + 1], bundles[idx]
                b_ids = [b["id"] for b in bundles]
                self.state.update_file_bundles_order(b_ids)
                self._refresh_file_bundles_tree()
        else:
            files = list(target_b.get("file_paths", []))
            if 0 <= f_idx < len(files) - 1:
                files[f_idx], files[f_idx + 1] = files[f_idx + 1], files[f_idx]
                self.state.save_file_bundle(target_b["group_name"], files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
                self._refresh_file_bundles_tree()

    def _delete_bundle_or_file(self):
        """Xóa nhóm hoặc xóa file đang chọn."""
        target_b, f_idx = self._get_selected_bundle_target()
        if not target_b:
            return

        if f_idx is None:
            if messagebox.askyesno("Xác Nhận Xóa Nhóm", f"Bạn có chắc muốn XÓA nhóm '{target_b['group_name']}' cùng toàn bộ tệp bên trong?", parent=self):
                self.state.delete_file_bundle(target_b["id"])
                self._refresh_file_bundles_tree()
                self.show_toast("Đã Xóa", f"Đã xóa nhóm '{target_b['group_name']}'!", "info")
        else:
            files = list(target_b.get("file_paths", []))
            if 0 <= f_idx < len(files):
                del_fname = files[f_idx].get("name", "tệp")
                del files[f_idx]
                self.state.save_file_bundle(target_b["group_name"], files, bundle_id=target_b["id"], sort_order=target_b.get("sort_order", 0))
                self._refresh_file_bundles_tree()
                self.show_toast("Đã Xóa", f"Đã xóa '{del_fname}' khỏi nhóm!", "info")

    def _check_all_bundle_files(self, check_state: bool = True):
        """Tích chọn hoặc bỏ chọn toàn bộ file trong tất cả các nhóm."""
        for b in getattr(self, "_file_bundles_data", []):
            files = b.get("file_paths", [])
            for f in files:
                if isinstance(f, dict):
                    f["checked"] = check_state
            self.state.save_file_bundle(b["group_name"], files, bundle_id=b["id"], sort_order=b.get("sort_order", 0))
        self._refresh_file_bundles_tree()
        msg = "Đã TÍCH CHỌN tất cả tệp trong kho!" if check_state else "Đã BỎ CHỌN tất cả tệp!"
        self.show_toast("Kho Tệp", msg, "info")

    def _open_selected_bundle_file(self):
        """Mở file đang chọn bằng ứng dụng mặc định của Windows."""
        target_b, f_idx = self._get_selected_bundle_target()
        if target_b and f_idx is not None:
            files = target_b.get("file_paths", [])
            if 0 <= f_idx < len(files):
                p = files[f_idx].get("path", "")
                if os.path.exists(p):
                    try:
                        os.startfile(p)
                    except Exception as e:
                        self.show_toast("Không Thể Mở", f"Lỗi mở file: {e}", "error")
                else:
                    self.show_toast("File Không Tồn Tại", "Đường dẫn file không tồn tại trên máy!", "warning")

    def _open_selected_bundle_folder(self):
        """Mở thư mục chứa file trong Windows Explorer."""
        target_b, f_idx = self._get_selected_bundle_target()
        if target_b and f_idx is not None:
            files = target_b.get("file_paths", [])
            if 0 <= f_idx < len(files):
                p = files[f_idx].get("path", "")
                folder_p = os.path.dirname(p)
                if os.path.exists(folder_p):
                    try:
                        os.startfile(folder_p)
                    except Exception as e:
                        self.show_toast("Không Thể Mở", f"Lỗi mở thư mục: {e}", "error")
                else:
                    self.show_toast("Thư Mục Không Tồn Tại", "Thư mục không tồn tại!", "warning")

    def _export_file_bundles(self):
        """Xuất danh sách Kho Tệp Đính Kèm Nhanh ra file JSON."""
        f_path = filedialog.asksaveasfilename(
            title="Xuất Kho Tệp Đính Kèm Nhanh Ra File JSON",
            defaultextension=".json",
            initialfile="script_file_bundles.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if f_path:
            cnt = self.state.export_file_bundles_to_file(f_path)
            self.show_toast("Xuất Thành Công", f"Đã xuất thành công {cnt} nhóm tệp ra file!", "success")

    def _import_file_bundles(self):
        """Nạp danh sách Kho Tệp Đính Kèm Nhanh từ file JSON."""
        f_path = filedialog.askopenfilename(
            title="Nạp Kho Tệp Đính Kèm Nhanh Từ File JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if f_path:
            cnt = self.state.import_file_bundles_from_file(f_path)
            self._refresh_file_bundles_tree()
            self.show_toast("Nạp Thành Công", f"Đã nạp thành công {cnt} nhóm tệp từ file!", "success")

    def _switch_bundle_subview(self, mode: str = "files"):
        """Chuyển đổi hiển thị giữa '📦 Kho Tệp Đính Kèm' và '🔗 Đính Kèm Link Khối' trong Khung 3."""
        self.script_bundle_view_mode = mode
        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        act_bg = "#0284c7"
        act_fg = "white"
        inact_bg = "#e2e8f0" if is_light else "#1e293b"
        inact_fg = "#475569" if is_light else "#94a3b8"

        if mode == "files":
            if hasattr(self, 'btn_switch_bundle_files'):
                self.btn_switch_bundle_files.configure(bg=act_bg, fg=act_fg)
            if hasattr(self, 'btn_switch_bundle_links'):
                self.btn_switch_bundle_links.configure(bg=inact_bg, fg=inact_fg)
            if hasattr(self, 'script_links_subframe'):
                self.script_links_subframe.pack_forget()
            if hasattr(self, 'script_files_subframe'):
                self.script_files_subframe.pack(fill="both", expand=True)
            self._refresh_file_bundles_tree()
        else:
            if hasattr(self, 'btn_switch_bundle_files'):
                self.btn_switch_bundle_files.configure(bg=inact_bg, fg=inact_fg)
            if hasattr(self, 'btn_switch_bundle_links'):
                self.btn_switch_bundle_links.configure(bg=act_bg, fg=act_fg)
            if hasattr(self, 'script_files_subframe'):
                self.script_files_subframe.pack_forget()
            if hasattr(self, 'script_links_subframe'):
                self.script_links_subframe.pack(fill="both", expand=True)
            self._render_quick_links_for_category(getattr(self, "quick_links_selected_grade", "Khối 6"))
            self._update_quick_links_badge()

    def _get_short_grade_name(self, g: str) -> str:
        """Chuyển đổi tên khối dài sang mã viết tắt gọn gàng (K6, K7, THCS, THPT)."""
        mapping = {
            "Khối 6": "K6", "Khối 7": "K7", "Khối 8": "K8", "Khối 9": "K9",
            "Khối 10": "K10", "Khối 11": "K11", "Khối 12": "K12",
            "Link THCS": "THCS", "Link THPT": "THPT"
        }
        return mapping.get(g, g)

    def _update_grade_chips_ui(self):
        """Cập nhật màu sắc các nút chip khối và tiêu đề nút dropdown đa chọn khối."""
        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        active_bg = "#0284c7"
        active_fg = "white"
        inact_bg = "#e2e8f0" if is_light else "#1e293b"
        inact_fg = "#475569" if is_light else "#94a3b8"

        selected = getattr(self, "quick_links_selected_grades", [])
        if hasattr(self, "grade_chip_buttons"):
            for g_full, btn in self.grade_chip_buttons.items():
                if btn.winfo_exists():
                    if g_full in selected:
                        btn.configure(bg=active_bg, fg=active_fg, font=("Segoe UI", 7, "bold"))
                    else:
                        btn.configure(bg=inact_bg, fg=inact_fg, font=("Segoe UI", 7))

        if hasattr(self, "btn_multi_grade_dropdown") and self.btn_multi_grade_dropdown.winfo_exists():
            if not selected:
                self.btn_multi_grade_dropdown.configure(text="📚 Chọn Khối (0 khối) ▾", bg="#64748b", fg="white")
            elif len(selected) == 1:
                self.btn_multi_grade_dropdown.configure(text=f"📚 {selected[0]} ▾", bg="#0284c7", fg="white")
            elif len(selected) == len(QUICK_LINK_GRADES):
                self.btn_multi_grade_dropdown.configure(text="📚 Tất Cả 9 Khối (K6-K12, THCS, THPT) ▾", bg="#8b5cf6", fg="white")
            else:
                abbrs = [self._get_short_grade_name(g) for g in selected]
                self.btn_multi_grade_dropdown.configure(text=f"📚 {len(selected)} Khối ({', '.join(abbrs)}) ▾", bg="#0284c7", fg="white")

    def _toggle_quick_link_grade(self, grade: str):
        """Bật / Tắt một khối trong danh sách đa chọn khối."""
        if not hasattr(self, "quick_links_selected_grades"):
            self.quick_links_selected_grades = ["Khối 6"]

        if grade in self.quick_links_selected_grades:
            self.quick_links_selected_grades.remove(grade)
        else:
            self.quick_links_selected_grades.append(grade)
            self.quick_links_selected_grades.sort(key=lambda x: QUICK_LINK_GRADES.index(x) if x in QUICK_LINK_GRADES else 99)

        if self.quick_links_selected_grades:
            self.quick_links_selected_grade = self.quick_links_selected_grades[0]

        self._render_quick_links_for_category(self.quick_links_selected_grades)

    def _select_thcs_quick_grades(self):
        """Chọn nhanh toàn bộ các khối Cấp 2 (6, 7, 8, 9, THCS)."""
        self.quick_links_selected_grades = ["Khối 6", "Khối 7", "Khối 8", "Khối 9", "Link THCS"]
        self.quick_links_selected_grade = "Khối 6"
        self._render_quick_links_for_category(self.quick_links_selected_grades)

    def _select_thpt_quick_grades(self):
        """Chọn nhanh toàn bộ các khối Cấp 3 (10, 11, 12, THPT)."""
        self.quick_links_selected_grades = ["Khối 10", "Khối 11", "Khối 12", "Link THPT"]
        self.quick_links_selected_grade = "Khối 10"
        self._render_quick_links_for_category(self.quick_links_selected_grades)

    def _select_all_quick_grades(self):
        """Chọn toàn bộ 9 khối."""
        self.quick_links_selected_grades = list(QUICK_LINK_GRADES)
        self.quick_links_selected_grade = "Khối 6"
        self._render_quick_links_for_category(self.quick_links_selected_grades)

    def _clear_all_quick_grades(self):
        """Bỏ chọn toàn bộ khối hiển thị."""
        self.quick_links_selected_grades = []
        self._render_quick_links_for_category(self.quick_links_selected_grades)

    def _show_multi_grade_dropdown_menu(self):
        """Mở Popup Menu tích chọn đa khối khi click nút Chọn Khối."""
        menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7", font=("Segoe UI", 9))
        selected = getattr(self, "quick_links_selected_grades", [])

        for g in QUICK_LINK_GRADES:
            is_active = g in selected
            prefix = "✓ " if is_active else "    "
            menu.add_command(
                label=f"{prefix}{g} ({self._get_short_grade_name(g)})",
                command=lambda target=g: self._toggle_quick_link_grade(target)
            )

        menu.add_separator()
        menu.add_command(label="⚡ Chọn Tất Cả (9 Khối)", command=self._select_all_quick_grades)
        menu.add_command(label="⚡ Chọn Cả Cấp 2 (K6, K7, K8, K9, THCS)", command=self._select_thcs_quick_grades)
        menu.add_command(label="⚡ Chọn Cả Cấp 3 (K10, K11, K12, THPT)", command=self._select_thpt_quick_grades)
        menu.add_command(label="🔄 Bỏ Chọn Hết", command=self._clear_all_quick_grades)

        try:
            x = self.btn_multi_grade_dropdown.winfo_rootx()
            y = self.btn_multi_grade_dropdown.winfo_rooty() + self.btn_multi_grade_dropdown.winfo_height() + 2
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _render_quick_links_for_category(self, grade_names: Union[str, List[str]] = None):
        """
        Vẽ danh sách các checkbox link cho một hoặc NHIỀU khối được chọn (Multi-Select Khối).
        Hỗ trợ hiển thị Ghi Chú nội bộ (note) cho mỗi link và tương thích 100% Light/Dark Theme.
        """
        if grade_names is None:
            grade_names = getattr(self, "quick_links_selected_grades", ["Khối 6"])
        elif isinstance(grade_names, str):
            grade_names = [grade_names]

        # Lọc danh sách hợp lệ
        valid_grades = [g for g in grade_names if g in QUICK_LINK_GRADES]
        self.quick_links_selected_grades = valid_grades
        if valid_grades:
            self.quick_links_selected_grade = valid_grades[0]

        self._update_grade_chips_ui()

        if not hasattr(self, 'quick_links_items_frame') or not self.quick_links_items_frame.winfo_exists():
            return

        for child in self.quick_links_items_frame.winfo_children():
            child.destroy()

        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        base_bg = "#ffffff" if is_light else "#0f172a"
        hdr_bg = "#f1f5f9" if is_light else "#1e293b"
        hdr_fg = "#0284c7" if is_light else "#38bdf8"
        btn_hdr_bg = "#e2e8f0" if is_light else "#334155"
        btn_hdr_all_fg = "#059669" if is_light else "#34d399"
        btn_hdr_none_fg = "#475569" if is_light else "#94a3b8"
        note_badge_bg = "#fef3c7" if is_light else "#3b2a0c"
        note_badge_fg = "#b45309" if is_light else "#fbbf24"

        if hasattr(self, 'quick_links_canvas') and self.quick_links_canvas.winfo_exists():
            self.quick_links_canvas.configure(bg=base_bg)
        self.quick_links_items_frame.configure(bg=base_bg)

        if not valid_grades:
            tk.Label(
                self.quick_links_items_frame,
                text="💡 Chưa chọn khối nào.\nVui lòng tích chọn một hoặc nhiều khối ở trên để xem danh sách link!",
                fg="#64748b" if is_light else "#94a3b8",
                bg=base_bg,
                font=("Segoe UI", 9, "italic"),
                justify="center"
            ).pack(pady=30)
            return

        # Lặp qua từng khối trong danh sách đã chọn
        for grade_idx, grade_name in enumerate(valid_grades):
            items = self.quick_links_data.get(grade_name, [])

            # Header Khối
            hdr_row = tk.Frame(self.quick_links_items_frame, bg=hdr_bg, padx=6, pady=4)
            hdr_row.pack(fill="x", pady=(6 if grade_idx > 0 else 0, 3))

            tk.Label(
                hdr_row,
                text=f"📚 {grade_name} ({len(items)} link)",
                font=("Segoe UI", 8, "bold"),
                fg=hdr_fg,
                bg=hdr_bg
            ).pack(side="left")

            # Nút chọn hết / bỏ chọn riêng cho khối này
            tk.Button(
                hdr_row,
                text="☐ Bỏ Khối Này",
                bg=btn_hdr_bg,
                fg=btn_hdr_none_fg,
                font=("Segoe UI", 7),
                relief="flat",
                padx=4,
                pady=1,
                cursor="hand2",
                command=lambda g=grade_name: self._check_all_links_in_specific_grade(g, False)
            ).pack(side="right", padx=(2, 0))

            tk.Button(
                hdr_row,
                text="☑️ Chọn Khối Này",
                bg=btn_hdr_bg,
                fg=btn_hdr_all_fg,
                font=("Segoe UI", 7, "bold"),
                relief="flat",
                padx=4,
                pady=1,
                cursor="hand2",
                command=lambda g=grade_name: self._check_all_links_in_specific_grade(g, True)
            ).pack(side="right", padx=2)

            if not items:
                tk.Label(
                    self.quick_links_items_frame,
                    text=f"(Chưa có link cho {grade_name})",
                    fg="#64748b" if is_light else "#94a3b8",
                    bg=base_bg,
                    font=("Segoe UI", 8, "italic")
                ).pack(pady=4)
                continue

            # Danh sách từng link trong khối này
            for idx, item in enumerate(items):
                if is_light:
                    row_bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
                    text_color = "#0f172a"
                    url_color = "#0284c7"
                    btn_action_bg = "#e2e8f0"
                    btn_action_fg = "#0f172a"
                    btn_open_fg = "#2563eb"
                    chk_sel_color = "#ffffff"
                else:
                    row_bg = "#1e293b" if idx % 2 == 0 else "#0f172a"
                    text_color = "#f8fafc"
                    url_color = "#38bdf8"
                    btn_action_bg = "#334155"
                    btn_action_fg = "white"
                    btn_open_fg = "#60a5fa"
                    chk_sel_color = "#0f172a"

                row = tk.Frame(self.quick_links_items_frame, bg=row_bg, padx=6, pady=3)
                row.pack(fill="x", pady=1)

                # Checkbox
                var = tk.BooleanVar(value=item.get("checked", False))

                def make_toggle(it=item, v=var):
                    def _cmd():
                        it["checked"] = v.get()
                        self._save_quick_links_to_file()
                        self._update_quick_links_badge()
                    return _cmd

                chk = tk.Checkbutton(
                    row,
                    variable=var,
                    bg=row_bg,
                    selectcolor=chk_sel_color,
                    activebackground=row_bg,
                    command=make_toggle()
                )
                chk.pack(side="left")

                # Tên link + Ghi chú nội bộ
                info_frame = tk.Frame(row, bg=row_bg)
                info_frame.pack(side="left", padx=(2, 4))

                name_lbl = tk.Label(
                    info_frame,
                    text=item.get("name", f"Link {idx+1}"),
                    font=("Segoe UI", 8, "bold"),
                    fg=text_color,
                    bg=row_bg,
                    anchor="w"
                )
                name_lbl.pack(side="left")

                # Hiển thị Ghi Chú nếu có (chỉ hiện nội bộ trên app)
                note_str = item.get("note", "").strip()
                if note_str:
                    note_badge = tk.Label(
                        info_frame,
                        text=f"📝 {note_str}",
                        font=("Segoe UI", 7),
                        fg=note_badge_fg,
                        bg=note_badge_bg,
                        padx=4,
                        pady=1
                    )
                    note_badge.pack(side="left", padx=(4, 0))

                # URL rút gọn
                url = item.get("url", "")
                url_short = url if len(url) <= 26 else (url[:23] + "...")
                url_lbl = tk.Label(
                    row,
                    text=url_short,
                    font=("Segoe UI", 8),
                    fg=url_color,
                    bg=row_bg,
                    anchor="w"
                )
                url_lbl.pack(side="left", fill="x", expand=True)

                # Copy link button
                def make_copy(u=url, n=item.get("name", "Link")):
                    def _cmd():
                        try:
                            import pyperclip
                            pyperclip.copy(u)
                        except Exception:
                            self.clipboard_clear()
                            self.clipboard_append(u)
                        self.show_toast("Đã Sao Chép Link", f"Đã sao chép {n} vào Clipboard!", "info")
                    return _cmd

                btn_cp = tk.Button(
                    row,
                    text="📋",
                    font=("Segoe UI", 7),
                    bg=btn_action_bg,
                    fg=btn_action_fg,
                    relief="flat",
                    padx=3,
                    pady=1,
                    cursor="hand2",
                    command=make_copy()
                )
                btn_cp.pack(side="right", padx=(2, 0))

                # Open link button
                def make_open(u=url):
                    def _cmd():
                        if u.startswith("http"):
                            import webbrowser
                            webbrowser.open(u)
                        else:
                            self.show_toast("Link Không Hợp Lệ", "URL phải bắt đầu bằng http hoặc https!", "warning")
                    return _cmd

                btn_op = tk.Button(
                    row,
                    text="🌐",
                    font=("Segoe UI", 7),
                    bg=btn_action_bg,
                    fg=btn_open_fg,
                    relief="flat",
                    padx=3,
                    pady=1,
                    cursor="hand2",
                    command=make_open()
                )
                btn_op.pack(side="right", padx=2)

        self._update_quick_links_badge()

    def _check_all_links_in_specific_grade(self, grade: str, check: bool):
        """Bật hoặc tắt tích chọn toàn bộ link của một khối cụ thể."""
        items = self.quick_links_data.get(grade, [])
        for it in items:
            it["checked"] = check
        self._save_quick_links_to_file()
        self._render_quick_links_for_category(self.quick_links_selected_grades)
        self._update_quick_links_badge()

    def _check_all_links_in_current_grade(self, check: bool):
        """Bật hoặc tắt tích chọn toàn bộ link của các khối đang chọn."""
        for grade in getattr(self, "quick_links_selected_grades", []):
            for it in self.quick_links_data.get(grade, []):
                it["checked"] = check
        self._save_quick_links_to_file()
        self._render_quick_links_for_category(self.quick_links_selected_grades)
        self._update_quick_links_badge()

    def _check_all_links_global(self, check: bool):
        """Bật hoặc tắt tích chọn tất cả các link trên mọi khối."""
        for grade in QUICK_LINK_GRADES:
            for it in self.quick_links_data.get(grade, []):
                it["checked"] = check
        self._save_quick_links_to_file()
        self._render_quick_links_for_category(self.quick_links_selected_grades)
        self._update_quick_links_badge()
        status_txt = "Đã tích chọn tất cả các link trên mọi khối!" if check else "Đã bỏ chọn toàn bộ link!"
        self.show_toast("Đính Kèm Link", status_txt, "info")

    def _open_quick_links_manager_modal(self):
        """Mở modal quản lý, thêm, xóa & chỉnh sửa URL / Tên link / Ghi chú nội bộ cho tất cả các khối (6-12, THCS, THPT)."""
        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        modal_bg = "#f8fafc" if is_light else "#0f172a"
        hdr_bg = "#ffffff" if is_light else "#1e293b"
        hdr_title_fg = "#0284c7" if is_light else "#38bdf8"
        sub_top_bg = "#f1f5f9" if is_light else "#0f172a"
        label_fg = "#0f172a" if is_light else "#f8fafc"
        card_bg = "#ffffff" if is_light else "#1e293b"
        card_border = "#e2e8f0" if is_light else "#334155"
        entry_bg = "#ffffff" if is_light else "#0f172a"
        entry_fg = "#0f172a" if is_light else "#f8fafc"
        insert_color = "#0f172a" if is_light else "white"
        ftr_bg = "#f1f5f9" if is_light else "#1e293b"
        btn_cancel_bg = "#e2e8f0" if is_light else "#334155"
        btn_cancel_fg = "#334155" if is_light else "#cbd5e1"
        btn_reset_bg = "#cbd5e1" if is_light else "#475569"
        btn_reset_fg = "#0f172a" if is_light else "#f8fafc"

        dlg = tk.Toplevel(self)
        dlg.title("⚙️ Quản Lý, Thêm, Sửa Link & Ghi Chú Các Khối (6-12, THCS, THPT)")
        dlg.geometry("820x600")
        dlg.minsize(720, 500)
        dlg.configure(bg=modal_bg)
        dlg.transient(self)
        dlg.grab_set()
        apply_windows_dark_titlebar(dlg, hdr_bg, label_fg)

        # Header
        hdr = tk.Frame(dlg, bg=hdr_bg, padx=12, pady=10)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="⚙️ QUẢN LÝ, THÊM / SỬA LINK & GHI CHÚ NỘI BỘ",
            font=("Segoe UI", 11, "bold"),
            fg=hdr_title_fg,
            bg=hdr_bg
        ).pack(side="left")
        tk.Label(
            hdr,
            text="💡 Ghi chú chỉ hiển thị trong phần mềm, không gửi vào tin nhắn",
            font=("Segoe UI", 8, "italic"),
            fg="#f59e0b" if is_light else "#fbbf24",
            bg=hdr_bg
        ).pack(side="right")

        # Grade Switcher in Modal
        sub_top = tk.Frame(dlg, bg=sub_top_bg, padx=10, pady=6)
        sub_top.pack(fill="x")

        tk.Label(sub_top, text="Chọn Khối:", font=("Segoe UI", 9, "bold"), fg=label_fg, bg=sub_top_bg).pack(side="left", padx=(0, 6))
        modal_grade_cb = ttk.Combobox(sub_top, values=QUICK_LINK_GRADES, state="readonly", width=16)
        initial_grade = self.quick_links_selected_grades[0] if getattr(self, "quick_links_selected_grades", None) else "Khối 6"
        modal_grade_cb.set(initial_grade)
        modal_grade_cb.pack(side="left", padx=(0, 10))

        # Main Scrollable Area for Editing
        scroll_f = tk.Frame(dlg, bg=modal_bg, padx=10, pady=4)
        scroll_f.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_f, bg=modal_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_f, orient="vertical", command=canvas.yview)
        form_inner = tk.Frame(canvas, bg=modal_bg)

        form_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=form_inner, anchor="nw")
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # List to track inputs: (item_dict, ent_name, ent_note, ent_url)
        entry_widgets = []

        def save_current_form():
            for item, ent_name, ent_note, ent_url in entry_widgets:
                item["name"] = ent_name.get().strip()
                item["note"] = ent_note.get().strip()
                item["url"] = ent_url.get().strip()
            self._save_quick_links_to_file()
            self._render_quick_links_for_category()
            self._update_quick_links_badge()

        def load_form_for_grade(grade_name: str):
            for w in form_inner.winfo_children():
                w.destroy()
            entry_widgets.clear()

            items = self.quick_links_data.get(grade_name, [])
            for idx, item in enumerate(items):
                card = tk.Frame(form_inner, bg=card_bg, padx=8, pady=6, highlightbackground=card_border, highlightthickness=1)
                card.pack(fill="x", pady=4)

                # Hàng 1: Tên link + Ghi chú nội bộ + Nút Xóa
                r1 = tk.Frame(card, bg=card_bg)
                r1.pack(fill="x", pady=(0, 3))

                tk.Label(r1, text=f"#{idx+1} Tên/Nhãn:", font=("Segoe UI", 8, "bold"), fg=hdr_title_fg, bg=card_bg).pack(side="left")
                ent_name = tk.Entry(r1, font=("Segoe UI", 9), bg=entry_bg, fg=entry_fg, insertbackground=insert_color, width=20)
                ent_name.insert(0, item.get("name", f"Link {idx+1}"))
                ent_name.pack(side="left", padx=(4, 8))

                tk.Label(r1, text="📝 Ghi Chú (Nội Bộ):", font=("Segoe UI", 8, "bold"), fg="#d97706" if is_light else "#fbbf24", bg=card_bg).pack(side="left")
                ent_note = tk.Entry(r1, font=("Segoe UI", 9), bg=entry_bg, fg=entry_fg, insertbackground=insert_color)
                ent_note.insert(0, item.get("note", ""))
                ent_note.pack(side="left", fill="x", expand=True, padx=(4, 6))

                def make_del(it_idx=idx):
                    def _del():
                        save_current_form()
                        if 0 <= it_idx < len(self.quick_links_data.get(grade_name, [])):
                            self.quick_links_data[grade_name].pop(it_idx)
                            save_current_form()
                            load_form_for_grade(grade_name)
                    return _del

                btn_del = tk.Button(
                    r1,
                    text="🗑️ Xóa",
                    font=("Segoe UI", 7),
                    bg="#ef4444" if not is_light else "#fee2e2",
                    fg="white" if not is_light else "#dc2626",
                    relief="flat",
                    padx=6,
                    pady=1,
                    cursor="hand2",
                    command=make_del()
                )
                btn_del.pack(side="right")

                # Hàng 2: URL
                r2 = tk.Frame(card, bg=card_bg)
                r2.pack(fill="x")

                tk.Label(r2, text="Đường dẫn URL:", font=("Segoe UI", 8, "bold"), fg="#059669" if is_light else "#34d399", bg=card_bg).pack(side="left")
                ent_url = tk.Entry(r2, font=("Segoe UI", 9), bg=entry_bg, fg=entry_fg, insertbackground=insert_color)
                ent_url.insert(0, item.get("url", ""))
                ent_url.pack(side="left", fill="x", expand=True, padx=(4, 0))

                entry_widgets.append((item, ent_name, ent_note, ent_url))

            # Nút Thêm Link ở cuối danh sách
            add_box = tk.Frame(form_inner, bg=modal_bg, pady=6)
            add_box.pack(fill="x")

            def add_new_link():
                save_current_form()
                new_idx = len(self.quick_links_data.get(grade_name, [])) + 1
                new_item = {
                    "id": f"link_{int(time.time() * 1000)}",
                    "name": f"Link {new_idx}",
                    "url": "",
                    "note": "",
                    "checked": False
                }
                if grade_name not in self.quick_links_data:
                    self.quick_links_data[grade_name] = []
                self.quick_links_data[grade_name].append(new_item)
                save_current_form()
                load_form_for_grade(grade_name)

            tk.Button(
                add_box,
                text=f"➕ Thêm Link Mới Cho {grade_name}",
                font=("Segoe UI", 8, "bold"),
                bg="#0284c7",
                fg="white",
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2",
                command=add_new_link
            ).pack(side="left")

        modal_grade_cb.bind("<<ComboboxSelected>>", lambda e: (save_current_form(), load_form_for_grade(modal_grade_cb.get())))
        load_form_for_grade(modal_grade_cb.get())

        # Footer Buttons
        ftr = tk.Frame(dlg, bg=ftr_bg, padx=12, pady=8)
        ftr.pack(fill="x")

        def on_save_and_close():
            save_current_form()
            dlg.destroy()
            self.show_toast("Đã Lưu Link Khối", "Đã cập nhật danh sách link và ghi chú thành công!", "success")

        def on_reset_default():
            cur_g = modal_grade_cb.get()
            if cur_g in DEFAULT_QUICK_LINKS:
                self.quick_links_data[cur_g] = copy.deepcopy(DEFAULT_QUICK_LINKS[cur_g])
                save_current_form()
                load_form_for_grade(cur_g)
                self.show_toast("Khôi Phục Gốc", f"Đã khôi phục link mặc định cho {cur_g}!", "info")

        tk.Button(ftr, text="🔄 Khôi Phục Gốc Khối Này", bg=btn_reset_bg, fg=btn_reset_fg, font=("Segoe UI", 8), relief="flat", padx=8, pady=3, cursor="hand2", command=on_reset_default).pack(side="left")
        tk.Button(ftr, text="💾 Lưu & Đóng", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=on_save_and_close).pack(side="right")
        tk.Button(ftr, text="Hủy", bg=btn_cancel_bg, fg=btn_cancel_fg, font=("Segoe UI", 8), relief="flat", padx=8, pady=3, cursor="hand2", command=dlg.destroy).pack(side="right", padx=6)

    # =========================================================================
    # TAB: 🖼️ FAKE ẢNH DRIVE (MOCKUP CHIA SẺ GOOGLE DRIVE & BẮN VÀO ZALO PC)
    # =========================================================================
    def _build_fake_drive_tab(self, parent):
        """
        Xây dựng Tab Tạo Ảnh Mockup Chia Sẻ Google Drive chuẩn 100% Google Material Design (Hình 1, 2 & Đa Email),
        hỗ trợ gửi 1 hoặc NHIỀU EMAIL đồng thời (avatar chữ cái đầu xếp dọc chuẩn Google Material),
        tự động đính kèm danh sách Link Khối (có nhãn) và Tin nhắn chốt dưới cùng,
        hỗ trợ Live Preview trực quan, Copy Clipboard chuẩn DIB và Bắn 1-Click vào Zalo PC / Trình Soạn Thảo Active.
        """
        self.fake_drive_role_var = tk.StringVar(value="Người xem")
        self.fake_drive_notify_var = tk.BooleanVar(value=True)
        self.fake_drive_msg_var = tk.StringVar(value="")
        self.fake_drive_include_label_var = tk.BooleanVar(value=True)
        self.fake_drive_target_mode = "target_locked"  # "target_locked" hoặc "free_mode"
        self.fake_drive_img_photo = None
        self.fake_drive_current_img_path = None

        # Trạng thái checkbox từng khối
        self.fake_drive_grade_vars = {}
        for g in QUICK_LINK_GRADES:
            self.fake_drive_grade_vars[g] = tk.BooleanVar(value=(g in ("Khối 7", "Khối 8", "Khối 9")))

        # Khung chính 2 cột (Trái: Cài đặt & Nút bấm, Phải: Live Preview Ảnh & Text)
        paned = tk.PanedWindow(parent, orient="horizontal", bg="#0f172a", sashwidth=5)
        paned.pack(fill="both", expand=True)
        self.fake_drive_paned = paned

        is_light = getattr(self, "current_theme", "tailwind_light") in ("tailwind_light", "light_theme", "light")
        bg_card = "#ffffff" if is_light else "#1e293b"
        border_card = "#e2e8f0" if is_light else "#334155"
        text_pri = "#0f172a" if is_light else "#f8fafc"
        text_sec = "#475569" if is_light else "#94a3b8"
        ent_bg = "#ffffff" if is_light else "#0f172a"
        ent_fg = "#0f172a" if is_light else "#f8fafc"
        insert_clr = "#0f172a" if is_light else "white"

        # =========================================================================
        # CỘT TRÁI: CẤU HÌNH THÔNG TIN, CHỌN KHỐI, TIN NHẮN CHỐT & NÚT BẮN ZALO
        # =========================================================================
        left_container = tk.Frame(paned, bg="#f8fafc" if is_light else "#0f172a", padx=4, pady=4)
        paned.add(left_container, minsize=380, width=500)

        # Scrollable Frame cho Cột Trái
        canvas_left = tk.Canvas(left_container, bg="#f8fafc" if is_light else "#0f172a", highlightthickness=0)
        scrollbar_left = ttk.Scrollbar(left_container, orient="vertical", command=canvas_left.yview)
        left_inner = tk.Frame(canvas_left, bg="#f8fafc" if is_light else "#0f172a")

        left_inner.bind("<Configure>", lambda e: canvas_left.configure(scrollregion=canvas_left.bbox("all")))
        canvas_left_win = canvas_left.create_window((0, 0), window=left_inner, anchor="nw")
        canvas_left.configure(yscrollcommand=scrollbar_left.set)

        def _on_canvas_left_config(event):
            canvas_left.itemconfig(canvas_left_win, width=event.width)
        canvas_left.bind("<Configure>", _on_canvas_left_config)

        canvas_left.pack(side="left", fill="both", expand=True)
        scrollbar_left.pack(side="right", fill="y")

        # Tiêu đề Card Trái
        hdr_box = tk.Frame(left_inner, bg=bg_card, padx=10, pady=8, highlightbackground=border_card, highlightthickness=1)
        hdr_box.pack(fill="x", pady=(0, 6))

        tk.Label(
            hdr_box,
            text="🖼️ TẠO ẢNH CHIA SẺ GOOGLE DRIVE & GỬI ZALO (1-CLICK)",
            font=("Segoe UI", 10, "bold"),
            fg="#ea580c" if is_light else "#fb923c",
            bg=bg_card
        ).pack(anchor="w")

        tk.Label(
            hdr_box,
            text="Tự động render Popup Google Drive Material (Hỗ trợ 1 hoặc NHIỀU EMAIL) + Kèm Link Khối + Tin nhắn chốt",
            font=("Segoe UI", 8),
            fg=text_sec,
            bg=bg_card,
            wraplength=460,
            justify="left"
        ).pack(anchor="w", pady=(2, 0))

        # --- CARD 1: THÔNG TIN NGƯỜI NHẬN & PHÂN QUYỀN (HỖ TRỢ NHIỀU EMAIL) ---
        card1 = tk.Frame(left_inner, bg=bg_card, padx=10, pady=8, highlightbackground=border_card, highlightthickness=1)
        card1.pack(fill="x", pady=4)

        r_hdr_email = tk.Frame(card1, bg=bg_card)
        r_hdr_email.pack(fill="x", pady=(0, 4))

        tk.Label(r_hdr_email, text="👤 1. EMAIL NGƯỜI NHẬN (GỬI 1 HOẶC NHIỀU EMAIL):", font=("Segoe UI", 9, "bold"), fg="#0284c7" if is_light else "#38bdf8", bg=bg_card).pack(side="left")
        self.lbl_fake_drive_email_count = tk.Label(r_hdr_email, text="(1 email)", font=("Segoe UI", 8, "bold"), fg="#d97706" if is_light else "#fbbf24", bg=bg_card)
        self.lbl_fake_drive_email_count.pack(side="left", padx=4)

        # Hàng công cụ Email (Dán Nhiều Email, Thêm Email, Xóa Trắng)
        r_email_tools = tk.Frame(card1, bg=bg_card)
        r_email_tools.pack(fill="x", pady=(0, 4))

        tool_btn_cfg = {"font": ("Segoe UI", 7, "bold"), "relief": "flat", "padx": 6, "pady": 2, "cursor": "hand2"}
        tk.Button(r_email_tools, text="📋 Dán Nhiều Email", bg="#0284c7", fg="white", command=self._on_fake_drive_email_paste, **tool_btn_cfg).pack(side="left", padx=(0, 3))
        tk.Button(r_email_tools, text="➕ Thêm Email", bg="#059669", fg="white", command=self._on_fake_drive_add_single_email, **tool_btn_cfg).pack(side="left", padx=2)
        tk.Button(r_email_tools, text="🧹 Xóa Trắng", bg="#64748b", fg="white", command=self._on_fake_drive_clear_emails, **tool_btn_cfg).pack(side="left", padx=2)

        # Ô nhập nhiều Email (Text Scrolled)
        self.txt_fake_drive_emails = tk.Text(
            card1,
            height=2,
            font=("Segoe UI", 9),
            bg=ent_bg,
            fg=ent_fg,
            insertbackground=insert_clr,
            relief="solid",
            bd=1,
            wrap="word"
        )
        self.txt_fake_drive_emails.insert("1.0", "anhdaosps36@gmail.com, nguyenchidinh248@gmail.com, nctnd.tttrang@gmail.com")
        self.txt_fake_drive_emails.pack(fill="x", pady=(0, 4))
        self.txt_fake_drive_emails.bind("<KeyRelease>", lambda e: self._on_fake_drive_email_changed())

        tk.Label(
            card1,
            text="💡 Gõ hoặc dán nhiều email cách nhau bằng dấu phẩy (,), chấm phẩy (;) hoặc xuống dòng",
            font=("Segoe UI", 7, "italic"),
            fg=text_sec,
            bg=bg_card
        ).pack(anchor="w", pady=(0, 4))

        # Hàng 2: Chọn từ CRM (Tự động cộng thêm email vào danh sách)
        r_crm = tk.Frame(card1, bg=bg_card)
        r_crm.pack(fill="x", pady=2)

        tk.Label(r_crm, text="Thêm từ CRM:", font=("Segoe UI", 8), fg=text_sec, bg=bg_card).pack(side="left")
        self.cb_fake_drive_crm = ttk.Combobox(r_crm, font=("Segoe UI", 8), state="readonly")
        self.cb_fake_drive_crm.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._populate_fake_drive_crm_combo()
        self.cb_fake_drive_crm.bind("<<ComboboxSelected>>", self._on_fake_drive_crm_user_selected)

        # Hàng 3: Quyền truy cập & Checkbox thông báo
        r_role = tk.Frame(card1, bg=bg_card)
        r_role.pack(fill="x", pady=(4, 2))

        tk.Label(r_role, text="Quyền truy cập:", font=("Segoe UI", 8, "bold"), fg=text_pri, bg=bg_card).pack(side="left")
        self.cb_fake_drive_role = ttk.Combobox(
            r_role,
            textvariable=self.fake_drive_role_var,
            values=["Người xem", "Người nhận xét", "Người chỉnh sửa"],
            state="readonly",
            width=16,
            font=("Segoe UI", 8)
        )
        self.cb_fake_drive_role.pack(side="left", padx=(6, 12))
        self.cb_fake_drive_role.bind("<<ComboboxSelected>>", lambda e: self._refresh_fake_drive_preview())

        chk_notif = tk.Checkbutton(
            r_role,
            text="Thông báo qua email",
            variable=self.fake_drive_notify_var,
            bg=bg_card,
            fg=text_pri,
            selectcolor=ent_bg,
            activebackground=bg_card,
            font=("Segoe UI", 8),
            command=self._refresh_fake_drive_preview
        )
        chk_notif.pack(side="left")

        # Hàng 4: Lời nhắn (Message)
        r_msg = tk.Frame(card1, bg=bg_card)
        r_msg.pack(fill="x", pady=(4, 2))

        tk.Label(r_msg, text="Lời nhắn (Tùy chọn):", font=("Segoe UI", 8), fg=text_sec, bg=bg_card).pack(side="left")
        ent_msg = tk.Entry(
            r_msg,
            textvariable=self.fake_drive_msg_var,
            font=("Segoe UI", 8),
            bg=ent_bg,
            fg=ent_fg,
            insertbackground=insert_clr
        )
        ent_msg.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.fake_drive_msg_var.trace_add("write", lambda *a: self._refresh_fake_drive_preview())

        # --- CARD 2: CHỌN KHỐI ĐÍNH KÈM & ĐỒNG BỘ LINK ---
        card2 = tk.Frame(left_inner, bg=bg_card, padx=10, pady=8, highlightbackground=border_card, highlightthickness=1)
        card2.pack(fill="x", pady=4)

        tk.Label(card2, text="📚 2. CHỌN KHỐI ĐÍNH KÈM & LINK TẢI", font=("Segoe UI", 9, "bold"), fg="#8b5cf6" if is_light else "#a78bfa", bg=bg_card).pack(anchor="w", pady=(0, 4))

        # Nút chọn nhanh Cấp 2 / Cấp 3 / Tất cả
        quick_btn_row = tk.Frame(card2, bg=bg_card)
        quick_btn_row.pack(fill="x", pady=2)

        btn_style_cfg = {"font": ("Segoe UI", 7, "bold"), "relief": "flat", "padx": 6, "pady": 1, "cursor": "hand2"}
        tk.Button(quick_btn_row, text="⚡ Cấp 2 (K6-9, THCS)", bg="#0284c7", fg="white", command=lambda: self._select_fake_drive_grades("thcs"), **btn_style_cfg).pack(side="left", padx=(0, 3))
        tk.Button(quick_btn_row, text="⚡ Cấp 3 (K10-12, THPT)", bg="#8b5cf6", fg="white", command=lambda: self._select_fake_drive_grades("thpt"), **btn_style_cfg).pack(side="left", padx=2)
        tk.Button(quick_btn_row, text="⚡ Tất Cả (9 Khối)", bg="#059669", fg="white", command=lambda: self._select_fake_drive_grades("all"), **btn_style_cfg).pack(side="left", padx=2)
        tk.Button(quick_btn_row, text="🔄 Bỏ Hết", bg="#64748b", fg="white", command=lambda: self._select_fake_drive_grades("none"), **btn_style_cfg).pack(side="left", padx=2)

        # Lưới Checkbox 9 Khối (3 cột x 3 hàng)
        grid_grades = tk.Frame(card2, bg=bg_card)
        grid_grades.pack(fill="x", pady=4)

        for idx, g in enumerate(QUICK_LINK_GRADES):
            r = idx // 3
            c = idx % 3
            chk = tk.Checkbutton(
                grid_grades,
                text=g,
                variable=self.fake_drive_grade_vars[g],
                bg=bg_card,
                fg=text_pri,
                selectcolor=ent_bg,
                activebackground=bg_card,
                font=("Segoe UI", 8, "bold" if self.fake_drive_grade_vars[g].get() else "normal"),
                command=self._refresh_fake_drive_preview
            )
            chk.grid(row=r, column=c, sticky="w", padx=4, pady=2)

        # Tùy chọn gửi kèm nhãn và chọn loại link
        r_opt = tk.Frame(card2, bg=bg_card)
        r_opt.pack(fill="x", pady=(4, 2))

        chk_lbl = tk.Checkbutton(
            r_opt,
            text="Gửi kèm Label tên khối trước URL (ví dụ: [Khối 7 - Link 1]: https://...)",
            variable=self.fake_drive_include_label_var,
            bg=bg_card,
            fg=text_pri,
            selectcolor=ent_bg,
            activebackground=bg_card,
            font=("Segoe UI", 8),
            command=self._refresh_fake_drive_preview
        )
        chk_lbl.pack(side="left")

        # --- CARD 3: TIN NHẮN CHỐT DƯỚI CÙNG ---
        card3 = tk.Frame(left_inner, bg=bg_card, padx=10, pady=8, highlightbackground=border_card, highlightthickness=1)
        card3.pack(fill="x", pady=4)

        r_chot_hdr = tk.Frame(card3, bg=bg_card)
        r_chot_hdr.pack(fill="x", pady=(0, 4))

        tk.Label(r_chot_hdr, text="💬 3. TIN NHẮN CHỐT DƯỚI CÙNG", font=("Segoe UI", 9, "bold"), fg="#d97706" if is_light else "#fbbf24", bg=bg_card).pack(side="left")
        
        def _reset_default_closing_msg():
            def_msg = "đã gửi mail hoặc thầy cô vào mail hoặc vào đường link trên đây tải nhé! có gì cứ nhắn zalo nhé!"
            self.txt_fake_drive_closing.delete("1.0", tk.END)
            self.txt_fake_drive_closing.insert("1.0", def_msg)
            self._refresh_fake_drive_preview()
            self.show_toast("Khôi Phục", "Đã khôi phục tin nhắn chốt mặc định!", "info")

        tk.Button(
            r_chot_hdr,
            text="🔄 Khôi Phục Mặc Định",
            font=("Segoe UI", 7),
            bg="#e2e8f0" if is_light else "#334155",
            fg=text_sec,
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            command=_reset_default_closing_msg
        ).pack(side="right")

        self.txt_fake_drive_closing = tk.Text(
            card3,
            height=2,
            font=("Segoe UI", 8),
            bg=ent_bg,
            fg=ent_fg,
            insertbackground=insert_clr,
            relief="solid",
            bd=1,
            wrap="word"
        )
        self.txt_fake_drive_closing.insert("1.0", "đã gửi mail hoặc thầy cô vào mail hoặc vào đường link trên đây tải nhé! có gì cứ nhắn zalo nhé!")
        self.txt_fake_drive_closing.pack(fill="x", pady=(0, 2))
        self.txt_fake_drive_closing.bind("<KeyRelease>", lambda e: self._schedule_fake_drive_refresh(180))

        # --- CARD 4: BỘ NÚT HÀNH ĐỘNG & ĐIỀU HƯỚNG GỬI ---
        card4 = tk.Frame(left_inner, bg=bg_card, padx=10, pady=10, highlightbackground=border_card, highlightthickness=1)
        card4.pack(fill="x", pady=6)

        # Hàng chọn Target Mode (Khóa Nền Zalo PC vs Gửi Cửa Sổ Active)
        r_mode = tk.Frame(card4, bg=bg_card)
        r_mode.pack(fill="x", pady=(0, 6))

        tk.Label(r_mode, text="Đích Gửi:", font=("Segoe UI", 8, "bold"), fg=text_pri, bg=bg_card).pack(side="left")
        self.btn_fake_drive_target_mode = tk.Button(
            r_mode,
            text="🔒 Khóa Nền Zalo PC",
            font=("Segoe UI", 8, "bold"),
            bg="#8b5cf6",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_fake_drive_target_mode
        )
        self.btn_fake_drive_target_mode.pack(side="left", padx=6)

        tk.Label(
            r_mode,
            text="(Bắn ngầm vào Zalo PC hoặc gửi vào cửa sổ Active)",
            font=("Segoe UI", 7, "italic"),
            fg=text_sec,
            bg=bg_card
        ).pack(side="left")

        # NÚT BẮN ZALO 1-CLICK NỔI BẬT
        self.btn_fake_drive_send_zalo = tk.Button(
            card4,
            text="🚀 BẮN VÀO ZALO PC / CỬA SỔ ACTIVE (1-CLICK)",
            font=("Segoe UI", 11, "bold"),
            bg="#059669",
            fg="white",
            activebackground="#047857",
            activeforeground="white",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._send_fake_drive_to_zalo
        )
        self.btn_fake_drive_send_zalo.pack(fill="x", pady=(0, 6))

        # Các nút sao chép vào Clipboard chuyên nghiệp
        r_sub_btns = tk.Frame(card4, bg=bg_card)
        r_sub_btns.pack(fill="x")

        sub_btn_cfg = {"font": ("Segoe UI", 8, "bold"), "relief": "flat", "padx": 6, "pady": 4, "cursor": "hand2"}
        tk.Button(r_sub_btns, text="📋 Copy Ảnh (DIB)", bg="#0284c7", fg="white", command=self._copy_fake_drive_image, **sub_btn_cfg).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(r_sub_btns, text="📋 Copy Link & Chốt", bg="#8b5cf6", fg="white", command=self._copy_fake_drive_text, **sub_btn_cfg).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(r_sub_btns, text="📋 Copy Toàn Bộ", bg="#d97706", fg="white", command=self._copy_fake_drive_all, **sub_btn_cfg).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(r_sub_btns, text="💾 Lưu PNG", bg="#475569", fg="white", command=self._save_fake_drive_image, **sub_btn_cfg).pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Label hiển thị trạng thái gửi
        self.lbl_fake_drive_status = tk.Label(card4, text="Sẵn sàng render & gửi vào Zalo PC.", font=("Segoe UI", 8, "italic"), fg=text_sec, bg=bg_card)
        self.lbl_fake_drive_status.pack(fill="x", pady=(6, 0))

        # =========================================================================
        # CỘT PHẢI: LIVE PREVIEW ẢNH MOCKUP DRIVE & NỘI DUNG VĂN BẢN GỬI KÈM
        # =========================================================================
        right_container = tk.Frame(paned, bg="#f8fafc" if is_light else "#0f172a", padx=4, pady=4)
        paned.add(right_container, minsize=380, width=540)

        # 1. Preview Ảnh
        box_img_prev = tk.Frame(right_container, bg=bg_card, padx=8, pady=8, highlightbackground=border_card, highlightthickness=1)
        box_img_prev.pack(fill="both", expand=True, pady=(0, 4))

        tk.Label(
            box_img_prev,
            text="👁️ LIVE PREVIEW: ẢNH POPUP CHIA SẺ GOOGLE DRIVE CHUẨN MATERIAL DESIGN",
            font=("Segoe UI", 9, "bold"),
            fg="#ea580c" if is_light else "#fb923c",
            bg=bg_card
        ).pack(anchor="w", pady=(0, 4))

        self.lbl_fake_drive_img_preview = tk.Label(box_img_prev, bg="#9fa8b1", text="Đang tải ảnh preview...")
        self.lbl_fake_drive_img_preview.pack(fill="both", expand=True, padx=2, pady=2)

        # 2. Preview Nội Dung Tin Nhắn Gửi Kèm
        box_txt_prev = tk.Frame(right_container, bg=bg_card, padx=8, pady=8, highlightbackground=border_card, highlightthickness=1)
        box_txt_prev.pack(fill="x", pady=(4, 0))

        tk.Label(
            box_txt_prev,
            text="📝 NỘI DUNG VĂN BẢN GỬI KÈM PHÍA DƯỚI ẢNH (LINK KHỐI + TIN NHẮN CHỐT):",
            font=("Segoe UI", 8, "bold"),
            fg="#0284c7" if is_light else "#38bdf8",
            bg=bg_card
        ).pack(anchor="w", pady=(0, 2))

        self.txt_fake_drive_msg_preview = tk.Text(
            box_txt_prev,
            height=6,
            font=("Consolas", 8),
            bg=ent_bg,
            fg=ent_fg,
            relief="solid",
            bd=1,
            wrap="word"
        )
        self.txt_fake_drive_msg_preview.pack(fill="x", pady=2)

        # Kích hoạt render preview lần đầu sau khi GUI đã nạp
        self.after(200, self._refresh_fake_drive_preview)

    def _toggle_fake_drive_target_mode(self):
        """Chuyển đổi giữa chế độ Khóa Nền Zalo PC và Gửi vào Cửa Sổ Active."""
        if getattr(self, "fake_drive_target_mode", "target_locked") == "target_locked":
            self.fake_drive_target_mode = "free_mode"
            self.btn_fake_drive_target_mode.configure(text="🌐 Gửi Active (Bất kỳ App)", bg="#0284c7")
            self.show_toast("Chế Độ Gửi", "Đã chuyển sang: Bắn trực tiếp vào cửa sổ soạn thảo đang kích hoạt (UltraViewer / AnyDesk / Word / Browser)!", "info")
        else:
            self.fake_drive_target_mode = "target_locked"
            self.btn_fake_drive_target_mode.configure(text="🔒 Khóa Nền Zalo PC", bg="#8b5cf6")
            self.show_toast("Chế Độ Gửi", "Đã chuyển sang: Khóa Nền tự động tìm và gửi vào Zalo PC!", "info")

    def _get_fake_drive_email_list(self) -> List[str]:
        """Trích xuất danh sách tất cả các email hợp lệ từ ô nhập liệu."""
        if not hasattr(self, "txt_fake_drive_emails") or not self.txt_fake_drive_emails.winfo_exists():
            return ["vothihuyen82@gmail.com"]
        raw = self.txt_fake_drive_emails.get("1.0", tk.END).strip()
        import re
        found = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", raw)
        # Loại bỏ các chuỗi đường dẫn tệp tạm nếu có
        cleaned = [e for e in found if not e.endswith(".png") and "storage" not in e]
        # Giữ thứ tự duy nhất
        unique = []
        for e in cleaned:
            if e not in unique:
                unique.append(e)
        return unique if unique else ["vothihuyen82@gmail.com"]

    def _schedule_fake_drive_refresh(self, delay_ms: int = 180):
        """Debounce render preview để chống giật lag khi gõ phím liên tục."""
        if hasattr(self, "_fake_drive_debounce_job") and self._fake_drive_debounce_job:
            try:
                self.after_cancel(self._fake_drive_debounce_job)
            except Exception:
                pass
        self._fake_drive_debounce_job = self.after(delay_ms, self._refresh_fake_drive_preview)

    def _on_fake_drive_email_changed(self):
        """Cập nhật đếm số email và debounce render lại Live Preview khi người dùng nhập."""
        emails = self._get_fake_drive_email_list()
        cnt = len(emails)
        if hasattr(self, "lbl_fake_drive_email_count") and self.lbl_fake_drive_email_count.winfo_exists():
            self.lbl_fake_drive_email_count.configure(text=f"({cnt} email)")
        self._schedule_fake_drive_refresh(180)

    def _on_fake_drive_add_single_email(self):
        """Mở hộp thoại nhập thêm 1 email vào danh sách."""
        new_em = simpledialog.askstring("Thêm Email", "Nhập địa chỉ email người nhận mới:", parent=self)
        if new_em and new_em.strip():
            import re
            m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", new_em.strip())
            target_em = m.group(0) if m else new_em.strip()
            cur_txt = self.txt_fake_drive_emails.get("1.0", tk.END).strip()
            if cur_txt:
                self.txt_fake_drive_emails.insert(tk.END, f", {target_em}")
            else:
                self.txt_fake_drive_emails.insert(tk.END, target_em)
            self._on_fake_drive_email_changed()
            self.show_toast("Đã Thêm Email", f"Đã thêm email: {target_em}", "info")

    def _on_fake_drive_clear_emails(self):
        """Xóa trắng ô danh sách email."""
        if hasattr(self, "txt_fake_drive_emails"):
            self.txt_fake_drive_emails.delete("1.0", tk.END)
            self._on_fake_drive_email_changed()
            self.show_toast("Đã Xóa Trắng", "Đã xóa danh sách email!", "info")

    def _populate_fake_drive_crm_combo(self):
        """Nạp danh sách khách hàng có email từ CSDL CRM vào Combobox."""
        try:
            customers = self.state.get_all_customers()
            items = []
            for c in customers:
                em = c.get("email", "").strip()
                name = c.get("name", "Khách").strip()
                if em:
                    items.append(f"{name} ({em})")
            if hasattr(self, "cb_fake_drive_crm") and self.cb_fake_drive_crm.winfo_exists():
                self.cb_fake_drive_crm.configure(values=items)
                if items:
                    self.cb_fake_drive_crm.set("Chọn khách hàng từ CRM...")
        except Exception:
            pass

    def _on_fake_drive_crm_user_selected(self, event=None):
        """Khi chọn khách hàng từ CRM, tự động trích xuất email và cộng thêm vào danh sách."""
        val = self.cb_fake_drive_crm.get()
        if not val or "(" not in val:
            return
        import re
        m = re.search(r"\(([^)]+@.+)\)", val)
        if m:
            em = m.group(1).strip()
            cur_txt = self.txt_fake_drive_emails.get("1.0", tk.END).strip()
            if em not in cur_txt:
                if cur_txt:
                    self.txt_fake_drive_emails.insert(tk.END, f", {em}")
                else:
                    self.txt_fake_drive_emails.insert(tk.END, em)
            self._on_fake_drive_email_changed()
            self.show_toast("Đã Thêm Khách CRM", f"Đã thêm email: {em}", "info")

    def _on_fake_drive_email_paste(self):
        """Dán nhanh tất cả email từ Clipboard."""
        try:
            import pyperclip
            txt = pyperclip.paste().strip()
        except Exception:
            try:
                txt = self.clipboard_get().strip()
            except Exception:
                txt = ""
        if txt:
            import re
            found = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", txt)
            if found:
                joined = ", ".join(found)
                cur_txt = self.txt_fake_drive_emails.get("1.0", tk.END).strip()
                if cur_txt:
                    self.txt_fake_drive_emails.insert(tk.END, f", {joined}")
                else:
                    self.txt_fake_drive_emails.insert(tk.END, joined)
                self._on_fake_drive_email_changed()
                self.show_toast("Đã Dán Email", f"Đã nạp {len(found)} email từ Clipboard!", "info")
            else:
                self.show_toast("Không Tìm Thấy Email", "Không tìm thấy địa chỉ email hợp lệ trong Clipboard!", "warning")

    def _select_fake_drive_grades(self, mode: str):
        """Chọn nhanh khối cho Tab Fake Drive."""
        for g in QUICK_LINK_GRADES:
            var = self.fake_drive_grade_vars.get(g)
            if not var:
                continue
            if mode == "all":
                var.set(True)
            elif mode == "none":
                var.set(False)
            elif mode == "thcs":
                var.set(g in ("Khối 6", "Khối 7", "Khối 8", "Khối 9", "Link THCS"))
            elif mode == "thpt":
                var.set(g in ("Khối 10", "Khối 11", "Khối 12", "Link THPT"))
        self._refresh_fake_drive_preview()

    def _get_fake_drive_active_grades(self) -> List[str]:
        """Trả về danh sách các khối đang được tích chọn."""
        return [g for g in QUICK_LINK_GRADES if self.fake_drive_grade_vars.get(g, tk.BooleanVar(value=False)).get()]

    def _get_fake_drive_links_and_closing_text(self) -> str:
        """Tạo chuỗi văn bản gồm danh sách link khối (có nhãn) và tin nhắn chốt dưới cùng."""
        active_grades = self._get_fake_drive_active_grades()
        include_label = self.fake_drive_include_label_var.get()
        lines = []

        mapping_short = {
            "Khối 6": "K6", "Khối 7": "K7", "Khối 8": "K8", "Khối 9": "K9",
            "Khối 10": "K10", "Khối 11": "K11", "Khối 12": "K12",
            "Link THCS": "THCS", "Link THPT": "THPT"
        }

        for g in active_grades:
            items = self.quick_links_data.get(g, [])
            target_link = None
            for it in items:
                if it.get("checked", False):
                    target_link = it
                    break
            if not target_link and items:
                target_link = items[0]

            if target_link:
                url = target_link.get("url", "").strip()
                name = target_link.get("name", "Link").strip()
                if url:
                    abbr = mapping_short.get(g, g)
                    if include_label:
                        lines.append(f"[{abbr} - {name}]: {url}")
                    else:
                        lines.append(url)

        closing_msg = self.txt_fake_drive_closing.get("1.0", tk.END).strip() if hasattr(self, "txt_fake_drive_closing") else ""
        
        parts = []
        if lines:
            parts.append("\n".join(lines))
        if closing_msg:
            parts.append(closing_msg)

        return "\n\n".join(parts)

    def _refresh_fake_drive_preview(self):
        """Render ảnh Popup Google Drive Share mới nhất và cập nhật Live Preview trên GUI."""
        if not hasattr(self, "lbl_fake_drive_img_preview") or not self.lbl_fake_drive_img_preview.winfo_exists():
            return

        emails = self._get_fake_drive_email_list()
        active_grades = self._get_fake_drive_active_grades()
        role = self.fake_drive_role_var.get()
        notify = self.fake_drive_notify_var.get()
        msg = self.fake_drive_msg_var.get().strip()

        # Ánh xạ tên khối sang tên thư mục Drive hiển thị chuẩn trên hình
        mapping_folder = {
            "Khối 6": "BỘ MỚI HK1 K6",
            "Khối 7": "BỘ MỚI HK1 K7",
            "Khối 8": "BỘ MỚI HK1 K8",
            "Khối 9": "BỘ MỚI HK1 K9",
            "Khối 10": "BỘ MỚI HK1 K10",
            "Khối 11": "BỘ MỚI HK1 K11",
            "Khối 12": "BỘ MỚI HK1 K12",
            "Link THCS": "BỘ MỚI HK1 THCS (6-9)",
            "Link THPT": "BỘ MỚI HK1 THPT (10-12)"
        }
        folders = [mapping_folder.get(g, g) for g in active_grades] if active_grades else ["BỘ MỚI HK1 K11"]

        try:
            out_p = render_drive_share_image(
                email=emails,
                folders=folders,
                role=role,
                notify=notify,
                message=msg
            )
            self.fake_drive_current_img_path = out_p

            if os.path.exists(out_p):
                pil_img = None
                pil_resized = None
                try:
                    pil_img = Image.open(out_p)
                    w, h = pil_img.size
                    
                    target_w = 440
                    target_h = int(h * (target_w / float(w)))
                    pil_resized = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(pil_resized)
                    self.fake_drive_img_photo = photo
                    self.lbl_fake_drive_img_preview.configure(image=photo, text="")
                finally:
                    if pil_img:
                        try:
                            pil_img.close()
                        except Exception:
                            pass
                    if pil_resized:
                        try:
                            pil_resized.close()
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"[Fake Drive Preview] Lỗi render: {e}")
            self.lbl_fake_drive_img_preview.configure(text=f"Lỗi render preview: {e}", image="")

        if hasattr(self, "txt_fake_drive_msg_preview") and self.txt_fake_drive_msg_preview.winfo_exists():
            full_text = self._get_fake_drive_links_and_closing_text()
            self.txt_fake_drive_msg_preview.delete("1.0", tk.END)
            self.txt_fake_drive_msg_preview.insert("1.0", full_text)

    def _copy_fake_drive_image(self):
        """Sao chép file ảnh Mockup Google Drive vào Windows Clipboard dưới dạng DIB."""
        if not self.fake_drive_current_img_path or not os.path.exists(self.fake_drive_current_img_path):
            self._refresh_fake_drive_preview()

        p = self.fake_drive_current_img_path
        if not p or not os.path.exists(p):
            self.show_toast("Lỗi", "Không tìm thấy file ảnh render!", "error")
            return

        ok = ZaloAutomation.copy_image_to_clipboard(p)
        if not ok:
            ok = ZaloAutomation.copy_files_to_clipboard([p])

        if ok:
            self.show_toast("Đã Copy Ảnh (DIB)", "Đã nạp ảnh Google Drive vào Clipboard! Bạn có thể dán (Ctrl+V) vào Zalo, Word, Browser,...", "success")
        else:
            self.show_toast("Lỗi", "Không thể nạp ảnh vào Clipboard!", "error")

    def _copy_fake_drive_text(self):
        """Sao chép toàn bộ text gồm Link Khối & Tin Nhắn Chốt vào Clipboard."""
        full_text = self._get_fake_drive_links_and_closing_text()
        if not full_text:
            self.show_toast("Trống", "Nội dung tin nhắn trống!", "warning")
            return
        try:
            import pyperclip
            pyperclip.copy(full_text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(full_text)
        self.show_toast("Đã Sao Chép", "Đã sao chép Link khối & Tin nhắn chốt vào Clipboard!", "success")

    def _copy_fake_drive_all(self):
        """Nạp ảnh vào Clipboard và sao chép link đính kèm."""
        self._copy_fake_drive_image()
        full_text = self._get_fake_drive_links_and_closing_text()
        self.show_toast("Đã Sao Chép Toàn Bộ", "Đã nạp Ảnh vào Clipboard sẵn sàng để Ctrl+V dán ngay!", "success")

    def _save_fake_drive_image(self):
        """Mở hộp thoại lưu ảnh PNG ra máy tính."""
        if not self.fake_drive_current_img_path or not os.path.exists(self.fake_drive_current_img_path):
            self._refresh_fake_drive_preview()

        src_p = self.fake_drive_current_img_path
        if not src_p or not os.path.exists(src_p):
            self.show_toast("Lỗi", "Chưa có ảnh render!", "error")
            return

        dest_p = filedialog.asksaveasfilename(
            title="Lưu Ảnh Chia Sẻ Google Drive",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            initialfile=f"Google_Drive_Share_{int(time.time())}.png"
        )
        if dest_p:
            import shutil
            shutil.copy2(src_p, dest_p)
            self.show_toast("Đã Lưu Ảnh", f"Đã lưu ảnh vào: {os.path.basename(dest_p)}", "success")

    def _send_fake_drive_to_zalo(self):
        """
        Bắn 1-Click vào Zalo PC hoặc Cửa sổ Active:
        1. Hủy focus trên ô nhập email để chống việc dán nhầm vào chính Dashboard.
        2. Render ảnh Google Drive Share mới nhất với 1 hoặc nhiều email.
        3. Sử dụng ZaloAutomation.send_drive_mockup_and_text để gửi an toàn.
        """
        # Bỏ focus ô nhập liệu trên Dashboard để đảm bảo an toàn tuyệt đối
        try:
            self.focus_set()
        except Exception:
            pass

        self._refresh_fake_drive_preview()
        img_p = self.fake_drive_current_img_path
        if not img_p or not os.path.exists(img_p):
            self.show_toast("Lỗi", "Chưa thể tạo ảnh render!", "error")
            return

        text_to_send = self._get_fake_drive_links_and_closing_text()
        emails = self._get_fake_drive_email_list()
        email_desc = f"{len(emails)} email ({', '.join(emails[:2])}...)" if len(emails) > 1 else emails[0]
        is_bg = (getattr(self, "fake_drive_target_mode", "target_locked") == "target_locked")
        target_name = "Zalo PC (Khóa Nền)" if is_bg else "Cửa Sổ Active"

        if hasattr(self, "lbl_fake_drive_status"):
            self.lbl_fake_drive_status.configure(text=f"⏳ Đang dán ảnh & gửi vào {target_name} ({email_desc})...", fg="#fbbf24")
        self.set_footer_task(f"Đang bắn ảnh Drive và link vào {target_name}...")

        def _worker():
            try:
                ZaloAutomation.reset_abort()
                retries_cfg = int(self.app_settings.get("max_retries", 5))

                ok, reason = ZaloAutomation.send_drive_mockup_and_text(
                    image_path=img_p,
                    text_content=text_to_send,
                    background_mode=is_bg,
                    auto_press_enter=True,
                    max_attempts=retries_cfg
                )

                def _ui_done():
                    if not self.winfo_exists():
                        return
                    if ok:
                        msg = f"🎉 Đã bắn ảnh Drive Share & Link cho {email_desc} thành công vào {target_name}!"
                        if hasattr(self, "lbl_fake_drive_status"):
                            self.lbl_fake_drive_status.configure(text=msg, fg="#34d399")
                        self.show_toast("Thành Công", msg, "success")
                        self.set_footer_task("Sẵn sàng.")
                    else:
                        err_msg = f"❌ Gửi vào {target_name} thất bại ({reason}). Hãy đảm bảo cửa sổ {target_name} đang mở!"
                        if hasattr(self, "lbl_fake_drive_status"):
                            self.lbl_fake_drive_status.configure(text=err_msg, fg="#ef4444")
                        self.show_toast("Lỗi Gửi Zalo", err_msg, "error")
                        self.set_footer_task("Lỗi gửi Zalo.")

                self.after(0, _ui_done)
            except Exception as e:
                logger.error(f"[Fake Drive Send Error]: {e}", exc_info=True)
                def _ui_err():
                    if self.winfo_exists():
                        if hasattr(self, "lbl_fake_drive_status"):
                            self.lbl_fake_drive_status.configure(text=f"❌ Lỗi: {e}", fg="#ef4444")
                        self.show_toast("Lỗi Gửi", f"Đã xảy ra lỗi: {e}", "error")
                self.after(0, _ui_err)

        threading.Thread(target=_worker, daemon=True).start()

    # =========================================================================
    # TAB: 👥 QUẢN LÝ THÔNG TIN KHÁCH HÀNG & KHỐI MUA (CRM)
    # =========================================================================
    def _build_customers_tab(self, parent):
        """Xây dựng Tab Quản Lý Thông Tin Khách Hàng, Khối Mua & Check Trùng Email / SĐT."""
        self.crm_current_id = None
        self.crm_search_var = tk.StringVar()
        self.crm_search_var.trace_add("write", lambda *args: self._on_crm_search_changed())
        self.crm_grade_filter_var = tk.StringVar(value="Tất Cả Khối")
        self.crm_sort_var = tk.StringVar(value="Mới Nhất")
        self.crm_page = 1
        self.crm_page_size_var = tk.IntVar(value=50)
        self.crm_total_records = 0
        self.crm_total_pages = 1
        self.crm_auto_merge_var = tk.BooleanVar(value=True)

        # Biến check chọn khối mua 6-12
        self.crm_grade_vars = {
            "6": tk.BooleanVar(value=False),
            "7": tk.BooleanVar(value=False),
            "8": tk.BooleanVar(value=False),
            "9": tk.BooleanVar(value=False),
            "10": tk.BooleanVar(value=False),
            "11": tk.BooleanVar(value=False),
            "12": tk.BooleanVar(value=False)
        }

        # 1. TOP TOOLBAR: Tìm kiếm + Lọc khối mua + Sắp xếp + Thêm mới + Nhập/Xuất hàng loạt
        top_bar = tk.Frame(parent, bg="#1e293b", padx=10, pady=6)
        top_bar.pack(fill="x", pady=(0, 6))

        tk.Label(top_bar, text="🔍 Tìm Kiếm:", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")
        ent_search = tk.Entry(top_bar, textvariable=self.crm_search_var, font=("Segoe UI", 9), bg="#0f172a", fg="#f8fafc", insertbackground="white", width=18)
        ent_search.pack(side="left", padx=(4, 8))

        tk.Label(top_bar, text="📚 Khối Mua:", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e293b").pack(side="left")
        self.crm_filter_cb = ttk.Combobox(
            top_bar,
            textvariable=self.crm_grade_filter_var,
            values=[
                "Tất Cả Khối",
                "Lớp 6", "Lớp 7", "Lớp 8", "Lớp 9",
                "Lớp 10", "Lớp 11", "Lớp 12",
                "K6789 (Khối THCS)",
                "K101112 (Khối THPT)",
                "K6-12 (Trọn Bộ)"
            ],
            state="readonly",
            width=17
        )
        self.crm_filter_cb.pack(side="left", padx=(4, 4))
        self.crm_filter_cb.bind("<<ComboboxSelected>>", self._on_crm_filter_changed)

        btn_multi_filter = tk.Button(top_bar, text="🎛️ Lọc Nhiều Khối...", bg="#334155", fg="#38bdf8", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=self._open_crm_multi_grade_filter_modal)
        btn_multi_filter.pack(side="left", padx=(0, 8))

        tk.Label(top_bar, text="🔽 Sắp Xếp:", font=("Segoe UI", 9, "bold"), fg="#fbbf24", bg="#1e293b").pack(side="left")
        self.crm_sort_cb = ttk.Combobox(
            top_bar,
            textvariable=self.crm_sort_var,
            values=["Mới Nhất", "Cũ Nhất", "Tên A-Z", "Tên Z-A", "Email A-Z"],
            state="readonly",
            width=12
        )
        self.crm_sort_cb.pack(side="left", padx=(4, 10))
        self.crm_sort_cb.bind("<<ComboboxSelected>>", self._on_crm_sort_changed)

        btn_add = tk.Button(top_bar, text="➕ Thêm Khách", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._create_new_customer)
        btn_add.pack(side="left", padx=2)

        btn_import = tk.Button(top_bar, text="📥 Nhập Hàng Loạt", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._open_crm_batch_import_modal)
        btn_import.pack(side="left", padx=2)

        btn_export = tk.Button(top_bar, text="📤 Xuất File", bg="#0d9488", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._export_customers)
        btn_export.pack(side="left", padx=2)

        btn_copy_all_emails = tk.Button(top_bar, text="📋 Copy All Emails", bg="#6366f1", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._copy_all_customer_emails)
        btn_copy_all_emails.pack(side="left", padx=2)

        btn_copy_all_phones = tk.Button(top_bar, text="📞 Copy All SĐT", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2", command=self._copy_all_customer_phones)
        btn_copy_all_phones.pack(side="left", padx=2)

        btn_refresh = tk.Button(top_bar, text="🔄 Làm Mới", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=self._refresh_customers_list)
        btn_refresh.pack(side="right", padx=2)

        # 2. PANED WINDOW: Cột Trái = Form Nhập/Sửa; Cột Phải = Danh Sách Khách Hàng & Phân Trang
        paned = tk.PanedWindow(parent, orient="horizontal", bg="#1e293b", sashwidth=4)
        paned.pack(fill="both", expand=True)

        # ==================== CỘT TRÁI: FORM NHẬP / SỬA THÔNG TIN KHÁCH HÀNG ====================
        left_f = tk.Frame(paned, bg="#0f172a", padx=10, pady=8)
        paned.add(left_f, minsize=340, width=390)

        tk.Label(left_f, text="👤 THÔNG TIN CHI TIẾT KHÁCH HÀNG", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(anchor="w", pady=(0, 6))

        # Họ & Tên
        tk.Label(left_f, text="Họ & Tên (*):", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        self.crm_name_ent = tk.Entry(left_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.crm_name_ent.pack(fill="x", pady=(2, 5))
        self.crm_name_ent.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_name_ent.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # Email
        tk.Label(left_f, text="Địa Chỉ Email (*):", font=("Segoe UI", 8, "bold"), fg="#f8fafc", bg="#0f172a").pack(anchor="w")
        self.crm_email_ent = tk.Entry(left_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.crm_email_ent.pack(fill="x", pady=(2, 5))
        self.crm_email_ent.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_email_ent.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # Số Điện Thoại
        tk.Label(left_f, text="Số Điện Thoại (Zalo):", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.crm_phone_ent = tk.Entry(left_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.crm_phone_ent.pack(fill="x", pady=(2, 5))
        self.crm_phone_ent.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_phone_ent.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # Trường học công tác
        tk.Label(left_f, text="Trường Học Công Tác:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.crm_school_ent = tk.Entry(left_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.crm_school_ent.pack(fill="x", pady=(2, 5))
        self.crm_school_ent.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_school_ent.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # Địa chỉ
        tk.Label(left_f, text="Địa Chỉ / Tỉnh Thành:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.crm_addr_ent = tk.Entry(left_f, font=("Segoe UI", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.crm_addr_ent.pack(fill="x", pady=(2, 5))
        self.crm_addr_ent.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_addr_ent.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # Ghi chú
        tk.Label(left_f, text="Ghi Chú / Nhu Cầu:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.crm_notes_txt = tk.Text(left_f, font=("Segoe UI", 8), bg="#1e293b", fg="#f8fafc", insertbackground="white", height=2)
        self.crm_notes_txt.pack(fill="x", pady=(2, 6))
        self.crm_notes_txt.bind("<Control-s>", lambda e: (self._save_current_customer(), "break")[1])
        self.crm_notes_txt.bind("<Control-S>", lambda e: (self._save_current_customer(), "break")[1])

        # KHỐI MUA: CHỌN TRỰC TIẾP & CHỌN NHANH (HIỂN THỊ 2 HÀNG RÕ RÀNG TRÁNH BỊ CHE MẤT KHI MÀN HÌNH NHỎ)
        grade_box = tk.LabelFrame(left_f, text=" 📚 QUẢN LÝ KHỐI MUA (CHỌN NHIỀU) ", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a", padx=6, pady=4)
        grade_box.pack(fill="x", pady=(0, 6))

        # Hàng 1: Khối THCS (Lớp 6, 7, 8, 9)
        row_chk_thcs = tk.Frame(grade_box, bg="#0f172a")
        row_chk_thcs.pack(fill="x", pady=(1, 2))
        for g in ["6", "7", "8", "9"]:
            chk = tk.Checkbutton(
                row_chk_thcs,
                text=f"Lớp {g}",
                variable=self.crm_grade_vars[g],
                font=("Segoe UI", 8, "bold"),
                bg="#0f172a",
                fg="#f8fafc",
                selectcolor="#1e293b",
                activebackground="#0f172a",
                activeforeground="#38bdf8"
            )
            chk.pack(side="left", padx=(0, 6))

        # Hàng 2: Khối THPT (Lớp 10, 11, 12)
        row_chk_thpt = tk.Frame(grade_box, bg="#0f172a")
        row_chk_thpt.pack(fill="x", pady=(1, 4))
        for g in ["10", "11", "12"]:
            chk = tk.Checkbutton(
                row_chk_thpt,
                text=f"Lớp {g}",
                variable=self.crm_grade_vars[g],
                font=("Segoe UI", 8, "bold"),
                bg="#0f172a",
                fg="#f8fafc",
                selectcolor="#1e293b",
                activebackground="#0f172a",
                activeforeground="#38bdf8"
            )
            chk.pack(side="left", padx=(0, 6))

        # Hàng 3: Các nút chọn nhanh combo
        row_quick_btn = tk.Frame(grade_box, bg="#0f172a")
        row_quick_btn.pack(fill="x", pady=(2, 2))

        tk.Button(row_quick_btn, text="⚡ K6789 (THCS)", bg="#334155", fg="#38bdf8", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._set_crm_grades(["6", "7", "8", "9"])).pack(side="left", padx=(0, 2))
        tk.Button(row_quick_btn, text="⚡ K101112 (THPT)", bg="#334155", fg="#a855f7", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._set_crm_grades(["10", "11", "12"])).pack(side="left", padx=(0, 2))
        tk.Button(row_quick_btn, text="⭐ Trọn Bộ K6-12", bg="#334155", fg="#fbbf24", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._set_crm_grades(["6", "7", "8", "9", "10", "11", "12"])).pack(side="left", padx=(0, 2))
        tk.Button(row_quick_btn, text="🔄 Bỏ Hết", bg="#334155", fg="#fca5a5", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2", command=lambda: self._set_crm_grades([])).pack(side="left")

        # Checkbox Tự động gộp / cập nhật nếu trùng Email
        chk_merge = tk.Checkbutton(
            left_f,
            text="Tự động gộp khối mua & cập nhật nếu trùng Email",
            variable=self.crm_auto_merge_var,
            font=("Segoe UI", 8),
            bg="#0f172a",
            fg="#34d399",
            selectcolor="#1e293b",
            activebackground="#0f172a"
        )
        chk_merge.pack(anchor="w", pady=(0, 6))

        # Cụm nút hành động Form
        act_card = tk.Frame(left_f, bg="#0f172a")
        act_card.pack(fill="x", pady=(2, 4))

        btn_save = tk.Button(act_card, text="💾 Lưu Khách Hàng", bg="#22c55e", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=3, cursor="hand2", command=self._save_current_customer)
        btn_save.pack(side="left", padx=(0, 3))

        btn_new = tk.Button(act_card, text="➕ Tạo Mới", bg="#0284c7", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=3, cursor="hand2", command=self._create_new_customer)
        btn_new.pack(side="left", padx=2)

        btn_check_dup = tk.Button(act_card, text="🔍 Check Trùng", bg="#d97706", fg="white", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2", command=self._check_duplicate_customer)
        btn_check_dup.pack(side="left", padx=2)

        btn_del = tk.Button(act_card, text="🗑️ Xóa", bg="#dc2626", fg="white", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2", command=self._delete_current_customer)
        btn_del.pack(side="left", padx=2)

        self.crm_form_status_lbl = tk.Label(left_f, text="Sẵn sàng nhập / chỉnh sửa (Ctrl+S để lưu).", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        self.crm_form_status_lbl.pack(anchor="w", pady=(4, 0))

        # ==================== CỘT PHẢI: BẢNG DANH SÁCH & PHÂN TRANG ====================
        right_f = tk.Frame(paned, bg="#0f172a", padx=8, pady=8)
        paned.add(right_f, minsize=420)

        # Bảng Treeview danh sách khách hàng (selectmode='extended' hỗ trợ chọn nhiều dòng bằng Shift+Up/Down, Ctrl+Click)
        tree_f = tk.Frame(right_f, bg="#0f172a")
        tree_f.pack(fill="both", expand=True)

        cols = ("id", "name", "email", "phone", "school", "grades", "address", "notes", "created")
        self.crm_tree = ttk.Treeview(tree_f, columns=cols, show="headings", selectmode="extended")

        self.crm_tree.heading("id", text="ID")
        self.crm_tree.heading("name", text="Họ & Tên")
        self.crm_tree.heading("email", text="Email")
        self.crm_tree.heading("phone", text="Số Điện Thoại")
        self.crm_tree.heading("school", text="Trường Học Công Tác")
        self.crm_tree.heading("grades", text="Khối Đã Mua")
        self.crm_tree.heading("address", text="Địa Chỉ")
        self.crm_tree.heading("notes", text="Ghi Chú")
        self.crm_tree.heading("created", text="Ngày Tạo")

        self.crm_tree.column("id", width=35, anchor="center")
        self.crm_tree.column("name", width=130, anchor="w")
        self.crm_tree.column("email", width=170, anchor="w")
        self.crm_tree.column("phone", width=95, anchor="center")
        self.crm_tree.column("school", width=130, anchor="w")
        self.crm_tree.column("grades", width=105, anchor="center")
        self.crm_tree.column("address", width=100, anchor="w")
        self.crm_tree.column("notes", width=120, anchor="w")
        self.crm_tree.column("created", width=85, anchor="center")

        sb_y = tk.Scrollbar(tree_f, orient="vertical", command=self.crm_tree.yview)
        sb_x = tk.Scrollbar(tree_f, orient="horizontal", command=self.crm_tree.xview)
        self.crm_tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.crm_tree.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")

        self.crm_tree.bind("<<TreeviewSelect>>", self._on_crm_tree_select)
        self.crm_tree.bind("<Double-1>", self._on_crm_tree_double_click)
        self.crm_tree.bind("<Control-c>", self._on_crm_tree_ctrl_c)
        self.crm_tree.bind("<Control-C>", self._on_crm_tree_ctrl_c)
        self.crm_tree.bind("<Button-3>", self._show_crm_context_menu)

        # Context Menu chuột phải
        self.crm_context_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#0284c7")
        self.crm_context_menu.add_command(label="✏️ Chỉnh Sửa Thông Tin", command=lambda: self._on_crm_tree_select())
        self.crm_context_menu.add_separator()
        self.crm_context_menu.add_command(label="📋 Sao Chép Email (Các Dòng Đang Chọn)", command=lambda: self._copy_selected_customer_field("email"))
        self.crm_context_menu.add_command(label="📞 Sao Chép Số Điện Thoại (Các Dòng Đang Chọn)", command=lambda: self._copy_selected_customer_field("phone"))
        self.crm_context_menu.add_command(label="📄 Sao Chép Toàn Bộ Dòng (Ctrl+C)", command=lambda: self._copy_selected_customer_field("all"))
        self.crm_context_menu.add_separator()
        self.crm_context_menu.add_command(label="🗑️ Xóa Khách Hàng Đang Chọn", command=self._delete_current_customer)

        # THANH PHÂN TRANG (PAGINATION BAR)
        page_bar = tk.Frame(right_f, bg="#1e293b", padx=8, pady=4)
        page_bar.pack(fill="x", pady=(4, 0))

        tk.Button(page_bar, text="⏮ Đầu", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=1, cursor="hand2", command=self._crm_go_first_page).pack(side="left", padx=1)
        tk.Button(page_bar, text="◀ Trước", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=1, cursor="hand2", command=self._crm_go_prev_page).pack(side="left", padx=1)

        self.crm_page_lbl = tk.Label(page_bar, text="Trang 1 / 1 (Tổng: 0 khách hàng)", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b")
        self.crm_page_lbl.pack(side="left", padx=8)

        tk.Button(page_bar, text="Sau ▶", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=1, cursor="hand2", command=self._crm_go_next_page).pack(side="left", padx=1)
        tk.Button(page_bar, text="Cuối ⏭", bg="#334155", fg="#f8fafc", font=("Segoe UI", 8), relief="flat", padx=6, pady=1, cursor="hand2", command=self._crm_go_last_page).pack(side="left", padx=1)

        tk.Label(page_bar, text="Dòng/Trang:", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(side="right", padx=(6, 2))
        self.crm_page_size_cb = ttk.Combobox(page_bar, textvariable=self.crm_page_size_var, values=[20, 50, 100, 200], width=4, state="readonly")
        self.crm_page_size_cb.pack(side="right", padx=2)
        self.crm_page_size_cb.bind("<<ComboboxSelected>>", self._on_crm_page_size_changed)

        # Nạp dữ liệu ban đầu
        self._refresh_customers_list()

    def _set_crm_grades(self, grades_list: List[str]):
        """Bật/Tắt các checkbox khối mua theo danh sách."""
        for g in self.crm_grade_vars:
            self.crm_grade_vars[g].set(g in grades_list)

    def _get_selected_crm_grades(self) -> List[str]:
        """Lấy danh sách các khối đang được tích chọn."""
        res = [g for g in ["6", "7", "8", "9", "10", "11", "12"] if self.crm_grade_vars[g].get()]
        return res

    def _refresh_customers_list(self):
        """Tải và hiển thị danh sách khách hàng có phân trang, tìm kiếm và bộ lọc."""
        self.crm_tree.delete(*self.crm_tree.get_children())

        search_q = self.crm_search_var.get().strip() if hasattr(self, 'crm_search_var') else ""
        grade_flt = self.crm_grade_filter_var.get().strip() if hasattr(self, 'crm_grade_filter_var') else ""
        sort_choice = self.crm_sort_var.get().strip() if hasattr(self, 'crm_sort_var') else "Mới Nhất"

        sort_map = {
            "Mới Nhất": "created_desc",
            "Cũ Nhất": "created_asc",
            "Tên A-Z": "name_asc",
            "Tên Z-A": "name_desc",
            "Email A-Z": "email_asc"
        }
        sort_by = sort_map.get(sort_choice, "created_desc")
        page_size = self.crm_page_size_var.get() if hasattr(self, 'crm_page_size_var') else 50

        customers, total_count = self.state.get_customers(
            search_query=search_q,
            grade_filter=grade_flt,
            sort_by=sort_by,
            page=self.crm_page,
            page_size=page_size
        )

        self.crm_total_records = total_count
        import math
        self.crm_total_pages = max(1, math.ceil(total_count / max(1, page_size)))
        if self.crm_page > self.crm_total_pages:
            self.crm_page = self.crm_total_pages

        for c in customers:
            grades = c.get("purchased_grades", [])
            if isinstance(grades, list):
                if set(grades) == set(["6", "7", "8", "9"]):
                    g_badge = "K6789 (THCS)"
                elif set(grades) == set(["10", "11", "12"]):
                    g_badge = "K101112 (THPT)"
                elif len(grades) == 7:
                    g_badge = "⭐ K6-12 Trọn Bộ"
                elif grades:
                    g_badge = ", ".join(grades)
                else:
                    g_badge = "Chưa chọn"
            else:
                g_badge = str(grades)

            created_short = c.get("created_at", "")[:10] if c.get("created_at") else ""
            self.crm_tree.insert("", "end", iid=str(c['id']), values=(
                c['id'],
                c.get("name", ""),
                c.get("email", ""),
                c.get("phone", ""),
                c.get("school", ""),
                g_badge,
                c.get("address", ""),
                c.get("notes", ""),
                created_short
            ))

        if hasattr(self, 'crm_page_lbl'):
            self.crm_page_lbl.configure(text=f"Trang {self.crm_page} / {self.crm_total_pages} (Tổng: {total_count} khách hàng)")

    def _open_crm_multi_grade_filter_modal(self):
        """Mở Modal chọn nhiều khối mua cùng lúc để lọc danh sách khách hàng."""
        modal = tk.Toplevel(self)
        modal.title("🎛️ Lọc Khách Hàng Theo Nhiều Khối Mua")
        modal.geometry("450x330")
        modal.minsize(400, 280)
        modal.transient(self)
        modal.grab_set()

        is_light = getattr(self, "current_theme", "light_theme") in ("tailwind_light", "light_theme", "light")
        bg_col = "#ffffff" if is_light else "#0f172a"
        fg_col = "#0f172a" if is_light else "#f8fafc"
        sub_bg = "#f1f5f9" if is_light else "#1e293b"
        apply_windows_dark_titlebar(modal, bg_col, fg_col)

        modal.configure(bg=bg_col)

        hdr = tk.Frame(modal, bg=sub_bg, padx=14, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎛️ CHỌN CÁC KHỐI CẦN LỌC (CÓ THỂ CHỌN NHIỀU KHỐI)", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg=sub_bg).pack(anchor="w")

        body = tk.Frame(modal, bg=bg_col, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Chọn các khối lớp muốn tìm kiếm khách hàng đã mua:", font=("Segoe UI", 9), fg=fg_col, bg=bg_col).pack(anchor="w", pady=(0, 6))

        filter_vars = {}
        cur_filter = self.crm_grade_filter_var.get()
        for g in ["6", "7", "8", "9", "10", "11", "12"]:
            is_checked = False
            if g in cur_filter or (cur_filter == "K6789 (Khối THCS)" and g in ["6", "7", "8", "9"]) or (cur_filter == "K101112 (Khối THPT)" and g in ["10", "11", "12"]) or (cur_filter == "K6-12 (Trọn Bộ)"):
                is_checked = True
            filter_vars[g] = tk.BooleanVar(value=is_checked)

        # Khung Checkbox 2 hàng trong modal
        chk_frame = tk.LabelFrame(body, text=" Danh Sách Khối Lớp ", font=("Segoe UI", 8, "bold"), fg="#34d399", bg=bg_col, padx=10, pady=8)
        chk_frame.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(chk_frame, bg=bg_col)
        row1.pack(fill="x", pady=2)
        for g in ["6", "7", "8", "9"]:
            tk.Checkbutton(row1, text=f"Lớp {g}", variable=filter_vars[g], font=("Segoe UI", 9, "bold"), bg=bg_col, fg=fg_col, selectcolor=sub_bg, activebackground=bg_col).pack(side="left", padx=(0, 12))

        row2 = tk.Frame(chk_frame, bg=bg_col)
        row2.pack(fill="x", pady=2)
        for g in ["10", "11", "12"]:
            tk.Checkbutton(row2, text=f"Lớp {g}", variable=filter_vars[g], font=("Segoe UI", 9, "bold"), bg=bg_col, fg=fg_col, selectcolor=sub_bg, activebackground=bg_col).pack(side="left", padx=(0, 12))

        # Quick buttons trong modal
        q_row = tk.Frame(body, bg=bg_col)
        q_row.pack(fill="x", pady=(0, 8))

        def _set_f_grades(g_list):
            for k in filter_vars:
                filter_vars[k].set(k in g_list)

        tk.Button(q_row, text="⚡ THCS (6-9)", bg=sub_bg, fg="#38bdf8", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=lambda: _set_f_grades(["6", "7", "8", "9"])).pack(side="left", padx=(0, 4))
        tk.Button(q_row, text="⚡ THPT (10-12)", bg=sub_bg, fg="#a855f7", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=lambda: _set_f_grades(["10", "11", "12"])).pack(side="left", padx=(0, 4))
        tk.Button(q_row, text="⭐ Tất Cả (6-12)", bg=sub_bg, fg="#fbbf24", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2", command=lambda: _set_f_grades(["6", "7", "8", "9", "10", "11", "12"])).pack(side="left", padx=(0, 4))
        tk.Button(q_row, text="🔄 Bỏ Chọn", bg=sub_bg, fg="#fca5a5", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=lambda: _set_f_grades([])).pack(side="left")

        act_bar = tk.Frame(modal, bg=sub_bg, padx=14, pady=10)
        act_bar.pack(fill="x", side="bottom")

        def _do_apply_filter():
            selected = [g for g in ["6", "7", "8", "9", "10", "11", "12"] if filter_vars[g].get()]
            if not selected or len(selected) == 7:
                self.crm_grade_filter_var.set("Tất Cả Khối")
            elif set(selected) == {"6", "7", "8", "9"}:
                self.crm_grade_filter_var.set("K6789 (Khối THCS)")
            elif set(selected) == {"10", "11", "12"}:
                self.crm_grade_filter_var.set("K101112 (Khối THPT)")
            else:
                self.crm_grade_filter_var.set("Lớp " + ", ".join(selected))

            self.crm_page = 1
            self._refresh_customers_list()
            self.show_toast("Bộ Lọc Khối", f"Đã áp dụng bộ lọc: {self.crm_grade_filter_var.get()}", "info")
            modal.destroy()

        btn_ok = tk.Button(act_bar, text="🔍 Áp Dụng Lọc", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=_do_apply_filter)
        btn_ok.pack(side="left", padx=(0, 6))

        btn_cancel = tk.Button(act_bar, text="Hủy", bg="#475569", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=modal.destroy)
        btn_cancel.pack(side="right")

    def _on_crm_search_changed(self):
        self.crm_page = 1
        self._refresh_customers_list()

    def _on_crm_filter_changed(self, event=None):
        self.crm_page = 1
        self._refresh_customers_list()

    def _on_crm_sort_changed(self, event=None):
        self.crm_page = 1
        self._refresh_customers_list()

    def _on_crm_page_size_changed(self, event=None):
        self.crm_page = 1
        self._refresh_customers_list()

    def _crm_go_first_page(self):
        if self.crm_page != 1:
            self.crm_page = 1
            self._refresh_customers_list()

    def _crm_go_prev_page(self):
        if self.crm_page > 1:
            self.crm_page -= 1
            self._refresh_customers_list()

    def _crm_go_next_page(self):
        if self.crm_page < self.crm_total_pages:
            self.crm_page += 1
            self._refresh_customers_list()

    def _crm_go_last_page(self):
        if self.crm_page != self.crm_total_pages:
            self.crm_page = self.crm_total_pages
            self._refresh_customers_list()

    def _on_crm_tree_select(self, event=None):
        sel = self.crm_tree.selection()
        if not sel:
            return
        cid = int(sel[0])
        self._load_customer_to_editor(cid)

    def _on_crm_tree_double_click(self, event=None):
        self._on_crm_tree_select()

    def _on_crm_tree_ctrl_c(self, event=None):
        """Sao chép nhanh thông tin các khách hàng đang chọn trong CRM Treeview (Shift+Up/Down, Ctrl+Click)."""
        self._copy_selected_customer_field("all")
        return "break"

    def _show_crm_context_menu(self, event):
        """Hiển thị context menu chuột phải trong bảng khách hàng, giữ nguyên vùng chọn nhiều nếu có."""
        row_id = self.crm_tree.identify_row(event.y)
        if row_id:
            current_sel = self.crm_tree.selection()
            if row_id not in current_sel:
                self.crm_tree.selection_set(row_id)
                self._load_customer_to_editor(int(row_id))
            self.crm_context_menu.post(event.x_root, event.y_root)

    def _load_customer_to_editor(self, customer_id: int):
        c = self.state.get_customer_by_id(customer_id)
        if not c:
            return
        self.crm_current_id = c['id']
        self.crm_name_ent.delete(0, tk.END)
        self.crm_name_ent.insert(0, c.get("name", ""))

        self.crm_email_ent.delete(0, tk.END)
        self.crm_email_ent.insert(0, c.get("email", ""))

        self.crm_phone_ent.delete(0, tk.END)
        self.crm_phone_ent.insert(0, c.get("phone", ""))

        self.crm_school_ent.delete(0, tk.END)
        self.crm_school_ent.insert(0, c.get("school", ""))

        self.crm_addr_ent.delete(0, tk.END)
        self.crm_addr_ent.insert(0, c.get("address", ""))

        self.crm_notes_txt.delete("1.0", tk.END)
        self.crm_notes_txt.insert("1.0", c.get("notes", ""))

        self._set_crm_grades(c.get("purchased_grades", []))
        self.crm_form_status_lbl.configure(text=f"Đang chỉnh sửa: {c.get('name', '')} (ID: {c['id']})", fg="#34d399")

    def _create_new_customer(self):
        """Xóa trắng form để thêm mới khách hàng."""
        self.crm_current_id = None
        self.crm_name_ent.delete(0, tk.END)
        self.crm_email_ent.delete(0, tk.END)
        self.crm_phone_ent.delete(0, tk.END)
        self.crm_school_ent.delete(0, tk.END)
        self.crm_addr_ent.delete(0, tk.END)
        self.crm_notes_txt.delete("1.0", tk.END)
        self._set_crm_grades([])
        self.crm_name_ent.focus_set()
        self.crm_form_status_lbl.configure(text="Đang tạo khách hàng mới... (Ctrl+S để lưu)", fg="#38bdf8")

    def _save_current_customer(self):
        """Lưu hoặc cập nhật khách hàng từ Form."""
        name = self.crm_name_ent.get().strip()
        email = self.crm_email_ent.get().strip()
        phone = self.crm_phone_ent.get().strip()
        school = self.crm_school_ent.get().strip()
        addr = self.crm_addr_ent.get().strip()
        notes = self.crm_notes_txt.get("1.0", tk.END).strip()
        grades = self._get_selected_crm_grades()
        auto_merge = self.crm_auto_merge_var.get()

        ok, msg, new_id = self.state.save_customer(
            name=name,
            email=email,
            phone=phone,
            school=school,
            address=addr,
            notes=notes,
            purchased_grades=grades,
            customer_id=self.crm_current_id,
            overwrite_on_duplicate=auto_merge
        )

        if ok:
            self.crm_current_id = new_id
            self.show_toast("Thành Công (Ctrl+S)", msg, "success")
            self._refresh_customers_list()
            self._load_customer_to_editor(new_id)
        else:
            self.show_toast("Cảnh Báo", msg, "error")

    def _check_duplicate_customer(self):
        """Kiểm tra xem Email hoặc SĐT đã tồn tại trong CSDL hay chưa."""
        email = self.crm_email_ent.get().strip()
        phone = self.crm_phone_ent.get().strip()

        if not email and not phone:
            self.show_toast("Nhập Thông Tin", "Vui lòng nhập Email hoặc Số điện thoại để kiểm tra trùng!", "warning")
            return

        dup_info = []
        if email:
            by_email = self.state.get_customer_by_email(email)
            if by_email and (not self.crm_current_id or by_email['id'] != self.crm_current_id):
                g_str = ", ".join(by_email.get("purchased_grades", [])) or "Chưa có"
                dup_info.append(f"• Email '{email}' đã tồn tại: {by_email.get('name')} (Khối: {g_str})")

        if phone:
            by_phone = self.state.get_customer_by_phone(phone)
            if by_phone and (not self.crm_current_id or by_phone['id'] != self.crm_current_id):
                dup_info.append(f"• SĐT '{phone}' đã tồn tại: {by_phone.get('name')}")

        if dup_info:
            full_msg = "\n".join(dup_info)
            messagebox.showwarning("Phát Hiện Trùng Thông Tin", f"Đã tìm thấy thông tin trùng trong hệ thống:\n\n{full_msg}")
        else:
            self.show_toast("Không Trùng", "Email và Số điện thoại này hoàn toàn MỚI, chưa có trong hệ thống!", "success")

    def _delete_current_customer(self):
        """Xóa các khách hàng đang chọn (hỗ trợ xóa 1 hoặc nhiều khách hàng cùng lúc)."""
        sel = self.crm_tree.selection() if hasattr(self, 'crm_tree') else ()
        if not sel:
            if not self.crm_current_id:
                self.show_toast("Chưa Chọn", "Vui lòng chọn ít nhất 1 khách hàng để xóa!", "warning")
                return
            sel = [str(self.crm_current_id)]

        count = len(sel)
        if count == 1:
            cid = int(sel[0])
            c = self.state.get_customer_by_id(cid)
            name = c.get("name", "này") if c else "này"
            if messagebox.askyesno("Xác Nhận Xóa", f"Bạn có chắc chắn muốn xóa khách hàng '{name}' khỏi hệ thống?"):
                self.state.delete_customer(cid)
                self.show_toast("Đã Xóa", f"Đã xóa khách hàng '{name}' thành công!", "info")
                self._create_new_customer()
                self._refresh_customers_list()
        else:
            if messagebox.askyesno("Xác Nhận Xóa Nhiều", f"Bạn có chắc chắn muốn XÓA TOÀN BỘ {count} khách hàng đang chọn khỏi hệ thống?"):
                for iid in sel:
                    try:
                        self.state.delete_customer(int(iid))
                    except Exception:
                        pass
                self.show_toast("Đã Xóa", f"Đã xóa thành công {count} khách hàng!", "info")
                self._create_new_customer()
                self._refresh_customers_list()

    def _copy_selected_customer_field(self, field_name: str):
        """
        Sao chép email, sđt hoặc toàn bộ thông tin của các khách hàng đang chọn.
        Hỗ trợ chọn 1 hoặc nhiều dòng (Shift + Up/Down, Ctrl + Click).
        """
        sel = self.crm_tree.selection() if hasattr(self, 'crm_tree') else ()
        if not sel:
            if self.crm_current_id:
                sel = [str(self.crm_current_id)]
            else:
                self.show_toast("Chưa Chọn", "Vui lòng chọn ít nhất 1 khách hàng trong bảng!", "warning")
                return

        customers = []
        for iid in sel:
            try:
                c = self.state.get_customer_by_id(int(iid))
                if c:
                    customers.append(c)
            except Exception:
                pass

        if not customers:
            return

        try:
            import pyperclip
            if field_name == "email":
                emails = [c.get("email", "").strip() for c in customers if c.get("email")]
                val = ", ".join(emails) if len(emails) > 1 else (emails[0] if emails else "")
                pyperclip.copy(val)
                self.show_toast("Đã Sao Chép Email", f"Đã sao chép {len(emails)} địa chỉ email vào Clipboard!", "success")
            elif field_name == "phone":
                phones = [c.get("phone", "").strip() for c in customers if c.get("phone")]
                val = ", ".join(phones) if len(phones) > 1 else (phones[0] if phones else "")
                pyperclip.copy(val)
                self.show_toast("Đã Sao Chép SĐT", f"Đã sao chép {len(phones)} số điện thoại vào Clipboard!", "success")
            else:
                lines = []
                for c in customers:
                    g_str = ", ".join(c.get("purchased_grades", []))
                    lines.append(f"{c.get('name', '')} | {c.get('email', '')} | {c.get('phone', '')} | {c.get('school', '')} | Khối: [{g_str}] | {c.get('address', '')}")
                val = "\n".join(lines)
                pyperclip.copy(val)
                self.show_toast("Đã Sao Chép (Ctrl+C)", f"Đã sao chép thông tin của {len(customers)} khách hàng vào Clipboard!", "success")
        except Exception as e:
            self.show_toast("Lỗi Sao Chép", f"Lỗi: {e}", "error")

    def _copy_all_customer_emails(self):
        """Sao chép toàn bộ danh sách email khách hàng (ngăn cách bởi dấu phẩy)."""
        customers = self.state.get_all_customers_simple()
        emails = [c['email'].strip() for c in customers if c.get('email') and "@" in c['email']]
        if not emails:
            self.show_toast("Không Có Email", "Chưa có danh sách email nào trong hệ thống!", "warning")
            return
        joined = ", ".join(emails)
        try:
            import pyperclip
            pyperclip.copy(joined)
            self.show_toast("Đã Sao Chép All Emails", f"Đã sao chép {len(emails)} địa chỉ email vào Clipboard!", "success")
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(joined)
            self.show_toast("Đã Sao Chép", f"Đã sao chép {len(emails)} email!", "success")

    def _copy_all_customer_phones(self):
        """Sao chép toàn bộ danh sách Số Điện Thoại khách hàng (loại bỏ trùng lặp)."""
        customers = self.state.get_all_customers_simple()
        phones = [c['phone'].strip() for c in customers if c.get('phone') and c['phone'].strip()]
        unique_phones = []
        seen = set()
        for p in phones:
            clean_p = p.replace(" ", "").replace(".", "").replace("-", "")
            if clean_p not in seen:
                seen.add(clean_p)
                unique_phones.append(p)

        if not unique_phones:
            self.show_toast("Không Có SĐT", "Chưa có số điện thoại nào trong hệ thống khách hàng!", "warning")
            return

        joined = ", ".join(unique_phones)
        try:
            import pyperclip
            pyperclip.copy(joined)
            self.show_toast("Đã Sao Chép All SĐT", f"Đã sao chép {len(unique_phones)} số điện thoại vào Clipboard!", "success")
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(joined)
            self.show_toast("Đã Sao Chép All SĐT", f"Đã sao chép {len(unique_phones)} số điện thoại!", "success")

    def _export_customers(self):
        """Xuất danh sách khách hàng ra file CSV hoặc JSON."""
        f_path = filedialog.asksaveasfilename(
            title="Xuất Danh Sách Khách Hàng & Khối Mua",
            defaultextension=".csv",
            filetypes=[("CSV File (*.csv)", "*.csv"), ("JSON File (*.json)", "*.json")],
            initialfile="danh_sach_khach_hang_crm.csv"
        )
        if f_path:
            try:
                cnt = self.state.export_customers_to_file(f_path)
                self.show_toast("Xuất Thành Công", f"Đã xuất {cnt} khách hàng ra file:\n{os.path.basename(f_path)}", "success")
            except Exception as e:
                self.show_toast("Lỗi Xuất File", f"Đã xảy ra lỗi: {e}", "error")

    def _open_crm_batch_import_modal(self):
        """Mở Modal Nhập Danh Sách Khách Hàng Hàng Loạt (Hỗ trợ Dán Văn Bản hoặc Nạp File CSV/JSON)."""
        modal = tk.Toplevel(self)
        modal.title("📥 Nhập Danh Sách Khách Hàng Hàng Loạt")
        modal.geometry("620x520")
        modal.configure(bg="#0f172a")
        modal.transient(self)
        modal.grab_set()

        tk.Label(modal, text="📥 NHẬP HÀNG LOẠT KHÁCH HÀNG & KHỐI MUA", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a").pack(pady=(12, 4))
        tk.Label(
            modal,
            text="Dán danh sách (mỗi dòng 1 khách, ngăn cách bởi dấu phẩy hoặc tab):\nVí dụ: Tên, Email, SĐT, Trường học, Khối (6,7,8,9), Địa chỉ, Ghi chú",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a",
            justify="center"
        ).pack(pady=(0, 6))

        txt_f = tk.Frame(modal, bg="#0f172a", padx=14)
        txt_f.pack(fill="both", expand=True)

        input_txt = tk.Text(txt_f, font=("Consolas", 9), bg="#1e293b", fg="#f8fafc", insertbackground="white", height=12)
        input_txt.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(txt_f, orient="vertical", command=input_txt.yview)
        sb.pack(side="right", fill="y")
        input_txt.configure(yscrollcommand=sb.set)

        # Cài đặt xử lý trùng
        dup_frame = tk.LabelFrame(modal, text=" Xử Lý Khi Trùng Email ", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#0f172a", padx=10, pady=4)
        dup_frame.pack(fill="x", padx=14, pady=6)

        dup_action_var = tk.StringVar(value="merge")
        tk.Radiobutton(dup_frame, text="Gộp khối mua & Cập nhật thông tin (Khuyên dùng)", variable=dup_action_var, value="merge", bg="#0f172a", fg="#34d399", selectcolor="#1e293b", font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)
        tk.Radiobutton(dup_frame, text="Bỏ qua nếu đã có", variable=dup_action_var, value="skip", bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b", font=("Segoe UI", 8)).pack(side="left", padx=4)
        tk.Radiobutton(dup_frame, text="Ghi đè toàn bộ", variable=dup_action_var, value="overwrite", bg="#0f172a", fg="#fca5a5", selectcolor="#1e293b", font=("Segoe UI", 8)).pack(side="left", padx=4)

        act_f = tk.Frame(modal, bg="#0f172a", padx=14, pady=10)
        act_f.pack(fill="x")

        def _do_file_import():
            f_path = filedialog.askopenfilename(
                title="Chọn File CSV hoặc JSON",
                filetypes=[("CSV / JSON File (*.csv, *.json)", "*.csv *.json"), ("Tất Cả File (*.*)", "*.*")],
                parent=modal
            )
            if f_path:
                try:
                    added, updated = self.state.import_customers_from_file(f_path, on_duplicate=dup_action_var.get())
                    self._refresh_customers_list()
                    messagebox.showinfo("Nạp File Thành Công", f"Kết quả nạp từ file:\n• Thêm mới: {added} khách hàng\n• Cập nhật / Gộp thông tin: {updated} khách hàng", parent=modal)
                    modal.destroy()
                except Exception as e:
                    messagebox.showerror("Lỗi Nạp File", f"Đã xảy ra lỗi: {e}", parent=modal)

        def _do_text_import():
            raw_text = input_txt.get("1.0", tk.END).strip()
            if not raw_text:
                messagebox.showwarning("Chưa Có Dữ Liệu", "Vui lòng dán danh sách hoặc chọn file!", parent=modal)
                return

            lines = raw_text.split("\n")
            items = []
            for line in lines:
                l = line.strip()
                if not l:
                    continue
                # Hỗ trợ phân cách bởi tab hoặc dấu phẩy hoặc chấm phẩy
                delim = "\t" if "\t" in l else ("," if "," in l else ";")
                parts = [p.strip() for p in l.split(delim)]
                if len(parts) == 1 and "@" in parts[0]:
                    items.append({"name": "Thầy/Cô", "email": parts[0], "purchased_grades": []})
                elif len(parts) >= 2:
                    name = parts[0]
                    email = parts[1]
                    phone = parts[2] if len(parts) > 2 else ""
                    school = parts[3] if len(parts) > 3 else ""
                    grades_raw = parts[4] if len(parts) > 4 else ""
                    grades_list = [g.strip() for g in grades_raw.replace(";", ",").split(",") if g.strip()]
                    addr = parts[5] if len(parts) > 5 else ""
                    notes = parts[6] if len(parts) > 6 else ""
                    items.append({
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "school": school,
                        "purchased_grades": grades_list,
                        "address": addr,
                        "notes": notes
                    })

            if not items:
                messagebox.showwarning("Không Có Dòng Hợp Lệ", "Không tìm thấy thông tin email hợp lệ nào!", parent=modal)
                return

            added, updated = self.state.batch_import_customers(items, on_duplicate=dup_action_var.get())
            self._refresh_customers_list()
            messagebox.showinfo("Nạp Danh Sách Thành Công", f"Đã xử lý {len(items)} dòng:\n• Thêm mới: {added} khách hàng\n• Cập nhật / Gộp thông tin: {updated} khách hàng", parent=modal)
            modal.destroy()

        btn_import_file = tk.Button(act_f, text="📁 Nạp Từ File CSV/JSON", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=_do_file_import)
        btn_import_file.pack(side="left", padx=4)

        btn_execute = tk.Button(act_f, text="🚀 Bắt Đầu Nạp Văn Bản", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=_do_text_import)
        btn_execute.pack(side="right", padx=4)

        btn_close = tk.Button(act_f, text="Đóng", bg="#334155", fg="#f8fafc", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=modal.destroy)
        btn_close.pack(side="right", padx=4)





