"""B3A settings are explicit Python configuration, never journal/env enablement."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class CfdPracticeSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    enabled: bool = False
    api_port: Literal[8003, 8004, 8013, 8014] = 8003
    allow_creation: bool = False
    max_body_bytes: Annotated[int, Field(ge=1, le=4 * 1024 * 1024)] = 4 * 1024 * 1024
    max_json_depth: Annotated[int, Field(ge=1, le=16)] = 16
    preview_per_minute: Annotated[int, Field(ge=1, le=30)] = 30
    reads_per_minute: Annotated[int, Field(ge=1, le=120)] = 120
    request_timeout_seconds: Annotated[int, Field(ge=1, le=30)] = 30
