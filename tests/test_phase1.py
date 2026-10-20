"""Phase 1 Automated Tests: Repository Setup, Module Imports, and Configuration Loading.

Verifies:
- All core application modules import cleanly without side-effects.
- Valid warehouse and product JSON configuration files load properly.
- Missing and malformed configuration files raise clean, descriptive ConfigurationError exceptions.
"""

import json
import pytest
from pathlib import Path

from utils.config import (
    load_warehouse_config,
    load_products_config,
    ConfigurationError,
    WarehouseConfig,
    ProductConfig
)


def test_import_modules_cleanly():
    """Import all project packages and modules to ensure no side-effects or circular dependencies."""
    import ai
    import simulation
    import database
    import database.models
    import database.db
    import database.repositories
    import utils
    import utils.config

    assert ai is not None
    assert simulation is not None
    assert database is not None
    assert utils is not None


def test_load_valid_warehouse_config():
    """Verify that default warehouse.json loads and satisfies the 16x12 grid specification."""
    cfg = load_warehouse_config()
    assert isinstance(cfg, WarehouseConfig)
    assert cfg.grid.width == 16
    assert cfg.grid.height == 12
    assert cfg.distribution_station.id == "DS-01"
    assert cfg.distribution_station.x >= 0 and cfg.distribution_station.y >= 0
    assert cfg.robot_initial.id == "ROBOT-ALPHA"
    assert len(cfg.racks) >= 20
    assert len(cfg.fixed_obstacles) > 0


def test_load_valid_products_config():
    """Verify that default products.json loads with 20-30 products and valid attributes."""
    products = load_products_config()
    assert isinstance(products, list)
    assert 20 <= len(products) <= 30
    for prod in products:
        assert isinstance(prod, ProductConfig)
        assert prod.id.startswith("PROD-")
        assert len(prod.name) > 0
        assert prod.unit_weight_kg > 0
        assert prod.initial_stock >= 0
        assert prod.shelf_id.startswith("R")


def test_missing_warehouse_config_raises_error(tmp_path: Path):
    """Verify that non-existent warehouse configuration path raises ConfigurationError."""
    fake_path = tmp_path / "does_not_exist.json"
    with pytest.raises(ConfigurationError) as exc_info:
        load_warehouse_config(fake_path)
    assert "not found" in str(exc_info.value).lower()


def test_missing_products_config_raises_error(tmp_path: Path):
    """Verify that non-existent products configuration path raises ConfigurationError."""
    fake_path = tmp_path / "does_not_exist.json"
    with pytest.raises(ConfigurationError) as exc_info:
        load_products_config(fake_path)
    assert "not found" in str(exc_info.value).lower()


def test_malformed_json_raises_error(tmp_path: Path):
    """Verify that syntactically broken JSON raises ConfigurationError."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{ this is not valid json : ;", encoding="utf-8")

    with pytest.raises(ConfigurationError) as exc_info:
        load_warehouse_config(corrupt_file)
    assert "malformed json" in str(exc_info.value).lower()


def test_invalid_schema_structure_raises_error(tmp_path: Path):
    """Verify that JSON failing Pydantic schema validation raises ConfigurationError."""
    invalid_file = tmp_path / "invalid_schema.json"
    # Missing required 'grid' and 'distribution_station' fields
    invalid_file.write_text(json.dumps({"some_key": "some_value"}), encoding="utf-8")

    with pytest.raises(ConfigurationError) as exc_info:
        load_warehouse_config(invalid_file)
    assert "invalid warehouse configuration" in str(exc_info.value).lower()


def test_products_not_a_list_raises_error(tmp_path: Path):
    """Verify that products configuration that is a JSON object instead of a list raises error."""
    dict_file = tmp_path / "products_dict.json"
    dict_file.write_text(json.dumps({"prod_1": {}}), encoding="utf-8")

    with pytest.raises(ConfigurationError) as exc_info:
        load_products_config(dict_file)
    assert "expected a json list" in str(exc_info.value).lower()
