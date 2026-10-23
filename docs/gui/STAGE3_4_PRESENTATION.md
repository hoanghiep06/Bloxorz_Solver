# Chặng 3.4 — Camera, Lighting, Materials & Visual Quality

Ngày: **22/10/2026**, Asia/Ho_Chi_Minh.

**STAGE 3.4 CAMERA & VISUAL QUALITY PARTIALLY COMPLETE**.

Camera/resize, Basic lighting, matte presentation và gradient đã hoạt động; shadow mapping
và MSAA đã được nhìn thấy/kiểm tra trên máy hiện tại. 26 tests mới PASS.
**Gate full regression chưa PASS**: hai tests geometry 3.3 đọc vectors sau khi buffer mesh
được giải phóng. Đã tái hiện độc lập, không import presentation 3.4; không sửa tests cũ vì
scope yêu cầu read-only. Chi tiết và bản sửa đề xuất ở mục 13. Windows **NOT TESTED**.

## 1. Mục tiêu, preflight và quyền sở hữu

Triển khai riêng camera/lighting/material/background/AA và preview wiring.
Giữ Core của Phong, Controller của Tài, Renderer/geometry/DTO/host đã có.

| Preflight | Kết quả kiểm chứng |
|---|---|
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `956c0a0528c9170afceda58551772bcadd3fc12a` |
| Tracked changes có sẵn | `src/gui/renderer.py`, implementation 3.3 chưa commit |
| Untracked có sẵn | 14 files 3.1–3.3, gồm board_preview.py |
| Staged changes | Không có |
| Interpreter | `.venv/bin/python`, CPython 3.14.4 |
| Panda3D | 1.10.16, có sẵn, không install/update |
| Desktop | Ubuntu/X11, `DISPLAY=:0.0` |
| GUI baseline | Preview 3.3 dùng camera fixed và hai đèn tạm; không production camera |
| Manifest trước sửa | 52 file tracked/untracked không bị ignore |

Đã đối chiếu báo cáo 3.1–3.3, Layout/Camera, Visual, Geometry và Render Contract;
audit app, renderer, preview, geometry/math/mesh, Contracts/Adapter và tests liên quan.
Không suy đoán tiến độ remote, không fetch/pull hoặc chuyển branch.

Baseline đo lại trước thay đổi:

| Runtime | Ran | PASS | FAIL | ERROR | SKIP | Thời gian unittest |
|---|---:|---:|---:|---:|---:|---:|
| `.venv/bin/python` | 170 | 170 | 0 | 0 | 0 | 0.665s |
| `python3` hệ thống | 170 | 135 | 0 | 0 | 35 | 0.338s |

Các kết quả lịch sử 3.3 không được dùng thay baseline này. Full baseline PASS không chứng
minh test helper cũ an toàn về lifetime; thay đổi allocation order sau đó đã làm lộ lỗi.

## 2. Files và kiến trúc

| File | Thay đổi | Trách nhiệm |
|---|---|---|
| [camera.py](../../src/gui/camera.py) | Mới | Pure frustum math, BoardCameraController, resize ownership |
| [scene_lighting.py](../../src/gui/scene_lighting.py) | Mới | Ambient/key/fill, shadow lens, capability fallback |
| [scene_style.py](../../src/gui/scene_style.py) | Mới | Matte Material, gradient, AA render states |
| [board_preview.py](../../src/gui/board_preview.py) | Wiring hiện có | Bỏ camera/đèn tạm, compose presentation và cleanup |
| [test_gui_camera.py](../../tests/test_gui_camera.py) | Mới | 12 tests: 8 pure math, 4 engine integration |
| [test_gui_lighting.py](../../tests/test_gui_lighting.py) | Mới | 14 tests presentation/cleanup/import |
| Tài liệu này | Mới | API, evidence, kết quả và giới hạn |

`camera.py` chỉ import stdlib + StaticBoardData ở module scope. Panda3D và DirectObject
chỉ được import khi tạo controller. Contracts/geometry_math không kéo theo engine.
Lighting/Style dùng Panda3D, không Core/Controller/Solver. Chỉ board_preview làm wiring.
BasicSceneRenderer tiếp tục sở hữu geometry và public API cũ; không có API camera/light
mới chen vào renderer.py. Không thêm package, engine khác, external assets hoặc Pygame.

## 3. Camera basis và các quy ước

Mặc định `CameraConfig(azimuth=30, elevation=45, vertical_fov=45, padding=0.13)`.
Azimuth đo từ world -Y xoay về +X; elevation so với XY. Với a/e tính bằng radians:

```text
back = (sin(a)*cos(e), -cos(a)*cos(e), sin(e))  # target -> camera
forward = -back                                # camera -> target
right = (cos(a), sin(a), 0)
up = right × forward
camera_position = target + distance * back
```

Default back ≈ `(0.353553,-0.612372,0.707107)`. Các basis vectors đơn vị và trực giao;
không đồng nhất camera source direction với ray/view direction hoặc heading số 30.
Sau đặt position, controller dùng lookAt(target) với world-up Z.

Basic envelope ổn định cho toàn level:

```text
minimum = (-cols*pitch/2, -rows*pitch/2, -0.18*pitch)
maximum = ( cols*pitch/2,  rows*pitch/2,  2.30*pitch)
target = (center_x, center_y, 0.4*pitch)
```

Gồm footprint cả void, thickness, goal hiện tại sâu 0.14, Whole Block cao 2 và headroom
0.30. Không dùng goal well 0.65 từ thiết kế cũ vì geometry 3.3 thật đã dùng 0.14.
Không tạo fake block/envelope node trong Scene Graph. Bounds không phụ thuộc snapshot,
background hoặc số floor visible; camera không zoom lại khi khối di chuyển/đổi orientation.
Có thể cung cấp SceneBounds mở rộng có chủ đích, không sửa State/Core.

## 4. Perspective FOV và frustum fit

Với aspect = viewport_width / viewport_height và vertical FOV v=45°:

```text
horizontal_fov = degrees(2 * atan(aspect * tan(radians(v)/2)))
lens.setFov(horizontal_fov, v)
```

Không còn dùng setFov(45) một tham số. Tests đọc lại cả H/V FOV, aspect và projection
của PerspectiveLens thật, không chỉ xác nhận công thức Python.

Padding p=0.13 **trên mỗi cạnh**, usable NDC magnitude k=1−2p=0.74.
Với mỗi trong tám AABB corners q, delta=q−target:

```text
x = dot(delta, right)
y = dot(delta, up)
z = dot(delta, forward)
d >= max(abs(x)/(k*tan(horizontal_fov/2)) - z,
         abs(y)/(k*tan(vertical_fov/2)) - z,
         0.1*pitch - z)
```

Lấy max trên tám corners rồi thêm epsilon tương đối 1e-12. Đây là analytical fit theo
chiều sâu của từng corner, không diagonal×magic constant. `project_point` độc lập trả
NDC XY/depth để đối chiếu. Input dimensions/pitch/góc/bounds phải hợp lệ, hữu hạn;
reject kết quả không hữu hạn, projection suy biến hoặc clipping không an toàn.

Near/far theo depth thực sau fit:

```text
near = max(0.01*pitch, 0.5*minimum_corner_depth)
far = maximum_corner_depth + max(2*pitch, 0.1*maximum_corner_depth)
```

Level 4×7 ở 1280×720: H-FOV **72.73435°**, V-FOV **45°**, near **3.80856**, far **16.29511**.
Ở 934×530: H-FOV **72.25542°**, V-FOV **45°**. Tất cả corner depths nằm giữa clipping planes.
Margin áp lên envelope bảo thủ, nên visual geometry có thể còn nhiều khoảng trống hơn 13%.

## 5. Camera API, viewport và resize

```python
camera = BoardCameraController(camera_node, perspective_lens)
camera.fit_board(board_data, viewport_width, viewport_height, pitch=1.0)
camera.set_viewport_size(934, 530)
camera.configure(CameraConfig(...))
camera.bind_window(window, viewport_size=provider, on_refit=callback)
camera.dispose()
```

`provider(window)` trả viewport dimensions do caller/layout sở hữu. Không bắt buộc là
full window. Preview hiện dùng full window vì 3.4 chưa chia DisplayRegion/HUD.
Trong 3.5, caller phải cập nhật DisplayRegion và provider tương ứng; chỉ đổi aspect mà
không đổi region sẽ làm hình ảnh không khớp pixel viewport.

Controller có một DirectObject owner riêng, mỗi event một subscription:

- `window-event`: cập nhật resize, kể cả khi aspect không đổi.
- `aspectRatioChanged`: nhận sau ShowBase điều chỉnh lens để tái xác lập viewport FOV,
  tránh full-window aspect nội bộ ghi đè thông số caller.

Không override windowEvent, không ignore handlers của ShowBase, không polling task.
Rebind gỡ chỉ subscriptions của owner cũ; dispose gọi ignoreAll trên owner riêng.
Kích thước 0/minimized được bỏ qua, giữ fit trước. Resize tái sử dụng cùng camera NodePath.
Cùng dimensions và lens đúng thì no-op; nếu ShowBase đã thay lens, controller reassert
FOV dù dimensions chưa đổi. `show_snapshot` không liên kết/refit camera.

Đã test sáu viewport: 1280×720, 934×530, 1024×720, 1920×1080, 300×1000, 1200×300.
Ma trận six shapes × six viewports kiểm tra đủ tám corners mỗi case. Engine integration
test project corners bằng lens thật. Không tạo production layout/Control Panel.

## 6. Lighting và ownership

SceneLightingController tạo một `PresentationLights` dưới SceneRoot:

| Light | RGB | Vai trò |
|---|---|---|
| AmbientLight | (0.42,0.43,0.44) | Giữ chi tiết ở mặt tối, tone lạnh nhẹ |
| Directional key | (0.55,0.55,0.54) | Shape/top/side/recess và optional shadow |
| Directional fill | (0.10,0.115,0.13) | Fill nhẹ phía đối diện |

Nguồn key theo camera basis: normalize(-0.6*right + 0.65*up − 0.9*forward), nên nằm
phía trên-trái màn hình; không đoán world-left. Fill dùng hướng opposite-right nhẹ.
Position/light lens dùng static bounds; refit theo load/resize/config, không mỗi frame.
Không đồng thời giữ PreviewAmbient/PreviewKey của 3.3.

Light states chỉ áp lên scene subtree. `dispose` clear từng light do component sở hữu,
tắt shadow caster, gỡ rig và phục hồi ShaderAttrib đã có; không clear toàn bộ lights,
không xóa foreign nodes/lights hoặc host roots. Phải gọi fit_bounds khi level bounds đổi.

## 7. Materials và bảo toàn vertex colors

SceneStyle áp hai Material trên roots đã có, không sửa mesh:

- Static: MatteComposite, specular 0.025, shininess 12.
- Block: MatteSteelBlue, specular 0.055, shininess 24.

**Ambient/diffuse của Material được để UNSET** để màu lấy từ vertex colors. Không setColor
đè cả mesh. Normals, origins, dimensions, transforms, local detail và geometry buffers
giữ nguyên. Test hash vertex data trước/sau shadow toggles; ảnh thật xác nhận floor top/side,
block steel-blue và goal navy còn phân biệt, không biến thành màu trắng/material mặc định.
Các Material/Antialias attributes trước đó được lưu và phục hồi riêng, không setState toàn
root làm mất LightAttrib của module khác. Không texture/PBR/metallness workflow bên ngoài.

## 8. Gradient background

Một quad procedural unlit dưới camera NodePath, ở sau tất cả corner depths nhưng trước far:
`background_depth = (max_scene_depth + far)/2`. Quad cover frustum theo H/V FOV, thêm 1%
overscan. Cập nhật transform khi refit; không tạo lại geometry mỗi resize.

Vertex colors: trên BG_MAIN **#F1F4F7**, dưới BG_SECONDARY **#E7EFF5**. Dùng bin background,
depth-test/write off, light/shader off, không cần camera/ShowBase thứ hai. Quad nằm trong
camera space, không phải ground plane; không lấp Void hoặc tham gia camera fit.
Shadow camera dành mask bit 29; gradient bị ẩn với mask này, không cast bóng giả.
Shadow camera còn giới hạn sceneRoot nên backdrop ngoài subtree không nằm trong shadow scene.

3D opaque geometry vẽ phía trước gradient; HUD 2D tương lai vẽ sau 3D bình thường.
Không thêm DisplayRegion/HUD production, không thay window clear behavior BG_MAIN.
Gradient đã thấy trong screenshots và test có hai vertex colors khác nhau, không ghi
PASS chỉ dựa trên solid background fallback.

## 9. Optional shadows

Default **Basic**, không cần shadow shader. `--shadows` yêu cầu enhanced:

- Kiểm tra GSG supports basic shaders + depth textures; thiếu capability giữ Basic và
  `shadow_status='UNAVAILABLE'`.
- Một key DirectionalLight shadow map **2048×2048**; scene.setShaderAuto chỉ trong enhanced.
- Orthographic shadow lens fit tám bounds corners trong light space, padding 10%, near/far
  hữu hạn theo depth. Không far cực lớn hoặc shadow camera chụp background.
- Panda DepthOffsetAttrib **-2** trên shadow camera giảm acne. Bản thử +1 đã làm toàn scene
  bị self-shadow; ảnh so sánh không-shadow/shadow xác định được nguyên nhân và đã sửa trong 3.4.
- Tắt shadows phục hồi prior ShaderAttrib và giữ Basic lights/materials/geometry.

**Visual PASS trên GPU hiện tại:** thấy bóng block trên đúng Floor, không có ground plane
ở Void, không có mảng đen phủ toàn scene, không thấy acne nghiêm trọng trong các ảnh demo.
Bóng khá sắc nhưng tiết chế, không hứa soft-shadow/PCSS. Shader auto không làm mất palette.
Code giữ tên `ENABLED_UNVERIFIED` vì bật engine flag không tự chứng minh visual PASS;
kết luận PASS ở đây là kiểm tra manual screenshots trên phần cứng cụ thể.
Driver khác vẫn cần smoke; không đảm bảo mọi GPU compile shader hoặc có cùng chất lượng.

## 10. Anti-aliasing và giới hạn framebuffer cache

Preview tạo PRC page cục bộ trước host: request multisampling + 4 samples; unload page
ngay sau tạo window. Không cấu hình lúc import, không sửa app.py. SceneStyle chỉ chọn
MMultisample khi framebuffer readback có samples >1; nếu thiếu ghi UNAVAILABLE.

Cold process trên máy này: **framebuffer readback 8 samples**, style `MSAA_8X`.
Ảnh cho cạnh mượt hơn; không coi setAntialias thành công là đủ bằng chứng. Cold process
với antialiasing=False: framebuffer **0 samples**, style DISABLED.

**Giới hạn đã quan sát:** Panda cache default FrameBufferProperties khi được đọc lần đầu.
Nếu module khác đã đọc default trước create_preview, PRC request muộn có thể không thay
framebuffer (đã thấy chosen=0 dù request AA). Ngược lại, mở foundation tiếp trong cùng
process sau AA preview có thể tái dùng cached MSAA defaults dù PRC variables đã trở lại 0.
Không tuyên bố hot-reconfigure framebuffer thành công. Dùng process mới cho so sánh
`--no-aa`/AA hoặc để caller báo UNAVAILABLE theo readback. Không sửa host để che giới hạn.

Foundation CLI riêng vẫn nguyên: fresh process tạo framebuffer 0 samples, bốn roots rỗng,
nền BG_MAIN và import safety như cũ. Không có cấu hình PRC mới nào chạy khi import preview.

## 11. Wiring, API compatibility và cleanup

Public pair vẫn là `(app, renderer)`:

```python
app, renderer = create_preview(pose=BasicOrientation.STANDING,
                               shadows=False, antialiasing=True)
try:
    app.run()
finally:
    dispose_presentation(app)
    renderer.dispose()
    app.destroy()
```

`app.presentation` chứa camera/lighting/style. Trình tự setup: host → Renderer/data → Camera
→ Style/Lighting → bind events → main loop. Cleanup chính: Camera/listener, Lighting,
Style/background → Renderer → Host. Partial setup failure gỡ những component đã tạo.
Finally lồng bảo đảm renderer/host vẫn được cleanup nếu vòng lặp/presentation cleanup lỗi.

Đăng ký callback idempotent vào **ShowBase.finalExitCallbacks API có sẵn** để callers cũ
`renderer.dispose(); app.destroy()` không bỏ sót listeners/background. Không monkeypatch
destroy, không tạo host subclass mới hoặc sửa app.py. Callback tự gỡ khỏi danh sách khi
dispose; đã thử legacy path và xác nhận không còn window-event/aspect subscriptions.
Trong legacy path host override tháo SceneRoot trước callback của ShowBase; cleanup xử lý
root đã detach và vẫn release lights/background/listener. Main path giữ thứ tự chuẩn ở trên.

Lệnh cũ và options mới:

```bash
.venv/bin/python -B -m src.gui.board_preview
.venv/bin/python -B -m src.gui.board_preview --pose HORIZONTAL
.venv/bin/python -B -m src.gui.board_preview --pose VERTICAL
.venv/bin/python -B -m src.gui.board_preview --level levels/level_01.json
.venv/bin/python -B -m src.gui.board_preview --shadows
.venv/bin/python -B -m src.gui.board_preview --no-aa
.venv/bin/python -B -m src.gui.app
```

Không tạo buttons/settings menu, gameplay, session manager, solver hoặc animation.

## 12. Unit tests và kết quả regression

26 tests mới: **12 camera (8 pure + 4 Panda integration)** và **14 presentation**.
Camera phủ angles/basis, FOV, 36 shape/viewport combinations, margin/clipping, determinism,
pitch/errors, readback/project bằng lens thật, zero resize, node identity, listener cleanup,
viewport-provider và camera không refit khi Renderer.show_snapshot.

Presentation phủ light types/subtree/source, repeated fit/toggles, foreign state/node ownership,
capability fallback, shader restoration, vertex-buffer hash preservation, shadow lens corners,
Material unset ambient/diffuse, gradient masks/depth/colors, AA readback states, import safety,
cleanup ordering và setup-failure cleanup. Mocks chỉ tạo failure/capability scenarios;
không dùng mocks để tuyên bố visual GPU/shadow PASS.

Lệnh thực tế:

```bash
.venv/bin/python -B -m unittest discover -s tests -p test_gui_camera.py -v
.venv/bin/python -B -m unittest discover -s tests -p test_gui_lighting.py -v
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

| Sau triển khai | Ran | PASS | FAIL | ERROR | SKIP | Thời gian unittest |
|---|---:|---:|---:|---:|---:|---:|
| Camera mới | 12 | 12 | 0 | 0 | 0 | 0.168s |
| Lighting/style mới | 14 | 14 | 0 | 0 | 0 | 0.101s |
| Full venv, lần tái hiện lỗi cuối | 196 | 194 | 2 | 0 | 0 | 0.807s |
| Full system Python | 196 | 143 | 0 | 0 | 53 | 0.447s |

System skip 35 tests engine cũ + 4 camera integration + 14 presentation do không có Panda3D;
8 camera math tests mới vẫn chạy. Không lấy system PASS/SKIP để thay cho full venv regression.
Lần suite 195 tests trước bổ sung setup-failure case từng PASS; không dùng kết quả đó để
giấu lỗi lifetime được phát hiện sau. Old renderer suite chạy riêng 33/33 PASS nhưng không
giải quyết tính phụ thuộc memory allocation của helper.

## 13. Lỗi helper test 3.3 cần nhiệm vụ sửa riêng

Nguồn: [test_gui_renderer.py](../../tests/test_gui_renderer.py), **dòng 28–29**:

```python
vertices.append(position.getData3f())
normals.append(normal.getData3f())
```

Trên runtime Panda3D này, các vectors trả về còn tham chiếu vertex buffer. Một số tests
gọi `mesh_data(make_goal_mesh())` bằng node tạm, rồi dùng vectors sau khi node/data đã bị
giải phóng. Memory reuse làm normals thành 0/rác và triangle positions/area sai.
Hai failures quan sát: T22 normal length 0 thay vì 1; T23 aperture top area không còn 0.344.
Đây là lỗi đọc dữ liệu trong test helper, không phải bằng chứng goal mesh bị đổi bởi 3.4.

Đã tái hiện trong process chỉ import mesh_factory + helper 3.3, xác nhận không import
scene_style/scene_lighting. Giữ node: values bình thường; xóa node, gc.collect và tạo 100
Floor meshes: **56/56 borrowed positions thay đổi**, trong khi Vec3 copies vẫn giữ nguyên.

Đề xuất sửa, **chưa áp dụng vì tests cũ bị cấm sửa trong prompt 3.4**:

```python
# Import Vec3 từ panda3d.core rồi copy ngay khi đọc:
vertices.append(Vec3(position.getData3f()))
normals.append(Vec3(normal.getData3f()))
```

Hoặc giữ mesh/data owner sống suốt assertions. Không patch helper lúc chạy tests, không
giữ mesh toàn cục để che lỗi, không xóa setup-failure test mới hoặc rerun đến khi xanh rồi
gọi complete. Cần người dùng giao phạm vi sửa test 3.3 riêng và chạy full regression lại.

## 14. Onscreen visual smoke và screenshot evidence

Runtime: Ubuntu/X11, CPython 3.14.4, Panda3D 1.10.16; **GraphicsWindow onscreen** qua GLX.
GPU: **AMD Radeon Graphics (radeonsi, renoir, ACO, DRM 3.64, 7.0.0-38-generic)**.
Không dùng offscreen/AI image thay desktop evidence. PNG chụp framebuffer của window thật.

Harness tạm `/tmp/bloxorz-stage3-4-smoke.py` thực thi create_preview, cập nhật DTO fixtures,
window properties, xử lý event frames và kiểm tra lens.project cho tám corners ở mỗi case.
Không thêm production level file hoặc mutate Core. Log JSON: `/tmp/bloxorz-stage3-4-runtime.json`.
Đã mở xem ảnh poses, wide/tall/square, narrow resize và enhanced; các case còn lại có
projection/nonblank framebuffer checks. Không thấy clipping/backface/Z-fighting đáng kể
trong các góc đã kiểm tra, goal vẫn có recess, Void trống và palette giữ được.

| PNG dưới `/tmp/bloxorz-stage3-4-` | Case | Window thực tế | Trạng thái |
|---|---|---|---|
| `standing.png` | Level thật 4×7 STANDING | 1280×720 | PASS |
| `horizontal.png` | Level thật HORIZONTAL | 1280×720 | PASS |
| `vertical.png` | Level thật VERTICAL | 1280×720 | PASS |
| `wide.png` | DTO in-memory 3×15 | 1280×720 | PASS |
| `tall.png` | DTO in-memory 15×3 | 1280×720 | PASS |
| `square.png` | DTO in-memory 10×10 | 1280×720 | PASS |
| `resize-1024x720.png` | Resize + lens/projection check | 1024×720 | PASS |
| `resize-934x530.png` | Reference viewport size | 934×530 | PASS |
| `resize-640x900.png` | Hẹp/cao, real resize | 640×900 | PASS |
| `resize-1280x720.png` | Restore window size | 1280×720 | PASS |
| `basic.png` | Basic lighting | 1280×720 | PASS |
| `enhanced.png` | Shadow map thật, bóng block thấy rõ | 1280×720 | PASS trên GPU này |
| `foundation.png` | Host cũ, bốn roots rỗng | 1280×720 | PASS |

CLI `python -m src.gui.board_preview --shadows` cũng được mở thực tế, đóng bằng window-manager
close tới đúng observed window ID; process exit 0. Sau harness dispose/destroy, GraphicsEngine
có 0 windows (gồm shadow buffers). Legacy caller cleanup cũng PASS.
Ảnh/harness/log ở `/tmp`, không phải assets Git và có thể bị dọn.

## 15. Performance observations

Level thật 4×7 STANDING, 1280×720, framebuffer 8 samples, cùng camera/geometry/desktop;
80 frames warm-up mỗi profile rồi đo 240 taskMgr.step frames và syncFrame.
Request sync-video=false trong harness riêng; desktop/compositor hoặc pipeline vẫn có thể
giới hạn nhịp. Đây là wall-clock frame throughput, không phải GPU timing/benchmark độc quyền.

| Profile | Frames | Thời gian | Mean frame | Mean FPS |
|---|---:|---:|---:|---:|
| Basic | 240 | 3.99681s | 16.653ms | 60.05 |
| Enhanced shadow 2048² | 240 | 4.87044s | 20.293ms | 49.28 |

Enhanced chậm hơn trong phép đo này; Basic tiếp tục là default, enhanced chỉ bật bằng flag.
Không đặt KPI máy khác hoặc suy FPS này sang Windows, board lớn, HUD/animation tương lai.

## 16. Known limitations, coordination và 3.5

- Full venv regression còn hai failures từ helper test 3.3; không đổi ownership để tự sửa.
- AA request tốt nhất trong cold process vì cached framebuffer defaults; không hot-reconfigure.
- Shadows/AA visual chỉ verified trên GPU hiện tại. Driver không hỗ trợ shaders/depth textures
  giữ Basic; chưa có cam kết soft shadows hoặc mọi shader driver đều chạy.
- Camera fit envelope bảo thủ tính cả void/full grid và headroom; chưa optimize sparse bounds.
- Camera viewport-provider sẵn có, nhưng chưa DisplayRegion/layout/HUD; 3.5 caller phải wire
  region pixels và resize provider cùng nhau. Không coi 3.4 là đã dựng control panel.
- Chưa gameplay, Controller, solver, replay, animation/rolling, Advanced hoặc >=10 levels.
- Windows NOT TESTED; không sửa shared dependencies để tuyên bố cross-platform.

Phong: cần schema/envelope/events khi Advanced hoặc bridge/teleport vượt Basic bounds.
Tài: cần owner cho viewport-provider/load-level/refit/dispose, session/revision và main-thread
wiring. Không đổi game-state semantics để fit camera; không gửi tin nhắn cho thành viên.

Trước 3.5: review code/ảnh 3.4; giao riêng sửa helper test được bảo vệ, chạy full suite sạch;
sau đó mới cấp phạm vi layout/HUD và cơ chế viewport-provider. Không tự triển khai 3.5.

## 17. Git scope, quality gates và acceptance

Manifest trước/sau: **51/52 files có sẵn giữ nguyên**, ngoại lệ duy nhất là
`src/gui/board_preview.py` được cho phép sửa wiring. Sáu files mới thuộc camera/lighting/style,
hai tests và báo cáo. `renderer.py` vẫn xuất hiện M trong Git status vì thay đổi 3.3 có sẵn,
nhưng SHA-256 giữ nguyên trong toàn lượt 3.4. Tất cả tests/báo cáo cũ giữ nguyên.
Branch, HEAD và staging không đổi; không add/commit/push/merge/fetch/branch operation.

| Quality gate | Trạng thái | Bằng chứng |
|---|---|---|
| A — Camera math | PASS | Angles/FOV/36 combinations/clipping/margin tests |
| B — Camera integration | PASS | Lens readback, real resize, viewport-provider, same camera |
| C — Lighting/visual | PASS trên runtime này | Basic/enhanced/gradient/materials, AA readback + ảnh |
| D — Runtime/handoff | PARTIAL | Onscreen/cleanup/scope PASS; full regression FAIL do helper 3.3 |

| # | Acceptance | Trạng thái | Evidence |
|---:|---|---|---|
| 1 | Audit/bảo toàn thay đổi có sẵn | PASS | Git/manifest/source baseline |
| 2 | Perspective camera | PASS | PerspectiveLens + real projection |
| 3 | Elevation/azimuth | PASS | Unit-vector angle tests |
| 4 | Vertical FOV chính xác | PASS | 45° lens readback |
| 5 | Auto-fit nhiều board sizes | PASS | Math matrix + wide/tall/square onscreen |
| 6 | Viewport aspect | PASS | Sáu viewport sizes, caller provider |
| 7 | Resize | PASS | Event ownership tests + actual window resizes |
| 8 | Không nhảy theo snapshot | PASS | Camera transform unchanged in show_snapshot test |
| 9 | Clipping | PASS | Corner depth/near/far checks |
| 10 | Basic lighting | PASS | Real image + state tests |
| 11 | Matte palette presentation | PASS | Material states + screenshots |
| 12 | Vertex colors giữ nguyên | PASS | Buffer hash + unset ambient/diffuse + ảnh |
| 13 | Background | PASS | Gradient geometry/colors/depth + ảnh |
| 14 | Optional shadow/fallback | PASS trên GPU này | Visible shadow + capability failure test |
| 15 | Antialiasing kiểm tra | PASS có giới hạn | Cold-process 8 samples / disabled 0; cache limitation mục 10 |
| 16 | Reuse Renderer 3.3 | PASS | Same API/source hash |
| 17 | Foundation giữ nguyên | PASS | Source hash, import tests, fresh onscreen |
| 18 | Contracts/Adapter giữ nguyên | PASS | Manifest + old tests |
| 19 | Geometry/Renderer giữ nguyên | PASS | Manifest, không sửa tests cũ |
| 20 | Một ShowBase | PASS | Existing host only, import/window checks |
| 21 | Unit tests thực thi | PASS | 26 tests mới PASS |
| 22 | Full regression thực thi | FAIL về kết quả | 194 PASS + 2 FAIL venv; nguyên nhân mục 13 |
| 23 | Desktop screenshots | PASS | PNG/log thực tế |
| 24 | Cleanup | PASS | Main order, partial setup, legacy callback, 0 windows |
| 25 | Không sửa Core/Controller/Solver | PASS | Manifest |
| 26 | Không HUD/Animation/Replay | PASS | Scope/source review |
| 27 | Không commit/push/merge | PASS | HEAD/branch/staging giữ nguyên |
| 28 | Docs/diff report | PASS | Tài liệu và manifest |

**Dừng để người dùng review; không đánh dấu COMPLETE khi full regression còn lỗi.**
