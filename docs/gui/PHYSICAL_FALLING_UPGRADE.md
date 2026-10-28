# Physical Falling Upgrade

Trạng thái: **PHYSICAL FALLING UPGRADE COMPLETE** — hoàn tất mô hình chuyển động
thị giác xác định theo thời gian, có fallback rõ ràng cho khe không đủ chỗ xoay.
Đây không phải hệ mô phỏng va chạm vật rắn. Kiểm chứng ngày 27/10/2026 trên nhánh
`feat/team-code/phase2-game-gui`, HEAD ban đầu `a87f095`.

## 1. Phạm vi và baseline

Đầu phiên working tree sạch, không có tracked modification hoặc untracked file.
Baseline thực chạy **499 test PASS**, không có failure phải bỏ qua. Python trong
`.venv` là 3.14.4; Panda3D 1.10.16. Entrypoint hiện hành là `main.py` hoặc
`python -m src.gui.game_app`, có Controller/Core/solver thật; không phải chỉ preview.

Thay đổi giới hạn ở presentation: tắt directional assist mặc định và thay quỹ đạo
FALL trong AnimationManager hiện có. Không đổi luật, lời giải, chi phí, metrics,
Moves, level, model, texture, shader, theme, dependency hoặc rolling math.

## 2. Component tạo warning

`src/gui/move_arrows.py::MoveAssistLayer` tạo các mũi tên, nhãn `OK / ! / X`, vùng
dự báo đáp và viền vàng. Đây là **gameplay assist / prediction visualization**,
không phải bộ kiểm tra hợp lệ của Core. `UIFlow` sở hữu instance này.

Instance mặc định hiện dừng ngay trước khi dựng predictor, node, label và task.
Không dùng alpha=0 để che overlay còn chạy. Không tính bốn transition mỗi frame.
Cờ development tùy chọn:

```bash
BLOXORZ_MOVE_ASSIST_DEBUG=1 .venv/bin/python -B main.py
```

Giữ nguyên component khi bật debug; không thêm nút Settings. Không đụng Guide Rail,
Goal Flag, HUD, input bàn phím/chuột hoặc `Board.describe_transition()`.
Tutorial bỏ ba hướng dẫn hover/OK/yellow đã không còn đúng trong gameplay mặc định.

## 3. Files thay đổi

| File | Trách nhiệm |
| --- | --- |
| `src/gui/fall_math.py` (mới) | Toán support, contact, clearance, tipping, ballistic, pose sampling thuần Python |
| `src/gui/animation_manager.py` | Tạo một FallPlan khi nhận explicit FALL; sample trong timeline cũ |
| `src/gui/animation_effects.py` | Rig không hide rồi show lại actor đang hiển thị trong mỗi sample |
| `src/gui/move_arrows.py` | Default-disable trước khi tạo tài nguyên; lifecycle an toàn |
| `src/gui/screens.py` | Nối cờ debug tại owner của component |
| `src/gui/tutorial.py` | Nội dung mouse controls phù hợp UI mới |
| `tests/test_physical_fall.py` (mới) | 16 test toán, integration/lifecycle, assist mặc định |
| `tests/test_mouse_control.py` | Các test trực tiếp component assist bật `enabled=True`; giữ nguyên assertions |
| `tools/physical_fall_smoke.py` (mới) | Production losing moves, framebuffer và native XTest QA |
| `tools/move_assist_smoke.py` | Bật debug rõ ràng cho smoke của component cũ |
| Tài liệu này và `evidence/physical-falling/` | Báo cáo, test output, ảnh/GIF thực |

## 4. Kết luận audit chuyển động cũ và nhấp nháy

FALL off-board cũ chạy hết một RollPlan 90° trong 45% đầu, sau đó rơi Z bậc hai,
quaternion đứng yên. Với void trong board, normal ROLL đã kết thúc ở tư thế đáp rồi
FALL bắt đầu từ nghỉ. Chưa có last-contact tipping hoặc vận tốc tiếp tuyến nối
sang free fall. Fade cũ bắt đầu ở nửa sau phần rơi mà không kiểm tra độ sâu.

**Không tái hiện được lỗi actor nhấp nháy độc lập trong baseline đã chụp.** Trong
mẫu cũ, actor chỉ hidden khi opacity cuối bằng 0. Không có bằng chứng static actor
hiện đồng thời hoặc Controller reset trước khi kết thúc. Rig cũ gọi hide/show trong
cùng một main-thread sample; đó là thao tác thừa, không đủ để kết luận là nguyên
nhân của một frame nhấp nháy. Bản mới tránh thao tác đó, giữ node/material/slot/Q.
Không tuyên bố đã chứng minh và sửa một nguyên nhân blink chưa tái hiện được.

## 5. Kiến trúc và đường đi gameplay

```text
Keyboard / Mouse -> UIFlow / GameController._submit_move
 -> action_plan.plan_action -> Board.describe_transition
 -> ROLL / EFFECTS / explicit TERMINAL FALL requests
 -> AnimationManager + AnimationTimeline
 -> FallPlan.sample -> AnimatedActorRig.apply
 -> terminal callback -> Controller FELL -> UI result
```

Off-board không thể tạo snapshot đích hợp lệ: adapter cũ gửi terminal với
`roll_direction`. In-bounds void: ROLL bình thường tới attempted pose rồi terminal.
Fragile: roll -> crack/sag effects 0.12s -> FALL có `collapse_cell`. Bridge/switch,
split/merge vẫn theo request và outcome của Core. GUI không tự suy bridge ẩn là thua.
Không gọi solver hay thêm task/manager/game loop để điều khiển rơi.

## 6. Support, hình học và clearance

Khi submit FALL, manager lấy sàn/cầu hiện diện từ **before snapshot** của request:
FLOOR/FRAGILE còn nguyên, cầu có `present=True`; loại goal và broken fragile.
Tọa độ dùng cùng `cell_to_world`, `pitch` và convention Y giảm theo row.

Contact chỉ phục vụ hình ảnh sau khi caller đã xác nhận FALL. Helper xét footprint
và vùng support nửa ô, chấp nhận seam 0.02 hiện hữu; không đổi kích thước mesh.
Full support, không support, hoặc actor đang cách mặt sàn không được gán pivot giả.

Partial support có contact cuối hợp lý sẽ nghiêng khỏi cạnh đó. Constructor kiểm
tra 12 tư thế nghiêng với các slab lân cận bằng OBB/slab SAT (15 separating axes),
slab giữ nguyên 0.96×0.96×0.18. Tiếp xúc không tính là xuyên thể tích. Việc kiểm tra
này chỉ tránh **tipping xuyên phiến đối diện**, không phải collision engine.

Khi khối đang chắn khe nhỏ không thể xoay qua, chọn `confined-drop`: giữ orientation,
rơi gia tốc từ pose hiện tại và dùng depth occlusion vốn có của sàn. Không ép xoay,
thu nhỏ, teleport hoặc fade sớm. **Fallback có overlap hình học với phần sàn đang
đỡ khối khi đi xuống; không phải rigid-body clearance chính xác.** Ảnh/GIF riêng
được giữ để người review thấy giới hạn này. Core quy định mất một phần support là
thua, dù trong cơ học thật vật rắn có thể bị kẹt. Không sửa luật để giải quyết mâu
thuẫn đó. Interior void đủ rộng và edge thông thoáng dùng quỹ đạo bình thường.

## 7. Tipping mathematics

Với world pivot P, axis A và pose hiện tại C0/Q0:

```text
C(t) = P + R(A, theta(t)) * (C0 - P)
Q(t) = normalize(q_axis(A, theta(t)) * Q0)
theta(t) = omega0*t + 0.5*alpha*t²
```

Quaternion Hamilton `(w,x,y,z)`, world rotation nhân bên trái, cùng convention
RollPlan/Panda Quat hiện có. Không reset về canonical orientation. Partial bắt đầu
từ vận tốc 0 sau endpoint roll đang dừng; trục/pivot giữ tiếp xúc trên cạnh cuối.

## 8. Gravity và tham số

Tại release, lấy chính pose cuối của tipping và vận tốc tiếp tuyến:

```text
v0 = omega × (C_release - P)
p(t) = p_release + v0*t + (0, 0, -0.5*g_visual*t²)
```

Không có contact hoặc không có lịch sử vận tốc đáng tin cậy thì bắt đầu từ nghỉ.
Không giả định world unit là mét. `FallTuning` tập trung các giá trị:

| Tham số mặc định | Giá trị |
| --- | --- |
| Gravity nền | 16 pitch/s² |
| Tip time | tối đa 0.18s, giới hạn theo duration/góc còn lại |
| Partial tip angle | 0.52 rad trước release |
| Fade cuối | tối đa 0.20s và 45% thời gian free fall |
| Độ sâu trước fade | giảm ít nhất 1.1 pitch so với release center |
| Angular retention | 0.35 vận tốc góc release khi kết thúc |

Gravity thực dùng `max(16*pitch, 2*fall_distance*pitch/free_time²)`, bảo đảm khoảng
rơi tối thiểu. `fall_distance` cũ được giữ trong request nhưng nay là **minimum
clearance**, không phải tọa độ Z endpoint chính xác. Đây là visual tuning có chủ
đích; không thay timing request hoặc gameplay. Một unsupported fall 0.9s với gravity
16 có khoảng rơi 6.48 pitch. Tham số phải finite/dương; angular bounds được validate.

## 9. Angular motion, fade và sampling

Free fall tiếp tục quay theo omega release, giảm dần tới 35% để tránh quay quá mức.
Mỗi sample dùng elapsed tuyệt đối, không nhân transform tích lũy qua frame.
Lấy mẫu đảo thứ tự hoặc lặp nhiều lần cho cùng kết quả. Nominal dimensions giữ nguyên;
không scale khối khi rơi. Fade chỉ ở đoạn cuối và sau ngưỡng sâu, opacity cuối bằng 0.
Actor khác không nhận opacity của actor bị rơi; không fade toàn scene.

## 10. Roll -> Fall continuity

Không sửa `animation_math.py::RollPlan`: pivot, circular center path, 90° và easing
bình thường vẫn nguyên. Off-edge dùng đúng prefix RollPlan tới góc cân bằng
`atan2(horizontal_half_extent, vertical_half_extent)`, rồi nối bằng góc/vận tốc hiện
hành. Tip kết thúc ở tổng góc 90°, release giữ đúng C/Q và tangent velocity. Kiểm tra
sai phân ở cả hai ranh giới xác nhận continuity vị trí, quaternion và vận tốc.

Partial trong board bắt đầu sau roll 0.35s, nghiêng tối đa 0.18s rồi ballistic trong
terminal 0.9s. Complete loss không bịa tipping. FALL event có `start/end` riêng vẫn
được retime theo cửa sổ đó; pose giữ nguyên trước start, giữ endpoint sau end,
callback chỉ chạy khi toàn request kết thúc. Timing .9s là terminal, không phải tổng
roll/effects + terminal: partial/interior khoảng 1.25s, fragile khoảng 1.37s ở 1×.

## 11. Actor ownership

Manager tiếp tục là visual owner; static renderer actor bị ẩn trong suốt animation.
Không rebuild mesh, không chuyển rig, không đổi magma material/emission hoặc cube
identity. Rig chỉ hide actor không có trong pose/opacity, không hide/show lặp actor
đang dùng. Split FALL chỉ áp vào `terminal.actor_id`; cube kia giữ node và pose.
Không thay shadow pipeline, Goal Flag, Guide hoặc HUD.

## 12. Cancellation và completion

Tái sử dụng timeline/rate/pause/resume/cancel/resync/dispose sẵn có. FallPlan chỉ là
dữ liệu thuần được tạo một lần/request, không đăng ký callback. Cancel trả CANCELLED
một lần, không phát COMPLETED sau đó; session cũ không thể hoàn thành session mới.
Restart/resync dựng lại pose chuẩn và tài nguyên hiệu ứng theo owner hiện hành.
Bảng kết quả xuất hiện sau khi FALL hoàn tất; không reset actor giữa tip/free fall.

## 13. Gameplay integration và các bất biến

Không sửa `controller.py`, `action_plan.py`, `game_adapter.py`, Core hay solver.
Giữ phân biệt blocked/rejected input và losing move. Các action thắng vẫn đi theo
GOAL_COMPLETE; request ROLL/EFFECTS không có FALL không tạo FallPlan. Bridge/fragile
chỉ gây fall theo explicit outcome; thứ tự effects và fragment collapse cũ giữ nguyên.

Core state/board trước và sau từng losing move được so lại trong native smoke.
Losing move **không tăng Moves** theo Controller hiện có; không đổi hành vi này.
Không thêm Core commit hoặc metrics sample trong frame animation.

## 14. Bộ test

- **16 test mới PASS**: ba tư thế × bốn hướng và cube; initial C/Q chính xác;
  pivot giữ tiếp xúc; unsupported không có pivot; interior clearance; SAT/fallback;
  gravity/tangent; C/Q/velocity liên tục; không NaN, không drift, không fade sớm;
  pause tip/free fall; 0.5×/1×/2×; 30/60/120 FPS cùng endpoint; cancel/dispose/resync;
  stable split node; cửa sổ event; assist không tạo tài nguyên.
- **Full regression 515/515 PASS**, baseline 499/499; không skip hoặc nới clipping,
  geometry, Core, metrics expectations. Output “Missing background” là nhánh negative
  test hiện có; asset được phục hồi, full suite OK.
- Existing suite vẫn kiểm tra goal, fragile fragments, bridge, switches, split/merge,
  replay, metrics và merge đóng cầu làm cả khối rơi. Bridge loss dùng integration
  fixture với injected split state; không gọi nó là route production đã chơi được.
- **14 nhóm native Mechanics Guide PASS**: hai theme, bốn kích thước, chọn/đóng card,
  restart, sáu solver chạy worker thật/metrics và clock replay.
- **33 nhóm native debug assist PASS**: hai mode input, ba camera, split Space,
  hover/click, tutorial, replay Pause/Step, cancel/restart/exit.

[Baseline](evidence/physical-falling/baseline-tests.txt) ·
[16 test mới](evidence/physical-falling/physical-tests.txt) ·
[Full regression](evidence/physical-falling/regression-tests.txt).

## 15. GUI thực và bằng chứng ảnh/clip

Mở Panda3D GraphicsWindow GLX thật. Capture tự động 12 losing moves (sáu cơ chế × hai
theme) qua **production Controller/Core**, không sửa level hoặc inject state. Đường đi
bắt đầu từ spawn, mỗi chữ là một action đã hoàn thành:

| Case | Production level | Đường đi an toàn | Nước gây thua | Motion |
| --- | --- | --- | --- | --- |
| Edge | `level_01.json` | — | U | roll-off |
| Partial | `level_01.json` | — | D | partial tip |
| Interior | `level_04.json` | R D D R R D D D R R | U | unsupported, hai ô trống |
| Confined | `level_04.json` | D R R D R U R R R | D | confined-drop fallback |
| Fragile | `level_05.json` | R | R | crack/fragments rồi unsupported fall |
| Split | `level_15.json` | D R R U L D R | U | chỉ cube được Core chỉ định |

Các clip so sánh từ cùng level/path/theme/camera. “Before” là HEAD `a87f095` được đọc
bằng archive riêng; không checkout/reset nhánh. Mẫu deterministic advance timeline
1/60s, render thật mỗi hai sample; **không trình bày đó là benchmark FPS thực**.
GIF resize/palette để chia sẻ; ảnh PNG chọn lọc là framebuffer gốc 1280×720.

| Loại | Trước | Sau |
| --- | --- | --- |
| Edge | [GIF](evidence/physical-falling/light-edge-before.gif) | [GIF](evidence/physical-falling/light-edge-after.gif) |
| Partial | [GIF](evidence/physical-falling/light-partial-before.gif) | [GIF](evidence/physical-falling/light-partial-after.gif) |
| Interior void | [GIF](evidence/physical-falling/light-interior-before.gif) | [GIF](evidence/physical-falling/light-interior-after.gif) |

Thêm [Fragile](evidence/physical-falling/light-fragile-after.gif),
[Split](evidence/physical-falling/light-split-after.gif),
[Confined fallback](evidence/physical-falling/light-confined-after.gif),
[Dark edge](evidence/physical-falling/dark-edge-after.gif).

Đã tự xem các frame tipping, below-board và terminal: edge/partial nghiêng ra ngoài,
interior đủ rộng giữ tư thế khi rơi; không thấy teleport, reset mặt hoặc mất magma
material trong các mẫu đã chụp. Split giữ cube kia. Confined được đánh giá riêng
với giới hạn hình học ở mục 6, không dùng fade sớm để giấu chuyển động đó.

Có thêm kiểm tra **XTest keyboard và mouse thật** trên cửa sổ Panda3D trong Xvfb:
Up -> FALL -> result -> R; mouse click gây FALL trên Iso/Top/Follow; click HUD Restart;
H mở/đóng Tutorial. Clip [native clock](evidence/physical-falling/native-clock-edge.gif)
đi theo task/clock của ứng dụng, không manual advance. Guide mở trong native fall
vẫn giữ lựa chọn; kết quả chỉ hiện sau animation.

Cũng mở cửa sổ trên **desktop `DISPLAY=:0.0`** và xác minh public Controller action
chạy theo clock đến bảng thua rồi Restart:
[ảnh trước](evidence/physical-falling/desktop-before.png),
[ảnh đang rơi](evidence/physical-falling/desktop-falling.png),
[report](evidence/physical-falling/desktop-report.json).
XTest không đưa được pointer vào MouseWatcher trên desktop này, nên kiểm tra native
input chạy trên Xvfb; không tuyên bố đã click được trên desktop. Desktop capture có
render/screenshot overhead, không dùng để đo độ mượt hay FPS.

[Mouse result](evidence/physical-falling/native-mouse-result.png) ·
[Tutorial](evidence/physical-falling/native-mouse-tutorial.png) ·
[Manifest và các PNG tại 0/25/50/75/100%, thêm tip](evidence/physical-falling/manifest.json) ·
[Production UI report](evidence/physical-falling/controlled-ui-report.json) ·
[Native input report](evidence/physical-falling/native-input-report.json).
Raw report giữ path capture `/tmp` để truy nguồn; các file giao kèm dùng relative path
trong manifest. Interior không có tip vì không có contact; không dựng pivot giả để
đủ tên ảnh.

## 16. Tài nguyên và hiệu năng

20 lần restart giữa fall: **194 scene nodes, 13 tasks gồm delayed, 127 widgets,
1 graphics output** trước/sau bằng nhau trong production smoke. Sau dispose:
**0 task, 0 widget, 0 output, 0 listener**. 15 lượt pause/resume/restart ở ba thời điểm
trên năm cơ chế không có terminal/callback cũ.

FallPlan được tạo một lần khi FALL bắt đầu, support/clearance không quét lại mỗi
frame. Sampling là quaternion/vector thuần. Không thêm Panda task hay allocations
mesh. Default assist bỏ hẳn updater/predictor/nodes. Đây là finite stress check,
không phải chứng minh mọi phiên chạy dài đều không leak, cũng không có FPS benchmark.

## 17. Regression và lệnh tái chạy

```bash
.venv/bin/python -B main.py
.venv/bin/python -B -m unittest discover -s tests
.venv/bin/python -B -m unittest discover -s tests -p 'test_physical_fall.py'
xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.physical_fall_smoke --output /tmp/physical-fall-check
xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.physical_fall_smoke --native-only --output /tmp/physical-fall-native
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.mechanics_guide_smoke --output /tmp/physical-fall-guide
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.move_assist_smoke --output /tmp/physical-fall-debug
```

Xvfb/libXtst/wmctrl là công cụ QA sẵn có của máy này, không phải dependency runtime
mới. Các tool dùng save tạm, không thay profile hoặc production level.

## 18. Giới hạn

- Scripted visual physics, không Bullet/contact solver. Confined fallback có overlap
  hình học được che theo depth của sàn; không bảo đảm cuboid đi qua khe hẹp như vật
  rắn thật. Không mở rộng hole, giảm kích thước khối hoặc thay model để lách giới hạn.
- Ngoài off-board prefix, request không truyền lịch sử vận tốc nên unsupported fall
  từ current visual pose bắt đầu từ nghỉ. Không suy một vận tốc hoặc hướng quay giả.
- Support helper tối ưu cho footprint quarter-turn của request sau roll; không phải
  API dự đoán va chạm cho actor đang chuyển động tự do.
- Gravity và góc tip là visual tuning, không đại lượng vật lý được hiệu chuẩn theo mét.
- Baseline chưa tái hiện blink độc lập; bằng chứng không thể chứng minh hết mọi máy/GPU.
- Native QA hữu hạn, không claim chơi đủ mọi route của 18 level hoặc sáu solver trên
  từng level production; regression solver/metrics và sáu nút chạy thật được kiểm tra
  riêng bằng suite/Guide smoke.

## 19. Điểm cần nhóm xác nhận

Không có blocker Core/Controller cho luồng hiện tại: explicit outcome, stable cube ID,
bridge flags và terminal callback đã có đầy đủ. Nếu sau này nhóm muốn va chạm vật rắn
thật ở confined void, cần chốt presentation policy hoặc thay đổi rules/geometry ở
một task riêng; bản này không tự ý sửa phần của Phong/Tài.

## 20. Git scope và quality gates

- A PASS: warning/OK mặc định không dựng node/task; input và Guide giữ nguyên.
- B PASS trong phạm vi scripted motion và fallback công khai: edge/partial có
  contact/tangent, unsupported ballistic; C/Q/velocity continuity được test. Không
  gọi fallback là mô phỏng va chạm chính xác hoặc che giấu giới hạn đó.
- C PASS: production losing moves nối manager thật, state không đổi, cancel/restart
  sạch, result chờ terminal.
- D PASS: 515 test, native UI, PNG/GIF và stress cleanup; không bỏ failure baseline.

Không sửa Core, Controller, solver, level, asset, shader, model hoặc rolling math.
Không thêm thư viện. Không commit/push/merge/checkout/reset/clean/stash/rebase.
Toàn bộ thay đổi để nguyên working tree cho Phước review.

## Follow-up: F1/F2 và UI polish

Báo cáo này ghi kết quả của đợt Physical Falling trước đó (515 test). Đợt sửa tiếp
ngày 27/10/2026 bổ sung GUI adapter cho in-grid open-void F1/F2, card Guide overlay
không refit viewport và toolbar/robot. Xem [báo cáo mới](BUGFIX_FALLING_GUIDE_TOOLBAR.md)
cho source ownership, 521 test và bằng chứng native/desktop mới nhất.
