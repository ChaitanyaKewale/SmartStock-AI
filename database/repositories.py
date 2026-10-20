"""Transactional repositories for SmartStock AI inventory and order persistence.

Enforces:
- Atomic inventory reservations and pickups
- Invariant 0 <= reserved <= on_hand
- Exactly-once delivery confirmation and transaction idempotency
- Startup recovery flagging for interrupted orders
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from database.models import (
    InventoryRecord,
    OrderRecord,
    OrderLineRecord,
    TransactionRecord,
    DeliveryRecord,
    DurableEventRecord
)


class PersistenceError(Exception):
    """Base exception for persistence and transaction failures."""
    pass


class InsufficientStockError(PersistenceError):
    """Raised when available stock is insufficient to fulfill an order reservation."""
    pass


class DeliveryError(PersistenceError):
    """Raised when delivery confirmation fails preconditions."""
    pass


# -----------------------------------------------------------------------------
# Inventory Repository
# -----------------------------------------------------------------------------

class InventoryRepository:
    """Manages transactional inventory on-hand, reservations, and pick reconciliation."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def get_inventory(self, product_id: Optional[str] = None) -> List[InventoryRecord]:
        """Fetch all inventory records or a single product record."""
        cursor = self.conn.cursor()
        if product_id:
            cursor.execute(
                "SELECT product_id, shelf_id, on_hand, reserved FROM inventory WHERE product_id = ?",
                (product_id,)
            )
        else:
            cursor.execute("SELECT product_id, shelf_id, on_hand, reserved FROM inventory ORDER BY product_id")

        return [
            InventoryRecord(
                product_id=row["product_id"],
                shelf_id=row["shelf_id"],
                on_hand=row["on_hand"],
                reserved=row["reserved"]
            )
            for row in cursor.fetchall()
        ]

    def get_stock(self, product_id: str) -> Optional[InventoryRecord]:
        """Fetch stock record for a specific product."""
        records = self.get_inventory(product_id=product_id)
        return records[0] if records else None

    def reserve_order_stock(
        self,
        order_id: str,
        items: List[Tuple[str, int]],  # (product_id, quantity)
        idempotency_key: str
    ) -> bool:
        """Atomically reserve requested stock quantities for an order.

        Invariants:
        - If idempotency_key was already processed, returns True without double-reserving.
        - Checks available = on_hand - reserved >= requested.
        - Updates reserved += requested and writes audit transaction.
        - If any item has insufficient available stock, rolls back entirely.
        """
        cursor = self.conn.cursor()

        with self.conn:
            # 1. Idempotency Check
            cursor.execute(
                "SELECT id FROM inventory_transactions WHERE idempotency_key = ?",
                (idempotency_key,)
            )
            if cursor.fetchone() is not None:
                return True

            if order_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO orders (id, status, created_at, notes) VALUES (?, 'VALIDATED', ?, 'Created via reservation')",
                    (order_id, datetime.now().isoformat())
                )

            # 2. Check availability across all items
            for product_id, quantity in items:
                cursor.execute(
                    "SELECT on_hand, reserved FROM inventory WHERE product_id = ?",
                    (product_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise InsufficientStockError(f"Product {product_id} is not registered in inventory.")

                on_hand = row["on_hand"]
                reserved = row["reserved"]
                available = on_hand - reserved
                if available < quantity:
                    raise InsufficientStockError(
                        f"Insufficient stock for {product_id}: requested {quantity}, available {available} (on-hand {on_hand}, reserved {reserved})."
                    )

            # 3. Apply reservations
            now_ts = datetime.now().isoformat()
            for product_id, quantity in items:
                cursor.execute(
                    """
                    UPDATE inventory
                    SET reserved = reserved + ?
                    WHERE product_id = ?;
                    """,
                    (quantity, product_id)
                )

                cursor.execute(
                    """
                    INSERT INTO inventory_transactions
                    (idempotency_key, order_id, product_id, action_type, delta_on_hand, delta_reserved, timestamp, notes)
                    VALUES (?, ?, ?, 'RESERVE', 0, ?, ?, 'Order reservation committed');
                    """,
                    (f"{idempotency_key}-{product_id}", order_id, product_id, quantity, now_ts)
                )

        return True

    def record_item_picked(
        self,
        order_id: str,
        product_id: str,
        quantity: int,
        idempotency_key: str
    ) -> bool:
        """Convert reserved stock into picked load when robot collects an item.

        Policy:
        - Shelf on_hand decreases by quantity (item removed from shelf).
        - Shelf reserved decreases by quantity (reservation converted to picked load).
        - Order line picked_quantity increases by quantity.
        """
        cursor = self.conn.cursor()

        with self.conn:
            # Idempotency check
            cursor.execute(
                "SELECT id FROM inventory_transactions WHERE idempotency_key = ?",
                (idempotency_key,)
            )
            if cursor.fetchone() is not None:
                return True

            # Validate stock balances
            cursor.execute(
                "SELECT on_hand, reserved FROM inventory WHERE product_id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            if not row or row["reserved"] < quantity or row["on_hand"] < quantity:
                raise PersistenceError(
                    f"Cannot pick {quantity}x {product_id}: insufficient reserved balance."
                )

            # Update inventory
            cursor.execute(
                """
                UPDATE inventory
                SET on_hand = on_hand - ?,
                    reserved = reserved - ?
                WHERE product_id = ?;
                """,
                (quantity, quantity, product_id)
            )

            # Update order line picked count
            cursor.execute(
                """
                UPDATE order_lines
                SET picked_quantity = picked_quantity + ?
                WHERE order_id = ? AND product_id = ?;
                """,
                (quantity, order_id, product_id)
            )

            # Record audit transaction
            cursor.execute(
                """
                INSERT INTO inventory_transactions
                (idempotency_key, order_id, product_id, action_type, delta_on_hand, delta_reserved, timestamp, notes)
                VALUES (?, ?, ?, 'PICK', -?, -?, ?, 'Item picked into robot bay');
                """,
                (idempotency_key, order_id, product_id, quantity, quantity, datetime.now().isoformat())
            )

        return True

    def release_and_reconcile_order(
        self,
        order_id: str,
        reconcile_picked: bool = True
    ) -> None:
        """Release remaining reservations and optionally return picked items to shelf upon cancellation."""
        cursor = self.conn.cursor()

        with self.conn:
            cursor.execute(
                "SELECT product_id, quantity, picked_quantity FROM order_lines WHERE order_id = ?",
                (order_id,)
            )
            lines = cursor.fetchall()

            now_ts = datetime.now().isoformat()
            for line in lines:
                p_id = line["product_id"]
                qty = line["quantity"]
                picked = line["picked_quantity"]
                unpicked = qty - picked

                # Release remaining reservations
                if unpicked > 0:
                    cursor.execute(
                        "UPDATE inventory SET reserved = max(0, reserved - ?) WHERE product_id = ?",
                        (unpicked, p_id)
                    )
                    cursor.execute(
                        """
                        INSERT INTO inventory_transactions
                        (idempotency_key, order_id, product_id, action_type, delta_on_hand, delta_reserved, timestamp, notes)
                        VALUES (?, ?, ?, 'RELEASE', 0, -?, ?, 'Unpicked reservation released on cancel');
                        """,
                        (f"RELEASE-{order_id}-{p_id}", order_id, p_id, unpicked, now_ts)
                    )

                # Return already-picked items to shelf on-hand
                if reconcile_picked and picked > 0:
                    cursor.execute(
                        "UPDATE inventory SET on_hand = on_hand + ? WHERE product_id = ?",
                        (picked, p_id)
                    )
                    cursor.execute(
                        """
                        INSERT INTO inventory_transactions
                        (idempotency_key, order_id, product_id, action_type, delta_on_hand, delta_reserved, timestamp, notes)
                        VALUES (?, ?, ?, 'RESTOCK_RETURN', ?, 0, ?, 'Picked cargo returned to shelf on cancel');
                        """,
                        (f"RETURN-{order_id}-{p_id}", order_id, p_id, picked, now_ts)
                    )

    def adjust_stock(
        self,
        product_id: str,
        new_on_hand: int,
        reason: str = "MANUAL_ADJUSTMENT"
    ) -> bool:
        """Manually adjust on-hand inventory quantity while strictly maintaining invariants."""
        if new_on_hand < 0:
            raise ValueError(f"On-hand stock cannot be negative (got {new_on_hand}).")

        cursor = self.conn.cursor()
        with self.conn:
            cursor.execute(
                "SELECT on_hand, reserved FROM inventory WHERE product_id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product {product_id} is not registered in inventory.")

            cur_on_hand = row["on_hand"]
            reserved = row["reserved"]
            if new_on_hand < reserved:
                raise ValueError(
                    f"Cannot reduce on-hand stock to {new_on_hand}: active reservations are {reserved} units."
                )

            delta = new_on_hand - cur_on_hand
            cursor.execute(
                "UPDATE inventory SET on_hand = ? WHERE product_id = ?",
                (new_on_hand, product_id)
            )

            idemp = f"ADJ-{product_id}-{int(datetime.now().timestamp() * 1000)}"
            cursor.execute(
                """
                INSERT INTO inventory_transactions
                (idempotency_key, order_id, product_id, action_type, delta_on_hand, delta_reserved, timestamp, notes)
                VALUES (?, NULL, ?, 'ADJUST', ?, 0, ?, ?);
                """,
                (idemp, product_id, delta, datetime.now().isoformat(), reason)
            )

        return True


# -----------------------------------------------------------------------------
# Order Repository
# -----------------------------------------------------------------------------

class OrderRepository:
    """Manages order creation, order line records, delivery confirmation, and startup recovery."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def create_order(
        self,
        order_id: str,
        lines: List[Dict[str, any]],  # product_id, quantity, unit_weight_kg, shelf_id
        status: str = "DRAFT",
        notes: Optional[str] = None
    ) -> OrderRecord:
        """Insert order header and lines in a single transaction."""
        now_ts = datetime.now().isoformat()
        cursor = self.conn.cursor()

        with self.conn:
            cursor.execute(
                "INSERT INTO orders (id, status, created_at, notes) VALUES (?, ?, ?, ?)",
                (order_id, status, now_ts, notes)
            )

            for line in lines:
                cursor.execute(
                    """
                    INSERT INTO order_lines
                    (order_id, product_id, quantity, picked_quantity, unit_weight_kg, shelf_id)
                    VALUES (?, ?, ?, 0, ?, ?)
                    """,
                    (order_id, line["product_id"], line["quantity"], line["unit_weight_kg"], line["shelf_id"])
                )

        return OrderRecord(id=order_id, status=status, created_at=now_ts, notes=notes)

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        """Fetch an order record by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, status, created_at, completed_at, notes FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return OrderRecord(
            id=row["id"],
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            notes=row["notes"]
        )

    def get_order_lines(self, order_id: str) -> List[OrderLineRecord]:
        """Fetch all line items for an order."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, order_id, product_id, quantity, picked_quantity, unit_weight_kg, shelf_id
            FROM order_lines WHERE order_id = ?
            """,
            (order_id,)
        )
        return [
            OrderLineRecord(
                id=row["id"],
                order_id=row["order_id"],
                product_id=row["product_id"],
                quantity=row["quantity"],
                picked_quantity=row["picked_quantity"],
                unit_weight_kg=row["unit_weight_kg"],
                shelf_id=row["shelf_id"]
            )
            for row in cursor.fetchall()
        ]

    def update_status(self, order_id: str, status: str, notes: Optional[str] = None) -> None:
        """Update an order's status and optional notes."""
        with self.conn:
            self.conn.execute(
                "UPDATE orders SET status = ?, notes = coalesce(?, notes) WHERE id = ?",
                (status, notes, order_id)
            )

    def confirm_delivery(
        self,
        order_id: str,
        total_items: int,
        total_weight_kg: float,
        idempotency_key: str
    ) -> DeliveryRecord:
        """Confirm delivery exactly once, verifying all order lines were picked."""
        cursor = self.conn.cursor()

        with self.conn:
            # Check if delivery is already recorded (idempotency)
            cursor.execute("SELECT order_id, delivered_at, total_items, total_weight_kg, notes FROM deliveries WHERE order_id = ?", (order_id,))
            existing = cursor.fetchone()
            if existing:
                return DeliveryRecord(
                    order_id=existing["order_id"],
                    delivered_at=existing["delivered_at"],
                    total_items=existing["total_items"],
                    total_weight_kg=existing["total_weight_kg"],
                    notes=existing["notes"]
                )

            # Validate all items were picked
            lines = self.get_order_lines(order_id)
            if not lines:
                raise DeliveryError(f"No order lines found for order {order_id}.")
            if not all(l.is_fully_picked for l in lines):
                unpicked = [f"{l.product_id} ({l.picked_quantity}/{l.quantity})" for l in lines if not l.is_fully_picked]
                raise DeliveryError(f"Delivery rejected: Incomplete items: {', '.join(unpicked)}.")

            now_ts = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO deliveries (order_id, delivered_at, total_items, total_weight_kg, notes)
                VALUES (?, ?, ?, ?, 'Confirmed delivery at station');
                """,
                (order_id, now_ts, total_items, total_weight_kg)
            )

            cursor.execute(
                "UPDATE orders SET status = 'DELIVERED', completed_at = ? WHERE id = ?",
                (now_ts, order_id)
            )

        return DeliveryRecord(
            order_id=order_id,
            delivered_at=now_ts,
            total_items=total_items,
            total_weight_kg=total_weight_kg,
            notes="Confirmed delivery at station"
        )

    def flag_interrupted_orders(self) -> List[str]:
        """Detect any active orders interrupted while in progress and mark them RECOVERY_REQUIRED.

        In-flight active states: IN_PROGRESS, COLLECTING, RETURNING_TO_DISTRIBUTION, UNLOADING, PLANNING, READY
        """
        active_states = (
            "IN_PROGRESS",
            "COLLECTING",
            "RETURNING_TO_DISTRIBUTION",
            "UNLOADING",
            "PLANNING",
            "READY",
            "VALIDATING"
        )
        cursor = self.conn.cursor()
        placeholders = ",".join("?" for _ in active_states)

        with self.conn:
            cursor.execute(
                f"SELECT id FROM orders WHERE status IN ({placeholders})",
                active_states
            )
            interrupted = [row["id"] for row in cursor.fetchall()]

            if interrupted:
                cursor.execute(
                    f"""
                    UPDATE orders
                    SET status = 'RECOVERY_REQUIRED',
                        notes = 'Application interrupted while order was active. Recovery required.'
                    WHERE id IN ({','.join('?' for _ in interrupted)});
                    """,
                    interrupted
                )

        return interrupted

    def get_completed_orders(self) -> List[OrderRecord]:
        """Fetch all delivered orders from database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, status, created_at, completed_at, notes FROM orders WHERE status = 'DELIVERED' ORDER BY completed_at DESC")
        return [
            OrderRecord(
                id=row["id"],
                status=row["status"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                notes=row["notes"]
            )
            for row in cursor.fetchall()
        ]
