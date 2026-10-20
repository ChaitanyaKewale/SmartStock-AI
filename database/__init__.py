"""Database package for SmartStock AI SQLite persistence."""

from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.models import (
    ProductRecord,
    InventoryRecord,
    OrderRecord,
    OrderLineRecord,
    TransactionRecord,
    DeliveryRecord,
    DurableEventRecord
)
from database.repositories import (
    InventoryRepository,
    OrderRepository,
    PersistenceError,
    InsufficientStockError,
    DeliveryError
)

__all__ = [
    "get_db_connection",
    "init_db",
    "seed_catalog_if_empty",
    "ProductRecord",
    "InventoryRecord",
    "OrderRecord",
    "OrderLineRecord",
    "TransactionRecord",
    "DeliveryRecord",
    "DurableEventRecord",
    "InventoryRepository",
    "OrderRepository",
    "PersistenceError",
    "InsufficientStockError",
    "DeliveryError"
]
