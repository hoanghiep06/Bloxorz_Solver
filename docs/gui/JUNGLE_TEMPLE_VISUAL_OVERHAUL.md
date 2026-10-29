# Premium Visual Overhaul V2 — Jungle Temple / Magma Meteorite

**FINAL STATUS: VISUAL OVERHAUL COMPLETE**

Ngày kiểm tra: 27/10/2026; đã hoàn thiện bổ sung nền đá/dây leo, cờ động và chất lượng đồ họa trong Settings. Điểm xuất phát: `f602351` trên `feat/team-code/phase2-game-gui`. Đây là nâng cấp renderer chạy thật trong Panda3D; không dùng ảnh concept làm bàn chơi hoặc làm bằng chứng thực thi. Không commit, push, merge, checkout, reset hoặc clean.

## 1. Định hướng và đối chiếu reference

| Thành phần | Mục tiêu reference | Triển khai thực tế |
| --- | --- | --- |
| Bố cục | Board isometric nổi giữa thung lũng | Giữ góc Iso; fit theo tất cả ô có thể có sàn/cầu, bỏ khoảng void ngoài cùng. Giữ headroom 2,3 ô, bổ sung bounds xuống −0,8 ô cho chân nền/dây leo, padding và near/far theo camera hiện có. |
| Khối | Thiên thạch đen, khe magma cam/vàng | Cuboid bevel 1×1×2, texture đá, mạng nứt Voronoi bất đối xứng, emission mask, height detail và bloom nhẹ. Split dùng cùng vật liệu trên cube 1×1×1. |
| Sàn | Đá cổ có seams, rêu, chiều dày | UV stone texture, vân nứt, variation theo tọa độ, bevel/thickness thật; chân đá vát dày dưới ô sàn ở biên, dây leo/lá ở light và icicle ở dark; batch thành bốn Geom cho cả hai theme. |
| Fragile | Đá cam nứt nóng | Texture đá nứt + emission, giữ glyph nứt lớn; broken chỉ còn mảnh nhỏ dưới mặt đỡ. Sáu mảnh animation cũng có texture. |
| Switch | Nhìn được bằng hình dáng | Soft là vòng cyan; Heavy là đế vuông với hai thanh; Split là hai phần tách. Active dùng palette riêng. Vòng/thanh/glyph dùng vật liệu emissive giữ đúng màu cyan/trắng. |
| Cầu | Gia cường kim loại | Bề dày thật, texture metal/stone, ba ribs. Đóng là không có mesh sàn đỡ, animation dịch chuyển giữ scale. |
| Goal | Hố sâu + cờ cam rõ | Aperture và đáy hố giữ hình học cũ; viền cam, lòng tối; cờ cam chia 12 dải, cột vàng và glyph tam giác; cloth/glyph gợn nhẹ bằng shader, cột đứng yên. |
| Cảnh nền | Rừng, thác, sương, đền xa | Panorama AI mới chỉ chứa môi trường; board/block/switch/flag là mesh riêng, vẫn xoay, di chuyển, ẩn/hiện theo game. Có panorama tuyết đêm riêng. |
| HUD | Kính tối, tương phản tốt, vàng/cam | Rounded outline thật có phần giữa rỗng, fill trong suốt, viền vàng cho AI Solver, nhãn Exit/Restart/AI Solver, icon metrics, separator và bảng tên màn. |

Đây không phải pixel-perfect. Reference có mức độ tạo hình/ánh sáng của ảnh cinematic; bản chạy hiện tại ưu tiên footprint chính xác, độ đọc gameplay và chi phí renderer có thể kiểm soát.

## 2. Kiến trúc visual

Luồng dữ liệu vẫn là **Core → adapter → DTO → renderer/animation**. Không đưa texture, shader, effect hoặc cờ vào Core state. Không thay schema level, API solver, số bước hoặc cách đo metrics.

- `visual_materials.py`: đọc PNG cục bộ, cache texture/state có giới hạn, chuẩn bị shader trên GSG thật. Mỗi Geom giữ Texture/Shader RenderState, do đó `_combine()` phải bảo toàn state khi ghép mesh.
- `mesh_factory.py`: thêm UV vào vertex format. Phép chiếu UV được bake trong tọa độ **local của mesh**, không lấy từ vị trí world hoặc thời gian. Khối mặc định và khối theo theme cùng dùng magma.
- `temple_environment.py`: variation deterministic theo `(row, col)` (texture matrix được áp dụng cả trong GLSL lẫn fallback), trang trí mép nằm dưới mặt đỡ; tính bounds cho composition. Không tạo floor/collision cho void.
- `AdvancedSceneRenderer`: giữ prototype cho hai theme; floor cũng có theme holder. Khi đồng bộ commit `b93127a`, cờ dùng bản sao trong animated surface lúc renderer surface bị lease; chỉ một bản hiện tại một thời điểm.
- `AnimatedActorRig`: tái sử dụng các mesh magma qua toàn bộ roll; chỉ đổi transform, quaternion, opacity và scale. Không tạo lại texture mỗi frame.
- `AnimatedSurfaceLayer`: dùng cùng factories/materials cho cầu, switch, fragile và fragments; theme được đồng bộ qua API cũ.
- `CinematicBloom`: thuộc `DashboardPresentation`, chỉ xử lý 3D viewport trước HUD. Cleanup chạy trước khi viewport trả region/camera cho host.
- `visual_quality.py`: chính sách Auto/High/Balanced/Low thuần Python. Settings áp dụng ngay và lưu trong profile; JSON cũ vẫn dùng được. Uniform dùng PTA chia sẻ để đổi chi tiết mà không rebuild mesh/actor.
- `TempleAtmosphere`: một task thuộc `AdvancedPreviewPresentation`, cập nhật thời gian cloth. Restart/đổi level không tạo thêm task; dispose gỡ task. Chỉ cloth/glyph có motion uniform khác zero; pole và actor không biến dạng.
- Chân đá/dây leo chỉ ở ô FLOOR cố định có cạnh giáp void, bỏ qua goal/bridge/fragile; toàn bộ dưới z=0, nằm trong footprint ô. `LevelIntro` ẩn batch đến khi các slab đáp xuống; không để chân nền lơ lửng trong intro.

### Vật liệu khối

Texture RGBA 512×512 chứa RGB albedo và **alpha làm emission mask**. `magma-height.png` chứa height detail. Mạng nứt được tạo từ chênh lệch khoảng cách đến hai seed Voronoi gần nhất, biến dạng bằng trường sóng; đá dùng noise nhiều tần số. Không dùng các ellipse hoặc vài đường cam để thay thế vật liệu khối.

Stone dùng albedo AI; relief nhỏ của stone lấy gradient cường độ albedo, không dùng displacement. Các bản `stone-light/dark` procedural được giữ trong bộ asset authoring.

GLSL 1.20 đọc albedo/mask, ước lượng perturbation normal từ gradient height, tính ánh sáng hướng ấm/lạnh và cộng thermal emission. Mẫu texture, bevel và origin giữ nguyên sau mỗi lần lăn. Cuboid không bị đẩy vertex theo height map, vì vậy không thay envelope/pivot hoặc xuyên sàn.

Đây là shader ánh sáng gọn, **không phải PBR đầy đủ**. Height detail không phải displacement; không có tessellation. Vết nứt không phát một point light động lên các ô xung quanh.

### Bloom và fallback

Bloom dùng GLSL 1.30, một buffer scene và một buffer glow nửa kích thước. Pass trích vùng nóng ưu tiên cam/đỏ, blur nhỏ, composite cường độ 0,22. `textureSize()` xử lý đúng framebuffer texture bị padding lên power-of-two; resize cập nhật kích thước scene và bán kính lấy mẫu. HUD không bị bloom.

Shader được compile/prepare trước khi gắn vào renderer. Lỗi có log và fallback; nếu bloom không khả dụng, material emission vẫn chạy. Khi material shader không khả dụng, fallback dùng RGB texture có khe nứt sáng được bake sẵn. Emission alpha được loại khỏi texture fallback để tránh làm thủng bề mặt khi actor fade.

```bash
# Ép chất lượng đẹp nhất (Auto mặc định giảm xuống Balanced trên software renderer)
BLOXORZ_QUALITY=high .venv/bin/python -B main.py

# Giữ shader vật liệu, tắt riêng bloom
BLOXORZ_BLOOM=0 .venv/bin/python -B main.py

# Fallback texture không dùng shader, không bloom
BLOXORZ_MATERIALS=fixed .venv/bin/python -B main.py
```

Chất lượng mặc định **High**; Settings không còn hàng Graphics quality. Các mức sau chỉ còn dùng cho kiểm thử/chẩn đoán bằng biến môi trường `BLOXORZ_QUALITY`:

| Mức | Detail normal | Bloom |
| --- | --- | --- |
| Auto | High trên GPU; Balanced nếu nhận diện llvmpipe/softpipe/SwiftShader/software | Theo mức hiệu dụng |
| High | Đầy đủ; thêm halo material | Có nếu backend hỗ trợ |
| Balanced | Giảm biên độ normal; bỏ halo | Tắt |
| Low | Bỏ gradient normal và halo; giữ albedo/emission | Tắt |

File lưu cũ có mức Auto/Balanced/Low được đưa về High, giữ nguyên các thiết lập còn lại và tiến độ. `BLOXORZ_QUALITY` chỉ override khi khởi động để chẩn đoán; giá trị env không hợp lệ dùng mặc định High. Các mức này không đổi resolution, luật, animation duration hoặc metrics. Fallback material vẫn được dùng nếu shader không khả dụng.

Ánh sáng cố định của material bổ sung cho rig key/fill hiện có và contact shadow được clip vào ô có sàn. Shadow map tùy chọn của rig cũ không được quảng bá là PBR shadow receiver cho shader mới.

## 3. Bảo toàn chức năng và lifecycle

Không sửa `src/core/`, `src/solvers/`, `src/gui/controller.py`, `animation_math.py`, `animation_manager.py` hoặc timeline. Controller vẫn tăng Moves theo action hoàn tất, solver/replay vẫn dùng kết quả thật.

- Origin mesh và envelope 1×1×2 / 1×1×1 giữ nguyên.
- Floor top `z=0`, bottom `z=-0.18`, rộng `0.96`; goal aperture không đổi.
- Bridge tắt không được thay bằng floor. Broken fragile không có platform đầy đủ.
- Cờ vẫn ẩn theo snapshot khi block chiếm goal; khi layer cầu/switch bị lease, animated surface tiếp quản cờ để không biến mất hoặc vẽ trùng.
- Geometry/UV/texture không bị sửa bởi Pause, Step, cancel hoặc roll.
- Theme holders và fragments được tái dùng. Có một task cosmetic chung cho cờ; Pause/Step của actor không bị thay đổi. Cờ tiếp tục gợn nhẹ khi actor đang Pause, không tăng Moves hoặc sửa snapshot.
- Bloom sở hữu hai outputs và một subscription resize; dispose trả camera và xoá outputs/subscription. GUI controls giữ callback/state thật.
- 1024×720: tên màn được rút gọn nhưng giữ hậu tố số màn `(…/…)`.

## 4. Regression và kiểm thử native

Baseline trên `f602351`: **471 test, 10 error** vì fixture cũ đã bị xóa khỏi `levels/`. Đã lưu nguyên các JSON cơ chế từ `2f19245` vào `tests/fixtures/mechanics/`, sửa tham chiếu test và cho smoke tools nhận `--levels`. Không khôi phục các màn cũ vào catalog sản phẩm. Test dự báo vẫn duyệt cả fixtures và 18 level hiện hành.

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ unittest cuối cùng | **489/489 PASS** |
| Native keyboard/mouse, hai theme, Iso/Top/Follow, hai cube, tốc độ 0,25×/1×/4×, resize, Pause/Step, cancel | **33 nhóm PASS** |
| Sáu solver × 11 fixture cơ chế, replay theo clock thật | **66/66 PASS**, gồm DFS sandbox 528 bước |
| Sáu solver × 18 màn hiện hành | **108/108 PASS**; worker/metrics thật, timeline tăng tốc có xác định, chụp framebuffer mẫu |
| Game/dashboard 1280×720 và 1024×720; split/Space thật | PASS |
| Fallback fixed-function, cả hai theme và resize | PASS |
| Shader không được GPU hỗ trợ hoặc compile lỗi | Unit tests xác nhận log + fallback |
| 10 roll nối tiếp | UV, vertex data, texture/state identity giữ nguyên |
| 30/60/120 FPS × các playback rate | Test cơ học/timeline hiện có tiếp tục PASS |
| Restart/cancel khi fragile/fall/split/goal đang chạy | Native PASS, không còn actor/terminal/result cũ |
| 10 Restart liên tiếp | Số node/task/widget/output không tăng |
| 20 lần click chất lượng bằng XTest | State/session/Moves giữ nguyên; JSON đúng; node/task/widget/output không tăng |
| Đóng/mở game với preference Balanced đã lưu | PASS; không reset về Auto |
| Nền đá/dây leo mới | Test mọi vertex dưới mặt sàn, chỉ nằm trong footprint FLOOR, không dưới goal/void/bridge/fragile |
| Cờ động | Native frames + test mesh chia dải, giới hạn footprint, pole riêng và task cleanup |
| Sau dispose | 0 task, 0 widget, 0 subscription, 0 graphics output |

`tools.jungle_solver_smoke` tăng tốc **timeline trong QA**, không giả kết quả solver và không thay game code. Kiểm tra replay theo thời gian thật được tách riêng trong `tools.game_integration_smoke`.

### Lệnh tái kiểm tra

```bash
.venv/bin/python -B -m unittest discover -s tests

xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.move_assist_smoke --levels tests/fixtures/mechanics

xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.game_integration_smoke --all --levels tests/fixtures/mechanics

xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.jungle_solver_smoke

xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  env BLOXORZ_QUALITY=high .venv/bin/python -B -m tools.jungle_visual_capture --output /tmp/jungle-visual

xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.jungle_quality_smoke --output /tmp/jungle-quality

BLOXORZ_QUALITY=high xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.jungle_motion_capture --output /tmp/jungle-motion
```

Xvfb/XTest chỉ là công cụ QA Linux, không phải dependency chạy game.

## 5. Ảnh và clip chạy thật

Ảnh trước lấy từ bản `f602351` được đọc bằng `git archive` vào thư mục QA riêng, không checkout/reset workspace. Cùng level, cửa sổ và góc Iso; bản mới có fit bỏ void ngoài cùng nên tỷ lệ board được cải thiện có chủ đích. Các ảnh close-up cố ý zoom vào vật liệu; không dùng chúng thay cho kiểm tra toàn màn hình.

| Bằng chứng | File |
| --- | --- |
| Màn cơ bản trước / sau | [Trước](evidence/jungle-temple/game-before.png) · [Sau](evidence/jungle-temple/game-comparable.png) |
| Sandbox trước / sau | [Trước](evidence/jungle-temple/sandbox-before.png) · [Jungle dashboard](evidence/jungle-temple/dashboard-light-1280.png) |
| Hai theme ở 1024×720 | [Light](evidence/jungle-temple/dashboard-light-1024.png) · [Dark](evidence/jungle-temple/dashboard-dark-1024.png) |
| Dark 1280×720 | [Winter dashboard](evidence/jungle-temple/dashboard-dark-1280.png) |
| Nhiều mặt magma | [45°](evidence/jungle-temple/magma-face-45.png) · [135°](evidence/jungle-temple/magma-face-135.png) · [225°](evidence/jungle-temple/magma-face-225.png) |
| Roll 0 / 50 / 100% | [0](evidence/jungle-temple/demo-basic-roll-000.png) · [50](evidence/jungle-temple/demo-basic-roll-050.png) · [100](evidence/jungle-temple/demo-basic-roll-100.png) |
| Controls solver thật, có Play/Step/speed | [BFS được chọn](evidence/jungle-temple/solver-controls.png) |
| Split trong game thật | [Hai cube](evidence/jungle-temple/advanced-split.png) |
| Các ô đặc biệt | [Fragile](evidence/jungle-temple/demo-fragile-050.png) · [Switches](evidence/jungle-temple/demo-switches-100.png) · [Bridge](evidence/jungle-temple/demo-bridge-050.png) · [Goal](evidence/jungle-temple/demo-goal-050.png) |
| Settings chất lượng, cửa sổ nhỏ | [1024×720](evidence/jungle-temple/settings-1024.png) |
| Cờ shader, snapshot không đổi | [Cận cảnh](evidence/jungle-temple/goal-flag-closeup.png) · [Clip](evidence/jungle-temple/flag.gif) |
| Clip native frames | [Roll](evidence/jungle-temple/basic-roll.gif) · [Fragile](evidence/jungle-temple/fragile.gif) · [Goal](evidence/jungle-temple/goal.gif) · [Split](evidence/jungle-temple/split.gif) · [Merge](evidence/jungle-temple/merge.gif) |

Các clip roll/fragile/goal/split/merge mới dùng 21 framebuffer cho từng action; clip cờ dùng 25 frame với clock thật, kiểm tra snapshot không đổi. Chênh lệch pixel của clip cờ chỉ nằm tại vùng cloth/glyph; pole đứng yên.

Ảnh/clip `demo-*` dùng explicit animation DTO và hiển thị `NOT GAMEPLAY`. Chúng kiểm tra renderer/timeline, không được trình bày như một lời giải Core. Ảnh `dashboard-*`, `advanced-split` và `game-comparable` lấy từ ứng dụng game thật. GIF chỉ encode các frame chụp trực tiếp; không thêm block, texture hoặc hiệu ứng bằng công cụ tạo ảnh.

## 6. FPS và tài nguyên

Số đo là thời gian `renderFrame + syncFrame` trên **llvmpipe (software renderer, Xvfb)**, không phải benchmark GPU người dùng. Có các tiến trình QA khác chạy cùng thời điểm. Không suy ra 60 FPS hoặc khả năng trên mọi GPU từ các số này.

Capture sandbox High: median **60.62 ms/frame (~16,5 FPS render)**. Lần đo lại trên cùng level cơ bản 1280×720, sau khi các QA nặng đã kết thúc: High **38,75 ms (~25,8 FPS)**; Balanced **22,56 ms (~44,3 FPS)**; Low **20,23 ms (~49,4 FPS)**. Chi tiết ở `quality-report.json`. Đây là level nhỏ, không so trực tiếp với sandbox ở trên. Lần fallback mới ở sandbox: **19,12 ms (~52,3 FPS render)**, texture cố định, 1 output, cleanup sạch. Profile Low/Balance giảm texture samples và bỏ hai buffer bloom. Không phải số đo input-to-present hoặc cam kết hiệu năng trên GPU thật.

Số đo chi tiết nằm trong `evidence/jungle-temple/visual-report.json` và `fallback-report.json`. Native report ghi cả resource trước/sau 10 Restart và trạng thái `GLSL_DETAIL_EMISSION` / `FIXED_FUNCTION`, `ENABLED` / `DISABLED_QUALITY` / `UNAVAILABLE` của bloom.

High dùng 3 graphics outputs tổng cộng (cửa sổ + 2 buffer); Balanced/Low/fallback dùng 1. Sau 20 click chất lượng: 192 scene nodes, 14 task (tính cả delayed), 141 widget và 1 output ở Auto Balanced trước/sau đều bằng nhau. Sandbox High qua 10 Restart: 781 nodes, 14 task, 99 widget, 3 outputs giữ nguyên. Dispose còn 0 task/widget/output/subscription. Có thể chọn Low trong Settings hoặc dùng fallback bằng biến môi trường ở mục 2. Chưa benchmark GPU rời, tích hợp Intel/AMD hoặc backend ngoài OpenGL.

## 7. Asset, nguồn và phạm vi chưa tái tạo như reference

Nguồn và **nguyên văn prompt**: [assets/VISUAL_ATTRIBUTION.md](../../assets/VISUAL_ATTRIBUTION.md). Hai panorama và albedo đá `temple-stone.png` được sinh bằng built-in ImageGen; magma, mask/height, texture cơ chế và shader được tự tạo bằng mã. Albedo đá được chiếu UV lên từng slab, không thay thế mesh board. Không thêm thư viện runtime. Numpy/Pillow chỉ được dùng bởi công cụ authoring để tái sinh PNG đã lưu sẵn.

```bash
# Authoring, không cần cho người chơi
python3 tools/build_visual_materials.py
```

Khác biệt còn lại:

1. Rừng, thác, đền và sương xa nằm trong panorama, chưa là mô hình 3D có parallax/đổ bóng/animation nước. Board, khối và cơ chế là 3D thật.
2. Đá và rêu dùng albedo đá có chi tiết khoáng/nứt + bevel + chi tiết mép gọn; chưa có sculpt high-poly, photogrammetry, PBR/SSAO hoặc volumetric lighting như hình cinematic.
3. Bloom nhẹ theo màu nóng, không mô phỏng tán xạ vật lý hoặc ánh sáng GI từ magma. Contact shadow hiện có được giữ; không tuyên bố shadow map PBR trên material tùy biến.
4. Cờ dùng deformation shader xác định theo thời gian, không có mô phỏng vải vật lý. Fallback giữ silhouette cong tĩnh; cột và footprint gameplay không đổi.
5. Số đo FPS hiện tại chỉ có software OpenGL. Có bốn mức trong Settings và Auto hạ chất lượng trên software renderer; chưa có bằng chứng hiệu năng GPU thật.

Vấn đề tài liệu có sẵn ngoài phạm vi: lệnh `benchmark.py` cũ trong README vẫn cần một tác vụ riêng; bản nâng cấp này không thêm benchmark hoặc thay thuật toán.

## 8. Chạy và xem màn đủ cơ chế

```bash
.venv/bin/python -B main.py
```

Vào **Settings → Appearance → Light**; chất lượng High đã được chọn mặc định, sau đó **Start → chọn level**. AI Solver mở hàng BFS/DFS/IDS/UCS/Greedy/A*. Có thể đổi theme trong Settings, camera bằng C, đổi cube bằng Space. Các nút và metrics vẫn dùng pipeline thật.

Để xem chính sandbox đầy đủ trong ảnh kiểm chứng, dùng **catalog fixture** rồi chọn màn 11:

```bash
.venv/bin/python -B main.py --levels tests/fixtures/mechanics --save /tmp/bloxorz-visual-review.json
```

Đây không phải `levels/level_11.json` của catalog 18 màn mới. Profile `/tmp` giúp xem thử mà không đổi save đang chơi.

## 9. Files và Git inventory

Các file nguồn sửa: `mesh_factory.py`, `advanced_mesh_factory.py`, `advanced_renderer.py`, `animation_effects.py`, `app.py`, `game_app.py`, `camera_views.py`, `dashboard_preview.py`, `scene_style.py`, `hud.py`, `icons.py`, `ui_theme.py`, `advanced_preview.py`, `level_intro.py`, `profile.py`, `screens.py`.

Các module mới: `visual_materials.py`, `cinematic_bloom.py`, `temple_environment.py`, `visual_quality.py`. Shader/texture/panorama mới ở `assets/`; công cụ build/capture/catalog QA mới ở `tools/`. Tests mới ở `tests/test_visual_overhaul.py`; test HUD và các tham chiếu fixture được cập nhật.

`Core`, `Controller`, `Solver`, level sản phẩm, requirements và luật game không có diff. Patch cho các file đã track: [tracked-changes.patch](evidence/jungle-temple/tracked-changes.patch); file mới được ghi riêng trong inventory. Inventory đầy đủ, diff stat và tên các file untracked được lưu ở [git-inventory.txt](evidence/jungle-temple/git-inventory.txt). Các file mới vẫn là untracked cho đến khi chủ repo quyết định commit. Thư mục evidence chứa PNG/GIF native nên có kích thước khoảng 48 MB; đây là bằng chứng QA, không được runtime load.
