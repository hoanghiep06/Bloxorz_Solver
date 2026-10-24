# 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

> **Lưu ý cho các thành viên:** Khi tạo mới, đổi tên hoặc tái cấu trúc các file/thư mục thuộc phân công của mình, hãy chủ động cập nhật lại sơ đồ cây và bảng mô tả bên dưới trước khi tạo Pull Request (PR).

---

## 1. Sơ đồ cây tổng quan

```text
Bloxorz_Solver/
├── assets/                                 # Tài nguyên đa phương tiện tĩnh
│   └── audio/                             # Hiệu ứng âm thanh (.wav) và nhạc nền
│       ├── click.wav                      # Âm thanh click tương tác giao diện UI
│       ├── fall.wav                       # Âm thanh rơi khối khi sảy chân (Game Over)
│       ├── goal.wav                       # Âm thanh hoàn thành màn chơi (Win)
│       ├── music.wav                      # Nhạc nền ambient trong game
│       └── roll.wav                       # Âm thanh lật khối 90 độ
├── docs/                                  # Tài liệu kỹ thuật, báo cáo & đặc tả thiết kế
│   ├── BASELINE.md                        # Cơ sở lý thuyết thuật toán tìm kiếm
│   ├── BFS.md                             # Báo cáo chuyên sâu thuật toán BFS
│   └── gui/                               # Đặc tả kiến trúc hệ thống giao diện 3D
│       ├── ASSET_CREDITS.md               # Nguồn gốc tài nguyên và bản quyền
│       ├── BASIC_RENDERER_API.md          # Tài liệu API cho Renderer cơ bản
│       ├── GEOMETRY_TILE_SPEC.md          # Đặc tả hình học ô gạch và switch
│       ├── LAYOUT_CAMERA_SPEC.md          # Đặc tả camera và phân vùng viewport
│       ├── RENDER_CONTRACT.md             # Hợp đồng dữ liệu tầng đồ họa
│       ├── STAGE*_*.md                    # Đặc tả chi tiết các giai đoạn phát triển GUI (1 đến 5)
│       └── TEST_PLAN.md                   # Kế hoạch kiểm thử tự động giao diện
├── levels/                                # Dữ liệu bản đồ các màn chơi (JSON)
│   └── level_01.json                      # Bản đồ chuẩn (sàn, đích, công tắc soft/heavy, cầu)
├── src/                                   # Toàn bộ mã nguồn chính của dự án
│   ├── core/                              # Tầng lõi trò chơi (Logic & Quy tắc vật lý)
│   │   ├── board.py                       # Quản lý bản đồ, transition model, kiểm tra hợp lệ, xử lý công tắc/cầu
│   │   └── state.py                       # Biểu diễn trạng thái khối Bloxorz (tư thế STANDING/HORIZ/VERT, khối tách)
│   ├── solvers/                           # Tầng thuật toán tìm kiếm AI (AI Solvers)
│   │   ├── base_solver.py                 # Lớp cơ sở trừu tượng BaseSolver & tích hợp đo Benchmark chuẩn
│   │   ├── bfs.py                         # Thuật toán BFS (Breadth-First Search)
│   │   ├── dfs.py                         # Thuật toán DFS (Depth-First Search)
│   │   ├── ids.py                         # Thuật toán IDS (Iterative Deepening Search)
│   │   ├── greedy.py                      # Thuật toán GBFS (Greedy Best-First Search)
│   │   ├── astar.py                       # Thuật toán A* Search
│   │   └── UCS_Algorithm/                 # Thuật toán UCS (Uniform-Cost Search)
│   │       ├── ucs.py                     # Lõi giải thuật tìm kiếm chi phí đều
│   │       ├── cost_functions.py          # Các hàm tính toán chi phí bước đi
│   │       └── main_ucs.py                # Điểm chạy kiểm thử độc lập cho UCS
│   └── gui/                               # Tầng giao diện đồ họa 3D (Panda3D Engine)
│       ├── app.py                         # Nền tảng cửa sổ ShowBase Panda3D cơ bản
│       ├── game_app.py                    # Ứng dụng game hoàn chỉnh (kết nối Menu, Controller, Âm thanh, Renderer)
│       ├── controller.py                  # Điều phối gameplay: chơi tay, chọn level, chạy AI Solver & auto-replay
│       ├── screens.py                     # Quản lý luồng giao diện menu (Main Menu, Level Select, Solvers, Settings)
│       ├── hud.py                         # ViewModel và các thanh trạng thái hiển thị chỉ số HUD
│       ├── ui_theme.py                    # Bảng màu, typography và kiểu dáng DirectGUI
│       ├── profile.py                     # Lưu trữ tiến trình màn chơi (sao, điểm) và cài đặt người dùng
│       ├── audio.py                       # Trình quản lý phát hiệu ứng âm thanh và nhạc nền
│       ├── attract.py                     # Chế độ tự động demo màn chơi khi người dùng không tương tác
│       ├── ambient.py                     # Hiệu ứng hạt động nền menu (sao băng / lá bay theo theme)
│       ├── level_intro.py                 # Hoạt cảnh dâng sàn dạng sóng và thả khối khi vào màn chơi mới
│       ├── move_arrows.py                 # Mũi tên tương tác 3D quanh khối phục vụ điều khiển bằng chuột
│       ├── mouse_control.py               # Xử lý hover/click chuột trên bàn cờ và mũi tên 3D
│       ├── renderer.py                    # Bộ dựng hình 3D cơ bản (sàn tĩnh, ô động, khối)
│       ├── advanced_renderer.py           # Bộ dựng hình nâng cao (vật liệu chi tiết, bóng đổ, trạng thái switch)
│       ├── mesh_factory.py                # Tạo lưới hình học tĩnh (sàn, đích, khối chữ nhật)
│       ├── advanced_mesh_factory.py       # Tạo lưới hình học động (ô cam vỡ, nút bấm tròn/chéo, cầu gập)
│       ├── animation_manager.py           # Quản lý tiến trình hoạt cảnh lăn, rơi tự do, mở cầu mượt mà
│       ├── animation_effects.py           # Các hiệu ứng chuyển động phụ trợ (nảy, vỡ nát, rơi)
│       ├── animation_math.py              # Tính toán góc xoay vật lý 90 độ và điểm tựa (pivot) lăn khối
│       ├── animation_contracts.py         # Định nghĩa các trạng thái, sự kiện và contract hoạt cảnh
│       ├── animation_preview.py           # Khung xem thử các chuỗi hoạt cảnh
│       ├── animation_timeline.py          # Dòng thời gian điều khiển frame hoạt cảnh
│       ├── camera.py                      # Hệ thống camera động: tự căn chỉnh góc nhìn bao quát toàn bộ map
│       ├── scene_lighting.py              # Thiết lập nguồn sáng Ambient, Directional và đổ bóng
│       ├── scene_style.py                 # Phối màu môi trường nền, sương mù và ánh sáng
│       ├── layout.py                      # Bố cục màn hình: phân chia vùng hiển thị 3D và thanh điều khiển
│       ├── viewport.py                    # Quản lý khung nhìn Viewport của Panda3D
│       ├── render_adapter.py              # Chuyển đổi dữ liệu từ Core Board sang định dạng VisualBoard
│       ├── contracts.py                   # Các dataclass định nghĩa dữ liệu hiển thị cơ bản
│       ├── advanced_contracts.py          # Các dataclass mở rộng cho hiệu ứng và vật liệu nâng cao
│       ├── geometry_math.py               # Các hàm phụ trợ tính toán tọa độ hình học 3D
│       ├── board_preview.py               # Công cụ xem trước bản đồ tĩnh
│       └── dashboard_preview.py           # Công cụ xem trước giao diện Dashboard & HUD
├── tests/                                 # Bộ kiểm thử tự động (Unit Tests & Integration Tests)
│   ├── test_board.py                      # Kiểm thử logic bàn cờ và va chạm
│   ├── test_state.py                      # Kiểm thử trạng thái khối Bloxorz
│   ├── test_bfs.py                        # Kiểm thử thuật toán BFS
│   ├── test_greedy.py                     # Kiểm thử thuật toán Greedy
│   ├── test_base_solver.py                # Kiểm thử lớp cơ sở đo đạc hiệu năng
│   ├── test_gui_*.py                      # Hàng loạt bài test cho Renderer, Camera, HUD, Hoạt cảnh
│   └── gui_animation_support.py           # Dữ liệu giả lập (fixture) cho kiểm thử hoạt cảnh
├── tools/                                 # Công cụ chạy kiểm thử nhanh (Smoke Tests)
│   ├── gui_stage3_6_smoke.py              # Smoke test tầng Renderer và HUD cơ bản
│   ├── gui_stage4_smoke.py              # Smoke test tầng Advanced Renderer và vật liệu
│   └── gui_stage5_smoke.py              # Smoke test hệ thống hoạt cảnh liên tục
├── main.py                                # Điểm khởi chạy chính toàn bộ dự án (Game 3D + AI Visualizer)
├── requirements.txt                       # Danh mục các thư viện phụ thuộc (Panda3D, Pygame, ...)
├── STRUCTURE.md                           # Tài liệu cấu trúc thư mục này
└── README.md                              # Hướng dẫn cài đặt môi trường, quy ước git và hướng dẫn sử dụng
```

---

## 2. Chi tiết vai trò từng phân hệ

### 2.1. Điểm khởi chạy (`main.py`)
- Khởi động toàn bộ giao diện 3D trực quan ([game_app.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_app.py)).
- Tích hợp cơ chế tự động chuyển tiếp môi trường ảo `.venv` nếu chưa kích hoạt, đảm bảo đầy đủ thư viện `panda3d` khi thực thi.

### 2.2. Tầng Lõi Logic (`src/core/`)
- **[board.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/core/board.py)**: Đọc cấu hình JSON, quản lý lưới tọa độ, xử lý 12 trường hợp lăn khối nguyên vẹn, cơ chế tách khối (Split Switch `( )`), tái hợp khối (Merge), và kích hoạt các công tắc đóng/mở cầu (`soft`, `heavy`).
- **[state.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/core/state.py)**: Định nghĩa lớp trạng thái `BloxorzState`, lưu trữ tư thế khối (`STANDING`, `HORIZONTAL`, `VERTICAL`), vị trí tọa độ, trạng thái các cây cầu (`bridges_state`) và tọa độ 2 khối con khi bị tách.

### 2.3. Tầng Thuật toán AI (`src/solvers/`)
- Triển khai các giải thuật tìm kiếm trạng thái: **BFS**, **DFS**, **IDS**, **UCS**, **Greedy Best-First**, và **A\***.
- Tất cả thuật toán kế thừa [base_solver.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/solvers/base_solver.py) để tự động ghi nhận 4 chỉ số thực nghiệm chuẩn:
  1. *Thời gian tìm kiếm (Search Time)*.
  2. *Dung lượng RAM tối đa (Peak Memory)*.
  3. *Số trạng thái đã mở (Expanded Nodes)*.
  4. *Độ dài đường đi tối ưu (Solution Length)*.

### 2.4. Tầng Giao diện 3D & Hoạt cảnh (`src/gui/`)
Xây dựng trên nền tảng **Panda3D**, chia làm các nhóm chức năng:
- **Game Flow & Menu**: [game_app.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/game_app.py), [screens.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/screens.py), [controller.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/controller.py), [hud.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/hud.py), [profile.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/profile.py), [ui_theme.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ui_theme.py).
- **Tương tác & Hiệu ứng sinh động**:
  - [move_arrows.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/move_arrows.py) & [mouse_control.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mouse_control.py): Hiển thị mũi tên 3D xung quanh khối và bắt sự kiện chuột.
  - [level_intro.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/level_intro.py): Hoạt cảnh sóng sàn trồi lên và thả khối khi bắt đầu level.
  - [ambient.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/ambient.py): Hạt nền lơ lửng (sao băng hoặc lá rơi theo chủ đề màu).
  - [audio.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/audio.py): Quản lý âm thanh tương tác và nhạc nền.
  - [attract.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/attract.py): Tự động minh họa đường đi sau thời gian rảnh rỗi.
- **Dựng hình 3D & Animation**: [renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/renderer.py), [advanced_renderer.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/advanced_renderer.py), [animation_manager.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_manager.py), [animation_math.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/animation_math.py), [mesh_factory.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/mesh_factory.py).
- **Môi trường & Camera**: [camera.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/camera.py), [scene_lighting.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_lighting.py), [scene_style.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/scene_style.py), [viewport.py](file:///d:/Tai/CSAI/Bloxorz_Solver/src/gui/viewport.py).

---

## 3. Cách thức vận hành dự án

### Chạy ứng dụng Game 3D & Trình diễn Solvers
```bash
python main.py
```

### Chạy kiểm thử tự động (Unit Tests)
```bash
pytest tests/
```

### Chạy các kịch bản kiểm tra giao diện đồ họa (Smoke Tests)
```bash
python -m tools.gui_stage3_6_smoke
python -m tools.gui_stage4_smoke
python -m tools.gui_stage5_smoke
```


## Native game integration modules

- `src/gui/game_adapter.py`: validated Advanced board/snapshot mapping from Core, stable bridge/switch/cube IDs.
- `src/gui/action_plan.py`: one Core action becomes explicit roll/effect/terminal phases.
- `src/gui/game_scene.py`: staged level scene and surface-layer ownership; failed loading preserves the live scene.
- `src/gui/solver_worker.py`: cancellable solver processes; Panda remains on the main thread.
- `tools/game_integration_smoke.py`: native UI regression, including all 10 levels × 6 solvers.
- `docs/gui/GAME_INTEGRATION.md`: current contracts, controls, cancellation and verification.
