# Shared Baseline — Bloxorz Solver

## 1. Mục tiêu, phạm vi và trạng thái bàn giao

Baseline thống nhất State, Actions, luật lăn, kiểm tra hợp lệ, goal test và giao diện/đo lường solver để các thành viên phát triển thuật toán trên cùng một bài toán. Đây là phần của TV1 — Phước; TV5 — Phong là reviewer giai đoạn 1. TV1 còn review DFS/IDS của TV2 — Tài.

Phạm vi lần thay đổi này chỉ gồm `src/core/state.py`, `src/core/board.py`, `src/solvers/base_solver.py`, ba file test và tài liệu này. Không thay đổi BFS hay thuật toán khác, GUI, level, dependencies. Hoàn thành baseline **không có nghĩa** hoàn thành nhiệm vụ BFS hoặc toàn bộ giai đoạn 1 của TV1.

Nhánh bàn giao: `feat/phuoc/shared-baseline`. Base commit: `9c1ac8e` trên `main`; trước khi sửa, working tree sạch và `git pull --ff-only origin main` trả `Already up to date`. Chưa commit, push, tạo merge commit hay PR. Trạng thái bàn giao là sẵn sàng để review, chưa phải mentor đã phê duyệt.

### Kết quả audit

| Thành phần trước thay đổi | Đánh giá và cách xử lý |
| --- | --- |
| Enum, ô neo, occupied cells, `is_standing()` | Đúng; giữ tên và giá trị enum, giữ công thức |
| Equality/hash | Đã xét vị trí, orientation, bridge flags; giữ logic |
| State | Chưa validate input; mutable có nguy cơ phá khóa set/dict; bổ sung validation và bảo vệ bằng frozen dataclass |
| 12 công thức transition | Đúng; giữ nguyên công thức và thứ tự `ACTIONS` |
| Action lạ | Tạo self-loop giả; sửa thành `ValueError` |
| Bounds/void và goal test | Đúng với dữ liệu hợp lệ; giữ luật |
| Đọc JSON | Thiếu validation grid/start/goal; bổ sung thông báo lỗi rõ |
| `_search()`/`SearchResult` | Hợp đồng đúng; giữ tên, tham số, trường kết quả; sửa hiển thị nghiệm rỗng và đơn vị bộ nhớ |
| Đo tài nguyên | Thiếu cleanup khi exception, có thể dừng tracing của caller; sửa ownership và `try/finally` |
| BFS | Demo chạy đúng trước và sau; không sửa source |
| A* | `_search()` còn `pass`, heuristic có phản ví dụ; ngoài phạm vi sửa |
| Các file solver khác/GUI | Khung chưa triển khai; không sửa hoặc review thuật toán trong nhiệm vụ này |

Đã đọc README và STRUCTURE hiện có. `README_LLM.md` không tồn tại trong checkout lúc audit; không tạo lại ngoài phạm vi. Hai tài liệu PDF đề bài/kế hoạch nhóm đã được đọc từ các tệp người dùng cung cấp trong `/home/sv/Downloads/`, không được chép vào repository. Tài liệu cũ có thể chứa thành phần dự kiến như `benchmark.py` và level mở rộng chưa tồn tại. Hành vi dưới đây được đối chiếu với source thực tế.

## 2. Kiến trúc và trách nhiệm

```text
main.py
  ├── Board(filepath)                         # Đọc level và giữ luật chơi
  └── Solver(board).solve()                   # Đo lường dùng chung
        └── _search() của lớp con             # Chiến lược tìm kiếm
              ├── get_initial_state()
              ├── ACTIONS / transition()
              ├── is_goal()
              └── visited, frontier, path do solver quản lý
        └── SearchResult
```

`State` biểu diễn dữ liệu và identity; `Board` quyết định luật hợp lệ/chuyển trạng thái/thắng. Solver quản lý frontier, visited, path reconstruction, chi phí, heuristic và stale entries. `BaseSolver` chỉ gọi tìm kiếm, reset counter, đo tài nguyên, đóng gói kết quả. Không đặt thuật toán vào core; không lặp lại bảng lăn trong từng solver hoặc GUI.

## 3. State space, tọa độ và identity

State cơ bản là `S = (r, c, o)`. Public constructor vẫn nhận:

```python
from src.core.state import BloxorzState, Orientation

state = BloxorzState(1, 2, Orientation.HORIZONTAL)
same = BloxorzState(r=1, c=2, orientation=Orientation.HORIZONTAL, bridges_state=())
assert state == same
```

- Chỉ số bắt đầu từ `0`; `r` tăng xuống dưới, `c` tăng sang phải.
- `(r, c)` là ô neo: ô bên trái khi nằm ngang hoặc ô bên trên khi nằm dọc.
- `VERTICAL` là **nằm dọc trên mặt bàn**, khác `STANDING` là đứng thẳng.

| Orientation | Giá trị enum giữ nguyên | Occupied cells |
| --- | --- | --- |
| `STANDING` | `0` | `[(r, c)]` |
| `HORIZONTAL` | `1` | `[(r, c), (r, c + 1)]` |
| `VERTICAL` | `2` | `[(r, c), (r + 1, c)]` |

Identity đầy đủ hiện tại là `(r, c, orientation, bridges_state)`. Hai state bằng nhau có hash bằng nhau; hai bridge configurations khác nhau là hai state khác nhau. `bridges_state` là `Tuple[bool, ...]`, mặc định `()`. Trường này được giữ nguyên qua transition nhưng **chưa điều khiển passability hoặc switch**.

### Dữ liệu hợp lệ và immutability

- `r`, `c` phải là Python `int`, không nhận `bool`, float hoặc chuỗi. Sai kiểu báo `TypeError`.
- `orientation` phải là thành viên `Orientation`; không tự chuyển số `0` hoặc chuỗi thành enum. Giá trị không được hỗ trợ báo `ValueError`.
- `bridges_state` phải là tuple chứa các giá trị `bool`; list hoặc tuple chứa `0/1` bị từ chối bằng `TypeError`.
- Tọa độ âm vẫn biểu diễn được ở mức state; bounds và sàn thuộc trách nhiệm `Board`.

State dùng `@dataclass(frozen=True, eq=False, repr=False)` để không thể gán/xóa các trường bằng thao tác thuộc tính thông thường. Equality/hash và debug representation vẫn do các phương thức hiện có định nghĩa. Việc sửa `state.r`, `state.c`, `state.orientation`, `state.bridges_state` sẽ báo `dataclasses.FrozenInstanceError`; hãy tạo state mới.

Lý do thay đổi: sửa dữ liệu tham gia hash sau khi đưa vào visited/dict có thể làm hỏng tra cứu. Audit mã hiện tại chỉ tìm thấy gán các trường trong constructor cũ, không có caller sửa state tại chỗ; `Board.transition()` đã tạo đối tượng mới. Test xác nhận constructor positional/keyword, hashing, transition và BFS tương thích. Đây là thay đổi có chủ đích về **khả năng ghi thuộc tính**, cần giữ khi phát triển solver sau này; không bảo đảm tương thích với mã bên ngoài repo từng sửa state trực tiếp.

`get_occupied_cells()` trả một list mới, nên sửa list đó không đổi state. `repr()` giữ dạng `State(1, 2, HORIZONTAL)` khi bridge tuple rỗng; khi có flags sẽ hiển thị thêm `bridges_state` để debug.

## 4. Action space

Nguồn định nghĩa duy nhất trong production code là `src/core/board.py`:

```python
from src.core.board import ACTIONS
# ['U', 'D', 'L', 'R']
```

`U` = Up, `D` = Down, `L` = Left, `R` = Right. Giữ thứ tự này khi sinh successor; nó ảnh hưởng cách chọn giữa các nghiệm cùng độ dài trong BFS. Không sửa list `ACTIONS` tại runtime và không tạo bộ action khác trong solver.

Action ngoài tập chuẩn báo `ValueError`, khác với bước lăn đúng action nhưng rơi khỏi sàn trả `None`. Không có action đổi khối đang điều khiển trong baseline cơ bản; phần đó cần thống nhất ở giai đoạn 2.

## 5. Transition model — đủ 12 trường hợp

Mỗi hàng cho một kết quả hình học xác định trước khi kiểm tra sàn:

| Orientation hiện tại | Action | Ô neo mới | Orientation mới | Occupied cells mới |
| --- | --- | --- | --- | --- |
| `STANDING` | `U` | `(r-2, c)` | `VERTICAL` | `(r-2,c)`, `(r-1,c)` |
| `STANDING` | `D` | `(r+1, c)` | `VERTICAL` | `(r+1,c)`, `(r+2,c)` |
| `STANDING` | `L` | `(r, c-2)` | `HORIZONTAL` | `(r,c-2)`, `(r,c-1)` |
| `STANDING` | `R` | `(r, c+1)` | `HORIZONTAL` | `(r,c+1)`, `(r,c+2)` |
| `HORIZONTAL` | `U` | `(r-1, c)` | `HORIZONTAL` | `(r-1,c)`, `(r-1,c+1)` |
| `HORIZONTAL` | `D` | `(r+1, c)` | `HORIZONTAL` | `(r+1,c)`, `(r+1,c+1)` |
| `HORIZONTAL` | `L` | `(r, c-1)` | `STANDING` | `(r,c-1)` |
| `HORIZONTAL` | `R` | `(r, c+2)` | `STANDING` | `(r,c+2)` |
| `VERTICAL` | `U` | `(r-1, c)` | `STANDING` | `(r-1,c)` |
| `VERTICAL` | `D` | `(r+2, c)` | `STANDING` | `(r+2,c)` |
| `VERTICAL` | `L` | `(r, c-1)` | `VERTICAL` | `(r,c-1)`, `(r+1,c-1)` |
| `VERTICAL` | `R` | `(r, c+1)` | `VERTICAL` | `(r,c+1)`, `(r+1,c+1)` |

`Board.transition()` xác thực action, tính ô neo/tư thế, tạo state mới với bridge flags cũ, rồi kiểm tra toàn bộ occupied cells. Nó không mutate source. Các công thức đang đúng được giữ nguyên, không tạo transition engine hoặc successor helper thứ hai.

Caller truyền một `BloxorzState` hợp lệ trên board làm source. Hàm kiểm tra trạng thái **đích của bước lăn**, không bổ sung một lượt validate source; trạng thái tự tạo cần được kiểm tra bằng `is_valid_state()` trước khi dùng làm gốc tìm kiếm.

## 6. Level input và validity checking

Schema cơ bản được giữ nguyên:

```json
{
  "name": "Example",
  "grid": [[1, 1, 2], [1, 1, 1]],
  "start": [0, 0],
  "goal": [0, 2]
}
```

Ví dụ trên minh họa schema, không cam kết level đó có nghiệm. `name` và metadata khác được chấp nhận nhưng không được `Board` sử dụng. Không yêu cầu phải có ô `2`; trường `goal` quyết định tọa độ đích.

Constructor kiểm tra:

1. JSON phải là object và có `grid`, `start`, `goal`.
2. Grid phải là list không rỗng, các hàng là list không rỗng, cùng số cột.
3. Tile codes phải là Python `int`, không nhận boolean hoặc giá trị không nguyên.
4. Start/goal là list đúng hai số nguyên `[row, col]`, nằm trong biên và không trên void.

Malformed JSON/schema/level báo `ValueError` có ngữ cảnh; malformed JSON giữ `JSONDecodeError` ở `__cause__` và thông báo vị trí dòng/cột. Lỗi đọc file như `FileNotFoundError`, `PermissionError` giữ exception hệ thống. Không có cơ chế tự sửa dữ liệu level.

Một occupied cell hợp lệ phải thỏa `0 <= r < rows`, `0 <= c < cols` và `grid[r][c] != 0`. Mọi ô khối chiếm đều phải hợp lệ. Chỉ một trong hai ô ngoài biên/trên void cũng làm cả state không hợp lệ.

Mã tile cơ bản: `0` là void, `1` là floor, `2` là ký hiệu goal. Để giữ hành vi cũ, các mã **nguyên khác 0** vẫn được coi là sàn; chấp nhận mã mới không có nghĩa đã hỗ trợ advanced mechanics. Board/grid và `ACTIONS` phải được coi là dữ liệu cố định trong một lượt search.

## 7. Goal test

```text
state.orientation == STANDING
and state.r == board.goal_r
and state.c == board.goal_c
```

Khối nằm ngang hoặc nằm dọc đè qua goal chưa thắng; đứng ở vị trí khác cũng chưa thắng. Khối được phép đi ngang/dọc qua ô goal nếu có đủ sàn. Solver gọi `Board.is_goal()`, không tự tìm ô `2` hay viết điều kiện thắng khác.

`is_goal()` chỉ kiểm tra placement/tư thế, không gọi lại `is_valid_state()`. Constructor đã bảo đảm goal có sàn; solver bình thường chỉ nhận state đầu hợp lệ và successor hợp lệ.

## 8. Core API — input, output, lỗi và ví dụ

| API | Input | Output/ý nghĩa | Lỗi và điều kiện sử dụng |
| --- | --- | --- | --- |
| `Board(filepath)` | Đường dẫn JSON UTF-8 | Board có grid, rows/cols, start/goal | `ValueError` nếu JSON/schema/level sai; lỗi hệ thống khi không đọc được file |
| `get_initial_state()` | Không có | State mới đứng tại start, bridge flags `()` | Board phải được tạo thành công |
| `is_valid_cell(r, c)` | Hai Python `int` | `bool`: có sàn và trong biên | `TypeError` với kiểu tọa độ sai; ngoài biên/trên void trả `False` |
| `is_valid_state(state)` | `BloxorzState` | `bool`: toàn bộ occupied cells hợp lệ | Caller phải cung cấp đúng kiểu state; không có coercion từ tuple/dict |
| `transition(state, action)` | State source hợp lệ, một action chuẩn | State mới hoặc `None` nếu rơi/ngoài biên | `ValueError` với action ngoài `ACTIONS`; không mutate source |
| `is_goal(state)` | `BloxorzState` | `bool`: standing tại goal | Không tự validate sàn; dùng trên state hợp lệ |
| `BloxorzState(r,c,orientation,bridges_state=())` | Tọa độ nguyên, enum, tuple bool | State có hash ổn định | `TypeError` với tọa độ/flags sai kiểu; `ValueError` với orientation sai |
| `get_occupied_cells()` | Không có | List mới chứa một/hai tuple tọa độ | Constructor bảo đảm orientation hợp lệ |
| `is_standing()` | Không có | `bool` | Không có lỗi dự kiến với state hợp lệ |

Ví dụ chạy từ repo root, dùng level thực tế:

```python
from src.core.board import ACTIONS, Board
from src.core.state import BloxorzState, Orientation

board = Board("levels/level_01.json")
initial = board.get_initial_state()
assert initial == BloxorzState(1, 1, Orientation.STANDING)
assert initial.is_standing()
assert initial.get_occupied_cells() == [(1, 1)]
assert board.is_valid_cell(1, 1)
assert board.is_valid_state(initial)
assert not board.is_goal(initial)

next_state = board.transition(initial, "R")
assert next_state == BloxorzState(1, 2, Orientation.HORIZONTAL)
assert next_state.get_occupied_cells() == [(1, 2), (1, 3)]
assert board.transition(initial, "U") is None
assert ACTIONS == ["U", "D", "L", "R"]
# board.transition(initial, "X") -> ValueError
```

## 9. BaseSolver và hợp đồng tìm kiếm

Giữ nguyên public API:

```python
BaseSolver(board)
solver.solve() -> SearchResult
solver._search() -> Optional[List[str]]
```

`BaseSolver` là abstract class; phải override `_search()` mới khởi tạo được lớp con. `_search()` trả:

| Giá trị | Ý nghĩa |
| --- | --- |
| `['R', 'D', ...]` | Tìm được nghiệm; danh sách actions theo thứ tự từ start đến goal |
| `[]` | Start đã là goal; thành công, 0 bước |
| `None` | Tìm kiếm kết thúc mà không có nghiệm |

Exception thuật toán/đo lường truyền ra ngoài; wrapper không chuyển nó thành thất bại thông thường hoặc thành công giả. Không dùng `None` để che lỗi implementation. `_search()` không tự quản lý `tracemalloc` hoặc wrapper đo khác.

`solve()` reset `expanded_nodes`, kiểm tra ownership tracing, mở tracing, lấy mốc thời gian, gọi `_search()`, lấy mốc kết thúc/peak allocation, đóng tracing trong `finally`, rồi tạo `SearchResult`. Lỗi cũng đóng tracing do wrapper sở hữu. Gọi lại solver sau lỗi vẫn reset counter.

### Phiên tracing đã tồn tại

Nếu `tracemalloc.is_tracing()` đã là `True` trước khi bắt đầu đo, `solve()` báo `RuntimeError` **trước khi gọi `_search()`** và không dừng/reset tracing bên ngoài. Counter vẫn được reset ở đầu `solve()`.

Lý do: peak cũ ở mức process có thể làm sai số đo; reset peak hoặc stop tracing sẽ tác động caller. Baseline chọn từ chối rõ ràng thay vì trả một số đo không độc lập. Caller cần kết thúc phiên tracing do chính mình mở trước khi gọi solver. Không hỗ trợ nested `solve()`, search đồng thời trong cùng process hoặc chạy dưới `python -X tracemalloc`/`PYTHONTRACEMALLOC` đang bật. Không xây dựng framework đo đa luồng.

## 10. SearchResult và các chỉ số

Constructor giữ nguyên:

```python
SearchResult(actions, time_taken, peak_memory, expanded_nodes)
```

| Field | Quy ước |
| --- | --- |
| `actions` | `Optional[List[str]]` từ `_search()` |
| `success` | `actions is not None` |
| `solution_length` | Số action nếu có nghiệm, ngược lại `0` |
| `time_taken` | Thời gian `_search()` theo `time.perf_counter()`, giây |
| `peak_memory` | Peak Python allocation được `tracemalloc` theo dõi, bytes chia `1024`, **KiB** |
| `expanded_nodes` | Counter do solver cập nhật theo mục 11 |

Thời gian không gồm load level, tạo solver, render GUI, tương tác người dùng, in kết quả hoặc tạo `SearchResult`; có overhead theo dõi allocation trong lúc search. Peak allocation không phải RSS/tổng RAM process, và không bao gồm toàn bộ dữ liệu đã cấp phát trước lúc mở tracing. Cả hai số đo thay đổi theo môi trường/phiên chạy.

Output đã sửa nhãn thành `Peak Python Memory: ... KiB`, tránh gọi nhầm là toàn bộ RAM. Nghiệm rỗng hiển thị `Moves (0): (empty)`, thất bại hiển thị `Moves (0): None`. Các field dùng lập trình giữ nguyên. `main.py` chỉ in object và không cần sửa; nếu sau này parse output, nên dùng fields thay vì dựa vào chuỗi `repr()`.

`SearchResult` không tự replay/xác minh nghiệm, không tự kiểm tra kiểu giá trị `_search()` và không tính chi phí đường đi. Các fields là snapshot lúc tạo; không sửa `actions` sau khi nhận kết quả vì có thể làm metadata không còn khớp.

## 11. Quy ước Expanded Nodes

**Tính một node khi lấy nó khỏi frontier và chấp nhận xử lý; không tính stale/duplicate entry bị loại mà không được xử lý thực sự.**

- BFS hiện đánh dấu visited khi enqueue nên không có stale entries cần lọc. Mỗi `popleft()` hiện tại tăng counter, gồm cả goal node.
- Start đã là goal và được kiểm tra trước khi enqueue: counter `0`.
- UCS/A*: pop heap, kiểm tra entry còn đại diện chi phí tốt nhất/còn cần xử lý; entry stale bị bỏ thì không tăng counter. Sau khi qua bước lọc, tăng counter trước goal test/xử lý successors.
- Một state được mở lại hợp lệ vì tìm được đường tốt hơn và được xử lý lại có thể được tính thêm một lần. Counter đếm lần xử lý search node, không phải số state duy nhất.
- IDS: counter cộng dồn các lần xử lý hợp lệ qua mọi depth iteration trong cùng `solve()`; không reset ở mỗi vòng depth. Chỉ wrapper reset trước lượt solve mới.
- Node chỉ được sinh/enqueue chưa được tính là expanded. Counter này cũng không phải kích thước visited hoặc frontier.

Wrapper không biết frontier hoặc stale policy, nên **không tự tăng counter**. Hợp đồng trên là hướng dẫn tích hợp cho solver chưa triển khai, không khẳng định chúng đã được kiểm thử.

## 12. Hướng dẫn tích hợp solver

Các thành viên dùng cùng import/API:

```python
from typing import List, Optional
from src.core.board import ACTIONS
from src.solvers.base_solver import BaseSolver

class YourSolver(BaseSolver):
    def _search(self) -> Optional[List[str]]:
        initial = self.board.get_initial_state()
        if self.board.is_goal(initial):
            return []
        # Cài chiến lược riêng, frontier/visited/path của thuật toán tại đây.
        # Sinh nhánh chỉ bằng self.board.transition(current_state, action).
        # Không dùng khung chưa hoàn thiện này như một solver hoạt động.
        raise NotImplementedError
```

Không có `get_successors()` mới vì vòng lặp qua `ACTIONS` và `transition()` đã đủ, đồng thời giữ nguyên API mà BFS đang dùng.

| Thành viên | Phần tự quản lý | Phần lấy từ baseline |
| --- | --- | --- |
| TV2 — DFS/IDS | Stack/đệ quy, depth limit, xử lý chu trình, cách truy vết path | State identity; Board rules/goal; `BaseSolver.solve()` |
| TV3 — UCS | Heap, hàm chi phí, best-cost map, stale filtering, path | Cùng State/Board; cùng counter và wrapper đo |
| TV4 — Greedy | Frontier theo heuristic, visited/path, tie-break | Cùng Core API và result contract |
| TV5 — A* | `g+h`, heuristic phù hợp cost, best-cost/reopen/stale policy | Cùng Core API và result contract |

Baseline chưa định nghĩa cost API chung. Không áp đặt các ví dụ cost của kế hoạch nhóm vào core. Nếu dùng chi phí không đồng nhất, UCS/A* tối ưu **chi phí được định nghĩa**, không nhất thiết tối thiểu số bước; cần trình bày rõ khi so sánh với BFS. Heuristic phải phù hợp cost và các cơ chế state được hỗ trợ.

`BloxorzState` không có phép so sánh thứ tự. Khi dùng `heapq`, thêm tie-breaker ổn định, ví dụ counter, để hai priority bằng nhau không dẫn tới so sánh trực tiếp state. Đây là lưu ý tích hợp, không phải thuật toán được thêm trong nhiệm vụ này.

### Checklist bàn giao cho người làm solver

- [ ] Import `ACTIONS` từ core, giữ thứ tự `U/D/L/R`.
- [ ] Dùng `Board` làm nguồn luật duy nhất; không viết transition/goal test riêng.
- [ ] Giữ constructor/state identity, không gán lại state trong visited/dict.
- [ ] Kế thừa `BaseSolver`; chỉ cài chiến lược trong `_search()`.
- [ ] Trả list/`[]`/`None` đúng nghĩa; exception không bị che thành vô nghiệm.
- [ ] Đếm expanded sau stale filtering, tính goal được xử lý; reset do wrapper.
- [ ] Dùng wrapper đo time/memory; không tự start/stop tracing trong `_search()`.
- [ ] Xử lý visited/cycle/depth hoặc best-cost phù hợp thuật toán.
- [ ] Replay nghiệm qua `Board.transition()` và xác nhận `is_goal()`.
- [ ] Không đổi core API/cost/schema khi chưa thống nhất với nhóm.

## 13. Kiểm thử và kết quả đã xác minh

Chạy từ thư mục gốc repo, không cần cài thêm dependency:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B main.py
git diff --check
```

`-B` chỉ ngăn sinh `__pycache__`; có thể bỏ khi phát triển. Nếu máy có lệnh `python` trỏ tới Python 3 tương ứng thì dùng thay `python3`. README gốc nêu Python >=3.9; lần kiểm chứng này dùng **Python 3.14.4**, chưa chạy ma trận nhiều phiên bản.

Kết quả thực tế: **59 tests pass, 0 fail, 0 error**.

| File | Số test methods | Nội dung |
| --- | --- | --- |
| `tests/test_state.py` | 16 | Enum/constructor, occupied cells/anchor, identity/hash, bridge flags, immutability, invalid input, repr |
| `tests/test_board.py` | 25 | Geometry, biên/void, action, goal, JSON/schema và BFS regression |
| `tests/test_base_solver.py` | 18 | Dummy outcomes, counter reset, thời gian, peak allocation, cleanup/exception, external/nested tracing |

Một test geometry dùng **12 subtests**, mỗi subtest xét một orientation/action từ `(4,4)` trên board floor `9×9`, kiểm tra tọa độ, tư thế, các ô chiếm chỗ, flags và source không đổi. Các test validation còn dùng nhiều subtests riêng; không cộng chúng thành số test methods ở bảng.

Tests tạo level JSON trong temporary directories, không sửa `levels/`. Dummy solver chỉ trả kết quả định sẵn và cập nhật counter, không cài thuật toán tìm kiếm mới. Tests đo lường có cả clock/peak mock để xác minh đơn vị chính xác và allocation thật trong `_search()`; không so sánh số thời gian/RAM cụ thể phụ thuộc máy.

### BFS regression trước và sau

```text
Start: (1, 1), Goal: (1, 6)
Success: True
Moves (7): R -> R -> D -> L -> U -> R -> R
Expanded Nodes: 35
```

Replay bằng `Board.transition()`:

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

Có thêm regression cases start=goal (`[]`, success, 0 node) và level không thể đi tới đích (`None`, failure). Không thay source BFS. Các số time/memory không dùng làm expected cố định.

## 14. Checklist mentor review và trình bày 7 phút

TV5 có thể kiểm tra baseline bằng các lệnh ở mục 13, đối chiếu bảng 12 transition, tests hash/immutability, validation và wrapper exception cleanup; xác minh diff không đụng BFS/solver khác. Đây là checklist chuẩn bị, chưa ghi nhận phê duyệt của TV5.

### Checklist để TV1 review DFS/IDS của TV2 sau này

- [ ] Tài giải thích frontier LIFO/đệ quy và giới hạn recursion/depth.
- [ ] Nghiệm được replay trên cùng Board và đạt goal.
- [ ] Map có chu trình không gây lặp vô hạn; giải thích visited/path checking.
- [ ] IDS tăng depth limit, phân biệt cutoff và không có nghiệm theo thiết kế.
- [ ] Visited của DFS/IDS không loại nhầm state có thể tới ở độ sâu phù hợp hơn.
- [ ] Trả `[]` khi start là goal và `None` khi tìm hết không có nghiệm.
- [ ] Counter theo mục 11, đủ bốn chỉ số, không tự viết wrapper đo riêng.
- [ ] Người viết giải thích ưu/nhược điểm và các phần code quản lý frontier/path.

Chưa thực hiện review hoặc sửa code DFS/IDS trong nhiệm vụ hiện tại.

### Dàn ý giải thích kỹ thuật 7 phút

| Thời lượng | Nội dung trình bày |
| --- | --- |
| 0:00–1:00 | State cần orientation vì cùng ô neo có thể chiếm các ô khác nhau và có successor khác nhau |
| 1:00–2:00 | Anchor convention, ba tư thế và cách đọc 12 dòng bảng lăn |
| 2:00–3:00 | Một nguồn luật trong Board; move hợp lệ/`None`/action sai; goal cần đứng thẳng |
| 3:00–4:00 | Equality/hash, visited tránh chu trình; bridge flags làm tương lai khác nhau nên phải tham gia identity |
| 4:00–5:00 | Vai trò BaseSolver; list/`[]`/`None`, counter và phân biệt stale entries |
| 5:00–6:00 | `perf_counter`, KiB Python allocation khác RSS; exception cleanup và ownership tracing |
| 6:00–7:00 | Chạy tests/BFS replay, giới hạn hiện tại, reviewer nhận xét |

## 15. Giới hạn hiện tại và lỗi ngoài phạm vi

**Đã hỗ trợ:** ba tư thế, lăn cơ bản, bounds/void/goal, validated JSON, state identity ổn định, shared solver/result/measurement contract và unit tests.

**Chưa hỗ trợ:** fragile rules, bridge effects, soft/heavy/split activation, toggle/permanent semantics, teleport, split/rejoin, khối đang điều khiển, advanced transitions, GUI, bộ 16 level hoặc benchmark hàng loạt. Các cơ chế này là nhiệm vụ toàn project/giai đoạn 2, không được đánh dấu đã xong khi chỉ có `bridges_state`.

Baseline chưa có cost function chung, timeout/cancellation, đo RSS, tracing đa luồng hoặc xác minh tự động path do mọi solver trả về. Không thay đổi schema để thêm những tính năng đó ở giai đoạn này.

`src/solvers/astar.py` có `_search()` chỉ `pass`, nên gọi `solve()` sẽ trả failure mà không tìm kiếm. Heuristic hiện có phản ví dụ trên level demo: state `(1,4,HORIZONTAL)`, goal `(1,6)`, còn một bước `R` nhưng heuristic trả `2`. Không được coi heuristic này đã admissible hoặc A* đã hoàn thiện; ghi nhận cho TV5, giữ nguyên file.

README/STRUCTURE chưa cập nhật thông tin baseline này vì nằm ngoài phạm vi file được phép sửa. Khi tài liệu cũ khác hợp đồng hiện tại, dùng tài liệu này và source baseline; việc cập nhật tài liệu gốc cần một nhiệm vụ được cho phép riêng.

## 16. Future Extensions — thiết kế cần thống nhất

Các mục sau là phân tích cho giai đoạn 2, **chưa triển khai**:

1. **Fragile:** Board cần phân loại tile và cấm khối đứng trên fragile, vẫn cho nằm nếu toàn bộ sàn hợp lệ.
2. **Bridges:** thống nhất thứ tự bridge IDs/flags, trạng thái ban đầu trong level và ý nghĩa bool. `Board` đọc passability từ state thay vì sửa global board theo đường đi.
3. **Switches:** thống nhất soft/heavy/split, linked bridge IDs, toggle/permanent, và thời điểm kích hoạt so với validation sàn. Cần quyết định khi khối tiếp tục đè một switch thì có kích hoạt lại không và xử lý nhiều switch cùng lúc thế nào.
4. **Split state:** cần mode nguyên khối/tách khối, hai vị trí cube và khối đang điều khiển. Các trường ảnh hưởng successor phải tham gia equality/hash. Chưa chốt hai cube có identity riêng hay chuẩn hóa thứ tự vị trí; nếu canonicalize phải giữ đúng active cube.
5. **Split actions/cost:** hiện chỉ có bốn roll actions. Cần thống nhất việc đổi active cube là action tìm kiếm hay chỉ điều khiển GUI, có tốn move/cost không, và cách biểu diễn nó trong `List[str]` để replay được.
6. **Rejoin/teleport:** thống nhất vị trí đích split, điều kiện hai cube kề nhau và tư thế/ô neo khi nhập lại. Cube đơn không được tự hoàn thành goal hoặc kích hoạt heavy switch.
7. **Compatibility:** giữ Board là nguồn luật duy nhất, không mutate state của nhánh search khác; mở rộng JSON có version/default tương thích level cũ và cập nhật tests/replay/heuristic cùng lúc.

### Quyết định cần nhóm trưởng và thành viên liên quan xác nhận

- Schema/IDs tile, bridge, switch; biểu diễn toggle/permanent và cấu hình cầu ban đầu.
- Thứ tự áp dụng switch, cầu và kiểm tra sàn; quy tắc kích hoạt lại/switch đồng thời.
- Model split/active cube, action đổi khối và chi phí của action đó.
- Hàm chi phí UCS do TV3 thiết kế; cost model nào dùng để so sánh A* và chứng minh heuristic, có cần API cost chung hay không.
- Có cần mở rộng `SearchResult` với total cost/status timeout ở nhiệm vụ tiếp theo; baseline hiện không thêm field.

Các quyết định này không chặn review baseline **cơ bản**, nhưng phải được thống nhất trước khi triển khai cơ chế nâng cao và thí nghiệm tương ứng.

## 17. Git handoff, atomic commits và PR đề xuất

Các thay đổi đang nằm trên `feat/phuoc/shared-baseline`, chưa stage/commit/push/PR. Mỗi nhóm commit dưới đây chỉ là đề xuất, gồm source và tests liên quan để có thể review độc lập:

| Commit message đề xuất | Files |
| --- | --- |
| `fix(state): validate and freeze search state` | `src/core/state.py`, `tests/test_state.py` |
| `fix(board): validate levels and reject unsupported actions` | `src/core/board.py`, `tests/test_board.py` |
| `fix(metrics): clean up tracing and clarify search results` | `src/solvers/base_solver.py`, `tests/test_base_solver.py` |
| `docs(core): document shared baseline and team handoff` | `docs/BASELINE.md` |

Không tự tạo commit/PR; không force/reset/rebase. Kiểm tra tests và diff trước khi người dùng quyết định thực hiện Git operations. Reviewer đề xuất: **TV5 — Phong**.

### PR title đề xuất

```text
Standardize shared core and search metrics baseline
```

### PR body đề xuất

```markdown
## Summary
Unsupported actions previously produced self-loops, malformed levels failed with
unclear errors, and search exceptions could leave tracemalloc active. Validate
state/levels, protect hashed state identity, reject unsupported actions, and make
measurement cleanup exception-safe while preserving the shared solver API.

## Files changed
- src/core/state.py: validate inputs and freeze identity fields.
- src/core/board.py: validate level input and reject unsupported actions;
  preserve all 12 movement formulas.
- src/solvers/base_solver.py: safe tracing ownership/cleanup, accurate KiB label,
  distinct empty-solution display; retain existing result fields.
- tests/test_state.py, tests/test_board.py, tests/test_base_solver.py.
- docs/BASELINE.md: API, metrics, integration/review checklists, future decisions.

## Tests performed
- python3 -B -m unittest discover -s tests -v: 59 tests pass.
- All 12 orientation/action combinations verified with subtests.
- python3 -B main.py: RRDLURR, 7 moves, 35 expanded nodes.
- Replay each demo action through Board.transition() and confirm goal.
- Validate counter reset, empty/failure results, exception cleanup and ownership
  of tracing sessions, including external/nested tracing rejection.
- git diff --check.

## API compatibility
Constructor parameters, Orientation values, ACTIONS order, Board methods,
_search() signature and SearchResult fields are preserved. Existing callers only
read state; assignments now raise FrozenInstanceError to protect visited keys.
Unsupported actions now raise ValueError; invalid levels fail early.
Existing external tracing now raises RuntimeError without stopping that session.
Result display uses KiB Python allocation and distinguishes [] from None.

## Known limitations
Basic gameplay only; advanced mechanics, cost model and other solver algorithms
are separate tasks. No GUI/dependency/level changes. No multi-version Python test
matrix or concurrent/nested solver measurement support.

## Review
Reviewer: TV5 — Phong.
BFS source remains byte-for-byte unchanged. Other solver sources remain unchanged.
No mentor approval is claimed by this draft.
```
