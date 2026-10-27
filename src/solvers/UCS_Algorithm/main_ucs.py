from pathlib import Path

from src.core.board import Board
from src.solvers.UCS_Algorithm.ucs import (
    UCSSolver,
    visualize_ucs_solution,
)
from src.solvers.UCS_Algorithm.cost_functions import (
    PhysicsBasedCost,
    RiskSafetyCost,
    LearnedWeightCost,
    TunedWeightCost,
)


def run_ucs_algorithm():
    project_root = Path(__file__).resolve().parents[3]
    level_path = project_root / "levels" / "level_01.json"

    if not level_path.exists():
        print(f"Không tìm thấy level: {level_path}")
        return

    board = Board(str(level_path))

    models = [
        TunedWeightCost(),
        PhysicsBasedCost(),
        RiskSafetyCost(),
        LearnedWeightCost(
            w_step=1.0,
            w_tilt=1.5,
            w_risk=3.0,
        ),
    ]

    for model in models:
        solver = UCSSolver(board, cost_function=model)
        result = solver.solve()

        print(f"\n{'=' * 68}")
        print(f"Cost model: {model.name}")
        print(f"Solution length: {getattr(result, 'solution_length', 'N/A')}")
        print(f"Expanded nodes: {getattr(result, 'expanded_nodes', 'N/A')}")
        print(
            f"Search time: "
            f"{getattr(result, 'time_taken', 0.0) * 1000:.2f} ms"
        )
        print(
            f"Peak memory: "
            f"{getattr(result, 'peak_memory', 0.0):.2f} KB"
        )
        print(f"Total cost: {solver.total_cost:.2f}")

        solution = (
            getattr(result, "solution", None)
            or getattr(result, "path", None)
            or getattr(result, "actions", None)
            or solver.solution
        )

        if solution is None and isinstance(result, list):
            solution = result

        if solution is not None:
            visualize_ucs_solution(board, solution, model)
        else:
            print("Không lấy được danh sách action từ kết quả solve().")
            print("Kiểm tra src/solvers/base_solver.py.")


if __name__ == "__main__":
    run_ucs_algorithm()
