import { ArrowRight, Bookmark, Library, Link2, RotateCcw, Scale, Search, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { reactionMeta } from "../lib/reactions";

const reactionCards = [
  {
    type: "highlight",
    icon: Sparkles,
    title: "Highlight",
    description: "Surface the sentence the agent thinks is most worth carrying forward.",
  },
  {
    type: "association",
    icon: Link2,
    title: "Association",
    description: "Connect a passage to nearby ideas, frameworks, or outside patterns.",
  },
  {
    type: "discern",
    icon: Scale,
    title: "Discern",
    description: "Sharpen the distinction, tension, or hidden tradeoff inside a claim.",
  },
  {
    type: "retrospect",
    icon: RotateCcw,
    title: "Retrospect",
    description: "Call back to earlier threads in the book when the current passage reactivates them.",
  },
  {
    type: "curious",
    icon: Search,
    title: "Curious",
    description: "Push into missing evidence, edge cases, and questions worth searching.",
  },
  {
    type: "marks",
    icon: Bookmark,
    title: "Known / Blindspot",
    description: "Use marks to separate what already felt familiar from what actually changed your map.",
  },
];

const teaserReactions = [
  {
    reactionId: 4101,
    type: "highlight",
    chapterRef: "Chapter 1",
    sectionRef: "1.1",
    anchorQuote: "You do not enter relationships with value, you enter relationships as value.",
    content: "The sentence reframes attraction as exchange structure, not mood or moral approval.",
  },
  {
    reactionId: 4102,
    type: "discern",
    chapterRef: "Chapter 1",
    sectionRef: "1.2",
    anchorQuote: "Rules and laws govern behavior because they encode expected consequences.",
    content: "The move is from romance language to system language: consequences are not exceptions, they are the operating logic.",
  },
  {
    reactionId: 4103,
    type: "retrospect",
    chapterRef: "Chapter 1",
    sectionRef: "1.3",
    anchorQuote: "Relationships are games in the sense that incentives shape what survives.",
    content: "This loops back to the opening claim and turns it into a design principle: incentives explain continuity better than stated intentions do.",
  },
];

export function LandingPage() {
  return (
    <div className="overflow-hidden">
      <section className="px-6 pt-18 pb-20">
        <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
          <div>
            <p className="text-[var(--amber-accent)] uppercase tracking-[0.2em] mb-4" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
              Current Product Strategy
            </p>
            <h1 className="text-[var(--warm-900)] mb-5" style={{ fontSize: "3rem", fontWeight: 600, lineHeight: 1.15 }}>
              DeepRead
            </h1>
            <p className="text-[var(--warm-600)] max-w-2xl mb-8" style={{ fontSize: "1.0625rem", lineHeight: 1.8 }}>
              The landing experience is intentionally frontend-owned. The copy, taxonomy explainer cards, and sample teaser cards are static so the product surface stays stable even when backend payloads evolve.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/books"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-lg no-underline transition-colors bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)]"
                style={{ fontSize: "0.9375rem", fontWeight: 500 }}
              >
                Browse books
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/marks"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-lg no-underline transition-colors border border-[var(--warm-300)]/60 text-[var(--warm-700)] hover:bg-[var(--warm-200)]"
                style={{ fontSize: "0.9375rem", fontWeight: 500 }}
              >
                Open marks
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          <div className="bg-white rounded-3xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
            <p className="text-[var(--warm-500)] uppercase tracking-[0.18em] mb-3" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
              Contract Notes
            </p>
            <div className="space-y-4 text-[var(--warm-700)]" style={{ fontSize: "0.875rem", lineHeight: 1.75 }}>
              <p>The canonical web routes are `/`, `/books`, `/books/:id`, `/books/:id/analysis`, `/books/:id/chapters/:chapterId`, and `/marks`.</p>
              <p>All public IDs are integers at the API boundary, even though the backend still stores legacy slug/hash identifiers internally.</p>
              <p>The upload flow remains available at `/upload` as a utility route, but it is not part of the canonical navigation contract.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-18 bg-white/50">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between gap-4 mb-10 flex-wrap">
            <div>
              <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
                Reaction Taxonomy
              </p>
              <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1.75rem", fontWeight: 600 }}>
                The six cards the landing page owns
              </h2>
            </div>
            <Link
              to="/books"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--warm-300)]/50 text-[var(--warm-700)] no-underline hover:bg-[var(--warm-100)] transition-colors"
              style={{ fontSize: "0.875rem", fontWeight: 500 }}
            >
              <Library className="w-4 h-4" />
              Open books
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {reactionCards.map((item) => {
              const Icon = item.icon;
              const meta = reactionMeta[item.type] ?? reactionMeta.highlight;
              return (
                <div key={item.title} className={`rounded-2xl border border-[var(--warm-300)]/30 p-5 ${meta.surfaceClass} shadow-sm`}>
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className={`w-4 h-4 ${meta.accentClass}`} />
                    <h3 className="text-[var(--warm-900)]" style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                      {item.title}
                    </h3>
                  </div>
                  <p className="text-[var(--warm-600)]" style={{ fontSize: "0.8125rem", lineHeight: 1.7 }}>
                    {item.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-6 py-18">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <p className="text-[var(--amber-accent)] uppercase tracking-[0.18em] mb-2" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>
              Static Sample Teasers
            </p>
            <h2 className="text-[var(--warm-900)]" style={{ fontSize: "1.75rem", fontWeight: 600 }}>
              Hardcoded on purpose for the current landing strategy
            </h2>
          </div>

          <div className="space-y-4">
            {teaserReactions.map((reaction) => (
              <div key={reaction.reactionId} className="bg-white rounded-2xl border border-[var(--warm-300)]/30 p-6 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <span className={`inline-flex px-2.5 py-1 rounded-full text-[var(--warm-900)] ${reactionMeta[reaction.type].surfaceClass}`} style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                    {reactionMeta[reaction.type].label}
                  </span>
                  <span className="text-[var(--warm-500)]" style={{ fontSize: "0.75rem" }}>
                    {reaction.chapterRef} · {reaction.sectionRef}
                  </span>
                </div>
                <blockquote className="border-l-2 border-[var(--amber-accent)]/40 pl-4 mb-3 text-[var(--warm-600)] italic" style={{ fontSize: "0.875rem", lineHeight: 1.7 }}>
                  “{reaction.anchorQuote}”
                </blockquote>
                <p className="text-[var(--warm-800)]" style={{ fontSize: "0.9375rem", lineHeight: 1.8 }}>
                  {reaction.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
