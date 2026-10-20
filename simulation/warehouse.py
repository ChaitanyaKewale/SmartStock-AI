"""Authoritative warehouse layout and grid query engine for SmartStock AI.

Enforces physical constraints:
- 16x12 grid bounds
- Physical racks are impassable (not walkable)
- Pickup positions and distribution station must remain walkable
- Obstacle placement validation and layout persistence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from simulation.models import (
    Position,
    ShelfLocation,
    Obstacle,
    RestrictedZone,
    DistributionStation,
    Product,
    Robot,
    RobotDirection
)
from utils.config import (
    WarehouseConfig,
    ProductConfig,
    load_warehouse_config,
    load_products_config,
    ConfigurationError
)


class WarehouseGrid:
    """Authoritative representation of the warehouse layout and spatial constraints."""

    def __init__(self, config: WarehouseConfig, products: Optional[List[ProductConfig]] = None):
        self.width = config.grid.width
        self.height = config.grid.height

        # Distribution station
        self.distribution_station = DistributionStation(
            id=config.distribution_station.id,
            name=config.distribution_station.name,
            x=config.distribution_station.x,
            y=config.distribution_station.y,
            facing=RobotDirection(config.distribution_station.facing)
        )

        # Initial robot start
        self.robot_initial = Robot(
            id=config.robot_initial.id,
            name=config.robot_initial.name,
            position=Position(x=config.robot_initial.x, y=config.robot_initial.y),
            facing=RobotDirection(config.robot_initial.facing),
            max_capacity_kg=config.robot_initial.max_capacity_kg
        )

        # Racks mapped by id and by coordinate
        self.racks_by_id: Dict[str, ShelfLocation] = {}
        self.racks_by_coord: Dict[Tuple[int, int], ShelfLocation] = {}
        for r in config.racks:
            shelf = ShelfLocation(
                id=r.id,
                name=r.name,
                x=r.x,
                y=r.y,
                pickup_position=Position(x=r.pickup_position.x, y=r.pickup_position.y),
                zone=r.zone,
                max_capacity=r.max_capacity
            )
            self.racks_by_id[shelf.id] = shelf
            self.racks_by_coord[(shelf.x, shelf.y)] = shelf

        # Obstacles (fixed and user-added)
        self.fixed_obstacles: Dict[Tuple[int, int], Obstacle] = {
            (obs.x, obs.y): Obstacle(id=obs.id, name=obs.name, x=obs.x, y=obs.y, is_user_added=False)
            for obs in config.fixed_obstacles
        }
        self.user_added_obstacles: Dict[Tuple[int, int], Obstacle] = {}

        # Restricted zones
        self.restricted_zones: Dict[Tuple[int, int], RestrictedZone] = {
            (rz.x, rz.y): RestrictedZone(id=rz.id, name=rz.name, x=rz.x, y=rz.y, reason=rz.reason or "")
            for rz in config.restricted_zones
        }

        # Products mapping
        self.products_by_id: Dict[str, Product] = {}
        self.products_by_shelf: Dict[str, List[Product]] = {shelf_id: [] for shelf_id in self.racks_by_id}

        if products:
            for p in products:
                prod = Product(
                    id=p.id,
                    name=p.name,
                    category=p.category,
                    unit_weight_kg=p.unit_weight_kg,
                    shelf_id=p.shelf_id,
                    initial_stock=p.initial_stock,
                    active=p.active
                )
                self.products_by_id[prod.id] = prod
                if prod.shelf_id in self.products_by_shelf:
                    self.products_by_shelf[prod.shelf_id].append(prod)
                    # Update shelf stock count
                    shelf = self.racks_by_id[prod.shelf_id]
                    shelf.product_ids.append(prod.id)
                    shelf.current_stock_count += prod.initial_stock

        # Validate layout integrity on construction
        self.validate_layout()

    # -------------------------------------------------------------------------
    # Spatial Boundary and Walkability Queries
    # -------------------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) coordinate is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_rack(self, x: int, y: int) -> bool:
        """Return True if (x, y) is occupied by a storage rack."""
        return (x, y) in self.racks_by_coord

    def is_obstacle(self, x: int, y: int) -> bool:
        """Return True if (x, y) contains a fixed or user-added obstacle."""
        return (x, y) in self.fixed_obstacles or (x, y) in self.user_added_obstacles

    def is_restricted(self, x: int, y: int) -> bool:
        """Return True if (x, y) is inside a restricted hazard zone."""
        return (x, y) in self.restricted_zones

    def is_distribution_station(self, x: int, y: int) -> bool:
        """Return True if (x, y) is the distribution station."""
        return (x, y) == (self.distribution_station.x, self.distribution_station.y)

    def is_walkable(self, x: int, y: int) -> bool:
        """Authoritative rule: A cell is walkable if it is inside the grid,
        not occupied by a physical rack, not an obstacle, and not a restricted zone.
        The distribution station and accessible pickup positions are walkable.
        """
        if not self.in_bounds(x, y):
            return False
        if self.is_rack(x, y):
            return False
        if self.is_obstacle(x, y):
            return False
        if self.is_restricted(x, y):
            return False
        return True

    def is_blocked(self, x: int, y: int) -> bool:
        """Inverse of is_walkable."""
        return not self.is_walkable(x, y)

    def get_neighbours(self, x: int, y: int) -> List[Position]:
        """Return all 4-directionally adjacent walkable neighbours (North, South, East, West)."""
        candidates = [
            (x, y - 1),  # North
            (x, y + 1),  # South
            (x + 1, y),  # East
            (x - 1, y),  # West
        ]
        return [Position(x=nx, y=ny) for nx, ny in candidates if self.is_walkable(nx, ny)]

    # -------------------------------------------------------------------------
    # Warehouse Content Queries
    # -------------------------------------------------------------------------

    def get_shelf_at(self, x: int, y: int) -> Optional[ShelfLocation]:
        """Return the ShelfLocation at (x, y), or None."""
        return self.racks_by_coord.get((x, y))

    def get_shelf_by_id(self, shelf_id: str) -> Optional[ShelfLocation]:
        """Return the ShelfLocation by shelf ID, or None."""
        return self.racks_by_id.get(shelf_id)

    def get_pickup_position(self, shelf_id: str) -> Optional[Position]:
        """Return the designated accessible pickup position for a shelf."""
        shelf = self.racks_by_id.get(shelf_id)
        return shelf.pickup_position if shelf else None

    def get_products_at_shelf(self, shelf_id: str) -> List[Product]:
        """Return list of products stored at the specified shelf."""
        return self.products_by_shelf.get(shelf_id, [])

    # -------------------------------------------------------------------------
    # Warehouse Obstacle Editing & Validation
    # -------------------------------------------------------------------------

    def can_place_obstacle(self, x: int, y: int) -> Tuple[bool, str]:
        """Validate if an obstacle can be placed at (x, y).

        Rejects placement on:
        - Out-of-bounds coordinates
        - Distribution station
        - Physical rack cells
        - Existing fixed or user obstacles
        - Robot start or current location
        """
        if not self.in_bounds(x, y):
            return False, f"Coordinate ({x}, {y}) is outside the {self.width}x{self.height} warehouse grid."
        if self.is_distribution_station(x, y):
            return False, f"Cannot place obstacle on Distribution Station ({x}, {y})."
        if self.is_rack(x, y):
            return False, f"Cannot place obstacle on physical rack cell ({x}, {y})."
        if self.is_obstacle(x, y):
            return False, f"An obstacle already exists at coordinate ({x}, {y})."
        if (x, y) == (self.robot_initial.position.x, self.robot_initial.position.y):
            return False, f"Cannot place obstacle on Robot Home position ({x}, {y})."
        return True, "Valid placement coordinate."

    def add_obstacle(self, x: int, y: int, name: str = "User Barrier") -> bool:
        """Add a user obstacle at (x, y) if placement is valid."""
        can_place, _ = self.can_place_obstacle(x, y)
        if not can_place:
            return False
        obs_id = f"UOBS-{x}-{y}"
        self.user_added_obstacles[(x, y)] = Obstacle(
            id=obs_id,
            name=name,
            x=x,
            y=y,
            is_user_added=True
        )
        return True

    def remove_obstacle(self, x: int, y: int) -> bool:
        """Remove an obstacle at (x, y) if it is user-added or removable."""
        if (x, y) in self.user_added_obstacles:
            del self.user_added_obstacles[(x, y)]
            return True
        return False

    def discard_edits(self) -> None:
        """Discard all user-added obstacles and restore the pristine initial layout."""
        self.user_added_obstacles.clear()

    def validate_layout(self) -> None:
        """Validate layout invariants per the implementation contract.

        Raises:
            ValueError: If distribution station or any pickup position is impassable,
                        or if rack/obstacle coordinates overlap.
        """
        # 1. Distribution station must be in bounds and walkable
        ds = self.distribution_station
        if not self.in_bounds(ds.x, ds.y):
            raise ValueError(f"Distribution station at ({ds.x}, {ds.y}) is out of bounds.")
        if self.is_rack(ds.x, ds.y) or self.is_obstacle(ds.x, ds.y) or self.is_restricted(ds.x, ds.y):
            raise ValueError(f"Distribution station at ({ds.x}, {ds.y}) must be a valid walkable cell.")

        # 2. All pickup positions must be in bounds and walkable
        for shelf in self.racks_by_id.values():
            pp = shelf.pickup_position
            if not self.in_bounds(pp.x, pp.y):
                raise ValueError(f"Shelf {shelf.id} pickup position ({pp.x}, {pp.y}) is out of bounds.")
            if self.is_rack(pp.x, pp.y):
                raise ValueError(f"Shelf {shelf.id} pickup position ({pp.x}, {pp.y}) cannot be on a rack.")
            if (pp.x, pp.y) in self.fixed_obstacles:
                raise ValueError(f"Shelf {shelf.id} pickup position ({pp.x}, {pp.y}) is blocked by a fixed obstacle.")
            if not shelf.pickup_position.is_adjacent_to(Position(x=shelf.x, y=shelf.y)):
                raise ValueError(f"Shelf {shelf.id} at ({shelf.x}, {shelf.y}) is not adjacent to its pickup position ({pp.x}, {pp.y}).")

    # -------------------------------------------------------------------------
    # JSON Serialization & Persistence Round-trip
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize current warehouse layout to a dictionary matching warehouse.json schema."""
        all_fixed = list(self.fixed_obstacles.values())
        all_user = list(self.user_added_obstacles.values())
        return {
            "grid": {"width": self.width, "height": self.height},
            "distribution_station": {
                "id": self.distribution_station.id,
                "name": self.distribution_station.name,
                "x": self.distribution_station.x,
                "y": self.distribution_station.y,
                "facing": self.distribution_station.facing.value
            },
            "robot_initial": {
                "id": self.robot_initial.id,
                "name": self.robot_initial.name,
                "x": self.robot_initial.position.x,
                "y": self.robot_initial.position.y,
                "facing": self.robot_initial.facing.value,
                "max_capacity_kg": self.robot_initial.max_capacity_kg
            },
            "racks": [
                {
                    "id": r.id,
                    "name": r.name,
                    "x": r.x,
                    "y": r.y,
                    "pickup_position": {"x": r.pickup_position.x, "y": r.pickup_position.y},
                    "zone": r.zone,
                    "max_capacity": r.max_capacity
                }
                for r in self.racks_by_id.values()
            ],
            "fixed_obstacles": [
                {"id": obs.id, "name": obs.name, "x": obs.x, "y": obs.y}
                for obs in (all_fixed + all_user)
            ],
            "restricted_zones": [
                {"id": rz.id, "name": rz.name, "x": rz.x, "y": rz.y, "reason": rz.reason}
                for rz in self.restricted_zones.values()
            ]
        }

    def save_layout_to_file(self, filepath: Path | str) -> None:
        """Write current layout to a JSON file."""
        data = self.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def get_default_warehouse() -> WarehouseGrid:
    """Factory function loading default warehouse and product configurations."""
    w_cfg = load_warehouse_config()
    p_cfg = load_products_config()
    return WarehouseGrid(config=w_cfg, products=p_cfg)
