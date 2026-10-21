"""Domain models for SmartStock AI simulation, warehouse entities, and robot lifecycle.

Defines strictly typed models for positions, shelves, obstacles, products,
robot states, order states, and simulation events.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field


class RobotDirection(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"

    @property
    def delta(self) -> Tuple[int, int]:
        """Return (dx, dy) coordinate changes for this direction."""
        mapping = {
            RobotDirection.NORTH: (0, -1),
            RobotDirection.SOUTH: (0, 1),
            RobotDirection.EAST: (1, 0),
            RobotDirection.WEST: (-1, 0),
        }
        return mapping[self]

    @property
    def rotation_degrees(self) -> int:
        """Return degrees clockwise from North."""
        mapping = {
            RobotDirection.NORTH: 0,
            RobotDirection.EAST: 90,
            RobotDirection.SOUTH: 180,
            RobotDirection.WEST: 270,
        }
        return mapping[self]


class RobotState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    NAVIGATING_TO_PICKUP = "NAVIGATING_TO_PICKUP"
    PICKING = "PICKING"
    NAVIGATING_TO_DISTRIBUTION = "NAVIGATING_TO_DISTRIBUTION"
    UNLOADING = "UNLOADING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    COMPLETED = "COMPLETED"


class OrderState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PLANNING = "PLANNING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COLLECTING = "COLLECTING"
    RETURNING_TO_DISTRIBUTION = "RETURNING_TO_DISTRIBUTION"
    UNLOADING = "UNLOADING"
    DELIVERED = "DELIVERED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class Position(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def manhattan_distance_to(self, other: Position) -> int:
        """Calculate the Manhattan distance between two positions."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def manhattan_distance(self, other: Position) -> int:
        """Alias for manhattan_distance_to."""
        return self.manhattan_distance_to(other)

    def is_adjacent_to(self, other: Position) -> bool:
        """Check if another position is 4-directionally adjacent."""
        return self.manhattan_distance_to(other) == 1


class Product(BaseModel):
    id: str
    name: str
    category: str
    unit_weight_kg: float = Field(gt=0.0)
    shelf_id: str
    initial_stock: int = Field(ge=0)
    active: bool = True


class ShelfLocation(BaseModel):
    id: str
    name: str
    x: int
    y: int
    pickup_position: Position
    zone: str
    max_capacity: int = 50
    current_stock_count: int = 0
    product_ids: List[str] = Field(default_factory=list)


class Obstacle(BaseModel):
    id: str
    name: str
    x: int
    y: int
    is_user_added: bool = False


class RestrictedZone(BaseModel):
    id: str
    name: str
    x: int
    y: int
    reason: str = ""


class DistributionStation(BaseModel):
    id: str
    name: str
    x: int
    y: int
    facing: RobotDirection = RobotDirection.SOUTH


class Robot(BaseModel):
    id: str = "ROBOT-ALPHA"
    name: str = "Warehouse Bot 01"
    position: Position
    facing: RobotDirection = RobotDirection.SOUTH
    max_capacity_kg: float = 25.0
    current_load_kg: float = 0.0
    state: RobotState = RobotState.IDLE
    target: Optional[Position] = None
    route: List[Position] = Field(default_factory=list)
    route_progress: int = 0
    distance_travelled: int = 0
    carried_items: Dict[str, int] = Field(default_factory=dict)


class OrderLine(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    unit_weight_kg: float = Field(gt=0.0)
    shelf_id: str
    picked: int = 0


class Order(BaseModel):
    order_id: str
    lines: List[OrderLine] = Field(default_factory=list)
    status: OrderState = OrderState.DRAFT
    created_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class InventoryItem(BaseModel):
    product_id: str
    shelf_id: str
    on_hand: int = Field(ge=0)
    reserved: int = Field(ge=0)

    @property
    def available(self) -> int:
        return max(0, self.on_hand - self.reserved)


class SimulationEvent(BaseModel):
    event_id: int
    timestamp: str
    category: str
    order_id: Optional[str] = None
    position: Optional[Position] = None
    action: str
    outcome: str
    explanation: str
