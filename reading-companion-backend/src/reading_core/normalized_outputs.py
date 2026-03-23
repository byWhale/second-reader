"""Cross-mechanism normalized output types for runtime comparison and evaluation."""

from __future__ import annotations

from typing import Literal, TypedDict


ReactionType = Literal["highlight", "association", "curious", "discern", "retrospect", "silent"]
ThoughtFamily = Literal["highlight", "association", "curious", "discern", "retrospect"]
CurrentReadingPhase = Literal["reading", "thinking", "searching", "fusing", "reflecting", "waiting", "preparing"]
AttentionEventKind = Literal[
    "position",
    "thought",
    "search",
    "segment_complete",
    "chapter_complete",
    "parse",
    "checkpoint",
    "waiting",
    "error",
    "transition",
]


class SearchHit(TypedDict, total=False):
    """Normalized search hit attached to reactions or search events."""

    title: str
    url: str
    snippet: str
    score: float | None


class NormalizedAttentionEvent(TypedDict, total=False):
    """One normalized attention-trace event emitted by any mechanism."""

    event_id: str
    timestamp: str
    stream: str
    kind: AttentionEventKind
    phase: CurrentReadingPhase
    message: str
    chapter_ref: str
    section_ref: str
    current_excerpt: str
    search_query: str
    thought_family: ThoughtFamily
    problem_code: str
    reading_locus: dict[str, object] | None
    move_type: str
    active_reaction_id: str


class NormalizedReaction(TypedDict, total=False):
    """One normalized visible reaction emitted from chapter outputs."""

    reaction_id: str
    type: ReactionType
    chapter_ref: str
    section_ref: str
    anchor_quote: str
    content: str
    search_query: str
    search_results: list[SearchHit]
    primary_anchor: dict[str, object] | None
    related_anchors: list[dict[str, object]]
    supersedes_reaction_id: str


class NormalizedRunSnapshot(TypedDict, total=False):
    """Mechanism-neutral snapshot of a run's current state."""

    status: str
    current_chapter_ref: str
    current_section_ref: str
    current_reading_activity: dict[str, object] | None
    current_reading_locus: dict[str, object] | None
    current_move_type: str
    reconstructed_hot_state: bool | None
    last_resume_kind: str | None
    active_reaction_id: str | None
    resume_available: bool | None
    last_checkpoint_at: str | None
    completed_chapters: int | None
    total_chapters: int | None
    eta_seconds: int | None


class NormalizedChapterOutput(TypedDict, total=False):
    """Mechanism-neutral chapter-level summary used by eval and comparison tools."""

    chapter_id: int
    chapter_ref: str
    title: str
    status: str
    section_count: int
    visible_reaction_count: int
    featured_reaction_count: int
    reflection_summary: str


class NormalizedEvalBundle(TypedDict, total=False):
    """Normalized cross-mechanism bundle for evaluation and comparison."""

    mechanism_key: str
    mechanism_label: str
    generated_at: str
    output_dir: str
    config_fingerprint: str
    run_snapshot: NormalizedRunSnapshot | None
    attention_events: list[NormalizedAttentionEvent]
    reactions: list[NormalizedReaction]
    chapters: list[NormalizedChapterOutput]
    memory_summaries: list[str]
    token_metadata: dict[str, object]
    latency_metadata: dict[str, object]
    cost_metadata: dict[str, object]
