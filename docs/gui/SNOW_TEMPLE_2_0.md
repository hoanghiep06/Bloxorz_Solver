# Snow Temple 2.0 — Snow-covered Ancient Temple Stone

## 1. Phạm vi và root cause

Bản Frosted Ancient Stone trước đây có màu đá xám ấm, normal/roughness và sương mỏng ở mép. Mask chỉ phục vụ edge frost nên phần lớn mặt ô vẫn là đá, chưa có lớp tuyết rõ. Tăng brightness hoặc đổi vertex color không giải quyết được sự thiếu lớp phủ và độ dày thị giác.

Snow Temple 2.0 thay **vật liệu Floor Dark**, giữ nguyên Core, Solver, Controller, production level, animation math/pivot, HUD, Main Menu, Mechanics Guide, background và global lights. Không thiết kế lại các special tiles theo hình concept; ký hiệu thật của game được giữ nguyên.

## 2. Color palette

Nguồn tập trung, thuần Python: `src/gui/snow_palette.py`. Authoring và runtime cùng dùng palette này; `visual_materials.SNOW_PALETTE` vẫn được re-export để tương thích.

| Thành phần | Token | Màu |
| --- | --- | --- |
| Main Snow | top | `#EFF5F8` |
| Snow Shadow | wear | `#CADCE9` |
| Fresh highlight/bevel | bevel | `#FFFFFF` |
| Ice Blue | frost | `#A8CCDF` |
| Exposed Stone | variation | `#849AAA` |
| Seams | seam | `#455E73` |
| Slate side | side | `#334D63` |
| Underside | underside | `#203448` |

Jungle không sử dụng palette này.

## 3. Ba lớp vật liệu

**Ancient Stone:** các mảng xám xanh có vân lớn, phân tầng nhẹ, vết nứt nhỏ và màu đá thay đổi có kiểm soát. Texture không phủ lên Fragile/Bridge/Goal/marker.

**Snow:** vùng phủ liên thông lấy từ noise đa tỉ lệ seed cố định, không có ellipse hoặc sprite chấm trắng. Mặt tuyết có các gợn thấp, sắc trắng bạc/xanh lạnh, chi tiết hạt mịn yếu và biên chuyển tiếp mềm. Snowbank có height ảo cao hơn phần đá lộ ra trong normal map; không displacement mesh.

**Frost/Ice:** sắc xanh bạc tại bờ tuyết và dải tuyết đóng băng nằm xuống phần trên của thành tile. Roughness cao giúp mặt tuyết không thành kính; specular nhỏ, không emission. Bevel thật và thành đá tối tạo silhouette, không dùng glow/outline neon.

Trong quá trình xem screenshot, bản thử có nhiều mảng đá nhỏ dạng camouflage đã được loại bỏ; asset cuối dùng cấu trúc lớn hơn và chuyển tiếp mềm. Các ảnh deliver là bản cuối, không phải ảnh tham khảo.

## 4. Snow coverage

`tools/build_snow_materials.py` tạo field liên thông từ noise ở nhiều scale. Threshold lấy quantile 20%; `smoothstep` có bề rộng hữu hạn giữ lớp chuyển tiếp mềm. RGBA alpha trong `snow-stone.png` là coverage, **không phải transparency**.

- Toàn atlas: **79.97%** pixel có coverage ≥0.5; coverage có trọng số **80.32%**.
- 64 phép UV thực tế tại pitch 1: **76.25–84.75%**, trung bình **80.07%**; giá trị có trọng số **76.87–84.95%**, trung bình **80.41%**.
- Kiểm tra dùng UV của face top thật, TexMatrix thực, offset/xoay từ `vary_tile`, không chỉ đo atlas rồi giả định mọi ô giống nhau.
- Tone/compactness theo row/col không nhân giảm alpha snow; không ngẫu nhiên mỗi frame.

Các con số là phép đo mask vật liệu trên mặt top, không phải phân loại pixel trắng từ screenshot đã chịu ánh sáng. Bevel và các ô đặc biệt không được tính là mặt tuyết.

## 5. Geometry, bevel và seams

Không đổi geometry: top **Z=0**, đáy Floor **−0.18 pitch**, cạnh **0.96 pitch**, bevel **0.02 pitch**, khe vật lý **0.04 pitch**. Vertices, normals hình học và UV giữ nguyên tại pitch 0.5/1/2.5. Khối không bị nâng hoặc chìm vào tuyết.

Snow depth dùng normal/height-like shading, gợn và dải màu ở thành, không thêm mesh nằm trên mặt tiếp xúc. Contact shading chỉ nằm sát khe thật. Tuyết không nối qua gap, không dựng grid overlay hoặc đáy liền dưới board. Không thêm bề mặt ở Void hay bridge inactive.

## 6. Side và underside

Thành slate xanh than có vân theo Z, phía trên có dải tuyết/băng trắng bạc; mặt dưới tối hơn. Nền biên cũ kéo xuống khoảng −0.45 đến −0.64 pitch tiếp tục được tái sử dụng. Chỉ các ô Floor thường ở biên có nền này; Fragile/Bridge/Goal/Void không có supporting slab ẩn. Các icicle nhỏ có sẵn ở mép ngoài được giữ, không thêm hệ particle/geometry mới.

## 7. Texture/shader pipeline

- `snow-stone.png`: RGBA 1024²; RGB đã compositing đá/tuyết có màu và sắc độ, alpha coverage. Fallback vì vậy vẫn nhìn thấy tuyết thật trong texture.
- `snow-stone-normal.png`: RGBA 1024²; RGB tangent-space normals, alpha roughness, cao hơn ở powder snow. Normal chứa độ dốc của bờ tuyết và các gợn/hạt mịn.
- Hai asset procedural nguyên bản, seed `28102026`, không dùng asset bên ngoài. Numpy/Pillow chỉ dùng để author; game không thêm dependency.
- `snow-floor.vert/frag` xử lý riêng Floor Dark. TBN derivative theo UV/world position hỗ trợ xoay UV, offset và thành đứng. Quality hiện có điều khiển độ mạnh normal map.
- Dải frost/snow lip theo local Z nằm xuống thành, không đổi support plane. Thao tác wall/lip/strata được bỏ qua trên fragments top phẳng để giảm chi phí.
- Sampler dùng mipmaps/anisotropic 8×. Texture/material cache hiện có được tái sử dụng; mỗi instance chỉ có transform/uniform riêng.
- Khi GLSL không khả dụng: albedo RGB opaque, palette vertex và bevel/side geometry vẫn đúng. Tắt light riêng trên Floor fallback để tránh bị ánh trăng global nhuộm xanh. Không có normal/specular/lip shader trong fallback.

Rebuild chỉ hai asset Snow:

```bash
python3 -B -m tools.build_snow_materials
```

## 8. Lighting và background

Shader có fill trung tính và key bạc lạnh riêng cho Floor. Tuyết không emissive; roughness giữ highlight mềm. Không đổi `scene_lighting.py`, shader Temple/magma, moon, panorama, waterfalls, weather, exposure hoặc bố cục môi trường.

Không bổ sung shadow-map sampling hoặc nguồn sáng động mới. Depth perception đến từ normals, snowbank shading, bevel, seams và slate sides.

## 9. Theme isolation

Light giữ nguyên texture/UV/material, dây leo, vertex buffer và ánh sáng. Dark có `ColorScaleOff` trên holder riêng để multiplier Jungle 0.88–1.05 không làm tuyết tối lần thứ hai; Light vẫn nhận multiplier cũ. Shader/tone/UV được gán trên instance holder, không mutate prototype hoặc texture chung.

Ảnh Jungle trước/sau cùng camera tại Level 4 và 11 giống hệt toàn bộ framebuffer (**0 pixel thay đổi**), số liệu trong `evidence/snow-temple-2-0/comparison.json`. 12 lần Light↔Dark trên cùng scene không tăng node, không tải lại texture và không sửa Core/snapshot.

## 10. Kiểm thử tự động

Baseline **597 tests PASS**. Bộ regression cuối **601 tests PASS, 128.827 giây**. Bốn test thêm mới kiểm tra:

1. Coverage atlas ~80%, đủ vùng chuyển tiếp mềm.
2. 64 tile UV transforms giữ coverage trong 75–85%.
3. Texture có sắc độ tuyết và đá lộ ra, không phải mặt trắng phẳng.
4. Dark bỏ đúng Jungle multiplier; Light giữ nguyên.

Test fallback được kiểm tra cả trường hợp common shader tồn tại nhưng Snow shader không khả dụng. Các assertion geometry/footprint, floor height, normals và collision-related contracts cũ không được nới hoặc bỏ. Log đầy đủ: [regression](evidence/snow-temple-2-0/regression.txt).

## 11. Panda3D runtime

Xác minh trên GLX `GraphicsWindow`, Mesa llvmpipe; thao tác Guide, phím, solver và các nút dùng X11 XTest. Không có ShowBase thứ hai. Chụp thật ở **1024×720, 1280×720, 1920×1080**.

- Snow Level 1/4/11/18: basic, board lớn, nhiều Void, Fragile/Bridge/switches, Goal/flag và magma.
- Full orbit 30° đến 390°, close-up, low-angle side/underside, distant framing, Guide focus/Back và camera takeover.
- Shader đã compile/prepare trên GSG thật; thay normal map bằng flat normal tạm thời làm framebuffer thay đổi, xác nhận map thực sự được dùng.
- Manual roll, Core-danger fall, result, Restart.
- Sáu solver replay đến Goal; bridge đóng/mở; Guide không chiếm camera khi gameplay busy.
- Split và merge: hai theme, các pha VFX, Pause/Step, restart/đổi level giữa chừng, Iso/Top/Follow, speed/resize.
- Fallback không shader; Main Menu/HUD; 12 lần theme switching.

Các report đều PASS: Snow/orbit **5 nhóm**, fallback **3**, Guide/sáu solver **11**, split **5**, merge **5**; Main Menu chụp/kiểm tra riêng. Snow shader không có compile/runtime error; normal-map A/B làm thay đổi **9.197 mẫu pixel** tại close-up trên lưới sample bước 2.

Weather và nhịp cờ được freeze **chỉ trong tool so ảnh** để giữ before/after khớp. Game thường vẫn chạy hiệu ứng. Orbit GIF là các keyframes chụp từ framebuffer thật, không phải quay video thời gian thực.

```bash
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.snow_floor_smoke --orbit --output /tmp/snow-temple-qa
```

## 12. Before/after và bằng chứng

Ảnh before là bản Frosted Ancient Stone ngay trước nhiệm vụ này, cùng camera và level. Ảnh concept người dùng chỉ là art direction, không dùng làm chứng cứ runtime.

- [Before Level 4](evidence/snow-temple-2-0/before/dark-level_04-1280x720.png)
- [After Level 4](evidence/snow-temple-2-0/after/dark-level_04-1280x720.png)
- [Full board nhiều Void/specials](evidence/snow-temple-2-0/after/dark-level_18-1280x720.png)
- [Close-up Snow tile](evidence/snow-temple-2-0/after/dark-stone-close-up.png)
- [Side/lip/slate](evidence/snow-temple-2-0/after/dark-platform-sides.png)
- [1024×720](evidence/snow-temple-2-0/after/dark-level_04-1024x720.png)
- [1920×1080](evidence/snow-temple-2-0/after/dark-level_04-1920x1080.png)
- [Guide focus](evidence/snow-temple-2-0/after/dark-fragile-guide-focus.png)
- [Jungle regression](evidence/snow-temple-2-0/after/light-level_04-1280x720.png)
- [Orbit keyframes GIF](evidence/snow-temple-2-0/orbit.gif)
- [Snow Main Menu](evidence/snow-temple-2-0/main-menu.png)
- [Fixed-function fallback](evidence/snow-temple-2-0/fallback.png)

Reports Guide/sáu solver, split, merge và fallback được lưu cạnh các ảnh. Các report gốc liệt kê thêm frame trong thư mục `/tmp/snow-temple-*` của phiên làm việc; bộ ảnh đại diện được copy vào repo này.

## 13. Performance/tài nguyên

Vẫn **hai texture RGBA 1024²**, không thêm sampler, mesh, draw Geom, node, light hoặc task so với Frosted Ancient Stone. Base texture memory khoảng 8 MiB, khoảng 10.7 MiB với mip chain; PNG tổng khoảng 1.25 MiB. Không rebuild tile mỗi animation tick hoặc snapshot.

`comparison.json` lưu node/Geom, texture reuse và timings của từng scene. Timing các lần chụp riêng có tải CPU khác nhau; không dùng chúng để kết luận FPS regression. Đo shader-cost bổ sung xen kẽ 6×30 frames mỗi shader, cùng scene/camera/geometry và texture hiện tại: shader Snow trước nhiệm vụ so với Snow Temple 2.0. Đây chỉ là phép so chi phí shader, không dựng ảnh giả before. Số liệu trong `benchmark.json`.

Kết quả llvmpipe: median **33.71 → 35.31 ms** (**+1.60 ms, +4.75%**); p95 **48.60 → 41.49 ms**. Đây là chi phí tăng nhỏ trong phép đo software renderer này, không phải cam kết FPS trên GPU khác. Node/Geom giống baseline ở cả sáu scene/theme; không có texture reload hoặc tăng node qua 12 lần đổi theme. Không có performance/resource regression nghiêm trọng được ghi nhận trong phạm vi kiểm tra.

## 14. Files thay đổi trong nhiệm vụ này

- `src/gui/snow_palette.py`: palette/coverage target dùng chung authoring/runtime.
- `src/gui/visual_materials.py`: re-export palette, bind snow colour; giữ nguyên common materials/fallback.
- `src/gui/temple_environment.py`: Dark ColorScale isolation; Light không đổi.
- `tools/build_snow_materials.py`: layered snow/stone/mask/normal/roughness.
- `assets/materials/snow-stone.png`, `snow-stone-normal.png`.
- `assets/shaders/snow-floor.frag`: snowbank, lip, side shading và top-face optimisation. Vertex shader/geometry giữ nguyên.
- `tests/test_snow_floor_material.py`, `tools/snow_floor_smoke.py` (`--orbit`).
- Báo cáo này và evidence. Báo cáo Frosted Ancient Stone cũ được giữ làm lịch sử, thêm link tới bản hiện tại.

## 15. Giới hạn và Git scope

- Đây là vật liệu winter fantasy stylized, không cam kết chất lượng photoreal giống ảnh concept. Có normal/roughness; không tessellation/displacement/PBR/IBL đầy đủ.
- Coverage được kiểm tra trên atlas và 64 transforms tại pitch gameplay 1; không khẳng định mọi crop/UV tuỳ chỉnh ở mọi pitch có chính xác 80%.
- Fallback giảm chi tiết so với GLSL; không tuyên bố có normal map khi shader không chạy.
- Xác minh runtime trên Mesa llvmpipe; chưa test GPU NVIDIA/AMD/Intel riêng, Windows hoặc macOS. Dynamic shadow pipeline không được nâng cấp trong đợt này.
- Khe và vân nhỏ giảm theo mipmap khi zoom rất xa; giữ ưu tiên silhouette/grid, không thêm outline neon.
- Benchmark là software rendering trong môi trường kiểm thử, không suy rộng tốc độ sang GPU người dùng.
- Giữ nguyên branch `feat/team-code/phase2-game-gui`, HEAD `2cb6140`, toàn bộ tracked/untracked changes có sẵn. Không commit, push, merge, checkout, reset, clean, stash hoặc rebase.
