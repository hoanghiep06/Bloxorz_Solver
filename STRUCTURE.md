# 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

> **Lưu ý cho các thành viên:** Khi tạo mới, đổi tên hoặc tái cấu trúc các file/thư mục thuộc phân công của mình, hãy chủ động cập nhật lại sơ đồ cây và bảng mô tả bên dưới trước khi tạo Pull Request (PR).

---

## 1. Sơ đồ cây tổng quan

```text
Bloxorz_Solver/
├── assets/                                 # Tài nguyên đa phương tiện tĩnh
│   ├── audio/                             # Hiệu ứng âm thanh (.wav) và nhạc nền cơ bản
│   │   ├── click.wav                      # Âm thanh click tương tác giao diện UI
│   │   ├── fall.wav                       # Âm thanh rơi khối khi sảy chân (Game Over)
│   │   ├── goal.wav                       # Âm thanh hoàn thành màn chơi (Victory)
│   │   ├── music.wav                      # Nhạc nền ambient trong game
│   │   └── roll.wav                       # Âm thanh lật khối 90 độ
│   ├── backgrounds/                       # Ảnh nền panorama/backdrop chất lượng cao cho không gian 3D
│   │   ├── day.png                        # Ảnh nền ban ngày (Theme Light)
│   │   ├── jungle-temple.png              # Ảnh nền đền cổ nhiệt đới (Jungle Temple Theme)
│   │   ├── night.png                      # Ảnh nền ban đêm vũ trụ (Theme Dark)
│   │   └── winter-temple.png              # Ảnh nền đền tuyết mùa đông (Winter Temple Theme)
│   ├── icons/                             # Biểu tượng đồ họa giao diện
│   │   ├── README.md                      # Tài liệu quy trình tiền xử lý và nguồn gốc icon AI Robot
│   │   ├── ai-robot.png                   # Icon robot AI chuẩn RGBA đã tách nền cho thanh công cụ HUD
│   │   └── sources/                       # Ảnh gốc trước xử lý
│   │       └── ai-robot-source.png        # Ảnh robot AI gốc (360×360)
│   ├── materials/                         # Texture map bề mặt vật liệu PBR/shading tự sinh
│   │   ├── fragile.png                    # Texture bề mặt ô cam dễ vỡ
│   │   ├── magma.png                      # Texture phát sáng dung nham nóng chảy
│   │   ├── magma-height.png               # Bản đồ độ cao (height map) dung nham
│   │   ├── metal.png                      # Texture bề mặt kim loại cho công tắc & cầu
│   │   ├── stone-dark.png                 # Texture đá tối màu cho sàn gạch
│   │   ├── stone-height.png               # Bản đồ độ cao (height map) đá gạch
│   │   ├── stone-light.png                # Texture đá sáng màu cho sàn gạch
│   │   └── temple-stone.png               # Texture albedo đá cổ rêu phong cho môi trường Đền
│   ├── shaders/                           # Bộ shader GLSL tùy chỉnh cho Panda3D
│   │   ├── bloom.vert                     # Vertex shader cho hiệu ứng Cinematic Bloom
│   │   ├── bloom-extract.frag             # Fragment shader trích xuất vùng sáng phát quang (emission)
│   │   ├── bloom-composite.frag           # Fragment shader hòa trộn lớp bloom với khung cảnh gốc
│   │   ├── temple.vert                    # Vertex shader dựng hình bề mặt khối và sàn đền cổ
│   │   └── temple.frag                    # Fragment shader xử lý ánh sáng chi tiết và phát quang
│   └── VISUAL_ATTRIBUTION.md              # Ghi nhận nguồn gốc, bản quyền và prompt tạo asset đồ họa
├── docs/                                  # Tài liệu kỹ thuật, báo cáo & đặc tả thiết kế
│   ├── BASELINE.md                        # Cơ sở lý thuyết thuật toán tìm kiếm
│   ├── BFS.md                             # Báo cáo chuyên sâu thuật toán BFS
│   └── gui/                               # Đặc tả kiến trúc hệ thống giao diện 3D Panda3D
│       ├── evidence/                      # Dữ liệu hình ảnh, báo cáo JSON, GIF kiểm thử trực quan
│       ├── ASSET_CREDITS.md               # Nguồn gốc tài nguyên và bản quyền
│       ├── BASIC_RENDERER_API.md          # Tài liệu API cho Renderer cơ bản
│       ├── BUGFIX_FALLING_GUIDE_TOOLBAR.md# Ghi chú khắc phục lỗi hoạt cảnh rơi, guide rail và toolbar
│       ├── GAME_INTEGRATION.md            # Tài liệu tích hợp game native, luồng điều khiển & solver worker
│       ├── GEOMETRY_TILE_SPEC.md          # Đặc tả hình học ô gạch và switch
│       ├── JUNGLE_TEMPLE_VISUAL_OVERHAUL.md # Tài liệu đại tu nâng cấp đồ họa chủ đề Đền Cổ
│       ├── LAYOUT_CAMERA_SPEC.md          # Đặc tả camera và phân vùng viewport
│       ├── MECHANICS_GUIDE.md             # Đặc tả hệ thống thẻ hướng dẫn cơ chế trò chơi
│       ├── MOVE_ASSIST_ANIMATION.md       # Đặc tả hệ thống hỗ trợ di chuyển và cảnh báo nguy hiểm
│       ├── PHYSICAL_FALLING_UPGRADE.md    # Đặc tả nâng cấp mô phỏng vật lý khối rơi tự do
│       ├── README.md                      # Tổng quan kiến trúc phân tầng module GUI
│       ├── RENDER_CONTRACT.md             # Hợp đồng dữ liệu tầng đồ họa
│       ├── STAGE2_HANDOFF.md              # Bàn giao kiến trúc giai đoạn Stage 2
│       ├── STAGE3_1_FOUNDATION.md         # Đặc tả nền tảng ứng dụng GUI (Stage 3.1)
│       ├── STAGE3_2_CONTRACTS.md          # Đặc tả hợp đồng dữ liệu hiển thị (Stage 3.2)
│       ├── STAGE3_3_GEOMETRY.md           # Đặc tả lưới hình học cơ bản (Stage 3.3)
│       ├── STAGE3_4_PRESENTATION.md       # Đặc tả vật liệu và nguồn sáng cơ bản (Stage 3.4)
│       ├── STAGE3_5_LAYOUT_HUD.md         # Đặc tả bố cục layout và HUD (Stage 3.5)
│       ├── STAGE3_6_VALIDATION.md         # Quy chuẩn nghiệm thu và kiểm thử (Stage 3.6)
│       ├── STAGE3_HANDOFF.md              # Bàn giao tổng kết giai đoạn Stage 3
│       ├── STAGE3_RELEASE_CHECKLIST.md    # Danh mục kiểm tra phát hành Stage 3
│       ├── STAGE4_ADVANCED_RENDERER.md    # Đặc tả bộ dựng hình nâng cao (Stage 4)
│       ├── STAGE4_INTEGRATION_NOTES.md    # Ghi chú tích hợp đồ họa nâng cao (Stage 4)
│       ├── STAGE5_ANIMATION_SYSTEM.md     # Đặc tả hệ thống hoạt cảnh liên tục (Stage 5)
│       ├── STAGE5_INTEGRATION_NOTES.md    # Ghi chú tích hợp hệ thống hoạt cảnh (Stage 5)
│       ├── TEAM_INTEGRATION_REVIEW.md     # Đánh giá và ghi chú tích hợp liên nhóm
│       ├── TEST_PLAN.md                   # Kế hoạch kiểm thử tự động giao diện
│       └── VISUAL_SPEC.md                 # Quy chuẩn thẩm mỹ thị giác và vật liệu
├── levels/                                # Catalog 18 màn chơi chính thức của game (JSON)
│   ├── level_01.json                      # Màn 01: Nhập môn di chuyển khối cơ bản
│   ├── level_02.json                      # Màn 02: Ô cam mỏng manh dễ vỡ (fragile tile)
│   ├── level_03.json                      # Màn 03: Nút tròn (soft switch) và cầu nối
│   ├── level_04.json                      # Màn 04: Nút chéo (heavy switch) yêu cầu đứng thẳng
│   ├── level_05.json                      # Màn 05: Nút phân tách khối (split switch) thành 2 khối 1x1
│   ├── level_06.json                      # Màn 06: Phối hợp công tắc và cầu mở rộng
│   ├── level_07.json                      # Màn 07: Thử thách ô vỡ và đường vòng hẹp
│   ├── level_08.json                      # Màn 08: Cơ chế chuyển đổi cầu bật/tắt luân phiên (toggle)
│   ├── level_09.json                      # Màn 09: Cầu kích hoạt một chiều vĩnh viễn (permanent)
│   ├── level_10.json                      # Màn 10: Phối hợp khối con và địa hình hiểm trở
│   ├── level_11.json                      # Màn 11: Mê cung công tắc liên hoàn
│   ├── level_12.json                      # Màn 12: Phân tách khối tầm xa và hội tụ
│   ├── level_13.json                      # Màn 13: Cầu song song và nhịp bước chính xác
│   ├── level_14.json                      # Màn 14: Địa hình rời rạc với mật độ ô cam cao
│   ├── level_15.json                      # Màn 15: Thử thách giải đố đa tầng switch
│   ├── level_16.json                      # Màn 16: Không gian mở và bài toán định hướng
│   ├── level_17.json                      # Màn 17: Phối hợp toàn diện công tắc nặng, nhẹ và phân tách
│   └── level_18.json                      # Màn 18: Thử thách đỉnh cao kết hợp toàn bộ cơ chế
├── music/                                 # Nhạc nền bổ sung định dạng MP3
│   ├── 1.mp3                              # Nhạc nền chủ đề 1
│   └── 2.mp3                              # Nhạc nền chủ đề 2
├── src/                                   # Toàn bộ mã nguồn chính của dự án
│   ├── core/                              # Tầng lõi trò chơi (Logic & Quy tắc vật lý)
│   │   ├── __init__.py                    # Khởi tạo package core
│   │   ├── board.py                       # Quản lý bản đồ, transition model, xử lý switch/cầu/tách/nhập khối
│   │   └── state.py                       # Biểu diễn trạng thái BloxorzState (tư thế, tọa độ, khối tách, trạng thái cầu)
│   ├── solvers/                           # Tầng thuật toán tìm kiếm AI (AI Solvers)
│   │   ├── __init__.py                    # Khởi tạo package solvers
│   │   ├── base_solver.py                 # Lớp cơ sở trừu tượng BaseSolver & đo benchmark 4 chỉ số chuẩn
│   │   ├── astar.py                       # Thuật toán A* Search (kết hợp heuristic)
│   │   ├── bfs.py                         # Thuật toán BFS (Breadth-First Search)
│   │   ├── dfs.py                         # Thuật toán DFS (Depth-First Search)
│   │   ├── greedy.py                      # Thuật toán GBFS (Greedy Best-First Search)
│   │   ├── ids.py                         # Thuật toán IDS (Iterative Deepening Search)
│   │   ├── ucs.py                         # Thuật toán UCS (Uniform-Cost Search) chuẩn tích hợp
│   │   └── UCS_Algorithm/                 # Mô-đun thử nghiệm độc lập cho thuật toán UCS
│   │       ├── cost_functions.py          # Các hàm đánh giá chi phí bước đi
│   │       ├── main_ucs.py                # Điểm chạy kiểm thử độc lập UCS
│   │       └── ucs.py                     # Lõi giải thuật tìm kiếm chi phí đều độc lập
│   └── gui/                               # Tầng giao diện đồ họa 3D (Panda3D Engine)
│       ├── __init__.py                    # Khởi tạo package gui
│       ├── action_plan.py                 # Phân rã hành động Core thành các pha hoạt cảnh (lăn, kích hoạt, kết thúc)
│       ├── advanced_contracts.py          # Dataclass mở rộng cho tầng đồ họa nâng cao (vật liệu, switch, cầu)
│       ├── advanced_fixtures.py           # Dữ liệu giả lập phục vụ kiểm thử và preview renderer nâng cao
│       ├── advanced_mesh_factory.py       # Tạo lưới hình học động (nút tròn, nút chéo, ô cam vỡ, cầu đóng/mở)
│       ├── advanced_preview.py            # Công cụ xem trước các thành phần đồ họa nâng cao độc lập
│       ├── advanced_renderer.py           # Bộ dựng hình nâng cao (quản lý node 3D switch, cầu, vật liệu PBR/shading)
│       ├── ambient.py                     # Hiệu ứng hạt nền lơ lửng (sao băng / lá bay theo theme màu)
│       ├── animation_contracts.py         # Định nghĩa các trạng thái, sự kiện và hợp đồng hoạt cảnh
│       ├── animation_effects.py           # Các hiệu ứng chuyển động phụ trợ (nảy, rung chấn, chấn động)
│       ├── animation_fixtures.py          # Dữ liệu mẫu (fixture) cho kiểm thử và preview hoạt cảnh
│       ├── animation_manager.py           # Bộ quản lý tiến trình hoạt cảnh lăn khối, trễ switch và mở cầu
│       ├── animation_math.py              # Tính toán góc xoay vật lý 90 độ và tâm xoay (pivot) khi lăn khối
│       ├── animation_preview.py           # Khung xem thử độc lập các chuỗi hoạt cảnh
│       ├── animation_timeline.py          # Dòng thời gian điều khiển frame hoạt cảnh
│       ├── app.py                         # Nền tảng cửa sổ ShowBase Panda3D cơ bản
│       ├── attract.py                     # Chế độ tự động demo màn chơi khi người dùng không tương tác (idle)
│       ├── audio.py                       # Trình quản lý phát âm thanh hiệu ứng (SFX) và nhạc nền (BGM)
│       ├── board_preview.py               # Công cụ xem trước bản đồ tĩnh
│       ├── camera.py                      # Hệ thống camera động: tự căn chỉnh góc nhìn bao quát toàn bộ map
│       ├── camera_views.py                # Chuyển đổi góc nhìn camera (Iso / Top / Follow), xoay orbit và map phím
│       ├── cinematic_bloom.py             # Bộ xử lý hậu kỳ ánh sáng phát quang (Cinematic Bloom) bằng GLSL
│       ├── contracts.py                   # Các dataclass định nghĩa dữ liệu hiển thị cơ bản (VisualBoard, VisualTile)
│       ├── controller.py                  # Điều phối gameplay: chơi tay, chọn level, chạy AI Solver & auto-replay
│       ├── dashboard_preview.py           # Công cụ xem trước giao diện Dashboard & HUD
│       ├── fall_math.py                   # Tính toán mô phỏng vật lý rơi tự do, lật nghiêng chân thực theo điểm tựa
│       ├── game_adapter.py                # Cầu nối chuyển đổi dữ liệu Core Board sang Advanced VisualBoard với ID ổn định
│       ├── game_app.py                    # Ứng dụng game hoàn chỉnh (kết nối Menu, Controller, Scene, Audio)
│       ├── game_scene.py                  # Quản lý scene 3D của level, bảo toàn scene khi tải thất bại
│       ├── geometry_math.py               # Các hàm phụ trợ tính toán tọa độ và kích thước hình học 3D
│       ├── hud.py                         # ViewModel và các thanh trạng thái hiển thị chỉ số HUD & Solver benchmark
│       ├── icons.py                       # Icon vector phẳng vẽ bằng hình học Panda3D cho các nút bấm HUD
│       ├── layout.py                      # Bố cục màn hình: phân chia vùng hiển thị 3D và thanh điều khiển HUD
│       ├── level_intro.py                 # Hoạt cảnh dâng sàn dạng sóng và thả khối khi vào màn chơi mới
│       ├── mechanics_guide.py             # Thanh công cụ dạng ray (guide rail) và thẻ hướng dẫn cơ chế trực quan
│       ├── mechanics_guide_data.py        # Cấu trúc dữ liệu và nội dung minh họa các cơ chế chơi trong game
│       ├── mesh_factory.py                # Tạo lưới hình học tĩnh (sàn thường, đích đến, khối chữ nhật)
│       ├── mouse_control.py               # Xử lý hover/click chuột trên bàn cờ và tương tác mũi tên 3D
│       ├── move_arrows.py                 # Mũi tên tương tác 3D quanh khối phục vụ điều khiển bằng chuột
│       ├── move_assist.py                 # Phân tích dự đoán bước đi tiếp theo (an toàn, nguy hiểm, rơi vực)
│       ├── profile.py                     # Lưu trữ hồ sơ người chơi (tiến trình level, sao, điểm, âm lượng)
│       ├── render_adapter.py              # Chuyển đổi dữ liệu từ Core Board sang định dạng cơ bản của renderer
│       ├── renderer.py                    # Bộ dựng hình 3D cơ bản (sàn tĩnh, ô động, khối)
│       ├── scene_lighting.py              # Thiết lập nguồn sáng Ambient, Directional, bóng đổ và đổi tông sáng theo theme
│       ├── scene_style.py                 # Nạp backdrop texture (day/night/temple), phủ UV, phối màu sàn và khối
│       ├── screens.py                     # Quản lý luồng giao diện menu (Main Menu, Level Select, Solvers, Settings)
│       ├── solver_worker.py               # Tiến trình chạy AI Solver nền (multiprocessing) có thể hủy bỏ tức thì
│       ├── temple_environment.py          # Dựng cảnh quan đền cổ xung quanh bàn cờ (thực vật, vách đá mép vực)
│       ├── tutorial.py                    # Popup overlay hướng dẫn điều khiển (bàn phím, chuột, HUD)
│       ├── ui_theme.py                    # Bảng màu, typography và kiểu dáng DirectGUI
│       ├── viewport.py                    # Quản lý khung nhìn Viewport của Panda3D
│       ├── visual_materials.py            # Quản lý vật liệu nâng cao (đá đền cổ, kim loại, dung nham, GLSL shaders)
│       └── visual_quality.py              # Cấu hình chất lượng đồ họa (High / Low, Bloom, Shaders, Antialiasing)
├── tests/                                 # Bộ kiểm thử tự động (Unit Tests & Integration Tests)
│   ├── fixtures/                          # Dữ liệu cố định phục vụ kiểm thử hồi quy
│   │   └── mechanics/                     # 11 màn chơi kiểm thử cơ chế cố định (độc lập với catalog levels)
│   │       ├── level_01.json … level_10_cube_fragile.json
│   │       ├── level_11_advanced_sandbox.json
│   │       └── README.md                  # Hướng dẫn và cam kết tính ổn định của fixture kiểm thử
│   ├── game_integration_support.py        # Hỗ trợ giả lập cho kiểm thử tích hợp game
│   ├── gui_animation_support.py           # Dữ liệu giả lập (fixture) cho kiểm thử hoạt cảnh
│   ├── gui_task_support.py                # Hỗ trợ quản lý tác vụ (task) Panda3D trong test
│   ├── solver_test_support.py             # Dữ liệu và hàm hỗ trợ kiểm thử các thuật toán AI
│   ├── test_astar.py                      # Kiểm thử thuật toán A*
│   ├── test_base_solver.py                # Kiểm thử lớp cơ sở đo đạc hiệu năng benchmark
│   ├── test_bfs.py                        # Kiểm thử thuật toán BFS
│   ├── test_board.py                      # Kiểm thử logic bàn cờ, va chạm và di chuyển
│   ├── test_bridge_switches.py            # Kiểm thử cơ chế công tắc soft/heavy và đóng/mở cầu
│   ├── test_game_adapter.py               # Kiểm thử bộ chuyển đổi dữ liệu game adapter
│   ├── test_game_integration.py           # Kiểm thử tích hợp toàn diện luồng game
│   ├── test_game_menu_lifecycle.py        # Kiểm thử vòng đời các màn hình menu
│   ├── test_game_ui_state.py              # Kiểm thử trạng thái giao diện UI
│   ├── test_greedy.py                     # Kiểm thử thuật toán Greedy Best-First Search
│   ├── test_gui_advanced_contracts.py     # Kiểm thử contracts nâng cao của GUI
│   ├── test_gui_advanced_geometry.py      # Kiểm thử hình học nâng cao
│   ├── test_gui_advanced_preview.py       # Kiểm thử preview nâng cao
│   ├── test_gui_advanced_renderer.py      # Kiểm thử bộ dựng hình nâng cao
│   ├── test_gui_animation_contracts.py    # Kiểm thử contracts của hoạt cảnh
│   ├── test_gui_animation_effects.py      # Kiểm thử hiệu ứng hoạt cảnh
│   ├── test_gui_animation_manager.py      # Kiểm thử bộ quản lý hoạt cảnh
│   ├── test_gui_animation_math.py         # Kiểm thử toán học xoay và lăn khối
│   ├── test_gui_animation_preview.py      # Kiểm thử preview hoạt cảnh
│   ├── test_gui_camera.py                 # Kiểm thử camera động
│   ├── test_gui_contracts.py              # Kiểm thử contracts cơ bản
│   ├── test_gui_foundation.py             # Kiểm thử nền tảng Panda3D app
│   ├── test_gui_geometry_math.py          # Kiểm thử tính toán tọa độ hình học
│   ├── test_gui_hud.py                    # Kiểm thử giao diện HUD
│   ├── test_gui_layout.py                 # Kiểm thử bố cục layout
│   ├── test_gui_lighting.py               # Kiểm thử ánh sáng và bóng đổ
│   ├── test_gui_renderer.py               # Kiểm thử bộ dựng hình cơ bản
│   ├── test_gui_render_adapter.py         # Kiểm thử adapter dữ liệu hiển thị
│   ├── test_gui_stage3_6_integration.py   # Kiểm thử tích hợp giai đoạn Stage 3.6
│   ├── test_gui_stage3_6_quality.py       # Kiểm thử chất lượng hiển thị Stage 3.6
│   ├── test_gui_stage3_6_stability.py     # Kiểm thử tính ổn định Stage 3.6
│   ├── test_gui_viewport.py               # Kiểm thử viewport và aspect ratio
│   ├── test_mechanical_animation.py       # Kiểm thử hoạt cảnh cơ chế switch, cầu và phân tách
│   ├── test_mechanics_guide.py            # Kiểm thử hệ thống giao diện hướng dẫn cơ chế
│   ├── test_mouse_control.py              # Kiểm thử điều khiển chuột và bắt sự kiện
│   ├── test_move_assist.py                # Kiểm thử hệ thống phân tích và hỗ trợ di chuyển
│   ├── test_physical_fall.py              # Kiểm thử logic tính toán rơi vật lý theo điểm tựa
│   ├── test_solver_worker.py              # Kiểm thử tiến trình nền solver worker & tính năng hủy
│   ├── test_state.py                      # Kiểm thử trạng thái khối Bloxorz
│   ├── test_surface_animation_theme.py    # Kiểm thử hoạt cảnh bề mặt theo chủ đề giao diện
│   ├── test_targeted_falling_ui.py        # Kiểm thử tích hợp hoạt cảnh rơi và UI
│   └── test_visual_overhaul.py            # Kiểm thử tính toàn vẹn hệ thống đồ họa nâng cấp
├── tools/                                 # Công cụ kiểm thử nhanh (Smoke Tests) & tiền xử lý Asset
│   ├── animation_capture.py               # Chụp chuỗi khung hình hoạt cảnh phục vụ kiểm thử trực quan
│   ├── build_visual_materials.py          # Sinh texture vật liệu PBR (đá nứt, dung nham, kim loại)
│   ├── game_integration_smoke.py          # Smoke test tích hợp toàn diện game (18 màn chơi × 6 solvers)
│   ├── gui_stage3_6_smoke.py              # Smoke test tầng Renderer và HUD cơ bản
│   ├── gui_stage4_smoke.py                # Smoke test tầng Advanced Renderer và vật liệu
│   ├── gui_stage5_smoke.py                # Smoke test hệ thống hoạt cảnh liên tục
│   ├── jungle_motion_capture.py           # Ghi nhận chuyển động và hoạt cảnh môi trường Jungle Temple
│   ├── jungle_quality_smoke.py            # Smoke test kiểm định chất lượng hình ảnh môi trường Đền Cổ
│   ├── jungle_solver_smoke.py             # Smoke test chạy solver AI trên môi trường đồ họa mới
│   ├── jungle_visual_capture.py           # Chụp ảnh đối chiếu trực quan đồ họa Jungle Temple
│   ├── mechanics_guide_smoke.py           # Smoke test thanh tương tác và thẻ hướng dẫn cơ chế
│   ├── move_assist_smoke.py               # Smoke test hệ thống hỗ trợ di chuyển và cảnh báo
│   ├── native_input.py                    # Tiện ích giả lập tương tác phím và chuột native
│   ├── physical_fall_smoke.py             # Smoke test hoạt cảnh rơi vật lý chân thực theo điểm tựa
│   ├── prepare_toolbar_robot.py           # Tiền xử lý tách nền và căn chỉnh icon AI Robot cho toolbar
│   ├── split_mouse_smoke.py               # Smoke test cơ chế tách khối và điều khiển tương tác chuột
│   └── targeted_ui_smoke.py               # Smoke test kiểm tra UI theo theme và kiểm chứng lỗi hiển thị
├── main.py                                # Điểm khởi chạy chính toàn bộ dự án (Game 3D + AI Visualizer)
├── requirements.txt                       # Danh mục các thư viện phụ thuộc (Panda3D, Pytest, ...)
├── STRUCTURE.md                           # Tài liệu cấu trúc thư mục này
└── README.md                              # Hướng dẫn cài đặt môi trường, quy ước git và hướng dẫn sử dụng
```

---

## 2. Chi tiết vai trò từng phân hệ

### 2.1. Điểm khởi chạy ([main.py](file:///d:/Tai/CSAI/Bloxorz_Solver/main.py))
- Khởi động toàn bộ giao diện 3D trực quan thông qua [game_app.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_app.py).
- Tích hợp cơ chế tự động phát hiện và chuyển tiếp môi trường ảo `.venv` nếu chưa kích hoạt, đảm bảo đầy đủ thư viện `panda3d` khi thực thi.

### 2.2. Tầng Lõi Logic (`src/core/`)
- **[board.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/core/board.py)**: Đọc cấu hình JSON bản đồ, quản lý lưới tọa độ 2D, xử lý các trường hợp lăn khối Bloxorz, cơ chế kích hoạt công tắc tròn (`soft`), công tắc chéo (`heavy`), công tắc phân tách (`split` `( )`), tái hợp khối (Merge), đóng/mở cầu và ô cam dễ vỡ (`fragile`).
- **[state.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/core/state.py)**: Định nghĩa lớp trạng thái `BloxorzState`, lưu trữ tư thế khối (`STANDING`, `HORIZONTAL`, `VERTICAL`), vị trí tọa độ, trạng thái các cây cầu (`bridges_state`) và tọa độ 2 khối 1x1 khi bị tách.

### 2.3. Tầng Thuật toán AI (`src/solvers/`)
- Triển khai 6 giải thuật tìm kiếm trạng thái kinh điển:
  - **A\*** ([astar.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/astar.py)): Tìm kiếm tối ưu kết hợp hàm heuristic Manhattan/khoảng cách ước lượng đến đích.
  - **BFS** ([bfs.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/bfs.py)): Tìm kiếm theo chiều rộng (đảm bảo số bước đi tối ưu).
  - **DFS** ([dfs.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/dfs.py)): Tìm kiếm theo chiều sâu.
  - **Greedy Best-First** ([greedy.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/greedy.py)): Tìm kiếm tham lam theo hàm đánh giá khoảng cách.
  - **IDS** ([ids.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/ids.py)): Tìm kiếm sâu dần kết hợp ưu điểm của BFS và DFS.
  - **UCS** ([ucs.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/ucs.py) & [UCS_Algorithm/](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/UCS_Algorithm)): Tìm kiếm chi phí đều với trọng số bước đi.
- Tất cả thuật toán kế thừa [base_solver.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/base_solver.py) để tự động ghi nhận 4 chỉ số thực nghiệm chuẩn:
  1. *Thời gian tìm kiếm (Search Time - ms)*.
  2. *Dung lượng RAM tối đa (Peak Memory - MB)*.
  3. *Số trạng thái đã mở (Expanded Nodes)*.
  4. *Độ dài đường đi giải pháp (Solution Length)*.

### 2.4. Tầng Giao diện 3D & Hoạt cảnh (`src/gui/`)
Xây dựng trên nền tảng **Panda3D Engine**, được tổ chức thành các nhóm chức năng mạch lạc:

- **Game Flow, Quản lý Màn hình & Tích hợp**:
  - [game_app.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_app.py): Điểm khởi tạo và vòng lặp ứng dụng game chính; điều phối cửa sổ, bộ chuyển đổi camera, thanh toolbar và popup trợ giúp.
  - [screens.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/screens.py): Quản lý luồng giao diện menu (Main Menu, Level Select, Solvers Menu, Settings, Victory, Defeat) và đồng bộ chủ đề sáng/tối sang toàn bộ đối tượng 3D (backdrop, đèn, sàn, khối).
  - [controller.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/controller.py): Điều phối gameplay: tiếp nhận tương tác, chọn level, chạy AI Solver và tự động phát lại (auto-replay).
  - [game_scene.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_scene.py): Quản lý vòng đời scene 3D của level, bảo toàn bàn chơi hiện tại nếu tải level mới gặp lỗi.
  - [game_adapter.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_adapter.py): Cầu nối chuyển đổi dữ liệu từ Core Board sang định dạng `VisualBoard` nâng cao với định danh (ID) ổn định cho khối, switch và cầu.
  - [solver_worker.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/solver_worker.py): Chạy các thuật toán AI trong tiến trình nền độc lập (`multiprocessing`), hỗ trợ hủy tác vụ tức thì mà không làm đóng băng luồng giao diện Panda3D.
  - [profile.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/profile.py): Lưu trữ tiến trình màn chơi (sao, điểm) và cài đặt người dùng.

- **Tương tác, Hỗ trợ Gameplay & HUD**:
  - [hud.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/hud.py): ViewModel và thanh hiển thị chỉ số HUD (bước đi, thời gian, benchmark AI, các nút bấm thao tác kèm icon vector/texture và tooltip chú thích).
  - [icons.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/icons.py): Thư viện dựng icon vector phẳng (Exit, Restart, AI Sparkle, View, Help, Play, Pause, Step) bằng lưới tam giác hình học Panda3D thuần túy.
  - [mechanics_guide.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mechanics_guide.py) & [mechanics_guide_data.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mechanics_guide_data.py): Thanh công cụ dạng ray (guide rail) và thẻ hiển thị hướng dẫn trực quan từng loại ô gạch, switch và quy tắc chơi.
  - [move_assist.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/move_assist.py): Module phân tích hỗ trợ di chuyển, dự đoán trước tính an toàn/nguy hiểm/rơi vực của từng nước đi.
  - [move_arrows.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/move_arrows.py) & [mouse_control.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mouse_control.py): Hiển thị mũi tên 3D xung quanh khối và xử lý sự kiện hover/click chuột trên bàn cờ.
  - [tutorial.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/tutorial.py): Quản lý popup overlay hướng dẫn chơi (`TutorialOverlay`), liệt kê đầy đủ phím tắt bàn phím và thao tác chuột.

- **Dựng hình 3D, Môi trường & Vật liệu**:
  - [renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/renderer.py) & [advanced_renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_renderer.py): Bộ dựng hình 3D (sàn tĩnh, ô động, switch, cầu, vật liệu PBR/shading).
  - [mesh_factory.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mesh_factory.py) & [advanced_mesh_factory.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_mesh_factory.py): Tạo lưới hình học tĩnh và động (ô cam vỡ, nút bấm tròn/chéo, cầu gập).
  - [visual_materials.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/visual_materials.py): Nạp và quản lý texture maps bề mặt (đá đền cổ, dung nham, kim loại, ô cam) và các shader GLSL tương ứng.
  - [visual_quality.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/visual_quality.py): Quản lý cấu hình mức đồ họa (High / Low), kiểm soát bật/tắt bloom, shaders chi tiết và khử răng cưa.
  - [temple_environment.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/temple_environment.py): Tự động sinh cảnh quan đền cổ xung quanh bàn cờ (nền móng đá, rêu phong, thực vật treo mép vực).

- **Hệ thống Hoạt cảnh & Vật lý**:
  - [action_plan.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/action_plan.py): Phân rã một hành động từ Core thành chuỗi các pha hoạt cảnh rõ ràng: lăn khối, kích hoạt cơ chế và hiệu ứng kết thúc.
  - [animation_manager.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_manager.py): Quản lý tiến trình hoạt cảnh lăn, rơi tự do, mở cầu mượt mà.
  - [animation_math.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_math.py): Tính toán góc xoay vật lý 90 độ và điểm tựa (pivot) lăn khối.
  - [fall_math.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/fall_math.py): Tính toán mô phỏng vật lý khối rơi chân thực khi sẩy chân (góc nghiêng tiếp xúc mép sàn, gia tốc rơi tự do và fade out).
  - [animation_effects.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_effects.py): Hiệu ứng chuyển động nảy, vỡ nát, rung chấn.
  - [animation_contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_contracts.py) & [animation_timeline.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_timeline.py): Định nghĩa hợp đồng dữ liệu và dòng thời gian hoạt cảnh.
  - [level_intro.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/level_intro.py): Hoạt cảnh dâng sàn dạng sóng và thả khối khi vào màn chơi mới.

- **Hậu kỳ, Môi trường & Hệ thống Camera 3D**:
  - [cinematic_bloom.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/cinematic_bloom.py): Hiệu ứng hậu kỳ phát quang điện ảnh (warm-emission bloom) áp dụng trước khi dựng GUI.
  - [camera.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/camera.py): Tính toán bounding box và thông số góc nhìn camera bao quát bản đồ.
  - [camera_views.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/camera_views.py): Quản lý chuyển đổi các góc nhìn camera (`Iso` chéo truyền thống, `Top` nhìn từ trên xuống, `Follow` bám theo khối xoay orbit 75°), hỗ trợ phím `C` và nút HUD, đồng thời tự động tái ánh xạ phím điều khiển thích ứng với hướng camera trên màn hình.
  - [scene_lighting.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_lighting.py): Thiết lập nguồn sáng Ambient/Directional, đổ bóng và tự động chuyển đổi tông màu sáng ấm/lạnh theo Light/Dark/Temple theme.
  - [scene_style.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_style.py): Quản lý nền đồ họa không gian (load backdrop texture từ `assets/backgrounds/`), tính toán UV tự co dãn (cover) theo aspect ratio camera.
  - [ambient.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ambient.py): Hạt nền lơ lửng (sao băng, đom đóm hoặc lá rơi theo chủ đề màu).
  - [audio.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/audio.py): Quản lý phát hiệu ứng âm thanh và nhạc nền.
  - [attract.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/attract.py): Tự động minh họa đường đi sau thời gian rảnh rỗi (idle demo).
  - [layout.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/layout.py) & [viewport.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/viewport.py): Quản lý tỷ lệ màn hình và phân vùng hiển thị 3D / HUD.
  - [ui_theme.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ui_theme.py): Bảng màu, typography và kiểu dáng DirectGUI.

- **Công cụ Xem trước & Hỗ trợ Kiểm thử**:
  - [contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/contracts.py) & [advanced_contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_contracts.py): Định nghĩa cấu trúc dữ liệu hiển thị.
  - [render_adapter.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/render_adapter.py): Chuyển đổi dữ liệu Core Board sang định dạng VisualBoard cơ bản.
  - [board_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/board_preview.py), [dashboard_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/dashboard_preview.py), [advanced_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_preview.py), [animation_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_preview.py): Các công cụ preview chạy độc lập từng module.
  - [advanced_fixtures.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_fixtures.py) & [animation_fixtures.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_fixtures.py): Dữ liệu mẫu phục vụ kiểm thử và preview.

### 2.5. Tầng Tài nguyên & Cấu hình màn chơi (`assets/`, `music/`, `levels/`)
- **[levels/](file:///d:/Tai/CSAI/Bloxorz_Solver/levels/)**: Danh mục 18 màn chơi JSON (`level_01.json` đến `level_18.json`) được thiết kế chuẩn mực tăng dần độ khó, bao phủ toàn bộ cơ chế của Bloxorz (ô thường, ô cam vỡ, công tắc tròn/chéo, cầu toggle/permanent, công tắc phân tách khối 1x1).
- **[assets/audio/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/audio/)**: Hiệu ứng âm thanh WAV tương tác: click, fall, goal, music, roll.
- **[assets/backgrounds/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/backgrounds/)**: Bộ ảnh nền backdrop 3D chất lượng cao gồm `day.png` (ban ngày), `night.png` (ban đêm/vũ trụ), `jungle-temple.png` (đền cổ nhiệt đới) và `winter-temple.png` (đền tuyết mùa đông).
- **[assets/icons/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/icons/)**: Biểu tượng đồ họa cho toolbar HUD (gồm `ai-robot.png` chuẩn RGBA 228×274 và ảnh gốc).
- **[assets/materials/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/materials/)**: Texture maps PBR cho bề mặt sàn đá (`stone-dark.png`, `stone-light.png`, `stone-height.png`), ô vỡ (`fragile.png`), dung nham phát sáng (`magma.png`, `magma-height.png`), kim loại (`metal.png`) và đá cổ đền (`temple-stone.png`).
- **[assets/shaders/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/shaders/)**: Hệ thống shader GLSL phục vụ hiệu ứng ánh sáng bề mặt đền cổ (`temple.vert`, `temple.frag`) và hiệu ứng hậu kỳ Cinematic Bloom (`bloom.vert`, `bloom-extract.frag`, `bloom-composite.frag`).
- **[music/](file:///d:/Tai/CSAI/Bloxorz_Solver/music/)**: Nhạc nền MP3 bổ sung cho game (`1.mp3`, `2.mp3`).

### 2.6. Tầng Tài liệu & Bộ kiểm thử (`docs/`, `tests/`, `tools/`)
- **[docs/](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/)**: Báo cáo lý thuyết thuật toán ([BASELINE.md](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/BASELINE.md), [BFS.md](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/BFS.md)) và hệ thống tài liệu đặc tả kiến trúc, hợp đồng đồ họa, báo cáo nâng cấp đồ họa Đền Cổ, vật lý rơi và cơ chế hướng dẫn ([docs/gui/](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/gui/)).
- **[tests/](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/)**: Hệ thống kiểm thử tự động toàn diện:
  - Logic cốt lõi bàn cờ, trạng thái khối, 6 thuật toán AI, quản lý solver worker nền.
  - Toàn bộ các tầng giao diện Panda3D, hợp đồng dữ liệu, camera, viewport, HUD, DirectGUI.
  - Hoạt cảnh cơ chế, mô phỏng rơi vật lý ([test_physical_fall.py](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/test_physical_fall.py)), hỗ trợ di chuyển ([test_move_assist.py](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/test_move_assist.py)), hướng dẫn cơ chế ([test_mechanics_guide.py](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/test_mechanics_guide.py)) và nâng cấp đồ họa trực quan ([test_visual_overhaul.py](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/test_visual_overhaul.py)).
  - [tests/fixtures/mechanics/](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/fixtures/mechanics/): Bộ 11 màn chơi mẫu cố định dành riêng cho kiểm thử cơ chế ổn định mà không phụ thuộc vào sự thay đổi số lượng màn chơi trong catalog sản phẩm.
- **[tools/](file:///d:/Tai/CSAI/Bloxorz_Solver/tools/)**: Tập hợp 17 công cụ hỗ trợ kiểm thử khói (Smoke Tests), chụp khung hình hoạt cảnh (capture tools), kiểm định chất lượng đồ họa và tiền xử lý asset tự động.

---

## 3. Cách thức vận hành dự án

### Khởi chạy ứng dụng Game 3D & Trình diễn Solvers
```bash
python main.py
```

### Chạy toàn bộ kiểm thử tự động (Unit Tests)
```bash
pytest tests/
```

### Chạy kiểm thử khói tích hợp (Smoke Tests & QA Tools)
- Kiểm thử tích hợp toàn diện giao diện native và kiểm tra 18 màn chơi × 6 solver:
  ```bash
  python -m tools.game_integration_smoke
  ```
- Kiểm thử hệ thống hỗ trợ di chuyển và cảnh báo nước đi nguy hiểm:
  ```bash
  python -m tools.move_assist_smoke
  ```
- Kiểm thử thanh ray hướng dẫn cơ chế gameplay (Mechanics Guide):
  ```bash
  python -m tools.mechanics_guide_smoke
  ```
- Kiểm thử mô phỏng vật lý rơi tự do theo điểm tựa mép sàn:
  ```bash
  python -m tools.physical_fall_smoke
  ```
- Kiểm định chất lượng hình ảnh môi trường Đền Cổ (Jungle Temple):
  ```bash
  python -m tools.jungle_quality_smoke
  ```
- Kiểm thử chạy solver AI trên môi trường đồ họa mới:
  ```bash
  python -m tools.jungle_solver_smoke
  ```
- Kiểm tra giao diện theo chủ đề và kiểm chứng hiển thị:
  ```bash
  python -m tools.targeted_ui_smoke
  ```
- Kiểm thử cơ chế phân tách khối và điều khiển tương tác chuột:
  ```bash
  python -m tools.split_mouse_smoke
  ```
- Tái tạo bộ textures vật liệu PBR bằng thuật toán:
  ```bash
  python -m tools.build_visual_materials
  ```
