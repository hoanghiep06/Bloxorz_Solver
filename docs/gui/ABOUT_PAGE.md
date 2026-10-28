# About Page

Đã thêm **About** giữa Settings và Quit trên Main Menu. Nút cùng kích thước
300×58 và phong cách với Settings, giữ nguyên callbacks Start/Settings/Quit.
About thay vùng trái, dùng cùng preview đang chạy bên phải. Back hoặc Escape trở
về Main Menu; Main ↔ About không cancel solver demo, reset Controller, reload
Board/level, refit camera hoặc tạo thêm ShowBase/GraphicsWindow.

## Files

- `src/gui/about_page.py`: nội dung, đúng 5 MSSV/tên được cung cấp, YouTube icon
  procedural, URL validation, browser worker và builder dùng Screen hiện hữu.
- `src/gui/screens.py`: nút About, AboutPage kế thừa Screen, navigation và region
  trái hiện hữu. Không tạo framework navigation mới.
- `assets/fonts/DejaVuSans.ttf`, `LICENSE-DejaVu.txt`: font đóng gói có glyph tiếng
  Việt, kèm giấy phép Bitstream/DejaVu. Font mặc định Panda thiếu các ký tự như
  `ệ`, `ễ`, `ư`, `ớ`, `Đ`; không phụ thuộc font đã cài trên máy chạy. Không thêm
  dependency. Tên nhóm giữ nguyên dấu, thứ tự và nội dung; không gán vai trò.
- `tests/test_about_page.py`, `tools/about_page_smoke.py`: kiểm thử và native QA.

About dùng `ui_theme` hiện tại (CARD/INK/MUTED/GOLD, button component sẵn có),
không có theme system khác. Cùng hierarchy/layout ở Light và Dark. Nội dung được
wrap theo width thực tế, hàng MSSV/tên chia cột, Back luôn ở dưới vùng nội dung.
Không thay Core, Controller, solver, animation, camera, lighting, background,
HUD, Mechanics Guide hoặc production level.

## Cấu hình Gameplay Demo

Trong `src/gui/about_page.py`:

```python
DEMO_YOUTUBE_URL = None
```

Thay `None` bằng URL video YouTube chính thức sau khi nhóm có link, rồi chạy lại
game. Nếu cấu hình được cập nhật trong tiến trình, mở lại About để rebuild button. Chưa có URL hoặc sai định dạng: **Coming soon**,
**Watch Demo disabled**, không mở link. URL HTTPS video hợp lệ của youtube.com
(watch/shorts/live/embed) hoặc youtu.be sẽ bật Watch Demo. Không chấp nhận host
lookalike, URL có credentials hoặc link không phải video. Validator kiểm tra định
dạng/host/video ID, không truy cập mạng để xác minh video còn tồn tại.

Click Watch Demo mở browser mặc định trên daemon worker để `webbrowser.open`
không chặn Panda main thread. Worker không chạm UI/Panda. Không có URL mặc định
hoặc video giả trong production. Tests dùng URL cấu trúc giả và mock browser,
**không mở video thực**. Máy chạy cần có browser mặc định nếu muốn dùng chức năng này.

## Kiểm thử ngày 28/10/2026

- Branch `feat/team-code/phase2-game-gui`, HEAD ban đầu `2cb6140`, working tree sạch.
- Baseline **522 test PASS**; full regression sau triển khai **530 test PASS**.
- **8 About tests PASS**, thêm **7 menu lifecycle tests PASS** trên source cuối:
  dữ liệu chính xác; glyph tiếng Việt thực; URL hợp lệ/không hợp lệ; worker không
  chặn thread GUI; callbacks; preview không reset; text bounds và Back nằm trong
  vùng trái; disabled/configured URL; rebuild/theme/resize và resource cleanup.
- **5 nhóm native XTest PASS**: About/Back hai theme × 1024×720, 1280×720,
  1366×768, 1920×1080; disabled click không mở browser; enabled click gọi đúng URL
  qua mock; Escape/Start/Settings/Quit callbacks; 20 lần About/Back.
- Native navigation kiểm tra cùng Board/manager/scene identity và viewport, không
  gọi load_level/restart_level. Preview attract vẫn active. Sau 20 chu kỳ:
  **220 widgets, 113 listeners, 14 tasks, 1 output** trước/sau bằng nhau. Sau dispose
  cả bốn bằng **0**. Không tăng cửa sổ hoặc event registration.
- Đã mở cửa sổ desktop thật `:0.0`, qua public button callbacks Main → About → Back
  ở Light/Dark, giữ cùng scene/window. Native mouse/keys được chạy trên Panda3D
  GraphicsWindow trong Xvfb/GLX; desktop test không giả nhận XTest injection.
- Đã tự xem screenshots: đủ 5 thành viên có dấu, không tràn sang preview, không cắt
  text, YouTube section/Back đều thấy ở 1024×720. Title và nội dung trắng rõ, accent
  gold, màu panel theo theme; nút disabled phản ánh trạng thái chưa có URL.

[Baseline](evidence/about/baseline-tests.txt) ·
[Regression](evidence/about/regression-tests.txt) ·
[About tests](evidence/about/about-tests.txt) ·
[Menu tests](evidence/about/menu-tests.txt) ·
[Native report](evidence/about/native-report.json) ·
[Desktop report](evidence/about/desktop-report.json).
Raw report giữ đường dẫn `/tmp` capture; các ảnh giao kèm dùng links dưới đây.

## Runtime screenshots

| Jungle / Light | Snow / Dark |
| --- | --- |
| [About 1280×720](evidence/about/light-about-1280.png) | [About 1280×720](evidence/about/dark-about-1280.png) |
| [About 1024×720](evidence/about/light-about-1024.png) | [About 1024×720](evidence/about/dark-about-1024.png) |
| [Main Menu mới](evidence/about/light-main.png) | [Main Menu mới](evidence/about/dark-main.png) |

Ảnh framebuffer thật, không phải concept hoặc UI dựng lại.

## Lệnh chạy và giới hạn

```bash
.venv/bin/python -B main.py
.venv/bin/python -B -m unittest discover -s tests -p 'test_about_page.py'
.venv/bin/python -B -m unittest discover -s tests
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.about_page_smoke --output /tmp/about-page-check
```

Chưa có URL chính thức nên chưa xác minh phát video thật. QA dùng profile tạm;
Quit được mock để kiểm tra callback mà không cắt quá trình thu bằng chứng.
Không claim hỗ trợ layout dưới minimum 1024×720 hoặc OS HiDPI chưa test.
Không tự commit/push/merge/reset hoặc đổi branch.
