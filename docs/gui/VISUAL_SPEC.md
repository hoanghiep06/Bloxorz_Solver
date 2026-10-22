# 2.1 — Visual Specification

Trạng thái: **USER APPROVED DESIGN** cho direction/palette; các tuning bổ sung là đề xuất. **NOT IMPLEMENTED / NOT TESTED**.

## Mục lục

1. [Mục tiêu và nhận diện](#mục-tiêu-và-nhận-diện)
2. [Palette](#palette)
3. [Materials và tile identity](#materials-và-tile-identity)
4. [Lighting và background](#lighting-và-background)
5. [HUD và chữ](#hud-và-chữ)
6. [Animation art direction](#animation-art-direction)
7. [Assets, chất lượng và nghiệm thu](#assets-chất-lượng-và-nghiệm-thu)

## Mục tiêu và nhận diện

**Modern Light Minimal 3D**: sáng, hiện đại, ít chi tiết thừa, đường nét rõ, có khối tích và chiều sâu. Gameplay đọc được ngay ở góc camera nghiêng. Chất lượng cần đủ trình chiếu video, gồm background, vật liệu và hướng animation; scene tĩnh Chặng 3 chưa chứng minh yêu cầu auto-solve toàn game.

Board lơ lửng trong **Clean Floating Architectural Space**. Không dùng phong cách tối, kim loại gỉ, đá cổ, dung nham hoặc ánh neon làm chủ đạo. Không đưa logo/chữ lên block. Accent phục vụ nhận biết trạng thái, không biến scene thành bảng đèn.

## Palette

Bảng này là nguồn chuẩn; giữ nguyên HEX. HEX mô tả màu sRGB mục tiêu, không bảo đảm pixel sau lighting giống hệt. Nếu renderer dùng linear lighting, phải chuyển đổi đúng color space; UI/background unlit tránh bị đổi tone ngoài ý muốn.

| Token | HEX | Vai trò |
|---|---|---|
| BG_MAIN | #F1F4F7 | Nền chính |
| BG_SECONDARY | #E7EFF5 | Gradient phụ, hover panel |
| FLOOR_TOP | #DCE5ED | Mặt sàn |
| FLOOR_SIDE | #A8BBCD | Thành sàn |
| FLOOR_EDGE | #91A8BB | Bevel, đường ghép |
| BLOCK_MAIN | #527B9C | Mặt chính block |
| BLOCK_DARK | #354F68 | Mặt tối, pressed |
| BLOCK_HIGHLIGHT | #91ADC3 | Bevel và chi tiết nhận biết lăn |
| TEXT_PRIMARY | #273B50 | Chữ chính |
| TEXT_SECONDARY | #61778B | Chữ phụ |
| GOAL_INTERIOR | #273B50 | Lòng hố |
| GOAL_RIM | #527B9C | Viền goal |
| FRAGILE | #D6A15F | Tile dễ vỡ |
| SUCCESS | #4E8A72 | Kết quả thành công |
| DANGER | #BE6D65 | Mất hỗ trợ/lỗi theo dữ liệu cung cấp |
| HUD_SURFACE | #FFFFFF | Panel, nhãn primary button |
| HUD_BORDER | #D1DEE8 | Viền HUD |
| BUTTON_PRIMARY | #527B9C | Nút chính |

Không thêm màu accent nếu chưa ghi vai trò và được review. Có thể tạo biến thể bằng roughness, normal, độ sáng/alpha có kiểm soát; không thay HEX gốc trong tài liệu khác.

## Materials và tile identity

| Thành phần | Material/shape | Dấu hiệu ngoài màu | Stage |
|---|---|---|---|
| Floor | Ceramic/composite mờ; top sáng, side tối, bevel nhỏ | Đường ghép và thành dày | Basic |
| Void | Không có floor mesh | Nhìn xuyên xuống không gian nền | Basic |
| Main block | Steel blue/brushed titanium, phản xạ tiết chế | Tỷ lệ 1×1×2 và một chi tiết bất đối xứng nhỏ | Basic |
| Goal | Viền thép xanh, lòng navy, inner wall có độ sâu | Hố có thành, khác void mở hoàn toàn | Basic |
| Fragile | Amber nhạt, mờ | Vân nứt mảnh, không thành vân đá cổ | Advanced visual, chờ Core |
| Bridge | Composite/kim loại gọn | Khớp/cạnh phân đoạn; mở/đóng đọc được | Advanced |
| Soft switch | Đĩa tròn | Vòng tròn nổi hoặc inset | Advanced |
| Heavy switch | Cùng family material | Dấu X, không chỉ khác màu | Advanced |
| Split switch | Đế gọn | Hai ngoặc đối xứng | Advanced |
| Split cubes | Hai cube cùng family block | Marker/outline active cube theo ID | Advanced |

Floor dùng material chung theo loại mặt; không tạo một material độc lập cho từng ô. Bevel phải góp ánh sáng thật, không chỉ vẽ viền đen. Normals/winding đúng để không phải bật two-sided toàn scene nhằm che lỗi mesh.

Block cần đậm hơn floor, highlight không phủ toàn mặt. Đề xuất brushed look bằng material trước; texture vân kim loại chỉ thêm khi cần. Một đường inset lệch tâm hoặc mảng nhỏ trên một mặt giúp nhìn được chuyển động về sau. Chi tiết có local coordinates ổn định; khi xoay tư thế không được đột ngột đổi mặt. Quy tắc pose tại [Geometry](GEOMETRY_TILE_SPEC.md).

Fragile nứt bằng geometry/line decal nông, dùng FLOOR_SIDE hoặc BLOCK_DARK có alpha phù hợp; tránh z-fighting. Cube nhỏ an toàn trên fragile theo giải đáp giảng viên, nhưng renderer chỉ phản ánh event Core, không quyết định luật.

Bridge đóng không trông như floor đi được: đề xuất phần sàn rút xuống/mất khỏi mặt phẳng Z=0, chỉ giữ gá nhỏ để nhận diện. Chưa triển khai chuyển động này hoặc suy đoán flag nào nghĩa là mở. Switch pressed phải nhận dữ liệu, không dùng việc mesh bị block chạm làm trigger gameplay.

## Lighting và background

Thiết kế ánh sáng:

- Ambient trung tính, đủ nhìn mặt khuất nhưng không làm phẳng hình.
- Directional key từ phía trên-trái của màn hình; xác định bằng camera basis để không nhầm world left.
- Fill nhẹ phía đối diện nếu cần. Bản Basic có thể bắt đầu bằng ambient + key.
- Contact shadow dưới block; shadow mapping là quality option, không phải dependency bắt buộc.
- Shadow phải được receiver sàn/bridge hợp lệ nhận; không vẽ một miếng tối trôi nổi trên void hoặc lấp goal.

Tuning khởi điểm PROPOSED: ambient RGB tuyến tính trung tính cỡ 0.25; key 0.75; fill tối đa 0.15. Đây là trọng số để thử, không phải giá trị pixel hoặc kết quả runtime. Không tích hợp PBR/IBL phức tạp chỉ để đạt bản đầu.

Gradient BG_MAIN → BG_SECONDARY là full-window backdrop không nhận đèn. Board có thành sàn và vùng trống phía dưới; không đặt ground plane sát tile làm void trông có sàn. Vật trang trí không nằm trước board; pattern nền phải nhẹ, không tạo cảm giác một level khác phía sau. Camera bounds bỏ qua backdrop vô hạn.

Nếu bật shadow mapping: kiểm tra driver, bias, shadow bounds và khả năng fallback. Không hứa chất lượng bóng trên mọi GPU. Tắt shadow mapping vẫn giữ chiều sâu bằng side shading, bevel và contact shadow được giới hạn đúng.

Nguồn kỹ thuật: [Lighting](https://docs.panda3d.org/1.10/python/programming/render-attributes/lighting), [Materials](https://docs.panda3d.org/1.10/python/programming/render-attributes/materials). Tỷ lệ đèn và mỹ thuật trên là thiết kế dự án, chưa được runtime xác minh.

## HUD và chữ

Panel trắng, border 1 px HUD_BORDER, corner radius đề xuất 8 px; padding 16 px; layout theo [Layout](LAYOUT_CAMERA_SPEC.md). Nút có normal/hover/pressed/disabled/focus rõ bằng nền, viền và trạng thái, không chỉ đổi màu chữ.

| Loại | Kích thước đề xuất tại reference | Cách dùng |
|---|---|---|
| Title | 24 px, semibold | Header |
| Heading nhóm | 16 px, semibold | Control Panel |
| Body/value | 16 px | Nội dung và metrics |
| Nhãn phụ | 14 px tối thiểu | Trên HUD_SURFACE |
| Primary button | 20 px, bold | Chữ trắng trên BUTTON_PRIMARY |
| Secondary button | 16 px, semibold | TEXT_PRIMARY trên trắng |

Phân tích tĩnh màu sRGB, chưa là visual test: TEXT_PRIMARY/trắng ≈11.49:1; TEXT_SECONDARY/trắng ≈4.65:1; TEXT_SECONDARY/BG_MAIN ≈4.21:1; trắng/BUTTON_PRIMARY ≈4.495:1. Không làm tròn 4.495 thành đạt ngưỡng 4.5 cho chữ nhỏ. Vì giữ palette đã chốt, dùng primary label 20 px bold, và ưu tiên TEXT_PRIMARY cho chữ nhỏ trên nền chính. Đây không phải tuyên bố toàn UI đã đạt chuẩn accessibility.

Hover primary có thể dùng BLOCK_DARK, pressed thêm offset visual 1 px không đổi hitbox. Focus viền BLOCK_DARK 2 px có khoảng cách; disabled có nhãn/trạng thái và không nhận command, không chỉ giảm alpha toàn widget đến khó đọc. Font sans-serif có dấu tiếng Việt; Noto Sans là ứng viên, chưa import. Không phụ thuộc font đường dẫn hệ thống Windows.

Moves/metrics chưa có hiển thị `—`, không dùng 0 để giả là đã đo. Trong Chặng 3, các nút gameplay/solver/replay chỉ là shell disabled; chỉ widget visual-state inspection được dùng để kiểm thử, không gọi Controller/solver.

## Animation art direction

**Thiết kế tương lai, NOT IMPLEMENTED**. Roll mang trọng lượng gọn, không bật nảy quá mức hoặc squash làm sai hình. PROPOSED nominal roll 0.30 s tại rate 1; easing nhẹ, không overshoot endpoint. Các hiệu ứng switch/bridge dùng cùng nhịp, goal khác fall qua tín hiệu kết quả chứ không chỉ màu.

Renderer chỉ thực hiện một action request và events đã xác nhận; toàn replay do Tài. Không dùng thời gian thực để quyết định trạng thái game. Pause đứng hình cả block và hiệu ứng thuộc request; background trang trí có thể độc lập nhưng không gây khó nhận biết pause. Hoàn tất phải khớp after-snapshot, kể cả hiệu ứng bị giảm chất lượng. Xem [Contract](RENDER_CONTRACT.md).

## Assets, chất lượng và nghiệm thu

Ưu tiên geometry/material/background procedural, Panda3D built-ins. Không tải texture/font/icon trong Chặng 2. Nguồn và điều kiện tại [Asset Credits](ASSET_CREDITS.md); liệt kê không đồng nghĩa đã sử dụng.

Chất lượng/performance: cache mesh/material, tách static/dynamic roots, không tạo lại toàn board mỗi snapshot; tránh lights/transparent layers thừa. Shadows, chi tiết crack và texture là quality options. Chưa có FPS/VRAM benchmark, không cam kết một con số hiệu năng không có bằng chứng.

Acceptance thiết kế, còn NOT RUN ở runtime:

- [ ] Scene sáng đúng palette, không có tone tối thay thế.
- [ ] Block đọc rõ ba mặt, floor có thickness và bevel.
- [ ] Goal nhận ra là hố ngay cả khi không dựa vào màu; void không có floor.
- [ ] HUD đọc được ở các kích thước được hỗ trợ, có đủ trạng thái widget.
- [ ] Background có chiều sâu và không che board; hiệu ứng không làm lẫn đường đi.
- [ ] Không đổi Core state để đạt hiệu ứng visual.

USER APPROVED DESIGN: direction, palette, material family, background concept. PROPOSED/PENDING TEAM APPROVAL: tuning đèn, font asset cụ thể, chi tiết block, thời lượng/easing và visual của events nâng cao. Không chặn Basic tĩnh nếu dùng mặc định này; phải review khi tích hợp. Test IDs tại [Test Plan](TEST_PLAN.md).
