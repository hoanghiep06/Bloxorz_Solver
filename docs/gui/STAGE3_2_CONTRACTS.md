# Chặng 3.2 — Basic Render Contracts & Core-to-render Adapter

Ngày thực hiện: **22/10/2026**. Trạng thái: **STAGE 3.2 CONTRACTS & ADAPTER COMPLETE**.

Phạm vi hoàn tất: DTO Python thuần, adapter cho Core Basic hiện tại, structural validation,
fingerprint, unit tests và regression. Basic Renderer chưa hoàn thành; Board/Block 3D,
camera, HUD, animation và tích hợp Controller thuộc các nhiệm vụ sau.

## 1. Repository preflight

- Branch: `feat/phuoc/3d-renderer`.
- HEAD: `956c0a0528c9170afceda58551772bcadd3fc12a` —
  `docs(gui): define stage 2 3D renderer design and contracts`.
- Tracked diff và staged diff rỗng lúc bắt đầu.
- Ba file untracked có sẵn từ 3.1 được bảo toàn:
  `src/gui/app.py`, `tests/test_gui_foundation.py`, `docs/gui/STAGE3_1_FOUNDATION.md`.
- Chưa có `contracts.py`/`render_adapter.py`; GUI package initializer,
  Controller và Renderer vẫn rỗng. Repository dùng `unittest`.
- Đã đọc foundation report, host, Board/State, level thật, tests Core,
  Render Contract, Geometry Spec và Stage 2 Handoff trước khi triển khai.
- Đã ghi SHA-256 của toàn bộ 41 file tracked/untracked không bị ignore có sẵn để đối chiếu.
  Không fetch/pull hoặc suy đoán tiến độ remote của thành viên khác.

Baseline đo lại trước khi sửa:

| Runtime | Ran | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|---:|
| `.venv/bin/python -B -m unittest discover -s tests` | 85 | 85 | 0 | 0 | 0 |
| `python3 -B -m unittest discover -s tests` | 85 | 83 | 0 | 0 | 2 |

Hai skip của Python hệ thống là foundation tests cần Panda3D.
Không mở lại cửa sổ 3.1 trong nhiệm vụ này; kết quả smoke GUI cũ là bằng chứng lịch sử,
không phải một lần kiểm thử visual mới. Windows chưa kiểm thử.

## 2. Core API thực tế đã kiểm chứng

Nguồn: [Board](../../src/core/board.py), [State](../../src/core/state.py),
[level_01](../../levels/level_01.json), [Board tests](../../tests/test_board.py),
[State tests](../../tests/test_state.py).

| API/dữ liệu | Hiện trạng trong checkout | Adapter sử dụng |
|---|---|---|
| `Board.grid` | Mutable list các list, mã nguyên; constructor reject bool | Copy thành tuple, chỉ nhận Basic 0/1/2 |
| `Board.rows/cols` | Kích thước rectangular grid | Kiểm tra số nguyên dương, shape khớp |
| `Board.goal_r/goal_c` | Một goal chính thức | Xuất đúng một cell, không dò tất cả mã 2 |
| `Board.start_r/start_c` | Tọa độ ban đầu | Không thuộc static fingerprint được giao |
| `get_initial_state()` | Whole block STANDING, bridge flags rỗng | Caller có thể lấy state này để preview |
| `Orientation` | Enum STANDING=0, HORIZONTAL=1, VERTICAL=2 | Map bằng member Enum thật |
| `BloxorzState.r/c` | Anchor nguyên; Core cho phép biểu diễn số âm | Snapshot Basic yêu cầu cell không âm và trong board |
| `get_occupied_cells()` | List cell, 1 hoặc 2 theo orientation | Gọi API rồi copy/canonicalize, kiểm tra consistency |
| `bridges_state` | Tuple bool tham gia state identity | Chỉ tuple rỗng được hỗ trợ; không đánh mất flags |
| `transition/is_goal/is_valid_state/is_valid_cell` | Core sở hữu gameplay | Không gọi |

Core hiện coi mọi mã grid khác 0 là có sàn, kể cả 3; chưa có schema semantic tile,
bridge definitions/IDs, split cubes, active cube hoặc ordered events trong Board/State.
Việc Basic adapter từ chối mã ngoài 0/1/2 là giới hạn khả năng chuyển đổi của GUI,
không kết luận level sai luật và không đổi hành vi Core.

## 3. Đối chiếu Chặng 2 và foundation 3.1

Các DTO/API trong [RENDER_CONTRACT](RENDER_CONTRACT.md) và
[STAGE2_HANDOFF](STAGE2_HANDOFF.md) mang nhãn **PROPOSED / PENDING TEAM APPROVAL**.
Chặng 3.2 triển khai duy nhất profile tối thiểu theo yêu cầu mới; không tạo bộ DTO song song.

| Chủ đề | Đề xuất Stage 2 | Quyết định thực thi Stage 3.2 |
|---|---|---|
| Tile payload | Sequence entries với cell/kind/raw diagnostic | Matrix tuple Enum đúng rows×cols |
| Goal | Kind GOAL và goal coordinates | Tile chỉ VOID/FLOOR; goal riêng trong `goal_cells` |
| Session | Integer tăng theo session | Chuỗi không rỗng do caller cung cấp; không tự cấp/tăng |
| Board fingerprint | Canonical semantic tiles/definitions/capabilities | Level ID, dimensions, **raw grid**, goal theo yêu cầu mới |
| Snapshot mở rộng | Bridge maps, cubes, game_status… | Chỉ 8 fields Basic được mô tả bên dưới |
| BlockMode | Đề xuất token WHOLE/SPLIT, chưa có class Python | Dùng `"WHOLE"`; không thêm Enum cạnh tranh |
| Validation errors | Đề xuất category/custom protocol | `TypeError`/`ValueError` với field path |
| Foundation | Một host và các scene roots | Không sửa app, roots, entry point hoặc foundation tests |

Boundary đã duyệt vẫn giữ: Core quyết định luật; Controller sở hữu session/current state;
adapter chuyển dữ liệu; Renderer vẽ. Tọa độ logical và nominal geometry của Stage 2 giữ nguyên.
Không sửa các tài liệu Stage 2 để biến đề xuất tích hợp thành đã được cả nhóm duyệt.

## 4. Kiến trúc và files

```text
Caller: Board + State + level_id/session_id/state_revision
    -> render_adapter.py (đọc Core, copy, structural validation)
    -> contracts.py (StaticBoardData, GameSnapshot bất biến)
    -> Renderer tương lai (chưa được nối trong 3.2)
```

Files mới duy nhất:

- [contracts.py](../../src/gui/contracts.py): Enums, frozen/slotted dataclasses và validation.
- [render_adapter.py](../../src/gui/render_adapter.py): Hai public factory functions.
- [test_gui_contracts.py](../../tests/test_gui_contracts.py): 13 tests.
- [test_gui_render_adapter.py](../../tests/test_gui_render_adapter.py): 24 tests.
- Tài liệu này.

Contracts không import Core. Adapter import đúng Board/State, không import app,
Controller, Renderer, solvers, Panda3D hoặc Pygame. Không có IO trong hai public functions;
việc đọc file level là trách nhiệm caller/Core Board constructor.

## 5. StaticBoardData

| Field | Kiểu và ý nghĩa |
|---|---|
| `schema_version` | int đúng 1, không nhận bool |
| `level_id` | str không rỗng/không chỉ whitespace, giữ nguyên giá trị caller |
| `board_revision` | str không rỗng; adapter xuất SHA-256 hex 64 ký tự |
| `rows`, `cols` | int > 0, không nhận bool |
| `tiles` | `tuple[tuple[BasicTileKind, ...], ...]`, shape chính xác |
| `goal_cells` | Tuple các `(row, col)` nguyên không âm, không trùng, trong board |

`BasicTileKind.VOID.value == "VOID"`, `BasicTileKind.FLOOR.value == "FLOOR"`.
Adapter hiện xuất một goal theo Core. DTO chỉ kiểm tra cấu trúc tập vị trí: không áp đặt
luật số goal hoặc tile support; chấp nhận tuple rỗng/nhiều goal structurally, không chứng minh
Core/renderer đã hỗ trợ level như vậy. Direct constructor cho phép revision fixture không phải
SHA-256 để test dữ liệu độc lập; không tự chứng thực hash của một DTO do caller tự dựng.

## 6. GameSnapshot

| Field | Kiểu và ý nghĩa |
|---|---|
| `schema_version` | int đúng 1 |
| `session_id` | str không rỗng do caller cung cấp |
| `state_revision` | int >= 0 do caller cung cấp, không nhận bool |
| `board_revision` | Lấy nguyên từ StaticBoardData được truyền vào adapter |
| `block_mode` | Chuỗi đúng `"WHOLE"` |
| `orientation` | Member BasicOrientation, không nhận string/raw int |
| `anchor_cell` | Tuple `(row, col)` nguyên không âm |
| `occupied_cells` | Tuple các cell khớp footprint, không trùng; canonical row/col order |

GameSnapshot không giữ State, Board, dimensions hay grid. Direct constructor kiểm tra
footprint; adapter bổ sung kiểm tra bounds với `board_data`. Snapshot không chứa game status,
world coordinates, cube giả hoặc switch/bridge state giả.

## 7. Tile và orientation mapping

| Core | Render output |
|---|---|
| Raw 0 | VOID |
| Raw 1 hoặc 2 | FLOOR, kể cả mã 2 ngoài goal |
| `(goal_r, goal_c)` | `goal_cells=((goal_r, goal_c),)` |
| Raw khác 0/1/2 | ValueError unsupported Basic tile với vị trí grid |
| Không phải mã int, kể cả bool | TypeError với vị trí grid |
| STANDING tại `(r,c)` | BasicOrientation.STANDING, `((r,c),)` |
| HORIZONTAL tại `(r,c)` | BasicOrientation.HORIZONTAL, `((r,c),(r,c+1))` |
| VERTICAL tại `(r,c)` | BasicOrientation.VERTICAL, `((r,c),(r+1,c))` |

Footprint lấy từ `get_occupied_cells()`, không tính bằng transition. Validation đối chiếu
hình dạng footprint với anchor/orientation; đây không phải bảng luật di chuyển.
List/tuple/set/frozenset occupied cells được copy, validate từng cell rồi sort.
Không dùng set để khử trùng trước validation. Orientation lạ không được đổi thành STANDING.

## 8. Public APIs và ví dụ Input → Output

```python
from src.core.board import Board
from src.gui.render_adapter import build_board_data, build_game_snapshot

board = Board("levels/level_01.json")
board_data = build_board_data(board, level_id="level_01")
snapshot = build_game_snapshot(
    board.get_initial_state(),
    board_data=board_data,
    session_id="preview-1",
    state_revision=0,
)
```

Kết quả đã chạy với level thật:

```text
board_data.schema_version = 1
board_data.level_id = "level_01"
board_data.rows, board_data.cols = 4, 7
board_data.goal_cells = ((1, 6),)
board_data.tiles[0][3] = BasicTileKind.VOID
board_data.tiles[1][6] = BasicTileKind.FLOOR
board_data.board_revision =
  e7a5bdc0ae641d022883067d99a1b4a041fae2ae8b714c6594009db0a12019dd

snapshot.session_id = "preview-1"
snapshot.state_revision = 0
snapshot.board_revision = board_data.board_revision
snapshot.block_mode = "WHOLE"
snapshot.orientation = BasicOrientation.STANDING
snapshot.anchor_cell = (1, 1)
snapshot.occupied_cells = ((1, 1),)
```

Đã thử thêm State HORIZONTAL và VERTICAL tại `(1,1)`:
occupied cells tương ứng `((1,1),(1,2))` và `((1,1),(2,1))`.
Không đổi sang tọa độ Panda3D. Tạo `board_data` một lần khi load/thay đổi nội dung board;
reuse khi tạo các snapshots tiếp theo. Không gọi `build_board_data` trong mỗi frame.

## 9. Validation và error handling

- Constructor DTO yêu cầu **tuple chính xác** ở mọi container; list/dict không được giữ lại
  hoặc âm thầm chuẩn hóa. Adapter chịu trách nhiệm copy dữ liệu mutable thành tuple.
- Số nguyên dùng kiểm tra exact int để loại bool; string identity phải có nội dung.
- Kiểm tra schema, dimensions, shape, tile Enum, goal bounds, footprint, logical bounds,
  orientation, WHOLE, session/revision. Error message nêu field như `board.grid[0][1]`.
- Adapter chỉ nhận đúng class Board/BloxorzState đã audit, không nhận subclass/schema lạ;
  fail rõ thay vì coi representation mở rộng là Basic. Nonempty bridge flags, kể cả
  `(False,)`, bị từ chối vì chưa có definitions/ID mapping.
- Không kiểm tra ô dưới khối có FLOOR hay VOID; test khối trên VOID vẫn được chuyển đổi
  khi hợp lệ về cấu trúc. Không gọi `is_goal`, `is_valid_state`, `is_valid_cell`, `is_standing`
  hoặc `transition`; không tính luật Fragile/Bridge/Switch/Split/Goal.
- Không catch-all hoặc trả dữ liệu mặc định khi gặp lỗi.

State Core không có board ID: adapter gắn đúng revision của `board_data` và kiểm tra bounds,
nhưng không thể chứng minh provenance một State thuộc level nào. Caller phải ghép State với
đúng board authoritative. Không thử dùng collision/goal rules để đoán nguồn State.
Kiểm tra stale session, revision tăng và board loaded mismatch thuộc consumer/controller
tương lai; constructor không có lịch sử để tự thực hiện.

## 10. Deterministic board revision và chi phí

Payload chính xác, không gồm state/session/revision động:

```python
{
    "level_id": level_id,
    "rows": board.rows,
    "cols": board.cols,
    "grid": copied_raw_rows,
    "goal_cells": ((board.goal_r, board.goal_c),),
}
```

Serialization: `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`.
Encode UTF-8 rồi `hashlib.sha256(...).hexdigest()`. Tuple serialize thành JSON arrays.
Không built-in hash, mtime, object address, UUID hoặc thứ tự set/dict không ổn định.

Cùng input cho cùng revision giữa các objects/processes và `PYTHONHASHSEED=1/991`.
Đổi raw 1 thành 2 ngoài goal vẫn đổi revision dù tiles visuals giống nhau.
Đổi goal, level ID hoặc dimensions/content cũng đổi fingerprint.
Start không nằm trong payload được yêu cầu: chỉ đổi start không đổi static board revision;
caller cần cấp session/state revision phù hợp khi khởi tạo state mới.

Static conversion và bộ nhớ tạm O(rows×cols), bỏ qua độ dài string ID/raw encoding.
Snapshot chỉ đọc tối đa hai occupied cells và board revision/dimensions, O(1) theo kích thước
board; không đọc tiles, clone board, hash, serialize hoặc cache. Không có thread/async/network.

## 11. Immutability

DTO dùng `@dataclass(frozen=True, slots=True)`; nested containers là tuples,
leaf data là Enum/int/str. Không giữ mutable Core references. Tests xác minh:
gán fields/ghi nested cell bị lỗi; sửa/xóa rows của grid gốc hoặc sửa goal sau conversion
không đổi DTO; sửa nested occupied list do API trả về cũng không đổi snapshot.
Board và State giữ nguyên sau cả đường thành công và validation failure;
State hash và membership trong visited set được bảo toàn.
Đây là bất biến qua API Python thông thường, không phải sandbox chống cố ý bypass bằng reflection.

## 12. Unit tests và regression thực tế

Hai test files mới có **37 tests**: 13 contracts + 24 adapter. T01–T26 có test method riêng
với tiền tố `test_tNN_`; 11 tests bổ sung phủ validation, canonicalization, bounds,
snapshot performance boundary, context và canonical fingerprint fixture.

| IDs | Coverage |
|---|---|
| T01–T05 | Board hợp lệ, dimensions, shape, goal bounds, nested immutability |
| T06–T08 | Snapshot identity/revision, orientation, session/revision sai |
| T09–T12 | Level thật, VOID/FLOOR, goal authoritative |
| T13–T15 | Ba orientation/footprints |
| T16–T18 | Không mutate Board/State, detach nested mutable data |
| T19–T21 | Stable process/hashseed fingerprint, đổi raw code/goal |
| T22 | Tile/state schema/bridge flags chưa hỗ trợ |
| T23–T24 | Không cần site packages; guard chặn imports engine/host/controller/solvers |
| T25–T26 | Logical coords trên board không vuông; không gọi transition/game rules |

Lệnh đã chạy:

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_gui_*contracts.py' -v
.venv/bin/python -B -m unittest discover -s tests -p test_gui_render_adapter.py -v
.venv/bin/python -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

| Sau triển khai | Ran | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|---:|
| Contracts mới trong .venv | 13 | 13 | 0 | 0 | 0 |
| Adapter mới trong .venv | 24 | 24 | 0 | 0 | 0 |
| Full regression trong .venv | 122 | 122 | 0 | 0 | 0 |
| Full regression Python hệ thống | 122 | 120 | 0 | 0 | 2 |

T23 tạo subprocess `sys.executable -S -B`: không load site-packages, import contracts trước
và xác nhận Core chưa bị import, sau đó import adapter và convert level thật thành DTO.
T24 dùng import hook chặn `panda3d`, `direct`, `pygame`, app/controller/renderer/solvers.
Không thể khởi tạo ShowBase qua các dependency này trong probe. T19 chạy hai subprocess
khác hash seed. T26 patch gameplay APIs để lập tức raise nếu bị gọi.
Temporary level fixtures dùng TemporaryDirectory và cleanup ngay khi Board đã load.
Không mở window, tạo graphics resources hoặc chạy GUI main loop trong các tests này.

## 13. Giới hạn và xác nhận tích hợp

**Phong cần xác nhận trước Advanced:** semantic tile schema, bridge IDs/definitions và ý nghĩa
flags; mode/split/active cube; ordered events; phân biệt rejected/fall/loss và terminal state.
Nếu Core sửa class hiện tại tại chỗ để thêm semantics, nominal type check không tự phát hiện
được mọi thay đổi: phải audit lại adapter/schema/tests. Không tuyên bố Advanced đã chạy.
Basic profile hiện kiểm thử độc lập trên source local; chưa có approval tích hợp Core mới.

**Tài cần xác nhận trước wiring:** cấp chuỗi session ID ổn định, không tái dùng cho game session
mới; revision không âm và cách tăng/reset; level ID ổn định, state/board pairing authoritative;
gọi static conversion khi load/thay board, snapshots theo logical update. Chuỗi session là token
opaque, không so sánh lớn/nhỏ theo thứ tự chữ. Cách xử lý stale callbacks/session replacement,
HUD, solver/replay và cancellation vẫn cần contract tích hợp riêng.

Không gửi tin nhắn cho thành viên, không sửa source Core/Controller/Solver hoặc dependencies.
Mới có một level trong repo; fixtures không thay thế yêu cầu >=10 levels/benchmark đồ án.
Windows và visual geometry không được kiểm thử tại 3.2; không có platform/renderer claim.

## 14. Git scope và acceptance

Tracked/staged diff vẫn rỗng; năm file 3.2 là untracked mới, cùng ba file 3.1 có sẵn.
Đối chiếu SHA-256 trước/sau xác nhận toàn bộ 41 file có sẵn không đổi.
Branch và HEAD không đổi. Không stage, branch operation, commit, push hoặc merge.

| # | Tiêu chí | Trạng thái | Bằng chứng |
|---:|---|---|---|
| 1 | Preflight hoàn thành | PASS | Git/read audit, baseline chạy trước source mới |
| 2 | Core API hiện tại được xác minh | PASS | Board/State/level/tests, mục 2 |
| 3 | Đối chiếu Stage 2 | PASS | Bảng khác biệt mục 3; pending giữ nguyên |
| 4 | Có StaticBoardData | PASS | contracts.py, T01–T05 |
| 5 | Có GameSnapshot | PASS | contracts.py, T06–T08 |
| 6 | Có Basic adapter | PASS | Hai public functions, 24 tests adapter |
| 7 | Board mapping đúng | PASS | T09–T11 |
| 8 | Goal mapping đúng | PASS | T12, goal field khác raw 2 |
| 9 | Ba orientation đúng | PASS | T13–T15 |
| 10 | Logical coordinates đúng | PASS | T25, non-square board |
| 11 | Dữ liệu bất biến | PASS | T05/T18 và nested constructor tests |
| 12 | Board revision xác định | PASS | T19–T21, canonical JSON test |
| 13 | Caller cấp session/revision | PASS | T06/T25, context validation test |
| 14 | Validation rõ | PASS | Invalid field tests, TypeError/ValueError |
| 15 | Không sao chép luật Core | PASS | Source review, T26 và state trên VOID |
| 16 | Không import Panda3D | PASS | T23–T24, cả system regression |
| 17 | Không mở GUI | PASS | Pure code, guarded imports, không gọi app |
| 18 | Unit tests đã thực thi | PASS | 37 tests mới PASS |
| 19 | Regression đã thực thi | PASS | 122/122 venv; 120 PASS + 2 SKIP system |
| 20 | Foundation 3.1 được giữ | PASS | SHA-256 ba file, hai foundation tests venv PASS |
| 21 | Không sửa Phong/Tài source | PASS | Manifest và tracked diff |
| 22 | Không sửa shared dependencies | PASS | requirements.txt giữ nguyên; không install |
| 23 | Không tự commit/push/merge | PASS | HEAD/branch giữ nguyên, files vẫn untracked |
| 24 | Không triển khai 3.3 | PASS | Năm files đúng scope; renderer/camera/HUD chưa sửa |

## 15. Điều kiện chuyển sang 3.3

Người dùng review Chặng 3.2 trước nhiệm vụ tiếp theo. Chặng 3.3 có thể dùng hai DTO này
làm đầu vào geometry Basic, chuyển `(row,col)` sang world coordinates theo Geometry Spec,
giữ host/scene roots 3.1. Cần nhiệm vụ riêng và tests hình học/visual thực tế.
Đồng thuận Phong/Tài cho tích hợp và Advanced vẫn PENDING; hoàn thành 3.2 không thay thế
các xác nhận đó. Dừng tại contracts/adapter, không tự triển khai tiếp.
