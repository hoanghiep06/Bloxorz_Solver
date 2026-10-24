import json
from typing import Dict, List, Optional, Set, Tuple
from src.core.state import BloxorzState, Orientation

# Định nghĩa các hành động chuẩn
ACTIONS = ['U', 'D', 'L', 'R']
ALL_ACTIONS = ['U', 'D', 'L', 'R', 'SPACE']
VALID_ACTIONS = ('U', 'D', 'L', 'R', 'SPACE', 'SWITCH')

DIRECTION_DELTA = {
    'U': (-1, 0),
    'D': (1, 0),
    'L': (0, -1),
    'R': (0, 1),
}


class Board:
    def __init__(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid level JSON in {filepath}: {exc.msg} "
                    f"(line {exc.lineno}, column {exc.colno})."
                ) from exc
        if not isinstance(data, dict):
            raise ValueError("Level must be a JSON object with grid, start and goal.")
        for key in ('grid', 'start', 'goal'):
            if key not in data:
                raise ValueError(f"Level is missing required field '{key}'.")

        grid = data['grid']
        if not isinstance(grid, list) or not grid:
            raise ValueError("Level grid must be a non-empty list of rows.")
        if not isinstance(grid[0], list) or not grid[0]:
            raise ValueError("Level grid rows must be non-empty lists.")
        cols = len(grid[0])
        for row in grid:
            if not isinstance(row, list) or len(row) != cols:
                raise ValueError("Level grid must be rectangular with non-empty rows.")
            if any(type(cell) is not int for cell in row):
                raise ValueError("Level grid cells must be integer tile codes (not booleans).")

        self.grid = data['grid']
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.name = data.get('name', 'Bloxorz Board')
        self.metadata = data.get('metadata', {})

        # --- Khởi tạo Bridges (cầu nối: mã ô 7) ---
        self.bridges: List[dict] = data.get('bridges', [])
        self.bridge_id_to_idx: Dict[object, int] = {}
        self.cell_to_bridge_idx: Dict[Tuple[int, int], int] = {}
        initial_bridge_flags = []

        for idx, bridge in enumerate(self.bridges):
            raw_id = bridge.get('id', idx)
            self.bridge_id_to_idx[raw_id] = idx
            self.bridge_id_to_idx[str(raw_id)] = idx
            self.bridge_id_to_idx[idx] = idx
            self.bridge_id_to_idx[str(idx)] = idx

            is_open = bool(bridge.get('initial_state', False))
            initial_bridge_flags.append(is_open)
            for cell in bridge.get('cells', []):
                self.cell_to_bridge_idx[(cell[0], cell[1])] = idx

        self.initial_bridges_state: Tuple[bool, ...] = tuple(initial_bridge_flags)

        # Kiểm tra tính hợp lệ của start và goal
        for key in ('start', 'goal'):
            position = data[key]
            if (not isinstance(position, list) or len(position) != 2
                    or any(type(coord) is not int for coord in position)):
                raise ValueError(f"Level {key} must be [row, col] with two integers.")
            r, c = position
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                raise ValueError(f"Level {key} {position} lies outside the grid.")
            if not self.is_valid_cell(r, c, self.initial_bridges_state):
                raise ValueError(f"Level {key} {position} must not be on a void tile.")

        self.start_r, self.start_c = data['start']
        self.goal_r, self.goal_c = data['goal']

        # --- Khởi tạo Fragile tiles (ô cam dễ vỡ: mã ô 3) ---
        self.fragile_cells: Set[Tuple[int, int]] = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == 3:
                    self.fragile_cells.add((r, c))
        for item in data.get('fragile_tiles', []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                self.fragile_cells.add((item[0], item[1]))

        # --- Khởi tạo Switches (công tắc tròn: mã ô 4, công tắc chữ X: mã ô 5) ---
        self.switches: List[dict] = data.get('switches', [])
        self.switches_by_cell: Dict[Tuple[int, int], List[dict]] = {}

        for sw in self.switches:
            if 'r' in sw and 'c' in sw:
                key = (sw['r'], sw['c'])
            elif 'cell' in sw and len(sw['cell']) == 2:
                key = (sw['cell'][0], sw['cell'][1])
            else:
                continue

            # Tự động gán type theo quy ước kỹ thuật nếu chưa khai báo tường minh
            if 'type' not in sw:
                tile_code = self.grid[key[0]][key[1]] if (0 <= key[0] < self.rows and 0 <= key[1] < self.cols) else None
                if tile_code == 4:
                    sw['type'] = 'soft'
                elif tile_code == 5:
                    sw['type'] = 'heavy'
                elif tile_code == 6:
                    sw['type'] = 'split'
                else:
                    sw['type'] = 'soft'

            self.switches_by_cell.setdefault(key, []).append(sw)

        # --- Khởi tạo Split Switch (công tắc phân tách: mã ô 6) ---
        self.split_switch = data.get('split_switch', None)
        self.split_switches: Dict[Tuple[int, int], dict] = {}

        if self.split_switch:
            raw_splits = self.split_switch if isinstance(self.split_switch, list) else [self.split_switch]
            for sp in raw_splits:
                if isinstance(sp, dict):
                    if 'r' in sp and 'c' in sp:
                        sp_key = (sp['r'], sp['c'])
                    elif 'cell' in sp and len(sp['cell']) == 2:
                        sp_key = (sp['cell'][0], sp['cell'][1])
                    else:
                        continue
                    self.split_switches[sp_key] = sp

        # Hỗ trợ thêm trường hợp split switch nằm trong danh sách switches
        for sw in self.switches:
            if sw.get('type') == 'split':
                if 'r' in sw and 'c' in sw:
                    sp_key = (sw['r'], sw['c'])
                elif 'cell' in sw and len(sw['cell']) == 2:
                    sp_key = (sw['cell'][0], sw['cell'][1])
                else:
                    continue
                self.split_switches[sp_key] = sw

    def get_initial_state(self) -> BloxorzState:
        return BloxorzState(
            self.start_r,
            self.start_c,
            Orientation.STANDING,
            self.initial_bridges_state
        )

    def is_goal(self, state: BloxorzState) -> bool:
        """Đích chỉ được chấp nhận khi khối nguyên vẹn đứng thẳng trên ô Goal."""
        if state.is_split():
            return False
        return state.is_standing() and state.r == self.goal_r and state.c == self.goal_c

    def is_valid_cell(self, r: int, c: int, bridges_state: Optional[Tuple[bool, ...]] = None) -> bool:
        """Kiểm tra ô nằm trong sàn và không rơi vào vực (0: void) hoặc cầu đang đóng."""
        if type(r) is not int or type(c) is not int:
            raise TypeError("Cell coordinates r and c must be integers (not booleans).")
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return False

        # Nếu là ô cầu, trạng thái mở/đóng quyết định tính hợp lệ (mở = đi được, đóng = vực 0)
        if (r, c) in self.cell_to_bridge_idx:
            b_idx = self.cell_to_bridge_idx[(r, c)]
            flags = bridges_state if bridges_state is not None else self.initial_bridges_state
            if b_idx < len(flags):
                return bool(flags[b_idx])
            return False

        # Các ô thông thường: 0 là vực thẳm
        if self.grid[r][c] == 0:
            return False
        return True

    def is_fragile_tile(self, r: int, c: int) -> bool:
        """Kiểm tra ô có phải ô cam dễ vỡ (mã 3) không."""
        return (r, c) in self.fragile_cells or (0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] == 3)

    def is_bridge_tile(self, r: int, c: int) -> bool:
        """Kiểm tra ô có phải ô cầu nối (mã 7 hoặc nằm trong bridges) không."""
        return (r, c) in self.cell_to_bridge_idx or (0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] == 7)

    def is_valid_state(self, state: BloxorzState) -> bool:
        """Kiểm tra toàn bộ các ô mà khối đang chiếm giữ có hợp lệ và được sàn nâng đỡ không."""
        if state.is_split():
            # Hai khối không được ở cùng một vị trí
            if state.cubes[0] == state.cubes[1]:
                return False
            for r, c in state.cubes:
                if not self.is_valid_cell(r, c, state.bridges_state):
                    return False
            # Khối con 1x1x1 có trọng lượng nhẹ bằng một nửa, đi qua ô cam an toàn
            return True

        cells = state.get_occupied_cells()
        for r, c in cells:
            if not self.is_valid_cell(r, c, state.bridges_state):
                return False

        # Kiểm tra ô cam Fragile:
        # Nếu khối nguyên vẹn đứng thẳng trên ô cam -> sàn gãy, khối rơi (không hợp lệ)
        # Nếu khối nằm (HORIZONTAL hoặc VERTICAL) -> trọng lượng phân bổ, an toàn!
        if state.is_standing() and self.is_fragile_tile(state.r, state.c):
            return False
        return True

    def get_actions(self, state: BloxorzState) -> List[str]:
        """Trả về danh sách hành động hợp lệ có thể thử từ trạng thái hiện tại."""
        if state.is_split():
            return ALL_ACTIONS
        return ACTIONS

    def _apply_switch_effects(self, sw: dict, bridges_state: Tuple[bool, ...]) -> Tuple[bool, ...]:
        """Cập nhật trạng thái các cầu liên kết khi công tắc được kích hoạt."""
        if not bridges_state:
            return bridges_state
        target_bridges = sw.get('targets') or sw.get('bridges') or sw.get('target') or []
        if isinstance(target_bridges, (int, str)):
            target_bridges = [target_bridges]
        if not target_bridges:
            return bridges_state

        new_flags = list(bridges_state)
        action = sw.get('action') or sw.get('behavior', 'toggle')

        for b_id in target_bridges:
            b_idx = self.bridge_id_to_idx.get(b_id)
            if b_idx is None:
                b_idx = self.bridge_id_to_idx.get(str(b_id))
            if b_idx is not None and b_idx < len(new_flags):
                if action == 'toggle':
                    new_flags[b_idx] = not new_flags[b_idx]
                elif action in ('open', 'permanent'):
                    new_flags[b_idx] = True
                elif action == 'close':
                    new_flags[b_idx] = False

        return tuple(new_flags)

    def _apply_soft_switch_at(self, cell: Tuple[int, int], bridges_state: Tuple[bool, ...]) -> Tuple[bool, ...]:
        """Kích hoạt công tắc mềm tại cell nếu có."""
        switches = self.switches_by_cell.get(cell, [])
        for sw in switches:
            if sw.get('type') == 'soft':
                bridges_state = self._apply_switch_effects(sw, bridges_state)
        return bridges_state

    def _apply_switches_for_cells(
        self,
        cells: List[Tuple[int, int]],
        orientation: Orientation,
        bridges_state: Tuple[bool, ...]
    ) -> Tuple[bool, ...]:
        """Kích hoạt công tắc khi khối nằm trên các ô cells (chỉ soft switch)."""
        for cell in cells:
            switches = self.switches_by_cell.get(cell, [])
            for sw in switches:
                if sw.get('type') == 'soft':
                    bridges_state = self._apply_switch_effects(sw, bridges_state)
        return bridges_state

    def _apply_switches_for_standing(
        self,
        cell: Tuple[int, int],
        bridges_state: Tuple[bool, ...]
    ) -> Tuple[bool, ...]:
        """Kích hoạt công tắc khi khối đứng thẳng trên cell (cả soft và heavy switch)."""
        switches = self.switches_by_cell.get(cell, [])
        for sw in switches:
            sw_type = sw.get('type')
            if sw_type in ('soft', 'heavy'):
                bridges_state = self._apply_switch_effects(sw, bridges_state)
        return bridges_state

    def _get_split_switch_at(self, cell: Tuple[int, int]) -> Optional[dict]:
        """Lấy cấu hình split switch tại cell nếu có."""
        if cell in self.split_switches:
            return self.split_switches[cell]
        for sw in self.switches_by_cell.get(cell, []):
            if sw.get('type') == 'split':
                return sw
        return None

    def get_switches_at(self, cell: Tuple[int, int]) -> List[dict]:
        """Trả về danh sách các công tắc tại ô (r, c)."""
        return self.switches_by_cell.get(cell, [])

    def transition(self, state: BloxorzState, action: str) -> Optional[BloxorzState]:
        """Return a new valid state or None; unsupported actions raise ValueError.

        The source must be a valid BloxorzState on this board and is never mutated.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(f"Unsupported action {action!r}; expected one of {ACTIONS}.")

        # --- Xử lý đổi khối điều khiển khi đang SPLIT ('SPACE' hoặc 'SWITCH') ---
        if action in ('SPACE', 'SWITCH'):
            if not state.is_split():
                return None
            new_active = 1 - state.active_cube
            return BloxorzState.create_split(
                state.cubes[0],
                state.cubes[1],
                active_cube=new_active,
                bridges_state=state.bridges_state
            )

        # --- Xử lý di chuyển khi khối đang bị tách (SPLIT mode) ---
        if state.is_split():
            active_idx = state.active_cube
            curr_pos = state.cubes[active_idx]
            other_pos = state.cubes[1 - active_idx]
            dr, dc = DIRECTION_DELTA[action]
            next_pos = (curr_pos[0] + dr, curr_pos[1] + dc)

            # Hai khối không thể bước vào cùng một ô
            if next_pos == other_pos:
                return None

            # Kiểm tra ô đích có nằm trong sàn và không phải void / cầu đóng
            if not self.is_valid_cell(next_pos[0], next_pos[1], state.bridges_state):
                return None

            # Kiểm tra tái hợp nhất (REJOIN/MERGE) khi 2 khối nằm ở 2 ô kề sát nhau trực giao
            r1, c1_pos = next_pos
            r2, c2_pos = other_pos

            # Kề ngang: cùng hàng r, cột cách nhau đúng 1
            if r1 == r2 and abs(c1_pos - c2_pos) == 1:
                merged_r = r1
                merged_c = min(c1_pos, c2_pos)
                merged_o = Orientation.HORIZONTAL
                merged_cells = [(merged_r, merged_c), (merged_r, merged_c + 1)]
                new_bridges = self._apply_switches_for_cells(merged_cells, merged_o, state.bridges_state)
                merged_state = BloxorzState(merged_r, merged_c, merged_o, new_bridges)
                return merged_state if self.is_valid_state(merged_state) else None

            # Kề dọc: cùng cột c, hàng cách nhau đúng 1
            elif c1_pos == c2_pos and abs(r1 - r2) == 1:
                merged_r = min(r1, r2)
                merged_c = c1_pos
                merged_o = Orientation.VERTICAL
                merged_cells = [(merged_r, merged_c), (merged_r + 1, merged_c)]
                new_bridges = self._apply_switches_for_cells(merged_cells, merged_o, state.bridges_state)
                merged_state = BloxorzState(merged_r, merged_c, merged_o, new_bridges)
                return merged_state if self.is_valid_state(merged_state) else None

            else:
                # Chưa kề nhau: tiếp tục di chuyển khối con ở chế độ SPLIT
                new_c0 = next_pos if active_idx == 0 else other_pos
                new_c1 = next_pos if active_idx == 1 else other_pos
                # Khối con 1x1x1 chỉ kích hoạt được SOFT switch (không đủ nặng kích hoạt heavy switch)
                new_bridges = self._apply_soft_switch_at(next_pos, state.bridges_state)
                new_state = BloxorzState.create_split(new_c0, new_c1, active_idx, new_bridges)
                return new_state if self.is_valid_state(new_state) else None

        # --- Xử lý di chuyển khối nguyên vẹn (WHOLE mode: 12 trường hợp lăn) ---
        r, c, o = state.r, state.c, state.orientation
        new_r, new_c, new_o = r, c, o

        if o == Orientation.STANDING:
            if action == 'U':   new_r, new_c, new_o = r - 2, c, Orientation.VERTICAL
            elif action == 'D': new_r, new_c, new_o = r + 1, c, Orientation.VERTICAL
            elif action == 'L': new_r, new_c, new_o = r, c - 2, Orientation.HORIZONTAL
            elif action == 'R': new_r, new_c, new_o = r, c + 1, Orientation.HORIZONTAL

        elif o == Orientation.HORIZONTAL:
            if action == 'U':   new_r, new_c, new_o = r - 1, c, Orientation.HORIZONTAL
            elif action == 'D': new_r, new_c, new_o = r + 1, c, Orientation.HORIZONTAL
            elif action == 'L': new_r, new_c, new_o = r, c - 1, Orientation.STANDING
            elif action == 'R': new_r, new_c, new_o = r, c + 2, Orientation.STANDING

        elif o == Orientation.VERTICAL:
            if action == 'U':   new_r, new_c, new_o = r - 1, c, Orientation.STANDING
            elif action == 'D': new_r, new_c, new_o = r + 2, c, Orientation.STANDING
            elif action == 'L': new_r, new_c, new_o = r, c - 1, Orientation.VERTICAL
            elif action == 'R': new_r, new_c, new_o = r, c + 1, Orientation.VERTICAL

        candidate = BloxorzState(new_r, new_c, new_o, state.bridges_state)
        if not self.is_valid_state(candidate):
            return None

        # Kiểm tra kích hoạt switch
        if new_o == Orientation.STANDING:
            # Split switch ("( )"): chỉ kích hoạt khi khối đứng thẳng lên ô
            split_sw = self._get_split_switch_at((new_r, new_c))
            if split_sw is not None:
                split_positions = split_sw.get('split_positions')
                if split_positions and len(split_positions) == 2:
                    pos0 = (split_positions[0][0], split_positions[0][1])
                    pos1 = (split_positions[1][0], split_positions[1][1])
                    if pos0 != pos1:
                        new_bridges = self._apply_switch_effects(split_sw, state.bridges_state)
                        # Nếu các điểm dịch chuyển tới có soft switch, kích hoạt tiếp
                        new_bridges = self._apply_soft_switch_at(pos0, new_bridges)
                        new_bridges = self._apply_soft_switch_at(pos1, new_bridges)
                        split_state = BloxorzState.create_split(pos0, pos1, active_cube=0, bridges_state=new_bridges)
                        return split_state if self.is_valid_state(split_state) else None

            # Kích hoạt Heavy switch ("X") hoặc Soft switch ("O") khi đứng thẳng
            new_bridges = self._apply_switches_for_standing((new_r, new_c), state.bridges_state)
            result_state = BloxorzState(new_r, new_c, new_o, new_bridges)
            return result_state if self.is_valid_state(result_state) else None

        else:
            # Khối đang nằm (HORIZONTAL hoặc VERTICAL): chỉ kích hoạt Soft switch
            occupied = candidate.get_occupied_cells()
            new_bridges = self._apply_switches_for_cells(occupied, new_o, state.bridges_state)
            result_state = BloxorzState(new_r, new_c, new_o, new_bridges)
            return result_state if self.is_valid_state(result_state) else None
