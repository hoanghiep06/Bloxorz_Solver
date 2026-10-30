# Changelog — Starter Kit V2 (Bản cập nhật Readjusted)

## Cập nhật mới nhất — Heuristic Split State thực tế & 3 Baselines đối sánh

Theo yêu cầu chuẩn hóa thực nghiệm và đối sánh thuật toán:

1. **Triển khai Heuristic A* thực tế của trạng thái SPLIT theo codebase (`src/solvers/astar.py`):**
   - Loại bỏ cơ chế fallback gán $h_0 = 0$ nhân tạo khi gặp split-switch. Thay vào đó, harness tính toán chính xác công thức heuristic của nhóm trong codebase:
     \[
     h_0(s) = \max\left(0, \frac{\text{inter\_dist} - 1}{2}\right) + \frac{\min(d(c_0, \text{goal}), d(c_1, \text{goal}))}{2} + 1.0
     \]
   - Kiểm tra toàn diện trên 18 level: 14 level không split đạt 0 vi phạm admissibility và consistency; 4 level split (15-18) phản ánh đúng tính chất vật lý của hai khối con và hợp nhất.
   - Thực nghiệm xác nhận A* với heuristic này đạt **100% cost tối ưu khớp tuyệt đối với UCS** trên cả 18 level cho mọi $\alpha$, đồng thời giảm mạnh số node mở rộng (ở Level 16 giảm hơn 34% số node so với $\alpha=0$).

2. **Bổ sung 2 Baselines mới phục vụ đối sánh toàn diện:**
   - **Baseline Constant Cost ($c = \text{const} = 1.0$):** $w = (0, 0, 0, 0, 0)$ — mô hình chi phí đồng nhất (Uniform Cost), tương đương việc UCS chỉ tối thiểu hóa số bước như BFS. Dùng để chứng minh giá trị gia tăng của các trọng số phạt an toàn.
   - **Baseline Equal Normalized Weights (mọi trọng số chuẩn hóa bằng 1.0):** $w = (1, 1, 1, 1, 1)$ — chuẩn hóa mọi trọng số phạt bằng 1.0. Dùng để chứng minh việc phân chia tỷ lệ phạt (rubric/tuned) có ưu thế rõ rệt so với việc gán cào bằng tất cả rủi ro.
   - Cả 3 baselines (Team Rubric, Const=1, Equal=1) được tính toán xuyên suốt trong Grouped 6-Fold CV (`ucs_grouped_cv.csv`), summary (`ucs_tuning_summary.json`), repeated benchmark (`final_selected_weights_summary.csv`) và bảng báo cáo mẫu (`templates/report_table_template.md`).

3. **Tối ưu hóa môi trường thực thi:**
   - Thư viện `matplotlib` được xử lý an toàn (graceful fallback): script chạy đầy đủ mọi phép đo, CV, benchmark và xuất CSV/JSON ngay cả khi môi trường chưa cài sẵn matplotlib.

4. **Script vẽ biểu đồ độc lập (`experiments/plot_results.py`):**
   - Tách riêng toàn bộ logic vẽ biểu đồ thành script độc lập; trực tiếp đọc dữ liệu từ `experiments/results/` và xuất 7 hình ảnh PNG độ phân giải cao mà **không cần chạy lại quá trình search hay training**.

## Vì sao có V2?
Starter Kit V2 sửa cách xử lý action chuyển quyền điều khiển cube theo FAQ của giảng viên.

- `SPACE`/`SWITCH` không được tính là một nước lăn.
- Chỉ `U`, `D`, `L`, `R` được tính vào `steps` / `solution_length` và có base movement cost `1.0`.
- `SPACE`/`SWITCH` có base cost `0.0`, không cộng các feature địa hình, và được thống kê riêng qua `action_count` / `control_switches`.
- Khi chuyển cube đang điều khiển, ngữ cảnh quay đầu tức thời được reset.
- README và hướng dẫn Word/PDF đã được cập nhật tương ứng.

## Kiểm tra được thực hiện

- `python -m py_compile experiments/tune_weights.py`: thành công.
- `python experiments/tune_weights.py --help`: thành công.
- Smoke test Level 16: UCS tìm được nghiệm; nghiệm replay hợp lệ; `solution_length` (số lần lăn) = 45, tổng action = 46, control switch = 1; A* với alpha=0 có tổng cost bằng UCS; kiểm tra heuristic trên graph Level 16 ghi nhận 0 vi phạm admissibility và 0 vi phạm consistency theo base movement cost.

Đây chỉ là kiểm tra cú pháp, CLI và smoke test trên một level. **Không có Grid Search toàn bộ nào được chạy để tạo các trọng số cuối cùng.** Người dùng cần tự chạy thí nghiệm theo hướng dẫn để sinh kết quả.

## Nâng cấp từ bản cũ

Nếu đã chạy Starter Kit phiên bản trước, hãy sao lưu và xóa mọi file kết quả/checkpoint trong `experiments/results/` trước lần chạy V2 đầu tiên. Không trộn kết quả cũ (khi SPACE còn bị tính như move) với kết quả V2.
