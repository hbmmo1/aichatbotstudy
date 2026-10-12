# 🤖 Zalo Automation, Performance & Thread-Safety Rules

## 1. Process Isolation Rule
Always exclude the current application process (`pid == os.getpid()`) and window titles containing `AI Zalo CSKH` or `Quản Lý Giáo Án` from window scanning functions (`find_zalo_hwnd`, `scan_active_windows`, `pick_window_1click`).

## 2. Process Name Caching & CPU Optimization Rule
Always use `get_proc_name_cached(pid)` with TTL (8s) instead of invoking `psutil.Process(pid).name()` directly in loops to eliminate CPU spikes during window scanning.

## 3. Tkinter Thread-Safety & Anti-Freeze ("Not Responding") Rule
All GUI updates (`widget.configure`, `widget.insert`, `widget.delete`, `show_toast`, `messagebox`) triggered from background threads (`_worker`, `_scan`, `threading.Thread`) MUST be dispatched via `self.after(0, ...)` wrapped in `try...except`.

## 4. SQLite Performance & Concurrency Rule
Always open SQLite connections in `StateManager` with `timeout=15.0`, `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, and `PRAGMA cache_size=-64000;`. Maintain database indices on foreign keys and search columns.

## 5. Credential Encryption & Login Safety Rule
Never store passwords in plain text in `storage/saved_login.json`. Use `_obfuscate_secret` and `_deobfuscate_secret`. Never prefill login credentials unless explicitly chosen by user via "💾 Lưu thông tin đăng nhập".

## 6. Silent Background Mode Rule
When sending in background mode:
- Use `send_deep_background_click` (`PostMessage` with `WM_LBUTTONDOWN`/`WM_LBUTTONUP`) to avoid moving the hardware mouse cursor.
- Never use `pyautogui.moveTo` or `pyautogui.click` during background operations.
- Use `quick_focus_and_restore` to preserve and restore the user's active window within <150ms. Always detach `AttachThreadInput` in `finally` blocks.

## 7. Global Hotkeys Mapping
- `F10`: Quick send current script template (Tab 3) or broadcast template (Tab 2) directly into Zalo PC / active chat.
- `F8`: Start / Toggle Bot CSKH.
- `F9`: Emergency Abort (`emergency_cancel_all_operations`).
- `F6`: Pause / Resume Broadcast.
- `F7`: Cancel Broadcast.
- `Ctrl+S`: Context-aware Save (Tab 3 Templates, Tab 4 CRM, Tab 10 Settings).

## 8. Multi-Theme Color Contrast & Readability Rule
All UI additions or modifications MUST provide optimal high contrast and readability on both Light Theme (white/slate-50 background with dark `#0f172a` text/accent `#0284c7`) and Dark Theme (slate-900/950 background with bright `#f8fafc` text/accent `#38bdf8`). Never use low-contrast text that blends with the background.

## 9. Vietnam Timezone (UTC+7) & Timestamp Rule
All timestamps in SQLite database schemas (`datetime('now', 'localtime')`) and Python datetime formatting (`datetime.now()`, `format_smart_timestamp`) must strictly follow local Vietnam Timezone (UTC+7).

## 10. Clean Workspace & PyInstaller Output Rule
All PyInstaller outputs, `.spec` files, temporary `build/` files, and final `dist/` portable bundles must be located inside `.agents/build/` and `.agents/dist/` to keep the project root clean and organized.

