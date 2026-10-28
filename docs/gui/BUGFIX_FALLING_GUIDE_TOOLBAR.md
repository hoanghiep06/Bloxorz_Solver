# Targeted bug fix: Falling, Guide Rail, Toolbar

**COMPLETE trong phạm vi bốn yêu cầu.** Kiểm chứng ngày 27/10/2026.
Branch `feat/team-code/phase2-game-gui`, HEAD `a87f095`. Working tree đầu phiên đã có
nâng cấp Physical Falling chưa commit; giữ nguyên các thay đổi đó. Baseline thực
chạy **515 test PASS**, sau đợt này **521 test PASS**, không skip failure.

## 1. F1 và F2: tái hiện, nguyên nhân

Người dùng xác nhận **Moves 1 bấm Down**, **Moves 10 bấm Left**. Từ production
`levels/level_04.json`, tìm các route hợp lệ đưa tới footprint và số Moves tương ứng:

| Case | Route tới vị trí ảnh | State/footprint trước nước thua | Input | Core motion/attempted footprint |
| --- | --- | --- | --- | --- |
| F1 | `D` | VERTICAL `(1,1),(2,1)`; Moves 1 | D | STANDING `(3,1)`, Void |
| F2 | `D U D R R D R R D L` | VERTICAL `(4,5),(5,5)`; Moves 10 | L | VERTICAL `(4,4),(5,4)`, Void |

Đây là **reproducer từ Core**, không khẳng định F2 là toàn bộ lịch sử phím của người
dùng. Hai bước D/U đầu của F2 quay về spawn, giúp tái hiện cùng footprint ở Moves 10.
Không inject state, không sửa level. Ảnh before được chụp lại để đối chiếu ảnh gửi.

**Không tái hiện được việc mất FALL event.** Ở cả F1 và F2, baseline Core trả
`failure_reason='fall', next_state=None`; Controller phát request, actor xuống Z và
callback cuối đưa game tới FELL. [Trace baseline](evidence/targeted-ui/baseline-fall-trace.txt)
ghi pose/quaternion và kết quả thực. Vì vậy không gán lỗi giả cho validation,
rollback, session filtering hoặc Controller bỏ event.

Root cause chung của phần **chuyển động thiếu lao xuống**: `action_plan.plan_action`
chỉ dùng terminal `roll_direction` khi snapshot đích vượt giới hạn hình chữ nhật
JSON. Hai vùng Void này vẫn **ở trong grid**, dù nằm ngoài bề mặt chơi. Adapter phát
ROLL 0.35s tới pose đáp, dừng hoàn toàn, rồi FALL 0.9s bắt đầu từ nghỉ với quaternion
đứng yên. Đó là đường đi khác với off-grid fall đã có contact và quán tính.

## 2. Sửa adapter đúng ownership

Thêm `_open_void_exit()` trong **GUI adapter** `src/gui/action_plan.py`. Chỉ sau khi
Core đã xác nhận fall, chọn profile edge nếu:

- Whole block, `failure_reason == 'fall'`, không có next state.
- Motion và attempted state bằng nhau: không bỏ qua split/merge/switch/bridge effects.
- Mọi lane của footprint đích không có support, tiếp tục trống theo hướng di chuyển
  cho tới mép grid. Đọc support bằng `Board.is_valid_cell`, không viết lại luật.

Khi đủ điều kiện, phát **một terminal FALL có hướng từ before snapshot**, tái sử dụng
FallPlan/AnimationManager cũ: đúng RollPlan prefix -> tip -> tangent ballistic fall.
Không tạo một engine khác, không bịa snapshot trên Void, không reset Q. F1/F2 nay
liên tục từ current visual pose, có vận tốc ngang và quay, xuống dưới mặt board rồi
mới fade và hoàn tất. Losing action tổng 0.9s thay vì roll dừng + fall 1.25s; duration
terminal, outcome, Core state và cách tính Moves/metrics giữ nguyên.

Enclosed hole, partial support có lane còn sàn, fragile, bridge/split/merge effects
và rejected input giữ pipeline riêng. Không biến mọi invalid move thành thua.
Standing off-grid positive control giữ nguyên. Không sửa Core, solver hoặc Controller.

## 3. Before/after và gameplay thực

| Case | Baseline excerpt | Sau sửa, phím XTest + clock thật | Ảnh desktop giữa fall |
| --- | --- | --- | --- |
| F1 | [GIF](evidence/targeted-ui/F1-baseline-excerpt.gif) | [Dark](evidence/targeted-ui/dark-F1-native.gif) / [Light](evidence/targeted-ui/light-F1-native.gif) | [PNG](evidence/targeted-ui/desktop-F1-mid.png) |
| F2 | [GIF](evidence/targeted-ui/F2-baseline-excerpt.gif) | [Dark](evidence/targeted-ui/dark-F2-native.gif) / [Light](evidence/targeted-ui/light-F2-native.gif) | [PNG](evidence/targeted-ui/desktop-F2-mid.png) |

Before excerpt lấy từ working tree 515 test trước khi sửa adapter, mỗi 10/60s tới
70/60s, chưa tới callback; trace riêng xác nhận FELL. After có hai loại bằng chứng:

1. [Controlled F1](evidence/targeted-ui/dark-F1-controlled.gif) và
   [F2](evidence/targeted-ui/dark-F2-controlled.gif): cùng production Controller/Core,
   sample timeline 1/60s, framebuffer thật mỗi 2/60s. Không gọi nó là đo FPS thực.
2. Native XTest Down/Left, kiểm tra Controller **nhận đúng `D`/`L`** ở cả hai theme.
   Lượt cuối buffer framebuffer trong RAM, chỉ ghi PNG sau terminal; không để encode
   PNG làm stall animation. 21–23 frame/case cho thấy cả pha roll, tip, xuống thấp và
   terminal. Frame đầu có thể là trước input, với progress=1 của safe move trước đó.

Đã tự xem các ảnh tip/below-board: khối rời mép theo đúng hướng, vẫn giữ magma,
không thấy blink, teleport, ghost actor hoặc reset mặt giữa chuỗi trong các mẫu.
Result chờ terminal; bấm HUD Restart trở về READY. Bảng HUD vẫn ghi READY khi đang
animate theo Controller hiện tại; không sửa semantics status/Moves trong đợt này.

Đã mở GraphicsWindow trên **desktop thật `:0.0`**, chạy F1/F2 qua public Controller
và task clock, chụp ở progress khoảng 0.20/0.52/0.81 rồi FELL; Restart thành công.
[Desktop report](evidence/targeted-ui/desktop-report.json). Native keyboard/mouse
được kiểm tra trên Xvfb có GLX; không tuyên bố XTest hoạt động trên desktop khi
MouseWatcher của desktop không nhận pointer injection trong môi trường này.

GIF chỉ resize/palette, không dựng frame hoặc dùng ảnh concept. PNG gốc 1280×720;
file `toolbar-crop` chỉ crop đúng pixel. [Manifest](evidence/targeted-ui/manifest.json)
chứa pose, thời điểm và ảnh chọn; raw reports giữ đường dẫn `/tmp` để truy nguồn.

## 4. Guide Rail: nguyên nhân và stable anchor

Preflight thấy rail đã anchor theo cạnh phải và button đã `pressEffect=0`. Không
chứng minh được NodePath icon tự dịch khi pressed. Tuy nhiên mỗi lần mở card:

- `guide_layout.reserved` tăng từ **90 lên 362 px**.
- `UIFlow._mechanics_changed()` gọi `viewport.refresh()`.
- Camera refit, board/panorama dịch và đổi tỉ lệ ngay khi click.

Bản sửa giữ reserved **90 px cố định**, card là overlay độc lập bên trái rail và
bỏ refresh tại callback mở/đóng card. Không bù offset ngược, không đổi button size,
icon center, parent transform hoặc spacing. Resize thật vẫn fit theo kích thước
cửa sổ; chỉ mở/đổi/đóng card không fit camera.

Vì card nay nằm trên viewport, click guard được đổi để chặn **rectangle card thực**
và strip rail, tránh click phần chữ/padding thành nước đi. Không chặn cả vùng board
ngoài card. Hover/selected vẫn đổi fill/border như cũ.

Đã đo screen-space position, frame rectangle, icon center và tight bounds của cả
7 icon qua hover, button-down, button-up, đổi card, close và đổi theme. **Max error
0 px** trong từng window size, tại 1024×720, 1280×720, 1920×1080 ở hai theme. Rail
vẫn cách mép phải 20 px khi resize; tọa độ X thay đổi theo window là hành vi anchor
mong muốn. Native test còn so camera fit và viewport trước/sau click: bằng nhau.

[Dark card](evidence/targeted-ui/dark-guide-card.png) ·
[Light card](evidence/targeted-ui/light-guide-card.png) ·
[Bounds/resource report](evidence/targeted-ui/native-ui-report.json).

## 5. Toolbar: audit và sửa chất lượng icon

Icon cũ là **triangle geometry**, không phải font/Unicode hay bitmap nhỏ bị phóng.
Toolbar scale 14 (hộp khoảng 28 px), Exit có stem dày tới 6.7 px; vector node không
chỉ định multisample antialias. Ảnh runtime cho thấy cạnh khá thô/đậm và độ dày không
đồng nhất. Không có bằng chứng lỗi xuất phát từ một PNG nguồn thấp hoặc font atlas.

Giữ pipeline geometry: đặt node `MMultisample`, chuẩn hóa toolbar half-size 12
(khoảng 24 px), Exit thành stroke round-joined 2.16 px, Restart ring khoảng 2.28 px,
Eye/Info giữ silhouette hiện hành. Nền, kích thước, vị trí, text, hitbox và callback
nút giữ nguyên. Không đổi theme architecture hoặc thêm thư viện runtime.

Xem crop **ở kích thước pixel thật**:

| Theme | 1024×720 | 1280×720 | 1920×1080 |
| --- | --- | --- | --- |
| Dark | [Crop](evidence/targeted-ui/dark-1024-toolbar-crop.png) | [Crop](evidence/targeted-ui/dark-1280-toolbar-crop.png) | [Crop](evidence/targeted-ui/dark-1920-toolbar-crop.png) |
| Light | [Crop](evidence/targeted-ui/light-1024-toolbar-crop.png) | [Crop](evidence/targeted-ui/light-1280-toolbar-crop.png) | [Crop](evidence/targeted-ui/light-1920-toolbar-crop.png) |

Các PNG full-window tương ứng nằm cùng thư mục, bỏ hậu tố `-crop`. Đã nhìn ảnh thật
và kiểm tra all five callbacks: Exit, Restart, AI Solver, View và Tutorial. Không
biến nút thành disabled. AA dựa trên MSAA framebuffer sẵn có; không đo/chứng nhận
HiDPI/OS scaling khác 1× hoặc GPU không hỗ trợ MSAA.

## 6. Robot: đúng nguồn, alpha, portable asset

Dùng **đúng robot do người dùng đính kèm**, không tìm icon internet hoặc tạo robot
khác. Giữ nguồn `assets/icons/sources/ai-robot-source.png` 360×360. Tool offline
`tools/prepare_toolbar_robot.py` flood-fill nền gần trắng **kết nối với viền ảnh**,
giữ component robot lớn nhất để bỏ shadow rời, làm mềm/decontaminate matte trắng
ở boundary. Không threshold toàn bộ nội dung; vùng trắng trong thân được giữ.

Derived asset `assets/icons/ai-robot.png`: **228×274 RGBA**, padding 6 px. Unit test
kiểm tra alpha thật, pixel mềm, nền alpha=0 và hơn 1.000 pixel trắng opaque bên trong.
Đã tự xem ảnh cắt nền trên nền tối và ảnh runtime; không thấy rectangle/halo rõ.

`icons.make_robot_icon()` load bằng path suy từ `__file__`, TexturePool hiện có,
linear mipmap/minification, linear magnification và clamp. Giữ đúng tỉ lệ, hiển thị
portrait cao 26 px bên trái `AI Solver`, không stretch. Robot giữ màu gốc, không
nhận tint vàng của text; disabled chỉ giảm opacity. Callback/toggle solver không đổi.
Pillow chỉ dùng trong tool offline trên máy hiện tại, **runtime không cần Pillow**.

[Derived PNG](../../assets/icons/ai-robot.png) ·
[Source/provenance và lệnh tái tạo](../../assets/icons/README.md).

## 7. Regression và UI QA

| Kiểm tra | Kết quả |
| --- | --- |
| Baseline full suite | PASS — 515/515 |
| Full suite cuối | PASS — 521/521, 91.224s |
| Test mới F1/F2 + pause/restart + enclosed/nonlosing + robot/AA | PASS — 5 test, gồm subcases |
| Guide suite | PASS — 11 test, thêm bất biến transform/bounds mọi PGButton state |
| HUD suite | PASS — 12 test |
| Native F1/F2 hai theme, đúng phím, terminal/Restart | PASS — 4 case |
| Native Guide/toolbar, ba kích thước × hai theme | PASS — bounds 0 px; viewport/camera cố định |
| Guide regression + worker/metrics/replay sáu solver | PASS — 14 nhóm native |
| Positive falling/control regression | PASS — native Up, mouse Iso/Top/Follow, Tutorial, 15 pause/resume/restart |
| Desktop F1/F2 clock, result, Restart | PASS — cửa sổ thật, public Controller |
| 30/60/120 FPS, tốc độ, callback, cancel/resync, stable split identity | PASS — bộ tests Physical Falling hiện hữu trong full suite |
| OS HiDPI khác 1×, mọi GPU/driver | NOT TESTED |

Không nới test clipping hoặc Core để làm xanh. Chỉ thay expectation cũ “card đẩy
viewport sang trái” bằng invariant mới **card overlay không refit**, theo yêu cầu
thiết kế. Guard click phần body card vẫn được kiểm tra bằng native mouse.

[Baseline](evidence/targeted-ui/baseline-tests.txt) ·
[Regression](evidence/targeted-ui/regression-tests.txt) ·
[Native clock](evidence/targeted-ui/native-clock-report.json) ·
[Guide/six solvers](evidence/targeted-ui/guide-solvers-report.json) ·
[Positive fall](evidence/targeted-ui/positive-falls-report.json).

## 8. Resource cleanup

20 vòng close/đổi card/open ở cuối cùng một production scene: trước/sau bằng nhau,
**393 scene nodes, 13 tasks gồm delayed, 152 widgets, 1 output**. Sau dispose:
**0 task, 0 widget, 0 output, 0 listener**. Guide six-solver smoke riêng cũng dọn
sạch toàn bộ widget/task/output/Guide node. Đây là finite stress test, không phải
chứng minh mọi phiên chơi dài đều không leak; không có benchmark FPS trong báo cáo.

## 9. Acceptance matrix

| Hạng mục | Trạng thái |
| --- | --- |
| F1 tái hiện, sửa profile và xác minh gameplay thật | PASS |
| F2 tái hiện, sửa profile và xác minh gameplay thật | PASS |
| Hai case lao xuống, C/Q liên tục, magma và actor owner giữ nguyên | PASS |
| Không thấy blink/teleport/ghost trong captured cases | PASS |
| Positive/standing/horizontal/vertical/split fall và invalid non-losing | PASS — full suite + positive native smoke |
| Pause/resume, cancel/restart/session, callback một lần | PASS |
| Rail center/rectangle không đổi khi click; không offset bù | PASS |
| Card độc lập, không đẩy rail hoặc refit board | PASS |
| Hover/selected, close, Light/Dark/resize và click guard | PASS |
| Exit/Restart/Eye/Info rõ và căn giữa ở các size đã test | PASS — visual inspection |
| Toolbar callbacks/hitboxes và text giữ nguyên | PASS |
| Đúng robot source, alpha, không rectangle, tỉ lệ/position/theme | PASS |
| AI Solver vẫn toggle và sáu thuật toán/replay chạy | PASS |
| Full regression, không thêm dependency runtime | PASS |
| Không sửa Core/solver/production level/mesh/material/background | PASS |
| Không commit/push/merge hoặc chuyển branch | PASS |
| Có screenshot, GIF, trace và báo cáo | PASS |

## 10. Files, ownership và giới hạn

Thay đổi **mới trong đợt này**:

- `src/gui/action_plan.py`: phân loại visual open-void fall đã được Core xác nhận.
- `src/gui/mechanics_guide.py`, `screens.py`: fixed reservation/overlay/guard, bỏ refit
  khi card đổi. Các thay đổi default-disable assist từ phiên trước vẫn được giữ.
- `src/gui/icons.py`, `hud.py`: stroke/AA/scale, robot asset và tint handling.
- `assets/icons/`: nguồn và RGBA từ ảnh người dùng, README.
- `tests/test_targeted_falling_ui.py`, `tests/test_mechanics_guide.py`: regression mới.
- `tools/targeted_ui_smoke.py`, `tools/prepare_toolbar_robot.py`,
  `tools/mechanics_guide_smoke.py`: native QA, asset preparation, overlay expectation.
- Báo cáo này, evidence và cập nhật ghi chú các tài liệu GUI liên quan.

Giữ các tracked/untracked changes Physical Falling trước đó, không xóa chúng.
Không sửa `src/core/`, `src/solvers/`, `controller.py`, production JSON, board geometry,
magma mesh/material, background hoặc ánh sáng. Git diff gồm cả thay đổi chưa commit
của phiên trước; không gọi tất cả là phát sinh trong đợt này.

Giới hạn: ảnh tĩnh không xác định duy nhất input history, nên F2 là route tương đương
có Core xác minh. Gate open-void cố ý bảo thủ: nếu còn sàn ở bất kỳ lane hướng ra
ngoài thì dùng profile cũ của hố/partial; không thay luật. Fallback confined-drop với
overlap hình học đã nêu trong báo cáo Physical Falling vẫn là giới hạn trước đó,
không thuộc hai vùng Void thông thoáng F1/F2 và không được tuyên bố đã giải quyết.
Card overlay có thể che một phần board ở window hẹp; đóng card để nhìn lại, không
refit hoặc dịch rail. Robot full-body ở 26 px đương nhiên có ít chi tiết hơn source 360 px; không phóng
bitmap nhỏ hoặc thay nhân vật để làm nó khác ảnh đã chọn.

## 11. Lệnh tái kiểm tra

```bash
.venv/bin/python -B main.py
.venv/bin/python -B -m unittest discover -s tests
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.targeted_ui_smoke --output /tmp/targeted-ui-check
xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.targeted_ui_smoke --native-falls-only --output /tmp/targeted-clock-check
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.mechanics_guide_smoke --output /tmp/targeted-guide-check
```

Tool dùng save tạm, không thay profile người chơi. Không commit/push/merge/reset/
clean/stash/rebase/checkout. Dừng sau báo cáo; để toàn bộ working tree cho Phước review.
