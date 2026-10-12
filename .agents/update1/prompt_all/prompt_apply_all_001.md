# PROMPT ÁP DỤNG DÙNG CHUNG: ĐÓNG GÓI PYTHON EXE CHUYÊN NGHIỆP

```text
Hãy thực hiện đóng gói ứng dụng Python GUI sang file thực thi .exe độc lập theo các tiêu chuẩn kỹ thuật sau:
1. Xuất file .exe vào thư mục .agents/dist/ và thư mục tạm .agents/build/ để giữ thư mục gốc sạch sẽ.
2. Tắt hoàn toàn cửa sổ dòng lệnh đen (console=False / --noconsole / --windowed).
3. Gắn biểu tượng app_icon.ico chất lượng cao.
4. Gom đầy đủ tài nguyên động tĩnh (Assets, Images, Themes, JSON presets) bằng hàm get_resource_path() an toàn sys._MEIPASS.
5. Tự động nén file ZIP kết quả sau khi build thành công.
```