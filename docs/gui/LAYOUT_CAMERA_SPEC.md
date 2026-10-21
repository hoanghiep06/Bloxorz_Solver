# 2.2 — Screen Layout & Camera Specification

Reference layout và thông số camera: **USER APPROVED DESIGN**. Quy ước góc, thuật toán và responsive dưới đây là thiết kế cụ thể đề xuất cho implementation. **NOT IMPLEMENTED / NOT TESTED**.

## Mục lục

1. [Bốn vùng màn hình](#bốn-vùng-màn-hình)
2. [Nội dung và bố cục HUD](#nội-dung-và-bố-cục-hud)
3. [Responsive](#responsive)
4. [DisplayRegion và pixel2d](#displayregion-và-pixel2d)
5. [Camera và auto-fit](#camera-và-auto-fit)
6. [Kiểm thử và nghiệm thu](#kiểm-thử-và-nghiệm-thu)

## Bốn vùng màn hình

Đơn vị pixel theo kích thước framebuffer; UI gốc trên-trái, X phải, Y xuống. Reference **1280×720**:

| Region | X | Y | Width | Height | Cạnh phải/dưới |
|---|---:|---:|---:|---:|---|
| Header | 24 | 24 | 1232 | 56 | 1256 / 80 |
| Viewport | 24 | 92 | 934 | 530 | 958 / 622 |
| Control Panel | 974 | 92 | 282 | 530 | 1256 / 622 |
| Status Bar | 24 | 634 | 1232 | 62 | 1256 / 696 |

Outer margin 24 px; viewport-panel gap 16 px; các gap dọc 12 px. Border vẽ vào trong region, không làm vượt bounds. Không đặt HUD controls trong viewport. Full-window background nằm sau các vùng.

## Nội dung và bố cục HUD

Header: title trái, level ở giữa vùng còn lại, game status phải. Title không bị level name dài đẩy ra ngoài; elide level name khi cần, đầy đủ trong tooltip/chi tiết sau này. Trạng thái từ HUD View Model, không đọc màu mesh để suy ra thắng/thua.

Control Panel: padding ngang 16 px, content X=990..1240 tại reference, rộng 250 px. Nội dung khởi điểm:

| Nhóm/row | Y | H | Bố cục |
|---|---:|---:|---|
| Game heading | 108 | 18 | Một dòng |
| New Game / Restart | 134 | 32 | 2 cột; gap 8; mỗi nút 121 px |
| Select Level | 174 | 32 | Toàn chiều rộng |
| Solver heading | 222 | 18 | Một dòng |
| BFS / DFS | 248 | 32 | 2 cột |
| IDS / UCS | 288 | 32 | 2 cột |
| Greedy / A* | 328 | 32 | 2 cột |
| Playback heading | 376 | 18 | Một dòng |
| Play / Pause | 402 | 32 | 2 cột |
| Step / Reset Replay | 442 | 32 | 2 cột |
| Speed label | 490 | 18 | Tên và đơn vị |
| Speed slider | 520 | 18 | Visual track; hit area tối thiểu 32 px, không đè label |
| Rate value | 548 | 18 | Ví dụ placeholder `—`, không giả replay đang chạy |
| Help/status ngắn | 582 | 20 | Không quá 1 dòng ở reference |

`Reset Replay` dùng chữ 16 px để vừa cột. Chữ/nút không co vô hạn theo chiều rộng cửa sổ. Nội dung trên chỉ là thiết kế, **chưa có nút hoạt động**. Chặng 3 hiển thị shell disabled với trạng thái `Chưa tích hợp`; việc nối callbacks thuộc Tài ở chặng sau.

Status Bar: padding 16 px, năm cột bằng nhau, nhãn nhỏ trên và value dưới: Moves, Search Time, Expanded Nodes, Solution Length, Peak Python Memory. Đơn vị: moves/nodes là count, time s, memory KiB. Giá trị thiếu là `—`; 0 chỉ dùng khi có dữ liệu thật. Tên solver/status tìm kiếm nằm trong Control Panel hoặc Header theo view model, không tạo một metric thứ sáu chen lấn. Source metric và semantics ở [Contract](RENDER_CONTRACT.md).

## Responsive

PROPOSED first-pass rule cho W≥1024, H≥720: không scale toàn UI; giữ font, margin 24, panel 282, gap ngang 16, header 56, status 62. Các region:

- Header: `(24,24,W−48,56)`.
- Viewport: `(24,92,W−346,H−190)`.
- Control Panel: `(W−306,92,282,H−190)`.
- Status Bar: `(24,H−86,W−48,62)`.

| Window | Viewport | Panel height |
|---|---|---:|
| 1920×1080 | 1574×890 | 890 |
| 1366×768 | 1020×578 | 578 |
| 1280×720 | 934×530 | 530 |
| 1024×768 | 678×578 | 578 |
| 1024×720 | 678×530 | 530 |

Panel nội dung neo top, không kéo giãn chữ khi cao hơn reference. Metric cell tại W=1024 còn khoảng 188.8 px sau padding, phải đo text thực tế trước nghiệm thu. Board fit lại theo viewport, không theo toàn window.

Cửa sổ nhỏ hơn minimum: đề xuất enforce minimum window size; nếu OS vẫn cấp nhỏ hơn, hiện thông báo cần mở rộng cửa sổ và không cho controls chồng lấn. Compact/scroll mode là quyết định tương lai, không được tuyên bố đã hỗ trợ. Khi framebuffer zero/minimized, bỏ qua fit và đợi kích thước dương; không chia cho 0.

HiDPI: dùng cùng một đơn vị framebuffer pixel cho region, lens và pixel2d; nếu input trả logical pixels thì host phải quy đổi theo scale thực tế trước hit-test. Không mặc định scale factor=1 trên Windows.

## DisplayRegion và pixel2d

Một ShowBase, một cửa sổ, một event loop. Đề xuất 3D DisplayRegion riêng trong cửa sổ; GUI overlay full-window. Tắt/thu hẹp default full-window 3D region để không render scene hai lần. Sort/clear phải được host quản lý: backdrop → 3D region có depth clear → HUD, không clear color ở HUD làm mất 3D.

Với rectangle UI `(x,y,w,h)` trong framebuffer `(W,H)`:

\[
left=x/W,\quad right=(x+w)/W,\quad bottom=1-(y+h)/H,\quad top=1-y/H.
\]

Reference viewport: `(left,right,bottom,top)` ≈ `(0.01875,0.7484375,0.1361111111,0.8722222222)`. Panda API nhận thứ tự left/right/bottom/top; không truyền tọa độ top-left trực tiếp. [Display Regions](https://docs.panda3d.org/1.10/python/programming/rendering-process/display-regions).

HUD đề xuất parent dưới pixel2d: điểm UI `(x,y)` ánh xạ thành `(x,0,−y)`. Rectangle theo local X/Z có thể dùng X `[0,w]`, Z `[−h,0]`; text baseline cần tính riêng theo font metrics. `pixel2d` có origin trên-trái và Z âm đi xuống. Nếu chọn aspect2d thay thế, phải dùng một hàm quy đổi duy nhất, không trộn hệ tọa độ trong cùng layout. [GUI coordinate systems](https://docs.panda3d.org/1.10/python/programming/gui/index).

Lens của camera 3D dùng `aspect=w/h` của viewport thực tế, không dùng W/H. Host cập nhật region và lens cùng lúc sau resize; không để window resize tự ghi đè lens bằng full-window aspect mà không sửa lại.

## Camera và auto-fit

### Góc và cơ sở tọa độ

Perspective Camera, elevation `e=45°`, azimuth `a=30°`, vertical FOV `v=45°`. Định nghĩa azimuth PROPOSED: bắt đầu từ phía world −Y, quay về +X. Tâm nhắm `T=(0,0,0.4s)`; bù Z là tuning khởi điểm, không làm đổi origin board.

Gọi vector từ target ra camera:

\[
b=(\cos e\sin a,-\cos e\cos a,\sin e),\quad P=T+d\,b.
\]

Camera nhìn từ P về T, world-up Z; không đồng nhất azimuth với Panda heading số 30 nếu chưa kiểm chứng dấu/góc. `f=−b` là forward; `r=normalize(f×Z)` là right; `u=r×f` là camera up. Elevation cố định này không suy biến với Z.

### FOV

\[
h=2\arctan\bigl(aspect\tan(v/2)\bigr),\quad aspect=w/h_{viewport}.
\]

Ký hiệu `h` trong công thức là horizontal FOV, không phải chiều cao viewport. Tính lượng giác bằng radians, chỉ chuyển degrees ở API. Reference horizontal FOV ≈72.2554°.

**Bẫy API:** Panda `setFov(angle)` một tham số đặt horizontal FOV. Để giữ vertical 45°, tính horizontal theo aspect và đặt cả hai góc hoặc cấu hình lens tương đương rồi đọc lại xác minh. [Lenses and Field of View](https://docs.panda3d.org/1.10/python/programming/camera-control/perspective-lenses).

### Bounding box dùng để fit

1. Lấy union geometry board/tile/goal, gồm thickness, goal well, vị trí hợp lệ của block toàn level.
2. Basic dùng XY envelope ít nhất `[-cols*s/2,+cols*s/2] × [-rows*s/2,+rows*s/2]`; không chỉ lấy vị trí block hiện tại.
3. Z gồm tile bottom −0.18s, goal well xuống −0.65s nếu có, block cao 2s. Đề xuất envelope đến +2.30s để dự phòng arc rolling tương lai (không triển khai rolling ở Basic).
4. Không lấy background vô hạn hoặc đồ trang trí xa vào bounds. Advanced sau này phải khai báo envelope nếu teleport/bridge vượt envelope này.
5. Xét đủ tám góc AABB; board nhiều void vẫn có thể fit rộng hơn cần thiết, chấp nhận ở bản đầu.

### Khoảng cách từ hình chiếu các góc

Đề xuất safety padding **p=0.13 mỗi cạnh** (trong khoảng 12–15%); phần giữa còn `k=1−2p=0.74`. Quy ước này loại sự mơ hồ “tăng distance 13%” vốn không bảo đảm margin hình chiếu.

Với mỗi góc `qᵢ`, lấy `vᵢ=qᵢ−T`, `xᵢ=vᵢ·r`, `yᵢ=vᵢ·u`, `zᵢ=vᵢ·f`. Depth từ camera là `d+zᵢ`. Chọn:

\[
d\ge\max_i\left(\frac{|x_i|}{k\tan(h/2)}-z_i,\frac{|y_i|}{k\tan(v/2)}-z_i,0.1s-z_i\right).
\]

Giữ d dương. Sau khi đặt camera, project lại tám góc và kiểm tra NDC X/Y nằm trong `[-k,+k]`, mọi depth dương. Đây là thuật toán hình học dự án, không phải khẳng định Panda có sẵn hàm auto-fit như vậy.

Đặt near/far theo depth thực: `depth_min=min(d+zᵢ)`, `depth_max=max(d+zᵢ)`, near đề xuất `max(0.01s,0.5*depth_min)`, far `depth_max+max(2s,0.1*depth_max)`. Không dùng far cực lớn để che lỗi clipping; nếu effect đi ngoài envelope thì mở rộng bounds có chủ đích.

Re-fit khi load/change board revision hoặc resize, không theo từng roll hay snapshot. Clip plane và camera phải xét cùng bounds. Khi người chơi di chuyển, camera giữ ổn định để không gây zoom liên tục.

## Kiểm thử và nghiệm thu

Rủi ro: đảo top/bottom, dùng full-window aspect, set nhầm horizontal/vertical FOV, thiếu corner gần camera, quên chiều cao block, lấy background vào bounds, near quá nhỏ gây z-fighting, HiDPI không đồng nhất.

Chặng 3 phải chứng minh theo CAM-* và LAY-* tại [Test Plan](TEST_PLAN.md): reference đúng rectangle; mọi kích thước hỗ trợ không overlap; đủ tám corners có padding; board rộng/cao không cắt cạnh; pixel2d và DisplayRegion khớp; camera không đổi khi chỉ gọi show_snapshot; font/slider hit areas không đè nhau.

Các tiêu chí trên **NOT RUN**. Không cần Controller, solver hoặc animation để kiểm thử layout/camera Basic.
