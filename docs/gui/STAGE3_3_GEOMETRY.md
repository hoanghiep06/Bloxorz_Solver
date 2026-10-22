# Chặng 3.3 — Procedural Geometry & Basic 3D Board Renderer

Ngày: **22/10/2026**, Asia/Ho_Chi_Minh.

**STAGE 3.3 BASIC GEOMETRY COMPLETE**, trên Ubuntu/X11 và Panda3D runtime hiện tại.
Đã qua Gates A–D: pure math, mesh integrity, scene composition, onscreen visual smoke
và regression. Đây là preview tĩnh; không phải game playable hay Camera/Lighting/HUD
production. Windows **NOT TESTED**.

## 1. Preflight và phạm vi

| Hạng mục | Đã kiểm chứng trước khi sửa |
|---|---|
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `956c0a0528c9170afceda58551772bcadd3fc12a` |
| Tracked/staged diff | Rỗng |
| Thay đổi có sẵn | Tám file untracked của 3.1/3.2; giữ nguyên |
| Renderer | `src/gui/renderer.py` rỗng, không có implementation khác để ghi đè |
| Host | Một `BloxorzPreviewApp`, bốn roots đúng 3.1 |
| Contracts/Adapter | DTO bất biến và hai factories đúng source 3.2 |
| Level | `levels/level_01.json`, 4×7, start (1,1), goal (1,6) |
| Python GUI | `.venv/bin/python`, CPython 3.14.4 |
| Panda3D | 1.10.16, đã có sẵn; không install thêm |
| Display | Ubuntu, X11, `DISPLAY=:0.0` |

Đã đọc source GUI hiện có, tests foundation/contracts/adapter và các báo cáo 3.1/3.2;
đối chiếu GUI README, Geometry/Visual/Render Contract và Stage 2 Handoff.
Đã ghi SHA-256 của 46 file tracked/untracked không bị ignore trước thay đổi.
Không đồng bộ remote hoặc thay đổi branch. Phân công vẫn giữ: Phong sở hữu Core,
Tài sở hữu Controller/session/input/replay; Phước sở hữu geometry/renderer.

Baseline chạy lại trước triển khai:

| Lệnh | Ran | PASS | FAIL | ERROR | SKIP | Thời gian unittest |
|---|---:|---:|---:|---:|---:|---:|
| `.venv/bin/python -B -m unittest discover -s tests` | 122 | 122 | 0 | 0 | 0 | 0.580s |
| `python3 -B -m unittest discover -s tests` | 122 | 120 | 0 | 0 | 2 | 0.350s |

## 2. Đối chiếu các chặng trước

- `app.py`, các scene roots, entry point foundation và lifecycle 3.1 giữ nguyên.
- Dùng nguyên `StaticBoardData`, `GameSnapshot`, `BasicTileKind`, `BasicOrientation`;
  không sửa/copy Contracts hoặc Adapter để phục vụ Renderer.
- Goal lấy từ `goal_cells`; tiles chỉ VOID/FLOOR. Renderer không biết raw tile code 2.
- X tăng theo col, Y giảm theo row, Z lên trên, top floor Z=0 như Geometry Spec.
- **Khác biệt thông số có chủ đích:** đề bài 3.3 mới chỉ định recess depth khoảng **0.14**;
  dùng đúng giá trị này thay đề xuất **0.65** ở Stage 2. Không sửa tài liệu lịch sử.
  Aperture vẫn 0.76 < block 1.0; chưa có goal-sink animation để nghiệm thu clearance.
- Stage 2 receipt/callback/animation APIs còn là đề xuất. API Basic 3.3 dùng None khi
  thành công và exception rõ khi reject; không tạo receipt/AnimationResult giả.
- Camera cố định và hai đèn chỉ phục vụ preview được giao trong 3.3; production camera,
  vertical FOV/aspect management/auto-fit/shadows/material system vẫn thuộc 3.4.

## 3. Files và kiến trúc

| File | Thay đổi | Trách nhiệm |
|---|---|---|
| [geometry_math.py](../../src/gui/geometry_math.py) | Mới | Cell XY, logical bounds, canonical BlockPose |
| [mesh_factory.py](../../src/gui/mesh_factory.py) | Mới | Shared Floor/Goal/Block GeomNode prototypes |
| [renderer.py](../../src/gui/renderer.py) | Sửa placeholder rỗng | BasicSceneRenderer, DTO-only composition/lifecycle |
| [board_preview.py](../../src/gui/board_preview.py) | Mới | Core→Adapter→Renderer wiring, host cũ, CLI preview |
| [test_gui_geometry_math.py](../../tests/test_gui_geometry_math.py) | Mới | 15 pure Python tests |
| [test_gui_renderer.py](../../tests/test_gui_renderer.py) | Mới | 33 Panda3D mesh/scene/preview tests, không tạo window |
| Tài liệu này | Mới | Evidence, API, limitations và handoff |

```text
geometry_math -> Contracts Enum                 (stdlib, không Panda/Core)
mesh_factory -> panda3d.core                    (không window, không Core)
renderer -> Contracts + geometry_math + meshes  (không Core, không ShowBase)
board_preview -> Core + Adapter + Renderer + host 3.1
```

Không package mới, external mesh/texture/font/assets, Pygame, raw OpenGL, shader,
NumPy, dependency edit, thread/process worker, custom engine hoặc background task.
Các subprocess chỉ dùng trong tests/import probes; preview không tạo subprocess.

## 4. Panda3D APIs sử dụng

Mesh dùng `GeomVertexData`, `GeomVertexFormat.getV3n3c4`, `GeomVertexWriter`,
`GeomTriangles`, `Geom`, `GeomNode`, `Geom.UHStatic`. Flat normals và vertex colors
được ghi trực tiếp; mặt polygon lồi được chia fan thành triangles có winding theo normal.
`Mat4.translateMat` bake offset Z vào mesh Floor. Không bật two-sided để che lỗi winding.

Scene dùng `NodePath.attachNewNode/reparentTo/removeNode`, `setPos/setQuat`,
`Quat.setFromAxisAngle`, `Vec3`. Tests đọc vertex buffers bằng `GeomVertexReader`,
decompose triangle primitive, kiểm tra transformed AABB bằng `getTightBounds`.
Các thao tác này không cần ShowBase/window/GPU context trong unit tests.

Preview dùng host có sẵn, camera `setPos/lookAt`, lens `setFov/setNearFar`,
`AmbientLight` và `DirectionalLight`. Không viết production camera/lighting class.

## 5. Pure geometry math

Public APIs:

```python
cell_to_world(row, col, *, rows, cols, pitch=1.0) -> (x, y)
logical_board_bounds(rows, cols, *, pitch=1.0) -> ((min_x, min_y), (max_x, max_y))
block_pose(row, col, orientation, *, rows, cols, pitch=1.0) -> BlockPose
```

`BlockPose` là frozen/slotted dataclass chứa center, dimensions, rotation_axis,
angle_degrees. Anchor vẫn nằm trong snapshot, không bị thay bằng world center.
Dimensions là kích thước nominal của model sau rotation, không phải scale node.

```text
X = (col - (cols - 1)/2) * pitch
Y = ((rows - 1)/2 - row) * pitch
logical bounds = ((-cols*pitch/2, -rows*pitch/2),
                  ( cols*pitch/2,  rows*pitch/2))
```

Bounds tính toàn footprint cell, gồm void và nửa ô ngoài rìa; khác visual tile width 0.96.
Kiểm tra dimensions nguyên dương, cell nguyên trong bounds, pitch hữu hạn dương (không bool),
Enum hợp lệ và occupied footprint không vượt board. Không kiểm tra floor support/game rules.

| Orientation tại (1,1), board 4×7 | Center | Dimensions | Axis / angle |
|---|---|---|---|
| STANDING | (-2, 0.5, 1) | (1,1,2) | Z / 0° |
| HORIZONTAL | (-1.5, 0.5, 0.5) | (2,1,1) | +Y / 90° |
| VERTICAL | (-2, 0, 0.5) | (1,2,1) | +X / 90° |

Goal (1,6) có XY=(3,0.5). VERTICAL là block nằm theo hàng, không phải đứng theo Z.
Tính center nằm ngang qua col+0.5; nằm dọc qua row+0.5. Bottom Z=center_z−height/2=0.
Pitch tùy chọn scale mọi kích thước và vị trí; không scale pose/pivot node.

## 6. Mesh dimensions, Floor và Void

Thông số ở pitch=1; các kích thước được nhân pitch khi tạo mesh:

| Mesh | Nominal dimensions | Z bounds | Bevel / rim |
|---|---|---|---|
| Floor | 0.96×0.96×0.18 | [-0.18,0] | Chamfer 0.02 |
| Goal | Outer 0.96×0.96×0.18 | Outer [-0.18,0], cavity đáy -0.14 | Rim 0.10, aperture 0.76 |
| Block | 1×1×2, local origin tại tâm | [-1,1] trước pose | Chamfer 0.03 |

Floor/Block dùng sáu faces inset, 12 edge strips và tám corner triangles. Nominal outer
support planes không đổi; bevel cắt vào bên trong. Floor có mặt trên, bốn sides và underside.
44 triangles mỗi Floor prototype; mesh reuse giữa các ô. Màu top `#DCE5ED`, sides
`#A8BBCD`, bevel `#91A8BB`. Pitch 1 và width 0.96 cho seam nominal 0.04.
Bevel làm vùng phẳng trên cùng nhỏ hơn outer bounds; đó là chamfer thật, không đổi cell pitch.

VOID bị bỏ qua hoàn toàn: không node tile, top face, black square, collider hoặc ground plane.
Level thật có 28 cells: 8 VOID và 20 FLOOR, trong đó một FLOOR được thay bằng Goal mesh.
Scene vì vậy có **19 Floor instances + 1 Goal**, không phải 20 Floor cộng thêm decal goal.

## 7. Goal recess và các input đặc biệt

Goal mesh gồm bốn top rim trapezoids ở Z=0, bốn outer walls, bốn inner walls,
cavity bottom ở Z=-0.14 và underside ở Z=-0.18: 28 triangles. Không có top quad kín
bên dưới miệng hố. Rim steel blue `#527B9C`, interior navy `#273B50`.
Inner normals hướng vào khoảng rỗng; bottom cavity hướng lên, underside hướng xuống.
Diện tích các triangles Z=0 đúng `0.96² - 0.76²`, không phủ aperture.

Hành vi theo DTO 3.2:

- `goal_cells=()`: vẽ board không goal.
- Nhiều goal trên FLOOR: vẽ tất cả, dùng chung Goal prototype; không kết luận gameplay nhiều goal.
- Goal trên VOID: reject rõ `ValueError`, giữ scene trước đó. Đây là unsupported visual profile,
  không tự tạo Floor hoặc thay đổi luật Core.
- Không đọc raw grid, không suy goal từ mã 2.

## 8. Main Block và orientation transforms

Một prototype duy nhất có nominal 1×1×2, đủ sáu mặt và origin ở tâm hình học.
Block dùng main `#527B9C`, dark `#354F68`, chamfer/detail `#91ADC3`.
Chi tiết lệch tâm trên local -Y face được tạo bằng cách chia mặt thành vùng ngoài và
một hình chữ nhật màu highlight phẳng cùng mặt: không overlay/decal đồng phẳng,
không hở mesh, không tăng bounds. Tổng Block prototype 52 triangles.

Renderer tạo `MainBlockVisual -> MainBlockMesh` một lần, cập nhật absolute position/quaternion.
HORIZONTAL quay +90° quanh Y đưa local Z sang X; VERTICAL quay +90° quanh X đưa local Z
sang -Y. AABB phải đúng kích thước bất kể dấu trục dài; không đoán theo tên HPR.
Tests đọc AABB thật sau transform cho cả ba pose và sau 300 updates; node scale luôn (1,1,1).
Không nhân dồn quaternion, flatten block hoặc áp dụng interpolation/rolling/pivot hiện tại.

## 9. Scene graph và mesh reuse

```text
SceneRoot                         # host 3.1 sở hữu
├── StaticBoardRoot
│   └── BasicBoardContent          # Renderer sở hữu
│       ├── Floor-r-c              # unique transform parents
│       │   └── FloorMesh          # shared immutable GeomNode
│       └── Goal-r-c
│           └── GoalMesh           # shared prototype
├── DynamicTileRoot               # empty
├── BlockRoot
│   └── MainBlockVisual            # unique pose node, Renderer sở hữu
│       └── MainBlockMesh
├── EffectsRoot                   # empty
├── PreviewAmbient                # chỉ board_preview tạo, host cleanup
└── PreviewKey                    # chỉ board_preview tạo, host cleanup
```

Các Floor dùng chung GeomNode/vertex data. Vị trí nằm trên unique parent NodePaths,
không set transform lên shared mesh node làm mọi instance di chuyển theo nhau.
Renderer không tạo SceneRoot khác, không sửa root names, không quản lý camera/lighting.
Hai lights là preview-only; DynamicTileRoot/EffectsRoot vẫn rỗng.

## 10. BasicSceneRenderer API và lifecycle

```python
renderer = BasicSceneRenderer(app.static_board_root, app.block_root, pitch=1.0)
renderer.load_board(board_data)
renderer.show_snapshot(snapshot)
# ... snapshots theo logical updates ...
renderer.clear()    # có thể load lại
renderer.dispose()  # terminal; gọi lặp lại an toàn
```

Các methods trả None khi thành công. Wrong DTO type: TypeError; invalid/unsupported/mismatch:
ValueError; gọi trước load hoặc sau dispose: RuntimeError. Main-thread ownership do caller giữ.

`load_board`:

- Revalidate schema/structure của đúng StaticBoardData class và supported goal profile.
- Cùng DTO là no-op, giữ block đang hiển thị. Cùng revision nhưng khác payload bị reject.
- Board mới được build trong subtree detached. Validation/build fail không xóa scene cũ.
- Khi build thành công mới gỡ owned board/block cũ, attach content mới và reset snapshot binding.
- Không Board constructor, Core rule call hoặc graphics window trong Renderer.

`show_snapshot`:

- Yêu cầu đã load board, đúng DTO/schema/WHOLE/Enum, footprint hợp lệ và board revision khớp.
- Tính canonical pose, kiểm tra logical bounds; không kiểm tra floor support/thắng/thua.
- Không rebuild static geometry, không clone board, không tạo block mới cho mỗi update.
- Cùng session: reject revision giảm; cùng revision chỉ chấp nhận nội dung giống hệt.
- Session strings là opaque tokens; caller có quyền thay session. Renderer chỉ nhớ snapshot
  hiện tại, không tạo session manager hoặc tự xác thực session cũ đã bị retire.

`clear` chỉ remove owned content/block và reset binding, giữ prototypes để reuse.
`dispose` gọi clear, giải phóng prototype references và đánh dấu disposed; gọi nhiều lần an toàn.
Không xóa roots, foreign siblings hoặc ShowBase; caller dispose trước host.destroy.
Không tasks, timers, queue hoặc callbacks phát sinh từ Renderer.

## 11. Standalone preview và cách chạy

Từ repository root:

```bash
.venv/bin/python -B -m src.gui.board_preview
.venv/bin/python -B -m src.gui.board_preview --pose HORIZONTAL
.venv/bin/python -B -m src.gui.board_preview --pose VERTICAL
.venv/bin/python -B -m src.gui.board_preview --level levels/level_01.json
.venv/bin/python -B -m src.gui.board_preview --help

# Demo foundation cũ giữ nguyên:
.venv/bin/python -B -m src.gui.app
```

Default level path được resolve theo source file, không phụ thuộc cwd để tìm level mặc định.
`--level` relative path do người dùng truyền được resolve theo cwd. Level ID là absolute
path đã resolve; chỉ là ID có ý nghĩa cho preview, không phải quyết định ID chung nhóm.
Session preview là `"board-preview"`, state_revision=0. Mỗi process preview là phiên độc lập.

Wiring chỉ nằm trong board_preview: load Board → adapter static data → initial state/pose
fixture → adapter snapshot → một BloxorzPreviewApp → Renderer. Alternative orientations
đặt tại initial anchor, không gọi transition hay tìm nước đi. Fixture vượt bounds bị adapter
reject trước khi mở window. Không manual keyboard input, menu, solver hay replay.

`create_preview(level, *, pose=BasicOrientation.STANDING)` trả `(app, renderer)`;
caller chịu trách nhiệm lifecycle. `main()` gọi app.run và luôn dispose/destroy trong finally.
Lỗi khi populate scene sau tạo host cũng cleanup rồi raise lại, không trả scene mặc định.

Camera preview cố định `(7,-11,10)`, nhìn `(0,0,0.2)`, lens setFov(45), near/far 0.1/100.
Đây là FOV preview theo API lens hiện tại, không phải nghiệm thu vertical FOV/aspect/auto-fit
production của Stage 2. Ambient 0.55 và directional 0.5, key HPR=(-35,-55,0) giúp đọc
được sides, bevel và recess. Không shadow/PBR/material system, camera fit/resize listener.

## 12. Unit tests và chất lượng mesh

Gate A chạy trước mesh; Gate B chạy trước nối scene; Gate C chạy trước desktop smoke.

| Gate / nhóm | Tests mới | Kết quả |
|---|---:|---|
| A — Pure math | 15 | PASS trên cả venv và system Python |
| B — Mesh factory | 10 | PASS, real Panda vertex/triangle data |
| C — Renderer/preview unit checks | 23 | PASS, real NodePath/Geom; không window |
| Tổng mới | 48 | PASS trong venv |

Các IDs T01–T41 và T44 có test tương ứng trong hai files mới. T42 dùng lại foundation
tests/onscreen smoke; T43 dùng nguyên 37 contracts/adapter tests của 3.2 trong regression.
Không sửa tests cũ hoặc tạo mocks để giả kết quả GPU.

Coverage gồm centered odd/even/non-square boards; cả ba centers/dimensions/bottoms;
footprint extents; pitch scaling; wrong inputs; import pure math với Python `-S`.
Mesh tests kiểm tra finite positions/normals, indices hợp lệ, nonzero triangle area,
unit normals, normal/winding alignment, outward convex faces, cavity wall directions,
no duplicate coincident triangles và mỗi welded geometric edge có đúng hai triangles.
Như vậy chamfer/inlay ghép kín, không lấy two-sided rendering làm bằng chứng correctness.

Scene tests gồm 19 Floor + 1 Goal/8 Void, shared mesh identity, authoritative goal move,
transformed AABBs, 300 pose updates không drift, 50 repeated loads/updates giữ node count,
20 board replacements, idempotent dispose, foreign nodes, revision mismatch/stale checks,
empty/multiple/VOID goal handling và failure không phá scene cũ.

Subprocess import guard chặn Core, solver, adapter, app, controller, ShowBase và Pygame
khi import/instantiate Renderer; GraphicsEngine vẫn có 0 windows. Separate preview import
probe xác nhận không tự tạo host/window. Mock chỉ dùng kiểm tra cleanup/control flow,
không dùng kết luận mesh hoặc visual GPU PASS.

Lệnh gate và regression đã thực thi:

```bash
python3 -B -m unittest discover -s tests -p test_gui_geometry_math.py -v
.venv/bin/python -B -m unittest discover -s tests -p test_gui_renderer.py -v
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

## 13. Regression sau triển khai

| Runtime | Ran | PASS | FAIL | ERROR | SKIP | Thời gian unittest |
|---|---:|---:|---:|---:|---:|---:|
| `.venv/bin/python` | 170 | 170 | 0 | 0 | 0 | 0.875s |
| `python3` hệ thống | 170 | 135 | 0 | 0 | 35 | 0.474s |

System Python không có Panda3D: skip 33 mesh/scene/preview tests và 2 foundation tests
với lý do rõ; 15 pure geometry tests vẫn chạy. Không công bố system Python đã nghiệm thu
rendering. Venv chạy cả foundation, contracts, adapter và tests cũ không skip.

## 14. Visual smoke thực tế và screenshots

Đã mở cửa sổ **onscreen GraphicsWindow qua glxGraphicsPipe**, 1280×720 trên X11.
GPU renderer: **AMD Radeon Graphics (radeonsi, renoir, ACO, DRM 3.64,
7.0.0-38-generic)**. Dùng `.venv` Python 3.14.4 + Panda3D 1.10.16 đã kiểm chứng.
Không offscreen buffer hoặc hình minh họa AI làm bằng chứng.

Đã chạy entry point `.venv/bin/python -B -m src.gui.board_preview`,
đóng bằng window-manager close request (`wmctrl -ic` tới đúng window ID đã quan sát),
process exit 0. Lệnh `.venv/bin/python -B -m src.gui.app` cũng chạy và exit 0.
Một harness kiểm tra lại host foundation onscreen, bốn roots đều empty, capture rồi destroy.

Ba pose được kiểm tra trong các onscreen preview, xử lý frames bằng taskMgr.step,
capture framebuffer của window bằng Panda3D và dispose/destroy sau mỗi lần.
Đã mở và xem các PNG thật:

| Evidence tạm | Nội dung | Kết quả |
|---|---|---|
| `/tmp/bloxorz-stage3-3-standing.png` | Whole block đứng tại initial anchor | PASS |
| `/tmp/bloxorz-stage3-3-horizontal.png` | Whole block nằm theo X | PASS |
| `/tmp/bloxorz-stage3-3-vertical.png` | Whole block nằm theo Y | PASS |
| `/tmp/bloxorz-stage3-3-foundation-regression.png` | Host cũ nền sáng, chưa có geometry | PASS |

Nhìn rõ Floor có thickness/seams/chamfer, Void là khoảng trống thật, Goal có rim/inner walls
và recess, Main Block có bevel/detail và ba tư thế. Không thấy clipping, lộ backface chính,
mặt bị mất hoặc Z-fighting trong các góc tĩnh đã chụp. Đây là smoke giới hạn góc camera
demo, không phải kiểm chứng mọi camera, animation hay hardware.

Ảnh HORIZONTAL đầu tiên bị đen vì capture quá sớm sau khi mở lại window nhanh trong
smoke harness. Đã chụp lại ở process riêng sau xử lý window events/frames đủ thời gian,
kiểm tra average pixel không đen rồi xem ảnh thật. Không đổi Renderer/host để che lỗi capture.
Preview-only lighting được thêm sau ảnh kiểm tra đầu để dễ đọc chiều sâu; chưa có lighting 3.4.
Sau cleanup, GraphicsEngine.getGlobalPtr().getNumWindows()==0 được assert.
Ảnh ở `/tmp` không đưa vào Git và có thể mất sau khi dọn thư mục tạm.

## 15. Known limitations và nâng cấp 3.4

- Camera cố định dành cho level_01; board lớn/wide/tall có thể clipping trong preview.
  Pure math kiểm tra các board shapes khác, nhưng không có robust auto-fit/aspect/resize.
- Chưa anti-alias/material/shadow/background production, responsive layout, HUD hoặc buttons.
- Chưa rolling/falling/goal sink; pose là canonical instant placement, không giữ face history
  từ chuỗi chuyển động. Chưa tạo animation pivot hoặc callback protocol.
- Chưa Advanced, gameplay Controller, manual input, solver orchestration/replay hay session manager.
- Renderer giữ opaque current session và monotonic revision trong phiên; lọc late callbacks
  từ session cũ là trách nhiệm Controller sau này.
- Goals trên VOID bị reject visual profile; không tự suy gameplay. Nhiều/không goal chỉ là
  hành vi hiển thị xác định cho DTO hợp lệ, không claim Core hỗ trợ nhiều goal.
- Tests float/AABB dùng tolerance; pitch thông thường 0.5/1/2 được kiểm chứng, không benchmark
  precision của tọa độ/kích thước cực lớn hoặc cực nhỏ trong engine float32.
- Mới một level production, chưa đáp ứng >=10 maps/benchmark của toàn đồ án.
- Windows NOT TESTED. Không install/update dependencies hoặc sửa requirements để giả cross-platform.

3.4 cần nhiệm vụ riêng sau review: camera/viewport fit thực tế, lighting/material/background
và visual quality theo phạm vi được giao sau. Không tự triển khai tiếp từ báo cáo này.

## 16. Những vấn đề cần Phong/Tài xác nhận

**Phong:** vẫn cần semantic Advanced tile schema, bridge IDs/state mapping, split/active cube,
ordered events và final-state/outcome semantics trước Advanced/animation integration.
Xác nhận Basic mapping phù hợp Core refactor tương lai. Renderer hiện chỉ nhận DTO 3.2,
không sửa State/Board/Transition để chạy preview.

**Tài:** thống nhất level/session IDs của ứng dụng thật, state_revision tăng/reset,
state-board pairing, caller quyền thay session, load/show/dispose ordering và main-thread wiring.
Preview không phải Controller mẫu để sao chép gameplay. Receipt/callback, busy/cancel,
stale session, HUD và replay sequencing vẫn cần review giao thức riêng.
Không gửi tin nhắn cho các thành viên trong lượt thực hiện này.

## 17. Git scope và acceptance

Tracked diff duy nhất là `src/gui/renderer.py` từ placeholder rỗng sang implementation.
Sáu files mới thuộc phạm vi 3.3 chưa stage. Tám file untracked 3.1/3.2 vẫn nguyên.
Đối chiếu manifest: **45/46 file có sẵn không đổi**, ngoại lệ duy nhất là Renderer được giao.
Không sửa app, contracts, adapter, controller, Core, solvers, main.py, requirements, levels,
tests cũ hoặc tài liệu 3.1/3.2/Stage 2. Không git add/commit/push/merge/reset/branch change.
Branch/HEAD giữ nguyên; screenshots chỉ ở `/tmp`.

| # | Acceptance | Trạng thái | Bằng chứng |
|---:|---|---|---|
| 1 | Audit source hiện tại | PASS | Preflight, source/tests/docs và baseline |
| 2 | Bảo toàn file chưa commit | PASS | SHA-256 tám file có sẵn |
| 3 | Đúng hệ tọa độ Stage 2 | PASS | T01–T12, three pose fixtures |
| 4 | Pure geometry math | PASS | 15 tests, `-S` import probe |
| 5 | Reusable procedural Floor | PASS | Shared GeomNode identity, mesh tests |
| 6 | Void không có sàn | PASS | T21, 8 missing cells, screenshots |
| 7 | Goal có rim/depth thật | PASS | T22–T24, screenshot recess |
| 8 | Main Block 3D | PASS | Mesh dimensions/normals, onscreen |
| 9 | Ba orientations | PASS | Math, AABB và ba PNG |
| 10 | Block transform đúng | PASS | T27/T28 |
| 11 | Bottom Z=0 | PASS | T10 và transformed AABB |
| 12 | Renderer dùng DTO 3.2 | PASS | Real level DTO integration tests |
| 13 | Renderer không phụ thuộc Core | PASS | Import guard T30 |
| 14 | Dùng roots 3.1 | PASS | Scene graph dump, foreign node tests |
| 15 | Không ShowBase thứ hai | PASS | Một host/preview, renderer import probe |
| 16 | Standalone preview | PASS | Module CLI và window manager close, exit 0 |
| 17 | Foundation vẫn chạy | PASS | Old tests, entry point, fresh empty-root screenshot |
| 18 | Unit geometry tests chạy | PASS | 48 tests mới venv PASS |
| 19 | Regression chạy | PASS | 170/170 venv; 135 PASS + 35 SKIP system |
| 20 | Visual runtime thực tế | PASS | Onscreen GLX, ba PNG đã xem |
| 21 | Không sửa Core | PASS | Manifest |
| 22 | Không sửa Controller | PASS | Manifest |
| 23 | Không sửa Solver | PASS | Manifest |
| 24 | Không triển khai 3.4/3.5 | PASS | Chỉ camera/lights preview; không production/HUD/animation |
| 25 | Không commit/push/merge | PASS | Branch/HEAD/staging giữ nguyên |
| 26 | Documentation | PASS | Tài liệu này, API/commands/evidence/limits |
| 27 | Git diff report | PASS | Tracked renderer + sáu files mới, manifest |

**Dừng tại 3.3 để người dùng review trước khi giao Chặng 3.4.**
