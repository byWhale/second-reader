import {
  Activity,
  ArrowUpRight,
  ArrowRight,
  BookOpen,
  Bookmark,
  Download,
  LoaderCircle,
  MapPin,
  Search,
  Sparkles,
  TreePine,
} from "lucide-react";
import { type CSSProperties, type ReactNode, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  type ActivityEvent,
  type AnalysisStateResponse,
  type BookDetailResponse,
  type BookMarksResponse,
  fetchBookDetail,
  fetchBookMarks,
  getErrorMessage,
  getErrorPresentation,
  resumeBookAnalysis,
  startBookAnalysis,
  toApiAssetUrl,
} from "../lib/api";
import { canonicalChapterPath } from "../lib/contract";
import { useBookAnalysisResource } from "../lib/use-book-analysis-resource";
import { useApiResource } from "../lib/use-api-resource";
import { copy, copyForLocale, maybeCopy, type ControlledCopyKey } from "../config/controlled-copy";
import type { AppLocale } from "../config/app-locale";
import { term } from "../config/product-lexicon";
import { markLabel } from "../lib/marks";
import { reactionLabel } from "../lib/reactions";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import { useViewportResponsiveTier } from "./ui/use-responsive-tier";

type StructureViewMode = "outline" | "progress" | "result";
type OverviewChapter = {
  chapter_id: number;
  chapter_ref: string;
  title: string;
  segment_count: number;
  visible_reaction_count: number;
  result_ready: boolean;
  status: string;
  is_current: boolean;
};

type RuntimeStateSummary = {
  label: string;
  detail: string;
  toneClassName: string;
};

type MessageParams = Record<string, string | number | null | undefined>;

function formatTimestamp(value?: string | null) {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function totalBookReactionCount(detail: BookDetailResponse) {
  return Object.values(detail.reaction_counts ?? {}).reduce((sum, count) => sum + Number(count || 0), 0);
}

function normalizeMessageParams(
  value?: Record<string, unknown> | null,
): MessageParams | undefined {
  if (!value) {
    return undefined;
  }
  const normalized: MessageParams = {};
  for (const [key, entry] of Object.entries(value)) {
    if (
      entry == null ||
      typeof entry === "string" ||
      typeof entry === "number"
    ) {
      normalized[key] = entry as string | number | null;
    }
  }
  return Object.keys(normalized).length ? normalized : undefined;
}

function resolveStructuredCopy(
  key?: string | null,
  params?: Record<string, unknown> | null,
  fallback?: string | null,
) {
  return maybeCopy(key, normalizeMessageParams(params)) ?? fallback ?? null;
}

function resolveCurrentStep(analysis: AnalysisStateResponse | null) {
  return (
    resolveStructuredCopy(
      analysis?.current_state_panel.current_phase_step_key ?? analysis?.current_phase_step_key,
      analysis?.current_state_panel.current_phase_step_params ?? analysis?.current_phase_step_params,
    ) ?? copy("overview.runtime.pending")
  );
}

function hasWaitingStep(analysis: AnalysisStateResponse | null) {
  const key =
    analysis?.current_state_panel.current_phase_step_key ?? analysis?.current_phase_step_key ?? "";
  if (
    key === "system.step.waitingToResume" ||
    key === "system.step.waitingCurrentChapterSegmentation" ||
    key === "system.step.waitingFirstChapterSegmentation" ||
    key === "system.step.waitingNextChapterSegmentation"
  ) {
    return true;
  }
  return false;
}

function isAnalysisParsing(analysis: AnalysisStateResponse | null) {
  if (!analysis) {
    return false;
  }
  const stepKey = analysis.current_state_panel.current_phase_step_key ?? analysis.current_phase_step_key ?? "";
  if (
    stepKey === "system.step.prepareChapterStructure" ||
    stepKey === "system.step.segmenting" ||
    stepKey === "system.step.structureCheckpointSaved" ||
    stepKey === "system.step.structureParseFailed" ||
    stepKey === "system.step.prefetchFutureChapters" ||
    stepKey === "system.step.prepareFirstChapter" ||
    stepKey === "system.step.waitingFirstChapterSegmentation"
  ) {
    return true;
  }
  return analysis.status === "parsing_structure";
}

function buildOverviewChapters(detail: BookDetailResponse, analysis: AnalysisStateResponse | null): OverviewChapter[] {
  const analysisById = new Map(analysis?.chapters.map((chapter) => [chapter.chapter_id, chapter]) ?? []);

  return detail.chapters.map((chapter) => {
    const analysisChapter = analysisById.get(chapter.chapter_id);
    return {
      chapter_id: chapter.chapter_id,
      chapter_ref: chapter.chapter_ref,
      title: chapter.title,
      segment_count: analysisChapter?.segment_count ?? chapter.segment_count,
      visible_reaction_count: chapter.visible_reaction_count,
      result_ready: analysisChapter?.result_ready ?? chapter.result_ready,
      status: analysisChapter?.status ?? chapter.status,
      is_current: analysisChapter?.is_current ?? false,
    };
  });
}

function describeRuntimeState(
  detail: BookDetailResponse,
  analysis: AnalysisStateResponse | null,
  options: { isParsing: boolean },
): RuntimeStateSummary {
  const phase = resolveCurrentStep(analysis).trim();
  const waiting = hasWaitingStep(analysis);
  const hasReaderFocus = Boolean((analysis?.current_state_panel.current_section_ref ?? "").trim());
  const completedChapters = analysis?.completed_chapters ?? detail.completed_chapter_count;

  if (detail.status === "paused") {
    return {
      label: copy("overview.runtime.state.paused.label"),
      detail: phase || copy("overview.runtime.state.paused.detail"),
      toneClassName: "text-[var(--warm-700)]",
    };
  }

  if (waiting && completedChapters > 0) {
    return {
      label: copy("overview.runtime.state.blocked.label"),
      detail: copy("overview.runtime.state.blocked.detail"),
      toneClassName: "text-[var(--destructive)]",
    };
  }

  if (waiting) {
    return {
      label: copy("overview.runtime.state.preparing.label"),
      detail: copy("overview.runtime.state.preparing.detail"),
      toneClassName: "text-[var(--amber-accent)]",
    };
  }

  if (options.isParsing) {
    return {
      label: copy("overview.runtime.state.segmenting.label"),
      detail: phase || copy("overview.runtime.state.segmenting.detail"),
      toneClassName: "text-[var(--amber-accent)]",
    };
  }

  if (hasReaderFocus) {
    return {
      label: copy("overview.runtime.state.reading.label"),
      detail: analysis?.current_state_panel.current_section_ref ?? copy("overview.runtime.state.reading.detail"),
      toneClassName: "text-[var(--amber-accent)]",
    };
  }

  return {
    label: copy("overview.runtime.state.running.label"),
    detail: phase || copy("overview.runtime.state.running.detail"),
    toneClassName: "text-[var(--warm-800)]",
  };
}

function structureStatusLabel(
  chapter: OverviewChapter,
  viewMode: StructureViewMode,
  options: { isParsing?: boolean; isPaused?: boolean } = {},
) {
  if (viewMode === "outline") {
    return term("state.notStarted");
  }

  if (viewMode === "result") {
    if (chapter.status === "error") {
      return term("state.needsAttention");
    }
    return term("state.completed");
  }

  if (chapter.status === "error") {
    return term("state.needsAttention");
  }
  if (chapter.status === "completed") {
    return options.isParsing || chapter.result_ready ? term("state.openResult") : term("state.analyzing");
  }
  if (chapter.status === "in_progress") {
    if (options.isPaused) {
      return term("state.paused");
    }
    return options.isParsing ? term("state.segmenting") : term("state.reading");
  }
  return term("state.waiting");
}

function chapterDisplayParts(chapter: OverviewChapter) {
  const chapterRef = chapter.chapter_ref?.trim() ?? "";
  const chapterTitle = chapter.title?.trim() ?? "";
  const hasDistinctTitle = chapterTitle.length > 0 && chapterTitle !== chapterRef;

  return {
    eyebrow: hasDistinctTitle ? chapterRef : null,
    title: hasDistinctTitle ? chapterTitle : chapterRef || chapterTitle,
  };
}

function currentChapterRuntimeLabel(
  chapter: OverviewChapter,
  analysis: AnalysisStateResponse | null,
  options: { isParsing: boolean },
) {
  if (!analysis || !chapter.is_current) {
    return null;
  }

  const panel = analysis.current_state_panel;
  const currentChapterRef = (panel.current_chapter_ref ?? analysis.current_chapter_ref ?? "").trim();
  const chapterMatches =
    !currentChapterRef ||
    currentChapterRef === chapter.chapter_ref ||
    currentChapterRef === chapter.title;

  if (!chapterMatches) {
    return null;
  }

  const step =
    resolveStructuredCopy(
      panel.current_phase_step_key ?? analysis.current_phase_step_key,
      panel.current_phase_step_params ?? analysis.current_phase_step_params,
    )?.trim() ?? "";
  if (options.isParsing) {
    if (hasWaitingStep(analysis)) {
      return chapter.result_ready ? copy("overview.runtime.waitingResume") : copy("overview.runtime.waitingNext");
    }
    return step
      ? copy("overview.runtime.currentStep.prefix", { value: step })
      : copy("overview.runtime.currentStep.preparing");
  }

  const sectionRef = (panel.current_section_ref ?? "").trim();
  if (sectionRef) {
    return copy("overview.runtime.readingSection", { value: sectionRef });
  }

  if (hasWaitingStep(analysis)) {
    return copy("overview.runtime.waitingNext");
  }

  return step
    ? copy("overview.runtime.currentStatus.prefix", { value: step })
    : copy("overview.runtime.currentStatus.reading");
}

function BookOverviewHeader({
  title,
  author,
  coverImageUrl,
  markCount,
  children,
}: {
  title: string;
  author: string;
  coverImageUrl?: string | null;
  markCount: number;
  children?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-5 md:mb-8 md:flex-row md:gap-6">
      <div className="h-38 w-28 rounded-2xl overflow-hidden bg-[var(--warm-200)] shadow-sm md:h-42 md:w-32 md:flex-shrink-0">
        {coverImageUrl ? (
          <ImageWithFallback
            src={toApiAssetUrl(coverImageUrl) ?? ""}
            alt={title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--warm-500)]">
            <BookOpen className="w-10 h-10" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h1
          className="mb-1 text-[var(--warm-900)] text-[1.75rem] leading-none md:text-[2.5rem]"
          style={{ fontWeight: 600 }}
        >
          {title}
        </h1>
        <p className="mb-3 text-[var(--warm-600)] md:mb-4" style={{ fontSize: "0.9375rem" }}>
          {author}
        </p>

        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[var(--warm-600)] md:mb-5" style={{ fontSize: "0.8125rem" }}>
          <span className="inline-flex items-center gap-1.5">
            <Bookmark className="w-4 h-4" />
            {markCount} marks
          </span>
        </div>

        {children}
      </div>
    </div>
  );
}

function StatusMetric({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={`rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 ${compact ? "p-3" : "p-3.5 md:p-4"}`}>
      <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: compact ? "0.6875rem" : "0.75rem" }}>
        {label}
      </p>
      <p
        className="text-[var(--warm-900)]"
        style={{ fontSize: compact ? "0.9375rem" : "1.125rem", fontWeight: 600, lineHeight: compact ? 1.5 : undefined }}
      >
        {value}
      </p>
    </div>
  );
}

function BookOverviewStatusBand({
  detail,
  analysis,
  activity,
  contentLanguage,
  analysisLoading,
  analysisError,
  onRetryAnalysis,
}: {
  detail: BookDetailResponse;
  analysis: AnalysisStateResponse | null;
  activity: ActivityEvent[];
  contentLanguage: ContentLocale;
  analysisLoading: boolean;
  analysisError: unknown | null;
  onRetryAnalysis: () => void;
}) {
  if (detail.status === "not_started") {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm mb-8">
        <div className="flex items-start justify-between gap-6 flex-col md:flex-row">
          <div>
            <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
              {copy("overview.section.readyToStart")}
            </p>
            <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.25rem", fontWeight: 600 }}>
              {detail.chapter_count > 0 ? copy("overview.ready.title.ready") : copy("overview.ready.title.preparing")}
            </h2>
            <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
              {copy("overview.ready.description")}
            </p>
          </div>
          <div className="w-full md:w-64">
            <StatusMetric label={copy("overview.metric.parsedChapters")} value={detail.chapter_count} />
          </div>
        </div>
      </section>
    );
  }

  if (detail.status === "completed") {
    const surfacedReactions = totalBookReactionCount(detail);
    return (
      <section className="mb-8 rounded-3xl border border-[var(--warm-300)]/30 bg-white p-6 shadow-sm">
        <p className="mb-3 text-[var(--amber-accent)] uppercase tracking-[0.18em]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {copy("overview.section.completed")}
        </p>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <h2 className="mb-2 text-[var(--warm-900)]" style={{ fontSize: "1.25rem", fontWeight: 600 }}>
              {copy("overview.completed.title")}
            </h2>
            <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
              {copy("overview.completed.description")}
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:w-[30rem]">
            <StatusMetric label={copy("overview.metric.completedChapters")} value={`${detail.completed_chapter_count}/${detail.chapter_count}`} />
            <StatusMetric label={copy("overview.metric.totalReactions")} value={surfacedReactions} />
            <StatusMetric label={copy("overview.metric.savedMarks")} value={detail.my_mark_count} />
          </div>
        </div>
      </section>
    );
  }

  if (detail.status === "analyzing" || detail.status === "paused") {
    return (
      <MindstreamHeroCard
        detail={detail}
        analysis={analysis}
        activity={activity}
        contentLanguage={contentLanguage}
        loading={analysisLoading}
        error={analysisError}
        onRetry={onRetryAnalysis}
      />
    );
  }

  if (detail.status === "error") {
    return (
      <section className="bg-white rounded-3xl border border-[var(--destructive)]/20 p-6 shadow-sm mb-8">
        <p className="text-[var(--destructive)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {copy("overview.section.interrupted")}
        </p>
        <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
          {copy("overview.error.interruptedTitle")}
        </h2>
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
          {copy("overview.error.interruptedDescription")}
        </p>
      </section>
    );
  }
  return null;
}

function StructureChapterList({
  bookId,
  chapters,
  viewMode,
  isParsing = false,
  isPaused = false,
}: {
  bookId: number;
  chapters: OverviewChapter[];
  viewMode: StructureViewMode;
  isParsing?: boolean;
  isPaused?: boolean;
}) {
  return (
    <div className="space-y-3">
      {chapters.map((chapter) => {
        const statusLabel = structureStatusLabel(chapter, viewMode, { isParsing, isPaused });
        const isInteractive = chapter.result_ready;
        const display = chapterDisplayParts(chapter);
        const wrapperClass = `block rounded-2xl border p-5 no-underline transition-all ${
          chapter.is_current
            ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)]"
            : "border-[var(--warm-300)]/30 bg-white hover:border-[var(--amber-accent)]/30 hover:shadow-sm"
        }`;
        const content = (
          <>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                {display.eyebrow ? (
                  <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                    {display.eyebrow}
                  </p>
                ) : null}
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  {display.title}
                </h2>
              </div>

              <div className="flex items-center gap-4 text-[var(--warm-600)] flex-wrap justify-end" style={{ fontSize: "0.8125rem" }}>
                {viewMode !== "outline" && chapter.segment_count > 0 ? <span>{chapter.segment_count} sections</span> : null}
                {viewMode === "result" ? <span>{chapter.visible_reaction_count} reactions</span> : null}
                <span className="text-[var(--warm-500)]">{statusLabel}</span>
              </div>
            </div>
          </>
        );

        if (!isInteractive) {
          return (
            <div key={chapter.chapter_id} data-testid={`book-overview-chapter-${chapter.chapter_id}`} className={wrapperClass}>
              {content}
            </div>
          );
        }

        return (
          <Link
            key={chapter.chapter_id}
            to={canonicalChapterPath(bookId, chapter.chapter_id)}
            data-testid={`book-overview-chapter-${chapter.chapter_id}`}
            className={wrapperClass}
          >
            {content}
          </Link>
        );
      })}
    </div>
  );
}

function ProcessingStructureNavigator({
  bookId,
  chapters,
  analysis,
  viewMode,
  isParsing = false,
  isPaused = false,
  isCollapsedByDefault = false,
  emptyTitle,
  emptyMessage,
}: {
  bookId: number;
  chapters: OverviewChapter[];
  analysis: AnalysisStateResponse | null;
  viewMode: StructureViewMode;
  isParsing?: boolean;
  isPaused?: boolean;
  isCollapsedByDefault?: boolean;
  emptyTitle: string;
  emptyMessage: string;
}) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const listNode = listRef.current;
    if (!listNode || chapters.length === 0) {
      return;
    }
    const currentRow = listNode.querySelector<HTMLElement>("[data-current='true']");
    if (!currentRow) {
      return;
    }
    const currentTop = currentRow.offsetTop;
    const currentBottom = currentTop + currentRow.offsetHeight;
    const viewportTop = listNode.scrollTop;
    const viewportBottom = viewportTop + listNode.clientHeight;
    const targetTop = Math.max(0, currentTop - (listNode.clientHeight - currentRow.offsetHeight) / 2);

    if (currentTop < viewportTop || currentBottom > viewportBottom) {
      listNode.scrollTo({ top: targetTop, behavior: "smooth" });
    }
  }, [chapters]);

  const content = chapters.length === 0 ? (
    <div className="py-4">
      <EmptyState title={emptyTitle} message={emptyMessage} />
    </div>
  ) : (
    <div ref={listRef} className="space-y-2 overflow-y-auto pr-2 md:max-h-[28rem] lg:max-h-[calc(100vh-11rem)]">
      {chapters.map((chapter) => {
        const statusLabel = structureStatusLabel(chapter, viewMode, { isParsing, isPaused });
        const runtimeLabel = currentChapterRuntimeLabel(chapter, analysis, { isParsing });
        const isInteractive = chapter.result_ready;
        const display = chapterDisplayParts(chapter);
        const wrapperClass = `block rounded-2xl border px-4 py-3 no-underline transition-all ${
          chapter.is_current
            ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)] shadow-sm"
            : "border-[var(--warm-300)]/25 bg-[var(--warm-50)] hover:border-[var(--amber-accent)]/25 hover:bg-white"
        }`;
        const rowContent = (
          <>
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                {display.eyebrow ? (
                  <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                    {display.eyebrow}
                  </p>
                ) : null}
                <p
                  className="text-[var(--warm-900)] line-clamp-2"
                  style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.45 }}
                >
                  {display.title}
                </p>
              </div>
              <div className="shrink-0 text-right space-y-1">
                {viewMode !== "outline" && chapter.segment_count > 0 ? (
                  <p className="text-[var(--warm-600)]" style={{ fontSize: "0.75rem" }}>
                    {chapter.segment_count} sections
                  </p>
                ) : null}
                <span
                  className={`inline-flex rounded-full px-2.5 py-1 ${
                    chapter.is_current
                      ? "bg-white text-[var(--amber-accent)]"
                      : "bg-[var(--warm-100)] text-[var(--warm-500)]"
                  }`}
                  style={{ fontSize: "0.6875rem", fontWeight: 600 }}
                >
                  {statusLabel}
                </span>
              </div>
            </div>

            {viewMode === "result" ? (
              <div className="mt-2 flex items-center gap-3 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                <span>{chapter.visible_reaction_count} reactions</span>
              </div>
            ) : null}

            {runtimeLabel ? (
              <div
                className="mt-2 rounded-xl bg-white/75 px-3 py-2 text-[var(--amber-accent)]"
                style={{ fontSize: "0.75rem", fontWeight: 600, lineHeight: 1.5 }}
              >
                {runtimeLabel}
              </div>
            ) : null}
          </>
        );

        if (!isInteractive) {
          return (
            <div
              key={chapter.chapter_id}
              data-current={chapter.is_current ? "true" : "false"}
              data-testid={`book-overview-structure-nav-${chapter.chapter_id}`}
              className={wrapperClass}
            >
              {rowContent}
            </div>
          );
        }

        return (
          <Link
            key={chapter.chapter_id}
            to={canonicalChapterPath(bookId, chapter.chapter_id)}
            data-current={chapter.is_current ? "true" : "false"}
            data-testid={`book-overview-structure-nav-${chapter.chapter_id}`}
            className={wrapperClass}
          >
            {rowContent}
          </Link>
        );
      })}
    </div>
  );

  if (isCollapsedByDefault) {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-5 shadow-sm">
        <details>
          <summary className="list-none cursor-pointer">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <TreePine className="w-[1.05rem] h-[1.05rem] text-[var(--amber-accent)]" />
                  <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                    {term("view.structure")}
                  </h2>
                </div>
                <p className="mt-1 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                  {copy("overview.structure.mobileHint")}
                </p>
              </div>
              <span className="text-[var(--amber-accent)]" style={{ fontSize: "0.8125rem", fontWeight: 600 }}>
                {copy("overview.structure.expand")}
              </span>
            </div>
          </summary>
          <div className="mt-4">{content}</div>
        </details>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-5 shadow-sm lg:sticky lg:top-28">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <TreePine className="w-[1.05rem] h-[1.05rem] text-[var(--amber-accent)]" />
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              {term("view.structure")}
            </h2>
          </div>
          <p className="mt-1 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
            {copy("overview.structure.desktopHint")}
          </p>
        </div>
      </div>
      {content}
    </section>
  );
}

function CompletedBookSupportingRail({
  detail,
  onOpenMarks,
}: {
  detail: BookDetailResponse;
  onOpenMarks: () => void;
}) {
  const surfacedReactions = totalBookReactionCount(detail);

  return (
    <div className="space-y-4 lg:sticky lg:top-28">
      <section className="rounded-3xl border border-[var(--warm-300)]/30 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--amber-accent)]" />
          <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
            {copy("overview.summary.title")}
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <StatusMetric label={copy("overview.metric.totalReactions")} value={surfacedReactions} />
          <StatusMetric label={copy("overview.metric.savedMarks")} value={detail.my_mark_count} />
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--warm-300)]/30 bg-white p-5 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Bookmark className="h-4 w-4 text-[var(--amber-accent)]" />
          <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
            {copy("overview.marks.summaryTitle")}
          </h2>
        </div>

        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
          {detail.my_mark_count > 0
            ? copy("overview.marks.summaryReady", { count: detail.my_mark_count })
            : copy("overview.marks.summaryEmpty")}
        </p>

        <button
          type="button"
          onClick={onOpenMarks}
          className="mt-4 inline-flex items-center gap-2 rounded-xl border border-[var(--warm-300)]/60 px-4 py-2 text-[var(--warm-700)] transition-colors hover:bg-[var(--warm-100)] cursor-pointer"
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          <Bookmark className="h-4 w-4" />
          {copy("overview.marks.summaryAction")}
        </button>
      </section>
    </div>
  );
}

function BookMarksPanel({
  bookId,
  marks,
}: {
  bookId: number;
  marks: BookMarksResponse;
}) {
  if (marks.groups.length === 0) {
    return (
      <EmptyState
        title={copy("overview.marks.emptyTitle")}
        message={copy("overview.marks.emptyMessage")}
      />
    );
  }

  return (
    <div className="space-y-6">
      {marks.groups.map((group) => (
        <section key={group.chapter_id} className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              {group.chapter_ref}
            </h2>
            <Link
              to={canonicalChapterPath(bookId, group.chapter_id)}
              className="text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
              style={{ fontSize: "0.8125rem", fontWeight: 500 }}
            >
              {copy("marks.action.openChapter")}
            </Link>
          </div>

          <div className="space-y-3">
            {group.items.map((mark) => {
              const anchorQuote = mark.anchor_quote.trim();
              return (
                <div key={mark.mark_id} className="rounded-2xl bg-[var(--warm-50)] border border-[var(--warm-300)]/25 p-5">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                      {mark.section_ref}
                    </span>
                    <span className="text-[var(--warm-300)]">·</span>
                    <span className="text-[var(--warm-700)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                      {reactionLabel(mark.reaction_type)}
                    </span>
                    <span className="text-[var(--warm-300)]">·</span>
                    <span className="text-[var(--amber-accent)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                      {markLabel(mark.mark_type)}
                    </span>
                  </div>
                  {anchorQuote ? (
                    <blockquote
                      className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-3 text-[var(--warm-600)] italic"
                      style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}
                    >
                      “{anchorQuote}”
                    </blockquote>
                  ) : null}
                  <p className="text-[var(--warm-800)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                    {mark.reaction_excerpt}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function activityStream(event: ActivityEvent) {
  return event.stream ?? "system";
}

function activityKind(event: ActivityEvent) {
  return event.kind ?? "transition";
}

function activityVisibility(event: ActivityEvent) {
  return event.visibility ?? "default";
}

type MindstreamReaction = ActivityEvent["visible_reactions"][number];

type MindstreamMoment = {
  momentId: string;
  timestamp: string;
  chapterRef: string | null;
  sectionRef: string | null;
  anchorQuote: string;
  reactions: MindstreamReaction[];
  resultUrl: string | null;
};

type ContentLocale = "en" | "zh";
type MindstreamActionFamily = "discern" | "association" | "curious" | "retrospect" | "highlight";
type CurrentReadingActivitySnapshot = NonNullable<AnalysisStateResponse["current_reading_activity"]>;
type MindstreamProblemCode = NonNullable<CurrentReadingActivitySnapshot["problem_code"]>;
type CurrentMindstreamActivity = {
  message: string;
  context: string | null;
  contextKind: "excerpt" | "query" | "none";
  mode: "active" | "waiting" | "slow" | "degraded";
};

type MindstreamTrailPreview = {
  label: string;
  teaser: string | null;
};

type ReadingLocus = {
  chapterRef: string | null;
  sectionRef: string | null;
};

const LIVE_PHASE_SLOW_THRESHOLD_MS = 8_000;
const LIVE_HEARTBEAT_STALE_MS = 10_000;

function normalizeContentLocale(language?: string | null): ContentLocale {
  return String(language ?? "").trim().toLowerCase().startsWith("zh") ? "zh" : "en";
}

function contentCopy(
  key: ControlledCopyKey,
  locale: ContentLocale,
  params?: Record<string, string | number | null | undefined>,
) {
  return copyForLocale(key, locale as AppLocale, params);
}

function excerptText(value?: string | null, maxLength = 120) {
  const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "";
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

function timestampToMs(value?: string | null) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

const REACTION_PRIORITY: Record<string, number> = {
  discern: 0,
  association: 1,
  curious: 2,
  retrospect: 3,
  highlight: 4,
};

function reactionPriority(type?: string | null) {
  return REACTION_PRIORITY[String(type ?? "").toLowerCase()] ?? 99;
}

function buildMindstreamMoments(activity: ActivityEvent[]) {
  const rawEvents = activity.filter((event) => {
    if (activityStream(event) !== "mindstream" || activityVisibility(event) !== "default") {
      return false;
    }
    return activityKind(event) === "segment_complete" && (event.visible_reactions?.length ?? 0) > 0;
  });

  const grouped = new Map<string, MindstreamMoment>();
  const order: string[] = [];

  for (const event of rawEvents) {
    const anchorQuote = (event.anchor_quote ?? event.highlight_quote ?? "").trim();
    const groupingKey = anchorQuote
      ? `${event.chapter_id ?? "chapter"}:${event.section_ref ?? "section"}:${anchorQuote}`
      : event.event_id;
    const visibleReactions = event.visible_reactions ?? [];

    if (!grouped.has(groupingKey)) {
      grouped.set(groupingKey, {
        momentId: groupingKey,
        timestamp: event.timestamp,
        chapterRef: event.chapter_ref ?? null,
        sectionRef: event.section_ref ?? null,
        anchorQuote,
        reactions: [],
        resultUrl: event.result_url ?? null,
      });
      order.push(groupingKey);
    }

    const current = grouped.get(groupingKey);
    if (!current) {
      continue;
    }

    for (const reaction of visibleReactions) {
      if (current.reactions.some((item) => item.reaction_id === reaction.reaction_id)) {
        continue;
      }
      current.reactions.push(reaction);
    }
  }

  return order
    .map((key) => grouped.get(key))
    .filter((item): item is MindstreamMoment => Boolean(item))
    .map((moment) => {
      const reactions = [...moment.reactions].sort((left, right) => reactionPriority(left.type) - reactionPriority(right.type));
      return {
        ...moment,
        reactions,
      };
    });
}

function clampStyle(lines: number): CSSProperties {
  return {
    display: "-webkit-box",
    WebkitBoxOrient: "vertical",
    WebkitLineClamp: lines,
    overflow: "hidden",
  };
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setPrefersReducedMotion(media.matches);
    update();

    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", update);
      return () => media.removeEventListener("change", update);
    }

    media.addListener(update);
    return () => media.removeListener(update);
  }, []);

  return prefersReducedMotion;
}

function reactionActionFamily(reaction: MindstreamReaction): MindstreamActionFamily {
  const normalizedType = String(reaction.type ?? "").toLowerCase();
  if (normalizedType === "association") {
    return "association";
  }
  if (normalizedType === "curious") {
    return "curious";
  }
  if (normalizedType === "retrospect") {
    return "retrospect";
  }
  if (normalizedType === "highlight") {
    return "highlight";
  }
  return "discern";
}

function looksQuestioning(text: string) {
  return /[?\uFF1F]/.test(text)
    || /\b(why|how|what|does|is|are|should|could|would)\b/i.test(text)
    || /(\u4e3a\u4ec0\u4e48|\u5982\u4f55|\u662f\u5426|\u662f\u4e0d\u662f|\u96be\u9053|\u5417|\u4e48)/.test(text);
}

function looksEchoing(text: string) {
  return /\b(earlier|previous|before|again|echo|recalls|comes back|returns to)\b/i.test(text)
    || /(\u524d\u6587|\u524d\u9762|\u56de\u54cd|\u547c\u5e94|\u53c8\u4e00\u6b21|\u518d\u4e00\u6b21|\u56de\u5230\u524d\u9762)/.test(text);
}

const MINDSTREAM_TRACE_COPY_KEYS: Record<
  MindstreamActionFamily,
  { default: ControlledCopyKey; alternate?: ControlledCopyKey; search?: ControlledCopyKey }
> = {
  discern: {
    default: "overview.mindstream.trace.discern.default",
    alternate: "overview.mindstream.trace.discern.question",
  },
  association: {
    default: "overview.mindstream.trace.association.default",
    alternate: "overview.mindstream.trace.association.echo",
  },
  curious: {
    default: "overview.mindstream.trace.curious.default",
    search: "overview.mindstream.trace.curious.search",
  },
  retrospect: {
    default: "overview.mindstream.trace.retrospect.default",
    alternate: "overview.mindstream.trace.retrospect.echo",
  },
  highlight: {
    default: "overview.mindstream.trace.highlight.default",
  },
};

function traceCopyKeyForReaction(reaction: MindstreamReaction): ControlledCopyKey {
  const family = reactionActionFamily(reaction);
  const copyGroup = MINDSTREAM_TRACE_COPY_KEYS[family];
  const content = String(reaction.content ?? "");

  if (family === "curious" && reaction.search_query) {
    return copyGroup.search ?? copyGroup.default;
  }
  if (family === "discern" && looksQuestioning(content) && copyGroup.alternate) {
    return copyGroup.alternate;
  }
  if ((family === "association" || family === "retrospect") && looksEchoing(content) && copyGroup.alternate) {
    return copyGroup.alternate;
  }
  return copyGroup.default;
}

function reactionTracePhrase(reaction: MindstreamReaction, locale: ContentLocale) {
  return contentCopy(traceCopyKeyForReaction(reaction), locale);
}

function buildMindstreamTrailPreview(moment: MindstreamMoment, locale: ContentLocale): MindstreamTrailPreview | null {
  const leadReaction = moment.reactions[0];
  if (!leadReaction) {
    return null;
  }

  const teaserSource = String(leadReaction.content ?? "").trim() || String(moment.anchorQuote ?? "").trim();
  return {
    label: reactionTracePhrase(leadReaction, locale),
    teaser: teaserSource ? excerptText(teaserSource, 92) : null,
  };
}

const MINDSTREAM_LIVE_COPY_KEYS: Record<
  CurrentReadingActivitySnapshot["phase"],
  {
    default: ControlledCopyKey;
    alternate?: ControlledCopyKey;
    still?: ControlledCopyKey;
    families?: Partial<Record<MindstreamActionFamily, ControlledCopyKey>>;
  }
> = {
  reading: {
    default: "overview.mindstream.live.reading.default",
    alternate: "overview.mindstream.live.reading.alternate",
    still: "overview.mindstream.live.reading.still",
  },
  thinking: {
    default: "overview.mindstream.live.thinking.default",
    still: "overview.mindstream.live.thinking.still",
    families: {
      discern: "overview.mindstream.live.thinking.discern",
      association: "overview.mindstream.live.thinking.association",
      curious: "overview.mindstream.live.thinking.curious",
      retrospect: "overview.mindstream.live.thinking.retrospect",
      highlight: "overview.mindstream.live.thinking.highlight",
    },
  },
  searching: {
    default: "overview.mindstream.live.searching.default",
    still: "overview.mindstream.live.searching.still",
    families: {
      curious: "overview.mindstream.live.searching.curious",
    },
  },
  fusing: {
    default: "overview.mindstream.live.fusing.default",
    alternate: "overview.mindstream.live.fusing.alternate",
    still: "overview.mindstream.live.fusing.still",
  },
  reflecting: {
    default: "overview.mindstream.live.reflecting.default",
    alternate: "overview.mindstream.live.reflecting.alternate",
    still: "overview.mindstream.live.reflecting.still",
  },
  waiting: {
    default: "overview.mindstream.live.waiting.default",
  },
  preparing: {
    default: "overview.mindstream.live.preparing.default",
  },
};

const MINDSTREAM_LIVE_PROBLEM_COPY_KEYS: Record<MindstreamProblemCode, ControlledCopyKey> = {
  llm_timeout: "overview.mindstream.live.problem.llm_timeout",
  llm_quota: "overview.mindstream.live.problem.llm_quota",
  llm_auth: "overview.mindstream.live.problem.llm_auth",
  search_timeout: "overview.mindstream.live.problem.search_timeout",
  search_quota: "overview.mindstream.live.problem.search_quota",
  search_auth: "overview.mindstream.live.problem.search_auth",
  network_blocked: "overview.mindstream.live.problem.network_blocked",
};

function isWaitingOrPreparingPulse(value: string) {
  return /^waiting\b/i.test(value)
    || /^preparing\b/i.test(value)
    || /^readying\b/i.test(value)
    || /^(\u7b49\u5f85|\u6b63\u5728\u51c6\u5907|\u51c6\u5907)/.test(value);
}

function normalizeThoughtFamily(value?: string | null): MindstreamActionFamily | null {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (
    normalized === "discern" ||
    normalized === "association" ||
    normalized === "curious" ||
    normalized === "retrospect" ||
    normalized === "highlight"
  ) {
    return normalized;
  }
  return null;
}

function looksLikeLocationToken(value: string, segmentRef?: string | null) {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return false;
  }
  if (segmentRef && normalized === segmentRef.trim()) {
    return true;
  }
  return /^[A-Za-z0-9][A-Za-z0-9_\-]*(?:\.[A-Za-z0-9_\-]+)*$/.test(normalized);
}

function liveCopyKeyForActivity(activity: CurrentReadingActivitySnapshot): ControlledCopyKey {
  const copyGroup = MINDSTREAM_LIVE_COPY_KEYS[activity.phase];
  const family = normalizeThoughtFamily(activity.thought_family);

  if (family && copyGroup.families?.[family]) {
    return copyGroup.families[family]!;
  }

  if (activity.phase === "reading" && activity.current_excerpt) {
    return copyGroup.alternate ?? copyGroup.default;
  }
  if (activity.phase === "fusing" && (activity.search_query || activity.current_excerpt)) {
    return copyGroup.alternate ?? copyGroup.default;
  }
  if (activity.phase === "reflecting" && activity.current_excerpt) {
    return copyGroup.alternate ?? copyGroup.default;
  }

  return copyGroup.default;
}

function stillLiveCopyKeyForActivity(activity: CurrentReadingActivitySnapshot): ControlledCopyKey {
  const copyGroup = MINDSTREAM_LIVE_COPY_KEYS[activity.phase];
  return copyGroup.still ?? copyGroup.alternate ?? copyGroup.default;
}

function liveProblemCopyKey(problemCode?: string | null): ControlledCopyKey {
  const normalized = String(problemCode ?? "").trim().toLowerCase() as MindstreamProblemCode;
  return MINDSTREAM_LIVE_PROBLEM_COPY_KEYS[normalized] ?? "overview.mindstream.live.problem.default";
}

function buildCurrentMindstreamContext(
  activity: CurrentReadingActivitySnapshot,
): Pick<CurrentMindstreamActivity, "context" | "contextKind"> {
  const excerpt = String(activity.current_excerpt ?? "").trim();
  const query = String(activity.search_query ?? "").trim();
  const segmentRef = String(activity.segment_ref ?? "").trim();

  if (query) {
    return {
      context: excerptText(query, 72),
      contextKind: "query",
    };
  }

  if (excerpt && !looksLikeLocationToken(excerpt, segmentRef)) {
    return {
      context: excerptText(excerpt, 180),
      contextKind: "excerpt",
    };
  }

  return {
    context: null,
    contextKind: "none",
  };
}

function buildCurrentMindstreamActivity(
  analysis: AnalysisStateResponse | null,
  locale: ContentLocale,
  nowMs: number,
): CurrentMindstreamActivity | null {
  if (!analysis) {
    return null;
  }

  const liveActivity = analysis.current_reading_activity ?? analysis.current_state_panel.current_reading_activity ?? null;
  if (liveActivity) {
    const startedAtMs = timestampToMs(liveActivity.started_at) ?? timestampToMs(liveActivity.updated_at) ?? nowMs;
    const updatedAtMs = timestampToMs(liveActivity.updated_at) ?? startedAtMs;
    const phaseDurationMs = Math.max(0, nowMs - startedAtMs);
    const heartbeatAgeMs = Math.max(0, nowMs - updatedAtMs);
    const context = buildCurrentMindstreamContext(liveActivity);

    if (heartbeatAgeMs > LIVE_HEARTBEAT_STALE_MS) {
      return {
        message: contentCopy(liveProblemCopyKey(liveActivity.problem_code), locale),
        context: context.context,
        contextKind: context.contextKind,
        mode: "degraded",
      };
    }

    const isWaiting = liveActivity.phase === "waiting" || liveActivity.phase === "preparing";
    const isSlow = !isWaiting && phaseDurationMs >= LIVE_PHASE_SLOW_THRESHOLD_MS;

    return {
      message: contentCopy(isSlow ? stillLiveCopyKeyForActivity(liveActivity) : liveCopyKeyForActivity(liveActivity), locale),
      context: context.context,
      contextKind: context.contextKind,
      mode: isWaiting ? "waiting" : (isSlow ? "slow" : "active"),
    };
  }

  const fallbackPulse = analysis.pulse_message?.trim() ?? analysis.current_state_panel.pulse_message?.trim() ?? "";
  if (fallbackPulse && isWaitingOrPreparingPulse(fallbackPulse)) {
    return {
      message: fallbackPulse,
      context: null,
      contextKind: "none",
      mode: "waiting",
    };
  }

  if (analysis.status === "deep_reading") {
    return {
      message: contentCopy("overview.mindstream.live.reading.default", locale),
      context: null,
      contextKind: "none",
      mode: "degraded",
    };
  }

  return null;
}

function buildReadingLocus(analysis: AnalysisStateResponse | null): ReadingLocus {
  const chapterRef = String(
    analysis?.current_state_panel.current_chapter_ref
      ?? analysis?.current_chapter_ref
      ?? "",
  ).trim();
  const sectionRef = String(
    analysis?.current_state_panel.current_section_ref
      ?? analysis?.current_reading_activity?.segment_ref
      ?? analysis?.current_state_panel.current_reading_activity?.segment_ref
      ?? "",
  ).trim();

  return {
    chapterRef: chapterRef || null,
    sectionRef: sectionRef || null,
  };
}

function ActivityMeta({
  event,
  compact = false,
}: {
  event: ActivityEvent;
  compact?: boolean;
}) {
  return (
    <div className="mt-2 flex items-center gap-2 flex-wrap text-[var(--warm-500)]" style={{ fontSize: compact ? "0.6875rem" : "0.75rem" }}>
      <span>{formatTimestamp(event.timestamp)}</span>
      {event.chapter_ref ? <span>{event.chapter_ref}</span> : null}
      {event.section_ref ? <span>{event.section_ref}</span> : null}
    </div>
  );
}

function formatMindstreamSectionToken(sectionRef?: string | null, chapterRef?: string | null) {
  const normalizedSection = String(sectionRef ?? "").trim();
  if (!normalizedSection) {
    return null;
  }
  if (normalizedSection.startsWith("§")) {
    return normalizedSection;
  }

  const normalizedChapter = String(chapterRef ?? "").trim();
  if (normalizedChapter && normalizedSection.startsWith(`${normalizedChapter}.`)) {
    const suffix = normalizedSection.slice(normalizedChapter.length + 1).trim();
    return suffix ? `§${suffix}` : normalizedSection;
  }

  const prefixedMatch = normalizedSection.match(/^[A-Za-z][A-Za-z0-9_\-\s]*\.(.+)$/);
  if (prefixedMatch?.[1]?.trim()) {
    return `§${prefixedMatch[1].trim()}`;
  }

  return normalizedSection;
}

function buildMindstreamBreadcrumbTail(activity: CurrentMindstreamActivity | null) {
  if (!activity?.context) {
    return null;
  }
  return excerptText(activity.context, 56) || null;
}

function formatMindstreamQuote(activity: CurrentMindstreamActivity) {
  if (!activity.context) {
    return null;
  }
  return activity.contextKind === "excerpt" ? `“${activity.context}”` : activity.context;
}

function MindstreamHeroBreadcrumb({
  analysis,
  currentActivity,
}: {
  analysis: AnalysisStateResponse | null;
  currentActivity: CurrentMindstreamActivity | null;
}) {
  const locus = buildReadingLocus(analysis);
  const sectionToken = formatMindstreamSectionToken(locus.sectionRef, locus.chapterRef);
  const tail = buildMindstreamBreadcrumbTail(currentActivity);

  if (!locus.chapterRef && !sectionToken && !tail) {
    return null;
  }

  return (
    <div className="min-w-0 md:ml-auto">
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5 md:justify-end">
        <MapPin className="h-[1rem] w-[1rem] shrink-0 text-[var(--warm-300)]" strokeWidth={2.1} />
        {locus.chapterRef ? (
          <span className="text-[var(--warm-700)]" style={{ fontSize: "clamp(0.95rem, 1.05vw, 1rem)", fontWeight: 600 }}>
            {locus.chapterRef}
          </span>
        ) : null}
        {sectionToken ? (
          <>
            <span className="text-[var(--warm-300)]" style={{ fontSize: "clamp(0.875rem, 0.95vw, 0.9375rem)", fontWeight: 500 }}>
              ›
            </span>
            <span className="text-[var(--warm-400)]" style={{ fontSize: "clamp(0.875rem, 0.95vw, 0.9375rem)", fontWeight: 500 }}>
              {sectionToken}
            </span>
          </>
        ) : null}
        {tail ? (
          <>
            <span className="text-[var(--warm-300)]" style={{ fontSize: "clamp(0.875rem, 0.95vw, 0.9375rem)", fontWeight: 500 }}>
              ·
            </span>
            <span
              className="min-w-0 max-w-full text-[var(--warm-400)] md:max-w-[20rem] lg:max-w-[24rem]"
              style={{
                fontSize: "clamp(0.8125rem, 0.9vw, 0.9375rem)",
                fontWeight: 500,
                lineHeight: 1.35,
                ...clampStyle(1),
              }}
            >
              {tail}
            </span>
          </>
        ) : null}
      </div>
    </div>
  );
}

function MindstreamHeroStatusRow({
  runtimeState,
}: {
  runtimeState: RuntimeStateSummary;
}) {
  return (
    <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
      <span
        className="inline-flex w-fit items-center gap-3 rounded-full border border-[var(--warm-300)]/65 px-5 py-3 text-[var(--warm-800)]"
        style={{
          backgroundColor: "rgba(255, 251, 244, 0.9)",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.55)",
        }}
      >
        <span className="h-3 w-3 shrink-0 rounded-full bg-[var(--amber-accent)]" />
        <span style={{ fontSize: "clamp(0.9375rem, 1vw, 1rem)", fontWeight: 600, lineHeight: 1.2 }}>
          {runtimeState.label}
        </span>
      </span>
      <p
        className="text-[var(--warm-400)]"
        style={{
          fontSize: "clamp(0.9375rem, 1vw, 1rem)",
          fontWeight: 500,
          lineHeight: 1.35,
        }}
      >
        {runtimeState.detail}
      </p>
    </div>
  );
}

function MindstreamEventCard({
  moment,
  isCompact,
  contentLocale,
  prefersReducedMotion,
}: {
  moment: MindstreamMoment;
  isCompact: boolean;
  contentLocale: ContentLocale;
  prefersReducedMotion: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [entered, setEntered] = useState(false);
  const leadReaction = moment.reactions[0];
  if (!leadReaction) {
    return null;
  }
  const remainingReactions = moment.reactions.slice(1);
  const isHighlightOnly = moment.reactions.every((reaction) => reaction.type === "highlight");
  const teaserLines = 2;
  const traceLabel = reactionTracePhrase(leadReaction, contentLocale);
  const showExpandedReactions = !isCompact && remainingReactions.length > 0;

  useEffect(() => {
    if (prefersReducedMotion) {
      setEntered(true);
      return;
    }
    const frame = window.requestAnimationFrame(() => setEntered(true));
    return () => window.cancelAnimationFrame(frame);
  }, [prefersReducedMotion]);

  function ReactionTeaser({
    reaction,
    compact = false,
    showHeader = true,
  }: {
    reaction: MindstreamReaction;
    compact?: boolean;
    showHeader?: boolean;
  }) {
    return (
      <div className={compact ? "space-y-1.5" : "space-y-2"}>
        {showHeader ? (
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex rounded-full px-2 py-0.5 ${
                isHighlightOnly ? "bg-[var(--warm-100)] text-[var(--warm-600)]" : "bg-[var(--amber-bg)] text-[var(--warm-800)]"
              }`}
              style={{ fontSize: "0.625rem", fontWeight: 600 }}
            >
              {reactionLabel(reaction.type)}
            </span>
            {compact && moment.sectionRef ? (
              <span className="text-[var(--warm-500)]" style={{ fontSize: "0.6875rem" }}>
                {moment.sectionRef}
              </span>
            ) : null}
          </div>
        ) : null}
        <p
          className={isHighlightOnly ? "text-[var(--warm-700)]" : "text-[var(--warm-900)]"}
          style={{
            fontSize: compact ? "0.75rem" : "0.9375rem",
            lineHeight: compact ? 1.65 : 1.75,
            ...clampStyle(compact ? 2 : teaserLines),
          }}
        >
          {reaction.content}
        </p>
        {expanded && !compact && reaction.search_query ? (
          <div className="flex items-center gap-1.5 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
            <Search className="w-3 h-3" />
            <span className="truncate">{reaction.search_query}</span>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <article
      className="relative border-l border-[var(--warm-300)]/25 pl-5"
      style={
        prefersReducedMotion
          ? undefined
          : {
              opacity: entered ? 1 : 0,
              transform: entered ? "translateY(0)" : "translateY(5px)",
              transition: "opacity 220ms ease, transform 220ms ease",
            }
      }
    >
      <span
        className={`absolute -left-[4px] top-1.5 block h-2 w-2 rounded-full ${
          isHighlightOnly ? "bg-[var(--warm-200)]" : "bg-[var(--warm-300)]"
        }`}
      />

      <div className="min-w-0 max-w-[44rem]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={isHighlightOnly ? "text-[var(--warm-500)]" : "text-[var(--warm-700)]"}
                style={{ fontSize: isCompact ? "0.6875rem" : "0.75rem", fontWeight: 600, letterSpacing: "0.01em" }}
              >
                {traceLabel}
              </span>
              {moment.sectionRef ? (
                <span className="text-[var(--warm-400)]" style={{ fontSize: isCompact ? "0.625rem" : "0.6875rem", fontWeight: 500 }}>
                  {moment.sectionRef}
                </span>
              ) : null}
            </div>
          </div>
          {moment.resultUrl ? (
            <Link
              to={moment.resultUrl}
              aria-label={copy("overview.mindstream.openInChapterTooltip")}
              title={copy("overview.mindstream.openInChapterTooltip")}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--warm-500)] no-underline hover:bg-[var(--warm-100)] hover:text-[var(--warm-800)] transition-colors"
            >
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          ) : null}
        </div>

        <div className="mt-2 space-y-3">
          {moment.anchorQuote ? (
            <blockquote
              className="text-[var(--warm-500)] italic"
              style={{
                fontSize: isCompact ? "0.6875rem" : "0.75rem",
                lineHeight: 1.55,
                ...clampStyle(1),
              }}
            >
              “{moment.anchorQuote}”
            </blockquote>
          ) : null}

          <div>
            <ReactionTeaser reaction={leadReaction} compact={isCompact} showHeader={false} />
          </div>

          {showExpandedReactions ? (
            <div
              className="grid overflow-hidden"
              style={
                prefersReducedMotion
                  ? { gridTemplateRows: expanded ? "1fr" : "0fr" }
                  : {
                      gridTemplateRows: expanded ? "1fr" : "0fr",
                      transition: "grid-template-rows 200ms ease, opacity 200ms ease",
                      opacity: expanded ? 1 : 0.72,
                    }
              }
            >
              <div className="min-h-0 overflow-hidden">
                <div className="space-y-3 border-l border-[var(--warm-300)]/25 pl-4 pt-1">
                  {remainingReactions.map((reaction) => (
                    <ReactionTeaser key={reaction.reaction_id} reaction={reaction} compact />
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex items-center gap-2 flex-wrap text-[var(--warm-500)]" style={{ fontSize: "0.6875rem" }}>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 ${
                isHighlightOnly ? "bg-[var(--warm-100)] text-[var(--warm-500)]" : "bg-[var(--warm-100)]/70 text-[var(--warm-600)]"
              }`}
              style={{ fontWeight: 600 }}
            >
              {reactionLabel(leadReaction.type)}
            </span>
            {moment.chapterRef ? <span>{moment.chapterRef}</span> : null}
            <span>{formatTimestamp(moment.timestamp)}</span>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            {showExpandedReactions ? (
              <button
                type="button"
                onClick={() => setExpanded((value) => !value)}
                className="inline-flex items-center gap-1 text-[var(--amber-accent)] hover:text-[var(--warm-700)] transition-colors cursor-pointer"
                style={{ fontSize: "0.8125rem", fontWeight: 600 }}
              >
                {expanded
                  ? copy("overview.mindstream.hideExtraThoughts")
                  : copy("overview.mindstream.moreThoughts", { count: remainingReactions.length })}
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}

function MindstreamHistoryDisclosure({
  analysis,
  activity,
  contentLanguage,
  loading,
  error,
  onRetry,
}: {
  analysis: AnalysisStateResponse | null;
  activity: ActivityEvent[];
  contentLanguage: ContentLocale;
  loading: boolean;
  error: unknown | null;
  onRetry: () => void;
}) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const [expanded, setExpanded] = useState(false);
  const historyMoments = buildMindstreamMoments(activity).slice(0, 3);
  const trailPreview = historyMoments.length > 0 ? buildMindstreamTrailPreview(historyMoments[0], contentLanguage) : null;

  if (loading && !analysis) {
    return (
      <section className="rounded-2xl border border-[var(--warm-300)]/25 bg-[var(--warm-50)] px-5 py-4">
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem" }}>
          {copy("overview.runtime.syncing")}
        </p>
      </section>
    );
  }

  if (error || !analysis) {
    const errorState = getErrorPresentation(error, {
      title: copy("state.error.backendUnavailable.title"),
      message: copy("overview.syncError.default"),
    });
    return (
      <section className="rounded-2xl border border-[var(--warm-300)]/25 bg-[var(--warm-50)] px-5 py-4">
        <p className="text-[var(--destructive)] mb-3" style={{ fontSize: "0.875rem" }}>
          {errorState.message}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          {copy("overview.runtime.retry")}
        </button>
      </section>
    );
  }

  return (
    <section className="mt-5 border-t border-[var(--warm-300)]/14 pt-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-start md:gap-5">
        <div className="min-w-0 max-w-[54rem] flex-1">
          <p className="text-[var(--warm-500)] uppercase tracking-[0.18em]" style={{ fontSize: "0.625rem", fontWeight: 600 }}>
            {copy("overview.mindstream.recentTrail")}
          </p>
          {trailPreview ? (
            <div className="mt-1 min-w-0">
              <p className="text-[var(--warm-600)]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                {trailPreview.label}
              </p>
              {trailPreview.teaser ? (
                <p className="mt-0.5 text-[var(--warm-500)]" style={{ fontSize: "0.6875rem", lineHeight: 1.5, ...clampStyle(1) }}>
                  {trailPreview.teaser}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-0.5 text-[var(--warm-500)]" style={{ fontSize: "0.6875rem" }}>
              {copy("overview.mindstream.trailEmpty")}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="inline-flex shrink-0 items-center gap-2 self-start text-[var(--warm-500)] transition-colors hover:text-[var(--warm-700)] cursor-pointer md:mt-5"
          style={{ fontSize: "0.75rem", fontWeight: 600 }}
        >
          {expanded ? copy("overview.mindstream.hideRecentTrail") : copy("overview.mindstream.showRecentTrail")}
        </button>
      </div>

      {expanded ? (
        historyMoments.length > 0 ? (
          <div className="mt-4 max-h-[16rem] overflow-y-auto overscroll-contain pr-2">
            <div className="space-y-4">
              {historyMoments.map((moment) => (
                <MindstreamEventCard
                  key={moment.momentId}
                  moment={moment}
                  isCompact
                  contentLocale={contentLanguage}
                  prefersReducedMotion={prefersReducedMotion}
                />
              ))}
            </div>
          </div>
        ) : (
          <p className="mt-4 text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            {copy("overview.mindstream.trailEmpty")}
          </p>
        )
      ) : null}
    </section>
  );
}

function MindstreamHeroCard({
  detail,
  analysis,
  activity,
  contentLanguage,
  loading,
  error,
  onRetry,
}: {
  detail: BookDetailResponse;
  analysis: AnalysisStateResponse | null;
  activity: ActivityEvent[];
  contentLanguage: ContentLocale;
  loading: boolean;
  error: unknown | null;
  onRetry: () => void;
}) {
  const [liveNowMs, setLiveNowMs] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => {
      setLiveNowMs(Date.now());
    }, 1_000);
    return () => window.clearInterval(interval);
  }, []);

  if (loading && !analysis) {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm mb-8">
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem" }}>
          {copy("overview.runtime.syncing")}
        </p>
      </section>
    );
  }

  if (error || !analysis) {
    const errorState = getErrorPresentation(error, {
      title: copy("state.error.backendUnavailable.title"),
      message: copy("overview.syncError.default"),
    });
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm mb-8">
        <p className="text-[var(--destructive)] mb-3" style={{ fontSize: "0.875rem" }}>
          {errorState.message}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          {copy("overview.runtime.retry")}
        </button>
      </section>
    );
  }

  const currentActivity = buildCurrentMindstreamActivity(analysis, contentLanguage, liveNowMs);
  const runtimeState = describeRuntimeState(detail, analysis, { isParsing: isAnalysisParsing(analysis) });
  const quoteText = currentActivity ? formatMindstreamQuote(currentActivity) : null;

  return (
    <section className="mb-8 rounded-3xl border border-[var(--warm-300)]/30 bg-white px-6 py-6 shadow-sm md:px-10 md:py-9">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between md:gap-8">
        <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {copy("overview.mindstream.title")}
        </p>
        <MindstreamHeroBreadcrumb analysis={analysis} currentActivity={currentActivity} />
      </div>

      <div className="mt-7 flex items-start gap-4 md:mt-9 md:gap-6">
        {currentActivity ? (
          <span
            className="mt-3.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--amber-accent)] md:mt-4 md:h-3 md:w-3"
            aria-hidden="true"
          />
        ) : null}

        <div className="min-w-0 flex-1">
          {currentActivity ? (
            <h2
              className="text-[var(--warm-900)]"
              style={{
                fontFamily: "Lora, Georgia, serif",
                fontSize: "clamp(1.75rem, 2.2vw, 2.25rem)",
                fontWeight: 600,
                lineHeight: 1.08,
                letterSpacing: "-0.02em",
              }}
            >
              {currentActivity.message}
            </h2>
          ) : (
            <p
              className="max-w-[44rem] text-[var(--warm-500)]"
              style={{
                fontFamily: "Lora, Georgia, serif",
                fontSize: "clamp(1.25rem, 1.8vw, 1.625rem)",
                lineHeight: 1.4,
              }}
            >
              {copy("overview.mindstream.empty")}
            </p>
          )}

          {quoteText ? (
            <blockquote
              className="mt-8 border-l-[4px] border-[var(--warm-200)]/95 pl-5 text-[var(--warm-700)] md:pl-10"
              style={{
                fontSize: "clamp(1.125rem, 1.4vw, 1.375rem)",
                fontWeight: 400,
                lineHeight: 1.55,
              }}
            >
              <p className="line-clamp-4 md:line-clamp-3">
                {quoteText}
              </p>
            </blockquote>
          ) : null}

          <MindstreamHeroStatusRow runtimeState={runtimeState} />

          {loading || error ? (
            <div className="mt-4 flex items-center gap-3 flex-wrap text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
              {loading ? (
                <span className="inline-flex items-center gap-1.5">
                  <LoaderCircle className="w-3.5 h-3.5 animate-spin text-[var(--amber-accent)]" />
                  {copy("overview.runtime.syncing")}
                </span>
              ) : null}
              {error ? (
                <span className="text-[var(--destructive)]">{getErrorMessage(error)}</span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <MindstreamHistoryDisclosure
        analysis={analysis}
        activity={activity}
        contentLanguage={contentLanguage}
        loading={loading}
        error={error}
        onRetry={onRetry}
      />
    </section>
  );
}

function RuntimeSupportingRail({
  detail,
  analysis,
}: {
  detail: BookDetailResponse;
  analysis: AnalysisStateResponse | null;
}) {
  const currentStep = resolveCurrentStep(analysis);

  return (
    <div className="space-y-4 lg:sticky lg:top-28">
      <section className="rounded-3xl border border-[var(--warm-300)]/30 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--amber-accent)]" />
          <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
            {copy("overview.summary.title")}
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-3">
          <StatusMetric label={copy("overview.metric.completedChapters")} value={`${detail.completed_chapter_count}/${detail.chapter_count}`} compact />
          <StatusMetric label={copy("overview.metric.savedMarks")} value={detail.my_mark_count} compact />
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--warm-300)]/30 bg-white p-5 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Activity className="h-4 w-4 text-[var(--amber-accent)]" />
          <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
            {copy("overview.section.runConsole")}
          </h2>
        </div>
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
          {currentStep}
        </p>
      </section>
    </div>
  );
}

export function BookOverviewPage() {
  const { id = "", bookId = "" } = useParams();
  const resolvedBookId = id || bookId;
  const bookIdNumber = Number(resolvedBookId);
  const { tier } = useViewportResponsiveTier();
  const [activeTab, setActiveTab] = useState<"chapters" | "marks">("chapters");
  const [startPending, setStartPending] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [resumePending, setResumePending] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const { data, loading, error, reload } = useApiResource(
    async () => ({
      detail: await fetchBookDetail(bookIdNumber),
      marks: await fetchBookMarks(bookIdNumber),
    }),
    [bookIdNumber],
  );
  const analysisEnabled = data?.detail.status === "analyzing" || data?.detail.status === "paused";
  const analysisResource = useBookAnalysisResource(bookIdNumber, analysisEnabled);

  async function handleStartAnalysis() {
    setStartPending(true);
    setStartError(null);
    try {
      await startBookAnalysis(bookIdNumber);
      reload();
      analysisResource.refresh();
    } catch (reason) {
      setStartError(reason instanceof Error ? reason.message : copy("overview.error.start"));
    } finally {
      setStartPending(false);
    }
  }

  async function handleResumeAnalysis() {
    setResumePending(true);
    setResumeError(null);
    try {
      await resumeBookAnalysis(bookIdNumber);
      reload();
      analysisResource.refresh();
    } catch (reason) {
      setResumeError(reason instanceof Error ? reason.message : copy("overview.error.resume"));
    } finally {
      setResumePending(false);
    }
  }

  if (loading) {
    return <LoadingState title={copy("overview.loading")} />;
  }

  if (error || !data) {
    const errorState = getErrorPresentation(error, {
      title: copy("overview.error.title"),
      message: copy("overview.error.message"),
    });
    return (
      <ErrorState
        title={errorState.title}
        message={errorState.message}
        onRetry={reload}
        linkLabel={copy("page.books.title")}
        linkTo="/books"
      />
    );
  }

  const { detail, marks } = data;
  const contentLanguage = normalizeContentLocale(detail.output_language || detail.book_language);
  const isRuntimeState = detail.status === "analyzing" || detail.status === "paused";
  const viewMode: StructureViewMode =
    detail.status === "completed" ? "result" : isRuntimeState || detail.status === "error" ? "progress" : "outline";
  const structureChapters = buildOverviewChapters(detail, analysisResource.analysis);
  const isCompactStructureTier = tier === "mobile";
  const structureEmptyTitle = detail.status === "not_started"
    ? copy("overview.structure.emptyNotReady")
    : copy("overview.structure.emptyProgress");
  const structureEmptyMessage =
    detail.status === "not_started"
      ? copy("overview.structure.emptyNotReadyMessage")
      : copy("overview.structure.emptyProgressMessage");
  return (
    <div className="mx-auto max-w-6xl px-5 py-8 md:px-6 md:py-10">
      <BookOverviewHeader
        title={detail.title}
        author={detail.author}
        coverImageUrl={detail.cover_image_url}
        markCount={detail.my_mark_count}
      >
        <div className="flex flex-wrap items-center gap-3">
          {detail.status === "not_started" ? (
            <button
              type="button"
              onClick={handleStartAnalysis}
              disabled={startPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors disabled:opacity-60 cursor-pointer"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              {startPending ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              {copy("overview.cta.start")}
            </button>
          ) : null}
          {detail.status === "paused" ? (
            <button
              type="button"
              onClick={handleResumeAnalysis}
              disabled={resumePending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors disabled:opacity-60 cursor-pointer"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <LoaderCircle className={`w-4 h-4 ${resumePending ? "animate-spin" : ""}`} />
              {copy("overview.cta.resume")}
            </button>
          ) : null}
          {detail.status === "analyzing" ? (
            <span
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-bg)] text-[var(--warm-800)]"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <LoaderCircle className="w-4 h-4 text-[var(--amber-accent)] animate-spin" />
              {copy("overview.cta.running")}
            </span>
          ) : null}
          <a
            href={toApiAssetUrl(detail.source_asset.url) ?? "#"}
            data-testid="book-overview-source-download"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            <Download className="w-4 h-4" />
            {copy("overview.cta.downloadSource")}
          </a>
          {startError ? (
            <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {startError}
            </p>
          ) : null}
          {resumeError ? (
            <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {resumeError}
            </p>
          ) : null}
        </div>
      </BookOverviewHeader>

      <BookOverviewStatusBand
        detail={detail}
        analysis={analysisResource.analysis}
        activity={analysisResource.activity}
        contentLanguage={contentLanguage}
        analysisLoading={analysisResource.loading}
        analysisError={analysisResource.error}
        onRetryAnalysis={analysisResource.refresh}
      />

      <section className="mb-5 md:mb-6">
        <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {copy("overview.section.explore")}
        </p>
        <div className="flex items-center gap-2 bg-[var(--warm-200)]/50 rounded-xl p-1 w-fit">
          <button
            type="button"
            onClick={() => setActiveTab("chapters")}
            className={`px-4 py-2 rounded-lg cursor-pointer transition-colors ${
              activeTab === "chapters" ? "bg-white shadow-sm text-[var(--warm-900)]" : "text-[var(--warm-600)]"
            }`}
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            {term("view.structure")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("marks")}
            className={`px-4 py-2 rounded-lg cursor-pointer transition-colors ${
              activeTab === "marks" ? "bg-white shadow-sm text-[var(--warm-900)]" : "text-[var(--warm-600)]"
            }`}
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            {term("view.myMarks")}
          </button>
        </div>
      </section>

      {activeTab === "chapters" ? (
        isRuntimeState ? (
          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <ProcessingStructureNavigator
              bookId={detail.book_id}
              chapters={structureChapters}
              analysis={analysisResource.analysis}
              viewMode={viewMode}
              isParsing={isAnalysisParsing(analysisResource.analysis)}
              isPaused={detail.status === "paused"}
              isCollapsedByDefault={isCompactStructureTier}
              emptyTitle={structureEmptyTitle}
              emptyMessage={structureEmptyMessage}
            />

            <RuntimeSupportingRail
              detail={detail}
              analysis={analysisResource.analysis}
            />
          </div>
        ) : detail.status === "completed" ? (
          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  {term("view.structure")}
                </h2>
              </div>
              {structureChapters.length === 0 ? (
                <EmptyState title={structureEmptyTitle} message={structureEmptyMessage} />
              ) : (
                <StructureChapterList bookId={detail.book_id} chapters={structureChapters} viewMode={viewMode} />
              )}
            </section>

            <CompletedBookSupportingRail
              detail={detail}
              onOpenMarks={() => setActiveTab("marks")}
            />
          </div>
        ) : (
          <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                {term("view.structure")}
              </h2>
            </div>
            {structureChapters.length === 0 ? (
              <EmptyState title={structureEmptyTitle} message={structureEmptyMessage} />
            ) : (
              <StructureChapterList bookId={detail.book_id} chapters={structureChapters} viewMode={viewMode} />
            )}
          </section>
        )
      ) : (
        <BookMarksPanel bookId={detail.book_id} marks={marks} />
      )}
    </div>
  );
}
