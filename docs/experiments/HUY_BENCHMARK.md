# Bộ thực nghiệm benchmark của Huy

Hai file ở thư mục gốc được tiếp nhận nguyên trạng từ nhánh `test/huy/benchmark-script`, commit `c8c8ab47e10d53adf0aa02f13a139f03907f880d`:

- [benchmark_results.csv](../../benchmark_results.csv)
- [benchmark_summary.csv](../../benchmark_summary.csv)

Đây là bộ số liệu thực nghiệm của Huy dùng để tham chiếu/báo cáo. Việc merge giữ nguyên kết quả, không chạy lại benchmark để thay số liệu theo thuật toán mới trên main.

## Phạm vi và cách đọc

- Level 01–18, sáu solver: BFS, DFS, IDS, UCS, Greedy, AStar.
- File results chứa 108 dòng level/solver, tất cả ghi SUCCESS, và 6 dòng SUMMARY.
- File summary chứa cùng 6 dòng SUMMARY; nội dung khớp phần tổng hợp trong results.
- Thời gian là ms, bộ nhớ là KiB; các cột còn lại giữ nguyên định nghĩa benchmark/evaluator tại thời điểm thực nghiệm.
- Tên commit ghi “540-run”; hai CSV chỉ lưu 108 dòng kết quả level/solver, không kèm raw data từng lượt, run ID hoặc metadata đủ xác định cách tổng hợp các lần lặp. Không tự suy ra số lần lặp hay phương pháp tính trung bình.
- Bộ số liệu không bao gồm Level 19, cũng không phải phép đo lại trên main sau tích hợp weighted solvers và heuristic Split an toàn. Khi trích bảng, ghi nguồn “Thực nghiệm của Huy, c8c8ab4, Level 01–18”.

Giữ nguyên số liệu do tác giả cung cấp. Nếu thực nghiệm thêm trên revision mới, lưu thành bộ riêng và ghi revision, môi trường, cost model, số lần lặp, cách tổng hợp; không âm thầm trộn với bảng này.

## Lưu ý khi chạy lại công cụ

`python benchmark.py` ghi đè `benchmark_results.csv` và `benchmark_summary.csv`. Đổi `--output` chỉ đổi file chi tiết; summary vẫn ghi ở thư mục chạy. Hãy bảo toàn bộ số liệu Huy trước khi chạy nếu cần giữ bằng chứng gốc. Chỉ merge dữ liệu và tài liệu nguồn, không sửa thuật toán, Core, GUI hoặc level.
