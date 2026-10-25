# 🎮 Bloxorz Solver - Project 1 (CSC14003 - AI)

Dự án cài đặt và giải trò chơi giải đố **Bloxorz** bằng các thuật toán tìm kiếm trong Trí tuệ nhân tạo (BFS, DFS/IDS, UCS, Greedy, $A^*$).

---

## 📋 Mục lục
1. [Yêu cầu hệ thống & Cài đặt](#1-yêu-cầu-hệ-thống--cài-đặt)
2. [Hướng dẫn chạy chương trình](#2-hướng-dẫn-chạy-chương-trình)
3. [Quy ước làm việc nhóm & Quy trình Git](#3-quy-ước-làm-việc-nhóm--quy-trình-git)
4. [Khuôn mẫu viết Solver mới](#4-khuôn-mẫu-viết-solver-mới)
5. [Cấu trúc Benchmark chuẩn](#5-cấu-trúc-benchmark-chuẩn)

---

## 1. Yêu cầu hệ thống & Cài đặt

* **Python:** Khuyến nghị Python **3.12**. Code sử dụng cú pháp Python 3.10 trở lên; không dùng Python 3.9.
* **Giao diện:** Panda3D **1.10.16**, được cài tự động từ `requirements.txt`. Các module `direct.*` nằm trong cùng gói Panda3D.
* **Hiển thị:** Cần môi trường desktop và driver OpenGL để mở cửa sổ game. Kích thước cửa sổ tối thiểu là **1024 × 720**.
* Chạy các lệnh bên dưới tại thư mục gốc của repo. Dùng môi trường ảo riêng cho dự án.

Đã kiểm tra quy trình cài mới trên Linux với Python **3.12.14** và Panda3D **1.10.16**: mở GUI, di chuyển, Restart, chạy BFS và toàn bộ 431 test đều đạt.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Windows (Command Prompt):**

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Trên Windows PowerShell, có thể gọi trực tiếp `.venv\Scripts\python.exe -m pip install -r requirements.txt` và `.venv\Scripts\python.exe -B main.py` mà không cần kích hoạt môi trường.

Nếu Ubuntu/Debian báo thiếu `ensurepip` khi tạo môi trường, cài gói venv tương ứng với phiên bản Python đang dùng (ví dụ `python3.12-venv` cho Python 3.12), rồi tạo lại `.venv`.

Kiểm tra thư viện sau khi cài:

```bash
python -m pip check
python -c "from panda3d.core import PandaSystem; print(PandaSystem.getVersionString())"
```

Lệnh cuối phải in `1.10.16`. Nếu báo `No module named 'panda3d'`, kiểm tra đang dùng đúng Python của `.venv` và chạy lại lệnh cài thư viện ở trên.

---

## 2. Hướng dẫn chạy chương trình

### A. Chạy game 3D

Sau khi cài đặt và kích hoạt môi trường ảo:

```bash
python -B main.py
```

`main.py` mở GUI hiện tại; không cần sửa import hoặc bỏ comment solver. Bấm **Start → chọn level** để chơi. Dùng **WASD / phím mũi tên** để di chuyển, **Space** để đổi khối khi tách, **R** để chơi lại. Vào **Settings → Mouse** để điều khiển bằng chuột.

Nút **AI Solver** xuất hiện sau 30 giây không di chuyển. Mở nút này để chọn BFS, DFS, IDS, UCS, Greedy hoặc A*, sau đó dùng Play / Step. HUD hiển thị số bước, thời gian tìm kiếm, số node, độ dài nghiệm và bộ nhớ đỉnh của các allocation Python (`Peak Python Memory`, không phải toàn bộ RAM tiến trình).

Chạy bộ test trong cùng môi trường:

```bash
python -B -m unittest discover -s tests
```

### B. Chạy Benchmark hàng loạt (Giai đoạn 2)
```bash
python benchmark.py
```
Kết quả đo trên toàn bộ các map trong thư mục `levels/` sẽ được xuất ra file `benchmark_results.csv`.

---

## 3. Quy ước làm việc nhóm & Quy trình Git

### A. Quy tắc đặt tên nhánh (Branch Naming)
Cú pháp: `<loại-nhánh>/<tên-thành-viên>/<tên-tính-năng>`

* `feat/`: Tính năng hoặc thuật toán mới (ví dụ: `feat/nam/bfs-solver`, `feat/an/astar-heuristic`)
* `fix/`: Sửa lỗi logic (ví dụ: `fix/tuan/visited-cycle-dfs`)
* `perf/`: Tối ưu thời gian/bộ nhớ (ví dụ: `perf/tuan/priority-queue-ucs`)
* `docs/`: Viết báo cáo, cập nhật README (ví dụ: `docs/an/heuristic-proof`)
* `test/`: Tạo test case, viết benchmark (ví dụ: `test/hung/benchmark-script`)

### B. Quy tắc Commit (Conventional Commits)
Cú pháp: `<type>(<scope>): <mô tả ngắn gọn>`
* **Ví dụ chuẩn:**
  * `feat(bfs): implement queue exploration logic`
  * `perf(ucs): optimize state hashing for faster lookup`
  * `fix(core): correct vertical roll boundary check`
* **Lưu ý:** Commit mang tính nguyên tử (Atomic Commit), không gom nhiều tính năng không liên quan vào cùng một commit. Tuyệt đối không commit mã nguồn gây lỗi cú pháp.

### C. Quy trình làm việc chuẩn (Standard Workflow)
```bash
# 1. Đồng bộ code mới nhất từ nhánh main
git checkout main
git pull origin main

# 2. Tạo nhánh làm việc cá nhân
git checkout -b feat/<ten>/<ten-thuat-toan>

# 3. Code, kiểm thử cục bộ và commit
git status
git add src/solvers/<file_cua_ban>.py
git commit -m "feat(<scope>): description"

# 4. Kéo cập nhật từ main trước khi đẩy code (giải quyết conflict nếu có)
git fetch origin
git merge origin/main

# 5. Đẩy nhánh lên Remote Repository
git push -u origin feat/<ten>/<ten-thuat-toan>

# 6. Tạo Pull Request (PR) trên GitHub và gán đúng Reviewer (Mentor) phụ trách.
```

---

## 4. Khuôn mẫu viết Solver mới

Tất cả các thuật toán phải kế thừa từ lớp `BaseSolver` trong `src/solvers/base_solver.py` để được tự động đo tài nguyên:

```python
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS

class YourSolver(BaseSolver):
    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        
        # 1. Khởi tạo cấu trúc dữ liệu hàng đợi / ngăn xếp
        # 2. Khởi tạo tập đã thăm (visited set)
        
        while frontier_not_empty:
            # 3. MỖI LẦN LẤY 1 STATE RA KHỎI FRONTIER, BẮT BUỘC TĂNG BIẾN ĐẾM:
            self.expanded_nodes += 1
            
            # 4. Kiểm tra đích
            if self.board.is_goal(current_state):
                return path_to_goal
                
            # 5. Duyệt các nhánh con hợp lệ
            for action in ACTIONS:
                next_state = self.board.transition(current_state, action)
                if next_state is not None:
                    # Kiểm tra visited và đưa vào frontier
                    pass
                    
        return None # Trả về None nếu không tìm thấy lời giải
```

---

## 5. Cấu trúc Benchmark chuẩn

Mỗi thuật toán khi hoàn tất cần được đối chiếu qua 4 tiêu chuẩn bắt buộc:

1. **Search Time ($s$):** Tối ưu thuật toán để giảm thời gian chạy trên các map lớn.
2. **Peak Memory Usage ($KB$):** Sử dụng các cấu trúc dữ liệu nhẹ, hashing tuple thay vì object nặng.
3. **Number of Expanded Nodes:** Đo lường độ hiệu quả của hàm định hướng (heuristic / cost).
4. **Solution Length (Moves):** Kiểm chứng tính tối ưu nghiệm (BFS và $A^*$ bắt buộc phải cho ra nghiệm có số bước ngắn nhất).
