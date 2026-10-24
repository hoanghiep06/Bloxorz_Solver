# Stage 4 — Advanced Mechanics 3D Renderer

**STAGE 4 ADVANCED VISUAL RENDERER COMPLETE — CORE INTEGRATION PENDING**

Ngày kiểm chứng: 2026-10-23, Ubuntu desktop. Phạm vi: Phước / GUI & Renderer.
Dữ liệu chạy thử là **VISUAL DEMO DATA**, không phải Advanced levels đã giải được
hoặc chuỗi transition được Core xác nhận. Tài liệu này là review package; không
thay thế quyết định API của nhóm.

## 1. Repository và môi trường

| Kiểm tra trước khi sửa | Kết quả |
| --- | --- |
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `b0e5f726f0a55d019c2413428dda7fe962131398` |
| Tracked/staged/untracked ban đầu | Không có thay đổi/file mới không bị ignore |
| Baseline `.venv` | 243/243 PASS, 2.171 s |
| Baseline system Python | 243 discovered; 159 PASS, 84 SKIP vì thiếu Panda3D |
| Python / Panda3D | 3.14.4 / 1.10.16 |
| Desktop | Ubuntu 26.04.1, X11, `DISPLAY=:0.0`, GraphicsWindow thật |
| GPU / GL | AMD Radeon Graphics, radeonsi/renoir/ACO, Mesa 26.0.8, OpenGL 4.6 |
| Windows native | NOT TESTED |

Đã đối chiếu source, tests và các tài liệu Stage 3: `STAGE3_HANDOFF.md`,
`BASIC_RENDERER_API.md`, `TEAM_INTEGRATION_REVIEW.md`, `STAGE3_RELEASE_CHECKLIST.md`,
`VISUAL_SPEC.md`, `GEOMETRY_TILE_SPEC.md`, `RENDER_CONTRACT.md`,
`LAYOUT_CAMERA_SPEC.md`, `STAGE3_6_VALIDATION.md`.

Core hiện có Board/State/whole orientations và Basic transitions. Các thay đổi
Advanced trước đây đã bị revert trong lịch sử checkout; không có semantic API
cho fragile, bridge IDs, switch definitions, split identities hay events/outcomes.
`bridges_state` trong State không cung cấp mapping đủ authority cho renderer.
Controller hiện là file khung. Không viết `advanced_render_adapter.py` giả.

**ADVANCED CORE ADAPTER — PENDING PHONG SCHEMA.**

## 2. File changes và lý do chọn kiến trúc

| File | Vai trò |
| --- | --- |
| `src/gui/advanced_contracts.py` | DTO schema 2 thuần Python, kiểm tra cấu trúc/references |
| `src/gui/advanced_fixtures.py` | Sáu scenarios deterministic, 18 snapshots minh họa |
| `src/gui/advanced_mesh_factory.py` | Geometry Advanced dùng chung low-level primitives |
| `src/gui/advanced_renderer.py` | Renderer nhận DTO, sở hữu content nodes, update tại chỗ |
| `src/gui/advanced_preview.py` | Một host, presentation kế thừa, dashboard disabled |
| `tests/test_gui_advanced_contracts.py` | 18 tests thuần Python |
| `tests/test_gui_advanced_geometry.py` | 10 tests đọc vertices/normals/triangles thật |
| `tests/test_gui_advanced_renderer.py` | 17 tests scene graph, state, identity, lifecycle |
| `tests/test_gui_advanced_preview.py` | 8 tests framing/composition/cleanup |
| `tools/gui_stage4_smoke.py` | Harness GraphicsWindow: visual/stress/profile/native close |
| `docs/gui/STAGE4_ADVANCED_RENDERER.md` | Báo cáo và acceptance |
| `docs/gui/STAGE4_INTEGRATION_NOTES.md` | Các điểm Phong/Tài cần review |
| `src/gui/mesh_factory.py` | Chỉ nối thêm 27 dòng public extension point |

Chọn reuse low-level mesh factories và geometry math. Ghép nguyên một
BasicSceneRenderer vào board Advanced sẽ tạo Floor sai dưới ô fragile/bridge;
subclass cũng phải can thiệp vào private state Basic. Renderer mới chỉ giữ việc
composition riêng cho schema 2; engine, host, camera, lights, HUD đều dùng lại.

Extension duy nhất trong file cũ là `MeshBuilder` và
`make_beveled_box_mesh(name=..., dimensions=..., bevel=..., top_color=...,
side_color=..., edge_color=...)`. Primitive mới validate extents, bevel và RGBA,
ủy quyền cho builder bevel sẵn có. Mục đích: không copy thuật toán mesh, không
import private helper từ consumer mới. Toàn bộ nội dung cũ giữ nguyên byte-for-byte
ở đầu file. Basic DTO v1, adapter, mesh outputs và renderer không đổi.

## 3. Luồng dữ liệu và ownership

```text
Advanced visual fixtures [hiện tại]      Phong Core → adapter [PENDING]
                         \             /
                      AdvancedBoardData + AdvancedSnapshot (schema 2)
                                          |
                              AdvancedSceneRenderer
                                          |
BloxorzPreviewApp / SceneRoot
├── StaticBoardRoot / AdvancedStaticContent   Floor, Goal
├── DynamicTileRoot / AdvancedDynamicContent  fragile pairs, bridge groups, switches
├── BlockRoot / AdvancedBlockContent          whole, two cube slots + indicators
└── EffectsRoot                              reserved, không dùng ở Stage 4
```

Renderer mượn ba NodePaths sống và khác nhau; không xóa host roots/foreign
siblings. Không tạo ShowBase, task, listener, camera, loop hay gameplay callback.
Prototypes tạo một lần cho mỗi renderer. Chỉ wrapper instances có transforms;
shared GeomNode không mang transform theo cell.

Presentation và DashboardPresentation dùng lại từ Stage 3. Subclass
`AdvancedPreviewPresentation` chỉ copy MaterialAttrib/AntialiasAttrib của static
root sang dynamic root, lưu/khôi phục hai attributes đó khi dispose. Điều này
bổ sung style cho root Advanced mà không sửa source presentation Stage 3.

## 4. Contract schema 2

Tất cả DTO là frozen/slotted dataclasses, nested containers phải là tuples;
không có Panda3D, NodePath, mutable Core references hoặc numeric tile codes.

| DTO | Fields |
| --- | --- |
| `AdvancedBoardData` | `schema_version=2`, `level_id`, `board_revision`, `rows`, `cols`, `tiles`, `goal_cells`, `bridges`, `switches` |
| `AdvancedSnapshot` | `schema_version=2`, `session_id`, `state_revision`, `board_revision`, `block_mode`, `whole_pose`, `cubes`, `active_cube_id`, `bridge_states`, `broken_fragile_cells`, `activated_switch_ids` |
| `WholeBlockVisualPose` | `orientation: BasicOrientation`, `anchor_cell: (row,col)` |
| `BridgeVisualDefinition` | `bridge_id`, nonempty tuple `cells` |
| `BridgeVisualState` | `bridge_id`, `present: bool` |
| `SwitchVisualDefinition` | `switch_id`, `cell`, `kind: SwitchVisualKind` |
| `SplitCubeVisualState` | `cube_id`, `cell` |

`AdvancedTileKind`: VOID/FLOOR/FRAGILE/BRIDGE. Goals là cells riêng.
`SwitchVisualKind`: SOFT/HEAVY/SPLIT. `AdvancedBlockMode`: WHOLE/SPLIT.
Fragile definitions nằm trực tiếp trong semantic tiles; `board.fragile_cells`
là property tính từ các definitions đó, không lưu thêm danh sách dễ lệch nhau.

Board kiểm tra dimensions/grid/enum exact, unique goals, bridge IDs/cells và
switch IDs/positions. Mỗi BRIDGE cell phải thuộc đúng một definition. Visual
profile hiện chỉ hỗ trợ Goal trên FLOOR và switch overlay trên non-goal FLOOR;
unsupported overlay bị reject, không chuyển ngầm thành loại tile khác.

Snapshot là **complete state**, không phải delta:

- Mọi bridge definition phải có đúng một `BridgeVisualState`; không thiếu/unknown IDs.
- `present=True`: có platform; `False`: không có platform. Không dùng open/closed mơ hồ.
- Fragile không nằm trong `broken_fragile_cells` là intact; broken cells phải thuộc FRAGILE definitions.
- Switch không nằm trong `activated_switch_ids` là inactive; tất cả IDs phải được định nghĩa.
- WHOLE bắt buộc whole_pose, không cubes/active ID.
- SPLIT bắt buộc hai cube IDs khác nhau, không whole_pose; active ID thuộc hai IDs hoặc `None`.
- Revision là exact int >=0, không bool; session/board revision là nonempty strings.
- `validate_snapshot(snapshot, board)` kiểm tra board revision và full footprint bounds.

Đây là structural/visual-profile validation. Hai cube có thể cùng cell, trên
VOID; whole có thể được caller đặt trên broken tile. Renderer không quyết định
support, legal move, activation, split/merge, win/loss hoặc transition order.

`create_advanced_board_data(level_id, tiles, *, goal_cells=(), bridges=(), switches=())`
tạo SHA-256 từ schema, level ID, semantic layout, goals và definitions. Tuple order
là một phần payload identity; caller cần giữ thứ tự ổn định. Direct constructor
có thể dùng opaque board_revision hợp lệ; renderer reject cùng revision với
payload khác. Đây là visual factory, không phải Core adapter.

## 5. Geometry và trạng thái hiển thị

| Đối tượng | Geometry / trạng thái |
| --- | --- |
| Floor/Goal/Whole | Dùng nguyên factories Stage 3 |
| Fragile intact | Sàn bevel .96×.96×.18 pitch, support top Z=0; amber `#D6A15F`, volumetric cracks Z=.002… .010 |
| Fragile broken | Không còn support mesh; ba debris nhỏ dưới Z=-.10, không có Basic Floor bên dưới |
| Bridge | Platform .96×.96×.18 pitch, blue/steel khác Floor, ribs nổi trên Z=0; hỗ trợ nhiều cells/ID |
| Bridge absent | Hide cả group platform, không Floor thay thế |
| Soft | Disc 24 cạnh, raised .015… .070 pitch |
| Heavy | Square base + dấu cộng nổi, không chỉ khác màu Soft |
| Split switch | Hai raised plates tách nhau, phân biệt với circle/cross ở 1024×720 |
| Activated | Cùng shape, đổi top accent sang SUCCESS `#4E8A72` theo supplied IDs |
| Split cubes | Mesh bevel 1×1×1 pitch thật, center Z=.5 pitch, bottom Z=0 |
| Active cube | Bốn green corner brackets trên top cube, trong footprint ±.5; local Z=.510… .540 pitch |

Các meshes có top/side/bottom, flat normals và winding theo normals; không
TwoSided, texture/asset ngoài, scale node để giả cube, collision hoặc animation.
Cracks/ribs/markers cách plane sàn, không dùng decal coplanar. Palette dùng
FLOOR_TOP/FLOOR_SIDE/BLOCK_MAIN/BLOCK_DARK/BLOCK_HIGHLIGHT và FRAGILE/SUCCESS.
Goal recess giữ aperture .76 và depth .14 của Stage 3, không lấp Goal/VOID.

## 6. Public renderer API

```python
renderer = AdvancedSceneRenderer(static_root, dynamic_root, block_root, pitch=1.0)
renderer.load_board(board_data)
renderer.show_snapshot(snapshot)
renderer.clear()
renderer.dispose()
```

Methods thành công trả `None`; lỗi dữ liệu raise trước khi đổi scene. Các calls
phải trên host/main thread. Không trả NodePath cho Controller.

`load_board` validate, build content detached rồi mới thay content cũ. Cùng data
là no-op; cùng revision/payload khác bị reject; build lỗi giữ scene trước đó.
Dynamic và block content ẩn cho tới complete snapshot đầu tiên, tránh đoán trạng
thái default của cầu/fragile/switch. Load chỉ tạo Normal Floor cho FLOOR; bridge
và fragile hoàn toàn thuộc DynamicTileRoot.

`show_snapshot` validate toàn bộ trước khi mutate. Update visibility và absolute
poses tại chỗ, không rebuild board/camera. Hai cube slots preallocated; map ID→slot
giữ node identity khi input tuple đổi thứ tự. Map tối đa hai IDs, không tăng cache
qua mỗi state. Active indicator chọn bằng ID, không vị trí/màu sắc. WHOLE/SPLIT
ẩn mutually exclusive. `None` active ID ẩn cả hai indicators.

Cùng session: revision không giảm; cùng revision chỉ chấp nhận payload y hệt.
Khác session: opaque replacement, không suy tuổi từ chuỗi. Controller phải lọc
old-session responses trước renderer. `clear` idempotent và giữ prototypes;
`dispose` idempotent/terminal, giải phóng prototypes và owned nodes.

## 7. Preview và fixtures

| Scenario | `--state` |
| --- | --- |
| `basic` | `standing`, `horizontal`, `vertical` |
| `fragile` | `intact`, `broken` |
| `bridge` | `present`, `absent` |
| `switches` | `inactive`, `activated` |
| `split` | `whole`, `cube-a`, `cube-b`, `no-active` |
| `combined` | `whole`, `absent`, `broken`, `cube-a`, `cube-b` |

Default scenario `combined`, default state là variant đầu tiên. Scenarios nhỏ
4×7, combined 5×9. Labels luôn có **VISUAL DEMO DATA**. Chúng không được thêm vào
`levels/`, không tuyên bố solvability hay legal sequence. CLI không có input game,
auto replay hoặc auto state cycling.

Tại repository root:

```bash
.venv/bin/python -B -m src.gui.advanced_preview --scenario combined
.venv/bin/python -B -m src.gui.advanced_preview --scenario fragile --state broken
.venv/bin/python -B -m src.gui.advanced_preview --scenario bridge --state absent
.venv/bin/python -B -m src.gui.advanced_preview --scenario switches --state activated
.venv/bin/python -B -m src.gui.advanced_preview --scenario split --state cube-a
.venv/bin/python -B -m src.gui.advanced_preview --scenario split --state cube-b
.venv/bin/python -B -m src.gui.advanced_preview --scenario split --state no-active
.venv/bin/python -B -m src.gui.advanced_preview --scenario combined --shadows
```

`--no-aa` tắt AA request. Panda cache default framebuffer properties: dùng process
mới để so AA. Host có một ShowBase/main loop. `dispose_advanced_preview(app, renderer)`
cleanup dashboard → presentation → renderer → host trong nested finally; gọi một
lần cho host. Renderer/presentation component disposals riêng đều idempotent.

`build_framing_data` là dimensions-only carrier cho camera hiện có: schema 1,
all VOID, không goals, level ID prefix `framing-only:`. **Không render carrier này.**
Advanced semantics vẫn ở schema 2 và AdvancedSceneRenderer. Full-grid envelope
Z[-.18,2.30] chứa toàn bộ geometry. Camera không follow mỗi snapshot; composition
refit khi đổi board/viewport. Dashboard 1280×720 vẫn có viewport 934×530;
1024×720 có viewport 678×530. Các controls disabled/command=None, năm metrics `None`
hiện em dash; không có fake solver timings/counts.

## 8. Automated tests và regression

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_advanced*'
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

| Chạy | Kết quả |
| --- | --- |
| Tests mới | 53/53 PASS |
| Full `.venv` | 296/296 PASS (243 cũ +53 mới), run cuối 3.043 s |
| System Python thiếu Panda | 296 discovered, 177 PASS /119 SKIP, không failure/error, run cuối .580 s |
| Old assertions/tests | Không chỉnh sửa hoặc skip thêm |

Tests mới cover deep immutability/strict types, schema/IDs/board references,
complete snapshots, structural-not-gameplay validation, no Panda/Core import ở
pure layer; actual mesh dimensions/pitch, finite vertices, unit normals,
nondegenerate triangles và winding; mode exclusivity/active identity, stale/conflict
rejection/atomic invalid scene, build failure, node reuse, foreign ownership,
framing bounds, one-host composition, style restore và failure cleanup.

Native entry points `src.gui.app`, `src.gui.board_preview`,
`src.gui.dashboard_preview` và `src.gui.advanced_preview --scenario bridge --state absent`
đều mở window thật rồi đóng qua window manager: exit 0, không traceback.

## 9. Visual smoke và screenshot evidence

Evidence local nằm ngoài Git tại `/tmp/bloxorz-stage4/`; `/tmp` không phải kho lưu
trữ lâu dài. Có thể tái tạo bằng harness đi kèm. Không có ảnh AI-generated.

```bash
.venv/bin/python -B -m tools.gui_stage4_smoke --mode visual
.venv/bin/python -B -m tools.gui_stage4_smoke --mode stress
.venv/bin/python -B -m tools.gui_stage4_smoke --mode profile --output /tmp/bloxorz-stage4/normal
.venv/bin/python -B -m tools.gui_stage4_smoke --mode profile --shadows --output /tmp/bloxorz-stage4/shadows
.venv/bin/python -B -m tools.gui_stage4_smoke --mode profile --no-aa --output /tmp/bloxorz-stage4/no-aa
.venv/bin/python -B -m tools.gui_stage4_smoke --mode entrypoint
.venv/bin/python -B -m tools.gui_stage3_6_smoke --mode entrypoints --output /tmp/bloxorz-stage4/basic-regression
```

22 screenshots chính: mỗi state trong bảng fixture có `{scenario}-{state}-1280x720.png`
(18 ảnh); thêm `switches-inactive`, `switches-activated`, `combined-cube-a`,
`combined-cube-b` với suffix `-1024x720.png` (4 ảnh). Ba profile captures nằm tại
`normal/profile.png`, `shadows/profile.png`, `no-aa/profile.png`: tổng 25 ảnh evidence.

| Kiểm tra trực quan | Evidence tiêu biểu | Kết quả |
| --- | --- | --- |
| Fragile intact/broken, không support sau vỡ | [intact](/tmp/bloxorz-stage4/fragile-intact-1280x720.png), [broken](/tmp/bloxorz-stage4/fragile-broken-1280x720.png) | PASS |
| Bridge nhiều cells, platform hiện/vắng | [present](/tmp/bloxorz-stage4/bridge-present-1280x720.png), [absent](/tmp/bloxorz-stage4/bridge-absent-1280x720.png) | PASS |
| Switch circle/cross/two plates và activation ở minimum window | [inactive](/tmp/bloxorz-stage4/switches-inactive-1024x720.png), [activated](/tmp/bloxorz-stage4/switches-activated-1024x720.png) | PASS |
| WHOLE, hai cubes, identity A/B/none | [A](/tmp/bloxorz-stage4/split-cube-a-1280x720.png), [B](/tmp/bloxorz-stage4/split-cube-b-1280x720.png), [none](/tmp/bloxorz-stage4/split-no-active-1280x720.png) | PASS |
| Combined/Goal/VOID, HUD không clip | [combined](/tmp/bloxorz-stage4/combined-whole-1280x720.png), [minimum](/tmp/bloxorz-stage4/combined-cube-b-1024x720.png) | PASS |
| Matte/lighting/shadow, AA khác biệt | [shadow](/tmp/bloxorz-stage4/shadows/profile.png), [no AA](/tmp/bloxorz-stage4/no-aa/profile.png) | PASS trên máy kiểm chứng |

Đã kiểm tra màu, mesh silhouette, normals, occlusion, bounds/camera, HUD labels,
Goal/VOID và indicators. Để tránh nhầm ảnh buffered khi chuyển fixture nhanh,
harness complete fresh draws trước saveScreenshot. Trạng thái active còn được
đối chiếu pixel vùng top cubes: A có green accent chỉ ở A; B chỉ ở B; none không
có green accent ở cả hai. Không thay gameplay/render semantics để sửa evidence.
Shadow API vẫn báo `ENABLED_UNVERIFIED` theo thiết kế cũ; ảnh runtime xác nhận có
cast shadow trên máy này, không nâng trạng thái API thành bảo đảm cross-platform.

## 10. Stability và resources

Stress thật trong GraphicsWindow: 1.500 snapshot updates gồm bridge present/absent,
fragile intact/broken, whole/split và active A/B; 36 board reloads +same-board no-op;
20 presentation/dashboard recreate; 12 renderer dispose/recreate.

Counts của combined board ổn định trước/sau và giữa ba batches:

| Resource | Count |
| --- | ---: |
| Scene paths | 111 |
| Static / Dynamic / Block paths | 66 /27 /12 |
| Dynamic mesh instances (kể cả hidden variants) | 12 |
| HUD widgets / HUD paths | 42 /44 |
| Main-camera DisplayRegions / tất cả window regions | 1 /4 |
| Native windows / graphics outputs (shadow off) | 1 /1 |
| Light nodes | 3 |
| Window / aspect / total subscriptions | 2 /1 /20 |
| Graphics outputs sau destroy | 0 |

Static node identity, mesh prototype identities và camera transform giữ nguyên
qua snapshot batches. Python `tracemalloc` current ở batches 500/1000/1500:
808/1584/2328 bytes; peak 13240/14208/14952 bytes. Sau toàn bộ reload/recreate,
current 305445, peak 334903 bytes so với mốc trace ban đầu 0. Có giữ/cấp phát Python
qua finite run; không suy ra zero leak. Đây không phải RSS, VRAM hoặc tổng memory
của Panda/C++/driver. Shadow profile dùng 2 graphics outputs trong lúc chạy, 0 sau
host destroy; không có shadow output tồn tại sau cleanup.

## 11. Performance observations

Combined fixture, 1280×720, viewport 934×530, 60 warmup +240 measured foreground
frames mỗi process, không minimized frame. Đo wall-clock TaskMgr.step+syncFrame,
gồm CPU/driver/compositor; không phải GPU-only và không suy rộng throughput.

| Profile | Actual MSAA | FPS mean | Mean / median / P95 ms |
| --- | ---: | ---: | --- |
| Normal | 8 | 60.089 | 16.642 /16.638 /16.983 |
| Shadow requested | 8 | 60.088 | 16.642 /16.638 /17.004 |
| No AA | 0 | 60.088 | 16.642 /16.642 /16.880 |

MSAA request 4 được driver cấp 8; report actual, không giả 4. Cả ba gần cadence
60 Hz của desktop, chưa thấy bottleneck Advanced ở fixture nhỏ này.

## 12. Limitations và Stage 5 readiness

- Core integration PENDING: không authoritative advanced levels/transitions/events.
- Fixtures minh họa states độc lập; broken→intact hay WHOLE→SPLIT trong stress
  không được diễn giải là hợp lệ trong game.
- Chưa gameplay input, Solver buttons, Controller, replay, animation hoặc outcome UI.
- Supported visual profile không gồm goal trên fragile/bridge, stacked switches,
  teleporter, extended mechanics hay board có cube ngoài logical bounds.
- Active highlight nhỏ, giữ footprint đúng; palette/placement có thể review thêm.
- Camera envelope full grid vẫn conservative; không đổi framing/padding Stage 3.
- Presentation dùng coupling `_refit` hiện có qua DashboardPresentation; chưa refactor API nhóm.
- Windows native NOT TESTED. Shadow capability phụ thuộc GPU/driver.
- Basic rolling có thể bắt đầu ở mức visual prototype Stage 5 từ geometry/poses;
  contract request/completion/cancel và continuous visual face basis cần chốt trước tích hợp.
- Fragile/bridge/switch animation cần authoritative before/after +semantic events/order.
- Split/merge cần stable identity, correspondence, source/destination và event order.
- Goal-sink cần quyết định clearance vì aperture .76 <block width1, depth .14;
  không dùng animation xuyên rim hoặc tự sửa luật Core.

Chi tiết data/API pending xem [Stage 4 integration notes](STAGE4_INTEGRATION_NOTES.md).

## 13. Git scope và quality gates

Manifest SHA-256 của 75 file có sẵn trước triển khai: chỉ `mesh_factory.py` thay đổi
(thêm 27 dòng); 74 file còn lại nguyên vẹn, không file mất. Không đổi Core,
Controller, Solver, main.py, levels, requirements, Basic DTO/adapter/renderer hay
báo cáo lịch sử. 12 files mới trong bảng changes đang untracked; 1 tracked file
modified; staged empty. Không fetch/pull/checkout/stash/reset/clean/rebase/merge/
branch creation/commit/push trong nhiệm vụ. `git diff --check` và kiểm tra whitespace
các file mới sạch. Git diff mặc định chỉ hiển thị tracked change; cần review cả
untracked files, không chỉ stat 27 dòng.

| Gate | Kết quả |
| --- | --- |
| A — Advanced Data | PASS, độc lập Core |
| B — Advanced Geometry | PASS |
| C — Advanced Scene | PASS trên finite node/resource tests |
| D — Runtime & Regression | PASS trên Ubuntu thực tế |
| Core Integration | PENDING PHONG SCHEMA, chưa đạt VERIFIED |

## 14. Acceptance matrix

| # | Tiêu chí | Status / bằng chứng |
| ---: | --- | --- |
| 1 | Advanced Contracts | PASS — schema 2, strict references |
| 2 | Immutable Visual State | PASS — frozen/slots/tuples, pure imports |
| 3 | Visual Fixtures | PASS — 6 scenarios /18 explicit states |
| 4 | Fragile intact/broken | PASS — mesh/tests/screenshots |
| 5 | Bridge enabled/disabled | PASS — present/absent, multi-cell |
| 6 | Soft Switch | PASS — circular raised mesh |
| 7 | Heavy Switch | PASS — square +cross |
| 8 | Split Switch | PASS — two plates |
| 9 | Activated Switch visual | PASS — explicit supplied IDs |
| 10 | Two Split Cubes | PASS — true 1×1×1, bottom Z=0 |
| 11 | Active Cube A/B | PASS — ID-based brackets, None hides both |
| 12 | Whole/Split visual mode switching | PASS — mutually exclusive |
| 13 | Dynamic Scene updates | PASS — prebuilt nodes, absolute transforms |
| 14 | Correct Goal/Void handling | PASS — recess, void gaps, no fallback floor |
| 15 | Scene ownership | PASS — only owned content, foreign preservation |
| 16 | Lifecycle/cleanup | PASS — reload/dispose/recreate, outputs=0 after destroy |
| 17 | Basic Stage 3 backward compatibility | PASS — 243 old tests +3 old native entry points |
| 18 | No Core mutation | PASS — Core hash unchanged, no Core in renderer/data |
| 19 | No gameplay logic | PASS — no transitions/activation inference |
| 20 | No Controller implementation | PASS — Controller unchanged |
| 21 | No solver execution | PASS — no solver invocation |
| 22 | No rolling/falling animation | PASS — static snapshots only |
| 23 | Unit tests | PASS — 53 new tests |
| 24 | Full regression | PASS — 296/296 in .venv |
| 25 | Real visual preview | PASS — GraphicsWindow Ubuntu, 25 evidence captures |
| 26 | Documentation | PASS — 2 new documents, historical docs untouched |
| 27 | Git scope compliance | PASS — one additive old-file extension +12 new files |

**STAGE 4 ADVANCED VISUAL RENDERER COMPLETE — CORE INTEGRATION PENDING**
