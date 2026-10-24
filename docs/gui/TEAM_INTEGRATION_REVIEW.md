# Team Integration Review — Phong / Phước / Tài

Ngày: **23/10/2026**. **REVIEW PACKAGE READY / PENDING TEAM APPROVAL**.
Không là thỏa thuận đã ký, không xác nhận Phong/Tài đã đọc hoặc đồng ý.
Phản ánh checkout local, không suy đoán công việc trên nhánh/máy thành viên khác.

Đọc [handoff](STAGE3_HANDOFF.md), [API thực tế](BASIC_RENDERER_API.md) và
[release checklist](STAGE3_RELEASE_CHECKLIST.md). Ba thành viên tiếp tục làm
phạm vi riêng; chỉ thống nhất boundary cần thiết trước từng lần tích hợp.
Adapter/presentation sẽ thích ứng khi có thể, không ép Core/Controller viết lại
để khớp mọi đề xuất ban đầu của Phước.

## 1. Ranh giới hiện tại đã xác minh

| Thành viên | Đang có trong checkout | Giới hạn |
| --- | --- | --- |
| Phong/Core | Board JSON/grid/start/goal, BloxorzState, Orientation, occupied cells, basic U/D/L/R transition/validity/goal | Chưa semantic Advanced schema/events; bridge flags tham gia identity nhưng không triển khai bridge effects |
| Phước/GUI | DTO/adapter Basic, procedural scene, 3 poses, camera/lights/style, layout/HUD/viewport, preview/QA | Không gameplay, solver UI, replay hoặc animation |
| Tài/Controller | `src/gui/controller.py` 0 byte trong checkout | Không kết luận tiến độ ngoài checkout; không ghi đè file này |
| Shared | Host/entry-point/dependency/context boundary | Một owner mỗi thay đổi, review trước wiring/merge |

Core không import GUI/Panda. Adapter đọc Core; renderer chỉ nhận DTO. HUD không
đọc Board hoặc đo benchmark. Một ShowBase, một app.run loop, scene/UI trên main
thread. Preview components không phải một Controller tạm thời.

## 2. Handoff cho Phong

Basic adapter đọc exact `Board.rows/cols/grid/goal_r/goal_c` và exact
`BloxorzState.r/c/orientation/bridges_state/get_occupied_cells()`. Không gọi
transition/goal/validity để tạo luật thứ hai. Grid 0/1/2, bridge flags rỗng
được hỗ trợ; code khác hoặc flags không rỗng reject rõ. Core hiện coi nonzero
là support, nhưng điều đó chưa định nghĩa fragile/bridge/switch semantics.

| Chủ đề cần phối hợp | Source hiện tại | Phong cần cung cấp/xác nhận trước Advanced |
| --- | --- | --- |
| Tile schema | Raw ints, Basic 0/1/2 được adapter map | Numeric/semantic kinds chính thức, phiên bản và capability negotiation |
| Fragile | Chưa broken-state/events | Tile identity, actor/weight semantics, authoritative broken event/state; không GUI tự quyết định vỡ |
| Soft/Heavy/Split switches | Chưa definitions/activation data | IDs, loại, cells, toggle/permanent/activation semantics và linked objects |
| Bridges | Tuple flags tồn tại trong State; chưa definitions/effects | Stable bridge IDs, cells, initial/open/closed meaning và state mapping; không enumerate flags thành ID giả |
| Whole/Split state | Whole Orientation/anchor; chưa cube schema | Mode, stable cube IDs/cells, active cube, merge conditions/ordering |
| Teleport | Chưa source API | Actor IDs, source/destination, before/after pose và event ordering nếu có |
| Transition result | BloxorzState hoặc None, unsupported action ValueError | Phân biệt reject/fall/terminal outcome; chỉ cung cấp event API nếu domain cần và nhóm chốt |
| Fall/Goal | is_goal cho whole standing; không rich events | Authoritative win/loss và terminal visual pose khi không có valid after-state |
| Event ordering | Chưa ordered events | Thứ tự roll/switch/bridge/split/teleport/fall; không GUI suy từ hai snapshots |
| Bounds | Full grid -0.18..2.30 basic envelope | Objects/effects có vượt grid/height hay không, để presentation fit có dữ liệu đúng |

Đề nghị Phong phản hồi các câu sau trong review, không bắt buộc đổi code ngay:

1. API nào đã ổn định và API nào còn refactor? Breaking changes có timeline nào?
2. Adapter cần chuyển các fields nào; có thể giữ DTO Basic dùng riêng hay cần version mới?
3. Event nào thật sự cần phát cho Renderer và nguồn authoritative là đâu?
4. Các điều kiện split/merge/fall/goal nào phải chốt trước Stage 4/5?
5. Có bounds/outcome nào Basic DTO không thể biểu diễn trung thực?

## 3. Handoff cho Tài

Hướng tích hợp **PROPOSED**:

```text
Input / UI command
    → Controller (session/current state)
    → Core (validity/transition/outcome)
    → Adapter (DTO + caller context)
    → Renderer (static snapshot; animation chỉ sau Stage 5)
    → HUD (ViewModel từ caller)
```

Không tạo ShowBase/Pygame loop thứ hai. Controller giữ game state, session ID,
state revision, replay cursor, solver worker/results, reset/stop/pause/resume.
Renderer không chạy solver. Worker chỉ chuyển plain data về dispatcher; mọi
Panda/DirectGUI update ở main thread. Solver hiện synchronous từ initial state,
có thể block GUI nếu gọi trực tiếp; loại worker/process, cancellation/timeouts
và starting-state policy do Tài đề xuất, không implement trong 3.7.

Basic `session_id` là nonempty **string**, không tự tăng trong renderer. Cùng
session: revision không giảm, cùng revision phải cùng snapshot. Khác session:
renderer nhận replacement theo quyền caller, **không lọc stale callback từ
session cũ**. Tài phải loại old-session solver results/updates trước adapter/renderer.
Không đưa session cũ trở lại chỉ vì renderer vẫn chấp nhận một string khác.

HUD units: search_time_ms là milliseconds, peak_python_memory_bytes là integer
bytes. Source SearchResult.time_taken là seconds, peak_memory là KiB float;
boundary cần đổi đơn vị có chủ đích. Failure không được biến thành solution
length=0 như thành công; dùng None cho số chưa biết. Đừng đặt profiler 3.6 vào HUD.
BaseSolver.solve từ chối external/nested tracemalloc session đang hoạt động;
không bọc GUI+solver trong cùng một tracing session mà không thiết kế lại owner.

| Câu hỏi Tài cần xác nhận | Đang có | Hướng review đề xuất |
| --- | --- | --- |
| 1. Final Application Host owner? | BloxorzPreviewApp, preview factories | Reuse một host; chốt owner bootstrap/shutdown trước integration |
| 2. Ai nối input events? | disableMouse, chưa game input | Tài wiring commands; Phước không gắn gameplay vào mesh/HUD |
| 3. Renderer interface? | load_board/show_snapshot/clear/dispose | Dùng public DTO API; chưa animation/callback API |
| 4. Session/revision truyền thế nào? | Opaque str + int≥0 | Controller cấp/lọc session, revision tăng theo logical update |
| 5. Đổi level/refit? | Renderer reload tách camera/HUD | Coordinator đồng bộ data/snapshot/camera viewport/HUD; thống nhất failure policy |
| 6. Status/metrics update? | HudViewModel + update_view_model | Đổi đơn vị ở boundary, None khi chưa biết, main-thread update |
| 7. Solver worker? | solve synchronous | Tài chọn orchestration/worker, IDs/cancel/timeout; không Panda objects trong worker |
| 8. Reset giữa animation? | Animation chưa có | Chốt cancel barrier + authoritative resync cùng Phước trước Stage 5/6 |
| 9. Stale callback/result? | Renderer chỉ chống stale cùng session | Controller filter old session và command generation; completion có terminal guard sau này |
| 10. Enable buttons khi nào? | Tất cả disabled, command=None | Sau khi action owner/error/lifecycle được duyệt; API wiring hiện chưa có |

## 4. Findings kiến trúc — không tự refactor

Không tìm thấy P0/P1 trong Basic workflow đã kiểm thử. Các P2 dưới đây là
integration/release prerequisites, không lỗi giả làm Basic hiện tại bị FAIL.

| ID / mức | Bằng chứng source / function | Tác động / owner | Recommended next action | Blocking? |
| --- | --- | --- | --- | --- |
| R1 / P2 | dashboard_preview.py:24, DashboardPresentation.__init__ truyền `app.presentation._refit`; board_preview.py:51 private callback; viewport.py:67 đọc camera.camera | Rename private callback dễ phá composition; Phước/shared | Public facade hoặc public refit callback cho presentation; viewport ownership/restoration documented; API proposal chưa triển khai | Nonblocking Basic/3.7; chốt trước Stage 6 facade integration |
| R2 / P2 | renderer.py:79–82 reload không fit camera; PreviewPresentation tạo fit riêng; viewport.py:55–70 restore full-window binding | Đổi level chỉ gọi renderer có thể dùng bounds/HUD cũ; arbitrary provider không được restore; Phước+Tài | Public coordinator có thao tác bind board/snapshot, viewport-aware fit, HUD identity và cleanup; chọn một owner cho resize | Nonblocking preview; trước integrated level switching |
| R3 / P2 | renderer.py:101–107 chỉ so state_revision khi session strings bằng nhau | Late session cũ có thể thay scene nếu caller gửi lại; Tài | Caller-side current-session filtering và reset/cancel policy; không sửa renderer theo phỏng đoán ordering strings | Nonblocking Basic; trước worker/replay |
| R4 / P2 | requirements.txt rỗng, Panda chỉ có trong local .venv; Windows chưa chạy | Clone không tự có GUI runtime; shared owners | Duyệt dependency setup/pinning/packaging file trong nhiệm vụ riêng; native Windows validation | Nonblocking local handoff; trước portable release |
| R5 / P2 tương lai | mesh_factory.py make_goal_mesh aperture .76/depth .14; block nominal width1 | Goal-sink có thể xuyên rim; Phước+Phong | Review visual transition, before/after framing và luật goal trước sink animation; không đổi luật Core | Nonblocking static Basic/basic roll trên floor; chặn goal-sink acceptance Stage 5 |
| R6 / P3 | Camera board_bounds full-grid +whole-block envelope; occupancy 3.6 ~41% ngang reference | Nhiều khoảng trống; Phước | Proposal tuning riêng, giữ frustum padding/pose continuity và before/after validation | Nonblocking |
| R7 / P3 | 3.6 finite stress: registry/nodes/listeners ổn định, traced heap drift nhỏ | Chưa đủ chứng minh leak hoặc zero-leak; Phước/shared QA | Long soak khi có Controller/animation, phân biệt Python/C++/VRAM, giữ reproducer | Nonblocking |
| R8 / P2 trước portable identity | board_preview.py create_preview resolve level path rồi dùng absolute POSIX path làm level_id; adapter digest có level_id | Cùng map ở checkout khác có board_revision khác; Tài+Phước | Chốt stable level_id tại Controller/adapter boundary nếu cần portable cache/golden IDs; không hardcode filesystem path vào contract | Nonblocking local preview; trước chia sẻ IDs/cache giữa máy |

Các paths trong bảng relative tới repository; đây là review references, không
receipt API. Private nodes/methods của QA harness dùng để đo không trở thành
Controller interface được duyệt. Nếu public facade được chọn, tên/signatures
và error/rollback semantics phải được review trước khi coding.

## 5. Stage 2 proposals so với implementation

Source hiện tại là chuẩn mô tả behavior; không sửa lịch sử Stage 2.

| Original proposal | Actual implementation | Why different / evidence | Compatibility impact | Current status | Future action |
| --- | --- | --- | --- | --- | --- |
| Rich StaticBoardData có definitions/capabilities | Basic DTO 8 fields, tiles tuple enums + goal_cells | Scope Basic 3.2; report 3.2 | Không truyền extra fields vào constructor | IMPLEMENTED Basic / Advanced PENDING | Version/mapping sau domain review |
| Tile semantic kind GOAL/advanced | Enum chỉ VOID/FLOOR, goal_cells riêng | Goal authoritative từ Board, source 3.2 | Không import BasicTileKind.GOAL | IMPLEMENTED | Adapter map advanced khi được chốt |
| session_id int tăng | Nonempty str opaque | Basic identity 3.2, không Controller session allocator | Integer invalid; không so sessions theo số | IMPLEMENTED / integration PENDING | Tài chốt session filtering |
| GameSnapshot có game_status/bridge/cubes | WHOLE basic footprint, không các fields đó | Unsupported capability bị reject, không giả empty advanced | Không serialize proposal Stage 2 trực tiếp thành DTO hiện tại | IMPLEMENTED Basic | Contract version trước Advanced |
| Custom category errors/receipts | TypeError/ValueError/RuntimeError, success None | Báo cáo 3.2/3.3 và source | Không đọc result.accepted | IMPLEMENTED | Review error facade nếu Controller cần |
| load_board đồng thời fit camera | Renderer geometry-only, presentation fit riêng | Ownership 3.3–3.4 | Caller phải phối hợp reload/refit | IMPLEMENTED / R2 PENDING | Coordinator Stage 6 |
| show_hud / controls_enabled trong VM | HudShell.update_view_model; mọi controls disabled | Scope shell 3.5 | Không có callback/enabling protocol | IMPLEMENTED shell | Tài+Phước chốt action binding |
| HUD time seconds, memory KiB | search_time_ms; peak_python_memory_bytes | Yêu cầu 3.5; formatter/source thật | Chuyển đơn vị SearchResult ở boundary | IMPLEMENTED | Tests conversion trước wiring |
| Reset Replay button | Stop button | Prompt 3.5 mới hơn | Không giả Reset Replay API | IMPLEMENTED disabled visual | Tài chốt behavior |
| Goal well depth .65 | .14, aperture vẫn .76 | Prompt 3.3 override, report 3.3 ghi rõ | Goal-sink visual còn cần review | IMPLEMENTED static / R5 PENDING | Stage 5 visual decision |
| MainBlockRoot/EffectRoot | BlockRoot/EffectsRoot; dynamic root có sẵn | Prompt host 3.1 mới hơn | Dùng đúng attrs app.block_root/effects_root | IMPLEMENTED | Chốt split/effect subtree khi cần |
| Vietnamese-capable external font candidate | Panda default font +English labels, 1.0x | Scope 3.5 không download assets; × thiếu glyph | Không cam kết arbitrary Unicode/localization | IMPLEMENTED Basic | Font/license/glyph validation nhiệm vụ riêng |
| AnimationRequest/Result, pause/resume/cancel | Không có source methods/classes | Ngoài Basic 3.1–3.7 | Không gọi APIs đề xuất như đã triển khai | PROPOSED / PENDING | Stage 5 lifecycle review với Tài |

## 6. Bảng quyết định nhóm

Mọi dòng dưới đây là **PENDING**, không có approval hoặc chữ ký suy đoán.
Blocking stage chỉ thời điểm cần chốt, không ép đổi code ngay lúc nhận tài liệu.

| Topic | Current implementation | Proposed integration direction | Owner | Approval needed? | Status | Blocking stage | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Core schema/version | Basic raw0/1/2 | Semantic adapter +version/capabilities được thống nhất | Phong+Phước | Có | PENDING | Advanced Stage4 | Core chọn domain representation |
| Bridge IDs/state | Tuple flags, no effects | Definitions +authoritative mapping | Phong | Có | PENDING | Bridge rendering | Không enumerate giả |
| Split/merge/active | Chưa schema | Stable actors/IDs, mode/events từ domain | Phong+Tài | Có | PENDING | Split Stage4/5 | Không merge theo khoảng cách GUI |
| Fall/goal/events | None hoặc State, basic is_goal | Explicit semantics cần cho terminal visuals | Phong+Phước | Có | PENDING | Terminal Stage5 | Không xem mọi None là fall |
| Final host/shutdown | Preview host/callbacks | Một owner bootstrap, Controller ngừng delivery trước cleanup | Phước+Tài | Có | PENDING | Stage6 | Không hai ShowBase |
| Public presentation facade | Private _refit dependency | Public refit/board binding/coordinator | Phước+Tài | Có | PENDING | Stage6 | R1/R2; chưa có facade source |
| Session/stale filtering | str +same-session guard | Controller cấp context, discard expired work | Tài | Có | PENDING | Worker/replay | R3 |
| Stable level identity | Preview absolute path nằm trong revision digest | Caller chọn stable level_id khi tích hợp portable content/cache | Tài+Phước | Có | PENDING | Portable IDs/cache | R8; factory hiện dành local preview |
| Level change | Geometry/fit/HUD APIs tách | Một coordinated main-thread operation/error policy | Tài+Phước | Có | PENDING | Stage6 | Không private NodePaths |
| HUD units/actions | ms/bytes, disabled | Caller conversion +action owner/enabling lifecycle | Tài+Phước | Có | PENDING | Stage6 | Failure length dùng None |
| Solver origin/worker | Synchronous, từ initial | Chốt reset/initial hoặc API current-state riêng, worker data-only | Tài+solver owners | Có | PENDING | Solver GUI | Không block Panda loop |
| Animation completion | Chưa implementation | Một terminal result, IDs, cancel/reset/resync | Tài+Phước | Có | PENDING | Stage5/6 | Basic roll face basis phải liên tục |
| Goal-sink clearance | .76 aperture <1 block | Visual transition không sửa gameplay | Phước+Phong | Có | PENDING | Goal animation | R5 |
| Dependency/platform | Local venv, requirements trống | Pin/setup được duyệt, native Windows QA | Shared | Có | PENDING | Portable release | R4, không tự sửa requirements |
| Merge/review scope | GUI code chưa stage/commit | Review theo owner, nhóm quyết định nhánh/thời điểm | Cả nhóm | Có | PENDING | Integration/merge | Không remote sync trong 3.7 |

## 7. Điều kiện chuyển chặng

- **Stage 4:** đủ Basic nền để lập kế hoạch; Advanced implementation cần schema/state
  và mappings Phong xác nhận. Không tuyên bố Advanced integration ready toàn bộ.
- **Stage 5 Basic Rolling:** đủ geometry/camera nền để thiết kế và test roll trên floor;
  cần giao nhiệm vụ riêng, review pivot/face history, cancel/resync và completion.
  Goal-sink/advanced animations còn R5/domain dependencies.
- **Stage 6:** chốt host/facade/session/worker/HUD/action lifecycle trước wiring;
  giữ disabled controls đến khi thật sự có owner triển khai và error handling.

Tài liệu sẵn sàng để Phước gửi review. Chưa tự gửi tin nhắn thành viên, chưa có
team approval, chưa tạo integration source, branch, commit hoặc merge.
