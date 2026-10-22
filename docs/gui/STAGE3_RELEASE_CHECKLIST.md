# Stage 3 — Basic Renderer Release & Git Checklist

Ngày audit: **23/10/2026**. **BASIC HANDOFF READY FOR REVIEW**;
chưa là approval tích hợp, release toàn game hoặc lệnh commit/merge.
Entry document: [STAGE3_HANDOFF](STAGE3_HANDOFF.md).

## 1. Verification hiện tại và evidence kế thừa

| Hạng mục | Status | Evidence / phạm vi |
| --- | --- | --- |
| Imports an toàn | PASS | Full suite, guarded import tests; module import không mở window |
| Foundation | PASS | Fresh 3.7 native open/close, exit 0 |
| Board Preview | PASS | Fresh 3.7 native open/close, exit 0; source full-window giữ nguyên |
| Dashboard Preview | PASS | Fresh 3.7 native open/close, title 3D Preview |
| Core→DTO→scene/HUD example | PASS | Hai snippets [API](BASIC_RENDERER_API.md) chạy; composition native exit 0, outputs=0 |
| Real level / 3 poses / Floor/Void/Goal | PASS | Tests chạy lại; ảnh 3.6 còn tồn tại, rendering source không đổi |
| Camera/viewport/resize/light/style | PASS | Current tests; 3.6 actual five-size/shadow images và readback |
| HUD disabled / None metrics | PASS | Current real DirectGUI item/model tests |
| Disposal/foreign ownership | PASS | Current lifecycle/failure tests + native close/example cleanup |
| P0/P1 Basic đang mở | Không phát hiện | Finite scope/matrix, không exhaustive proof |
| P2/P3 integration risks | OPEN, documented | [Team findings R1–R8](TEAM_INTEGRATION_REVIEW.md#4-findings-kiến-trúc--không-tự-refactor) |
| Team approval | PENDING | Tài liệu sẵn sàng gửi, chưa có xác nhận thành viên |
| Native Windows | NOT TESTED | Checklist mục 4 |

Không rerun nặng profiling/stress/15-case capture của 3.6 trong 3.7 vì source
không đổi. Kết quả đó được ghi **inherited 3.6 evidence**, không giả thành đo mới.
Fresh smoke log `/tmp/bloxorz-stage3-7/entrypoints.json`; example verification
`/tmp/bloxorz-stage3-7/examples.json`. Evidence tạm có thể mất sau reboot.

## 2. Regression 3.7

| Interpreter | Ran | PASS | FAIL | ERROR | SKIP | Elapsed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| .venv Python/Panda | 243 | 243 | 0 | 0 | 0 | 2.195s |
| System Python, không Panda | 243 | 159 | 0 | 0 | 84 | 0.574s |

```bash
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
.venv/bin/python -B -m pip check
```

Không coi SKIP là PASS; không sửa test/source trong 3.7. Không dùng unittest
elapsed time làm FPS. Historical baseline 3.6 cũng là 243/243, không regression mới.

## 3. Runtime và setup

VERIFIED: Ubuntu 26.04.1 LTS x86_64, kernel7.0.0-38, CPython3.14.4,
Panda3D1.10.16, X11 DISPLAY=:0.0, GLX GraphicsWindow, AMD Radeon Graphics
(radeonsi/renoir/ACO), OpenGL4.6 Mesa26.0.8-1ubuntu0.3 theo 3.6 logs hiện có.
pip check hiện tại sạch. Không install/update package ở 3.7.

VERIFIED client sizes: 1280×720,1366×768,1920×1080,1024×768,1024×720;
small fallback640×480. Không suy ra mọi DPI/GPU đều hoạt động.

Setup hướng dẫn, không là lệnh đã chạy lại trong 3.7:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install panda3d==1.10.16
.venv/bin/python -m pip check
.venv/bin/python -B -m src.gui.dashboard_preview
```

Máy cần Python có venv/ensurepip phù hợp. Nếu thiếu, xem ghi nhận bootstrap
riêng của [3.1](STAGE3_1_FOUNDATION.md); không copy đường dẫn runtime Codex riêng
máy vào app. `requirements.txt` vẫn 0 byte: dependency manifest dùng chung là
**PENDING shared decision**, trước portable distribution phải chốt trong nhiệm vụ khác.

## 4. Windows native — NOT TESTED

Các lệnh sau là dự kiến để người kiểm thử chạy trên Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install panda3d==1.10.16
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
.\.venv\Scripts\python.exe -B -m src.gui.app
.\.venv\Scripts\python.exe -B -m src.gui.board_preview
.\.venv\Scripts\python.exe -B -m src.gui.dashboard_preview
```

- [ ] Ghi OS/Python/Panda/GPU/driver và actual framebuffer/client sizes.
- [ ] Kiểm font, em dash, labels và DPI100/125/150%.
- [ ] Năm window sizes, fallback, minimize/restore, normal close.
- [ ] Ba poses; wide/tall/square/sparse/goal cạnh.
- [ ] Shadow ON/OFF/capability fallback; actual AA samples.
- [ ] Repeated Dashboard lifecycle, node/widget/region/listener counts.
- [ ] Measured frame timing với cùng level/pose/window state, đọc đúng đơn vị.

Không đánh dấu các ô trên PASS từ wheel availability, Wine hoặc Ubuntu. X11
wmctrl/xprop/iconify của QA tool chỉ là helper Linux, không là application dependency.

## 5. Git inventory đầy đủ

Branch/HEAD trước và sau: `feat/phuoc/3d-renderer` /
`956c0a0528c9170afceda58551772bcadd3fc12a`. Không kiểm remote freshness.

| Nhóm | Preflight 3.7 | Sau tài liệu 3.7 |
| --- | --- | --- |
| Tracked total | 38 | 38 |
| Tracked modified | renderer.py có sẵn | renderer.py có sẵn + docs/gui/README.md thêm index |
| Untracked files | 33 | 37, gồm 4 docs mới |
| Staged files | 0 | 0 |
| Nonignored preserved/new manifest | 71 | 75 |
| Source/tests/tools/levels thay đổi trong 3.7 | 0 | 0 |

**Tracked modified:**

```text
src/gui/renderer.py             # 131 lines implementation có sẵn từ 3.3
docs/gui/README.md              # chỉ index/link/context đọc tài liệu 3.7 mới
```

**33 untracked có sẵn, giữ nguyên nội dung:**

```text
docs/gui/STAGE3_1_FOUNDATION.md
docs/gui/STAGE3_2_CONTRACTS.md
docs/gui/STAGE3_3_GEOMETRY.md
docs/gui/STAGE3_4_PRESENTATION.md
docs/gui/STAGE3_5_LAYOUT_HUD.md
docs/gui/STAGE3_6_VALIDATION.md
src/gui/app.py
src/gui/board_preview.py
src/gui/camera.py
src/gui/contracts.py
src/gui/dashboard_preview.py
src/gui/geometry_math.py
src/gui/hud.py
src/gui/layout.py
src/gui/mesh_factory.py
src/gui/render_adapter.py
src/gui/scene_lighting.py
src/gui/scene_style.py
src/gui/viewport.py
tests/test_gui_camera.py
tests/test_gui_contracts.py
tests/test_gui_foundation.py
tests/test_gui_geometry_math.py
tests/test_gui_hud.py
tests/test_gui_layout.py
tests/test_gui_lighting.py
tests/test_gui_render_adapter.py
tests/test_gui_renderer.py
tests/test_gui_stage3_6_integration.py
tests/test_gui_stage3_6_quality.py
tests/test_gui_stage3_6_stability.py
tests/test_gui_viewport.py
tools/gui_stage3_6_smoke.py
```

**4 untracked docs mới:**

```text
docs/gui/BASIC_RENDERER_API.md
docs/gui/TEAM_INTEGRATION_REVIEW.md
docs/gui/STAGE3_RELEASE_CHECKLIST.md
docs/gui/STAGE3_HANDOFF.md
```

Ignored liên quan đã quan sát: `.venv/`, `src/__pycache__/`,
`src/core/__pycache__/`, `src/solvers/__pycache__/`,
`src/solvers/UCS_Algorithm/__pycache__/`. Không đưa venv/cache/PNG/tmp vào delivery,
không xóa chúng để làm tree trông sạch. Không có `.pyc` được Git track trong audit này.
Screenshots/logs QA nằm ngoài repo dưới `/tmp`.

```bash
git status --short
git ls-files --others --exclude-standard
git diff --stat
git diff --check
git diff --cached --stat
```

git diff --stat chỉ thấy tracked changes; không thay thế inventory 37 untracked.
SHA manifest trước/sau: 71 file cũ, chỉ README đổi index; 70 file khác nguyên byte,
không mất file. Bốn docs mới được review riêng. Không stage hoặc tạo commit.

## 6. Ownership và đề xuất phạm vi PR/commit

**Đề xuất để Phước duyệt riêng**, chưa thực thi:

| Review group | Files | Owner / điều kiện |
| --- | --- | --- |
| Basic implementation | 14 GUI modules: 13 untracked source +tracked renderer | Phước, Phong/Tài review boundary |
| Tests/tool | 13 GUI test files +1 QA tool | Phước/QA, giữ existing vector-copy fix |
| Historical evidence | 6 reports 3.1–3.6 | Giữ lịch sử 3.4 PARTIAL và repair3.5, không sửa xanh giả |
| Final handoff | 4 docs3.7 +README index | Documentation review, không tự nhận team approval |

Tổng candidate delivery hiện tại **39 changed/new files**, nếu nhóm chọn đưa
toàn Basic3.1–3.7 trong cùng PR; không gồm Core/Controller/Solver/requirements.
Có thể tách commits theo feature/tests/docs nhưng phải giữ code chạy được và
không bỏ untracked dependencies. Ví dụ message docs theo quy tắc nhóm:
`docs(gui): finalize basic renderer API and team handoff`.
Không dùng `git add .` từ tài liệu này; Phước duyệt file scope, base branch,
reviewers và integration timing trước bất kỳ thao tác Git write.

## 7. Source attribution và license audit

Audit bằng source inventory, installed distribution metadata/license; không
tải thêm assets hoặc sửa lịch sử [ASSET_CREDITS](ASSET_CREDITS.md).

| Nguồn | Actual use / evidence | Status / việc khi phân phối |
| --- | --- | --- |
| Panda3D1.10.16, gồm DirectGUI | Runtime imports và installed metadata, `.venv/lib/python3.14/site-packages/panda3d-1.10.16.dist-info/LICENSE.txt` | VERIFIED Modified BSD: giữ copyright/conditions/disclaimer khi redistribute source; binary kèm notice tương ứng, không dùng tên contributors để endorse |
| Procedural Floor/Goal/Block/gradient/HUD | Project Python Geom/DirectGUI, không asset loader cho external models/textures | VERIFIED implementation; không gán license asset bên ngoài chưa dùng |
| Default font và engine-bundled runtime | TextNode/DirectGUI default font; không import font file riêng | USED THROUGH ENGINE; audit exact bundled notices/font/native dependencies nếu vendor/repackage binary: NEEDS VERIFICATION |
| Panda Chessboard/Procedural Cube/Music Box/Carousel samples | Stage2 register là REFERENCE ONLY; không thấy vendored sample file/assets trong GUI source | Không khẳng định đã copy sample. Nếu có nguồn copy ngoài bằng chứng checkout, thành viên cần bổ sung provenance trước release |
| Poly Haven/Kenney/Noto/game template ngoài | Không có assets tương ứng trong nonignored source inventory | NOT USED IN GUI DELIVERY; không credit như đã dùng, không bịa license clearance |
| License của chính repository/group contribution | Không có root LICENSE được track trong audit | NEEDS VERIFICATION bởi nhóm trước công bố/distribution; không tự chọn license ở 3.7 |

Đây là attribution inventory, không tuyên bố đã audit mọi third-party file
trong wheel hoặc cấp clearance pháp lý cho bản game đóng gói. Không thêm license
files/downloads khi chưa có quyết định và nguồn thực sự cần phân phối.

## 8. Delivery scope

**Basic Renderer completed:** static Board, Whole Block ba orientation,
Basic adapter/contracts, camera/fit, lighting/material/gradient, responsive
viewport/HUD disabled, preview entry points, tests/visual/performance evidence
và tài liệu bàn giao. Ranh giới API hiện tại xem [API reference](BASIC_RENDERER_API.md).

**NOT COMPLETED:** Advanced tiles/states, gameplay input, animated movement,
solver UI execution, replay, interactive level selection, final Windows
validation, final group integration. Dashboard là preview tĩnh, không game playable.

## 9. Gate/approval checklist bàn giao

- [x] Source truth/API inventory và architecture/lifecycle review.
- [x] Current full regression, fresh native entry points, verified examples.
- [x] Historical3.6 images/performance còn hợp lệ cho source không đổi, có giới hạn rõ.
- [x] Untracked files và source/tests integrity được bảo toàn.
- [x] Handoff cho Phong/Tài có questions/owners/blocking stages; chưa giả approval.
- [x] Links/examples và documentation scope được kiểm tra.
- [ ] Phong xác nhận schema/Advanced mappings trước Stage4 integration.
- [ ] Tài/Phước chốt facade/session/worker/action lifecycle trước Stage6.
- [ ] Goal-sink visual decision trước animation tương ứng Stage5.
- [ ] Native Windows validation và shared dependency/distribution notices.
- [ ] Phước/nhóm duyệt PR scope và thời điểm commit/merge.

Các ô pending là công việc sau bàn giao, không được biến thành PASS để tự
release. Stage3.7 documentation hoàn tất không đồng nghĩa team integration đã duyệt.
