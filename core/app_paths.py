import os
import sys

def get_app_dir() -> str:
    """
    Trả về thư mục gốc của ứng dụng.
    - Khi chạy file .exe đóng gói (PyInstaller): Trả về thư mục chứa file .exe
    - Khi chạy trực tiếp qua python main.py: Trả về thư mục gốc của dự án.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bundle_dir() -> str:
    """
    Trả về thư mục chứa các tài nguyên nội bộ được đóng gói cùng PyInstaller (_MEIPASS nếu có).
    """
    if hasattr(sys, '_MEIPASS'):
        return getattr(sys, '_MEIPASS')
    return get_app_dir()

def get_resource_path(relative_path: str) -> str:
    """
    Tìm đường dẫn file tài nguyên (config, assets, knowledge_base).
    Ưu tiên tìm bên ngoài (cạnh file .exe) để người dùng có thể tùy biến,
    nếu không có thì lấy từ tài nguyên nội bộ đóng gói.
    """
    # 1. Tìm ở thư mục làm việc cạnh file .exe
    external_path = os.path.join(get_app_dir(), relative_path)
    if os.path.exists(external_path):
        return external_path
    
    # 2. Tìm trong bundle nội bộ
    bundled_path = os.path.join(get_bundle_dir(), relative_path)
    if os.path.exists(bundled_path):
        return bundled_path

    return external_path

def get_storage_path(filename: str = "") -> str:
    """
    Trả về đường dẫn tới file/thư mục trong storage luôn nằm cạnh file .exe (để lưu dữ liệu lâu dài).
    """
    storage_dir = os.path.join(get_app_dir(), "storage")
    os.makedirs(storage_dir, exist_ok=True)
    if filename:
        return os.path.join(storage_dir, filename)
    return storage_dir
