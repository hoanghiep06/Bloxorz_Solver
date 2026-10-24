# Chặng 3.1 — Environment & Application Foundation

Ngày kiểm thử: **22/10/2026**, Asia/Ho_Chi_Minh.

**STAGE 3.1 FOUNDATION COMPLETE.** Kết luận chỉ cho application foundation trên Ubuntu đang có; **Windows NOT TESTED**. Chưa hoàn thành Board Renderer, Basic Renderer toàn bộ hoặc game playable.

## Mục lục

1. [Preflight và phạm vi](#preflight-và-phạm-vi)
2. [Kiến trúc foundation](#kiến-trúc-foundation)
3. [Môi trường thực tế](#môi-trường-thực-tế)
4. [Virtual environment và dependency](#virtual-environment-và-dependency)
5. [Chạy demo](#chạy-demo)
6. [Kết quả kiểm thử](#kết-quả-kiểm-thử)
7. [Minh chứng cửa sổ thật](#minh-chứng-cửa-sổ-thật)
8. [Lỗi đã gặp và xử lý](#lỗi-đã-gặp-và-xử-lý)
9. [Giới hạn và hướng mở rộng](#giới-hạn-và-hướng-mở-rộng)
10. [Phối hợp với Tài](#phối-hợp-với-tài)
11. [Acceptance và Git](#acceptance-và-git)

## Preflight và phạm vi

| Hạng mục trước triển khai | Kết quả |
|---|---|
| Branch | `feat/phuoc/3d-renderer` |
| HEAD | `956c0a0528c9170afceda58551772bcadd3fc12a` |
| Working tree/staging | Sạch, không có thay đổi của thành viên khác cần bảo toàn trong file mục tiêu |
| GUI source | `renderer.py`, `controller.py`, `__init__.py` rỗng; chưa có `app.py` |
| CLI | Root `main.py` chạy các phần BFS/DFS/IDS/Greedy/UCS, giữ nguyên |
| Dependency | `requirements.txt` rỗng; Python hệ thống chưa có Panda3D |
| Design Package | Đã đọc/đối chiếu [README](README.md), [Visual](VISUAL_SPEC.md), [Geometry](GEOMETRY_TILE_SPEC.md), [Contract](RENDER_CONTRACT.md), [Handoff](STAGE2_HANDOFF.md); là thiết kế Chặng 2, không phải bằng chứng GUI đã chạy |

Khác snapshot Chặng 1: hiện ở nhánh cá nhân và HEAD đã có commit tài liệu Chặng 2. Không fetch, pull, chuyển hoặc tạo nhánh. Không thấy code refactor mới của Phong hoặc Controller của Tài trong checkout; không kết luận về công việc ngoài checkout.

Chặng 3.1 mới là phần đầu của Chặng 3. Phạm vi prompt mới hẹp hơn toàn Basic Renderer trong handoff: chỉ host, window, roots và lifecycle. Prompt mới dùng tên **BlockRoot/EffectsRoot**, thay cho MainBlockRoot/EffectRoot trong sơ đồ thiết kế tổng thể. Foundation dùng đúng tên mới; các nhánh con main/split/effects có thể được thống nhất khi mở rộng, chưa tạo chúng ở đây. Không sửa tài liệu Chặng 2 lịch sử để tuyên bố toàn bộ Basic đã hoàn thành.

## Kiến trúc foundation

Các file mới:

| File | Trách nhiệm |
|---|---|
| [src/gui/app.py](../../src/gui/app.py) | `BloxorzPreviewApp(ShowBase)`, cấu hình trước tạo window, roots, cleanup và `main()` |
| [tests/test_gui_foundation.py](../../tests/test_gui_foundation.py) | Import safety bằng subprocess và cleanup khi main loop raise; không mở window khi chạy unittest |
| Tài liệu này | Setup, lệnh chạy, evidence, trạng thái nghiệm thu và scope tiếp theo |

```text
ShowBase (một instance)
└── render
    └── SceneRoot
        ├── StaticBoardRoot
        ├── DynamicTileRoot
        ├── BlockRoot
        └── EffectsRoot
```

Bốn roots rỗng, không chứa GeomNode/mesh/gameplay data. Public host attributes tương ứng: `scene_root`, `static_board_root`, `dynamic_tile_root`, `block_root`, `effects_root`. Chúng phục vụ lắp ghép Renderer sau này; Controller không dùng chúng để sửa mesh riêng của Renderer.

Module chỉ định nghĩa constants, class và entry point. PRC configuration được đặt trong constructor **trước** `ShowBase.__init__()`, không chạy lúc import. `super().__init__(windowType="onscreen")` yêu cầu window thật, không đổi sang offscreen khi lỗi display. Default camera được giữ, mouse camera-control bị tắt; chưa triển khai FOV, camera fit hoặc controls mới.

`main()` tạo đúng một host rồi gọi đúng một `run()`. Khối `finally` gọi `destroy()` kể cả SystemExit do đóng cửa sổ hoặc lỗi vòng lặp. Override destroy tháo SceneRoot riêng trước khi gọi cleanup của ShowBase. Không thêm thread, timer, task game loop, input binding, GUI framework hoặc worker.

Audio backend đặt `null` trong foundation vì chưa có âm thanh; đây là cấu hình của preview, không phải quyết định audio cho game cuối. Engine vẫn tạo các tác vụ nội bộ mặc định; host không thêm tác vụ riêng.

## Môi trường thực tế

| Hạng mục | Giá trị đã kiểm chứng |
|---|---|
| OS | Ubuntu 26.04.1 LTS, x86_64 |
| Desktop/display | XFCE, X11, `DISPLAY=:0.0` |
| Python hệ thống | CPython 3.14.4, `/usr/bin/python3` |
| Python được chọn cho GUI | `/home/sv/Code/Bloxorz_Solver/.venv/bin/python`, CPython 3.14.4 |
| Panda3D | Package và runtime 1.10.16; import PASS trong venv |
| Wheel đã cài | `panda3d-1.10.16-cp314-cp314-manylinux2014_x86_64.whl` |
| Window thực tế | `glxGraphicsWindow`, không phải offscreen buffer |
| Driver vendor/renderer | AMD / AMD Radeon Graphics, radeonsi, renoir, ACO |
| OpenGL | 4.6 Compatibility Profile, Mesa 26.0.8-1ubuntu0.3 |
| Dependency check | `pip check`: No broken requirements found |
| Windows | NOT TESTED; không suy ra PASS từ việc có wheel Windows |

Không thay interpreter/package hệ thống. `.venv/` đã được `.gitignore` bao phủ trước khi tạo; không sửa `.gitignore` hoặc shared requirements. Pip/Panda3D nằm trong venv local, không được Git track.

## Virtual environment và dependency

Chạy từ root repository. Lệnh thông thường trên Linux khi Python có ensurepip:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'panda3d==1.10.16'
.venv/bin/python -m pip check
```

**Trên máy kiểm thử, lệnh venv thông thường đã thất bại vì thiếu ensurepip.** Không cài apt package hoặc pip vào Python hệ thống. Quy trình thực tế đã dùng:

```bash
python3 -m venv --without-pip .venv
/home/sv/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pip --python .venv/bin/python install pip
.venv/bin/python -m pip install 'panda3d==1.10.16'
.venv/bin/python -m pip check
```

Pip của runtime Codex chỉ dùng để bootstrap vào **target venv** qua `--python`; không sửa runtime đó. Pip trong venv sau bootstrap là 26.2.2. Đường dẫn runtime Codex là fallback đã xác minh riêng trên máy này, không hardcode vào app và không yêu cầu mọi máy có cùng đường dẫn. Máy khác nên dùng Python có ensurepip hoặc một installer tin cậy đã có để cấp pip cho venv được chọn.

Không dùng `.resolve()` lên `.venv/bin/python` để thay đường dẫn launcher trong lệnh chạy: trên Ubuntu đây là symlink tới Python hệ thống; chạy trực tiếp đường dẫn đã resolve có thể bỏ qua venv và không tìm thấy Panda3D.

Windows dự kiến, **chưa thực thi**:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install panda3d==1.10.16
.\.venv\Scripts\python.exe -B -m src.gui.app
```

Không chạy các lệnh tạo lại venv đè một môi trường đang được thành viên khác sử dụng. Trong lượt này đã xác minh `.venv` chưa tồn tại trước khi tạo.

## Chạy demo

Lệnh đã xác minh trên repository thật:

```bash
.venv/bin/python -B -m src.gui.app
```

Không cần activate venv nếu gọi interpreter như trên. Có thể activate rồi chạy `python -m src.gui.app`; không dùng root `main.py` để mở preview. Cần chạy từ root repository để module `src` resolve được; chưa triển khai packaging/launcher từ working directory bất kỳ.

Kỳ vọng của **3.1** là cửa sổ nền sáng rỗng. Không có sàn, block, HUD, chữ trong scene hoặc animation. Title: **Bloxorz Solver — Renderer Foundation**. Client area mặc định **1280×720**; khung viền/title bar do desktop thêm nên screenshot toàn cửa sổ có thể lớn hơn. Tắt bằng nút X; không phải nhấn Ctrl+C hoặc kill process.

Resize dùng tính năng engine/window manager; chưa có responsive layout. Không fullscreen, menu, splash hoặc camera interaction. Window title/size/fixed-size được đặt trước khi engine tạo window. Clear color RGBA là `(241/255,244/255,247/255,1)`, tức BG_MAIN `#F1F4F7`.

## Kết quả kiểm thử

| ID | Cách kiểm tra thực tế | Kết quả | Phạm vi bằng chứng |
|---|---|---|---|
| T1 | Import module trong subprocess, không có ShowBase global instance, GraphicsEngine có 0 windows; default WindowProperties không đổi; không import Core/solver/Pygame | PASS | Import không mở window/chạy loop; timeout test 15 s |
| T2 | Live app: `builtins.base` và ShowBaseGlobal.base cùng là app; `winList` và GraphicsEngine có 1 output | PASS | Một host/window trong demo |
| T3 | X11 thật, đọc WindowProperties và xwininfo; capture framebuffer/native window; resize qua WM | PASS | Title đúng; client 1280×720; resized 1024×720; nền RGB đúng; close exit 0 |
| T4 | Inspect live SceneRoot/children/parents/GeomNode count | PASS | SceneRoot dưới render; 4 roots đúng tên, mỗi root 0 children; không GeomNode trong subtree |
| T5 | Chạy đúng `.venv/bin/python -B -m src.gui.app`; chạy root CLI với venv và Python hệ thống | PASS | Module launch thành công; CLI exit 0, đủ các phần baseline |
| T6 trước | `python3 -B -m unittest discover -s tests` trước sửa source | PASS | 83 tests cũ |
| T6 sau, venv | `.venv/bin/python -B -m unittest discover -s tests` | PASS | 85 tests: 83 cũ + 2 foundation |
| T6 sau, system | `python3 -B -m unittest discover -s tests` | PASS | 85 discovered, 83 chạy thành công, 2 GUI tests skip vì Panda3D không cài ở system |
| T7 Ubuntu | Import + live GLX desktop smoke | PASS | Chỉ môi trường Ubuntu/driver nêu trên |
| T7 Windows | Chưa có Windows runtime để chạy | NOT TESTED | Không công bố cross-platform PASS |
| T8 | Xác nhận IsViewable, focus đúng window của PID demo rồi capture; đã quan sát ảnh thật | PASS | Native screenshot 1284×758 gồm frame; client 1280×720, không phải headless test |
| Cleanup | Đóng qua WM route tương đương nút X; sau destroy window count=0, SceneRoot detached, global base không còn | PASS | Không có task do host tự tạo; validation task tạm của harness đã kết thúc |

Hai test foundation tự động không mở GUI khi unittest discovery chạy. Test cleanup dùng lỗi loop giả có chủ đích để kiểm tra `finally`; không gọi test đó là bằng chứng window thật. Live smoke được chạy riêng, có một task capture/inspection tạm trong harness kiểm thử; task này **không có trong source application**.

CLI đã chạy thành công với cả `.venv/bin/python -B main.py` và `python3 -B main.py`. Không sửa hoặc mở rộng thuật toán; không coi CLI baseline pass là bằng chứng A* hay Advanced đã được kiểm thử đầy đủ. Không gặp regression mới.

## Minh chứng cửa sổ thật

- Native desktop screenshot: `/tmp/bloxorz-stage3-1-desktop.png` — có title bar và nền sáng, kích thước toàn ảnh 1284×758.
- Readback từ **onscreen GraphicsWindow**: `/tmp/bloxorz-stage3-1-frame.png` — client 1280×720; toàn bộ RGB được kiểm tra bằng số và đúng `(241,244,247)`.
- Live window inspector xác nhận type GLX, open, resizable, title và parent hierarchy. Screenshot native chỉ lấy khi active window đúng PID/ID demo, tránh nhầm ứng dụng khác.

Các ảnh là evidence tạm ngoài Git, không phải asset ứng dụng; có thể mất khi dọn `/tmp`. Không thêm ảnh/assets vào repo. Quan sát bằng ảnh cho thấy foundation rỗng đúng scope; chưa có board/block để review mỹ thuật hoặc camera.

## Lỗi đã gặp và xử lý

1. **Thiếu ensurepip:** `python3 -m venv .venv` thất bại. Tạo lại bằng `--without-pip` và dùng pip có sẵn để bootstrap venv như phần setup. Không dùng sudo/apt và không sửa Python hệ thống.
2. **Ảnh desktop ban đầu đen/không đúng cửa sổ:** capture lúc client unmapped hoặc focus đã đổi không dùng làm evidence. Harness cuối tìm đúng window theo PID, đợi IsViewable/focus rồi chụp trong một lượt kiểm thử. Ảnh cuối đúng nền và title; không cần sửa renderer để chữa lỗi capture này.
3. **Window ID cũ không còn:** có lần truy vấn ID sau khi window đã đóng trả BadWindow. Harness cuối gắn ID theo từng process và chờ exit, không tái dùng ID từ phiên trước. Lệnh module đóng sạch exit 0.

Không gặp graphics/display error lúc tạo GLX window. Thông báo stderr `Known pipe types: glxGraphicsPipe (1 aux display modules not yet loaded.)` là thông tin engine, không phải lỗi tạo cửa sổ. Nếu máy khác không có DISPLAY/driver phù hợp, ghi BLOCKED/NOT TESTED cho desktop; không đổi sang offscreen rồi báo window PASS.

## Giới hạn và hướng mở rộng

Chưa có Board Renderer, meshes Floor/Void/Goal, main block, materials, lighting, HUD, DTO/RenderAdapter, manual input, solver invocation, replay, animation, worker hoặc game session. Camera chỉ dùng mặc định và tắt mouse-control. Không sửa Core/Controller/solvers/levels/tests cũ hoặc shared requirements.

Các phần tiếp theo chỉ là chuẩn bị bàn giao, **chưa thực hiện**:

- **3.2:** nhiệm vụ sau có thể xây pure render data/adapter và validation theo contract Basic nếu đúng phân chia được người dùng giao; không tự áp schema Advanced.
- **3.3:** board/block geometry khi được giao, dùng các roots hiện có và tọa độ thiết kế.
- **3.4:** camera perspective/auto-fit, viewport aspect và resize theo Layout Spec, chưa có ở foundation.
- **3.5:** HUD visual shell/layout; Tài sẽ nối hành vi sau. Không tạo thêm ShowBase.

Tên/phạm vi chi tiết 3.2/3.3 phải theo prompt chặng sau nếu người dùng phân chia khác; tài liệu này không tự cấp quyền làm chúng. Không triển khai 3.2–3.7 trong lượt 3.1.

## Phối hợp với Tài

- Tài sử dụng cùng host, không tạo ShowBase thứ hai hoặc tự gọi một loop phụ.
- Host engine do Phước quản lý; xác nhận người chịu trách nhiệm wiring Controller và thứ tự shutdown trước tích hợp.
- Controller không thao tác private meshes; Renderer sau này nhận scene roots từ host, giữ API hiển thị riêng.
- Game session/solver worker/replay/cancellation thuộc Tài và vẫn pending; foundation chưa đưa ra implementation thay thế.
- Khi thêm tasks/events sau này, từng thành phần phải cleanup tài nguyên của mình trước host destroy. Cách drain animation callbacks chưa áp dụng ở 3.1 vì chưa có animation.
- Audio hiện null; nếu game sau có sound phải thống nhất init audio trước ShowBase, không dùng một host phụ.

## Acceptance và Git

| Điều kiện Chặng 3.1 | Trạng thái |
|---|---|
| Preflight branch/HEAD/working tree và source | PASS |
| Panda3D được xác minh trong môi trường ảo đã chọn | PASS |
| Demo độc lập, đúng một ShowBase và một main loop | PASS |
| Window client 1280×720, title đúng, resizable | PASS |
| Background #F1F4F7 | PASS |
| Scene roots cơ bản tồn tại và rỗng | PASS |
| Import không mở window hoặc chạy game | PASS |
| Đóng window/cleanup sạch | PASS |
| Có hướng dẫn chạy và evidence runtime Ubuntu | PASS |
| Các tests thực hiện được đã chạy | PASS |
| Không sửa Core/Controller/solver, không dùng Pygame | PASS |
| Không commit/push/merge/chuyển nhánh | PASS |
| Không triển khai 3.2–3.7 | PASS |
| Windows runtime | NOT TESTED |

Git sau triển khai giữ branch/HEAD nêu đầu file. Chỉ có ba file mới: `src/gui/app.py`, `tests/test_gui_foundation.py`, tài liệu này; chưa stage/commit. `.venv/` là thay đổi local đã ignore, không đưa vào commit. Các file tracked trước lượt triển khai giữ nguyên nội dung; diff/manifest được kiểm tra trước bàn giao.

Điều kiện bắt đầu 3.2: người dùng review foundation và giao phạm vi tiếp theo; audit lại source/ownership nếu Phong/Tài cập nhật; giữ interpreter venv đã kiểm chứng. Không cần chờ Advanced hoàn chỉnh để dùng host rỗng, nhưng không được tự đoán API refactor.

Nguồn kỹ thuật: [ShowBase lifecycle](https://docs.panda3d.org/1.10/python/introduction/tutorial/starting-panda3d), [ShowBase source v1.10.16](https://github.com/panda3d/panda3d/blob/v1.10.16/direct/src/showbase/ShowBase.py), [Panda3D 1.10.16 distribution](https://pypi.org/project/Panda3D/1.10.16/). Không chép sample gameplay hoặc assets ngoài.
