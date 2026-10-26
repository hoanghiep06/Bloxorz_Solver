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
│   └── backgrounds/                       # Ảnh nền panorama/backdrop chất lượng cao cho không gian 3D
│       ├── day.png                        # Ảnh nền ban ngày (chủ đề Light Theme)
│       └── night.png                      # Ảnh nền ban đêm vũ trụ (chủ đề Dark Theme)
├── docs/                                  # Tài liệu kỹ thuật, báo cáo & đặc tả thiết kế
│   ├── BASELINE.md                        # Cơ sở lý thuyết thuật toán tìm kiếm
│   ├── BFS.md                             # Báo cáo chuyên sâu thuật toán BFS
│   └── gui/                               # Đặc tả kiến trúc hệ thống giao diện 3D Panda3D
│       ├── ASSET_CREDITS.md               # Nguồn gốc tài nguyên và bản quyền
│       ├── BASIC_RENDERER_API.md          # Tài liệu API cho Renderer cơ bản
│       ├── GAME_INTEGRATION.md            # Tài liệu tích hợp game native, luồng điều khiển & solver worker
│       ├── GEOMETRY_TILE_SPEC.md          # Đặc tả hình học ô gạch và switch
│       ├── LAYOUT_CAMERA_SPEC.md          # Đặc tả camera và phân vùng viewport
│       ├── README.md                      # Tổng quan kiến trúc phân tầng module GUI
│       ├── RENDER_CONTRACT.md             # Hợp đồng dữ liệu tầng đồ họa
│       ├── STAGE*_*.md                    # Đặc tả chi tiết các giai đoạn phát triển GUI (Stage 2 -> Stage 5)
│       ├── TEAM_INTEGRATION_REVIEW.md     # Đánh giá và ghi chú tích hợp liên nhóm
│       ├── TEST_PLAN.md                   # Kế hoạch kiểm thử tự động giao diện
│       └── VISUAL_SPEC.md                 # Quy chuẩn thẩm mỹ thị giác và vật liệu
├── levels/                                # Dữ liệu bản đồ các màn chơi (JSON)
│   ├── level_01.json                      # Màn 1: Giới thiệu di chuyển khối cơ bản
│   ├── level_02_fragile.json              # Màn 2: Cơ chế ô cam dễ vỡ (fragile tile)
│   ├── level_03_soft_bridge.json          # Màn 3: Nút tròn (soft switch) và cầu đóng/mở
│   ├── level_04_heavy_bridge.json         # Màn 4: Nút chéo (heavy switch) yêu cầu đứng thẳng
│   ├── level_05_split.json                # Màn 5: Nút phân tách khối (split switch) thành 2 khối 1x1
│   ├── level_06_combined.json             # Màn 6: Kết hợp đa công tắc, ô cam và cầu
│   ├── level_07_fragile_detour.json       # Màn 7: Đường vòng lắt léo với mật độ ô vỡ cao
│   ├── level_08_toggle_bridge.json        # Màn 8: Cơ chế chuyển đổi cầu bật/tắt luân phiên
│   ├── level_09_permanent_bridge.json     # Màn 9: Cầu kích hoạt một chiều vĩnh viễn
│   └── level_10_cube_fragile.json         # Màn 10: Phối hợp khối con và ô mỏng manh
├── music/                                 # Nhạc nền bổ sung định dạng MP3
│   ├── 1.mp3                              # Nhạc nền chủ đề 1
│   └── 2.mp3                              # Nhạc nền chủ đề 2
├── src/                                   # Toàn bộ mã nguồn chính của dự án
│   ├── core/                              # Tầng lõi trò chơi (Logic & Quy tắc vật lý)
│   │   ├── board.py                       # Quản lý bản đồ, transition model, xử lý switch/cầu/tách/nhập khối
│   │   └── state.py                       # Biểu diễn trạng thái BloxorzState (tư thế, tọa độ, khối tách, trạng thái cầu)
│   ├── solvers/                           # Tầng thuật toán tìm kiếm AI (AI Solvers)
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
│       ├── action_plan.py                 # Phân rã hành động Core thành các pha hoạt cảnh chi tiết (lăn, kích hoạt, kết thúc)
│       ├── advanced_contracts.py          # Dataclass mở rộng cho tầng đồ họa nâng cao (vật liệu, switch, cầu)
│       ├── advanced_fixtures.py           # Dữ liệu giả lập phục vụ kiểm thử và preview renderer nâng cao
│       ├── advanced_mesh_factory.py       # Tạo lưới hình học động (nút tròn, nút chéo, ô cam vỡ, cầu đóng/mở)
│       ├── advanced_preview.py            # Công cụ xem trước các thành phần đồ họa nâng cao độc lập
│       ├── advanced_renderer.py           # Bộ dựng hình nâng cao (quản lý node 3D switch, cầu, vật liệu PBR/shading)
│       ├── ambient.py                     # Hiệu ứng hạt nền lơ lửng (sao băng / lá bay theo theme màu)
│       ├── animation_contracts.py         # Định nghĩa các trạng thái, sự kiện và hợp đồng hoạt cảnh
│       ├── animation_effects.py           # Các hiệu ứng chuyển động phụ trợ (nảy, rơi tự do, chấn động)
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
│       ├── contracts.py                   # Các dataclass định nghĩa dữ liệu hiển thị cơ bản (VisualBoard, VisualTile)
│       ├── controller.py                  # Điều phối gameplay: chơi tay, chọn level, chạy AI Solver & auto-replay
│       ├── dashboard_preview.py           # Công cụ xem trước giao diện Dashboard & HUD
│       ├── game_adapter.py                # Cầu nối chuyển đổi dữ liệu Core Board sang Advanced VisualBoard với ID ổn định
│       ├── game_app.py                    # Ứng dụng game hoàn chỉnh (kết nối Menu, Controller, Scene, Audio)
│       ├── game_scene.py                  # Quản lý scene 3D của level, bảo toàn scene khi tải thất bại
│       ├── geometry_math.py               # Các hàm phụ trợ tính toán tọa độ và kích thước hình học 3D
│       ├── hud.py                         # ViewModel và các thanh trạng thái hiển thị chỉ số HUD & Solver benchmark
│       ├── icons.py                       # Icon vector phẳng vẽ bằng hình học Panda3D cho các nút bấm HUD
│       ├── layout.py                      # Bố cục màn hình: phân chia vùng hiển thị 3D và thanh điều khiển HUD
│       ├── level_intro.py                 # Hoạt cảnh dâng sàn dạng sóng và thả khối khi vào màn chơi mới
│       ├── mesh_factory.py                # Tạo lưới hình học tĩnh (sàn thường, đích đến, khối chữ nhật)
│       ├── mouse_control.py               # Xử lý hover/click chuột trên bàn cờ và tương tác mũi tên 3D
│       ├── move_arrows.py                 # Mũi tên tương tác 3D quanh khối phục vụ điều khiển bằng chuột
│       ├── profile.py                     # Lưu trữ hồ sơ người chơi (tiến trình level, sao, điểm, âm lượng)
│       ├── render_adapter.py              # Chuyển đổi dữ liệu từ Core Board sang định dạng cơ bản của renderer
│       ├── renderer.py                    # Bộ dựng hình 3D cơ bản (sàn tĩnh, ô động, khối)
│       ├── scene_lighting.py              # Thiết lập nguồn sáng Ambient, Directional, bóng đổ và đổi tông sáng theo theme
│       ├── scene_style.py                 # Nạp backdrop texture (day/night), phủ kín UV, phối màu sàn, khối và sương mù
│       ├── screens.py                     # Quản lý luồng giao diện menu (Main Menu, Level Select, Solvers, Settings)
│       ├── solver_worker.py               # Tiến trình chạy AI Solver nền (multiprocessing) có thể hủy bỏ mà không treo GUI
│       ├── tutorial.py                    # Popup overlay hướng dẫn điều khiển (bàn phím, chuột, HUD)
│       ├── ui_theme.py                    # Bảng màu, typography và kiểu dáng DirectGUI
│       └── viewport.py                    # Quản lý khung nhìn Viewport của Panda3D
├── tests/                                 # Bộ kiểm thử tự động (Unit Tests & Integration Tests)
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
│   ├── test_mouse_control.py              # Kiểm thử điều khiển chuột và bắt sự kiện
│   ├── test_solver_worker.py              # Kiểm thử tiến trình nền solver worker & tính năng hủy
│   └── test_state.py                      # Kiểm thử trạng thái khối Bloxorz
├── tools/                                 # Công cụ chạy kiểm thử nhanh (Smoke Tests)
│   ├── game_integration_smoke.py          # Smoke test tích hợp toàn diện game (kiểm tra 10 levels × 6 solvers)
│   ├── gui_stage3_6_smoke.py              # Smoke test tầng Renderer và HUD cơ bản
│   ├── gui_stage4_smoke.py                # Smoke test tầng Advanced Renderer và vật liệu
│   ├── gui_stage5_smoke.py                # Smoke test hệ thống hoạt cảnh liên tục
│   └── split_mouse_smoke.py               # Smoke test cơ chế tách khối và điều khiển tương tác chuột
├── main.py                                # Điểm khởi chạy chính toàn bộ dự án (Game 3D + AI Visualizer)
├── requirements.txt                       # Danh mục các thư viện phụ thuộc (Panda3D, Pygame, ...)
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
  - [game_app.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_app.py): Điểm khởi tạo và vòng lặp ứng dụng game chính; điều phối cửa sổ, bộ chuyển đổi camera và popup trợ giúp.
  - [screens.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/screens.py): Quản lý luồng giao diện menu (Main Menu, Level Select, Solvers Menu, Settings, Victory, Defeat) và đồng bộ chủ đề sáng/tối sang toàn bộ đối tượng 3D (backdrop, đèn, sàn, khối).
  - [controller.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/controller.py): Điều phối gameplay: tiếp nhận tương tác, chọn level, chạy AI Solver và tự động phát lại (auto-replay).
  - [game_scene.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_scene.py): Quản lý vòng đời scene 3D của level, bảo toàn bàn chơi hiện tại nếu tải level mới gặp lỗi.
  - [game_adapter.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_adapter.py): Cầu nối chuyển đổi dữ liệu từ Core Board sang định dạng `VisualBoard` nâng cao với định danh (ID) ổn định cho khối, switch và cầu.
  - [action_plan.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/action_plan.py): Phân rã một hành động từ Core thành chuỗi các pha hoạt cảnh rõ ràng: lăn khối, kích hoạt cơ chế và hiệu ứng kết thúc.
  - [solver_worker.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/solver_worker.py): Chạy các thuật toán AI trong tiến trình nền độc lập (`multiprocessing`), hỗ trợ hủy tác vụ tức thì mà không làm đóng băng luồng giao diện Panda3D.
  - [tutorial.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/tutorial.py): Quản lý popup overlay hướng dẫn chơi (`TutorialOverlay`), liệt kê đầy đủ phím tắt bàn phím, thao tác chuột và mô tả các nút bấm HUD; tự động tạm dừng/khôi phục input điều khiển.
  - [profile.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/profile.py): Lưu trữ tiến trình màn chơi (sao, điểm) và cài đặt người dùng.
- **Tương tác & Hiệu ứng sinh động**:
  - [hud.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/hud.py): ViewModel và thanh hiển thị chỉ số HUD (bước đi, thời gian, benchmark AI, các nút bấm thao tác kèm icon vector và tooltip chú thích).
  - [icons.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/icons.py): Thư viện dựng icon vector phẳng (Exit, Restart, AI Sparkle, View, Help, Play, Pause, Step) bằng lưới tam giác hình học Panda3D thuần túy, không phụ thuộc font hay file ảnh ngoài.
  - [move_arrows.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/move_arrows.py) & [mouse_control.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mouse_control.py): Hiển thị mũi tên 3D xung quanh khối và xử lý sự kiện hover/click chuột trên bàn cờ.
  - [level_intro.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/level_intro.py): Hoạt cảnh dâng sàn dạng sóng và thả khối khi vào màn chơi mới.
  - [ambient.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ambient.py): Hạt nền lơ lửng (sao băng hoặc lá rơi theo chủ đề màu).
  - [audio.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/audio.py): Quản lý phát hiệu ứng âm thanh và nhạc nền.
  - [attract.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/attract.py): Tự động minh họa đường đi sau thời gian rảnh rỗi (idle demo).
  - [ui_theme.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ui_theme.py): Bảng màu, typography và kiểu dáng DirectGUI.
- **Dựng hình 3D & Animation**:
  - [renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/renderer.py) & [advanced_renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_renderer.py): Bộ dựng hình 3D (sàn tĩnh, ô động, switch, cầu, vật liệu PBR/shading).
  - [mesh_factory.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mesh_factory.py) & [advanced_mesh_factory.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_mesh_factory.py): Tạo lưới hình học tĩnh và động (ô cam vỡ, nút bấm tròn/chéo, cầu gập).
  - [animation_manager.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_manager.py): Quản lý tiến trình hoạt cảnh lăn, rơi tự do, mở cầu mượt mà.
  - [animation_effects.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_effects.py): Hiệu ứng chuyển động nảy, vỡ nát, rung chấn.
  - [animation_math.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_math.py): Tính toán góc xoay vật lý 90 độ và điểm tựa (pivot) lăn khối.
  - [animation_contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_contracts.py) & [animation_timeline.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_timeline.py): Định nghĩa hợp đồng dữ liệu và dòng thời gian hoạt cảnh.
- **Môi trường & Hệ thống Camera 3D**:
  - [camera.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/camera.py): Tính toán bounding box và thông số góc nhìn camera bao quát bản đồ.
  - [camera_views.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/camera_views.py): Quản lý chuyển đổi các góc nhìn camera (`Iso` chéo truyền thống, `Top` nhìn từ trên xuống, `Follow` bám theo khối xoay orbit 75°), hỗ trợ phím `C` và nút HUD, đồng thời tự động tái ánh xạ phím điều khiển thích ứng với hướng camera trên màn hình.
  - [scene_lighting.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_lighting.py): Thiết lập nguồn sáng Ambient/Directional, đổ bóng và tự động chuyển đổi tông màu sáng ấm/lạnh theo Light/Dark theme.
  - [scene_style.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_style.py): Quản lý nền đồ họa không gian (load texture ảnh từ `assets/backgrounds/` hoặc gradient dự phòng), tính toán UV tự co dãn (cover) theo aspect ratio camera, tint màu sàn và khối theo chủ đề.
  - [layout.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/layout.py) & [viewport.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/viewport.py): Quản lý tỷ lệ màn hình và phân vùng hiển thị 3D / HUD.
- **Công cụ Xem trước & Hỗ trợ Kiểm thử**:
  - [contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/contracts.py) & [advanced_contracts.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_contracts.py): Định nghĩa cấu trúc dữ liệu hiển thị.
  - [render_adapter.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/render_adapter.py): Chuyển đổi dữ liệu Core Board sang định dạng VisualBoard cơ bản.
  - [board_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/board_preview.py), [dashboard_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/dashboard_preview.py), [advanced_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_preview.py), [animation_preview.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_preview.py): Các công cụ preview chạy độc lập từng module.
  - [advanced_fixtures.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_fixtures.py) & [animation_fixtures.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_fixtures.py): Dữ liệu mẫu phục vụ kiểm thử và preview.

### 2.5. Tầng Tài nguyên & Cấu hình màn chơi (`assets/`, `music/`, `levels/`)
- **[levels/](file:///d:/Tai/CSAI/Bloxorz_Solver/levels/)**: Gồm 10 màn chơi JSON được thiết kế chuẩn mực tăng dần độ khó, bao phủ toàn bộ cơ chế của Bloxorz (ô thường, ô cam vỡ, công tắc tròn/chéo, cầu toggle/permanent, công tắc phân tách khối 1x1).
- **[assets/audio/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/audio/)**: Hiệu ứng âm thanh WAV tương tác: click, fall, goal, music, roll.
- **[assets/backgrounds/](file:///d:/Tai/CSAI/Bloxorz_Solver/assets/backgrounds/)**: Bộ ảnh nền backdrop 3D chất lượng cao gồm `day.png` (ban ngày) và `night.png` (ban đêm/vũ trụ).
- **[music/](file:///d:/Tai/CSAI/Bloxorz_Solver/music/)**: Nhạc nền MP3 bổ sung cho game (`1.mp3`, `2.mp3`).

### 2.6. Tầng Tài liệu & Bộ kiểm thử (`docs/`, `tests/`, `tools/`)
- **[docs/](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/)**: Báo cáo lý thuyết thuật toán ([BASELINE.md](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/BASELINE.md), [BFS.md](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/BFS.md)) và hệ thống tài liệu đặc tả kiến trúc, hợp đồng đồ họa và hướng dẫn tích hợp chi tiết ([docs/gui/](file:///d:/Tai/CSAI/Bloxorz_Solver/docs/gui/)).
- **[tests/](file:///d:/Tai/CSAI/Bloxorz_Solver/tests/)**: Hệ thống kiểm thử tự động toàn diện từ logic bàn cờ, trạng thái khối, 6 thuật toán AI, quản lý worker nền đến kiểm thử giao diện DirectGUI và hoạt cảnh 3D.
- **[tools/](file:///d:/Tai/CSAI/Bloxorz_Solver/tools/)**: Các công cụ chạy kiểm thử khói (Smoke Tests) độc lập nhằm kiểm tra tức thì chức năng tích hợp UI, kiểm tra 10 màn chơi × 6 solver, và các giai đoạn phát triển đồ họa.

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

### Chạy kiểm thử khói tích hợp (Smoke Tests)
- Kiểm thử tích hợp toàn diện giao diện native và kiểm tra 10 màn chơi × 6 solver:
  ```bash
  python -m tools.game_integration_smoke
  ```
- Kiểm thử tầng Renderer và HUD:
  ```bash
  python -m tools.gui_stage3_6_smoke
  ```
- Kiểm thử tầng Advanced Renderer và vật liệu:
  ```bash
  python -m tools.gui_stage4_smoke
  ```
- Kiểm thử hệ thống hoạt cảnh liên tục:
  ```bash
  python -m tools.gui_stage5_smoke
  ```
- Kiểm thử cơ chế tách khối và điều khiển tương tác chuột:
  ```bash
  python -m tools.split_mouse_smoke
  ```
