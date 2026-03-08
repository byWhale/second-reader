import { Bookmark } from "lucide-react";
import { Link } from "react-router";
import { fetchGlobalMarks } from "../lib/api";
import { reactionLabel } from "../lib/reactions";
import { useApiResource } from "../lib/use-api-resource";
import { EmptyState, ErrorState, LoadingState } from "./page-state";

export function GlobalMarksPage() {
  const { data, loading, error, reload } = useApiResource(fetchGlobalMarks, []);

  if (loading) {
    return <LoadingState title="Loading saved marks..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Marks page is unavailable"
        message={error ?? "The API did not return mark data."}
        onRetry={reload}
        linkLabel="Back to books"
        linkTo="/books"
      />
    );
  }

  const grouped = data.items.reduce<Record<string, typeof data.items>>((accumulator, item) => {
    const current = accumulator[item.book_id] ?? [];
    current.push(item);
    accumulator[item.book_id] = current;
    return accumulator;
  }, {});

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <Bookmark className="w-6 h-6 text-[var(--amber-accent)]" />
        <div>
          <h1 className="text-[var(--warm-900)]" style={{ fontSize: "1.875rem", fontWeight: 600 }}>
            My Marks
          </h1>
          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem" }}>
            Known and blindspot reactions saved across the whole workspace
          </p>
        </div>
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          title="No marks yet"
          message="Review book and chapter result pages, then use the mark controls on individual reactions."
          actionLabel="Open books"
          actionTo="/books"
        />
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([bookId, items]) => (
            <section key={bookId}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
                    {items[0]?.book_title}
                  </h2>
                  <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                    {items.length} saved marks
                  </p>
                </div>
                <Link
                  to={`/books/${bookId}`}
                  className="text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
                  style={{ fontSize: "0.8125rem", fontWeight: 500 }}
                >
                  Open book
                </Link>
              </div>

              <div className="space-y-3">
                {items.map((mark) => (
                  <div key={mark.mark_id} className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-5 shadow-sm">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                        {mark.chapter_ref} · {mark.section_ref}
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

                    <Link
                      to={`/books/${mark.book_id}/chapters/${mark.chapter_id}`}
                      className="inline-flex mt-4 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
                      style={{ fontSize: "0.8125rem", fontWeight: 500 }}
                    >
                      Open chapter
                    </Link>
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
