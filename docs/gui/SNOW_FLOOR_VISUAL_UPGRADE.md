# Snow Floor — Frosted Ancient Stone 2.0

Đây là báo cáo của giai đoạn đá phủ sương trước đây. Vật liệu Snow hiện tại đã được nâng cấp tiếp trong [Snow Temple 2.0](SNOW_TEMPLE_2_0.md); palette/mask cũ bên dưới được giữ làm lịch sử đối chiếu.

## Phạm vi và nguyên nhân

Chỉ đổi Floor và thành đá trang trí của Snow/Dark. Không đổi Core, solver, controller, level, camera, HUD, animation, background hoặc global lighting. Các thay đổi chưa commit có sẵn trong workspace được giữ nguyên.

Trước đây cả hai theme dùng `temple-stone.png`. Vertex Floor và shader ánh trăng làm mặt đá xanh gần màu núi; texture nhiều chi tiết nhỏ gây nhiễu khi thu nhỏ. Thành đá cũng dùng màu xanh sáng nên thiếu tương phản với mặt trên. UV chỉ dịch ngẫu nhiên, chưa xoay. Bevel, nền đá dưới các ô biên và mipmaps đã tồn tại; nâng cấp tận dụng chúng thay vì dựng thêm nền liền.

## Palette tập trung

`visual_materials.SNOW_PALETTE` là nguồn màu duy nhất cho sàn Snow:

| Token | Màu | Công dụng |
| --- | --- | --- |
| top | `#A5A8A1` | Granite xám trung tính hơi ấm |
| variation | `#7D8585` | Màu tham chiếu biến thiên đá |
| frost | `#E4EDF0` | Sương bạc tại mép |
| bevel | `#CBD3D1` | Highlight cạnh vát |
| side | `#3A4B57` | Thành đá phiến |
| underside | `#253744` | Mặt dưới |
| seam | `#344753` | Contact shading mép gạch |
| wear | `#D6DAD2` | Màu tham chiếu đá mòn |

## Vật liệu, texture và shader

- `snow-stone.png`: RGBA 1024×1024. RGB là albedo điều biến với mảng khoáng lớn, vân trung bình, nứt mảnh và grain rất nhẹ; alpha là mask phân bố sương, **không phải transparency**.
- `snow-stone-normal.png`: RGBA 1024×1024. RGB chứa tangent-space normal; alpha là roughness (~0.84–0.98), tránh bề mặt bóng như kim loại.
- Hai asset được tạo nguyên bản, seed cố định `28102026`, bởi `tools/build_snow_materials.py`. Không tải ảnh bên ngoài hoặc thêm dependency runtime. Numpy/Pillow chỉ dùng khi authoring.
- `snow-floor.vert/frag` là shader GLSL 120 riêng cho Floor Dark. TBN tính bằng derivative của UV/world position, nên normal mapping đi theo UV xoay ở từng ô, kể cả thành đứng.
- Normal strength tuân theo quality hiện tại. Roughness điều khiển highlight nhỏ, không phải pipeline PBR đầy đủ.
- Texture lọc mipmaps + anisotropic 8×, cache có giới hạn qua pipeline material hiện có; không tải lại mỗi frame/snapshot.
- Compile/prepare shader trên GSG thật. `SNOW_STATUS=GLSL_NORMAL_ROUGHNESS_FROST` khi thành công. Nếu shader chung hoặc shader Snow không dùng được, sàn dùng albedo RGB opaque, vertex palette và geometry cũ. Fallback tắt light riêng trên Floor Snow để tránh ánh trăng global nhuộm xanh trở lại; tương phản top/side/underside có sẵn trong vertex colours. Không để mask alpha biến Floor thành trong suốt.

Rebuild **chỉ hai asset mới**, từ repo root:

```bash
python3 -B -m tools.build_snow_materials
```

## Frost, seams và thành đá

Sương là blend theo khoảng cách tới cạnh trong local tile coordinates và mask texture, không phải decal trắng hoặc geometry nằm trên mặt lăn. Mật độ thay đổi xác định theo row/col. Các ô xoay UV 0/90/180/270°, có biến thiên tone/mask nhẹ. Shader input trên instance có priority cao hơn default của shared Geom, không mutate prototype.

Khe vật lý vẫn 0.04 pitch. Bevel vẫn 0.02 pitch; shader thêm contact shading hẹp sát cạnh mỗi tile, không tạo outline quanh board. Mặt bên tối, có vân phân tầng theo Z; mặt dưới tối hơn nữa.

Không tăng độ dày mesh Floor: kích thước vẫn 0.96×0.96×0.18 pitch, mặt trên Z=0, đáy Z=−0.18 pitch. Thành đá biên có sẵn kéo xuống khoảng −0.45 đến −0.64 pitch, nằm trong footprint từng ô Floor thường. Không đặt nền dưới Fragile, Bridge, Goal hoặc Void. Không tạo tấm đá phủ các lỗ.

## Ánh sáng và cách ly theme

Shader Floor Snow phối key ánh trăng lạnh với fill trung tính cục bộ. Không thêm light/task và không chỉnh `SceneLightingController`, shader Temple, magma hay các marker.

`TileTheme-light/dark` tiếp tục chọn mesh riêng như trước. Jungle giữ nguyên texture, vertex buffer, vật liệu, UV, cây/dây leo và ánh sáng. Screenshot Jungle Level 4 và 11 trước/sau được so pixel ở cùng camera: vùng gameplay/background có **0 pixel đổi**. Level 4 giống toàn bộ framebuffer; Level 11 có 15 pixel ở HUD y=45 lệch 1/255 do rounding, không nằm trên board. Kết quả nằm trong `evidence/snow-floor/comparison.json`.

## Kiểm tra tự động

Baseline trước sửa: **587 tests PASS**. Thêm 10 tests về:

- Hash vertex buffer Jungle đúng baseline; texture Jungle không đổi.
- Floor hai theme có cùng vertices/normals/UV tại pitch 0.5/1/2.5; Z=0 và kích thước không đổi.
- Phân biệt màu top/bevel/side/underside.
- Texture Snow riêng, mipmaps, cache, không phủ lên các special materials.
- Normal map có normal đơn vị và roughness phù hợp.
- Shader bind normal/roughness thật, pitch đúng, không đổi Jungle.
- Fallback opaque khi shader Snow không khả dụng.
- Xoay UV/tone xác định; instance không sửa mesh chia sẻ.
- Frost per-instance thực sự override default ở Geom.
- Nhiều lần dựng mesh không tạo texture/material mới không giới hạn.

Các assertion cũ về hình học, footprint, chống xuyên sàn không bị sửa. **Full regression cuối: 597 tests PASS, 98.454 giây**, lưu trong `evidence/snow-floor/regression.txt`. Không có test bị bỏ qua để đạt kết quả này.

## Kiểm tra runtime và ảnh

Ảnh chụp từ Panda3D `GraphicsWindow` trên GLX/llvmpipe, không phải mock hoặc concept. Dùng X11 XTest để bấm Guide, Back, điều khiển, Restart và chạy solver. Thời tiết 2D và nhịp cờ được tạm dừng **chỉ trong công cụ so ảnh**, để before/after khớp; game bình thường vẫn chạy hiệu ứng.

```bash
xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
  .venv/bin/python -B -m tools.snow_floor_smoke --output /tmp/snow-floor-check
```

`--stage before` dùng trước khi chỉnh material để ghi cùng camera/level. Không giả lập vật liệu cũ trong game và không có công tắc legacy trong production.

Các ảnh trong `evidence/snow-floor/`:

- [Before Snow Level 4](evidence/snow-floor/before/dark-level_04-1280x720.png)
- [After Snow Level 4](evidence/snow-floor/after/dark-level_04-1280x720.png)
- [Board có nhiều khoảng trống và special tiles](evidence/snow-floor/after/dark-level_11-1280x720.png)
- [Stone close-up trên panorama thật](evidence/snow-floor/after/dark-stone-close-up.png)
- [Platform sides](evidence/snow-floor/after/dark-platform-sides.png)
- [Underside](evidence/snow-floor/after/dark-platform-underside.png)
- [1280×720, level đơn giản](evidence/snow-floor/after/dark-level_01-1280x720.png)
- [1024×720](evidence/snow-floor/after/dark-level_04-1024x720.png)
- [1920×1080](evidence/snow-floor/after/dark-level_04-1920x1080.png)
- [Jungle regression](evidence/snow-floor/after/light-level_04-1280x720.png)
- [Guide focus Fragile](evidence/snow-floor/after/dark-fragile-guide-focus.png)

Runtime còn kiểm tra 12 lần đổi Light/Dark trên cùng scene, không tăng node/reload texture; normal-map A/B với flat normal làm framebuffer Floor thay đổi; roll/fall/restart bằng phím thật. Quy tắc Moves khi thất bại giữ nguyên controller hiện tại: chỉ transition thành công mới được commit.

Kết quả: Snow smoke **4 nhóm PASS**, fixed-function fallback **3 nhóm PASS**, Guide/sáu solver **11 nhóm PASS**, split **5 nhóm PASS**, merge **5 nhóm PASS**. Shader biên dịch không lỗi; normal-map A/B tại close-up có 101 mẫu pixel đổi trên lưới lấy mẫu bước 2, xác nhận normal/roughness texture thực sự được shader dùng. Ba độ phân giải đều đã chụp framebuffer.

`mechanics_focus_smoke` kiểm tra hai theme, bốn kích thước, bridge inactive/active, Guide lifecycle và sáu solver replay tới Goal. `split_teleport_smoke` và `merge_teleport_smoke` kiểm tra các pha hiệu ứng, Pause/Step, restart/đổi level khi đang chạy, ba camera và các tốc độ replay. Các report được lưu kèm evidence.

## Hiệu năng và tài nguyên

Không thêm Geom, node, light hoặc task vào scene. Floor và foundations tái sử dụng geometry có sẵn. Hai texture mới thêm khoảng 8 MiB base RGBA, khoảng 10.7 MiB nếu tính đủ mip chain; PNG tổng khoảng 1.4 MiB. Không thay asset chung để tiết kiệm bộ nhớ bằng cách làm Jungle đổi theo.

`comparison.json` so node/Geom và frame timings trước/sau. Timing trên llvmpipe có ảnh hưởng tải CPU và không thay cho benchmark GPU thực. Thử đổi theme kiểm tra tài nguyên ổn định riêng, không suy leak từ một lần đo.

Các lần chụp riêng lẻ có tải CPU khác nhau nên không dùng chênh lệch frame time đó để kết luận regression. Đo bổ sung xen kẽ 6 lượt × 30 frame cho mỗi material trên **cùng** Level 4/camera/geometry, chờ ParSolver xong: Temple shader cũ median **29.68 ms**, Snow shader **27.73 ms** (tỷ lệ **0.934**). Đây là phép so chi phí shader/texture, không giả tạo screenshot baseline. Không ghi nhận tăng chi phí frame trong phép đo này; chưa suy rộng sang GPU khác. Chi tiết trong `interleaved-benchmark.json`.

## Files thay đổi trong nhiệm vụ này

- `src/gui/mesh_factory.py`: palette Floor Dark; giữ geometry/Light.
- `src/gui/visual_materials.py`: palette, texture/cache opaque, compile/bind shader Snow và fallback.
- `src/gui/temple_environment.py`: instance variation Snow, màu foundations Dark và pitch.
- `assets/materials/snow-stone.png`, `snow-stone-normal.png`.
- `assets/shaders/snow-floor.vert`, `snow-floor.frag`.
- `tools/build_snow_materials.py`, `tools/snow_floor_smoke.py`.
- `tests/test_snow_floor_material.py`, tài liệu và evidence này.

## Giới hạn

- Đây là vật liệu stylized có normal/roughness; không có displacement, tessellation hoặc PBR/IBL đầy đủ.
- Snow shader dùng local contact shading; không bổ sung sampling shadow map thật. Không tuyên bố đã cải thiện dynamic shadows.
- Fallback giữ màu, texture, bevel và chiều sâu nhưng không có normal/specular/frost blend của shader.
- Bộ geometry cũ vẫn có các icicle nhỏ và nền biên; không làm lại model. Ở camera rất xa, chi tiết nhỏ giảm theo mipmap, ưu tiên hình board và khe gạch.
- Runtime xác minh trên Mesa llvmpipe; chưa kiểm tra trực tiếp NVIDIA/AMD/Intel/Windows/macOS.
- Không sửa các vấn đề nền/trình bày camera ngoài phạm vi sàn Snow. Trong công cụ close-up, cập nhật backdrop theo lens để tránh ảnh inspection bị nền trắng do `reframe()` vốn dành cho Follow và không gửi refit callback.

Không commit, push, merge hoặc đổi branch.
