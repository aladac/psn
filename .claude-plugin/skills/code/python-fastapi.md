---
description: 'Use when building FastAPI applications, creating Python APIs, or implementing async web services in Python.'
---

# Python FastAPI Development

Modern async Python API development with FastAPI.

## Project Structure

```
myapi/
├── src/
│   └── myapi/
│       ├── __init__.py
│       ├── main.py           # FastAPI app
│       ├── config.py         # Settings
│       ├── models/           # Pydantic models
│       │   ├── __init__.py
│       │   └── user.py
│       ├── routes/           # Route handlers
│       │   ├── __init__.py
│       │   └── users.py
│       ├── services/         # Business logic
│       │   └── user_service.py
│       └── dependencies.py   # Dependency injection
├── tests/
│   ├── conftest.py
│   └── test_users.py
└── pyproject.toml
```

## Main Application

```python
# src/myapi/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from myapi.routes import users
from myapi.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users.router, prefix="/api/v1", tags=["users"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

## Pydantic Models

```python
# src/myapi/models/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None

class User(UserBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

class UserList(BaseModel):
    data: list[User]
    total: int
    page: int
    per_page: int
```

## Routes

```python
# src/myapi/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated

from myapi.models.user import User, UserCreate, UserUpdate, UserList
from myapi.services.user_service import UserService
from myapi.dependencies import get_user_service, get_current_user

router = APIRouter()

@router.get("/users", response_model=UserList)
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    users, total = await service.list(page=page, per_page=per_page)
    return UserList(data=users, total=total, page=page, per_page=per_page)

@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)],
):
    user = await service.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.create(user_data)

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    user = await service.update(user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)],
):
    await service.delete(user_id)
```

## Dependency Injection

```python
# src/myapi/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from myapi.services.user_service import UserService
from myapi.database import get_db

security = HTTPBearer()

async def get_user_service(db = Depends(get_db)) -> UserService:
    return UserService(db)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    user = await service.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return user
```

## Configuration

```python
# src/myapi/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MyAPI"
    debug: bool = False
    database_url: str
    secret_key: str

    model_config = {"env_file": ".env"}

settings = Settings()
```

## Service Layer

```python
# src/myapi/services/user_service.py
from myapi.models.user import User, UserCreate, UserUpdate

class UserService:
    def __init__(self, db):
        self.db = db

    async def list(self, page: int, per_page: int) -> tuple[list[User], int]:
        offset = (page - 1) * per_page
        users = await self.db.fetch_all(
            "SELECT * FROM users LIMIT :limit OFFSET :offset",
            {"limit": per_page, "offset": offset}
        )
        total = await self.db.fetch_val("SELECT COUNT(*) FROM users")
        return [User.model_validate(u) for u in users], total

    async def get(self, user_id: int) -> User | None:
        row = await self.db.fetch_one(
            "SELECT * FROM users WHERE id = :id",
            {"id": user_id}
        )
        return User.model_validate(row) if row else None

    async def create(self, data: UserCreate) -> User:
        # ... implementation
        pass
```

## Testing

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from myapi.main import app

@pytest.fixture
def client():
    return TestClient(app)

# tests/test_users.py
def test_list_users(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert "data" in response.json()

def test_create_user(client):
    response = client.post("/api/v1/users", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "securepassword123"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"

def test_get_user_not_found(client):
    response = client.get("/api/v1/users/999999")
    assert response.status_code == 404
```

## pyproject.toml

```toml
[project]
name = "myapi"
version = "0.1.0"
dependencies = [
    "fastapi>=0.109",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.6",
    "pydantic-settings>=2.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.26"]

[project.scripts]
myapi = "myapi.main:app"
```

## Running

```bash
# Development
uvicorn myapi.main:app --reload

# Production
uvicorn myapi.main:app --host 0.0.0.0 --port 8000 --workers 4

# View docs
open http://localhost:8000/docs     # Swagger UI
open http://localhost:8000/redoc    # ReDoc
```

## Summary

| Component | Purpose |
|-----------|---------|
| FastAPI | Framework |
| Pydantic | Validation, serialization |
| Depends | Dependency injection |
| HTTPException | Error responses |
| TestClient | Testing |
| uvicorn | ASGI server |
