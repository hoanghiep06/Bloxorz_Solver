# Visual Overhaul V2 — nguồn tài nguyên

Ngày tạo: 2026-10-27. Không tải texture/model từ website, không cắt bàn chơi hoặc UI từ ảnh tham chiếu. Không bổ sung thư viện runtime.

| Tài nguyên mới | Nguồn / phương pháp |
| --- | --- |
| `backgrounds/jungle-temple.png` | Sinh mới bằng built-in `image_gen` (skill `imagegen`), chỉ cảnh môi trường; không chứa bàn chơi hoặc giao diện. |
| `backgrounds/winter-temple.png` | Sinh mới bằng built-in `image_gen`, chỉ cảnh môi trường mùa đông. |
| `materials/temple-stone.png` | Sinh mới bằng built-in `image_gen`, albedo đá cổ, không cắt từ ảnh game. |
| Các PNG material còn lại | Mã tự sinh trong `tools/build_visual_materials.py`, seed 42716; Voronoi tuần hoàn bị biến dạng, noise nhiều tần số, mask emission và height. |
| `shaders/*.vert`, `shaders/*.frag` | Shader GLSL viết cho repo này. |
| Mesh, glyph, edge growth, HUD icons mới | Geometry tạo bằng mã Python trong repo, không dùng model bên ngoài. |

Không có tài nguyên mới nào mang giấy phép của kho asset bên thứ ba cần mua hoặc ghi nguồn riêng. Hai panorama và albedo temple-stone là đầu ra AI, không được mô tả là ảnh chụp thực tế hoặc là tài sản được vẽ thủ công. Việc phân phối mã/asset của dự án theo chính sách mà chủ repo lựa chọn; tài liệu này ghi nguồn, không tự đặt giấy phép mới cho cả repo. Các asset cũ `day.png`, `night.png`, âm thanh và font hiện có không bị thay thế hoặc đổi thông tin nguồn.

## Prompt gốc — built-in tool mode

### Jungle

> Use case: stylized-concept. Asset type: 16:9 widescreen scenic background panorama for a real-time 3D puzzle game. Bright Jungle Temple: lush tropical rainforest canyon, several tall distant waterfalls dropping into a deep misty valley, ancient small stone temple on the upper right horizon, warm diagonal morning sunlight, blue sky with soft clouds, green foliage framing the far left and lower corners. High quality cinematic environment matte painting, believable detailed rock, vegetation and atmospheric depth. The CENTER and lower-middle must be an OPEN MISTY CANYON with low contrast distant foliage and pale atmospheric haze, unobstructed negative space for a separately rendered floating board. Horizon in upper third. No floating game platforms, no board, no tiles, no block, no UI, no text, no icons, no logo, no watermark. Avoid large foreground objects crossing the central 75 percent. This is only scenery, never a screenshot of a game.

### Winter

> Use case: stylized-concept. Asset type: cinematic 16:9 scenic background for a real-time 3D puzzle game, environment only. Snowy alpine canyon under a deep sapphire blue starry night with a full moon high on the right, tiny warm golden cabin windows in distant snowy pine forest at the left margin and far right hillside, soft atmospheric mist in a deep valley. Center and lower-middle must be an OPEN MISTY CHASM with subdued distant scenery and negative space for a separately rendered floating puzzle board. Horizon upper third. Beautiful painterly realistic 3D game environment matte painting, snow-covered rock and evergreen framing extreme corners, balanced blue ambient moonlight and warm accents. No board, no tiled platform, no game blocks, no UI, no text, no logos, no watermark. No prominent objects crossing the central 75 percent.

### Stone albedo

> Use case: stylized-concept. Asset type: square tileable diffuse ALBEDO texture for an ancient jungle-temple stone material in a real-time 3D game. A close straight-on orthographic view of pale warm gray aged limestone, rugged mineral grain, small irregular flaked stone patches, worn fine fissures, a few uneven thin dark gray hairline cracks, sparse olive moss embedded in crevices, tiny bright chipped mineral edges. Realistic detailed tactile stone surface, professionally authored game texture, neutral even diffuse illumination, moderately bright midtones. Entire image filled edge to edge with continuous stone material. No separate tiles, no grout grid, no slab boundary or outer border, no objects, no perspective, no cast shadows, no directional lighting, no black holes, no vignette, no text, no logos, no orange lava. Texture must be readable on small slabs yet have rich close-up detail. Soft seamless transitions on all four edges.
