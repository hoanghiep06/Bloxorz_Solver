import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.board import Board
from src.solvers.bfs import BFSSolver
from src.solvers.UCS_Algorithm.main_ucs import run_ucs_algorithm

if __name__ == "__main__":
    run_ucs_algorithm()