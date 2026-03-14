import { ArrowRight, BookOpen, Bookmark, Download, Globe2, LoaderCircle, Sparkles } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, useParams } from "react-router";
import { type BookDetailResponse, type BookMarksResponse, fetchBookDetail, fetchBookMarks, resumeBookAnalysis, startBookAnalysis, toApiAssetUrl } from "../lib/api";
import { canonicalBookPath, canonicalChapterPath } from "../lib/contract";
import { useBookAnalysisResource } from "../lib/use-book-analysis-resource";
import { useApiResource } from "../lib/use-api-resource";
import { markLabel } from "../lib/marks";
import { reactionLabel } from "../lib/reactions";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import { BookAnalysisOverview } from "./book-analysis-overview";

function BookOverviewHeader({
  title,
  author,
  coverImageUrl,
  bookLanguage,
  outputLanguage,
  chapterCount,
  markCount,
  segmentCount,
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
  children?: ReactNode;
}) {
  return (
    <div className="flex gap-6 flex-col md:flex-row mb-10">
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
          <span>{segmentCount} segments</span>
        </div>

        {children}
      </div>
    </div>
  );
}

function ChaptersStructureList({
  bookId,
  chapters,
  chapterStatusLabel,
}: {
  bookId: number;
  chapters: Array<{
    chapter_id: number;
    chapter_ref: string;
    title: string;
    segment_count: number;
    visible_reaction_count: number;
    high_signal_reaction_count: number;
    result_ready: boolean;
    status: string;
  }>;
  chapterStatusLabel?: (value: string) => string;
}) {
  return (
    <div className="space-y-3">
      {chapters.map((chapter) => (
        <Link
          key={chapter.chapter_id}
          to={chapter.result_ready ? canonicalChapterPath(bookId, chapter.chapter_id) : canonicalBookPath(bookId)}
          data-testid={`book-overview-chapter-${chapter.chapter_id}`}
          className="block bg-white rounded-2xl border border-[var(--warm-300)]/30 p-5 no-underline hover:border-[var(--amber-accent)]/30 hover:shadow-sm transition-all"
        >
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                {chapter.chapter_ref}
              </p>
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                {chapter.title}
              </h2>
            </div>
            <div className="flex items-center gap-4 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
              <span>{chapter.segment_count} sections</span>
              <span>{chapter.visible_reaction_count} reactions</span>
              <span>{chapter.high_signal_reaction_count} high-signal</span>
              <span className="text-[var(--warm-500)]">{chapterStatusLabel ? chapterStatusLabel(chapter.status) : chapter.status}</span>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

function CompletedBookOverview({
  detail,
  marks,
}: {
  detail: BookDetailResponse;
  marks: BookMarksResponse;
}) {
  const [activeTab, setActiveTab] = useState<"chapters" | "marks">("chapters");

  return (
    <>
      <div className="flex items-center gap-2 mb-6 bg-[var(--warm-200)]/50 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab("chapters")}
          className={`px-4 py-2 rounded-md cursor-pointer transition-colors ${
            activeTab === "chapters" ? "bg-white shadow-sm text-[var(--warm-900)]" : "text-[var(--warm-600)]"
          }`}
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          Chapters
        </button>
        <button
          onClick={() => setActiveTab("marks")}
          className={`px-4 py-2 rounded-md cursor-pointer transition-colors ${
            activeTab === "marks" ? "bg-white shadow-sm text-[var(--warm-900)]" : "text-[var(--warm-600)]"
          }`}
          style={{ fontSize: "0.875rem", fontWeight: 500 }}
        >
          My Marks
        </button>
      </div>

      {activeTab === "chapters" ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                Completed chapters
              </p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1.375rem", fontWeight: 600 }}>
                {detail.completed_chapter_count}/{detail.chapter_count}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                Reaction density
              </p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1.375rem", fontWeight: 600 }}>
                {detail.segment_count > 0
                  ? (Object.values(detail.reaction_counts).reduce((sum, count) => sum + count, 0) / detail.segment_count).toFixed(2)
                  : "0.00"}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                Top reaction type
              </p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                {reactionLabel(
                  Object.entries(detail.reaction_counts).sort((left, right) => right[1] - left[1])[0]?.[0] ?? "highlight",
                )}
              </p>
            </div>
          </div>

          {detail.chapters.length === 0 ? (
            <EmptyState
              title="No chapters are available yet"
              message="Chapter-level results are not ready yet for this book."
            />
          ) : (
            <ChaptersStructureList bookId={detail.book_id} chapters={detail.chapters} />
          )}
        </div>
      ) : marks.groups.length === 0 ? (
        <EmptyState
          title="No marks for this book yet"
          message="Resonance, blindspot, and bookmark marks will appear here after you review chapter reactions."
        />
      ) : (
        <div className="space-y-6">
          {marks.groups.map((group) => (
            <section key={group.chapter_id}>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                  {group.chapter_ref}
                </h2>
                <Link
                  to={canonicalChapterPath(detail.book_id, group.chapter_id)}
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
                    <div key={mark.mark_id} className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-5 shadow-sm">
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
      )}
    </>
  );
}

export function BookOverviewPage() {
  const { id = "", bookId = "" } = useParams();
  const resolvedBookId = id || bookId;
  const bookIdNumber = Number(resolvedBookId);
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

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <BookOverviewHeader
        title={detail.title}
        author={detail.author}
        coverImageUrl={detail.cover_image_url}
        bookLanguage={detail.book_language}
        outputLanguage={detail.output_language}
        chapterCount={detail.chapter_count}
        markCount={detail.my_mark_count}
        segmentCount={detail.segment_count}
      >
        {detail.status === "not_started" ? (
          <div className="flex flex-wrap items-center gap-3">
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
          </div>
        ) : detail.status === "analyzing" || detail.status === "paused" ? (
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-bg)] text-[var(--warm-800)]"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <LoaderCircle className={`w-4 h-4 text-[var(--amber-accent)] ${detail.status === "analyzing" ? "animate-spin" : ""}`} />
              {detail.status === "paused" ? "已暂停" : "分析中"}
            </span>
            {detail.status === "paused" ? (
              <button
                type="button"
                onClick={handleResumeAnalysis}
                disabled={resumePending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)] transition-colors disabled:opacity-60 cursor-pointer"
                style={{ fontSize: "0.875rem", fontWeight: 500 }}
              >
                <LoaderCircle className={`w-4 h-4 ${resumePending ? "animate-spin" : ""}`} />
                继续执行
              </button>
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
            {resumeError ? (
              <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
                {resumeError}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={toApiAssetUrl(detail.source_asset.url) ?? "#"}
              data-testid="book-overview-source-download"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <Download className="w-4 h-4" />
              Download source EPUB
            </a>
          </div>
        )}
      </BookOverviewHeader>

      {detail.status === "not_started" ? (
        detail.chapters.length === 0 ? (
          <EmptyState
            title="Book structure is not ready yet"
            message="The book was added, but the parsed chapter structure is not available yet."
          />
        ) : (
          <div className="space-y-6">
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>
                Ready to start
              </p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
                {detail.chapter_count} chapters parsed
              </p>
            </div>
            <ChaptersStructureList
              bookId={detail.book_id}
              chapters={detail.chapters}
              chapterStatusLabel={() => "未开始"}
            />
          </div>
        )
      ) : detail.status === "analyzing" || detail.status === "paused" ? (
        analysisResource.loading && !analysisResource.analysis ? (
          <LoadingState title="Loading live analysis..." />
        ) : analysisResource.error || !analysisResource.analysis ? (
          <ErrorState
            title="Analysis view is unavailable"
            message={analysisResource.error ?? "The reading progress is not available right now."}
            onRetry={analysisResource.refresh}
            linkLabel="Back to books"
            linkTo="/books"
          />
        ) : (
          <BookAnalysisOverview
            analysis={analysisResource.analysis}
            activity={analysisResource.activity}
            log={analysisResource.log}
            onResume={detail.status === "paused" ? handleResumeAnalysis : undefined}
            resumePending={resumePending}
            resumeError={resumeError}
          />
        )
      ) : (
        <CompletedBookOverview detail={detail} marks={marks} />
      )}
    </div>
  );
}
