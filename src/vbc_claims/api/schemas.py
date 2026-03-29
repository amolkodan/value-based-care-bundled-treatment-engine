from __future__ import annotations

from pydantic import BaseModel, Field


class AssignEpisodesRequest(BaseModel):
    run_member_months: bool = Field(default=True)
    start_month: str = Field(default="2025-01-01")
    end_month: str = Field(default="2025-12-01")


class AssignEpisodesResponse(BaseModel):
    episode_instances: int
    episode_assignments: int

