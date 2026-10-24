# Stage 5 — Phong / Tài integration review package

**CORE INTEGRATION PENDING — CONTROLLER INTEGRATION PENDING.**

Các animation APIs dưới đây đã có source và tests trong phạm vi GUI. Mapping với
Core/Controller và quyết định lifecycle nhóm vẫn **PENDING TEAM APPROVAL**. Không
có Advanced Core adapter, gameplay Controller, solver queue/replay hoặc action-bound
HUD được triển khai trong Stage 5.

## 1. Dữ liệu Phong cần cung cấp

| Dữ liệu | Render/animation contract | Authority cần xác nhận |
| --- | --- | --- |
| Before/after state | Basic GameSnapshot hoặc AdvancedSnapshot, cùng schema/board/session | State thật trước/sau transition, orientation/anchor/cube positions |
| Direction | RollDirection.RIGHT/LEFT/UP/DOWN | Mapping Core action; UP là world+Y/row giảm |
| Bridge state | Stable bridge_id, complete `present: bool` | Exact ID→cells và Core open/closed→platform present/absent |
| Fragile | Definitions và explicit FRAGILE_BREAK(cell) | Khi nào vỡ; broken-state lifetime/reset semantics |
| Switch | switch_id/kind +explicit activate/deactivate event | Activation status, toggle/permanent semantics và ordering |
| Split | Whole source, two stable target IDs/cells, ordered ID correspondence | Ai là lower/upper half trong visual split; identity lifetime |
| Merge | Hai source IDs/poses và whole destination | Correspondence, identity retirement, outcome semantics |
| Active cube | ID hoặc explicit None | Core/Controller authority của selection, không suy từ vị trí/màu |
| Fall | Explicit FALL outcome +actor ID | Không coi mọi transition=None là fall; terminal visual source pose |
| Goal | Explicit GOAL_COMPLETE, standing whole trên goal | Win/outcome authority; GUI không tự quyết thắng |
| Event timing/order | Ordered events với normalized start/end | Semantic ordering do caller xác nhận, không lấy từ collision hoặc diff inference |

Các cube split trùng cell hoặc actor đứng trên VOID vẫn có thể được structural DTO
biểu diễn. Animation chỉ kiểm tra geometry của request; không thực thi luật Board.
Không được gọi fixtures là valid Core transitions hay solved route.

## 2. Request/result đã implement

```python
AnimationRequest(
    schema_version=1,
    request_id=...,
    before_snapshot=...,
    after_snapshot=...,     # None chỉ cho explicit TERMINAL
    kind=AnimationKind.ROLL,
    duration=.6,            # seconds at rate1
    direction=RollDirection.RIGHT,
    actor_id=None,          # None = WHOLE; string = supplied cube ID
    events=(),
    terminal=None,
)
```

Session/board/from/to revisions là derived properties từ supplied snapshots,
không có hai bộ fields dễ lệch. Animation schema1 là type namespace riêng, không
sửa Basic schema1 hoặc Advanced schema2. Contracts immutable và không chứa engine
objects. `AnimationEvent` có kind, start/end trong[0,1], target_id/cell/ordered
cube_ids/active_cube_id theo event type. Typed payload không phù hợp bị reject.

Supported combinations: one-actor ROLL +optional surface events; EFFECTS với
nonrepeated surface targets và tối đa một mode/active event; TERMINAL chỉ một
matching FALL/GOAL_COMPLETE event và explicit TerminalVisualOutcome. Roll+mode/
active/terminal trong cùng request không được hỗ trợ. Tách storyboard hoặc review
profile mới; không chế after-state để lách validation.

`validate_request` so after-state với explicit events như consistency check; không
sinh events từ differences. RollPlan dự đoán endpoint chỉ để verify supplied
center/extents, không trở thành authoritative Core transition.

## 3. Composition boundary

Khi đã có **một** app host, dùng public ownership boundary:

```python
from src.gui.animation_contracts import as_visual_board
from src.gui.animation_effects import AnimatedSurfaceLayer
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.animation_manager import AnimationManager

visual_board = as_visual_board(board_data)
surfaces = AnimatedSurfaceLayer(app.dynamic_tile_root, visual_board)
renderer = AdvancedSceneRenderer(
    app.static_board_root, surfaces.renderer_root, app.block_root,
)
renderer.load_board(visual_board)
manager = AnimationManager(
    renderer, board_data, before_snapshot, app.block_root,
    surface_layer=surfaces, task_mgr=app.taskMgr,
)
```

Caller vẫn phối hợp presentation/camera/HUD và cleanup theo đầy đủ example trong
Animation Preview. Không tạo ShowBase thứ hai. `surfaces.renderer_root` là layer
chuyên dụng, không đặt foreign nodes vào đó. Surface pool không hide host root.

`renderer.set_actor_visuals_visible(False)` là public lease do manager giữ suốt
lifetime, kể cả idle giữa requests. Không gọi show_snapshot trên renderer thay
cho manager khi đang giữ lease; không lấy private NodePaths để animate. Static
snapshot canonical basis không được làm mất quaternion face history của rig.

Task ownership chọn một:

- Pass task_mgr: manager sở hữu một runtime updater, dùng elapsed seconds của Panda.
- task_mgr=None: caller chịu trách nhiệm `advance(dt)` trên main thread.

Không vừa pass task_mgr vừa tự advance mỗi frame. New Preview dùng một finite
fixture driver và task_mgr=None; driver này không là API queue cho solver replay.

## 4. Tài: session, revision và accepted request

1. Core/Controller cấp session_id, board_revision và state revisions; manager không
   tạo gameplay session hoặc so tuổi opaque strings.
2. Before phải khớp toàn bộ `manager.current_snapshot`. After giữ schema/board/
   session và revision tăng. Manager chưa commit after trước completion.
3. Tài phải lọc stale async results/callbacks bằng session+board+request+revision
   trước khi áp dụng replay cursor/HUD hoặc submit request kế tiếp.
4. Manager busy raise RuntimeError; invalid raise trước acceptance, không callback.
   Không có queue ngầm. Recent `(session_id,request_id)` duplicates bị reject,
   cache bounded128; caller vẫn phải đảm bảo ID policy và stale filtering của mình.
5. Accepted bắt đầu khi context đã được cài sau validation. Engine failure ngay
   sample0 có thể phát FAILED callback đồng bộ rồi submit raise. Exception handler
   của Controller không được phát terminal notification thứ hai.
6. Core có thể đã tính state sau khi chuẩn bị animation, nhưng GUI cancel không
   có nghĩa Core rollback. Nếu Core hiện ở state khác known before, caller phải
   explicit resync đúng authoritative snapshot sau cancel.

## 5. Completion callback và cancellation barrier

`submit(request, on_finished=None)` thành công trả None. Callback nếu có nhận
AnimationResult đồng bộ, trên main thread, tối đa một lần cho accepted request.
Result gồm request/session/board IDs, from revision, committed to revision hoặc
None, COMPLETED/CANCELLED/FAILED, terminal outcome/error phù hợp.

- COMPLETED bình thường: supplied after đã commit, continuous visual quaternion
  được giữ; callback có thể submit compatible request kế tiếp.
- COMPLETED terminal: to revision=None và explicit outcome, current_snapshot vẫn
  là known before. Chờ caller reset/resync, không tự chuyển level/victory UI.
- CANCELLED: before visuals/Q được restore, không success, không after commit.
- FAILED: best-effort before restore, error và exception propagate. Engine failure
  không recover được phải báo, không coi completion thành công.

Callback tự raise không tạo FAILED result lần hai. Bookkeeping terminal được làm
trước callback. Tài phải xử lý callback exceptions của chính mình.

`cancel()` restore known before-state, không dùng Interval.finish. Repeated cancel
khi idle trảFalse. `resync(snapshot)` validate trước khi cancel; cancel accepted
request một lần rồi apply canonical pose. Trong resync/dispose barrier, callback
không được reentrant submit; caller chờ resync trả về rồi bắt đầu request mới.
Cancel thông thường cho phép callback xử lý state, nhưng chỉ nên auto-submit sau
COMPLETED, tránh vô tình phát lại request đã cancel.

## 6. Pause/resume/rate, reset và đổi board

`pause()`/`resume()` trảbool và no-opFalse khi không applicable. `set_playback_rate`
nhận finite[.05,8], không bool; .25/.5/1/2/4 có hỗ trợ. Đổi speed khi paused không
nhảy transform; resume tiếp tục progress hiện tại. Rate giữ qua requests.

Explicit resync intentionally reset visual face basis về canonical, đồng thời
restore scale/opacity sau terminal proxy. Same-session stale/conflicting revision
bị reject; opaque new session do caller cấp được chấp nhận trên cùng board.

Manager board-bound: khi đổi board, dispose manager, renderer, surface pool đúng
ownership rồi tạo composition tương ứng; camera refit/HUD do caller phối hợp.
Không đổi renderer board ở phía sau manager đang hoạt động.

## 7. Face history và Advanced cinematic limits

Whole body dùng local asymmetric inlay; split cubes có local amber bevel marker
nằm trong nominal cuboid, không dùng decal nhô khỏi mặt có thể xuyên floor sau roll.
Successful rolls giữ Q qua nhiều steps; không lấy after canonical orientation để
reset mặt. Active indicator là cue riêng theo ID, không thay face-history marker.

Split/merge là cinematic: ordered cube_ids map lower/upper local halves; destinations
lấy từ supplied snapshots. Merge slerp tới target whole canonical basis; có thể
intersect cube volumes giữa cinematic, không collision simulation. Muốn physical
face correspondence xuyên split/merge cần review thêm contract, không giả đã có.

FALL profile là downward visual drop từ supplied pose; một whole/cube được chọn,
cube còn lại giữ nguyên. GOAL profile là stationary shrink/fade **visual proxy**
ở trên mouth, không physical sinking. Không sửa logic footprint hoặc Goal mesh .76.
Roll-into-void terminal path không có after-state bình thường cần một explicit
profile mới nếu muốn roll+fall liên tục; không dùng fabricated Core snapshot.

## 8. Main thread / HUD / queue cho Stage 6

Animation mutation APIs enforce owning thread. Solver workers chỉ trả plain data;
Controller schedule calls vào Panda main thread. Tài sở hữu queue/replay cursor,
mode/session/input/reset orchestration. Manager không gọi Solver hoặc Board.transition.

HUD buttons/slider hiện disabled/command=None và metrics unknown. Sau khi team
approve Stage6 action bindings, Controller có thể mapping Pause→pause(),
Resume→resume(), speed→set_playback_rate(), Stop/Reset→cancel rồi authoritative
resync. Current HUD chưa có public enable/action-binding facade; không thao tác
widgets private để giả đã tích hợp. Metrics phải lấy số đo/thông tin thật.

## 9. Shutdown và known compatibility risks

Normal order: stop owned updater/driver → manager.dispose → dashboard.dispose →
presentation.dispose → renderer.dispose → surfaces.dispose → host.destroy.
Dispose manager đang busy emit synchronous CANCELLED một lần rồi bỏ owned rig.
Host-close fallback đã kiểm chứng; không có late task/callback sau teardown.

New preview cũng cleanup public BufferViewer của **host nó tạo** bằng ignoreAll,
vì Panda 1.10.16 ShowBase để lại inspector subscription qua sequential hosts. Tài
nên giữ equivalent scoped cleanup nếu dùng host composition riêng. Không xóa
engine-global/foreign messenger handlers.

Supported profile dùng pool thêm dynamic instances để đổi ownership, chỉ một pool
được draw. Node counts không phải số actors visible. Finite stress/teardown PASS
không là chứng minh zero leak mọi driver. Windows native NOT TESTED; shadow/AA
phụ thuộc capability. Camera không follow actor rơi khỏi board.

## 10. Stage 6 readiness

Đã có và có thể review: submit/advance/pause/resume/rate/cancel/resync/dispose,
immutable request/event/result, actor/surface lease, pure rolling/timeline,
Advanced cues và terminal proxy. Chưa có/không giả đã có: authoritative Advanced
Core adapter, final Controller/session/replay queue, solver delivery integration,
HUD action facade, approved event/outcome mapping hoặc victory screen.

Điều kiện VERIFIED: source Phong/Tài chính thức, mapping được xác nhận, integration
tests bằng states/events thật, stale/cancel/reset/mode transitions và native Windows
nếu nhóm yêu cầu. Stage 5 hiện **INTEGRATION PENDING**. QA/evidence/acceptance và
source scope xem [STAGE5_ANIMATION_SYSTEM.md](STAGE5_ANIMATION_SYSTEM.md).
