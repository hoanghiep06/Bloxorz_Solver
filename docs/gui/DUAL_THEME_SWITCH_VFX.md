# Dual-theme Elemental Switch VFX

Implemented in the actual static and animated gameplay renderers. Guide icons share the same switch definitions. No second animation manager, game loop, physics system or dependency is introduced.

## 1. Art direction

| Mechanic | Ancient Emerald — Jungle/Light | Frozen Sapphire — Snow/Dark |
| --- | --- | --- |
| Soft | Sculpted annular stone socket, bronze rune rim, moss carvings, emerald energy inlay | Faceted ice ring, dark slate socket, frost caps and ice fissures, cyan inlay |
| Heavy | Two long bronze/stone pressure bars, mechanical latches, inset emerald grooves | Two separate ice pressure bars, diagonal fractures and white/cyan grooves |
| Split | Two low eight-sided emerald gems, bronze/moss plinth, connecting seam | Two six-sided sapphire gems, frosted slate plinth, cold connecting seam |

The families differ in geometry, surface shading, particle shapes and switch audio, not just colour. The circular ring, paired bars and paired gems remain distinguishable from the normal gameplay camera and in monochrome silhouette. Ornament is kept low so it reads as an inset mechanism rather than a tall obstacle.

## 2. Source audit and baseline

Preflight branch: `feat/team-code/phase2-game-gui`; HEAD `2939dc7`. Existing uncommitted Settings/High-quality, centred HUD and Cinematic Audio V1 changes were retained. No Git mutation was performed.

Inspected Core switch rules, Basic/Advanced Board and snapshot contracts, `game_adapter`, `action_plan`, static Advanced renderer, mesh factory, scene theme/material pipeline, `AnimatedSurfaceLayer`, `AnimationManager`, existing Split Teleport, bridge motion, audio cue tracks, Mechanics Guide icons/focus and gameplay wiring.

The baseline on that existing working tree was **628 tests PASS**, 139.661 seconds. This baseline supersedes the older animation planning baseline mentioned in previous conversations.

Verified Core conditions, left unchanged:

- Soft: valid contact, including a small split cube.
- Heavy: the whole block standing upright; lying contact does not activate it.
- Split: whole block upright and valid distinct split destinations. Source/destinations and cube identity are supplied by the validated transition.

The renderer only consumes supplied events and snapshots. There is no proximity, Guide-hover or speculative activation rule.

## 3. Jungle materials

Shared palette in `elemental_switches.PALETTE`: stone `#687D65`, moss `#496D4F`, bronze `#987A4D`, emerald `#37D1AC`, rune highlight `#A0FFE0`, dark base `#294C40`.

Procedural geometry adds chisel marks, low moss clumps, a raised ring/socket, bronze bar latches and faceted gems. The switch-only shader adds granular wear and restrained moss variation, bronze highlights and emissive energy inlays. Idle emission is lower than authoritative active emission and the temporary activation pulse.

## 4. Snow materials and fallback

Palette: frosted ice `#A8E9FA`, energy `#32D9FF`, highlight `#E8FAFF`, sapphire `#3B91D1`, slate `#244A68`, deep shadow `#17334F`.

Snow has actual frost-cap/fissure meshes, different ring tessellation, bar fractures and a different gem cut. Its shader provides frozen fissures and facet highlights on a dark base, separating switches from the existing white Snow floor. Gems use an opaque translucent-looking treatment, avoiding transparent crystal sorting problems.

`switch_materials.configure(gsg)` compiles/links GLSL 1.20 in the actual graphics context. Unsupported/failed compilation retains opaque sculpted vertex-colour geometry. `BLOXORZ_MATERIALS=fixed` explicitly selects this fallback. Real GLX runs verified both GLSL and fallback; switches remain visible and functional. Existing floor, block and background materials are not redesigned by this task.

## 5. Soft animation

Only `SWITCH_ACTIVATE` for the supplied Soft definition creates the local burst. The inset ring depresses at most `.018 × pitch`; the socket stays at Z=0. A smooth pressure/release envelope, shader pulse, two expanding thin rings and eight short-lived particles accompany contact. Jungle particles are folded energy-leaf/dust shapes; Snow particles are faceted ice chips.

The normalized contact, pulse and recovery phases occupy the existing authoritative event window. Its supplied duration and replay rate are retained; the reference 0.50-second timeline is not imposed by adding gameplay delay. Completion returns to the snapshot state.

## 6. Heavy animation

Two actuators depress together with a longer pressure hold than Soft. The stone plinth does not move. Rune/ice energy ramps up after pressure, then releases through a bounded local pulse and twelve particles. The new geometry keeps the bars physically separate and long in both modes.

No Heavy event means no Heavy burst or pressure SFX. A real Core regression covers lying contact on a Heavy switch with the linked bridge remaining closed.

## 7. Split animation

The generic Split marker activation updates appearance only. Charging requires the confirmed `SPLIT` event. The exact source anchor selects its Split definition; no destination or rule is inferred by the renderer.

The local gem charge uses the first **33% of the existing Split event**: glow buildup, small opposed gem offsets (up to `.035 × pitch`) and dual energy rings with sixteen particles. Jungle emerald blends toward cyan; Snow hands cyan/sapphire directly to the existing teleport. Actuator pressure remains shallow and gems return to their canonical positions.

## 8. Bridge event integration

`SwitchVisualDefinition` provides switch ID, cell and kind, but not a reliable source-switch → target-bridge relation. Consequently this implementation deliberately uses the requested fallback: local switch pulse plus the existing bridge animation/audio for the actual bridge events. It does not guess the nearest bridge or draw an invented energy link.

Bridge flags, event windows and rigid platform translation remain unchanged. Native Soft/Heavy activation checks confirm exact final bridge flags.

## 9. Teleport handoff and actor ownership

The existing Split Teleport plan, VFX rig, phase constants, whole/cube actor slots and Core-provided destinations are reused unchanged. The switch layer adds no block/cube actors. Charge effects stop before the later travel/materialization phases, avoiding a second competing teleport.

Native testing confirms one Split activation cue, one charge/arrival sequence, exactly two resulting cubes and two committed moves after the fixture's two manual actions. Six solver replays also cover split, cube selection, merge and Goal without extra commits.

## 10. Audio mapping

All cues use the existing `AnimationAudioTrack` → `AudioManager` → bounded `SoundBank` pipeline:

| Authoritative event | Typed cue | Jungle asset | Snow asset |
| --- | --- | --- | --- |
| Soft `SWITCH_ACTIVATE` | `SOFT_SWITCH` | `soft_switch.wav` | `soft_switch_ice.wav` |
| Heavy `SWITCH_ACTIVATE` | `HEAVY_SWITCH` | `heavy_switch.wav` | `heavy_switch_ice.wav` |
| Confirmed `SPLIT` | `SPLIT_SWITCH` | `split_switch.wav` | `split_switch_ice.wav` |
| Existing Split/Merge phases | charge, disassemble, travel, arrival, materialize | Existing assets | Existing assets |

The three new Snow WAVs are original offline procedural designs: ice resonances/transients, heavier frozen pressure and a charging shimmer. No external recordings or runtime synthesis are added. They are prewarmed with the existing bank; a missing optional skin falls back to the original typed sound. See [audio permissions](../audio/AUDIO_ASSET_LICENSES.md).

Split SFX moved from the generic marker event to confirmed `SPLIT`, preventing a false/duplicate activation sound. Pause/resume consumes each cue once, cancel/Restart stops the existing scopes, and theme changes do not replay past cues. The bank now has 30 authored WAVs and 90 prewarmed sound instances, with the same 16-voice mixer limit. Runtime used real OpenAL decoding with its null output; it verifies cue/decoding integration, not listening quality on speakers.

## 11. Guide icon synchronization

`switch_icon_polygons` now projects the actual idle mesh top/bevel/facet triangles, including bronze runes, moss carvings, frost caps, pressure latches and gem cuts. It uses the original vertex palette and caches six themed projections; there is no separate hand-drawn glyph approximation. The Rail and Help Card share this geometry. A fixed transparent UI canvas keeps bounds stable across different source silhouettes; selected switch borders follow the matching emerald/cyan theme. See the [Guide icon follow-up](MECHANICS_GUIDE.md#follow-up-icon-theo-theme-2026-10-29) for the latest 646-test/native validation and screenshots.

Goal, Bridge, Fragile and Void icons remain unchanged. No thumbnail camera/render pass is added. Existing rail anchors, widget sizes, font, Help Card, focus/cycling and Back to Board are retained. Native clicks on all three switch icons check stable button positions and unchanged Core State/Moves/revision.

## 12. Theme switching

Both themed geometry variants are prepared when the level loads. Theme selection changes the existing variant visibility; it does not reload the level or rebuild Core State.

During a live/paused request, a genuine theme change hides and suppresses the old request's particle burst. New-themed mechanical actuators continue sampling the same existing timeline; the authoritative request, progress, state and commit remain unchanged. The next request may emit its normal new-theme burst. No particles from the previous theme survive or restart during the same request.

## 13. Lifecycle

There are no switch-owned tasks, timers, intervals or callbacks. `AnimatedSurfaceLayer.sample()` uses supplied normalized elapsed progress. Pause freezes actuators and particles because the existing manager stops advancing. Step finishes the existing multiphase action.

Surface release resets actuator offsets/shader pulse and hides pooled effects. Cancel, Restart and level disposal reuse existing release paths; disposal removes owned nodes and weak pool registrations. Session/revision/event context prevents an old theme burst from being reapplied. The static renderer resumes canonical snapshot appearance after the surface lease ends.

## 14. Resource management

- Geometry cache: at most 48 part sets and 48 assembled meshes; material states at most 32. Identical geometry/material states are consolidated for fewer draw calls.
- One prewarmed effect pool per surface layer; at most three concurrent local effects, two theme variants, two rings and sixteen particles per slot. No per-frame mesh/shader/texture/node allocation.
- Soft/Heavy/Split display 8/12/16 particles. No dynamic lights or extra bloom passes.
- Raised geometry stays within `.46 × pitch` XY and `.151 × pitch` Z; no collision nodes or support surfaces are added. Existing cell mapping, floor contact and roll/fall mathematics are untouched.
- Native 24-theme-cycle run: exactly **1274 render nodes**, no growth or Core mutation.
- Six native activate/Restart cycles: **181 → 181 render nodes, 14 → 14 tasks, 90 → 90 sound loads**.

These bounded counts establish no observed node/task growth in the tested lifecycle. They are not a GPU-memory profiler or a hardware FPS benchmark.

## 15. Automated tests

Final full suite: **644 tests PASS**, versus 628 baseline. Fifteen focused elemental-switch tests and one new audio skin/fallback test were added. Existing tests were updated only where the intended design changed: socket stays fixed while actuators depress; Guide contours now match each material family; confirmed Split gains its own typed cue.

Coverage includes geometry bounds/winding/normals, real theme geometry differences, opaque fallback, shader family/active inputs, shared Guide definitions, caches, actual Soft/Heavy/Split transitions, Heavy lying nonactivation, Split-marker suppression, bridge flags, no extra cube actors/Moves, Pause, cancellation/restart/level disposal, theme changes and bounded resources. Elapsed-time checks at 30/60/120 FPS and `.25×/1×/4×` compare actual actuator matrices and identical committed Core results, including the Split charging phase.

```bash
.venv/bin/python -B -m unittest discover -s tests
.venv/bin/python -B -m unittest discover -s tests -p test_elemental_switches.py
.venv/bin/python -B -m unittest discover -s tests -p test_game_audio.py
```

Logs: [baseline](evidence/elemental-switches/baseline.txt), [regression](evidence/elemental-switches/regression.txt), [focused](evidence/elemental-switches/elemental-tests.txt), [audio](evidence/elemental-switches/audio-tests.txt). Full-suite fallback diagnostics come from the existing fake-GSG failure injection; actual shader compilation is separately verified in the native window.

## 16. Runtime evidence

Actual Panda3D GLX `GraphicsWindow` under Xvfb; X11 XTest keys/clicks pass through Panda input/DirectGUI. Screenshots are framebuffer captures, not concepts or mocked renders.

```bash
ALSOFT_DRIVERS=null LP_NUM_THREADS=2 xvfb-run -a \
  -s '-screen 0 1600x1000x24 +extension GLX' \
  .venv/bin/python -B -m tools.elemental_switch_smoke \
  --output /tmp/bloxorz-elemental-ui
# Optional targeted runs use --fallback-only or --lifecycle-only.
```

| Evidence | Jungle/Light | Snow/Dark |
| --- | --- | --- |
| All three idle, normal gameplay camera | [Image](evidence/elemental-switches/light-all-idle.png) | [Image](evidence/elemental-switches/dark-all-idle.png) |
| Soft activation | [Image](evidence/elemental-switches/light-soft-active.png) · [Clip](evidence/elemental-switches/light-soft.gif) | [Image](evidence/elemental-switches/dark-soft-active.png) · [Clip](evidence/elemental-switches/dark-soft.gif) |
| Heavy activation | [Image](evidence/elemental-switches/light-heavy-active.png) · [Clip](evidence/elemental-switches/light-heavy.gif) | [Image](evidence/elemental-switches/dark-heavy-active.png) · [Clip](evidence/elemental-switches/dark-heavy.gif) |
| Split charge / existing teleport | [Image](evidence/elemental-switches/light-split-active.png) · [Clip](evidence/elemental-switches/light-split.gif) | [Image](evidence/elemental-switches/dark-split-active.png) · [Clip](evidence/elemental-switches/dark-split.gif) |
| Matching Guide / camera focus | [Image](evidence/elemental-switches/light-guide-icons.png) | [Image](evidence/elemental-switches/dark-guide-icons.png) |
| Real fixed-function fallback | [Image](evidence/elemental-switches/light-fallback-idle.png) | [Image](evidence/elemental-switches/dark-fallback-idle.png) |

18 screenshots and six sampled GIFs are saved. GIFs reduce captured frames to 768×432 and display samples at 120 ms; they illustrate progression, not precise wall-clock timing. Block occlusion during contact is retained rather than hiding gameplay actors for a prettier screenshot.

Runtime checks: both themed sandbox boards; native Soft/Heavy/Split actions; Guide focus/Back without activation or layout shift; Pause and mid-animation theme change; 24 theme cycles; six spawned solver workers; Restart/change level during burst; Iso/Top/Follow at 1024×720 and 1280×720; GLSL/fallback rendering; repeated resource audit.

On the actual Split fixture, BFS/IDS/UCS/Greedy/A* reach Goal in 5 actions and DFS in 19, each exactly matching its returned solution length. DFS is not required to return the shortest path. No search algorithm/cost/metrics logic was changed.

Reports: [native matrix](evidence/elemental-switches/runtime-report.json), [runtime log](evidence/elemental-switches/runtime.txt), [fallback](evidence/elemental-switches/fallback-report.json), [resource lifecycle](evidence/elemental-switches/lifecycle-report.json).

## 17. Files changed for this task

- New `src/gui/elemental_switches.py`, `switch_materials.py`, `switch_vfx.py`: shared geometry/icons, material family, bounded presentation rigs/VFX.
- New `assets/shaders/elemental-switch.vert`, `.frag`: switch-only surface/emission shader.
- `advanced_mesh_factory.py`, `animation_effects.py`, `visual_materials.py`, `scene_style.py`, `mechanics_icons.py`: minimal actual-gameplay/Guide/theme integration.
- Existing audio work extended in `audio_events.py`, `audio.py`, `sound_bank.py`, `tools/build_game_audio.py`; three new `assets/audio/sfx/*_ice.wav` skins and audio documentation.
- `tests/test_elemental_switches.py`, `test_game_audio.py`, `test_gui_animation_effects.py`, `test_mechanics_focus.py`; `tools/elemental_switch_smoke.py`.
- This document, `MECHANICS_GUIDE.md` and `docs/gui/evidence/elemental-switches/`.

Other dirty files visible in Git status belong to the preceding work and were preserved. Core, solvers, Controller/action semantics, level data, roll/fall math, Split/Merge math/VFX, existing block/floor meshes and background assets were not modified for this upgrade. No commit, push, merge, branch switch or other Git mutation was performed.

## 18. Known limitations

- No invented switch-to-bridge energy beam: the current render DTO lacks the authoritative relation. Local pulse and event-confirmed bridge animation are used as specified.
- Energy is emission/geometry based; there is no new dynamic light or bloom pass. Frozen crystals deliberately remain opaque.
- Timings fit existing event windows and replay rates rather than adding extra switch-only gameplay phases.
- The native matrix uses targeted mechanics fixtures and the sandbox, not every reachable state of every level. GPU-specific performance and listening quality require testing on the user's target hardware.

Status: **DUAL-THEME SWITCH VFX COMPLETE**.
