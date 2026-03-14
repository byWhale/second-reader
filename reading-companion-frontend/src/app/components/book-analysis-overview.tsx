import { Activity, BookOpen, Clock3, FileText, LoaderCircle, RotateCcw, Search, TreePine } from "lucide-react";
import { Link } from "react-router";
import { type ActivityEvent, type AnalysisLogResponse, type AnalysisStateResponse, toFrontendPath } from "../lib/api";
import { canonicalBookPath, canonicalChapterPath } from "../lib/contract";
import { reactionLabel } from "../lib/reactions";

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

export function BookAnalysisOverview({
  analysis,
  activity,
  log,
  onResume,
  resumePending = false,
  resumeError = null,
}: {
  analysis: AnalysisStateResponse;
  activity: ActivityEvent[];
  log: AnalysisLogResponse | null;
  onResume?: () => void;
  resumePending?: boolean;
  resumeError?: string | null;
}) {
  const isParsing = analysis.status === "parsing_structure";
  const isPaused = analysis.status === "paused";
  const stepLabel = analysis.current_state_panel.current_phase_step ?? analysis.current_phase_step ?? (isParsing ? "Preparing structure" : "Pending");

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
        <div className="flex items-center gap-4 flex-wrap mb-4 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
          <span className="inline-flex items-center gap-1.5">
            <LoaderCircle className={`w-4 h-4 ${analysis.status === "completed" || isPaused ? "" : "animate-spin text-[var(--amber-accent)]"}`} />
            {analysis.stage_label}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock3 className="w-4 h-4" />
            {analysis.eta_seconds != null ? `${analysis.eta_seconds}s remaining` : "ETA unavailable"}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" />
            {analysis.completed_chapters}/{analysis.total_chapters} chapters
          </span>
        </div>

        <div className="h-2 bg-[var(--warm-200)] rounded-full overflow-hidden">
          <div className="h-full bg-[var(--amber-accent)]" style={{ width: `${analysis.progress_percent ?? 0}%` }} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          {analysis.resume_available ? (
            <span className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
              {analysis.last_checkpoint_at ? `Checkpoint ${formatTimestamp(analysis.last_checkpoint_at)}` : "Checkpoint available"}
            </span>
          ) : null}
          {isPaused && onResume ? (
            <button
              type="button"
              onClick={onResume}
              disabled={resumePending}
              className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors disabled:opacity-60 cursor-pointer"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <RotateCcw className={`w-4 h-4 ${resumePending ? "animate-spin" : ""}`} />
              Continue
            </button>
          ) : null}
          {analysis.status === "completed" ? (
            <Link
              to={canonicalBookPath(analysis.book_id)}
              className="inline-flex items-center gap-2 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              Open finished overview
            </Link>
          ) : null}
          {resumeError ? (
            <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
              {resumeError}
            </p>
          ) : null}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-6">
        <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <TreePine className="w-4 h-4 text-[var(--amber-accent)]" />
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
              Structure
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
                      {chapter.status === "completed"
                        ? isParsing
                          ? "Parsed"
                          : "Ready"
                        : chapter.status === "in_progress"
                          ? isParsing
                            ? (isPaused ? "Paused here" : "Parsing now")
                            : "Reading now"
                          : chapter.status === "error"
                            ? "Needs attention"
                            : "Queued"}
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
                    Open chapter result
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
                Current state
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl bg-[var(--warm-100)] p-4">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                  Chapter
                </p>
                <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                  {analysis.current_state_panel.current_chapter_ref ?? "Waiting for structure"}
                </p>
              </div>
              <div className="rounded-2xl bg-[var(--warm-100)] p-4">
                <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                  {isParsing ? "Step" : "Section"}
                </p>
                <p className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                  {isParsing ? stepLabel : analysis.current_state_panel.current_section_ref ?? "Pending"}
                </p>
              </div>
            </div>

            {!isParsing ? (
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
            ) : null}

            <p className="text-[var(--warm-600)] mt-4" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
              {analysis.current_state_panel.last_activity_message ?? "No recent activity message yet."}
            </p>
          </section>

          {analysis.recent_completed_chapters.length > 0 ? (
            <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-4 h-4 text-[var(--amber-accent)]" />
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  Recently completed
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
                      {chapter.visible_reaction_count} reactions · {chapter.high_signal_reaction_count} high-signal
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
                Activity feed
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

          <section className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-4 h-4 text-[var(--amber-accent)]" />
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                Technical log
              </h2>
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
          </section>
        </div>
      </div>
    </div>
  );
}
