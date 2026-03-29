"""Pydantic models for HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionOut(BaseModel):
    id: int
    title: str
    source: str
    started_at: str
    ended_at: str | None
    duration_secs: int | None
    notes: str
    session_type: str = Field(description="meeting | work_process | customer_service")
    department_id: int | None = None
    metadata: dict[str, Any] | None = None
    wbs_node_id: int | None = None
    case_id: str | None = None
    created_at: str
    updated_at: str


class SessionPatch(BaseModel):
    title: str | None = None
    session_type: str | None = None
    metadata: dict[str, Any] | None = None
    department_id: int | None = None
    wbs_node_id: int | None = None
    case_id: str | None = None


class SegmentOut(BaseModel):
    id: int
    meeting_id: int
    sequence_num: int
    text: str
    start_ms: int
    end_ms: int
    speaker_label: str | None = None
    confidence: float | None = None
    created_at: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    chat_session_id: int | None = None


class LlmSettingsOut(BaseModel):
    effective_model_id: str
    effective_max_new_tokens: int
    stored_model_id: str | None = None
    stored_max_new_tokens: int | None = None
    environment_model_id: str
    environment_max_new_tokens: int


class LlmSettingsPatch(BaseModel):
    """Partial update. Omit a field to leave it unchanged; ``null`` or empty ``model_id`` clears DB override."""

    model_id: str | None = None
    max_new_tokens: int | None = Field(default=None, ge=32, le=8192)


class SummarizeBody(BaseModel):
    """Optional body for one-shot transcript summarization."""

    max_chars: int = Field(
        default=32_000,
        ge=2_000,
        le=200_000,
        description="Max characters of concatenated transcript text to send to the LLM",
    )


def meeting_to_session_out(m) -> SessionOut:
    return SessionOut(
        id=m.id,
        title=m.title,
        source=m.source,
        started_at=m.started_at,
        ended_at=m.ended_at,
        duration_secs=m.duration_secs,
        notes=m.notes,
        session_type=m.session_type,
        department_id=m.department_id,
        metadata=m.metadata,
        wbs_node_id=m.wbs_node_id,
        case_id=m.case_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )
