"""Database and domain models for SmartStock AI persistence."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryRecord:
    product_id: str
    shelf_id: str
    on_hand: int
    reserved: int

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


@dataclass
class OrderRecord:
    order_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None
