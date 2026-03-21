"""Mechanism-neutral runtime contracts and shared backend envelope types."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, TypedDict

from .book_document import BookDocument
from .normalized_outputs import NormalizedEvalBundle, ReactionType


ReadTaskMode = Literal["sequential", "book_analysis"]
MarkType = Literal["resonance", "blindspot", "bookmark"]
JobStatus = Literal["queued", "parsing_structure", "ready", "deep_reading", "chapter_note_generation", "paused", "completed", "error"]
JobKind = Literal["parse", "read"]
CurrentReadingProblemCode = Literal[
    "llm_timeout",
    "llm_quota",
    "llm_auth",
    "search_timeout",
    "search_quota",
    "search_auth",
    "network_blocked",
]


class UserMark(TypedDict):
    """Persisted user mark attached to one frontend-visible reaction."""

    reaction_id: str
    book_id: str
    book_title: str
    chapter_id: int
    chapter_ref: str
    segment_ref: str
    reaction_type: ReactionType
    mark_type: MarkType
    reaction_excerpt: str
    anchor_quote: str
    created_at: str
    updated_at: str


class UserMarksState(TypedDict):
    """Top-level single-user mark store."""

    updated_at: str
    marks: dict[str, UserMark]


class JobRecord(TypedDict):
    """Background job record shared across backend surfaces."""

    job_id: str
    status: JobStatus
    job_kind: JobKind
    upload_path: str
    book_id: str | None
    language: str
    intent: str | None
    resume_count: int
    pid: int | None
    created_at: str
    updated_at: str
    error: str | None


@dataclass(frozen=True)
class MechanismInfo:
    """Stable identity for one registered reading mechanism."""

    key: str
    label: str
    is_default: bool = False


@dataclass(frozen=True)
class ParseRequest:
    """Mechanism-neutral parse request routed through the runtime shell."""

    book_path: Path
    language_mode: str = "auto"
    continue_mode: bool = False
    mechanism_key: str | None = None
    mechanism_config: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    """Result envelope for one mechanism parse pass."""

    mechanism: MechanismInfo
    book_document: BookDocument
    output_dir: Path
    created: bool = False
    mechanism_artifact: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ReadRequest:
    """Mechanism-neutral read request routed through the runtime shell."""

    book_path: Path
    chapter_number: int | None = None
    continue_mode: bool = False
    user_intent: str | None = None
    language_mode: str = "auto"
    task_mode: ReadTaskMode = "sequential"
    mechanism_key: str | None = None
    mechanism_config: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadResult:
    """Result envelope for one mechanism read run."""

    mechanism: MechanismInfo
    book_document: BookDocument
    output_dir: Path
    created: bool = False
    mechanism_artifact: Mapping[str, object] | None = None
    normalized_eval_bundle: NormalizedEvalBundle | None = None


def stable_config_fingerprint(payload: Mapping[str, object] | object) -> str:
    """Return a stable short fingerprint for mechanism config and run settings."""

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
