# Đóng góp và contract solver

## Nhánh và commit

Tên nhánh: `<type>/<thanh-vien>/<tinh-nang>`; ví dụ `feat/phuoc/mechanics-guide`, `fix/phong/astar-heuristic`. Dùng `feat`, `fix`, `perf`, `docs`, `test` hoặc `refactor` theo thay đổi.

Commit: `<type>(<scope>): <mô tả ngắn>`; ví dụ `docs(readme): document weighted solvers and code structure`. Commit có phạm vi rõ, không chứa save cá nhân, môi trường ảo hoặc kết quả sinh ngoài ý muốn.

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/<ten>/readme
# Sửa code/tài liệu, chạy kiểm tra phù hợp
git status
git add README.md
git commit -m "docs(readme): improve usage documentation"
git fetch origin
git merge origin/main
# Giải quyết xung đột và kiểm tra lại trước khi push
git push -u origin docs/<ten>/readme
```

Tạo PR và gán reviewer của nhóm. Chỉ đổi nhánh khi đã bảo toàn thay đổi cục bộ; không reset/clean để bỏ qua conflict.

## Viết solver

Kế thừa `BaseSolver` trong [base_solver.py](src/solvers/base_solver.py). `_search()` trả `list[str]` khi có nghiệm, `[]` nếu root đã ở Goal, `None` khi không tìm được nghiệm.

- Lấy root bằng **`self.get_start_state()`**, không gọi thẳng Initial State: GUI cần giải từ trạng thái đang chơi.
- Duyệt **`self.board.get_actions(state)`** để hỗ trợ action đổi cube.
- Dùng `Board.transition()` và `Board.is_goal()`; không viết lại luật trong solver.
- Tăng `self.expanded_nodes` khi xử lý node; loại stale entry trước khi đếm.
- Board/state không bị mutate; state key phải giữ cả bridge flags và active cube.
- Cost phụ thuộc action trước cần key `(state, last_action)` phù hợp; chỉ key theo state có thể loại đường đi tốt hơn.
- Không tự mở `tracemalloc` trong `_search()`; `solve()` sở hữu phép đo. Không gọi các `solve()` lồng nhau khi tracing còn chạy.

Ví dụ BFS tối giản để minh họa contract (không thay solver production):

```python
from collections import deque
from src.solvers.base_solver import BaseSolver


class ExampleSolver(BaseSolver):
    def _search(self):
        root = self.get_start_state()
        frontier = deque([(root, [])])
        seen = {root}
        while frontier:
            state, path = frontier.popleft()
            self.expanded_nodes += 1
            if self.board.is_goal(state):
                return path
            for action in self.board.get_actions(state):
                nxt = self.board.transition(state, action)
                if nxt is not None and nxt not in seen:
                    seen.add(nxt)
                    frontier.append((nxt, path + [action]))
        return None
```

Sử dụng API:

```python
from src.core.board import Board
from src.solvers.astar import AStarSolver
from src.solvers.UCS_Algorithm.cost_functions import UniformCost

board = Board('levels/level_01.json')
result = AStarSolver(board).solve()  # Weighted cost mặc định
unit_result = AStarSolver(board, cost_function=UniformCost()).solve()
# Khi có trạng thái gameplay đã commit: solver.solve(start_state=current_state)
print(result)
```

Không dùng số action để kết luận A* weighted sai khi khác BFS. So sánh A*/UCS với cùng cost model và root; dùng UniformCost khi kiểm tra tối ưu số action. Heuristic phải là chặn dưới của chi phí còn lại; đặc biệt cẩn trọng với teleport và chi phí Space bằng 0.

## Kiểm tra trước PR

```bash
python -B -m unittest discover -s tests
git diff --check
```

Replay action qua Core để xác nhận Goal, kiểm tra root hiện tại, split/bridge flags và không mutate dữ liệu. Thay GUI/animation cần chạy Panda3D thật bằng công cụ phù hợp trong `tools/`; không xem ảnh giả hoặc mock là bằng chứng runtime. Khi cập nhật kết quả benchmark, ghi rõ revision, môi trường, cost model và phạm vi màn đã đo.
