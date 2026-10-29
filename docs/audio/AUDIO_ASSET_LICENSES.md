# Audio assets and permission to redistribute

## Newly authored Cinematic Audio V1 assets

All WAVs in `assets/audio/sfx/` and `assets/audio/ambience/` are **original procedural sound designs authored for Bloxorz Solver with Codex**. No third-party recordings, movie/game excerpts, YouTube audio, stock sound libraries, or downloaded samples are used.

Generator: `tools/build_game_audio.py`, deterministic seeds, standard-library Python only. Format: stereo, 48,000 Hz, 16-bit PCM WAV. Regenerating assets is an offline authoring step, never a per-frame/runtime operation.

**Permission:** these newly authored audio files may be used, copied, modified and redistributed with or without modification, including commercially, without attribution requirements. They are supplied without warranty. This permission applies to the new assets listed below, not unrelated existing music in the repository.

| Files | Original design layers |
| --- | --- |
| `sfx/landing.wav` | Damped inharmonic stone body, low-frequency weight, filtered grit/debris |
| `sfx/roll_scrape.wav` | Broadband filtered friction, irregular granular modulation |
| `sfx/impact_0.wav` … `impact_2.wav` | Three original stone transient/resonance variations |
| `sfx/cube_impact.wav` | Shorter stone impact, mixed more softly |
| `sfx/edge_slide.wav` | Short gritty scrape |
| `sfx/fall_wind.wav` | Filtered broadband air/wind swell |
| `sfx/goal_energy.wav`, `sfx/victory.wav` | Energy texture and layered damped harmonic flourish |
| `sfx/soft_switch.wav`, `sfx/heavy_switch.wav`, `sfx/split_switch.wav` | Cyan energy click / heavier body / charging texture |
| `sfx/teleport_charge.wav`, `teleport_disassemble.wav`, `teleport_travel.wav`, `teleport_arrival.wav`, `teleport_materialize.wav` | FM/granular energy, filtered whoosh, impact and shimmer layers |
| `sfx/bridge_open.wav`, `sfx/bridge_close.wav` | Modulated mechanical grit/body |
| `sfx/fragile_crack.wav`, `sfx/fragile_break.wav` | Staggered noise fractures, stone body and debris |
| `sfx/ui_click.wav`, `sfx/ui_confirm.wav`, `sfx/ui_back.wav` | Short filtered tactile transients |
| `ambience/jungle.wav`, `ambience/snow.wav` | Original filtered-noise environment loops; designed, not recorded nature audio |

The original bank contains **27 WAV files**. The elemental-switch upgrade adds **3 original Snow switch skins** (`soft_switch_ice.wav`, `heavy_switch_ice.wav`, `split_switch_ice.wav`): inharmonic ice resonance, filtered ice transients and pressure/energy layers, authored by the same generator under the same permission. The current bank totals **30 WAV files**. These are deliberately layered synthesized effects, not single sine-wave placeholders. Their perceptual quality still benefits from human listening review; the runtime evidence establishes actual decoded playback and signal levels, not a subjective listening verdict.

## Existing assets retained unchanged

- `assets/audio/click.wav`, `roll.wav`, `fall.wav`, `goal.wav`, `music.wav`: existing procedural legacy files. The four legacy SFX are no longer used by the cinematic event bank. The original music synthesizer remains a fallback.
- `music/1.mp3`, `music/2.mp3`: existing repository playlist, unchanged. This task does not establish or extend their license/provenance. The project owner remains responsible for their distribution rights. They are excluded from the new audio evidence recording by disabling music during the gameplay capture.

No new runtime dependency or external audio download was added.
