# 2.5 — Asset Credits & Source Register

Kiểm tra nguồn ngày **22/10/2026**. Tài liệu này ghi provenance và tình trạng sử dụng, không phải bằng chứng đã nhập asset. Mọi nguồn ngoài hiện chỉ là **CANDIDATE / NOT USED IN PROJECT**; tài liệu kỹ thuật được đọc để nghiên cứu, không chép source game vào repo.

## Mục lục

1. [A — Đã sử dụng thực tế](#a--đã-sử-dụng-thực-tế)
2. [B — Các nguồn đang cân nhắc](#b--các-nguồn-đang-cân-nhắc)
3. [Quy trình đưa tài nguyên vào sau này](#quy-trình-đưa-tài-nguyên-vào-sau-này)
4. [Nguồn kỹ thuật và acceptance](#nguồn-kỹ-thuật-và-acceptance)

## A — Đã sử dụng thực tế

**No third-party assets have been imported during Stage 2.**

Không có model, texture, icon, font, âm thanh hoặc code sample được copy vào project trong Chặng 2. Không cài dependency. Geometry và background procedural là chiến lược thiết kế, chưa được tạo. Nhóm A chưa có entry asset/code runtime.

Panda3D là engine người dùng đã chọn, chưa có trong interpreter đã audit và chưa được thêm vào requirements. Việc liên kết tài liệu chính thức bên dưới không có nghĩa engine hoặc sample đã được nhúng vào sản phẩm.

## B — Các nguồn đang cân nhắc

Toàn bộ nhóm B chưa được import hoặc sử dụng làm code/assets runtime.

### B.1 — Code và engine

| ID | Nguồn/URL | Tác giả/đơn vị | Version tham chiếu | License/bằng chứng | Intended usage, cost, status |
|---|---|---|---|---|---|
| SRC-01 | [Panda3D](https://github.com/panda3d/panda3d) | Panda3D contributors; copyright CMU theo LICENSE | v1.10.16 | [LICENSE tại tag](https://github.com/panda3d/panda3d/blob/v1.10.16/LICENSE), Modified BSD/BSD-3-Clause | Engine/framework, không phải game template; chi phí vừa; CANDIDATE DEPENDENCY, NOT INSTALLED |
| SRC-02 | [Chessboard main.py](https://github.com/panda3d/panda3d/blob/v1.10.16/samples/chessboard/main.py) | Shao Zhang, Phil Saltzman; model credit Eddie Canaan | v1.10.16 | LICENSE repo SRC-01; header source có authors | Tham khảo board root, camera, đèn; chi phí thấp–vừa; REFERENCE ONLY |
| SRC-03 | [Procedural Cube main.py](https://github.com/panda3d/panda3d/blob/v1.10.16/samples/procedural-cube/main.py) | Kwasi Mensah | v1.10.16 | LICENSE repo SRC-01; header source | Tham khảo Geom/normals/UV; chi phí thấp; REFERENCE ONLY; không phải roll solver |
| SRC-04 | [Music Box main.py](https://github.com/panda3d/panda3d/blob/v1.10.16/samples/music-box/main.py) | Shao Zhang, Phil Saltzman, Elan Ruskin | v1.10.16 | LICENSE repo SRC-01; header source | Button/slider, hinge và interval; chi phí thấp–vừa; REFERENCE ONLY |
| SRC-05 | [Carousel main.py](https://github.com/panda3d/panda3d/blob/v1.10.16/samples/carousel/main.py) | Shao Zhang, Phil Saltzman, Eddie Canaan | v1.10.16 | LICENSE repo SRC-01; header source | Parent node và phối hợp intervals; chi phí thấp–vừa; REFERENCE ONLY |

BSD notice cần giữ copyright, điều kiện và disclaimer cho source; bản phân phối binary phải kèm thông báo tương ứng; không dùng tên chủ thể để bảo chứng sản phẩm. Khi thực sự lấy source, giữ header tác giả và ghi phần đã sửa. [Panda3D license chính thức](https://www.panda3d.org/license/).

**Giới hạn audit sample:** đã kiểm tra source/giấy phép gốc, chưa kiểm tra từng model, texture, audio hoặc font sample load. Không suy ra mọi tài nguyên đi kèm đều được clearance chỉ từ license source. Tái sử dụng kỹ thuật không đòi lấy nguyên assets, controls, global variables hoặc ShowBase riêng của sample.

Không lựa chọn copy nguyên game ngoài. Framework khác không thuộc engine decision; thư viện PBR/importer chưa nằm trong dependency tối thiểu của Basic.

### B.2 — Assets và font

| ID | Project/asset, URL | Author | Version/asset identity | License evidence | Dùng dự kiến/cost | Status và attribution |
|---|---|---|---|---|---|---|
| AST-01 | [Poly Haven](https://polyhaven.com/) | Poly Haven; artist cụ thể chưa chọn | Chưa chọn asset ID/version/hash | [Asset License](https://polyhaven.com/license): HDRIs/textures/models CC0 | Texture ceramic/metal sạch hoặc HDRI nhẹ nếu cần; chi phí vừa vì UV/color/size | CANDIDATE, NOT USED. CC0 không bắt buộc credit; đồ án vẫn ghi nguồn/artist. Chưa có file cụ thể để audit |
| AST-02 | [Kenney UI Pack](https://kenney.nl/assets/ui-pack) | Kenney | Trang công bố 2.0; chưa chọn file/hash | CC0 trên asset page | Icons/frame khi procedural UI chưa đủ; thấp–vừa | CANDIDATE, NOT USED. Không bắt buộc attribution theo [support](https://kenney.nl/support); đồ án vẫn ghi Kenney |
| AST-03 | [Kenney Input Prompts](https://kenney.nl/assets/input-prompts) | Kenney | Pack, chưa pin phiên bản/file | CC0 trên asset page | Hướng dẫn phím; thấp | CANDIDATE, NOT USED. Không lấy tất cả biểu tượng gamepad nếu chỉ dùng keyboard |
| AST-04 | [Noto Sans Regular](https://github.com/notofonts/noto-fonts/blob/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf) | The Noto Project Authors | Đường dẫn legacy repo đã archive; chưa pin commit/hash | [SIL OFL 1.1](https://github.com/notofonts/noto-fonts/blob/main/LICENSE) | Font sans-serif, kiểm tra dấu Việt; thấp | CANDIDATE, NOT USED. Kèm copyright/OFL khi phân phối; chú ý Reserved Font Name nếu sửa font |

Poly Haven license assets không được tự áp cho website/API code hoặc screenshot trang web. Chưa có lý do tải HDRI/texture nặng cho Basic. Noto legacy path là ứng viên xác minh được, không khẳng định đó là bản mới nhất; trước import cần chọn release/font cụ thể và đo glyph/metrics.

Textures/fonts/icons không dùng chung license với engine chỉ vì được load bởi Panda3D. Không dùng screenshot sản phẩm khác làm background. Không tự gán tác giả/version cho một asset chưa chọn.

## Quy trình đưa tài nguyên vào sau này

Chỉ thực hiện trong một nhiệm vụ cho phép import assets:

1. Chọn file thật và lưu URL nguồn, tác giả, asset ID, version/commit, ngày lấy, SHA-256.
2. Đọc license tại version đó và mọi notice riêng của file; nếu chưa rõ, không sử dụng.
3. Ghi file đích, phần sử dụng, chỉnh sửa/conversion và dependency importer nếu có.
4. Giữ license/copyright bắt buộc cùng tài nguyên và credit cho yêu cầu học thuật, kể cả CC0.
5. Chuyển entry từ candidate sang actual-used, không để cả hai bảng mâu thuẫn.
6. Giữ đường dẫn tương đối, tên file đúng case, dùng được trên Windows/Ubuntu; không nhúng đường dẫn Downloads hoặc font hệ thống.
7. Đặt budget kích thước theo nhu cầu runtime đã đo; không import nhiều độ phân giải không dùng.

Mẫu metadata tương lai: `source_url`, `source_path`, `author`, `version_or_commit`, `asset_id`, `sha256`, `license`, `license_url`, `destination`, `modifications`, `intended_usage`, `attribution`, `status`. Đây là checklist tài liệu, không tạo manifest/assets trong Chặng 2.

## Nguồn kỹ thuật và acceptance

Các tài liệu được dùng làm căn cứ kỹ thuật, không phải asset runtime:

- [SDK stable release](https://www.panda3d.org/download/), [Panda3D 1.10.16 wheels](https://pypi.org/project/Panda3D/1.10.16/).
- [ShowBase](https://docs.panda3d.org/1.10/python/introduction/tutorial/starting-panda3d), [Scene Graph](https://docs.panda3d.org/1.10/python/programming/scene-graph/index).
- [GUI/pixel2d](https://docs.panda3d.org/1.10/python/programming/gui/index), [DirectGUI](https://docs.panda3d.org/1.10/python/programming/gui/directgui/index).
- [Display Regions](https://docs.panda3d.org/1.10/python/programming/rendering-process/display-regions), [Perspective Lens](https://docs.panda3d.org/1.10/python/programming/camera-control/perspective-lenses).
- [Intervals](https://docs.panda3d.org/1.10/python/programming/intervals/index), [Tasks](https://docs.panda3d.org/1.10/python/programming/tasks-and-events/tasks).

Acceptance: đã phân biệt code/framework/assets; không có actual-used entry giả; nguồn cụ thể có URL và license evidence; asset chưa chọn có metadata pending rõ; không tuyên bố license audit toàn bộ assets. Rủi ro và owner tại [Handoff](STAGE2_HANDOFF.md). Palette/mỹ thuật không được đổi chỉ để phù hợp một asset ứng viên.
