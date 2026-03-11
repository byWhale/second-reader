export type BookId = number;
export type ChapterId = number;
export type ReactionId = number;
export type MarkId = number;

export const REACTION_TYPES = [
  "highlight",
  "association",
  "discern",
  "retrospect",
  "curious",
] as const;

export const MARK_TYPES = ["known", "blindspot"] as const;
export const REACTION_FILTERS = ["all", ...REACTION_TYPES] as const;

export type ReactionType = (typeof REACTION_TYPES)[number];
export type ReactionFilter = (typeof REACTION_FILTERS)[number];
export type MarkType = (typeof MARK_TYPES)[number];

export const CANONICAL_ROUTE_PATTERNS = {
  landing: "/",
  books: "/books",
  book: "/books/:id",
  chapter: "/books/:id/chapters/:chapterId",
  analysis: "/books/:id/analysis",
  marks: "/marks",
} as const;

export const COMPAT_ROUTE_PATTERNS = {
  bookshelf: "/bookshelf",
  book: "/book/:bookId",
  chapter: "/book/:bookId/chapter/:chapterId",
  analysis: "/analysis/:bookId",
  marks: "/bookshelf/marks",
} as const;

export const COMPAT_ROUTE_LIST = [
  COMPAT_ROUTE_PATTERNS.bookshelf,
  COMPAT_ROUTE_PATTERNS.book,
  COMPAT_ROUTE_PATTERNS.chapter,
  COMPAT_ROUTE_PATTERNS.analysis,
  COMPAT_ROUTE_PATTERNS.marks,
] as const;

export const UTILITY_ROUTE_PATTERNS = {
  upload: "/upload",
} as const;

export const LANDING_STRATEGY = {
  owner: "frontend_static",
  display_card_count: 5,
  sample_teaser_source: "frontend_static",
} as const;

export const PUBLIC_CONTRACT_SPEC = {
  reaction_types: [...REACTION_TYPES],
  mark_types: [...MARK_TYPES],
  canonical_routes: { ...CANONICAL_ROUTE_PATTERNS },
  compat_routes: [...COMPAT_ROUTE_LIST],
  landing_strategy: { ...LANDING_STRATEGY },
} as const;

export function canonicalBookPath(bookId: BookId | string): string {
  return `/books/${bookId}`;
}

export function canonicalBookAnalysisPath(bookId: BookId | string): string {
  return `/books/${bookId}/analysis`;
}

export function canonicalChapterPath(bookId: BookId | string, chapterId: ChapterId | string): string {
  return `/books/${bookId}/chapters/${chapterId}`;
}
