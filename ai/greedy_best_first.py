"""Greedy Best-First Search (GBFS) Pathfinding Algorithm for SmartStock AI.

Finds navigation routes across walkable warehouse cells using a Manhattan-distance
heuristic priority queue, parent pointers, and visited sets.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from simulation.models import Position
from simulation.warehouse import WarehouseGrid


class GBFSResult(BaseModel):
    """Structured report returned by the Greedy Best-First Search pathfinder."""
    success: bool
    path: List[Position] = Field(default_factory=list)
    explored_count: int = 0
    explored_nodes: List[Position] = Field(default_factory=list)
    total_cost: int = 0
    explanation: str = ""


def manhattan_heuristic(pos: Position, goal: Position) -> int:
    """Calculate Manhattan distance |x1 - x2| + |y1 - y2|."""
    return abs(pos.x - goal.x) + abs(pos.y - goal.y)


def greedy_best_first_search(
    grid: WarehouseGrid,
    start: Position,
    goal: Position
) -> GBFSResult:
    """Plan a step-by-step route from start to goal over walkable warehouse aisles.

    Characteristics:
    - Guided strictly by heuristic distance h(n) = Manhattan distance to goal.
    - Avoids impassable cells (racks, obstacles, hazard zones).
    - Note: Greedy Best-First Search prioritizes goal proximity and does not guarantee shortest path.
    """
    # 1. Start and Goal Validation
    if not grid.in_bounds(start.x, start.y):
        return GBFSResult(
            success=False,
            explanation=f"GBFS rejected: Start position ({start.x}, {start.y}) is out of grid bounds."
        )

    if not grid.in_bounds(goal.x, goal.y):
        return GBFSResult(
            success=False,
            explanation=f"GBFS rejected: Goal position ({goal.x}, {goal.y}) is out of grid bounds."
        )

    if not grid.is_walkable(start.x, start.y):
        return GBFSResult(
            success=False,
            explanation=f"GBFS rejected: Start position ({start.x}, {start.y}) is impassable/blocked."
        )

    if not grid.is_walkable(goal.x, goal.y):
        return GBFSResult(
            success=False,
            explanation=f"GBFS rejected: Goal position ({goal.x}, {goal.y}) is impassable/blocked."
        )

    # Trivially at goal
    if (start.x, start.y) == (goal.x, goal.y):
        return GBFSResult(
            success=True,
            path=[Position(x=start.x, y=start.y)],
            explored_count=1,
            explored_nodes=[Position(x=start.x, y=start.y)],
            total_cost=0,
            explanation="Start and goal positions are identical; zero-step path."
        )

    # 2. Priority Queue setup: (h_score, counter, current_tuple)
    counter = 0
    frontier: List[Tuple[int, int, Tuple[int, int]]] = []
    initial_h = manhattan_heuristic(start, goal)
    heapq.heappush(frontier, (initial_h, counter, (start.x, start.y)))

    # Parent pointers: child_tuple -> parent_tuple
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    visited: Set[Tuple[int, int]] = set([(start.x, start.y)])
    explored_nodes: List[Position] = []

    # 3. Best-First Search Loop
    while frontier:
        h_score, _, current_tuple = heapq.heappop(frontier)
        curr_pos = Position(x=current_tuple[0], y=current_tuple[1])
        explored_nodes.append(curr_pos)

        # Check goal reached
        if current_tuple == (goal.x, goal.y):
            # Reconstruct route from goal backwards to start
            path_coords = [current_tuple]
            curr = current_tuple
            while curr in came_from:
                curr = came_from[curr]
                path_coords.append(curr)
            path_coords.reverse()

            path_positions = [Position(x=cx, y=cy) for cx, cy in path_coords]
            total_steps = len(path_positions) - 1

            return GBFSResult(
                success=True,
                path=path_positions,
                explored_count=len(explored_nodes),
                explored_nodes=explored_nodes,
                total_cost=total_steps,
                explanation=(
                    f"Route discovered: {total_steps} steps found via Greedy Best-First Search "
                    f"({len(explored_nodes)} nodes evaluated)."
                )
            )

        # Expand adjacent walkable neighbours
        for neighbour in grid.get_neighbours(curr_pos.x, curr_pos.y):
            n_tuple = (neighbour.x, neighbour.y)
            if n_tuple not in visited:
                visited.add(n_tuple)
                came_from[n_tuple] = current_tuple
                counter += 1
                n_h = manhattan_heuristic(neighbour, goal)
                heapq.heappush(frontier, (n_h, counter, n_tuple))

    # 4. Exhausted search without reaching goal (unreachable)
    return GBFSResult(
        success=False,
        path=[],
        explored_count=len(explored_nodes),
        explored_nodes=explored_nodes,
        total_cost=0,
        explanation=f"Goal ({goal.x}, {goal.y}) is unreachable from ({start.x}, {start.y}) due to surrounding obstacles."
    )
