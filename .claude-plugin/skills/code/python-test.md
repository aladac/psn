---
description: 'Use when writing Python tests, setting up pytest, creating fixtures, or implementing test patterns in Python.'
---

# Python Testing

Comprehensive guide to testing Python with pytest.

## Installation

```bash
pip install pytest pytest-cov pytest-xdist pytest-asyncio
```

## Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-ra",                    # Show extra summary
    "--strict-markers",       # Error on unknown markers
    "--strict-config",        # Error on bad config
    "-v",                     # Verbose
]
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
```

## Structure (Readable First)

```python
# tests/test_order.py
import pytest
from myapp.order import Order, OrderItem

class TestOrder:
    """Tests for Order class."""

    class TestApplyDiscount:
        """Tests for apply_discount method."""

        def test_reduces_total_by_percentage(self):
            order = Order(items=[OrderItem(price=100)])

            order.apply_discount(10)

            assert order.total == 90

        def test_does_not_modify_total_below_threshold(self):
            order = Order(items=[OrderItem(price=50)])

            order.apply_discount(10)

            assert order.total == 50  # Threshold is 100

        def test_raises_for_negative_percentage(self):
            order = Order(items=[OrderItem(price=100)])

            with pytest.raises(ValueError, match="positive"):
                order.apply_discount(-5)
```

## Fixtures

```python
# tests/conftest.py
import pytest
from myapp.database import Database
from myapp.models import User

@pytest.fixture
def db():
    """Provide test database connection."""
    database = Database(":memory:")
    database.create_tables()
    yield database
    database.close()

@pytest.fixture
def user(db):
    """Provide test user."""
    return User.create(db, name="Alice", email="alice@example.com")

@pytest.fixture(scope="module")
def expensive_resource():
    """Shared across all tests in module."""
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

## Parametrized Tests

```python
@pytest.mark.parametrize("discount,expected", [
    (0, 100),
    (10, 90),
    (50, 50),
    (100, 0),
])
def test_apply_discount(discount, expected):
    order = Order(items=[OrderItem(price=100)])
    order.apply_discount(discount)
    assert order.total == expected

@pytest.mark.parametrize("invalid_input", ["", "   ", None])
def test_rejects_invalid_input(invalid_input):
    with pytest.raises(ValueError):
        parse_name(invalid_input)
```

## Mocking

```python
from unittest.mock import Mock, patch, MagicMock

def test_sends_notification():
    notifier = Mock()
    service = OrderService(notifier=notifier)

    service.complete_order(order_id=123)

    notifier.send.assert_called_once_with(
        user_id=order.user_id,
        message="Order 123 completed"
    )

@patch("myapp.services.external_api")
def test_handles_api_failure(mock_api):
    mock_api.fetch.side_effect = ConnectionError("Network down")

    result = fetch_user_data(user_id=1)

    assert result is None
```

## Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    client = AsyncClient()

    result = await client.fetch("/users/1")

    assert result["id"] == 1
```

## Commands

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_order.py

# Run specific test
pytest tests/test_order.py::TestOrder::test_apply_discount

# Run by marker
pytest -m "not slow"
pytest -m integration

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Parallel execution
pytest -n auto

# Stop on first failure
pytest -x

# Re-run failed tests
pytest --lf
```

## Test File Mirroring

```
# Source                      # Test
src/users/service.py        → tests/users/test_service.py
src/orders/validator.py     → tests/orders/test_validator.py
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
- name: Test
  run: pytest --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v4
```

## Makefile

```makefile
test:
    pytest

test-cov:
    pytest --cov=src --cov-report=term-missing

test-fast:
    pytest -x -n auto
```

## Summary

| Command | Purpose |
|---------|---------|
| `pytest` | Run all tests |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run last failed |
| `pytest -n auto` | Run parallel |
| `pytest --cov=src` | With coverage |
| `pytest -m "not slow"` | Skip slow tests |
