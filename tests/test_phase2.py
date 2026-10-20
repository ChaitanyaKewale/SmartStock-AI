"""Phase 2 Automated Tests: Warehouse Domain Models, Grid Queries, Obstacle Editing, and SVG Rendering.

Verifies:
- Warehouse configuration integrity and grid boundaries (16x12).
- Rack cells are strictly impassable.
- All designated shelf pickup positions are valid, adjacent, walkable cells.
- Distribution station is in-bounds and walkable.
- Obstacle placement validation (rejection on station, racks, and robot home).
- Adding, removing, and discarding obstacles.
- JSON serialization and round-trip reloading.
- SVG map rendering and HTML fallback generation.
"""

import json
import pytest
from pathlib import Path

from simulation.models import Position, RobotDirection
from simulation.warehouse import WarehouseGrid, get_default_warehouse
from utils.config import (
    WarehouseConfig,
    GridConfig,
    DistributionStationConfig,
    RobotInitialConfig,
    RackConfig,
    PositionConfig
)
from frontend.map_renderer import render_warehouse_svg, render_map_fallback


def test_default_warehouse_creation():
    """Verify that default warehouse initializes with 16x12 grid, racks, and station."""
    grid = get_default_warehouse()
    assert grid.width == 16
    assert grid.height == 12
    assert len(grid.racks_by_id) == 30
    assert len(grid.fixed_obstacles) == 4
    assert len(grid.restricted_zones) == 2
    assert grid.distribution_station.id == "DS-01"
    assert grid.distribution_station.x == 0
    assert grid.distribution_station.y == 0
    assert grid.robot_initial.position.x == 0
    assert grid.robot_initial.position.y == 1


def test_grid_bounds_and_neighbour_generation():
    """Verify coordinate bounds checking and 4-directional neighbour generation."""
    grid = get_default_warehouse()

    # In-bounds and out-of-bounds
    assert grid.in_bounds(0, 0) is True
    assert grid.in_bounds(15, 11) is True
    assert grid.in_bounds(-1, 0) is False
    assert grid.in_bounds(0, -1) is False
    assert grid.in_bounds(16, 5) is False
    assert grid.in_bounds(5, 12) is False

    # Neighbours at walkable coordinate (1, 1)
    neighbours = grid.get_neighbours(1, 1)
    assert len(neighbours) > 0
    for n in neighbours:
        assert isinstance(n, Position)
        assert grid.in_bounds(n.x, n.y)
        assert grid.is_walkable(n.x, n.y)
        assert n.is_adjacent_to(Position(x=1, y=1))


def test_rack_cells_are_strictly_impassable():
    """Verify that all rack locations are blocked/not walkable."""
    grid = get_default_warehouse()
    for shelf in grid.racks_by_id.values():
        assert grid.is_rack(shelf.x, shelf.y) is True
        assert grid.is_walkable(shelf.x, shelf.y) is False
        assert grid.is_blocked(shelf.x, shelf.y) is True


def test_all_pickup_positions_are_walkable_and_adjacent():
    """Verify that every rack has an accessible pickup position that is walkable and adjacent."""
    grid = get_default_warehouse()
    for shelf in grid.racks_by_id.values():
        pp = shelf.pickup_position
        assert grid.in_bounds(pp.x, pp.y) is True
        assert grid.is_walkable(pp.x, pp.y) is True
        assert not grid.is_rack(pp.x, pp.y)
        assert pp.manhattan_distance_to(Position(x=shelf.x, y=shelf.y)) == 1


def test_obstacle_and_hazard_zone_walkability():
    """Verify that fixed pillars and restricted zones cannot be walked through."""
    grid = get_default_warehouse()
    # Fixed obstacle at (5, 5)
    assert grid.is_obstacle(5, 5) is True
    assert grid.is_walkable(5, 5) is False

    # Restricted hazard zone at (15, 10)
    assert grid.is_restricted(15, 10) is True
    assert grid.is_walkable(15, 10) is False


def test_distribution_station_walkability():
    """Verify that the distribution station is a valid walkable destination."""
    grid = get_default_warehouse()
    ds = grid.distribution_station
    assert grid.is_distribution_station(ds.x, ds.y) is True
    assert grid.is_walkable(ds.x, ds.y) is True


def test_obstacle_placement_validation_and_lifecycle():
    """Verify obstacle placement rules, dynamic addition, blocking, and removal."""
    grid = get_default_warehouse()

    # 1. Invalid placements rejected
    can_place, msg = grid.can_place_obstacle(0, 0)  # On Distribution Station
    assert can_place is False
    assert "station" in msg.lower()

    can_place, msg = grid.can_place_obstacle(2, 2)  # On Rack R01
    assert can_place is False
    assert "rack" in msg.lower()

    can_place, msg = grid.can_place_obstacle(0, 1)  # On Robot Start
    assert can_place is False
    assert "robot" in msg.lower()

    can_place, msg = grid.can_place_obstacle(99, 99)  # Out of bounds
    assert can_place is False
    assert "outside" in msg.lower()

    # 2. Valid placement on open walkway (1, 4)
    assert grid.is_walkable(1, 4) is True
    can_place, _ = grid.can_place_obstacle(1, 4)
    assert can_place is True

    # Add obstacle
    assert grid.add_obstacle(1, 4, name="Test Barrier") is True
    assert grid.is_walkable(1, 4) is False
    assert (1, 4) in grid.user_added_obstacles

    # Attempting to add again at same spot is rejected
    can_place_again, _ = grid.can_place_obstacle(1, 4)
    assert can_place_again is False

    # Remove obstacle
    assert grid.remove_obstacle(1, 4) is True
    assert grid.is_walkable(1, 4) is True
    assert (1, 4) not in grid.user_added_obstacles


def test_discard_edits_restores_layout():
    """Verify that discard_edits removes all temporary barriers and restores layout."""
    grid = get_default_warehouse()

    # Add multiple user barriers
    grid.add_obstacle(1, 4)
    grid.add_obstacle(1, 5)
    assert len(grid.user_added_obstacles) == 2
    assert grid.is_walkable(1, 4) is False
    assert grid.is_walkable(1, 5) is False

    # Discard
    grid.discard_edits()
    assert len(grid.user_added_obstacles) == 0
    assert grid.is_walkable(1, 4) is True
    assert grid.is_walkable(1, 5) is True


def test_json_serialization_round_trip(tmp_path: Path):
    """Verify saving to JSON and reloading preserves the complete warehouse structure."""
    grid = get_default_warehouse()
    grid.add_obstacle(1, 4, name="Saved Barrier")

    temp_file = tmp_path / "saved_warehouse.json"
    grid.save_layout_to_file(temp_file)
    assert temp_file.is_file()

    # Reload from saved file
    with open(temp_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    reloaded_cfg = WarehouseConfig.model_validate(data)
    reloaded_grid = WarehouseGrid(reloaded_cfg)

    assert reloaded_grid.width == grid.width
    assert reloaded_grid.height == grid.height
    assert len(reloaded_grid.racks_by_id) == len(grid.racks_by_id)
    # The user barrier was saved into obstacles
    assert (1, 4) in reloaded_grid.fixed_obstacles


def test_invalid_layout_raises_value_error():
    """Verify that layout with non-adjacent or overlapping pickup position raises ValueError."""
    bad_cfg = WarehouseConfig(
        grid=GridConfig(width=16, height=12),
        distribution_station=DistributionStationConfig(id="DS", name="Station", x=0, y=0),
        robot_initial=RobotInitialConfig(id="BOT", name="Bot", x=0, y=1),
        racks=[
            # Rack at (2, 2) but pickup position is placed inside the rack itself
            RackConfig(
                id="BAD_RACK",
                name="Bad Rack",
                x=2,
                y=2,
                pickup_position=PositionConfig(x=2, y=2),
                zone="ZONE_A"
            )
        ]
    )
    with pytest.raises(ValueError) as exc_info:
        WarehouseGrid(bad_cfg)
    assert "cannot be on a rack" in str(exc_info.value).lower()


def test_svg_rendering_and_shelf_highlight():
    """Verify SVG renderer outputs valid markup and highlights the inspected shelf."""
    grid = get_default_warehouse()
    svg = render_warehouse_svg(grid, selected_shelf_id="R01")

    assert "<svg" in svg
    assert "</svg>" in svg
    assert "DS-01" in svg
    assert "R01" in svg
    assert "stroke-dasharray" in svg  # Dashed line to pickup bay for selected shelf

    # Verify HTML fallback
    fallback = render_map_fallback(grid)
    assert "<table" in fallback
    assert "DS" in fallback
