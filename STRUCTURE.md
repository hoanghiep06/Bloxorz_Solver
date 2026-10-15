# 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

> **Lưu ý cho các thành viên:** Khi tạo mới, đổi tên hoặc tái cấu trúc các file/thư mục thuộc phân công của mình, hãy chủ động cập nhật lại sơ đồ cây và bảng mô tả bên dưới trước khi tạo Pull Request (PR).

---

## 1. Sơ đồ cây tổng quan (MVP & Mở rộng)

```text
Bloxorz-Project1/
├── levels/
│   ├── level_01.json              # Level demo cơ bản (Floor + Void + Goal)
│   ├── level_02.json              # (Mở rộng) Level cơ bản nâng độ khó
│   ├── level_05_fragile.json      # (Giai đoạn 2) Map chứa ô cam dễ vỡ
│   ├── level_09_switches.json     # (Giai đoạn 2) Map chứa switch & bridge
│   └── level_13_split.json        # (Giai đoạn 2) Map chứa split switch
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py               # Biểu diễn trạng thái khối (tư thế, vị trí, cầu, khối tách)
│   │   └── board.py               # Quản lý bản đồ, transition model, kiểm tra hợp lệ
│   ├── solvers/
│   │   ├── __init__.py
│   │   ├── base_solver.py         # Lớp trừu tượng BaseSolver & tích hợp đo Benchmark chuẩn
│   │   ├── bfs.py                 # Thuật toán BFS (Breadth-First Search) [TV 1]
│   │   ├── dfs.py                 # Thuật toán DFS (Depth-First Search) [TV 2]
│   │   ├── ids.py                 # Thuật toán IDS (Iterative Deepening Search) [TV 2]
│   │   ├── ucs.py                 # Thuật toán UCS (Uniform-Cost Search) [TV 3]
│   │   ├── greedy.py              # Thuật toán GBFS (Greedy Best-First Search) [TV 4]
│   │   ├── astar.py               # Thuật toán A* Search [TV 5]
|   |   └── ids.py                 # Thuật toán IDS
│   └── gui/                       # (Giai đoạn 2 - Phụ trách: TV 2 & TV 3)
│       ├── __init__.py
│       ├── renderer.py            # Vẽ sàn, khối, hiệu ứng lật
│       └── controller.py          # Nút bấm UI, điều khiển tay, auto-replay
├── main.py                        # Điểm chạy kiểm thử nhanh trên Terminal
├── benchmark.py                   # (Giai đoạn 2) Script chạy tự động bộ test cases & xuất CSV
├── requirements.txt               # Danh sách thư viện phụ thuộc
├── STRUCTURE.md           # Tài liệu cấu trúc thư mục này
└── README.md                      # Hướng dẫn cài đặt, quy ước git và chạy thuật toán
```

---
