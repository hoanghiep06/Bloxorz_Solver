"""
BENCHMARK RUNNER CHO TOAN BO 6 THUAT TOAN BLOXORZ TREN 18 MAN CHOI
D- -n: Bloxorz AI Solver (AI - Project 1 / LAB01)
Nh-m ph- tr-ch: Nh-m 2 - Benchmarking & --nh gi- (Huy & Phong)

Thu-t to-n -o l--ng:
1. BFS (BFSSolver)
2. DFS (DFSSolver)
3. IDS (IDSSolver)
4. UCS (UCSSolver)
5. Greedy (GreedySolver)
6. A* (AStarSolver)

Xu-t k-t qu-: benchmark_results.csv
"""

import os
import sys
import json
import time
import argparse
import re
from typing import List, Dict, Any, Optional
import concurrent.futures

# Reconfigure stdout to UTF-8
sys.stdout.reconfigure(encoding="utf-8")

from src.core.board import Board
from src.solvers.bfs import BFSSolver
from src.solvers.dfs import DFSSolver
from src.solvers.ids import IDSSolver
from src.solvers.ucs import UCSSolver
from src.solvers.greedy import GreedySolver
from src.solvers.astar import AStarSolver
from src.evaluation.evaluator import TrajectoryEvaluator


SOLVER_CLASSES = [
    ("BFS", BFSSolver),
    ("AStar", AStarSolver),
    ("Greedy", GreedySolver),
    ("UCS", UCSSolver),
    ("DFS", DFSSolver),
    ("IDS", IDSSolver),
]


def calc_effective_branching_factor(N: int, S: int) -> float:
    if S <= 0 or N <= 0 or N <= S:
        return 1.0
    low, high = 1.0, 4.0
    for _ in range(40):
        mid = (low + high) / 2.0
        try:
            if abs(mid - 1.0) < 1e-9:
                total = float(S)
            else:
                total = (mid ** (S + 1) - mid) / (mid - 1.0)
        except OverflowError:
            total = float('inf')
        if total < N:
            low = mid
        else:
            high = mid
    return round(mid, 3)


def run_solver_with_timeout(solver_cls, board: Board, timeout_sec: float):
    """Ch-y solver v-i c- ch- an to-n timeout b-ng ThreadPoolExecutor."""
    solver = solver_cls(board)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(solver.solve)
        try:
            return future.result(timeout=timeout_sec), None
        except concurrent.futures.TimeoutError:
            return None, "TIMEOUT"
        except Exception as e:
            return None, f"ERROR: {str(e)}"


def run_benchmark(levels_dir: str = "levels", output_csv: str = "benchmark_results.csv", timeout_sec: float = 15.0, target_levels: Optional[List[int]] = None):
    # 1. T-m t-t c- c-c file level
    all_files = [f for f in os.listdir(levels_dir) if f.startswith("level_") and f.endswith(".json")]
    all_files.sort(key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 0)

    if target_levels:
        selected_files = []
        for f in all_files:
            match = re.search(r"\d+", f)
            if match and int(match.group()) in target_levels:
                selected_files.append(f)
        all_files = selected_files

    print(f"==========================================================================================")
    print(f"               BLOXORZ AI SOLVER - AUTOMATED BENCHMARK SUITE")
    print(f"==========================================================================================")
    print(f"  - S- l--ng m-n ch-i: {len(all_files)}")
    print(f"  - Thu-t to-n ki-m th- (6): {', '.join([name for name, _ in SOLVER_CLASSES])}")
    print(f"  - Ng--ng Timeout m-i thu-t to-n: {timeout_sec}s")
    print(f"  - File xu-t k-t qu-: {output_csv}")
    print(f"==========================================================================================\n")

    evaluator = TrajectoryEvaluator()
    results: List[Dict[str, Any]] = []

    # Kh-i t-o CSV v-i header
    csv_headers = [
        "level", "solver", "status", "runtime_ms", "memory_kib",
        "expanded_nodes", "steps", "backtracks", "void_hazards",
        "penalty", "score", "penetrance_pct", "subopt_ratio", "branching_factor"
    ]

    total_benchmarks = len(all_files) * len(SOLVER_CLASSES)
    current_idx = 0

    start_benchmark_time = time.perf_counter()

    for file_name in all_files:
        level_id = os.path.splitext(file_name)[0]
        level_path = os.path.join(levels_dir, file_name)

        with open(level_path, "r", encoding="utf-8") as f:
            level_data = json.load(f)

        board_baseline = Board(level_path)

        # 1. Ch-y BFS l-m m-c chu-n t-i -u
        bfs_solver = BFSSolver(board_baseline)
        bfs_res = bfs_solver.solve()
        if not bfs_res or not bfs_res.actions:
            print(f"[!] C-NH B-O: M-n {level_id} kh-ng gi-i ---c b-ng BFS! B- qua m-n n-y.")
            continue

        optimal_steps = len(bfs_res.actions)
        report_optimal = evaluator.evaluate(board_baseline, bfs_res.actions, level_data=level_data)
        optimal_penalty = report_optimal.penalty_cost

        print(f"------------------------------------------------------------------------------------------")
        print(f"- M-N CH-I: {level_id.upper()} (M-c t-i -u S_min = {optimal_steps} b--c, Penalty_min = {optimal_penalty:.1f})")
        print(f"------------------------------------------------------------------------------------------")
        print(f"{'Thu-t to-n':<10} | {'Tr-ng th-i':<8} | {'Th-i gian (ms)':<14} | {'RAM (KiB)':<10} | {'Nodes':<7} | {'B--c':<5} | {'Score':<6} | {'P (%)':<7} | {'b*':<6}")
        print(f"-" * 90)

        for solver_name, solver_cls in SOLVER_CLASSES:
            current_idx += 1
            board = Board(level_path)

            res, error_flag = run_solver_with_timeout(solver_cls, board, timeout_sec)

            if error_flag == "TIMEOUT":
                status = "TIMEOUT"
                runtime_ms = timeout_sec * 1000.0
                memory_kib = 0.0
                expanded_nodes = 0
                steps = 0
                backtracks = 0
                void_hazards = 0
                penalty = 999.0
                score = 0.0
                penetrance_pct = 0.0
                subopt_ratio = 0.0
                branching_factor = 4.0
            elif res is None or not res.success or res.actions is None:
                status = "FAIL"
                runtime_ms = round(res.time_taken * 1000.0, 2) if res else 0.0
                memory_kib = round(res.peak_memory, 2) if res else 0.0
                expanded_nodes = res.expanded_nodes if res else 0
                steps = 0
                backtracks = 0
                void_hazards = 0
                penalty = 999.0
                score = 0.0
                penetrance_pct = 0.0
                subopt_ratio = 0.0
                branching_factor = 4.0
            else:
                status = "SUCCESS"
                runtime_ms = round(res.time_taken * 1000.0, 2)
                memory_kib = round(res.peak_memory, 2)
                expanded_nodes = res.expanded_nodes
                steps = len(res.actions)

                # --nh gi- b-ng TrajectoryEvaluator
                report = evaluator.evaluate(board, res.actions, optimal_penalty=optimal_penalty, level_data=level_data)
                backtracks = report.backtracks
                void_hazards = report.void_exposure
                penalty = round(report.penalty_cost, 2)
                score = round(report.score, 1)

                # Advanced metrics
                penetrance_pct = round((steps / expanded_nodes) * 100.0, 2) if expanded_nodes > 0 else 0.0
                subopt_ratio = round(steps / optimal_steps, 2) if optimal_steps > 0 else 1.0
                branching_factor = calc_effective_branching_factor(expanded_nodes, steps)

            row = {
                "level": level_id,
                "solver": solver_name,
                "status": status,
                "runtime_ms": runtime_ms,
                "memory_kib": memory_kib,
                "expanded_nodes": expanded_nodes,
                "steps": steps,
                "backtracks": backtracks,
                "void_hazards": void_hazards,
                "penalty": penalty,
                "score": score,
                "penetrance_pct": penetrance_pct,
                "subopt_ratio": subopt_ratio,
                "branching_factor": branching_factor
            }
            results.append(row)

            # In d-ng k-t qu-
            status_display = "OK" if status == "SUCCESS" else status
            print(f"{solver_name:<10} | {status_display:<8} | {runtime_ms:>11.2f} ms | {memory_kib:>8.1f} KiB | {expanded_nodes:>7d} | {steps:>5d} | {score:>6.1f} | {penetrance_pct:>6.2f}% | {branching_factor:>6.3f}")

        print()

    # -------------------------------------------------------------
    # TINH TOAN VA XUAT BANG TRUNG BINH CAC TIEU CHI (AVERAGE SUMMARY)
    # -------------------------------------------------------------
    from collections import defaultdict
    solver_stats = defaultdict(lambda: defaultdict(list))
    for r in results:
        s = r['solver']
        if r['status'] == 'SUCCESS':
            for col in ['runtime_ms', 'memory_kib', 'expanded_nodes', 'steps', 'backtracks', 'void_hazards', 'penalty', 'score', 'penetrance_pct', 'subopt_ratio', 'branching_factor']:
                solver_stats[s][col].append(r[col])

    print('==========================================================================================')
    print('      BANG TONG HOP GIA TRI TRUNG BINH TAT CA TIEU CHI (AVERAGE ACROSS 18 LEVELS)')
    print('==========================================================================================')
    print(f"{'Thuat toan':<10} | {'Thoi gian (ms)':<14} | {'RAM (KiB)':<10} | {'Nodes':<7} | {'Buoc':<5} | {'Score':<6} | {'P (%)':<7} | {'rho':<5} | {'b*':<6}")
    print('-' * 90)

    summary_rows = []
    for solver_name, _ in SOLVER_CLASSES:
        st = solver_stats[solver_name]
        n_succ = len(st['steps'])
        if n_succ > 0:
            avg_row = {
                'level': 'AVERAGE',
                'solver': solver_name,
                'status': 'SUMMARY',
                'runtime_ms': round(sum(st['runtime_ms']) / n_succ, 2),
                'memory_kib': round(sum(st['memory_kib']) / n_succ, 2),
                'expanded_nodes': round(sum(st['expanded_nodes']) / n_succ, 1),
                'steps': round(sum(st['steps']) / n_succ, 1),
                'backtracks': round(sum(st['backtracks']) / n_succ, 2),
                'void_hazards': round(sum(st['void_hazards']) / n_succ, 2),
                'penalty': round(sum(st['penalty']) / n_succ, 2),
                'score': round(sum(st['score']) / n_succ, 1),
                'penetrance_pct': round(sum(st['penetrance_pct']) / n_succ, 2),
                'subopt_ratio': round(sum(st['subopt_ratio']) / n_succ, 2),
                'branching_factor': round(sum(st['branching_factor']) / n_succ, 3)
            }
            summary_rows.append(avg_row)
            print(f"{solver_name:<10} | {avg_row['runtime_ms']:>11.2f} ms | {avg_row['memory_kib']:>8.2f} KiB | {avg_row['expanded_nodes']:>7.1f} | {avg_row['steps']:>5.1f} | {avg_row['score']:>6.1f} | {avg_row['penetrance_pct']:>6.2f}% | {avg_row['subopt_ratio']:>5.2f} | {avg_row['branching_factor']:>6.3f}")

    print('==========================================================================================\n')

    # Xuat file CSV bao gom ca cac dong AVERAGE o cuoi
    with open(output_csv, 'w', encoding='utf-8') as f:
        f.write(','.join(csv_headers) + '\n')
        for r in results:
            f.write(','.join(str(r[h]) for h in csv_headers) + '\n')
        for r in summary_rows:
            f.write(','.join(str(r[h]) for h in csv_headers) + '\n')

    # Xuat file summary rieng: benchmark_summary.csv
    summary_csv = 'benchmark_summary.csv'
    with open(summary_csv, 'w', encoding='utf-8') as f:
        f.write(','.join(csv_headers) + '\n')
        for r in summary_rows:
            f.write(','.join(str(r[h]) for h in csv_headers) + '\n')
    total_time = time.perf_counter() - start_benchmark_time
    print(f"==========================================================================================")
    print(f"  BENCHMARK HO-N T-T TH-NH C-NG!")
    print(f"==========================================================================================")
    print(f"  - T-ng th-i gian -o th-c nghi-m: {total_time:.2f} gi-y")
    print(f"  - T-ng s- ph-p th- ho-n th-nh: {len(results)} / {total_benchmarks}")
    print(f"  - File k-t qu- -- xu-t: {os.path.abspath(output_csv)}")
    print(f"==========================================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bloxorz Benchmark Runner")
    parser.add_argument("--levels", type=str, default="", help="Danh s-ch level c-n ch-y, v- d-: '1,2,5' (m-c --nh: to-n b-)")
    parser.add_argument("--output", type=str, default="benchmark_results.csv", help="---ng d-n file CSV xu-t ra")
    parser.add_argument("--timeout", type=float, default=15.0, help="Th-i gian timeout m-i thu-t to-n (gi-y)")
    args = parser.parse_args()

    selected_levels = None
    if args.levels:
        selected_levels = [int(x.strip()) for x in args.levels.split(",") if x.strip().isdigit()]

    run_benchmark(
        levels_dir="levels",
        output_csv=args.output,
        timeout_sec=args.timeout,
        target_levels=selected_levels
    )
