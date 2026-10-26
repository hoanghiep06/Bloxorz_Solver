# BÁO CÁO KỸ THUẬT NHÓM 2: THIẾT KẾ MÀN CHƠI, HÀM ĐÁNH GIÁ VÀ THỰC NGHIỆM BENCHMARK
**Môn học:** Trí tuệ Nhân tạo (CSAI - AI Project 1 / LAB01)  
**Nhóm thực hiện:** Nhóm 2 -- Benchmarking, Đánh giá Quỹ đạo & Thiết kế Màn chơi  
**Thành viên:** Phạm Quang Huy (TV 4) & Nguyễn Thanh Phong (TV 5)  
**Mentor hướng dẫn:** Hoàng Hiệp (TV 3)  

---

## MỤC LỤC BÁO CÁO
1. **Phần 1: Thiết kế, Sửa lỗi và Chuẩn hóa Bộ 18 Màn chơi (Level Engineering)**
2. **Phần 2: Xây dựng và Phân tích Hàm Đánh giá Quỹ đạo (Trajectory Evaluation Function)**
3. **Phần 3: Hệ thống Tiêu chí và Chỉ số Khoa học Nâng cao (Scientific Metrics)**
4. **Phần 4: Kết quả Thực nghiệm Benchmark trên 18 Màn chơi (108 Phép thử)**
5. **Phần 5: Phân tích So sánh 6 Thuật toán và Bàn giao (Conclusion & Handover)**

---

## PHẦN 1: THIẾT KẾ, SỬA LỖI VÀ CHUẨN HÓA BỘ 18 MÀN CHƠI

### 1.1. Nguyên lý Tiến trình Cơ chế (Progression Design)
Toàn bộ 18 màn chơi được thiết kế và xây dựng theo mô hình xoắn ốc tăng dần độ phức tạp không gian trạng thái:
* **Nhóm 1: Hình học không gian cơ bản (Level 1 -- 4):** Lưới sàn thuần túy, đòi hỏi thuật toán phải tính toán tư thế Đứng/Nằm và tính chẵn lẻ (Parity) để về đích đúng tư thế đứng.
* **Nhóm 2: Ô cam dễ vỡ -- Fragile Hazard (Level 5 -- 8):** Xuất hiện ô loại 3. Khối gỗ đứng thẳng lên ô cam sẽ làm sập sàn, buộc thuật toán phải 'lăn nằm trượt qua'.
* **Nhóm 3: Cầu nhị phân và Công tắc -- Switch & Bridge (Level 9 -- 14):** Các hòn đảo ngăn cách bởi vực thểm; khối gỗ phải bấm công tắc tròn (Soft) hoặc công tắc chữ X (Heavy -- chỉ kích hoạt khi đứng) để bắc cầu trước khi về đích.
* **Nhóm 4: Phân thân và Mê cung đỉnh cao (Level 15 -- 18):** Kích hoạt công tắc phân thân, tách thành 2 nửa khối vuông $1 \times 1 \times 1$ điều khiển luân phiên qua phím SPACE, cùng các mê cung phức tạp (Level 16 có $S_{\min} = 46$ bước).

### 1.2. Khắc phục Lỗi Hình học (Geometry Bug Fixes)
Trong quá trình kiểm thử ban đầu, nhóm đã phát hiện và sửa chữa triệt để các lỗi thiết kế gây bế tắc không thể giải trên các màn:
1. **Level 10:** Cầu 101 bị đặt lệch tại hàng 3, tạo ra hố vực hở ngăn cách đảo. Đã sửa tọa độ cầu về `[[2, 4], [2, 5]]` khớp hoàn toàn với mép sàn.
2. **Level 11:** Cầu 101 bị hở 1 ô so với đảo đích. Đã di dời về `[[3, 4], [3, 5]]`.
3. **Level 14:** Ô tiếp đất sau cầu $[6, 10]$ bị gán giá trị 0 (vực), khiến khối gỗ bước qua cầu là rơi ngay. Đã chuyển thành ô sàn cứng (1).
4. **Level 15:** Vị trí phân thân bị thiết kế trùng vực. Đã chuẩn hóa start `[0, 0]` và cặp tọa độ tách `[[1, 5], [2, 5]]`.
5. **Level 16:** Cầu 101 quá ngắn (chỉ có 2 ô) không bắc qua được vực rộng 4 ô. Đã mở rộng thành 4 ô `[[2, 4], [2, 5], [2, 6], [2, 7]]`.

### 1.3. Kiểm thử Tính Khả giải (100% Solvability Verification)
Sau khi chuẩn hóa ma trận 2D trong từng file JSON, nhóm đã chạy kiểm tra toàn bộ bằng thuật toán BFS, xác nhận **18/18 màn chơi đều có lời giải hợp lệ** với $S_{\min}$ cụ thể:
* L01: 7 bước | L02: 12 bước | L03: 16 bước | L04: 17 bước | L05: 11 bước | L06: 15 bước
* L07: 17 bước | L08: 21 bước | L09: 10 bước | L10: 14 bước | L11: 24 bước | L12: 19 bước
* L13: 15 bước | L14: 19 bước | L15: 15 bước | L16: 46 bước | L17: 21 bước | L18: 22 bước

### 1.4. Bộ dữ liệu 180 Quỹ đạo mẫu (`generate_trajectories.py`)
Nhóm đã xây dựng script sinh 10 quỹ đạo đa dạng (từ tối ưu, an toàn đến đi vòng, tệ nhất) cho mỗi màn chơi, xuất thành 18 file JSON trong thư mục `trajectories/` làm cơ sở hiệu chuẩn trọng số cho hàm đánh giá.

---

## PHẦN 2: XÂY DỰNG VÀ PHÂN TÍCH HÀM ĐÁNH GIÁ QUỸ ĐẠO

### 2.1. Đặt vấn đề Kỹ thuật
Trong game Bloxorz, một con đường ít bước nhưng liên tục chạy bám sát mép vực hoặc đi lùi dao động là một con đường có rủi ro vật lý rất cao. Do đó, nhóm đã xây dựng class `TrajectoryEvaluator` dựa trên **Mô hình Chi phí tuyến tính đa tiêu chí (Multi-Criteria Linear Weighted Penalty Model)**.

### 2.2. Công thức Tính Điểm Phạt (Penalty Cost)
$$\text{Penalty} = 1.0 \times S + 3.0 \times B + 2.0 \times V + 4.0 \times M_{\text{fragile}} + 2.5 \times M_{\text{switch}} + 3.0 \times C_{\text{bridge}}$$

### 2.3. Cơ sở Kỹ thuật và Luật Vật lý của từng Trọng số:
1. **$1.0 \times S$ (Số bước cơ bản):** Chi phí chuẩn cho mỗi thao tác lật khối gỗ trên lưới ô vuông.
2. **$3.0 \times B$ (Quay đầu / Đi lùi):** Hành động tiến rồi lùi lại ngay lập tức tốn 2 bước vô ích ($2.0$) cộng thêm $1.0$ điểm phạt cho việc gây dao động trạng thái (Oscillation).
3. **$2.0 \times V$ (Sát mép vực):** Ô có $\ge 2$ hướng xung quanh là vực thẳm. Sàn Bloxorz không có lan can, nguy cơ trượt chân rơi vực cao gấp đôi so với đi giữa tâm sàn.
4. **$4.0 \times M_{\text{fragile}}$ (Lúng túng trước ô cam):** Đứng thẳng lên ô cam là thua ngay. Trên mặt phẳng lưới, chu trình ngắn nhất để đổi tư thế từ Đứng sang Nằm mà quay lại vị trí cũ bắt buộc phải chạy vòng 4 hướng (`Trái - Lên - Phải - Xuống`). Do đó, $4.0$ chính là số bước di chuyển tối thiểu bị lãng phí để sửa sai nhịp tư thế.
5. **$2.5 \times M_{\text{switch}}$ (Thao tác switch lỗi):** Bấm hụt nút chữ X hoặc bật tắt cầu thừa tốn trung bình 2 đến 3 bước vòng lại $\rightarrow \frac{2+3}{2} = 2.5$.
6. **$3.0 \times C_{\text{bridge}}$ (Chạy qua cầu lặp lại):** Cầu là điểm nghẽn; việc chạy qua chạy lại thể hiện thuật toán bị mất phương hướng.

### 2.4. Công thức Quy đổi Thang điểm 100
$$\text{Score} = \max\Big(0.0,\; 100.0 - (\text{Penalty} - \text{Penalty}_{\min}) \times 2.5\Big)$$
* $\text{Penalty}_{\min}$: Mốc điểm phạt của con đường tối ưu mẫu (làm chuẩn 100 điểm). Việc trừ $\text{Penalty}_{\min}$ giúp cấn trừ triệt để các nguy cơ bắt buộc phải qua của địa hình (như cầu hẹp 1 ô), không phạt oan thuật toán tối ưu.
* Hệ số $2.5$: Ngưỡng dôi dư $\Delta \text{Penalty} = 40.0$ tương đương thất bại hoàn toàn ($0$ điểm).

---

## PHẦN 3: HỆ THỐNG TIÊU CHÍ VÀ CHỈ SỐ KHOA HỌC NÂNG CAO

Bộ Benchmark đo lường toàn diện trên **3 Trụ cột**:

### 3.1. Trụ cột 1: Hiệu năng Hệ thống (System Metrics)
* **Execution Time ($T$, ms):** Đo bằng `time.perf_counter()` độ chính xác cao.
* **Peak Memory ($M_{\text{RAM}}$, KiB):** Đo bằng thư viện chuẩn `tracemalloc` của Python.
* **Expanded Nodes ($N$):** Bộ đếm tổng số trạng thái được lấy ra khỏi Frontier để xét duyệt.
* **Timeout:** Thiết lập ngưỡng an toàn $15.0$s mỗi thuật toán bằng `ThreadPoolExecutor`.

### 3.2. Trụ cột 2: Chất lượng Quỹ đạo (Trajectory Quality)
* Số bước ($S$), số lần lùi ($B$), số bước sát vực ($V$), điểm phạt (Penalty) và điểm quy đổi (Score).

### 3.3. Trụ cột 3: Chỉ số Khoa học Nâng cao (Advanced Metrics)
1. **Search Penetrance ($P = \frac{S}{N} \times 100\%$):** Tỷ lệ giữa độ dài lời giải trên tổng số node duyệt. Phản ánh độ chính xác của hàm dẫn đường Heuristic.
2. **Suboptimality Ratio ($\rho = \frac{S}{S_{\min}}$):** Hệ số phình to quãng đường so với nghiệm ngắn nhất. $\rho = 1.0$ là tối ưu tuyệt đối.
3. **Effective Branching Factor ($b^*$):** Hệ số rẽ nhánh hiệu dụng của cây tìm kiếm theo giáo trình AI Russell & Norvig:
   $$N + 1 = \sum_{i=0}^S (b^*)^i = \frac{(b^*)^{S+1} - 1}{b^* - 1}$$
   Nhóm giải bằng giải thuật Binary Search trên đoạn $[1.0, 4.0]$ với cơ chế bắt lỗi tràn số (Overflow-safe).

---

## PHẦN 4: KẾT QUẢ THỰC NGHIỆM BENCHMARK TRÊN 18 MÀN CHƠI

Toàn bộ 108 phép thử đã hoàn tất trong **33.92 giây**. Bảng dưới đây trích xuất giá trị trung bình của 6 thuật toán trên toàn bộ các tiêu chí:

| Thuật toán | Thời gian ($T$, ms) | RAM ($M$, KiB) | Nodes ($N$) | Số bước ($S$) | Điểm Barem (/100) | Hệ số $b^*$ | Penetrance ($P$) | Lệch tối ưu ($\rho$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A* (A-Star)** | $80.16$ | $44.74$ | $153.2$ | **$17.8$** | **$100.0$** | $1.181$ | $20.91\%$ | **$1.00$** |
| **Greedy**      | **$31.01$** | **$16.28$** | **$49.6$** | $20.8$ | $85.3$ | **$1.089$** | **$45.21\%$** | $1.17$ |
| **BFS**         | $102.24$ | $116.74$ | $348.8$ | **$17.8$** | **$100.0$** | $1.228$ | $14.87\%$ | **$1.00$** |
| **UCS**         | $137.97$ | $142.85$ | $398.5$ | **$17.8$** | $99.7$ | $1.233$ | $14.52\%$ | **$1.00$** |
| **DFS**         | $95.20$ | $97.76$ | $271.4$ | $80.6$ | $17.8$ | $1.032$ | $53.21\%$ | $4.43$ |
| **IDS**         | $1297.68$ | $127.70$ | $4278.7$ | **$17.8$** | **$100.0$** | $1.471$ | $1.61\%$ | **$1.00$** |

---

## PHẦN 5: PHÂN TÍCH SO SÁNH VÀ BÀN GIAO CHO NHÓM

### 5.1. Nhận xét và Đánh giá Chuyên sâu
1. **$A^*$ là thuật toán xuất sắc toàn diện nhất:** Vừa đảm bảo tối ưu tuyệt đối quãng đường ($S=17.8, \rho=1.00, \text{Score}=100.0$), vừa tiết kiệm gần gấp 3 lần bộ nhớ RAM ($44.74$ KiB so với $116.74$ KiB của BFS) và cắt giảm hơn một nửa số node duyệt ($153.2$ so với $348.8$).
2. **Greedy là thuật toán nhanh nhất và nhẹ nhất:** Thời gian nhanh gấp 3 lần $A^*$ ($31.01$ ms), RAM vỏnvẹn $16.28$ KiB và chỉ duyệt $49.6$ node. Tuy nhiên, bản chất tham lam khiến nó bị phình đường ở các màn có bẫy hẻm cụt ($\rho = 1.17$, điểm $85.3$ -- xếp loại Tốt).
3. **BFS và UCS là chuẩn mực tối ưu không thông tin:** Cả hai đều đạt nghiệm tối ưu tuyệt đối ($17.8$ bước, 100 điểm). UCS với trọng số an toàn phân bổ node dày hơn ở các vùng an toàn nên số node ($398.5$) và thời gian ($137.97$ ms) cao hơn BFS một chút.
4. **DFS thể hiện sự yếu kém rõ rệt trên không gian có chu trình:** Đi lạc sâu vào mê cung khiến số bước phình to gấp $4.43$ lần (trung bình $80.6$ bước, riêng Level 17 lên tới 612 bước), điểm Barem rất thấp ($17.8$ điểm -- Rất kém).
5. **IDS bảo toàn tính tối ưu nhưng trả giá thời gian:** Tìm ra đường tối ưu $17.8$ bước giống BFS nhưng do phải duyệt lặp lại nhiều tầng nên tổng số node lên tới $4278.7$ nodes và tốn trung bình $1297.68$ ms (chậm nhất).

### 5.2. Kết quả Bàn giao (Deliverables)
* **Mã nguồn:** `benchmark.py` (Script chạy thực nghiệm tự động) và `src/evaluation/evaluator.py` (Class chấm điểm).
* **Dữ liệu thực nghiệm:** `benchmark_results.csv` (108 dòng chi tiết) và `benchmark_summary.csv` (6 dòng trung bình).
* **Bàn giao cho Phong (TV 5):** Sử dụng 2 file CSV trên để viết script `plot_charts.py` vẽ 4 biểu đồ: Thời gian, RAM, Số node và Điểm chất lượng đưa vào báo cáo chính thức.
