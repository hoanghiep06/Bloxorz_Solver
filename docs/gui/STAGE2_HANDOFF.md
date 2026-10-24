# Chặng 2 — Handoff cho Phước và coding agent Chặng 3

Ngày: **22/10/2026**. Baseline local: **7e483b6c56b6b07799119e8b5721819c0346c541**. Branch: **feat/phuoc/3d-renderer**.

**DESIGN PACKAGE COMPLETE**. **INTEGRATION CONTRACT APPROVED: chưa có xác nhận**. Có thể tiếp tục Basic Renderer độc lập từ baseline đã kiểm chứng; chưa được tự tích hợp Advanced hoặc Controller.

## Mục lục

1. [Executive Summary](#executive-summary)
2. [Quyết định và tài liệu bàn giao](#quyết-định-và-tài-liệu-bàn-giao)
3. [Kiến trúc và ownership](#kiến-trúc-và-ownership)
4. [Phạm vi coding Chặng 3](#phạm-vi-coding-chặng-3)
5. [Acceptance Basic Renderer](#acceptance-basic-renderer)
6. [Risk register](#risk-register)
7. [Bảng xác nhận với nhóm](#bảng-xác-nhận-với-nhóm)
8. [Review và contract change](#review-và-contract-change)
9. [Checklist và readiness](#checklist-và-readiness)

## Executive Summary

Gói thiết kế hoàn tất phần 2.1–2.5: direction sáng tối giản, bảng màu, layout pixel, perspective camera và fit theo corner projection, mesh/tile poses, DTO/animation lifecycle, nguồn/giấy phép và test plan. Chỉ tạo Markdown; chưa có GUI hoặc runtime test.

Repository vẫn có Core basic và GUI placeholders rỗng. So với audit Chặng 1, branch đã đổi theo yêu cầu người dùng; HEAD/source giữ nguyên. Phong đang refactor và Tài đang thiết kế theo context người dùng, nhưng chưa có implementation mới ở checkout này. Không fetch để suy đoán tiến độ thành viên.

**Điểm thay đổi readiness so với Chặng 1:** Chặng 1 chặn kiến trúc tích hợp khi chưa có contract. Chặng 2 đã cung cấp một contract đề xuất cụ thể và một Basic profile độc lập dùng source hiện tại; vì vậy thiếu contract Advanced không còn là lý do chặn mọi công việc Basic. Điều này không biến các đề xuất thành API được Phong/Tài duyệt.

## Quyết định và tài liệu bàn giao

| Phần | Quyết định | Trạng thái |
|---|---|---|
| 2.1 | Panda3D, Modern Light Minimal 3D, palette, material families, background sáng | USER APPROVED DESIGN |
| 2.2 | Reference 1280×720; bốn rectangles; perspective elevation 45°, azimuth 30°, vertical FOV 45° | USER APPROVED DESIGN |
| 2.2 chi tiết | Azimuth đo từ −Y về +X; responsive cố định panel; padding projection 13% mỗi cạnh | PROPOSED tuning/implementation convention |
| 2.3 | X=column, Y đảo row, Z up, s=1, three nominal poses | USER APPROVED DESIGN |
| 2.3 chi tiết | Bevel/thickness/seam/rim và goal well theo spec | PROPOSED tuning; cần visual test |
| 2.4 | Core giữ luật, Renderer giữ visuals, Controller điều phối; một host | USER APPROVED DESIGN về boundary |
| 2.4 DTO/API | StaticBoardData, GameSnapshot, HUD VM, AnimationRequest/Result và session lifecycle | PROPOSED CONTRACT / PENDING TEAM APPROVAL |
| 2.5 | Procedural-first, code/assets ngoài có provenance; không import ở Chặng 2 | USER APPROVED DESIGN |
| Test/runtime | Không giả PASS hoặc benchmark | NOT TESTED, các cases NOT RUN |

| Tài liệu | Vai trò |
|---|---|
| [README](README.md) | Entry point, labels, source audit và cách đọc |
| [VISUAL_SPEC](VISUAL_SPEC.md) | Palette, vật liệu, ánh sáng, background, UI/animation art |
| [LAYOUT_CAMERA_SPEC](LAYOUT_CAMERA_SPEC.md) | Region/hit areas, responsive, DisplayRegion/pixel2d, camera math |
| [GEOMETRY_TILE_SPEC](GEOMETRY_TILE_SPEC.md) | Coordinates, meshes, poses, Advanced identity, pivot |
| [RENDER_CONTRACT](RENDER_CONTRACT.md) | Data, adapter, API/lifecycle, replay boundary, versioning |
| [ASSET_CREDITS](ASSET_CREDITS.md) | Actual-used rỗng, candidates với URL/license/version/usage |
| [TEST_PLAN](TEST_PLAN.md) | Test cases Basic và tương lai, tất cả NOT RUN |
| Tài liệu này | Phạm vi thực thi tiếp theo, rủi ro, approvals, readiness |

Nguồn chuẩn theo từng chủ đề nằm ở README. Tránh copy bảng màu/fields sang nhiều nơi rồi sửa một bản. Chọn Panda3D 1.10.16 theo [stable downloads](https://www.panda3d.org/download/) và [wheel files](https://pypi.org/project/Panda3D/1.10.16/); chưa xác nhận cửa sổ chạy được. CPython hiện tại 3.14.4; runtime chung nhóm còn pending.

## Kiến trúc và ownership

Host tạo ShowBase, roots và lifecycle. Controller gọi Core, adapter rồi Renderer; Renderer trả animation terminal result cho Controller. Solver worker tương lai chỉ nhận data thuần và trả actions/metrics. Không có coupling Core→Panda3D, Renderer→solver hoặc Controller→private NodePath.

| Vùng | Chủ trì | Review/phối hợp |
|---|---|---|
| Core/State/schema/events | Phong | Phước/Tài xác minh dữ liệu đủ dùng |
| Renderer/camera/light/material/background | Phước | Phong review đúng cơ chế |
| Adapter và render DTO | Phước | Phong duyệt domain mapping, Tài duyệt context/session |
| HUD visual shell/theme | Phước | Tài cung cấp VM và callbacks hành vi sau này |
| Animation từng action | Phước, sau Basic | Tài duyệt sequencing/completion/cancel |
| Input/game session/solver/replay/worker | Tài | Phước kiểm thử chéo Controller |
| Host wiring, contracts, dependencies, entry point | Shared | Phước host engine, Tài controller integration; từng thay đổi có một owner |

Các file dễ conflict: `src/gui/__init__.py`, host/entry point, contracts, requirements và docs hợp đồng. Core refactor cũng có thể phá API mà Git không báo conflict.

Nhánh cá nhân đã tồn tại là `feat/phuoc/3d-renderer`; nhánh chung `feat/team-code/phase2-game-gui` dùng cho tích hợp theo thỏa thuận nhóm. Gói này không ra lệnh chuyển nhánh/merge/push. Khi có nhiệm vụ coding tiếp theo, kiểm tra thay đổi local và thống nhất cách đưa code lên nhánh chung; không tự ghi đè phần thành viên khác.

## Phạm vi coding Chặng 3

Đây là kế hoạch cho nhiệm vụ được giao tiếp theo, **không phải công việc đã triển khai trong Chặng 2**.

### Được chuẩn bị triển khai: Basic 3D Renderer độc lập

- Một Panda3D host, một cửa sổ/event loop; entry point GUI riêng, bảo toàn CLI gốc.
- Static board renderer cho Floor/Void/Goal của profile 0/1/2 đã mô tả.
- Main block ba orientation, show_snapshot tĩnh; camera, lighting, procedural background.
- HUD visual shell đầy đủ vị trí controls/metrics, gameplay controls disabled và placeholders.
- Basic RenderAdapter và pure DTO/validation không phụ thuộc Panda3D.
- Unit tests mới trong phạm vi được cho phép; smoke/visual test trên môi trường thực.

Có thể kiểm tra ba poses bằng fixtures hoặc thao tác visual inspection; không biến pose inspector thành manual gameplay Controller mới. Không tạo solution path giả để trông như đã có replay.

### File dự kiến cho coding agent, chưa tạo

| Path dự kiến | Nội dung được phép ở Basic | Lưu ý |
|---|---|---|
| `src/gui/app.py` | Host/window/display region/bootstrap | Phước engine; không triển khai Controller |
| `src/gui/__main__.py` | Entry point GUI độc lập | Dự kiến chạy module GUI sau khi implement; hiện chưa chạy được |
| `src/gui/contracts.py` | Basic StaticBoardData/GameSnapshot/HUD VM | Chưa cần class Advanced/animation implementation |
| `src/gui/render_adapter.py` | Mapping baseline, IDs context, immutable data | Không sửa Core |
| `src/gui/renderer.py` | Load/show/dispose, geometry, scene/camera/light | Helper đủ dùng, chưa cần class cho từng tile |
| `src/gui/hud.py` | Visual shell, labels, disabled controls | Không nối solver/input/replay callbacks |
| `src/gui/__init__.py` | Exports tối thiểu nếu cần | Tránh import ShowBase qua pure contract/Core |
| `tests/gui/` hoặc file test GUI mới được thống nhất | Math/adapter/layout/smoke tests | Không sửa test giai đoạn 1 để che lỗi |
| `docs/gui/` | Ghi evidence/điều chỉnh thiết kế sau review | Không đổi pending thành approved tùy tiện |

`animation.py` thuộc chặng sau; không cần tạo ở Basic. Không sửa `main.py`, Core, Controller, Solver, level/benchmark ngoài nhiệm vụ được cấp riêng. Đề xuất dependency runtime `panda3d==1.10.16`; DirectGUI/Intervals thuộc engine, không cần package riêng. Việc cài runtime/chỉnh requirements phải nằm trong quyền của nhiệm vụ coding tiếp theo; Chặng 2 không làm.

Asset strategy Basic: procedural meshes/materials/background; chưa cần glTF importer/PBR plugin. Font có thể dùng built-in để smoke trước, nhưng nghiệm thu dấu Việt cần font hợp lệ/glyph đủ; nếu cần import Noto, nhiệm vụ sau phải cho phép và cập nhật credits, không dùng font hệ thống tuyệt đối làm giải pháp mặc định.

### Tuyệt đối ngoài Basic

Advanced Mechanics, chỉnh State/Board/Transition, Controller của Tài, solver buttons hoạt động, manual play, solver replay, full rolling animation, split/merge gameplay, worker process, solver refactor, benchmark, tự push/merge. Chọn engine không cho phép làm lấn các phần đó.

## Acceptance Basic Renderer

1. App mở/đóng được với một host; source hiện tại vẫn chạy CLI/tests cũ theo nhiệm vụ coding sau.
2. Vẽ demo 4×7 đúng goal field, void thật, floor có thickness và main block đúng ba poses/bottom.
3. Đúng Modern Light Minimal 3D, background sáng, HUD shell rõ và không giả chức năng/metrics.
4. Camera perspective giữ vertical 45°, fit projection của đủ góc AABB với padding; đổi level/resize không clipping.
5. Đúng layout ở năm kích thước mục tiêu, minimum 1024×720; font không co vô hạn.
6. Adapter không mutate Core hoặc gán mã Advanced tùy tiện; unknown mappings có lỗi rõ.
7. Show_snapshot không rebuild static board; load/show/dispose có cleanup.
8. Tests/evidence Basic trong TEST_PLAN thực sự được chạy ở nhiệm vụ implementation. Windows chưa thử phải ghi NOT RUN/BLOCKED, không công bố cross-platform pass.

Đây là acceptance cho renderer tĩnh, **chưa đủ nghiệm thu game đồ án cuối**. Auto-roll từ Solve, Advanced, ≥10 level và benchmark là các integration gates khác.

## Risk register

Probability chưa có dữ liệu định lượng: **UNKNOWN** cho toàn bảng; severity là đánh giá kỹ thuật theo ảnh hưởng. Không coi mọi rủi ro là blocker của Basic tĩnh.

| ID | Risk | Severity / probability | Impact | Owner | Mitigation | Gate Basic / Advanced |
|---|---|---|---|---|---|---|
| R01 | Core refactor | Cao / UNKNOWN | Mapping baseline đổi | Phong + Phước | Audit HEAD trước coding, adapter riêng, pin profile | Basic: không nếu baseline còn đúng; Advanced: có |
| R02 | Tile schema chưa chốt | Cao / UNKNOWN | Vẽ sai fragile/bridge | Phong | Basic chỉ 0/1/2, unknown reject | Basic: không; Advanced: có |
| R03 | Advanced State thiếu split/active mapping | Cao / UNKNOWN | Không thể vẽ state thật | Phong | Không fabricate cubes/IDs; contract v1 review | Basic: không; Advanced: có |
| R04 | Transition thiếu outcome/events | Cao / UNKNOWN | Lẫn reject/loss, sai thứ tự effect | Phong + Tài | Rich gameplay result hoặc API tương đương do Core chọn | Basic: không; Advanced/animation: có |
| R05 | Controller chưa có implementation | Cao / UNKNOWN | Chưa manual/replay | Tài | Basic độc lập, shell disabled; duyệt lifecycle trước wiring | Basic: không; Integration: có |
| R06 | Panda3D chưa runtime-tested | Cao / UNKNOWN | Window/driver có thể lỗi | Phước | Smoke sớm ở nhiệm vụ coding, ghi GPU/runtime | Basic runtime acceptance: có; design: không |
| R07 | Solver chỉ initial state | Cao / UNKNOWN | Replay lệch phiên chơi | Tài + solver owners | Default reset initial, current-state API riêng | Basic: không; replay: có |
| R08 | Synchronous solver block loop | Cao / UNKNOWN | GUI treo khi solve | Tài | Thiết kế async/process, IDs, cancellation thật | Basic: không; replay integration: có |
| R09 | Asset license chưa audit từng file | Vừa–cao / UNKNOWN | Không đủ clearance/credit | Phước | Procedural-first, register metadata trước import | Basic: không nếu không import; asset import: có |
| R10 | Shared file conflicts | Vừa / UNKNOWN | Ghi đè wiring/dependency | Cả ba | Ownership, review, commits atomic khi được giao | Không tự chặn; cần review trước merge |
| R11 | Camera không fit map lớn | Cao / UNKNOWN | Cắt block/edge | Phước | Corner projection, viewport aspect, test wide/tall | Basic acceptance: có nếu test fail |
| R12 | Pivot/tọa độ sai | Cao / UNKNOWN | Trượt/xuyên sàn/snap mặt | Phước | Geometry math, centered mesh, future roll matrix | Basic poses phải đúng; rolling: chặn nếu sai |
| R13 | Windows/Ubuntu khác driver/path/DPI | Vừa–cao / UNKNOWN | Chạy một máy, lỗi máy kia | Phước + Tài | Platform smoke, portable paths/font | Chặn tuyên bố platform pass nếu chưa thử |
| R14 | Nhầm peak allocations với tổng RAM | Vừa / UNKNOWN | Báo cáo/HUD sai | Tài + benchmark owner | Field peak_python_memory_kib, nhãn đúng | Basic placeholder: không; metric integration: có |
| R15 | Goal aperture 0.76s < block 1s | Vừa / UNKNOWN | Sink effect xuyên rim | Phước | Review thủ pháp visual trước goal animation | Basic tĩnh: không; goal-sink: có |
| R16 | Stale callback/reset race | Cao / UNKNOWN | Phiên cũ đổi phiên mới | Tài + Phước | IDs, terminal guard, cancel/resync/drain | Basic identity validation; integration cần duyệt |

Các phát hiện solver từ audit như A* thiếu `is_standing()` call và UCS `solution_state/solution_states` không được sửa trong docs task hoặc Basic Renderer. Người phụ trách solver cần review riêng trước công bố sáu solver đã nghiệm thu toàn diện. Phase 1 merge không đồng nghĩa mọi corner case đã được chứng minh.

## Bảng xác nhận với nhóm

**Tất cả câu hỏi dưới đây: PENDING TEAM APPROVAL.** Proposed default không phải câu trả lời đã duyệt. `Không` ở cột Basic nghĩa là có thể tiếp tục Basic độc lập theo profile hiện tại; không có nghĩa có thể bỏ qua trước tích hợp.

### Phong

| ID / Câu hỏi | Proposed default | Người xác nhận | Ảnh hưởng | Chặn Basic? | Chặn Advanced? |
|---|---|---|---|---|---|
| Q-P1 Tile schema chính thức? | Semantic kinds qua adapter; không đoán numeric IDs; Basic 0/1/2 | Phong | Mapping toàn board | Không | Có |
| Q-P2 Bridge IDs/initial states? | Stable IDs, cells tĩnh, state map động; bool meaning explicit | Phong | Cầu đóng/mở đúng | Không | Có |
| Q-P3 Split State biểu diễn thế nào? | Mode WHOLE/SPLIT, hai cube IDs + cells; Core chọn identity/canonicalization | Phong | DTO/hash/replay | Không | Có |
| Q-P4 Active cube được quản lý thế nào? | Active ID thuộc domain nếu ảnh hưởng successor | Phong + Tài | Điều khiển và search state | Không | Có |
| Q-P5 Transition outcome/events? | Core cung cấp ordered semantics; giữ compatibility solver nếu cần | Phong | Chuỗi animation đúng | Không | Có |
| Q-P6 Rejected vs falling move? | Kết quả phân biệt, terminal visual pose rõ, không dùng mọi None là loss | Phong | Fall/loss lifecycle | Không | Có |
| Q-P7 Actions mới sau split? | Core định nghĩa action đổi cube/actor và cost, path serialize được | Phong + solver owners + Tài | Solver/manual/replay thống nhất | Không | Có |

### Tài

| ID / Câu hỏi | Proposed default | Người xác nhận | Ảnh hưởng | Chặn Basic? | Chặn Advanced? |
|---|---|---|---|---|---|
| Q-T1 Xác nhận một host khi tích hợp? | Một ShowBase/loop đã là boundary người dùng khóa; Controller dùng host này | Tài | Không tạo loop thứ hai | Không | Có trước wiring |
| Q-T2 Ai điều phối ShowBase lifecycle? | Phước engine/bootstrap, Tài commands/shutdown sequencing phối hợp | Phước + Tài | Init/drain/dispose | Không | Có trước wiring |
| Q-T3 Controller gửi snapshots thế nào? | Controller gọi adapter rồi public renderer API trên main thread | Tài | Data ownership | Không | Có |
| Q-T4 Replay initial hay current? | Solve/replay từ initial; reset trước replay | Tài | Path đúng starting state | Không | Có với replay |
| Q-T5 Callback animation dạng gì? | Callback nhận AnimationResult data; host dispatcher, IDs, tối đa một terminal | Tài + Phước | Completion race/reentrancy | Không | Có |
| Q-T6 Reset/cancel semantics? | Session tăng trước cancel, resync snapshot, bỏ old result | Tài + Phước | Phiên không bị đảo | Không | Có |
| Q-T7 Rate và step delay? | Rate 0.25–4×; delay riêng, pause không dùng rate=0 | Tài | Playback UI/animation | Không | Có với replay |
| Q-T8 Solver worker thế nào? | Process là ứng viên; không Panda objects, có IDs/timeout/cancel policy | Tài | Responsiveness/metrics | Không | Có với solver UI |
| Q-T9 HUD interface nào? | HUD VM riêng, public show_hud, controls state/callback từ Tài | Tài + Phước | Metrics và status thật | Không cho shell | Có |

### Cả nhóm

| ID / Câu hỏi | Proposed default | Người xác nhận | Ảnh hưởng | Chặn Basic? | Chặn Advanced? |
|---|---|---|---|---|---|
| Q-G1 Contract version đầu? | v1, Basic profile; reject unknown version | Cả ba | DTO compatibility | Không cho độc lập | Có |
| Q-G2 Shared files ownership? | Một owner mỗi change; Phước host, Tài wiring; contracts review chung | Cả ba | Giảm ghi đè | Không file riêng | Có trước integration |
| Q-G3 PR/review flow? | Phong review Renderer; Tài review completion/API; merge vào nhánh chung khi được giao | Cả ba | Bàn giao có kiểm tra | Không coding local | Có trước merge |
| Q-G4 Python runtime chung? | Đề xuất CPython 3.14.x thường + Panda3D 1.10.16 theo môi trường hiện tại, xác minh Windows | Cả nhóm | Dependency/wheels | Cần chọn trước smoke | Có |
| Q-G5 Core đổi thì cập nhật contract ra sao? | Phong thông báo breaking; update adapter/spec/examples/tests cùng review; tăng version khi cần | Cả ba | Không silent fallback | Không nếu Basic baseline giữ | Có |

Font asset cụ thể, tuning đèn, độ dày/bevel và thủ pháp goal-sink cần Phước review visual ở runtime; không cần đổi palette hay engine để giải các tuning này.

## Review và contract change

Trước coding: agent đọc README→Visual→Layout→Geometry→Contract→Tests→handoff, audit lại Git và source, bảo toàn thay đổi đang có. Không tự đồng bộ remote hoặc đổi nhánh chỉ từ các hướng dẫn lịch sử trong README gốc.

Bàn giao cho Phong: bảng tile/State mapping, static/dynamic boundaries, unknown handling và fixtures ba poses; xin xác nhận các Q-P trước Advanced. Bàn giao cho Tài: receipt/callback, session/revision, busy/cancel/resync, HUD fields, Solve origin và ví dụ reset. Đây là gói tài liệu để người dùng chia sẻ; không gửi tin nhắn thành viên thay người dùng trong nhiệm vụ này.

Khi contract đổi: ghi quyết định và bằng chứng approval, cập nhật nguồn chuẩn rồi sửa links/examples/tests liên quan; không sửa source thành viên khác để làm renderer tạm chạy. Vẫn giữ approved visual direction trừ khi người dùng đổi yêu cầu.

## Checklist và readiness

### Bàn giao thiết kế

- [x] Đủ tám tài liệu 2.1–2.5, nguồn chuẩn từng chủ đề rõ.
- [x] Phân biệt VERIFIED IN SOURCE, USER APPROVED DESIGN và PROPOSED/PENDING.
- [x] Basic profile độc lập, scope Chặng 3 và Advanced gates đã tách.
- [x] Có geometry/camera math, data examples, architecture/sequence diagrams.
- [x] Có source/license register actual-used rỗng và future tests NOT RUN.
- [ ] Phong duyệt Core/Advanced contract.
- [ ] Tài duyệt Controller/animation/HUD contract.
- [ ] Runtime tests Basic/Windows/Ubuntu được thực thi ở nhiệm vụ tiếp theo.

### Validation bộ tài liệu

Kết quả review Chặng 2 (kiểm tra tài liệu, không phải runtime GUI):

- Đủ tám Markdown không rỗng; links nội bộ/anchors, JSON minh họa, code fences và số cột bảng đã được kiểm tra. Một anchor mục lục sai đã được sửa trước vòng kiểm tra cuối.
- Palette khớp đủ 18 token/HEX gốc. Nguồn chuẩn và nhãn pending/implemented đã được review chéo.
- Tính số học năm window sizes xác nhận bốn region luôn trong cửa sổ và không overlap.
- Kiểm tra công thức camera bằng số học thuần: 6 board bounds × 5 viewports × 8 corners = 240 projections, đúng NDC padding và near/far. Không import/chạy Panda3D.
- 66 test case tương lai đều NOT RUN; không đánh dấu runtime PASS. Mermaid đã review cấu trúc text/fence, chưa render bằng engine Mermaid.
- Manifest SHA-256 của 30 file ngoài `docs/gui/` trước/sau không đổi: `9bc21c2dff0eccad577370ded75023c3144ef133e0f018b0212c9773f7223523`.
- Trước: working tree sạch. Sau: chỉ tám Markdown mới dưới `docs/gui/`, untracked/chưa stage; branch và HEAD giữ nguyên. Tracked diff và staged diff rỗng; diff từng file mới được đọc dưới dạng no-index để không stage.
- Không tạo/chuyển branch, fetch/pull, commit/push/merge, cài package, sửa source hoặc chạy GUI. Giữ tài liệu chưa commit cho người dùng review.

### Readiness

**STAGE 2 DESIGN PACKAGE COMPLETE — TEAM APPROVAL REQUIRED FOR INTEGRATION**

Basic Renderer độc lập đã có đầu vào thiết kế đủ rõ để triển khai trong nhiệm vụ Chặng 3 được giao sau. Chưa có quyền thực thi Chặng 3 trong lượt biên soạn này. Contract Advanced và Controller còn pending không chặn geometry/camera/HUD shell Basic, nhưng chặn việc tự nối gameplay/solver/animation nâng cao hoặc tuyên bố game hoàn chỉnh.
