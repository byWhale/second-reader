import {
  Activity,
  ArrowRight,
  BookOpen,
  Bookmark,
  Clock3,
  Download,
  FileText,
  Globe2,
  LoaderCircle,
  Sparkles,
  TreePine,
} from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  type ActivityEvent,
  type AnalysisLogResponse,
  type AnalysisStateResponse,
  type BookDetailResponse,
  type BookMarksResponse,
  fetchBookDetail,
  fetchBookMarks,
  resumeBookAnalysis,
  startBookAnalysis,
  toApiAssetUrl,
} from "../lib/api";
import { canonicalChapterPath } from "../lib/contract";
import { useBookAnalysisResource } from "../lib/use-book-analysis-resource";
import { useApiResource } from "../lib/use-api-resource";
import { copy, maybeCopy } from "../config/controlled-copy";
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

function formatEta(seconds?: number | null) {
  if (seconds == null) {
    return copy("overview.metric.etaUnavailable");
  }
  if (seconds < 60) {
    return copy("overview.metric.etaSecondsRemaining", { seconds });
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return remainingSeconds > 0
      ? copy("overview.metric.etaMinutesSecondsRemaining", { minutes, seconds: remainingSeconds })
      : copy("overview.metric.etaMinutesRemaining", { minutes });
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0
    ? copy("overview.metric.etaHoursMinutesRemaining", { hours, minutes: remainingMinutes })
    : copy("overview.metric.etaHoursRemaining", { hours });
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

function resolveStageLabel(detail: BookDetailResponse, analysis: AnalysisStateResponse | null) {
  return (
    resolveStructuredCopy(analysis?.stage_label_key, analysis?.stage_label_params, analysis?.stage_label) ??
    (detail.status === "paused" ? term("state.paused") : copy("overview.runtime.syncing"))
  );
}

function resolveCurrentStep(analysis: AnalysisStateResponse | null) {
  return (
    resolveStructuredCopy(
      analysis?.current_state_panel.current_phase_step_key ?? analysis?.current_phase_step_key,
      analysis?.current_state_panel.current_phase_step_params ?? analysis?.current_phase_step_params,
      analysis?.current_state_panel.current_phase_step ?? analysis?.current_phase_step,
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
  const raw = analysis?.current_state_panel.current_phase_step ?? analysis?.current_phase_step ?? "";
  return /(waiting)/i.test(raw.trim());
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
  const stepLabel = analysis.current_state_panel.current_phase_step ?? analysis.current_phase_step ?? "";
  return analysis.status === "parsing_structure" || /(segment|structure)/i.test(stepLabel);
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
      panel.current_phase_step ?? analysis.current_phase_step,
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
  bookLanguage,
  outputLanguage,
  chapterCount,
  markCount,
  children,
}: {
  title: string;
  author: string;
  coverImageUrl?: string | null;
  bookLanguage: string;
  outputLanguage: string;
  chapterCount: number;
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
            <Globe2 className="w-4 h-4" />
            {bookLanguage} → {outputLanguage}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Sparkles className="w-4 h-4" />
            {chapterCount} chapters
          </span>
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
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-3.5 md:p-4">
      <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
        {label}
      </p>
      <p className="text-[var(--warm-900)]" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
        {value}
      </p>
    </div>
  );
}

function BookOverviewStatusBand({
  detail,
  analysis,
  analysisLoading,
  analysisError,
  onRetryAnalysis,
}: {
  detail: BookDetailResponse;
  analysis: AnalysisStateResponse | null;
  analysisLoading: boolean;
  analysisError: string | null;
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
    return (
      <section className="mb-8 max-w-xl rounded-3xl border border-[var(--warm-300)]/30 bg-white p-6 shadow-sm">
        <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-4" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {copy("overview.section.completed")}
        </p>
        <div className="grid grid-cols-1 gap-4 md:max-w-sm">
          <StatusMetric label={copy("overview.metric.completedChapters")} value={`${detail.completed_chapter_count}/${detail.chapter_count}`} />
        </div>
      </section>
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

  const progressPercent =
    analysis?.progress_percent ??
    (detail.chapter_count > 0 ? Math.round((detail.completed_chapter_count / detail.chapter_count) * 10000) / 100 : 0);
  const parsing = isAnalysisParsing(analysis);
  const stepLabel = resolveCurrentStep(analysis);
  const currentFocus = parsing
    ? stepLabel
    : analysis?.current_state_panel.current_section_ref ?? stepLabel;
  const currentChapter = analysis?.current_state_panel.current_chapter_ref ?? copy("overview.runtime.waitingForStructure");
  const runtimeState = describeRuntimeState(detail, analysis, { isParsing: parsing });
  const reactionEntries = Object.entries(analysis?.current_state_panel.reaction_counts ?? {}).filter(([, count]) => count > 0);
  const reactionTotal = reactionEntries.reduce((sum, [, count]) => sum + count, 0);
  const checkpointLabel = formatTimestamp(analysis?.last_checkpoint_at);

  return (
    <section className="mb-6 rounded-3xl border border-[var(--warm-300)]/30 bg-white p-5 shadow-sm md:mb-8 md:p-6">
      <div className="flex items-start gap-4 flex-col">
        <div>
          <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
            {copy("overview.section.runConsole")}
          </p>
          <div className="flex items-center gap-4 flex-wrap text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
            <span className="inline-flex items-center gap-1.5">
              <LoaderCircle
                className={`w-4 h-4 ${detail.status === "paused" ? "" : "animate-spin text-[var(--amber-accent)]"}`}
              />
              {resolveStageLabel(detail, analysis)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock3 className="w-4 h-4" />
              {formatEta(analysis?.eta_seconds)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <BookOpen className="w-4 h-4" />
              {(analysis?.completed_chapters ?? detail.completed_chapter_count)}/{analysis?.total_chapters ?? detail.chapter_count} chapters
            </span>
          </div>
        </div>
      </div>

      <div className="mt-5 h-2 bg-[var(--warm-200)] rounded-full overflow-hidden">
        <div className="h-full bg-[var(--amber-accent)]" style={{ width: `${progressPercent}%` }} />
      </div>

      <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            {copy("overview.metric.currentChapter")}
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {currentChapter}
          </p>
        </div>
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            {parsing ? copy("overview.metric.currentStep") : copy("overview.metric.currentFocus")}
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {currentFocus}
          </p>
        </div>
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            {copy("overview.metric.runtimeState")}
          </p>
          <p className={runtimeState.toneClassName} style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {runtimeState.label}
          </p>
          <p className="text-[var(--warm-600)] mt-1" style={{ fontSize: "0.8125rem", lineHeight: 1.6 }}>
            {runtimeState.detail}
          </p>
        </div>
      </div>

      {reactionEntries.length > 0 && !parsing ? (
        <details className="mt-4 rounded-2xl border border-[var(--warm-300)]/20 bg-[var(--warm-50)] px-4 py-3">
          <summary
            className="cursor-pointer list-none text-[var(--warm-700)]"
            style={{ fontSize: "0.8125rem", fontWeight: 600 }}
          >
            {copy("overview.runtime.reactionsSummary", { count: reactionTotal })}
          </summary>
          <div className="mt-3 flex flex-wrap gap-2">
            {reactionEntries.map(([type, count]) => (
              <span
                key={type}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[var(--warm-300)]/20 px-3 py-1.5 text-[var(--warm-700)]"
                style={{ fontSize: "0.75rem", fontWeight: 500 }}
              >
                {reactionLabel(type)}
                <span className="text-[var(--warm-500)]">{count}</span>
              </span>
            ))}
          </div>
        </details>
      ) : null}

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        {checkpointLabel ? (
          <span className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            {copy("overview.runtime.lastCheckpoint", { value: checkpointLabel })}
          </span>
        ) : null}
        {analysisLoading && !analysis ? (
          <span className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            {copy("overview.runtime.syncing")}
          </span>
        ) : null}
        {analysisError ? (
          <>
            <span className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {analysisError}
            </span>
            <button
              type="button"
              onClick={onRetryAnalysis}
              className="text-[var(--amber-accent)] hover:text-[var(--warm-700)] cursor-pointer"
              style={{ fontSize: "0.8125rem", fontWeight: 500 }}
            >
              {copy("overview.runtime.retry")}
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
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
              <div className="flex items-center gap-2">
                <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
                <div>
                  <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                    {term("view.structure")}
                  </h2>
                  <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                    {copy("overview.structure.mobileHint")}
                  </p>
                </div>
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
        <div className="flex items-center gap-2">
          <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
          <div>
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              {term("view.structure")}
            </h2>
            <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
              {copy("overview.structure.desktopHint")}
            </p>
          </div>
        </div>
        <span className="text-[var(--warm-500)] whitespace-nowrap" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
          {chapters.length} chapters
        </span>
      </div>
      {content}
    </section>
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

function MindstreamEventCard({
  event,
}: {
  event: ActivityEvent;
}) {
  const kind = activityKind(event);

  if (kind === "chapter_complete") {
    return (
      <div className="rounded-2xl border border-[var(--amber-accent)]/25 bg-[var(--amber-bg)] px-4 py-4">
        <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
          {event.message}
        </p>
        <ActivityMeta event={event} />
        <div className="mt-3 flex items-center gap-3 flex-wrap text-[var(--warm-600)]" style={{ fontSize: "0.75rem" }}>
          {event.visible_reaction_count != null ? <span>{event.visible_reaction_count} reactions</span> : null}
        </div>
        {event.featured_reactions.length > 0 ? (
          <div className="mt-4 space-y-3">
            {event.featured_reactions.slice(0, 2).map((reaction) => (
              <div key={reaction.reaction_id} className="rounded-xl bg-white/90 border border-[var(--warm-300)]/20 px-3 py-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="inline-flex rounded-full bg-[var(--warm-100)] px-2.5 py-1 text-[var(--warm-700)]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                    {reactionLabel(reaction.type)}
                  </span>
                  <span className="text-[var(--warm-500)]" style={{ fontSize: "0.6875rem" }}>
                    {reaction.section_ref}
                  </span>
                </div>
                {reaction.anchor_quote ? (
                  <blockquote className="mt-2 text-[var(--warm-600)] italic" style={{ fontSize: "0.75rem", lineHeight: 1.7 }}>
                    “{excerptText(reaction.anchor_quote, 150)}”
                  </blockquote>
                ) : null}
                <p className="mt-2 text-[var(--warm-800)]" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                  {excerptText(reaction.content, 180)}
                </p>
              </div>
            ))}
          </div>
        ) : null}
        {event.result_url ? (
          <Link
            to={event.result_url}
            className="mt-4 inline-flex items-center gap-1 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
            style={{ fontSize: "0.8125rem", fontWeight: 600 }}
          >
            {copy("overview.structure.openCompletedChapter")}
            <ArrowRight className="w-3 h-3" />
          </Link>
        ) : null}
      </div>
    );
  }

  if (kind === "segment_complete") {
    return (
      <div className="border-l-2 border-[var(--amber-accent)]/35 pl-4">
        <p className="text-[var(--warm-900)]" style={{ fontSize: "0.875rem", fontWeight: 600, lineHeight: 1.6 }}>
          {event.message}
        </p>
        {event.reaction_types.length > 0 ? (
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            {event.reaction_types.map((type) => (
              <span
                key={type}
                className="inline-flex rounded-full bg-[var(--warm-100)] px-2.5 py-1 text-[var(--warm-700)]"
                style={{ fontSize: "0.6875rem", fontWeight: 600 }}
              >
                {reactionLabel(type)}
              </span>
            ))}
          </div>
        ) : null}
        {event.highlight_quote ? (
          <blockquote className="mt-2 text-[var(--warm-600)] italic" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
            “{event.highlight_quote}”
          </blockquote>
        ) : null}
        <ActivityMeta event={event} />
      </div>
    );
  }

  return (
    <div className={`border-l-2 pl-4 ${kind === "position" ? "border-[var(--warm-300)]" : "border-[var(--amber-accent)]/35"}`}>
      <p
        className={kind === "position" ? "text-[var(--warm-700)]" : "text-[var(--warm-900)]"}
        style={{ fontSize: kind === "position" ? "0.8125rem" : "0.875rem", fontWeight: kind === "position" ? 500 : 600, lineHeight: 1.6 }}
      >
        {event.message}
      </p>
      {kind === "search" && event.search_query ? (
        <div className="mt-2 inline-flex rounded-full bg-[var(--warm-100)] px-2.5 py-1 text-[var(--warm-700)]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {event.search_query}
        </div>
      ) : null}
      <ActivityMeta event={event} />
    </div>
  );
}

function ProgramLogEvent({
  event,
}: {
  event: ActivityEvent;
}) {
  return (
    <div className="rounded-xl border border-[var(--warm-300)]/20 bg-[var(--warm-50)] px-3 py-3">
      <p className="text-[var(--warm-800)]" style={{ fontSize: "0.8125rem", fontWeight: 500, lineHeight: 1.6 }}>
        {event.message}
      </p>
      <ActivityMeta event={event} compact />
    </div>
  );
}

function RuntimeFeedPanel({
  analysis,
  activity,
  log,
  loading,
  error,
  onRetry,
}: {
  analysis: AnalysisStateResponse | null;
  activity: ActivityEvent[];
  log: AnalysisLogResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading && !analysis) {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem" }}>
          {copy("overview.runtime.syncing")}
        </p>
      </section>
    );
  }

  if (error || !analysis) {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
        <p className="text-[var(--destructive)] mb-3" style={{ fontSize: "0.875rem" }}>
          {error ?? copy("overview.syncError.default")}
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

  const mindstreamEvents = activity.filter((event) => activityStream(event) === "mindstream");
  const mainMindstreamEvents = mindstreamEvents.filter((event) => activityVisibility(event) === "default");
  const collapsedMindstreamEvents = mindstreamEvents.filter((event) => activityVisibility(event) === "collapsed");
  const programEvents = activity.filter(
    (event) => activityStream(event) === "system" && activityVisibility(event) !== "hidden",
  );

  return (
    <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-5 shadow-sm md:p-6">
      <div className="flex items-start justify-between gap-4 flex-col md:flex-row">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-[var(--amber-accent)]" />
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              {copy("overview.mindstream.title")}
            </h2>
          </div>
          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
            {copy("overview.mindstream.description")}
          </p>
        </div>
        <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
          {copy("overview.mindstream.visibleMoments", { count: mainMindstreamEvents.length })}
        </span>
      </div>

      <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-[var(--amber-accent)]" />
          <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
            {copy("overview.mindstream.liveTrail")}
          </h3>
        </div>
        {mainMindstreamEvents.length === 0 ? (
          <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            {copy("overview.mindstream.empty")}
          </p>
        ) : (
          <div className="max-h-[18rem] overflow-y-auto overscroll-contain pr-2 md:max-h-[26rem]">
            <div className="space-y-4">
              {mainMindstreamEvents.map((event) => (
                <MindstreamEventCard key={event.event_id} event={event} />
              ))}
            </div>
          </div>
        )}
      </div>

      {collapsedMindstreamEvents.length > 0 ? (
        <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
          <details className="group">
            <summary
            className="cursor-pointer text-[var(--warm-700)] hover:text-[var(--warm-900)]"
            style={{ fontSize: "0.875rem", fontWeight: 600 }}
          >
            {copy("overview.mindstream.quietTransitions", { count: collapsedMindstreamEvents.length })}
          </summary>
            <div className="mt-4 space-y-3">
              {collapsedMindstreamEvents.map((event) => (
                <MindstreamEventCard key={event.event_id} event={event} />
              ))}
            </div>
          </details>
        </div>
      ) : null}

      <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
        <details className="group">
          <summary
            className="cursor-pointer text-[var(--warm-800)] hover:text-[var(--warm-900)]"
            style={{ fontSize: "0.9375rem", fontWeight: 600 }}
          >
            {copy("overview.programLog.title", { count: programEvents.length })}
          </summary>
          <p className="mt-3 text-[var(--warm-500)]" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
            {copy("overview.programLog.description")}
          </p>
          {programEvents.length === 0 ? (
            <p className="mt-4 text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
              {copy("overview.programLog.empty")}
            </p>
          ) : (
            <div className="mt-4 max-h-56 overflow-y-auto overscroll-contain pr-2">
              <div className="space-y-3">
                {programEvents.map((event) => (
                  <ProgramLogEvent key={event.event_id} event={event} />
                ))}
              </div>
            </div>
          )}
        </details>
      </div>

      <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-[var(--amber-accent)]" />
          <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
            {copy("overview.technicalLog.title")}
          </h3>
        </div>
        <details className="group">
          <summary
            className="cursor-pointer text-[var(--amber-accent)] hover:text-[var(--warm-700)]"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            {copy("overview.technicalLog.show")}
          </summary>
          <div className="mt-4 rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/30 p-4 max-h-72 overflow-auto">
            {log?.lines.length ? (
              <pre className="m-0 whitespace-pre-wrap break-words text-[var(--warm-700)] font-mono" style={{ fontSize: "0.75rem", lineHeight: 1.7 }}>
                {log.lines.join("\n")}
              </pre>
            ) : (
              <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
                {copy("overview.technicalLog.empty")}
              </p>
            )}
          </div>
        </details>
      </div>
    </section>
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
    return (
      <ErrorState
        title={copy("overview.error.title")}
        message={error ?? copy("overview.error.message")}
        onRetry={reload}
        linkLabel={copy("page.books.title")}
        linkTo="/books"
      />
    );
  }

  const { detail, marks } = data;
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
        bookLanguage={detail.book_language}
        outputLanguage={detail.output_language}
        chapterCount={detail.chapter_count}
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
          <div className="grid grid-cols-1 lg:grid-cols-[22rem_minmax(0,1fr)] gap-6 items-start">
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

            <RuntimeFeedPanel
              analysis={analysisResource.analysis}
              activity={analysisResource.activity}
              log={analysisResource.log}
              loading={analysisResource.loading}
              error={analysisResource.error}
              onRetry={analysisResource.refresh}
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
