# Stage 5 — Continuous 3D Animation System

**STAGE 5 VISUAL ANIMATION SYSTEM COMPLETE — INTEGRATION PENDING**

Ngày QA: 2026-10-23. Phước / GUI & Renderer. Mọi fixture có provenance
**ANIMATION DEMO DATA — NOT AUTHORITATIVE GAMEPLAY**. Đây là review package,
không phải thỏa thuận API nhóm đã được duyệt. Không triển khai Stage 6.

## 1. Repository / baseline / scope

| Preflight | Kết quả |
| --- | --- |
| Branch | `feat/phuoc/3d-renderer` |
| Current HEAD trước triển khai | `d1c5960769cf1ff7766cb8c9b6ef3f0d0fcd1bca` |
| Tracked/staged/untracked ban đầu | Sạch |
| Baseline | 296/296 PASS, 2.933 s |
| Environment | Ubuntu 26.04.1 X11, Python 3.14.4, Panda3D 1.10.16 |
| Graphics | Onscreen GraphicsWindow; AMD Radeon Graphics/radeonsi/renoir/ACO, Mesa 26.0.8, GL 4.6 |
| Core Advanced | Chưa có semantic definitions/events/outcomes; adapter pending |
| Controller | Chưa tích hợp gameplay/session/replay |
| Windows native | NOT TESTED |

Đối chiếu source Basic/Advanced DTO, adapter, mesh origins/math, renderers,
Camera/Lighting/Style, responsive viewport/HUD và preview composition. Các tài liệu
Stage 3 handoff/API/team review/release checklist và hai báo cáo Stage 4 là baseline
lịch sử; không sửa các tài liệu đó để tuyên bố integration.

Chỉ thay đổi một file cũ: `src/gui/advanced_renderer.py` (+16/-1 dòng), thêm actor
visibility lease. Không sửa Core, Controller, Solver, root main.py, levels,
requirements, Basic schema 1, Advanced schema 2, Basic renderer, camera/light/HUD.
Không fetch/pull/checkout/stash/reset/clean/rebase/merge/create branch/commit/push.

## 2. Files và kiến trúc

| File mới | Trách nhiệm |
| --- | --- |
| `src/gui/animation_contracts.py` | Immutable animation schema 1, explicit events/results, consistency validation |
| `src/gui/animation_math.py` | Pure Hamilton quaternion/vector, rigid roll plan, canonical resync poses |
| `src/gui/animation_timeline.py` | Pure elapsed-time, rate, pause/resume |
| `src/gui/animation_effects.py` | Persistent actor rig và dynamic surface lease |
| `src/gui/animation_manager.py` | Main-thread submit/lifecycle, successful commit, rollback, optional one-task driver |
| `src/gui/animation_fixtures.py` | 12 deterministic demo scenarios và explicit geometric endpoints |
| `src/gui/animation_preview.py` | One-host composition và finite autoplay storyboard |
| `tests/test_gui_animation_*.py` | 5 suites; math/contracts/lifecycle/effects/preview |
| `tests/gui_animation_support.py` | Shared headless NodePath test setup |
| `tools/gui_stage5_smoke.py` | Onscreen captures/stress/profiles/autoplay/native close/recreate |
| `docs/gui/STAGE5_ANIMATION_SYSTEM.md` | Handoff và QA |
| `docs/gui/STAGE5_INTEGRATION_NOTES.md` | API/data review cho Phong/Tài |

```text
Caller / explicit fixture requests
           |
AnimationManager -------- AnimationTimeline (elapsed * rate)
           |                         |
           +---- RollPlan / pure math +---- immutable start pose + progress
           |
           +---- AnimatedActorRig under BlockRoot
           +---- AnimatedSurfaceLayer under DynamicTileRoot
           +---- AdvancedSceneRenderer: complete snapshots only

SceneRoot
├── StaticBoardRoot / AdvancedStaticContent        existing Floor/Goal
├── DynamicTileRoot / AnimationSurfaceLayer
│   ├── StaticSurfaceLease / AdvancedDynamicContent  Stage 4 renderer owns children
│   └── AnimatedSurfaceContent                      Stage 5 owns replacement surfaces
├── BlockRoot
│   ├── AdvancedBlockContent                        hidden while actor lease is held
│   └── AnimatedActorRig                            whole +2 cube slots +local markers
└── EffectsRoot                                    reserved, empty in this profile
```

Không tạo ShowBase, input bindings, collision/game rules, solver queue hoặc replay
Controller trong manager. Effects dùng preallocated owned meshes, không cần particle
system/request tasks hay transient children trong EffectsRoot. Camera/lights/HUD
và procedural factories Stage 3/4 dùng lại. Không có framework/dependency/assets mới.

## 3. Public animation API

```python
manager = AnimationManager(
    renderer, board_data, initial_snapshot, block_root,
    surface_layer=surface_layer, pitch=1.0, task_mgr=None,
)
manager.submit(request, on_finished=None)   # None khi accepted; invalid/busy raise
manager.advance(dt)                        # nonnegative finite seconds; returns progress
manager.pause()                            # bool, False nếu không đang PLAYING
manager.resume()                           # bool, False nếu không đang PAUSED
manager.set_playback_rate(rate)            # finite [.05, 8], gồm .25/.5/1/2/4
manager.cancel()                           # bool; False nếu không có request
manager.resync(snapshot)                   # explicit canonical reset, same loaded board
manager.dispose()                         # idempotent, synchronous cleanup
```

Read-only properties: `status`, `is_busy`, `current_request_id`, `progress`,
`current_snapshot`, `current_visual_poses` (tuple các ID/immutable VisualPose),
`terminal_outcome`. `None` actor key biểu thị WHOLE, string biểu thị stable cube ID;
không dùng string reserved gây xung đột cube IDs.

Manager gắn với một board trong lifetime. Đổi board: cancel/dispose manager,
release renderer/surface layer, load board mới và tạo manager mới; composition
phối hợp camera/HUD. Không có session store/solver replay queue bên trong manager.
Caller phải giữ exclusive visual ownership; không ghi snapshots trực tiếp vào
renderer trong khi manager đang nhận request.

## 4. Animation data schema

Animation schema **1 riêng theo type**, không đổi Basic v1 hay Advanced v2.
Contracts thuần Python, frozen/slotted, tuples; không Panda3D/NodePath/Core imports.

| Type | Fields |
| --- | --- |
| `AnimationRequest` | schema_version=1, request_id, before_snapshot, after_snapshot hoặc None, kind, duration, direction, actor_id, events, terminal |
| Derived identity properties | session_id, board_revision, from_state_revision, to_state_revision từ supplied snapshots |
| `AnimationEvent` | kind, normalized start/end, target_id, cell, ordered cube_ids, active_cube_id |
| `TerminalVisualOutcome` | FALL hoặc GOAL_COMPLETE, actor_id, fall_distance (pitch multiples, mặc định3) |
| `AnimationResult` | request/session/board IDs, from_revision, committed to_revision hoặc None, terminal status, terminal outcome hoặc error |
| `VisualPose` | center XYZ, normalized quaternion (w,x,y,z), nominal_dimensions |

`AnimationKind`: ROLL /EFFECTS /TERMINAL. Event kinds:
FRAGILE_BREAK, BRIDGE_PRESENT, BRIDGE_ABSENT, SWITCH_ACTIVATE,
SWITCH_DEACTIVATE, SPLIT, MERGE, ACTIVE_CUBE_CHANGE, FALL, GOAL_COMPLETE.
Event intervals thỏa `0<=start<end<=1`, được caller sắp theo start; cùng start giữ
thứ tự tuple. Không tự sinh events từ state diff. Diff chỉ dùng consistency check.

Supported request profiles:

- ROLL: một whole hoặc một cube theo explicit direction, supplied before/after.
  Có thể kèm surface events; không kèm mode/active change ngầm.
- EFFECTS: surface cues và tối đa một SPLIT/MERGE/ACTIVE_CUBE_CHANGE.
- TERMINAL: exactly một FALL/GOAL_COMPLETE event khớp explicit outcome,
  `after_snapshot=None`. Không fake snapshot đặt block dưới board.
- Mỗi surface target chỉ có một event trong request. Tổ hợp không hỗ trợ bị reject;
  tách thành requests có before/after tương thích.

Whole/split actor IDs, bridge/switch IDs, fragile cells, complete references,
schema, board/session và revisions đều được validate trước acceptance. Before
phải khớp toàn bộ current input snapshot. After cùng schema/board/session và revision
tăng. Các thay đổi dynamic fields phải được events giải thích chính xác; stationary
actors không tự di chuyển. Geometry endpoint mismatch bị reject độc lập với luật
Board. Không đánh giá passability hay legal transition.

Basic input được normalize bằng `as_visual_board`/`as_visual_snapshot`: mapping
semantic VOID/FLOOR và whole pose đã biết sang Advanced drawing foundation, giữ
identity. Không đọc numeric Core codes, không hạ Advanced về Basic hoặc bỏ data.

## 5. Lifecycle / timing / callback policy

IDLE → PLAYING ↔ PAUSED → COMPLETED /CANCELLED /FAILED. Terminal status vẫn cho
submit tiếp nếu không có terminal visual outcome và before snapshot khớp current.
Busy submit raise RuntimeError, không queue. Recent `(session_id,request_id)` trùng
bị reject; history bounded128. Opaque session strings không được so từ điển.

Với callback đã cung cấp, mỗi **accepted request** nhận đúng một synchronous terminal
result. Không cung cấp callback thì chỉ cập nhật status. Rejected request không có
fake completion. Bookkeeping terminal và bỏ callback/request cũ thực hiện trước
callback; completed callback có thể submit next request. Callback tự raise được
propagate, không đổi COMPLETED thành FAILED hay phát result lần hai.

- COMPLETED bình thường: commit supplied after snapshot, giữ continuous visual Q.
- COMPLETED terminal: outcome riêng, không committed revision; giữ known before
  snapshot và terminal visuals cho đến explicit resync, không tự reset/win UI.
- CANCELLED: restore known before visual poses/Q, release surface overrides,
  không commit after, `to_state_revision=None`; repeated cancel là False.
- FAILED: best-effort rollback, một FAILED result có error và propagate exception.
  Nếu engine không cho rollback, error ghi thêm lý do; không giả recovery thành công.
- Dispose đang chạy: stop owned task trước, synchronous CANCELLED, cleanup; không
  notification/task muộn sau dispose. Calls sau dispose raise, dispose lặp no-op.

`advance(dt)` tính elapsed từ dt×rate, sample từ immutable start +absolute progress;
không cộng góc theo frame. Pause giữ nguyên transform; đổi rate lúc playing/paused
không đổi elapsed/pose ngay lúc gọi. Không dùng `Interval.finish()` để cancel.

Có hai wiring choices, **không dùng đồng thời**:

1. `task_mgr=app.taskMgr`: manager sở hữu đúng một updater dùng Panda global clock.
2. `task_mgr=None`: caller tự `advance(dt)`. Preview dùng một `AnimationDemoDriver`
   task để vừa advance vừa phát finite fixture storyboard. Đây không phải gameplay
   replay queue. Task này giữ ở idle sau demo và được remove khi dispose.

Tất cả mutation APIs bắt buộc owning main thread. Không đổi engine-global task
behavior. resync validate trước cancel, chặn callback reentrant submit trong barrier,
cho phép new opaque session qua caller authorization, reject same-session stale/
conflicting revision. Explicit resync chủ động canonicalize face basis.

## 6. Physical rolling và quaternion convention

World X theo column, Y ngược row, Z lên; support Z=0. Whole nominal1×1×2,
standing center Z=1, lying center Z=.5; cube1×1×1 centerZ=.5, tất cả nhân pitch.
Với oriented world half-extents h, direction d và C0/Q0:

```text
P = C0 + (d.x*hx, d.y*hy, -hz)
a = cross((0,0,1), d)
u = s*s*(3-2*s)
R = axis_angle(a, (pi/2)*u)
C(s) = P + R*(C0-P)
Q(s) = normalize(HamiltonMultiply(R,Q0))
```

Pivot nằm trên contact edge và giữ nguyên cả bước. Không lerp center C0→C1,
không quay quanh tâm/teleport. At θ=0/90°, endpoints ổn định. Start phải là
quarter-turn basis và bottomZ=0. Predicted end center và world extents được đối
chiếu supplied target với tolerance `1e-6*max(nominal_dimensions)`; không tự coi
prediction là Core-authoritative state.

Pure quaternions là Hamilton (w,x,y,z). Chuyển components trực tiếp sang
`Panda Quat(w,x,y,z)` và kiểm tra `xform` basis vectors. Trong convention của Panda,
`Panda(local)*Panda(world)` tương ứng pure `Hamilton(world,local)`; không copy
thứ tự multiply từ engine vào công thức pure. Tests dùng hai trục không giao hoán
để chứng minh convention, không chỉ single-axis identity.

Mỗi frame sample từ Q0 bất biến; final Q được giữ cho bước sau. Không đưa history
vào Core State hoặc canonicalize cuối mỗi roll. Whole dùng asymmetric local inlay
sẵn có từ Stage 3; cube có amber strip trên một local bevel. Marker nằm trong
nominal cuboid, không dùng raised decal có thể xuyên floor sau roll. Các marker quay cùng
geometry. Active cue riêng đi theo world top/cube ID, không được dùng thay face
marker. Normalize Q sau composition; 500 reverse rolls có position drift <1e-10
trong pure test. Successful sequence có nhiều poses khác canonical basis dù cùng
logical orientation; screenshots xác nhận mặt khối không snap.

## 7. Actor và surface visual ownership

Extension duy nhất ở file cũ:

```python
renderer.set_actor_visuals_visible(visible: bool)
```

Chỉ đổi renderer-owned actor container; không đổi snapshot, tiles, mesh hoặc foreign
nodes. Default True giữ Stage 4 behavior. False được giữ qua `show_snapshot` và
load_board; caller phải explicit release. Manager không truy cập private renderer
NodePaths. Nó giữ actor lease cả khi idle giữa rolls; static actor không hiện lại
và canonical Q không gây snap. Resync/release là deliberate canonical reset.

AnimatedSurfaceLayer tạo một dedicated `renderer_root` được truyền vào existing
AdvancedSceneRenderer; không ẩn cả host DynamicTileRoot. Khi animate, layer đó ẩn
và các replacement surfaces thuộc Stage 5 hiện ra. Khi complete/cancel, restore
đúng layer visibility và renderer vẫn quản lý authoritative before/after snapshots.
Unchanged dynamic tiles vẫn hiện đúng. Không double-render cùng tile hay actor.

Có chi phí pool persistent hai bộ dynamic visual instances trong scene graph,
nhưng chỉ một bộ được draw tại một thời điểm. Mọi actor/surface mesh dùng lại qua
requests; dispose xóa nodes và giải phóng cả các NodePath handles/prototype refs
trong pool. Host roots và foreign siblings giữ nguyên.

## 8. Advanced animations thuộc supported visual profile

| Event | Hiệu ứng và endpoint |
| --- | --- |
| FRAGILE_BREAK | Cue làm tối intact, tắt supporting mesh, debris chuyển Z xuống; final Stage 4 broken không Floor bên dưới |
| BRIDGE_PRESENT | Platform nhiều cells nổi lên từ vị trí hạ/thu gọn; final Z/shape đúng Stage 4 |
| BRIDGE_ABSENT | Platform hạ/thu thickness rồi ẩn; không tự làm block rơi |
| SWITCH_ACTIVATE/DEACTIVATE | Raised marker press/release, swap accent theo supplied state/timing; shape Soft/Heavy/Split giữ nguyên |
| SPLIT | Whole source chia thành hai true1×1×1 cubes, giữ source Q, arc ngắn tới supplied cells; explicit ordered IDs map local lower/upper half |
| MERGE | Hai supplied cube IDs về hai halves của target whole, slerp tới target basis, final đúng một whole |
| ACTIVE_CUBE_CHANGE | Crossfade ID-based highlights, positions/Q không đổi; None tắt cả hai |
| FALL | Supplied whole/cube giảm Z theo u² và fade, không fake after-state; cube còn lại không bị dịch chuyển |
| GOAL_COMPLETE | Standing whole đúng supplied goal: stationary shrink/fade proxy phía trên mouth, không rigid-body sink xuyên rim .76 |

Split/merge là cinematic visual transitions, không mô phỏng collision hay chia tách
vật lý. Có thể overlap cube volumes ở đoạn merge; endpoints/identities được giữ
đúng. Merge chủ động dùng target canonical whole basis; continuity guarantee của
rolling không được diễn giải là physical face correspondence xuyên split/merge.
Không sửa Goal mesh hoặc logic footprint. Terminal actor opacity0 được hide thật
để không giữ ghost shadow. Resync khôi phục scale/opacity1 và actor visible.

Không event nào được suy từ occupancy, heavy orientation, state diff, transition
None, cube distance hoặc bridge/switch relation. Source Core không bị gọi/mutate.

## 9. Preview và executable commands

Tại repository root:

```bash
.venv/bin/python -B -m src.gui.animation_preview --scenario basic-roll
.venv/bin/python -B -m src.gui.animation_preview --scenario roll-chain
.venv/bin/python -B -m src.gui.animation_preview --scenario cube-roll
.venv/bin/python -B -m src.gui.animation_preview --scenario fragile
.venv/bin/python -B -m src.gui.animation_preview --scenario bridge
.venv/bin/python -B -m src.gui.animation_preview --scenario switches
.venv/bin/python -B -m src.gui.animation_preview --scenario split
.venv/bin/python -B -m src.gui.animation_preview --scenario merge
.venv/bin/python -B -m src.gui.animation_preview --scenario active-cube
.venv/bin/python -B -m src.gui.animation_preview --scenario fall
.venv/bin/python -B -m src.gui.animation_preview --scenario goal
.venv/bin/python -B -m src.gui.animation_preview --scenario combined --speed 0.5 --shadows
```

Default `combined`, speed1; `--no-aa`, `--no-autoplay` có thật. Autoplay một lượt,
initial/inter-request pause .60 s, giữ final visuals. Không replay solver hoặc
bind phím/nút gameplay. Header ghi ANIMATION DEMO DATA; title/provenance ghi
NOT AUTHORITATIVE GAMEPLAY. HUD actions disabled, command=None; 5 metrics unknown.

`create_animation_preview(...)->(app,renderer,manager)`; normal cleanup bằng
`dispose_animation_preview(app,renderer,manager)` **một lần cho host**. Thứ tự:
driver → manager → dashboard → presentation → renderer → surface layer → host.
Host-close fallback cũng stop animation qua finalExitCallbacks trước presentation.

Repeated-host audit phát hiện Panda 1.10.16 BufferViewer của ShowBase để lại một
`render-texture-targets-changed` subscription/host. New preview wiring cleanup
**chỉ inspector của host do nó tạo** qua public `app.bufferViewer.ignoreAll()`.
Không sửa Panda/Stage 3 source hoặc xóa global/foreign handlers. Ba sequential
hosts sau sửa về0 subscriptions thay vì1/2/3. Old previews không bị thay code.

## 10. Automated tests / regression

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_animation*'
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

Kết quả cuối: **373/373 PASS** trong `.venv`: 296 baseline +77 tests mới.
System Python không Panda: 373 discovered, 205 PASS /168 SKIP, không failure/error.
SKIP không được gộp vào PASS. Không sửa assertions hay skip tests cũ.

Coverage: twelve roll orientation/direction cases; keyframes/contact plane/no-floor
penetration; target mismatch; unit Q/Panda convention; 16-move face history;
500 reverse-roll drift; 30/60/120FPS-equivalent samples; immutable schema/events;
references/session/revision/duplicate/busy; pause/rate/resume; exactly-once success,
cancel, runtime failure và callback exception; explicit resync/barrier; task ownership;
actor/surface leasing; all advanced cues, terminal/cube fall, goal clearance/reset;
foreign nodes; pooled/disposed handles; one-host preview and failure cleanup.

Năm native entry points Foundation/Board/Dashboard/Advanced/Animation mở window
thật và đóng qua WM: exit0, không traceback. New autoplay chạy hết 7 requests bằng
clock/task thật; current snapshot đúng final fixture và chỉ một owned updater.

## 11. Real keyframe evidence

Artifacts ở `/tmp/bloxorz-stage5/`, ngoài Git, có thể mất khi dọn `/tmp`. Harness:

```bash
.venv/bin/python -B -m tools.gui_stage5_smoke --mode visual
.venv/bin/python -B -m tools.gui_stage5_smoke --mode stress
.venv/bin/python -B -m tools.gui_stage5_smoke --mode autoplay
.venv/bin/python -B -m tools.gui_stage5_smoke --mode terminal --shadows --output /tmp/bloxorz-stage5/terminal-shadows
.venv/bin/python -B -m tools.gui_stage5_smoke --mode lifecycle
.venv/bin/python -B -m tools.gui_stage5_smoke --mode entrypoints
```

169 primary captures =60 whole rolling keyframes (3 orientations×4directions×5),
48 chain captures (16×0/50/100%), 60 effect captures (20 requests×before/middle/after),
1 minimum1024×720. Thêm6 terminal-shadow +4 profile +2 autoplay captures: **181 ảnh
GraphicsWindow**, không ảnh AI/offscreen. Bounded framebuffer retries tránh đọc
khi native window chưa mapped; premature close không được ghi PASS.

| Evidence | Link |
| --- | --- |
| Standing RIGHT/LEFT/UP/DOWN, 0/25/50/75/100% | [Contact sheet](/tmp/bloxorz-stage5/contact-roll-standing.png) |
| Horizontal bốn hướng | [Contact sheet](/tmp/bloxorz-stage5/contact-roll-horizontal.png) |
| Vertical bốn hướng | [Contact sheet](/tmp/bloxorz-stage5/contact-roll-vertical.png) |
| Chain1–4 /5–8 /9–12 /13–16 | [1](/tmp/bloxorz-stage5/contact-chain-01.png), [5](/tmp/bloxorz-stage5/contact-chain-05.png), [9](/tmp/bloxorz-stage5/contact-chain-09.png), [13](/tmp/bloxorz-stage5/contact-chain-13.png) |
| Fragile /bridge /switches | [Surfaces](/tmp/bloxorz-stage5/contact-surfaces.png) |
| Split /merge /active /cube rolling | [Actors](/tmp/bloxorz-stage5/contact-actors.png) |
| Fall /goal before/middle/after | [Terminal](/tmp/bloxorz-stage5/contact-terminal.png) |
| Combined seven-step storyboard | [Combined](/tmp/bloxorz-stage5/contact-combined.png) |
| Minimum window, middle roll | [1024×720](/tmp/bloxorz-stage5/minimum-rolling-middle.png) |
| Goal terminal không ghost shadow | [Shadow final](/tmp/bloxorz-stage5/terminal-shadows/terminal-goal-100.png) |
| Actual-clock autoplay midpoint/end | [Middle](/tmp/bloxorz-stage5/autoplay-first-roll-middle.png), [End](/tmp/bloxorz-stage5/autoplay-complete.png) |

11 contact sheets là crops/layouts dẫn xuất từ ảnh thật bằng Pillow sẵn trên system,
không thay đổi originals. Không thêm Pillow vào dependency của app/tests/harness.
Tên originals/poses/Q/progress nằm trong JSON visual/terminal/autoplay/profile.
Ảnh và contact sheets đã được đọc để review contact edge, middle tilt, face markers,
colors/normals, occlusion, mode/active identity, Goal/VOID, HUD và shadow.

## 12. Stress / resources / lifecycle

- 500 completed rolling requests, alternating RIGHT/LEFT, supplied before/after.
- 100 pause/resume/rate cycles và100 cancel/resync cycles;600 unique terminal
  callback results ở hai populations, không callbacks trùng.
- 80 effect requests, gồm complete/cancel;20 board/manager recreates có dispose
  giữa request; foreign nodes preserved.
- Three sequential native hosts, middle request bị host-first close: mỗi request
  CANCELLED đúng1lần, output/task/subscription đều0 sau close.
- Actual autoplay: 7requests completed, one native window, one owned updater.

| Resource | Idle/combined | Rolling Basic |
| --- | ---: | ---: |
| Scene paths |225|191|
| Static /Dynamic /Block paths |148 /47 /24|156 /5 /24|
| Animated rig paths (không phải số actors visible) |12|12|
| HUD widgets /paths |42 /44|42 /44|
| Main regions /window regions |1 /4|1 /4|
| Native windows /outputs (shadow off) |1 /1|1 /1|
| Lights /subscriptions |3 /20|3 /20|
| Base tasks +manual animation sampling |8|8|
| Tasks với actual autoplay |9 (1owned)|—|
| EffectsRoot children |0|0|

Counts giữ nguyên giữa các batches cùng board. Shadow profile có1buffer/2outputs,
teardown0. `lifecycle.json` sau fix: mỗi host0 task/0 output/0 subscriptions.
Python heap trace start0/end121898/peak165381 bytes ở finite stress; current sau
100/200/300/400/500 rolls:25582/43650/61262/80246/99454. Harness cố ý giữ callback
results để audit IDs; trace gồm các objects này và cached Python allocations.
Đây không phải RSS/VRAM/C++ allocations và không chứng minh zero leak tuyệt đối.

## 13. FPS / frame timing

1280×720, viewport934×530, actualMSAA8 (request4). Mỗi process60warmup +240measured,
240foreground,0minimized. Wall-clock update+TaskMgr.step+syncFrame, không GPU-only.
Profile visual dt=1/60 deterministic; real-clock driver được kiểm riêng bằng autoplay.

| Profile | Active frames | MeanFPS | Mean /median /P95 ms |
| --- | ---: | ---: | --- |
| Idle Advanced |0|60.092|16.641 /16.654 /17.061|
| Rolling chain |232|60.091|16.642 /16.634 /17.050|
| Combined effects |236|60.091|16.641 /16.628 /17.108|
| Combined +shadows |236|60.103|16.638 /16.598 /17.308|

Boundary frames đã complete trước request kế tiếp không tính active. Desktop gần
cadence60Hz, không suy ra GPU throughput/KPI mọi máy. Shadow API vẫn báo
ENABLED_UNVERIFIED theo foundation; cast shadow đã được kiểm bằng ảnh máy này.
Không tối ưu speculative khi chưa có bottleneck.

```bash
.venv/bin/python -B -m tools.gui_stage5_smoke --mode profile --profile idle --output /tmp/bloxorz-stage5/idle
.venv/bin/python -B -m tools.gui_stage5_smoke --mode profile --profile rolling --output /tmp/bloxorz-stage5/rolling
.venv/bin/python -B -m tools.gui_stage5_smoke --mode profile --profile combined --output /tmp/bloxorz-stage5/combined-profile
.venv/bin/python -B -m tools.gui_stage5_smoke --mode profile --profile combined --shadows --output /tmp/bloxorz-stage5/shadows
```

## 14. Limitations / integration / Stage 6

Core/Controller integration **PENDING**, không VERIFIED. Need authoritative semantic
events/outcomes, stable cube correspondence và approved completion/cancel/session
mapping. Snapshot schemas cũ chưa chứa animation history và sẽ tiếp tục không chứa.

Profile không hỗ trợ arbitrary tilted start, multiple actor-mode events cùng request,
repeat event cùng surface target, simultaneous rolling+active change hay roll+terminal
không có valid after pose; tách requests/scenarios. Không collision/physical split/
merge/sinking, queue, replay, UI bindings hay victory screen. Goal chỉ standing whole;
FALL target có thể whole/cube. Camera giữ full-grid framing, không follow falling
actor; khi fade đi xa có thể nằm ngoài frame. Windows native NOT TESTED.

Ranh giới callback/task phải giữ khi Tài tích hợp; đầu vào async phải lọc stale
session trước submit/resync. Current preview finite storyboard không là solver route.
Chỉ `set_actor_visuals_visible` là extension vào renderer đã có; animation APIs mới
vẫn **PENDING TEAM APPROVAL** trước Stage 6. Chi tiết ở
[STAGE5_INTEGRATION_NOTES.md](STAGE5_INTEGRATION_NOTES.md).

## 15. Acceptance / quality gates / Git audit

| # | Criterion | Status |
| ---: | --- | --- |
| 1 | Animation request validation | PASS |
| 2 | Event definitions | PASS |
| 3 | Session/revision safety | PASS |
| 4 | Completion/cancel policy | PASS |
| 5 | Deterministic timeline | PASS |
| 6 | Playback rate | PASS |
| 7 | Pause/resume | PASS |
| 8 | Rolling math | PASS |
| 9 | Standing→Horizontal | PASS |
| 10 | Horizontal→Standing | PASS |
| 11 | Standing→Vertical | PASS |
| 12 | Vertical→Standing | PASS |
| 13 | Sideways rolls | PASS |
| 14 | Quaternion/face continuity | PASS |
| 15 | Stable final poses | PASS |
| 16 | Multiple-roll sequence | PASS |
| 17 | Actor visual ownership | PASS |
| 18 | Fragile break | PASS |
| 19 | Bridge present/absent | PASS |
| 20 | Switch activation | PASS |
| 21 | Split | PASS |
| 22 | Merge | PASS |
| 23 | Active cube selection | PASS |
| 24 | Split cube rolling | PASS |
| 25 | Fall | PASS |
| 26 | Goal effect without rim intersection | PASS |
| 27 | Terminal outcome handling | PASS |
| 28 | Cancel/resync | PASS |
| 29 | No duplicated callbacks | PASS |
| 30 | No leftover tasks | PASS |
| 31 | No leaked transient effects | PASS |
| 32 | No gameplay logic | PASS |
| 33 | No Core changes | PASS |
| 34 | No Controller changes | PASS |
| 35 | No Solver execution | PASS |
| 36 | No accidental enable of HUD controls | PASS |
| 37 | Stage 3 compatibility | PASS |
| 38 | Stage 4 compatibility | PASS |
| 39 | Full regression | PASS |
| 40 | Real visual smoke | PASS |
| 41 | Stability | PASS |
| 42 | Performance reporting | PASS |
| 43 | Documentation | PASS |
| 44 | Git scope | PASS |
| — | Windows native | NOT TESTED |
| — | Core /Controller integration | PENDING |

GateA contracts/lifecycle PASS; GateB physical rolling PASS; GateC supported Advanced
effects PASS; GateD Ubuntu runtime/handoff PASS. Conditional integration gates PENDING.

Manifest trước sửa có87files: chỉ `src/gui/advanced_renderer.py` thay đổi,86files còn
lại nguyên SHA-256, không file mất. 16files mới untracked (7modules,6test/support,
1tool,2docs),1tracked modified; staged empty. Default `git diff` không hiển thị
untracked nên phải review toàn bộ inventory. Whitespace/AST checks sạch. Không
commit/push hoặc thay branch trong Stage5.

**STAGE 5 VISUAL ANIMATION SYSTEM COMPLETE — INTEGRATION PENDING**
