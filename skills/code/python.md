---
description: 'Use when writing Python code, implementing Python features, or needing Python best practices and idioms.'
---

# Python Coding Practices

Modern Python idioms (3.10+) focused on readability and type safety.

## Type Hints

### Always Annotate

```python
from collections.abc import Sequence
from typing import Optional

def process_users(
    users: Sequence[User],
    active_only: bool = True,
    limit: Optional[int] = None,
) -> list[ProcessedUser]:
    """Process users with optional filtering."""
    ...
```

### Modern Syntax (3.10+)

```python
# Use built-in generics
def get_names(users: list[User]) -> list[str]:
    return [u.name for u in users]

# Union with |
def parse(value: str | int) -> Data: ...

# Optional is just X | None
def find(id: int) -> User | None: ...
```

## Data Classes

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Order:
    id: str
    items: list[Item]
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total(self) -> Decimal:
        return sum(item.price for item in self.items)

# Frozen (Immutable)
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

## Pydantic for Validation

```python
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

## Pattern Matching (3.10+)

```python
match response:
    case {"status": 200, "data": data}:
        return process(data)
    case {"status": 404}:
        raise NotFoundError()
    case {"status": status} if status >= 500:
        raise ServerError(status)
    case _:
        raise UnknownResponse()
```

## Context Managers

```python
from contextlib import contextmanager

@contextmanager
def database_transaction(db):
    tx = db.begin()
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise
```

## Clean Exports

```python
# myapp/models/__init__.py
from .user import User, UserCreate
from .order import Order, OrderItem

__all__ = ['User', 'UserCreate', 'Order', 'OrderItem']
```

## Error Handling

```python
class AppError(Exception):
    """Base exception for application."""

class ValidationError(AppError):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")
```

### Exception Chaining

```python
try:
    result = external_api.call()
except ApiError as e:
    raise ProcessingError(f"Failed to process: {e}") from e
```

## Async/Await

```python
async def fetch_all_users(ids: list[int]) -> list[User]:
    tasks = [fetch_user(id) for id in ids]
    return await asyncio.gather(*tasks)

# TaskGroup (3.11+)
async with asyncio.TaskGroup() as tg:
    for item in items:
        tg.create_task(process_item(item))
```

## Logging

Always use logging, especially for desktop/non-terminal apps:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting operation: %s", name)
logger.exception("Failed")  # includes traceback
```

**Never use `print()` for logging** — no visibility in bundled apps.

## Forbidden

Never commit:
- `# noqa` without explanation
- `# type: ignore` without explanation
- Bare `except:` (always specify exception type)
- `print()` for logging (use `logger`)
- Silent exception swallowing
