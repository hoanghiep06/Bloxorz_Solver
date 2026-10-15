import sys
from src.core.board import Board
from src.solvers.bfs import BFSSolver
# from src.solvers.dfs import DFSSolver
# from src.solvers.astar import AStarSolver

def main():
    map_path = "levels/level_01.json"
    board = Board(map_path)
    print(f"Loaded {map_path} successfully!")
    print(f"Start: ({board.start_r}, {board.start_c}), Goal: ({board.goal_r}, {board.goal_c})\n")

    print(">>> Testing BFS Solver...")
    solver = BFSSolver(board)
    result = solver.solve()
    print(result)

if __name__ == "__main__":
    main()