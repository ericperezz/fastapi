import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from datetime import datetime


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
    current_branch: str | None = None
    local_commit: str | None = None
    remote_commit: str | None = None
    has_local_changes: bool = False
    has_remote_changes: bool = False


class RepositoryStatusRequest(BaseModel):
    repository_id: uuid.UUID


class RepositoryStatusResponse(BaseModel):
    repository_id: uuid.UUID
    local_path: str | None = None
    is_cloned: bool
    current_branch: str | None = None
    local_commit: str | None = None
    remote_commit: str | None = None
    has_local_changes: bool
    has_remote_changes: bool
    message: str


class RepositoryRunTestsRequest(BaseModel):
    repository_id: uuid.UUID
    pull_before_tests: bool = True


class RepositoryRunTestsResponse(BaseModel):
    test_run_id: uuid.UUID | None = None
    repository_id: uuid.UUID
    local_path: str | None = None
    tests_ran: bool
    success: bool | None = None
    status: str
    has_local_changes: bool
    has_remote_changes: bool
    docker_image: str | None = None
    command: str | None = None
    exit_code: int | None = None
    duration_seconds: float | None = None
    stdout: str | None = None
    stderr: str | None = None
    finished_at: datetime | None = None
    message: str