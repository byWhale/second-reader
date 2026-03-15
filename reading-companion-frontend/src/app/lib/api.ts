import {
  type BookId,
  type ChapterId,
  type MarkType,
  type ReactionId,
  CANONICAL_ROUTE_PATTERNS,
  COMPAT_ROUTE_PATTERNS,
} from "./contract";
import { copy } from "../config/controlled-copy";
import type {
  ActivityEvent,
  ActivityEventsPageResponse,
  AnalysisLogResponse,
  AnalysisResumeAcceptedResponse,
  AnalysisStartAcceptedResponse,
  AnalysisStateResponse,
  ApiErrorResponse,
  BookDetailResponse,
  BookMarksResponse,
  BookShelfCard,
  BooksPageResponse,
  ChapterDetailResponse,
  ChapterOutlineResponse,
  DeleteMarkResponse,
  ErrorPayload,
  JobStatusResponse,
  MarkRecord,
  MarksPageResponse,
  SetMarkRequest,
  UploadAcceptedResponse,
} from "./api-types";

export type {
  ActivityEvent,
  ActivityEventsPageResponse,
  AnalysisLogResponse,
  AnalysisResumeAcceptedResponse,
  AnalysisStartAcceptedResponse,
  AnalysisStateResponse,
  BookDetailResponse,
  BookMarksResponse,
  BookShelfCard,
  BooksPageResponse,
  ChapterDetailResponse,
  ChapterOutlineResponse,
  ErrorPayload,
  JobStatusResponse,
  MarkRecord,
  MarksPageResponse,
  UploadAcceptedResponse,
} from "./api-types";

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

const NETWORK_ERROR_PATTERNS = [/failed to fetch/i, /networkerror/i, /load failed/i, /fetch failed/i];

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

const ENV = (((import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env ?? {}) as Record<
  string,
  string | undefined
>);

export const API_BASE_URL = normalizeBaseUrl(ENV["VITE_API_BASE_URL"]?.trim() || defaultApiBaseUrl());
export const WS_BASE_URL = normalizeBaseUrl(ENV["VITE_WS_BASE_URL"]?.trim() || defaultWsBaseUrl());

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return `${error.code}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown request error";
}

export function isBackendUnavailableError(error: unknown): boolean {
  if (error instanceof ApiRequestError) {
    return false;
  }
  if (error instanceof Error) {
    return NETWORK_ERROR_PATTERNS.some((pattern) => pattern.test(error.message));
  }
  return false;
}

export function getErrorPresentation(
  error: unknown,
  fallback: { title: string; message: string },
): { title: string; message: string } {
  if (isBackendUnavailableError(error)) {
    return {
      title: copy("state.error.backendUnavailable.title"),
      message: copy("state.error.backendUnavailable.message"),
    };
  }
  return {
    title: fallback.title,
    message: error ? getErrorMessage(error) : fallback.message,
  };
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
    return CANONICAL_ROUTE_PATTERNS.landing;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (normalized === COMPAT_ROUTE_PATTERNS.bookshelf) {
    return CANONICAL_ROUTE_PATTERNS.books;
  }
  if (normalized === COMPAT_ROUTE_PATTERNS.marks) {
    return CANONICAL_ROUTE_PATTERNS.marks;
  }
  if (normalized.startsWith("/book/")) {
    return normalized.replace(/^\/book\//, "/books/").replace("/chapter/", "/chapters/");
  }
  if (/^\/books\/[^/]+\/analysis$/.test(normalized)) {
    return normalized.replace(/\/analysis$/, "");
  }
  if (normalized.startsWith("/analysis/")) {
    return normalized.replace(/^\/analysis\//, "/books/");
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

export function fetchActivity(
  bookId: BookId,
  options: {
    limit?: number;
    cursor?: string;
    type?: string;
    stream?: "mindstream" | "system";
    chapterId?: number;
  } = {},
) {
  const params = new URLSearchParams();
  if (options.limit != null) {
    params.set("limit", String(options.limit));
  }
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }
  if (options.type) {
    params.set("type", options.type);
  }
  if (options.stream) {
    params.set("stream", options.stream);
  }
  if (options.chapterId != null) {
    params.set("chapter_id", String(options.chapterId));
  }
  const search = params.toString();
  return request<ActivityEventsPageResponse>(`/api/books/${bookId}/activity${search ? `?${search}` : ""}`);
}

export function fetchAnalysisLog(bookId: BookId) {
  return request<AnalysisLogResponse>(`/api/books/${bookId}/analysis-log`);
}

export function fetchBookMarks(bookId: BookId) {
  return request<BookMarksResponse>(`/api/books/${bookId}/marks`);
}

export function fetchChapterDetail(
  bookId: BookId,
  chapterId: ChapterId,
  options: { limit?: number; reactionFilter?: string } = {},
) {
  const params = new URLSearchParams();
  if (options.limit != null) {
    params.set("limit", String(options.limit));
  }
  if (options.reactionFilter) {
    params.set("reaction_filter", options.reactionFilter);
  }
  const search = params.toString();
  return request<ChapterDetailResponse>(
    `/api/books/${bookId}/chapters/${chapterId}${search ? `?${search}` : ""}`,
  );
}

export function fetchChapterOutline(bookId: BookId, chapterId: ChapterId) {
  return request<ChapterOutlineResponse>(`/api/books/${bookId}/chapters/${chapterId}/outline`);
}

export function fetchGlobalMarks() {
  return request<MarksPageResponse>("/api/marks");
}

export function fetchJobStatus(jobId: string) {
  return request<JobStatusResponse>(`/api/jobs/${jobId}`);
}

export function uploadEpub(file: File, options: { startMode?: "immediate" | "deferred" } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  if (options.startMode) {
    formData.append("start_mode", options.startMode);
  }
  return request<UploadAcceptedResponse>("/api/uploads/epub", {
    method: "POST",
    body: formData,
  });
}

export function startBookAnalysis(bookId: BookId) {
  return request<AnalysisStartAcceptedResponse>(`/api/books/${bookId}/analysis/start`, {
    method: "POST",
  });
}

export function resumeBookAnalysis(bookId: BookId) {
  return request<AnalysisResumeAcceptedResponse>(`/api/books/${bookId}/analysis/resume`, {
    method: "POST",
  });
}

export function putReactionMark(reactionId: ReactionId, bookId: BookId, markType: MarkType) {
  const payload: SetMarkRequest = {
    book_id: bookId,
    mark_type: markType,
  };
  return request<MarkRecord>(`/api/marks/${reactionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteReactionMark(reactionId: ReactionId) {
  return request<DeleteMarkResponse>(`/api/marks/${reactionId}`, {
    method: "DELETE",
  });
}
