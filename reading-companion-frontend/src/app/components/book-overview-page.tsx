import { BookOpen, Bookmark, Download, Globe2, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { fetchBookDetail, fetchBookMarks, toApiAssetUrl } from "../lib/api";
import { reactionLabel } from "../lib/reactions";
import { useApiResource } from "../lib/use-api-resource";
import { EmptyState, ErrorState, LoadingState } from "./page-state";
import { ImageWithFallback } from "./figma/ImageWithFallback";

export function BookOverviewPage() {
  const { bookId: bookIdParam = "" } = useParams();
  const bookId = Number(bookIdParam);
  const [activeTab, setActiveTab] = useState<"chapters" | "marks">("chapters");
  const { data, loading, error, reload } = useApiResource(
    async () => ({
      detail: await fetchBookDetail(bookId),
      marks: await fetchBookMarks(bookId),
    }),
    [bookId],
  );

  if (loading) {
    return <LoadingState title="Loading book overview..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Book overview is unavailable"
        message={error ?? "The API did not return book overview data."}
        onRetry={reload}
        linkLabel="Back to books"
        linkTo="/books"
      />
    );
  }

  const { detail, marks } = data;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex gap-6 flex-col md:flex-row mb-10">
        <div className="w-32 h-42 rounded-2xl overflow-hidden bg-[var(--warm-200)] flex-shrink-0 shadow-sm">
          {detail.cover_image_url ? (
            <ImageWithFallback
              src={toApiAssetUrl(detail.cover_image_url) ?? ""}
              alt={detail.title}
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
            {detail.title}
          </h1>
          <p className="text-[var(--warm-600)] mb-4" style={{ fontSize: "1rem" }}>
            {detail.author}
          </p>

          <div className="flex flex-wrap items-center gap-4 mb-5 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
            <span className="inline-flex items-center gap-1.5">
              <Globe2 className="w-4 h-4" />
              {detail.book_language} → {detail.output_language}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" />
              {detail.chapter_count} chapters
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Bookmark className="w-4 h-4" />
              {detail.my_mark_count} marks
            </span>
            <span>{detail.segment_count} segments</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {detail.status === "analyzing" ? (
              <Link
                to={`/books/${detail.book_id}/analysis`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--amber-accent)] text-white no-underline hover:bg-[var(--warm-700)] transition-colors"
                style={{ fontSize: "0.875rem", fontWeight: 500 }}
              >
                Continue analysis
              </Link>
            ) : null}
            <a
              href={toApiAssetUrl(detail.source_asset.url) ?? "#"}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/60 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <Download className="w-4 h-4" />
              Download source EPUB
            </a>
          </div>
        </div>
      </div>

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
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>Completed chapters</p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1.375rem", fontWeight: 600 }}>
                {detail.completed_chapter_count}/{detail.chapter_count}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>Reaction density</p>
              <p className="text-[var(--warm-900)]" style={{ fontSize: "1.375rem", fontWeight: 600 }}>
                {detail.segment_count > 0
                  ? (Object.values(detail.reaction_counts).reduce((sum, count) => sum + count, 0) / detail.segment_count).toFixed(2)
                  : "0.00"}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-[var(--warm-300)]/30 p-5 shadow-sm">
              <p className="text-[var(--warm-500)] mb-1" style={{ fontSize: "0.75rem" }}>Top reaction type</p>
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
              message="This book has not produced chapter-level results yet."
              actionLabel={detail.status === "analyzing" ? "Open analysis" : undefined}
              actionTo={detail.status === "analyzing" ? `/books/${detail.book_id}/analysis` : undefined}
            />
          ) : (
            <div className="space-y-3">
              {detail.chapters.map((chapter) => (
                <Link
                  key={chapter.chapter_id}
                  to={chapter.result_ready ? `/books/${detail.book_id}/chapters/${chapter.chapter_id}` : `/books/${detail.book_id}/analysis`}
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
                      <span className="text-[var(--warm-500)]">{chapter.status}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      ) : marks.groups.length === 0 ? (
        <EmptyState
          title="No marks for this book yet"
          message="Known and blindspot marks will appear here after you review chapter reactions."
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
                  to={`/books/${detail.book_id}/chapters/${group.chapter_id}`}
                  className="text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
                  style={{ fontSize: "0.8125rem", fontWeight: 500 }}
                >
                  Open chapter
                </Link>
              </div>

              <div className="space-y-3">
                {group.items.map((mark) => (
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
                        {mark.mark_type}
                      </span>
                    </div>
                    <blockquote className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-3 text-[var(--warm-600)] italic" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                      “{mark.anchor_quote}”
                    </blockquote>
                    <p className="text-[var(--warm-800)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                      {mark.reaction_excerpt}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
