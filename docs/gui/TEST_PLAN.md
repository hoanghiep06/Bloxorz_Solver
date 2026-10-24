# 2.5 — Test Plan cho Basic Renderer và tích hợp sau

**KẾ HOẠCH, KHÔNG PHẢI KẾT QUẢ. Tất cả test case bên dưới: NOT RUN.** Không tạo test Python, map, ảnh render hoặc GUI runtime trong Chặng 2.

## Mục lục

1. [Phạm vi, fixtures và evidence](#phạm-vi-fixtures-và-evidence)
2. [Geometry](#geometry)
3. [Camera và layout](#camera-và-layout)
4. [Adapter và contract](#adapter-và-contract)
5. [Animation tương lai](#animation-tương-lai)
6. [Integration tương lai](#integration-tương-lai)
7. [Visual](#visual)
8. [Platform](#platform)
9. [Yêu cầu đồ án và nghiệm thu](#yêu-cầu-đồ-án-và-nghiệm-thu)

## Phạm vi, fixtures và evidence

Target `3 Basic` chỉ gồm renderer tĩnh, HUD shell và adapter. `Sau Basic` dành animation/controller/replay, `Advanced` cần Core mới được duyệt. Không tự biến test plan thành quyền triển khai các phần đó.

Mỗi row nêu purpose, preconditions, setup, expected result, target, type và status. Fixtures synthetic ở kế hoạch không phải màn chơi chính thức của nhóm và không được dùng để tăng số lượng level nộp. Không sửa level/tests hiện có; khi được cho phép ở Chặng 3 có thể thêm fixture in-memory hoặc file test mới trong vùng được giao.

Evidence khi chạy sau này: test ID, commit, OS/Python/Panda version, GPU/driver cho visual, window/framebuffer size và scale, expected/actual, screenshot/log nếu phù hợp, PASS/FAIL/BLOCKED cùng lý do. Chỉ ghi PASS khi test thực sự thực thi. Chưa có số đo FPS/RAM hay ảnh nghiệm thu.

Tolerance đề xuất: geometry center/bounds 1e−5s; layout edges tối đa 1 framebuffer px do rounding; camera NDC 0.74+1e−6 theo padding p=0.13. Không dùng epsilon để che lỗi anchor nửa ô. Palette kiểm tra input tokens trước lighting; không đòi rendered pixel trùng HEX trên mặt có đèn.

## Geometry

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| GEO-01 | Standing center/size | Basic geometry có thể inspect | Board 4×7, state S(1,1) | Center (−2,0.5,1), size (1,1,2), bottom Z=0 | 3 Basic | Math unit + runtime bounds | NOT RUN |
| GEO-02 | Horizontal anchor | Như GEO-01 | H(1,1), cells (1,1),(1,2) | Center (−1.5,0.5,0.5), size (2,1,1) | 3 Basic | Unit + bounds | NOT RUN |
| GEO-03 | Vertical anchor | Như GEO-01 | V(1,1), cells (1,1),(2,1) | Center (−2,0,0.5), size (1,2,1) | 3 Basic | Unit + bounds | NOT RUN |
| GEO-04 | Odd/even origin | Tọa độ function có s=1 | 4×6, 5×7, 4×7 | Tâm ngoài cùng đối xứng quanh 0; không lệch nửa ô | 3 Basic | Parameterized unit | NOT RUN |
| GEO-05 | Non-square axes | Source dùng row/col | 3×11 và 11×3 | Column tăng X; row tăng làm Y giảm, không transpose | 3 Basic | Unit + visual | NOT RUN |
| GEO-06 | Floor thickness/seam | Tile mesh dựng được | Hai ô kế nhau | Top 0, bottom −0.18, width 0.96, gap 0.04; không đổi occupancy | 3 Basic | Bounds + visual | NOT RUN |
| GEO-07 | Void thật | Scene graph inspect được | Demo có 0 | Không có floor mesh tại cell 0, không có nền giả ở mặt sàn | 3 Basic | Scene inspection | NOT RUN |
| GEO-08 | Goal depth/authority | Board loaded | Goal field ở tile code 1; code 2 ở ô khác | Hố ở field goal, inner wall/đáy −0.65; ô 2 ngoài goal là floor | 3 Basic | Unit + visual | NOT RUN |
| GEO-09 | Normals và bevel | Có key light | Xem top, sides, bevel ở camera chuẩn | Không mất mặt hoặc lighting đảo; bevel trong nominal bounds | 3 Basic | Visual + mesh inspection | NOT RUN |
| GEO-10 | Không rebuild board | Load một board | show 3 snapshots hợp lệ cùng revision board | StaticBoardRoot/geometry tái dùng, chỉ block pose đổi | 3 Basic | Runtime identity check | NOT RUN |
| GEO-11 | Detail face continuity | Animation đã được cho phép | Chuỗi roll đủ quay về pose | Chi tiết đi cùng mặt mesh, không snap lại mỗi bước | Sau Basic | Visual sequence | NOT RUN |
| GEO-12 | Split identities | Core split contract approved | Hai cubes với IDs, đổi active ID | Đúng vị trí, marker chỉ đổi active; renderer không merge | Advanced | Integration + visual | NOT RUN |

## Camera và layout

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| LAY-01 | Reference rectangles | Layout function có | 1280×720 | Đúng 4 region ở Layout Spec, không overlap/out-of-window | 3 Basic | Pure math | NOT RUN |
| LAY-02 | Responsive minimum | Như LAY-01 | 1920×1080,1366×768,1024×768,1024×720 | Giữ panel/fonts; viewport lần lượt 1574×890,1020×578,678×578,678×530 | 3 Basic | Parameterized math | NOT RUN |
| LAY-03 | Hit areas/text | HUD shell có | Reference và minimum | Label/slider hitbox không chồng; 5 metrics không bị cắt | 3 Basic | Visual bounds | NOT RUN |
| LAY-04 | UI coordinate conversion | Pixel2d/region có | Điểm (24,92), viewport 934×530 | Pixel2d (24,0,−92); normalized region khớp Layout Spec | 3 Basic | Math + runtime | NOT RUN |
| LAY-05 | Below minimum/minimize | Host có resize handler | 900×600 rồi 0×0 rồi phục hồi | Không divide-by-zero, không co font vô hạn; minimum/notice theo spec | 3 Basic | Manual resize | NOT RUN |
| CAM-01 | Demo auto-fit | Perspective lens có | Bbox demo, viewport 934×530 | Vertical 45°, horizontal ≈72.2554°, corners trong NDC ±0.74 | 3 Basic | Math + lens inspection | NOT RUN |
| CAM-02 | Wide map | Synthetic bounds | 4×20, mọi edge có thể đặt block | Không clip near corners; có safety margin đúng, không chỉ max(rows,cols) | 3 Basic | Projection unit + visual | NOT RUN |
| CAM-03 | Tall map | Synthetic bounds | 20×4 | Vừa viewport theo cả hai trục và độ sâu | 3 Basic | Projection unit + visual | NOT RUN |
| CAM-04 | Height/thickness/well | Fit routine có | Bbox Z −0.65..2.30, standing ở biên | Đủ top block/bottom well; depth trong near/far | 3 Basic | Corner projection | NOT RUN |
| CAM-05 | Resize lens aspect | Host runtime có | Chuyển mọi size hỗ trợ | Lens dùng viewport aspect mới, không dùng window aspect | 3 Basic | Runtime inspect | NOT RUN |
| CAM-06 | Camera stability | Một board revision | Đổi vị trí/pose block bằng snapshot | Camera distance/target không đổi theo từng bước | 3 Basic | Transform comparison | NOT RUN |
| CAM-07 | Background exclusion | Backdrop có | Gradient/full-scene backdrop | Fit không bị bounds nền kéo quá xa; không render board hai lần | 3 Basic | Scene inspection | NOT RUN |

## Adapter và contract

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| ADP-01 | Immutability | Basic adapter có | Chụp grid/state/hash trước và sau map | Source không đổi; sửa container output không sửa Core | 3 Basic | Unit | NOT RUN |
| ADP-02 | Orientation mapping | Board/state thật | Ba orientation hợp lệ | Anchor/cells đúng State method và công thức Geometry | 3 Basic | Parameterized unit | NOT RUN |
| ADP-03 | Authoritative goal | Valid Board fixture | Goal trên code 1, code 2 ô khác | Chỉ goal field thành semantic GOAL | 3 Basic | Unit | NOT RUN |
| ADP-04 | Invalid data | Validator có | Bool coords, bad orientation, duplicate cells, mismatch footprint | Reject có field path, không sửa scene/Core | 3 Basic | Negative unit | NOT RUN |
| ADP-05 | Unknown tile | Basic profile | Mã 3 hoặc nonzero lạ | UNSUPPORTED_TILE, không giả fragile đã có | 3 Basic | Negative unit | NOT RUN |
| ADP-06 | Pure DTO/adapter | Các module tương lai có | Import không có Panda3D | Import được pure module, không mở window hoặc import engine gián tiếp | 3 Basic | Isolated import test | NOT RUN |
| ADP-07 | Bridge unknown mapping | Chỉ Basic hỗ trợ | State flags (True,False), definitions thiếu | Unsupported mapping, không sinh bridge IDs giả | 3 Basic | Negative unit | NOT RUN |
| ADP-08 | Identity/version | load/show có | Sai schema_version/board_revision; session/revision cũ | Reject; same revision khác content cũng reject; scene cũ không đổi | 3 Basic | Contract unit/runtime | NOT RUN |
| ADP-09 | Session reset | show_snapshot có | Session 1 rev20 rồi session 2 rev0 | Snapshot mới nhận; snapshot session1 đến muộn bị reject | 3 Basic | Contract unit | NOT RUN |
| ADP-10 | Split mapping | Core API đã duyệt | Hai cube IDs và active ID, bridge states | DTO giữ identity/mapping, không tự merge/switch | Advanced | Contract integration | NOT RUN |

## Animation tương lai

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| ANI-01 | Roll đủ hướng/pose | Rolling được cho phép | 3 orientations × U/D/L/R, Core cho valid moves | Pivot cạnh tiếp xúc, 90°, endpoint đúng after, không lerp thẳng center | Sau Basic | Parameterized integration | NOT RUN |
| ANI-02 | Endpoint drift | Như ANI-01 | Chuỗi dài và ngược lại | Sai số center/bottom ≤1e−5s; không snap mặt bất thường | Sau Basic | Numeric + visual | NOT RUN |
| ANI-03 | Cancel mid-roll | Lifecycle có | Cancel ở 25%,50%,75% | Một CANCELLED, không COMPLETED, IDLE cần resync | Sau Basic | Controlled-clock test | NOT RUN |
| ANI-04 | Pause/resume | Như ANI-03 | Pause giữa roll, đợi, resume | Progress đứng yên rồi tiếp tục, không terminal khi pause | Sau Basic | Controlled-clock | NOT RUN |
| ANI-05 | Speed change | Rate API có | 1×→0.5×→2×; rate 0/NaN/bool | Rate hợp lệ không nhảy progress; invalid reject | Sau Basic | Unit + clock | NOT RUN |
| ANI-06 | Terminal race | Terminal guard có | Cancel đúng frame complete; cancel hai lần | Tối đa một result đúng IDs, không next-step hai lần | Sau Basic | Race scheduling test | NOT RUN |
| ANI-07 | Reset/level change | Controller session wired | Animation cũ đang chạy rồi session mới | Callback cũ không đổi phiên mới; temp pivots được gỡ | Sau Basic | Integration | NOT RUN |
| ANI-08 | Event order | Core events approved | Switch→bridge→fall hoặc split→teleport theo Core | Giữ thứ tự đã nhận; không suy ra luật từ visuals | Advanced | Integration + visual | NOT RUN |
| ANI-09 | Goal clearance | Phương án goal-sink đã duyệt | GOAL_REACHED với block nominal 1s | Không xuyên rim 0.76s; effect không sửa State/goal rule | Sau Basic | Visual acceptance | NOT RUN |
| ANI-10 | Shutdown | Host teardown wired | Close window khi animating/paused | Cancel/drain/dispose an toàn; không callback vào nodes đã hủy | Sau Basic | Lifecycle integration | NOT RUN |

## Integration tương lai

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| INT-01 | Boundary | Controller đã có | Static review + instrument public API | Tài không sửa mesh/NodePath; Renderer không gọi solver/transition | Sau Basic | Architecture review | NOT RUN |
| INT-02 | Successful replay | Worker/controller wired | Solver thành công, path không rỗng | Reset initial theo default; từng action qua Core; chờ completion rồi next; tới goal | Sau Basic | End-to-end | NOT RUN |
| INT-03 | Empty success | Như INT-02 | SearchResult.actions=[] | Thành công 0 step; không bật failure hoặc animate giả | Sau Basic | Integration unit | NOT RUN |
| INT-04 | No solution | Như INT-02 | actions=None | NO_SOLUTION, không replay, length không giả success | Sau Basic | Integration unit | NOT RUN |
| INT-05 | Solver exception | Như INT-02 | Worker/solver raise exception | Hiện ERROR, GUI sống, không dùng metrics giả | Sau Basic | Error injection | NOT RUN |
| INT-06 | Stale search | Session IDs có | Search A, đổi level B rồi A trả | B không bị thay snapshot/HUD; bỏ result A | Sau Basic | Async integration | NOT RUN |
| INT-07 | New level during work | Cancel policy có | Đổi level trong search/replay | Có cancellation policy thật, không chỉ hide result; resource cleanup | Sau Basic | Integration | NOT RUN |
| INT-08 | HUD truthfulness | View model wired | Missing metrics, success 0, no-solution, stale update | Missing là —, zero thật giữ 0, peak đúng KiB; stale bị bỏ | Sau Basic | View-model unit | NOT RUN |
| INT-09 | Fragile split exception | Advanced Core approved | Single cube trên fragile; whole standing trên fragile | Phản ánh đúng outcome Core; single cube không gây broken event tự chế | Advanced | Core + renderer integration | NOT RUN |

## Visual

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| VIS-01 | Palette/style | Scene Basic chạy | Inspect color tokens + screenshot | Đúng Modern Light Minimal 3D, input HEX chuẩn; không thay bằng theme tối | 3 Basic | Static + visual | NOT RUN |
| VIS-02 | Block/floor contrast | Lights/materials có | 3 poses tại camera mặc định | Khối đọc rõ mặt, bevel và silhouette trên floor sáng | 3 Basic | Visual review | NOT RUN |
| VIS-03 | Goal/void | Như VIS-02 | Có cả goal và void trong khung hình | Goal có viền/thành/độ sâu; void là khoảng trống | 3 Basic | Visual review | NOT RUN |
| VIS-04 | HUD typography | Font được cấp phép có | Việt/Anh, label dài, minimum window | Đủ glyph, không cắt, đúng font size/contrast; placeholder không thành số giả | 3 Basic | Visual + text bounds | NOT RUN |
| VIS-05 | Widget states | Shell có | Normal/hover/pressed/disabled/focus qua visual inspection | Nhận biết trạng thái, gameplay disabled không gọi action | 3 Basic | Manual/visual harness | NOT RUN |
| VIS-06 | Background/shadow | Scene có fallback | Bật/tắt shadow mapping nếu hỗ trợ | Background không che board; shadow không phủ void/goal như sàn | 3 Basic | Visual quality matrix | NOT RUN |
| VIS-07 | Advanced symbols | Mapping Core approved | Soft/Heavy/Split/Bridge ở camera chuẩn | Circle/X/ngoặc và trạng thái cầu đọc được, active cube rõ | Advanced | Visual review | NOT RUN |

## Platform

| ID | Purpose | Preconditions | Input/setup | Expected result | Target | Type | Status |
|---|---|---|---|---|---|---|---|
| PLT-01 | Ubuntu smoke | Stage 3 cho phép dependency/runtime | Python/Panda pin đã thống nhất, mở scene | Một window/loop, hiện demo, close sạch; ghi driver/version | 3 Basic | Runtime smoke | NOT RUN |
| PLT-02 | Windows smoke | Như PLT-01 trên Windows | Cùng source/runtime target | Cùng tọa độ/layout và shutdown; không lỗi path/case/font | 3 Basic | Runtime smoke | NOT RUN |
| PLT-03 | Dependency/import | Runtime target được chọn | Pure imports và GUI entry point | Core/tests không bắt buộc mở Panda window; GUI có dependency rõ | 3 Basic | Import + environment | NOT RUN |
| PLT-04 | Portable paths | App entry point có | Chạy từ repo và working directory khác, path có space | Level/assets resolve theo package/root hợp lệ; không dùng absolute user path | 3 Basic | CLI smoke | NOT RUN |
| PLT-05 | DPI/framebuffer | Windows/Ubuntu scale được | Scale 100%,150%,200% nếu OS hỗ trợ | HUD/region/input thống nhất một đơn vị; không double scale | 3 Basic | Manual platform matrix | NOT RUN |
| PLT-06 | Resource cleanup | Scene load/dispose có | Lặp load/show/dispose, resize và close | Không nodes/tasks/request tăng vô hạn; không crash | 3 Basic | Runtime inspection | NOT RUN |

## Yêu cầu đồ án và nghiệm thu

| Yêu cầu người dùng/giảng viên cung cấp | Thiết kế bao phủ | Evidence tương lai |
|---|---|---|
| 3D thực, có thẩm mỹ/background | Visual/Geometry/Camera specs | GEO-*, VIS-*, PLT-01/02 |
| Solve tự lăn tới đích | Contract, Tài sở hữu replay | INT-02 và ANI-*; chưa thuộc Basic |
| Source ngoài có cite | Asset register actual/candidate | Review provenance trước import |
| GUI có thể khác công nghệ, solver Python | Đã chọn Panda3D + Core/solver Python | Architecture review INT-01 |
| Tối thiểu 10 test cases, nhóm dự kiến 16 level | Renderer nhiều kích thước/cơ chế; map/benchmark do nhóm khác | Bộ màn chính thức + benchmark ngoài phạm vi; không đếm unit tests GUI thay level |
| Split cube không làm fragile vỡ | Không cài luật trong visual | INT-09 |
| Peak memory | HUD field peak_python_memory_kib | INT-08; không gọi là tổng RAM |
| Fully observable | Adapter có thể nhận metadata đầy đủ, không yêu cầu khám phá switch | ADP-10 và review schema Phong |

Basic acceptance gồm GEO-01..10, LAY-*, CAM-*, ADP-01..09, VIS-01..06, PLT-* trong phạm vi đã implement. Nếu chưa có máy Windows, ghi BLOCKED/NOT RUN cho PLT-02, không giả PASS. Regression tests giai đoạn 1 chạy ở nhiệm vụ coding sau theo phạm vi được giao, không phải bằng chứng GUI đã đúng.

Approval gates ở [Handoff](STAGE2_HANDOFF.md), invariants ở [Contract](RENDER_CONTRACT.md), expected geometry/camera ở [Geometry](GEOMETRY_TILE_SPEC.md) và [Layout](LAYOUT_CAMERA_SPEC.md).
