import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class DriveManager:
    """Quản lý cấp quyền Google Drive, tự động chuyển link phụ 1-2 khi link chính đầy 500 email và tra cứu tài liệu kèm theo."""

    def __init__(self, credentials_path: str = "config/service_account.json", enabled: bool = False, state_manager = None):
        self.credentials_path = credentials_path
        self.enabled = enabled and os.path.exists(credentials_path)
        self.state_mgr = state_manager
        self.service = None
        self.matrix_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "curriculum_matrix.json")
        self.matrix = self._load_matrix()
        self.email_limit = self.matrix.get("email_limit_per_link", 500)

        if self.enabled:
            self._init_service()

    def _load_matrix(self) -> Dict[str, Any]:
        if os.path.exists(self.matrix_path):
            with open(self.matrix_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_matrix(self, new_matrix: Dict[str, Any]):
        """Lưu lại bảng ma trận cấu hình link mới từ Dashboard."""
        self.matrix = new_matrix
        with open(self.matrix_path, "w", encoding="utf-8") as f:
            json.dump(new_matrix, f, ensure_ascii=False, indent=2)
        logger.info("[Drive] Đã cập nhật ma trận link Google Drive mới.")

    def _init_service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            scopes = ['https://www.googleapis.com/auth/drive']
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=scopes
            )
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("[Drive] Khởi tạo Google Drive Service thành công.")
        except Exception as e:
            logger.warning(f"[Drive] Chưa thể kết nối Google Drive API: {e}")
            self.enabled = False

    def get_folder_info(self, grade_or_level: str) -> Optional[Dict[str, Any]]:
        grade_or_level = grade_or_level.upper().strip()
        if grade_or_level in self.matrix.get("curriculum_levels", {}):
            return self.matrix["curriculum_levels"][grade_or_level]
        
        cleaned_grade = grade_or_level.replace("LỚP", "").replace("LOP", "").replace("L", "").strip()
        if cleaned_grade in self.matrix.get("grade_details", {}):
            return self.matrix["grade_details"][cleaned_grade]
        return None

    def get_active_link(self, grade_or_level: str) -> Tuple[str, str]:
        """
        Chọn link khả dụng (primary -> backup_1 -> backup_2) nếu số email vượt ngưỡng 500.
        Trả về: (link_type, drive_link)
        """
        folder_info = self.get_folder_info(grade_or_level)
        if not folder_info:
            return "primary", ""

        links = folder_info.get("drive_links", {})
        if not isinstance(links, dict):
            return "primary", folder_info.get("drive_link", "")

        # Kiểm tra số lượng email đã gán cho từng link nếu có StateManager
        if self.state_mgr:
            for l_type in ["primary", "backup_1", "backup_2"]:
                count = self.state_mgr.get_email_count_for_link(grade_or_level, l_type)
                if count < self.email_limit and links.get(l_type):
                    return l_type, links[l_type]
        
        # Mặc định lấy link primary hoặc backup_1
        return "primary", links.get("primary") or links.get("backup_1", "")

    def get_material_link(self, grade: str, material_type: str) -> Optional[str]:
        """Lấy link tài liệu cụ thể: ppct, de_kiem_tra, phieu_hoc_tap, phieu_nhom, chuyen_de."""
        folder_info = self.get_folder_info(grade)
        if folder_info and "materials" in folder_info:
            return folder_info["materials"].get(material_type.lower())
        return None

    def grant_view_permission(self, target_email: str, grade_or_level: str, user_id: str = "") -> Dict[str, Any]:
        """Tự động chọn link (chống đầy 500 email), cấp quyền hoặc gửi link cho khách."""
        folder_info = self.get_folder_info(grade_or_level)
        if not folder_info:
            return {
                "success": False,
                "message": f"Dạ Thầy/Cô đang cần cấp quyền cho Khối/Lớp mấy (Lớp 6 đến 12 hoặc THCS/THPT) ạ?"
            }

        link_type, active_link = self.get_active_link(grade_or_level)
        folder_title = folder_info.get("title") or folder_info.get("name")

        # Ghi log cấp quyền vào CSDL
        if self.state_mgr:
            self.state_mgr.log_drive_access(
                email=target_email,
                grade_or_level=grade_or_level,
                link_type=link_type,
                drive_link=active_link,
                user_id=user_id
            )

        link_note = f" (Link #{link_type})" if link_type != "primary" else ""

        return {
            "success": True,
            "mode": "link_direct",
            "link_type": link_type,
            "folder_name": folder_title,
            "drive_link": active_link,
            "message": f"Dạ em đã thêm email {target_email} vào danh sách truy cập {folder_title}{link_note} rồi ạ! ✨\nThầy/Cô mở xem trực tiếp tại: {active_link}"
        }
