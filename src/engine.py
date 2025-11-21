"""
Maze engine: map constants and movement calculations.

What it defines:
- Grid: 5x5, walls at (1,1), (1,2), (3,3), (2,0), goal at (4,4).
- Direction normalization (n/s/e/w -> north/south/east/west).
- Movement outcomes: SUCCESS, BLOCKED (wall), OOB (out of bounds), GOAL.

What calculate_move() does:
- Applies direction delta to the current position.
- Rejects OOB or wall cells (returns current position + status).
- Detects goal cell (returns new position + GOAL).
- Otherwise returns new position + SUCCESS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

Position = Tuple[int, int]
Direction = Literal["north", "south", "east", "west"]

STATUS_SUCCESS = "SUCCESS"
STATUS_BLOCKED = "BLOCKED"
STATUS_OOB = "OOB"
STATUS_GOAL = "GOAL"

GRID_SIZE = 5
WALLS: set[Position] = {(1, 1), (1, 2), (3, 3), (2, 0)}
GOAL: Position = (4, 4)


@dataclass(frozen=True)
class MoveOutcome:
    new_position: Position
    status: str


DIRECTION_DELTAS: dict[Direction, Position] = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}


def normalize_direction(raw: str) -> Direction | None:
    """Normalize user-facing direction strings."""
    val = raw.strip().lower()
    alias_map = {"n": "north", "s": "south", "e": "east", "w": "west"}
    normalized = alias_map.get(val, val)
    return normalized if normalized in DIRECTION_DELTAS else None


def calculate_move(current_pos: Position, direction: Direction) -> MoveOutcome:
    """Calculate new position and movement status."""
    dx, dy = DIRECTION_DELTAS[direction]
    candidate = (current_pos[0] + dx, current_pos[1] + dy)

    if candidate[0] < 0 or candidate[0] >= GRID_SIZE or candidate[1] < 0 or candidate[1] >= GRID_SIZE:
        return MoveOutcome(current_pos, STATUS_OOB)

    if candidate in WALLS:
        return MoveOutcome(current_pos, STATUS_BLOCKED)

    if candidate == GOAL:
        return MoveOutcome(candidate, STATUS_GOAL)

    return MoveOutcome(candidate, STATUS_SUCCESS)
