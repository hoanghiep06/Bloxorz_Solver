# Stable mechanics fixtures

Các JSON ở đây giữ nguyên nội dung từ commit `2f19245`, trước khi catalog màn chơi được thay bằng `level_01.json` … `level_18.json` ở `f602351`.

Mục đích: test bridge, fragile, split, mouse, replay có dữ liệu và đường đi cố định; không phụ thuộc việc nhóm thay số/tên màn chơi sản phẩm. Đây là **fixture kiểm thử**, không thêm lại các màn này vào `levels/`.

`test_move_assist` vẫn duyệt cả fixtures và catalog hiện hành. Native QA catalog hiện hành được chạy riêng bằng `tools.jungle_solver_smoke`; QA đường đi/cơ chế cố định dùng `--levels tests/fixtures/mechanics`.
