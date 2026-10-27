"""Short English help, verified against Board transitions and current mesh glyphs."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mechanic:
    id: str
    name: str
    description: str
    note: str
    accent: str


MECHANICS = (
    Mechanic('goal', 'Goal', 'Stand the whole block upright on the goal hole to finish the level.',
             'A single split cube cannot finish.', 'F5A623'),
    Mechanic('bridge', 'Bridge', 'A linked switch can open or close this crossing. An open bridge supports the block like normal floor.',
             'A closed bridge has no support.', '9FB4C8'),
    Mechanic('soft_switch', 'Soft Switch', 'Touch this plate with any part of the block to activate its linked bridges.',
             'Small split cubes can activate it too.', '4EDBFF'),
    Mechanic('heavy_switch', 'Heavy Switch', 'Stand the whole block upright on this plate to activate its linked bridges.',
             'Lying blocks and small cubes do not activate it.', '4EDBFF'),
    Mechanic('split_switch', 'Split Switch', 'Stand the whole block upright here to split it into two cubes at the configured destinations.',
             'Space selects a cube. Cubes merge when they meet along an edge.', '4EDBFF'),
    Mechanic('fragile', 'Fragile Tile', 'This tile breaks when the whole block stands upright on it. Lying across it is safe.',
             'A small split cube is safe here.', 'FFB347'),
    Mechanic('void', 'Void', 'There is no floor here. Moving any occupied part of the block over the gap makes it fall.',
             'Check the full landing area before rolling.', '8195AB'),
)
BY_ID = {item.id: item for item in MECHANICS}
