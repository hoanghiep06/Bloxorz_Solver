# 2.3 — Geometry & Tile Specification

Trạng thái: tọa độ và block nominal là **USER APPROVED DESIGN**; kích thước chi tiết là tuning đề xuất. Advanced visual **PENDING TEAM APPROVAL / NOT IMPLEMENTED**.

## Mục lục

1. [World coordinates và thông số](#world-coordinates-và-thông-số)
2. [Floor, Void và Goal](#floor-void-và-goal)
3. [Main block và pose](#main-block-và-pose)
4. [Pivot và rolling tương lai](#pivot-và-rolling-tương-lai)
5. [Advanced visuals](#advanced-visuals)
6. [Scene graph và nghiệm thu](#scene-graph-và-nghiệm-thu)

## World coordinates và thông số

Không đổi tọa độ Core: `(r,c)` vẫn là hàng/cột nguyên. Renderer dùng X tăng theo cột, Y giảm theo hàng, Z chiều cao. Tâm hình chữ nhật toàn grid tại XY origin, kể cả grid chẵn hoặc các hàng ngoài chứa void. `s=1` world unit, floor top Z=0.

\[
X(c)=(c-(cols-1)/2)s,\quad Y(r)=((rows-1)/2-r)s.
\]

Công thức được định nghĩa cả cho tọa độ nửa ô để đặt tâm khối nằm; không làm Core dùng float. Với grid 4×7: `X(c)=c−3`, `Y(r)=1.5−r`; start `[1,1]` có tâm ô `(-2,0.5,0)`, goal `[1,6]` là `(3,0.5,0)`.

| Thông số | Mặc định đề xuất | Ý nghĩa |
|---|---|---|
| Spacing | 1.00s | Khoảng cách tâm ô |
| Tile visual width/depth | 0.96s | Giữa tile có seam |
| Tile top/bottom | 0 / −0.18s | Thành dày 0.18s |
| Tile bevel | khoảng 0.02s | Nằm trong visual bounds |
| Tile seam | khoảng 0.04s | 1.00−0.96, không phải void logic |
| Block bevel | khoảng 0.03s | Trong nominal bounds |
| Goal rim width | khoảng 0.10s | Bề rộng dải viền trong visual tile |
| Goal interior depth | 0.65s | Tuning cho hố Basic |
| Marker/decal offset | khoảng 0.002s | Tránh coplanar z-fighting; thử ở runtime |

Nominal block rộng 1s có thể nhô qua visual top 0.96s mỗi bên 0.02s. Đây là khe thẩm mỹ, không được dùng làm kiểm tra va chạm hoặc hỗ trợ sàn.

## Floor, Void và Goal

**Floor:** hộp dẹt có top, bốn sides, bevel và underside nếu góc nhìn cần. Mesh local origin tại tâm XY, top local Z=0; node tile đặt `(X(c),Y(r),0)`. Top normal +Z, side normals theo mặt; bevel có normals phù hợp. Winding thống nhất, tránh duplicate coplanar faces. Material theo [Visual Spec](VISUAL_SPEC.md).

**Void:** không tạo floor/collision support mesh. Background có thể nhìn thấy qua nhưng không nằm cùng mặt sàn. Không dùng một tile đen đặc thay void.

**Goal:** lấy vị trí từ `Board.goal_r/goal_c`, không từ việc gặp mã grid 2. Tại goal thay top floor bằng frame bốn dải, inner walls và đáy tối ở −0.65s. Outer width 0.96s, rim 0.10s cho aperture 0.76s; không đặt một top quad floor kín phía dưới frame. Nội thất không trở thành floor gameplay.

**Giới hạn clearance đã nhận diện:** aperture 0.76s nhỏ hơn nominal block 1s. Basic chỉ biểu diễn tĩnh nên chưa có chuyển động block lọt hố. Khi làm GOAL_REACHED ở chặng animation, phải duyệt thủ pháp visual (ví dụ thu nhẹ block trong hiệu ứng xuống hố hoặc sửa profile viền) để tránh xuyên viền. Chưa chọn thủ pháp là quyết định đã duyệt; không đổi occupancy/goal rule của Core. Rủi ro này không chặn Basic tĩnh nhưng chặn nghiệm thu goal-sink animation nếu chưa giải quyết.

Basic mapping 0/1/2 và tile không hỗ trợ nằm ở [Render Contract](RENDER_CONTRACT.md), không suy đoán mã Advanced từ màu.

## Main block và pose

Block một hộp nominal **1×1×2**, mesh local centered `(0,0,0)`, chiều dài ban đầu theo local +Z. Tạo đúng kích thước trong geometry; tránh scale không đều trên pose/pivot node. Bevel cắt vào trong, không tăng nominal bounding box.

| Orientation | Anchor | Occupied cells | World center | World size X/Y/Z |
|---|---|---|---|---|
| STANDING | `(r,c)` | `(r,c)` | `(X(c),Y(r),s)` | `(s,s,2s)` |
| HORIZONTAL | Ô trái `(r,c)` | `(r,c),(r,c+1)` | `(X(c+0.5),Y(r),s/2)` | `(2s,s,s)` |
| VERTICAL | Ô trên `(r,c)` | `(r,c),(r+1,c)` | `(X(c),Y(r+0.5),s/2)` | `(s,2s,s)` |

Bottom cả ba là Z=0. `VERTICAL` chỉ block nằm dọc hàng, không phải standing theo Z. Không lấy trung bình occupied centers để tính Z standing: occupied chỉ cho footprint, phải xét mode/orientation.

Canonical static rotations PROPOSED, hiểu theo right-hand world axes, không tự chuyển thành Panda HPR cùng tên: standing identity; horizontal rotate +90° quanh world Y; vertical rotate +90° quanh world X. Tâm và bounds là căn cứ đúng/sai, không phải dấu Euler nhìn có vẻ hợp lý. Coding agent dùng quaternion/axis-angle hoặc mapping được kiểm chứng từ vector local long axis.

Một mesh source cùng visual detail cho ba orientation. Static pose có thể canonicalize vì chưa có motion history. Animation sau này phải giữ visual face basis qua chuỗi roll; State logic chỉ có orientation nên không đủ biết toàn bộ lịch sử mặt. Khi reset/load tĩnh có thể chọn canonical basis, nhưng không reset detail giữa hai frame roll. Không mở rộng hash Core bằng visual quaternion.

## Pivot và rolling tương lai

Thiết kế, **không coding ở Chặng 3**:

- `BlockPose` đặt tâm/orientation, chứa mesh con; pivot tạm không có non-uniform scale.
- Cạnh xoay là cạnh dưới bbox ở phía action; ở Z=0 đối với roll trên sàn.
- Với hướng chuyển động world đơn vị d, trục quay right-hand có thể lấy `Z×d`; xoay +90° quanh trục đó. Ví dụ R→+X, U→+Y vì row giảm.
- Reparent bảo toàn world transform trước/sau interval; sau complete hiệu chỉnh tâm/bounds theo after-snapshot để bỏ sai số float, không tự sinh after-state từ mesh.
- Không lerp center thẳng rồi quay tại tâm. Các orientation khác nhau có quỹ đạo center khác nhau.
- Float tolerance đề xuất endpoint 1e−5s; visual face quaternion giữ liên tục, chỉ normalize số học/quaternion, không quay lại canonical face ở mỗi bước.

Split cubes có nominal 1×1×1, center Z=s/2. Chuyển identity của cube và nhập lại phải theo event Core, không theo node nào gần nhau.

## Advanced visuals

| Loại | Hình học/nhận diện | Dữ liệu bắt buộc trước tích hợp |
|---|---|---|
| Fragile | Tile amber, crack mảnh, cùng footprint logic | Semantic tile type và event broken; không tự đếm trọng lượng |
| Bridge | Segment riêng, có gá/khớp; tách static floor | ID, cell set, initial/open state, bool semantics |
| Soft | Circle inset/nổi, đọc được góc nghiêng | ID, cell, activation state nếu có |
| Heavy | X rõ ở mặt trên | Core xác nhận event và điều kiện kích hoạt |
| Split | Hai ngoặc đối xứng | Core target cube positions và event order |
| Split cubes | Hai node theo cube IDs ổn định | Mode, IDs, positions, active ID |
| Active cube marker | Outline/marker nhỏ không che switch | Active ID từ Core/Controller |

Không gán số 3/4/5… thành tile enum mới. Không xác định bridge mở/đóng bằng việc node đang visible. Cube nhỏ không làm fragile vỡ theo yêu cầu giảng viên; visual broken chỉ thực hiện khi nhận event tương ứng từ Core.

## Scene graph và nghiệm thu

```text
render
└── SceneRoot
    ├── StaticBoardRoot       # floor + goal, giữ qua mỗi snapshot
    ├── DynamicTileRoot       # bridge, switch, fragile biến đổi về sau
    ├── MainBlockRoot         # BlockPose -> centered mesh
    ├── SplitCubeRoot         # cube nodes theo ID, chỉ khi hỗ trợ
    └── EffectRoot            # pivot/effect tạm, cleanup rõ
pixel2d
└── HudRoot
```

`TemporaryAnimationPivot` chỉ tồn tại lúc cần, là node có transform ổn định trong cùng scene. Không cần class/node manager riêng cho từng ô. Static mesh có thể dùng instance/share geometry; không flatten bridge/switch vào floor làm mất khả năng cập nhật. Không tái sử dụng node mutable của scene cũ sau dispose.

Geometry test matrix và expected values ở [Test Plan](TEST_PLAN.md): 3 orientations × odd/even/non-square; mirror row/column; bbox/bottom; floor seam; void; goal. Lỗi thường gặp: nhầm `(r,c)` thành `(x,y)`, lệch nửa ô, mesh origin không khớp, quay sai dấu, VERTICAL theo Z, scale trên pivot, marker đổi mặt, goal bị top floor lấp.

Acceptance (chưa chạy):

- [ ] Tile centers đúng công thức ở grid chẵn/lẻ; không đổi Core coordinates.
- [ ] Ba pose đúng center/size, bottom Z=0 trong tolerance.
- [ ] Normals, bevel, seams đọc được, không z-fighting.
- [ ] Void không có floor; goal có inner wall/depth và khác void.
- [ ] Snapshot chỉ cập nhật block/dynamic nodes, không rebuild StaticBoardRoot.
- [ ] Advanced visuals không được tuyên bố đã hỗ trợ nếu thiếu contract Core.

Nguồn engine cho transforms: [Common State Changes](https://docs.panda3d.org/1.10/python/programming/scene-graph/common-state-changes). Các kích thước và công thức ở đây là thiết kế dự án; liên hệ camera tại [Layout/Camera](LAYOUT_CAMERA_SPEC.md).
