"""Typed structures for the Iterator-Reader workflow."""

from __future__ import annotations

from typing import Literal, TypedDict


ChapterStatus = Literal["pending", "in_progress", "done"]
ReadMode = Literal["sequential", "book_analysis"]
ReaderDecision = Literal["pass", "revise", "skip"]
ReactionType = Literal["highlight", "association", "curious", "discern", "connect_back", "silent"]
SkillProfileName = Literal["balanced", "analytical", "curious", "quiet"]
ClaimType = Literal["main", "support", "assumption", "counter"]
EvidenceStatus = Literal["covered", "gap", "disputed"]
ReasonCode = Literal[
    "LOW_SELECTIVITY",
    "WEAK_ASSOCIATION",
    "LOW_ATTRIBUTION_CONFIDENCE",
    "WEAK_TEXT_CONNECTION",
    "LOW_DEPTH",
    "NO_CONCRETE_DISCERN",
    "NO_EXPLICIT_CALLBACK",
    "OVER_EXTENDED",
    "INSUFFICIENT_EVIDENCE",
    "OTHER",
]
SegmentStatus = Literal["pending", "done", "skipped"]
QualityStatus = Literal["strong", "acceptable", "weak", "skipped"]
RunStage = Literal["ready", "deep_reading", "completed", "error"]
MatchMode = Literal["exact", "normalized", "segment_fallback"]
MarkType = Literal["known", "blindspot"]
JobStatus = Literal["queued", "parsing_structure", "deep_reading", "chapter_note_generation", "completed", "error"]


class SourceAsset(TypedDict):
    """Frontend-facing source asset descriptor."""

    format: Literal["epub"]
    file: str


class ParagraphLocator(TypedDict, total=False):
    """Paragraph-level locator retained to derive reaction anchors."""

    href: str
    start_cfi: str | None
    end_cfi: str | None
    paragraph_index: int
    text: str


class SegmentLocator(TypedDict, total=False):
    """Stable segment-level EPUB locator."""

    href: str
    start_cfi: str | None
    end_cfi: str | None
    paragraph_start: int
    paragraph_end: int


class ReactionTargetLocator(TypedDict, total=False):
    """Frontend-facing locator for one reaction anchor."""

    href: str
    start_cfi: str | None
    end_cfi: str | None
    match_text: str
    match_mode: MatchMode


class SemanticSegmentBase(TypedDict):
    """A semantically coherent unit inside a chapter."""

    id: str
    summary: str
    tokens: int
    text: str
    paragraph_start: int
    paragraph_end: int
    status: SegmentStatus


class SemanticSegment(SemanticSegmentBase, total=False):
    """A semantically coherent unit inside a chapter."""

    segment_ref: str
    locator: SegmentLocator
    paragraph_locators: list[ParagraphLocator]


class StructureChapterBase(TypedDict):
    """Persisted chapter definition in structure.json."""

    id: int
    title: str
    status: ChapterStatus
    level: int
    segments: list[SemanticSegment]


class StructureChapter(StructureChapterBase, total=False):
    """Persisted chapter definition in structure.json."""

    chapter_number: int
    output_file: str
    item_id: str
    href: str
    spine_index: int


class BookStructure(TypedDict):
    """Persisted structure.json format."""

    book: str
    author: str
    book_language: str
    output_language: str
    source_file: str
    output_dir: str
    chapters: list[StructureChapter]


class ManifestChapterEntry(TypedDict, total=False):
    """Frontend-facing chapter summary in book_manifest.json."""

    id: int
    title: str
    chapter_number: int
    reference: str
    status: ChapterStatus
    segment_count: int
    markdown_file: str
    result_file: str
    visible_reaction_count: int
    reaction_type_diversity: int
    high_signal_reaction_count: int


class BookManifest(TypedDict):
    """Stable book-level summary for frontend consumption."""

    book_id: str
    book: str
    author: str
    cover_image_url: str | None
    book_language: str
    output_language: str
    source_file: str
    source_asset: SourceAsset
    updated_at: str
    chapters: list[ManifestChapterEntry]


class RunState(TypedDict):
    """Sequential run status persisted for the frontend."""

    mode: Literal["sequential"]
    stage: RunStage
    book: str
    current_chapter_id: int | None
    current_chapter_ref: str | None
    current_segment_ref: str | None
    completed_chapters: int
    total_chapters: int
    eta_seconds: int | None
    updated_at: str
    error: str | None


class ActivityEvent(TypedDict, total=False):
    """One user-facing activity item in activity.jsonl."""

    event_id: str
    timestamp: str
    type: str
    message: str
    chapter_id: int
    chapter_ref: str
    segment_id: str
    segment_ref: str
    reaction_types: list[str]
    highlight_quote: str
    search_query: str
    visible_reaction_count: int
    high_signal_reaction_count: int
    featured_reactions: list[dict[str, object]]
    result_file: str
    result_url: str


class ReaderMemory(TypedDict):
    """Running memory carried across semantic units in one read session."""

    prior_segment_summaries: list[str]
    notable_findings: list[str]
    open_threads: list[str]
    highlighted_quotes: list[str]


class ThoughtPayload(TypedDict):
    """Think node output."""

    should_express: bool
    selected_excerpt: str
    reason: str
    connections: list[str]
    curiosities: list[str]
    curiosity_potential: int


class SearchHit(TypedDict):
    """Normalized Tavily hit used by the reader."""

    title: str
    url: str
    snippet: str
    score: float | None


class ReactionPayload(TypedDict, total=False):
    """One reading reaction produced by Express."""

    type: ReactionType
    anchor_quote: str
    content: str
    search_query: str
    search_results: list[SearchHit]


class ChapterResultReaction(TypedDict, total=False):
    """Frontend-facing reaction payload in chapter_result.json."""

    reaction_id: str
    type: ReactionType
    anchor_quote: str
    content: str
    search_query: str
    search_results: list[SearchHit]
    target_locator: ReactionTargetLocator


class SearchResultPayload(TypedDict, total=False):
    """A curiosity-driven search execution record."""

    reaction_indexes: list[int]
    search_query: str
    results: list[SearchHit]
    error: str


class ReflectionPayload(TypedDict):
    """Reflect node output."""

    verdict: ReaderDecision
    summary: str
    selectivity: int
    association_quality: int
    attribution_reasonableness: int
    text_connection: int
    depth: int
    issues: list[str]
    reason_codes: list[ReasonCode]
    target_reaction_indexes: list[int]
    revision_instruction: str


class RenderedSegmentBase(TypedDict):
    """Final per-segment payload used for markdown rendering."""

    segment_id: str
    summary: str
    verdict: ReaderDecision
    reactions: list[ReactionPayload]
    reflection_summary: str
    reflection_reason_codes: list[ReasonCode]


class RenderedSegment(RenderedSegmentBase, total=False):
    """Final per-segment payload used for markdown rendering."""

    segment_ref: str
    quality_status: QualityStatus
    skip_reason: str


class ChapterResultChapter(TypedDict, total=False):
    """Frontend-facing chapter metadata for one companion result file."""

    id: int
    title: str
    chapter_number: int
    reference: str
    status: ChapterStatus


class ChapterResultSection(TypedDict, total=False):
    """One rendered section in a chapter companion JSON file."""

    segment_id: str
    segment_ref: str
    summary: str
    original_text: str
    verdict: ReaderDecision
    quality_status: QualityStatus
    skip_reason: str
    reflection_summary: str
    reflection_reason_codes: list[ReasonCode]
    locator: SegmentLocator
    reactions: list[ChapterResultReaction]


class FeaturedReaction(TypedDict, total=False):
    """Compact high-signal reaction summary for chapter cards and events."""

    reaction_id: str
    type: ReactionType
    segment_ref: str
    anchor_quote: str
    content: str
    target_locator: ReactionTargetLocator


class ChapterResultUISummary(TypedDict):
    """Small aggregate summary for frontend result views."""

    kept_section_count: int
    skipped_section_count: int
    reaction_counts: dict[str, int]


class ChapterResult(TypedDict):
    """Stable per-chapter companion JSON payload."""

    chapter: ChapterResultChapter
    output_language: str
    generated_at: str
    sections: list[ChapterResultSection]
    chapter_reflection: dict[str, object]
    featured_reactions: list[FeaturedReaction]
    visible_reaction_count: int
    reaction_type_diversity: int
    high_signal_reaction_count: int
    ui_summary: ChapterResultUISummary


class BookAnalysisPolicy(TypedDict):
    """Execution policy for full-book analysis mode."""

    deep_target_ratio: float
    min_deep_per_chapter: int
    max_core_claims: int
    max_web_queries: int
    max_queries_per_claim: int
    reuse_existing_notes: bool


class SegmentSkimCard(TypedDict, total=False):
    """One skim card generated for a semantic segment."""

    chapter_id: int
    segment_id: str
    segment_ref: str
    segment_summary: str
    skim_summary: str
    candidate_claims: list[str]
    importance_score: float
    controversy_score: float
    evidence_gap_score: float
    intent_relevance_score: float
    needs_deep_read: bool
    reason: str
    fallback: bool


class ClaimCard(TypedDict, total=False):
    """One synthesized claim in book-level analysis."""

    claim_id: str
    statement: str
    claim_type: ClaimType
    anchors: list[str]
    confidence: float
    evidence_status: EvidenceStatus
    search_queries: list[str]
    sources: list[SearchHit]
    insufficient_evidence: bool


class BookAnalysisState(TypedDict):
    """Mutable state passed across book analysis phases."""

    skim_cards: list[SegmentSkimCard]
    claim_cards: list[ClaimCard]
    deep_targets: list[dict[str, object]]
    web_tasks: list[dict[str, object]]
    deep_dossiers: list[dict[str, object]]
    chapter_arc: list[dict[str, object]]
    report_payload: dict[str, object]


class SkillPolicy(TypedDict):
    """Pluggable skill policy for reaction controls."""

    profile: SkillProfileName
    enabled_reactions: list[ReactionType]
    max_reactions_per_segment: int
    max_curious_reactions: int


class BudgetPolicy(TypedDict):
    """Budget controls for per-segment/per-chapter execution."""

    max_search_queries_per_segment: int
    max_search_queries_per_chapter: int
    segment_timeout_seconds: int
    max_revisions: int
    token_budget_ratio: float
    slice_target_tokens: int
    slice_max_tokens: int
    slice_max_subsegments: int


class ReaderBudget(TypedDict):
    """Mutable budget counters shared across one segment execution."""

    search_queries_remaining_in_chapter: int
    search_queries_remaining_in_segment: int
    segment_timeout_seconds: int
    segment_timed_out: bool
    early_stop: bool
    token_budget_ratio: float
    slice_target_tokens: int
    slice_max_tokens: int
    slice_max_subsegments: int
    work_units_remaining: int


class ReaderState(TypedDict):
    """LangGraph state for the inner Reader agent."""

    chapter_title: str
    segment_id: str
    segment_ref: str
    segment_summary: str
    segment_text: str
    user_intent: str | None
    output_language: str
    memory: ReaderMemory
    read_packet: str
    thought: ThoughtPayload | None
    reactions: list[ReactionPayload]
    search_results: list[SearchResultPayload]
    reflection: ReflectionPayload | None
    revision_count: int
    max_revisions: int
    revision_instruction: str
    skill_policy: SkillPolicy
    budget: ReaderBudget
    chapter_reflection: dict[str, object] | None
    segment_quality_flags: list[dict[str, str]]


class UserMark(TypedDict):
    """Persisted user mark attached to one frontend reaction."""

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
    """Top-level user mark store."""

    updated_at: str
    marks: dict[str, UserMark]


class JobRecord(TypedDict):
    """Background sequential-read job state."""

    job_id: str
    status: JobStatus
    upload_path: str
    book_id: str | None
    pid: int | None
    created_at: str
    updated_at: str
    error: str | None
