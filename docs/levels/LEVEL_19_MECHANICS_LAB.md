# Level 19 — The Mechanics Laboratory

## 1. Identity and registration

Production file: `levels/level_19.json`; name: **The Mechanics Laboratory**; type: advanced mechanics testing sandbox. This is a playable catalog level, not a preview fixture. It is appended after `level_18` through the existing natural-sort `LevelCatalog`; no separate registry, level count constant or custom loader is added.

The level has a short safe route to Goal and optional laboratory branches. Winning does not require triggering every hazardous tile; each mechanic can instead be tested through a real path from Start.

## 2. Dimensions and implemented grid

**13 rows × 17 columns**, zero-based `(row, col)` coordinates. Existing schema only: `name`, `grid`, `start`, `goal`, `switches`, `bridges`, and the already-supported list form of `split_switch`.

Legend: `.` Void (0), `#` Floor (1), `G` Goal (2), `F` Fragile (3), `S` Soft (4), `H` Heavy (5), `T` Split (6), `=` Bridge (7).

```text
   01234567890123456
00 .................
01 .F#####...#####F.
02 .###H##...##T###.
03 .###SH#===###S##.
04 .#H####...####T#.
05 .###S#F...######.
06 ...=........=....
07 ...=........=....
08 .#F##F#...######.
09 .##.#########G##.
10 .##F.##...######.
11 .####F#...#####F.
12 .................
```

Counts: 92 normal floor cells, 105 in-bounds Void cells, one Goal, eight Fragile, three Soft, three Heavy, two Split and seven Bridge cells in three groups. Closed bridge positions remain Bridge definitions rather than being counted as static Void.

## 3. Start and Goal

- Start **(3,2)**, whole block standing on normal floor.
- Goal **(9,13)**, the only tile code 2; the normal renderer supplies the flag/hole and victory animation.
- Initial bridge flags, in definition order: **(False, True, False)**.
- No initially unsupported Start, overlapping bridge groups, special-tile metadata conflicts or out-of-bounds destinations.

## 4. Mechanic coordinates

| Mechanic | Cells |
| --- | --- |
| Soft | (3,4), (5,4), (3,13) |
| Heavy | (3,5), (2,4), (4,2) |
| Split | (2,12), (4,14) |
| Fragile | (1, 1), (1, 15), (5, 6), (8, 2), (8, 5), (10, 3), (11, 5), (11, 15) |
| Goal | (9,13) |
| Interior Void examples | (9,3), (10,4) |

All other Void positions are explicitly 0 in the grid above, including the outer border and gaps between the four zones. The permanent C–D connector is row 9, columns 7–9. Fragile cells are spread across zones so nearby tests are possible without first crossing the whole map.

## 5. Switch-to-Bridge mappings

String IDs are explicit and unambiguous; there is no positional/numeric alias dependency.

| Bridge ID | Cells | Initial state |
| --- | --- | --- |
| `east_crossing` | (3,7), (3,8), (3,9) | inactive |
| `fragile_access` | (6,3), (7,3) | active |
| `goal_access` | (6,12), (7,12) | inactive |

| Switch cell | Type | Target ID | Action |
| --- | --- | --- | --- |
| (3,4) | Soft | `east_crossing` | open |
| (5,4) | Soft | `fragile_access` | open |
| (3,13) | Soft | `goal_access` | toggle |
| (3,5) | Heavy | `fragile_access` | toggle |
| (2,4) | Heavy | `fragile_access` | open |
| (4,2) | Heavy | `east_crossing` | close |

All three groups have verified open and close paths. Re-entering a toggle switch causes a new legitimate transition; merely standing on it between frames adds no activation. Existing Core conditions remain unchanged: Soft accepts contact by whole/small cubes; Heavy requires the whole block upright. For example, the first `D` from Start lies across Heavy (4,2) and does not close the east bridge.

## 6. Split destinations

| Source | Cube A destination | Cube B destination |
| --- | --- | --- |
| (2,12) | (2,10) | (4,12) |
| (4,14) | (3,14) | (5,12) |

Both destination pairs are distinct, separated, in bounds and on normal floor independent of bridge flags. They have space to move the active cube, use Space, and merge along an edge under existing Core rules. The level defines no teleport animation, cube IDs or custom merge logic.

## 7. Four connected laboratory zones

- **A — Switch Playground:** rows 1–5, columns 1–6; Start, two Soft, all three Heavy, and two nearby Fragile tiles. Room for standing/lying approaches, returning to switches and opening/closing crossings.
- **B — Split & Teleport:** rows 1–5, columns 10–15; both Split switches, their destinations, a Soft toggle for the south crossing and one edge Fragile. Connected east of A through `east_crossing`.
- **C — Fragile & Falling:** rows 8–11, columns 1–6; four Fragile cells, interior holes and perimeter edges. The initially active `fragile_access` bridge allows reaching it early; a safe route also connects east to D.
- **D — Goal & AI:** rows 8–11, columns 10–15; Goal, approach space, one edge Fragile, the permanent connector from C and `goal_access` from B.

The rooms form a loop when crossings are open. Closing a bridge can alter access and cause valid failure; Restart always restores the initial map/flags. There is no checkpoint or special tester teleport. The nearest shatter test takes six attempted inputs from Start.

## 8. Reproducible gameplay scenarios

Actions below are native game actions, **each sequence starts after Restart**. Space changes the active cube. Prefixes must finish before sending the next input.

| Scenario | Sequence | Expected result |
| --- | --- | --- |
| Soft / east bridge open | `R` | Soft (3,4) touched while lying; east crossing opens |
| Heavy / fragile bridge close | `R R` | Stand on Heavy (3,5); fragile crossing closes |
| Reopen same toggle | `R R L R` | Return upright to (3,5); fragile crossing reopens |
| Heavy close east bridge | `R D L` | Stand on Heavy (4,2); east crossing closes |
| Early Fragile safe contact | `U L` | Whole block lies across Fragile (1,1), stays supported |
| Early shatter | `R U R D R D` | Stand on Fragile (5,6), confirmed collapse/fall |
| Edge tipping/fall | `L` | Block partly leaves floor near column 0 |
| Interior hole fall | `D R D D D` | Attempt upright landing at Void (9,3) |
| Split at (4,14) | `R R R R R R R D R` | Two valid Core-provided cubes, one teleport sequence |
| Switch active cube | previous sequence + `SPACE` | Same positions, different active cube |
| Merge | `R R R R R R R D R D D L` | Whole block reunited by edge adjacency |
| Split at (2,12) | `U R D R R R R R U R` | Second valid source/destination pair |

The tracked [36-scenario action corpus](../../tests/fixtures/level19/scenarios.json) additionally covers activation of every Soft/Heavy/Split, all three bridge groups opening/closing, safe lying contact **and** upright failure for each of the eight Fragile tiles, cube movement/selection/merge, in-bounds interior/edge failure and Goal. Paths were discovered using actual Core transitions from Initial State; discovery stopped expansion at Goal, matching gameplay termination. The discovery visited 35,903 reachable states before satisfying all targets. Tests replay and verify each stored action sequence rather than injecting arbitrary poses or replaying prebuilt visual events.

## 9. Valid solution

A BFS-verified **16-action** path is:

```text
R R R R R R R L D R D D D D R U
```

Every action passes `Board.transition`; the final state is the whole block standing at (9,13). This route opens the east and goal crossings through the actual Soft switches. Optional Split/Fragile branches remain available for testing rather than being forced into the shortest route.

BFS also finds valid suffixes from a real split state and a state with the fragile bridge closed. Controller replay tests start from the current immutable state without resetting it.

## 10. AI results

Measured through the existing `.solve()` implementation with its unchanged `tracemalloc` metrics, on this workstation. Seconds/peak traced KiB are measurements, not performance guarantees.

| Solver | Result | Actions | Expanded nodes | Seconds | Peak Python KiB |
| --- | --- | ---: | ---: | ---: | ---: |
| BFS | PASS | 16 | 3190 | 0.1941 | 1515.0 |
| DFS | PASS | 260 | 295 | 0.0172 | 105.1 |
| IDS | PASS | 16 | 21132 | 0.9937 | 1231.9 |
| UCS | PASS | 16 | 4597 | 0.2886 | 2495.2 |
| Greedy | PASS | 24 | 59 | 0.0039 | 35.6 |
| A* | PASS | 16 | 3190 | 0.1693 | 1562.5 |

Each returned path was independently replayed through Core and through the real Controller/AnimationManager pipeline. BFS/IDS/A* give the 16-step unit-cost route. UCS uses its existing **PhysicsBasedCost**, so its optimization criterion is not silently replaced with a unit cost. On split-capable boards the existing A* heuristic intentionally becomes zero to retain admissibility; it is not weakened/modified for this level. DFS and Greedy are not required to be shortest-path solvers.

Native worker/clock replay results are recorded separately in [runtime-report.json](evidence/level19/runtime-report.json).

## 11. Guide and runtime validation

No Guide-specific Level 19 code is added. Existing authoritative lookup supplies 8 Fragile, 3 Soft, 3 Heavy, 2 Split, 3 bridge groups, one Goal and 105 bounded Void targets. Multiple-cell bridges retain one target per group. Tests/native clicks verify row-major cycling, wrapping, correct camera focus, Back to Board, stable Rail placement and unchanged Core/Moves/revision in both themes.

Runtime uses a real Panda3D GLX window under Xvfb, with native XTest mouse/keyboard input and the production 19-level catalog. Temporary saves isolate stars/settings; no existing profile is overwritten. Effects arise only from confirmed gameplay actions. No event or game-state injection is used to obtain screenshots. Audio is decoded through OpenAL Soft null output; this does not establish listening quality on speakers.

The original HUD normalization hides catalog fractions in the title. A minimal generic presentation adjustment keeps that short title and places the parsed catalog fraction in the status line, such as `READY | 19/19`. It derives the fraction from the existing view model and preserves it when status text is elided; it is not a hardcoded Level 19 label.

Images:

- [Jungle / Light](evidence/level19/light-level19.png) · [Snow / Dark](evidence/level19/dark-level19.png).
- [Level Select, page 3 with 19](evidence/level19/level-select-19.png).
- [Soft/bridge assembly](evidence/level19/light-soft-bridge.png) · [Heavy/bridge retraction](evidence/level19/light-heavy-bridge-closed.png).
- [Fragile shatter](evidence/level19/light-fragile-collapse.png) · [Interior Void fall](evidence/level19/light-interior-void.png).
- [Split Teleport](evidence/level19/dark-split-teleport.png) · [Merge](evidence/level19/dark-merge.png).
- [Guide with multiple Split targets](evidence/level19/dark-split-guide.png).
- [Last-level victory: Next disabled](evidence/level19/level19-victory-last-level.png).

## 12. Automated checks, progression and commands

Baseline on the preserved working tree: **646 tests PASS**, 92.768 s. New `test_level19.py` adds 13 focused tests: schema/geometry counts, metadata, bounds, split destinations, all 36 reachable scenarios, real Heavy lying semantics/toggle reactivation, Guide counts/order, six solvers, solve from intermediate state, six Controller replays, restart/failure cleanup, actual Level Select/18→19/last-level flow, themed Guide cycling and exactly-once audio dispatch for real switch/bridge/fragile/split/merge/goal transitions.

Original levels 1–18 remain byte-for-byte identical, protected by [SHA-256 snapshots](../../tests/fixtures/level19/original_levels_sha256.json). Catalog IDs/order are exactly level_01 through level_19. Level Select uses its existing third page and 57-star total. Completing 18 enables Next to 19; completing 19 disables Next and retains Retry/Levels instead of attempting a missing level_20.

```bash
# Normal project launch; select 19 on the third Level Select page:
.venv/bin/python -B -m src.gui.game_app
# Focused and full regression:
.venv/bin/python -B -m unittest discover -s tests -p test_level19.py
.venv/bin/python -B -m unittest discover -s tests
# Reproduce actual native validation (production catalog, temporary save):
ALSOFT_DRIVERS=null LP_NUM_THREADS=2 xvfb-run -a \
  -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.level19_smoke --output /tmp/bloxorz-level19-ui
```

Final result: **659 tests PASS**, 109.012 s; focused laboratory suite **13 PASS**, 12.633 s. Native GLX/XTest matrix **PASS** with 20 actual framebuffer screenshots, all six real worker/replays, both themes, all repeated special-target cycling, confirmed shatter/fall/split/merge/bridge actions and real 18→19 / last-level victory behavior. The original 18 level hashes still match.

Evidence: [full regression](evidence/level19/regression.txt), [baseline](evidence/level19/baseline.txt), [focused tests](evidence/level19/level19-tests.txt), [native report](evidence/level19/runtime-report.json), [native log](evidence/level19/runtime.txt), [solver measurements/actions](evidence/level19/solver-results.json), [36-scenario discovery](evidence/level19/reachability.txt). Full-suite fake-GSG shader fallback diagnostics are expected failure-injection output; there are no failed tests. Native compilation/gameplay uses the actual GLX context.

## 13. Files changed

- `levels/level_19.json` — new production level, automatically registered by the existing catalog.
- `src/gui/hud.py` — minimal generic catalog-fraction status presentation required for visible `19/19`; no gameplay semantics or counter constant added.
- `tests/test_level19.py`; `tests/fixtures/level19/scenarios.json`, `original_levels_sha256.json` — focused verification and reproducible real-action corpus.
- `tools/level19_smoke.py` — actual native UI/worker/mechanics validation.
- This document and `docs/levels/evidence/level19/` — measured solver/Core/runtime proof and framebuffer screenshots.

Preflight branch `feat/team-code/phase2-game-gui`, HEAD `2939dc7`. Existing tracked and untracked changes from preceding GUI/audio tasks are preserved. No Core, solver, animation/teleport math, renderer material, AudioManager, Guide behavior or existing level file is changed for this task. No commit, push, merge, checkout, reset, stash or clean was performed.

## 14. Known limitations

- This is an accessible laboratory with optional test branches, not a puzzle requiring every mechanic before Goal. Hazard failures require Restart; no checkpoint system is added.
- Some distant Fragile test paths are longer; the nearby A-zone Fragile tiles provide quick shatter tests. All eight nevertheless have independently verified safe-contact and failure paths from Start.
- DFS returns a much longer valid route (260 actions); Greedy returns 24. Their algorithms are unchanged.
- Render screenshots use the existing camera framing/materials. Software-GL runtime evidence is not a GPU FPS benchmark, and audio null output is not human listening validation.


Status: **LEVEL 19 — THE MECHANICS LABORATORY COMPLETE**.
