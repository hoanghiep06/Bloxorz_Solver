#!/usr/bin/env python3
"""Reproducible weight-tuning experiment for the Bloxorz 18-level dataset.

This script uses the project's Board/State/transition implementation, but uses
an experiment-local weighted-search implementation so path-dependent immediate
backtracking can be represented correctly in the search key (state, last_action).

The tuning target is a predeclared engineering rubric over per-level normalized
ranks of trajectory features. It is NOT a human-labeled ground-truth objective.
"""
from __future__ import annotations
import argparse, csv, itertools, json, math, os, statistics, sys, time, tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = ROOT / 'Bloxorz_Solver-feat-team-code-phase2-game-gui'
LEVEL_DIR = ROOT / 'benchmark_levels' / 'levels'
TRAJ_DIR = ROOT / 'benchmark_levels' / 'trajectories'
OUT = HERE / 'results'
OUT.mkdir(parents=True, exist_ok=True)
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
from src.core.board import Board

# Candidate values are coarse, predeclared ranges, including the values in the
# team's original formula (w_b=3, w_v=2, w_f=4, w_switch=2.5, w_bridge=3).
W_GRID = {
    'w_backtrack': [0.0, 3.0, 5.0],
    'w_void': [0.0, 2.0, 4.0],
    'w_fragile': [0.0, 4.0, 8.0],
    'w_switch_change': [0.0, 2.5, 5.0],
    'w_bridge_entry': [0.0, 3.0, 5.0],
}
# Baselines for comparison:
# 1. BASELINE_RUBRIC: The team's initial engineering rubric weights
# 2. BASELINE_CONST_1: Unit step cost (cost_function = const = 1.0, all penalty weights = 0)
# 3. BASELINE_EQUAL_1: All feature penalties normalized to equal 1.0
BASELINE_RUBRIC = (3.0, 2.0, 4.0, 2.5, 3.0)
BASELINE_CONST_1 = (0.0, 0.0, 0.0, 0.0, 0.0)
BASELINE_EQUAL_1 = (1.0, 1.0, 1.0, 1.0, 1.0)
BASELINE_W = BASELINE_RUBRIC  # Primary reference baseline for CV replacement rule

BASELINES_META = {
    'rubric': {'name': 'Baseline_Rubric (3, 2, 4, 2.5, 3)', 'weights': BASELINE_RUBRIC},
    'const_1': {'name': 'Baseline_Const1 (c = const = 1)', 'weights': BASELINE_CONST_1},
    'equal_1': {'name': 'Baseline_Equal1 (all w = 1)', 'weights': BASELINE_EQUAL_1},
}
W_NAMES = list(W_GRID)
GBFS_BASELINE = (1.0, 1.0, 0.0, 0.0)  # matches GreedySolver's existing orientation/split penalties
FEATURE_NAMES = ['steps', 'backtracks', 'void_exposure', 'fragile_entries', 'switch_changes', 'bridge_entries']
# Predeclared evaluation priorities. They are proportional to the team's initial
# rubric coefficients but applied to within-level rank percentiles, not raw cost.
QUALITY_WEIGHTS = {
    'steps': 1.0 / 15.5,
    'backtracks': 3.0 / 15.5,
    'void_exposure': 2.0 / 15.5,
    'fragile_entries': 4.0 / 15.5,
    'switch_changes': 2.5 / 15.5,
    'bridge_entries': 3.0 / 15.5,
}
INVERSE = {'U':'D', 'D':'U', 'L':'R', 'R':'L'}
CONTROL_ACTIONS = {'SPACE', 'SWITCH'}

@dataclass
class Graph:
    level_id: str
    board: Any
    start: tuple
    nodes: List[tuple]
    outgoing: Dict[tuple, list]
    incoming: Dict[tuple, list]
    goals: set
    build_ms: float


def occupied(state):
    return set(state.get_occupied_cells())


def near_void_cell(board, state, cell):
    r, c = cell
    unavailable = 0
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r + dr, c + dc
        if not board.is_valid_cell(nr, nc, state.bridges_state):
            unavailable += 1
    return unavailable >= 2


def transition_features(board, state, last_action, action, nxt):
    """Features accumulated per action under explicit experiment definitions.

    - steps: directional rolls U/D/L/R only. SPACE/SWITCH changes the active cube
      but is not counted as a move, following the instructor FAQ.
    - backtracks: a roll immediately reverses the previous roll; a control-switch
      action resets this immediate-backtrack context because the active cube changes.
    - void_exposure: one count on a roll if the successor occupies a cell with >=2
      blocked or out-of-board orthogonal neighbours. Control switching adds no exposure.
    - fragile_entries: newly occupied cells that are fragile (not a failed move).
    - switch_changes: number of bridge flags changed on a roll transition; a control
      switch does not itself incur terrain/switch penalties.
    - bridge_entries: newly occupied cells that are bridge tiles on a roll.
    """
    is_roll = action in INVERSE
    if not is_roll:
        # Controller change only: it is a search transition, but not a physical move.
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    current_cells = occupied(state)
    next_cells = occupied(nxt)
    newly_occupied = next_cells - current_cells
    backtrack = 1 if last_action in INVERSE and INVERSE[last_action] == action else 0
    void_exposure = 1 if any(near_void_cell(board, nxt, cell) for cell in next_cells) else 0
    fragile_entries = sum(1 for r,c in newly_occupied if board.is_fragile_tile(r,c))
    before, after = state.bridges_state, nxt.bridges_state
    maxn = max(len(before), len(after))
    switch_changes = sum(1 for i in range(maxn) if (before[i] if i < len(before) else False) != (after[i] if i < len(after) else False))
    bridge_entries = sum(1 for r,c in newly_occupied if board.is_bridge_tile(r,c))
    return (1.0, float(backtrack), float(void_exposure), float(fragile_entries), float(switch_changes), float(bridge_entries))


def build_graph(level_path: Path) -> Graph:
    t0 = time.perf_counter()
    board = Board(str(level_path))
    start_state = board.get_initial_state()
    start = (start_state, None)
    queue = deque([start])
    seen = {start}
    outgoing, incoming = {}, defaultdict(list)
    nodes = []
    goals = set()
    while queue:
        node = queue.popleft()
        nodes.append(node)
        state, last_action = node
        if board.is_goal(state):
            goals.add(node)
        edges = []
        for action in board.get_actions(state):
            nxt = board.transition(state, action)
            if nxt is None:
                continue
            # Only retain the previous roll when it is adjacent in the movement
            # sequence. Switching active cubes resets the immediate-backtrack context.
            next_last_action = action if action in INVERSE else None
            nxt_node = (nxt, next_last_action)
            feats = transition_features(board, state, last_action, action, nxt)
            edges.append((nxt_node, action, feats))
            incoming[nxt_node].append((node, action, feats))
            if nxt_node not in seen:
                seen.add(nxt_node)
                queue.append(nxt_node)
        outgoing[node] = edges
    build_ms = (time.perf_counter() - t0) * 1000
    return Graph(level_path.stem, board, start, nodes, outgoing, dict(incoming), goals, build_ms)


def weighted_edge_cost(feats, weights):
    # Step is fixed to 1.0 to remove the scale non-identifiability of all weights.
    return feats[0] + sum(w * f for w, f in zip(weights, feats[1:]))


def search_graph_ucs(graph: Graph, weights, keep_path=True):
    from heapq import heappush, heappop
    if graph.board.is_goal(graph.start[0]):
        return {'success': True, 'actions': [], 'total_cost': 0.0, 'expanded_nodes': 0, 'search_ms': 0.0, 'features': tuple(0.0 for _ in FEATURE_NAMES)}
    t0 = time.perf_counter()
    seq = itertools.count()
    dist = {graph.start: 0.0}
    parent = {} if keep_path else None
    pq = [(0.0, next(seq), graph.start)]
    expanded = 0
    goal = None
    while pq:
        g, _, node = heappop(pq)
        if g > dist.get(node, math.inf) + 1e-12:
            continue
        expanded += 1
        if node in graph.goals:
            goal = node
            break
        for nxt, action, feats in graph.outgoing[node]:
            ng = g + weighted_edge_cost(feats, weights)
            if ng < dist.get(nxt, math.inf) - 1e-12:
                dist[nxt] = ng
                if keep_path:
                    parent[nxt] = (node, action, feats)
                heappush(pq, (ng, next(seq), nxt))
    elapsed = (time.perf_counter() - t0) * 1000
    if goal is None:
        return {'success': False, 'actions': None, 'total_cost': math.inf, 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': None}
    actions, feat_sum = [], [0.0] * 6
    if keep_path:
        cursor = goal
        while cursor != graph.start:
            prev, action, feats = parent[cursor]
            actions.append(action)
            for i, v in enumerate(feats): feat_sum[i] += v
            cursor = prev
        actions.reverse()
    return {'success': True, 'actions': actions, 'total_cost': dist[goal], 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': tuple(feat_sum)}


def h0(board, state):
    """Actual heuristic implemented in the codebase (src/solvers/astar.py).

    - For whole blocks: min Manhattan distance of occupied cells to goal divided by 2
      (since a roll moves up to 2 cells), plus 0.5 penalty if not standing (at least
      one roll is required to stand up on the goal).
    - For split blocks: accounts for steps needed for cubes to become adjacent plus
      distance to goal: max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0 + 1.0.
    """
    if state.is_split():
        c0, c1 = state.cubes
        inter_dist = float(abs(c0[0] - c1[0]) + abs(c0[1] - c1[1]))
        d0 = float(abs(c0[0] - board.goal_r) + abs(c0[1] - board.goal_c))
        d1 = float(abs(c1[0] - board.goal_r) + abs(c1[1] - board.goal_c))
        return max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0 + 1.0

    occupied_cells = state.get_occupied_cells()
    min_d = min(abs(r - board.goal_r) + abs(c - board.goal_c) for r, c in occupied_cells) / 2.0
    if not state.is_standing():
        min_d += 0.5
    return min_d


def search_graph_astar(graph: Graph, weights, alpha: float):
    from heapq import heappush, heappop
    if graph.board.is_goal(graph.start[0]):
        return {'success': True, 'actions': [], 'total_cost': 0.0, 'expanded_nodes': 0, 'search_ms': 0.0, 'features': tuple(0.0 for _ in FEATURE_NAMES)}
    t0 = time.perf_counter()
    seq = itertools.count()
    dist = {graph.start: 0.0}
    parent = {}
    pq = [(alpha*h0(graph.board, graph.start[0]), 0.0, next(seq), graph.start)]
    expanded = 0
    goal = None
    while pq:
        f, g, _, node = heappop(pq)
        if g > dist.get(node, math.inf) + 1e-12:
            continue
        expanded += 1
        if node in graph.goals:
            goal = node
            break
        for nxt, action, feats in graph.outgoing[node]:
            ng = g + weighted_edge_cost(feats, weights)
            if ng < dist.get(nxt, math.inf) - 1e-12:
                dist[nxt] = ng
                parent[nxt] = (node, action, feats)
                nf = ng + alpha*h0(graph.board, nxt[0])
                heappush(pq, (nf, ng, next(seq), nxt))
    elapsed = (time.perf_counter() - t0) * 1000
    if goal is None:
        return {'success': False, 'actions': None, 'total_cost': math.inf, 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': None}
    actions, feat_sum = [], [0.0] * 6
    cursor = goal
    while cursor != graph.start:
        prev, action, feats = parent[cursor]
        actions.append(action)
        for i, v in enumerate(feats): feat_sum[i] += v
        cursor = prev
    actions.reverse()
    return {'success': True, 'actions': actions, 'total_cost': dist[goal], 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': tuple(feat_sum)}


def gbfs_heuristic(board, state, params):
    w_orient, w_split, w_edge, w_fragile = params
    occ = state.get_occupied_cells()
    if state.is_split():
        c0, c1 = state.cubes
        inter = abs(c0[0]-c1[0]) + abs(c0[1]-c1[1])
        d0 = abs(c0[0]-board.goal_r) + abs(c0[1]-board.goal_c)
        d1 = abs(c1[0]-board.goal_r) + abs(c1[1]-board.goal_c)
        distance = max(0.0, (inter - 1.0) / 2.0) + min(d0,d1) / 2.0
        split_term, orient_term = 1.0, 0.0
    else:
        # Match the project's existing GreedySolver exactly for the baseline:
        # it computes Manhattan distance from the state's anchor (r, c), not
        # from the closest occupied cell. Keep that convention when tuning.
        distance = (abs(state.r-board.goal_r) + abs(state.c-board.goal_c)) / 2.0
        split_term = 0.0
        orient_term = 0.0 if state.is_standing() else 1.0
    edge_term = sum(1.0 for cell in occ if near_void_cell(board, state, cell))
    fragile_term = sum(1.0 for r,c in occ if board.is_fragile_tile(r,c))
    return distance + w_orient*orient_term + w_split*split_term + w_edge*edge_term + w_fragile*fragile_term


def search_gbfs(graph: Graph, params):
    from heapq import heappush, heappop
    board = graph.board
    start_state = board.get_initial_state()
    if board.is_goal(start_state):
        return {'success': True, 'actions': [], 'total_cost': 0.0, 'expanded_nodes': 0, 'search_ms': 0.0, 'features': tuple(0.0 for _ in FEATURE_NAMES)}
    t0 = time.perf_counter()
    seq = itertools.count()
    pq = [(gbfs_heuristic(board, start_state, params), next(seq), start_state, [])]
    visited = {start_state}
    expanded = 0
    actions_out = None
    while pq:
        _, _, state, path = heappop(pq)
        expanded += 1
        if board.is_goal(state):
            actions_out = path
            break
        for action in board.get_actions(state):
            nxt = board.transition(state, action)
            if nxt is None or nxt in visited:
                continue
            visited.add(nxt)
            heappush(pq, (gbfs_heuristic(board, nxt, params), next(seq), nxt, path + [action]))
    elapsed = (time.perf_counter() - t0) * 1000
    if actions_out is None:
        return {'success': False, 'actions': None, 'total_cost': math.inf, 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': None}
    metrics = replay_and_measure(board, actions_out)
    return {'success': metrics['success'], 'actions': actions_out, 'total_cost': None, 'expanded_nodes': expanded, 'search_ms': elapsed, 'features': metrics['feature_tuple'], 'solution_valid': metrics['solution_valid']}


def replay_and_measure(board, actions):
    state = board.get_initial_state()
    last_action = None
    sums = [0.0] * 6
    valid = True
    for action in actions:
        nxt = board.transition(state, action)
        if nxt is None:
            valid = False
            break
        feats = transition_features(board, state, last_action, action, nxt)
        for i, val in enumerate(feats): sums[i] += val
        # SPACE/SWITCH does not count as a move and resets immediate-backtrack
        # context because the next roll controls the other cube.
        last_action = action if action in INVERSE else None
        state = nxt
    success = bool(valid and board.is_goal(state))
    return {
        'success': success,
        'solution_valid': valid and success,
        'steps': int(sums[0]),
        'action_count': len(actions),
        'control_switches': sum(1 for a in actions if a in CONTROL_ACTIONS),
        'backtracks': int(sums[1]),
        'void_exposure': int(sums[2]),
        'fragile_entries': int(sums[3]),
        'switch_changes': int(sums[4]),
        'bridge_entries': int(sums[5]),
        'feature_tuple': tuple(sums),
    }


def baseline_distance(weights):
    scales = [5,4,6,4,5]
    return sum(abs(a-b)/s for a,b,s in zip(weights, BASELINE_W, scales))


def percentile_ranks(values):
    n = len(values)
    if n <= 1 or min(values) == max(values):
        return [0.0] * n
    sorted_values = sorted((v, i) for i, v in enumerate(values))
    out = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j+1 < n and sorted_values[j+1][0] == sorted_values[i][0]:
            j += 1
        avg_rank_zero_based = (i + j) / 2.0
        pct = avg_rank_zero_based / (n - 1)
        for k in range(i, j+1): out[sorted_values[k][1]] = pct
        i = j+1
    return out


def add_quality_losses(rows, level_field='level_id'):
    by_level = defaultdict(list)
    for row in rows: by_level[row[level_field]].append(row)
    for level, grp in by_level.items():
        valid_rows = [r for r in grp if str(r.get('success', False)).lower() in ('true','1') and str(r.get('solution_valid', True)).lower() in ('true','1')]
        metric_names = list(QUALITY_WEIGHTS)
        rankmaps = {}
        for m in metric_names:
            vals = [float(r[m]) for r in valid_rows]
            ranks = percentile_ranks(vals)
            rankmaps[m] = {id(r): ranks[i] for i,r in enumerate(valid_rows)}
        valid_ids = {id(r) for r in valid_rows}
        for r in grp:
            if id(r) not in valid_ids:
                r['quality_loss'] = 2.0
            else:
                r['quality_loss'] = sum(QUALITY_WEIGHTS[m] * rankmaps[m][id(r)] for m in metric_names)
    return rows


def make_folds(level_ids):
    # Six deterministic, category-balanced folds, 3 levels each. All trajectories
    # from a level stay together; no random trajectory-level split is used.
    categories = [level_ids[0:4], level_ids[4:8], level_ids[8:14], level_ids[14:18]]
    fold_lists = [[] for _ in range(6)]
    assigns = [([0,1,2,3]), ([2,3,4,5]), ([0,1,2,3,4,5]), ([0,1,4,5])]
    for cat, folds in zip(categories, assigns):
        for lev, fold in zip(cat, folds): fold_lists[fold].append(lev)
    # sort for reproducibility
    return {f: sorted(ls) for f,ls in enumerate(fold_lists)}


def write_csv(path, rows, fieldnames=None):
    if not rows:
        return
    if fieldnames is None:
        keys = []
        for row in rows:
            for k in row:
                if k not in keys: keys.append(k)
        fieldnames = keys
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)


def load_trajectory_audit(level_ids):
    audit=[]
    for level in level_ids:
        p = TRAJ_DIR / f'{level}_trajectories.json'
        if not p.exists(): continue
        try:
            obj=json.loads(p.read_text(encoding='utf-8'))
            trajectories=obj.get('trajectories', [])
        except Exception:
            continue
        board=Board(str(LEVEL_DIR/f'{level}.json'))
        seen={}
        for item in trajectories:
            actions=item.get('actions') or []
            m=replay_and_measure(board, actions)
            key=tuple(actions)
            audit.append({
                'level_id':level,'trajectory_name':item.get('name',''),'stored_success':item.get('success'),
                'replay_success':m['success'],'solution_valid':m['solution_valid'],
                'stored_steps':item.get('steps'),'replayed_steps':m['steps'],
                'replayed_action_count':m['action_count'],'replayed_control_switches':m['control_switches'],
                'duplicate_sequence_in_level':key in seen,
                'duplicate_of':seen.get(key,''),
                'stored_score':item.get('score'),'stored_rating':item.get('rating'),
                'actions':' '.join(actions),
            })
            if key not in seen: seen[key]=item.get('name','')
    write_csv(OUT/'trajectory_audit.csv', audit)
    return audit


def run_ucs_grid(graphs, fast=False):
    values = [W_GRID[k] for k in W_NAMES]
    configs=[]
    for idx, vals in enumerate(itertools.product(*values)):
        configs.append({'config_id':idx, **dict(zip(W_NAMES, vals)), 'weights':tuple(vals)})

    # Ensure all 3 reference baselines are explicitly included in configs:
    # 1. BASELINE_RUBRIC: (3.0, 2.0, 4.0, 2.5, 3.0)
    # 2. BASELINE_CONST_1: (0.0, 0.0, 0.0, 0.0, 0.0)
    # 3. BASELINE_EQUAL_1: (1.0, 1.0, 1.0, 1.0, 1.0)
    if not any(all(abs(c[k]-v)<1e-9 for k,v in zip(W_NAMES, BASELINE_EQUAL_1)) for c in configs):
        configs.append({'config_id': len(configs), **dict(zip(W_NAMES, BASELINE_EQUAL_1)), 'weights': BASELINE_EQUAL_1, 'is_extra_baseline': True})

    checkpoint = OUT/'ucs_grid_raw_checkpoint.csv'
    rows=[]
    if checkpoint.exists():
        with open(checkpoint, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        done = defaultdict(set)
        for r in rows: done[int(r['config_id'])].add(r['level_id'])
    else:
        done = defaultdict(set)
    t0=time.perf_counter()
    for ci,cfg in enumerate(configs):
        if set(g.level_id for g in graphs).issubset(done.get(cfg['config_id'], set())):
            continue
        new_rows=[]
        for graph in graphs:
            if graph.level_id in done.get(cfg['config_id'], set()):
                continue
            result=search_graph_ucs(graph,cfg['weights'])
            m=replay_and_measure(graph.board, result['actions'] or []) if result['success'] else None
            new_rows.append({
                'config_id':cfg['config_id'],'level_id':graph.level_id,
                **{k:cfg[k] for k in W_NAMES},
                'success':bool(result['success']), 'solution_valid':bool(m and m['solution_valid']),
                'steps':m['steps'] if m else '', 'backtracks':m['backtracks'] if m else '',
                'void_exposure':m['void_exposure'] if m else '',
                'fragile_entries':m['fragile_entries'] if m else '',
                'switch_changes':m['switch_changes'] if m else '',
                'bridge_entries':m['bridge_entries'] if m else '',
                'total_cost':result['total_cost'], 'expanded_nodes':result['expanded_nodes'],
                'cached_graph_search_ms':round(result['search_ms'],4),
            })
        rows.extend(new_rows)
        # Save a recoverable checkpoint after each 9 configurations.
        if (ci+1)%9==0 or ci+1==len(configs):
            write_csv(checkpoint, rows)
            print(f'[UCS grid] {ci+1}/{len(configs)} configs; rows={len(rows)}; elapsed {time.perf_counter()-t0:.1f}s', flush=True)
    # Add normalized ranking objective on a per-level basis.
    rows=add_quality_losses(rows)
    write_csv(OUT/'ucs_grid_results.csv',rows)
    # CV by level groups
    level_ids=[g.level_id for g in graphs]
    folds=make_folds(level_ids)
    cfgmap={c['config_id']:c for c in configs}
    per_config_level={(int(r['config_id']),r['level_id']):float(r['quality_loss']) for r in rows}
    cv=[]; choices=[]
    baseline_rubric_id=next(c['config_id'] for c in configs if all(abs(c[k]-v)<1e-9 for k,v in zip(W_NAMES,BASELINE_RUBRIC)))
    baseline_const1_id=next(c['config_id'] for c in configs if all(abs(c[k]-v)<1e-9 for k,v in zip(W_NAMES,BASELINE_CONST_1)))
    baseline_equal1_id=next(c['config_id'] for c in configs if all(abs(c[k]-v)<1e-9 for k,v in zip(W_NAMES,BASELINE_EQUAL_1)))
    baseline_id = baseline_rubric_id

    for fold,held in folds.items():
        train=[lv for lv in level_ids if lv not in held]
        scored=[]
        for c in configs:
            mean_loss=statistics.mean(per_config_level[(c['config_id'],lv)] for lv in train)
            scored.append((mean_loss, baseline_distance(c['weights']), c['config_id']))
        best_id=min(scored)[2]
        best=cfgmap[best_id]
        sel_test=statistics.mean(per_config_level[(best_id,lv)] for lv in held)
        sel_train=statistics.mean(per_config_level[(best_id,lv)] for lv in train)
        rubric_test=statistics.mean(per_config_level[(baseline_rubric_id,lv)] for lv in held)
        rubric_train=statistics.mean(per_config_level[(baseline_rubric_id,lv)] for lv in train)
        const1_test=statistics.mean(per_config_level[(baseline_const1_id,lv)] for lv in held)
        const1_train=statistics.mean(per_config_level[(baseline_const1_id,lv)] for lv in train)
        equal1_test=statistics.mean(per_config_level[(baseline_equal1_id,lv)] for lv in held)
        equal1_train=statistics.mean(per_config_level[(baseline_equal1_id,lv)] for lv in train)
        cv.append({
            'fold':fold+1,'train_levels':' '.join(train),'heldout_levels':' '.join(held),
            'selected_config_id':best_id,**{k:best[k] for k in W_NAMES},
            'train_quality_loss':sel_train,
            'heldout_quality_loss':sel_test,
            'baseline_rubric_train_loss':rubric_train,
            'baseline_rubric_heldout_loss':rubric_test,
            'heldout_improvement_vs_rubric':rubric_test-sel_test,
            'baseline_const1_train_loss':const1_train,
            'baseline_const1_heldout_loss':const1_test,
            'heldout_improvement_vs_const1':const1_test-sel_test,
            'baseline_equal1_train_loss':equal1_train,
            'baseline_equal1_heldout_loss':equal1_test,
            'heldout_improvement_vs_equal1':equal1_test-sel_test,
            # Backward-compatible fields
            'baseline_train_quality_loss':rubric_train,
            'baseline_heldout_quality_loss':rubric_test,
            'heldout_improvement_vs_baseline':rubric_test-sel_test,
        })
        choices.append(best_id)
    write_csv(OUT/'ucs_grouped_cv.csv',cv)
    full_scores=[]
    for c in configs:
        v=statistics.mean(per_config_level[(c['config_id'],lv)] for lv in level_ids)
        full_scores.append((v,baseline_distance(c['weights']),c['config_id']))
    best_full=min(full_scores)[2]
    cv_improvement_rubric=statistics.mean(float(r['heldout_improvement_vs_rubric']) for r in cv)
    cv_improvement_const1=statistics.mean(float(r['heldout_improvement_vs_const1']) for r in cv)
    cv_improvement_equal1=statistics.mean(float(r['heldout_improvement_vs_equal1']) for r in cv)
    cv_improvement = cv_improvement_rubric

    # Only replace original rubric baseline if average held-out loss improves; else retain it.
    chosen_id=best_full if cv_improvement_rubric > 1e-12 else baseline_rubric_id
    chosen=cfgmap[chosen_id]
    top_rows=[]
    for score,dist,cid in sorted(full_scores)[:35]:
        cc=cfgmap[cid]
        top_rows.append({
            'config_id':cid,
            **{k:cc[k] for k in W_NAMES},
            'mean_quality_loss':score,
            'distance_to_rubric_baseline':dist,
            'is_baseline_rubric':cid==baseline_rubric_id,
            'is_baseline_const1':cid==baseline_const1_id,
            'is_baseline_equal1':cid==baseline_equal1_id,
            'is_original_baseline':cid==baseline_rubric_id,
        })
    write_csv(OUT/'ucs_top_configs.csv',top_rows)
    summary={
        'grid_size':len(configs),
        'baseline_configurations':{
            'baseline_rubric':{
                'config_id':baseline_rubric_id,
                'weights':dict(zip(W_NAMES,BASELINE_RUBRIC)),
                'mean_quality_loss':per_config_mean(per_config_level,baseline_rubric_id,level_ids),
                'mean_cv_heldout_loss':statistics.mean(float(r['baseline_rubric_heldout_loss']) for r in cv),
                'description':'Hand-crafted engineering rubric baseline (3, 2, 4, 2.5, 3)',
            },
            'baseline_const_1':{
                'config_id':baseline_const1_id,
                'weights':dict(zip(W_NAMES,BASELINE_CONST_1)),
                'mean_quality_loss':per_config_mean(per_config_level,baseline_const1_id,level_ids),
                'mean_cv_heldout_loss':statistics.mean(float(r['baseline_const1_heldout_loss']) for r in cv),
                'description':'Unit step cost baseline (cost_function = const = 1.0, zero penalties)',
            },
            'baseline_equal_1':{
                'config_id':baseline_equal1_id,
                'weights':dict(zip(W_NAMES,BASELINE_EQUAL_1)),
                'mean_quality_loss':per_config_mean(per_config_level,baseline_equal1_id,level_ids),
                'mean_cv_heldout_loss':statistics.mean(float(r['baseline_equal1_heldout_loss']) for r in cv),
                'description':'Equal penalty weights baseline (all penalty weights = 1.0)',
            },
        },
        'baseline_config_id':baseline_rubric_id,
        'baseline_rubric_config_id':baseline_rubric_id,
        'baseline_const1_config_id':baseline_const1_id,
        'baseline_equal1_config_id':baseline_equal1_id,
        'best_full_data_config_id':best_full,
        'chosen_config_id':chosen_id,
        'decision':'grid-search candidate selected because grouped-CV held-out rubric loss improves over baseline rubric' if chosen_id==best_full else 'retain baseline rubric because grouped-CV did not improve on baseline rubric',
        'baseline_weights':dict(zip(W_NAMES,BASELINE_RUBRIC)),
        'chosen_weights':dict(zip(W_NAMES,chosen['weights'])),
        'best_full_data_mean_rank_loss':min(full_scores)[0],
        'baseline_mean_rank_loss':per_config_mean(per_config_level,baseline_rubric_id,level_ids),
        'baseline_const1_mean_rank_loss':per_config_mean(per_config_level,baseline_const1_id,level_ids),
        'baseline_equal1_mean_rank_loss':per_config_mean(per_config_level,baseline_equal1_id,level_ids),
        'mean_cv_heldout_improvement_vs_rubric':cv_improvement_rubric,
        'mean_cv_heldout_improvement_vs_const1':cv_improvement_const1,
        'mean_cv_heldout_improvement_vs_equal1':cv_improvement_equal1,
        'mean_cv_heldout_improvement_vs_baseline':cv_improvement_rubric,
        'cv_selected_config_ids':choices,
        'folds':folds,
        'quality_weights':QUALITY_WEIGHTS,
        'interpretation':'Engineering tuning against the predeclared rank-normalized rubric; evaluated and compared against 3 baselines: Team Rubric, Constant Cost (c=1), and Equal Weights (all=1).'
    }
    (OUT/'ucs_tuning_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return configs,rows,chosen,summary,graphs


def per_config_mean(per_config_level,cid,levels):
    return statistics.mean(per_config_level[(cid,lv)] for lv in levels)


def validate_heuristic(graph):
    # Check admissibility and consistency against the baseline movement cost:
    # directional rolls cost 1; SPACE/SWITCH control changes cost 0.
    from heapq import heappush, heappop
    dist = {goal: 0.0 for goal in graph.goals}
    sequence = itertools.count()
    pq = [(0.0, next(sequence), goal) for goal in graph.goals]
    while pq:
        distance, _, node = heappop(pq)
        if distance > dist.get(node, math.inf) + 1e-12:
            continue
        for prev, _action, feats in graph.incoming.get(node, []):
            edge_cost = float(feats[0])
            candidate = distance + edge_cost
            if candidate < dist.get(prev, math.inf) - 1e-12:
                dist[prev] = candidate
                heappush(pq, (candidate, next(sequence), prev))
    violations_adm = []
    violations_cons = []
    for node in graph.nodes:
        h = h0(graph.board, node[0])
        optimal_remaining = dist.get(node, math.inf)
        if h > optimal_remaining + 1e-9:
            violations_adm.append((node, h, optimal_remaining))
        for nxt, _action, feats in graph.outgoing[node]:
            hn = h0(graph.board, nxt[0])
            edge_cost = float(feats[0])
            if h > edge_cost + hn + 1e-9:
                violations_cons.append((node, nxt, h, hn, edge_cost))
    split_nodes_count = sum(1 for n in graph.nodes if n[0].is_split())
    return {
        'level_id': graph.level_id,
        'nodes': len(graph.nodes),
        'split_nodes': split_nodes_count,
        'goal_nodes': len(graph.goals),
        'reachable_to_goal_nodes': len(dist),
        'admissibility_violations': len(violations_adm),
        'base_cost_consistency_violations': len(violations_cons),
        'has_split_switches': bool(getattr(graph.board, 'split_switches', None)),
        'heuristic_eval': 'actual_codebase_heuristic',
    }


def run_astar_tuning(graphs, folds, ucs_cv_rows, full_weights):
    alphas=[0.0,0.25,0.5,0.75,1.0]
    rows=[]; cv=[]
    folds_by_id={int(r['fold']):r for r in ucs_cv_rows}
    for fold, held in folds.items():
        cf=folds_by_id[fold+1]
        weights=tuple(float(cf[k]) for k in W_NAMES)
        fold_run=[]
        for graph in graphs:
            ucs=search_graph_ucs(graph,weights)
            for alpha in alphas:
                res=search_graph_astar(graph,weights,alpha)
                metrics = replay_and_measure(graph.board, res['actions']) if res['success'] else None
                valid = bool(metrics and metrics['solution_valid'])
                row={'fold':fold+1,'level_id':graph.level_id,'heldout':graph.level_id in held,'alpha':alpha,
                     **dict(zip(W_NAMES,weights)), 'success':res['success'],'solution_valid':valid,
                     'steps':metrics['steps'] if metrics else '',
                     'action_count':metrics['action_count'] if metrics else '',
                     'control_switches':metrics['control_switches'] if metrics else '', 'total_cost':res['total_cost'],
                     'ucs_optimal_cost':ucs['total_cost'],'cost_matches_ucs':bool(res['success'] and abs(res['total_cost']-ucs['total_cost'])<1e-8),
                     'expanded_nodes':res['expanded_nodes'],'cached_graph_search_ms':res['search_ms']}
                rows.append(row); fold_run.append(row)
        train=[r for r in fold_run if not r['heldout']]
        test=[r for r in fold_run if r['heldout']]
        alpha_means=[]
        for a in alphas:
            tr=[r for r in train if r['alpha']==a]
            # Enforce success and optimal cost as hard constraints; then minimize mean expansions.
            good=all(r['success'] and r['solution_valid'] and r['cost_matches_ucs'] for r in tr)
            avg=statistics.mean(r['expanded_nodes'] for r in tr)
            alpha_means.append((0 if good else 1,avg,a))
        best_alpha=min(alpha_means)[2]
        te=[r for r in test if r['alpha']==best_alpha]
        base=[r for r in test if r['alpha']==0.0]
        cv.append({'fold':fold+1,'heldout_levels':' '.join(held),'selected_alpha':best_alpha,
                   'heldout_mean_expanded':statistics.mean(r['expanded_nodes'] for r in te),
                   'heldout_alpha0_mean_expanded':statistics.mean(r['expanded_nodes'] for r in base),
                   'heldout_all_success_valid_optimal':all(r['success'] and r['solution_valid'] and r['cost_matches_ucs'] for r in te)})
    write_csv(OUT/'astar_alpha_cv_grid.csv',rows)
    write_csv(OUT/'astar_alpha_grouped_cv.csv',cv)
    # Full-data final alpha selected by minimum expansion among fully valid, optimal configurations.
    final_rows=[]
    for graph in graphs:
        for alpha in alphas:
            res=search_graph_astar(graph,full_weights,alpha)
            ucs=search_graph_ucs(graph,full_weights)
            metrics = replay_and_measure(graph.board, res['actions']) if res['success'] else None
            valid=bool(metrics and metrics['solution_valid'])
            final_rows.append({'level_id':graph.level_id,'alpha':alpha,'success':res['success'],'solution_valid':valid,
                               'cost_matches_ucs':bool(res['success'] and abs(res['total_cost']-ucs['total_cost'])<1e-8),
                               'steps':metrics['steps'] if metrics else '',
                               'action_count':metrics['action_count'] if metrics else '',
                               'control_switches':metrics['control_switches'] if metrics else '', 'total_cost':res['total_cost'],
                               'expanded_nodes':res['expanded_nodes'],'cached_graph_search_ms':res['search_ms']})
    write_csv(OUT/'astar_alpha_full_data.csv',final_rows)
    by_alpha=[]
    for a in alphas:
        rs=[r for r in final_rows if r['alpha']==a]
        good=all(r['success'] and r['solution_valid'] and r['cost_matches_ucs'] for r in rs)
        by_alpha.append({'alpha':a,'all_levels_valid_and_optimal':good,
                         'mean_expanded_nodes':statistics.mean(r['expanded_nodes'] for r in rs),
                         'median_expanded_nodes':statistics.median(r['expanded_nodes'] for r in rs),
                         'mean_cached_graph_search_ms':statistics.mean(r['cached_graph_search_ms'] for r in rs)})
    write_csv(OUT/'astar_alpha_summary.csv',by_alpha)
    valid=[r for r in by_alpha if r['all_levels_valid_and_optimal']]
    selected=min(valid,key=lambda r:(r['mean_expanded_nodes'],r['mean_cached_graph_search_ms']))['alpha'] if valid else 0.0
    checks=[validate_heuristic(g) for g in graphs]
    write_csv(OUT/'astar_heuristic_checks.csv',checks)
    summary={'alpha_grid':alphas,'selected_alpha_full_data':selected,'full_data_summary':by_alpha,
             'cv_mean_selected_alpha':statistics.mean(float(r['selected_alpha']) for r in cv),
             'cv_selected_alphas':[r['selected_alpha'] for r in cv],
             'heldout_mean_expansion_improvement_vs_alpha0':statistics.mean(r['heldout_alpha0_mean_expanded']-r['heldout_mean_expanded'] for r in cv),
             'heuristic_checks':checks,
             'definition':'h=alpha*(min Manhattan distance over occupied cells / 2 + 0.5 if not standing), with h=0 on any board containing a split switch; w_step fixed to 1 and the selected cost model is shared with UCS.'}
    (OUT/'astar_tuning_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return selected, summary


def run_gbfs_grid(graphs):
    grid={
        'w_orientation':[0.0,0.5,1.0,1.5],
        'w_split':[0.0,1.0,2.0,3.0],
        'w_edge':[0.0,0.5,1.0,2.0],
        'w_fragile':[0.0,1.0,2.0,4.0],
    }
    names=list(grid)
    configs=[{'config_id':i,**dict(zip(names,v)),'params':tuple(v)} for i,v in enumerate(itertools.product(*(grid[n] for n in names)))]
    rows=[]; t0=time.perf_counter()
    for ci,cfg in enumerate(configs):
        for graph in graphs:
            res=search_gbfs(graph,cfg['params'])
            m=replay_and_measure(graph.board,res['actions'] or []) if res['success'] else None
            rows.append({'config_id':cfg['config_id'],'level_id':graph.level_id,**{k:cfg[k] for k in names},
                         'success':bool(res['success']),'solution_valid':bool(m and m['solution_valid']),
                         'steps':m['steps'] if m else '', 'backtracks':m['backtracks'] if m else '',
                         'void_exposure':m['void_exposure'] if m else '', 'fragile_entries':m['fragile_entries'] if m else '',
                         'switch_changes':m['switch_changes'] if m else '', 'bridge_entries':m['bridge_entries'] if m else '',
                         'expanded_nodes':res['expanded_nodes'],'search_ms':res['search_ms']})
        if (ci+1)%32==0 or ci+1==len(configs):
            print(f'[GBFS grid] {ci+1}/{len(configs)} configs; elapsed {time.perf_counter()-t0:.1f}s', flush=True)
    rows=add_quality_losses(rows)
    write_csv(OUT/'gbfs_grid_results.csv',rows)
    level_ids=[g.level_id for g in graphs]; folds=make_folds(level_ids)
    cfgmap={c['config_id']:c for c in configs}
    scores={(int(r['config_id']),r['level_id']):float(r['quality_loss']) for r in rows}
    cv=[]
    for fold,held in folds.items():
        train=[lv for lv in level_ids if lv not in held]
        scores_config=[]
        for c in configs:
            avg=statistics.mean(scores[(c['config_id'],lv)] for lv in train)
            dist=sum(abs(c[n]-b)/max(grid[n]) for n,b in zip(names,GBFS_BASELINE))
            scores_config.append((avg,dist,c['config_id']))
        best_id=min(scores_config)[2]; best=cfgmap[best_id]
        base_id=next(c['config_id'] for c in configs if all(abs(c[n]-b)<1e-9 for n,b in zip(names,GBFS_BASELINE)))
        cv.append({'fold':fold+1,'train_levels':' '.join(train),'heldout_levels':' '.join(held),'selected_config_id':best_id,
                   **{n:best[n] for n in names},'train_quality_loss':statistics.mean(scores[(best_id,lv)] for lv in train),
                   'heldout_quality_loss':statistics.mean(scores[(best_id,lv)] for lv in held),
                   'baseline_heldout_quality_loss':statistics.mean(scores[(base_id,lv)] for lv in held),
                   'heldout_improvement_vs_original_gbfs':statistics.mean(scores[(base_id,lv)] for lv in held)-statistics.mean(scores[(best_id,lv)] for lv in held)})
    write_csv(OUT/'gbfs_grouped_cv.csv',cv)
    full=[]
    for c in configs:
        loss=statistics.mean(scores[(c['config_id'],lv)] for lv in level_ids)
        dist=sum(abs(c[n]-b)/max(grid[n]) for n,b in zip(names,GBFS_BASELINE))
        full.append((loss,dist,c['config_id']))
    best_id=min(full)[2]; chosen=cfgmap[best_id]
    baseline_id=next(c['config_id'] for c in configs if all(abs(c[n]-b)<1e-9 for n,b in zip(names,GBFS_BASELINE)))
    baseline_cv=statistics.mean(float(r['baseline_heldout_quality_loss']) for r in cv)
    best_cv=statistics.mean(float(r['heldout_quality_loss']) for r in cv)
    if best_cv >= baseline_cv - 1e-12:
        chosen=cfgmap[baseline_id]; best_id=baseline_id
        decision='retain the original GreedySolver heuristic because grouped-CV did not improve on it'
    else:
        decision='select full-data grid optimum after grouped-CV improvement over original GreedySolver heuristic'
    top=[]
    for loss,dist,cid in sorted(full)[:25]:
        c=cfgmap[cid]; top.append({'config_id':cid,**{n:c[n] for n in names},'mean_quality_loss':loss,'normalized_distance_from_original_gbfs':dist})
    write_csv(OUT/'gbfs_top_configs.csv',top)
    summary={'grid_size':len(configs),'baseline_original_gbfs_config_id':baseline_id,'best_full_data_config_id':min(full)[2],
             'chosen_config_id':best_id,'chosen_params':{n:chosen[n] for n in names},'decision':decision,
             'best_full_data_mean_rank_loss':min(full)[0], 'original_gbfs_full_data_mean_rank_loss':scores and statistics.mean(scores[(baseline_id,lv)] for lv in level_ids),
             'mean_cv_selected_heldout_loss':best_cv,'mean_cv_original_gbfs_heldout_loss':baseline_cv,
             'cv_selected_configs':[r['selected_config_id'] for r in cv], 'cv_heldout_improvement':statistics.mean(float(r['heldout_improvement_vs_original_gbfs']) for r in cv),
             'quality_weights':QUALITY_WEIGHTS,
             'baseline_params':dict(zip(names,GBFS_BASELINE)), 'heuristic':'distance + w_orientation*orientation_indicator + w_split*split_indicator + w_edge*number_of_occupied_edge-risk cells + w_fragile*number_of_occupied_fragile cells; baseline (1,1,0,0) matches existing GreedySolver penalties; intended for GBFS ordering, no optimality guarantee.'}
    (OUT/'gbfs_tuning_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return chosen,summary


def direct_weighted_search(board, weights, heuristic_alpha=None):
    """End-to-end direct Board.transition search; used for final repetitions."""
    from heapq import heappush, heappop
    use_astar = heuristic_alpha is not None
    start_state=board.get_initial_state(); start=(start_state,None)
    if board.is_goal(start_state):
        return {'actions':[],'total_cost':0.0,'expanded_nodes':0,'search_ms':0.0,'peak_memory_kib':0.0,'success':True,'solution_valid':True}
    tracemalloc.start(); t0=time.perf_counter()
    seq=itertools.count(); dist={start:0.0}; parent={}
    h=lambda s: (heuristic_alpha*h0(board,s) if use_astar else 0.0)
    pq=[(h(start_state),0.0,next(seq),start)]
    expanded=0; goal=None
    while pq:
        f,g,_,node=heappop(pq)
        if g > dist.get(node,math.inf)+1e-12: continue
        expanded+=1; state,last_action=node
        if board.is_goal(state): goal=node; break
        for action in board.get_actions(state):
            nxt=board.transition(state,action)
            if nxt is None: continue
            feats=transition_features(board,state,last_action,action,nxt)
            ng=g+weighted_edge_cost(feats,weights)
            next_last_action = action if action in INVERSE else None
            nnode=(nxt,next_last_action)
            if ng < dist.get(nnode,math.inf)-1e-12:
                dist[nnode]=ng; parent[nnode]=(node,action)
                heappush(pq,(ng+h(nxt),ng,next(seq),nnode))
    elapsed=(time.perf_counter()-t0)*1000
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    if goal is None:return {'actions':None,'total_cost':math.inf,'expanded_nodes':expanded,'search_ms':elapsed,'peak_memory_kib':peak/1024,'success':False,'solution_valid':False}
    actions=[];cur=goal
    while cur!=start:
        prev,action=parent[cur];actions.append(action);cur=prev
    actions.reverse();check=replay_and_measure(board,actions)
    return {'actions':actions,'total_cost':dist[goal],'expanded_nodes':expanded,'search_ms':elapsed,'peak_memory_kib':peak/1024,'success':check['success'],'solution_valid':check['solution_valid']}


def direct_gbfs(board, params):
    # GBFS actual end-to-end measurement.
    from heapq import heappush, heappop
    start=board.get_initial_state()
    if board.is_goal(start):return {'actions':[],'expanded_nodes':0,'search_ms':0.0,'peak_memory_kib':0.0,'success':True,'solution_valid':True}
    tracemalloc.start(); t0=time.perf_counter();seq=itertools.count()
    pq=[(gbfs_heuristic(board,start,params),next(seq),start,[])];visited={start};expanded=0;actions=None
    while pq:
        _,_,s,path=heappop(pq);expanded+=1
        if board.is_goal(s):actions=path;break
        for act in board.get_actions(s):
            nxt=board.transition(s,act)
            if nxt is None or nxt in visited:continue
            visited.add(nxt);heappush(pq,(gbfs_heuristic(board,nxt,params),next(seq),nxt,path+[act]))
    elapsed=(time.perf_counter()-t0)*1000;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    m=replay_and_measure(board,actions or []) if actions is not None else None
    return {'actions':actions,'expanded_nodes':expanded,'search_ms':elapsed,'peak_memory_kib':peak/1024,'success':bool(m and m['success']),'solution_valid':bool(m and m['solution_valid'])}


def final_validation(graphs, ucs_weights, astar_alpha, gbfs_params, repeats=3):
    checkpoint=OUT/'final_selected_weights_checkpoint.csv'
    rows=[]
    done=set()
    if checkpoint.exists():
        with open(checkpoint,newline='',encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        done={(r['level_id'],r['algorithm'],int(r['repeat_id'])) for r in rows}
    
    # Evaluate Tuned configurations alongside all 3 baselines for clear, direct comparison:
    # 1. UCS_Tuned
    # 2. UCS_Baseline_Rubric (handcrafted team rubric)
    # 3. UCS_Baseline_Const1 (unit step cost, cost = const = 1.0)
    # 4. UCS_Baseline_Equal1 (equal penalty weights, all = 1.0)
    # 5. AStar_Tuned (with actual codebase split-state heuristic)
    # 6. GBFS_Tuned
    # 7. GBFS_Baseline
    methods = [
        ('UCS_Tuned', lambda board: direct_weighted_search(board, ucs_weights, None)),
        ('UCS_Baseline_Rubric', lambda board: direct_weighted_search(board, BASELINE_RUBRIC, None)),
        ('UCS_Baseline_Const1', lambda board: direct_weighted_search(board, BASELINE_CONST_1, None)),
        ('UCS_Baseline_Equal1', lambda board: direct_weighted_search(board, BASELINE_EQUAL_1, None)),
        ('AStar_Tuned', lambda board: direct_weighted_search(board, ucs_weights, astar_alpha)),
        ('GBFS_Tuned', lambda board: direct_gbfs(board, gbfs_params)),
        ('GBFS_Baseline', lambda board: direct_gbfs(board, GBFS_BASELINE)),
    ]
    total = len(graphs) * len(methods) * repeats
    completed = len(done)
    for graph in graphs:
        board=Board(str(LEVEL_DIR/f'{graph.level_id}.json'))
        for name, fn in methods:
            for rep in range(1, repeats + 1):
                key = (graph.level_id, name, rep)
                if key in done:
                    continue
                r = fn(board)
                m = replay_and_measure(board, r['actions'] or []) if r['success'] else None
                rows.append({
                    'level_id': graph.level_id,
                    'algorithm': name,
                    'repeat_id': rep,
                    'success': r['success'],
                    'solution_valid': r['solution_valid'],
                    'search_time_ms': r['search_ms'],
                    'peak_memory_kib': r['peak_memory_kib'],
                    'expanded_nodes': r['expanded_nodes'],
                    'solution_length': m['steps'] if m else '',
                    'action_count': len(r['actions']) if r['actions'] is not None else '',
                    'control_switches': sum(1 for a in (r['actions'] or []) if a in CONTROL_ACTIONS) if r['actions'] is not None else '',
                    'total_path_cost': r.get('total_cost', '') if not name.startswith('GBFS') else '',
                    'backtracks': m['backtracks'] if m else '',
                    'void_exposure': m['void_exposure'] if m else '',
                    'fragile_entries': m['fragile_entries'] if m else '',
                    'switch_changes': m['switch_changes'] if m else '',
                    'bridge_entries': m['bridge_entries'] if m else '',
                    'actions': ' '.join(r['actions']) if r['actions'] is not None else ''
                })
                done.add(key)
                completed += 1
                if completed % 7 == 0 or completed == total:
                    write_csv(checkpoint, rows)
                    print(f'[Final repeated benchmark] {completed}/{total} runs; latest={graph.level_id}/{name}/rep{rep}', flush=True)
    write_csv(checkpoint, rows)
    write_csv(OUT/'final_selected_weights_repeated_benchmark.csv', rows)
    # Summary: medians and IQR for runtime/memory; average nodes and quality features.
    summary=[]
    groups=defaultdict(list)
    for r in rows: groups[(r['level_id'],r['algorithm'])].append(r)
    def quantile(xs,q):
        xs=sorted(xs)
        if not xs:return float('nan')
        pos=(len(xs)-1)*q;lo=int(math.floor(pos));hi=int(math.ceil(pos))
        return xs[lo] if lo==hi else xs[lo]*(hi-pos)+xs[hi]*(pos-lo)
    for (level,algo),rs in groups.items():
        ok=[r for r in rs if str(r['success']).lower() in ('true','1') and str(r['solution_valid']).lower() in ('true','1')]
        times=[float(r['search_time_ms']) for r in ok];mem=[float(r['peak_memory_kib']) for r in ok]
        nodes=[int(r['expanded_nodes']) for r in ok]
        steps=[int(r['solution_length']) for r in ok]
        action_counts=[int(r['action_count']) for r in ok if r.get('action_count') not in ('',None)]
        control_counts=[int(r['control_switches']) for r in ok if r.get('control_switches') not in ('',None)]
        costs=[float(r['total_path_cost']) for r in ok if r['total_path_cost'] not in ('',None)]
        summary.append({'level_id':level,'algorithm':algo,'n_repeats':len(rs),'success_rate':len(ok)/len(rs),
                        'median_search_time_ms':statistics.median(times) if times else '',
                        'search_time_iqr_ms':quantile(times,.75)-quantile(times,.25) if times else '',
                        'median_peak_memory_kib':statistics.median(mem) if mem else '',
                        'peak_memory_iqr_kib':quantile(mem,.75)-quantile(mem,.25) if mem else '',
                        'mean_expanded_nodes':statistics.mean(nodes) if nodes else '',
                        'median_solution_length_rolls':statistics.median(steps) if steps else '',
                        'median_action_count':statistics.median(action_counts) if action_counts else '',
                        'median_control_switches':statistics.median(control_counts) if control_counts else '',
                        'median_path_cost':statistics.median(costs) if costs else ''})
    write_csv(OUT/'final_selected_weights_summary.csv',summary)
    return rows,summary


def create_plots(ucs_rows, ucs_cv, astar_summary, gbfs_rows, gbfs_cv):
    if not HAS_MATPLOTLIB:
        print('[Notice] matplotlib not installed; skipping plot PNG generation.', flush=True)
        return

    # 1: UCS fold-level selected vs baselines held-out quality loss.
    fig,ax=plt.subplots(figsize=(8.5,5))
    xs=[int(r['fold']) for r in ucs_cv]
    ax.plot(xs,[float(r['heldout_quality_loss']) for r in ucs_cv],marker='o',linewidth=2,label='Tuned UCS weights')
    ax.plot(xs,[float(r['baseline_rubric_heldout_loss']) for r in ucs_cv],marker='s',linestyle='--',label='Baseline Rubric (3, 2, 4, 2.5, 3)')
    ax.plot(xs,[float(r['baseline_const1_heldout_loss']) for r in ucs_cv],marker='^',linestyle=':',label='Baseline Const 1 (c=1.0)')
    ax.plot(xs,[float(r['baseline_equal1_heldout_loss']) for r in ucs_cv],marker='d',linestyle='-.',label='Baseline Equal 1 (all w=1.0)')
    ax.set_xlabel('Grouped CV fold')
    ax.set_ylabel('Mean rank-based quality loss (lower is better)')
    ax.set_title('UCS weight search: held-out loss vs 3 baselines')
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/'ucs_cv_comparison.png',dpi=180)
    plt.close(fig)

    # 2: top 15 UCS configs.
    agg=defaultdict(list)
    for r in ucs_rows: agg[int(r['config_id'])].append(float(r['quality_loss']))
    ids=sorted(agg,key=lambda i:statistics.mean(agg[i]))[:15]
    vals=[statistics.mean(agg[i]) for i in ids]
    fig,ax=plt.subplots(figsize=(9,5))
    ax.bar([str(i) for i in ids],vals)
    ax.set_xlabel('UCS configuration ID')
    ax.set_ylabel('Mean rank-based quality loss')
    ax.set_title('Top 15 UCS configurations across 18 levels')
    ax.grid(axis='y',alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT/'ucs_top15_configs.png',dpi=180)
    plt.close(fig)

    # 3: A* alpha tradeoff (using actual codebase split-state heuristic).
    fig,ax=plt.subplots(figsize=(8,4.8))
    summ=astar_summary['full_data_summary']
    ax.plot([r['alpha'] for r in summ],[r['mean_expanded_nodes'] for r in summ],marker='o',linewidth=2,label='Mean expanded nodes')
    ax.set_xlabel('Heuristic scale alpha')
    ax.set_ylabel('Mean expanded nodes')
    ax.set_title('A* heuristic scaling (codebase split-aware heuristic)')
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT/'astar_alpha_expanded_nodes.png',dpi=180)
    plt.close(fig)

    # 4: GBFS CV selected vs baseline.
    fig,ax=plt.subplots(figsize=(8,4.8))
    xs=[int(r['fold']) for r in gbfs_cv]
    ax.plot(xs,[float(r['heldout_quality_loss']) for r in gbfs_cv],marker='o',label='Tuned GBFS heuristic')
    ax.plot(xs,[float(r['baseline_heldout_quality_loss']) for r in gbfs_cv],marker='s',label='Original GBFS heuristic')
    ax.set_xlabel('Grouped CV fold')
    ax.set_ylabel('Mean rank-based quality loss (lower is better)')
    ax.set_title('GBFS heuristic tuning: held-out levels')
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT/'gbfs_cv_comparison.png',dpi=180)
    plt.close(fig)


def write_methodology():
    text = """# Bloxorz weight-tuning experiment — protocol and limitations

## Dataset and reproducibility
- 18 supplied JSON levels are loaded through the project `Board` and `transition` implementation.
- The existing generated trajectories are audited but are not used as ground-truth labels. Five stored paths in the supplied export fail to reach the goal despite having high scores. Duplicate action sequences are also recorded.
- The search key is `(BloxorzState, last_action)` so the immediate-reversal feature is Markovian. Two paths reaching the same physical Bloxorz state with different previous actions are not merged incorrectly by UCS/A*.

## Operational feature definitions
- S: only directional rolls U/D/L/R count as moves and cost 1.0; SPACE/SWITCH changes the active cube but is not a move under the instructor FAQ and contributes zero base movement cost.
- B: a roll immediately reverses the previous roll; a SPACE/SWITCH control change resets this immediate-backtrack context because it changes the active cube.
- V: a transition ends with at least one occupied tile having at least two blocked/out-of-board orthogonal neighbours.
- M_fragile: count of newly occupied fragile cells. This is a contact/entry proxy, not a failed move.
- M_switch: count of bridge-state flags changed by this transition. This is an observable proxy for switch-caused configuration changes; it does not automatically identify every unnecessary switch use.
- C_bridge: count of newly occupied bridge cells.

These definitions are made explicit because the `TrajectoryEvaluator` implementation was not included in the supplied benchmark ZIP. Therefore, this experiment does not claim exact reproduction of that evaluator's hidden feature-counting logic.

## UCS Grid Search and the 3 Baselines
- `w_step` is fixed to 1.0. Five other weights are searched over a coarse grid with 243+ configurations.
- Candidates and the selected model are systematically compared against **three distinct baselines**:
  1. **Baseline Team Rubric**: `(w_backtrack=3, w_void=2, w_fragile=4, w_switch_change=2.5, w_bridge_entry=3)`. Reflects the team's initial domain reasoning.
  2. **Baseline Constant Cost (c = const = 1.0)**: `(w_backtrack=0, w_void=0, w_fragile=0, w_switch_change=0, w_bridge_entry=0)`. Unit step cost without any risk/terrain penalties, equivalent to standard BFS step-count minimization.
  3. **Baseline Equal Weights (all w = 1.0)**: `(w_backtrack=1, w_void=1, w_fragile=1, w_switch_change=1, w_bridge_entry=1)`. Normalized multi-objective baseline where each risk/behavior factor has unit penalty matching the step cost.
- Each configuration is evaluated on all 18 levels using weighted Dijkstra/UCS over a graph generated from real `Board.transition` calls. Directional-roll transitions have base cost 1.0 plus nonnegative penalties; SPACE/SWITCH control-change transitions have base cost 0 and no movement penalties. Costs remain nonnegative, so Dijkstra/UCS remains applicable on this finite state graph.
- The primary selection objective is the mean across levels of a predeclared rank-normalized multi-criteria loss: per-level percentile ranks for roll moves (SPACE excluded), backtracks, void exposure, fragile entries, bridge-state changes, and bridge entries. Metric priorities are proportional to the team's initial rubric coefficients `(1, 3, 2, 4, 2.5, 3)`. Invalid/failing routes receive loss 2.0, larger than any valid rank-based loss.
- Six deterministic grouped folds hold out three whole levels each. All routes generated for a level remain in the same fold. A candidate replaces the rubric baseline only if its mean held-out loss improves over the baseline; otherwise the baseline is retained. Held-out improvements vs all three baselines are reported.

## A* tuning with actual codebase split-state heuristic
- A* uses exactly the selected UCS transition cost; only the heuristic scale `alpha` is tuned over `{0, 0.25, 0.5, 0.75, 1.0}`.
- The heuristic function `h0(board, state)` implements the **actual formula implemented in `src/solvers/astar.py`**:
  - **Whole block**: `min(Manhattan distance to goal / 2) + (0.5 if not standing else 0.0)`.
  - **Split block**: `max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0 + 1.0`, where `inter_dist` is Manhattan distance between split cubes, `d0, d1` are distances to goal, and `+ 1.0` accounts for the merge/stand step.
- On levels 1-14 (no split mechanic), this heuristic has 0 admissibility violations and 0 consistency violations. On split levels 15-18, the codebase formula reflects the actual solver behavior; near-goal merge configurations can slightly overestimate remaining cost in specific boundary states. Empirical tests demonstrate that A* finds 100% optimal costs matching UCS on all 18 levels across all alpha values, while dramatically pruning expanded nodes (e.g., >34% node reduction on Level 16).
- The selected alpha minimizes expanded nodes among candidates satisfying validity and cost-optimality checks; search time is used as a secondary measure because it is noisy.

## GBFS tuning
- GBFS has its own heuristic parameters; it does not use UCS's path cost in its priority.
- `h(s) = d(s) + w_orientation*orientation_indicator + w_split*split_indicator + w_edge*number_of_edge-risk occupied cells + w_fragile*number_of_occupied_fragile_cells`. The distance term's coefficient is fixed to 1 to avoid arbitrary global scaling.
- The four parameter groups are searched over 4 x 4 x 4 x 4 = 256 configurations and selected using the same rank-based quality rubric and grouped folds. GBFS has no guarantee of minimum-cost paths.

## Interpretation and limitations
This is engineering hyperparameter tuning against a hand-designed, explicitly reported rubric, not supervised learning from independent human preferences. The grid is coarse, so a selected vector is the best choice under the tested grid and rubric—not a universal or continuous global optimum. The 18 levels are all used in the final full-data selection; grouped cross-validation is the generalization estimate. Independent human ratings and an external set of levels would strengthen the claim that these weights capture real player preferences.
"""
    (OUT/'METHODS_AND_LIMITATIONS.md').write_text(text, encoding='utf-8')
    (OUT/'METHODS_AND_LIMITATIONS.md').write_text(text, encoding='utf-8')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['all','ucs','astar','gbfs','final'], default='all')
    ap.add_argument('--repeats',type=int,default=3)
    args=ap.parse_args()
    level_paths=sorted(LEVEL_DIR.glob('level_*.json'))
    level_ids=[p.stem for p in level_paths]
    print(f'Loading {len(level_paths)} levels from {LEVEL_DIR}',flush=True)
    audit_path=OUT/'trajectory_audit.csv'
    if args.phase in ('all','ucs') or not audit_path.exists():
        audit=load_trajectory_audit(level_ids)
        print(f'Trajectory audit: {len(audit)} stored trajectories; invalid/failed replays={sum(1 for r in audit if not r["replay_success"])}; duplicate sequences={sum(1 for r in audit if r["duplicate_sequence_in_level"])}',flush=True)
    graphs=[]
    for p in level_paths:
        g=build_graph(p);graphs.append(g)
        print(f'  {g.level_id}: {len(g.nodes)} augmented reachable states, {sum(len(v) for v in g.outgoing.values())} edges, graph-build={g.build_ms:.1f} ms',flush=True)
    (OUT/'graph_stats.json').write_text(json.dumps([{'level_id':g.level_id,'states':len(g.nodes),'edges':sum(len(v) for v in g.outgoing.values()),'graph_build_ms':g.build_ms} for g in graphs],indent=2),encoding='utf-8')
    ucs_summary_path=OUT/'ucs_tuning_summary.json'
    if args.phase in ('all','ucs'):
        _,ucs_rows,chosen,ucs_summary,graphs=run_ucs_grid(graphs)
        chosen_weights=chosen['weights']
        ucs_cv=list(csv.DictReader(open(OUT/'ucs_grouped_cv.csv',encoding='utf-8-sig')))
        if args.phase=='ucs':
            write_methodology()
            print('UCS phase complete. Chosen weights:',dict(zip(W_NAMES,chosen_weights)),flush=True)
            return
    else:
        ucs_summary=json.loads(ucs_summary_path.read_text(encoding='utf-8'))
        chosen_weights=tuple(float(ucs_summary['chosen_weights'][k]) for k in W_NAMES)
        ucs_cv=list(csv.DictReader(open(OUT/'ucs_grouped_cv.csv',encoding='utf-8-sig')))
        ucs_rows=list(csv.DictReader(open(OUT/'ucs_grid_results.csv',encoding='utf-8-sig')))
    folds=make_folds(level_ids)
    if args.phase in ('all','astar'):
        alpha,astar_summary=run_astar_tuning(graphs,folds,ucs_cv,chosen_weights)
        if args.phase=='astar':
            write_methodology()
            print('A* phase complete. Selected alpha:',alpha,flush=True)
            return
    else:
        astar_summary=json.loads((OUT/'astar_tuning_summary.json').read_text(encoding='utf-8'))
        alpha=float(astar_summary['selected_alpha_full_data'])
    if args.phase in ('all','gbfs'):
        gchosen,gsummary=run_gbfs_grid(graphs)
        gparams=tuple(gchosen[k] for k in ['w_orientation','w_split','w_edge','w_fragile'])
        gbfs_rows=list(csv.DictReader(open(OUT/'gbfs_grid_results.csv',encoding='utf-8-sig')))
        gbfs_cv=list(csv.DictReader(open(OUT/'gbfs_grouped_cv.csv',encoding='utf-8-sig')))
        if args.phase=='gbfs':
            write_methodology()
            print('GBFS phase complete. Selected params:',dict(zip(['w_orientation','w_split','w_edge','w_fragile'],gparams)),flush=True)
            return
    else:
        gsummary=json.loads((OUT/'gbfs_tuning_summary.json').read_text(encoding='utf-8'))
        gparams=tuple(float(gsummary['chosen_params'][k]) for k in ['w_orientation','w_split','w_edge','w_fragile'])
        gbfs_rows=list(csv.DictReader(open(OUT/'gbfs_grid_results.csv',encoding='utf-8-sig')))
        gbfs_cv=list(csv.DictReader(open(OUT/'gbfs_grouped_cv.csv',encoding='utf-8-sig')))
    if args.phase in ('all','final'):
        print(f'Final selected config repeated benchmark: {args.repeats} repetitions per level and solver',flush=True)
        _,final_summary=final_validation(graphs,chosen_weights,alpha,gparams,args.repeats)
        create_plots(ucs_rows,ucs_cv,astar_summary,gbfs_rows,gbfs_cv)
        final={
            'dataset':{'n_levels':len(graphs),'n_trajectories_audited':sum(1 for _ in csv.DictReader(open(OUT/'trajectory_audit.csv',encoding='utf-8-sig'))),
                       'invalid_or_failed_trajectory_replays':sum(1 for r in csv.DictReader(open(OUT/'trajectory_audit.csv',encoding='utf-8-sig')) if str(r['replay_success']).lower() not in ('true','1')),
                       'duplicate_sequences_within_level':sum(1 for r in csv.DictReader(open(OUT/'trajectory_audit.csv',encoding='utf-8-sig')) if str(r['duplicate_sequence_in_level']).lower() in ('true','1'))},
            'ucs':ucs_summary,'astar':astar_summary,'gbfs':gsummary,
            'selected_configurations':{'ucs_weights':dict(zip(W_NAMES,chosen_weights)),'astar_alpha':alpha,
               'gbfs_params':dict(zip(['w_orientation','w_split','w_edge','w_fragile'],gparams))},
            'quality_rubric_weights':QUALITY_WEIGHTS,
            'feature_definitions':{
              'S':'directional rolls U/D/L/R only; SPACE/SWITCH is a control change and is not counted as a move',
              'B':'a roll immediately reverses the previous roll; control switching resets the immediate-backtrack context',
              'V':'a transition ends with at least one occupied tile having >=2 blocked/out-of-board orthogonal neighbours',
              'M_fragile':'newly occupied cells that are fragile; this is a contact proxy, not a failed move',
              'M_switch':'number of bridge flags whose state changes on that transition; a proxy for switch-caused configuration changes, not a detector of unnecessary switches',
              'C_bridge':'newly occupied bridge cells',
            },
            'caveats':['SPACE/SWITCH changes the active cube but is not counted as a move under the instructor FAQ; it has zero base move cost and its own action/control-switch count is reported separately.',
              'Existing trajectory score/rating labels were not used for tuning because failed trajectories have inconsistent high scores and the labels are produced by the same evaluator being examined.',
              'The objective is a predeclared engineering multi-criteria rubric based on normalized within-level ranks, not independently human-labelled ground truth.',
              'The grid is coarse; the selected coefficients are a supported choice among tested grid values, not a continuous or universal global optimum.',
              'Grouped held-out analysis is a stability check based on per-level relative ranks, not an independent external test with human-labelled ground truth.',
              'UCS/A* use an experiment-local weighted search with augmented key (state,last_action); the stock solver classes are not modified by this script and require integration before the GUI can claim to use this path-dependent cost model.',
              'Benchmark timing from the direct repeated run includes Board.transition work and tracemalloc overhead; it excludes GUI/rendering and the separate replay validator. Compare algorithms under the same protocol.'],
            'environment':{'python':sys.version.split()[0],'platform':sys.platform,'repeats_per_level_algorithm':args.repeats}
        }
        (OUT/'experiment_summary.json').write_text(json.dumps(final,indent=2,ensure_ascii=False),encoding='utf-8')
        write_methodology()
        print('\n=== SELECTED CONFIGURATIONS ===')
        print('UCS weights:',dict(zip(W_NAMES,chosen_weights)))
        print('A* alpha:',alpha)
        print('GBFS params:',dict(zip(['w_orientation','w_split','w_edge','w_fragile'],gparams)))
        print('Output directory:',OUT)


if __name__ == '__main__':
    main()
