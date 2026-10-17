# BFS Solver — thiết kế, kiểm thử và bàn giao

## 1. Mục tiêu và phạm vi

`BFSSolver` tìm một chuỗi hành động hợp lệ có **ít hành động nhất**, khi mỗi hành động có cùng chi phí. Đây là phần BFS giai đoạn 1 của TV1 — Phước, chuẩn bị cho TV5 — Phong review.

Phạm vi thay đổi chỉ gồm:

- `src/solvers/bfs.py`: giữ thuật toán FIFO/visited, thay lưu path trên frontier bằng parent tracking.
- `tests/test_bfs.py`: kiểm thử BFS, tính tối ưu, metrics và tương thích.
- `docs/BFS.md`: tài liệu này.

Không sửa Core, BaseSolver, SearchResult, thuật toán thành viên khác, GUI, level chính thức hoặc dependencies. Không commit/push/merge/PR trong nhiệm vụ này. Nhánh làm việc là `feat/phuoc/bfs-solver`, tạo từ `6a6cf45` khi working tree sạch; chưa có mentor approval.

## 2. Đánh giá mã ban đầu

BFS trước thay đổi đã dùng `collections.deque`, pop FIFO, đánh dấu visited khi enqueue, gọi `Board.transition()`/`is_goal()`, tăng expanded nodes khi dequeue. Không phát hiện lỗi logic trên mô hình cơ bản.

Hạn chế cần cải thiện: mỗi queue entry chứa `(state, path)` và mỗi successor tạo `path + [action]`. Như vậy cùng một prefix hành động bị sao chép nhiều lần. Phiên bản mới giữ một parent link cho mỗi state được phát hiện, chỉ dựng list hành động khi gặp goal. Đây là cải thiện về cấu trúc lưu đường đi, **không khẳng định luôn nhanh hơn hoặc ít peak memory hơn**; xem số đo thực tế ở mục 15.

Audit xác nhận:

- `Board` đã cung cấp ba API cần thiết, chưa có `get_successors()` hay action space theo state.
- Core dùng frozen state, identity gồm tọa độ, orientation và bridge flags.
- BaseSolver đã xử lý reset counter, `perf_counter`, `tracemalloc`, exception cleanup; không cần sửa.
- Bộ baseline ban đầu có 59 tests và pass trước khi sửa BFS.
- `README_LLM.md` không tồn tại trong checkout; dùng source và `docs/BASELINE.md` đối chiếu. Các ghi chú lưu path cũ trong tài liệu baseline là ảnh chụp giai đoạn trước; tài liệu này mô tả BFS hiện tại.

## 3. State space và hợp đồng với Core

Với gameplay cơ bản, state là `(r, c, orientation, bridges_state)`:

| Orientation | Occupied cells theo ô neo `(r,c)` |
| --- | --- |
| `STANDING` | `(r,c)` |
| `HORIZONTAL` | `(r,c)`, `(r,c+1)` |
| `VERTICAL` | `(r,c)`, `(r+1,c)` |

`r` tăng xuống, `c` tăng sang phải. `VERTICAL` là nằm dọc, không phải đứng thẳng. BFS không đọc các tọa độ để tự tính bước lăn và không chiếu state thành tuple thiếu orientation/flags; visited và parent dùng trực tiếp equality/hash của Core.

Đồ thị tìm kiếm phải hữu hạn và luật không đổi trong một lượt `solve()`. State phải chứa đủ dữ liệu quyết định các successor; không được mutate state sau khi dùng làm key. Core hiện bảo vệ việc ghi thuộc tính bằng frozen dataclass.

## 4. Frontier — deque FIFO

```python
queue = deque([initial_state])
```

Queue chỉ chứa state, không chứa path. `popleft()` lấy state đến trước; `append()` đưa state mới vào cuối. Các lớp độ sâu được xử lý tăng dần. Thao tác hai đầu deque có chi phí O(1); không dùng `list.pop(0)` vì phải dịch các phần tử.

State đầu được kiểm tra goal trước khi tạo queue. Nếu đã thắng, `_search()` trả `[]` và counter vẫn bằng 0. Nếu queue cạn mà chưa gặp goal, trả `None`.

## 5. Visited và lần phát hiện đầu tiên

```python
visited = {initial_state}
parent = {}
```

Khi gặp successor hợp lệ chưa visited:

```python
parent[next_state] = (current_state, action)
visited.add(next_state)
queue.append(next_state)
```

Đánh dấu **khi enqueue**, không chờ dequeue. Nhờ đó nhiều cạnh cùng dẫn đến một state không tạo nhiều queue entries hoặc ghi đè parent đầu tiên. State đầu đã trong visited nên một chu trình quay lại start không tạo parent cho root.

Hai state cùng ô neo nhưng khác orientation là hai keys. Các bridge flags khác nhau cũng thuộc identity do Core định nghĩa; BFS không bỏ flags. Hiện Core chưa tạo ra các biến đổi cầu nên chưa kiểm thử một level có nhiều cấu hình cầu thực sự đạt tới.

## 6. Successor generation và goal detection

Mỗi state chưa đạt goal được mở qua đúng thứ tự `ACTIONS = ['U', 'D', 'L', 'R']` từ `src/core/board.py`:

```python
next_state = self.board.transition(current_state, action)
```

`None` nghĩa là move không hợp lệ và bị bỏ qua; state hợp lệ đã visited cũng bị bỏ qua. Không tự viết lại luật xoay lật, bounds, void hoặc advanced tiles trong BFS.

Sau mỗi dequeue, tăng `self.expanded_nodes`, rồi gọi `board.is_goal(current_state)`. Giữ kiểm tra goal ở **dequeue** để bảo toàn thứ tự xử lý và cách đếm node của baseline. State đang nằm đè lên goal chưa thắng; Core quyết định goal test, BFS không nhìn tile code `2`.

Khi nhiều nghiệm ngắn nhất tồn tại, thứ tự `U/D/L/R` và parent lần đầu quyết định nghiệm được trả. Không ghi đè parent khi một đường khác cùng độ sâu tới state đã visited.

## 7. Parent tracking và path reconstruction

Root không có entry trong `parent`; mỗi state còn lại chỉ có một entry `(previous_state, action_from_previous)`.

Khi dequeue goal:

```python
path = []
while current_state != initial_state:
    current_state, action = parent[current_state]
    path.append(action)
path.reverse()
return path
```

Mỗi link đi về một state ở độ sâu nhỏ hơn đúng 1. Vì parent chỉ được đặt khi phát hiện lần đầu từ một node đã dequeue, parent chain không có cycle. Dừng khi về root, đảo ngược danh sách để nhận thứ tự **start → goal**.

Thao tác gán `current_state` chỉ đổi biến cục bộ; không sửa object state. Truy vết dùng vòng lặp, không dùng đệ quy nên không phụ thuộc recursion limit cho lời giải dài.

Không lưu parent hoặc visited trên `self`; chúng được tạo mới mỗi lần `_search()`. Hai lần `solve()` dựng hai action lists riêng và không dùng lại dữ liệu tìm kiếm trước.

## 8. Public API và kết quả

Public API không đổi:

```python
from src.core.board import Board
from src.solvers.bfs import BFSSolver

board = Board("levels/level_01.json")
solver = BFSSolver(board)
result = solver.solve()
```

`BFSSolver` kế thừa `BaseSolver`, không override constructor hoặc `solve()`. `_search() -> Optional[List[str]]` trả:

| Kết quả | Ý nghĩa |
| --- | --- |
| `List[str]` không rỗng | Nghiệm, các action theo thứ tự replay |
| `[]` | Start đã là goal; success, 0 bước |
| `None` | Tìm hết vùng đạt tới mà không có nghiệm |

Lỗi từ Core truyền ra ngoài qua BaseSolver và được cleanup tracing; không chuyển exception thành kết quả vô nghiệm. Ứng dụng/GUI nên gọi `solve()` để có metrics, không gọi `_search()` trực tiếp để đo tài nguyên.

Ví dụ replay nghiệm, không đưa luật chơi vào GUI:

```python
if result.success:
    state = board.get_initial_state()
    for action in result.actions:
        state = board.transition(state, action)
        assert state is not None
    assert board.is_goal(state)
```

## 9. Search metrics

Toàn bộ phép đo dùng BaseSolver hiện có:

| Field | Ý nghĩa |
| --- | --- |
| `success` | `actions is not None`; `[]` vẫn thành công |
| `actions` | Action list hoặc `None` |
| `solution_length` | Số action của nghiệm, 0 nếu rỗng/vô nghiệm |
| `expanded_nodes` | Số state được dequeue để xử lý, gồm goal |
| `time_taken` | `perf_counter` bao quanh `_search()`, giây |
| `peak_memory` | Peak Python allocation do `tracemalloc` theo dõi, KiB |

Không tăng counter khi sinh/enqueue successor, từ chối move hoặc bỏ state trùng. State chỉ nằm trong queue khi solver dừng chưa được tính. Start đã là goal được trả trước queue nên count bằng 0. BFS không có stale heap entries.

BaseSolver reset counter trước mỗi `solve()`, mở tracing trước tìm kiếm và đóng trong `finally`, kể cả khi Core lỗi. Thời gian gồm tìm kiếm **và dựng lại nghiệm**, có overhead tracing; không gồm đọc level, in output, animation hoặc tương tác người dùng. Peak allocation không phải RSS/tổng RAM process.

Tracing ngoài đã bật hoặc nested solve bị BaseSolver từ chối bằng `RuntimeError`; BFS không tự quản lý tracing hoặc thay đổi hợp đồng này. Search song song trong cùng process, timeout và cancellation chưa được hỗ trợ.

## 10. Completeness

Trên đồ thị hợp lệ hữu hạn, mỗi state đạt tới chỉ được enqueue một lần, sau đó dequeue không quá một lần. Mỗi dequeue sinh hữu hạn successor. Do đó thuật toán hoặc gặp goal, hoặc xử lý hết vùng đạt tới và trả `None`; chu trình không làm tìm kiếm vô hạn.

Phát biểu này giả định Core sinh đúng toàn bộ actions của mô hình, equality/hash ổn định và đủ để phân biệt các tương lai khác nhau. Nếu Core bỏ thông tin quan trọng khỏi state identity thì visited có thể gộp sai state; BFS không thể tự sửa mô hình đó.

## 11. Optimality theo số hành động

FIFO xử lý các state theo độ sâu không giảm. Khi sinh một state lần đầu từ lớp `d`, parent đặt cho nó cho một đường dài `d+1`; không thể có đường ngắn hơn chưa được xét, vì mọi lớp nhỏ hơn đã hoặc đang được xử lý trước.

Vì vậy goal đầu tiên được dequeue có độ sâu nhỏ nhất. Parent reconstruction không thêm/bớt bước, nên action list trả về có số hành động ít nhất.

Điều kiện là mọi action có cùng chi phí. Nếu nhóm thiết kế chi phí khác nhau, BFS vẫn tối ưu **số action**, không bảo đảm tối ưu tổng cost. Khi đó dùng thuật toán phù hợp như UCS/A* với cost model được thống nhất. Không hardcode cost UCS vào BFS.

Tests dùng hai phép kiểm chứng độc lập với solver: liệt kê action sequences có độ dài giới hạn và Floyd–Warshall trên đồ thị trạng thái nhỏ. Không dùng BFS đang được kiểm tra làm oracle duy nhất cho chính nó.

## 12. Độ phức tạp và kích thước state space

Gọi `V` là số state đạt tới, `E` là số cạnh được xét, `L` là độ dài nghiệm. Với hash/transition chi phí hằng số trong mô hình cơ bản:

- Search: `O(V + E)` thời gian.
- Dựng nghiệm: `O(L)` thời gian và list `O(L)`.
- Queue + visited + parent: `O(V)` bộ nhớ; `L <= V-1` với nghiệm không rỗng nên tổng vẫn `O(V)`.
- Branching factor tối đa là `4` trong action space hiện tại; `E <= 4V`.

Với lưới `R×C`, chặn trên theo placement trước khi loại void là `RC + R(C-1) + (R-1)C = 3RC-R-C`, nhỏ hơn `3RC`. Vùng đạt tới có thể nhỏ hơn nhiều. Bridge configurations/split states tương lai sẽ tăng không gian trạng thái; chặn này chỉ áp dụng basic gameplay với flags cố định.

Phiên bản cũ sao chép một path dài `depth(v)` cho mỗi state mới. Tổng công sao chép có thể tới `O(Vd)` với độ sâu lớn nhất `d`; phần path trên frontier cần tới `O(Fd)` với `F` là frontier size. Parent tracking bỏ việc sao chép prefix đó nhưng thêm dict và tuple giữ đến cuối search. Vì thế hằng số bộ nhớ có thể cao hơn phiên bản cũ nếu frontier/path còn ngắn.

## 13. Test cases và kết quả

`tests/test_bfs.py` có **17 test methods**, dùng `unittest`, level JSON tạm và instrumentation trong tests. Không sửa level chính thức hoặc tạo solver khác trong production code.

| Trường hợp | Kiểm chứng |
| --- | --- |
| Demo | Nghiệm `RRDLURR`, dài 7, 35 node; replay đạt goal; liệt kê đủ các action sequences dài 0–6 không tìm thấy nghiệm |
| Start=goal | `[]`, success, length 0, count 0; không tạo queue |
| Start bị cô lập | `None`, failure, chỉ xử lý start |
| Chu trình, goal cô lập | Có cạnh `R` rồi `L` quay lại start; xử lý hết 20 state, không duplicate enqueue/pop |
| Nhiều cạnh đến cùng state | Xác nhận successor trùng thực sự xuất hiện nhưng queue chỉ chứa mỗi state một lần; nghiệm vẫn đúng |
| Nhiều nghiệm ngắn nhất | Lưới floor 4×4, `(0,0)` → `(3,3)`: enumeration độc lập xác nhận hai nghiệm dài 4 là `DDRR`, `RRDD`; BFS chọn `DDRR` |
| Oracle toàn bộ 81 cặp start/goal | Trên floor 3×3, dựng toàn bộ state hợp lệ và tính all-pairs bằng Floyd–Warshall; so sánh success/độ dài và replay mọi nghiệm |
| Parent chain dài | Hành lang 1×301: 200 action `R`, 201 node, replay đúng |
| Identity | Cùng ô neo nhưng khác orientation vẫn được xử lý riêng; bridge flags có sẵn được giữ nguyên |
| Immutability | Lưu identity/hash của mọi state quan sát trước/sau; board không đổi |
| Delegation | Tất cả action/goal checks đi qua Board; không tự cài luật |
| FIFO/count | Pop là prefix của thứ tự enqueue; goal được tính, state còn trong queue không tính |
| Metrics/reuse | Time/memory hữu hạn không âm; length/counter đúng; solve nhiều lần không cộng dồn, trả lists riêng |
| Return contract/errors | Raw `_search()` giữ list/`[]`/`None`; Core exception truyền ra ngoài, tracing dừng |

Recording queue có giới hạn pop bằng chặn hữu hạn `3RC` để test không bị treo nếu visited bị regression. Các oracle là mã kiểm thử, không được import vào BFS.

Kết quả lần kiểm chứng: **17/17 tests BFS pass; toàn bộ repo 76/76 tests pass, 0 failure/error**. Các 81 cặp start/goal là subcases trong một test, không phải cộng thêm 81 test methods. Runtime kiểm chứng: Python 3.14.4. Chưa chạy ma trận nhiều phiên bản Python.

## 14. Kết quả demo và cách chạy

Từ repo root:

```bash
python3 -B main.py
python3 -B -m unittest discover -s tests -p test_bfs.py -v
python3 -B -m unittest discover -s tests -v
git diff --check
```

Nếu môi trường có `python` trỏ đúng Python 3 thì dùng thay `python3`. `-B` chỉ ngăn sinh `__pycache__`; không thêm dependency.

Output ổn định của demo:

```text
Start: (1, 1), Goal: (1, 6)
Success: True
Moves (7): R -> R -> D -> L -> U -> R -> R
Expanded Nodes: 35
```

Replay:

```text
(1,1,STANDING)
  R -> (1,2,HORIZONTAL)
  R -> (1,4,STANDING)
  D -> (2,4,VERTICAL)
  L -> (2,3,VERTICAL)
  U -> (1,3,STANDING)
  R -> (1,4,HORIZONTAL)
  R -> (1,6,STANDING) => goal
```

Time/memory được tính thật mỗi lần, không dùng làm hằng số expected trong tests. Kết quả demo trước/sau parent tracking có cùng actions, solution length và expanded nodes.

## 15. So sánh trước/sau đã đo thực tế

Đo trên Python 3.14.4, cùng process, cùng Core/BaseSolver và cùng Board cho hai implementation. Bản trước lấy nguyên `src/solvers/bfs.py` từ commit `6a6cf45d40ffe8231c1003f87b0a177832e06bf1`; bản sau là source đang bàn giao. Mỗi case warm-up một lần cho mỗi bản, sau đó 7 lượt/bản, đảo thứ tự chạy trước/sau qua các lượt, `gc.collect()` ngoài vùng đo trước mỗi `solve()`. Bảng dùng **median**, time đổi từ giây sang ms, peak giữ KiB. Không chạy tests đồng thời trong phép đo.

Các fixtures tổng hợp không phải level benchmark chính thức của nhóm:

- `open_NxN`: toàn floor, start `(0,0)`, goal `(N-1,N-1)`.
- `corridor_K_room_20x20`: grid có 20 hàng, `K+20` cột; hàng 0 toàn floor, 19 hàng còn lại là `K` ô void rồi 20 ô floor; start `(0,0)`, goal `(19,K+19)`. Đây là hành lang dài nối phòng rộng, dùng để khảo sát path prefix trước khi phân nhánh.

| Case | Length / nodes (cả hai) | Trước: ms | Sau: ms | Trước: KiB | Sau: KiB |
| --- | --- | ---: | ---: | ---: | ---: |
| Demo | 7 / 35 | 0.831 | 0.809 | 10.81 | 13.91 |
| Open 20×20 | 26 / 1158 | 28.603 | 29.924 | 166.60 | 261.53 |
| Open 40×40 | 52 / 4713 | 130.715 | 131.320 | 637.47 | 1050.11 |
| Corridor 300 + room | 226 / 1400 | 40.386 | 40.830 | 417.94 | 493.52 |
| Corridor 900 + room | 626 / 1800 | 52.610 | 53.354 | 781.20 | 548.18 |

Mọi lượt đo đều kiểm tra actions/node count trước-sau bằng nhau và replay hợp lệ. Parent tracking giảm peak khoảng 30% trong case corridor 900 + room, nhưng **tăng peak ở bốn case còn lại**. Thời gian gần nhau, không có bằng chứng cho tăng tốc tổng quát từ phép đo này. Không dùng các số này để khẳng định hiệu suất trên toàn bộ 16 level tương lai.

Giữ parent tracking vì bỏ sao chép prefix cho từng successor, có chặn lưu đường đi rõ `O(V)` và truy vết dễ giải thích; đánh đổi là dict/tuple overhead thực tế. Chưa thêm tối ưu hợp nhất visited/parent hoặc thay cấu trúc key; đó là thay đổi khác, chỉ cân nhắc khi có dữ liệu workload phù hợp.

### Mã tái hiện phép đo

Chạy đoạn Python sau từ repo root, sau khi kiểm tra source đang bàn giao. Dữ liệu tạo trong temporary directory; không sửa repo, không dùng thuật toán bên thứ ba. Đo lại có thể cho số khác do hệ thống:

```python
import gc
import json
import statistics
import subprocess
import tempfile
from pathlib import Path
from src.core.board import Board
from src.solvers.bfs import BFSSolver

namespace = {"__name__": "bfs_before"}
base = "6a6cf45d40ffe8231c1003f87b0a177832e06bf1"
exec(subprocess.check_output(
    ["git", "show", base + ":src/solvers/bfs.py"], text=True
), namespace)
Before = namespace["BFSSolver"]

with tempfile.TemporaryDirectory() as directory:
    boards = [("demo", Board("levels/level_01.json"))]
    cases = []
    for n in (20, 40):
        cases.append((f"open_{n}", [[1]*n for _ in range(n)], [0,0], [n-1,n-1]))
    for k in (300, 900):
        grid = [[1]*(k+20)] + [[0]*k + [1]*20 for _ in range(19)]
        cases.append((f"corridor_{k}", grid, [0,0], [19,k+19]))
    for name, grid, start, goal in cases:
        path = Path(directory) / (name + ".json")
        path.write_text(json.dumps(dict(grid=grid, start=start, goal=goal)))
        boards.append((name, Board(str(path))))
    for name, board in boards:
        samples = {"before": [], "after": []}
        for cls in (Before, BFSSolver):
            cls(board).solve()
        for iteration in range(7):
            order = [("before", Before), ("after", BFSSolver)]
            if iteration % 2:
                order.reverse()
            for label, cls in order:
                gc.collect()
                samples[label].append(cls(board).solve())
        reference = samples["before"][0]
        for label, runs in samples.items():
            for result in runs:
                assert result.actions == reference.actions
                assert result.expanded_nodes == reference.expanded_nodes
                state = board.get_initial_state()
                for action in result.actions:
                    state = board.transition(state, action)
                    assert state is not None
                assert board.is_goal(state)
            print(name, label,
                  statistics.median(r.time_taken for r in runs)*1000, "ms",
                  statistics.median(r.peak_memory for r in runs), "KiB")
```

## 16. Current limitations và advanced compatibility

Core hiện chỉ có basic movement, floor/void/goal, chưa có hiệu ứng fragile, bridge/switch, teleport hoặc split/rejoin. Test bridge flags chỉ kiểm tra dữ liệu được giữ nguyên, **không chứng minh giải được level có cầu hoặc switch**. Chưa có bộ benchmark 16 level chính thức.

BFS chỉ dùng Core API, nên luật fragile/cầu được bổ sung trong `Board.transition()` và identity đầy đủ có thể được dùng lại mà không chép luật vào BFS, miễn action space/hợp đồng vẫn tương thích. Tuy nhiên split/đổi cube có thể cần thêm action hoặc API actions theo state; implementation hiện duyệt đúng bốn `ACTIONS`. Không tự khẳng định nó đã hỗ trợ các action tương lai.

Khi nhóm triển khai advanced mechanics cần thống nhất:

1. Bridge configuration, hai vị trí cube, active cube/mode và mọi thông tin ảnh hưởng tương lai phải tham gia equality/hash.
2. Cách Core sinh actions/successors cho khối tách, biểu diễn action đổi cube trong path và GUI replay.
3. Quy tắc switch/bridge/fragile và trạng thái ban đầu nằm trong Core/schema, không nằm trong BFS.
4. Action đổi cube có được tính vào solution length/cost hay không; optimality của BFS chỉ theo số action đồng chi phí đã chọn.
5. Bổ sung tests thật cho toggle/permanent, soft/heavy/split, rejoin và replay. Chưa thực hiện các tests này ở giai đoạn hiện tại.

Với graph lớn, visited/parent vẫn có thể chiếm nhiều memory; không có timeout, cancellation, external-memory search hay bidirectional search. Không thêm những cơ chế đó trong nhiệm vụ BFS này.

## 17. Giải thích cho mentor trong 7 phút

| Thời lượng | Nội dung |
| --- | --- |
| 0:00–1:00 | Bài toán: state gồm vị trí/tư thế, goal đứng thẳng; dùng Core chung |
| 1:00–2:00 | Deque FIFO duyệt từng lớp; append/popleft; action order |
| 2:00–3:00 | Visited khi enqueue ngăn chu trình và duplicate; parent ghi một lần |
| 3:00–4:00 | Chứng minh ngắn nhất theo độ sâu, truy vết parent về root rồi reverse |
| 4:00–5:00 | Metrics: goal được tính khi pop, start=goal count 0, KiB allocation khác RSS |
| 5:00–6:00 | Chạy demo và test oracle độc lập; đưa ra tradeoff peak memory đã đo |
| 6:00–7:00 | So sánh thuật toán, giới hạn advanced/graph lớn, hỏi đáp reviewer |

So sánh ở mức chiến lược: DFS ưu tiên một nhánh và không bảo đảm ít bước nhất; UCS ưu tiên tổng cost nên xử lý được chi phí không đồng nhất; A* ưu tiên `g+h` và phụ thuộc heuristic/cost cùng chính sách xử lý graph phù hợp. BFS ưu tiên độ sâu, đơn giản và complete trên graph hữu hạn, nhưng phải giữ nhiều state trong memory. Không khẳng định DFS luôn ít RAM hơn hoặc A* luôn nhanh hơn trên mọi graph.

Checklist TV5 review:

- [ ] Giải thích vì sao FIFO + first discovery cho đường ngắn nhất.
- [ ] Kiểm tra visited được đánh dấu khi enqueue, root không có parent.
- [ ] Kiểm tra reconstruction không mutate state, không mất/đảo sai action.
- [ ] Chạy 17 tests BFS và 76 tests toàn repo; xem 81 subcases oracle độc lập.
- [ ] Replay demo, xác nhận 7 action/35 node và xử lý start=goal/vô nghiệm.
- [ ] Xác nhận time/memory từ BaseSolver và mô tả đúng tradeoff đã đo.
- [ ] Xem diff chỉ có BFS, tests và tài liệu; không sửa Core/solver khác.

## 18. Git handoff

Nhánh: `feat/phuoc/bfs-solver`; reviewer đề xuất: **TV5 — Phong**. Chưa commit, push, merge hoặc tạo PR trong nhiệm vụ này.

Đề xuất atomic commits, chưa thực hiện:

```text
perf(bfs): reconstruct solutions with parent tracking
test(bfs): verify cycles, optimality and baseline integration
docs(bfs): document search design, tests and tradeoffs
```

Trạng thái: **BFS READY FOR REVIEW** trên mô hình basic hiện tại, dựa trên tests/regression/oracle đã chạy. Đây không phải tuyên bố advanced mechanics đã được hỗ trợ hoặc mentor đã phê duyệt.
