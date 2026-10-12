import os
import math
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont

TEMP_IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")

def _get_font(font_name: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Tải font chuẩn từ hệ điều hành Windows với fallback an toàn."""
    font_paths = []
    if bold:
        font_paths = [
            f"C:/Windows/Fonts/{font_name}bd.ttf",
            f"C:/Windows/Fonts/{font_name}b.ttf",
            f"C:/Windows/Fonts/{font_name}Bold.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf"
        ]
    else:
        font_paths = [
            f"C:/Windows/Fonts/{font_name}.ttf",
            f"C:/Windows/Fonts/{font_name}r.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf"
        ]

    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_folder_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color="#5f6368"):
    """Vẽ icon thư mục Google Drive dạng vector sắc nét chuẩn Google Material."""
    # Tab đỉnh
    draw.polygon([(x, y + 2), (x + 6, y + 2), (x + 8, y + 5), (x, y + 5)], fill=color)
    # Thân thư mục
    draw.rounded_rectangle([x, y + 4, x + 16, y + 14], radius=2, fill=color)


def _draw_gear_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 6, color="#444746"):
    """Vẽ icon bánh răng Settings Google."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=1)
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=color)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int((r - 1) * math.cos(rad))
        y1 = cy + int((r - 1) * math.sin(rad))
        x2 = cx + int((r + 2) * math.cos(rad))
        y2 = cy + int((r + 2) * math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=color, width=1)


def _draw_help_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 6, color="#444746"):
    """Vẽ icon dấu hỏi Help Google."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=1)
    font_q = _get_font("arial", 9, bold=True)
    draw.text((cx - 3, cy - 6), "?", fill=color, font=font_q)


def _draw_link_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color="#1f1f1f"):
    """Vẽ icon sao chép liên kết hai khuyên."""
    draw.rounded_rectangle([x, y + 2, x + 8, y + 9], radius=3, outline=color, width=2)
    draw.rounded_rectangle([x + 6, y + 5, x + 14, y + 12], radius=3, outline=color, width=2)
    draw.line([x + 6, y + 6, x + 8, y + 8], fill=color, width=2)


def _draw_back_arrow(draw: ImageDraw.ImageDraw, x: int, y: int, color="#1f1f1f"):
    """Vẽ mũi tên quay lại ←."""
    draw.line([x + 2, y + 6, x + 13, y + 6], fill=color, width=2)
    draw.line([x + 2, y + 6, x + 6, y + 2], fill=color, width=2)
    draw.line([x + 2, y + 6, x + 6, y + 10], fill=color, width=2)


def _draw_user_avatar(img: Image.Image, cx: int, cy: int, r: int = 10, letter: str = "T"):
    """Vẽ avatar người dùng hình tròn nhiều màu sắc tự nhiên."""
    draw = ImageDraw.Draw(img)
    colors = ["#43a047", "#1e88e5", "#e53935", "#fb8c00", "#8e24aa", "#00acc1", "#3949ab", "#d81b60"]
    idx = abs(hash(letter)) % len(colors)
    bg_color = colors[idx]
    
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_color)
    font_av = _get_font("arial", 10, bold=True)
    draw.text((cx - 4, cy - 6), letter.upper()[:1], fill="#ffffff", font=font_av)


def render_drive_share_image(
    email: Union[str, List[str]] = "vothihuyen82@gmail.com",
    folders: Optional[List[str]] = None,
    role: str = "Người xem",
    notify: bool = True,
    message: str = "",
    output_path: Optional[str] = None
) -> str:
    """
    Render hình ảnh Popup Google Drive Share hoàn hảo 100% giống giao diện gốc của Google Drive (Hình 1 & 2).
    Hỗ trợ gửi 1 hoặc NHIỀU EMAIL đồng thời (mỗi email một chip avatar riêng xếp dọc chuẩn Google Material).
    
    Tham số:
    - email: Địa chỉ email người nhận (chuỗi hoặc danh sách các email)
    - folders: Danh sách tên thư mục (ví dụ: ["BỘ MỚI HK1 K7", "BỘ MỚI HK1 K8", "BỘ MỚI HK1 K9"])
    - role: Quyền truy cập (Người xem / Người chỉnh sửa / Người nhận xét)
    - notify: Có tích chọn thông báo email không
    - message: Lời nhắn tùy chỉnh (để trống sẽ hiện placeholder 'Lời nhắn')
    - output_path: Đường dẫn lưu file ảnh (mặc định lưu vào storage/temp_drive_share.png)
    
    Trả về:
    - Đường dẫn tuyệt đối đến file ảnh PNG đã render.
    """
    import re

    # 1. Chuẩn hóa danh sách Email
    if isinstance(email, str):
        found_emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", email)
        if found_emails:
            email_list = found_emails
        else:
            s = email.strip()
            email_list = [s] if s else ["vothihuyen82@gmail.com"]
    elif isinstance(email, (list, tuple)):
        email_list = []
        for item in email:
            if isinstance(item, str):
                for em in re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", item):
                    if em not in email_list:
                        email_list.append(em)
        if not email_list:
            email_list = ["vothihuyen82@gmail.com"]
    else:
        email_list = ["vothihuyen82@gmail.com"]

    num_emails = len(email_list)

    if not folders:
        folders = ["THPT AI MỚI L2 10-08"]

    num_folders = len(folders)
    is_multi_folders = num_folders > 1

    # Tính toán kích thước card
    card_w = 410
    
    # Tính số hàng folder chips (mỗi hàng chứa tối đa 2 chips)
    chip_rows = math.ceil(num_folders / 2) if is_multi_folders else 0
    extra_height_folders = (chip_rows * 36) if is_multi_folders else 0

    # Chiều cao box input email: 1 email = 38px, nhiều email = 10 + num_emails * 33px
    input_box_h = 38 if num_emails == 1 else (10 + num_emails * 33)
    extra_height_emails = input_box_h - 38

    card_h = 390 + extra_height_folders + extra_height_emails
    canvas_w = 470
    canvas_h = card_h + 60

    # 1. Tạo Canvas nền xám Google Drive
    canvas = Image.new("RGB", (canvas_w, canvas_h), color="#9fa8b1")
    draw = ImageDraw.Draw(canvas)

    # Thanh bar xanh phía trên Drive
    draw.rectangle([0, 0, canvas_w, 20], fill="#7c9bb4")
    # Avatar nhỏ góc trên phải Drive [H] Tôi
    draw.ellipse([canvas_w - 48, 3, canvas_w - 34, 17], fill="#388e3c")
    font_mini = _get_font("arial", 9, bold=True)
    draw.text((canvas_w - 43, 3), "H", fill="#ffffff", font=font_mini)
    draw.text((canvas_w - 30, 4), "Tôi", fill="#1f1f1f", font=_get_font("segoeui", 8))

    # 2. Tọa độ Card Dialog trắng trung tâm
    card_x1 = (canvas_w - card_w) // 2
    card_y1 = 30
    card_x2 = card_x1 + card_w
    card_y2 = card_y1 + card_h

    # Vẽ đổ bóng nhẹ (Soft drop shadow)
    for i in range(5, 0, -1):
        alpha = 8 - i
        shadow_box = [card_x1 - i, card_y1 - i + 2, card_x2 + i, card_y2 + i + 2]
        draw.rounded_rectangle(shadow_box, radius=12 + i, fill="#88929c")

    # Vẽ Dialog trắng chính
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=12, fill="#ffffff")

    # Font definitions
    font_title = _get_font("segoeui", 15, bold=False)
    font_label = _get_font("segoeui", 8, bold=False)
    font_chip = _get_font("segoeui", 10, bold=False)
    font_role = _get_font("segoeui", 10, bold=False)
    font_body = _get_font("segoeui", 11, bold=False)
    font_btn = _get_font("segoeuib", 11, bold=True)
    font_f_chip = _get_font("segoeuib", 9, bold=True)

    # 3. HEADER
    cur_y = card_y1 + 18
    # Mũi tên quay lại
    _draw_back_arrow(draw, card_x1 + 18, cur_y + 4, color="#1f1f1f")

    # Tiêu đề Dialog
    if is_multi_folders:
        title_text = f"Chia sẻ {num_folders} thư mục"
    else:
        folder_title = folders[0] if folders else "Thư mục"
        title_text = f'Chia sẻ "{folder_title}"'

    draw.text((card_x1 + 40, cur_y + 1), title_text, fill="#1f1f1f", font=font_title)

    # Icon Help & Settings bên phải
    _draw_help_icon(draw, card_x2 - 46, cur_y + 10, r=6, color="#444746")
    _draw_gear_icon(draw, card_x2 - 24, cur_y + 10, r=5, color="#444746")

    # 4. INPUT CONTAINER ("Thêm người, nhóm...") & ROLE DROPDOWN
    cur_y += 34
    input_box_x1 = card_x1 + 18
    input_box_y1 = cur_y
    input_box_w = 260
    input_box_x2 = input_box_x1 + input_box_w
    input_box_y2 = input_box_y1 + input_box_h

    # Role box bên phải (căn ở góc trên bên phải)
    role_box_x1 = input_box_x2 + 6
    role_box_y1 = input_box_y1
    role_box_x2 = card_x2 - 18
    role_box_y2 = role_box_y1 + 38

    # Vẽ khung Input Thêm người
    draw.rounded_rectangle([input_box_x1, input_box_y1, input_box_x2, input_box_y2], radius=6, outline="#747775", width=1)
    
    # Nhãn nằm chèn lên viền trên
    lbl_text = "Thêm người, nhóm, không gian và sự kiện trên lịch"
    draw.rectangle([input_box_x1 + 8, input_box_y1 - 5, input_box_x1 + 8 + 205, input_box_y1 + 3], fill="#ffffff")
    draw.text((input_box_x1 + 10, input_box_y1 - 6), lbl_text, fill="#444746", font=font_label)

    # Vẽ từng Chip Email bên trong Input Box
    for e_idx, em_str in enumerate(email_list):
        chip_x1 = input_box_x1 + 6
        chip_y1 = input_box_y1 + 6 + (e_idx * 33)
        chip_y2 = chip_y1 + 26
        
        email_w = int(draw.textlength(em_str, font=font_chip))
        chip_w = 24 + email_w + 18
        chip_w = min(chip_w, input_box_w - (22 if num_emails > 1 else 12))
        chip_x2 = chip_x1 + chip_w

        draw.rounded_rectangle([chip_x1, chip_y1, chip_x2, chip_y2], radius=13, outline="#747775", fill="#ffffff", width=1)
        
        # Avatar trong chip
        user_initial = em_str[0] if em_str else "U"
        _draw_user_avatar(canvas, chip_x1 + 13, chip_y1 + 13, r=8, letter=user_initial)

        # Text Email
        draw.text((chip_x1 + 25, chip_y1 + 6), em_str, fill="#1f1f1f", font=font_chip)
        
        # Nút X đóng chip
        cx_x = chip_x2 - 10
        cx_y = chip_y1 + 13
        draw.line([cx_x - 3, cx_y - 3, cx_x + 3, cx_y + 3], fill="#444746", width=1)
        draw.line([cx_x - 3, cx_y + 3, cx_x + 3, cx_y - 3], fill="#444746", width=1)

    # Nếu có nhiều email, vẽ thanh cuộn Material Scrollbar bên phải input box
    if num_emails > 1:
        sb_x1 = input_box_x2 - 10
        sb_x2 = input_box_x2 - 6
        sb_y1 = input_box_y1 + 18
        sb_y2 = min(sb_y1 + 32, input_box_y2 - 8)
        draw.rounded_rectangle([sb_x1, sb_y1, sb_x2, sb_y2], radius=2, fill="#8e918f")

    # Vẽ khung Role (Người xem ▼)
    draw.rounded_rectangle([role_box_x1, role_box_y1, role_box_x2, role_box_y2], radius=6, outline="#747775", width=1)
    role_str = role if role else "Người xem"
    draw.text((role_box_x1 + 8, role_box_y1 + 11), role_str, fill="#1f1f1f", font=font_role)
    draw.text((role_box_x2 - 14, role_box_y1 + 12), "▼", fill="#444746", font=_get_font("segoeui", 7))

    # 5. CHECKBOX "Thông báo cho những người này"
    cur_y = input_box_y2 + 14
    chk_x = card_x1 + 18
    chk_y = cur_y
    chk_size = 15

    if notify:
        draw.rounded_rectangle([chk_x, chk_y, chk_x + chk_size, chk_y + chk_size], radius=3, fill="#0b57d0")
        draw.line([chk_x + 3, chk_y + 7, chk_x + 6, chk_y + 11], fill="#ffffff", width=2)
        draw.line([chk_x + 6, chk_y + 11, chk_x + 12, chk_y + 4], fill="#ffffff", width=2)
    else:
        draw.rounded_rectangle([chk_x, chk_y, chk_x + chk_size, chk_y + chk_size], radius=3, outline="#747775", fill="#ffffff", width=1)

    draw.text((chk_x + 22, chk_y + 1), "Thông báo cho những người này", fill="#1f1f1f", font=font_body)

    # 6. KHUNG NHẬP LỜI NHẮN (TEXTAREA)
    cur_y = chk_y + 24
    msg_box_x1 = card_x1 + 18
    msg_box_y1 = cur_y
    msg_box_x2 = card_x2 - 18
    msg_box_h = 88
    msg_box_y2 = msg_box_y1 + msg_box_h

    draw.rounded_rectangle([msg_box_x1, msg_box_y1, msg_box_x2, msg_box_y2], radius=6, outline="#747775", width=1)
    msg_display = message.strip() if message else "Lời nhắn"
    msg_color = "#1f1f1f" if message else "#747775"
    draw.text((msg_box_x1 + 12, msg_box_y1 + 10), msg_display, fill=msg_color, font=font_body)

    # 7. CÁC THẺ THƯ MỤC (FOLDER CHIPS) - KHI CHIA SẺ NHIỀU THƯ MỤC
    cur_y = msg_box_y2 + 10
    if is_multi_folders:
        chip_col_w = (card_w - 36 - 8) // 2
        for idx, f_name in enumerate(folders):
            col = idx % 2
            row = idx // 2
            fx1 = card_x1 + 18 + col * (chip_col_w + 8)
            fy1 = cur_y + row * 32
            fx2 = fx1 + chip_col_w
            fy2 = fy1 + 26

            draw.rounded_rectangle([fx1, fy1, fx2, fy2], radius=6, outline="#747775", fill="#ffffff", width=1)
            _draw_folder_icon(draw, fx1 + 8, fy1 + 6, color="#5f6368")
            
            short_name = f_name if len(f_name) <= 19 else f_name[:17] + "..."
            draw.text((fx1 + 28, fy1 + 5), short_name, fill="#1f1f1f", font=font_f_chip)

        cur_y += chip_rows * 32 + 8
    else:
        cur_y += 10

    # 8. FOOTER ACTIONS: Link Icon, Nút Huỷ & Nút Gửi
    footer_y = card_y2 - 38
    _draw_link_icon(draw, card_x1 + 20, footer_y + 4, color="#1f1f1f")

    # Nút "Huỷ"
    draw.text((card_x2 - 115, footer_y + 4), "Huỷ", fill="#0b57d0", font=font_btn)

    # Nút "Gửi" (Pill Button Xanh Dương)
    btn_send_x1 = card_x2 - 72
    btn_send_y1 = footer_y - 3
    btn_send_x2 = card_x2 - 18
    btn_send_y2 = footer_y + 25

    draw.rounded_rectangle([btn_send_x1, btn_send_y1, btn_send_x2, btn_send_y2], radius=14, fill="#0b57d0")
    draw.text((btn_send_x1 + 16, btn_send_y1 + 5), "Gửi", fill="#ffffff", font=font_btn)

    # 9. Lưu file ảnh đầu ra
    if not output_path:
        os.makedirs(TEMP_IMG_DIR, exist_ok=True)
        output_path = os.path.join(TEMP_IMG_DIR, "temp_drive_share.png")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG", quality=95)
    return output_path
