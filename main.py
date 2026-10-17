import sys
from src.core.board import Board
from src.solvers.bfs import BFSSolver
from src.solvers.greedy import GreedySolver
# from src.solvers.dfs import DFSSolver
# from src.solvers.astar import AStarSolver

def main():
    map_path = "levels/level_01.json"
    board = Board(map_path)
    print(f"Loaded {map_path} successfully!")
    print(f"Start: ({board.start_r}, {board.start_c}), Goal: ({board.goal_r}, {board.goal_c})\n")

    print(">>> Testing BFS Solver...")
    bfs_solver = BFSSolver(board)
    bfs_result = bfs_solver.solve()
    print(bfs_result)

    print(">>> Testing Greedy Best-First Search (GBFS) Solver...")
    greedy_solver = GreedySolver(board)
    greedy_result = greedy_solver.solve()
    print(greedy_result)

if __name__ == "__main__":
    main()
