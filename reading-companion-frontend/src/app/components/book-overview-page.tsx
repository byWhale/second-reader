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
  high_signal_reaction_count: number;
  result_ready: boolean;
  status: string;
  is_current: boolean;
};

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
    return "ETA unavailable";
  }
  if (seconds < 60) {
    return `${seconds}s remaining`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s remaining` : `${minutes}m remaining`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m remaining` : `${hours}h remaining`;
}

function totalReactionCount(detail: BookDetailResponse) {
  return Object.values(detail.reaction_counts).reduce((sum, count) => sum + count, 0);
}

function topReactionType(detail: BookDetailResponse) {
  const entry = Object.entries(detail.reaction_counts).sort((left, right) => right[1] - left[1])[0];
  return entry && entry[1] > 0 ? reactionLabel(entry[0]) : "暂无";
}

function isAnalysisParsing(analysis: AnalysisStateResponse | null) {
  if (!analysis) {
    return false;
  }
  const stepLabel = analysis.current_state_panel.current_phase_step ?? analysis.current_phase_step ?? "";
  return analysis.status === "parsing_structure" || /结构|切分/.test(stepLabel);
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
      high_signal_reaction_count: chapter.high_signal_reaction_count,
      result_ready: analysisChapter?.result_ready ?? chapter.result_ready,
      status: analysisChapter?.status ?? chapter.status,
      is_current: analysisChapter?.is_current ?? false,
    };
  });
}

function structureStatusLabel(
  chapter: OverviewChapter,
  viewMode: StructureViewMode,
  options: { isParsing?: boolean; isPaused?: boolean } = {},
) {
  if (viewMode === "outline") {
    return "未开始";
  }

  if (viewMode === "result") {
    if (chapter.status === "error") {
      return "需要处理";
    }
    return "已完成";
  }

  if (chapter.status === "error") {
    return "需要处理";
  }
  if (chapter.status === "completed") {
    return options.isParsing ? "已切分" : chapter.result_ready ? "可查看" : "处理中";
  }
  if (chapter.status === "in_progress") {
    if (options.isPaused) {
      return "暂停在此";
    }
    return options.isParsing ? "切分中" : "深读中";
  }
  return "排队中";
}

function BookOverviewHeader({
  title,
  author,
  coverImageUrl,
  bookLanguage,
  outputLanguage,
  chapterCount,
  markCount,
  segmentCount,
  showSegmentCount,
  children,
}: {
  title: string;
  author: string;
  coverImageUrl?: string | null;
  bookLanguage: string;
  outputLanguage: string;
  chapterCount: number;
  markCount: number;
  segmentCount: number;
  showSegmentCount: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="flex gap-6 flex-col md:flex-row mb-8">
      <div className="w-32 h-42 rounded-2xl overflow-hidden bg-[var(--warm-200)] flex-shrink-0 shadow-sm">
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
        <h1 className="text-[var(--warm-900)] mb-1" style={{ fontSize: "2rem", fontWeight: 600 }}>
          {title}
        </h1>
        <p className="text-[var(--warm-600)] mb-4" style={{ fontSize: "1rem" }}>
          {author}
        </p>

        <div className="flex flex-wrap items-center gap-4 mb-5 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
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
          {showSegmentCount ? <span>{segmentCount} segments</span> : null}
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
    <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
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
              Ready to Start
            </p>
            <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.25rem", fontWeight: 600 }}>
              {detail.chapter_count > 0 ? "原书目录已就绪" : "正在准备目录"}
            </h2>
            <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
              语义段落切分会在开始深读后自动进行，当前页先帮助你确认整本书的原始章节结构。
            </p>
          </div>
          <div className="w-full md:w-64">
            <StatusMetric label="Parsed chapters" value={detail.chapter_count} />
          </div>
        </div>
      </section>
    );
  }

  if (detail.status === "completed") {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm mb-8">
        <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-4" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          Completed Overview
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatusMetric label="Completed chapters" value={`${detail.completed_chapter_count}/${detail.chapter_count}`} />
          <StatusMetric
            label="Reaction density"
            value={detail.segment_count > 0 ? (totalReactionCount(detail) / detail.segment_count).toFixed(2) : "0.00"}
          />
          <StatusMetric label="Top reaction type" value={topReactionType(detail)} />
        </div>
      </section>
    );
  }

  if (detail.status === "error") {
    return (
      <section className="bg-white rounded-3xl border border-[var(--destructive)]/20 p-6 shadow-sm mb-8">
        <p className="text-[var(--destructive)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          Interrupted
        </p>
        <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
          处理过程已中断
        </h2>
        <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
          这本书目前无法继续同步实时状态，请稍后重试或返回书架重新进入。
        </p>
      </section>
    );
  }

  const progressPercent =
    analysis?.progress_percent ??
    (detail.chapter_count > 0 ? Math.round((detail.completed_chapter_count / detail.chapter_count) * 10000) / 100 : 0);
  const parsing = isAnalysisParsing(analysis);
  const stepLabel = analysis?.current_state_panel.current_phase_step ?? analysis?.current_phase_step ?? "Pending";
  const currentFocus = parsing
    ? stepLabel
    : analysis?.current_state_panel.current_section_ref ?? stepLabel;
  const currentChapter = analysis?.current_state_panel.current_chapter_ref ?? "Waiting for structure";
  const reactionEntries = Object.entries(analysis?.current_state_panel.reaction_counts ?? {}).filter(([, count]) => count > 0);

  return (
    <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm mb-8">
      <div className="flex items-start justify-between gap-4 flex-col lg:flex-row lg:items-end">
        <div>
          <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
            Run Console
          </p>
          <div className="flex items-center gap-4 flex-wrap text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
            <span className="inline-flex items-center gap-1.5">
              <LoaderCircle
                className={`w-4 h-4 ${detail.status === "paused" ? "" : "animate-spin text-[var(--amber-accent)]"}`}
              />
              {analysis?.stage_label ?? (detail.status === "paused" ? "已暂停" : "正在同步实时进度")}
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

        <div className="rounded-2xl border border-[var(--warm-300)]/30 bg-[var(--warm-50)] px-4 py-3 min-w-0 w-full lg:w-auto lg:min-w-72">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
            Status summary
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {analysis?.current_state_panel.last_activity_message ?? "Waiting for the next runtime update."}
          </p>
        </div>
      </div>

      <div className="mt-5 h-2 bg-[var(--warm-200)] rounded-full overflow-hidden">
        <div className="h-full bg-[var(--amber-accent)]" style={{ width: `${progressPercent}%` }} />
      </div>

      <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            Current chapter
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {currentChapter}
          </p>
        </div>
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            {parsing ? "Current step" : "Current focus"}
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {currentFocus}
          </p>
        </div>
        <div className="rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/20 p-4">
          <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
            Latest checkpoint
          </p>
          <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5 }}>
            {formatTimestamp(analysis?.last_checkpoint_at) ?? "Not available yet"}
          </p>
        </div>
      </div>

      {reactionEntries.length > 0 && !parsing ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {reactionEntries.map(([type, count]) => (
            <span
              key={type}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--warm-100)] border border-[var(--warm-300)]/20 px-3 py-1.5 text-[var(--warm-700)]"
              style={{ fontSize: "0.75rem", fontWeight: 500 }}
            >
              {reactionLabel(type)}
              <span className="text-[var(--warm-500)]">{count}</span>
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        {analysisLoading && !analysis ? (
          <span className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            正在同步运行时状态...
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
              重试同步
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
        const wrapperClass = `block rounded-2xl border p-5 no-underline transition-all ${
          chapter.is_current
            ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)]"
            : "border-[var(--warm-300)]/30 bg-white hover:border-[var(--amber-accent)]/30 hover:shadow-sm"
        }`;
        const content = (
          <>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                  {chapter.chapter_ref}
                </p>
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  {chapter.title}
                </h2>
              </div>

              <div className="flex items-center gap-4 text-[var(--warm-600)] flex-wrap justify-end" style={{ fontSize: "0.8125rem" }}>
                {viewMode !== "outline" && chapter.segment_count > 0 ? <span>{chapter.segment_count} sections</span> : null}
                {viewMode === "result" ? <span>{chapter.visible_reaction_count} reactions</span> : null}
                {viewMode === "result" ? <span>{chapter.high_signal_reaction_count} high-signal</span> : null}
                <span className="text-[var(--warm-500)]">{statusLabel}</span>
              </div>
            </div>

            {viewMode === "progress" && isInteractive ? (
              <span
                className="inline-flex mt-3 text-[var(--amber-accent)]"
                style={{ fontSize: "0.8125rem", fontWeight: 500 }}
              >
                打开已完成章节
              </span>
            ) : null}
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
  viewMode,
  isParsing = false,
  isPaused = false,
  isCollapsedByDefault = false,
  emptyTitle,
  emptyMessage,
}: {
  bookId: number;
  chapters: OverviewChapter[];
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
    currentRow.scrollIntoView({ block: "center" });
  }, [chapters]);

  const content = chapters.length === 0 ? (
    <div className="py-4">
      <EmptyState title={emptyTitle} message={emptyMessage} />
    </div>
  ) : (
    <div ref={listRef} className="space-y-2 overflow-y-auto pr-2 md:max-h-[32rem] lg:max-h-[calc(100vh-10rem)]">
      {chapters.map((chapter) => {
        const statusLabel = structureStatusLabel(chapter, viewMode, { isParsing, isPaused });
        const isInteractive = chapter.result_ready;
        const wrapperClass = `block rounded-2xl border px-4 py-3 no-underline transition-all ${
          chapter.is_current
            ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)] shadow-sm"
            : "border-[var(--warm-300)]/25 bg-[var(--warm-50)] hover:border-[var(--amber-accent)]/25 hover:bg-white"
        }`;
        const rowContent = (
          <>
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                  {chapter.chapter_ref}
                </p>
                <p
                  className="text-[var(--warm-900)] line-clamp-2"
                  style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.45 }}
                >
                  {chapter.title}
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
                <span>{chapter.high_signal_reaction_count} high-signal</span>
              </div>
            ) : null}

            {viewMode === "progress" && isInteractive ? (
              <div className="mt-2 inline-flex items-center gap-1 text-[var(--amber-accent)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                Open chapter
                <ArrowRight className="w-3 h-3" />
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
                    Structure
                  </h2>
                  <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                    Navigate chapters without turning the page into one long stream.
                  </p>
                </div>
              </div>
              <span className="text-[var(--amber-accent)]" style={{ fontSize: "0.8125rem", fontWeight: 600 }}>
                Expand
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
              Structure
            </h2>
            <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
              Compact chapter navigation with live progress.
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
        title="No marks for this book yet"
        message="Resonance, blindspot, and bookmark marks will appear here as soon as you save them from completed chapters."
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
              Open chapter
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
          正在同步实时状态...
        </p>
      </section>
    );
  }

  if (error || !analysis) {
    return (
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
        <p className="text-[var(--destructive)] mb-3" style={{ fontSize: "0.875rem" }}>
          {error ?? "实时状态暂时不可用。"}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors cursor-pointer"
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          重新同步
        </button>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 flex-col md:flex-row">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-[var(--amber-accent)]" />
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              Run log
            </h2>
          </div>
          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
            Keep one place for recently finished chapters, live activity, and lower-level runtime output.
          </p>
        </div>
        <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
          {activity.length} recent events
        </span>
      </div>

      {analysis.recent_completed_chapters.length > 0 ? (
        <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-4 h-4 text-[var(--amber-accent)]" />
            <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
              Recently completed
            </h3>
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {analysis.recent_completed_chapters.map((chapter) => (
              <Link
                key={chapter.chapter_id}
                to={canonicalChapterPath(analysis.book_id, chapter.chapter_id)}
                data-testid={`analysis-completed-${chapter.chapter_id}`}
                className="block rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/25 px-4 py-3 no-underline hover:bg-white hover:border-[var(--amber-accent)]/25 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                      {chapter.chapter_ref}
                    </p>
                    <p className="text-[var(--warm-900)] line-clamp-2" style={{ fontSize: "0.875rem", fontWeight: 600, lineHeight: 1.5 }}>
                      {chapter.title}
                    </p>
                  </div>
                  <ArrowRight className="w-4 h-4 shrink-0 text-[var(--amber-accent)]" />
                </div>
                <p className="text-[var(--warm-600)] mt-2" style={{ fontSize: "0.75rem" }}>
                  {chapter.visible_reaction_count} reactions · {chapter.high_signal_reaction_count} high-signal
                </p>
              </Link>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-[var(--amber-accent)]" />
          <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
            Activity feed
          </h3>
        </div>
        {activity.length === 0 ? (
          <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            Activity will appear here as the parser and reader make progress.
          </p>
        ) : (
          <div className="space-y-4">
            {activity.map((event) => (
              <div key={event.event_id} className="border-l-2 border-[var(--warm-300)] pl-4">
                <p className="text-[var(--warm-900)]" style={{ fontSize: "0.875rem", fontWeight: 500, lineHeight: 1.6 }}>
                  {event.message}
                </p>
                {event.highlight_quote ? (
                  <blockquote className="text-[var(--warm-600)] italic mt-2" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                    “{event.highlight_quote}”
                  </blockquote>
                ) : null}
                <div className="flex items-center gap-2 flex-wrap mt-2 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                  <span>{formatTimestamp(event.timestamp)}</span>
                  {event.chapter_ref ? <span>{event.chapter_ref}</span> : null}
                  {event.section_ref ? <span>{event.section_ref}</span> : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 border-t border-[var(--warm-300)]/30 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-[var(--amber-accent)]" />
          <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
            Technical log
          </h3>
        </div>
        <details className="group">
          <summary
            className="cursor-pointer text-[var(--amber-accent)] hover:text-[var(--warm-700)]"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            Show recent runtime output
          </summary>
          <div className="mt-4 rounded-2xl bg-[var(--warm-100)] border border-[var(--warm-300)]/30 p-4 max-h-72 overflow-auto">
            {log?.lines.length ? (
              <pre className="m-0 whitespace-pre-wrap break-words text-[var(--warm-700)] font-mono" style={{ fontSize: "0.75rem", lineHeight: 1.7 }}>
                {log.lines.join("\n")}
              </pre>
            ) : (
              <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
                Runtime output will appear here as the parser or reader writes new lines.
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
      setStartError(reason instanceof Error ? reason.message : "Could not start deep reading.");
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
      setResumeError(reason instanceof Error ? reason.message : "Could not continue deep reading.");
    } finally {
      setResumePending(false);
    }
  }

  if (loading) {
    return <LoadingState title="Loading book details..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Book overview is unavailable"
        message={error ?? "We could not load this book right now."}
        onRetry={reload}
        linkLabel="Back to books"
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
  const structureEmptyTitle = detail.status === "not_started" ? "Book structure is not ready yet" : "No chapters are available yet";
  const structureEmptyMessage =
    detail.status === "not_started"
      ? "The book was added, but the parsed chapter structure is not available yet."
      : "Chapter-level structure will appear here as the parser and reader make progress.";

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <BookOverviewHeader
        title={detail.title}
        author={detail.author}
        coverImageUrl={detail.cover_image_url}
        bookLanguage={detail.book_language}
        outputLanguage={detail.output_language}
        chapterCount={detail.chapter_count}
        markCount={detail.my_mark_count}
        segmentCount={detail.segment_count}
        showSegmentCount={detail.status !== "not_started"}
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
              开始深读
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
              继续深读
            </button>
          ) : null}
          {detail.status === "analyzing" ? (
            <span
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-bg)] text-[var(--warm-800)]"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <LoaderCircle className="w-4 h-4 text-[var(--amber-accent)] animate-spin" />
              深读进行中
            </span>
          ) : null}
          <a
            href={toApiAssetUrl(detail.source_asset.url) ?? "#"}
            data-testid="book-overview-source-download"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            <Download className="w-4 h-4" />
            Download source EPUB
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

      <section className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
            Explore this book
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
              Structure
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("marks")}
              className={`px-4 py-2 rounded-lg cursor-pointer transition-colors ${
                activeTab === "marks" ? "bg-white shadow-sm text-[var(--warm-900)]" : "text-[var(--warm-600)]"
              }`}
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              My Marks
            </button>
          </div>
        </div>
        <p className="text-[var(--warm-500)] max-w-2xl" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
          {isRuntimeState
            ? "The structure column acts as a live navigator, while the right side stays focused on progress, completed chapters, and runtime output."
            : "Switch between the book structure and your saved marks without changing page context."}
        </p>
      </section>

      {activeTab === "chapters" ? (
        isRuntimeState ? (
          <div className="grid grid-cols-1 lg:grid-cols-[22rem_minmax(0,1fr)] gap-6 items-start">
            <ProcessingStructureNavigator
              bookId={detail.book_id}
              chapters={structureChapters}
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
                Structure
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
