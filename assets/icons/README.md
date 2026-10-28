# AI Solver robot

`ai-robot.png` derives from the robot image supplied by the user for this task.
The original is preserved at `sources/ai-robot-source.png` (360×360).
No external robot or generated replacement was used.

Offline preparation (Pillow available on the author's system):

```bash
python3 -m tools.prepare_toolbar_robot assets/icons/sources/ai-robot-source.png
```

The tool flood-fills border-connected near-white background, keeps the largest
robot component (discarding the separate floor shadow), and removes white matte
from soft boundary pixels. Interior white highlights remain opaque. Output:
228×274 RGBA with six-pixel padding, displayed aspect-correct at 26px tall using
Panda3D's existing TexturePool/linear mipmap filtering. Runtime needs no Pillow.
