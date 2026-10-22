# 📋 BẢN QUY ƯỚC KỸ THUẬT CHUNG — GIAI ĐOẠN 2 (BLOXORZ SOLVER)



## I. QUY ƯỚC MÃ Ô TRÊN MA TRẬN BẢN ĐỒ (`grid`)

Mọi file cấu hình bản đồ trong thư mục `levels/` sử dụng các mã số nguyên sau trong ma trận `grid`:

| Mã ô | Tên loại ô | Mô tả trạng thái | Pygame (Tài) hiển thị | Core Engine (Phước) xử lý |
| :---: | :--- | :--- | :--- | :--- |
| **`0`** | **Void** | Vực thẳm bên ngoài | Khoảng trống đen / Không gian | Khối chạm vào là **rơi (Thua/Invalid)** |
| **`1`** | **Normal Floor** | Sàn đá/gỗ kiên cố | Ô vuông xám sáng chuẩn | Đứng hay Nằm đều **hợp lệ (An toàn)** |
| **`2`** | **Goal** | Lỗ đích đến | Ô vuông phát sáng màu đỏ | Chỉ thắng khi khối ở tư thế **STANDING** |
| **`3`** | **Fragile Tile** | Ô cam dễ vỡ | Ô màu cam có vân nứt | **Chỉ an toàn khi NẰM**. Nếu **ĐỨNG** $\rightarrow$ Sập sàn rơi vực |
| **`4`** | **Soft Switch** | Công tắc tròn | Vòng tròn nổi trên sàn | NẰM hay ĐỨNG đè lên đều **kích hoạt** |
| **`5`** | **Heavy Switch** | Công tắc chữ X | Dấu chữ **X** dập nổi | Bắt buộc phải **ĐỨNG** thẳng mới **kích hoạt** |
| **`6`** | **Split Switch** | Công tắc phân tách | Biểu tượng hai khối nhỏ | Đè lên sẽ tách khối làm đôi |
| **`7`** | **Bridge Tile** | Ô cầu nối đóng/mở | Cầu gỗ/thanh rào | Trạng thái do công tắc điều khiển (Hiện/Ẩn) |

---

## II. ĐẶC TẢ CẤU TRÚC FILE JSON CỦA MÀN CHƠI (LEVEL SCHEMA)

Mọi file JSON từ `level_01.json` đến `level_16.json` tuân theo chuẩn tổng quát sau:

```json
{
  "grid": [
    [1, 1, 1, 0, 0, 0, 1, 1, 1],
    [1, 1, 3, 3, 0, 0, 1, 1, 1],
    [1, 1, 1, 4, 0, 0, 1, 1, 1]
  ],
  "start": [0, 1],
  "goal": [2, 8],

  "switches": [
    {
      "id": 1,
      "r": 2,
      "c": 3,
      "type": "soft",
      "action": "toggle",
      "targets": [101]
    },
    {
      "id": 2,
      "r": 0,
      "c": 2,
      "type": "heavy",
      "action": "open",
      "targets": [102]
    }
  ],

  "bridges": [
    {
      "id": 101,
      "cells": [[1, 4], [1, 5]],
      "initial_state": false
    },
    {
      "id": 102,
      "cells": [[2, 4], [2, 5]],
      "initial_state": true
    }
  ],

  "split_switch": {
    "r": 1,
    "c": 8,
    "split_positions": [
      [0, 1],
      [2, 8]
    ]
  }
}
```

### Quy tắc đọc file (Safe Parsing) cho Core Engine & Solvers:
Khi đọc file JSON, luôn sử dụng `.get()` để tránh lỗi `KeyError` đối với các map cơ bản (Level 1–8) không có công tắc:
```python
switches = data.get("switches", [])
bridges = data.get("bridges", [])
split_switch = data.get("split_switch", None)
```

---

## III. NGUYÊN TẮC VẬN HÀNH CÔNG TẮC & CẦU NỐI (SWITCH & BRIDGE MECHANICS)

### 1. Phân loại Công tắc (`type`):
* `"soft"` (Công tắc tròn): Khối chạm bất kỳ phần nào lên ô `[r, c]` (cả Đứng, Nằm ngang, Nằm dọc) $\rightarrow$ Kích hoạt.
* `"heavy"` (Công tắc chữ X): **Chỉ khi** khối ở tư thế `Orientation.STANDING` tại đúng toạ độ `[r, c]` $\rightarrow$ Mới kích hoạt. Nếu nằm đè qua $\rightarrow$ Bỏ qua (không kích hoạt).

### 2. Các kiểu hành động của công tắc (`action`):
* `"toggle"`: Đảo trạng thái hiện tại của tất cả cây cầu trong danh sách `targets` (Mở $\leftrightarrow$ Đóng). Dẫm lần 1 mở cầu, dẫm lần 2 đóng cầu.
* `"open"`: Chỉ dùng để mở cầu (nếu cầu đã mở thì giữ nguyên mở).
* `"close"`: Chỉ dùng để đóng/thu hồi cầu.

### 3. Vận hành Cầu nối (`bridges`):
* `"cells"`: Danh sách toạ độ `[[r, c], ...]` các ô sàn cấu tạo nên cây cầu đó.
* `"initial_state"`:
  * `false`: Ban đầu cầu đang **ĐÓNG** (các ô trong `cells` hoạt động như vực thẳm `0`).
  * `true`: Ban đầu cầu đang **MỞ** (các ô trong `cells` hoạt động như sàn đi được `1` hoặc `7`).

---

## IV. QUY ƯỚC HÀNH ĐỘNG (`actions`) & CƠ CHẾ PHÂN TÁCH KHỐI (SPLIT BLOCK)

### 1. Bảng ký tự hành động:
* `'U'`: Roll Up (Hàng giảm $r - 1$ hoặc $r - 2$)
* `'D'`: Roll Down (Hàng tăng $r + 1$ hoặc $r + 2$)
* `'L'`: Roll Left (Cột giảm $c - 1$ hoặc $c - 2$)
* `'R'`: Roll Right (Cột tăng $c + 1$ hoặc $c + 2$)
* `'SPACE'`: Đổi quyền điều khiển giữa Khối 1 và Khối 2 khi đang bị phân tách.

### 2. Luật chơi khi phân tách khối:
* Khối $1 \times 1 \times 2$ dẫm lên ô Split switch $\rightarrow$ Tách đôi thành 2 khối lập phương con kích thước $1 \times 1 \times 1$ rơi tại 2 vị trí khai báo trong `split_positions`.
* **Đặc tính khối con:**
  * Do trọng lượng nhẹ bằng một nửa, khối con **đi qua ô cam `3` an toàn mà không làm sập sàn**.
  * Khối con **không đủ nặng** để kích hoạt Heavy Switch (chữ X).
* **Hợp nhất khối:** Khi 2 khối con di chuyển đến 2 ô kề sát nhau $\rightarrow$ Tự động hợp nhất trở lại thành khối lớn $1 \times 1 \times 2$.

---

