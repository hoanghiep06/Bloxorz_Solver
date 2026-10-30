# Bảng kết quả để điền sau khi chạy

Không điền số giả định. Lấy số từ `experiments/results/final_selected_weights_summary.csv` và `ucs_tuning_summary.json`.

## 1. Bảng so sánh Benchmark lặp (18 Level)

| Thuật toán / Cấu hình | Tham số cấu hình | Tỷ lệ nghiệm hợp lệ | Median thời gian (ms) | Median bộ nhớ (KiB) | Mean node mở rộng | Median số lần lăn (U/D/L/R) | Median action count | Median control switches | Median total cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **UCS (Tuned)** | `w_backtrack=...; w_void=...; w_fragile=...; w_switch_change=...; w_bridge_entry=...` | ... | ... | ... | ... | ... | ... | ... | ... |
| **UCS (Baseline Rubric)** | `(3.0, 2.0, 4.0, 2.5, 3.0)` | ... | ... | ... | ... | ... | ... | ... | ... |
| **UCS (Baseline Const=1)** | `cost_function = const = 1.0 (w=(0, 0, 0, 0, 0))` | ... | ... | ... | ... | ... | ... | ... | ... |
| **UCS (Baseline Equal=1)** | `all penalty weights = 1.0 (w=(1, 1, 1, 1, 1))` | ... | ... | ... | ... | ... | ... | ... | ... |
| **A* (Tuned)** | `UCS weights = ...; alpha=...` *(Heuristic split-state codebase)* | ... | ... | ... | ... | ... | ... | ... | ... |
| **GBFS (Tuned)** | `w_orientation=...; w_split=...; w_edge=...; w_fragile=...` | ... | ... | ... | ... | ... | ... | ... | N/A |
| **GBFS (Baseline)** | `w_orientation=1; w_split=1; w_edge=0; w_fragile=0` | ... | ... | ... | ... | ... | ... | ... | N/A |

## 2. Bảng so sánh 3 Baselines UCS trên Grouped 6-Fold Cross-Validation

| Cấu hình UCS | Định nghĩa | Mean Quality Loss (18 levels) | Mean Held-out Loss (6 Folds) | Mức cải thiện của Tuned so với Baseline |
|---|---|---:|---:|---:|
| **Baseline Const=1** | $c = \text{const} = 1.0$ (Uniform step cost / unweighted BFS) | ... | ... | +... |
| **Baseline Equal=1** | All penalty weights = 1.0 ($w_i = 1.0$) | ... | ... | +... |
| **Baseline Team Rubric** | Rubric kỹ thuật ban đầu $(3, 2, 4, 2.5, 3)$ | ... | ... | +... |
| **UCS Tuned (Selected)** | Cấu hình tốt nhất từ Grid Search | ... | ... | — |

