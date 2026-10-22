"""Logical cells and canonical whole-block poses, with no graphics dependency."""

from dataclasses import dataclass
import math

from src.gui.contracts import BasicOrientation


@dataclass(frozen=True, slots=True)
class BlockPose:
    """Model-local 1×1×2 block transformed about its geometric center."""

    center: tuple[float, float, float]
    dimensions: tuple[float, float, float]
    rotation_axis: tuple[int, int, int]
    angle_degrees: float


def _board_parameters(rows: int, cols: int, pitch: float) -> None:
    for field, value in (("rows", rows), ("cols", cols)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{field} must be a positive integer (not bool).")
    if type(pitch) not in (int, float) or not math.isfinite(pitch) or pitch <= 0:
        raise ValueError("pitch must be finite and positive (not bool).")


def _anchor(row: int, col: int, rows: int, cols: int) -> None:
    for field, value, limit in (("row", row, rows), ("col", col, cols)):
        if type(value) is not int or not 0 <= value < limit:
            raise ValueError(f"{field} must be an integer within board bounds.")


def _xy(row: float, col: float, rows: int, cols: int, pitch: float) -> tuple[float, float]:
    return ((col - (cols - 1) / 2) * pitch,
            ((rows - 1) / 2 - row) * pitch)


def cell_to_world(row: int, col: int, *, rows: int, cols: int,
                  pitch: float = 1.0) -> tuple[float, float]:
    """Map a logical cell to its world XY center; world Y decreases with row."""
    _board_parameters(rows, cols, pitch)
    _anchor(row, col, rows, cols)
    return _xy(row, col, rows, cols, pitch)


def logical_board_bounds(rows: int, cols: int, *, pitch: float = 1.0
                         ) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return full cell-footprint XY bounds, including void and half-cell edges."""
    _board_parameters(rows, cols, pitch)
    return ((-cols * pitch / 2, -rows * pitch / 2),
            (cols * pitch / 2, rows * pitch / 2))


def block_pose(row: int, col: int, orientation: BasicOrientation, *,
               rows: int, cols: int, pitch: float = 1.0) -> BlockPose:
    """Return center, dimensions and an absolute axis-angle; never accumulate rolls."""
    _board_parameters(rows, cols, pitch)
    _anchor(row, col, rows, cols)
    if not isinstance(orientation, BasicOrientation):
        raise ValueError("orientation must be BasicOrientation.")
    if orientation is BasicOrientation.STANDING:
        xy = _xy(row, col, rows, cols, pitch)
        return BlockPose((*xy, pitch), (pitch, pitch, 2 * pitch), (0, 0, 1), 0.0)
    if orientation is BasicOrientation.HORIZONTAL:
        if col + 1 >= cols:
            raise ValueError("horizontal footprint lies outside board bounds.")
        xy = _xy(row, col + 0.5, rows, cols, pitch)
        return BlockPose((*xy, pitch / 2), (2 * pitch, pitch, pitch), (0, 1, 0), 90.0)
    if row + 1 >= rows:
        raise ValueError("vertical footprint lies outside board bounds.")
    xy = _xy(row + 0.5, col, rows, cols, pitch)
    return BlockPose((*xy, pitch / 2), (pitch, 2 * pitch, pitch), (1, 0, 0), 90.0)
