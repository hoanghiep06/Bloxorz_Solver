import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.board import Board
from src.solvers.bfs import BFSSolver
from src.solvers.dfs import DFSSolver
from src.solvers.ids import IDSSolver
from src.solvers.UCS_Algorithm.main_ucs import run_ucs_algorithm
# from src.solvers.astar import AStarSolver

def main():
    map_path = "levels/level_01.json"
    board = Board(map_path)
    print(f"Loaded {map_path} successfully!")
    print(f"Start: ({board.start_r}, {board.start_c}), Goal: ({board.goal_r}, {board.goal_c})\n")

    for name, cls in [("BFS", BFSSolver), ("DFS", DFSSolver), ("IDS", IDSSolver)]:
        print(f">>> Testing {name} Solver...")
        print(cls(board).solve())

    print(">>> Testing UCS Solver...")
    run_ucs_algorithm()

if __name__ == "__main__":
    main()
