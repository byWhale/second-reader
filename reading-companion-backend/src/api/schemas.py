"""Pydantic schemas for the Deep Read Agent REST and WebSocket API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.api.contract import MARK_TYPES, REACTION_FILTERS, REACTION_TYPES


ReactionType = Literal[
    REACTION_TYPES[0],
    REACTION_TYPES[1],
    REACTION_TYPES[2],
    REACTION_TYPES[3],
    REACTION_TYPES[4],
]
ReactionFilter = Literal[
    REACTION_FILTERS[0],
    REACTION_FILTERS[1],
    REACTION_FILTERS[2],
    REACTION_FILTERS[3],
    REACTION_FILTERS[4],
    REACTION_FILTERS[5],
]
MarkType = Literal[MARK_TYPES[0], MARK_TYPES[1], MARK_TYPES[2]]
JobLifecycleStatus = Literal[
    "queued",
    "parsing_structure",
    "ready",
    "deep_reading",
    "chapter_note_generation",
    "paused",
    "completed",
    "error",
]


class ApiModel(BaseModel):
    """Base model with strict extra-field handling."""

    model_config = ConfigDict(extra="forbid")


class PageInfo(ApiModel):
    """Cursor pagination metadata."""

    limit: int = Field(description="The page size used for this response.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for the next page, or null when there are no more results.",
    )
    has_more: bool = Field(description="Whether another page of results is available.")


class ErrorResponse(ApiModel):
    """Stable error envelope returned by every REST failure."""

    error_id: str = Field(description="Server-generated identifier for this specific error instance.")
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable explanation of the failure.")
    status: int = Field(description="HTTP status code returned with this error.")
    retryable: bool = Field(description="Whether retrying the same request may succeed.")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional structured context for debugging or client-side branching.",
    )


class SearchHit(ApiModel):
    """One external search result attached to a reaction."""

    title: str = Field(description="Title of the external source.")
    url: str = Field(description="Canonical URL of the external source.")
    snippet: str = Field(description="Short source snippet shown to the user.")
    score: Optional[float] = Field(default=None, description="Optional retrieval relevance score.")


class SourceAsset(ApiModel):
    """Frontend-accessible source book asset."""

    format: str = Field(description="Source asset format. This version uses epub.")
    url: str = Field(description="API URL serving the source asset.")
    media_type: str = Field(description="MIME type returned by the asset endpoint.")


class SegmentLocator(ApiModel):
    """Section-level EPUB locator used by the reader."""

    href: str = Field(description="EPUB spine document href for this section.")
    start_cfi: Optional[str] = Field(default=None, description="Start EPUB CFI for the section.")
    end_cfi: Optional[str] = Field(default=None, description="End EPUB CFI for the section.")
    paragraph_start: Optional[int] = Field(
        default=None,
        description="First paragraph index covered by the section inside the source document.",
    )
    paragraph_end: Optional[int] = Field(
        default=None,
        description="Last paragraph index covered by the section inside the source document.",
    )


class ChapterHeadingBlock(ApiModel):
    """Structured chapter-heading metadata kept outside body sections."""

    label: Optional[str] = Field(default=None, description="Optional chapter label, such as Chapter 1.")
    title: str = Field(description="Primary visible heading text for the chapter.")
    subtitle: Optional[str] = Field(default=None, description="Optional subtitle or secondary heading line.")
    text: str = Field(description="Combined heading text shown to the user when needed.")
    locator: Optional[SegmentLocator] = Field(
        default=None,
        description="EPUB locator for the chapter heading block when the source exposes one.",
    )


class ReactionTargetLocator(ApiModel):
    """Reaction-level locator used for precise jump/highlight behavior."""

    href: str = Field(description="EPUB spine document href for the reaction target.")
    start_cfi: Optional[str] = Field(default=None, description="Preferred start EPUB CFI for the target.")
    end_cfi: Optional[str] = Field(default=None, description="Preferred end EPUB CFI for the target.")
    match_text: str = Field(description="Anchor text used to verify the target match in the reader.")
    match_mode: Literal["exact", "normalized", "segment_fallback"] = Field(
        description="How the target locator was resolved from the anchor quote.",
    )


class FeaturedReactionPreview(ApiModel):
    """Compact reaction payload used in teasers, cards, and realtime summaries."""

    reaction_id: int = Field(description="Stable public integer identifier for the reaction.")
    type: ReactionType = Field(description="Reaction type key.")
    anchor_quote: str = Field(description="Quoted anchor text from the source book.")
    content: str = Field(description="AI-authored reaction text shown to the user.")
    book_id: int = Field(description="Stable public integer identifier of the book that owns this reaction.")
    chapter_id: int = Field(description="Chapter identifier that owns this reaction.")
    chapter_ref: str = Field(description="Human-readable chapter reference, such as Chapter 3.")
    section_ref: str = Field(description="Human-readable section reference, such as 3.2.")
    target_locator: Optional[ReactionTargetLocator] = Field(
        default=None,
        description="Reader locator used to jump to the source passage for this reaction.",
    )


class BookShelfCard(ApiModel):
    """One bookshelf card."""

    book_id: int = Field(description="Stable public integer identifier of the book.")
    title: str = Field(description="Title of the book.")
    author: str = Field(description="Author of the book.")
    cover_image_url: Optional[str] = Field(default=None, description="Optional API URL for the book cover image.")
    book_language: str = Field(description="Detected primary language of the source book.")
    output_language: str = Field(description="Language used for the AI-generated reading output.")
    reading_status: Literal["not_started", "analyzing", "paused", "completed", "error"] = Field(
        description="Current high-level reading state used by the bookshelf.",
    )
    completed_chapters: int = Field(description="Number of finished chapters.")
    total_chapters: int = Field(description="Total number of chapters in the parsed book.")
    updated_at: str = Field(description="Last artifact update time for this book.")
    mark_count: int = Field(description="Number of user marks attached to this book.")
    open_target: str = Field(description="Frontend route opened when the card is clicked.")


class BooksPageResponse(ApiModel):
    """Paginated bookshelf response."""

    items: list[BookShelfCard] = Field(description="Bookshelf cards for the current page.")
    page_info: PageInfo = Field(description="Pagination metadata for the bookshelf query.")
    global_mark_count: int = Field(description="Total number of marks across all books.")


class JobAcceptedResponse(ApiModel):
    """Common response returned after a background job is accepted."""

    job_id: str = Field(description="Identifier of the newly created analysis job.")
    status: JobLifecycleStatus = Field(description="Initial job status immediately after the request is accepted.")
    book_id: Optional[int] = Field(
        default=None,
        description="Resolved public integer book identifier if already known; otherwise null.",
    )
    job_url: str = Field(description="REST URL used to poll the job status.")
    ws_url: str = Field(description="WebSocket URL used to subscribe to live job updates.")


class UploadAcceptedResponse(JobAcceptedResponse):
    """Response returned after an EPUB upload is accepted."""

    upload_filename: str = Field(description="Original filename supplied by the client.")


class AnalysisStartAcceptedResponse(JobAcceptedResponse):
    """Response returned after starting analysis for an existing uploaded book."""


class AnalysisResumeAcceptedResponse(JobAcceptedResponse):
    """Response returned after resuming a paused analysis job."""


class JobStatusResponse(ApiModel):
    """Snapshot of one background sequential-read job."""

    job_id: str = Field(description="Job identifier.")
    status: JobLifecycleStatus = Field(
        description="Current execution stage of the upload/analysis job.",
    )
    book_id: Optional[int] = Field(default=None, description="Resolved public integer book identifier once structure parsing finishes.")
    book_title: Optional[str] = Field(default=None, description="Resolved book title when known.")
    progress_percent: Optional[float] = Field(default=None, description="Overall progress percentage from 0 to 100 when known.")
    completed_chapters: Optional[int] = Field(default=None, description="Number of completed chapters when known.")
    total_chapters: Optional[int] = Field(default=None, description="Total number of chapters when known.")
    current_chapter_id: Optional[int] = Field(default=None, description="Identifier of the chapter currently being processed.")
    current_chapter_ref: Optional[str] = Field(default=None, description="Human-readable reference of the current chapter.")
    current_section_ref: Optional[str] = Field(default=None, description="Human-readable reference of the current section.")
    current_phase_step: Optional[str] = Field(default=None, description="Human-readable label for the current parse or read step.")
    eta_seconds: Optional[int] = Field(default=None, description="Estimated remaining time in seconds.")
    resume_available: bool = Field(default=False, description="Whether the job can resume from a checkpoint.")
    last_checkpoint_at: Optional[str] = Field(default=None, description="Last checkpoint timestamp when available.")
    last_error: Optional[ErrorResponse] = Field(default=None, description="Structured error information when the job is in an error state.")
    created_at: str = Field(description="Job creation time.")
    updated_at: str = Field(description="Last update time for the job record.")
    ws_url: str = Field(description="WebSocket URL for live progress updates for this job.")


class ChapterTreeItem(ApiModel):
    """Structure tree node used on the analysis progress page."""

    chapter_id: int = Field(description="Chapter identifier.")
    chapter_ref: str = Field(description="Human-readable chapter reference.")
    title: str = Field(description="Chapter title.")
    segment_count: int = Field(description="Number of semantic sections in this chapter.")
    status: Literal["pending", "in_progress", "completed", "error"] = Field(description="Current processing state of the chapter.")
    is_current: bool = Field(description="Whether this chapter is currently being processed.")
    result_ready: bool = Field(description="Whether the chapter result page can already be opened.")


class CurrentStatePanel(ApiModel):
    """Focused realtime status block for the analysis page."""

    current_chapter_id: Optional[int] = Field(default=None, description="Identifier of the chapter currently being processed.")
    current_chapter_ref: Optional[str] = Field(default=None, description="Human-readable reference of the chapter currently being processed.")
    current_section_ref: Optional[str] = Field(default=None, description="Human-readable reference of the current section.")
    current_phase_step: Optional[str] = Field(default=None, description="Human-readable label of the current parse or read step.")
    recent_reactions: list[FeaturedReactionPreview] = Field(description="Small set of recently surfaced reactions for quick feedback.")
    reaction_counts: dict[ReactionType, int] = Field(description="Visible reaction counts grouped by reaction type.")
    search_active: bool = Field(description="Whether the agent has recent active search behavior.")
    last_activity_message: Optional[str] = Field(default=None, description="Most recent user-facing activity line.")


class ChapterCompletionCard(ApiModel):
    """Completion micro-ritual card for one finished chapter."""

    chapter_id: int = Field(description="Completed chapter identifier.")
    chapter_ref: str = Field(description="Human-readable reference for the completed chapter.")
    title: str = Field(description="Title of the completed chapter.")
    visible_reaction_count: int = Field(description="Number of visible reactions in the chapter.")
    high_signal_reaction_count: int = Field(description="Number of high-signal reactions in the chapter.")
    featured_reactions: list[FeaturedReactionPreview] = Field(description="Small set of featured reactions used for the completion card.")
    result_url: str = Field(description="Frontend route that opens the finished chapter result.")


class AnalysisStateResponse(ApiModel):
    """Snapshot payload for the analysis-in-progress page."""

    book_id: int = Field(description="Stable public integer identifier of the book.")
    title: str = Field(description="Book title.")
    author: str = Field(description="Book author.")
    status: Literal["queued", "parsing_structure", "deep_reading", "chapter_note_generation", "paused", "completed", "error"] = Field(
        description="Current lifecycle state of the active analysis.",
    )
    stage_label: str = Field(description="User-facing stage label shown at the top of the progress page.")
    progress_percent: Optional[float] = Field(default=None, description="Overall progress percentage from 0 to 100 when known.")
    completed_chapters: int = Field(description="Number of completed chapters.")
    total_chapters: int = Field(description="Total number of chapters.")
    current_chapter_id: Optional[int] = Field(default=None, description="Identifier of the chapter currently being processed.")
    current_chapter_ref: Optional[str] = Field(default=None, description="Human-readable reference of the current chapter.")
    eta_seconds: Optional[int] = Field(default=None, description="Estimated remaining time in seconds.")
    current_phase_step: Optional[str] = Field(default=None, description="Human-readable label for the current parse or read step.")
    resume_available: bool = Field(default=False, description="Whether this analysis can resume from the latest checkpoint.")
    last_checkpoint_at: Optional[str] = Field(default=None, description="Last checkpoint timestamp when available.")
    structure_ready: bool = Field(description="Whether the structure tree is ready to render.")
    chapters: list[ChapterTreeItem] = Field(description="Structure tree displayed on the progress page.")
    current_state_panel: CurrentStatePanel = Field(description="Focused realtime state shown beside the structure tree.")
    recent_completed_chapters: list[ChapterCompletionCard] = Field(description="Recently completed chapters shown as micro-ritual cards.")
    last_error: Optional[ErrorResponse] = Field(default=None, description="Structured error payload when the analysis has failed.")


class ActivityEvent(ApiModel):
    """User-facing activity stream event."""

    event_id: str = Field(description="Stable identifier of the activity event.")
    timestamp: str = Field(description="Event timestamp.")
    type: str = Field(description="Stable event type key.")
    message: str = Field(description="User-facing message shown in the activity stream.")
    chapter_id: Optional[int] = Field(default=None, description="Related chapter identifier when applicable.")
    chapter_ref: Optional[str] = Field(default=None, description="Related chapter reference when applicable.")
    section_ref: Optional[str] = Field(default=None, description="Related section reference when applicable.")
    highlight_quote: Optional[str] = Field(default=None, description="High-signal anchor quote attached to the event when available.")
    reaction_types: list[ReactionType] = Field(description="Reaction types represented in this event.")
    search_query: Optional[str] = Field(default=None, description="Search query attached to the event when applicable.")
    featured_reactions: list[FeaturedReactionPreview] = Field(description="Featured reactions attached to the event when applicable.")
    visible_reaction_count: Optional[int] = Field(default=None, description="Visible reaction count attached to the event when applicable.")
    high_signal_reaction_count: Optional[int] = Field(default=None, description="High-signal reaction count attached to the event when applicable.")
    result_url: Optional[str] = Field(default=None, description="Frontend result route associated with the event when available.")


class ActivityEventsPageResponse(ApiModel):
    """Paginated activity stream response."""

    items: list[ActivityEvent] = Field(description="Activity events for the current page.")
    page_info: PageInfo = Field(description="Pagination metadata for the activity query.")


class AnalysisLogResponse(ApiModel):
    """Technical log tail for one active or recent analysis job."""

    job_id: Optional[str] = Field(default=None, description="Latest related job identifier when available.")
    available: bool = Field(description="Whether a technical log is available for this book.")
    updated_at: Optional[str] = Field(default=None, description="Last update time of the related job record when available.")
    lines: list[str] = Field(description="Recent log lines for debugging and long-task visibility.")


class ChapterListItem(ApiModel):
    """Chapter overview item used on the book result page."""

    chapter_id: int = Field(description="Chapter identifier.")
    chapter_ref: str = Field(description="Human-readable chapter reference.")
    title: str = Field(description="Chapter title.")
    segment_count: int = Field(description="Number of semantic sections in the chapter.")
    status: Literal["pending", "completed", "error"] = Field(description="User-facing chapter status in the result overview.")
    visible_reaction_count: int = Field(description="Number of visible reactions in the chapter.")
    reaction_type_diversity: int = Field(description="Count of distinct reaction types in the chapter.")
    high_signal_reaction_count: int = Field(description="Count of high-signal reactions in the chapter.")
    result_ready: bool = Field(description="Whether the chapter result is ready to open.")


class BookDetailResponse(ApiModel):
    """Book-level overview payload for the result page."""

    book_id: int = Field(description="Stable public integer identifier of the book.")
    title: str = Field(description="Book title.")
    author: str = Field(description="Book author.")
    cover_image_url: Optional[str] = Field(default=None, description="Optional API URL for the cover image.")
    book_language: str = Field(description="Detected primary language of the source book.")
    output_language: str = Field(description="Language used for AI-generated output.")
    status: Literal["analyzing", "paused", "completed", "error", "not_started"] = Field(description="High-level book state for the result page.")
    source_asset: SourceAsset = Field(description="Source EPUB asset configuration for epub.js.")
    chapters: list[ChapterListItem] = Field(description="Overview list of chapters in reading order.")
    my_mark_count: int = Field(description="Number of user marks attached to this book.")
    reaction_counts: dict[ReactionType, int] = Field(description="Counts grouped by the five canonical reaction types.")
    chapter_count: int = Field(description="Total number of chapters in the book.")
    completed_chapter_count: int = Field(description="Number of completed chapters in the book.")
    segment_count: int = Field(description="Total number of semantic segments across the book.")


class ReactionCard(ApiModel):
    """Visible reaction card rendered in result views."""

    reaction_id: int = Field(description="Stable public integer reaction identifier.")
    type: ReactionType = Field(description="Reaction type key.")
    anchor_quote: str = Field(description="Anchor quote taken from the source book.")
    content: str = Field(description="Full AI reaction content.")
    search_query: Optional[str] = Field(default=None, description="Search query used to gather additional evidence when applicable.")
    search_results: list[SearchHit] = Field(description="External search results attached to the reaction.")
    target_locator: Optional[ReactionTargetLocator] = Field(default=None, description="Reader locator for jumping to the source passage.")
    section_ref: str = Field(description="Human-readable parent section reference.")
    section_summary: str = Field(description="One-line summary of the parent section.")
    mark_type: Optional[MarkType] = Field(default=None, description="Current user mark attached to the reaction, if any.")


class SectionCard(ApiModel):
    """Section card rendered in the chapter result view."""

    section_ref: str = Field(description="Human-readable section reference.")
    summary: str = Field(description="One-line summary of the section.")
    verdict: str = Field(description="Section verdict returned by the reader pipeline.")
    quality_status: str = Field(description="Quality label assigned to the section.")
    skip_reason: Optional[str] = Field(default=None, description="Machine-readable skip reason when the section was skipped.")
    locator: Optional[SegmentLocator] = Field(default=None, description="Section-level locator for the EPUB reader.")
    reactions: list[ReactionCard] = Field(description="Visible reactions attached to the section.")


class ChapterDetailResponse(ApiModel):
    """Chapter result page payload."""

    book_id: int = Field(description="Stable public integer identifier of the book.")
    chapter_id: int = Field(description="Chapter identifier.")
    chapter_ref: str = Field(description="Human-readable chapter reference.")
    title: str = Field(description="Chapter title.")
    status: Literal["completed", "error"] = Field(description="User-facing chapter result status.")
    output_language: str = Field(description="Language used for the AI-generated chapter result.")
    visible_reaction_count: int = Field(description="Number of visible reactions in the chapter.")
    reaction_type_diversity: int = Field(description="Number of distinct reaction types in the chapter.")
    high_signal_reaction_count: int = Field(description="Number of high-signal reactions in the chapter.")
    featured_reactions: list[FeaturedReactionPreview] = Field(description="Featured reactions used for summary and teaser areas.")
    chapter_heading: Optional[ChapterHeadingBlock] = Field(
        default=None,
        description="Optional structured chapter-heading block kept separate from body semantic sections.",
    )
    chapter_reflection: list[str] = Field(
        description="Deprecated compatibility field. Internal chapter reflection is no longer exposed, so this list is always empty."
    )
    sections: list[SectionCard] = Field(description="Current page of section cards.")
    sections_page_info: PageInfo = Field(description="Pagination metadata for the section list.")
    available_filters: list[ReactionFilter] = Field(description="Reaction filters available to the frontend.")
    source_asset: SourceAsset = Field(description="Source EPUB asset configuration for the right-side reader.")


class ChapterOutlineSectionItem(ApiModel):
    """Compact section entry used in the chapter drawer outline preview."""

    section_ref: str = Field(description="Human-readable section reference.")
    summary: str = Field(description="One-line semantic title for the section.")
    preview_text: str = Field(description="Short preview text shown under the section title.")
    visible_reaction_count: int = Field(description="Number of visible reactions attached to this section.")
    locator: Optional[SegmentLocator] = Field(default=None, description="Section-level locator used for section jumps.")


class ChapterOutlineResponse(ApiModel):
    """Lightweight chapter outline payload used by the chapter drawer preview."""

    book_id: int = Field(description="Stable public integer identifier of the book.")
    chapter_id: int = Field(description="Chapter identifier.")
    chapter_ref: str = Field(description="Human-readable chapter reference.")
    title: str = Field(description="Chapter title.")
    result_ready: bool = Field(description="Whether the chapter result is ready to open.")
    status: Literal["pending", "completed", "error"] = Field(description="User-facing chapter status.")
    chapter_heading: Optional[ChapterHeadingBlock] = Field(
        default=None,
        description="Optional structured chapter-heading block shown as a non-numbered outline item.",
    )
    section_count: int = Field(description="Number of semantic sections in the chapter.")
    sections: list[ChapterOutlineSectionItem] = Field(description="Semantic section outline for the chapter.")


class ReactionsPageResponse(ApiModel):
    """Paginated flattened reaction response."""

    items: list[ReactionCard] = Field(description="Flattened reactions for the current page.")
    page_info: PageInfo = Field(description="Pagination metadata for the reaction query.")
    applied_filters: dict[str, Any] = Field(description="Echoed filter values applied to the query.")


class MarkRecord(ApiModel):
    """Persisted user mark record."""

    mark_id: int = Field(description="Stable public integer identifier of the mark.")
    reaction_id: int = Field(description="Public integer reaction identifier that owns this mark.")
    book_id: int = Field(description="Public integer book identifier for the marked reaction.")
    book_title: str = Field(description="Book title for the marked reaction.")
    chapter_id: int = Field(description="Chapter identifier for the marked reaction.")
    chapter_ref: str = Field(description="Human-readable chapter reference for the marked reaction.")
    section_ref: str = Field(description="Human-readable section reference for the marked reaction.")
    reaction_type: ReactionType = Field(description="Reaction type key for the marked reaction.")
    mark_type: MarkType = Field(description="User-selected mark value.")
    reaction_excerpt: str = Field(description="Short excerpt of the reaction content used in marks views.")
    anchor_quote: str = Field(description="Anchor quote used to recall the marked passage.")
    created_at: str = Field(description="Mark creation time.")
    updated_at: str = Field(description="Mark last update time.")


class MarksPageResponse(ApiModel):
    """Paginated global marks response."""

    items: list[MarkRecord] = Field(description="Mark records for the current page.")
    page_info: PageInfo = Field(description="Pagination metadata for the marks query.")


class BookMarksGroup(ApiModel):
    """Marks grouped under a single chapter."""

    chapter_id: int = Field(description="Chapter identifier for this mark group.")
    chapter_ref: str = Field(description="Human-readable chapter reference for this mark group.")
    items: list[MarkRecord] = Field(description="Marks that belong to the chapter.")


class BookMarksResponse(ApiModel):
    """Book-scoped grouped marks response."""

    book_id: int = Field(description="Public integer book identifier.")
    groups: list[BookMarksGroup] = Field(description="Marks grouped by chapter.")


class SetMarkRequest(ApiModel):
    """Request body for creating or updating a user mark."""

    book_id: int = Field(description="Public integer book identifier used to resolve the target reaction.")
    mark_type: MarkType = Field(description="User-selected mark value.")


class DeleteMarkResponse(ApiModel):
    """Response returned after deleting a mark."""

    reaction_id: int = Field(description="Public integer reaction identifier targeted by the delete request.")
    deleted: bool = Field(description="Whether a persisted mark was deleted.")


class WsEventEnvelope(ApiModel):
    """Common server-to-client WebSocket event envelope."""

    event_id: str = Field(description="Stable identifier for the emitted WebSocket event.")
    event_type: str = Field(description="Exact event type key.")
    sent_at: str = Field(description="Time when the server sent the event.")
    job_id: Optional[str] = Field(default=None, description="Job identifier when the event is job-scoped.")
    book_id: Optional[int] = Field(default=None, description="Public integer book identifier when the event is book-scoped.")
    payload: dict[str, Any] = Field(description="Event-specific payload object.")


class JobSnapshotPayload(ApiModel):
    """Initial or refreshed job snapshot payload."""

    status: str = Field(description="Current job status.")
    stage_label: str = Field(description="User-facing stage label.")
    progress_percent: Optional[float] = Field(default=None, description="Overall progress percentage when known.")
    completed_chapters: Optional[int] = Field(default=None, description="Completed chapter count when known.")
    total_chapters: Optional[int] = Field(default=None, description="Total chapter count when known.")
    current_chapter_id: Optional[int] = Field(default=None, description="Current chapter identifier when known.")
    current_chapter_ref: Optional[str] = Field(default=None, description="Current chapter reference when known.")
    current_section_ref: Optional[str] = Field(default=None, description="Current section reference when known.")
    current_phase_step: Optional[str] = Field(default=None, description="Current parse or read step when known.")
    eta_seconds: Optional[int] = Field(default=None, description="Estimated remaining time in seconds when known.")
    resume_available: bool = Field(default=False, description="Whether the current run can resume from a checkpoint.")
    last_checkpoint_at: Optional[str] = Field(default=None, description="Last checkpoint timestamp when known.")


class StageChangedPayload(ApiModel):
    """WebSocket payload emitted when the top-level stage changes."""

    previous_status: Optional[str] = Field(default=None, description="Previous top-level status before this change.")
    current_status: str = Field(description="New top-level status after this change.")
    stage_label: str = Field(description="User-facing label for the new stage.")


class StructureReadyPayload(ApiModel):
    """WebSocket payload emitted once the book structure is available."""

    book_id: int = Field(description="Resolved public integer book identifier.")
    title: str = Field(description="Resolved book title.")
    chapter_count: int = Field(description="Number of parsed chapters.")
    chapters: list[ChapterTreeItem] = Field(description="Initial structure tree for the book.")


class ChapterStartedPayload(ApiModel):
    """WebSocket payload emitted when a chapter begins processing."""

    chapter_id: int = Field(description="Chapter identifier.")
    chapter_ref: str = Field(description="Human-readable chapter reference.")
    title: str = Field(description="Chapter title.")
    segment_count: int = Field(description="Number of sections in the chapter.")


class SegmentStartedPayload(ApiModel):
    """WebSocket payload emitted when a section begins processing."""

    chapter_id: int = Field(description="Parent chapter identifier.")
    chapter_ref: str = Field(description="Parent chapter reference.")
    section_ref: str = Field(description="Section reference currently being processed.")
    section_summary: str = Field(description="One-line summary of the section when available.")


class ActivityCreatedPayload(ApiModel):
    """WebSocket payload wrapping a newly appended activity event."""

    event: ActivityEvent = Field(description="Newly created activity event.")


class ChapterCompletedPayload(ApiModel):
    """WebSocket payload emitted when one chapter finishes."""

    chapter_id: int = Field(description="Completed chapter identifier.")
    chapter_ref: str = Field(description="Human-readable reference of the completed chapter.")
    title: str = Field(description="Title of the completed chapter.")
    visible_reaction_count: int = Field(description="Number of visible reactions in the completed chapter.")
    high_signal_reaction_count: int = Field(description="Number of high-signal reactions in the completed chapter.")
    featured_reactions: list[FeaturedReactionPreview] = Field(description="Featured reactions used to summarize the completed chapter.")
    result_url: str = Field(description="Frontend route that opens the completed chapter result.")


class BookCompletedPayload(ApiModel):
    """WebSocket payload emitted when the whole book finishes."""

    book_id: int = Field(description="Completed public integer book identifier.")
    completed_at: str = Field(description="Book completion time.")
    result_url: str = Field(description="Frontend route that opens the completed book result.")


class JobErrorPayload(ApiModel):
    """WebSocket payload emitted when a job enters an error state."""

    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable error message.")
    retryable: bool = Field(description="Whether retrying may succeed.")
    chapter_id: Optional[int] = Field(default=None, description="Related chapter identifier when the error is chapter-scoped.")
    chapter_ref: Optional[str] = Field(default=None, description="Related chapter reference when applicable.")
    section_ref: Optional[str] = Field(default=None, description="Related section reference when applicable.")


class HeartbeatPayload(ApiModel):
    """Periodic WebSocket heartbeat payload."""

    status: str = Field(description="Current job or book status at heartbeat time.")
    server_time: str = Field(description="Current server timestamp.")
