import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    repository_url: str
    git_username: str
    git_password: str


class RepositoryGetRequest(BaseModel):
    repository_id: uuid.UUID


class RepositoryUpdate(BaseModel):
    repository_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=150)
    repository_url: str | None = None
    git_username: str | None = None
    git_password: str | None = None
    is_active: bool | None = None


class RepositoryDeleteRequest(BaseModel):
    repository_id: uuid.UUID


class RepositoryCloneRequest(BaseModel):
    repository_id: uuid.UUID


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    repository_url: str
    git_username: str
    local_path: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class CloneRepositoryResponse(BaseModel):
    message: str
    repository_id: uuid.UUID
    local_path: str