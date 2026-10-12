import os
import time
import logging
from typing import Optional, List, Tuple, Dict, Any, Callable, Union
import pyperclip
import pyautogui
pyautogui.FAILSAFE = False

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = False

import psutil

logger = logging.getLogger(__name__)

# Cache Process Name theo PID với TTL 8 giây để giảm 99% CPU khi quét cửa sổ
_PID_PROC_CACHE: Dict[int, Tuple[float, str]] = {}

def get_proc_name_cached(pid: int) -> str:
    """Lấy tên tiến trình từ PID với cache 8s, chống lag & CPU 100% khi enum windows."""
    if not pid:
        return ""
    now = time.time()
    if pid in _PID_PROC_CACHE:
        t, name = _PID_PROC_CACHE[pid]
        if now - t < 8.0:
            return name
    try:
        name = psutil.Process(pid).name().lower()
    except Exception:
        name = ""
    _PID_PROC_CACHE[pid] = (now, name)
    return name

# Giới hạn tối đa số lần thử lại trước khi DỪNG LẠI (chống lặp vô tận)
MAX_RETRIES = 5

# Danh sách từ khóa ứng dụng được phép khóa/ưu tiên (phân cách bằng dấu phẩy)
TARGET_ALLOWED_KEYWORDS: List[str] = ["zalo", "ultraviewer", "anydesk", "teamviewer", "remote desktop", "mstsc"]

# Danh sách từ khóa ứng dụng loại trừ / bỏ qua tuyệt đối (IDE, Code Editor, Terminal,...)
TARGET_EXCLUSION_KEYWORDS: List[str] = ["antigravity", "cursor", "vscode", "code.exe", "pycharm", "powershell", "cmd.exe", "windowsterminal", "laragon"]

# Biến toàn cục: Quản lý Ghim & Khóa Chặt Ứng Dụng Đích (Target Window Isolation)
BACKGROUND_TARGET_INFO = {
    "enabled": True,  # Mặc định BẬT gửi ngầm
    "top_hwnd": None,
    "leaf_hwnd": None,
    "proc_name": "Zalo.exe",
    "title": "Zalo"
}


class ZaloAutomation:
    """
    Module tự động hóa tương tác trực tiếp với Zalo PC trên Windows (Tương thích Python 3.12).
    Có cơ chế giới hạn tối đa 5 lần thử (MAX_RETRIES = 5), nếu thất bại sẽ dừng lại và báo cáo,
    hoàn toàn không chạy vòng lặp vô tận.
    Hỗ trợ Chế độ Khóa Chặt Chạy Nền (Cách ly 100% không ảnh hưởng ứng dụng khác).
    """

    # ============================================================================
    # QUẢN LÝ GHIM & KHÓA CHẶT ỨNG DỤNG ĐÍCH (THEO PHONG CÁCH AUTO KEY PRO)
    # ============================================================================

    @classmethod
    def set_max_retries(cls, count: int):
        global MAX_RETRIES
        try:
            MAX_RETRIES = max(1, int(count))
            logger.info(f"[Zalo Automation] ⚙️ Đã cập nhật giới hạn thử lại: MAX_RETRIES = {MAX_RETRIES} lần")
        except Exception:
            pass

    @classmethod
    def get_max_retries(cls) -> int:
        global MAX_RETRIES
        return MAX_RETRIES

    @staticmethod
    def safe_clipboard_copy(text: str, retries: int = 3) -> bool:
        """Ghi Clipboard an toàn có retry chống lỗi khi app khác khóa clipboard."""
        if text is None:
            text = ""
        for i in range(retries):
            try:
                pyperclip.copy(text)
                return True
            except Exception:
                time.sleep(0.04)
        return False

    @staticmethod
    def safe_clipboard_paste(retries: int = 3) -> str:
        """Đọc Clipboard an toàn có retry."""
        for i in range(retries):
            try:
                return pyperclip.paste() or ""
            except Exception:
                time.sleep(0.04)
        return ""

    @classmethod
    def set_target_keywords(cls, allowed_keywords: Union[str, List[str]], exclusion_keywords: Union[str, List[str]]):
        """Cập nhật danh sách từ khóa Cho Phép Khóa và từ khóa Loại Trừ / Blacklist."""
        global TARGET_ALLOWED_KEYWORDS, TARGET_EXCLUSION_KEYWORDS
        if isinstance(allowed_keywords, str):
            TARGET_ALLOWED_KEYWORDS = [k.strip().lower() for k in allowed_keywords.split(",") if k.strip()]
        elif isinstance(allowed_keywords, list):
            TARGET_ALLOWED_KEYWORDS = [str(k).strip().lower() for k in allowed_keywords if str(k).strip()]

        if isinstance(exclusion_keywords, str):
            TARGET_EXCLUSION_KEYWORDS = [k.strip().lower() for k in exclusion_keywords.split(",") if k.strip()]
        elif isinstance(exclusion_keywords, list):
            TARGET_EXCLUSION_KEYWORDS = [str(k).strip().lower() for k in exclusion_keywords if str(k).strip()]

        logger.info(f"[Target Config] 🎯 Đã nạp từ khóa Cho Phép: {TARGET_ALLOWED_KEYWORDS} | Loại Trừ: {TARGET_EXCLUSION_KEYWORDS}")

    @classmethod
    def get_target_keywords(cls) -> Tuple[List[str], List[str]]:
        """Lấy danh sách từ khóa Cho Phép Khóa và từ khóa Loại Trừ hiện tại."""
        global TARGET_ALLOWED_KEYWORDS, TARGET_EXCLUSION_KEYWORDS
        return list(TARGET_ALLOWED_KEYWORDS), list(TARGET_EXCLUSION_KEYWORDS)

    @staticmethod
    def set_target_window(top_hwnd: Optional[int], leaf_hwnd: Optional[int] = None, proc_name: str = "Zalo.exe", title: str = "Zalo", enabled: bool = True):
        """Cập nhật thông tin cửa sổ ứng dụng đích được khóa ngầm."""
        global BACKGROUND_TARGET_INFO
        BACKGROUND_TARGET_INFO["enabled"] = enabled
        BACKGROUND_TARGET_INFO["top_hwnd"] = top_hwnd
        BACKGROUND_TARGET_INFO["leaf_hwnd"] = leaf_hwnd or top_hwnd
        BACKGROUND_TARGET_INFO["proc_name"] = proc_name
        BACKGROUND_TARGET_INFO["title"] = title
        logger.info(f"[Target Lock] 🔒 Đã khóa đích: [{proc_name}] '{title}' (HWND: {hex(top_hwnd) if top_hwnd else 'None'}) - Khóa nền: {enabled}")

    @staticmethod
    def get_target_window() -> dict:
        """Lấy thông tin cửa sổ đích đang được khóa."""
        global BACKGROUND_TARGET_INFO
        return BACKGROUND_TARGET_INFO

    @staticmethod
    def is_remote_desktop_target(target_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Kiểm tra xem cửa sổ đích có phải là ứng dụng điều khiển máy từ xa (UltraViewer, AnyDesk, TeamViewer, Remote Desktop) hay không.
        """
        t = target_info or BACKGROUND_TARGET_INFO
        proc = (t.get("proc_name") or "").lower()
        title = (t.get("title") or "").lower()
        remote_keywords = ["ultraviewer", "anydesk", "teamviewer", "remote desktop", "mstsc", "vnc", "sunlogin", "toydesk", "rustdesk"]
        return any(k in proc or k in title for k in remote_keywords)

    @staticmethod
    def scan_active_windows() -> List[Tuple[int, str, str, str]]:
        """
        Quét toàn bộ danh sách cửa sổ đang mở trên Windows.
        Trả về danh sách tuple: (hwnd, display_str, proc_name, title)
        Tự động ưu tiên cửa sổ trong danh sách TARGET_ALLOWED_KEYWORDS lên đầu!
        Tuyệt đối loại trừ cửa sổ của Dashboard và các ứng dụng trong TARGET_EXCLUSION_KEYWORDS.
        """
        if not HAS_WIN32:
            return []
        windows_found = []
        cached_pids = {}
        my_pid = os.getpid()

        def enum_cb(hwnd, _):
            try:
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    cls = win32gui.GetClassName(hwnd)
                    
                    # Bỏ qua các cửa sổ hệ thống không cần thiết
                    if not title or title.startswith("Default IME") or title.startswith("MSCTFIME UI") or cls in ["Progman", "Shell_TrayWnd"]:
                        return True

                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid == my_pid:
                            return True  # BỎ QUA APP CỦA MÌNH
                        proc_name = get_proc_name_cached(pid) or "App"
                    except Exception:
                        proc_name = "App"

                    if "AI Zalo CSKH" in title or "Quản Lý Giáo Án" in title:
                        return True

                    # Loại trừ các tiến trình trong danh sách Blacklist/Exclusion
                    proc_low = proc_name.lower()
                    title_low = title.lower()
                    if any(k in proc_low or k in title_low for k in TARGET_EXCLUSION_KEYWORDS):
                        return True

                    display_str = f"[{proc_name}] {title[:50]}"
                    windows_found.append((hwnd, display_str, proc_name, title))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_cb, 0)
        except Exception as e:
            logger.debug(f"[Window Scanner] Lỗi khi enum windows: {e}")

        # Ưu tiên các cửa sổ trong danh sách Allowed lên đầu
        priority_wins = []
        other_wins = []
        for w in windows_found:
            name_lower = (w[2] + " " + w[3]).lower()
            if any(k in name_lower for k in TARGET_ALLOWED_KEYWORDS):
                priority_wins.append(w)
            else:
                other_wins.append(w)
        return priority_wins + other_wins

    @staticmethod
    def pick_window_1click(on_picked_callback: Callable[[Optional[int], Optional[int], str, str], None]):
        """
        Bắt đầu chế độ Click 1-Click để gắn cửa sổ đích (sử dụng pynput mouse listener).
        Khi người dùng click vào bất kỳ cửa sổ nào, hàm callback sẽ nhận được (top_hwnd, leaf_hwnd, proc_name, title).
        """
        try:
            from pynput import mouse
        except ImportError:
            logger.warning("[Window Picker] Không tìm thấy thư viện pynput.")
            on_picked_callback(None, None, "", "")
            return

        my_pid = os.getpid()

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                try:
                    pt = wintypes.POINT(int(x), int(y))
                    clicked_hwnd = user32.WindowFromPoint(pt)
                    if clicked_hwnd and win32gui.IsWindow(clicked_hwnd):
                        leaf_hwnd = clicked_hwnd
                        top_hwnd = win32gui.GetAncestor(clicked_hwnd, win32con.GA_ROOT)
                        if not top_hwnd:
                            top_hwnd = clicked_hwnd
                        
                        _, pid = win32process.GetWindowThreadProcessId(top_hwnd)
                        if pid == my_pid:
                            logger.info("[Window Picker] Bỏ qua click vào chính Dashboard.")
                            return True

                        title = win32gui.GetWindowText(top_hwnd).strip()
                        if not title:
                            title = win32gui.GetWindowText(leaf_hwnd).strip()
                        try:
                            proc_name = get_proc_name_cached(pid) or "App"
                        except Exception:
                            proc_name = "App"
                        
                        on_picked_callback(top_hwnd, leaf_hwnd, proc_name, title)
                    else:
                        on_picked_callback(None, None, "", "")
                except Exception as ex:
                    logger.debug(f"[Window Picker] Lỗi pick window: {ex}")
                    on_picked_callback(None, None, "", "")
                return False  # Dừng listener sau click đầu tiên

        m_listener = mouse.Listener(on_click=on_click)
        m_listener.start()

    @staticmethod
    def test_single_background_key(top_hwnd: Optional[int] = None) -> bool:
        """Thử gửi 1 phím ngầm (Space) vào cửa sổ đích để kiểm tra kết nối chạy nền."""
        target_h = top_hwnd or BACKGROUND_TARGET_INFO.get("top_hwnd") or ZaloAutomation.find_zalo_hwnd()
        if not target_h or not win32gui.IsWindow(target_h):
            return False

        try:
            # Gửi thông điệp kích hoạt nội bộ & phím Space ngầm
            win32gui.PostMessage(target_h, win32con.WM_ACTIVATE, win32con.WA_CLICKACTIVE, 0)
            win32gui.PostMessage(target_h, win32con.WM_SETFOCUS, 0, 0)
            win32gui.PostMessage(target_h, win32con.WM_KEYDOWN, win32con.VK_SPACE, 0)
            time.sleep(0.05)
            win32gui.PostMessage(target_h, win32con.WM_CHAR, ord(' '), 0)
            win32gui.PostMessage(target_h, win32con.WM_KEYUP, win32con.VK_SPACE, 0)
            logger.info(f"[Test Key] ✅ Đã gửi phím ngầm (Space) vào HWND {hex(target_h)}")
            return True
        except Exception as e:
            logger.warning(f"[Test Key] ❌ Lỗi gửi phím ngầm: {e}")
            return False

    @staticmethod
    def send_deep_background_click(top_hwnd: int, x: int, y: int, btn: str = "left") -> bool:
        """
        Gửi click chuột ngầm chính xác theo tọa độ màn hình (X, Y) vào cửa sổ đích (không chiếm chuột thật).
        Tự động chuyển đổi sang tọa độ Client của cửa sổ đích.
        """
        if not top_hwnd or not win32gui.IsWindow(top_hwnd):
            return False

        try:
            pt = wintypes.POINT(int(x), int(y))
            user32.ScreenToClient(top_hwnd, ctypes.byref(pt))
            cx, cy = pt.x, pt.y
            lparam = (cy << 16) | (cx & 0xFFFF)

            # 1. Kích hoạt chuột nền
            win32gui.PostMessage(top_hwnd, win32con.WM_MOUSEACTIVATE, top_hwnd, (win32con.WM_LBUTTONDOWN << 16) | 1)
            win32gui.PostMessage(top_hwnd, win32con.WM_SETCURSOR, top_hwnd, (win32con.WM_LBUTTONDOWN << 16) | 1)
            win32gui.PostMessage(top_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
            time.sleep(0.02)

            # 2. Click ngầm
            if "right" in btn.lower() or "rclick" in btn.lower():
                win32gui.PostMessage(top_hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
                time.sleep(0.03)
                win32gui.PostMessage(top_hwnd, win32con.WM_RBUTTONUP, 0, lparam)
            else:
                win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
                time.sleep(0.03)
                win32gui.PostMessage(top_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

            return True
        except Exception as e:
            logger.debug(f"[Background Click] Lỗi gửi click ngầm: {e}")
            return False

    @staticmethod
    def find_zalo_hwnd() -> Optional[int]:
        """
        Tìm HWND của cửa sổ Zalo PC chính đang mở trên Windows (hoặc cửa sổ đã khóa đích).
        TUYỆT ĐỐI LOẠI TRỪ cửa sổ của chính ứng dụng Dashboard này!
        """
        if not HAS_WIN32:
            return None

        my_pid = os.getpid()

        # 1. Nếu đã khóa đích một cửa sổ hợp lệ thì kiểm tra xem có phải app của mình không
        locked_hwnd = BACKGROUND_TARGET_INFO.get("top_hwnd")
        if locked_hwnd and win32gui.IsWindow(locked_hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(locked_hwnd)
                if pid != my_pid:
                    return locked_hwnd
            except Exception:
                pass

        found_hwnds = []

        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                
                # Bỏ qua các cửa sổ con/popup không phải cửa sổ chính
                if owner != 0:
                    return

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == my_pid:
                        return  # LOẠI BỎ 100% CỬA SỔ CỦA DASHBOARD PYTHON NÀY
                except Exception:
                    pid = 0

                # Bỏ qua nếu tiêu đề là ứng dụng Dashboard của chúng ta
                if "AI Zalo CSKH" in title or "AI ZALO CSKH" in title or "Quản Lý Giáo Án" in title:
                    return

                proc_name = get_proc_name_cached(pid) if pid else ""

                # 1. Khớp ưu tiên số 1: Process Zalo.exe chính chủ
                if "zalo" in proc_name:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 350 and h > 350:
                        found_hwnds.append((hwnd, title or "Zalo Main Window", 100))
                    elif w > 200:
                        found_hwnds.append((hwnd, title or "Zalo Window", 60))
                    return

                # 2. Khớp ưu tiên số 2: Lớp Chrome_WidgetWin_1 của Zalo
                if cls == "Chrome_WidgetWin_1":
                    if "zalo" in title.lower() or "zalo" in proc_name:
                        rect = win32gui.GetWindowRect(hwnd)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 350 and h > 350:
                            found_hwnds.append((hwnd, title or "Zalo Main Window", 90))
                            return

                # 3. Khớp theo Tiêu đề cửa sổ chứa 'Zalo' (ví dụ 'Zalo - Lam Nguyễn')
                if "zalo" in title.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 300 and h > 300:
                        found_hwnds.append((hwnd, title, 80))
                    else:
                        found_hwnds.append((hwnd, title, 30))
                    return

                # 4. Khớp theo UltraViewer hoặc AnyDesk nếu đang điều khiển Zalo máy khác
                if any(k in title.lower() or k in proc_name for k in ["ultraviewer", "anydesk", "teamviewer"]):
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 300 and h > 300:
                        found_hwnds.append((hwnd, title, 50))

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.debug(f"[Zalo Automation] Lỗi khi enum windows: {e}")

        if found_hwnds:
            found_hwnds.sort(key=lambda x: x[2], reverse=True)
            return found_hwnds[0][0]
        return None
    _last_external_hwnd: Optional[int] = None
    _abort_requested: bool = False

    @classmethod
    def request_abort(cls):
        """Yêu cầu dừng / hủy khẩn cấp mọi thao tác tự động, gửi ngầm và gửi tin nhóm."""
        cls._abort_requested = True
        logger.warning("[Zalo Automation] 🛑 ĐÃ KÍCH HOẠT LỆNH HỦY KHẨN CẤP MỌI THAO TÁC (F9)!")

    @classmethod
    def reset_abort(cls):
        """Đặt lại cờ hủy để cho phép thực hiện thao tác mới."""
        cls._abort_requested = False

    @classmethod
    def is_abort_requested(cls) -> bool:
        """Kiểm tra xem người dùng có yêu cầu dừng khẩn cấp hay không."""
        return cls._abort_requested

    @staticmethod
    def force_focus_window(hwnd: int) -> bool:
        """
        Kích hoạt, khôi phục từ Minimize và đưa cửa sổ lên Foreground trên Windows
        (không làm giật chuột, luôn detach thread để chống đơ Not Responding).
        """
        if not HAS_WIN32 or not hwnd:
            return False
        attached_thread = None
        curr_thread = None
        try:
            # 1. Khôi phục nếu đang bị minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            try:
                user32.SwitchToThisWindow(hwnd, True)
            except Exception:
                pass

            # 2. Bypass ASFW lock bằng AttachThreadInput an toàn
            fore_hwnd = win32gui.GetForegroundWindow()
            if fore_hwnd and fore_hwnd != hwnd:
                fore_thread = win32process.GetWindowThreadProcessId(fore_hwnd)[0]
                curr_thread = win32api.GetCurrentThreadId()
                if fore_thread and curr_thread and fore_thread != curr_thread:
                    try:
                        if win32process.AttachThreadInput(curr_thread, fore_thread, True):
                            attached_thread = fore_thread
                    except Exception:
                        pass

            # 3. Mô phỏng phím Alt để Windows cho phép đổi Foreground
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_EXTENDEDKEY | 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)

            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.debug(f"[Zalo Automation] force_focus_window exception: {e}")
            try:
                win32gui.SetForegroundWindow(hwnd)
                return True
            except Exception:
                return False
        finally:
            # BẮT BUỘC DETACH THREAD ĐỂ KHÔNG KHÓA HÀNG ĐỢI MESSAGE GÂY NOT RESPONDING
            if attached_thread and curr_thread:
                try:
                    win32process.AttachThreadInput(curr_thread, attached_thread, False)
                except Exception:
                    pass

    # ============================================================================
    # CHẾ ĐỘ GỬI NGẦM (BACKGROUND MODE) - KHÔNG CHIẾM CHUỘT/BÀN PHÍM
    # Kỹ thuật: Quick Focus → Thao tác → Restore cửa sổ cũ & vị trí chuột (~200ms)
    # ============================================================================

    @staticmethod
    def _save_current_foreground() -> Optional[int]:
        """Lưu lại HWND cửa sổ đang active (foreground) trước khi chuyển sang Zalo."""
        if not HAS_WIN32:
            return None
        try:
            return win32gui.GetForegroundWindow()
        except Exception:
            return None

    @staticmethod
    def _restore_foreground(hwnd: Optional[int]):
        """Khôi phục lại cửa sổ foreground đã lưu trước đó (luôn detach thread an toàn)."""
        if not HAS_WIN32 or not hwnd:
            return
        attached_thread = None
        curr_thread = None
        try:
            if win32gui.IsWindow(hwnd):
                try:
                    user32.SwitchToThisWindow(hwnd, True)
                except Exception:
                    pass
                fore_hwnd = win32gui.GetForegroundWindow()
                if fore_hwnd and fore_hwnd != hwnd:
                    fore_thread = win32process.GetWindowThreadProcessId(fore_hwnd)[0]
                    curr_thread = win32api.GetCurrentThreadId()
                    if fore_thread and curr_thread and fore_thread != curr_thread:
                        try:
                            if win32process.AttachThreadInput(curr_thread, fore_thread, True):
                                attached_thread = fore_thread
                        except Exception:
                            pass
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_EXTENDEDKEY | 0, 0)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
                win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            logger.debug(f"[Background] Không thể restore foreground: {e}")
        finally:
            if attached_thread and curr_thread:
                try:
                    win32process.AttachThreadInput(curr_thread, attached_thread, False)
                except Exception:
                    pass

    @staticmethod
    def quick_focus_and_restore(action_func, restore_delay: float = 0.12):
        """
        Chế độ gửi ngầm: Tạm focus Zalo → thực hiện action → restore cửa sổ cũ.
        Tổng thời gian chiếm foreground: ~150-250ms (HOÀN TOÀN KHÔNG CƯỚP HOẶC GIẬT CHUỘT CỦA NGƯỜI DÙNG).
        """
        if ZaloAutomation.is_abort_requested():
            logger.info("[Background] Thao tác bị hủy khẩn cấp theo lệnh người dùng.")
            return False

        saved_hwnd = ZaloAutomation._save_current_foreground()
        zalo_hwnd = ZaloAutomation.find_zalo_hwnd()

        if not zalo_hwnd:
            logger.warning("[Background] Không tìm thấy cửa sổ Zalo PC.")
            return False

        try:
            # Focus nhanh Zalo
            ZaloAutomation.force_focus_window(zalo_hwnd)
            time.sleep(0.06)

            if ZaloAutomation.is_abort_requested():
                ZaloAutomation._restore_foreground(saved_hwnd)
                return False

            # Thực hiện thao tác
            result = action_func()

            # Chờ nhỏ để đảm bảo thao tác hoàn tất
            time.sleep(restore_delay)

            # Restore cửa sổ cũ
            ZaloAutomation._restore_foreground(saved_hwnd)
            return result
        except Exception as e:
            logger.error(f"[Background] Lỗi trong quick_focus_and_restore: {e}")
            ZaloAutomation._restore_foreground(saved_hwnd)
            return False

    @staticmethod
    def send_message_text_background(message: str, max_attempts: int = MAX_RETRIES) -> bool:
        """
        Gửi tin nhắn text vào Zalo PC hoặc UltraViewer / AnyDesk ở chế độ ngầm (Background Mode).
        Nếu là UltraViewer / AnyDesk: Gửi trực tiếp Ctrl+V + Enter vào vùng soạn thảo đang kích hoạt trên máy điều khiển.
        Nếu là Zalo PC: Quick focus Zalo → focus ô chat → paste tin nhắn → Enter → restore cửa sổ cũ.
        """
        if not message or not message.strip():
            return True

        is_remote = ZaloAutomation.is_remote_desktop_target()
        paste_wait = 0.22 if is_remote else 0.12

        for attempt in range(1, max_attempts + 1):
            if ZaloAutomation.is_abort_requested():
                logger.info("[Background] Gửi text bị hủy theo lệnh người dùng (F9).")
                return False
            try:
                def _action():
                    if ZaloAutomation.is_abort_requested():
                        return False
                    if not is_remote:
                        ZaloAutomation.focus_chat_input()
                        time.sleep(0.08)
                    pyperclip.copy(message)
                    time.sleep(0.06)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(paste_wait)
                    pyautogui.press("enter")
                    time.sleep(0.1)
                    return True

                result = ZaloAutomation.quick_focus_and_restore(_action, restore_delay=0.18 if is_remote else 0.15)
                if result:
                    target_name = "UltraViewer/AnyDesk" if is_remote else "Zalo PC"
                    logger.info(f"[Background] >>> ✅ ĐÃ GỬI NGẦM ({target_name}): \"{message[:40]}...\"")
                    return True
            except Exception as e:
                logger.warning(f"[Background] [Lần thử {attempt}/{max_attempts}] Lỗi gửi ngầm: {e}")
                time.sleep(0.2)

        logger.error(f"[Background] ⚠️ Đã thử {max_attempts} lần gửi ngầm thất bại.")
        return False

    @staticmethod
    def open_chat_background(contact_name: str, max_attempts: int = MAX_RETRIES) -> bool:
        """
        Mở cuộc trò chuyện với contact / nhóm ở chế độ ngầm (Background Mode) qua Ctrl + F.
        Hoạt động hoàn hảo cả trên Zalo PC cục bộ và Zalo trên máy bị điều khiển qua UltraViewer / AnyDesk.
        """
        is_remote = ZaloAutomation.is_remote_desktop_target()
        search_wait = 0.65 if is_remote else 0.45

        for attempt in range(1, max_attempts + 1):
            try:
                def _action():
                    time.sleep(0.15)
                    pyautogui.hotkey("ctrl", "f")
                    time.sleep(0.2)
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.06)
                    pyautogui.press("backspace")
                    time.sleep(0.06)
                    pyperclip.copy(contact_name)
                    time.sleep(0.06)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(search_wait)
                    pyautogui.press("down")
                    time.sleep(0.2 if is_remote else 0.15)
                    pyautogui.press("enter")
                    time.sleep(0.45 if is_remote else 0.35)
                    pyautogui.press("esc")
                    time.sleep(0.15)
                    if not is_remote:
                        ZaloAutomation.focus_chat_input()
                    return True

                result = ZaloAutomation.quick_focus_and_restore(_action, restore_delay=0.22 if is_remote else 0.18)
                if result:
                    logger.info(f"[Background] ✅ Đã mở chat ngầm với: '{contact_name}'")
                    return True
            except Exception as e:
                logger.warning(f"[Background] [Lần thử {attempt}/{max_attempts}] Lỗi mở chat ngầm '{contact_name}': {e}")
                time.sleep(0.3)

        logger.error(f"[Background] ⚠️ Đã thử {max_attempts} lần mở chat ngầm thất bại.")
        return False

    @staticmethod
    def send_files_background(file_paths: List[str], max_attempts: int = MAX_RETRIES) -> bool:
        """
        Gửi file đính kèm vào Zalo ở chế độ ngầm (Background Mode).
        Bắt buộc phải tạm focus Zalo / UltraViewer vì cần Ctrl+V file từ Clipboard.
        """
        if not file_paths:
            return True

        valid_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
        if not valid_paths:
            return False

        if not ZaloAutomation.copy_files_to_clipboard(valid_paths):
            return False

        is_remote = ZaloAutomation.is_remote_desktop_target()

        # Tính thời gian chờ Zalo nạp preview
        total_size_mb = 0.0
        try:
            for p in valid_paths:
                if os.path.isfile(p):
                    total_size_mb += os.path.getsize(p) / (1024 * 1024)
                elif os.path.isdir(p):
                    for root, dirs, files in os.walk(p):
                        for f in files:
                            fp = os.path.join(root, f)
                            total_size_mb += os.path.getsize(fp) / (1024 * 1024)
        except Exception:
            pass

        wait_preview = 2.2
        if total_size_mb >= 100:
            wait_preview = 5.5
        elif total_size_mb >= 30:
            wait_preview = 3.8

        if is_remote:
            wait_preview += 1.0  # Bù độ trễ đồng bộ mạng UltraViewer / AnyDesk

        for attempt in range(1, max_attempts + 1):
            if ZaloAutomation.is_abort_requested():
                logger.info("[Background] Gửi files bị hủy theo lệnh người dùng (F9).")
                return False
            try:
                def _action():
                    if ZaloAutomation.is_abort_requested():
                        return False
                    if not is_remote:
                        ZaloAutomation.focus_chat_input()
                        time.sleep(0.12)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(wait_preview)
                    if ZaloAutomation.is_abort_requested():
                        return False
                    pyautogui.press("enter")
                    time.sleep(0.4)
                    pyautogui.press("enter")
                    time.sleep(0.5)
                    return True

                result = ZaloAutomation.quick_focus_and_restore(_action, restore_delay=0.25 if is_remote else 0.2)
                if result:
                    logger.info(f"[Background] 📤 ĐÃ GỬI FILE NGẦM: {len(valid_paths)} file ({total_size_mb:.1f} MB)")
                    return True
            except Exception as e:
                logger.warning(f"[Background] [Lần thử {attempt}/{max_attempts}] Lỗi gửi file ngầm: {e}")
                time.sleep(0.3)

        return False

    @staticmethod
    def click_conversation_by_index_background(index: int = 0, max_attempts: int = MAX_RETRIES) -> bool:
        """Click chọn hội thoại thứ index ở chế độ ngầm qua WM_MOUSEWHEEL & Silent Click (100% Không giật/cướp chuột)."""
        target_hwnd = ZaloAutomation.find_zalo_hwnd()
        is_remote = ZaloAutomation.is_remote_desktop_target()

        for attempt in range(1, max_attempts + 1):
            try:
                def _action():
                    rect = ZaloAutomation.get_zalo_rect()
                    if not rect:
                        return False
                    left, top, right, bottom = rect
                    conv_x = left + 135

                    if index < 5:
                        target_y = top + 145 + index * 68
                    else:
                        if target_hwnd and HAS_WIN32:
                            lparam = (250 << 16) | 135
                            win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEWHEEL, (-120 << 16), lparam)
                            time.sleep(0.2 if is_remote else 0.15)
                        target_y = top + 145 + 4 * 68

                    # Silent click trực tiếp vào Zalo / UltraViewer bằng PostMessage
                    if target_hwnd:
                        ZaloAutomation.send_deep_background_click(target_hwnd, conv_x, target_y, btn="left")
                    time.sleep(0.5 if is_remote else 0.4)
                    if not is_remote:
                        ZaloAutomation.focus_chat_input()
                    return True

                result = ZaloAutomation.quick_focus_and_restore(_action, restore_delay=0.2 if is_remote else 0.15)
                if result:
                    logger.info(f"[Background] ✅ Đã chọn hội thoại ngầm thứ {index + 1} (Silent Click)")
                    return True
            except Exception as e:
                logger.warning(f"[Background] Lỗi click hội thoại ngầm thứ {index + 1}: {e}")
            time.sleep(0.3)

        return False

    @staticmethod
    def activate_zalo(max_attempts: int = MAX_RETRIES) -> bool:
        """
        Đưa cửa sổ Zalo PC lên phía trước màn hình (Foreground).
        Thử tối đa max_attempts (mặc định 5 lần). Nếu không được thì dừng lại.
        """
        for attempt in range(1, max_attempts + 1):
            logger.info(f"[Zalo Automation] [Lần thử {attempt}/{max_attempts}] Đang tìm & kích hoạt cửa sổ Zalo PC...")
            
            # 1. Thử qua win32gui
            hwnd = ZaloAutomation.find_zalo_hwnd()
            if hwnd and HAS_WIN32:
                if ZaloAutomation.force_focus_window(hwnd):
                    time.sleep(0.4)
                    logger.info(f"[Zalo Automation] ✅ [Thành công ở lần thử {attempt}] Đã kích hoạt cửa sổ Zalo PC.")
                    return True

            # 2. Fallback qua pygetwindow nếu có
            try:
                import pygetwindow as gw
                windows = [w for w in gw.getAllWindows() if ("zalo" in w.title.lower()) and w.width > 350 and w.height > 350]
                if windows:
                    w = windows[0]
                    if w.isMinimized:
                        w.restore()
                    w.activate()
                    time.sleep(0.4)
                    logger.info(f"[Zalo Automation] ✅ [Thành công ở lần thử {attempt}] Đã kích hoạt cửa sổ Zalo PC (pygetwindow).")
                    return True
            except Exception:
                pass

            # Nghỉ ngắn trước khi thử lại
            if attempt < max_attempts:
                time.sleep(0.6)

        logger.warning(
            f"[Zalo Automation] ⚠️ [DỪNG LẠI] Đã thử {max_attempts} lần kích hoạt Zalo PC thất bại. "
            "Hãy đảm bảo ứng dụng Zalo PC đang mở trên máy tính."
        )
        return False

    @staticmethod
    def get_zalo_rect() -> Optional[Tuple[int, int, int, int]]:
        """Lấy tọa độ (left, top, right, bottom) của cửa sổ Zalo."""
        hwnd = ZaloAutomation.find_zalo_hwnd()
        if hwnd and HAS_WIN32:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                if rect[2] > rect[0] and rect[3] > rect[1]:
                    return rect
            except Exception:
                pass
        try:
            import pygetwindow as gw
            windows = [w for w in gw.getAllWindows() if ("zalo" in w.title.lower()) and w.width > 350 and w.height > 350]
            if windows:
                w = windows[0]
                return (w.left, w.top, w.right, w.bottom)
        except Exception:
            pass
        return None

    @staticmethod
    def focus_chat_input(target_hwnd: Optional[int] = None) -> bool:
        """Focus chính xác vào ô soạn thảo tin nhắn của Zalo mà KHÔNG làm di chuyển chuột của người dùng."""
        hwnd = target_hwnd or ZaloAutomation.find_zalo_hwnd()
        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return False
        left, top, right, bottom = rect
        width = right - left
        if width >= 550:
            chat_input_x = left + 320 + int((width - 320) * 0.4)
        else:
            chat_input_x = left + int(width * 0.5)
        chat_input_y = bottom - 45
        try:
            if hwnd and HAS_WIN32:
                # Gửi click ngầm không giật chuột
                ok = ZaloAutomation.send_deep_background_click(hwnd, chat_input_x, chat_input_y, btn="left")
                time.sleep(0.06)
                return ok
            else:
                pyautogui.click(chat_input_x, chat_input_y)
                time.sleep(0.06)
                return True
        except Exception as e:
            logger.debug(f"[Zalo Automation] Lỗi click focus ô chat: {e}")
            return False

    @staticmethod
    def open_chat_with_contact(contact_name: str, max_attempts: int = MAX_RETRIES) -> bool:
        """
        Tìm kiếm và mở cuộc trò chuyện với 1 người trong Zalo PC bằng phím tắt Ctrl+F.
        Thử tối đa max_attempts (mặc định 5 lần). Nếu không được thì dừng lại.
        """
        for attempt in range(1, max_attempts + 1):
            logger.info(f"[Zalo Automation] [Lần thử {attempt}/{max_attempts}] Đang tìm liên hệ: '{contact_name}'...")
            
            # Kích hoạt Zalo
            if not ZaloAutomation.activate_zalo(max_attempts=2):
                if attempt == max_attempts:
                    break
                time.sleep(0.5)
                continue

            try:
                time.sleep(0.3)
                # 1. Bấm Ctrl + F để kích hoạt ô tìm kiếm của Zalo
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.3)

                # 2. Xóa nội dung tìm kiếm cũ nếu có
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                pyautogui.press("backspace")
                time.sleep(0.1)

                # 3. Copy tên người cần tìm vào Clipboard và Paste vào ô tìm kiếm
                pyperclip.copy(contact_name)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.6)  # Đợi Zalo hiển thị danh sách kết quả tìm kiếm

                # 4. Nhấn phím Enter (hoặc Down rồi Enter) để mở đoạn chat
                pyautogui.press("down")
                time.sleep(0.15)
                pyautogui.press("enter")
                time.sleep(0.5)
                pyautogui.press("esc")
                time.sleep(0.1)

                # 5. Focus vào ô chat
                ZaloAutomation.focus_chat_input()

                logger.info(f"[Zalo Automation] ✅ [Thành công ở lần thử {attempt}] Đã mở đoạn chat với '{contact_name}'.")
                return True
            except Exception as e:
                logger.warning(f"[Zalo Automation] [Lần thử {attempt}/{max_attempts}] Lỗi khi mở chat '{contact_name}': {e}")
                time.sleep(0.5)

        logger.error(
            f"[Zalo Automation] ⚠️ [DỪNG LẠI] Đã thử {max_attempts} lần mở chat với '{contact_name}' thất bại."
        )
        return False

    @staticmethod
    def click_conversation_by_index(index: int = 0, max_attempts: int = MAX_RETRIES) -> bool:
        """
        Click chọn cuộc trò chuyện thứ `index` (0-indexed) trong danh sách bên trái của Zalo.
        Sử dụng Silent Click để không chiếm chuột thật của người dùng.
        """
        target_hwnd = ZaloAutomation.find_zalo_hwnd()
        for attempt in range(1, max_attempts + 1):
            if not ZaloAutomation.activate_zalo(max_attempts=2):
                if attempt == max_attempts:
                    break
                time.sleep(0.4)
                continue

            rect = ZaloAutomation.get_zalo_rect()
            if not rect:
                time.sleep(0.4)
                continue

            left, top, right, bottom = rect
            conv_x = left + 135

            if index < 5:
                target_y = top + 145 + index * 68
                try:
                    if target_hwnd:
                        ZaloAutomation.send_deep_background_click(target_hwnd, conv_x, target_y, btn="left")
                    else:
                        pyautogui.click(conv_x, target_y)
                    time.sleep(0.5)
                    ZaloAutomation.focus_chat_input()
                    logger.info(f"[Zalo Automation] ✅ Đã chọn hội thoại thứ {index + 1} tại ({conv_x}, {target_y}).")
                    return True
                except Exception as e:
                    logger.warning(f"[Zalo Automation] Lỗi click hội thoại thứ {index + 1}: {e}")
            else:
                try:
                    if target_hwnd and HAS_WIN32:
                        lparam = (250 << 16) | 135
                        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEWHEEL, (-120 << 16), lparam)
                        time.sleep(0.2)
                    target_y = top + 145 + 4 * 68
                    if target_hwnd:
                        ZaloAutomation.send_deep_background_click(target_hwnd, conv_x, target_y, btn="left")
                    else:
                        pyautogui.click(conv_x, target_y)
                    time.sleep(0.5)
                    ZaloAutomation.focus_chat_input()
                    logger.info(f"[Zalo Automation] ✅ Đã chọn hội thoại thứ {index + 1} tại ({conv_x}, {target_y}).")
                    return True
                except Exception as e:
                    logger.warning(f"[Zalo Automation] Lỗi click hội thoại thứ {index + 1}: {e}")
            time.sleep(0.5)

        logger.error(f"[Zalo Automation] ⚠️ Không thể click hội thoại thứ {index + 1} sau {max_attempts} lần thử.")
        return False

    @staticmethod
    def filter_by_tag_name(tag_name: str = "Gửi mẫu quảng cáo", max_attempts: int = MAX_RETRIES) -> bool:
        """
        Kích hoạt bộ lọc theo Thẻ phân loại trên Zalo PC (ví dụ: 'Gửi mẫu quảng cáo', 'MUA NHÓM THCS',...).
        """
        logger.info(f"[Zalo Automation] 🏷️ Đang kích hoạt lọc theo Thẻ: '{tag_name}' trên Zalo PC...")
        if not ZaloAutomation.activate_zalo(max_attempts=max_attempts):
            return False

        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return False

        left, top, right, bottom = rect

        # 1. Thử click trực tiếp vào tab thẻ pill bên cạnh tab 'Khác' (khoảng left + 175, top + 95)
        try:
            pyautogui.click(left + 175, top + 95)
            time.sleep(0.4)
            logger.info(f"[Zalo Automation] ✅ Đã click Tab Thẻ '{tag_name}'.")
            return True
        except Exception as e:
            logger.debug(f"[Zalo Automation] Tab click error: {e}")

        # 2. Nếu cần mở menu phân loại qua nút '...' (vị trí left + 230, top + 95)
        try:
            pyautogui.click(left + 230, top + 95)
            time.sleep(0.4)
            
            tag_menu_offsets = {
                "tất cả": 30,
                "chưa đọc": 65,
                "gửi mẫu quảng cáo": 100,
                "mua nhóm thcs": 135,
                "mua nhóm thpt": 170,
                "mua giáo án ai mới": 205,
                "cần ghép thpt": 240,
                "nguyễn hữu cảnh": 275,
                "chưa gửi bài": 310,
                "cần giải quyết": 345
            }
            y_off = tag_menu_offsets.get(tag_name.lower().strip(), 100)
            pyautogui.click(left + 180, top + 130 + y_off)
            time.sleep(0.6)
            logger.info(f"[Zalo Automation] ✅ Đã chọn Thẻ '{tag_name}' từ menu phân loại.")
            return True
        except Exception as e:
            logger.warning(f"[Zalo Automation] Lỗi chọn menu Thẻ: {e}")

        return False

    @staticmethod
    def assign_tag_to_current_chat(tag_name: str = "cần giải quyết", max_attempts: int = MAX_RETRIES) -> bool:
        """
        Gắn Thẻ phân loại (ví dụ: 'cần giải quyết') cho cuộc hội thoại đang chọn.
        Thao tác: Click phải vào cuộc hội thoại -> Chọn 'Phân loại' -> Chọn thẻ.
        """
        logger.info(f"[Zalo Automation] 🏷️ Đang gắn Thẻ '{tag_name}' cho cuộc hội thoại hiện tại...")
        if not ZaloAutomation.activate_zalo(max_attempts=max_attempts):
            return False

        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return False

        left, top, right, bottom = rect
        # Click chuột phải vào nick đầu tiên bên trái
        conv_x = left + 140
        conv_y = top + 160

        try:
            pyautogui.rightClick(conv_x, conv_y)
            time.sleep(0.4)
            
            # Di chuyển vào menu chuột phải -> mục 'Phân loại' (thường là mục thứ 4)
            menu_x = conv_x + 80
            menu_y = conv_y + 110
            pyautogui.moveTo(menu_x, menu_y)
            time.sleep(0.3)
            
            # Click vào thẻ 'cần giải quyết' ở menu con bên cạnh
            sub_x = menu_x + 160
            sub_y = menu_y + 60
            pyautogui.click(sub_x, sub_y)
            time.sleep(0.3)

            logger.info(f"[Zalo Automation] ✅ Đã gắn Thẻ '{tag_name}' cho hội thoại thành công.")
            return True
        except Exception as e:
            logger.warning(f"[Zalo Automation] Lỗi khi gắn thẻ '{tag_name}': {e}")
            return False

    @staticmethod
    def detect_red_badge_count() -> int:
        """
        Quét nhanh vùng danh sách bên trái Zalo PC để phát hiện các chấm đỏ / bong bóng số tin nhắn chưa đọc.
        """
        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return 0
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        # Vùng chứa huy hiệu đỏ: góc bên phải của cột danh sách hội thoại
        badge_x = left + int(width * 0.23)
        badge_y = top + 130
        badge_w = 70
        badge_h = max(200, height - 180)

        try:
            from PIL import Image
            screenshot = pyautogui.screenshot(region=(badge_x, badge_y, badge_w, badge_h))
            # Quét các điểm ảnh màu đỏ đặc trưng của Zalo badge: R > 200, G < 80, B < 80
            red_y_coords = []
            for y in range(0, screenshot.height, 4):
                has_red = False
                for x in range(0, screenshot.width, 2):
                    r, g, b = screenshot.getpixel((x, y))[:3]
                    if r > 195 and g < 75 and b < 75:
                        has_red = True
                        break
                if has_red:
                    red_y_coords.append(y)

            # Gom nhóm các dòng màu đỏ liên tiếp thành các huy hiệu riêng biệt (cách nhau ít nhất 30px)
            badges = []
            for py in red_y_coords:
                if not badges or (py - badges[-1] > 30):
                    badges.append(py)
            logger.info(f"[Zalo Automation] 🔴 Phát hiện {len(badges)} cuộc hội thoại có chấm đỏ / số tin mới.")
            return len(badges)
        except Exception as e:
            logger.debug(f"[Zalo Automation] Lỗi phát hiện chấm đỏ: {e}")
            return 0

    @staticmethod
    def auto_scan_and_reply_unread(
        gemini_engine,
        max_chats: int = 5,
        delay_between: float = 1.5,
        max_attempts: int = MAX_RETRIES
    ) -> List[Dict[str, Any]]:
        """
        QUY TRÌNH TỰ ĐỘNG LỌC CHƯA ĐỌC & TRẢ LỜI HÀNG LOẠT:
        1. Bấm Phân loại -> Chọn 'Chưa đọc' để chỉ hiện các tin mới (có chấm đỏ / số đếm).
        2. Duyệt qua từng cuộc trò chuyện chưa đọc (tối đa max_chats khách).
        3. Chụp màn hình -> Gemini Vision đọc tin nhắn và sinh câu trả lời.
        4. Tự động gõ & gửi phản hồi vào Zalo.
        5. Nếu gặp ca khó/khiếu nại -> Tự động gắn thẻ 'cần giải quyết'!
        """
        logger.info(f"[Zalo Batch-Auto] 🚀 Bắt đầu quét và trả lời các tin nhắn CHƯA ĐỌC (Tối đa {max_chats} khách)...")
        results = []

        # Bước 1: Bật lọc Chưa đọc
        ok_filter = ZaloAutomation.filter_by_status("unread", max_attempts=max_attempts)
        if not ok_filter:
            logger.warning("[Zalo Batch-Auto] Không thể bật bộ lọc 'Chưa đọc'. Tiếp tục trên danh sách hiện tại.")

        time.sleep(0.5)

        # Đếm số lượng chấm đỏ đang hiển thị
        badge_count = ZaloAutomation.detect_red_badge_count()
        total_to_process = min(max_chats, max(1, badge_count))
        logger.info(f"[Zalo Batch-Auto] 🎯 Sẽ tiến hành xử lý tự động {total_to_process} cuộc hội thoại có tin mới.")

        # Bước 2: Duyệt từng cuộc trò chuyện
        for idx in range(total_to_process):
            logger.info(f"[Zalo Batch-Auto] 👉 Đang xử lý tin nhắn chưa đọc thứ {idx + 1}/{total_to_process}...")
            clicked = ZaloAutomation.click_conversation_by_index(index=0, max_attempts=max_attempts)
            if not clicked:
                logger.info(f"[Zalo Batch-Auto] Đã xử lý hết tất cả các tin nhắn chưa đọc.")
                break

            time.sleep(0.5)
            # Tự động đọc và trả lời cho hội thoại này
            ok, msg, replies = ZaloAutomation.auto_read_and_reply_current_chat(
                gemini_engine=gemini_engine,
                delay_between=delay_between,
                max_attempts=max_attempts
            )

            results.append({
                "chat_index": idx + 1,
                "success": ok,
                "status_msg": msg,
                "replies": replies
            })

            time.sleep(1.0)

        logger.info(f"[Zalo Batch-Auto] 🎉 Hoàn tất quét và trả lời {len(results)} khách hàng!")
        return results

    @staticmethod
    def send_message_text(message: str, max_attempts: int = MAX_RETRIES) -> bool:
        """
        Gõ tin nhắn tiếng Việt vào ô chat Zalo và bấm Enter để gửi.
        Thử tối đa max_attempts (mặc định 5 lần). Nếu không được thì dừng lại.
        """
        if not message or not message.strip():
            return True

        for attempt in range(1, max_attempts + 1):
            try:
                # Đảm bảo con trỏ đang ở trong ô chat
                ZaloAutomation.focus_chat_input()
                time.sleep(0.15)

                # Copy nội dung tiếng Việt chuẩn Unicode vào Clipboard
                pyperclip.copy(message)
                time.sleep(0.1)

                # Dán vào ô chat
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.25)

                # Nhấn Enter để gửi
                pyautogui.press("enter")
                logger.info(f"[Zalo Automation] >>> ✅ ĐÃ GỬI TIN: \"{message[:40]}...\"")
                return True
            except Exception as e:
                logger.warning(f"[Zalo Automation] [Lần thử {attempt}/{max_attempts}] Lỗi khi gửi tin: {e}")
                time.sleep(0.4)

        logger.error(
            f"[Zalo Automation] ⚠️ [DỪNG LẠI] Đã thử {max_attempts} lần gửi tin nhắn thất bại. Dừng quy trình."
        )
        return False

    @staticmethod
    def send_messages_to_contact(
        contact_name: str,
        messages: List[str],
        delay_between: float = 1.5,
        max_attempts: int = MAX_RETRIES
    ) -> bool:
        """
        Tự động mở chat với 1 người và gửi danh sách các tin nhắn.
        Áp dụng giới hạn tối đa 5 lần thử (MAX_RETRIES = 5). Nếu thất bại, dừng ngay lập tức.
        """
        logger.info(f"[Zalo Automation] Bắt đầu quy trình gửi {len(messages)} tin nhắn cho '{contact_name}' (Tối đa {max_attempts} lần thử)...")
        
        # Mở đoạn chat
        opened = ZaloAutomation.open_chat_with_contact(contact_name, max_attempts=max_attempts)
        if not opened:
            logger.error(
                f"[Zalo Automation] 🛑 Không thể mở chat với '{contact_name}' sau {max_attempts} lần thử. "
                "Hủy bỏ toàn bộ quá trình gửi."
            )
            return False

        time.sleep(0.3)
        for idx, msg in enumerate(messages, 1):
            sent = ZaloAutomation.send_message_text(msg, max_attempts=max_attempts)
            if not sent:
                logger.error(
                    f"[Zalo Automation] 🛑 Gửi tin thứ {idx}/{len(messages)} thất bại sau {max_attempts} lần thử. "
                    "Hủy gửi các tin còn lại để bảo toàn dữ liệu."
                )
                return False
            if idx < len(messages):
                time.sleep(delay_between)

        logger.info(f"[Zalo Automation] 🎉 Hoàn tất gửi thành công {len(messages)} tin nhắn cho '{contact_name}'.")
        return True

    @staticmethod
    def send_messages_to_two_contacts(
        nick1: str,
        msg1: str,
        nick2: str,
        msg2: str,
        delay_between_contacts: float = 2.0,
        max_attempts: int = MAX_RETRIES
    ) -> Tuple[bool, bool]:
        """
        Gửi test cho 2 người đầu tiên (TEST 2).
        Trả về: (kết quả người 1, kết quả người 2).
        """
        logger.info(f"[Zalo Test 2] Bắt đầu gửi cho 2 người: '{nick1}' và '{nick2}'...")
        
        # 1. Gửi cho người thứ 1
        res1 = ZaloAutomation.send_messages_to_contact(nick1, [msg1], max_attempts=max_attempts)
        time.sleep(delay_between_contacts)

        # 2. Gửi cho người thứ 2
        res2 = ZaloAutomation.send_messages_to_contact(nick2, [msg2], max_attempts=max_attempts)
        
        return res1, res2

    @staticmethod
    def capture_chat_area(save_path: str = "temp_zalo_chat.png") -> Optional[str]:
        """
        Chụp ảnh vùng màn hình hiển thị cuộc hội thoại Zalo PC.
        Cắt riêng khu vực tin nhắn để Gemini Vision đọc chuẩn xác nhất.
        """
        if not ZaloAutomation.activate_zalo(max_attempts=2):
            return None

        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return None

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        # Vùng chat bên phải: từ 32% bề ngang đến hết, từ thanh tiêu đề đến sát ô gõ chữ
        chat_x = left + int(width * 0.32)
        chat_y = top + 80
        chat_w = int(width * 0.68)
        chat_h = max(200, height - 160)

        try:
            screenshot = pyautogui.screenshot(region=(chat_x, chat_y, chat_w, chat_h))
            screenshot.save(save_path)
            logger.info(f"[Zalo Automation] 📸 Đã chụp ảnh vùng tin nhắn Zalo: {save_path} ({chat_w}x{chat_h}px)")
            return save_path
        except Exception as e:
            logger.error(f"[Zalo Automation] Lỗi khi chụp ảnh màn hình Zalo: {e}")
            return None

    @staticmethod
    def auto_read_and_reply_current_chat(
        gemini_engine,
        delay_between: float = 1.5,
        max_attempts: int = MAX_RETRIES
    ) -> Tuple[bool, str, List[str]]:
        """
        QUY TRÌNH TỰ ĐỘNG HOÀN TOÀN:
        1. Kích hoạt cửa sổ Zalo PC đang mở.
        2. Chụp ảnh vùng tin nhắn gần nhất của khách hàng.
        3. Dùng Gemini Multimodal (Vision) đọc chữ trong tin nhắn & ảnh lỗi.
        4. Gemini sinh câu trả lời chuẩn mực (Dạng chat tự nhiên, không bảng markdown).
        5. Tự động Paste và bấm Enter gửi câu trả lời vào Zalo PC.
        """
        logger.info("[Zalo Auto-Pilot] 🚀 Bắt đầu quy trình Đọc tin nhắn màn hình & Tự động phản hồi...")
        
        # Bước 1: Kích hoạt Zalo
        if not ZaloAutomation.activate_zalo(max_attempts=max_attempts):
            return False, "Không thể kích hoạt cửa sổ Zalo PC.", []

        # Bước 2: Chụp ảnh vùng chat
        time.sleep(0.3)
        img_path = ZaloAutomation.capture_chat_area()
        if not img_path or not os.path.exists(img_path):
            return False, "Không chụp được ảnh vùng chat Zalo.", []

        # Bước 3: Đưa ảnh vào Gemini Vision để đọc tin nhắn và suy luận
        logger.info("[Zalo Auto-Pilot] 🧠 Đang chuyển ảnh vùng chat sang Gemini Vision...")
        prompt_read = (
            "Hãy quan sát ảnh chụp màn hình Zalo này. Đọc tin nhắn hoặc ảnh lỗi gần nhất mà khách hàng gửi đến, "
            "sau đó hãy đóng vai Trợ lý CSKH Giáo án Lịch sử Kết Nối Tri Thức (hoặc Trợ lý đa năng) "
            "soạn câu trả lời trực diện, đầy đủ và thân thiện nhất cho khách theo dạng tin nhắn chat Zalo tự nhiên (không dùng bảng markdown thô)."
        )
        replies, analysis = gemini_engine.generate_response(prompt_read, image_path=img_path)

        if not replies:
            return False, "Gemini không sinh được câu trả lời.", []

        logger.info(f"[Zalo Auto-Pilot] ✍️ AI đã soạn xong {len(replies)} tin nhắn phản hồi.")

        # Bước 4: Focus ô chat và gửi từng tin nhắn
        ZaloAutomation.focus_chat_input()
        time.sleep(0.2)

        for idx, r in enumerate(replies, 1):
            ok = ZaloAutomation.send_message_text(r, max_attempts=max_attempts)
            if not ok:
                return False, f"Lỗi khi gửi tin thứ {idx}", replies
            if idx < len(replies):
                time.sleep(delay_between)

        logger.info("[Zalo Auto-Pilot] 🎉 Đã đọc tin nhắn và gửi phản hồi thành công vào Zalo PC!")
        return True, "Thành công", replies

    @staticmethod
    def scroll_chat_history(scroll_amount: int = 5) -> bool:
        """
        Di chuyển chuột vào giữa khung chat và cuộn lên để xem thêm 10-20 tin nhắn cũ trước đó.
        """
        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            return False
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        # Tọa độ giữa khung chat
        chat_mid_x = left + int(width * 0.65)
        chat_mid_y = top + int(height * 0.50)
        
        try:
            pyautogui.moveTo(chat_mid_x, chat_mid_y)
            time.sleep(0.2)
            # Cuộn lên (số dương là cuộn lên)
            pyautogui.scroll(scroll_amount * 120)
            time.sleep(0.4)
            logger.info(f"[Zalo Automation] 📜 Đã cuộn chuột lên {scroll_amount} nấc để lộ 20 tin nhắn cũ.")
            return True
        except Exception as e:
            logger.warning(f"[Zalo Automation] Lỗi khi cuộn chuột: {e}")
            return False

    @staticmethod
    def read_deep_context_and_reply(
        gemini_engine,
        scroll_up: bool = True,
        delay_between: float = 1.5,
        max_attempts: int = MAX_RETRIES
    ) -> Tuple[bool, str, List[str]]:
        """
        TỰ ĐỘNG ĐỌC NGỮ CẢNH SÂU 10-20 TIN NHẮN TRONG MÀN HÌNH CHAT:
        1. Kích hoạt Zalo PC.
        2. Nếu scroll_up=True: Cuộn nhẹ lên để lộ 10-20 tin nhắn trao đổi gần nhất.
        3. Chụp ảnh màn hình toàn bộ khung hội thoại (Full Chat Stream).
        4. Gemini Vision phân tích toàn bộ mạch đối thoại: hiểu khách đang cần gì, vướng mắc gì từ các câu trước.
        5. Soạn câu trả lời giải quyết trọn vẹn và liền mạch với câu chuyện.
        6. Tự động gửi phản hồi vào Zalo PC.
        """
        logger.info("[Zalo Deep-Context] 📜 Bắt đầu quy trình Phân tích ngữ cảnh sâu 20 tin nhắn...")
        if not ZaloAutomation.activate_zalo(max_attempts=max_attempts):
            return False, "Không thể kích hoạt cửa sổ Zalo PC.", []

        time.sleep(0.3)
        if scroll_up:
            ZaloAutomation.scroll_chat_history(scroll_amount=4)

        img_path = ZaloAutomation.capture_chat_area(save_path="deep_context_zalo.png")
        if not img_path or not os.path.exists(img_path):
            return False, "Không chụp được ảnh khung hội thoại Zalo.", []

        prompt_deep = (
            "Đây là ảnh chụp toàn bộ đoạn hội thoại gần nhất (khoảng 10-20 tin nhắn) trên Zalo giữa khách hàng và người bán.\n"
            "Hãy đọc kỹ toàn bộ dòng tin nhắn từ trên xuống dưới:\n"
            "1. PHÂN TÍCH NGỮ CẢNH: Khách hàng đang hỏi về chủ đề gì, trước đó đã trao đổi những gì, và câu hỏi/vướng mắc mới nhất của khách là gì.\n"
            "2. ĐÓNG VAI TRỢ LÝ CSKH: Hãy soạn câu trả lời trực diện, đầy đủ, chuẩn xác và LIỀN MẠCH với toàn bộ câu chuyện trước đó.\n"
            "3. ĐỊNH DẠNG: Trả lời dạng tin nhắn chat Zalo tự nhiên, ngắn gọn, dùng các biểu tượng (👉, •, 📌, ✨) thay vì bảng Markdown thô."
        )

        logger.info("[Zalo Deep-Context] 🧠 Gemini Multimodal đang phân tích sâu toàn bộ 20 tin nhắn...")
        replies, analysis = gemini_engine.generate_response(prompt_deep, image_path=img_path)

        if not replies:
            return False, "Gemini không sinh được phản hồi từ ảnh ngữ cảnh.", []

        # Focus lại ô chat cuối cùng
        ZaloAutomation.focus_chat_input()
        time.sleep(0.2)

        for idx, r in enumerate(replies, 1):
            ok = ZaloAutomation.send_message_text(r, max_attempts=max_attempts)
            if not ok:
                return False, f"Lỗi gửi tin thứ {idx}", replies
            if idx < len(replies):
                time.sleep(delay_between)

        logger.info("[Zalo Deep-Context] 🎉 Đã phân tích ngữ cảnh sâu và gửi phản hồi thành công vào Zalo PC!")
        return True, "Thành công", replies

    @staticmethod
    def copy_files_to_clipboard(file_paths: List[str]) -> bool:
        """
        Copy danh sách file hoặc thư mục vào Windows Clipboard dưới dạng CF_HDROP (Drop Files).
        Giúp Zalo PC nhận diện file đính kèm chuẩn xác khi nhấn Ctrl+V.
        Hỗ trợ tìm kiếm đường dẫn tương đối khi chuyển sang máy tính khác và thử lại khi Clipboard bị khóa.
        """
        if not file_paths:
            logger.warning("[Zalo Automation] Danh sách file rỗng, không thể copy vào Clipboard.")
            return False

        valid_paths = []
        missing_paths = []

        for p in file_paths:
            if not p:
                continue
            norm_p = os.path.normpath(p.strip())
            if os.path.exists(norm_p):
                valid_paths.append(os.path.abspath(norm_p))
            else:
                # Tìm kiếm tương đối từ thư mục hiện tại hoặc knowledge_base
                base_n = os.path.basename(norm_p)
                candidates = [
                    os.path.join(os.getcwd(), "knowledge_base", base_n),
                    os.path.join(os.getcwd(), "assets", base_n),
                    os.path.join(os.getcwd(), "storage", base_n),
                    os.path.join(os.getcwd(), base_n)
                ]
                found = False
                for c in candidates:
                    if os.path.exists(c):
                        valid_paths.append(os.path.abspath(c))
                        found = True
                        break
                if not found:
                    missing_paths.append(norm_p)

        if missing_paths:
            logger.warning(
                f"[Zalo Automation] ⚠️ Có {len(missing_paths)} file không tìm thấy trên máy tính này:\n" +
                "\n".join([f"  - {mp}" for mp in missing_paths]) +
                "\n💡 Gợi ý: Nếu bạn vừa chuyển phần mềm sang máy tính mới, hãy vào Tab 'Mẫu Tin Nhắn' để chọn lại file từ ổ đĩa của máy này!"
            )

        if not valid_paths:
            logger.error(
                f"[Zalo Automation] ❌ Toàn bộ file đính kèm không tồn tại trên ổ đĩa máy này: {file_paths}"
            )
            return False

        try:
            import struct
            import win32clipboard
            import win32con

            offset = 20
            files_str = '\0'.join(valid_paths) + '\0\0'
            encoded = files_str.encode('utf-16le')
            header = struct.pack('IIIII', offset, 0, 0, 0, 1)  # fWide = 1 (Unicode)
            data = header + encoded

            # Thử mở Clipboard tối đa 5 lần (chống trường hợp Clipboard bị phần mềm khác khóa)
            opened = False
            for try_idx in range(5):
                try:
                    win32clipboard.OpenClipboard(0)
                    opened = True
                    break
                except Exception:
                    time.sleep(0.08)

            if not opened:
                logger.error("[Zalo Automation] ❌ Không thể OpenClipboard (Bị ứng dụng khác khóa).")
                return False

            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
                logger.info(f"[Zalo Automation] 📁 Đã nạp thành công {len(valid_paths)} files vào Clipboard để gửi Zalo.")
                return True
            finally:
                win32clipboard.CloseClipboard()
        except ImportError as ie:
            logger.error(f"[Zalo Automation] ❌ Lỗi thiếu module win32clipboard: {ie}. Cần kiểm tra PyInstaller hidden imports!")
            return False
        except Exception as e:
            logger.error(f"[Zalo Automation] ❌ Lỗi khi copy file vào Clipboard: {e}", exc_info=True)
            return False

    @staticmethod
    def send_files_to_current_chat(file_paths: List[str], max_attempts: int = MAX_RETRIES) -> bool:
        """
        Dán và gửi các files/folders đã chọn vào cuộc hội thoại Zalo PC đang mở.
        - Copy files vào Clipboard dưới dạng CF_HDROP chuẩn Unicode.
        - Click focus vào ô chat Zalo.
        - Dán file bằng phím tắt Ctrl+V.
        - Chờ Zalo đọc file và tạo thẻ đính kèm preview (Tự điều chỉnh theo dung lượng: file nặng 200MB chờ lâu hơn).
        - Gửi Enter 2 lần cách nhau 0.6s để kích hoạt lệnh gửi chắc chắn 100%.
        """
        if not file_paths:
            return True

        valid_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
        if not valid_paths:
            logger.warning(f"[Zalo Automation] ⚠️ Không tìm thấy file hợp lệ nào tồn tại trong máy: {file_paths}")
            return False

        if not ZaloAutomation.copy_files_to_clipboard(valid_paths):
            logger.error("[Zalo Automation] ❌ Lỗi khi nạp danh sách file vào Clipboard.")
            return False

        # Tính toán dung lượng tổng để điều chỉnh thời gian chờ Zalo nạp preview
        total_size_mb = 0.0
        try:
            for p in valid_paths:
                if os.path.isfile(p):
                    total_size_mb += os.path.getsize(p) / (1024 * 1024)
                elif os.path.isdir(p):
                    for root, dirs, files in os.walk(p):
                        for f in files:
                            fp = os.path.join(root, f)
                            total_size_mb += os.path.getsize(fp) / (1024 * 1024)
        except Exception:
            pass

        wait_preview = 2.0
        if total_size_mb >= 100:
            wait_preview = 5.0
            logger.info(f"[Zalo Automation] 📦 Phát hiện file/folder dung lượng lớn ({total_size_mb:.1f} MB), chờ {wait_preview}s để Zalo nạp preview...")
        elif total_size_mb >= 30:
            wait_preview = 3.5
            logger.info(f"[Zalo Automation] 📦 Phát hiện file/folder ({total_size_mb:.1f} MB), chờ {wait_preview}s...")

        for attempt in range(1, max_attempts + 1):
            try:
                # Focus vào ô nhập liệu chat
                ZaloAutomation.focus_chat_input()
                time.sleep(0.3)

                # Dán file vào Zalo
                pyautogui.hotkey("ctrl", "v")
                logger.info(f"[Zalo Automation] 📋 Đã dán {len(valid_paths)} file vào ô chat. Đang chờ Zalo nạp file ({wait_preview}s)...")
                time.sleep(wait_preview)

                # Nhấn phím Enter để gửi file
                pyautogui.press("enter")
                time.sleep(0.8)

                # Nhấn thêm 1 lần Enter phụ trợ để đảm bảo kích hoạt gửi
                pyautogui.press("enter")
                time.sleep(1.0)

                logger.info(f"[Zalo Automation] 📤 ĐÃ GỬI FILE THÀNH CÔNG: {len(valid_paths)} file/thư mục ({total_size_mb:.1f} MB).")
                return True
            except Exception as e:
                logger.warning(f"[Zalo Automation] [Lần thử {attempt}/{max_attempts}] Lỗi gửi file: {e}")
                time.sleep(0.5)

        return False

    @staticmethod
    def send_script_template_to_current_chat(
        content: str,
        file_paths: Optional[List[str]] = None,
        background_mode: bool = False,
        auto_press_enter: bool = True,
        max_attempts: Optional[int] = None
    ) -> bool:
        """
        Gửi nhanh nội dung mẫu kịch bản và danh sách file đính kèm vào cuộc trò chuyện Zalo PC đang mở hiện tại (hoặc cửa sổ đang Active như UltraViewer/AnyDesk).
        - background_mode = True: Chế độ Khóa Nền Zalo (hoặc cửa sổ đã khóa đích như UltraViewer/AnyDesk).
        - background_mode = False: Chế độ Active Window (gửi vào cửa sổ đang làm việc gần nhất).
        - Có cơ chế giới hạn số lần thử lại tối đa (mặc định 5 lần từ cài đặt), nếu thất bại 5 lần sẽ DỪNG LẠI BẮT BUỘC.
        """
        if max_attempts is None:
            max_attempts = ZaloAutomation.get_max_retries()

        if ZaloAutomation.is_abort_requested():
            logger.info("[Script Send] Bị hủy theo lệnh người dùng (F9).")
            return False

        success = False

        for attempt in range(1, max_attempts + 1):
            if ZaloAutomation.is_abort_requested():
                logger.info("[Script Send] Bị hủy theo lệnh người dùng (F9).")
                return False

            try:
                if background_mode:
                    # ================= CHẾ ĐỘ KHÓA NỀN GỬI NGẦM (ZALO PC / ULTRAVIEWER KHÓA ĐÍCH) =================
                    target_hwnd = ZaloAutomation.find_zalo_hwnd()
                    if not target_hwnd:
                        logger.warning(f"[Script Send] [Lần thử {attempt}/{max_attempts}] Không tìm thấy cửa sổ Zalo / UltraViewer đích.")
                        time.sleep(0.3)
                        continue

                    # Kiểm tra xem cửa sổ đích là Zalo native hay UltraViewer/AnyDesk
                    is_remote_app = False
                    if HAS_WIN32:
                        w_title = win32gui.GetWindowText(target_hwnd).lower()
                        if any(k in w_title for k in ["ultraviewer", "anydesk", "teamviewer", "remote desktop"]):
                            is_remote_app = True

                    def _do_background_send():
                        if not is_remote_app:
                            # Với Zalo PC native: Focus chính xác vào ô soạn thảo
                            ZaloAutomation.focus_chat_input()
                            time.sleep(0.08)

                        # 1. Gửi văn bản
                        if content and content.strip():
                            pyperclip.copy(content.strip())
                            time.sleep(0.06)
                            pyautogui.hotkey("ctrl", "v")
                            time.sleep(0.12)
                            if auto_press_enter:
                                pyautogui.press("enter")
                                time.sleep(0.1)

                        # 2. Gửi files đính kèm
                        if file_paths and len(file_paths) > 0:
                            valid_paths = [p for p in file_paths if os.path.exists(p)]
                            if valid_paths:
                                time.sleep(0.15)
                                ZaloAutomation.copy_files_to_clipboard(valid_paths)
                                time.sleep(0.1)
                                pyautogui.hotkey("ctrl", "v")
                                time.sleep(0.8)
                                pyautogui.press("enter")
                                time.sleep(0.2)
                        return True

                    res = ZaloAutomation.quick_focus_and_restore(_do_background_send, restore_delay=0.15)
                    if res:
                        success = True
                        break
                    else:
                        logger.warning(f"[Script Send] [Lần thử {attempt}/{max_attempts}] Gửi ngầm chưa thành công, đang thử lại...")
                        time.sleep(0.3)
                else:
                    # ================= CHẾ ĐỘ CỬA SỔ ACTIVE (ULTRAVIEWER / ANYDESK / KHÁC) =================
                    # Nếu Dashboard đang chiếm Foreground, kích hoạt lại cửa sổ làm việc gần nhất của người dùng
                    if ZaloAutomation._last_external_hwnd and HAS_WIN32 and win32gui.IsWindow(ZaloAutomation._last_external_hwnd):
                        try:
                            win32gui.SetForegroundWindow(ZaloAutomation._last_external_hwnd)
                            time.sleep(0.12)
                        except Exception:
                            pass

                    # 1. Gửi text
                    if content and content.strip():
                        pyperclip.copy(content.strip())
                        time.sleep(0.06)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.12)
                        if auto_press_enter:
                            pyautogui.press("enter")
                            time.sleep(0.1)

                    # 2. Gửi files
                    if file_paths and len(file_paths) > 0:
                        valid_paths = [p for p in file_paths if os.path.exists(p)]
                        if valid_paths:
                            time.sleep(0.2)
                            ZaloAutomation.copy_files_to_clipboard(valid_paths)
                            time.sleep(0.1)
                            pyautogui.hotkey("ctrl", "v")
                            time.sleep(0.8)
                            pyautogui.press("enter")
                            time.sleep(0.2)
                    success = True
                    break
            except Exception as e:
                logger.warning(f"[Script Send] [Lần thử {attempt}/{max_attempts}] Lỗi khi gửi kịch bản: {e}")
                time.sleep(0.3)

        if not success:
            logger.error(f"[Script Send] 🛑 Đã thất bại sau {max_attempts} lần thử liên tiếp. DỪNG LẠI BẮT BUỘC!")

        return success

    @staticmethod
    def copy_image_to_clipboard(image_path: str) -> bool:
        """Nạp ảnh trực tiếp vào Windows Clipboard dưới dạng CF_DIB (Device Independent Bitmap)."""
        if not HAS_WIN32 or not os.path.exists(image_path):
            return False
        img = None
        output = None
        try:
            import io
            import win32clipboard
            from PIL import Image

            img = Image.open(image_path)
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
        except Exception as e:
            logger.error(f"[Zalo Automation] Lỗi đọc ảnh DIB: {e}")
            return False
        finally:
            if output:
                try:
                    output.close()
                except Exception:
                    pass
            if img:
                try:
                    img.close()
                except Exception:
                    pass

        try:
            opened = False
            for _ in range(5):
                try:
                    win32clipboard.OpenClipboard(0)
                    opened = True
                    break
                except Exception:
                    time.sleep(0.05)

            if opened:
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            return False
        except Exception as e:
            logger.error(f"[Zalo Automation] Lỗi copy_image_to_clipboard: {e}")
            return False

    @staticmethod
    def send_drive_mockup_and_text(
        image_path: str,
        text_content: str,
        background_mode: bool = True,
        auto_press_enter: bool = True,
        max_attempts: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Gửi hình ảnh Mockup Google Drive và nội dung Link + Tin nhắn chốt vào Zalo PC hoặc Cửa sổ Active.
        
        Quy trình chuẩn an toàn:
        1. Kiểm tra an toàn loại trừ PID của Dashboard chính mình (Rule 1.1).
        2. Nếu background_mode = True: Tìm Zalo HWND -> Focus Zalo -> Focus Chat Input.
           Nếu background_mode = False: Focus vào cửa sổ ngoài gần nhất (Active Window / Remote Desktop).
        3. Copy ảnh dạng Bitmap DIB vào Clipboard và Dán (Ctrl+V) -> Enter để gửi ảnh trước.
        4. Copy nội dung văn bản (Link khối + Tin nhắn chốt) vào Clipboard và Dán (Ctrl+V) -> Enter.
        5. Khôi phục cửa sổ cũ nếu ở background_mode.
        """
        if max_attempts is None:
            max_attempts = ZaloAutomation.get_max_retries()

        if ZaloAutomation.is_abort_requested():
            return False, "Bị hủy theo lệnh người dùng (F9)."

        if not os.path.exists(image_path):
            return False, f"File ảnh không tồn tại: {image_path}"

        my_pid = os.getpid()

        for attempt in range(1, max_attempts + 1):
            if ZaloAutomation.is_abort_requested():
                return False, "Bị hủy theo lệnh người dùng (F9)."

            try:
                if background_mode:
                    target_hwnd = ZaloAutomation.find_zalo_hwnd()
                    if not target_hwnd:
                        logger.warning(f"[Fake Drive Send] [Lần thử {attempt}/{max_attempts}] Không tìm thấy cửa sổ Zalo PC đích.")
                        time.sleep(0.4)
                        continue

                    # Kiểm tra PID để không bao giờ tự target vào Dashboard chính mình
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(target_hwnd)
                        if pid == my_pid:
                            logger.error("[Fake Drive Send] Target HWND trùng với Dashboard PID! Bỏ qua để chống Self-Target.")
                            return False, "Không thể gửi vào chính cửa sổ Dashboard."
                    except Exception:
                        pass

                    def _do_send():
                        # Focus Zalo & Chat Input
                        ZaloAutomation.focus_chat_input()
                        time.sleep(0.12)

                        # 1. Nạp ảnh DIB vào Clipboard và Dán
                        copied_img = ZaloAutomation.copy_image_to_clipboard(image_path)
                        if not copied_img:
                            # Fallback: Copy dạng Drop Files
                            ZaloAutomation.copy_files_to_clipboard([image_path])
                        
                        time.sleep(0.08)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.6)  # Chờ Zalo nạp ảnh preview
                        pyautogui.press("enter")
                        time.sleep(0.5)

                        # 2. Nạp văn bản (Link + Tin chốt) và Dán
                        if text_content and text_content.strip():
                            pyperclip.copy(text_content.strip())
                            time.sleep(0.08)
                            pyautogui.hotkey("ctrl", "v")
                            time.sleep(0.15)
                            if auto_press_enter:
                                pyautogui.press("enter")
                                time.sleep(0.1)

                        return True

                    res = ZaloAutomation.quick_focus_and_restore(_do_send, restore_delay=0.2)
                    if res:
                        logger.info("[Fake Drive Send] 🎉 Đã bắn ảnh Google Drive & Text thành công vào Zalo PC!")
                        return True, "Thành công"
                    else:
                        time.sleep(0.3)
                else:
                    # ================= ACTIVE WINDOW MODE (GỬI VÀO CỬA SỔ ĐANG MỞ) =================
                    # Focus vào cửa sổ ngoài gần nhất nếu có
                    if ZaloAutomation._last_external_hwnd and HAS_WIN32 and win32gui.IsWindow(ZaloAutomation._last_external_hwnd):
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(ZaloAutomation._last_external_hwnd)
                            if pid != my_pid:
                                win32gui.SetForegroundWindow(ZaloAutomation._last_external_hwnd)
                                time.sleep(0.2)
                        except Exception:
                            pass

                    # 1. Dán ảnh
                    copied_img = ZaloAutomation.copy_image_to_clipboard(image_path)
                    if not copied_img:
                        ZaloAutomation.copy_files_to_clipboard([image_path])
                    
                    time.sleep(0.1)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.6)
                    pyautogui.press("enter")
                    time.sleep(0.5)

                    # 2. Dán text
                    if text_content and text_content.strip():
                        pyperclip.copy(text_content.strip())
                        time.sleep(0.08)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.15)
                        if auto_press_enter:
                            pyautogui.press("enter")
                            time.sleep(0.1)

                    return True, "Thành công"
            except Exception as e:
                logger.warning(f"[Fake Drive Send] [Lần thử {attempt}/{max_attempts}] Lỗi: {e}")
                time.sleep(0.3)

        return False, f"Thất bại sau {max_attempts} lần thử liên tiếp."

    @staticmethod
    def broadcast_to_groups_in_tag(
        tag_name: str,
        messages: List[str],
        file_paths: List[str],
        state_mgr,
        batch_id: str = "",
        template_num: int = 1,
        max_groups: int = 5,
        delay_between: float = 3.5,
        min_delay: float = 5.0,
        max_delay: float = 15.0,
        progress_callback: Optional[Callable] = None,
        use_random_template: bool = False,
        anti_spam_time: bool = True,
        anti_spam_code: bool = False,
        anti_spam_icon: bool = False,
        max_attempts: int = MAX_RETRIES,
        background_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        QUY TRÌNH GỬI TIN & FILE ĐẾN TOÀN BỘ NHÓM TRONG TAB PHÂN LOẠI:
        - Sử dụng Thuật toán Hàng Đợi Đảo Ngược (Bottom-Up Shift Queue): Luôn gửi nhóm ở đáy hàng đợi để khi Zalo
          đẩy nhóm đã gửi lên đầu (Index 0), các nhóm chưa gửi bên dưới sẽ lần lượt được gửi trọn vẹn,
          TUYỆT ĐỐI KHÔNG BỊ GỬI LẶP 1 NHÓM NHIỀU LẦN VÀ KHÔNG BỎ SÓT BẤT KỲ NHÓM NÀO!
        - Giới hạn đúng số lượng nhóm cần gửi (mặc định max_groups), dừng ngay khi gửi đủ.
        - Hỗ trợ Random Delay Min-Max giữa các lần gửi giúp ổn định đường truyền mạng upload file nặng 200MB.
        - Hỗ trợ Tạm dừng (F6), Tiếp tục (F6), Hủy (F7).
        - Hỗ trợ Random Mẫu tin nhắn hoặc Mẫu mặc định.
        - Hỗ trợ Chống Spam (Chèn giờ HH:MM, mã ngẫu nhiên, icon ngẫu nhiên).
        """
        from datetime import datetime
        import random
        from core.state_manager import apply_anti_spam_randomizer
        
        total_targets = max(1, min(max_groups, 100))
        logger.info(f"[Zalo Broadcast] 📢 Bắt đầu chiến dịch gửi {total_targets} nhóm trong Thẻ '{tag_name}'...")
        BroadcastController.start()
        results = []
        if not batch_id:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Bước 1: Kích hoạt Zalo PC hoặc Cửa sổ Remote (UltraViewer / AnyDesk)
        is_remote = ZaloAutomation.is_remote_desktop_target()
        if not is_remote:
            if tag_name:
                ZaloAutomation.filter_by_tag_name(tag_name, max_attempts=max_attempts)
                time.sleep(0.8)
            else:
                ZaloAutomation.activate_zalo(max_attempts=max_attempts)
                time.sleep(0.8)
        else:
            target_info = ZaloAutomation.get_target_window()
            logger.info(f"[Zalo Broadcast - Remote Mode] 🌐 Gửi ngầm qua [{target_info.get('proc_name')}] '{target_info.get('title')}' vào máy bị điều khiển...")

        # Bước 2: Duyệt lần lượt từng nhóm theo danh sách (từ nhóm 1 đến nhóm N)
        for idx in range(total_targets):
            # Kiểm tra tín hiệu HỦY BỎ (F7)
            if BroadcastController.is_cancelled:
                logger.warning("[Zalo Broadcast] ⏹ Nhận lệnh HỦY GỬI từ người dùng. Dừng chiến dịch ngay lập tức.")
                break

            # Kiểm tra trạng thái TẠM DỪNG (F6)
            while BroadcastController.is_paused:
                time.sleep(0.5)
                if BroadcastController.is_cancelled:
                    break
            if BroadcastController.is_cancelled:
                break

            # Mở nhóm thứ idx (idx = 0: nhóm 1, idx = 1: nhóm 2,...)
            mode_label = "NGẦM" if background_mode else "Foreground"
            logger.info(f"[Zalo Broadcast] 👉 [Nhóm {idx + 1}/{total_targets}] [{mode_label}] Đang mở nhóm thứ {idx + 1}...")
            if background_mode:
                clicked = ZaloAutomation.click_conversation_by_index_background(index=idx, max_attempts=max_attempts)
            else:
                clicked = ZaloAutomation.click_conversation_by_index(index=idx, max_attempts=max_attempts)
            if not clicked:
                logger.info(f"[Zalo Broadcast] Đã duyệt hết tất cả các nhóm trong danh sách.")
                break

            time.sleep(0.7)

            group_label = f"Nhóm #{idx + 1} ({tag_name})"

            # Kiểm tra chống gửi lặp trong đợt này
            if state_mgr and state_mgr.is_group_sent_in_batch(group_label, batch_id):
                logger.info(f"[Zalo Broadcast] ⏭️ Nhóm '{group_label}' đã được gửi trong đợt này. BỎ QUA tránh lặp.")
                continue

            # Lấy nội dung gửi (Nếu bật Random Mẫu tin nhắn)
            cur_msgs = list(messages)
            cur_files = list(file_paths)
            cur_tpl_num = template_num

            if use_random_template and state_mgr:
                rnd_tpl = state_mgr.get_random_active_template()
                if rnd_tpl:
                    cur_msgs = [rnd_tpl.get('content', '')] if rnd_tpl.get('content') else []
                    cur_files = rnd_tpl.get('files', [])
                    cur_tpl_num = rnd_tpl.get('template_num', template_num)

            # Áp dụng bộ ngẫu nhiên chống spam Zalo
            customized_msgs = []
            for m in cur_msgs:
                if m.strip():
                    c_msg = apply_anti_spam_randomizer(
                        m,
                        append_time=anti_spam_time,
                        append_random_code=anti_spam_code,
                        append_random_icon=anti_spam_icon
                    )
                    customized_msgs.append(c_msg)

            # Gửi tin nhắn text (Foreground hoặc Background)
            success_text = True
            for m in customized_msgs:
                if BroadcastController.is_cancelled:
                    break
                if background_mode:
                    sent_m = ZaloAutomation.send_message_text_background(m, max_attempts=max_attempts)
                else:
                    sent_m = ZaloAutomation.send_message_text(m, max_attempts=max_attempts)
                if not sent_m:
                    success_text = False
                time.sleep(1.2)

            # Gửi file đính kèm (Foreground hoặc Background)
            success_file = True
            if cur_files and not BroadcastController.is_cancelled:
                time.sleep(0.8)
                if background_mode:
                    success_file = ZaloAutomation.send_files_background(cur_files, max_attempts=max_attempts)
                else:
                    success_file = ZaloAutomation.send_files_to_current_chat(cur_files, max_attempts=max_attempts)

            overall_ok = success_text and (success_file if cur_files else True)
            status_str = "COMPLETED" if overall_ok else "FAILED"

            if state_mgr:
                preview = customized_msgs[0] if customized_msgs else "Gửi file đính kèm"
                state_mgr.log_group_broadcast(
                    group_name=group_label,
                    tag_name=tag_name,
                    template_num=cur_tpl_num,
                    message_preview=preview,
                    file_count=len(cur_files),
                    status=status_str,
                    batch_id=batch_id
                )

            res_item = {
                "group_index": idx + 1,
                "group_name": group_label,
                "status": status_str,
                "messages_sent": len(customized_msgs),
                "files_sent": len(cur_files)
            }
            results.append(res_item)

            if progress_callback:
                try:
                    progress_callback(idx + 1, group_label, status_str)
                except Exception:
                    pass

            # Random thời gian nghỉ giữa các nhóm
            if min_delay > 0 or max_delay > 0:
                low_d = min(min_delay, max_delay)
                high_d = max(min_delay, max_delay)
                actual_delay = round(random.uniform(low_d, high_d), 1)
            else:
                actual_delay = delay_between if delay_between > 0 else 3.5

            logger.info(f"[Zalo Broadcast] ⏳ Nghỉ ngẫu nhiên {actual_delay}s (Min {min_delay}s - Max {max_delay}s) trước khi gửi nhóm tiếp theo...")
            t_start = time.time()
            while time.time() - t_start < actual_delay:
                if BroadcastController.is_cancelled:
                    break
                while BroadcastController.is_paused:
                    time.sleep(0.5)
                    if BroadcastController.is_cancelled:
                        break
                time.sleep(0.2)

        BroadcastController.reset()
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        logger.info(f"[Zalo Broadcast] 🎉 Hoàn tất chiến dịch gửi tin nhóm! Đã gửi thành công vào {sum(1 for r in results if r['status'] == 'COMPLETED')}/{len(results)} nhóm.")
        return results

    @staticmethod
    def broadcast_to_custom_target_list(
        target_names: List[str],
        messages: List[str],
        file_paths: List[str],
        state_mgr,
        batch_id: str = "",
        template_num: int = 1,
        delay_between: float = 3.5,
        min_delay: float = 5.0,
        max_delay: float = 15.0,
        progress_callback: Optional[Callable] = None,
        use_random_template: bool = False,
        anti_spam_time: bool = True,
        anti_spam_code: bool = False,
        anti_spam_icon: bool = False,
        max_attempts: int = MAX_RETRIES,
        background_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        QUY TRÌNH GỬI TIN & FILE THEO DANH SÁCH TÊN NHÓM / TÊN LIÊN HỆ ĐƯỢC NHẬP VÀO:
        - Sử dụng tìm kiếm đích danh bằng phím tắt Ctrl + F trên Zalo PC:
          Tìm đúng Tên Nhóm / Tên Người Dùng / Số Điện Thoại -> Mở phòng chat -> Gửi tin & file.
        - Tuyệt đối chính xác 100%, không bị phụ thuộc vào thứ tự danh sách hay click nhầm nhóm.
        - Hỗ trợ Random Delay Min-Max giữa các lần gửi giúp mạng upload file nặng 200MB ổn định.
        - Hỗ trợ Tạm dừng (F6), Tiếp tục (F6), Hủy (F7).
        - Hỗ trợ Random Mẫu tin nhắn hoặc Mẫu mặc định.
        - Hỗ trợ Chống Spam (Chèn giờ HH:MM, mã ngẫu nhiên, icon ngẫu nhiên).
        - Ghi nhật ký vào CSDL và cập nhật trạng thái tiến trình.
        """
        from datetime import datetime
        import random
        from core.state_manager import apply_anti_spam_randomizer

        cleaned_targets = [t.strip() for t in target_names if t and t.strip()]
        total_targets = len(cleaned_targets)
        if total_targets == 0:
            logger.warning("[Zalo Custom Broadcast] Danh sách người nhận trống.")
            return []

        logger.info(f"[Zalo Custom Broadcast] 📢 Bắt đầu gửi đến {total_targets} nhóm/người nhận đích danh (Delay Random: {min_delay}s - {max_delay}s)...")
        BroadcastController.start()
        results = []
        if not batch_id:
            batch_id = f"custom_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Đảm bảo Zalo PC hoặc Cửa sổ Remote đang sẵn sàng
        is_remote = ZaloAutomation.is_remote_desktop_target()
        if not is_remote:
            ZaloAutomation.activate_zalo(max_attempts=max_attempts)
            time.sleep(0.5)
        else:
            target_info = ZaloAutomation.get_target_window()
            logger.info(f"[Zalo Custom Broadcast - Remote Mode] 🌐 Gửi ngầm qua [{target_info.get('proc_name')}] '{target_info.get('title')}' vào máy bị điều khiển...")

        for idx, target_name in enumerate(cleaned_targets):
            # Kiểm tra tín hiệu HỦY BỎ (F7)
            if BroadcastController.is_cancelled:
                logger.warning("[Zalo Custom Broadcast] ⏹ Nhận lệnh HỦY GỬI từ người dùng. Dừng chiến dịch ngay lập tức.")
                break

            # Kiểm tra trạng thái TẠM DỪNG (F6)
            while BroadcastController.is_paused:
                time.sleep(0.5)
                if BroadcastController.is_cancelled:
                    break
            if BroadcastController.is_cancelled:
                break

            logger.info(f"[Zalo Custom Broadcast] 👉 [{idx + 1}/{total_targets}] Đang tìm & mở: '{target_name}'...")

            # Kiểm tra chống gửi lặp trong đợt này
            if state_mgr and state_mgr.is_group_sent_in_batch(target_name, batch_id):
                logger.info(f"[Zalo Custom Broadcast] ⏭️ '{target_name}' đã được gửi trong đợt này. BỎ QUA tránh lặp.")
                continue

            # Mở cuộc trò chuyện bằng tìm kiếm Ctrl + F (Foreground hoặc Background)
            if background_mode:
                opened = ZaloAutomation.open_chat_background(target_name, max_attempts=max_attempts)
            else:
                opened = ZaloAutomation.open_chat_with_contact(target_name, max_attempts=max_attempts)
            if not opened:
                logger.error(f"[Zalo Custom Broadcast] ❌ Không thể mở đoạn chat với: '{target_name}'.")
                status_str = "FAILED_OPEN"
                res_item = {
                    "group_index": idx + 1,
                    "group_name": target_name,
                    "status": status_str,
                    "messages_sent": 0,
                    "files_sent": 0
                }
                results.append(res_item)
                if progress_callback:
                    try:
                        progress_callback(idx + 1, target_name, status_str)
                    except Exception:
                        pass
                time.sleep(1.0)
                continue

            time.sleep(0.6)

            # Lấy nội dung gửi (Nếu bật Random Mẫu tin nhắn)
            cur_msgs = list(messages)
            cur_files = list(file_paths)
            cur_tpl_num = template_num

            if use_random_template and state_mgr:
                rnd_tpl = state_mgr.get_random_active_template()
                if rnd_tpl:
                    cur_msgs = [rnd_tpl.get('content', '')] if rnd_tpl.get('content') else []
                    cur_files = rnd_tpl.get('files', [])
                    cur_tpl_num = rnd_tpl.get('template_num', template_num)

            # Áp dụng bộ ngẫu nhiên chống spam Zalo
            customized_msgs = []
            for m in cur_msgs:
                if m.strip():
                    c_msg = apply_anti_spam_randomizer(
                        m,
                        append_time=anti_spam_time,
                        append_random_code=anti_spam_code,
                        append_random_icon=anti_spam_icon
                    )
                    customized_msgs.append(c_msg)

            # Gửi tin nhắn text (Foreground hoặc Background)
            success_text = True
            for m in customized_msgs:
                if BroadcastController.is_cancelled:
                    break
                if background_mode:
                    sent_m = ZaloAutomation.send_message_text_background(m, max_attempts=max_attempts)
                else:
                    sent_m = ZaloAutomation.send_message_text(m, max_attempts=max_attempts)
                if not sent_m:
                    success_text = False
                time.sleep(1.2)

            # Gửi file đính kèm (Foreground hoặc Background)
            success_file = True
            if cur_files and not BroadcastController.is_cancelled:
                time.sleep(0.8)
                if background_mode:
                    success_file = ZaloAutomation.send_files_background(cur_files, max_attempts=max_attempts)
                else:
                    success_file = ZaloAutomation.send_files_to_current_chat(cur_files, max_attempts=max_attempts)

            overall_ok = success_text and (success_file if cur_files else True)
            status_str = "COMPLETED" if overall_ok else "FAILED"

            if state_mgr:
                preview = customized_msgs[0] if customized_msgs else "Gửi file đính kèm"
                state_mgr.log_group_broadcast(
                    group_name=target_name,
                    tag_name="Danh sách tự nhập",
                    template_num=cur_tpl_num,
                    message_preview=preview,
                    file_count=len(cur_files),
                    status=status_str,
                    batch_id=batch_id
                )

            res_item = {
                "group_index": idx + 1,
                "group_name": target_name,
                "status": status_str,
                "messages_sent": len(customized_msgs),
                "files_sent": len(cur_files)
            }
            results.append(res_item)

            if progress_callback:
                try:
                    progress_callback(idx + 1, target_name, status_str)
                except Exception:
                    pass

            # Random thời gian nghỉ giữa các nhóm/người
            if min_delay > 0 or max_delay > 0:
                low_d = min(min_delay, max_delay)
                high_d = max(min_delay, max_delay)
                actual_delay = round(random.uniform(low_d, high_d), 1)
            else:
                actual_delay = delay_between if delay_between > 0 else 3.5

            logger.info(f"[Zalo Custom Broadcast] ⏳ Nghỉ ngẫu nhiên {actual_delay}s (Min {min_delay}s - Max {max_delay}s) trước khi gửi mục tiếp theo...")
            t_start = time.time()
            while time.time() - t_start < actual_delay:
                if BroadcastController.is_cancelled:
                    break
                while BroadcastController.is_paused:
                    time.sleep(0.5)
                    if BroadcastController.is_cancelled:
                        break
                time.sleep(0.2)

        BroadcastController.reset()
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        logger.info(f"[Zalo Custom Broadcast] 🎉 Hoàn tất gửi theo danh sách! Thành công {sum(1 for r in results if r['status'] == 'COMPLETED')}/{len(results)} nhóm/người.")
        return results

    @staticmethod
    def extract_target_names_from_tag(
        tag_name: str,
        gemini_engine,
        max_scrolls: int = 4,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        TỰ ĐỘNG QUÉT VÀ TRÍCH XUẤT TOÀN BỘ TÊN NHÓM / NGƯỜI DÙNG TỪ THẺ PHÂN LOẠI TRÊN ZALO PC:
        1. Kích hoạt Zalo PC và chọn Thẻ phân loại được yêu cầu.
        2. Chụp ảnh vùng danh sách hội thoại bên trái (Sidebar).
        3. Sử dụng Gemini Vision đọc và trích xuất danh sách tên nhóm/người dùng chuẩn xác 100%.
        4. Tự động cuộn danh sách (nếu có nhiều nhóm) để quét toàn diện không bỏ sót.
        5. Trả về danh sách tên nhóm/người nhận đã lọc trùng lặp.
        """
        logger.info(f"[Zalo Tag Scanner] 🔍 Bắt đầu quét danh sách nhóm/người từ Thẻ: '{tag_name}'...")
        if not ZaloAutomation.activate_zalo(max_attempts=3):
            logger.error("[Zalo Tag Scanner] Không thể kích hoạt cửa sổ Zalo PC.")
            return []

        time.sleep(0.4)
        if tag_name:
            ZaloAutomation.filter_by_tag_name(tag_name, max_attempts=3)
            time.sleep(0.7)

        rect = ZaloAutomation.get_zalo_rect()
        if not rect:
            logger.error("[Zalo Tag Scanner] Không tìm thấy kích thước cửa sổ Zalo.")
            return []

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        # Vùng danh sách hội thoại Zalo bên trái
        list_x = left + 55
        list_y = top + 120
        list_w = min(280, int(width * 0.28))
        list_h = max(260, height - 160)

        all_names = []
        seen_names = set()

        prompt_extract = (
            "Dưới đây là ảnh chụp cột danh sách hội thoại Zalo PC (các nhóm và người dùng thuộc Thẻ phân loại).\n"
            "Hãy trích xuất chính xác danh sách TÊN TẤT CẢ CÁC NHÓM / NGƯỜI DÙNG hiển thị trong danh sách này:\n"
            "- BỎ QUA các nhãn thời gian như 'Vài giây', '2 phút', '2 giờ', '3 giờ', '34 phút',...\n"
            "- BỎ QUA dòng tin nhắn phụ bên dưới (như 'Bạn: Video', 'Tin nhắn đã được thu hồi', 'Bạn: Sau khi nhận được...', 'Lê Mai Ngọc: ...').\n"
            "- CHỈ TRẢ VỀ danh sách Tên Nhóm / Tên Người Dùng, mỗi tên trên một dòng riêng biệt.\n"
            "- Giữ nguyên chữ hoa, chữ thường, dấu tiếng Việt và ký tự đặc biệt của tên.\n"
            "- Không đánh số thứ tự (1, 2, 3), không gạch đầu dòng."
        )

        for scroll_idx in range(max_scrolls):
            temp_scan_path = f"temp_tag_scan_{scroll_idx}.png"
            try:
                screenshot = pyautogui.screenshot(region=(list_x, list_y, list_w, list_h))
                screenshot.save(temp_scan_path)
            except Exception as e:
                logger.warning(f"[Zalo Tag Scanner] Lỗi chụp ảnh màn hình: {e}")
                break

            if progress_callback:
                try:
                    progress_callback(f"Đang quét trang {scroll_idx + 1}...")
                except Exception:
                    pass

            # Đưa ảnh vào Gemini Vision
            replies, _ = gemini_engine.generate_response(prompt_extract, image_path=temp_scan_path)
            
            # Xóa file ảnh tạm
            if os.path.exists(temp_scan_path):
                try:
                    os.remove(temp_scan_path)
                except Exception:
                    pass

            new_found = 0
            if replies:
                raw_text = "\n".join(replies)
                for line in raw_text.splitlines():
                    cleaned = line.strip()
                    import re
                    cleaned = re.sub(r'^[0-9]+[\.\)\-]\s*', '', cleaned)
                    cleaned = re.sub(r'^[\-\*\•\–]\s*', '', cleaned)
                    cleaned = cleaned.strip()

                    if not cleaned or len(cleaned) < 2:
                        continue
                    if any(cleaned.lower().startswith(x) for x in ["bạn:", "tin nhắn", "đoạn chat", "danh sách", "thẻ:", "phân loại"]):
                        continue

                    if cleaned not in seen_names:
                        seen_names.add(cleaned)
                        all_names.append(cleaned)
                        new_found += 1

            logger.info(f"[Zalo Tag Scanner] Trang {scroll_idx + 1}: Tìm thấy {new_found} tên nhóm mới (Tổng cộng: {len(all_names)}).")

            if new_found == 0 and scroll_idx > 0:
                break

            if scroll_idx < max_scrolls - 1:
                try:
                    pyautogui.moveTo(list_x + 120, list_y + 200)
                    time.sleep(0.1)
                    pyautogui.scroll(-380)
                    time.sleep(0.5)
                except Exception:
                    break

        logger.info(f"[Zalo Tag Scanner] 🎉 Quét hoàn tất! Tổng cộng trích xuất được {len(all_names)} tên nhóm/người từ Thẻ '{tag_name}'.")
        return all_names


class BroadcastController:
    """Điều khiển tiến trình gửi tin nhóm: Tạm dừng, Tiếp tục, Hủy bỏ (F6/F7)."""
    is_running = False
    is_paused = False
    is_cancelled = False
    status_text = "Sẵn sàng"

    @classmethod
    def start(cls):
        cls.is_running = True
        cls.is_paused = False
        cls.is_cancelled = False
        cls.status_text = "Đang chạy"

    @classmethod
    def toggle_pause(cls) -> bool:
        if not cls.is_running:
            return False
        cls.is_paused = not cls.is_paused
        cls.status_text = "Đang tạm dừng" if cls.is_paused else "Đang chạy tiếp"
        logger.info(f"[BroadcastController] ⏯ {cls.status_text}")
        return cls.is_paused

    @classmethod
    def cancel(cls):
        cls.is_cancelled = True
        cls.is_paused = False
        cls.status_text = "Đã hủy gửi"
        logger.info("[BroadcastController] ⏹ Đã gửi tín hiệu HỦY CHIẾN DỊCH GỬI TIN.")

    @classmethod
    def reset(cls):
        cls.is_running = False
        cls.is_paused = False
        cls.is_cancelled = False
        cls.status_text = "Sẵn sàng"


# Alias để tương thích cả 2 cách gọi
BroadcastController.broadcast_to_groups_in_tag = ZaloAutomation.broadcast_to_groups_in_tag
BroadcastController.broadcast_to_custom_target_list = ZaloAutomation.broadcast_to_custom_target_list



