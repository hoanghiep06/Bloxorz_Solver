# Solve from current state

## Kết quả

`SOLVE FROM CURRENT STATE COMPLETE` — cả sáu solver sử dụng trạng thái Core đã commit; replay tiếp tục từ chính trạng thái đó. Chọn thuật toán, Solve, Stop và đóng panel không đưa người chơi về đầu level. Restart vẫn reset rõ ràng.

Branch khi bắt đầu: `feat/team-code/phase2-game-gui`, HEAD `2cb6140`. Công việc About Page chưa commit đã có sẵn được giữ nguyên; phần thay đổi About trong `screens.py` không thuộc Task 2. Không tạo nhánh, commit, push hoặc merge.

## 1. Nguyên nhân auto-reset

Trước bản sửa:

1. `GameController.select_solver()` và `run_solver()` gọi `_reset_to_start()`.
2. Cả sáu `_search()` lấy `board.get_initial_state()` làm root.
3. `_prepare_replay()` dùng điều kiện `moves != _index` để đưa replay về đầu. Điều kiện này không thể đúng khi người chơi đã có manual moves.
4. `stop()`, `cancel_guide()` và `end_guide()` cũng reset.
5. `UIFlow` kết thúc guide bằng cách gọi `end_guide()`, khiến level đã giải bị quay lại đầu.

Luồng mới: AI Solver → chọn thuật toán (không sửa state) → Play/Step → capture current Core → worker tìm kiếm → kiểm tra root/identity/path → action plan → AnimationManager → commit Core/Moves → kết quả thắng.

## 2. Ownership trạng thái

`GameController.state` là `BloxorzState` immutable đang điều khiển gameplay. `GameController.board` chứa luật và cấu hình level. Renderer và HUD không phải nguồn luật.

| Dữ liệu | Nguồn authoritative |
| --- | --- |
| Vị trí, tư thế nguyên khối | `state.r`, `state.c`, `state.orientation` |
| Hai cube, thứ tự identity | `state.cubes`, không sắp xếp lại |
| Cube được chọn | `state.active_cube` |
| Cầu mở/đóng | `state.bridges_state` |
| Liên kết switch, action toggle/open/close | Cấu hình `Board.switches_by_cell`, bridge mappings |
| Split/teleport destinations | `Board.split_switches`, vị trí cube đã commit trong state |
| Fragile | `Board.fragile_cells`; Core hiện tại chỉ cho vỡ khi terminal thua |

Core **không có trạng thái fragile đã vỡ mà người chơi vẫn tiếp tục chơi**. `broken_fragile_cells` của renderer diễn tả hiệu ứng thua, không được đưa ngược vào search. Không gọi Solver trong `FELL`; phải Restart. Không phục hồi fragile hoặc sửa representation/luật Core.

Hash/equality của Core đã phân biệt orientation, bridge flags, split cube order và active cube; giữ nguyên, có regression test.

## 3. Solver API trước/sau

Trước: `Solver(board).solve()` luôn giải từ initial.

Sau:

```python
result = Solver(board).solve(start_state=current_state)
# Caller cũ vẫn dùng được:
result = Solver(board).solve()
```

`BaseSolver.get_start_state()` trả root được truyền vào hoặc initial nếu không truyền. Sáu thuật toán chỉ thay điểm lấy root; thứ tự successor, frontier/visited, heuristic, cost, counting và reconstruction không viết lại. UCS/A* vẫn bắt đầu g=0; manual moves không tham gia cost.

`SearchResult` thêm trường tùy chọn `start_state` ở cuối constructor để giữ tương thích các đối số cũ. Kết quả từ `BaseSolver.solve()` luôn có root để Controller xác minh. `UCSSolver.get_solution_states()` dùng cùng root khi dựng lại action path.

`SolverJob(board, module, class_name, start_state=None)` thêm đối số tùy chọn cuối; worker cũ không truyền root vẫn chạy như trước. Factory được inject vào Controller phải chấp nhận đối số thứ tư. Không đổi level schema hoặc thêm dependency.

## 4. Capture và snapshot isolation

`SearchCapture` lưu level index, live Board identity, `board_data.board_revision` đang có sẵn, session ID, committed revision, toàn bộ immutable state, moves và thuật toán. Đây là capture trong RAM.

Capture chỉ được chấp nhận ở `READY`/`GOAL`, manager rảnh, không có action plan hoặc replay đang chạy. Nếu đang roll/effect/split/merge/terminal, Controller từ chối kèm status; người chơi thử lại sau khi action commit. Không capture pose trung gian.

Board có các dictionary/list mutable nên capture dùng `deepcopy` của **Board hiện tại**, không đọc lại JSON hoặc dựng Board initial. Worker nhận bản copy riêng; validation cũng dùng copy riêng. Live Board không bị search hay validation sửa đổi. Không lấy trạng thái luật từ NodePath, snapshot render hay Moves của HUD.

## 5. Hỗ trợ sáu thuật toán

BFS queue, DFS stack, mỗi vòng IDS, UCS frontier, Greedy heap và A* frontier đều bắt đầu từ `get_start_state()`. Parent/root/path không bao gồm lịch sử chơi tay. Test truyền root đồng thời cấm `get_initial_state()` để phát hiện mọi đường fallback sai.

Đã kiểm tra initial, ngang, dọc, cầu đã mở, split cả active cube 0/1, cube trên fragile và khả năng gọi `.solve()` mặc định sau một lần solve với root khác.

## 6. Advanced mechanics

Bridge flags, thứ tự hai cube và active cube đi nguyên vẹn qua capture → process serialization → search → validation → replay. Teleport đã hoàn tất trước Solve không được phát lại; path bắt đầu ở vị trí sau teleport. Switch/bridge/merge vẫn do Core transition và action plan hiện hữu quyết định. Renderer không tự thay luật.

Integration tests trước đó tiếp tục phát replay cả sáu thuật toán trên toàn bộ catalog mechanics, gồm fragile, heavy/soft switch, toggle/permanent bridge, split/merge và sandbox.

## 7. Replay

Controller dùng Core để dựng danh sách state kỳ vọng từ captured root và các action trả về, kiểm tra action hợp lệ, mỗi transition khác `None`, root trùng và điểm cuối đạt Goal. Path sai/rỗng ngoài Goal hoặc malformed result trở thành diagnostic; trả manual control, không reset/animation lỗi.

Replay gọi `_submit_move()`/`plan_action()` hiện có, giữ roll quaternion và các pha surface/split/merge/terminal. Không `resync`, teleport đến root hoặc dựng actor mới lúc bắt đầu Solve/replay. Bảng kết quả xuất hiện sau pha Goal, giữ state đã thắng.

## 8. Moves và HUD

Moves chỉ tăng ở `_on_phase_done()` khi toàn bộ action đã commit, theo chính sách cũ (bao gồm Space nếu là Core action hợp lệ). Effect của bridge/switch không tăng thêm Moves. Action thua vẫn theo chính sách cũ: không tăng thành successful committed move.

Solution Length là số action của lời giải còn lại. Thời gian vẫn `perf_counter` giây → ms trong HUD; memory vẫn peak `tracemalloc` KiB → bytes trong HUD; expanded nodes giữ cách đếm hiện có.

Ví dụ UI thật: **9 manual moves + 6 remaining = 15 total moves**. Log kiểm tra từng giá trị `9, 10, 11, 12, 13, 14, 15`.

## 9. Lifecycle/cancellation

- Đang search: phase `SOLVING`, input đổi state bị từ chối; worker chạy child process hiện có, không gọi Panda từ worker.
- No Solution/error/invalid path: giữ state, pose, bridge/cube state, Moves/session; trở về manual control.
- Already Goal: result length 0; không phát terminal animation hay goal event lần nữa.
- Stop/đóng panel: hủy search/deferred work; bỏ remaining path, giữ metrics và tiến độ. Nếu đã bắt đầu action thì resume nếu đang Pause, hoàn thành **toàn bộ action nhiều pha đó**, rồi dừng trước action kế tiếp. Không lấy pose chưa commit làm state.
- Restart/đổi level/dispose: cancellation và session lifecycle hiện có vẫn hoạt động; Restart reset state/mechanisms/Moves như trước.
- Main menu attract demo cần loop: chỉ `AttractMode` gọi explicit Restart sau Goal; gameplay Solve không còn làm việc này.

## 10. Session/revision safety

Poll và finish kiểm tra request capture identity, Board identity/revision, level, session, state revision, Core state và Moves. Restart/đổi level/Stop làm capture hết hiệu lực; callback cũ không cập nhật HUD hoặc bắt đầu replay. Job giữ reference riêng trong closure, không vô tình poll/cancel job mới.

Nếu revision thay đổi ngoài luồng bình thường, kết quả bị loại và Controller không bị kẹt ở SOLVING. Callback UI hoàn tất guide cũng kiểm tra session/revision/Goal trước khi hiển thị kết quả.

## 11. File/functions để nhóm review

- `src/solvers/base_solver.py`: API optional root, getter, result root metadata.
- `src/solvers/{bfs,dfs,ids,greedy,astar}.py`: một dòng lấy search root mỗi file.
- `src/solvers/UCS_Algorithm/ucs.py`: search root và dựng solution states theo root.
- `src/gui/solver_worker.py`: truyền root vào process worker.
- `src/gui/controller.py`: capture/validation/replay/Stop; giữ action planner và animation math.
- `src/gui/screens.py`: kết thúc guide giữ Goal, hiển thị dialog; chặn callback cũ. Bảo toàn thay đổi About có sẵn.
- `src/gui/attract.py`: explicit reset riêng vòng lặp demo menu.
- `tests/test_solve_current_state.py`, `tests/test_solver_worker.py`: root/advanced/async/lifecycle/HUD tests.
- `tests/test_game_integration.py`, `tests/test_game_ui_state.py`: cập nhật kỳ vọng hành vi đã đổi có chủ đích.
- `tools/current_state_solver_smoke.py`: thao tác native và lưu evidence trên game thật.

Không sửa Core rules, production levels, materials/themes/camera/HUD layout, animation math hoặc assets trong Task 2.

## 12. Automated tests

Baseline trước sửa: **530 tests PASS**, 67.795s.

Bốn failure ban đầu sau implementation đều do hành vi test cũ: chọn Solver ở giữa initial Goal animation; kỳ vọng Moves reset từ 1 về 0; chọn algorithm để thoát GOAL/FELL. Đã sửa test cho yêu cầu mới: chờ commit trước capture, cộng manual+replay, giữ terminal state/dialog. Không hạ kiểm tra hình học/animation.

Lệnh:

```bash
.venv/bin/python -B -m unittest discover -s tests
```

**Kết quả cuối: 547 tests PASS**, 111.512s (chạy đồng thời với native UI QA). Không còn regression failure. Log được lưu trong thư mục evidence cạnh tài liệu. Các test bổ sung gồm sáu root APIs + cả sáu spawned workers, eight-manual-move replay/HUD từng bước, no solution, invalid/malformed result, worker error, busy split, paused-last-step, stop giữa split, restart/đổi level/cancel stale callback, revision mismatch và already Goal.

## 13. Runtime gameplay

Chạy **game Panda3D thật, GLX GraphicsWindow**, trong Xvfb X11; XTest gửi chuột/phím thật vào DirectGUI/MouseWatcher. Đây không phải mock screenshot hoặc chỉ NodePath tests. Native input trên desktop `:0.0` có hạn chế focus/input delivery đã biết nên dùng Xvfb để có thao tác tự động lặp lại được.

```bash
xvfb-run -a -s '-screen 0 1920x1200x24 +extension GLX' \
  .venv/bin/python -B -m tools.current_state_solver_smoke \
  --output /tmp/current-state-ui
```

Fixture/No Solution và save file đều tạo trong thư mục tạm, không thay production levels.

Đã kiểm tra native Main → Start → Level 1; BFS sau 9 manual moves ở tư thế ngang; A* từ tư thế dọc; cả sáu thuật toán từ bridge mở và split cube-1; theme Light/Dark; Step/Play; HUD từng commit; giữ pose trong SOLVING; Goal dialog; No Solution rồi tiếp tục chơi tay; đóng panel và Restart trong search.

Evidence: [report.json](evidence/solve-current-state/report.json), ảnh trước Solve/trong SOLVING/sau first Step/sau Goal, Dark Goal, No Solution; GIF ngắn là các frame chụp trực tiếp từ framebuffer trong replay thực tế.

## 14. Giới hạn

- Capture khi đang animation/replay bị từ chối; không queue tự động. Cần đợi commit hoặc Stop trước khi đổi solver.
- Stop giữa action hoàn tất action đang chạy rồi dừng, không dừng ở visual pose trung gian.
- Chi phí/cách duyệt DFS/IDS và heuristic không thay đổi; map lớn vẫn có thể tìm kiếm lâu. Worker vẫn cho phép hủy; không thêm timeout/thuật toán mới.
- Core không hỗ trợ tiếp tục chơi sau fragile vỡ; không thêm semantic state mới để giả lập.
- Runtime matrix tập trung các mechanics fixtures và root sau manual play; không khẳng định mọi trạng thái của mọi production level đã được duyệt bằng GUI.

## 15. Team review

Tài tập trung review Controller/worker, policy Stop và Goal dialog. Nhóm solver review optional `solve(start_state=...)`, result metadata và UCS state reconstruction. Phong có thể kiểm tra các root split/bridge trong regression; không có thay đổi code/luật Core.

Dừng ở working tree để review; About Page và các untracked files có sẵn vẫn được giữ.
