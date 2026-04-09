import { Activity, ArrowRight, BookOpen, Clock3, LoaderCircle, Search, TreePine } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { copy, maybeCopy } from "../config/controlled-copy";
import { ActivityEvent, AnalysisStateResponse, fetchActivity, fetchAnalysisState, getErrorPresentation, toFrontendPath, toWebSocketUrl } from "../lib/api";
import { canonicalBookAnalysisPath, canonicalBookPath, canonicalChapterPath } from "../lib/contract";
import { reactionLabel } from "../lib/reactions";
import { ErrorState, LoadingState } from "./page-state";

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function renderStructuredText(
  key?: string | null,
  params?: Record<string, unknown> | null,
  fallback?: string,
) {
  return maybeCopy(key, params as Record<string, string | number | null> | undefined) ?? fallback ?? "";
}

type RuntimeStatusReason = "runtime_stale" | "runtime_interrupted" | "resume_incompatible" | "dev_run_abandoned";

function readStatusReason(value: unknown): RuntimeStatusReason | null {
  const rawReason =
    value && typeof value === "object" && "status_reason" in value
      ? (value as { status_reason?: unknown }).status_reason
      : null;
  switch (rawReason) {
    case "runtime_stale":
    case "runtime_interrupted":
    case "resume_incompatible":
    case "dev_run_abandoned":
      return rawReason;
    default:
      return null;
  }
}

function isActiveAnalysisStatus(status: AnalysisStateResponse["status"]) {
  return status === "queued" || status === "parsing_structure" || status === "deep_reading" || status === "chapter_note_generation";
}

function isLastKnownPausedReason(reason: RuntimeStatusReason | null) {
  return reason != null;
}

function chapterStatusLabel(chapter: AnalysisStateResponse["chapters"][number], pausedLastKnown: boolean) {
  if (chapter.status === "completed") {
    return copy("analysis.structure.status.ready");
  }
  if (chapter.status === "in_progress") {
    return pausedLastKnown ? copy("analysis.structure.status.pausedHere") : copy("analysis.structure.status.readingNow");
  }
  if (chapter.status === "error") {
    return copy("analysis.structure.status.needsAttention");
  }
  return copy("analysis.structure.status.queued");
}

export function AnalysisPage() {
  const { id = "", bookId = "" } = useParams();
  const resolvedBookId = id || bookId;
  const bookIdNumber = Number(resolvedBookId);
  const [analysis, setAnalysis] = useState<AnalysisStateResponse | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    setAnalysis(null);
    setActivity([]);
    setLoading(true);
    setError(null);
  }, [bookIdNumber]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRefreshTick((value) => value + 1);
    }, 5000);

    return () => {
      window.clearInterval(timer);
    };
  }, [bookIdNumber]);

  useEffect(() => {
    if (!bookIdNumber) {
      return;
    }

    const socket = new WebSocket(toWebSocketUrl(`/api/ws/books/${bookIdNumber}/analysis`));
    socket.onmessage = () => {
      setRefreshTick((value) => value + 1);
    };
    socket.onerror = () => undefined;

    return () => {
      socket.close();
    };
  }, [bookIdNumber]);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [nextAnalysis, nextActivity] = await Promise.all([
          fetchAnalysisState(bookIdNumber),
          fetchActivity(bookIdNumber),
        ]);

        if (!active) {
          return;
        }

        setAnalysis(nextAnalysis);
        setActivity(nextActivity.items);
        setError(null);
      } catch (reason) {
        if (!active) {
          return;
        }
        setError(reason);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, [bookIdNumber, refreshTick]);

  if (loading && !analysis) {
    return <LoadingState title={copy("analysis.loading")} />;
  }

  if (error || !analysis) {
    const errorState = getErrorPresentation(error, {
      title: copy("analysis.error.title"),
      message: copy("analysis.error.message"),
    });
    return (
      <ErrorState
        title={errorState.title}
        message={errorState.message}
        onRetry={() => {
          setLoading(true);
          setRefreshTick((value) => value + 1);
        }}
        linkLabel={copy("analysis.action.backToBooks")}
        linkTo="/books"
      />
    );
  }

  const statusReason = readStatusReason(analysis);
  const pausedLastKnown = analysis.status === "paused" && isLastKnownPausedReason(statusReason);
  const liveLike = isActiveAnalysisStatus(analysis.status);
  const stageText = renderStructuredText(analysis.stage_label_key, analysis.stage_label_params, copy("overview.runtime.syncing"));
  const lastCheckpointText = analysis.last_checkpoint_at
    ? copy("analysis.meta.lastCheckpoint", { value: formatTimestamp(analysis.last_checkpoint_at) })
    : copy("analysis.meta.noCheckpoint");
  const pulseText = analysis.current_state_panel.pulse_message
    ?? analysis.pulse_message
    ?? (pausedLastKnown ? copy("analysis.currentState.noLastKnownPulse") : copy("analysis.currentState.noLivePulse"));

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
        <p className="text-[var(--warm-500)] mb-1 uppercase tracking-[0.18em]" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
          {pausedLastKnown ? copy("analysis.eyebrow.lastKnown") : copy("analysis.eyebrow.live")}
        </p>
        <h1 className="text-[var(--warm-900)] mb-1" style={{ fontSize: "1.75rem", fontWeight: 600 }}>
          {analysis.title}
        </h1>
        <p className="text-[var(--warm-600)] mb-5" style={{ fontSize: "0.9375rem" }}>
          {analysis.author}
        </p>

        <div className="flex items-center gap-4 flex-wrap mb-4 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
          <span className="inline-flex items-center gap-1.5">
            <LoaderCircle className={`w-4 h-4 ${liveLike ? "animate-spin text-[var(--amber-accent)]" : ""}`} />
            {stageText}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock3 className="w-4 h-4" />
            {liveLike
              ? (analysis.eta_seconds != null ? `${analysis.eta_seconds}s remaining` : copy("analysis.meta.etaUnavailable"))
              : lastCheckpointText}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" />
            {copy("analysis.meta.chapters", {
              completed: analysis.completed_chapters,
              total: analysis.total_chapters,
            })}
          </span>
        </div>

        <div className="h-2 bg-[var(--warm-200)] rounded-full overflow-hidden">
          <div className="h-full bg-[var(--amber-accent)]" style={{ width: `${analysis.progress_percent ?? 0}%` }} />
        </div>

        <div className="flex items-center gap-3 mt-5 flex-wrap">
          {analysis.book_id ? (
            <Link
              to={analysis.status === "completed" ? canonicalBookPath(analysis.book_id) : canonicalBookAnalysisPath(analysis.book_id)}
              data-testid="analysis-open-current"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white no-underline hover:bg-[var(--warm-700)] transition-colors"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              {copy("analysis.action.openCurrent")}
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : null}
          {analysis.last_error ? (
            <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {analysis.last_error.message}
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-6 mt-6">
        <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              {copy("analysis.section.structure")}
            </h2>
          </div>
          <div className="space-y-2">
            {analysis.chapters.map((chapter) => (
              <div
                key={chapter.chapter_id}
                className={`rounded-2xl border p-4 ${
                  chapter.is_current ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)]" : "border-[var(--warm-300)]/30 bg-[var(--warm-50)]"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                      {chapter.chapter_ref}
                    </p>
                    <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                      {chapter.title}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[var(--warm-600)]" style={{ fontSize: "0.75rem" }}>
                      {chapter.segment_count} sections
                    </p>
                    <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                      {chapterStatusLabel(chapter, pausedLastKnown && chapter.is_current)}
                    </p>
                  </div>
                </div>
                {chapter.result_ready ? (
                  <Link
                    to={canonicalChapterPath(analysis.book_id, chapter.chapter_id)}
                    data-testid={`analysis-structure-chapter-${chapter.chapter_id}`}
                    className="inline-flex mt-3 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
                    style={{ fontSize: "0.8125rem", fontWeight: 500 }}
                  >
                    {copy("analysis.structure.openChapter")}
                  </Link>
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <div className="space-y-6">
          <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-[var(--amber-accent)]" />
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                {copy("analysis.section.currentState")}
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl bg-[var(--warm-100)] p-4">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                  {pausedLastKnown ? copy("analysis.currentState.lastKnownChapter") : copy("analysis.currentState.chapter")}
                </p>
                <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                  {analysis.current_state_panel.current_chapter_ref ?? copy("analysis.currentState.waitingForStructure")}
                </p>
              </div>
              <div className="rounded-2xl bg-[var(--warm-100)] p-4">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                  {pausedLastKnown ? copy("analysis.currentState.lastKnownSection") : copy("analysis.currentState.section")}
                </p>
                <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                  {analysis.current_state_panel.current_section_ref ?? copy("analysis.currentState.pending")}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
              {Object.entries(analysis.current_state_panel.reaction_counts).map(([type, count]) => (
                <div key={type} className="rounded-2xl bg-[var(--warm-100)] p-4">
                  <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                    {reactionLabel(type)}
                  </p>
                  <p className="text-[var(--warm-900)]" style={{ fontSize: "1.25rem", fontWeight: 600 }}>
                    {count}
                  </p>
                </div>
              ))}
            </div>

            <p className="text-[var(--warm-600)] mt-4" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
              {pulseText}
            </p>
          </section>

          {analysis.recent_completed_chapters.length > 0 ? (
            <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-4 h-4 text-[var(--amber-accent)]" />
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  {copy("analysis.section.recentCompleted")}
                </h2>
              </div>
              <div className="space-y-3">
                {analysis.recent_completed_chapters.map((chapter) => (
                  <Link
                    key={chapter.chapter_id}
                    to={toFrontendPath(chapter.result_url)}
                    data-testid={`analysis-completed-${chapter.chapter_id}`}
                    className="block rounded-2xl bg-[var(--warm-100)] p-4 no-underline hover:bg-[var(--warm-200)] transition-colors"
                  >
                    <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                      {chapter.chapter_ref}
                    </p>
                    <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                      {chapter.title}
                    </p>
                    <p className="text-[var(--warm-600)] mt-2" style={{ fontSize: "0.8125rem" }}>
                      {chapter.visible_reaction_count} reactions
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-[var(--amber-accent)]" />
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                {copy("analysis.section.activityFeed")}
              </h2>
            </div>
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
          </section>
        </div>
      </div>
    </div>
  );
}
