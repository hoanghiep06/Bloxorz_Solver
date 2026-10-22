# Stage 3.5 — Responsive Layout, 3D Viewport & HUD Shell

Ngày xác minh: 2026-10-22, Ubuntu desktop/X11, Python 3.14.4,
Panda3D 1.10.16 trong `.venv`, GPU AMD Radeon Graphics/radeonsi.

**STAGE 3.5 LAYOUT & HUD SHELL COMPLETE**

## 1. Mục tiêu và phạm vi

Thêm Header, 3D Viewport, Right Control Panel và Bottom Status Bar theo
Modern Light Minimal 3D. Đây là presentation shell cho preview tĩnh:
không có manual input, gameplay, solver execution, replay hay animation.
Các controls chờ Tài tích hợp ở Stage 6 đều disabled thật.

## 2. Trạng thái Stage 3.4

Báo cáo lịch sử ghi 194 PASS/2 FAIL trên tổng 196 tests, hai failures nằm
ở helper đọc mesh của Stage 3.3. Không chỉnh báo cáo cũ hoặc bất kỳ source
3.1–3.4 nào. PreviewPresentation, camera, lighting, material, gradient,
geometry và rendering contracts vẫn dùng nguyên implementation hiện có.

## 3. Gate 0: regression repair

Baseline lần này tình cờ đạt 196/196 PASS; lỗi lifetime không ổn định theo
lần cấp phát. Đã tái hiện độc lập: đọc goal mesh bằng helper cũ, xóa owner,
thu gom rác rồi tạo 100 floor meshes làm **56/56 vector positions thay đổi**.
`GeomVertexReader.getData3f()` trả dữ liệu borrowed, nên giữ reference không
bảo đảm vector độc lập với buffer/reader.

Chỉ thay đúng ba dòng trong `tests/test_gui_renderer.py`:

```diff
-from panda3d.core import GeomVertexReader, NodePath
+from panda3d.core import GeomVertexReader, NodePath, Vec3
-            vertices.append(position.getData3f())
-            normals.append(normal.getData3f())
+            vertices.append(Vec3(position.getData3f()))
+            normals.append(Vec3(normal.getData3f()))
```

Sau sửa, positions và normals giữ nguyên sau khi giải phóng owner và cấp
phát lại 100 meshes. Renderer suite 33/33 PASS, full baseline 196/196 PASS.
Không sửa expected values, assertions, tolerance, geometry hoặc skip policy.
Gate 0 PASS trước khi viết layout/HUD.

## 4. Repository preflight

- Branch: `feat/phuoc/3d-renderer`.
- HEAD: `956c0a0528c9170afceda58551772bcadd3fc12a`.
- Tracked modification có sẵn: `src/gui/renderer.py`; giữ nguyên từng byte.
- 20 file untracked 3.1–3.4 có sẵn; không xóa hoặc ghi đè.
- Staged diff rỗng trước và sau công việc.
- Đã audit host, renderer API, create_preview, presentation, camera/provider,
  resize/refit, cleanup, renderer/camera/lighting tests và các tài liệu yêu cầu.
- Không có fetch/pull/checkout/reset/clean/stash/rebase/merge/commit/push.

## 5. Files tạo/sửa

Tạo tám file:

| File | Trách nhiệm |
| --- | --- |
| `src/gui/layout.py` | Rect/LayoutResult immutable, responsive math, panel control geometry |
| `src/gui/viewport.py` | Borrow main 3D DisplayRegion, viewport provider và restore |
| `src/gui/hud.py` | Pure ViewModel/formatting và DirectGUI shell |
| `src/gui/dashboard_preview.py` | Composition, CLI, lifecycle |
| `tests/test_gui_layout.py` | 8 tests layout thuần Python |
| `tests/test_gui_viewport.py` | 11 tests viewport/camera/events/composition/lifecycle |
| `tests/test_gui_hud.py` | 9 tests data/widget/disabled/resize/cleanup |
| `docs/gui/STAGE3_5_LAYOUT_HUD.md` | Báo cáo và bàn giao này |

Sửa file cũ duy nhất: helper `tests/test_gui_renderer.py`, đúng ba dòng ở mục 3.

## 6. Reference layout

Tại client area 1280×720, kiểm tra bằng assertions và pixel readback:

| Vùng | x | y | width | height |
| --- | ---: | ---: | ---: | ---: |
| Header | 24 | 24 | 1232 | 56 |
| Viewport | 24 | 92 | 934 | 530 |
| Panel | 974 | 92 | 282 | 530 |
| Status | 24 | 634 | 1232 | 62 |

## 7. Responsive rules

Với W≥1024, H≥720:

```text
Header   = (24, 24, W-48, 56)
Viewport = (24, 92, W-346, H-190)
Panel    = (W-306, 92, 282, H-190)
Status   = (24, H-86, W-48, 62)
```

Margin 24px, gutter giữa viewport/panel 16px, gap trên/dưới 12px.
Panel giữ width 282px, padding 16px, hai cột button 121px và gap 8px.
Nút cao 32px, font button 16px; title 24px, secondary/metric labels 14px.
Không scale cả HUD theo kích thước window. Panel cao hơn để thêm khoảng
trống phía dưới, không phóng to chữ hoặc kéo giãn controls.

| Client thực tế | Viewport thực tế | Lens aspect | VFOV |
| --- | --- | ---: | ---: |
| 1280×720 | 934×530 | 1.762264 | 45° |
| 1366×768 | 1020×578 | 1.764706 | 45° |
| 1920×1080 | 1574×890 | 1.768539 | 45° |
| 1024×768 | 678×578 | 1.173010 | 45° |
| 1024×720 | 678×530 | 1.279245 | 45° |

Ngoài minimum: ẩn ba HUD surfaces, deactivate vùng 3D và hiển thị
`Minimum window size: 1024 x 720`. Đã chạy 640×480 rồi phục hồi 1280×720.
Zero/minimized sizes không tính normalized region, không đổi fit cũ.

## 8. Coordinate system

Rect dùng integer client pixels, origin góc trên trái, X phải/Y xuống.
`pixel2d`: `(x, 0, -y)`. Rect width/height phải dương; layout từ chối
zero/negative/bool/float/string dimensions bằng ValueError. Minimized size
được viewport bỏ qua trước khi gọi layout math. Không trộn với world units.

## 9. DisplayRegion

Chọn đúng một existing region của `app.win` có `getCamera() == app.cam`.
Nếu không có hoặc có nhiều region khớp, fail sớm thay vì chỉnh nhầm camera.
Không tạo region/camera/output mới; giữ nguyên GUI regions, shadow buffers,
clear flags, scene roots và camera identity.

```text
left   = x / W
right  = (x+w) / W
bottom = 1 - (y+h) / H
top    = 1 - y / H
```

Reference normalized: `(0.01875, 0.7484375, 0.1361111111, 0.8722222222)`.
Runtime readback region pixels khớp chính xác tất cả năm viewport sizes.
Không có full-window 3D region thứ hai phía sau HUD.

## 10. Camera viewport provider

Reuse chính `app.presentation.camera`, không tạo BoardCameraController mới.
`DashboardViewport` rebind qua public `bind_window()` với provider đọc size
thật. Provider tính layout → cập nhật region/active → cập nhật HUD nếu layout
đổi → trả viewport width/height; listener camera gọi `set_viewport_size()`.

Composition truyền lại callback **hiện có** `app.presentation._refit`.
Đây là điểm nối có chủ ý với PreviewPresentation hiện tại, không copy
presentation logic: callback tiếp tục cập nhật gradient và lighting bounds.
Nếu đổi tên callback ở tương lai, cập nhật một chỗ trong composition.

ShowBase có thể đặt lens aspect theo full window trước; sự kiện
`aspectRatioChanged` được camera bắt sau đó để reassert viewport FOV/aspect.
Giữ VFOV 45°, azimuth 30°, elevation 45°, padding 13% mỗi phía và toàn bộ
block-height envelope của 3.4. Tất cả corners nằm trong NDC ±0.74 và near/far.

## 11. Event/listener ownership

Viewport không tạo DirectObject/listener/task riêng. Camera rebind sẽ gỡ
listener cũ của chính camera, đăng ký một listener cho `window-event` và
`aspectRatioChanged`. ShowBase handlers không bị ignore hoặc override.
Lặp resize không tạo thêm listener hoặc thêm widgets. Khi dispose, trả
camera về full-window binding/callback trước đó của create_preview.
Presentation tiếp tục sở hữu và dispose camera listener cuối cùng.

## 12. DirectGUI architecture

Một `DashboardHUD` root dưới pixel2d. Có ba cặp DirectFrame border/white
surface cho Header/Panel/Status; labels không có nền. Flat relief được dùng
để frame thực sự vẽ, không cần asset hoặc rounded-corner framework.
42 widgets được tạo một lần; resize sửa vị trí/frame size/text tại chỗ.
HUD import an toàn: Panda/DirectGUI chỉ được import khi khởi tạo HudShell.
Không import Core, Solver, Controller hoặc tạo ShowBase.

Palette: BG_MAIN #F1F4F7, BG_SECONDARY #E7EFF5, HUD_SURFACE #FFFFFF,
HUD_BORDER #D1DEE8, TEXT_PRIMARY #273B50, TEXT_SECONDARY #61778B.
3D giữ BLOCK_MAIN #527B9C và materials/palette có sẵn của 3.4.

## 13. Header

Title `Bloxorz Solver`, subtitle `3D Puzzle & AI Search`, friendly level
label từ filename stem, status `PREVIEW`, caption `Controls not connected`.
Không hiển thị absolute level path hoặc giả trạng thái solver/win.
Level/status dài được đo bằng TextNode rồi rút gọn với ellipsis; ViewModel
vẫn giữ dữ liệu đầy đủ. Không thu nhỏ font toàn UI để chứa text dài.

## 14. Game panel

Nhóm GAME: New Game, Restart, Select Level. Mỗi nút dùng cùng font/height,
select level chiếm full content width. Không dialog, input binding, reset
state hoặc callbacks. Không gọi Board.transition.

## 15. Solver buttons

AI SOLVERS: BFS/DFS, IDS/UCS, Greedy/A*, grid hai cột × ba hàng.
Sáu nút đều disabled, command=None; không import hoặc chạy solver,
benchmark, worker/thread hay orchestration.

## 16. Playback controls

PLAYBACK: Play/Pause, Step/Stop. Dùng Stop theo yêu cầu mới nhất.
Speed slider hiển thị 1.0x, range presentation 0.25..4; slider và thumb đều
disabled, command=None, không thay đổi tốc độ/interval thực tế. Dùng ASCII
`x` vì font Panda mặc định trên máy không có glyph multiplication U+00D7.
Không tải font ngoài. Không queue hoặc replay state machine.

## 17. HudViewModel và API

Frozen dataclass: `level_label`, `runtime_status`, `move_count`,
`search_time_ms`, `expanded_nodes`, `solution_length`,
`peak_python_memory_bytes`. Năm metric mặc định None.

```python
from src.gui.hud import HudViewModel

# Caller chỉ cung cấp số đã biết; những metric khác tiếp tục là None.
app.dashboard.hud.update_view_model(HudViewModel(
    level_label="Level 01", runtime_status="READY", move_count=0,
))
```

Ví dụ trên là API bàn giao, không tự chạy trong preview. `HudShell(pixel2d,
model)`, `apply_layout(layout)`, `update_view_model(model)`, `dispose()` là
interface tối thiểu. Không có action-binding API cho các nút lúc này.

Counts/memory phải là nonnegative int (không nhận bool); search time là
finite nonnegative int/float milliseconds; label/status phải nonempty.
Input sai bị ValueError. Không sao chép GameSnapshot thành Controller state.

## 18. Status metrics

Năm ô: Moves, Search Time, Expanded Nodes, Solution Length, Peak Python Memory.
None → em dash `—`. Zero thật → `0`, `0.00 ms`, `0 B` tùy metric.
Time <1000ms dùng ms hai số lẻ; từ 1000ms dùng s. Memory <1024 dùng B,
từ 1024 dùng KiB, từ 1048576 dùng MiB, binary units hai số lẻ.
Không đo tracemalloc trong HUD. Peak Python Memory là dữ liệu caller cung
cấp (có thể từ tracemalloc benchmark), không phải GPU memory hoặc tổng RSS.
Metric quá dài được ellide trên UI, không sửa giá trị model.

## 19. Disabled-state policy

Cả 13 action buttons, slider và slider thumb dùng DGG.DISABLED.
Đã kiểm tra `guiItem.getActive() == False` và `command is None` trên mọi
control. Màu nhạt và caption thể hiện trạng thái chưa kết nối; không có
command no-op hoặc button trông như đang hoạt động. Update ViewModel
không enable controls.

## 20. Lifecycle/cleanup

Normal: dashboard.dispose → existing presentation.dispose → renderer.dispose
→ host.destroy. Mọi component cleanup idempotent. Dashboard xóa callback
riêng khỏi finalExitCallbacks và chỉ destroy widgets/root mình sở hữu.

Nếu caller gọi trực tiếp `app.destroy()`, host 3.1 detach SceneRoot trước
khi ShowBase chạy finalExitCallbacks. Dashboard callback được insert trước
callback presentation để restore region/binding và destroy HUD trước.
**Không refit lighting khi SceneRoot đã empty**: viewport.dispose(refit=False)
tránh chạm vào scene bị detach. Sau đó presentation cleanup listener/lights.
Không monkeypatch destroy hoặc sửa host. Đã tái hiện lỗi thứ tự này trong
smoke và bổ sung tests cho đường shutdown đó.

Khi dispose dashboard mà host còn sống, restore đúng original dimensions,
active state và full-window camera fit. Resize tiếp 1366×768 vẫn hoạt động.
Foreign GUI nodes/region/camera không bị xóa. Constructor failure và loop
exception có cleanup tests. Engine windows sau destroy: **0**.

## 21. Dashboard commands

Từ repository root:

```bash
.venv/bin/python -B -m src.gui.dashboard_preview
.venv/bin/python -B -m src.gui.dashboard_preview --pose HORIZONTAL
.venv/bin/python -B -m src.gui.dashboard_preview --pose VERTICAL
.venv/bin/python -B -m src.gui.dashboard_preview --shadows
.venv/bin/python -B -m src.gui.dashboard_preview --no-aa
.venv/bin/python -B -m src.gui.dashboard_preview --level levels/level_01.json
```

Chỉ một ShowBase, một desktop window, một existing app.run loop.
`create_dashboard()` reuse `create_preview()` và giữ return `(app, renderer)`;
component mới được truy cập ở `app.dashboard`. Không hardcode machine paths.

## 22. Backward compatibility

```bash
.venv/bin/python -B -m src.gui.app
.venv/bin/python -B -m src.gui.board_preview
```

Đã chạy từng entry point trong process mới, tìm đúng native X11 window theo
PID rồi đóng bằng window-manager close. Cả Foundation, Board Preview và
Dashboard mở desktop window thật và exit code 0, không traceback/assertion.
Board Preview giữ full-window 3D, không có HUD. Source hai entry point cũ
không thay đổi.

## 23. Unit tests

28 tests mới: layout 8, HUD 9, viewport/composition 11.
Layout tests kiểm reference, containment, pairwise nonoverlap, năm sizes,
invalid inputs/fallback, determinism/immutability, coordinate flip và imports.
HUD tests kiểm formatting/validation/import isolation, real DirectGUI widgets
không cần window, disabled state, unchanged widget identities, label widths,
long text elision, fallback/recovery và foreign node ownership.
Viewport tests dùng region/window doubles và **real Panda lens/camera/events**;
không tuyên bố doubles là GPU/desktop evidence. Kiểm aspect/VFOV/frustum,
region selection, no duplication, provider freshness, zero/minimized,
listener ownership, restore, failures và detached-scene shutdown.
Desktop integration thực tế được kiểm riêng tại mục 25.

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_layout.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_viewport.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_hud.py'
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

## 24. Regression results

| Run | Ran | PASS | FAIL | ERROR | SKIP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline trước sửa, .venv | 196 | 196 | 0 | 0 | 0 |
| Gate 0 renderer sau sửa | 33 | 33 | 0 | 0 | 0 |
| Gate 0 full .venv | 196 | 196 | 0 | 0 | 0 |
| Gate 0 system Python | 196 | 143 | 0 | 0 | 53 |
| Final full .venv | 224 | 224 | 0 | 0 | 0 |
| Final system Python | 224 | 155 | 0 | 0 | 69 |

Final .venv 1.028s, system 0.481s trên runtime này. System Python không cài
Panda3D nên engine-dependent tests được skip có lý do; SKIP không tính PASS.
Không suy từ unittest time ra FPS/game performance.

## 25. Visual smoke và evidence

Dùng **onscreen GraphicsWindow thật**, không offscreen hoặc ảnh sinh AI.
Một session resize liên tiếp đủ năm sizes, assert actual client dimensions,
region pixel readback, VFOV/aspect và projected envelope. Đếm region/widgets/
listener identity để phát hiện tạo lặp. Pixel readback xác nhận surfaces trắng,
gutter đúng BG_MAIN; gradient bị giới hạn trong viewport. Đã mở và xem từng
ảnh dưới đây: text/buttons đủ nội dung, board/goal/block không bị cắt,
không 3D tràn panel, không distortion hoặc flicker quan sát được trong smoke.

Artifacts local của lần kiểm tra này (nằm `/tmp`, có thể mất khi reboot):

| Evidence | Path |
| --- | --- |
| Reference | `/tmp/bloxorz-stage3_5/dashboard-1280x720.png` |
| Responsive | `/tmp/bloxorz-stage3_5/dashboard-1366x768.png` |
| Large | `/tmp/bloxorz-stage3_5/dashboard-1920x1080.png` |
| Minimum width | `/tmp/bloxorz-stage3_5/dashboard-1024x768.png` |
| Minimum window | `/tmp/bloxorz-stage3_5/dashboard-1024x720.png` |
| Fallback | `/tmp/bloxorz-stage3_5/dashboard-small-fallback.png` |
| HORIZONTAL + shadows | `/tmp/bloxorz-stage3_5/dashboard-horizontal-shadow1-aa1.png` |
| VERTICAL + no AA | `/tmp/bloxorz-stage3_5/dashboard-vertical-shadow0-aa0.png` |
| Runtime values/cleanup | `/tmp/bloxorz-stage3_5/report.json` |
| Native entry point exits | `/tmp/bloxorz-stage3_5/entrypoints.json` |

Default cold-process framebuffer actual MSAA samples=8; --no-aa actual=0.
Request best-effort vẫn do 3.4 xử lý. Shadow controller giữ status
ENABLED_UNVERIFIED theo API cũ; ảnh thực tế HORIZONTAL cho thấy shadow đúng
trên floor, không tràn HUD. Không sửa status/implementation 3.4 để ghi PASS.
Không benchmark FPS ở chặng này.

## 26. Known limitations

- Shell tĩnh; mọi control disabled là chủ ý.
- Official minimum 1024×720 client pixels, chưa thiết kế mobile portrait.
- Font Panda mặc định; không bảo đảm Unicode tùy ý cho tên level/status.
- Nhãn dài/metric lớn được ellide; chưa có tooltip xem toàn bộ.
- Panel cao ở 1080p có khoảng trống phía dưới; fixed readable control sizes.
- Viewport adapter dành cho full-window binding của create_preview; không
  phải hệ quản lý/restore mọi arbitrary provider của ứng dụng khác.
- Callback `_refit` hiện tại là điểm nối với 3.4, chưa có public presentation
  callback facade riêng vì source 3.4 chỉ đọc trong nhiệm vụ này.
- AA/shadows là capability-dependent; screenshot chỉ xác nhận runtime Ubuntu này.
- Evidence `/tmp` không phải asset được đưa vào repo.

## 27. Windows testing

**NOT TESTED**. Không có Windows desktop trong môi trường này. Không suy ra
Windows PASS từ Ubuntu/unit tests. Cần kiểm DPI, font, resize, AA/shadow và
đóng window trên máy Windows trước khi chốt hỗ trợ nền tảng đó.

## 28. Tài cần nối ở Stage 6

Review HudViewModel/API và đơn vị milliseconds/bytes; truyền số thực sự biết,
giữ None khi chưa có kết quả. Tài sở hữu session, manual input, action handlers,
solver orchestration/worker và replay lifecycle. Thống nhất Play/Pause/Step/Stop
và speed semantics trước khi thiết kế action-binding rồi enable controls.
Không để HUD tự gọi transition hoặc đo benchmark; memory label cần đúng
nghĩa peak Python allocation, không nhầm với process/GPU memory.

## 29. Phong cần cung cấp khi vào Stage 4

Core/adapter cần thông tin fully observable và định nghĩa advanced tile/state
cho switch, bridge, fragile, split/teleport; giữ revision/session contracts rõ.
Phong xác nhận authoritative transition và split/fragile behavior. GUI không
tự suy luận luật hoặc mở rộng Basic DTO trong Stage 3.5. Review contracts
trước khi thêm advanced rendering ở chặng sau.

## 30. Git diff, scope, acceptance và điểm dừng

SHA-256 manifest trước/sau trên **58 file có sẵn**: 57 file giữ nguyên;
duy nhất `tests/test_gui_renderer.py` đổi, đúng helper-copy patch. Không mất
file có sẵn. Tạo đúng tám file mục 5. Tracked renderer diff có từ trước vẫn
nguyên byte; vì đa số file mới chưa track, `git diff --stat` không đại diện
toàn bộ chặng. Staged diff rỗng; git diff --check sạch. Branch/HEAD giữ nguyên.

| # | Acceptance | Trạng thái / evidence |
| --- | --- | --- |
| 1 | Regression helper khắc phục đúng nguyên nhân | PASS — lifetime reproduction + vector copies |
| 2 | Full baseline trước UI | PASS — Gate 0 196/196 |
| 3 | Đúng Panda3D | PASS — 1.10.16, real GraphicsWindow |
| 4 | Không Pygame | PASS — source/import inspection |
| 5 | Reference layout 1280×720 | PASS — assertions + pixel readback |
| 6 | Responsive năm sizes | PASS — runtime + năm ảnh đã xem |
| 7 | 3D DisplayRegion đúng rectangle | PASS — normalized/pixel readback |
| 8 | Không 3D tràn panel | PASS — region ownership + ảnh |
| 9 | Camera aspect/VFOV | PASS — real lens readback |
| 10 | Auto-fit/resize | PASS — envelope corners + real resize |
| 11 | Lighting/material/shadows | PASS — reused source + shadow smoke |
| 12 | Gradient trong viewport | PASS — clipped region + ảnh |
| 13 | Header | PASS — title/subtitle/level/preview |
| 14 | Control Panel | PASS — game/solver/playback groups |
| 15 | Sáu solvers | PASS — names + disabled GUI items |
| 16 | Playback controls | PASS — Play/Pause/Step/Stop/speed |
| 17 | Disabled buttons/slider | PASS — state/active/command checks |
| 18 | Năm status metrics | PASS — labels + view model tests |
| 19 | Không fake metrics | PASS — defaults None/em dash |
| 20 | HUD update API | PASS — validated model, real widget updates |
| 21 | Không triển khai Controller/gameplay/solver | PASS — scope/source |
| 22 | Không sửa Core | PASS — manifest |
| 23 | Không ShowBase thứ hai | PASS — create_preview reuse, one native window |
| 24 | Foundation demo | PASS — native open/close exit 0 |
| 25 | Board Preview demo | PASS — native open/close exit 0, full-window unchanged |
| 26 | Dashboard demo | PASS — native open/close + resize |
| 27 | Unit tests thực thi | PASS — 28 tests mới |
| 28 | Full regression sau UI | PASS — 224/224 .venv |
| 29 | Visual screenshots đã xem | PASS — mục 25 |
| 30 | Cleanup listeners/widgets | PASS — ownership tests, live restore, host destroy, engine windows=0 |
| 31 | Không commit/push/merge | PASS — Git read-only, HEAD/index unchanged |
| 32 | Documentation/diff report | PASS — tài liệu này + manifest audit |

Gates 0/A/B/C/D: **PASS** trên Ubuntu runtime hiện tại.
Windows: NOT TESTED; FPS benchmark: NOT TESTED (không bắt buộc).

**Dừng để Phước review trước 3.6.** Cần chấp thuận bố cục, placeholder/disabled
policy và API bàn giao trước khi thêm animation. Không tự triển khai 3.6 hoặc
Stages 4–6; không tự commit/push.
