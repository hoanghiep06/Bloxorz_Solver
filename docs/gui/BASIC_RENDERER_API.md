# Basic Renderer API — implementation hiện tại

Ngày xác minh: **23/10/2026**. Source truth: checkout `feat/phuoc/3d-renderer`,
HEAD `956c0a0528c9170afceda58551772bcadd3fc12a` cùng các GUI files chưa commit.
Đọc [handoff chính](STAGE3_HANDOFF.md) trước khi tích hợp.

## 1. Trạng thái và quy ước

**IMPLEMENTED / VERIFIED** dưới đây nghĩa là API đang có và đã đối chiếu source/tests.
Không đồng nghĩa hợp đồng tích hợp đã được cả nhóm duyệt. **PROPOSED** và
**PENDING TEAM APPROVAL** chỉ là hướng tương lai. **UNSUPPORTED** không được
chuyển thành fallback giả.

- Cell luôn `(row, col)` nguyên không âm trong DTO, không bool.
- X theo column, Y đảo row, Z lên; pitch mặc định 1 world unit.
- DTO/adapter/math không cần Panda3D. Renderer/scene/UI gọi trên host main thread.
- Methods renderer thành công trả `None`; lỗi là exception, không receipt.
- Không có `animate`, animation result, busy/cancel/pause/resume hoặc replay API.
- `src/gui/__init__.py` chưa export các class; import từ module cụ thể.

## 2. Contracts

Source: [contracts.py](../../src/gui/contracts.py).
Hai dataclasses `frozen=True, slots=True`; direct constructors yêu cầu tuple,
kể cả nested containers. Không nhận list/JSON dict rồi tự chuyển DTO.

### BasicTileKind và BasicOrientation

| Enum | Members / string values |
| --- | --- |
| `BasicTileKind` | `VOID="VOID"`, `FLOOR="FLOOR"` |
| `BasicOrientation` | `STANDING="STANDING"`, `HORIZONTAL="HORIZONTAL"`, `VERTICAL="VERTICAL"` |

Không có GOAL tile enum: `goal_cells` là nguồn goal. Core `Orientation` là enum
khác, không truyền trực tiếp vào GameSnapshot hoặc preview `pose`.

### StaticBoardData

Constructor theo thứ tự sau, không field default:

| Field | Type thực tế | Validation |
| --- | --- | --- |
| `schema_version` | `int` | Exact int, chỉ 1 |
| `level_id` | `str` | Exact str, không rỗng/whitespace |
| `board_revision` | `str` | Exact str không rỗng; constructor không xác minh đó là hash |
| `rows`, `cols` | `int` | Exact int >0 |
| `tiles` | `tuple[tuple[BasicTileKind,...],...]` | Đúng rows×cols, mỗi cell là member enum |
| `goal_cells` | `tuple[tuple[int,int],...]` | Cells trong board, không trùng |

Contract cho phép zero/multiple goals và goal trên VOID về mặt cấu trúc;
renderer **reject goal trên VOID**. Adapter Core hiện xuất đúng một goal.
DTO không chứa bridge/switch definitions, capabilities hoặc references Board.

### GameSnapshot

Constructor theo thứ tự sau, không field default:

| Field | Type / validation |
| --- | --- |
| `schema_version` | Exact int 1 |
| `session_id` | Exact nonempty str; opaque, không phải số tự tăng |
| `state_revision` | Exact int ≥0 |
| `board_revision` | Exact nonempty str |
| `block_mode` | Exact str `"WHOLE"`; SPLIT UNSUPPORTED |
| `orientation` | `BasicOrientation` member |
| `anchor_cell` | Tuple `(row,col)` exact ints ≥0 |
| `occupied_cells` | Tuple cells, phải đúng footprint/canonical order |

Footprints: standing `((r,c),)`; horizontal `((r,c),(r,c+1))`;
vertical `((r,c),(r+1,c))`. VERTICAL là nằm dọc hàng, không đứng theo Z.
GameSnapshot không mang dimensions nên constructor chưa kiểm upper board bounds;
adapter và renderer kiểm footprint trong board tương ứng. Không kiểm support/win/loss.
Không có bridge states, cubes, active cube hoặc gameplay status trong Basic DTO.

Sai type thường `TypeError`; sai giá trị/schema/footprint `ValueError`.
Đọc exact validators khi cần phân biệt trường hợp; không có custom error category class.

## 3. Adapter

Source: [render_adapter.py](../../src/gui/render_adapter.py).

```text
build_board_data(board: Board, *, level_id: str) -> StaticBoardData
build_game_snapshot(state: BloxorzState, *, board_data: StaticBoardData,
                    session_id: str, state_revision: int) -> GameSnapshot
```

### build_board_data

Chỉ nhận **exact Core Board class**, không arbitrary object/subclass theo duck typing.
Đọc `rows`, `cols`, `grid`, `goal_r`, `goal_c`. Grid list/tuple rectangular,
raw code exact int 0/1/2: 0→VOID, 1/2→FLOOR. Không suy goal từ raw code 2.
Cell goal authoritative lấy từ fields Board, phải trong bounds.

Trả detached immutable DTO. Revision là SHA-256 canonical JSON với sorted keys,
compact separators, ensure_ascii=True của `level_id`, dimensions, raw grid và goal_cells.
Raw 1→2 vẫn đổi revision dù cùng FLOOR visual; đổi level_id cũng đổi revision.
Start position **không** nằm trong static digest. Không dùng mtime hoặc hash ngẫu nhiên.

Exceptions: TypeError với schema/type sai; ValueError với dims/grid/goal sai hoặc
unsupported codes. Không gọi transition/is_goal/is_valid_state; không đọc file,
load graphics hoặc sửa Board. Core Board constructor do caller gọi riêng.

### build_game_snapshot

Chỉ nhận exact `BloxorzState` và exact `StaticBoardData`. Caller cung cấp session/revision;
không tự cấp session hoặc tăng revision. Chỉ hỗ trợ `bridges_state == ()` là exact tuple.
Map Core enum, đọc `r/c/get_occupied_cells()`, copy/sort cells thành canonical tuple,
validate footprint và bounds. Không copy/rehash toàn static grid mỗi update.

Caller chịu trách nhiệm ghép authoritative State với đúng Board; state không tự
chứa board identity. Không kiểm occupied FLOOR/support hoặc thắng/thua. Unsupported
bridge flags/orientation/bounds → ValueError; malformed types → TypeError/ValueError
theo field validator. File errors/JSON errors từ Board constructor không phải adapter.

<!-- example: basic-data -->
```python
from src.core.board import Board
from src.gui.render_adapter import build_board_data, build_game_snapshot

board = Board("levels/level_01.json")
state = board.get_initial_state()
data = build_board_data(board, level_id="levels/level_01.json")
snapshot = build_game_snapshot(
    state, board_data=data, session_id="example-session-1", state_revision=0,
)
assert snapshot.board_revision == data.board_revision
assert snapshot.anchor_cell == (1, 1)
```

**VERIFIED EXAMPLE** với level hiện tại từ repository root; không gọi transition.

## 4. BasicSceneRenderer

Source: [renderer.py](../../src/gui/renderer.py).

```text
BasicSceneRenderer(static_board_root: NodePath, block_root: NodePath, *, pitch: float=1.0)
load_board(board_data: StaticBoardData) -> None
show_snapshot(snapshot: GameSnapshot) -> None
clear() -> None
dispose() -> None
```

Constructor cần hai live NodePaths **khác nhau**, do host sở hữu; invalid roots/pitch
→ ValueError. Nó tạo shared Floor/Goal/Block GeomNode prototypes, không window,
ShowBase, camera, lights hoặc tasks. Không để Controller dùng `_content/_block`
hay private prototypes như public integration API.

| Operation | Preconditions / behavior | Error / ownership |
| --- | --- | --- |
| `load_board` | Renderer sống; exact DTO được revalidate. Cùng data là no-op, giữ block. Board khác build detached rồi thay owned content và reset snapshot/block | Wrong type TypeError; revision tái dùng cho data khác, goal trên VOID hoặc invalid DTO ValueError. Validation/build fail giữ scene cũ; engine exception được re-raise |
| `show_snapshot` | Phải load board trước; matching board_revision; valid WHOLE footprint trong bounds. Update absolute position/quaternion của một block | RuntimeError trước load/sau dispose/host roots mất; wrong type TypeError; mismatch/stale/conflict/out-of-bounds ValueError |
| `clear` | Xóa owned content/block và board/snapshot identity, giữ prototypes để load lại | Idempotent; không xóa host roots/foreign siblings; không resurrect renderer đã dispose |
| `dispose` | clear rồi release prototype references, terminal flag | Idempotent. load/show tiếp theo RuntimeError; clear/dispose lặp vẫn an toàn |

Same-session state_revision không được giảm. Cùng revision chỉ chấp nhận cùng
snapshot; tăng revision được phép. **Session string khác được coi là caller-authorized
replacement**, không có so thứ tự session, registry session đã hết hạn hoặc stale-worker
filter. Tài phải lọc old-session results trước khi gửi renderer.

Renderer không auto-fit camera, đổi HUD label/metrics hoặc light bounds khi reload.
Đó là trách nhiệm composition/Controller được thống nhất. Foreign nodes nên là
siblings dưới host roots; không gắn tài nguyên ngoài vào owned subtree rồi mong
clear giữ descendants đó.

## 5. Geometry helper API

Source: [geometry_math.py](../../src/gui/geometry_math.py),
[mesh_factory.py](../../src/gui/mesh_factory.py).

| API thực tế | Trả về / chú ý |
| --- | --- |
| `cell_to_world(row,col,*,rows,cols,pitch=1.0)` | XY cell center, ValueError cho params sai |
| `logical_board_bounds(rows,cols,*,pitch=1.0)` | XY full-grid footprint, gồm VOID |
| `block_pose(row,col,orientation,*,rows,cols,pitch=1.0)` | Frozen `BlockPose(center,dimensions,rotation_axis,angle_degrees)`; kiểm footprint bounds |
| `make_floor_mesh(*,pitch=1.0)` | GeomNode Floor, top 0/bottom -.18, width/depth .96×pitch |
| `make_goal_mesh(*,pitch=1.0)` | GeomNode open recess, aperture .76, depth .14×pitch |
| `make_block_mesh(*,pitch=1.0)` | Centered 1×1×2×pitch GeomNode |

Math không Panda/Core; mesh factory cần Panda nhưng không host/window. Không dùng
node scale để đổi footprint. Rolling visual face-history chưa được các canonical
poses này biểu diễn; không dùng orientation enum làm toàn bộ animation history.

## 6. Camera, Lighting, Style và presentation

Các API dưới đây là components hiện có; chưa là facade Controller đã duyệt.
Controller tương lai nên gọi một public presentation coordinator thay vì HPR,
Geom/lighting nodes. Facade đó **PROPOSED**, chưa có source.

### Camera

Source: [camera.py](../../src/gui/camera.py).

```text
CameraConfig(azimuth=30.0,elevation=45.0,vertical_fov=45.0,padding=0.13)
SceneBounds(minimum,maximum)                  # tuple XYZ, min<max từng axis
board_bounds(board_data,*,pitch=1.0) -> SceneBounds
fit_camera(board_data,width,height,*,pitch=1.0,config=CameraConfig(),bounds=None) -> CameraFit
camera_basis(config=CameraConfig()) -> (back,right,up,forward)
project_point(point,fit) -> (ndc_x,ndc_y,depth)
BoardCameraController(camera,lens,*,config=CameraConfig())
fit_board(board_data,width,height,*,pitch=1.0,bounds=None)
set_viewport_size(width,height)
configure(config)
bind_window(window,*,viewport_size=None,on_refit=None)
dispose()
```

`CameraConfig`, `SceneBounds`, `CameraFit` là frozen/slotted dataclasses.
CameraFit fields: position/target/right/up/forward (XYZ tuples), distance,
horizontal_fov, vertical_fov, near, far, aspect, bounds. Pure fitting lấy full-grid
envelope từ Z=-.18 tới 2.30×pitch và 13% padding mỗi cạnh; không nhìn current snapshot.
Config finite, elevation (-89,89), VFOV [1,175), padding [0,.45); invalid → ValueError.
Pure fit dimensions phải positive exact ints. project_point depth≤0 → ValueError.

Controller cần live camera node và PerspectiveLens. fit_board lưu context/cập nhật
pose/lens, gọi on_refit nếu có, trả True; zero width/height là False no-op. Other
invalid size/config thường ValueError, sai board type TypeError. set_viewport_size cần fit_board trước; trả False
nếu zero hoặc size/lens đã khớp, True nếu refit. configure cập nhật config/refit,
không trả receipt. Methods sau dispose RuntimeError; dispose idempotent.

Provider signature `viewport_size(window) -> (width,height)`, callback
`on_refit(CameraFit)`. bind_window thay listener **của chính camera**, không host
handler; nghe window-event và aspectRatioChanged. None provider = full-window.
Current fit đọc ở `current_fit`; không lấy private `_board/_provider` làm API.

### Lighting và Style

| Component / signature | Public operations và kết quả |
| --- | --- |
| `SceneLightingController(scene_root,fit,*,shadows=False,gsg=None)` | `fit_bounds(fit)`; `set_shadows(enabled,*,gsg=None)->bool`; `dispose()` |
| `SceneStyle(static_root,block_root,camera,*,multisamples=0,antialiasing=True)` | `update_background(fit)`; `dispose()` |

Source: [scene_lighting.py](../../src/gui/scene_lighting.py),
[scene_style.py](../../src/gui/scene_style.py). Lighting sở hữu ambient/key/fill
rig và shader state nó bật; shadow lens 2048², capability fallback. Status:
`DISABLED`, `UNAVAILABLE`, `ENABLED_UNVERIFIED` (engine request, chưa là visual verdict).
Style sở hữu material/AA attribs và camera backdrop; aa_status `DISABLED`,
`UNAVAILABLE` hoặc `MSAA_{samples}X`. multisamples cần **actual framebuffer readback**,
không coi request 4 samples là kết quả chắc chắn. Hai components restore prior
owned attributes, không quản lý concurrent foreign writes vào cùng attributes.
Dispose lặp an toàn; update/fit sau dispose RuntimeError. Không mutate mesh vertices.

### PreviewPresentation và create_preview

```text
PreviewPresentation(app,board_data,*,shadows=False,antialiasing=True)
PreviewPresentation.dispose()
create_preview(level=DEFAULT_LEVEL,*,pose=BasicOrientation.STANDING,
               shadows=False,antialiasing=True) -> (app,renderer)
dispose_presentation(app)
```

Source: [board_preview.py](../../src/gui/board_preview.py). DEFAULT_LEVEL là
repository `levels/level_01.json`. create_preview validate/load Board/DTO trước
host, dùng level.resolve().as_posix() làm level_id, session `"board-preview"`,
revision 0. Pose alternatives là fixtures tại initial anchor, không moves.
Nó tạo đúng một BloxorzPreviewApp và trả pair; app.presentation giữ camera,
lighting, style. File/DTO/engine exceptions propagate, resources đã tạo được cleanup.
PRC AA request tạm, framebuffer defaults có cache: dùng fresh process để so AA.

`PreviewPresentation._refit(fit)` là **PRIVATE**, được Dashboard composition gọi
để cập nhật background/light bounds. Không hướng dẫn Controller gọi private method;
cần public facade/callback trước Stage 6, xem finding R1 trong
[team review](TEAM_INTEGRATION_REVIEW.md).

## 7. Layout và DisplayRegion

Source: [layout.py](../../src/gui/layout.py), [viewport.py](../../src/gui/viewport.py).

| API | Hành vi |
| --- | --- |
| `Rect(x,y,width,height)` | Frozen dataclass, exact int, origin≥0/size>0; right/bottom properties, intersects(other) |
| `LayoutResult(width,height,viewport,header,panel,status,supported)` | Frozen data; header/panel/status None trong fallback; constructor không là validator toàn layout |
| `calculate_layout(width,height)` | Pure math, positive exact ints; reference 1280×720; dưới1024×720 trả supported=False |
| `normalized_region(rect,width,height)` | `(left,right,bottom,top)`; ValueError invalid dimensions/outside bounds |
| `panel_controls(panel_width=282)` | Dict tên controls→Rect local panel; helper geometry, không action callbacks |
| `DashboardViewport(window,camera_node,camera_controller,*,on_refit,on_layout)` | Borrow đúng một existing region của main camera; 0/>1 match → ValueError |
| `DashboardViewport.refresh()` | Provider+camera refresh; sau dispose False |
| `DashboardViewport.dispose(*,refit=True)` | Restore dimensions/active và full-window camera binding; idempotent |

Viewport không tạo camera/controller/listener/region mới. Camera đang bind chịu
resize. HUD layout callback nhận LayoutResult. Fallback ẩn surfaces, deactivate
3D và báo minimum size; zero/minimized dimensions giữ fit. dispose(refit=False)
dùng khi host đã detach scene để không refit lighting trên dead scene roots.
Component dành cho create_preview full-window binding, **không** lưu/restore arbitrary
foreign provider trước đó. Không dùng nó như generic viewport manager.

## 8. HUD/ViewModel

Source: [hud.py](../../src/gui/hud.py).

| HudViewModel field | Default / type / đơn vị |
| --- | --- |
| `level_label` | `"Level 01"`, nonempty str |
| `runtime_status` | `"PREVIEW"`, nonempty str; không restricted status enum |
| `move_count` | None hoặc exact nonnegative int |
| `search_time_ms` | None hoặc finite nonnegative int/float, không bool; **milliseconds** |
| `expanded_nodes` | None hoặc exact nonnegative int |
| `solution_length` | None hoặc exact nonnegative int |
| `peak_python_memory_bytes` | None hoặc exact nonnegative int; **bytes**, traced Python peak nếu caller có số đo đó |

Frozen dataclass, sai data → ValueError. `metric_values(model)` trả tuple năm strings:
None→`—`; zero thật→`0`, `0.00 ms`, `0 B`; time≥1000ms→seconds; memory≥1024→KiB,
≥1048576→MiB, hai chữ số lẻ. Không đo tracemalloc, RSS hoặc GPU trong HUD.

```text
HudShell(pixel2d,model=HudViewModel())
update_view_model(model)
apply_layout(layout)
dispose()
DashboardPresentation(app,model)
DashboardPresentation.dispose()
create_dashboard(level=DEFAULT_LEVEL,*,pose=BasicOrientation.STANDING,
                 shadows=False,antialiasing=True) -> (app,renderer)
```

HudShell sở hữu một pixel2d subtree, xây widgets một lần. update_view_model cần
HudViewModel (isinstance), gọi main thread khi caller có dữ liệu mới; wrong model
ValueError, disposed RuntimeError. apply_layout sau dispose là no-op; resize bình
thường chỉ đổi geometry/text. dispose idempotent, xóa owned widgets/root.
Long level/status/metric text được ellide, model giữ nguyên. Tất cả 13 action
buttons, slider và thumb luôn disabled, command=None. ViewModel update không
enable controls. Chưa có action-binding/enabling API được duyệt.

DashboardPresentation cần existing app.presentation, giữ viewport/HUD, không host.
create_dashboard reuse create_preview, đặt title `Bloxorz Solver — 3D Preview`,
friendly level label từ filename stem; pair return giữ nguyên, component tại
app.dashboard. Scene/UI updates luôn main thread; worker chỉ trả plain data.

## 9. Ví dụ composition từ Board/State

**VERIFIED EXAMPLE:** startup, data binding và cleanup đã chạy trên Ubuntu qua
bounded onscreen smoke. `app.run()` là loop thật; harness verification đóng đúng
native window theo PID bằng window manager từ bên ngoài, kiểm exit 0/output count 0.
Đây là các component API hiện có, chưa là hợp đồng Controller hoàn chỉnh.

<!-- example: basic-composition -->
```python
from src.core.board import Board
from src.gui.app import BloxorzPreviewApp
from src.gui.board_preview import PreviewPresentation, dispose_presentation
from src.gui.dashboard_preview import DashboardPresentation
from src.gui.hud import HudViewModel
from src.gui.render_adapter import build_board_data, build_game_snapshot
from src.gui.renderer import BasicSceneRenderer

board = Board("levels/level_01.json")
state = board.get_initial_state()
data = build_board_data(board, level_id="levels/level_01.json")
snapshot = build_game_snapshot(
    state, board_data=data, session_id="example-session-1", state_revision=0,
)
app = BloxorzPreviewApp()  # Chỉ tạo host này, không gọi thêm create_dashboard().
renderer = None
try:
    renderer = BasicSceneRenderer(app.static_board_root, app.block_root)
    renderer.load_board(data)
    renderer.show_snapshot(snapshot)
    app.presentation = PreviewPresentation(app, data)
    app.dashboard = DashboardPresentation(app, HudViewModel(level_label="Level 01"))
    # Caller biết số moves từ lúc vừa load là 0; search metrics chưa biết vẫn None.
    app.dashboard.hud.update_view_model(HudViewModel(level_label="Level 01", move_count=0))
    app.run()
finally:
    try:
        dashboard = getattr(app, "dashboard", None)
        if dashboard is not None:
            dashboard.dispose()
    finally:
        try:
            dispose_presentation(app)
        finally:
            try:
                if renderer is not None:
                    renderer.dispose()
            finally:
                app.destroy()
```

Đổi board với host này cần caller phối hợp `renderer.load_board(new_data)`,
`renderer.show_snapshot(new_snapshot)`, existing camera `fit_board(new_data,w,h)`
với viewport dimensions thực tế và cập nhật HUD. on_refit đã bind sẽ cập nhật
style/light bounds. Không tự ghép Controller/solver, không gọi private NodePaths.
Một public coordinator cho thao tác này là **PROPOSED / PENDING**, chưa có method
`load_level` hoặc `apply_board` ở app.presentation.

## 10. Lifecycle bắt buộc

Thứ tự normal: **dashboard.dispose → dispose_presentation(app) → renderer.dispose
→ app.destroy**, dùng nested finally như example. Bỏ dashboard step cho Board Preview.
Stop commands/worker delivery trước cleanup; ownership này do Controller tương lai giữ.

app.destroy detach SceneRoot **trước** ShowBase finalExitCallbacks. Dashboard callback
được insert đầu, restore region/binding không refit nếu scene empty; presentation
callback gỡ camera/lights/style. Đây là safety net, không thay renderer.dispose:
renderer vẫn giữ prototype references cho tới khi caller dispose/release nó.
Không hướng dẫn host-first như normal order. Dispose chỉ tài nguyên mình sở hữu;
đừng dùng old app.presentation.camera sau presentation.dispose vì field đã None.

## 11. Entry points và commands

Ubuntu/Linux, từ repository root, **VERIFIED**:

```bash
.venv/bin/python -B -m src.gui.app
.venv/bin/python -B -m src.gui.board_preview
.venv/bin/python -B -m src.gui.dashboard_preview
.venv/bin/python -B -m src.gui.dashboard_preview --pose HORIZONTAL
.venv/bin/python -B -m src.gui.dashboard_preview --pose VERTICAL
.venv/bin/python -B -m src.gui.dashboard_preview --shadows
.venv/bin/python -B -m src.gui.dashboard_preview --no-aa
.venv/bin/python -B -m src.gui.dashboard_preview --level levels/level_01.json
```

Board/Dashboard có --level/--pose/--shadows/--no-aa; Foundation không có custom
argparse CLI. Minimum Dashboard 1024×720; năm sizes/evidence tại
[release checklist](STAGE3_RELEASE_CHECKLIST.md).

Windows commands tương ứng, **hướng dẫn dự kiến / NOT TESTED native**:

```powershell
.\.venv\Scripts\python.exe -B -m src.gui.app
.\.venv\Scripts\python.exe -B -m src.gui.board_preview
.\.venv\Scripts\python.exe -B -m src.gui.dashboard_preview
```

## 12. Điểm chưa có

Advanced tile/state/event contracts, public action-binding/enabling, worker/replay,
animation requests/completion/cancel, integrated session coordinator và stable public
presentation facade đều chưa triển khai. Xem [team decisions](TEAM_INTEGRATION_REVIEW.md)
để phân biệt API đang dùng với proposal Stage 6; không tự thêm fields vào DTO v1.
