export interface ApiErrorResponse {
  error_id?: string;
  code: string;
  message: string;
  status: number;
  retryable?: boolean;
  details?: Record<string, unknown> | null;
}

export interface PageInfo {
  limit: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface SearchHit {
  title: string;
  url: string;
  snippet: string;
  score?: number | null;
}

export type BookId = number;
export type ChapterId = number;
export type ReactionId = number;
export type MarkId = number;
export type ReactionType = "highlight" | "association" | "discern" | "retrospect" | "curious";
export type ReactionFilter = "all" | ReactionType;
export type MarkType = "known" | "blindspot";

export interface ReactionTargetLocator {
  href: string;
  start_cfi?: string | null;
  end_cfi?: string | null;
  match_text: string;
  match_mode: "exact" | "normalized" | "segment_fallback";
}

export interface FeaturedReactionPreview {
  reaction_id: ReactionId;
  type: ReactionType;
  anchor_quote: string;
  content: string;
  book_id: BookId;
  chapter_id: number;
  chapter_ref: string;
  section_ref: string;
  target_locator?: ReactionTargetLocator | null;
}

export interface BookShelfCard {
  book_id: BookId;
  title: string;
  author: string;
  cover_image_url?: string | null;
  book_language: string;
  output_language: string;
  reading_status: "not_started" | "analyzing" | "completed" | "error";
  completed_chapters: number;
  total_chapters: number;
  updated_at: string;
  mark_count: number;
  open_target: string;
}

export interface BooksPageResponse {
  items: BookShelfCard[];
  page_info: PageInfo;
  global_mark_count: number;
}

export interface UploadAcceptedResponse {
  job_id: string;
  upload_filename: string;
  status: string;
  book_id?: BookId | null;
  job_url: string;
  ws_url: string;
}

export interface ErrorPayload {
  error_id: string;
  code: string;
  message: string;
  status: number;
  retryable: boolean;
  details?: Record<string, unknown> | null;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "parsing_structure" | "deep_reading" | "chapter_note_generation" | "completed" | "error";
  book_id?: BookId | null;
  book_title?: string | null;
  progress_percent?: number | null;
  completed_chapters?: number | null;
  total_chapters?: number | null;
  current_chapter_id?: number | null;
  current_chapter_ref?: string | null;
  current_section_ref?: string | null;
  eta_seconds?: number | null;
  last_error?: ErrorPayload | null;
  created_at: string;
  updated_at: string;
  ws_url: string;
}

export interface ChapterTreeItem {
  chapter_id: number;
  chapter_ref: string;
  title: string;
  segment_count: number;
  status: "pending" | "in_progress" | "completed" | "error";
  is_current: boolean;
  result_ready: boolean;
}

export interface CurrentStatePanel {
  current_chapter_id?: number | null;
  current_chapter_ref?: string | null;
  current_section_ref?: string | null;
  recent_reactions: FeaturedReactionPreview[];
  reaction_counts: Record<ReactionType, number>;
  search_active: boolean;
  last_activity_message?: string | null;
}

export interface ChapterCompletionCard {
  chapter_id: number;
  chapter_ref: string;
  title: string;
  visible_reaction_count: number;
  high_signal_reaction_count: number;
  featured_reactions: FeaturedReactionPreview[];
  result_url: string;
}

export interface AnalysisStateResponse {
  book_id: BookId;
  title: string;
  author: string;
  status: "queued" | "parsing_structure" | "deep_reading" | "chapter_note_generation" | "completed" | "error";
  stage_label: string;
  progress_percent?: number | null;
  completed_chapters: number;
  total_chapters: number;
  current_chapter_id?: number | null;
  current_chapter_ref?: string | null;
  eta_seconds?: number | null;
  structure_ready: boolean;
  chapters: ChapterTreeItem[];
  current_state_panel: CurrentStatePanel;
  recent_completed_chapters: ChapterCompletionCard[];
  last_error?: ErrorPayload | null;
}

export interface ActivityEvent {
  event_id: string;
  timestamp: string;
  type: string;
  message: string;
  chapter_id?: number | null;
  chapter_ref?: string | null;
  section_ref?: string | null;
  highlight_quote?: string | null;
  reaction_types: ReactionType[];
  search_query?: string | null;
  featured_reactions: FeaturedReactionPreview[];
  visible_reaction_count?: number | null;
  high_signal_reaction_count?: number | null;
  result_url?: string | null;
}

export interface ActivityEventsPageResponse {
  items: ActivityEvent[];
  page_info: PageInfo;
}

export interface SourceAsset {
  format: string;
  url: string;
  media_type: string;
}

export interface ChapterListItem {
  chapter_id: number;
  chapter_ref: string;
  title: string;
  segment_count: number;
  status: "pending" | "completed" | "error";
  visible_reaction_count: number;
  reaction_type_diversity: number;
  high_signal_reaction_count: number;
  result_ready: boolean;
}

export interface BookDetailResponse {
  book_id: BookId;
  title: string;
  author: string;
  cover_image_url?: string | null;
  book_language: string;
  output_language: string;
  status: "analyzing" | "completed" | "error" | "not_started";
  source_asset: SourceAsset;
  chapters: ChapterListItem[];
  my_mark_count: number;
  reaction_counts: Record<ReactionType, number>;
  chapter_count: number;
  completed_chapter_count: number;
  segment_count: number;
  sample: boolean;
}

export interface ReactionCard {
  reaction_id: ReactionId;
  type: ReactionType;
  anchor_quote: string;
  content: string;
  search_query?: string | null;
  search_results: SearchHit[];
  target_locator?: ReactionTargetLocator | null;
  section_ref: string;
  section_summary: string;
  mark_type?: MarkType | null;
}

export interface SectionCard {
  section_ref: string;
  summary: string;
  verdict: string;
  quality_status: string;
  skip_reason?: string | null;
  locator?: {
    href: string;
    start_cfi?: string | null;
    end_cfi?: string | null;
    paragraph_start?: number | null;
    paragraph_end?: number | null;
  } | null;
  reactions: ReactionCard[];
}

export interface ChapterDetailResponse {
  book_id: BookId;
  chapter_id: number;
  chapter_ref: string;
  title: string;
  status: "completed" | "error";
  output_language: string;
  visible_reaction_count: number;
  reaction_type_diversity: number;
  high_signal_reaction_count: number;
  featured_reactions: FeaturedReactionPreview[];
  chapter_reflection: string[];
  sections: SectionCard[];
  sections_page_info: PageInfo;
  available_filters: ReactionFilter[];
  source_asset: SourceAsset;
}

export interface MarkRecord {
  mark_id: MarkId;
  reaction_id: ReactionId;
  book_id: BookId;
  book_title: string;
  chapter_id: number;
  chapter_ref: string;
  section_ref: string;
  reaction_type: ReactionType;
  mark_type: MarkType;
  reaction_excerpt: string;
  anchor_quote: string;
  created_at: string;
  updated_at: string;
}

export interface MarksPageResponse {
  items: MarkRecord[];
  page_info: PageInfo;
}

export interface BookMarksGroup {
  chapter_id: number;
  chapter_ref: string;
  items: MarkRecord[];
}

export interface BookMarksResponse {
  book_id: BookId;
  groups: BookMarksGroup[];
}

export class ApiRequestError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown> | null;

  constructor(payload: ApiErrorResponse) {
    super(payload.message);
    this.name = "ApiRequestError";
    this.status = payload.status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

function defaultApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function defaultWsBaseUrl(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000";
  }
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.hostname}:8000`;
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL?.trim() || defaultApiBaseUrl());
export const WS_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_WS_BASE_URL?.trim() || defaultWsBaseUrl());

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return `${error.code}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown request error";
}

export function toApiAssetUrl(path?: string | null): string | null {
  if (!path) {
    return null;
  }
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function toWebSocketUrl(path: string): string {
  if (/^wss?:\/\//.test(path)) {
    return path;
  }
  return `${WS_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function toFrontendPath(path?: string | null): string {
  if (!path) {
    return "/";
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (normalized === "/bookshelf") {
    return "/books";
  }
  if (normalized === "/bookshelf/marks") {
    return "/marks";
  }
  if (normalized.startsWith("/book/")) {
    return normalized.replace(/^\/book\//, "/books/").replace("/chapter/", "/chapters/");
  }
  if (normalized.startsWith("/analysis/")) {
    return normalized.replace(/^\/analysis\//, "/books/") + "/analysis";
  }
  if (normalized === "/sample") {
    return "/books";
  }
  return normalized;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (!isFormData && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let payload: ApiErrorResponse = {
      code: "REQUEST_FAILED",
      message: `${response.status} ${response.statusText}`,
      status: response.status,
    };

    try {
      const json = await response.json();
      if (json && typeof json === "object") {
        payload = {
          ...payload,
          ...(json as ApiErrorResponse),
        };
      }
    } catch {
      // ignore non-json error bodies
    }

    throw new ApiRequestError(payload);
  }

  return response.json() as Promise<T>;
}

export function fetchBooks() {
  return request<BooksPageResponse>("/api/books");
}

export function fetchBookDetail(bookId: BookId) {
  return request<BookDetailResponse>(`/api/books/${bookId}`);
}

export function fetchAnalysisState(bookId: BookId) {
  return request<AnalysisStateResponse>(`/api/books/${bookId}/analysis-state`);
}

export function fetchActivity(bookId: BookId) {
  return request<ActivityEventsPageResponse>(`/api/books/${bookId}/activity`);
}

export function fetchBookMarks(bookId: BookId) {
  return request<BookMarksResponse>(`/api/books/${bookId}/marks`);
}

export function fetchChapterDetail(bookId: BookId, chapterId: ChapterId) {
  return request<ChapterDetailResponse>(`/api/books/${bookId}/chapters/${chapterId}`);
}

export function fetchGlobalMarks() {
  return request<MarksPageResponse>("/api/marks");
}

export function fetchJobStatus(jobId: string) {
  return request<JobStatusResponse>(`/api/jobs/${jobId}`);
}

export function uploadEpub(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadAcceptedResponse>("/api/uploads/epub", {
    method: "POST",
    body: formData,
  });
}

export function putReactionMark(reactionId: ReactionId, bookId: BookId, markType: MarkType) {
  return request<MarkRecord>(`/api/marks/${reactionId}`, {
    method: "PUT",
    body: JSON.stringify({
      book_id: bookId,
      mark_type: markType,
    }),
  });
}

export function deleteReactionMark(reactionId: ReactionId) {
  return request<{ reaction_id: ReactionId; deleted: boolean }>(`/api/marks/${reactionId}`, {
    method: "DELETE",
  });
}
