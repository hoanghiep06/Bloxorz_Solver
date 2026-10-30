# Bản đồ source Bloxorz Solver

Tài liệu này mô tả cấu trúc runtime hiện tại. Quay lại [README](README.md) để cài đặt/chạy; xem [CONTRIBUTING](CONTRIBUTING.md) để biết contract solver.

## Luồng xử lý

```text
main.py → gui/game_app.py → screens.py (menu, chọn màn, Settings)
                                   ↓
levels/*.json → core/Board → gui/controller.py ← input bàn phím/chuột
                   ↑          ↓            ↓
              core/State   solver_worker   action_plan + snapshots
                   ↑          ↓            ↓
                 solvers ← current root    animation_manager
                              ↓            ↓
                         SearchResult    renderer / surface VFX / audio
                              ↓            ↓
                             HUD       Panda3D scene
```

Core là nguồn luật duy nhất. Renderer, Guide và camera chỉ thay presentation. Controller giữ state đã commit và session; pose trung gian trong animation không phải root hợp lệ để solver tự suy ra.

## Cây thư mục chi tiết

Cây source dưới đây liệt kê các file Python thực tế; bỏ `__pycache__` và `__init__.py` để dễ đọc. Đây là bản đồ trách nhiệm, không phải yêu cầu mọi tính năng phải đọc toàn bộ GUI.

```text
Bloxorz_Solver/
├── main.py                              # Entry point ứng dụng
├── requirements.txt                     # Dependencies chung
├── README.md / CONTRIBUTING.md           # Sử dụng / phát triển
├── src/
│   ├── core/
│   │   ├── board.py                      # Load JSON, luật ô, switch/bridge, transition
│   │   └── state.py                      # Tư thế whole/split, cubes, active cube, flags
│   ├── solvers/
│   │   ├── base_solver.py                # SearchResult, root hiện tại, time/tracemalloc
│   │   ├── bfs.py                        # Breadth-first
│   │   ├── dfs.py                        # Depth-first
│   │   ├── ids.py                        # Iterative deepening
│   │   ├── astar.py                      # g+h, split-safe heuristic, weighted cost
│   │   ├── greedy.py                     # Weighted heuristic priorities
│   │   ├── ucs.py                        # Public exports, giữ import thống nhất
│   │   └── UCS_Algorithm/
│   │       ├── ucs.py                    # UCS search implementation
│   │       ├── cost_functions.py         # Uniform/Physics/Risk/Tuned cost models
│   │       └── main_ucs.py               # Entry/demo riêng của UCS
│   ├── evaluation/
│   │   └── evaluator.py                  # Trajectory penalty, score, hazards
│   └── gui/
│       ├── about_page.py                     # Nội dung/trình bày About
│       ├── action_plan.py                    # Chuyển Core transition thành các pha presentation
│       ├── advanced_contracts.py             # Bridge/switch/split render contracts
│       ├── advanced_fixtures.py              # Fixture render nâng cao
│       ├── advanced_mesh_factory.py          # Mesh cơ chế nâng cao
│       ├── advanced_preview.py               # Preview advanced board
│       ├── advanced_renderer.py              # Advanced actors/surfaces và trạng thái cơ chế
│       ├── ambient.py                        # Hạt nền theo theme
│       ├── animation_contracts.py            # Requests/events/snapshots animation
│       ├── animation_effects.py              # Animated surfaces, mảnh vỡ và hiệu ứng
│       ├── animation_fixtures.py             # Fixture animation
│       ├── animation_manager.py              # Chạy/cancel actor timeline
│       ├── animation_math.py                 # Toán pose lăn/animation
│       ├── animation_preview.py              # Preview animation
│       ├── animation_timeline.py             # Timeline xác định theo thời gian
│       ├── app.py                            # Khởi tạo host Panda3D nền
│       ├── attract.py                        # Demo khi menu idle
│       ├── audio.py                          # Phát âm thanh và lifecycle
│       ├── audio_events.py                   # Mapping event animation → âm thanh
│       ├── board_preview.py                  # Preview basic board
│       ├── camera.py                         # Framing, projection, camera presentation
│       ├── camera_views.py                   # Iso/Top/Follow, orbit/zoom, remap hướng
│       ├── cinematic_bloom.py                # Post-processing bloom
│       ├── contracts.py                      # Basic render contracts
│       ├── controller.py                     # Điều phối manual/solver/replay, commit state
│       ├── dashboard_preview.py              # Preview HUD/dashboard
│       ├── elemental_switches.py             # Visual switches theo hai theme
│       ├── fall_math.py                      # Quỹ đạo tipping/fall
│       ├── game_adapter.py                   # Adapter Board/State cho gameplay visuals
│       ├── game_app.py                       # Tạo/dispose game, CLI, nối các component
│       ├── game_scene.py                     # Quản lý scene/session và tài nguyên render
│       ├── geometry_math.py                  # Toán hình học không phụ thuộc frame
│       ├── hud.py                            # Nút solver, replay và bảng metrics
│       ├── icons.py                          # Icon HUD dùng chung
│       ├── layout.py                         # Tính layout UI
│       ├── level_intro.py                    # Intro level
│       ├── mechanics_focus.py                # Lookup targets, cycling, camera focus/restore
│       ├── mechanics_guide.py                # Rail/Help Card và lifecycle UI
│       ├── mechanics_guide_data.py           # Nội dung/dữ liệu cơ chế
│       ├── mechanics_icons.py                # Icon procedural theo visual identity/theme
│       ├── mesh_factory.py                   # Mesh cơ bản
│       ├── mouse_control.py                  # Picking action, controlled cells, HUD hit test
│       ├── move_arrows.py                    # Hình mũi tên điều khiển
│       ├── move_assist.py                    # Dự báo transition, vùng đáp, cảnh báo
│       ├── profile.py                        # Save settings, stars, best moves, par
│       ├── render_adapter.py                 # Chuyển basic Board sang dữ liệu render
│       ├── renderer.py                       # Basic scene renderer
│       ├── scene_lighting.py                 # Đèn/shadow theo theme
│       ├── scene_style.py                    # Áp style/texture/background scene
│       ├── screens.py                        # Main/Levels/Settings/Game và menu flow
│       ├── snow_palette.py                   # Palette băng/tuyết
│       ├── solver_worker.py                  # Tìm kiếm nền và trả kết quả theo session
│       ├── sound_bank.py                     # Catalog audio assets
│       ├── split_teleport_math.py            # Timeline/pose năng lượng teleport
│       ├── split_teleport_vfx.py             # Scene VFX split/merge
│       ├── switch_materials.py               # Shader/material switches và fallback
│       ├── switch_vfx.py                     # Hiệu ứng trạng thái công tắc
│       ├── temple_environment.py             # Trang trí môi trường temple
│       ├── tutorial.py                       # Hướng dẫn thao tác trong game
│       ├── ui_theme.py                       # Theme tokens, font, widget styles
│       ├── viewport.py                       # Vùng hiển thị an toàn và kích thước
│       ├── visual_materials.py               # Registry texture/shader/material
│       ├── visual_quality.py                 # Cấu hình chất lượng/fallback backend
├── levels/                              # Production 01–19, không dùng fixture để thay thế
├── assets/
│   ├── audio/                           # SFX/ambience và dữ liệu âm thanh
│   ├── backgrounds/                     # Jungle/Winter và backdrop
│   ├── fonts/                           # Font UI
│   ├── icons/                           # Toolbar assets
│   ├── materials/                       # Texture đá, tuyết, băng, magma, fragile…
│   ├── shaders/                         # GLSL vật liệu và postprocess
│   └── VISUAL_ATTRIBUTION.md             # Nguồn tài nguyên hình ảnh
├── music/                               # Nhạc bổ sung
├── tests/
│   ├── test_*.py                        # Core, solver, GUI, geometry, lifecycle
│   └── fixtures/                        # Board/action corpus cố định cho test
├── tools/                               # Native smoke/capture và build assets
├── benchmark.py                         # Sáu solver, evaluator, CSV chi tiết/summary
├── generate_trajectories.py              # Sinh action trajectories
├── trajectories/                        # Dữ liệu lịch sử Level 01–18
├── benchmark_results.csv                # Kết quả lịch sử, không tự cập nhật theo HEAD
├── benchmark_summary.csv                # Summary lịch sử
├── Bloxorz_Weight_Tuning_Guide/
│   ├── README_VI.md / CHANGELOG_V2.md    # Cách chạy thí nghiệm tuning
│   ├── requirements.txt                 # Dependencies riêng của bộ thí nghiệm
│   ├── experiments/                     # Grid search, plotting, kết quả lịch sử
│   ├── benchmark_levels/                # Dataset và trajectories training riêng
│   ├── templates/                       # Mẫu bảng báo cáo
│   └── Bloxorz_Solver-…/src/core/        # Snapshot tham chiếu; KHÔNG phải runtime Core
└── docs/
    ├── BASELINE.md / BFS.md              # Tài liệu thuật toán/baseline
    ├── PHONG_WEIGHTED_MERGE.md           # Quyết định weighted cost/heuristic và tests
    ├── BAO_CAO_TONG_KET_NHOM_2.md       # Báo cáo đánh giá
    ├── QUY_UOC_KY_THUAT_CHUNG.md        # Quy ước kỹ thuật
    ├── gui/                             # Render contracts, UI, camera, VFX và evidence
    ├── integration/                     # Current-state solver, tích hợp team
    ├── audio/                           # Audio API/credits/validation
    ├── levels/                          # Thiết kế và kịch bản Level 19
    └── evidence/                        # Logs, reports và ảnh runtime
```

## Nên đọc/sửa ở đâu?

| Công việc | File bắt đầu và dữ liệu liên quan |
| --- | --- |
| Luật đi, fragile, bridge, split/merge | [board.py](src/core/board.py), [state.py](src/core/state.py); kiểm tra Core tests trước khi động vào renderer |
| Solver từ current state | [base_solver.py](src/solvers/base_solver.py), [solver_worker.py](src/gui/solver_worker.py), [controller.py](src/gui/controller.py) |
| A*/UCS cost hoặc heuristic | [astar.py](src/solvers/astar.py), [UCS implementation](src/solvers/UCS_Algorithm/ucs.py), [cost functions](src/solvers/UCS_Algorithm/cost_functions.py) |
| Nút, Settings, menu/level select | [screens.py](src/gui/screens.py), [hud.py](src/gui/hud.py), [ui_theme.py](src/gui/ui_theme.py) |
| Guide icon, nội dung, focus tile | [mechanics_guide.py](src/gui/mechanics_guide.py), [icons](src/gui/mechanics_icons.py), [focus](src/gui/mechanics_focus.py) |
| Dự báo nước đi | [move_assist.py](src/gui/move_assist.py); dự báo qua Core, không viết lại luật |
| Lăn/rơi/vỡ hoặc thứ tự event | [action_plan.py](src/gui/action_plan.py), [animation_manager.py](src/gui/animation_manager.py), [fall_math.py](src/gui/fall_math.py), [animation_effects.py](src/gui/animation_effects.py) |
| Split/merge energy VFX | [teleport math](src/gui/split_teleport_math.py), [teleport VFX](src/gui/split_teleport_vfx.py) |
| Camera và điều khiển theo hướng nhìn | [camera.py](src/gui/camera.py), [camera_views.py](src/gui/camera_views.py), [mouse_control.py](src/gui/mouse_control.py) |
| Theme/sàn tuyết/material | [scene_style.py](src/gui/scene_style.py), [visual_materials.py](src/gui/visual_materials.py), [snow_palette.py](src/gui/snow_palette.py), `assets/materials/` |
| Âm thanh | [audio.py](src/gui/audio.py), [audio_events.py](src/gui/audio_events.py), [sound_bank.py](src/gui/sound_bank.py) |
| Save/tiến độ | [profile.py](src/gui/profile.py); file mặc định nằm ngoài repo ở thư mục người dùng |
| Penalty/score benchmark | [evaluator.py](src/evaluation/evaluator.py), [benchmark.py](benchmark.py); tách khỏi cost model tìm kiếm |

## Công cụ kiểm tra theo tính năng

Các tên dưới đây là module thật trong `tools/`; xem `--help` và yêu cầu runtime của từng tool trước khi chạy. Công cụ native input chủ yếu phục vụ Linux/X11, không coi tất cả là đa nền tảng.

| Nhóm | Module tiêu biểu |
| --- | --- |
| Current-state / weighted integration | `current_state_solver_smoke`, `phong_merge_smoke` |
| Level 19 | `level19_smoke` |
| Guide / focus | `mechanics_guide_smoke`, `mechanics_focus_smoke` |
| Fall / split / merge | `physical_fall_smoke`, `split_teleport_smoke`, `merge_teleport_smoke`, `split_mouse_smoke` |
| Theme / switch / snow | `jungle_quality_smoke`, `snow_floor_smoke`, `elemental_switch_smoke` |
| Camera / UI / About / audio | `merged_camera_smoke`, `targeted_ui_smoke`, `about_page_smoke`, `game_audio_smoke` |
| Capture / tạo asset | `animation_capture`, `jungle_visual_capture`, `build_visual_materials`, `build_snow_materials`, `build_game_audio` |

Ví dụ: `python -B -m tools.mechanics_focus_smoke --help`. Build asset có thể ghi file tài nguyên; không chạy như một phép test chỉ đọc nếu chưa có ý định tái tạo assets.

Các con số benchmark, danh sách tests và ảnh trong báo cáo gắn với revision/thời điểm ghi nhận. Ưu tiên source hiện tại và kết quả vừa chạy khi có khác biệt với tài liệu lịch sử.
