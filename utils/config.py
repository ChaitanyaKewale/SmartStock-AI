"""Configuration loading and validation module for SmartStock AI.

Validates warehouse layout and product catalog using Pydantic schemas,
handling missing or malformed files with descriptive errors without raw tracebacks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_WAREHOUSE_FILE = DEFAULT_DATA_DIR / "warehouse.json"
DEFAULT_PRODUCTS_FILE = DEFAULT_DATA_DIR / "products.json"


class ConfigurationError(Exception):
    """Raised when configuration files are missing, malformed, or invalid."""
    pass


class GridConfig(BaseModel):
    width: int = Field(gt=0, description="Warehouse grid width (columns)")
    height: int = Field(gt=0, description="Warehouse grid height (rows)")


class PositionConfig(BaseModel):
    x: int = Field(ge=0, description="0-indexed x coordinate")
    y: int = Field(ge=0, description="0-indexed y coordinate")


class DistributionStationConfig(BaseModel):
    id: str
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    facing: str = "SOUTH"


class RobotInitialConfig(BaseModel):
    id: str
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    facing: str = "SOUTH"
    max_capacity_kg: float = Field(gt=0.0, default=25.0)


class RackConfig(BaseModel):
    id: str
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    pickup_position: PositionConfig
    zone: str
    max_capacity: int = Field(gt=0, default=50)


class ObstacleConfig(BaseModel):
    id: str
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class RestrictedZoneConfig(BaseModel):
    id: str
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    reason: Optional[str] = ""


class WarehouseConfig(BaseModel):
    grid: GridConfig
    distribution_station: DistributionStationConfig
    robot_initial: RobotInitialConfig
    racks: List[RackConfig] = Field(default_factory=list)
    fixed_obstacles: List[ObstacleConfig] = Field(default_factory=list)
    restricted_zones: List[RestrictedZoneConfig] = Field(default_factory=list)


class ProductConfig(BaseModel):
    id: str
    name: str
    category: str
    unit_weight_kg: float = Field(gt=0.0)
    shelf_id: str
    initial_stock: int = Field(ge=0)
    active: bool = True


def load_warehouse_config(file_path: Path | str | None = None) -> WarehouseConfig:
    """Load and validate the warehouse JSON configuration.

    Args:
        file_path: Optional custom path to warehouse.json.

    Returns:
        Validated WarehouseConfig instance.

    Raises:
        ConfigurationError: If the file does not exist, contains invalid JSON,
                            or fails schema validation.
    """
    path = Path(file_path) if file_path is not None else DEFAULT_WAREHOUSE_FILE
    if not path.is_file():
        raise ConfigurationError(f"Warehouse configuration file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Malformed JSON in warehouse configuration ({path}): {exc}") from exc
    except Exception as exc:
        raise ConfigurationError(f"Failed to read warehouse configuration ({path}): {exc}") from exc

    try:
        return WarehouseConfig.model_validate(raw_data)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid warehouse configuration structure in {path}: {exc}") from exc


def load_products_config(file_path: Path | str | None = None) -> List[ProductConfig]:
    """Load and validate the products JSON configuration.

    Args:
        file_path: Optional custom path to products.json.

    Returns:
        List of validated ProductConfig instances.

    Raises:
        ConfigurationError: If the file does not exist, contains invalid JSON,
                            or fails schema validation.
    """
    path = Path(file_path) if file_path is not None else DEFAULT_PRODUCTS_FILE
    if not path.is_file():
        raise ConfigurationError(f"Products configuration file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Malformed JSON in products configuration ({path}): {exc}") from exc
    except Exception as exc:
        raise ConfigurationError(f"Failed to read products configuration ({path}): {exc}") from exc

    if not isinstance(raw_data, list):
        raise ConfigurationError(f"Expected a JSON list of products in {path}, got {type(raw_data).__name__}")

    try:
        return [ProductConfig.model_validate(item) for item in raw_data]
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid product schema in {path}: {exc}") from exc
