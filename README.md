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

* **Python:** Phiên bản `>= 3.9` (Khuyến nghị 3.10 hoặc 3.11).
* **Môi trường ảo (khuyến khích):**

```bash
# 1. Tạo môi trường ảo
python -m venv venv

# 2. Kích hoạt môi trường ảo
# Trên Windows:
venv\Scripts\activate
# Trên macOS / Linux:
source venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 2. Hướng dẫn chạy chương trình

### A. Chạy kiểm thử nhanh trên Terminal (CLI)
Sau khi hoàn thiện thuật toán của mình, mở file `main.py`, bỏ comment phần import solver bạn phụ trách và chạy:

```bash
python main.py
```

Kết quả in ra sẽ tự động chứa đủ 4 chỉ số thực nghiệm:
* **Trạng thái:** Thành công / Thất bại.
* **Chuỗi bước đi (Solution Path):** Dãy các thao tác `U`, `D`, `L`, `R`.
* **Độ dài lời giải (Solution Length):** Số bước đi tối ưu hoặc tìm được.
* **Số node đã mở (Expanded Nodes):** Số trạng thái được lấy ra khỏi Frontier.
* **Thời gian tìm kiếm (Search Time):** Đơn vị giây ($s$).
* **Bộ nhớ đỉnh (Peak RAM):** Đơn vị $KB$ (đo bằng `tracemalloc`).

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