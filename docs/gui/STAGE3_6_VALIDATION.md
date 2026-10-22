# Stage 3.6 — End-to-end Validation, Stability & Performance

Thực hiện ngày **22–23/10/2026**, Asia/Ho_Chi_Minh. Phụ trách: Phước.

**STAGE 3.6 VALIDATION COMPLETE** trên Ubuntu runtime được kiểm tra dưới đây.
Windows **NOT TESTED**. Kết quả này nghiệm thu Basic Renderer tĩnh 3.1–3.5,
không nghiệm thu gameplay, solver GUI, replay, animation hoặc Advanced Mechanics.

## 1. Mục tiêu

Kiểm chứng pipeline thật, visual desktop, lifecycle khi thao tác lặp, tài nguyên,
frame timing và regression. Ưu tiên bằng chứng; chỉ sửa lỗi nhỏ được cấp quyền.
Không refactor renderer/camera hoặc tối ưu khi chưa chứng minh bottleneck.

## 2. Repository state và preflight

| Hạng mục | Trạng thái lúc bắt đầu |
| --- | --- |
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `956c0a0528c9170afceda58551772bcadd3fc12a` |
| Tracked modification | `src/gui/renderer.py`, implementation có sẵn từ 3.3 |
| Untracked | 28 files GUI/tests/reports 3.1–3.5, cần bảo toàn |
| Staged diff | Rỗng |
| Manifest | SHA-256 của 66 files tracked/untracked không bị ignore |
| Baseline .venv | 224 PASS, 0 FAIL/ERROR/SKIP |
| Baseline system | Ran 224: 155 PASS, 69 SKIP, 0 FAIL/ERROR |

Đã đối chiếu tài liệu Chặng 2, báo cáo 3.1–3.5, source và tests hiện tại.
Không lấy báo cáo lịch sử thay bằng chứng runtime. Regression vector-copy
được sửa trong 3.5 vẫn giữ nguyên; không sửa thêm helper hoặc existing tests.
Không fetch/pull hoặc khẳng định remote freshness.

## 3. Environment và dependency integrity

- Ubuntu 26.04.1 LTS x86_64, Linux 7.0.0-38-generic, X11 `DISPLAY=:0.0`.
- GUI `.venv/bin/python`: CPython 3.14.4, Panda3D 1.10.16.
- Native output: **GraphicsWindow**, GLX; không dùng offscreen làm desktop evidence.
- GPU: AMD Radeon Graphics, radeonsi/renoir/ACO.
- Driver: OpenGL 4.6 Compatibility Profile, Mesa 26.0.8-1ubuntu0.3.
- `pip check`: No broken requirements found.
- Không cài dependency, sửa Python hệ thống hoặc shared requirements.
- Smoke tool chỉ dùng stdlib/Panda có sẵn. Native open/close/title checks dùng
  `wmctrl` và `xprop` đã có; X11 minimize fallback dùng libX11 hệ thống qua ctypes.
  Đây là nhu cầu của QA harness, không phải dependency mới của application.

## 4. Files tạo/sửa

| File | Công việc |
| --- | --- |
| `tests/test_gui_stage3_6_integration.py` | Mới; 6 tests toàn pipeline, fixture host không mở window |
| `tests/test_gui_stage3_6_stability.py` | Mới; 6 stress/lifecycle/failure tests |
| `tests/test_gui_stage3_6_quality.py` | Mới; 7 tests import isolation, camera matrix, contrast, invalid sizes và title |
| `tools/gui_stage3_6_smoke.py` | Mới; tái lập onscreen screenshots, stress, profiling, native entry points |
| `docs/gui/STAGE3_6_VALIDATION.md` | Mới; báo cáo này |
| `src/gui/dashboard_preview.py` | Sửa đúng 4 dòng: request title trên existing window |

Source của Phong/Tài, production levels, renderer, contracts, geometry,
camera, lighting, host và báo cáo/tests cũ đều giữ nguyên.

## 5. Test strategy và rủi ro

Ba lớp bằng chứng:

1. Pure tests: DTO/math/layout/validation/import isolation, chạy được không Panda.
2. Engine node integration: real Core/adapter, GeomNode, lens, lights, DirectGUI,
   messenger; window/region doubles được ghi rõ, không tạo ShowBase/window.
3. Onscreen runtime: create_dashboard → existing create_preview → một ShowBase,
   actual GraphicsWindow, actual DisplayRegion/pixels, resize/minimize, capture.

Rủi ro kiểm tra chính: revision mismatch, goal profile sai, stale data, quaternion
drift, board rebuild khi update block, resize listener/widget duplication,
cleanup scene bị detach, title cũ và frame timing bị nhiễu bởi minimized window.

## 6. End-to-end pipeline với real level

`levels/level_01.json` hiện tại vẫn là 4×7, initial `(1,1)`, goal `(1,6)`.
Adapter xuất StaticBoardData với 8 VOID, 20 surface cells; renderer tạo
**19 Floor instances + 1 Goal instance**, một MainBlockVisual.
Goal world XY `(3,0.5)`, initial block center `(-2,0.5,1)`.

Đã kiểm Board/State → Adapter → DTO → Renderer → camera/lights → viewport/HUD
trong tests và Dashboard desktop thật. Core grid/state hash không thay đổi.
Tests đặt transition thành lỗi nếu bị gọi để phát hiện gameplay ngoài quyền.
HUD không đọc Core, gọi solver hoặc tự tạo metrics. Những lần reload fixture
trong harness refit existing camera có chủ ý; đó không phải level Controller mới.

## 7. Orientation và geometry

Đọc real transformed tight bounds, không chỉ so công thức với chính nó:

| Pose tại anchor (1,1) | Center | Dimensions X/Y/Z | Bottom Z |
| --- | --- | --- | ---: |
| STANDING | (-2, 0.5, 1) | (1,1,2) | 0 |
| HORIZONTAL | (-1.5, 0.5, 0.5) | (2,1,1) | 0 |
| VERTICAL | (-2, 0, 0.5) | (1,2,1) | 0 |

Node scale luôn (1,1,1), dùng cùng block/prototypes. Snapshot updates không
refit camera. Floor/Goal/void topology và normal/winding tests cũ tiếp tục PASS.
Goal lấy từ goal_cells; chuyển goal sang FLOOR mã 1 vẫn đổi đúng mesh, còn
raw code 2 ngoài goal vẫn là Floor. Không có Floor solid lấp aperture.
Depth thật 0.14 theo nhiệm vụ 3.3; giá trị 0.65 trong đề xuất Stage 2 là lịch sử,
không phải regression. Aperture 0.76 nhỏ hơn block 1.0 vẫn là rủi ro goal-sink
animation về sau, không thay luật hoặc geometry tại 3.6.

## 8. Fixture matrix

Fixtures immutable, chỉ nằm trong QA tool/tests; không thêm level production
hoặc khẳng định fixtures có lời giải gameplay.

| Case | Shape | Mục đích | Kết quả |
| --- | --- | --- | --- |
| Real level | 4×7 | Pipeline thực tế, 3 poses, void/goal | PASS |
| wide | 3×15 | Fit ngang, goal cạnh xa | PASS |
| tall | 15×3 | Fit dọc | PASS |
| square | 10×10 | Envelope diện tích lớn | PASS |
| basic fixture | 4×7 | Grid full-floor độc lập với real map | PASS |
| sparse | 6×9, chỉ 6 FLOOR | VOID nhiều, hai nhóm geometry rời | PASS |
| tiny | 1×1 | Board nhỏ, standing | PASS |
| edge-goal | 3×5 | Goal sát cạnh trên/phải | PASS |

Tiny fixture có block đứng trên goal duy nhất nên block che goal là đúng theo
góc nhìn; goal recess được kiểm tra ở các case khác và mesh tests.

## 9. Viewport/resize matrix

| Native client | Actual 3D region | VFOV | Lens aspect |
| --- | --- | ---: | ---: |
| 1280×720 | 934×530 | 45° | 1.762264 |
| 1366×768 | 1020×578 | 45° | 1.764706 |
| 1920×1080 | 1574×890 | 45° | 1.768539 |
| 1024×768 | 678×578 | 45° | 1.173010 |
| 1024×720 | 678×530 | 45° | 1.279245 |
| 640×480 | 3D inactive, warning HUD | Giữ fit trước | N/A |

Readback pixel dimensions khớp. Azimuth/elevation vẫn 30°/45°, padding .13.
Toàn envelope corners nằm trong NDC ±.74 và near/far; lighting lens cũng chứa
bounds. UI không scale thành một ảnh, HUD widgets/listener identities ổn định.
Zero size test giữ fit cũ. Native minimize/restore PASS: WM không xác nhận
Panda minimized property request trực tiếp, nên harness iconify **chính X11
window của nó**, nhận readback minimized=True, sau đó activate/restore với
readback False. Không chỉnh engine-global handlers hoặc foreign windows.

## 10. Visual quality và UI/UX audit

Đã mở và xem từng ảnh gốc: 15 visual cases + 3 performance profile images.
Floor top/side/bevel phân biệt, block có thể tích; goal interior đủ tối, void
trống, không ground plane. Không thấy clipping/missing faces/Z-fighting mới
hoặc shadow acne đáng kể trong những case được kiểm tra. Shadow nằm trên
floor receiver, không có một miếng shadow plane che void/HUD.

Header/Panel/Status thống nhất, solver grid dễ đọc ở 1024×720, caption không
tràn, board không bị HUD che. Các buttons nhạt và có caption chưa kết nối;
kiểm state disabled thật riêng bằng GUI item readback. Nhãn English, em dash
và ASCII `1.0x` không có missing-glyph warning trong runs hợp lệ.
Pure contrast check: TEXT_SECONDARY/trắng ≥4.5:1; không suy ra toàn UI đã
được chứng nhận accessibility, đặc biệt disabled control text dùng nền khác.

## 11. Window title và board occupancy

**P2 title — đã sửa:** Dashboard trước đó dùng `Renderer Foundation`.
Trong create_dashboard, request WindowProperties title `Bloxorz Solver — 3D Preview`
trên app.win hiện có. Không sửa app.py hoặc mở window mới. Test title request,
failure cleanup và native `_NET_WM_NAME` readback xác nhận. Foundation và Board
Preview vẫn giữ title `Bloxorz Solver — Renderer Foundation`.

**Occupancy — không là camera failure:** Project tất cả vertices thật của
static board và block qua camera fit. Đơn vị rect/margins là viewport pixels,
origin góc trên trái viewport (chưa cộng offset viewport vào window).

| Client | Board+block projected width×height | Occupancy ngang/dọc |
| --- | --- | --- |
| 1280×720 | 383.20×283.44 | 41.03% / 53.48% |
| 1366×768 | 417.91×309.11 | 40.97% / 53.48% |
| 1920×1080 | 643.49×475.97 | 40.88% / 53.48% |
| 1024×768 | 380.51×279.51 | 56.12% / 48.36% |
| 1024×720 | 376.29×277.94 | 55.50% / 52.44% |

Reference rect `(286.19,123.61,383.20,283.44)` trong viewport 934×530;
margins trái/phải/trên/dưới = 286.19/264.61/123.61/122.94px.
JSON còn có projected rectangle **board riêng** để tách khỏi block.
Khoảng trống do fit toàn grid gồm VOID và toàn chiều cao block 2.30 trên mọi
cell, target/bounds bảo thủ, padding 13% mỗi phía và viewport aspect. Không
giảm padding hoặc đổi thuật toán camera để lấp viewport. Nếu muốn zoom hơn,
cần proposal riêng so full envelope với visible-surface/whole-block envelope,
giữ projection validation và review continuity khi đổi pose/level.

## 12. Lifecycle và failure paths

- Normal native close: cả ba entry points exit 0.
- Normal dispose, repeated dispose và gọi update sau dispose có kiểm tra.
- Dashboard dispose trả full-window Board Preview binding; recreate trên cùng
  host hoạt động, không tạo ShowBase thứ hai.
- Partial HUD failure sau khi tạo một phần controls: xóa widgets/root đã sở hữu,
  trả node/subscription counts về trước.
- Partial viewport setup failure: HUD được hủy, existing preview vẫn sống.
- Title request failure: presentation/renderer/host được cleanup theo thứ tự.
- Existing main-loop exception và detached-scene host shutdown tests vẫn PASS.
- Renderer/GUI foreign nodes, application roots và 2D regions không bị xóa nhầm.
- Cuối các completed onscreen runs: engine outputs, kể cả shadow buffer, =0.

Không dùng catch-all để nuốt lifecycle errors. QA tool chuyển SystemExit sớm
trong một lượt đo thành lỗi rõ, không coi việc đóng preview giữa chừng là một
measurement đã hoàn thành.

## 13. Stress tests đã thực thi

| Lớp | Thao tác | Kết quả |
| --- | --- | --- |
| Automated | 500 valid snapshots, xen kẽ ba poses | PASS |
| Automated | 100 board reloads, same/new revisions/different shapes | PASS |
| Automated | 140 resize sizes, mỗi size gửi cả aspect/window events | PASS |
| Automated | 40 dashboard create/dispose cycles | PASS |
| Onscreen tool | 3×500 snapshots | PASS |
| Onscreen tool | 70 reloads, mỗi board load lặp để kiểm no-op | PASS |
| Onscreen tool | 35 native resize requests, 5 chuỗi gồm fallback/restore | PASS |
| Onscreen tool | 60 dashboard recreations | PASS |
| Memory investigation | 120 rồi 400 dashboard recreations, có GC | PASS về resource counts; heap drift ghi mục 18 |

Snapshot stress giữ nguyên block node, board content node, vertex buffers,
mesh prototypes, camera transform và DTO hash; quaternion được đặt tuyệt đối,
không nhân dồn. Reload loại tiles cũ và giữ foreign nodes. Invalid board/snapshot
không phá scene đã hiển thị.

## 14. Resource-count observations

Real level Basic, sau warm-up và sau stress:

| Resource | Trước / sau |
| --- | --- |
| Scene paths, gồm các instance paths | 52 / 52 |
| Static subtree paths | 42 / 42 |
| Block subtree paths | 3 / 3 |
| Owned HUD widgets | 42 / 42 |
| HUD subtree paths | 44 / 44 |
| Registered DirectGUI widgets, gồm slider thumb | 43 / 43 trong memory investigation |
| Live HudShell instances sau GC | 1 / 1 |
| Main-camera regions | 1 / 1 |
| Main-window regions, gồm engine overlays | 4 / 4 |
| Native GraphicsWindow | 1 / 1 |
| Light nodes | 3 / 3 |
| window-event subscriptions | 2 / 2 (host + camera) |
| aspectRatioChanged subscriptions | 1 / 1 |
| Total messenger subscriptions | 20 / 20 |
| Basic graphics outputs / shadow buffers | 1 / 0, ổn định |
| Enhanced graphics outputs / shadow buffers | 2 / 1, ổn định |
| Outputs sau destroy | 0 |

Đây là số tài nguyên quan sát được trong những chuỗi hữu hạn, không là đo
mọi allocation C++ hoặc chứng minh không thể leak VRAM trong mọi tình huống.

## 15. FPS methodology

Mỗi profile chạy process mới (Panda cache framebuffer defaults), cùng level thật,
STANDING, client 1280×720, viewport 934×530, GPU/backend trên. Warm-up **80 frames**,
đo **360 frames**. Đo wall-clock `taskMgr.step()` + `graphicsEngine.syncFrame()`
bằng perf_counter; mean/median/p95 frame time, p95 dùng nearest-rank.
Không artificial sleep trong measured loop. Request `sync-video=false` cho cả ba.

Recorded valid runs đều **360 foreground frames, 0 minimized frames**. Desktop
compositor/driver hoặc background apps vẫn ảnh hưởng; nhịp ~60 FPS cho thấy
có pacing, không dùng con số này làm maximum GPU throughput/KPI mọi máy.
Đây không phải GPU-only timing. Không dùng unittest elapsed time để suy FPS.

## 16. Frame timing results

| Profile | Frames | Elapsed s | Mean FPS | Mean ms | Median ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Basic, shadows OFF, AA default | 360 | 5.994808 | 60.052 | 16.639 | 16.633 | 16.911 |
| Enhanced, shadows ON, AA default | 360 | 5.995277 | 60.047 | 16.643 | 16.628 | 17.074 |
| Basic, AA OFF | 360 | 5.995052 | 60.050 | 16.641 | 16.645 | 17.497 |

Các profiles không khác đáng kể về mean ở pacing này. Không kết luận shadow
miễn phí hoặc AA OFF chậm hơn từ p95 của một run. Chưa chứng minh bottleneck
cần optimization. Không so trực tiếp với lịch sử 3.4 ~60/~49 FPS: full-window
scene 3.4 khác số pixel 3D Dashboard hiện tại và điều kiện desktop không độc quyền.

## 17. Memory methodology

Tracemalloc bắt đầu sau khi host/scene/HUD ban đầu đã tạo và warm-up. Mỗi sample
gọi GC, ghi current/peak Python traced bytes và resource counts. Vì vậy số này
**không phải tổng Python memory của ứng dụng từ startup**, process RSS, C++ heap
hoặc GPU/VRAM. Không đo RSS/VRAM trong chặng này. Peak của GC enumeration hoặc
snapshot profiler cũng thuộc overhead QA. Không đưa profiling numbers vào HUD.

Investigation riêng so tracemalloc snapshots sau 20 và 120/400 recreations,
đếm DirectGUI registry và live HudShell để phân biệt một HUD hiện tại với
HUD cũ bị giữ. Harness có `--recreates 400` để tái lập chuỗi dài hơn mặc định.

## 18. Memory observations và giới hạn kết luận

Completed desktop stress 60 cycles, có object counters:
current cuối khoảng **310,482 B**, peak **756,970 B**. Live HudShell=1 và
DirectGUI registry=43 ở cả ba batches. GC object enumeration góp phần vào
peak của profiler. Một HUD được tạo lại sau khi tracing
bắt đầu sẽ có allocations được track, còn HUD ban đầu trước tracing không có;
do đó tăng từ initial traced 0 không tự chứng minh leak.

Trong investigation 400 cycles: current sau 20/100/200/400 lần là
293,247 / 308,549 / 316,027 / 325,631 B. Sample records được cố ý giữ trong list:
top growth có ~8.8KB từ resource dictionaries và ~6.9KB từ script log/counters.
Các allocations khác tập trung ở OnscreenText configure/getters/scale tuples
và live HUD wrappers; không có thêm HudShell/widget registry entries hoặc nodes.
Increment giảm từ ~7.9KB cho batch 20→40 xuống ~0.75KB cho batch 380→400.

Không đủ bằng chứng gọi đây là leak P1; cũng **không khẳng định heap plateau
hoàn toàn hoặc tuyệt đối không leak**. Theo dõi dài hạn là P3, đặc biệt khi
thêm Controller/animation. Không sửa engine hoặc HUD để ép memory số học giảm.
Resource observations và trace locations nằm trong JSON/logs mục 23.

## 19. Shadow/AA comparison

Basic và Enhanced cold-process request AA default: actual framebuffer **8 samples**.
AA OFF: actual **0 samples**. Enhanced có một actual shadow buffer; controller
giữ status `ENABLED_UNVERIFIED` theo API cũ, còn ảnh được xem xác nhận bóng block
đúng trên floor, không tràn HUD, không thấy acne đáng kể ở case này.
Basic vẫn default. Không đổi shadow bias/resolution/materials hoặc shader.

## 20. Tests mới và lệnh tái lập

19 methods mới: integration 6, stability 6, quality 7. 15 cần engine được skip
rõ khi interpreter không có Panda; 4 pure quality tests vẫn chạy. Existing tests
không bị sửa. Import toàn bộ GUI tests/entry points không tạo window/ShowBase.

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_stage3_6_*.py'
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests

.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode visual
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode stress
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode stress --recreates 400
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode profile --profile basic
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode profile --profile enhanced
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode profile --profile no-aa
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode entrypoints
```

Chạy profiling tuần tự, giữ preview mở và không minimize trong measured frames;
tool tự cleanup sau run. `--output` mặc định `/tmp/bloxorz-stage3-6`, có thể đổi.
Visual-review field trong machine capture JSON để PENDING có chủ ý; bản review
ảnh thực tế nằm riêng trong visual-review.json. File JSON thành công có thể từ
completed run trước nếu một run mới abort; kiểm cả stderr/exit status, không dùng
file tồn tại làm bằng chứng run mới đã PASS.

## 21. Full regression results

| Run | Ran | PASS | FAIL | ERROR | SKIP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline .venv | 224 | 224 | 0 | 0 | 0 |
| Baseline system | 224 | 155 | 0 | 0 | 69 |
| New 3.6 tests | 19 | 19 | 0 | 0 | 0 |
| Final .venv | 243 | 243 | 0 | 0 | 0 |
| Final system | 243 | 159 | 0 | 0 | 84 |

Final runs 2.266s/.venv và 0.710s/system. System skips vì thiếu Panda3D, không
gộp SKIP vào PASS. Không có regression mới. Lỗi tests title trước patch là
red test của behavior chưa triển khai, không là baseline failure; sau patch
title/failure-cleanup cases đều PASS.

## 22. Foundation/Board/Dashboard compatibility

Ba entry points đều mở native window đúng PID, nhận native window-manager
close và exit 0, không traceback. `_NET_WM_NAME` xác nhận title Foundation và
Board cũ giữ nguyên, Dashboard đổi đúng title. Foundation source và Board
Preview không thay byte nào; Board Preview vẫn full-window 3D.

```bash
.venv/bin/python -B -m src.gui.app
.venv/bin/python -B -m src.gui.board_preview
.venv/bin/python -B -m src.gui.dashboard_preview
```

## 23. Screenshots/log paths và review

Root evidence: **`/tmp/bloxorz-stage3-6/`**, không đưa PNG vào repository.

| Evidence | Tên file dưới evidence root |
| --- | --- |
| Năm sizes thật | `real-standing-1280x720.png`, `real-standing-1366x768.png`, `real-standing-1920x1080.png`, `real-standing-1024x768.png`, `real-standing-1024x720.png` |
| Hai poses khác | `real-horizontal.png`, `real-vertical.png` |
| Fallback | `small-fallback-640x480.png` |
| Shape matrix | `fixture-wide.png`, `fixture-tall.png`, `fixture-square.png`, `fixture-basic.png`, `fixture-sparse.png`, `fixture-tiny.png`, `fixture-edge-goal.png` |
| Profiles | `profile-basic.png`, `profile-enhanced.png`, `profile-no-aa.png` |
| Technical visual matrix/occupancy | `visual.json` |
| Manual image review, 18 originals | `visual-review.json` |
| Stress/resources/traced memory | `stress.json` |
| Frame timing/driver/window state | `profile-basic.json`, `profile-enhanced.json`, `profile-no-aa.json` |
| Native titles/exit codes | `entrypoints.json`, `before-title/entrypoints.json` |
| Extra heap investigation | `memory-investigation.json`, `memory-investigation-long.json` |
| File ownership/patch audit | `scope.json` |

Run logs: `/tmp/bloxorz-stage3-6-visual.log`, `...-stress.log`,
`...-entrypoints.log`, `...-profile-basic.log`, `...-profile-enhanced.log`,
`...-profile-no-aa.log`, `...-memory.log`, `...-memory-long.log`.
Unqualified FPS runs giữ riêng `profile-basic-unqualified.json` và
`profile-enhanced-unqualified.json`; không dùng cho bảng số cuối.
Local memory probe source: `/tmp/bloxorz-stage3-6-memory-check.py` và
`/tmp/bloxorz-stage3-6-memory-check-long.py`; core lifecycle sequence cũng được
tái lập bằng repo smoke tool. `/tmp` là artifacts tạm, có thể mất sau reboot.

## 24. Bugs/findings discovered

| Priority | Phát hiện | Owner / xử lý |
| --- | --- | --- |
| P2 | Dashboard dùng Foundation desktop title | Sửa trong dashboard_preview.py |
| P3 | Occupancy conservative, nhiều khoảng trống | Giữ camera; proposal zoom riêng nếu muốn |
| P3 | Small traced heap drift qua repeated GUI recreation | Đã điều tra; counts ổn định, cần soak dài hơn để kết luận tuyệt đối |
| QA harness | Native map/resize bất đồng bộ gây capture/timeout quá sớm | Chờ trạng thái/thời gian native, không sửa production |
| QA harness | FPS lúc window minimized bị khoảng nghỉ ~100ms của ShowBase | Ghi foreground/minimized từng frame, loại unqualified runs |
| QA harness | Preview đóng giữa profiling có thể exit 0 nhưng chưa có result | Chuyển SystemExit sớm thành lỗi validation rõ, cleanup vẫn chạy |

Không phát hiện P0 hoặc P1 thuộc Basic Renderer trong matrix/chuỗi đã chạy.
Một combined profiling attempt bị native close giữa chừng, đã abort, không
được dùng thay ba completed qualified runs. Không sửa engine để ngăn user close.

## 25. Bugs fixed trong scope

Production patch duy nhất: bốn dòng trong create_dashboard tạo WindowProperties,
set title và request trên window sẵn có. Có red/green title test, test failure
cleanup và native UTF-8 title readback. Không đổi public API hoặc default title
của host cũ. QA tool sửa các vấn đề đo/capture như mục 24; không thay assertion
cũ để che lỗi, không nới geometry/frustum tolerances.

## 26. Deferred issues

- P3 occupancy/zoom tuning: chỉ đề xuất riêng, không giảm padding tùy tiện.
- P3 long-duration heap/C++/VRAM soak sau khi có Controller/animation.
- Goal-sink clearance, advanced state/events và callback contracts tiếp tục
  theo handoff cũ; chưa là feature Basic được nghiệm thu ở đây.
- Không kiểm tất cả hardware/driver, native Windows hoặc arbitrary Unicode fonts.
- Không kết luận về sáu solver algorithm hoặc benchmark bài nộp từ GUI QA này.

## 27. Windows checklist — NOT TESTED

Thực hiện trên Windows native, không dùng wheel availability/Wine làm evidence:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install panda3d==1.10.16
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
.\.venv\Scripts\python.exe -B -m src.gui.app
.\.venv\Scripts\python.exe -B -m src.gui.board_preview
.\.venv\Scripts\python.exe -B -m src.gui.dashboard_preview
```

- [ ] Ghi OS/Python/GPU/driver/engine và actual client pixel sizes.
- [ ] Kiểm DPI 100/125/150%, font/emdash/labels.
- [ ] Năm sizes + small fallback, minimize/restore, normal close.
- [ ] Ba poses, wide/tall/square/sparse/edge goal.
- [ ] AA readback và shadow ON/OFF/fallback.
- [ ] Repeated Dashboard dispose/recreate, node/region/listener counts.
- [ ] Profile với cùng methodology, ghi foreground/minimized/compositor.

X11-specific native close/iconify trong QA tool không portable sang Windows;
dùng native manual open/close hoặc harness phù hợp để kiểm các bước đó.

## 28. Known limitations

Đây là finite Basic validation, không exhaustive proof. Desktop có các app khác
chạy; không là isolated GPU benchmark. Không đo C++ heap/RSS/VRAM. Native
map/focus/minimize phụ thuộc WM. Built-in font không bảo đảm Unicode mọi tên
level. Controls cố ý disabled, không có game/session/replay/solver/animation.
Chưa ≥10 production levels. Evidence tạm không phải source asset.

## 29. Integration risks với Phong/Tài

Phong cần xác nhận authoritative tile schema, bridge IDs/states, split/active
cube và outcome/event order, terminal fall/goal semantics trước Advanced.
Giữ geometry/camera envelope phù hợp nếu mới có objects vượt Basic bounds.

Tài cần xác nhận main-thread ownership, một ShowBase/lifecycle, session/revision
filtering, reset/cancel/resync, solve origin và worker không chặn main loop.
HudViewModel time dùng ms, memory bytes; solver metrics hiện dùng đơn vị khác
cần đổi rõ tại boundary, không nhầm traced Python peak với RSS/VRAM. Không
enable buttons hoặc dùng NodePaths nội bộ làm Controller API trong chặng này.

## 30. Git diff/ownership report

Đối chiếu 66 hashes preflight: chỉ dashboard_preview.py đổi với title patch
bốn dòng; **65 file còn lại giữ nguyên**, không mất file. Tạo đúng năm file
mục 4. Tracked renderer diff là thay đổi có sẵn, không thuộc patch 3.6.
Vì files 3.1–3.6 phần lớn untracked, git diff đơn thuần không mô tả hết;
manifest/file inventory và review source được dùng bổ sung.

Staged diff vẫn rỗng, `git diff --check` sạch, branch/HEAD không đổi.
Không fetch/pull/checkout/reset/clean/stash/rebase/merge/commit/push.

## 31. Quality gates và acceptance matrix

Gates A Correctness, B Visual, C Lifecycle/Stability, D Performance/Memory,
E Regression/Platform reporting: **PASS trong phạm vi Ubuntu đã kiểm tra**.

| ID | Tiêu chí | Trạng thái / evidence |
| --- | --- | --- |
| A1 | Core→Adapter→Renderer real level | PASS — integration + native Dashboard |
| A2 | Standing/Horizontal/Vertical | PASS — transformed bounds + ảnh |
| A3 | Goal/Void | PASS — counts, authority, mesh tests, sparse/edge ảnh |
| A4 | Không mutate DTO/Board/State | PASS — hashes/copies/stress |
| A5 | HUD binding | PASS — real widget text/disabled readback |
| A6 | Invalid inputs | PASS — rejected, scene cũ giữ nguyên |
| B1 | Real desktop visual | PASS — GraphicsWindow, 18 originals đã xem |
| B2 | Năm sizes | PASS — pixel/lens readback + ảnh |
| B3 | Wide/tall/square | PASS — DTO matrix + native images |
| B4 | Không serious clipping/overlap | PASS — frustum + visual |
| B5 | Lighting/material/gradient | PASS — inherited tests + profile ảnh |
| B6 | Window title đánh giá | PASS — patch + native readback |
| B7 | Board occupancy đánh giá | PASS — actual vertex projection |
| C1 | Snapshot stress | PASS — 500 automated, 1500 native |
| C2 | Board reload stress | PASS — 100 automated, 70 native |
| C3 | Resize stress | PASS — 140 automated, 35 native + minimize/restore |
| C4 | Dispose/cleanup | PASS — normal/partial failures/recreate/close |
| C5 | Không NodePath accumulation | PASS — finite resource counts ổn định |
| C6 | Không widget duplication | PASS — 42 owned, 43 registry |
| C7 | Không DisplayRegion duplication | PASS — main=1, window regions=4 |
| C8 | Không listener accumulation | PASS — window=2, aspect=1, total=20 |
| D1 | Basic FPS | PASS — 360 measured frames |
| D2 | Enhanced FPS khi hỗ trợ | PASS — supported + actual shadow buffer |
| D3 | AA ON/OFF đối chiếu | PASS — cold process 8/0 samples |
| D4 | Frame timing | PASS — mean/median/p95, window-state counters |
| D5 | Memory observations đúng nghĩa | PASS — traced Python, GC/counts/drift giải thích |
| D6 | Không suy VRAM từ tracemalloc | PASS — RSS/C++/VRAM không được đo |
| E1 | Full unittest | PASS — 243/243 .venv |
| E2 | Không regression mới | PASS — baseline/full results |
| E3 | Test isolation | PASS — -S import + zero windows khi discover |
| E4 | Foundation | PASS — native open/close exit 0 |
| E5 | Board Preview | PASS — native open/close exit 0 |
| E6 | Dashboard Preview | PASS — native matrix/close/title |
| E7 | Source Phong/Tài giữ nguyên | PASS — manifest |
| E8 | Windows báo trung thực | PASS — runtime Windows NOT TESTED, checklist mục 27 |
| E9 | Git scope | PASS — hashes, branch/HEAD/index |
| E10 | Documentation | PASS — tài liệu này, commands và evidence |

Windows native: **NOT TESTED**. GPU-only timing/RSS/VRAM: **NOT TESTED**.
Long-duration soak vô hạn: **NOT TESTED**; không phải một claim đã PASS.

## 32. Trạng thái cuối

**STAGE 3.6 VALIDATION COMPLETE** trên Ubuntu hiện tại: Basic integration đúng,
full regression PASS, desktop visual/stability checks PASS, hiệu năng được đo
có điều kiện rõ, không còn P0/P1 được phát hiện trong scope, ownership giữ nguyên.
Các giới hạn và P3 observations không bị che thành cam kết cross-platform/zero-leak.

## 33. Điều kiện chuyển sang Stage 3.7

Phước review source/tests, ảnh, occupancy và số đo; thống nhất các P3 cần theo
dõi. Duyệt bàn giao Basic trước khi mở nhiệm vụ 3.7. Phong/Tài xác nhận phần
contracts/lifecycle liên quan trước khi tích hợp. **Dừng ở 3.6**, không tự triển
khai 3.7/Advanced/Controller/animation; không tự commit hoặc push.
