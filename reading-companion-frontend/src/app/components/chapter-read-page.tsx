import { ArrowLeft, ExternalLink, Lightbulb, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { ChapterDetailResponse, ReactionId, deleteReactionMark, fetchChapterDetail, putReactionMark, toApiAssetUrl } from "../lib/api";
import { reactionLabel } from "../lib/reactions";
import { ErrorState, LoadingState } from "./page-state";

function replaceReaction(
  payload: ChapterDetailResponse,
  reactionId: ReactionId,
  updater: (markType: "known" | "blindspot" | null) => "known" | "blindspot" | null,
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

export function ChapterReadPage() {
  const { bookId: bookIdParam = "", chapterId: chapterIdParam = "" } = useParams();
  const bookId = Number(bookIdParam);
  const chapterNumber = Number(chapterIdParam);
  const [payload, setPayload] = useState<ChapterDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeReactionId, setActiveReactionId] = useState<ReactionId | null>(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    void fetchChapterDetail(bookId, chapterNumber)
      .then((nextPayload) => {
        if (!active) {
          return;
        }
        setPayload(nextPayload);
        const firstReaction = nextPayload.sections.flatMap((section) => section.reactions)[0];
        setActiveReactionId(firstReaction?.reaction_id ?? null);
      })
      .catch((reason) => {
        if (!active) {
          return;
        }
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
  }, [bookId, chapterNumber, reloadTick]);

  if (loading && !payload) {
    return <LoadingState title="Loading chapter result..." />;
  }

  if (error || !payload) {
    return (
      <ErrorState
        title="Chapter result is unavailable"
        message={error ?? "The API did not return chapter data."}
        onRetry={() => {
          setPayload(null);
          setLoading(true);
          setError(null);
          setReloadTick((value) => value + 1);
        }}
        linkLabel="Back to books"
        linkTo="/books"
      />
    );
  }

  const visibleSections = payload.sections
    .map((section) => ({
      ...section,
      reactions: activeFilter === "all"
        ? section.reactions
        : section.reactions.filter((reaction) => reaction.type === activeFilter),
    }))
    .filter((section) => section.reactions.length > 0);

  const reactions = visibleSections.flatMap((section) => section.reactions);
  const activeReaction = reactions.find((reaction) => reaction.reaction_id === activeReactionId) ?? reactions[0] ?? null;

  async function toggleMark(reactionId: ReactionId, currentMark: "known" | "blindspot" | null, nextMark: "known" | "blindspot") {
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

  return (
    <div className="h-[calc(100vh-65px)] flex flex-col">
      <div className="flex items-center justify-between px-6 py-3 border-b border-[var(--warm-200)] bg-white/90 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to={`/books/${payload.book_id}`}
            className="inline-flex items-center gap-1 text-[var(--warm-600)] no-underline hover:text-[var(--warm-800)]"
            style={{ fontSize: "0.8125rem" }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-[var(--warm-300)]">|</span>
          <div className="min-w-0">
            <p className="text-[var(--warm-500)] truncate" style={{ fontSize: "0.75rem" }}>
              {payload.chapter_ref}
            </p>
            <p className="text-[var(--warm-800)] truncate" style={{ fontSize: "0.875rem", fontWeight: 500 }}>
              {payload.title}
            </p>
          </div>
        </div>

        <a
          href={toApiAssetUrl(payload.source_asset.url) ?? "#"}
          className="inline-flex items-center gap-2 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)]"
          style={{ fontSize: "0.8125rem", fontWeight: 500 }}
        >
          Source EPUB
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>

      {error ? (
        <div className="px-6 pt-4">
          <p className="text-[var(--destructive)]" style={{ fontSize: "0.8125rem" }}>
            {error}
          </p>
        </div>
      ) : null}

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 border-r border-[var(--warm-200)] overflow-y-auto">
          <div className="p-6">
            <div className="mb-6">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-[var(--warm-500)] uppercase tracking-[0.18em] mb-1" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                    Chapter result
                  </p>
                  <h1 className="text-[var(--warm-900)]" style={{ fontSize: "1.375rem", fontWeight: 600 }}>
                    {payload.title}
                  </h1>
                </div>
                <div className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                  {payload.visible_reaction_count} reactions · {payload.high_signal_reaction_count} high-signal
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mt-4">
                {payload.available_filters.map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setActiveFilter(filter)}
                    className={`px-3 py-1.5 rounded-full border cursor-pointer transition-colors ${
                      activeFilter === filter
                        ? "border-[var(--amber-accent)] bg-[var(--amber-bg)] text-[var(--amber-accent)]"
                        : "border-[var(--warm-300)]/50 text-[var(--warm-600)] hover:bg-[var(--warm-100)]"
                    }`}
                    style={{ fontSize: "0.75rem", fontWeight: 500 }}
                  >
                    {filter === "all" ? "All" : reactionLabel(filter)}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-8">
              {visibleSections.map((section) => (
                <section key={section.section_ref}>
                  <div className="mb-3 pb-2 border-b border-[var(--warm-200)]">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <div>
                        <p className="text-[var(--amber-accent)] mb-1" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                          {section.section_ref}
                        </p>
                        <p className="text-[var(--warm-700)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                          {section.summary}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                          {section.verdict}
                        </p>
                        <p className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                          {section.quality_status}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {section.reactions.map((reaction) => (
                      <div
                        key={reaction.reaction_id}
                        className={`rounded-2xl border p-4 cursor-pointer transition-colors ${
                          activeReaction?.reaction_id === reaction.reaction_id
                            ? "border-[var(--amber-accent)]/40 bg-[var(--amber-bg)]"
                            : "border-[var(--warm-300)]/30 bg-white hover:border-[var(--warm-300)]"
                        }`}
                        onClick={() => setActiveReactionId(reaction.reaction_id)}
                      >
                        <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
                          <span className="inline-flex px-2.5 py-1 rounded-full bg-[var(--warm-100)] text-[var(--warm-800)]" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                            {reactionLabel(reaction.type)}
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                void toggleMark(reaction.reaction_id, reaction.mark_type ?? null, "known");
                              }}
                              className={`px-2.5 py-1 rounded-full border cursor-pointer transition-colors ${
                                reaction.mark_type === "known"
                                  ? "border-[var(--amber-accent)] bg-[var(--amber-bg)] text-[var(--amber-accent)]"
                                  : "border-[var(--warm-300)]/50 text-[var(--warm-600)]"
                              }`}
                              style={{ fontSize: "0.6875rem", fontWeight: 600 }}
                            >
                              Known
                            </button>
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                void toggleMark(reaction.reaction_id, reaction.mark_type ?? null, "blindspot");
                              }}
                              className={`px-2.5 py-1 rounded-full border cursor-pointer transition-colors ${
                                reaction.mark_type === "blindspot"
                                  ? "border-orange-300 bg-orange-50 text-orange-700"
                                  : "border-[var(--warm-300)]/50 text-[var(--warm-600)]"
                              }`}
                              style={{ fontSize: "0.6875rem", fontWeight: 600 }}
                            >
                              Blindspot
                            </button>
                          </div>
                        </div>

                        <blockquote className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-3 text-[var(--warm-600)] italic" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                          “{reaction.anchor_quote}”
                        </blockquote>
                        <p className="text-[var(--warm-800)]" style={{ fontSize: "0.875rem", lineHeight: 1.8 }}>
                          {reaction.content}
                        </p>
                        {reaction.search_query ? (
                          <div className="flex items-center gap-2 mt-3 text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                            <Search className="w-3.5 h-3.5" />
                            {reaction.search_query}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>

        <div className="w-1/2 bg-white overflow-y-auto">
          <div className="p-8 max-w-2xl">
            {activeReaction ? (
              <>
                <p className="text-[var(--warm-500)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                  Reaction detail
                </p>
                <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.25rem", fontWeight: 600 }}>
                  {reactionLabel(activeReaction.type)}
                </h2>
                <p className="text-[var(--warm-600)] mb-6" style={{ fontSize: "0.875rem" }}>
                  {activeReaction.section_ref} · {activeReaction.section_summary}
                </p>

                <blockquote className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-5 text-[var(--warm-700)] italic" style={{ fontSize: "1rem", lineHeight: 1.8 }}>
                  “{activeReaction.anchor_quote}”
                </blockquote>

                <p className="text-[var(--warm-800)] mb-6" style={{ fontSize: "0.9375rem", lineHeight: 1.9 }}>
                  {activeReaction.content}
                </p>

                {activeReaction.search_results.length > 0 ? (
                  <section className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Search className="w-4 h-4 text-[var(--amber-accent)]" />
                      <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                        Search evidence
                      </h3>
                    </div>
                    <div className="space-y-3">
                      {activeReaction.search_results.map((result) => (
                        <a
                          key={result.url}
                          href={result.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block rounded-2xl bg-[var(--warm-100)] p-4 no-underline hover:bg-[var(--warm-200)] transition-colors"
                        >
                          <p className="text-[var(--warm-900)] mb-1" style={{ fontSize: "0.875rem", fontWeight: 600 }}>
                            {result.title}
                          </p>
                          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                            {result.snippet}
                          </p>
                        </a>
                      ))}
                    </div>
                  </section>
                ) : null}

                <section className="rounded-2xl bg-[var(--warm-100)] p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-4 h-4 text-[var(--amber-accent)]" />
                    <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                      Source locator
                    </h3>
                  </div>
                  {activeReaction.target_locator ? (
                    <div className="space-y-2 text-[var(--warm-600)]" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                      <p>href: {activeReaction.target_locator.href}</p>
                      <p>match: {activeReaction.target_locator.match_text}</p>
                      <p>mode: {activeReaction.target_locator.match_mode}</p>
                    </div>
                  ) : (
                    <p className="text-[var(--warm-600)]" style={{ fontSize: "0.8125rem" }}>
                      No precise locator is available for this reaction.
                    </p>
                  )}
                </section>

                {payload.chapter_reflection.length > 0 ? (
                  <section className="mt-6">
                    <h3 className="text-[var(--warm-900)] mb-3" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                      Chapter reflection
                    </h3>
                    <div className="space-y-2">
                      {payload.chapter_reflection.map((item) => (
                        <div key={item} className="rounded-2xl bg-[var(--warm-100)] px-4 py-3 text-[var(--warm-700)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                          {item}
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <h2 className="text-[var(--warm-900)] mb-2" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
                    No reaction selected
                  </h2>
                  <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                    Choose a reaction on the left to inspect its full content, source locator, and search evidence.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
