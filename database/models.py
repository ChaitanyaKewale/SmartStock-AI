"""Database record dataclasses for SmartStock AI SQLite persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductRecord:
    id: str
    name: str
    category: str
    unit_weight_kg: float
    shelf_id: str
    active: bool


@dataclass
class InventoryRecord:
    product_id: str
    shelf_id: str
    on_hand: int
    reserved: int

    @property
    def available(self) -> int:
        """Available stock ready for new orders (on_hand - reserved)."""
        return max(0, self.on_hand - self.reserved)


@dataclass
class OrderLineRecord:
    id: int
    order_id: str
    product_id: str
    quantity: int
    picked_quantity: int
    unit_weight_kg: float
    shelf_id: str

    @property
    def is_fully_picked(self) -> bool:
        return self.picked_quantity >= self.quantity


@dataclass
class OrderRecord:
    id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class TransactionRecord:
    id: int
    idempotency_key: Optional[str]
    order_id: Optional[str]
    product_id: str
    action_type: str
    delta_on_hand: int
    delta_reserved: int
    timestamp: str
    notes: Optional[str] = None


@dataclass
class DeliveryRecord:
    order_id: str
    delivered_at: str
    total_items: int
    total_weight_kg: float
    notes: Optional[str] = None


@dataclass
class DurableEventRecord:
    id: int
    order_id: Optional[str]
    category: str
    action: str
    outcome: str
    explanation: str
    timestamp: str
