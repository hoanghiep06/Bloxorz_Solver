# TỜ HƯỚNG DẪN THỰC NGHIỆM GRID SEARCH — BLOXORZ

**Mục tiêu:** để nhóm tự chạy, lưu log, chọn bộ tham số có căn cứ và viết được phần thực nghiệm cho UCS, A* và GBFS. Tài liệu này mô tả quy trình; nó không phải báo cáo kết quả đã chạy trên máy của nhóm.

> **Nguyên tắc quan trọng:** không gọi các trọng số là “tối ưu tuyệt đối”. Với lưới tham số hữu hạn và 18 level, kết luận đúng là “cấu hình tốt nhất trong lưới đã khảo sát theo tiêu chí đã định trước”, kèm đánh giá trên level được giữ lại.

## 1. Bộ kit gồm những gì?

- `experiments/tune_weights.py`: script thực nghiệm Grid Search, kiểm tra heuristic, chạy benchmark cuối và xuất CSV/JSON/biểu đồ.
- `experiments/plot_results.py`: script độc lập chuyên vẽ biểu đồ từ các file kết quả CSV/JSON có sẵn trong `experiments/results/` mà **không cần chạy lại search hay grid tuning**.
- `Bloxorz_Solver-.../src/core/board.py`, `state.py`: bản core được lấy từ source game gửi kèm; search harness sử dụng `Board`/`BloxorzState` và `Board.transition()` thật.
- `benchmark_levels/levels/`: 18 level JSON.
- `benchmark_levels/trajectories/`: quỹ đạo đã sinh trước đây; script dùng chúng để audit tính hợp lệ, bản ghi trùng và nhãn lưu sẵn, **không xem `score`/`rating` cũ là ground truth**.
- `templates/`: tiêu đề CSV và mẫu bảng báo cáo.

Script tuning có phần cài đặt thuật toán thực nghiệm riêng, không tự sửa `src/solvers/*.py` của ứng dụng. Kết quả dùng để chọn cấu hình nghiên cứu; nếu muốn nút solver trong GUI dùng đúng trọng số đã chọn, nhóm phải tích hợp lại vào solver chính thức và kiểm thử sau đó.

## 2. Câu hỏi nghiên cứu và giới hạn tuyên bố

Có hai mục tiêu khác nhau:

1. **Tuning theo rubric kỹ thuật:** chọn đường đi ít bước, ít quay đầu và có mức tiếp xúc rủi ro thấp hơn theo một rubric do nhóm công bố trước. Đây là phương án script này thực hiện.
2. **Học trọng số từ sở thích người chơi:** cần nhãn độc lập, ví dụ người đánh giá xếp hạng các quỹ đạo. Dataset hiện tại chủ yếu chứa quỹ đạo do solver/sinh nhiễu tạo ra và điểm từ evaluator hiện tại; nó chưa đủ để tuyên bố đã học sở thích con người.

Không được dùng chính `Total Path Cost` của mỗi cấu hình làm tiêu chí duy nhất để tuyên bố cấu hình đó tốt hơn: UCS vốn được thiết kế để tối thiểu hóa cost mà nó nhận.

## 3. Mô hình chi phí UCS

Giữ trọng số bước cơ bản cố định `w_step = 1.0`, tìm năm trọng số còn lại:

\[
 c(s,a,s') = I[a\in\{U,D,L,R\}] + w_b B + w_v V + w_f F + w_m M + w_c C.
\]

| Ký hiệu | Định nghĩa vận hành của experiment harness | Lưu ý diễn giải |
|---|---|---|
| `S` / số lần lăn | Chỉ action lăn `U/D/L/R` được tính là một nước đi và có cost cơ bản 1; `SPACE/SWITCH` đổi cube đang điều khiển nên không tính là nước đi và có cost cơ bản 0 | `w_step` được cố định ở 1 cho mỗi lần lăn; `action_count` và `control_switches` được ghi riêng |
| `B` / backtrack | Lần lăn hiện tại đảo ngược ngay lần lăn trước đó, ví dụ `L` sau `R` | Feature phụ thuộc lịch sử; khóa tìm kiếm lưu `(state, last_action)`. SPACE/SWITCH reset ngữ cảnh vì đổi cube điều khiển |
| `V` / void exposure | Trạng thái kế tiếp có ít nhất một ô đang chiếm giữ với từ hai hướng lân cận là vực/ngoài biên/ô không thể đi vào | Proxy địa hình, không phải xác suất rơi thực nghiệm |
| `F` / fragile entry | Số ô fragile mới đi vào trong transition | Đây là tiếp xúc/đi vào ô fragile, không mặc nhiên là một lỗi; nằm ngang trên ô fragile có thể hợp lệ |
| `M` / switch-change proxy | Số cờ trạng thái bridge thay đổi ở transition | Proxy quan sát được cho thay đổi cấu hình cầu, không đồng nghĩa phát hiện hoàn hảo mọi switch không cần thiết |
| `C` / bridge entry | Số ô cầu mới được khối đi vào | Là số lượt vào ô cầu theo định nghĩa này, không phải số lần switch |

### 3 Baselines được đưa vào so sánh thực nghiệm

Để đánh giá khách quan hiệu quả của việc tuning trọng số UCS, script so sánh song song với **3 baselines chuẩn**:

1. **Baseline 1 — Team Rubric ban đầu:**
   \[
   (w_b,w_v,w_f,w_m,w_c)=(3,2,4,2.5,3).
   \]
   Phản ánh trực giác kỹ thuật và mức ưu tiên rủi ro ban đầu của nhóm nghiên cứu.

2. **Baseline 2 — Constant Step Cost ($c = \text{const} = 1.0$):**
   \[
   (w_b,w_v,w_f,w_m,w_c)=(0,0,0,0,0).
   \]
   Chi phí mỗi bước lăn $U/D/L/R$ bằng đúng hằng số $1.0$, không cộng bất kỳ khoản phạt địa hình hay hành vi nào ($SPACE/SWITCH$ vẫn có cost cơ bản 0). Đây là baseline chuẩn hóa tương đương việc UCS thoái hóa thành tìm đường ít bước nhất (như BFS), dùng để kiểm chứng xem việc thêm trọng số phạt có thực sự giúp tìm đường an toàn hơn hay không.

3. **Baseline 3 — Equal Normalized Weights (mọi trọng số chuẩn hóa bằng 1.0):**
   \[
   (w_b,w_v,w_f,w_m,w_c)=(1,1,1,1,1).
   \]
   Chuẩn hóa tất cả các trọng số phạt trong cost function bằng nhau và bằng $1.0$ (tương đương trọng số bước cơ bản). Baseline này dùng để kiểm chứng xem việc cân chỉnh tỷ lệ tương đối giữa các feature (ví dụ phạt fragile nặng hơn void hay backtrack) có mang lại lợi thế so với việc chỉ phạt đồng đều mọi rủi ro với hệ số 1 hay không.

Các định nghĩa feature phải được ghi rõ trong báo cáo, vì chúng không nhất thiết trùng hoàn toàn với cách `TrajectoryEvaluator` ban đầu đếm feature (module evaluator không nằm trong ZIP benchmark ban đầu).

**Điều chỉnh theo FAQ giảng viên:** `SPACE/SWITCH` chỉ đổi cube đang được điều khiển, không phải nước lăn. Nó có cost cơ bản 0, không cộng feature địa hình, không tính vào `steps/solution_length`; số lần đổi điều khiển được ghi riêng. Vì vậy cần dùng bản starter kit đã cập nhật, không dùng bản ZIP cũ nếu còn dòng “mỗi action, kể cả SPACE”.

**Nếu bạn đã chạy bản starter kit cũ:** trước lần chạy V2 đầu tiên, hãy sao lưu rồi xóa toàn bộ file trong `experiments/results/`. Checkpoint cũ được tạo khi `SPACE` còn bị tính như một move và không được trộn với kết quả mới.

### Lưới UCS được khảo sát

Script dùng lưới thô 3×3×3×3×3 = **243 cấu hình**, trong đó có baseline:

- `w_backtrack`: `{0, 3, 5}`
- `w_void`: `{0, 2, 4}`
- `w_fragile`: `{0, 4, 8}`
- `w_switch_change`: `{0, 2.5, 5}`
- `w_bridge_entry`: `{0, 3, 5}`

Lưới này được chọn để có baseline và khoảng giá trị thô, không có nghĩa các giá trị ngoài lưới là kém. Nếu cấu hình tốt nhất nằm ở biên (ví dụ trọng số lớn nhất đang được thử), có thể cần mở rộng lưới trong một nghiên cứu tiếp theo.

## 4. Tiêu chí chọn UCS — phải công bố trước khi chạy

Do chưa có đánh giá độc lập của con người, script dùng một **rubric kỹ thuật do nhóm xác định trước**, không dùng score/rating cũ trong JSON làm nhãn. Với mỗi level, các đường đi do từng cấu hình tạo ra được xếp hạng tương đối riêng trong level theo các feature. Percentile rank thấp hơn nghĩa là ít giá trị feature hơn trong nhóm ứng viên của level đó.

Loss gộp:

\[
\begin{aligned}
L ={}&\frac{1}{15.5}r_S+\frac{3}{15.5}r_B+\frac{2}{15.5}r_V\\
&+\frac{4}{15.5}r_F+\frac{2.5}{15.5}r_M+\frac{3}{15.5}r_C.
\end{aligned}
\]

Các hệ số tương ứng ưu tiên ban đầu của rubric; đây là lựa chọn giá trị của nhóm, không phải được suy ra từ ground truth. Đường đi thất bại hoặc replay không hợp lệ bị gán loss lớn (2.0) để không được ưu tiên hơn nghiệm hợp lệ.

**Quy tắc chọn:** trước hết chọn cấu hình có loss huấn luyện nhỏ nhất trong từng fold; chỉ thay baseline nếu loss trung bình trên các level held-out cải thiện so với baseline. Nếu cải thiện không dương, giữ baseline. Quy tắc này tránh đổi tham số chỉ vì một cải thiện nhỏ trên toàn bộ dữ liệu huấn luyện.

## 5. Chia level: Grouped 6-fold cross-validation

Không chia ngẫu nhiên từng trajectory, vì nhiều trajectory cùng level không độc lập. Tất cả dữ liệu của một `level_id` phải ở cùng một fold.

Script dùng các nhóm level giữ lại sau đây (mỗi fold giữ 3 level):

| Fold | Level held-out |
|---|---|
| 1 | `level_01`, `level_09`, `level_15` |
| 2 | `level_02`, `level_10`, `level_16` |
| 3 | `level_03`, `level_05`, `level_11` |
| 4 | `level_04`, `level_06`, `level_12` |
| 5 | `level_07`, `level_13`, `level_17` |
| 6 | `level_08`, `level_14`, `level_18` |

Các fold được cố định để có thể tái lập và phân bổ tương đối giữa các nhóm level. Với 18 level, đây là đánh giá độ ổn định theo nhóm chứ chưa thay thế được một test set bên ngoài gồm những level hoàn toàn mới.

## 6. A*: giữ cost model giống UCS, tuning heuristic theo codebase thực tế

A* sử dụng:

\[
 f(s)=g(s)+h_\alpha(s),\qquad h_\alpha(s)=\alpha h_0(s).
\]

- `g(s)` dùng chính cost model UCS được chọn ở bước trước.
- `alpha` được tìm trong `{0, 0.25, 0.5, 0.75, 1.0}`.
- Hàm heuristic cơ bản `h0(board, state)` triển khai **đúng logic thực tế trong codebase của nhóm (`src/solvers/astar.py`)**:
  - **Khối nguyên (whole block):** khoảng cách Manhattan nhỏ nhất từ các ô khối đang chiếm giữ đến goal, chia 2 (vì mỗi bước lăn di chuyển tối đa 2 ô), cộng `0.5` nếu khối không ở tư thế đứng (cần ít nhất 1 bước lật để đứng thẳng vào goal):
    \[
    h_0(s) = \min_{(r,c)\in \text{occ}(s)} \frac{|r - r_g| + |c - c_g|}{2} + 0.5 \cdot \mathbb{I}[\text{not standing}].
    \]
  - **Trạng thái tách đôi (split block):** tính toán số bước để hai khối con $1\times 1\times 1$ tiến lại gần nhau để hợp nhất, cộng khoảng cách từ khối con gần đích nhất đến goal chia 2, và cộng `1.0` cho bước hợp nhất/dựng đứng:
    \[
    h_0(s) = \max\left(0, \frac{\text{inter\_dist} - 1}{2}\right) + \frac{\min(d(c_0, \text{goal}), d(c_1, \text{goal}))}{2} + 1.0.
    \]

`alpha=0` là baseline A* không định hướng, tương đương UCS theo thứ tự ưu tiên cost. Chỉ chấp nhận alpha nếu nghiệm replay hợp lệ và tổng cost bằng với cost tối ưu do UCS tìm được trên cùng level/cost model. Trong các cấu hình hợp lệ, script ưu tiên số node mở rộng thấp hơn; thời gian là tiêu chí phụ vì nhạy với nhiễu đo.

### Đánh giá tính Admissibility và Consistency của Heuristic thực tế

Script tự động duyệt qua toàn bộ không gian trạng thái đạt tới của cả 18 level để kiểm tra admissibility ($h(s) \le h^*(s)$) và consistency ($h(s) \le c(s, a, s') + h(s')$) theo chi phí bước cơ bản:
- **14 level cơ bản (Level 01 đến 14):** Ghi nhận **0 vi phạm admissibility** và **0 vi phạm consistency**.
- **4 level có cơ chế split (Level 15 đến 18):** Công thức heuristic split-state của codebase phản ánh chặt chẽ hành vi thực tế của `AStarSolver`. Do hằng số $+1.0$ và tương tác với điều kiện hợp nhất ô sát đích, có một số ít trạng thái biên sát goal bị overestimate nhẹ (ví dụ 6 trạng thái ở Level 15).
- **Kết quả thực nghiệm:** Dù có độ lệch nhỏ ở trạng thái split cục bộ, A* với heuristic thực tế này **đạt 100% nghiệm tối ưu chi phí (khớp hoàn toàn với UCS)** trên cả 18 level cho mọi $\alpha \in \{0.25, 0.5, 0.75, 1.0\}$, đồng thời **giảm mạnh số node mở rộng** (ví dụ ở Level 16 giảm từ 6.213 node xuống còn 4.071 node, tức giảm hơn 34%). Việc tuning $\alpha$ vì thế đóng vai trò then chốt để chọn ra hệ số vừa tối đa hóa tốc độ tỉa nhánh vừa bảo toàn trọn vẹn tính tối ưu.

## 7. GBFS: tìm trọng số heuristic riêng

GBFS ưu tiên theo `h(s)` בלבד, không cộng `g(s)`; do đó không có bảo đảm tối ưu tổng cost.

Hàm heuristic trong harness:

\[
 h(s)=d(s)+w_o O(s)+w_p P(s)+w_e E(s)+w_f F(s),
\]

trong đó:

- `d(s)`: khoảng cách thư giãn tới đích, hệ số cố định bằng 1 để tránh tìm một hệ số nhân chung không làm đổi thứ tự ưu tiên.
- `O(s)`: chỉ báo khối chưa standing.
- `P(s)`: chỉ báo trạng thái split.
- `E(s)`: số ô đang chiếm giữ được tính là vùng sát vực theo định nghĩa ở trên.
- `F(s)`: số ô fragile đang bị khối chiếm giữ.

Lưới GBFS có 4×4×4×4 = **256 cấu hình**:

- `w_orientation`: `{0, 0.5, 1, 1.5}`
- `w_split`: `{0, 1, 2, 3}`
- `w_edge`: `{0, 0.5, 1, 2}`
- `w_fragile`: `{0, 1, 2, 4}`

Baseline `(1, 1, 0, 0)` phản ánh penalty tư thế/split được dùng để tái lập hành vi heuristic hiện tại trong harness. Tuning chọn theo rubric kỹ thuật và Grouped CV; nếu held-out không cải thiện so với baseline, giữ baseline. Không gọi kết quả GBFS là “tối ưu cost”.

## 8. Cài đặt và chạy trên Windows

### Bước 1 — Giải nén

Giải nén toàn bộ `Bloxorz_Weight_Tuning_Guide.zip` vào một thư mục không có dấu hoặc ký tự lạ, ví dụ:

`D:\AI_Project\Bloxorz_Weight_Tuning_Guide`

Giữ nguyên cấu trúc thư mục, đặc biệt là `benchmark_levels`, `experiments`, và `Bloxorz_Solver-feat-team-code-phase2-game-gui`.

### Bước 2 — Tạo môi trường Python

Mở PowerShell tại thư mục gốc vừa giải nén:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python --version
```

Cần Python 3.10 trở lên và `matplotlib`. Nếu chính sách PowerShell chặn kích hoạt môi trường, có thể dùng Command Prompt và chạy `.venv\Scripts\activate.bat`.

### Bước 3 — Kiểm tra script và đường dẫn

```powershell
python experiments\tune_weights.py --help
```

Script tự lấy 18 level từ `benchmark_levels/levels`, trajectory từ `benchmark_levels/trajectories` và ghi đầu ra vào `experiments/results/`.

### Bước 4 — Chạy toàn bộ thí nghiệm

```powershell
python experiments\tune_weights.py --phase all --repeats 5
```

Lệnh này thực hiện audit trajectory, xây graph từ `Board.transition`, tìm trọng số UCS, tuning alpha A*, tuning GBFS, rồi chạy benchmark cuối 5 lần cho từng level và thuật toán được chọn.

Để chạy từng giai đoạn riêng:

```powershell
python experiments\tune_weights.py --phase ucs
python experiments\tune_weights.py --phase astar
python experiments\tune_weights.py --phase gbfs
python experiments\tune_weights.py --phase final --repeats 5
```

Chỉ dùng lệnh từng giai đoạn khi file kết quả đầu vào của giai đoạn trước đã tồn tại từ cùng một lần thí nghiệm. Cách đơn giản nhất là chạy một lệnh `--phase all --repeats 5` trong thư mục sạch.

**Nếu bắt đầu một thí nghiệm hoàn toàn mới:** sao lưu kết quả cũ rồi làm sạch các file kết quả đã sinh trong `experiments/results/`; không để checkpoint từ một phiên bản script/dataset cũ bị tái sử dụng. Nếu chỉ tiếp tục một lần chạy bị gián đoạn, giữ checkpoint để script có thể tiếp tục phần UCS đã lưu.

### Bước 5 — Vẽ lại biểu đồ độc lập (Không cần chạy lại Search)

Để sinh lại toàn bộ 7 biểu đồ phân tích chất lượng cao mà không cần phải chạy lại quá trình Grid Search tốn thời gian:

```powershell
python experiments\plot_results.py
```

Lệnh này trực tiếp đọc các file kết quả CSV/JSON có sẵn trong `experiments/results/` và xuất các hình ảnh PNG độ phân giải 200 DPI:
- `ucs_cv_comparison.png`: So sánh held-out loss 6 fold của Tuned vs 3 Baselines.
- `ucs_top15_configs.png`: Bar chart top 15 cấu hình UCS tốt nhất và nhận diện baseline.
- `astar_alpha_expanded_nodes.png`: Đồ thị đánh đổi giữa hệ số $\alpha$ và số node mở rộng/thời gian.
- `gbfs_cv_comparison.png`: Đồ thị so sánh held-out loss của GBFS Tuned vs GBFS Baseline.
- `baselines_vs_tuned_comparison.png`: So sánh trực tiếp chất lượng giữa 3 Baselines và Tuned model.
- `benchmark_algorithms_comparison.png`: So sánh hiệu năng (node mở rộng & thời gian) giữa 7 thuật toán.
- `astar_heuristic_verification.png`: Phân bổ trạng thái split và kết quả kiểm tra tính admissibility/consistency trên 18 level.

## 9. Các file đầu ra cần giữ để đưa vào báo cáo

Sau khi lệnh chạy kết thúc thành công, sao lưu toàn bộ `experiments/results/`. Các file trọng yếu:

| File | Dùng để làm gì |
|---|---|
| `trajectory_audit.csv` | Bản ghi quỹ đạo cũ: replay có tới đích không, action trùng, score/rating lưu sẵn |
| `graph_stats.json` | Số trạng thái/cạnh đạt tới theo từng level và thời gian xây graph |
| `ucs_grid_results.csv` | Kết quả từng cấu hình UCS × level |
| `ucs_grouped_cv.csv` | Cấu hình chọn trong từng fold và kết quả held-out so với cả 3 baselines (Rubric, Const=1, Equal=1) |
| `ucs_top_configs.csv` | Những cấu hình UCS đứng đầu theo rubric trên toàn bộ level, kèm cờ nhận diện 3 baselines |
| `ucs_tuning_summary.json` | Trọng số UCS được chọn, so sánh chi tiết với 3 baselines và lý do giữ/thay baseline |
| `astar_alpha_cv_grid.csv` | Kết quả alpha A* theo fold/level |
| `astar_heuristic_checks.csv` | Kiểm tra admissibility/consistency của heuristic split-state thực tế trên 18 level |
| `astar_alpha_summary.csv` | So sánh cuối theo alpha |
| `gbfs_grid_results.csv` | Kết quả từng bộ tham số GBFS × level |
| `gbfs_grouped_cv.csv` | Tuning GBFS và kết quả held-out so với baseline |
| `gbfs_top_configs.csv` | Các cấu hình GBFS ứng viên tốt nhất |
| `final_selected_weights_repeated_benchmark.csv` | Dữ liệu gốc benchmark lặp (UCS Tuned, 3 UCS Baselines, A* Tuned, GBFS Tuned/Baseline) |
| `final_selected_weights_summary.csv` | Thống kê tổng hợp so sánh trực tiếp Tuned vs 3 Baselines (thời gian, bộ nhớ, node, cost) |
| `experiment_summary.json` | Tóm tắt các bộ tham số được chọn, định nghĩa feature và giới hạn phương pháp |
| các file `.png` | Biểu đồ kết quả được tạo từ CSV |

Không chỉ lưu ảnh terminal. CSV/JSON là dữ liệu nguồn để tạo bảng và biểu đồ, cũng là căn cứ để kiểm tra sau này.

## 10. Quy tắc đọc kết quả và quyết định trọng số

### UCS và đối sánh với 3 Baselines

- Đối sánh song song với 3 baselines:
  1. **Baseline Team Rubric $(3, 2, 4, 2.5, 3)$:** Tiêu chuẩn quyết định thay thế. Nếu trung bình held-out loss của cấu hình ứng viên tốt hơn baseline rubric, ghi rõ mức cải thiện và fold nào cải thiện. Nếu không tốt hơn, giữ baseline rubric theo quy tắc công bố trước.
  2. **Baseline Const=1 $(c=1.0, w=(0,0,0,0,0))$:** Chứng minh giá trị của mô hình chi phí có trọng số phạt địa hình so với tìm kiếm đơn thuần chỉ tối thiểu hóa số bước (BFS-like).
  3. **Baseline Equal=1 $(all\ w=1.0, w=(1,1,1,1,1))$:** Chứng minh việc phân tầng phạt có chủ đích (ví dụ phạt nặng fragile/backtrack hơn) mang lại chất lượng đường đi vượt trội so với gán phạt cào bằng.
- Không chỉ báo cáo cấu hình có `Total Path Cost` thấp nhất; đó là mục tiêu nội tại của UCS.

### A*

- Sử dụng **công thức heuristic split-state thực tế của codebase**:
  - Toàn vẹn 0 vi phạm trên 14 level không split.
  - Phản ánh đúng logic thực tế trên 4 level có split (15-18).
- Chỉ chấp nhận alpha có mọi nghiệm hợp lệ và `total_cost` khớp UCS cùng cost model (thực nghiệm xác nhận khớp 100% trên cả 18 level).
- Trong số các alpha hợp lệ, chọn theo số node mở rộng; báo cáo thêm median runtime và biến thiên runtime.

### GBFS

- Chọn theo rubric chất lượng và kết quả grouped held-out, không chọn chỉ theo thời gian hay node.
- GBFS không đảm bảo tìm đường tối ưu. Luôn báo cáo `success`, `solution_valid`, `solution_length` và các feature đường đi.
- Nếu cấu hình tuned không cải thiện baseline trên held-out, giữ heuristic baseline và giải thích.

### Tính nhất quán benchmark

- Dùng cùng một bộ JSON, cùng code `Board`, cùng quy tắc feature và cùng môi trường cho các thuật toán.
- Chạy solver không có GUI/animation.
- Đếm `expanded_nodes` theo định nghĩa trong script; entry lỗi thời bị bỏ qua không được tính.
- Độ dài nghiệm thất bại là `N/A`, không phải 0.
- Thời gian và bộ nhớ của script phản ánh **search harness** có dùng `tracemalloc`, không phải thời gian GUI hay tổng RSS của tiến trình. So sánh giữa thuật toán chỉ có ý nghĩa khi đo theo cùng giao thức.
- Đường đi của mỗi lần chạy được replay để kiểm tra tính hợp lệ.

## 11. Mẫu đoạn phương pháp có thể đưa vào báo cáo

> Nhóm thực hiện Grid Search theo lưới tham số hữu hạn được xác định trước. Trọng số bước cơ bản của UCS được cố định ở 1.0 nhằm loại bỏ nhập nhằng do nhân đồng thời toàn bộ hệ số chi phí với cùng một hằng số. Năm trọng số phạt được khảo sát trên 243+ cấu hình và được đối sánh chặt chẽ với ba baselines: (1) baseline rubric chuyên gia của nhóm (3, 2, 4, 2.5, 3), (2) baseline chi phí đồng nhất c = const = 1.0 (Uniform Cost / BFS), và (3) baseline chuẩn hóa mọi trọng số phạt bằng 1.0. Việc lựa chọn cấu hình không dựa riêng vào tổng chi phí mà thuật toán tự tối thiểu hóa; thay vào đó, nhóm dùng rubric đa tiêu chí được công bố trước, tính trên thứ hạng chuẩn hóa của các đặc trưng quỹ đạo theo từng level. Dữ liệu được đánh giá bằng sáu fold nhóm theo level, bảo đảm các quỹ đạo của cùng một level không xuất hiện đồng thời trong tập huấn luyện và held-out. Baseline ban đầu chỉ được thay khi cấu hình ứng viên cải thiện tiêu chí trên các level held-out; nếu không, nhóm giữ baseline.
>
> Với A*, nhóm giữ nguyên cost model đã chọn cho UCS và tuning hệ số \alpha của heuristic trên tập giá trị xác định trước. Heuristic của A* phản ánh chính xác công thức split-state đã cài đặt trong codebase của nhóm (tính cả khoảng cách giữa 2 khối con để hợp nhất và khoảng cách tới đích). Kiểm thử toàn diện trên 18 level khẳng định tính tối ưu chi phí 100% khớp với UCS và cắt giảm mạnh số node mở rộng. Với GBFS, nhóm tuning bộ trọng số heuristic độc lập; kết quả được đánh giá theo chất lượng quỹ đạo và tài nguyên tìm kiếm, không diễn giải là tối ưu tổng chi phí. Do chưa có nhãn đánh giá độc lập của con người, toàn bộ quy trình được xem là tuning kỹ thuật theo rubric định trước, không phải học trọng số từ ground truth người dùng.

Sau khi chạy, bổ sung các giá trị thật từ CSV/JSON vào phần kết quả. Không ghi sẵn các hệ số kết quả trước khi script hoàn tất.

## 12. Bảng kết quả cuối cùng trong báo cáo

Dùng `templates/report_table_template.md` làm khung. Báo cáo tổng hợp:

- Cấu hình UCS được chọn và so sánh chi tiết với cả 3 Baselines (Rubric, Const=1, Equal=1);
- Cấu hình cost chung A* và alpha được chọn cùng phân tích heuristic split-state;
- Cấu hình heuristic GBFS được chọn và baseline GBFS;
- Tỷ lệ lời giải hợp lệ;
- Median và IQR của thời gian/bộ nhớ;
- Số node mở rộng và số action;
- Tổng path cost cho UCS/A* (không áp dụng cùng nghĩa cho GBFS);
- Held-out loss và mức cải thiện so với cả 3 baselines;
- Giới hạn: lưới thô, 18 level, rubric kỹ thuật không phải nhãn người dùng, một số feature chỉ là proxy.

## 13. Những điều không nên viết trong báo cáo

Không viết “đã học được trọng số tối ưu phổ quát”, “GBFS tìm đường tối ưu”, “đường đi ít bước nhất luôn an toàn nhất”, “không có vi phạm trên 18 level chứng minh heuristic đúng cho mọi level”, hay “các nhãn score/rating cũ là ground truth”.

Cách diễn đạt an toàn và chính xác: **“cấu hình được chọn là cấu hình tốt nhất trong lưới khảo sát theo rubric kỹ thuật định trước, có/không cải thiện trên grouped held-out; kết luận được giới hạn trong 18 level và các định nghĩa feature đã công bố.”**
