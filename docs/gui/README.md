# GUI & Renderer — Gói thiết kế Chặng 2

> **Current game integration:** Core Advanced mechanics, phased replay, stable IDs,
> worker solvers and metrics HUD are connected in the native game. See
> [GAME_INTEGRATION.md](GAME_INTEGRATION.md) for the current API, controls and tests.
> Older stage/handoff documents below describe their historical checkpoint.

## Tài liệu Basic Renderer hiện hành

Index bổ sung **23/10/2026**: các phần Chặng2 bên dưới giữ nguyên snapshot lịch sử.
API/implementation hiện tại và readiness đọc từ gói bàn giao Chặng3:

- [STAGE3_HANDOFF](STAGE3_HANDOFF.md) — tài liệu chính gửi Phong/Tài review.
- [BASIC_RENDERER_API](BASIC_RENDERER_API.md) — source-backed API và verified examples.
- [TEAM_INTEGRATION_REVIEW](TEAM_INTEGRATION_REVIEW.md) — findings/deviations và pending decisions.
- [STAGE3_RELEASE_CHECKLIST](STAGE3_RELEASE_CHECKLIST.md) — runtime/Git/attribution checklist.

Ngày kiểm chứng: **22/10/2026**, múi giờ Asia/Ho_Chi_Minh. Phụ trách: **Phước**.

**DESIGN PACKAGE COMPLETE** là trạng thái của bộ tài liệu, không phải xác nhận GUI đã chạy hoặc **INTEGRATION CONTRACT APPROVED**. Hiện chưa có implementation GUI. Có thể dùng gói này để chuẩn bị Basic 3D Renderer độc lập; Advanced Integration cần Phong/Tài duyệt contract.

## Mục lục

1. [Phạm vi và nhãn trạng thái](#phạm-vi-và-nhãn-trạng-thái)
2. [Thứ tự đọc và trạng thái từng phần](#thứ-tự-đọc-và-trạng-thái-từng-phần)
3. [Repository đã kiểm chứng](#repository-đã-kiểm-chứng)
4. [Quyết định đã khóa](#quyết-định-đã-khóa)
5. [Ownership và cách dùng ở Chặng 3](#ownership-và-cách-dùng-ở-chặng-3)

## Phạm vi và nhãn trạng thái

Chặng 2 chỉ tạo Markdown trong `docs/gui/`. Không viết Python, prototype, assets, tests thực thi hoặc sửa dependency. Không đổi nhánh, đồng bộ remote, commit hay push.

| Nhãn | Ý nghĩa |
|---|---|
| VERIFIED IN SOURCE | Đã đọc source/check trạng thái local tại HEAD bên dưới; không đồng nghĩa runtime đã kiểm thử |
| USER APPROVED DESIGN | Quyết định thiết kế người dùng khóa trong yêu cầu Chặng 2 |
| PROPOSED CONTRACT | Hợp đồng đề xuất trong tài liệu, chưa có class/API tương ứng trong source |
| PENDING TEAM APPROVAL | Cần thành viên có quyền sở hữu xác nhận trước tích hợp |
| NOT IMPLEMENTED | Chưa có implementation trong checkout |
| NOT TESTED | Chưa có kiểm chứng runtime; test case tương lai mang trạng thái NOT RUN |

Trong báo cáo cũ, VERIFIED/APPROVED BY USER/PROPOSED tương ứng ba nhãn đầu. `RenderSnapshot` là tên khái niệm; tên DTO dùng xuyên suốt gói này là **GameSnapshot**. Không tạo thêm một DTO trùng tên.

## Thứ tự đọc và trạng thái từng phần

| Thứ tự | Phần | Tài liệu | Trạng thái thiết kế | Trạng thái implementation |
|---|---|---|---|---|
| 1 | 2.1 | [VISUAL_SPEC](VISUAL_SPEC.md) | Hoàn chỉnh theo visual direction đã khóa | NOT IMPLEMENTED |
| 2 | 2.2 | [LAYOUT_CAMERA_SPEC](LAYOUT_CAMERA_SPEC.md) | Layout đã khóa; có quy ước fit và responsive cụ thể | NOT IMPLEMENTED / NOT TESTED |
| 3 | 2.3 | [GEOMETRY_TILE_SPEC](GEOMETRY_TILE_SPEC.md) | Đủ Basic; hình ảnh Advanced có điều kiện | NOT IMPLEMENTED |
| 4 | 2.4 | [RENDER_CONTRACT](RENDER_CONTRACT.md) | Đủ bản đề xuất v1; PENDING TEAM APPROVAL | NOT IMPLEMENTED |
| 5 | 2.5 | [ASSET_CREDITS](ASSET_CREDITS.md) | Phân biệt nguồn tham khảo và tài nguyên thực dùng | Không import assets/code ngoài |
| 6 | 2.5 | [TEST_PLAN](TEST_PLAN.md) | Có setup, expected result và target stage | Tất cả test runtime: NOT RUN |
| 7 | 2.5 | [STAGE2_HANDOFF](STAGE2_HANDOFF.md) | Ranh giới coding, rủi ro, câu hỏi và tiêu chí bàn giao | Chưa bắt đầu Chặng 3 |

Nguồn chuẩn duy nhất: màu/material ở VISUAL_SPEC; layout/camera ở LAYOUT_CAMERA_SPEC; tọa độ/mesh ở GEOMETRY_TILE_SPEC; fields/lifecycle ở RENDER_CONTRACT; readiness/approval ở STAGE2_HANDOFF. Các file khác liên kết về nguồn chuẩn để tránh nhiều định nghĩa lệch nhau.

## Repository đã kiểm chứng

| Hạng mục | Kết quả local |
|---|---|
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `7e483b6c56b6b07799119e8b5721819c0346c541` |
| Trước biên soạn | Working tree sạch; chưa có `docs/gui/` |
| Khác audit Chặng 1 | Đã chuyển từ nhánh chung sang nhánh cá nhân theo yêu cầu người dùng; source cùng HEAD |
| Sau biên soạn | Tám Markdown mới trong `docs/gui/`, để untracked/chưa commit cho người dùng review |
| Remote freshness | Không fetch/pull trong Chặng 2; không khẳng định trạng thái server mới nhất |

| Source thật | API/trách nhiệm đã xác minh | Trạng thái/giới hạn |
|---|---|---|
| [state.py](../../src/core/state.py) | `Orientation`; frozen `BloxorzState(r,c,orientation,bridges_state)`; occupied cells, standing, equality/hash | Basic có code; flags chưa có cơ chế cầu; chưa có split/active cube |
| [board.py](../../src/core/board.py) | Load JSON; `grid`, `rows`, `cols`, start/goal; initial, validity, transition, goal test; actions U/D/L/R | Basic có code; không có tile enum/outcome/events Advanced |
| [base_solver.py](../../src/solvers/base_solver.py) | `solve()` đồng bộ; `SearchResult.actions/success/solution_length/time_taken/peak_memory/expanded_nodes` | Peak là traced Python allocations theo KiB, không phải RSS/GPU RAM |
| [renderer.py](../../src/gui/renderer.py), [controller.py](../../src/gui/controller.py), [gui init](../../src/gui/__init__.py) | Chưa có public GUI API | Cả ba rỗng, 0 byte |
| [main.py](../../main.py) | CLI BFS/DFS/IDS/Greedy + driver UCS; import A* còn comment | Không phải GUI host |
| [requirements.txt](../../requirements.txt) | Chưa khai báo dependency | Rỗng; không sửa trong Chặng 2 |
| [level_01.json](../../levels/level_01.json) | 4×7, start `[1,1]`, goal `[1,6]`, grid chứa 0/1/2 | Một level; chưa có bộ 16 map |
| [README gốc](../../README.md), [STRUCTURE](../../STRUCTURE.md) | Quy trình Git và sơ đồ dự kiến | Có phần kế hoạch cũ; không dùng thay bằng chứng source |
| [BASELINE](../BASELINE.md), [BFS](../BFS.md) | Baseline và giới hạn Advanced | Trạng thái bàn giao trong đó là ghi nhận lịch sử |
| [tests](../../tests) | 83 test method: State 16, Board 25, BaseSolver 18, BFS 17, Greedy 7 | Không chạy lại; chưa có test GUI/Advanced trong checkout |

Sáu implementation solver có trong source và đã thuộc local `main`. Tất cả tìm từ `get_initial_state()`; không mặc định giải từ current state. Source hiện không cho thấy refactor mới mà Phong đang làm; tiến độ ngoài checkout là UNKNOWN.

Môi trường kiểm chứng: `python3` là CPython 3.14.4; Panda3D chưa tìm thấy trong interpreter này. Không cài hoặc mở cửa sổ để kiểm tra. Không có assets/font/model được track. `README_LLM.md` và `benchmark.py` chưa tồn tại.

## Quyết định đã khóa

- USER APPROVED DESIGN: Panda3D; bản ưu tiên 1.10.16, chưa runtime-tested.
- Modern Light Minimal 3D; palette và Clean Floating Architectural Space theo VISUAL_SPEC.
- Reference 1280×720, bốn vùng màn hình cố định trong spec; first-pass từ 1024×720.
- Perspective Camera; elevation 45°, azimuth 30°, vertical FOV 45°; góc và vị trí phải được diễn giải theo quy ước camera đã ghi.
- World X theo column, Y đảo row, Z hướng lên; spacing `s=1`, floor top `Z=0`.
- Một host/event loop; Core không phụ thuộc Panda3D; Controller không sửa mesh; Renderer không chạy solver hoặc luật game.
- Ưu tiên procedural geometry; nguồn ngoài chỉ dùng khi license phù hợp và có attribution.

Các con số tuning mới, shape DTO, UI callback, IDs, lifecycle và mapping Advanced là PROPOSED CONTRACT; không chuyển thành team approval chỉ vì đã ghi tài liệu.

## Ownership và cách dùng ở Chặng 3

| Thành viên | Phạm vi |
|---|---|
| Phước | Scene, mesh, material, camera, lights, background, HUD visuals, animation từng action, adapter; review Controller |
| Phong | Core, State, tile schema, luật, outcome/events; review Renderer |
| Tài | Input, commands, session/current state, solver invocation, replay sequencing, speed, pause/reset/cancel |
| Shared | Host wiring, contract, entry point, dependencies, package exports; cần một người điều phối mỗi thay đổi |

Coding agent Chặng 3 phải đọc [handoff](STAGE2_HANDOFF.md), audit lại HEAD và kiểm tra contract Basic trước khi viết. Được chuẩn bị Basic Renderer độc lập từ baseline hiện tại; chưa được tự triển khai Controller, rolling animation, worker hoặc Advanced. Acceptance ở [TEST_PLAN](TEST_PLAN.md) là điều phải chứng minh về sau, không phải kết quả đã đạt.

Các thay đổi breaking cần Phong/Tài review; quyết định pending có mã Q-* ở handoff. Không tự sửa API thành viên khác để adapter hoạt động.
