# Mechanics Guide Rail

Đã thêm cột **GUIDE** gồm 7 icon vector ở mép phải, chỉ hiện trong gameplay. Mặc định không mở thẻ. Bấm icon để mở; bấm icon khác đổi nội dung trong cùng thẻ; bấm lại icon đang chọn hoặc **X** để đóng. Không thêm phím tắt, framework, dependency, cửa sổ hay task mới.

## Files và cấu trúc

- `src/gui/mechanics_guide_data.py`: registry bất biến với tên, mô tả, ghi chú và accent của 7 cơ chế.
- `src/gui/mechanics_guide.py`: `MechanicsGuide`, layout thuần Python và icon vector. Component sở hữu các widget; cung cấp `show_mechanic`, `close_card`, `apply_theme`, `apply_layout`, `set_visible`, `dispose`.
- `src/gui/screens.py`: UIFlow sở hữu Guide; nối theme, resize, điều hướng và viewport qua các API sẵn có. Restart/đổi level không tạo lại rail/card, giữ lựa chọn.
- `src/gui/mouse_control.py`: mở rộng guard HUD cho cả vùng Guide; phần chữ/padding cũng không nhận nhầm thành nước đi hoặc hover dự báo.
- `src/gui/ui_theme.py`: thêm bốn token `GUIDE_PANEL/BORDER/INK/MUTED` vào hai theme hiện có, không đổi palette của GUI khác.
- `src/gui/scene_style.py`: thêm crop panorama tùy chọn cho bố cục có vùng bên phải; giữ nguyên asset, ánh sáng và vật liệu hiện có.
- `tests/test_mechanics_guide.py`, `tools/mechanics_guide_smoke.py`: component/regression và native XTest QA.

Rail rộng 58 px, nút 40×40, khoảng cách 8 px. Card rộng 260 px, body 16 px, note 14 px; chiều cao dựa trên số dòng của font thật. Card tự dịch lên phía trên metrics. Sau targeted UI fix, viewport luôn dành 90 px cho rail; card là overlay độc lập bên trái rail. Mở/đổi/đóng card không refit camera hoặc dịch board. Click guard bao gồm rectangle card thực. Xem [báo cáo mới](BUGFIX_FALLING_GUIDE_TOOLBAR.md). Phần panorama tại vùng dành riêng được tiếp nối bằng crop GUI của **chính asset hiện tại**, không thêm camera hoặc thay theme. Crop trở về mặc định khi rời gameplay.

## Nội dung tiếng Anh

Mô tả được đối chiếu với `src/core/board.py`: `is_goal`, `is_valid_state`, `_apply_switch_effects`, `_apply_switches_for_cells`, `_apply_switches_for_standing`, `_transition`; cùng `docs/gui/GAME_INTEGRATION.md`, `GEOMETRY_TILE_SPEC.md` và glyph trong `advanced_mesh_factory.py`. Core là nguồn quyết định khi tài liệu cũ mô tả hình X/ngoặc nhưng renderer hiện tại dùng hai thanh/hai plate.

| Icon / tên | Nội dung cơ chế | Ghi chú |
| --- | --- | --- |
| Cờ / Goal | Stand the whole block upright on the goal hole to finish the level. | A single split cube cannot finish. |
| Thanh cầu / Bridge | A linked switch can open or close this crossing. An open bridge supports the block like normal floor. | A closed bridge has no support. |
| Vòng cyan / Soft Switch | Touch this plate with any part of the block to activate its linked bridges. | Small split cubes can activate it too. |
| Hai thanh cyan / Heavy Switch | Stand the whole block upright on this plate to activate its linked bridges. | Lying blocks and small cubes do not activate it. |
| Hai cube / Split Switch | Stand the whole block upright here to split it into two cubes at the configured destinations. | Space selects a cube. Cubes merge when they meet along an edge. |
| Ô nứt cam / Fragile Tile | This tile breaks when the whole block stands upright on it. Lying across it is safe. | A small split cube is safe here. |
| Hố rỗng / Void | There is no floor here. Moving any occupied part of the block over the gap makes it fall. | Check the full landing area before rolling. |

Không giả định mọi switch đều toggle: cách open/close/permanent phụ thuộc cấu hình Core. Guide chỉ cung cấp thông tin, không gọi transition, solver hoặc sửa state.

## Theme và tương tác

Light dùng panel trắng xanh; Dark dùng navy. Accent cyan/cam/amber/steel/slate giữ nguyên giữa hai mode. Đổi theme cập nhật rail và card đang mở ngay tại chỗ, giữ icon đang chọn và các widget hiện hữu. Hover có nền nhẹ; selected có viền accent. Các nút không lấy keyboard focus, không pause/cancel animation hay replay.

## Kiểm thử và ảnh chạy thật

- Baseline trước triển khai: **489 test PASS**.
- Regression sau triển khai: **499 test PASS**, không skip lỗi baseline.
- **14 nhóm native XTest PASS trên Auto/Balanced và lặp lại 14 nhóm trên High/bloom**: 7 icon ở cả hai theme; đổi nội dung, toggle/X; click phần body; hover guard; resize 1024×720, 1280×720, 1366×768, 1920×1080; bàn phím khi card mở; click Guide giữa animation; Restart/đổi màn; sáu nút solver, worker/metrics và replay theo clock thật; fallback kích thước nhỏ và phục hồi.
- 20 lần đổi theme khi card mở: **113 widget, 78 listener, 14 task, 1 graphics output, 29 Guide nodes** trước/sau bằng nhau trên Auto/Balanced. Trên High/bloom: **113 widget, 79 listener, 14 task, 3 outputs, 29 Guide nodes** cũng giữ nguyên. Sau dispose ở cả hai mức: tất cả bằng **0**.
- Không sửa Core, Controller, solvers, rolling math, 3D mesh, level hoặc callback gameplay.

Ảnh framebuffer thực tế (ba ảnh đầu ở High/bloom; ảnh kiểm tra kích thước ở Auto/Balanced):

- [Dark — chỉ rail](evidence/mechanics-guide/dark-rail-closed.png).
- [Dark — card mở](evidence/mechanics-guide/dark-card-open.png).
- [Light — card mở](evidence/mechanics-guide/light-card-open.png).
- [Dark 1024×720](evidence/mechanics-guide/dark-card-1024.png) · [Light 1024×720](evidence/mechanics-guide/light-card-1024.png).
- [Dark 1920×1080](evidence/mechanics-guide/dark-card-1920.png) · [Light 1920×1080](evidence/mechanics-guide/light-card-1920.png).
- [Native report](evidence/mechanics-guide/report.json), [High/bloom report](evidence/mechanics-guide/high-report.json), [baseline log](evidence/mechanics-guide/baseline-tests.log), [regression log](evidence/mechanics-guide/regression-tests.log).

```bash
.venv/bin/python -B main.py
.venv/bin/python -B -m unittest discover -s tests
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.mechanics_guide_smoke
```

QA dùng profile tạm và bộ fixtures cơ chế; không thay level hoặc save người chơi. Guide cũng hiện với catalog 18 level sản phẩm.

## Giới hạn

Nội dung hướng dẫn là registry tĩnh, hiện đủ 7 cơ chế ở mọi level; không tự giải thích ID cầu của từng switch. Card không phải modal: người chơi vẫn có thể lăn/rơi khi đọc. Dưới 1024×720, Guide ẩn cùng fallback kích thước tối thiểu hiện có; khi tăng lại sẽ giữ lựa chọn. Không thêm tooltip hoặc hiệu ứng mở thẻ để tránh tăng scope.

Không commit, push, merge, reset, chuyển nhánh hoặc xóa thay đổi chưa commit/untracked.

## Xác minh trước khi push

Đã đồng bộ hai commit remote `b93127a` (cờ đích trong animation) và `6f70603` (tutorial). Giữ cơ chế animated surface tiếp quản cờ của remote, tránh hiển thị hai bản cờ khi hiệu ứng chạy. Regression **499/499 PASS**; chạy lại **14 nhóm native UI PASS**, gồm sáu solver/replay. Với tutorial mới: 131 widget, 80 listener, 14 task, 1 output, 29 Guide nodes giữ nguyên sau 20 lần đổi theme; sau dispose đều bằng 0. [Native report mới](evidence/mechanics-guide/pre-push-report.json) · [Regression mới](evidence/mechanics-guide/pre-push-tests.log).
