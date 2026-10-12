import os
import re
from typing import List, Dict, Any, Optional

class LocalFileSearcher:
    """Công cụ tìm kiếm siêu nhanh tài liệu giáo án, PPCT, đề kiểm tra, phiếu học tập trong máy tính."""

    def __init__(self, root_dir: str = "C:/GiaoAnLichSu"):
        self.root_dir = root_dir

    def search(
        self,
        query: str = "",
        grade: Optional[str] = None,
        material_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm file theo từ khóa, khối lớp và loại tài liệu trong thư mục máy tính.
        """
        if not os.path.exists(self.root_dir):
            return []

        results = []
        lower_query = query.lower().strip() if query else ""
        
        # Mở rộng loại tài liệu
        type_keywords = {
            "ppct": ["ppct", "phan phoi", "phân phối", "ke hoach giang day"],
            "de_kiem_tra": ["de", "đề", "kiem tra", "kiểm tra", "trac nghiem", "giua ky", "cuoi ky", "15 phut"],
            "phieu_hoc_tap": ["phieu", "phiếu", "hoc tap", "học tập", "phieu nhom", "hoat dong"],
            "bai_giang": ["slide", "powerpoint", "ppt", "bai giang", "bài giảng", "chuyen de"]
        }

        target_keywords = type_keywords.get(material_type, []) if material_type else []

        for root, _, files in os.walk(self.root_dir):
            for file in files:
                # Bỏ qua các file ẩn/tạm
                if file.startswith("~$") or file.startswith("."):
                    continue

                full_path = os.path.join(root, file).replace("\\", "/")
                lower_name = file.lower()
                lower_full = full_path.lower()

                # Lọc theo khối/lớp nếu có
                if grade:
                    g_clean = grade.replace("LỚP", "").replace("LOP", "").strip()
                    if f"lop {g_clean}" not in lower_full and f"lop{g_clean}" not in lower_full and f"lớp {g_clean}" not in lower_full and f"sử {g_clean}" not in lower_full:
                        continue

                # Lọc theo loại tài liệu nếu có
                if target_keywords:
                    if not any(kw in lower_full for kw in target_keywords):
                        continue

                # Lọc theo query người dùng gõ
                if lower_query:
                    # Tách các từ khóa tìm kiếm
                    words = lower_query.split()
                    if not all(w in lower_full for w in words):
                        continue

                # Tính dung lượng file
                size_mb = 0.0
                try:
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                except Exception:
                    pass

                results.append({
                    "filename": file,
                    "filepath": full_path,
                    "directory": root.replace("\\", "/"),
                    "size_mb": size_mb,
                    "extension": os.path.splitext(file)[1].lower()
                })

        return results
