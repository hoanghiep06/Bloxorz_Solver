"""
Script tu dong sinh 10 duong di (tu toi uu den te nhat) cho moi man choi
va danh gia xep hang bang TrajectoryEvaluator (Barem cham diem Bloxorz).
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Tuple
from collections import deque

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.solvers.bfs import BFSSolver
from src.solvers.astar import AStarSolver
from src.solvers.greedy import GreedySolver
from src.solvers.dfs import DFSSolver
from src.solvers.UCS_Algorithm.ucs import UCSSolver
from src.solvers.UCS_Algorithm.cost_functions import RiskSafetyCost, PhysicsBasedCost
from src.evaluation.evaluator import TrajectoryEvaluator

# Huong di chuyen
DIRECTIONS = ['U', 'D', 'L', 'R']

def custom_bfs(board: Board, move_order: List[str]) -> List[str]:
    start_state = board.get_initial_state()
    queue = deque([(start_state, [])])
    visited = {start_state}
    while queue:
        st, path = queue.popleft()
        if board.is_goal(st):
            return path
        actions = board.get_actions(st) if hasattr(board, 'get_actions') else move_order
        ordered_actions = [m for m in move_order if m in actions] + [m for m in actions if m not in move_order]
        for m in ordered_actions:
            nxt = board.transition(st, m)
            if nxt and nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [m]))
    return []

def custom_dfs(board: Board, move_order: List[str], max_depth: int = 50, max_iterations: int = 4000) -> List[str]:
    start_state = board.get_initial_state()
    stack = [(start_state, [], {start_state})]
    best_path = None
    iters = 0
    while stack and iters < max_iterations:
        iters += 1
        st, path, visited = stack.pop()
        if board.is_goal(st):
            if best_path is None or len(path) > len(best_path):
                best_path = path
                if len(path) >= 25:
                    return path
            continue
        if len(path) >= max_depth:
            continue
        for m in move_order:
            nxt = board.transition(st, m)
            if nxt and nxt not in visited:
                new_visited = set(visited)
                new_visited.add(nxt)
                stack.append((nxt, path + [m], new_visited))
    return best_path or []

def generate_perturbed_path(board: Board, perturb_steps: int = 2) -> List[str]:
    """Mo phong nguoi choi di lung tung vai buoc roi moi tim duong den dich."""
    state = board.get_initial_state()
    lead_path = []
    import random
    rng = random.Random(42 + perturb_steps)
    
    for _ in range(perturb_steps):
        valid_moves = []
        for m in DIRECTIONS:
            nxt = board.transition(state, m)
            if nxt is not None:
                valid_moves.append((m, nxt))
        if not valid_moves:
            break
        chosen_m, state = rng.choice(valid_moves)
        lead_path.append(chosen_m)
        if board.is_goal(state):
            return lead_path

    # Tu state hien tai, tim duong tiep toi Goal bang BFS
    queue = deque([(state, [])])
    visited = {state}
    tail_path = None
    while queue:
        st, p = queue.popleft()
        if board.is_goal(st):
            tail_path = p
            break
        for m in ['U', 'R', 'D', 'L']:
            nxt = board.transition(st, m)
            if nxt and nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, p + [m]))

    if tail_path is not None:
        return lead_path + tail_path
    return lead_path

def generate_10_trajectories(level_path: str) -> List[Dict[str, Any]]:
    board = Board(level_path)
    with open(level_path, 'r', encoding='utf-8') as f:
        level_data = json.load(f)

    raw_candidates = []

    # 1. BFS chuan (Toi uu tuyet doi)
    sol_bfs = BFSSolver(board).solve()
    if sol_bfs.success:
        raw_candidates.append(("P1_BFS_Standard", sol_bfs.actions))

    # 2. A* Manhattan
    try:
        sol_astar = AStarSolver(board).solve()
        if sol_astar.success and sol_astar.actions != raw_candidates[0][1]:
            raw_candidates.append(("P2_AStar_Direct", sol_astar.actions))
    except Exception:
        pass

    # 3. BFS dao huong (Nhanh phu toi uu)
    sol_bfs_rev = custom_bfs(board, ['D', 'L', 'U', 'R'])
    if sol_bfs_rev:
        raw_candidates.append(("P3_BFS_Alternative", sol_bfs_rev))

    # 4. UCS Safe (Ne mep vuc)
    try:
        sol_ucs = UCSSolver(board, cost_function=RiskSafetyCost()).solve()
        if sol_ucs.success:
            raw_candidates.append(("P4_UCS_SafetyFirst", sol_ucs.actions))
    except Exception:
        pass

    # 5. Greedy Best-First Search
    try:
        sol_greedy = GreedySolver(board).solve()
        if sol_greedy.success:
            raw_candidates.append(("P5_Greedy_Direct", sol_greedy.actions))
    except Exception:
        pass

    # 6. BFS huong R-U-L-D
    sol_bfs_rul = custom_bfs(board, ['R', 'U', 'L', 'D'])
    if sol_bfs_rul:
        raw_candidates.append(("P6_BFS_Horizontal", sol_bfs_rul))

    # 7. Mo phong di lung tung 2 buoc
    p7 = generate_perturbed_path(board, perturb_steps=2)
    if p7:
        raw_candidates.append(("P7_Hesitation_2Steps", p7))

    # 8. Mo phong di lung tung 4 buoc
    p8 = generate_perturbed_path(board, perturb_steps=4)
    if p8:
        raw_candidates.append(("P8_Hesitation_4Steps", p8))

    # 9. DFS gioi han do sau
    try:
        p9 = custom_dfs(board, ['D', 'R', 'U', 'L'], max_depth=45)
        if p9:
            raw_candidates.append(("P9_DFS_Suboptimal", p9))
    except Exception:
        pass

    # 10. DFS di sau vao ngo cut
    try:
        p10 = custom_dfs(board, ['L', 'D', 'R', 'U'], max_depth=70)
        if p10:
            raw_candidates.append(("P10_DFS_DeepWander", p10))
    except Exception:
        pass

    # Neu chua du 10 candidate, bo sung bang cach tang perturb
    step_add = 6
    while len(raw_candidates) < 10:
        extra_p = generate_perturbed_path(board, perturb_steps=step_add)
        if extra_p:
            raw_candidates.append((f"P{len(raw_candidates)+1}_Wander_{step_add}Steps", extra_p))
        step_add += 2

    # Gioi han lay dung 10 duong
    candidates = raw_candidates[:10]

    # Cham diem voi Evaluator
    evaluator = TrajectoryEvaluator()

    # Tim optimal penalty tu loi giai ngan nhat
    optimal_penalty = 999.0
    for name, acts in candidates:
        rep = evaluator.evaluate(board, acts, optimal_penalty=None, level_data=level_data)
        if rep.success and rep.penalty_cost < optimal_penalty:
            optimal_penalty = rep.penalty_cost

    # Danh gia va xep hang
    results = []
    for name, acts in candidates:
        report = evaluator.evaluate(board, acts, optimal_penalty=optimal_penalty, level_data=level_data)
        results.append({
            "name": name,
            "report": report
        })

    # Sap xep tu Diem cao xuong Diem thap
    results.sort(key=lambda x: x["report"].score, reverse=True)
    return results

def print_and_save_report(level_path: str, results: List[Dict[str, Any]]):
    base_name = os.path.basename(level_path).replace('.json', '')
    os.makedirs('trajectories', exist_ok=True)
    out_json = f'trajectories/{base_name}_trajectories.json'

    print("\n" + "=" * 90)
    print(f" BANG DANH GIA 10 DUONG DI — {base_name.upper()}")
    print("=" * 90)
    print(f"{'Hang':<5} | {'Ten loi giai':<22} | {'Buoc':<5} | {'Lui':<4} | {'Vuc':<4} | {'Loi':<4} | {'Penalty':<7} | {'Diem':<6} | {'Xep loai'}")
    print("-" * 90)

    save_data = {
        "level": base_name,
        "total_trajectories": len(results),
        "trajectories": []
    }

    for rank, item in enumerate(results, start=1):
        name = item["name"]
        rep = item["report"]
        errs = rep.switch_inefficiencies + rep.fragile_hesitations + rep.bridge_crossings
        print(f"{rank:<5} | {name:<22} | {rep.steps:<5} | {rep.backtracks:<4} | {rep.void_exposure:<4} | {errs:<4} | {rep.penalty_cost:<7.1f} | {rep.score:<6.1f} | {rep.rating}")
        
        save_data["trajectories"].append({
            "rank": rank,
            "name": name,
            **rep.to_dict()
        })

    print("=" * 90)

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f">> Da luu chi tiet 10 duong di vao file: {out_json}\n")


def main():
    parser = argparse.ArgumentParser(description="Sinh 10 duong di va cham diem voi TrajectoryEvaluator")
    parser.add_argument("--level", type=str, default="levels/level_01.json", help="Duong dan den file map json")
    parser.add_argument("--all", action="store_true", help="Chay toan bo cac man trong levels/")
    args = parser.parse_args()

    if args.all:
        import glob
        all_levels = sorted(glob.glob('levels/level_*.json'))
        for lvl in all_levels:
            res = generate_10_trajectories(lvl)
            print_and_save_report(lvl, res)
    else:
        res = generate_10_trajectories(args.level)
        print_and_save_report(args.level, res)

if __name__ == "__main__":
    main()
