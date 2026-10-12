#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
UNIVERSAL KNOWLEDGE & UPDATEDONE HUB GENERATOR
================================================================================
Công cụ tự động hóa tạo trang tra cứu tài liệu kỹ thuật SPA (Single Page Application)
chuẩn Updatedone Logs v2.9.2 cho bất kỳ thư mục hoặc tệp văn bản/Markdown nào.

Tính năng:
1. Nhận đầu vào là 1 tệp văn bản (ngăn cách bằng '==' hoặc tương đương)
   HOẶC 1 thư mục chứa các tệp .md, .txt.
2. Tự động chuẩn hóa, tạo cấu trúc thư mục .agents/update1/:
   - knowledge/: Các chủ đề tài liệu kỹ thuật
   - changelog_data.json: Cơ sở dữ liệu JSON có phân loại, thẻ tag, tóm tắt
   - index.html: SPA giao diện hiện đại độc lập, chạy offline (file://) lẫn máy chủ web
3. Giao diện tích hợp đầy đủ:
   - Thanh dock nổi 5 nút (Toàn cảnh, Cuộn lên/giữa/xuống có hỗ trợ Click + Nhấn Giữ)
   - Tự động thu nhỏ la bàn (Compass) theo hẹn giờ (30s, 60s, 120s, 5m, không ẩn)
   - 3 chế độ sidebar (Đầy đủ 340px, Icon 56px, Ẩn)
   - Khung Kiến Trúc & Tệp Nguồn Áp Dụng (MVC) với nút Copy và Mở file trực tiếp
   - Dark / Light Mode chuẩn màu HSL, độ tương phản cao
   - Tìm kiếm nhanh bằng phím '/'
================================================================================
"""

import os
import sys
import re
import json
import argparse
import shutil
from datetime import datetime

# Đảm bảo console UTF-8 trên Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def clean_markdown_text(text: str) -> str:
    """Loại bỏ các ký tự ngăn cách thô như ==, ====, ====== ở đầu và cuối."""
    lines = text.strip().splitlines()
    cleaned = []
    for line in lines:
        if re.match(r'^\s*(?:\d+)?={2,}\s*$', line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def extract_title_and_summary(content: str, default_title: str):
    """Trích xuất tiêu đề h1 hoặc dòng đầu tiên và tóm tắt ngắn."""
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    title = default_title
    summary = ""

    for l in lines:
        if l.startswith("# "):
            title = l.replace("# ", "").strip()
            break
        elif l.startswith("**") and l.endswith("**") and len(l) < 120:
            title = l.strip("*").strip()
            break

    # Tìm đoạn văn đầu tiên không phải tiêu đề để làm summary
    for l in lines:
        if not l.startswith("#") and not l.startswith("|") and not l.startswith(">") and not l.startswith("```"):
            clean_l = re.sub(r'[*_`]', '', l).strip()
            if len(clean_l) > 25:
                summary = clean_l[:160] + ("..." if len(clean_l) > 160 else "")
                break

    if not summary:
        summary = f"Tài liệu kỹ thuật và hướng dẫn chi tiết về {title}."

    return title, summary


def guess_category_and_icon(title: str, content: str):
    """Phỏng đoán chuyên mục và icon dựa trên từ khóa nội dung."""
    text_lower = (title + " " + content[:600]).lower()
    
    if any(k in text_lower for k in ["python", "django", "fastapi", "flask"]):
        return "backend", "Backend & Core", "fa-brands fa-python", ["Python", "Backend"]
    elif any(k in text_lower for k in ["php", "laravel", "symfony", "codeigniter"]):
        return "backend", "Backend & Core", "fa-brands fa-php", ["PHP", "Laravel", "Backend"]
    elif any(k in text_lower for k in ["node.js", "nodejs", "nest", "express", "fastify"]):
        return "backend", "Backend & Core", "fa-brands fa-node-js", ["Node.js", "NestJS", "Backend"]
    elif any(k in text_lower for k in ["react", "vue", "angular", "frontend", "ui", "tailwind"]):
        return "frontend", "Frontend & UI", "fa-brands fa-react", ["Frontend", "UI", "React"]
    elif any(k in text_lower for k in ["windows", ".exe", "wpf", "c#", "pyside", "qt"]):
        return "crossplatform", "Đa Nền Tảng", "fa-brands fa-windows", ["Windows", "Desktop", ".exe"]
    elif any(k in text_lower for k in ["flutter", "cross-platform", "đa nền tảng", "android", "iphone", "ios", "tauri"]):
        return "crossplatform", "Đa Nền Tảng", "fa-solid fa-laptop-mobile", ["Cross-Platform", "Mobile", "Flutter"]
    elif any(k in text_lower for k in ["kiến trúc", "architecture", "hệ thống", "mvc", "full-stack", "fullstack"]):
        return "architecture", "Kiến Trúc", "fa-solid fa-cubes", ["Architecture", "System", "Full-Stack"]
    elif any(k in text_lower for k in ["kế hoạch", "plan", "roadmap"]):
        return "plans", "Kế Hoạch & Triển Khai", "fa-solid fa-clipboard-list", ["Plan", "Roadmap"]
    elif any(k in text_lower for k in ["sửa lỗi", "fix", "bug", "tối ưu"]):
        return "fixes", "Sửa Lỗi & Tối Ưu", "fa-solid fa-wrench", ["Fixes", "Optimization"]
    else:
        return "general", "Chuyên Mục Chung", "fa-solid fa-file-lines", ["Documentation", "Guide"]


def parse_source_file_or_dir(source_path: str):
    """Đọc dữ liệu từ file văn bản chia bằng '==' hoặc từ thư mục."""
    items = []
    
    if os.path.isfile(source_path):
        print(f"[*] Đang phân tích tệp nguồn: {source_path}")
        with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        # Tách theo regex bất kỳ dòng nào chỉ chứa dấu = (ít nhất 2 dấu)
        pattern = r'(?m)^\s*(?:\d+)?={2,}\s*$'
        raw_sections = re.split(pattern, raw_text)
        
        sec_idx = 1
        for sec in raw_sections:
            clean_sec = clean_markdown_text(sec)
            if not clean_sec or len(clean_sec) < 30:
                continue

            file_slug = f"{sec_idx:02d}_section_doc.md"
            title, summary = extract_title_and_summary(clean_sec, f"Tài Liệu Phần {sec_idx}")
            
            slug_title = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')[:35]
            if slug_title:
                file_slug = f"{sec_idx:02d}_{slug_title}.md"

            cat_id, cat_name, icon, tags = guess_category_and_icon(title, clean_sec)
            
            items.append({
                "id": f"KB-{sec_idx:03d}",
                "file": f"knowledge/{file_slug}",
                "title": title,
                "category": cat_id,
                "category_name": cat_name,
                "icon": icon,
                "version": "v2.9.2",
                "summary": summary,
                "tags": tags,
                "content": clean_sec
            })
            sec_idx += 1

    elif os.path.isdir(source_path):
        print(f"[*] Đang quét thư mục nguồn: {source_path}")
        doc_files = []
        for root, _, files in os.walk(source_path):
            for file in files:
                if file.endswith((".md", ".txt")) and not file.startswith("index"):
                    doc_files.append(os.path.join(root, file))

        doc_files.sort()
        sec_idx = 1
        for full_path in doc_files:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = clean_markdown_text(f.read())
            
            if not content:
                continue

            default_t = os.path.splitext(os.path.basename(full_path))[0].replace("_", " ").title()
            title, summary = extract_title_and_summary(content, default_t)
            cat_id, cat_name, icon, tags = guess_category_and_icon(title, content)

            target_filename = f"{sec_idx:02d}_{os.path.basename(full_path)}"
            if not target_filename.endswith(".md"):
                target_filename += ".md"

            items.append({
                "id": f"KB-{sec_idx:03d}",
                "file": f"knowledge/{target_filename}",
                "title": title,
                "category": cat_id,
                "category_name": cat_name,
                "icon": icon,
                "version": "v2.9.2",
                "summary": summary,
                "tags": tags,
                "content": content
            })
            sec_idx += 1
    else:
        raise FileNotFoundError(f"Không tìm thấy đường dẫn nguồn: {source_path}")

    return items


def build_spa_html(dataset: dict, project_title: str, version_str: str) -> str:
    """Tạo file HTML SPA duy nhất chứa toàn bộ CSS, JS, Icon, Renderer và Embedded Dataset."""
    dataset_json_str = json.dumps(dataset, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_title} - Technical Architecture Dashboard</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome 6 Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <!-- Marked.js for dynamic Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- Highlight.js for code syntax highlight -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark-dimmed.min.css" id="hljs-theme">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    <!-- Google Fonts: Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace']
                    }}
                }}
            }}
        }}
    </script>
    <style>
        .custom-scrollbar::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        .custom-scrollbar::-webkit-scrollbar-track {{ background: transparent; }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{ background: rgba(148, 163, 184, 0.3); border-radius: 9999px; }}
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {{ background: rgba(148, 163, 184, 0.55); }}

        /* Compact, crisp Markdown rendered typography */
        .markdown-body {{ line-height: 1.55; font-size: 0.84rem; }}
        .dark .markdown-body {{ color: #cbd5e1; }}
        .markdown-body {{ color: #334155; }}

        .dark .markdown-body h1 {{ color: #f8fafc; border-bottom-color: #334155; }}
        .markdown-body h1 {{ font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-top: 0.85rem; margin-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.3rem; }}

        .dark .markdown-body h2 {{ color: #f1f5f9; border-bottom-color: #1e293b; }}
        .markdown-body h2 {{ font-size: 1.02rem; font-weight: 700; color: #1e293b; margin-top: 1rem; margin-bottom: 0.4rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.25rem; }}

        .dark .markdown-body h3 {{ color: #e2e8f0; }}
        .markdown-body h3 {{ font-size: 0.92rem; font-weight: 600; color: #334155; margin-top: 0.75rem; margin-bottom: 0.3rem; }}

        .dark .markdown-body h4 {{ color: #cbd5e1; }}
        .markdown-body h4 {{ font-size: 0.85rem; font-weight: 600; color: #475569; margin-top: 0.6rem; margin-bottom: 0.25rem; }}

        .markdown-body p {{ margin-bottom: 0.55rem; }}
        .markdown-body ul, .markdown-body ol {{ margin-left: 1.35rem; margin-bottom: 0.55rem; }}
        .markdown-body ul {{ list-style-type: disc; }}
        .markdown-body ol {{ list-style-type: decimal; }}
        .markdown-body li {{ margin-bottom: 0.2rem; }}

        .dark .markdown-body code:not(pre code) {{ background-color: #1e293b; color: #38bdf8; border-color: #334155; }}
        .markdown-body code:not(pre code) {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82em; background-color: #f1f5f9; color: #0284c7; padding: 0.12rem 0.3rem; border-radius: 0.3rem; border: 1px solid #e2e8f0; }}

        .code-container {{ position: relative; margin-bottom: 0.75rem; }}
        .code-container pre {{ margin-bottom: 0 !important; }}
        .copy-code-btn {{ position: absolute; top: 0.4rem; right: 0.4rem; z-index: 10; padding: 0.2rem 0.45rem; font-size: 0.7rem; border-radius: 0.3rem; transition: all 0.2s; }}

        .dark .markdown-body pre {{ background-color: #0f172a; border-color: #334155; }}
        .markdown-body pre {{ background-color: #f8fafc; padding: 0.75rem; border-radius: 0.5rem; overflow-x: auto; border: 1px solid #e2e8f0; margin-bottom: 0.75rem; }}
        .markdown-body pre code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background-color: transparent !important; padding: 0; border: none; }}

        .markdown-body table {{ width: 100%; border-collapse: collapse; margin-top: 0.65rem; margin-bottom: 0.85rem; font-size: 0.8rem; }}
        .dark .markdown-body th, .dark .markdown-body td {{ border-color: #334155; }}
        .markdown-body th, .markdown-body td {{ border: 1px solid #e2e8f0; padding: 0.45rem 0.65rem; text-align: left; }}

        .dark .markdown-body th {{ background-color: #1e293b; color: #f8fafc; font-weight: 700; }}
        .markdown-body th {{ background-color: #f8fafc; color: #0f172a; font-weight: 700; }}

        .dark .markdown-body tr:nth-child(even) {{ background-color: rgba(30, 41, 59, 0.4); }}
        .markdown-body tr:nth-child(even) {{ background-color: rgba(241, 245, 249, 0.7); }}

        .dark .markdown-body blockquote {{ border-left-color: #6366f1; background-color: rgba(99, 102, 241, 0.08); color: #94a3b8; }}
        .markdown-body blockquote {{ border-left: 3px solid #6366f1; padding: 0.45rem 0.75rem; background-color: #f5f3ff; color: #475569; font-style: italic; margin-bottom: 0.65rem; border-radius: 0 0.375rem 0.375rem 0; font-size: 0.82rem; }}
        
        .dark .markdown-body hr {{ border-color: #334155; }}
        .markdown-body hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 1rem 0; }}

        /* Card styles - strictly matching theme */
        .sidebar-card {{
            transition: all 0.15s ease-in-out;
        }}
        .dark .sidebar-card-default {{
            background-color: #1e293b !important;
            border-color: #334155 !important;
            color: #f1f5f9;
        }}
        .dark .sidebar-card-default:hover {{
            background-color: #273549 !important;
            border-color: #475569 !important;
        }}
        .sidebar-card-default {{
            background-color: #ffffff !important;
            border-color: #e2e8f0 !important;
            color: #1e293b;
        }}
        .sidebar-card-default:hover {{
            background-color: #f8fafc !important;
            border-color: #cbd5e1 !important;
        }}

        .dark .sidebar-card-active {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.22) 0%, rgba(79, 70, 229, 0.12) 100%) !important;
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 1px #6366f1;
            color: #ffffff;
        }}
        .sidebar-card-active {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(238, 242, 255, 0.9) 100%) !important;
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 1px #6366f1;
            color: #0f172a;
        }}

        /* Floating Nav Dock Styling */
        #quick-nav-dock {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 50;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            user-select: none;
        }}
        .dock-pill-menu {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            padding: 6px;
            border-radius: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 8px 10px -6px rgba(0, 0, 0, 0.15);
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .dark .dock-pill-menu {{
            background: rgba(15, 23, 42, 0.92);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(51, 65, 85, 0.8);
        }}
        .dock-pill-menu {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(226, 232, 240, 0.9);
        }}
        .dock-btn {{
            width: 38px;
            height: 38px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease-in-out;
            cursor: pointer;
            position: relative;
            pointer-events: auto !important;
        }}
        .dock-btn * {{
            pointer-events: none !important;
        }}
        .dock-btn:hover {{
            transform: scale(1.08);
        }}
        .dock-btn:active {{
            transform: scale(0.95);
        }}
        .dock-trigger-btn {{
            width: 44px;
            height: 44px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.45);
            border: 2px solid rgba(255, 255, 255, 0.25);
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: auto !important;
        }}
        .dock-trigger-btn * {{
            pointer-events: none !important;
        }}
        .dock-trigger-btn:hover {{
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6);
        }}
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 font-sans min-h-screen antialiased transition-colors duration-200 flex flex-col" onmousemove="resetQuickNavIdleTimer()" onclick="resetQuickNavIdleTimer()">

    <!-- TOP HEADER -->
    <header class="sticky top-0 z-40 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-3 sm:px-5 py-2 shadow-xs">
        <div class="max-w-[1920px] mx-auto flex items-center justify-between gap-3 flex-wrap">
            
            <!-- Left Brand & Sidebar Mode Switcher -->
            <div class="flex items-center gap-2.5 shrink-0">
                <div class="flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 border border-slate-200 dark:border-slate-700">
                    <button type="button" onclick="setSidebarMode('expanded')" id="btn-mode-expanded" class="px-2 py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-2xs transition cursor-pointer" title="Cột đầy đủ (340px)">
                        <i class="fa-solid fa-bars-staggered"></i>
                    </button>
                    <button type="button" onclick="setSidebarMode('rail')" id="btn-mode-rail" class="px-2 py-1 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition cursor-pointer" title="Chỉ hiện Icon (56px)">
                        <i class="fa-solid fa-grip-vertical"></i>
                    </button>
                    <button type="button" onclick="setSidebarMode('hidden')" id="btn-mode-hidden" class="px-2 py-1 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition cursor-pointer" title="Ẩn hoàn toàn">
                        <i class="fa-solid fa-eye-slash"></i>
                    </button>
                </div>

                <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 text-white flex items-center justify-center text-sm shadow-xs font-black shrink-0">
                    <i class="fa-solid fa-code-commit"></i>
                </div>

                <div>
                    <h1 class="text-xs sm:text-sm font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5 leading-tight">
                        {project_title}
                        <span class="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">
                            {version_str}
                        </span>
                    </h1>
                </div>
            </div>

            <!-- Header Controls: Toàn Cảnh, 50/trang, Ẩn: 60s, Tìm kiếm, Dark Mode -->
            <div class="flex items-center gap-2 flex-wrap">
                <!-- Nút Mục Lục Toàn Cảnh -->
                <button type="button" onclick="openMasterTocModal()" class="px-2.5 py-1 rounded-lg bg-gradient-to-r from-amber-500/15 to-orange-500/15 hover:from-amber-500/25 hover:to-orange-500/25 text-amber-700 dark:text-amber-300 border border-amber-500/40 text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-2xs">
                    <i class="fa-solid fa-folder-tree text-amber-500 text-xs"></i>
                    <span>Toàn Cảnh</span>
                </button>

                <!-- Dropdown Phân Trang -->
                <div class="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-lg text-xs shrink-0">
                    <i class="fa-solid fa-layer-group text-slate-400 text-[10px]"></i>
                    <select id="select-items-per-page" onchange="changeItemsPerPage(this.value)" class="bg-transparent text-slate-800 dark:text-slate-100 font-bold outline-none cursor-pointer text-xs">
                        <option value="15" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">15/trang</option>
                        <option value="50" selected class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">50/trang</option>
                        <option value="100" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">100/trang</option>
                        <option value="all" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Tất cả</option>
                    </select>
                </div>

                <!-- Dropdown Tự Động Ẩn Thanh Điều Hướng (30s, 60s, 120s, 5 phút, Không ẩn) -->
                <div class="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-lg text-xs shrink-0" title="Tùy chọn tự động thu nhỏ thanh điều hướng">
                    <i class="fa-solid fa-clock text-amber-500 text-[10px]"></i>
                    <span class="text-slate-500 dark:text-slate-400 text-[11px] font-medium">Ẩn:</span>
                    <select id="select-autohide-time" onchange="changeAutoHideTime(this.value)" class="bg-transparent text-slate-800 dark:text-slate-100 font-bold outline-none cursor-pointer text-xs">
                        <option value="30" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">30s</option>
                        <option value="60" selected class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">60s</option>
                        <option value="120" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">120s</option>
                        <option value="300" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">5 phút</option>
                        <option value="0" class="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Không ẩn</option>
                    </select>
                </div>

                <!-- Dark / Light Mode -->
                <button type="button" onclick="toggleDarkMode()" id="btn-darkmode" class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 flex items-center justify-center transition cursor-pointer" title="Chuyển chế độ Sáng / Tối">
                    <i class="fa-solid fa-moon text-xs dark:hidden"></i>
                    <i class="fa-solid fa-sun text-xs hidden dark:block text-amber-400"></i>
                </button>
            </div>
        </div>

        <!-- CATEGORY PILLS BAR -->
        <div class="max-w-[1920px] mx-auto mt-2 pt-1.5 border-t border-slate-200/80 dark:border-slate-800 flex items-center gap-1.5 overflow-x-auto custom-scrollbar pb-0.5">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
                <i class="fa-solid fa-filter text-[9px]"></i> Phân Loại:
            </span>
            <div id="category-pills" class="flex items-center gap-1.5 shrink-0">
                <!-- Injected via JS -->
            </div>
        </div>
    </header>

    <!-- MAIN BODY 2-COLUMN LAYOUT -->
    <main class="flex-1 flex overflow-hidden max-w-[1920px] w-full mx-auto p-2.5 sm:p-3.5 gap-2.5 h-[calc(100vh-95px)]">
        
        <!-- LEFT ICON RAIL (Narrow 56px mode) -->
        <nav id="left-icon-rail" class="hidden w-14 shrink-0 flex flex-col items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs py-2.5 space-y-2 overflow-y-auto custom-scrollbar transition-all">
            <button type="button" onclick="setSidebarMode('expanded')" class="w-9 h-9 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-600 hover:text-white flex items-center justify-center transition text-xs cursor-pointer" title="Mở rộng danh sách">
                <i class="fa-solid fa-angles-right"></i>
            </button>
            <div class="w-8 border-t border-slate-200 dark:border-slate-800 my-1"></div>
            <div id="rail-icons-container" class="space-y-1.5 flex flex-col items-center w-full px-1">
                <!-- Injected via JS -->
            </div>
        </nav>

        <!-- LEFT SIDEBAR: Document List & Search (Full 340px mode) -->
        <aside id="left-sidebar" class="w-full md:w-[340px] lg:w-[380px] shrink-0 flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden transition-all duration-300">
            
            <!-- Search & Filter Controls -->
            <div class="p-2.5 border-b border-slate-200 dark:border-slate-800 space-y-1.5 bg-slate-50 dark:bg-slate-900/90">
                <div class="relative">
                    <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
                    <input 
                        type="text" 
                        id="search-input" 
                        oninput="handleSearch(this.value)" 
                        placeholder="Tìm kiếm tài liệu, mã nguồn (Nhấn /)..." 
                        class="w-full pl-8 pr-7 py-1.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs outline-none focus:border-indigo-500 dark:focus:border-indigo-400 text-slate-800 dark:text-slate-100 placeholder-slate-400 transition"
                    >
                    <button type="button" onclick="clearSearch()" id="btn-clear-search" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hidden cursor-pointer">
                        <i class="fa-solid fa-xmark text-xs"></i>
                    </button>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 px-0.5">
                    <span id="items-counter">Hiển thị mục</span>
                    <button type="button" onclick="resetFilters()" class="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">Đặt lại lọc</button>
                </div>
                <!-- Sắp Xếp: Mới nhất (Mặc định), Cũ nhất, Ngẫu nhiên -->
                <div class="flex items-center justify-between gap-1.5 pt-1 border-t border-slate-200/80 dark:border-slate-800/80 text-[11px]">
                    <div class="flex items-center gap-1.5 min-w-0">
                        <i class="fa-solid fa-arrow-down-short-wide text-[10px] text-indigo-500 shrink-0"></i>
                        <span class="text-[10px] font-semibold text-slate-500 dark:text-slate-400 shrink-0">Sắp xếp:</span>
                        <select 
                            id="select-sort-order" 
                            onchange="changeSortOrder(this.value)" 
                            class="bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5 text-[11px] font-medium outline-none cursor-pointer focus:border-indigo-500 truncate"
                        >
                            <option value="newest" selected>Mới nhất (Mặc định)</option>
                            <option value="oldest">Cũ nhất</option>
                            <option value="random">Ngẫu nhiên</option>
                        </select>
                    </div>
                    <button type="button" id="btn-shuffle-random" onclick="shuffleRandomOrder()" class="hidden text-amber-600 dark:text-amber-400 hover:text-amber-500 text-[10px] items-center gap-1 cursor-pointer font-medium px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 shrink-0 transition" title="Xáo trộn lại ngẫu nhiên">
                        <i class="fa-solid fa-dice"></i> Xáo lại
                    </button>
                </div>
            </div>

            <!-- Documents List Container -->
            <div id="items-list-container" class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1.5">
                <!-- Injected via JS -->
            </div>
        </aside>

        <!-- RIGHT PANE: Document Detail Viewer -->
        <section class="flex-1 flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden min-w-0 relative">
            
            <!-- Detail Toolbar & Header -->
            <div id="detail-header" class="px-3.5 sm:px-5 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/90 flex flex-wrap items-center justify-between gap-2 shrink-0">
                <div class="flex items-center gap-2 flex-wrap min-w-0">
                    <span id="doc-id-badge" class="font-mono text-[10px] font-bold text-amber-600 dark:text-amber-400 px-2 py-0.5 bg-amber-500/10 rounded-md border border-amber-500/20">
                        KB-001
                    </span>
                    <span id="doc-version-badge" class="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                        {version_str}
                    </span>
                    <span id="doc-category-badge" class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 flex items-center gap-1">
                        <i class="fa-solid fa-tag text-[9px]"></i>
                        <span id="doc-category-text">Chuyên Mục</span>
                    </span>
                </div>

                <!-- Action Buttons -->
                <div class="flex items-center gap-1 shrink-0">
                    <button type="button" onclick="togglePathInfoPanel()" id="btn-toggle-path-info" class="px-2 py-0.8 text-xs font-semibold rounded-lg bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/60 transition flex items-center gap-1 cursor-pointer" title="Ẩn/Hiện Khung Tệp">
                        <i class="fa-solid fa-code-fork text-indigo-500 text-[10px]"></i>
                        <span id="txt-toggle-path">Khung Tệp (Bật)</span>
                    </button>

                    <button type="button" onclick="toggleRawView()" id="btn-toggle-raw" class="px-2 py-0.8 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition flex items-center gap-1 cursor-pointer">
                        <i class="fa-solid fa-file-code text-indigo-500 text-[10px]"></i>
                        <span id="toggle-raw-text">Xem File .MD</span>
                    </button>

                    <button type="button" onclick="copyCurrentMarkdown()" class="px-2 py-0.8 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition flex items-center gap-1 cursor-pointer" title="Sao chép toàn bộ">
                        <i class="fa-solid fa-copy text-[10px]"></i>
                        <span>Sao Chép</span>
                    </button>
                </div>
            </div>

            <!-- DYNAMIC TECH PATH & URL INFO PANEL -->
            <div id="path-info-panel-container">
                <!-- Injected / Toggled via JS -->
            </div>

            <!-- Document Title & Tags Bar -->
            <div class="px-3.5 sm:px-5 py-2.5 bg-slate-50 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800 shrink-0">
                <h2 id="doc-main-title" class="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug">
                    Tên Tài Liệu
                </h2>
                <div id="doc-tags-container" class="flex items-center gap-1 flex-wrap mt-1.5">
                    <!-- Injected via JS -->
                </div>
            </div>

            <!-- Scrollable Content View Area -->
            <div id="doc-content-container" class="flex-1 overflow-y-auto custom-scrollbar p-3.5 sm:p-5 lg:p-6 relative">
                <div id="content-view-wrapper">
                    <!-- Rendered by JS -->
                </div>

                <div class="max-w-4xl mx-auto mt-8 pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
                    <button type="button" onclick="navigateDoc(-1)" id="btn-prev-doc" class="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer">
                        <i class="fa-solid fa-arrow-left text-[10px]"></i>
                        <span>Mục Trước</span>
                    </button>
                    <span id="doc-index-indicator" class="text-xs font-medium text-slate-400">1 / 1</span>
                    <button type="button" onclick="navigateDoc(1)" id="btn-next-doc" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-xs cursor-pointer">
                        <span>Mục Sau</span>
                        <i class="fa-solid fa-arrow-right text-[10px]"></i>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- QUICK NAVIGATION EXPANDABLE FLOATING DOCK -->
    <div id="quick-nav-dock" onmouseenter="resetQuickNavIdleTimer()">
        <div id="quick-nav-menu" class="dock-pill-menu flex flex-col items-center gap-1.5 scale-100 opacity-100 transition-all duration-200">
            <button type="button" onclick="openMasterTocModal(); resetQuickNavIdleTimer();" class="dock-btn bg-gradient-to-tr from-amber-500 to-orange-500 text-white shadow-xs" title="Mục Lục Toàn Cảnh">
                <i class="fa-solid fa-folder-tree text-sm"></i>
            </button>

            <button type="button" 
                onclick="handleScrollBtnClick('top')" 
                onmousedown="startHoldScroll('up')" 
                onmouseup="stopHoldScroll()" 
                onmouseleave="stopHoldScroll()"
                ontouchstart="startHoldScroll('up')" 
                ontouchend="stopHoldScroll()"
                class="dock-btn bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 hover:bg-indigo-600 hover:text-white" 
                title="Cuộn lên đầu trang (Nhấn hoặc Giữ để cuộn)">
                <i class="fa-solid fa-angles-up text-sm"></i>
            </button>

            <button type="button" 
                onclick="handleScrollBtnClick('middle')" 
                class="dock-btn bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 hover:bg-indigo-600 hover:text-white" 
                title="Cuộn vào giữa trang">
                <i class="fa-solid fa-arrows-up-down text-sm"></i>
            </button>

            <button type="button" 
                onclick="handleScrollBtnClick('bottom')" 
                onmousedown="startHoldScroll('down')" 
                onmouseup="stopHoldScroll()" 
                onmouseleave="stopHoldScroll()"
                ontouchstart="startHoldScroll('down')" 
                ontouchend="stopHoldScroll()"
                class="dock-btn bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 hover:bg-indigo-600 hover:text-white" 
                title="Cuộn xuống cuối trang (Nhấn hoặc Giữ để cuộn)">
                <i class="fa-solid fa-angles-down text-sm"></i>
            </button>
        </div>

        <button type="button" id="btn-quick-nav-toggle" onclick="toggleQuickNavDock()" class="dock-trigger-btn" title="Điều Hướng & Mục Lục">
            <i id="quick-nav-icon" class="fa-solid fa-xmark text-base transition-transform duration-300"></i>
        </button>
    </div>

    <!-- MASTER TOC MODAL -->
    <div id="modal-master-toc" class="fixed inset-0 z-50 bg-slate-950/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 hidden">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl w-full max-w-4xl max-h-[88vh] flex flex-col shadow-2xl overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center text-xs font-bold">
                        <i class="fa-solid fa-folder-tree"></i>
                    </div>
                    <div>
                        <h3 class="font-bold text-slate-900 dark:text-white text-sm">Mục Lục Toàn Cảnh Dự Án & Phân Loại Layout</h3>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400">Tổng hợp danh mục tài liệu phân tích kỹ thuật</p>
                    </div>
                </div>
                <button type="button" onclick="closeMasterTocModal()" class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center cursor-pointer">
                    <i class="fa-solid fa-xmark text-xs"></i>
                </button>
            </div>

            <div id="master-toc-grid" class="p-4 overflow-y-auto custom-scrollbar flex-1 space-y-4">
            </div>

            <div class="px-4 py-2.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between text-xs text-slate-500">
                <span class="text-[11px]">Nhấn vào bất kỳ mục nào để xem ngay</span>
                <button type="button" onclick="closeMasterTocModal()" class="px-3 py-1 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold hover:bg-slate-300 dark:hover:bg-slate-700 transition cursor-pointer text-xs">Đóng</button>
            </div>
        </div>
    </div>

    <!-- TOAST NOTIFICATION -->
    <div id="toast" class="fixed bottom-4 left-1/2 -translate-x-1/2 sm:left-auto sm:translate-x-0 sm:right-4 z-50 transform translate-y-12 opacity-0 pointer-events-none transition-all duration-300 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3.5 py-2 rounded-lg shadow-xl flex items-center gap-2 text-xs font-semibold">
        <i id="toast-icon" class="fa-solid fa-circle-check text-emerald-400 dark:text-emerald-600 text-xs"></i>
        <span id="toast-msg">Thông báo</span>
    </div>

    <script id="embedded-dataset" type="application/json">
{dataset_json_str}
    </script>

    <script>
        let appData = null;
        let activeCategoryId = 'all';
        let activeTag = null;
        let searchQuery = '';
        let currentItemIndex = 0;
        let isRawView = false;
        let sidebarMode = 'expanded';
        let isPathInfoVisible = true;
        let isQuickNavOpen = true;
        let autoHideSeconds = 60;
        let quickNavIdleTimer = null;
        let holdScrollTimer = null;
        let holdScrollActive = false;
        let currentSortMode = 'newest'; // 'newest' (Mặc định) | 'oldest' | 'random'
        let randomSeedMap = new Map();

        const renderer = new marked.Renderer();
        renderer.code = function(tokenOrCode, language) {{
            let codeText = '';
            let lang = 'plaintext';
            if (typeof tokenOrCode === 'object' && tokenOrCode !== null) {{
                codeText = tokenOrCode.text || tokenOrCode.raw || '';
                lang = tokenOrCode.lang || language || 'plaintext';
            }} else {{
                codeText = typeof tokenOrCode === 'string' ? tokenOrCode : '';
                lang = language || 'plaintext';
            }}

            lang = (lang || '').trim();
            if (!lang) lang = 'plaintext';

            let highlighted = '';
            try {{
                if (typeof hljs !== 'undefined' && hljs.getLanguage(lang)) {{
                    highlighted = hljs.highlight(codeText, {{ language: lang }}).value;
                }} else if (typeof hljs !== 'undefined') {{
                    highlighted = hljs.highlightAuto(codeText).value;
                }} else {{
                    highlighted = escapeHtml(codeText);
                }}
            }} catch (e) {{
                highlighted = escapeHtml(codeText);
            }}

            return `
                <div class="code-container group">
                    <button type="button" onclick="copyCodeSnippet(this)" class="copy-code-btn bg-slate-700/80 hover:bg-slate-600 text-slate-200 border border-slate-600/60 shadow-xs cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity">
                        <i class="fa-solid fa-copy mr-1 text-[9px]"></i>Copy
                    </button>
                    <pre><code class="hljs language-${{lang}}">${{highlighted}}</code></pre>
                </div>
            `;
        }};

        marked.use({{
            gfm: true,
            breaks: true,
            renderer: renderer
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            const savedTheme = localStorage.getItem('hub_theme') || 'dark';
            if (savedTheme === 'light') {{
                document.documentElement.classList.remove('dark');
            }} else {{
                document.documentElement.classList.add('dark');
            }}

            const savedMode = localStorage.getItem('hub_sidebar_mode') || 'expanded';
            setSidebarMode(savedMode);

            const savedAutoHide = localStorage.getItem('hub_autohide') || '60';
            autoHideSeconds = parseInt(savedAutoHide, 10);
            const selectEl = document.getElementById('select-autohide-time');
            if (selectEl) selectEl.value = savedAutoHide;

            // Load and apply saved Sort Order (Default: 'newest')
            const savedSort = localStorage.getItem('log_hub_sort_order') || 'newest';
            currentSortMode = savedSort;
            const sortSelect = document.getElementById('select-sort-order');
            if (sortSelect) sortSelect.value = savedSort;
            const shuffleBtn = document.getElementById('btn-shuffle-random');
            if (shuffleBtn) {{
                shuffleBtn.classList.toggle('hidden', savedSort !== 'random');
                shuffleBtn.classList.toggle('inline-flex', savedSort === 'random');
            }}

            loadDataset();
            initQuickNavDock();

            window.addEventListener('keydown', (e) => {{
                if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{
                    e.preventDefault();
                    if (sidebarMode === 'hidden' || sidebarMode === 'rail') {{
                        setSidebarMode('expanded');
                    }}
                    document.getElementById('search-input').focus();
                }}
            }});

            window.addEventListener('hashchange', () => {{
                handleHashRoute();
            }});
        }});

        function loadDataset() {{
            try {{
                const embedded = document.getElementById('embedded-dataset').textContent;
                appData = JSON.parse(embedded);
                appData.items.forEach((item, idx) => {{
                    item._origIndex = idx;
                }});
                if (currentSortMode === 'random') {{
                    regenerateRandomSeeds();
                }}
                initUI();
            }} catch (err) {{
                console.error("Failed to parse dataset:", err);
            }}
        }}

        function initUI() {{
            renderCategoryPills();
            renderItemsList();
            renderRailIcons();
            renderMasterToc();

            if (window.location.hash) {{
                handleHashRoute();
            }} else if (appData.items.length > 0) {{
                const filtered = getFilteredItems();
                if (filtered.length > 0) {{
                    const firstRealIndex = appData.items.findIndex(i => i.id === filtered[0].id);
                    selectItem(firstRealIndex !== -1 ? firstRealIndex : 0);
                }} else {{
                    selectItem(0);
                }}
            }}
        }}

        function handleHashRoute() {{
            const hash = window.location.hash.replace('#', '');
            if (!hash || !appData) return;
            const idx = appData.items.findIndex(item => item.id === hash || item.file.includes(hash));
            if (idx !== -1) {{
                selectItem(idx);
            }}
        }}

        function initQuickNavDock() {{
            resetQuickNavIdleTimer();
        }}

        function toggleQuickNavDock(forceState) {{
            const menu = document.getElementById('quick-nav-menu');
            const icon = document.getElementById('quick-nav-icon');
            const btn = document.getElementById('btn-quick-nav-toggle');
            if (!menu || !icon || !btn) return;

            resetQuickNavIdleTimer();

            if (typeof forceState === 'boolean') isQuickNavOpen = forceState;
            else isQuickNavOpen = !isQuickNavOpen;

            if (isQuickNavOpen) {{
                menu.classList.remove('hidden', 'scale-90', 'opacity-0');
                menu.classList.add('flex', 'scale-100', 'opacity-100');
                icon.className = 'fa-solid fa-xmark text-base transition-transform duration-300';
            }} else {{
                menu.classList.remove('scale-100', 'opacity-100');
                menu.classList.add('scale-90', 'opacity-0');
                setTimeout(() => {{
                    if (!isQuickNavOpen) {{
                        menu.classList.add('hidden');
                        menu.classList.remove('flex');
                    }}
                }}, 180);
                icon.className = 'fa-solid fa-compass text-lg transition-transform duration-300';
            }}
        }}

        function resetQuickNavIdleTimer() {{
            if (quickNavIdleTimer) clearTimeout(quickNavIdleTimer);
            if (autoHideSeconds > 0) {{
                quickNavIdleTimer = setTimeout(() => {{
                    toggleQuickNavDock(false);
                }}, autoHideSeconds * 1000);
            }}
        }}

        function changeAutoHideTime(val) {{
            autoHideSeconds = parseInt(val, 10);
            localStorage.setItem('hub_autohide', val);
            resetQuickNavIdleTimer();
            showToast(autoHideSeconds > 0 ? `Tự động ẩn sau ${{autoHideSeconds}}s` : "Đã tắt tự động ẩn", "fa-clock");
        }}

        function changeItemsPerPage(val) {{
            showToast(`Hiển thị ${{val}} mục/trang`, "fa-layer-group");
        }}

        function getScrollableContainer() {{
            return document.getElementById('doc-content-container') || document.documentElement || document.body;
        }}

        function scrollDocContent(position) {{
            const container = document.getElementById('doc-content-container');
            const targets = [container, document.documentElement, document.body].filter(Boolean);

            targets.forEach(el => {{
                try {{
                    const scrollHeight = el.scrollHeight;
                    const clientHeight = el.clientHeight;
                    const maxScroll = Math.max(0, scrollHeight - clientHeight);
                    let targetTop = 0;

                    if (position === 'top') {{
                        targetTop = 0;
                    }} else if (position === 'middle') {{
                        targetTop = maxScroll > 0 ? maxScroll / 2 : 0;
                    }} else if (position === 'bottom') {{
                        targetTop = scrollHeight;
                    }}

                    el.scrollTo({{ top: targetTop, behavior: 'smooth' }});
                }} catch (e) {{
                    if (position === 'top') el.scrollTop = 0;
                    else if (position === 'middle') el.scrollTop = el.scrollHeight / 2;
                    else if (position === 'bottom') el.scrollTop = el.scrollHeight;
                }}
            }});

            try {{
                if (position === 'top') {{
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                    showToast("Đã cuộn lên đầu trang", "fa-angles-up");
                }} else if (position === 'middle') {{
                    const total = document.documentElement.scrollHeight - window.innerHeight;
                    window.scrollTo({{ top: total > 0 ? total / 2 : 0, behavior: 'smooth' }});
                    showToast("Đã cuộn vào giữa trang", "fa-arrows-up-down");
                }} else if (position === 'bottom') {{
                    window.scrollTo({{ top: document.documentElement.scrollHeight, behavior: 'smooth' }});
                    showToast("Đã cuộn xuống cuối trang", "fa-angles-down");
                }}
            }} catch (err) {{}}
        }}

        function handleScrollBtnClick(position) {{
            resetQuickNavIdleTimer();
            if (!holdScrollActive) {{
                scrollDocContent(position);
            }}
        }}

        function startHoldScroll(direction) {{
            resetQuickNavIdleTimer();
            stopHoldScroll();
            holdScrollActive = false;

            holdScrollTimer = setTimeout(() => {{
                holdScrollActive = true;
                const container = getScrollableContainer();
                const step = direction === 'up' ? -28 : 28;

                const scrollLoop = () => {{
                    if (!holdScrollActive) return;
                    if (container) {{
                        container.scrollTop += step;
                    }}
                    window.scrollBy(0, step);
                    requestAnimationFrame(scrollLoop);
                }};
                requestAnimationFrame(scrollLoop);
            }}, 180);
        }}

        function stopHoldScroll() {{
            if (holdScrollTimer) {{
                clearTimeout(holdScrollTimer);
                holdScrollTimer = null;
            }}
            setTimeout(() => {{
                holdScrollActive = false;
            }}, 50);
        }}

        function setSidebarMode(mode) {{
            sidebarMode = mode;
            localStorage.setItem('hub_sidebar_mode', mode);

            const sidebar = document.getElementById('left-sidebar');
            const rail = document.getElementById('left-icon-rail');

            const btnExp = document.getElementById('btn-mode-expanded');
            const btnRail = document.getElementById('btn-mode-rail');
            const btnHid = document.getElementById('btn-mode-hidden');

            [btnExp, btnRail, btnHid].forEach(b => {{
                if (b) {{
                    b.className = 'px-2 py-1 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition cursor-pointer';
                }}
            }});

            if (mode === 'expanded') {{
                sidebar.classList.remove('hidden');
                rail.classList.add('hidden');
                if (btnExp) btnExp.className = 'px-2 py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-2xs transition cursor-pointer';
            }} else if (mode === 'rail') {{
                sidebar.classList.add('hidden');
                rail.classList.remove('hidden');
                if (btnRail) btnRail.className = 'px-2 py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-2xs transition cursor-pointer';
            }} else {{
                sidebar.classList.add('hidden');
                rail.classList.add('hidden');
                if (btnHid) btnHid.className = 'px-2 py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-700 text-rose-600 dark:text-rose-400 shadow-2xs transition cursor-pointer';
            }}
        }}

        function renderCategoryPills() {{
            const container = document.getElementById('category-pills');
            container.innerHTML = '';

            appData.categories.forEach(cat => {{
                const count = cat.id === 'all' 
                    ? appData.items.length 
                    : appData.items.filter(i => i.category === cat.id).length;

                const isActive = activeCategoryId === cat.id;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `px-2 py-0.8 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer shrink-0 ${{
                    isActive 
                        ? 'bg-indigo-600 text-white shadow-xs' 
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
                }}`;
                btn.innerHTML = `<i class="${{cat.icon}} text-[10px]"></i><span>${{cat.name}}</span><span class="px-1.5 py-0.2 rounded-full text-[10px] ${{isActive ? 'bg-indigo-800 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'}} font-mono">${{count}}</span>`;
                btn.onclick = () => {{
                    activeCategoryId = cat.id;
                    renderCategoryPills();
                    renderItemsList();
                }};
                container.appendChild(btn);
            }});
        }}

        function renderRailIcons() {{
            const container = document.getElementById('rail-icons-container');
            if (!container) return;
            container.innerHTML = '';

            const itemsToRender = getFilteredItems();
            itemsToRender.forEach(item => {{
                const realIndex = appData.items.findIndex(i => i.id === item.id);
                const isSelected = realIndex === currentItemIndex;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `w-9 h-9 rounded-lg flex items-center justify-center text-xs transition cursor-pointer relative group ${{
                    isSelected 
                        ? 'bg-indigo-600 text-white shadow-xs' 
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-slate-700 hover:text-indigo-600'
                }}`;
                btn.title = `${{item.id}}: ${{item.title}}`;
                btn.innerHTML = `<i class="${{item.icon}}"></i>`;
                btn.onclick = () => selectItem(realIndex);
                container.appendChild(btn);
            }});
        }}

        function getFilteredItems() {{
            if (!appData || !appData.items) return [];

            let filtered = appData.items.filter(item => {{
                if (activeCategoryId !== 'all' && item.category !== activeCategoryId) {{
                    return false;
                }}
                if (activeTag && !item.tags.includes(activeTag)) {{
                    return false;
                }}
                if (searchQuery) {{
                    const q = searchQuery.toLowerCase();
                    const matchTitle = item.title.toLowerCase().includes(q);
                    const matchId = item.id.toLowerCase().includes(q);
                    const matchSummary = item.summary.toLowerCase().includes(q);
                    const matchTags = item.tags.some(t => t.toLowerCase().includes(q));
                    const matchContent = item.content.toLowerCase().includes(q);
                    return matchTitle || matchId || matchSummary || matchTags || matchContent;
                }}
                return true;
            }});

            // Sorting Modes: Newest (Mặc định), Oldest, Random
            if (currentSortMode === 'newest') {{
                // Mới nhất: thứ tự đảo ngược chỉ số tạo ban đầu (_origIndex giảm dần)
                filtered.sort((a, b) => (b._origIndex ?? 0) - (a._origIndex ?? 0));
            }} else if (currentSortMode === 'oldest') {{
                // Cũ nhất: theo đúng chỉ số tạo ban đầu (_origIndex tăng dần)
                filtered.sort((a, b) => (a._origIndex ?? 0) - (b._origIndex ?? 0));
            }} else if (currentSortMode === 'random') {{
                // Ngẫu nhiên: dựa trên seed ngẫu nhiên ổn định trong phiên
                filtered.sort((a, b) => {{
                    const scoreA = randomSeedMap.has(a.id) ? randomSeedMap.get(a.id) : 0;
                    const scoreB = randomSeedMap.has(b.id) ? randomSeedMap.get(b.id) : 0;
                    return scoreA - scoreB;
                }});
            }}

            return filtered;
        }}

        function changeSortOrder(mode) {{
            currentSortMode = mode;
            localStorage.setItem('log_hub_sort_order', mode);

            const shuffleBtn = document.getElementById('btn-shuffle-random');
            if (shuffleBtn) {{
                shuffleBtn.classList.toggle('hidden', mode !== 'random');
                shuffleBtn.classList.toggle('inline-flex', mode === 'random');
            }}

            if (mode === 'random') {{
                regenerateRandomSeeds();
                showToast("Đã sắp xếp ngẫu nhiên (Random)", "fa-dice");
            }} else if (mode === 'oldest') {{
                showToast("Đã sắp xếp theo cũ nhất", "fa-arrow-up-wide-short");
            }} else {{
                showToast("Đã sắp xếp theo mới nhất (Mặc định)", "fa-arrow-down-short-wide");
            }}

            renderItemsList();
            renderRailIcons();

            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
        }}

        function shuffleRandomOrder() {{
            if (currentSortMode !== 'random') {{
                currentSortMode = 'random';
                const sortSelect = document.getElementById('select-sort-order');
                if (sortSelect) sortSelect.value = 'random';
                localStorage.setItem('log_hub_sort_order', 'random');
            }}
            regenerateRandomSeeds();
            showToast("Đã xáo trộn lại ngẫu nhiên", "fa-dice");
            renderItemsList();
            renderRailIcons();
            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
        }}

        function regenerateRandomSeeds() {{
            randomSeedMap.clear();
            if (!appData || !appData.items) return;
            const ids = appData.items.map(i => i.id);
            for (let i = ids.length - 1; i > 0; i--) {{
                const j = Math.floor(Math.random() * (i + 1));
                [ids[i], ids[j]] = [ids[j], ids[i]];
            }}
            ids.forEach((id, idx) => {{
                randomSeedMap.set(id, idx);
            }});
        }}

        function updateDocNavigationState(item) {{
            if (!item) return;
            const filtered = getFilteredItems();
            const currentPos = filtered.findIndex(i => i.id === item.id);
            const displayPos = currentPos !== -1 ? (currentPos + 1) : 1;
            const indicator = document.getElementById('doc-index-indicator');
            if (indicator) {{
                indicator.textContent = `${{displayPos}} / ${{filtered.length}}`;
            }}

            const hasPrev = currentPos > 0;
            const hasNext = currentPos !== -1 && currentPos < filtered.length - 1;

            const btnPrev = document.getElementById('btn-prev-doc');
            const btnNext = document.getElementById('btn-next-doc');
            if (btnPrev) {{
                btnPrev.disabled = !hasPrev;
                btnPrev.classList.toggle('opacity-50', !hasPrev);
            }}
            if (btnNext) {{
                btnNext.disabled = !hasNext;
                btnNext.classList.toggle('opacity-50', !hasNext);
            }}
        }}

        function renderItemsList() {{
            const container = document.getElementById('items-list-container');
            container.innerHTML = '';

            const filtered = getFilteredItems();
            document.getElementById('items-counter').textContent = `Hiển thị ${{filtered.length}} / ${{appData.items.length}} mục`;

            if (filtered.length === 0) {{
                container.innerHTML = `
                    <div class="p-6 text-center text-slate-400 dark:text-slate-500">
                        <i class="fa-solid fa-magnifying-glass text-2xl mb-1.5 text-slate-300 dark:text-slate-600"></i>
                        <p class="text-xs">Không tìm thấy tài liệu phù hợp</p>
                        <button type="button" onclick="resetFilters()" class="mt-2.5 px-2.5 py-1 bg-indigo-600 text-white rounded-md text-xs font-semibold cursor-pointer">Xóa bộ lọc</button>
                    </div>
                `;
                return;
            }}

            filtered.forEach(item => {{
                const realIndex = appData.items.findIndex(i => i.id === item.id);
                const isSelected = realIndex === currentItemIndex;

                const card = document.createElement('div');
                card.className = `sidebar-card p-2.5 rounded-lg border cursor-pointer group shadow-2xs ${{
                    isSelected ? 'sidebar-card-active' : 'sidebar-card-default'
                }}`;
                card.onclick = () => selectItem(realIndex);

                const tagsHtml = item.tags.slice(0, 3).map(t => 
                    `<span class="px-1.5 py-0.2 rounded text-[9px] font-medium bg-slate-100 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">${{t}}</span>`
                ).join('');

                card.innerHTML = `
                    <div class="flex items-start gap-2">
                        <div class="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5">
                            <i class="${{item.icon}}"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center justify-between gap-1 mb-0.5">
                                <span class="font-mono text-[10px] font-bold text-amber-500">${{item.id}}</span>
                                <span class="text-[9px] text-slate-400 truncate">${{item.category_name}}</span>
                            </div>
                            <h4 class="text-xs font-semibold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-1 leading-snug">
                                ${{item.title}}
                            </h4>
                            <p class="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                                ${{item.summary}}
                            </p>
                            <div class="flex items-center gap-1 mt-1.5 flex-wrap">
                                ${{tagsHtml}}
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            }});
        }}

        function selectItem(index) {{
            if (index < 0 || index >= appData.items.length) return;
            currentItemIndex = index;
            const item = appData.items[index];

            history.replaceState(null, null, '#' + item.id);

            document.getElementById('doc-category-text').textContent = item.category_name;
            document.getElementById('doc-id-badge').textContent = item.id;
            document.getElementById('doc-main-title').textContent = item.title;

            updateDocNavigationState(item);
            renderPathInfoPanel(item);

            const tagsContainer = document.getElementById('doc-tags-container');
            tagsContainer.innerHTML = item.tags.map(t => 
                `<button type="button" onclick="filterByTag('${{t}}')" class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition cursor-pointer border border-slate-200 dark:border-slate-700">#${{t}}</button>`
            ).join('');

            renderMainContent(item);

            renderItemsList();
            renderRailIcons();
            document.getElementById('doc-content-container').scrollTop = 0;
        }}

        function getRelativeFilePath(itemFile) {{
            return itemFile;
        }}

        function renderPathInfoPanel(item) {{
            const container = document.getElementById('path-info-panel-container');
            if (!container) return;

            if (!isPathInfoVisible) {{
                container.innerHTML = '';
                return;
            }}

            const relPath = getRelativeFilePath(item.file);
            const routeHash = `#${{item.id}}`;

            container.innerHTML = `
                <div class="px-3.5 sm:px-5 py-3 bg-slate-100/90 dark:bg-slate-950/80 text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800 text-[11px] space-y-2.5 transition-colors duration-200">
                    <div class="flex items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800/80 pb-2">
                        <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                            <i class="fa-solid fa-layer-group text-indigo-500"></i>
                            <span>Kiến Trúc & Tệp Nguồn Áp Dụng (MVC)</span>
                            <span class="px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-[10px] text-slate-600 dark:text-slate-400 font-mono">1 Tệp</span>
                        </div>
                        <button type="button" onclick="copyText('${{relPath}}', 'Đã chép đường dẫn tệp tương đối!')" class="px-2 py-0.5 rounded bg-white dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-[10px] font-medium transition cursor-pointer flex items-center gap-1 shadow-2xs">
                            <i class="fa-solid fa-copy text-[9px]"></i>Chép Đường Dẫn
                        </button>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
                        <div class="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-1.5 shadow-2xs">
                            <div class="min-w-0">
                                <div class="text-[9px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1">
                                    <i class="fa-solid fa-cube"></i> CHUYÊN MỤC
                                </div>
                                <div class="font-mono text-[10px] text-slate-700 dark:text-slate-300 truncate mt-0.5">${{item.category_name}}</div>
                            </div>
                            <button type="button" onclick="copyText('${{item.category_name}}', 'Đã chép chuyên mục!')" class="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 flex items-center justify-center text-[10px] shrink-0 cursor-pointer" title="Chép">
                                <i class="fa-solid fa-copy"></i>
                            </button>
                        </div>

                        <div class="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-1.5 shadow-2xs">
                            <div class="min-w-0">
                                <div class="text-[9px] font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
                                    <i class="fa-solid fa-table-columns"></i> TỆP NGUỒN MD
                                </div>
                                <div class="font-mono text-[10px] text-slate-700 dark:text-slate-300 truncate mt-0.5">${{item.file}}</div>
                            </div>
                            <button type="button" onclick="copyText('${{item.file}}', 'Đã chép tên tệp!')" class="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 flex items-center justify-center text-[10px] shrink-0 cursor-pointer" title="Chép">
                                <i class="fa-solid fa-copy"></i>
                            </button>
                        </div>

                        <div class="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-1.5 shadow-2xs">
                            <div class="min-w-0">
                                <div class="text-[9px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                    <i class="fa-solid fa-route"></i> ROUTER / HASH
                                </div>
                                <div class="font-mono text-[10px] text-slate-700 dark:text-slate-300 truncate mt-0.5">${{routeHash}}</div>
                            </div>
                            <button type="button" onclick="copyText(window.location.origin + window.location.pathname + '${{routeHash}}', 'Đã chép URL liên kết!')" class="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 flex items-center justify-center text-[10px] shrink-0 cursor-pointer" title="Chép">
                                <i class="fa-solid fa-copy"></i>
                            </button>
                        </div>
                    </div>

                    <div class="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2 shadow-2xs">
                        <div class="flex items-center gap-2 min-w-0 font-mono text-[11px]">
                            <span class="w-2 h-2 rounded-full bg-cyan-500 shrink-0"></span>
                            <span class="text-slate-600 dark:text-slate-300 truncate">${{relPath}}</span>
                        </div>
                        <div class="flex items-center gap-1 shrink-0">
                            <button type="button" onclick="copyText('${{relPath}}', 'Đã chép đường dẫn!')" class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px] font-bold transition cursor-pointer border border-slate-200 dark:border-slate-700">
                                Copy
                            </button>
                            <a href="${{relPath}}" target="_blank" class="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-bold transition flex items-center gap-1 cursor-pointer shadow-2xs">
                                <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>Mở
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }}

        function togglePathInfoPanel() {{
            isPathInfoVisible = !isPathInfoVisible;
            document.getElementById('txt-toggle-path').textContent = isPathInfoVisible ? 'Khung Tệp (Bật)' : 'Khung Tệp (Tắt)';
            const item = appData.items[currentItemIndex];
            if (item) renderPathInfoPanel(item);
            showToast(isPathInfoVisible ? 'Đã bật Khung Tệp' : 'Đã ẩn Khung Tệp', 'fa-code-fork');
        }}

        function renderMainContent(item) {{
            const wrapper = document.getElementById('content-view-wrapper');
            if (!wrapper) return;

            if (isRawView) {{
                wrapper.innerHTML = `
                    <div class="max-w-4xl mx-auto">
                        <div class="flex items-center justify-between mb-2 text-xs text-slate-500 dark:text-slate-400">
                            <span>Mã Nguồn Markdown Thô (${{item.file}})</span>
                            <button type="button" onclick="copyCurrentMarkdown()" class="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium">Sao chép</button>
                        </div>
                        <pre class="bg-slate-900 text-slate-100 p-3 rounded-lg text-xs font-mono overflow-x-auto border border-slate-800 custom-scrollbar"><code>${{escapeHtml(item.content)}}</code></pre>
                    </div>
                `;
            }} else {{
                let contentToRender = item.content.replace(/^---[\\s\\S]*?---\\n*/, '');
                wrapper.innerHTML = `
                    <div class="markdown-body max-w-4xl mx-auto">
                        ${{marked.parse(contentToRender)}}
                    </div>
                `;
            }}
        }}

        function toggleRawView() {{
            isRawView = !isRawView;
            document.getElementById('toggle-raw-text').textContent = isRawView ? 'Xem Giao Diện' : 'Xem File .MD';
            const item = appData.items[currentItemIndex];
            if (item) renderMainContent(item);
            showToast(isRawView ? 'Chế độ xem mã thô .MD' : 'Chế độ xem giao diện', isRawView ? 'fa-code' : 'fa-eye');
        }}

        function copyCurrentMarkdown() {{
            const item = appData.items[currentItemIndex];
            if (!item) return;
            copyText(item.content, "Đã sao chép toàn bộ Markdown!");
        }}

        function copyText(text, successMsg) {{
            navigator.clipboard.writeText(text).then(() => {{
                showToast(successMsg, "fa-copy");
            }}).catch(() => {{
                showToast("Lỗi sao chép", "fa-triangle-exclamation");
            }});
        }}

        function copyCodeSnippet(btn) {{
            const codeEl = btn.parentElement.querySelector('code');
            if (!codeEl) return;
            navigator.clipboard.writeText(codeEl.textContent).then(() => {{
                btn.innerHTML = '<i class="fa-solid fa-check mr-1 text-[9px] text-emerald-400"></i>Đã chép';
                setTimeout(() => {{
                    btn.innerHTML = '<i class="fa-solid fa-copy mr-1 text-[9px]"></i>Copy';
                }}, 2000);
            }});
        }}

        function navigateDoc(step) {{
            const filtered = getFilteredItems();
            if (!filtered || filtered.length === 0) return;
            const currentItem = appData.items[currentItemIndex];
            const currentPos = currentItem ? filtered.findIndex(i => i.id === currentItem.id) : -1;

            if (currentPos !== -1) {{
                const nextPos = currentPos + step;
                if (nextPos >= 0 && nextPos < filtered.length) {{
                    const targetRealIndex = appData.items.findIndex(i => i.id === filtered[nextPos].id);
                    if (targetRealIndex !== -1) selectItem(targetRealIndex);
                }}
            }} else {{
                const targetRealIndex = appData.items.findIndex(i => i.id === filtered[0].id);
                if (targetRealIndex !== -1) selectItem(targetRealIndex);
            }}
        }}

        function handleSearch(val) {{
            searchQuery = val.trim();
            document.getElementById('btn-clear-search').classList.toggle('hidden', searchQuery === '');
            renderItemsList();
            renderRailIcons();
            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
        }}

        function clearSearch() {{
            document.getElementById('search-input').value = '';
            searchQuery = '';
            document.getElementById('btn-clear-search').classList.add('hidden');
            renderItemsList();
            renderRailIcons();
            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
        }}

        function filterByTag(tag) {{
            activeTag = (activeTag === tag) ? null : tag;
            showToast(`Lọc theo thẻ #${{tag}}`, 'fa-filter');
            renderItemsList();
            renderRailIcons();
            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
        }}

        function resetFilters() {{
            activeCategoryId = 'all';
            activeTag = null;
            clearSearch();
            renderCategoryPills();
            renderItemsList();
            renderRailIcons();
            if (appData && appData.items[currentItemIndex]) {{
                updateDocNavigationState(appData.items[currentItemIndex]);
            }}
            showToast("Đã đặt lại toàn bộ bộ lọc", "fa-arrows-rotate");
        }}

        function toggleDarkMode() {{
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('hub_theme', isDark ? 'dark' : 'light');
            const item = appData.items[currentItemIndex];
            if (item) renderPathInfoPanel(item);
            renderItemsList();
            showToast(isDark ? 'Chế độ Tối' : 'Chế độ Sáng', isDark ? 'fa-moon' : 'fa-sun');
        }}

        function openMasterTocModal() {{
            document.getElementById('modal-master-toc').classList.remove('hidden');
        }}

        function closeMasterTocModal() {{
            document.getElementById('modal-master-toc').classList.add('hidden');
        }}

        function renderMasterToc() {{
            const container = document.getElementById('master-toc-grid');
            container.innerHTML = '';

            const groups = {{}};
            appData.items.forEach(item => {{
                if (!groups[item.category_name]) {{
                    groups[item.category_name] = [];
                }}
                groups[item.category_name].push(item);
            }});

            for (const [catName, list] of Object.entries(groups)) {{
                const groupEl = document.createElement('div');
                groupEl.className = 'bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-200 dark:border-slate-800';
                
                const itemsListHtml = list.map(item => {{
                    const realIndex = appData.items.findIndex(i => i.id === item.id);
                    return `
                        <div onclick="selectItemFromToc(${{realIndex}})" class="p-2 rounded-lg bg-white dark:bg-slate-900 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 border border-slate-200 dark:border-slate-700/60 transition cursor-pointer flex items-start gap-2 group shadow-2xs">
                            <div class="w-5 h-5 rounded bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                                <i class="${{item.icon}}"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between gap-1">
                                    <span class="font-mono text-[9px] font-bold text-amber-500">${{item.id}}</span>
                                </div>
                                <div class="text-xs font-semibold text-slate-800 dark:text-slate-100 group-hover:text-indigo-500 transition line-clamp-1">${{item.title}}</div>
                                <div class="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-1">${{item.summary}}</div>
                            </div>
                        </div>
                    `;
                }}).join('');

                groupEl.innerHTML = `
                    <h4 class="font-bold text-[11px] text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <i class="fa-solid fa-folder-open text-indigo-500 text-xs"></i>
                        <span>${{catName}}</span>
                        <span class="px-1.5 py-0.2 rounded-full text-[9px] bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-mono">${{list.length}}</span>
                    </h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                        ${{itemsListHtml}}
                    </div>
                `;
                container.appendChild(groupEl);
            }}
        }}

        function selectItemFromToc(index) {{
            closeMasterTocModal();
            selectItem(index);
        }}

        function showToast(msg, icon = 'fa-circle-check') {{
            const toast = document.getElementById('toast');
            document.getElementById('toast-msg').textContent = msg;
            document.getElementById('toast-icon').className = `fa-solid ${{icon}} text-emerald-400 dark:text-emerald-600 text-xs`;

            toast.classList.remove('translate-y-12', 'opacity-0', 'pointer-events-none');
            setTimeout(() => {{
                toast.classList.add('translate-y-12', 'opacity-0', 'pointer-events-none');
            }}, 2000);
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }}
    </script>
</body>
</html>
"""


def run_generator(source_path: str, output_dir: str, title: str, version: str):
    """Quy trình chính tạo Hub tài liệu hoàn chỉnh."""
    source_path = os.path.abspath(source_path)
    output_dir = os.path.abspath(output_dir)

    print("================================================================================")
    print("   UNIVERSAL KNOWLEDGE & UPDATEDONE HUB GENERATOR")
    print("================================================================================")
    print(f"[*] Nguồn đầu vào  : {source_path}")
    print(f"[*] Thư mục lưu    : {output_dir}")
    print(f"[*] Tên dự án      : {title}")
    print(f"[*] Phiên bản      : {version}")
    print("--------------------------------------------------------------------------------")

    items = parse_source_file_or_dir(source_path)
    print(f"[+] Đã trích xuất thành công {len(items)} tài liệu chuyên mục.")

    norm_output = os.path.normpath(output_dir)
    if norm_output.endswith(os.path.normpath(os.path.join(".agents", "updatedone"))):
        agents_dir = norm_output
    else:
        agents_dir = os.path.join(norm_output, ".agents", "updatedone")
    kb_out_dir = os.path.join(agents_dir, "knowledge")
    os.makedirs(kb_out_dir, exist_ok=True)

    for item in items:
        file_rel = item["file"].replace("/", os.sep)
        dest_file = os.path.join(agents_dir, file_rel)
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        with open(dest_file, "w", encoding="utf-8") as f:
            f.write(item["content"])
    print(f"[+] Đã ghi các tệp Markdown vào: {kb_out_dir}")

    cat_map = {"all": {"id": "all", "name": "Tất Cả", "icon": "fa-solid fa-border-all"}}
    for it in items:
        cid = it["category"]
        if cid not in cat_map:
            cat_map[cid] = {
                "id": cid,
                "name": it["category_name"],
                "icon": it["icon"]
            }

    categories = list(cat_map.values())

    dataset = {
        "version": version,
        "title": title,
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
        "categories": categories,
        "items": items
    }

    json_path = os.path.join(agents_dir, "changelog_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"[+] Đã tạo cơ sở dữ liệu: {json_path}")

    html_content = build_spa_html(dataset, title, version)

    agents_index = os.path.join(agents_dir, "index.html")
    with open(agents_index, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[+] Đã xuất bản giao diện SPA duy nhất tại: {agents_index}")
    print("================================================================================")
    print("   HOÀN THÀNH XUẤT BẢN THÀNH CÔNG (CHỈ TRONG THƯ MỤC .AGENTS/UPDATEDONE)!")
    print(f"   👉 Mở trực tiếp: file:///{agents_index.replace(os.sep, '/')}")
    print("================================================================================")


def main():
    parser = argparse.ArgumentParser(description="Universal Knowledge & Updatedone Hub Generator")
    parser.add_argument("-s", "--source", help="Đường dẫn tệp văn bản nguồn (.txt/.md) hoặc thư mục chứa các tệp")
    parser.add_argument("-o", "--output", help="Thư mục đích lưu trữ hệ thống tài liệu và file index.html")
    parser.add_argument("-t", "--title", default="Updatedone Logs", help="Tên hiển thị của Hub tài liệu")
    parser.add_argument("-v", "--version", default="v2.9.2", help="Mã phiên bản (VD: v2.9.2)")

    args = parser.parse_args()

    source = args.source
    output = args.output
    title = args.title
    version = args.version

    if not source:
        print("\n=== NHẬP THÔNG SỐ ĐẦU VÀO ĐỂ TẠO HUB TÀI LIỆU ===")
        source = input("1. Nhập đường dẫn tệp nguồn (vd: Hoi Dap.txt hoặc thư mục docs): ").strip(' "\'')
        if not source:
            print("[!] Đường dẫn nguồn không được để trống!")
            sys.exit(1)

    if not output:
        output = input("2. Nhập thư mục lưu kết quả (để trống nếu dùng thư mục hiện tại): ").strip(' "\'')
        if not output:
            output = os.getcwd()

    if not args.title or args.title == "Updatedone Logs":
        user_title = input(f"3. Nhập tiêu đề hiển thị (mặc định: '{title}'): ").strip()
        if user_title:
            title = user_title

    run_generator(source, output, title, version)


if __name__ == "__main__":
    main()
