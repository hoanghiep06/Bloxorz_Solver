# Bloxorz weight-tuning experiment — protocol and limitations

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
