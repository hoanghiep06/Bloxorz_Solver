# Stage 4 — Integration review package cho Phong / Tài

**ADVANCED CORE ADAPTER — PENDING PHONG SCHEMA.**

Đây là đề xuất để review, không phải team agreement đã duyệt. Source checkout tại
`b0e5f72` chưa có authoritative Advanced APIs. Stage 4 chỉ hoàn thiện visual layer
bằng typed DTO schema 2 và **VISUAL DEMO DATA**. Không chỉnh Core/Controller/Solvers,
không tạo `advanced_render_adapter.py` đọc raw numeric codes theo phỏng đoán.

## 1. Ranh giới dữ liệu đã triển khai

`advanced_contracts.py` là pure immutable data. `AdvancedSceneRenderer` chỉ nhận
board/snapshot, không biết Board/State Core, không gọi transition, không tự quyết
định validity, toggle, activation, fragile breakage hay split/merge.

Basic vẫn giữ `StaticBoardData`/`GameSnapshot` schema 1 và adapter hiện tại.
Advanced schema 2 là namespace DTO riêng; không chuyển Advanced về Basic hoặc
đánh rơi mechanics để tái sử dụng BasicSceneRenderer. Framing-only carrier trong
preview chỉ cấp dimensions cho camera, tuyệt đối không phải Core/render adapter.

Fixtures nằm riêng `advanced_fixtures.py`, không đưa vào `levels/`. Revision tăng
ở demo chỉ dùng kiểm tra renderer; không mang bằng chứng legal transition.

## 2. Các dữ liệu Phong cần xác nhận

| Domain | Data renderer đã nhận | Authority/mapping cần Phong xác nhận |
| --- | --- | --- |
| Coordinates | `(row,col)` zero-based, tuples, board bounds | Core cell order/origin; chuyển đúng một lần tại adapter |
| Static semantics | VOID/FLOOR/FRAGILE/BRIDGE; goals riêng | Semantic API hoặc named tile enum; không đoán numeric codes |
| Fragile | `board.fragile_cells` từ tile definitions | Fragile definitions, authoritative broken/intact state, lifetime qua reset |
| Bridges | ID +tuple cells; snapshot `present: bool` cho mọi ID | Stable ID→cells và ID→state mapping, không suy từ index `bridges_state` |
| Bridge naming | present = physical platform; absent = no platform | Core open/closed nghĩa gì; adapter phải map theo nghĩa chứ không tên |
| Switches | ID/cell/SOFT-HEAVY-SPLIT; complete activated IDs | Definitions và activation appearance source; không suy từ block occupancy |
| Switch relations | Không có switch→bridge logic trong renderer | Core giữ toggle/permanent/target relationships; adapter chỉ đọc resulting states |
| Whole block | Canonical orientation +anchor, WHOLE mode | After-state pose authoritative và footprint convention |
| Split | Hai stable cube IDs +cells | Identity từ lúc split, tồn tại qua movement, quy tắc/authority của merge |
| Active cube | ID thuộc hai IDs, hoặc None nếu không đánh dấu | Core/Controller nào cấp active ID; không nhận diện theo vị trí/màu |
| Board identity | Nonempty board_revision, content hash visual factory | Stable source identity/canonical ordering và khi nào reload |
| Terminal outcomes | Stage 4 chưa có event/outcome DTO | Win/loss/fall/goal outcomes và visual pose khi after-state không tồn tại |

Bridge state là complete set: không thiếu/unknown/duplicate IDs. Missing bridge
state bị reject, không default True/False. Empty activated IDs nghĩa là tất cả
inactive; empty broken cells nghĩa là tất cả fragile intact trong visual snapshot.
Adapter phải có dữ liệu authoritative cho các assertions đó; không dùng empty
containers để che nguồn data chưa hỗ trợ.

Profile hiện hỗ trợ goals trên FLOOR, switches trên non-goal FLOOR, mỗi bridge
cell thuộc đúng một bridge. Nếu Core có overlay khác, review và version/extend
visual profile trước; không âm thầm ép data vào profile này.

## 3. Adapter cần làm sau khi schema thật có sẵn

Tên đề xuất, **chưa có functions dưới đây trong source**:

```python
build_advanced_board_data(core_board, *, level_id) -> AdvancedBoardData
build_advanced_snapshot(core_state, *, board_data, session_id, state_revision) -> AdvancedSnapshot
```

Trước khi implement:

1. Đọc exact classes/enums/public APIs và test states thật của Phong.
2. Thống nhất semantic tables và stable IDs, không ép Core theo DTO visual.
3. Map immutable copies; không giữ mutable Core reference.
4. Kiểm tra toàn bộ references và board identity bằng `validate_snapshot`.
5. Test Basic compatibility và các authoritative advanced states (fragile/cầu/
   switches/split/active/mode). Có test proving source data không bị sửa.
6. Unsupported/unavailable semantics phải báo lỗi rõ, không fallback Basic.
7. Chỉ chuyển gate thành VERIFIED khi adapter/state tests thật đều đạt.

Hash visual factory deterministic với cùng ordered payload; tuple order là một
phần identity. Adapter tương lai có thể canonical-sort source collections trước
factory nếu source order không ổn định. Không reuse revision khi definitions đổi.

## 4. Các điểm Tài cần phối hợp

- Host tạo đúng một ShowBase/main loop. Renderer nhận roots, không tự chạy loop.
- Controller cung cấp session_id opaque và state_revision int >=0.
- Cùng session: revision giảm hoặc same revision/payload khác bị reject.
- Khác session: renderer chấp nhận replacement; Tài phải lọc async result/replay
  của session cũ trước khi gọi renderer. Renderer không đoán tuổi từ tên session.
- Khi load level: adapter board → `load_board` → complete snapshot →
  `show_snapshot`. Composition refit camera/update HUD khi board/viewport đổi.
- Khi state đổi: chỉ `show_snapshot`; không refit camera theo từng action.
- WHOLE/SPLIT/active ID phải lấy từ authority đã chốt. Không yêu cầu renderer
  tự split khi block chạm switch hoặc tự chọn active cube bên trái.
- Unknown bridge/switch/cube, board mismatch, mode conflict hay footprint ngoài
  bounds đều bị reject trước update; caller báo lỗi, không nuốt thành thành công.
- Controls hiện disabled, command=None; không nối gameplay qua Advanced Preview.
  Metrics vẫn unknown cho đến khi Controller có số đo thật.
- Cleanup: dashboard → presentation → renderer → host; mỗi renderer component
  dispose idempotent, không xóa foreign nodes. Gọi host destroy đúng một lần.
- NodePaths nội bộ không là API cho Controller. Main-thread UI calls, scheduling
  và transport của solver result do Controller phụ trách.

## 5. Dữ liệu cần cho Stage 5 — chưa implement

| Animation | Dữ liệu/decision pending |
| --- | --- |
| Basic roll | Before/after whole poses +action; persistent visual face basis; reject/accept/cancel ownership |
| Fragile break | Authoritative broken cells, trigger/event order, before/after support, terminal pose nếu fall |
| Bridge state | ID→present before/after, event order, trigger/outcome; không suy open=present |
| Switch appearance | Activated IDs trước/sau, activation/deactivation events và timing |
| Split | Source whole pose, split outcome, hai cube IDs/destination correspondence và event order |
| Merge | Hai source cube IDs/poses, whole destination/orientation, identity retirement và merge event |
| Active change | Supplied active ID và thời điểm đổi trong request; không suy từ keyboard/UI màu |
| Fall/goal | Explicit outcome/event; terminal pose/bounds khi không có valid after-state |
| Goal sink | Clearance/visual transition vì aperture .76 <width1, cavity .14; tránh xuyên rim |

Rolling cơ bản có thể bắt đầu ở mức visual prototype sau Stage 4; current static
absolute poses không giữ rotation history nên chưa đủ cho chuỗi rolling có
face/inlay liên tục. Không tự gọi canonical orientation là visual history.

Các APIs `AnimationRequest`, `AnimationResult`/Completion, `animate`,
`pause_animation`, `resume_animation`, `cancel_animation`, `set_playback_rate`
trong tài liệu Stage 2 là **proposals**, không tồn tại trong implementation Stage 4.
Cần chốt với Tài IDs (session/board/revision/request), acceptance/error behavior,
one terminal completion cho accepted request, cancellation barrier, reset/resync,
callback threading và cleanup khi window đóng. Không suy `Core.transition=None`
luôn đồng nghĩa fall, và không gọi callback animation giả từ `show_snapshot`.

## 6. Trạng thái handoff

| Hạng mục | Trạng thái |
| --- | --- |
| Visual data schema 2 / geometry / static state renderer | IMPLEMENTED +TESTED |
| Standalone advanced fixtures và disabled dashboard | IMPLEMENTED +Ubuntu visual verified |
| Basic schema 1/adapter/renderer compatibility | PASS: 243 old tests, 3 old native entry points |
| Phong Advanced schema authority | PENDING |
| Advanced Core adapter và integration tests | PENDING |
| Tài session orchestration / mode / gameplay integration | PENDING |
| Events/outcomes và AnimationRequest/Completion/Cancel | PENDING review Stage 5 |
| Windows native | NOT TESTED |

Không cần chờ Core để review visuals hiện tại. Không tuyên bố đã chơi được hay
giải được Advanced levels từ bộ fixtures này. Báo cáo QA, exact commands,
screenshots, resource counts và acceptance matrix nằm trong
[Stage 4 renderer report](STAGE4_ADVANCED_RENDERER.md).
