import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronLeft, ChevronRight, CircleDashed, List, Loader2, Search, Settings2 } from "lucide-react";
import { type CSSProperties, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import {
  BookDetailResponse,
  ChapterDetailResponse,
  ChapterOutlineResponse,
  deleteReactionMark,
  fetchBookDetail,
  fetchChapterDetail,
  fetchChapterOutline,
  putReactionMark,
  toApiAssetUrl,
} from "../lib/api";
import type { ChapterHeadingBlock, ChapterListItem, ChapterOutlineSectionItem, SectionCard } from "../lib/api-types";
import {
  type MarkType,
  type ReactionFilter,
  REACTION_FILTERS,
  canonicalBookPath,
  canonicalChapterPath,
  type ReactionId,
} from "../lib/contract";
import { markLabel } from "../lib/marks";
import {
  buildSectionJumpRequest,
  buildReaderJumpRequest,
  findSelectionByReactionId,
  reactionPreview,
  type ReaderJumpRequest,
  type ReaderLocationUpdate,
  type ReaderPanelMode,
} from "../lib/reader-types";
import { reactionLabel, reactionMeta } from "../lib/reactions";
import { copy } from "../config/controlled-copy";
import { term } from "../config/product-lexicon";
import {
  clampReaderFontSize,
  formatReaderProgress,
  READER_FONT_SIZE_MAX,
  READER_FONT_SIZE_MIN,
  READER_FONT_SIZE_STEP,
  READER_FONT_SIZE_STORAGE_KEY,
  readStoredReaderFontSize,
} from "../lib/reader-ui";
import { ErrorState, LoadingState } from "./page-state";
import { SourceReaderPane } from "./source-reader-pane";
import { OverflowTooltipText } from "./ui/overflow-tooltip-text";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "./ui/sheet";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "./ui/resizable";
import { Slider } from "./ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import { useIsMobile } from "./ui/use-mobile";
import { useElementResponsiveTier } from "./ui/use-responsive-tier";

const CHAPTER_FILTER_STORAGE_KEY_PREFIX = "chapter-reader-filter";
const CHAPTER_PANEL_MODE_STORAGE_KEY_PREFIX = "chapter-reader-panel-mode";
const CHAPTER_SECTION_HINT_STORAGE_KEY_PREFIX = "chapter-reader-section-hint";
const NOTE_CLICK_JUMP_THROTTLE_MS = 140;

function replaceReaction(
  payload: ChapterDetailResponse,
  reactionId: ReactionId,
  updater: (markType: MarkType | null) => MarkType | null,
): ChapterDetailResponse {
  return {
    ...payload,
    sections: payload.sections.map((section) => ({
      ...section,
      reactions: section.reactions.map((reaction) =>
        reaction.reaction_id === reactionId
          ? { ...reaction, mark_type: updater(reaction.mark_type ?? null) }
          : reaction,
      ),
    })),
  };
}

function parseReactionSearch(search: string): ReactionId | null {
  const params = new URLSearchParams(search);
  const value = params.get("reaction");
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    return null;
  }
  return parsed;
}

function parseSectionSearch(search: string): string | null {
  const params = new URLSearchParams(search);
  const value = params.get("section");
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function chapterFilterStorageKey(bookId: string): string {
  return `${CHAPTER_FILTER_STORAGE_KEY_PREFIX}:${bookId}`;
}

function chapterPanelModeStorageKey(bookId: string): string {
  return `${CHAPTER_PANEL_MODE_STORAGE_KEY_PREFIX}:${bookId}`;
}

function chapterSectionHintStorageKey(bookId: string, chapterId: number): string {
  return `${CHAPTER_SECTION_HINT_STORAGE_KEY_PREFIX}:${bookId}:${chapterId}`;
}

function readChapterFilterPreference(bookId: string): ReactionFilter {
  if (typeof window === "undefined" || !bookId) {
    return "all";
  }
  const persisted = window.sessionStorage.getItem(chapterFilterStorageKey(bookId));
  return persisted && REACTION_FILTERS.includes(persisted as ReactionFilter)
    ? (persisted as ReactionFilter)
    : "all";
}

function readChapterPanelModePreference(bookId: string): ReaderPanelMode {
  if (typeof window === "undefined" || !bookId) {
    return "notes";
  }
  const persisted = window.sessionStorage.getItem(chapterPanelModeStorageKey(bookId));
  return persisted === "book" ? "book" : "notes";
}

function filterSections(sections: SectionCard[], activeFilter: ReactionFilter): SectionCard[] {
  return sections
    .map((section) => ({
      ...section,
      reactions: activeFilter === "all"
        ? section.reactions
        : section.reactions.filter((reaction) => reaction.type === activeFilter),
    }))
    .filter((section) => section.reactions.length > 0);
}

function firstReactionId(sections: SectionCard[]): ReactionId | null {
  return sections.flatMap((section) => section.reactions)[0]?.reaction_id ?? null;
}

function initialReactionIdForFilter(
  sections: SectionCard[],
  activeFilter: ReactionFilter,
): ReactionId | null {
  return firstReactionId(filterSections(sections, activeFilter)) ?? firstReactionId(sections);
}

function findSectionByRef(sections: SectionCard[], sectionRef: string | null): SectionCard | null {
  if (!sectionRef) {
    return null;
  }
  return sections.find((section) => section.section_ref === sectionRef) ?? null;
}

function sectionHasVisibleReactions(section: SectionCard | null, activeFilter: ReactionFilter): boolean {
  if (!section) {
    return false;
  }
  if (activeFilter === "all") {
    return section.reactions.length > 0;
  }
  return section.reactions.some((reaction) => reaction.type === activeFilter);
}

function outlinePreviewTextFromSection(section: SectionCard): string {
  const quoted = section.reactions.find((reaction) => reaction.anchor_quote.trim())?.anchor_quote.trim();
  if (quoted) {
    return reactionPreview(quoted, 110);
  }
  const content = section.reactions.find((reaction) => reaction.content.trim())?.content.trim();
  if (content) {
    return reactionPreview(content, 110);
  }
  return "";
}

function chapterHeadingSupportingText(heading: ChapterHeadingBlock | null | undefined): string | null {
  if (!heading) {
    return null;
  }
  const subtitle = heading.subtitle?.trim();
  if (subtitle) {
    return subtitle;
  }
  const title = heading.title.trim();
  const text = heading.text.trim();
  return text && text !== title ? text : null;
}

function searchResultDomainLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function scaledRem(baseRem: number): string {
  return `calc(${baseRem}rem * var(--rc-reading-font-scale, 1))`;
}

function buildOutlineFromChapterPayload(
  payload: ChapterDetailResponse,
  chapterEntry: ChapterListItem | null,
): ChapterOutlineResponse {
  return {
    book_id: payload.book_id,
    chapter_id: payload.chapter_id,
    chapter_ref: chapterEntry?.chapter_ref || payload.chapter_ref,
    title: chapterEntry?.title || payload.title,
    chapter_heading: payload.chapter_heading ?? null,
    result_ready: true,
    status: "completed",
    section_count: payload.sections.length,
    sections: payload.sections.map((section) => ({
      section_ref: section.section_ref,
      summary: section.summary,
      preview_text: outlinePreviewTextFromSection(section),
      visible_reaction_count: section.reactions.length,
      locator: section.locator ?? null,
    })),
  };
}

export function ChapterReadPage() {
  const { id = "", bookId = "", chapterId: chapterIdParam = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { ref: workspaceRef, tier: workspaceTier } = useElementResponsiveTier<HTMLDivElement>();

  const resolvedBookId = id || bookId;
  const bookIdNumber = Number(resolvedBookId);
  const chapterNumber = Number(chapterIdParam);
  const [payload, setPayload] = useState<ChapterDetailResponse | null>(null);
  const [bookDetail, setBookDetail] = useState<BookDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeReactionId, setActiveReactionId] = useState<ReactionId | null>(null);
  const [activeFilter, setActiveFilter] = useState<ReactionFilter>(() => readChapterFilterPreference(resolvedBookId));
  const [reloadTick, setReloadTick] = useState(0);
  const [mobileMode, setMobileMode] = useState<ReaderPanelMode>(() => readChapterPanelModePreference(resolvedBookId));
  const [fontSizePercent, setFontSizePercent] = useState(readStoredReaderFontSize);
  const [passiveSectionRef, setPassiveSectionRef] = useState<string | null>(null);
  const [visibleSectionRef, setVisibleSectionRef] = useState<string | null>(null);
  const [readerProgress, setReaderProgress] = useState<number | null>(null);
  const [jumpRequest, setJumpRequest] = useState<ReaderJumpRequest | null>(null);
  const [isChapterSheetOpen, setIsChapterSheetOpen] = useState(false);
  const [sectionHint, setSectionHint] = useState<string | null>(null);
  const [outlineCache, setOutlineCache] = useState<Record<number, ChapterOutlineResponse>>({});
  const [outlineLoadingIds, setOutlineLoadingIds] = useState<number[]>([]);
  const [previewChapterId, setPreviewChapterId] = useState<number | null>(null);
  const [mobileChapterSheetView, setMobileChapterSheetView] = useState<"chapters" | "sections">("chapters");
  const [pendingSectionScrollRef, setPendingSectionScrollRef] = useState<string | null>(null);

  const jumpSequenceRef = useRef(0);
  const lastNoteJumpAtRef = useRef(0);
  const notesScrollContainerRef = useRef<HTMLDivElement | null>(null);
  const sectionRefs = useRef(new Map<string, HTMLElement | null>());
  const hoverPreviewTimerRef = useRef<number | null>(null);
  const outlineCacheRef = useRef<Record<number, ChapterOutlineResponse>>({});
  const outlineRequestRef = useRef<Record<number, Promise<ChapterOutlineResponse> | undefined>>({});
  const handledSectionQueryKeyRef = useRef<string | null>(null);
  const activeFilterRef = useRef<ReactionFilter>(activeFilter);
  const queryReactionId = useMemo(() => parseReactionSearch(location.search), [location.search]);
  const querySectionRef = useMemo(() => parseSectionSearch(location.search), [location.search]);

  const queueReaderJump = useCallback(
    (reactionId: ReactionId, source: ReaderJumpRequest["source"], sourcePayload: ChapterDetailResponse | null) => {
      if (!sourcePayload) {
        return;
      }
      const selection = findSelectionByReactionId(sourcePayload.sections, reactionId);
      if (!selection) {
        return;
      }
      jumpSequenceRef.current += 1;
      setJumpRequest(buildReaderJumpRequest(selection, source, jumpSequenceRef.current));
    },
    [],
  );

  const queueSectionJump = useCallback(
    (section: SectionCard, source: ReaderJumpRequest["source"]) => {
      jumpSequenceRef.current += 1;
      setJumpRequest(buildSectionJumpRequest(section, source, jumpSequenceRef.current));
    },
    [],
  );

  const syncWorkspaceQuery = useCallback(
    (
      options: {
        reactionId?: ReactionId | null;
        sectionRef?: string | null;
        replace?: boolean;
      },
    ) => {
      const params = new URLSearchParams(location.search);
      if (options.reactionId == null) {
        params.delete("reaction");
      } else {
        params.set("reaction", String(options.reactionId));
        params.delete("section");
      }
      if (options.sectionRef == null) {
        params.delete("section");
      } else if (options.reactionId == null) {
        params.set("section", options.sectionRef);
      }
      const search = params.toString();
      const target = `${location.pathname}${search ? `?${search}` : ""}`;
      const current = `${location.pathname}${location.search}`;
      if (target === current) {
        return;
      }
      navigate(target, { replace: options.replace ?? false });
    },
    [location.pathname, location.search, navigate],
  );

  const syncReactionQuery = useCallback(
    (reactionId: ReactionId | null, replace = false) => {
      syncWorkspaceQuery({ reactionId, replace });
    },
    [syncWorkspaceQuery],
  );

  const ensureChapterOutline = useCallback(
    async (chapterId: number) => {
      const cached = outlineCacheRef.current[chapterId];
      if (cached) {
        return cached;
      }
      const inFlight = outlineRequestRef.current[chapterId];
      if (inFlight) {
        return inFlight;
      }

      setOutlineLoadingIds((current) => (current.includes(chapterId) ? current : [...current, chapterId]));
      const request = fetchChapterOutline(bookIdNumber, chapterId)
        .then((outline) => {
          outlineCacheRef.current = { ...outlineCacheRef.current, [chapterId]: outline };
          setOutlineCache((current) => ({ ...current, [chapterId]: outline }));
          return outline;
        })
        .finally(() => {
          delete outlineRequestRef.current[chapterId];
          setOutlineLoadingIds((current) => current.filter((value) => value !== chapterId));
        });
      outlineRequestRef.current[chapterId] = request;
      return request;
    },
    [bookIdNumber],
  );

  const activateSection = useCallback(
    (
      sectionRef: string,
      sourcePayload: ChapterDetailResponse,
      source: "section-click" | "section-query",
      options: { syncQuery?: boolean; replaceQuery?: boolean } = {},
    ) => {
      const targetSection = findSectionByRef(sourcePayload.sections, sectionRef);
      if (!targetSection) {
        return false;
      }

      const shouldFallbackToAll =
        activeFilter !== "all" && !sectionHasVisibleReactions(targetSection, activeFilter);

      if (shouldFallbackToAll) {
        const nextHint = `This section has no ${reactionLabel(activeFilter)} reactions, showing all reactions instead.`;
        if (typeof window !== "undefined") {
          window.sessionStorage.setItem(
            chapterSectionHintStorageKey(String(sourcePayload.book_id), sourcePayload.chapter_id),
            nextHint,
          );
        }
        setActiveFilter("all");
        window.setTimeout(() => {
          setSectionHint(nextHint);
        }, 0);
      } else {
        setSectionHint(null);
      }

      setActiveReactionId(null);
      setPassiveSectionRef(sectionRef);
      setPendingSectionScrollRef(sectionRef);
      queueSectionJump(targetSection, source);

      if (options.syncQuery !== false) {
        syncWorkspaceQuery({
          sectionRef,
          replace: options.replaceQuery ?? false,
        });
      }

      return true;
    },
    [activeFilter, queueSectionJump, syncWorkspaceQuery],
  );

  const selectReaction = useCallback(
    (
      reactionId: ReactionId,
      source: "note-click" | "deep-link" | "initial" = "note-click",
      sourcePayload: ChapterDetailResponse | null,
      options?: { forceJump?: boolean },
    ) => {
      const isSameReaction = activeReactionId === reactionId;
      setActiveReactionId(reactionId);
      setSectionHint(null);
      setPassiveSectionRef(null);

      if (source === "note-click") {
        syncReactionQuery(reactionId);
        const now = Date.now();
        const isRapidRepeat = now - lastNoteJumpAtRef.current < NOTE_CLICK_JUMP_THROTTLE_MS;
        // Always honor switching to a different note.
        // Only suppress extremely fast duplicate taps on the same note.
        const shouldJump = Boolean(options?.forceJump) || !isSameReaction || !isRapidRepeat;
        if (shouldJump) {
          queueReaderJump(reactionId, "note-click", sourcePayload);
          lastNoteJumpAtRef.current = now;
        }
        if (isMobile) {
          setMobileMode("book");
        }
        return;
      }

      if (source === "deep-link") {
        queueReaderJump(reactionId, "deep-link", sourcePayload);
        return;
      }

      queueReaderJump(reactionId, "initial", sourcePayload);
    },
    [activeReactionId, isMobile, queueReaderJump, syncReactionQuery],
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(READER_FONT_SIZE_STORAGE_KEY, String(fontSizePercent));
    }
  }, [fontSizePercent]);

  useEffect(() => {
    outlineCacheRef.current = outlineCache;
  }, [outlineCache]);

  useEffect(() => {
    activeFilterRef.current = activeFilter;
  }, [activeFilter]);

  useEffect(() => {
    setActiveFilter(readChapterFilterPreference(resolvedBookId));
    setMobileMode(readChapterPanelModePreference(resolvedBookId));
  }, [resolvedBookId]);

  useEffect(() => {
    if (typeof window === "undefined" || !resolvedBookId) {
      return;
    }
    window.sessionStorage.setItem(chapterFilterStorageKey(resolvedBookId), activeFilter);
  }, [activeFilter, resolvedBookId]);

  useEffect(() => {
    if (typeof window === "undefined" || !resolvedBookId) {
      return;
    }
    window.sessionStorage.setItem(chapterPanelModeStorageKey(resolvedBookId), mobileMode);
  }, [mobileMode, resolvedBookId]);

  useEffect(() => {
    if (typeof window === "undefined" || !payload) {
      return;
    }
    const key = chapterSectionHintStorageKey(String(payload.book_id), payload.chapter_id);
    const persisted = window.sessionStorage.getItem(key);
    if (!persisted) {
      return;
    }
    setSectionHint(persisted);
    window.sessionStorage.removeItem(key);
  }, [payload]);

  useEffect(() => {
    setIsChapterSheetOpen(false);
    setMobileChapterSheetView("chapters");
    setPreviewChapterId(null);
    setSectionHint(null);
    handledSectionQueryKeyRef.current = null;
    if (hoverPreviewTimerRef.current != null) {
      window.clearTimeout(hoverPreviewTimerRef.current);
      hoverPreviewTimerRef.current = null;
    }
  }, [chapterNumber]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    void Promise.all([
      fetchChapterDetail(bookIdNumber, chapterNumber, { limit: 100 }),
      fetchBookDetail(bookIdNumber).catch(() => null),
    ])
      .then(([nextPayload, nextBookDetail]) => {
        if (!active) {
          return;
        }

        setPayload(nextPayload);
        setBookDetail(nextBookDetail);
        const nextChapterEntry =
          nextBookDetail?.chapters.find((chapter) => chapter.chapter_id === nextPayload.chapter_id) ?? null;
        const seededOutline = buildOutlineFromChapterPayload(nextPayload, nextChapterEntry);
        outlineCacheRef.current = { ...outlineCacheRef.current, [nextPayload.chapter_id]: seededOutline };
        setOutlineCache((current) => ({ ...current, [nextPayload.chapter_id]: current[nextPayload.chapter_id] ?? seededOutline }));

        const hasReactionQuery =
          queryReactionId != null && findSelectionByReactionId(nextPayload.sections, queryReactionId) != null;
        const hasSectionQuery = querySectionRef != null && findSectionByRef(nextPayload.sections, querySectionRef) != null;
        const initialReactionId =
          hasReactionQuery
            ? queryReactionId
            : hasSectionQuery
              ? null
              : initialReactionIdForFilter(nextPayload.sections, activeFilterRef.current) ?? null;

        setActiveReactionId(initialReactionId);
        if (initialReactionId != null) {
          queueReaderJump(
            initialReactionId,
            hasReactionQuery ? "deep-link" : "initial",
            nextPayload,
          );
        }
      })
      .catch((reason) => {
        if (!active) {
          return;
        }
        setBookDetail(null);
        setError(reason instanceof Error ? reason.message : "Failed to load chapter data.");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [bookIdNumber, chapterNumber, queueReaderJump, reloadTick]);

  useEffect(() => {
    if (!payload || queryReactionId == null) {
      return;
    }
    if (queryReactionId === activeReactionId) {
      return;
    }

    const selection = findSelectionByReactionId(payload.sections, queryReactionId);
    if (!selection) {
      return;
    }
    selectReaction(queryReactionId, "deep-link", payload);
  }, [activeReactionId, payload, queryReactionId, selectReaction]);

  useEffect(() => {
    if (!payload || queryReactionId != null || !querySectionRef) {
      return;
    }

    const queryKey = `${payload.chapter_id}:${querySectionRef}`;
    if (handledSectionQueryKeyRef.current === queryKey) {
      return;
    }

    const handled = activateSection(querySectionRef, payload, "section-query", {
      syncQuery: false,
    });
    if (handled) {
      handledSectionQueryKeyRef.current = queryKey;
    }
  }, [activateSection, payload, queryReactionId, querySectionRef]);

  useEffect(() => {
    if (!isChapterSheetOpen || !payload) {
      return;
    }
    setPreviewChapterId(payload.chapter_id);
    if (isMobile) {
      setMobileChapterSheetView("chapters");
      return;
    }
    void ensureChapterOutline(payload.chapter_id);
  }, [ensureChapterOutline, isChapterSheetOpen, isMobile, payload]);

  useEffect(() => {
    if (!pendingSectionScrollRef) {
      return;
    }
    const node = sectionRefs.current.get(pendingSectionScrollRef);
    if (!node) {
      return;
    }
    node.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
    setPendingSectionScrollRef(null);
  }, [activeFilter, payload, pendingSectionScrollRef]);

  useEffect(() => () => {
    if (hoverPreviewTimerRef.current != null) {
      window.clearTimeout(hoverPreviewTimerRef.current);
    }
  }, []);

  const visibleSections = payload ? filterSections(payload.sections, activeFilter) : [];

  useEffect(() => {
    if (!payload) {
      return;
    }
    if (isMobile && mobileMode === "book") {
      setVisibleSectionRef(null);
      return;
    }

    const container = notesScrollContainerRef.current;
    if (!container || visibleSections.length === 0) {
      setVisibleSectionRef(null);
      return;
    }

    let rafId: number | null = null;

    const updateVisibleSection = () => {
      rafId = null;
      const containerRect = container.getBoundingClientRect();
      const nextVisibleSection =
        visibleSections.find((section) => {
          const node = sectionRefs.current.get(section.section_ref);
          if (!node) {
            return false;
          }
          const nodeRect = node.getBoundingClientRect();
          return nodeRect.bottom > containerRect.top + 12 && nodeRect.top < containerRect.bottom - 12;
        })?.section_ref ?? null;

      setVisibleSectionRef((current) => (current === nextVisibleSection ? current : nextVisibleSection));
    };

    const scheduleVisibleSectionUpdate = () => {
      if (rafId != null) {
        return;
      }
      rafId = window.requestAnimationFrame(updateVisibleSection);
    };

    scheduleVisibleSectionUpdate();
    container.addEventListener("scroll", scheduleVisibleSectionUpdate, { passive: true });
    window.addEventListener("resize", scheduleVisibleSectionUpdate);

    return () => {
      container.removeEventListener("scroll", scheduleVisibleSectionUpdate);
      window.removeEventListener("resize", scheduleVisibleSectionUpdate);
      if (rafId != null) {
        window.cancelAnimationFrame(rafId);
      }
    };
  }, [activeFilter, isMobile, mobileMode, payload, visibleSections]);

  if (loading && !payload) {
    return <LoadingState title={copy("chapter.loading")} />;
  }

  if (error || !payload) {
    return (
      <ErrorState
        title={copy("chapter.error.title")}
        message={error ?? copy("chapter.error.message")}
        onRetry={() => {
          setPayload(null);
          setLoading(true);
          setError(null);
          setReloadTick((value) => value + 1);
        }}
        linkLabel={copy("chapter.error.backToBooks")}
        linkTo="/books"
      />
    );
  }

  const availableFilters = payload.available_filters.filter(
    (filter): filter is ReactionFilter => REACTION_FILTERS.includes(filter as ReactionFilter),
  );
  const renderedFilters = Array.from(
    new Set<ReactionFilter>([
      ...((availableFilters.length > 0 ? availableFilters : REACTION_FILTERS) as readonly ReactionFilter[]),
      activeFilter,
    ]),
  );
  const workspaceCompact = workspaceTier === "compact" || workspaceTier === "narrow" || workspaceTier === "mobile";
  const workspaceNarrow = workspaceTier === "narrow" || workspaceTier === "mobile";
  const workspaceMobile = workspaceTier === "mobile";
  const pillBaseClass = `inline-flex items-center rounded-full border backdrop-blur-sm shadow-[0_1px_0_rgba(255,255,255,0.9),0_10px_24px_rgba(61,46,31,0.045)] transition-all duration-200 ${
    workspaceCompact ? "px-3" : "px-3.5"
  }`;
  const workspaceToolbarButtonClass = "inline-flex items-center justify-center rounded-full text-[var(--warm-600)] transition-colors duration-200 hover:bg-white/72 hover:text-[var(--warm-900)] disabled:cursor-not-allowed disabled:text-[var(--warm-400)] disabled:hover:bg-transparent disabled:hover:text-[var(--warm-400)]";
  const chapterNavButtonClass = `${workspaceToolbarButtonClass} h-8 w-8`;
  const sectionNavButtonClass = `${workspaceToolbarButtonClass} h-7 w-7`;
  const workspaceGhostLinkClass = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[var(--warm-600)] transition-colors duration-200 hover:bg-white/72 hover:text-[var(--warm-900)]";
  const workspaceOverviewLinkClass = "inline-flex items-center gap-2 rounded-full px-2 py-1.5 text-[var(--warm-700)] no-underline transition-colors duration-200 hover:bg-white/72 hover:text-[var(--warm-900)]";
  const toolbarValueClass = "text-[var(--warm-700)]";
  const filterBaseClass = `${pillBaseClass} ${workspaceCompact ? "h-8" : "h-8.5"} border border-transparent bg-transparent text-[var(--warm-600)] shadow-none hover:-translate-y-[1px] hover:border-[var(--warm-300)]/52 hover:bg-white/82 hover:text-[var(--warm-800)]`;
  const markButtonBaseClass = `${pillBaseClass} ${workspaceCompact ? "h-7.5" : "h-8"} border border-[var(--warm-300)]/32 bg-transparent text-[var(--warm-500)] shadow-none hover:-translate-y-[1px] hover:border-[var(--warm-300)]/58 hover:bg-[var(--warm-50)]/82 hover:text-[var(--warm-700)]`;
  const chapterItems = bookDetail?.chapters ?? [];
  const readableChapters = chapterItems.filter((chapter) => chapter.result_ready);
  const readableChapterCount = readableChapters.length;
  const showChapterSwitcher = Boolean(bookDetail) && readableChapterCount > 1;
  const currentChapterEntry = chapterItems.find((chapter) => chapter.chapter_id === payload.chapter_id) ?? null;
  const currentChapterRef = currentChapterEntry?.chapter_ref || payload.chapter_ref;
  const currentChapterTitle = (currentChapterEntry?.title || payload.title || "").trim();
  const showSeparateChapterTitle = Boolean(currentChapterTitle) && currentChapterTitle !== currentChapterRef;
  const bookTitle = (bookDetail?.title || payload.title || copy("chapter.reader.originalBookFallback")).trim();
  const previewChapter = chapterItems.find((chapter) => chapter.chapter_id === previewChapterId) ?? currentChapterEntry;
  const previewOutline = previewChapterId != null ? outlineCache[previewChapterId] ?? null : null;
  const previewOutlineLoading = previewChapterId != null && outlineLoadingIds.includes(previewChapterId);
  const activeReactionSelection = findSelectionByReactionId(payload.sections, activeReactionId);
  const currentReadingSectionRef =
    passiveSectionRef ??
    activeReactionSelection?.section.section_ref ??
    querySectionRef ??
    null;
  const currentWorkspaceSectionRef =
    isMobile && mobileMode === "book"
      ? currentReadingSectionRef
      : visibleSectionRef ?? currentReadingSectionRef;
  const currentWorkspaceSection =
    findSectionByRef(payload.sections, currentWorkspaceSectionRef) ??
    findSectionByRef(payload.sections, currentReadingSectionRef) ??
    payload.sections[0] ??
    null;
  const currentSectionIndex = currentWorkspaceSection
    ? payload.sections.findIndex((section) => section.section_ref === currentWorkspaceSection.section_ref)
    : -1;
  const previousSection = currentSectionIndex > 0 ? payload.sections[currentSectionIndex - 1] : null;
  const nextSection =
    currentSectionIndex >= 0 && currentSectionIndex < payload.sections.length - 1
      ? payload.sections[currentSectionIndex + 1]
      : null;
  const currentReadableChapterIndex = readableChapters.findIndex((chapter) => chapter.chapter_id === payload.chapter_id);
  const previousReadableChapter = currentReadableChapterIndex > 0 ? readableChapters[currentReadableChapterIndex - 1] : null;
  const nextReadableChapter =
    currentReadableChapterIndex >= 0 && currentReadableChapterIndex < readableChapters.length - 1
      ? readableChapters[currentReadableChapterIndex + 1]
      : null;
  const previewSectionItems = previewOutline?.sections ?? [];
  const primaryBookActionLabel = term("view.bookOverview");
  const notesScrollbarClass = workspaceCompact ? "rc-scrollbar rc-scrollbar-compact" : "rc-scrollbar";
  const bodyPaddingClass = workspaceCompact ? "px-4 pb-5 pt-4 sm:px-5" : "px-5 pb-6 pt-4 sm:px-6 lg:px-7";
  const headerOuterPaddingClass = workspaceCompact ? "px-4 py-2 sm:px-5" : "px-5 py-2.5 sm:px-6 lg:px-7";
  const filterRailClass = "flex w-max items-center gap-1";
  const fontScaleStyle = {
    "--rc-reading-font-scale": String(fontSizePercent / 100),
  } as CSSProperties;


  function filterToneClass(filter: ReactionFilter, isActive: boolean): string {
    if (!isActive) {
      return filterBaseClass;
    }
    if (filter === "all") {
      return `${pillBaseClass} ${workspaceCompact ? "h-8" : "h-8.5"} border-[var(--amber-accent)]/34 bg-[var(--amber-bg)] text-[var(--amber-accent)] shadow-[0_1px_0_rgba(255,255,255,0.82),0_8px_18px_rgba(139,105,20,0.09)]`;
    }
    const tone = reactionMeta[filter];
    return `${pillBaseClass} ${workspaceCompact ? "h-8" : "h-8.5"} border-[var(--warm-300)]/40 ${tone.surfaceClass} ${tone.accentClass} shadow-[0_1px_0_rgba(255,255,255,0.82),0_8px_16px_rgba(61,46,31,0.055)]`;
  }

  function markToneClass(markType: MarkType, isActive: boolean): string {
    if (!isActive) {
      return markButtonBaseClass;
    }
    if (markType === "resonance") {
      return `${markButtonBaseClass} border-[var(--amber-accent)]/34 bg-[var(--amber-bg)]/82 text-[var(--amber-accent)] shadow-[0_1px_0_rgba(255,255,255,0.82),0_8px_18px_rgba(139,105,20,0.08)]`;
    }
    if (markType === "blindspot") {
      return `${markButtonBaseClass} border-orange-300/58 bg-orange-50/84 text-orange-700 shadow-[0_1px_0_rgba(255,255,255,0.82),0_8px_18px_rgba(234,88,12,0.08)]`;
    }
    return `${markButtonBaseClass} border-emerald-300/56 bg-emerald-50/82 text-emerald-700 shadow-[0_1px_0_rgba(255,255,255,0.82),0_8px_18px_rgba(16,185,129,0.08)]`;
  }

  async function toggleMark(
    reactionId: ReactionId,
    currentMark: MarkType | null,
    nextMark: MarkType,
  ) {
    try {
      if (currentMark === nextMark) {
        await deleteReactionMark(reactionId);
        setPayload((current) => (current ? replaceReaction(current, reactionId, () => null) : current));
        return;
      }

      await putReactionMark(reactionId, payload.book_id, nextMark);
      setPayload((current) => (current ? replaceReaction(current, reactionId, () => nextMark) : current));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to update mark.");
    }
  }

  function handleFilterChange(filter: ReactionFilter) {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(chapterSectionHintStorageKey(String(payload.book_id), payload.chapter_id));
    }
    setSectionHint(null);
    setActiveFilter(filter);
  }

  function openChapter(chapterId: number, options: { sectionRef?: string | null } = {}) {
    const search = options.sectionRef ? `?section=${encodeURIComponent(options.sectionRef)}` : "";
    if (chapterId === payload.chapter_id) {
      if (options.sectionRef) {
        handledSectionQueryKeyRef.current = `${payload.chapter_id}:${options.sectionRef}`;
        activateSection(options.sectionRef, payload, "section-click", {
          syncQuery: true,
          replaceQuery: false,
        });
      }
      setIsChapterSheetOpen(false);
      setMobileChapterSheetView("chapters");
      return;
    }
    setIsChapterSheetOpen(false);
    setMobileChapterSheetView("chapters");
    navigate(`${canonicalChapterPath(payload.book_id, chapterId)}${search}`);
  }

  function handleChapterPreview(chapter: ChapterListItem) {
    if (isMobile) {
      return;
    }
    if (hoverPreviewTimerRef.current != null) {
      window.clearTimeout(hoverPreviewTimerRef.current);
    }
    hoverPreviewTimerRef.current = window.setTimeout(() => {
      setPreviewChapterId(chapter.chapter_id);
      if (chapter.result_ready) {
        void ensureChapterOutline(chapter.chapter_id);
      }
    }, 110);
  }

  function openMobileChapterSections(chapter: ChapterListItem) {
    if (!chapter.result_ready) {
      return;
    }
    setPreviewChapterId(chapter.chapter_id);
    setMobileChapterSheetView("sections");
    void ensureChapterOutline(chapter.chapter_id);
  }

  function handleOutlineSectionClick(section: ChapterOutlineSectionItem) {
    if (!previewChapterId) {
      return;
    }
    if (previewChapterId === payload.chapter_id) {
      openChapter(previewChapterId, { sectionRef: section.section_ref });
      return;
    }
    openChapter(previewChapterId, { sectionRef: section.section_ref });
  }

  function stepSection(targetSection: SectionCard | null) {
    if (!targetSection) {
      return;
    }
    handledSectionQueryKeyRef.current = `${payload.chapter_id}:${targetSection.section_ref}`;
    activateSection(targetSection.section_ref, payload, "section-click", {
      syncQuery: true,
      replaceQuery: false,
    });
  }

  function stepChapter(targetChapter: ChapterListItem | null) {
    if (!targetChapter) {
      return;
    }
    openChapter(targetChapter.chapter_id);
  }

  function renderToolbarIconButton({
    ariaLabel,
    className,
    disabled,
    icon,
    onClick,
    testId,
    tooltip,
  }: {
    ariaLabel: string;
    className: string;
    disabled: boolean;
    icon: ReactNode;
    onClick: () => void;
    testId: string;
    tooltip: string;
  }) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            data-testid={testId}
            aria-label={ariaLabel}
            className={className}
          >
            {icon}
          </button>
        </TooltipTrigger>
        <TooltipContent>
          {tooltip}
        </TooltipContent>
      </Tooltip>
    );
  }

  function renderNotesPane() {
    return (
      <div className="flex h-full min-h-0 flex-col bg-[var(--warm-100)]">
        <div
          ref={notesScrollContainerRef}
          className={`${notesScrollbarClass} min-h-0 flex-1 overflow-y-auto`}
          data-testid="chapter-reactions-scroll"
        >
          <div className={bodyPaddingClass}>
            <div className="space-y-8">
              {sectionHint ? (
                <div className="rounded-2xl border border-[var(--amber-accent)]/18 bg-[var(--amber-bg)]/72 px-4 py-3 text-[var(--amber-accent)] shadow-[0_1px_0_rgba(255,255,255,0.82)]">
                  <p style={{ fontSize: scaledRem(0.76), lineHeight: 1.6, fontWeight: 500 }}>{sectionHint}</p>
                </div>
              ) : null}

              {visibleSections.length === 0 ? (
                <div className="rounded-2xl border border-[var(--warm-300)]/40 bg-white px-4 py-6">
                  <p className="text-[var(--warm-800)]" style={{ fontSize: scaledRem(0.9), fontWeight: 600 }}>
                    No reactions under this filter.
                  </p>
                  <p className="text-[var(--warm-600)] mt-1" style={{ fontSize: scaledRem(0.82), lineHeight: 1.7 }}>
                    Switch back to All to continue linked reading and jump navigation.
                  </p>
                </div>
              ) : null}

              {visibleSections.map((section) => (
                <section
                  key={section.section_ref}
                  ref={(node) => {
                    sectionRefs.current.set(section.section_ref, node);
                  }}
                  className={`rounded-2xl transition-colors ${
                    passiveSectionRef === section.section_ref
                      ? "bg-[var(--amber-bg)]/45 border border-[var(--amber-accent)]/20 p-3 -m-3"
                      : ""
                  }`}
                  style={{ scrollMarginTop: "1.25rem" }}
                >
                  <div className="space-y-3">
                    {section.reactions.map((reaction) => {
                      const isActive = activeReactionId === reaction.reaction_id;
                      const anchorQuote = reaction.anchor_quote.trim();
                      const reactionTone = reactionMeta[reaction.type];
                      return (
                        <article
                          key={reaction.reaction_id}
                          data-testid={`reaction-card-${reaction.reaction_id}`}
                          className={`rounded-2xl border p-4 cursor-pointer transition-colors ${
                            isActive
                              ? "border-[var(--amber-accent)]/45 bg-[var(--amber-bg)] shadow-[0_1px_0_rgba(255,255,255,0.9),0_20px_38px_rgba(139,105,20,0.11)]"
                              : "border-[var(--warm-300)]/30 bg-white shadow-[0_1px_0_rgba(255,255,255,0.92),0_12px_28px_rgba(61,46,31,0.04)] hover:-translate-y-[1px] hover:border-[var(--warm-300)]/65 hover:shadow-[0_1px_0_rgba(255,255,255,0.94),0_18px_34px_rgba(61,46,31,0.07)]"
                          }`}
                          style={{ transitionDuration: "180ms" }}
                          onClick={() => selectReaction(reaction.reaction_id, "note-click", payload)}
                        >
                          <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
                            <div className="flex items-center gap-2">
                              <span
                                className={`${pillBaseClass} h-9 border-[var(--warm-300)]/45 ${reactionTone.surfaceClass} ${reactionTone.accentClass}`}
                                style={{ fontSize: scaledRem(0.74), fontWeight: 600 }}
                              >
                                {reactionLabel(reaction.type)}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void toggleMark(reaction.reaction_id, reaction.mark_type ?? null, "resonance");
                                }}
                                data-testid={`mark-resonance-${reaction.reaction_id}`}
                                className={markToneClass("resonance", reaction.mark_type === "resonance")}
                                style={{ fontSize: scaledRem(0.72), fontWeight: 600 }}
                              >
                                {markLabel("resonance")}
                              </button>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void toggleMark(reaction.reaction_id, reaction.mark_type ?? null, "blindspot");
                                }}
                                data-testid={`mark-blindspot-${reaction.reaction_id}`}
                                className={markToneClass("blindspot", reaction.mark_type === "blindspot")}
                                style={{ fontSize: scaledRem(0.72), fontWeight: 600 }}
                              >
                                {markLabel("blindspot")}
                              </button>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void toggleMark(reaction.reaction_id, reaction.mark_type ?? null, "bookmark");
                                }}
                                data-testid={`mark-bookmark-${reaction.reaction_id}`}
                                className={markToneClass("bookmark", reaction.mark_type === "bookmark")}
                                style={{ fontSize: scaledRem(0.72), fontWeight: 600 }}
                              >
                                {markLabel("bookmark")}
                              </button>
                            </div>
                          </div>

                          {anchorQuote ? (
                            <blockquote
                              className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-3 text-[var(--warm-600)] italic"
                              style={{ fontSize: scaledRem(0.8125), lineHeight: 1.7 }}
                            >
                              “{anchorQuote}”
                            </blockquote>
                          ) : null}

                          {isActive ? (
                            <>
                              <p className="text-[var(--warm-800)]" style={{ fontSize: scaledRem(0.875), lineHeight: 1.82 }}>
                                {reaction.content}
                              </p>
                              {reaction.search_results.length > 0 ? (
                                <section className="mt-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Search className="w-4 h-4 text-[var(--amber-accent)]" />
                                    <p className="text-[var(--warm-900)]" style={{ fontSize: scaledRem(0.78), fontWeight: 600 }}>
                                      Extra context
                                    </p>
                                  </div>
                                  <div className="space-y-2">
                                    {reaction.search_results.map((result) => (
                                      <a
                                        key={result.url}
                                        href={result.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="block overflow-hidden rounded-xl bg-white/74 border border-[var(--warm-300)]/40 p-3 no-underline transition-colors hover:bg-white"
                                      >
                                        <div className="mb-1 flex items-start justify-between gap-3">
                                          <p
                                            className="min-w-0 text-[var(--warm-900)]"
                                            style={{
                                              fontSize: scaledRem(0.77),
                                              fontWeight: 600,
                                              lineHeight: 1.5,
                                              overflowWrap: "anywhere",
                                              wordBreak: "break-word",
                                            }}
                                          >
                                            {result.title}
                                          </p>
                                          <span
                                            className="shrink-0 rounded-full border border-[var(--warm-300)]/58 bg-[var(--warm-50)] px-2 py-0.5 text-[var(--warm-500)]"
                                            style={{ fontSize: scaledRem(0.64), fontWeight: 600 }}
                                          >
                                            {searchResultDomainLabel(result.url)}
                                          </span>
                                        </div>
                                        <p
                                          className="text-[var(--warm-600)]"
                                          style={{
                                            fontSize: scaledRem(0.75),
                                            lineHeight: 1.65,
                                            overflowWrap: "anywhere",
                                            wordBreak: "break-word",
                                            display: "-webkit-box",
                                            WebkitLineClamp: 3,
                                            WebkitBoxOrient: "vertical",
                                            overflow: "hidden",
                                          }}
                                        >
                                          {result.snippet}
                                        </p>
                                      </a>
                                    ))}
                                  </div>
                                </section>
                              ) : null}
                            </>
                          ) : (
                            <p className="text-[var(--warm-700)]" style={{ fontSize: scaledRem(0.84), lineHeight: 1.75 }}>
                              {reactionPreview(reaction.content)}
                            </p>
                          )}
                        </article>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const sourceUrl = toApiAssetUrl(payload.source_asset.url);
  const readerBookTitle =
    (bookDetail?.title || "").trim() || payload.title || copy("chapter.reader.originalBookFallback");
  const previewChapterHeading = previewOutline?.chapter_heading ?? null;
  const previewHasOutlineContent = Boolean(previewChapterHeading) || previewSectionItems.length > 0;

  function renderOutlineHeadingBlock(heading: ChapterHeadingBlock | null, mode: "desktop" | "mobile") {
    if (!heading) {
      return null;
    }

    const showLabel = heading.label?.trim() && heading.label.trim() !== heading.title.trim();
    const supportingText = chapterHeadingSupportingText(heading);
    return (
      <div
        className={`rounded-2xl border border-[var(--warm-300)]/36 bg-[linear-gradient(180deg,rgba(255,252,245,0.96),rgba(249,244,235,0.92))] shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_14px_28px_rgba(61,46,31,0.035)] ${
          mode === "desktop" ? "px-4 py-3.5" : "px-4 py-3"
        }`}
        data-testid="chapter-outline-heading-block"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p
              className="text-[var(--warm-500)] uppercase tracking-[0.14em]"
              style={{ fontSize: "0.64rem", fontWeight: 700 }}
            >
              Chapter heading
            </p>
            {showLabel ? (
              <p
                className="mt-1 text-[var(--amber-accent)]"
                style={{ fontSize: "0.69rem", fontWeight: 700, lineHeight: 1.35 }}
              >
                {heading.label}
              </p>
            ) : null}
            <OverflowTooltipText
              as="p"
              text={heading.title}
              lines={mode === "desktop" ? 2 : 3}
              side="right"
              className="mt-1 text-[var(--warm-950)] font-['Lora',Georgia,serif]"
              style={{ fontSize: mode === "desktop" ? "0.96rem" : "0.9rem", fontWeight: 700, lineHeight: 1.35 }}
            />
            {supportingText ? (
              <p className="mt-1.5 text-[var(--warm-600)]" style={{ fontSize: "0.76rem", lineHeight: 1.62 }}>
                {supportingText}
              </p>
            ) : null}
          </div>
          <span
            className="shrink-0 rounded-full border border-[var(--warm-300)]/58 bg-white/84 px-2.5 py-1 text-[var(--warm-500)] shadow-[inset_0_1px_0_rgba(255,255,255,0.88)]"
            style={{ fontSize: "0.64rem", fontWeight: 700 }}
          >
            {copy("chapter.sheet.structureBadge")}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div ref={workspaceRef} className="h-[calc(100vh-72px)] flex flex-col bg-[var(--warm-100)]" style={fontScaleStyle}>
      <Sheet open={isChapterSheetOpen} onOpenChange={setIsChapterSheetOpen}>
        <SheetContent
          side="left"
          data-testid="chapter-sheet-content"
          className={`gap-0 border-[var(--warm-300)]/50 bg-[var(--warm-50)] p-0 text-[var(--warm-900)] ${
            isMobile
              ? "w-[100vw] max-w-[100vw]"
              : "w-[min(880px,calc(100vw-40px))] max-w-[min(880px,calc(100vw-40px))] sm:max-w-none"
          }`}
        >
          <SheetHeader className="border-b border-[var(--warm-200)] bg-[var(--warm-50)] px-5 py-5 pr-12">
            <SheetTitle
              className="font-['Lora',Georgia,serif] text-[var(--warm-950)]"
              style={{ fontSize: "1.25rem", lineHeight: 1.2 }}
            >
              {readerBookTitle}
            </SheetTitle>
            <SheetDescription
              className="text-[var(--warm-600)]"
              style={{ fontSize: "0.84rem", lineHeight: 1.6 }}
            >
              {chapterItems.length} chapters
            </SheetDescription>
          </SheetHeader>

          <div className={`min-h-0 flex-1 overflow-hidden ${isMobile ? "flex flex-col" : "grid grid-cols-[304px_minmax(0,1fr)]"}`}>
            <div className={`rc-scrollbar min-h-0 overflow-y-auto ${isMobile ? "flex-1 px-3 py-3" : "border-r border-[var(--warm-200)] bg-[var(--warm-100)]/78 px-3 py-3"}`}>
              {isMobile && mobileChapterSheetView === "sections" ? (
                <div className="mb-3 flex items-center gap-2 px-1">
                  <button
                    type="button"
                    onClick={() => setMobileChapterSheetView("chapters")}
                    className="inline-flex h-8 items-center gap-2 rounded-full border border-[var(--warm-300)]/65 bg-white/86 px-3 text-[var(--warm-700)] shadow-[0_1px_0_rgba(255,255,255,0.88)] transition-all duration-200 hover:bg-white"
                    style={{ fontSize: "0.76rem", fontWeight: 600 }}
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    {copy("chapter.sheet.backToChapters")}
                  </button>
                </div>
              ) : null}

              {(!isMobile || mobileChapterSheetView === "chapters") ? (
                <div className="space-y-1.5">
                  {chapterItems.map((chapter) => {
                    const isCurrent = chapter.chapter_id === payload.chapter_id;
                    const chapterTitle =
                      chapter.title && chapter.title !== chapter.chapter_ref ? chapter.title : chapter.chapter_ref;
                    const chapterMeta =
                      chapter.title && chapter.title !== chapter.chapter_ref ? chapter.chapter_ref : null;
                    const StatusIcon = isCurrent
                      ? CheckCircle2
                      : !chapter.result_ready
                        ? chapter.status === "error"
                          ? AlertTriangle
                          : CircleDashed
                        : CheckCircle2;
                    const chapterStateLabel = isCurrent
                      ? copy("chapter.sheet.status.current")
                      : !chapter.result_ready
                        ? chapter.status === "error"
                          ? copy("chapter.sheet.status.error")
                          : copy("chapter.sheet.status.pending")
                        : chapter.status === "error"
                          ? copy("chapter.sheet.status.error")
                          : copy("chapter.sheet.status.completed");
                    const isPreviewing = previewChapterId === chapter.chapter_id;

                    return (
                      <button
                        key={chapter.chapter_id}
                        type="button"
                        data-testid={`chapter-sheet-item-${chapter.chapter_id}`}
                        disabled={!chapter.result_ready && !isCurrent}
                        onMouseEnter={() => handleChapterPreview(chapter)}
                        onFocus={() => handleChapterPreview(chapter)}
                        onClick={() => {
                          if (isMobile) {
                            openMobileChapterSections(chapter);
                            return;
                          }
                          if (!chapter.result_ready || isCurrent) {
                            return;
                          }
                          openChapter(chapter.chapter_id);
                        }}
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                          isCurrent
                            ? "border-[var(--amber-accent)]/28 bg-[var(--amber-bg)]/85 shadow-[0_1px_0_rgba(255,255,255,0.88),0_18px_34px_rgba(139,105,20,0.09)]"
                            : isPreviewing
                              ? "border-[var(--warm-300)]/60 bg-white/92 shadow-[0_1px_0_rgba(255,255,255,0.9),0_14px_32px_rgba(61,46,31,0.06)]"
                              : chapter.result_ready
                                ? "border-[var(--warm-300)]/28 bg-white/72 hover:-translate-y-[1px] hover:border-[var(--warm-400)]/55 hover:bg-white"
                                : "cursor-not-allowed border-[var(--warm-300)]/20 bg-[var(--warm-100)]/70 opacity-80"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            {chapterMeta ? (
                              <p
                                className="mb-1 text-[var(--warm-500)]"
                                style={{ fontSize: "0.69rem", fontWeight: 600, lineHeight: 1.3 }}
                              >
                                {chapterMeta}
                              </p>
                            ) : null}
                            <OverflowTooltipText
                              as="p"
                              text={chapterTitle}
                              lines={2}
                              side="right"
                              className="text-[var(--warm-950)]"
                              style={{ fontSize: "0.9rem", fontWeight: 600, lineHeight: 1.45, maxWidth: "14.25rem" }}
                            />
                            <p
                              className="mt-1 text-[var(--warm-600)]"
                              style={{ fontSize: "0.74rem", lineHeight: 1.55 }}
                            >
                              {chapter.visible_reaction_count} reactions
                            </p>
                          </div>

                          <div className="flex shrink-0 items-center gap-2">
                            <span
                              className={`inline-flex rounded-full border px-2.5 py-1 ${
                                isCurrent
                                  ? "border-[var(--amber-accent)]/30 bg-white/78 text-[var(--amber-accent)]"
                                  : chapter.result_ready
                                    ? "border-[var(--warm-300)]/45 bg-[var(--warm-50)] text-[var(--warm-600)]"
                                    : chapter.status === "error"
                                      ? "border-red-200 bg-red-50 text-red-700"
                                      : "border-[var(--warm-300)]/40 bg-[var(--warm-50)] text-[var(--warm-500)]"
                              }`}
                              style={{ fontSize: "0.69rem", fontWeight: 600 }}
                            >
                              <StatusIcon className="mr-1 h-3 w-3" />
                              {chapterStateLabel}
                            </span>
                            {(chapter.result_ready && !isCurrent) || (isMobile && chapter.result_ready) ? (
                              <ChevronRight className="h-4 w-4 text-[var(--warm-400)]" />
                            ) : null}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ) : null}

              {isMobile && mobileChapterSheetView === "sections" ? (
                previewOutlineLoading ? (
                  <div className="flex min-h-[14rem] items-center justify-center">
                    <p className="inline-flex items-center gap-2 text-[var(--warm-600)]" style={{ fontSize: "0.82rem" }}>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading chapter outline...
                    </p>
                  </div>
                ) : !previewChapter?.result_ready ? (
                  <div className="rounded-2xl border border-[var(--warm-300)]/35 bg-[var(--warm-50)]/78 px-4 py-5">
                    <p className="text-[var(--warm-900)]" style={{ fontSize: "0.88rem", fontWeight: 600 }}>
                      This chapter is not ready yet.
                    </p>
                  </div>
                ) : previewHasOutlineContent ? (
                  <div className="space-y-2">
                    {renderOutlineHeadingBlock(previewChapterHeading, "mobile")}
                    {(previewOutline?.sections ?? []).map((section) => {
                      const isCurrentSection =
                        previewChapterId === payload.chapter_id && currentReadingSectionRef === section.section_ref;
                      return (
                        <button
                          key={section.section_ref}
                          type="button"
                          onClick={() => handleOutlineSectionClick(section)}
                          className={`w-full rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                            isCurrentSection
                              ? "border-[var(--amber-accent)]/28 bg-[var(--amber-bg)]/82"
                              : "border-[var(--warm-300)]/28 bg-white/86 hover:-translate-y-[1px] hover:border-[var(--warm-400)]/55 hover:bg-white"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-[var(--amber-accent)]" style={{ fontSize: "0.7rem", fontWeight: 600 }}>
                                {section.section_ref}
                              </p>
                              <OverflowTooltipText
                                as="p"
                                text={section.summary}
                                lines={2}
                                side="right"
                                className="mt-1 text-[var(--warm-950)]"
                                style={{ fontSize: "0.9rem", fontWeight: 600, lineHeight: 1.45 }}
                              />
                              {section.preview_text ? (
                                <p className="mt-1 text-[var(--warm-600)]" style={{ fontSize: "0.76rem", lineHeight: 1.55 }}>
                                  {section.preview_text}
                                </p>
                              ) : null}
                            </div>
                            <div className="shrink-0 text-right">
                              <p className="text-[var(--warm-500)]" style={{ fontSize: "0.7rem", fontWeight: 600 }}>
                                {section.visible_reaction_count}
                              </p>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                    <div className="rounded-2xl border border-[var(--warm-300)]/35 bg-[var(--warm-50)]/78 px-4 py-5">
                      <p className="text-[var(--warm-900)]" style={{ fontSize: "0.88rem", fontWeight: 600 }}>
                        {copy("chapter.sheet.emptySections")}
                      </p>
                    </div>
                )
              ) : null}
            </div>

            {!isMobile ? (
              <div className="min-h-0 overflow-hidden bg-white/68">
                <div className="border-b border-[var(--warm-200)] bg-[var(--warm-50)]/94 px-5 py-4">
                  <p className="text-[var(--warm-500)] uppercase tracking-[0.16em]" style={{ fontSize: "0.64rem", fontWeight: 600 }}>
                    {copy("chapter.sheet.inThisChapter")}
                  </p>
                  <div className="mt-1 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <OverflowTooltipText
                        as="p"
                        text={previewOutline?.title || previewChapter?.title || previewChapter?.chapter_ref || copy("chapter.sheet.previewFallback")}
                        lines={1}
                        side="bottom"
                        className="text-[var(--warm-950)] font-['Lora',Georgia,serif]"
                        style={{ fontSize: "1.02rem", fontWeight: 700, lineHeight: 1.25, maxWidth: "26rem" }}
                      />
                      <p className="mt-1 text-[var(--warm-600)]" style={{ fontSize: "0.76rem", lineHeight: 1.5 }}>
                        {(previewOutline?.section_count ?? previewChapter?.segment_count ?? 0)} sections
                      </p>
                    </div>
                    {previewChapter?.chapter_ref ? (
                      <span className="inline-flex h-8 items-center rounded-full border border-[var(--warm-300)]/68 bg-white/84 px-3 text-[var(--warm-700)] shadow-[0_1px_0_rgba(255,255,255,0.88)]" style={{ fontSize: "0.72rem", fontWeight: 600 }}>
                        {previewChapter.chapter_ref}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="rc-scrollbar h-full overflow-y-auto px-4 py-4">
                  {previewOutlineLoading ? (
                    <div className="flex h-full min-h-[16rem] items-center justify-center">
                      <p className="inline-flex items-center gap-2 text-[var(--warm-600)]" style={{ fontSize: "0.82rem" }}>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {copy("chapter.sheet.loadingOutline")}
                      </p>
                    </div>
                  ) : !previewChapter?.result_ready ? (
                    <div className="rounded-2xl border border-[var(--warm-300)]/35 bg-[var(--warm-50)]/78 px-4 py-5">
                      <p className="text-[var(--warm-900)]" style={{ fontSize: "0.88rem", fontWeight: 600 }}>
                        {copy("chapter.sheet.notReadyTitle")}
                      </p>
                      <p className="mt-1 text-[var(--warm-600)]" style={{ fontSize: "0.78rem", lineHeight: 1.65 }}>
                        {copy("chapter.sheet.notReadyMessage")}
                      </p>
                    </div>
                  ) : !previewHasOutlineContent ? (
                    <div className="rounded-2xl border border-[var(--warm-300)]/35 bg-[var(--warm-50)]/78 px-4 py-5">
                      <p className="text-[var(--warm-900)]" style={{ fontSize: "0.88rem", fontWeight: 600 }}>
                        {copy("chapter.sheet.emptySections")}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {renderOutlineHeadingBlock(previewChapterHeading, "desktop")}
                      {previewSectionItems.map((section) => {
                        const isCurrentSection =
                          previewChapterId === payload.chapter_id && currentReadingSectionRef === section.section_ref;
                        return (
                          <button
                            key={section.section_ref}
                            type="button"
                            data-testid={`chapter-outline-section-${previewChapterId}-${section.section_ref}`}
                            onClick={() => handleOutlineSectionClick(section)}
                            className={`w-full rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                              isCurrentSection
                                ? "border-[var(--amber-accent)]/28 bg-[var(--amber-bg)]/78 shadow-[0_1px_0_rgba(255,255,255,0.88),0_14px_30px_rgba(139,105,20,0.08)]"
                                : "border-[var(--warm-300)]/26 bg-white/88 hover:-translate-y-[1px] hover:border-[var(--warm-400)]/55 hover:bg-white"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-[var(--amber-accent)]" style={{ fontSize: "0.7rem", fontWeight: 600 }}>
                                  {section.section_ref}
                                </p>
                                <OverflowTooltipText
                                  as="p"
                                  text={section.summary}
                                  lines={2}
                                  side="right"
                                  className="mt-1 text-[var(--warm-950)]"
                                  style={{ fontSize: "0.88rem", fontWeight: 600, lineHeight: 1.42 }}
                                />
                                {section.preview_text ? (
                                  <p className="mt-1.5 text-[var(--warm-600)]" style={{ fontSize: "0.77rem", lineHeight: 1.6 }}>
                                    {section.preview_text}
                                  </p>
                                ) : null}
                              </div>
                              <div className="shrink-0 text-right">
                                {isCurrentSection ? (
                                  <p className="text-[var(--amber-accent)]" style={{ fontSize: "0.68rem", fontWeight: 600 }}>
                                    Reading
                                  </p>
                                ) : null}
                                <p className="mt-1 text-[var(--warm-500)]" style={{ fontSize: "0.7rem", fontWeight: 600 }}>
                                  {section.visible_reaction_count} reactions
                                </p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <SheetFooter className="border-t border-[var(--warm-200)] bg-[var(--warm-50)] px-5 py-4">
            <Link
              to={canonicalBookPath(payload.book_id)}
              data-testid="chapter-sheet-book-overview-link"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[var(--warm-300)]/60 bg-white/84 px-4 text-[var(--warm-600)] no-underline shadow-[0_1px_0_rgba(255,255,255,0.88),0_10px_24px_rgba(61,46,31,0.04)] transition-all duration-200 hover:-translate-y-[1px] hover:border-[var(--warm-400)] hover:bg-white hover:text-[var(--warm-900)]"
              style={{ fontSize: "0.82rem", fontWeight: 600 }}
            >
              Open book overview
            </Link>
          </SheetFooter>
        </SheetContent>

      <div className="rc-workspace-topbar flex-shrink-0 border-b border-[var(--warm-200)]/70 bg-[var(--warm-100)] shadow-[0_1px_0_rgba(255,252,245,0.65)]" data-testid="chapter-topbar">
        <div className={headerOuterPaddingClass}>
          <div className="flex items-center justify-between gap-4 overflow-hidden">
            <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden text-[var(--warm-900)]">
              <OverflowTooltipText
                as="p"
                text={bookTitle}
                lines={1}
                side="bottom"
                className="min-w-0 max-w-[20rem] shrink truncate text-[var(--warm-500)] xl:max-w-[24rem]"
                style={{ fontSize: "0.82rem", fontWeight: 500, lineHeight: 1.35 }}
              />
              <span className="shrink-0 text-[var(--warm-400)]" style={{ fontSize: "0.8rem" }}>
                ›
              </span>
              <OverflowTooltipText
                as="p"
                text={showSeparateChapterTitle ? currentChapterTitle : currentChapterRef}
                lines={1}
                side="bottom"
                className="min-w-0 shrink-0 text-[var(--warm-800)]"
                style={{ fontSize: "0.88rem", fontWeight: 600, lineHeight: 1.35 }}
              />
              <span className="shrink-0 text-[var(--warm-400)]" style={{ fontSize: "0.8rem" }}>
                ›
              </span>
              <div className="min-w-0 flex-1" data-testid="chapter-topbar-current-section">
                <OverflowTooltipText
                  as="p"
                  text={currentWorkspaceSection ? `${currentWorkspaceSection.section_ref} ${currentWorkspaceSection.summary}` : "--"}
                  lines={1}
                  side="bottom"
                  className="min-w-0 truncate text-[var(--warm-800)]"
                  style={{ fontSize: "0.88rem", fontWeight: 600, lineHeight: 1.35 }}
                />
              </div>
            </div>

            <div className="ml-auto flex shrink-0 items-center gap-1.5">
              {showChapterSwitcher ? (
                <SheetTrigger asChild>
                  <button
                    type="button"
                    data-testid="chapter-sheet-trigger"
                    className={workspaceGhostLinkClass}
                    style={{ fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    <List className="h-4 w-4" />
                    {!workspaceMobile ? term("view.chapters") : null}
                  </button>
                </SheetTrigger>
              ) : null}

              <div className="flex items-center gap-1">
                <span className="shrink-0 text-[var(--warm-400)]" style={{ fontSize: "0.74rem", fontWeight: 500 }}>
                  {term("view.chapterShort")}
                </span>
                {renderToolbarIconButton({
                  ariaLabel: "Previous chapter",
                  className: chapterNavButtonClass,
                  disabled: !previousReadableChapter,
                  icon: <ChevronLeft className="h-4 w-4" />,
                  onClick: () => stepChapter(previousReadableChapter),
                  testId: "chapter-topbar-prev-chapter",
                  tooltip: copy("chapter.tooltip.prevChapter"),
                })}
                {renderToolbarIconButton({
                  ariaLabel: "Next chapter",
                  className: chapterNavButtonClass,
                  disabled: !nextReadableChapter,
                  icon: <ChevronRight className="h-4 w-4" />,
                  onClick: () => stepChapter(nextReadableChapter),
                  testId: "chapter-topbar-next-chapter",
                  tooltip: copy("chapter.tooltip.nextChapter"),
                })}
              </div>

              <span className="shrink-0 text-[var(--warm-300)]" style={{ fontSize: "0.76rem", fontWeight: 500 }}>
                |
              </span>

              <div className="flex items-center gap-1">
                <span className="shrink-0 text-[var(--warm-400)]" style={{ fontSize: "0.74rem", fontWeight: 500 }}>
                  {term("view.sectionShort")}
                </span>
                {renderToolbarIconButton({
                  ariaLabel: "Previous section",
                  className: sectionNavButtonClass,
                  disabled: !previousSection,
                  icon: <ChevronLeft className="h-3.5 w-3.5" />,
                  onClick: () => stepSection(previousSection),
                  testId: "chapter-topbar-prev-section",
                  tooltip: copy("chapter.tooltip.prevSection"),
                })}
                {renderToolbarIconButton({
                  ariaLabel: "Next section",
                  className: sectionNavButtonClass,
                  disabled: !nextSection,
                  icon: <ChevronRight className="h-3.5 w-3.5" />,
                  onClick: () => stepSection(nextSection),
                  testId: "chapter-topbar-next-section",
                  tooltip: copy("chapter.tooltip.nextSection"),
                })}
              </div>

              <Link
                to={canonicalBookPath(payload.book_id)}
                aria-label={term("view.bookOverview")}
                className={workspaceOverviewLinkClass}
                style={{ fontSize: "0.8rem", fontWeight: 600 }}
              >
                <ArrowLeft className="h-4 w-4" />
                {primaryBookActionLabel}
              </Link>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between gap-4 border-t border-[var(--warm-200)]/55 pt-2">
            <div className="flex min-w-0 flex-1 items-center gap-3 overflow-hidden">
              <div className="overflow-x-auto pb-0.5 rc-scrollbar-none">
                <div className={filterRailClass}>
                  {renderedFilters.map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => handleFilterChange(filter)}
                      data-testid={`reaction-filter-${filter}`}
                      className={filterToneClass(filter, activeFilter === filter)}
                      style={{ fontSize: scaledRem(workspaceCompact ? 0.72 : 0.75), fontWeight: 600 }}
                    >
                      {filter === "all" ? copy("chapter.filter.all") : reactionLabel(filter)}
                    </button>
                  ))}
                </div>
              </div>

              <p className="shrink-0 text-[var(--warm-500)]" style={{ fontSize: scaledRem(0.8), lineHeight: 1.4, fontWeight: 500 }}>
                {payload.visible_reaction_count} reactions
              </p>
            </div>

            <div className="ml-auto flex shrink-0 items-center gap-3">
              <div className={toolbarValueClass} data-testid="chapter-topbar-book-progress">
                <p style={{ fontSize: "0.82rem", fontWeight: 500, lineHeight: 1.35 }}>
                  {readerProgress == null || Number.isNaN(readerProgress)
                    ? copy("chapter.reader.bookProgressUnavailable")
                    : copy("chapter.reader.bookProgress", { value: formatReaderProgress(readerProgress) })}
                </p>
              </div>

              <Popover>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    data-testid="chapter-topbar-settings-trigger"
                    aria-label={copy("chapter.reader.settingsAria")}
                    className={workspaceGhostLinkClass}
                    style={{ fontSize: "0.8rem", fontWeight: 500 }}
                  >
                    <Settings2 className="h-4 w-4" />
                    {!workspaceMobile ? term("view.textSize") : null}
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  align="end"
                  className="w-[18rem] rounded-2xl border-[var(--warm-300)]/60 bg-[var(--warm-50)]/96 p-4 text-[var(--warm-900)] shadow-[0_18px_40px_rgba(61,46,31,0.12)]"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[var(--warm-900)]" style={{ fontSize: "0.88rem", fontWeight: 700 }}>
                          {copy("chapter.reader.settingsTitle")}
                        </p>
                        <p className="mt-1 text-[var(--warm-600)]" style={{ fontSize: "0.76rem", lineHeight: 1.55 }}>
                          {copy("chapter.reader.settingsDescription")}
                        </p>
                      </div>
                      <span
                        className="inline-flex h-8 items-center rounded-full border border-[var(--warm-300)]/60 bg-white/84 px-3 text-[var(--warm-700)]"
                        style={{ fontSize: "0.74rem", fontWeight: 700 }}
                      >
                        {fontSizePercent}%
                      </span>
                    </div>
                    <Slider
                      min={READER_FONT_SIZE_MIN}
                      max={READER_FONT_SIZE_MAX}
                      step={READER_FONT_SIZE_STEP}
                      value={[fontSizePercent]}
                      onValueChange={(value) => {
                        setFontSizePercent(clampReaderFontSize(value[0] ?? fontSizePercent));
                      }}
                    />
                    <div className="flex items-center justify-between text-[var(--warm-500)]" style={{ fontSize: "0.7rem", fontWeight: 600 }}>
                      <span>{READER_FONT_SIZE_MIN}%</span>
                      <span>{READER_FONT_SIZE_MAX}%</span>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>
      </div>

      {error ? (
        <div className="px-6 pt-4">
          <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
            {error}
          </p>
        </div>
      ) : null}

      <div className="flex-1 overflow-hidden bg-[var(--warm-100)]">
        {isMobile ? (
          <Tabs
            value={mobileMode}
            onValueChange={(next) => setMobileMode(next as ReaderPanelMode)}
            className="h-full"
          >
            <div className="px-4 py-2 border-b border-[var(--warm-200)]">
              <TabsList className="w-full max-w-xs">
                <TabsTrigger value="notes">{copy("chapter.reader.tabReactions")}</TabsTrigger>
                <TabsTrigger value="book">{copy("chapter.reader.tabOriginalBook")}</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent forceMount value="notes" className="h-[calc(100%-58px)] data-[state=inactive]:hidden">
              {renderNotesPane()}
            </TabsContent>
            <TabsContent forceMount value="book" className="h-[calc(100%-58px)] data-[state=inactive]:hidden">
              <SourceReaderPane
                sourceUrl={sourceUrl}
                fontSizePercent={fontSizePercent}
                sections={payload.sections}
                jumpRequest={jumpRequest}
                onLocationChange={(update: ReaderLocationUpdate) => {
                  setReaderProgress(update.location.progress);
                  if (!update.programmatic) {
                    setPassiveSectionRef(update.location.sectionRef);
                  }
                }}
              />
            </TabsContent>
          </Tabs>
        ) : (
          <ResizablePanelGroup
            direction="horizontal"
            autoSaveId={`chapter-workspace:${payload.book_id}:${chapterNumber}`}
            className="h-full bg-[var(--warm-100)]"
          >
            <ResizablePanel defaultSize={45} minSize={28} className="bg-[var(--warm-100)]">
              {renderNotesPane()}
            </ResizablePanel>
            <ResizableHandle withHandle className={workspaceCompact ? "w-[5px] after:inset-y-4 after:bg-[var(--warm-300)]/42" : undefined} />
            <ResizablePanel defaultSize={55} minSize={35} className="bg-[var(--warm-100)]">
              <SourceReaderPane
                sourceUrl={sourceUrl}
                fontSizePercent={fontSizePercent}
                sections={payload.sections}
                jumpRequest={jumpRequest}
                onLocationChange={(update: ReaderLocationUpdate) => {
                  setReaderProgress(update.location.progress);
                  if (!update.programmatic) {
                    setPassiveSectionRef(update.location.sectionRef);
                  }
                }}
              />
            </ResizablePanel>
          </ResizablePanelGroup>
        )}
      </div>
      </Sheet>
    </div>
  );
}
