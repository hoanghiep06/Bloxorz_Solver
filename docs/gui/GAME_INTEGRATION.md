# Game integration: Core, Controller and Advanced renderer

The native game now uses Advanced visual DTOs for both Basic and Advanced levels.
The Basic adapter remains a separate preview API; existing Basic fixtures/contracts
are not reinterpreted or weakened.

## Run and verify

```bash
.venv/bin/python -B main.py
.venv/bin/python -B main.py --shadows
.venv/bin/python -B -m unittest discover -s tests
.venv/bin/python -B -m tools.game_integration_smoke --all
```

Start → select a level. Arrow keys/WASD roll; Space changes the active split cube;
R restarts. Settings offers mouse control, theme and audio. Space remains available
in mouse mode to switch the active cube. AI Solver appears after 30 seconds without
a move. For inspection without that wait:

```bash
.venv/bin/python -B -c "from src.gui.screens import UIFlow; UIFlow.HINT_DELAY=0; from src.gui.game_app import main; main()"
```

Ten original project levels are under `levels/`. They cover the existing Basic
map, fragile crossing/detour, soft/heavy switches, toggle/permanent bridges,
split/Space/merge, cube movement on fragile and combined mechanics.
These are authoritative game levels, not the older visual-only animation fixtures.

## Ownership and data flow

```
Board/BloxorzState → game_adapter → action_plan → GameController
                                                   ↓
                                         GameScene / AnimationManager
                                                   ↓
                                         AdvancedSceneRenderer
```

- Core decides passability, switch effects, split/merge and success/failure.
- `Board.transition(state, action)` keeps its Optional-state solver interface.
- `Board.describe_transition` additionally exposes raw motion, attempted effects,
  failure reason and failed cube. It never mutates a Board or source state.
- `game_adapter.prepare_level` validates the full board plus initial Core state and
  snapshot before any live scene is replaced.
- `GameScene` builds hidden static/dynamic/block subtrees and owns the surface
  layer, renderer and animation manager. Activation occurs before the old scene
  is released. Failed staging leaves the previous session operational.
- `action_plan` translates one Core action into explicit visual requests.
- Controller owns the phase queue, input, replay, Core commit, metrics and workers.
  Renderer never derives a switch or changes Core state.

### Identity and tile conventions

- Raw codes: 0 VOID, 1/2 FLOOR, 3 FRAGILE, 4 SOFT, 5 HEAVY, 6 SPLIT, 7 BRIDGE.
- Switches are overlays on FLOOR in Advanced DTOs, not extra floor geometry.
- `fragile_tiles`, `bridges`, `switches` and `split_switch` metadata are retained
  even when the JSON grid uses only 0/1/2.
- Bridge IDs are `str(bridge.id)` or the declared default index. Explicit IDs win
  over positional aliases. Duplicate/equivalent IDs are rejected by Core.
- A switch glyph has stable ID `switch:<row>:<column>`. Multiple same-kind Core
  switch definitions at a cell share a glyph; conflicting kinds are rejected.
- Cube IDs are `cube-0` and `cube-1`, tied to the Core cube tuple index. They are
  never assigned by current position, sorting, or distance.
- `active_cube` maps to the corresponding stable cube ID.
- Snapshot bridge flags follow the order of the board's bridge definitions.
- Visual switch activation denotes current pressing/occupancy; bridge flags
  represent the persistent gameplay effect of toggle/open/close/permanent.

Unsupported tile codes, orphan code-7 bridge cells, switches without definitions,
invalid split destinations, ambiguous switch overlays, mismatched flag counts and
invalid starting support fail before scene replacement.

## One Core action, multiple visual phases

A normal movement can have these phases:

1. ROLL to the kinematic pose, with press/release surface events.
2. EFFECTS for bridge changes, split/teleport, merge or active-cube changes.
3. On failure: fragile break if applicable, then terminal FALL.

The Core state remains the last committed state until every phase of a successful
action finishes. Visual revisions advance per nonterminal request, while `moves`
advances once per successful Core action, including Space. Visual revisions are
not move counts. Failed attempts do not commit a new Core state or increment moves.

The animation manager's current snapshot is the current visual phase; an
intermediate pose may precede the Core action's final state. Each request has its
own ID, a matching before snapshot and a strictly newer after revision.

Pause stops the current phase. Step resumes that phase and completes the remainder
of the same Core action, then stops before the next action. This works even when
one action includes a roll followed by split/merge/surface effects.

Off-board FALL includes an explicit `TerminalVisualOutcome.roll_direction`; the
manager rolls around the contact edge before dropping the chosen actor. In-bounds
failure rolls to the attempted tile, applies effects and then falls. Split falls
identify the failed cube; a failed merge falls as the whole block.

Goal completion is a terminal shrink/fade proxy, not a rigid-body physics model.
An initial-goal/zero-action solution is valid and produces completion rather than
leaving the HUD in SOLVING.

## Cancellation, rollback and shutdown

- Restart/Hide/level changes cancel solver jobs and invalidate animation callbacks
  with an epoch/session change before resetting or disposing managers.
- A phase/request failure restores the last committed Core pose in a fresh visual
  session and reports ERROR; intermediate visual changes are not committed.
- Staged scene failure does not dispose the current scene.
- Surface layer disposal follows animation → renderer → surface layer → roots.
- Menu widgets call DirectGUI.destroy(), not only NodePath.removeNode().
- Deferred widget retirement is tracked and drained on UIFlow disposal; late UI
  callbacks are removed.
- `dispose_game` releases UI/attract, controller/worker/scene, audio, dashboard,
  presentation, then host.

## Solver computation and metrics

Native GUI solver requests use one spawned `SolverJob` process per active request.
Only the main thread touches Panda objects. The UI polls the result without blocking
frame rendering; restart/cancel terminates a pending process and ignores stale
results. SearchResult and its algorithm measurements are returned through a pipe.
Each process owns its own tracemalloc session, so a background par calculation does
not corrupt solver peak-memory measurement. Headless controllers without task_mgr
can execute synchronously for deterministic scene-graph tests.

The BFS par calculation also runs in a cancellable worker. SearchResult is retained
after guide completion, while the block returns to the start for manual play.
The bottom HUD shows Moves, Search Time, Expanded Nodes, Solution Length and Peak
Python Memory. Time is converted from seconds to ms; peak memory from KiB to bytes
before formatting. These are algorithm Python allocation metrics, not RSS/VRAM.

A* retains its Basic heuristic. On boards with split/teleport it uses h=0 to retain
optimality with nonnegative costs. This can expand more nodes; no claim is made
that Manhattan bounds are admissible across arbitrary teleport links.

## Regression and native UI coverage

- `test_game_adapter.py`: raw codes, metadata, stable IDs, activation rules,
  malformed mechanic definitions, initial support and deterministic revisions.
- `test_game_integration.py`: all 10 levels × all 6 solvers, actual scene-graph
  animation, Space/split/merge, bridge/switch state, failure outcomes, one commit
  per action, pause-step, reset, staging failures, rollback, zero actions,
  asynchronous result/cancel/error handling and stable level replacement.
- `test_game_menu_lifecycle.py`: repeated menu/theme rebuilds, delayed cleanup,
  capability checks and preventing a HUD click from also moving the board.
- `test_solver_worker.py`: real spawned search results/metrics, worker exceptions,
  nonblocking poll and cancellation.
- Existing HUD tests keep disabled-control, formatting, elision, stable-widget and
  partial-construction cleanup assertions. Obsolete sidebar names and the exact
  old widget count were updated to the actual top-bar/metrics UI; assertions were
  not simply deleted to hide regressions.
- `tools.game_integration_smoke --all`: native GraphicsWindow, real taskMgr clock,
  all 60 solver/level pairs, manual keyboard/Space through advanced maps, fragile
  and bridge failures, pause-step, slider/metrics, resize, theme/mouse, menu cycles,
  actual pointer projection, slow-worker responsiveness/cancel and shutdown counts.

Default native evidence output is `/tmp/bloxorz-game-integration/result.json` plus
screenshots. The smoke tool uses a temporary save and silences audio. It does not
validate audio quality by listening. Windows native behavior is not verified by
Ubuntu UI runs. Finite lifecycle counts do not establish universal absence of
memory leaks or performance guarantees for arbitrary large levels.
