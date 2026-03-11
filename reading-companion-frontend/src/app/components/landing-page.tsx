import { ArrowRight, Link2, RotateCcw, Scale, Search, Sparkles, Upload } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import {
  LANDING_FOOTER_COPY,
  LANDING_HERO_ART,
  LANDING_HERO,
  LANDING_PREVIEW_CONFIG,
  LANDING_PREVIEW_SECTION,
  LANDING_REACTION_ART,
  LANDING_REACTION_CARDS,
  LANDING_REACTION_SECTION,
} from "../content/landing-content";
import { type BookDetailResponse, type ChapterDetailResponse, fetchBookDetail, fetchChapterDetail } from "../lib/api";
import { canonicalBookPath, type ReactionType } from "../lib/contract";
import { reactionMeta } from "../lib/reactions";

const landingIcons = {
  highlight: Sparkles,
  association: Link2,
  discern: Scale,
  retrospect: RotateCcw,
  curious: Search,
} as const;

type PreviewReaction = {
  reactionId: number;
  type: ReactionType;
  chapterRef: string;
  sectionRef: string;
  anchorQuote: string;
  content: string;
};

type ResolvedLandingPreview = {
  sourceTitle: string;
  sourceAuthor: string;
  sourceLabel: string;
  ctaTo: string;
  items: ReadonlyArray<PreviewReaction>;
};

function splitKickerText(text: string): { lead: string; emphasis: string } {
  const normalized = text.trim();
  const match = normalized.match(/^(.*\S)\s+(\S+\s+\S+[.!?]?)$/);
  if (!match) {
    return { lead: "", emphasis: normalized };
  }
  return {
    lead: match[1],
    emphasis: match[2],
  };
}

function LandingHeroIllustration({ className = "", mobile = false }: { className?: string; mobile?: boolean }) {
  return (
    <div className={`relative ${className}`.trim()}>
      <img
        src={LANDING_HERO_ART.src}
        alt={LANDING_HERO_ART.alt}
        className="block h-auto w-full drop-shadow-[0_26px_70px_rgba(89,62,38,0.16)]"
        style={{ objectPosition: mobile ? LANDING_HERO_ART.mobileObjectPosition : LANDING_HERO_ART.desktopObjectPosition }}
      />
    </div>
  );
}

function LandingReactionIllustration({ className = "" }: { className?: string }) {
  return (
    <div className={`relative ${className}`.trim()}>
      <div className="absolute inset-[12%] rounded-full bg-[radial-gradient(circle_at_center,rgba(244,234,208,0.88)_0%,rgba(244,234,208,0.4)_52%,rgba(244,234,208,0)_76%)] blur-2xl" />
      <img
        src={LANDING_REACTION_ART.src}
        alt={LANDING_REACTION_ART.alt}
        className="relative block h-auto w-full drop-shadow-[0_16px_42px_rgba(89,62,38,0.14)]"
      />
    </div>
  );
}

function buildStaticPreview(): ResolvedLandingPreview {
  return {
    sourceTitle: LANDING_PREVIEW_CONFIG.static.sourceTitle,
    sourceAuthor: LANDING_PREVIEW_CONFIG.static.sourceAuthor,
    sourceLabel: LANDING_PREVIEW_CONFIG.static.sourceLabel,
    ctaTo: LANDING_PREVIEW_CONFIG.static.ctaTo,
    items: LANDING_PREVIEW_CONFIG.static.items,
  };
}

function collectPreviewItems(chapter: ChapterDetailResponse): PreviewReaction[] {
  const items = new Map<number, PreviewReaction>();

  for (const reaction of chapter.featured_reactions) {
    items.set(reaction.reaction_id, {
      reactionId: reaction.reaction_id,
      type: reaction.type,
      chapterRef: reaction.chapter_ref,
      sectionRef: reaction.section_ref,
      anchorQuote: reaction.anchor_quote,
      content: reaction.content,
    });
  }

  for (const section of chapter.sections) {
    for (const reaction of section.reactions) {
      if (items.has(reaction.reaction_id)) {
        continue;
      }
      items.set(reaction.reaction_id, {
        reactionId: reaction.reaction_id,
        type: reaction.type,
        chapterRef: chapter.chapter_ref,
        sectionRef: reaction.section_ref,
        anchorQuote: reaction.anchor_quote,
        content: reaction.content,
      });
    }
  }

  return Array.from(items.values());
}

function selectPreviewItems(chapter: ChapterDetailResponse, maxItems: number, selectedReactionIds?: readonly number[]) {
  const allItems = collectPreviewItems(chapter);

  if (selectedReactionIds?.length) {
    const byId = new Map(allItems.map((item) => [item.reactionId, item]));
    const selectedItems = selectedReactionIds
      .map((reactionId) => byId.get(reactionId))
      .filter((item): item is PreviewReaction => Boolean(item));

    if (selectedItems.length > 0) {
      return selectedItems.slice(0, maxItems);
    }
  }

  const featured = chapter.featured_reactions.slice(0, maxItems).map((reaction) => ({
    reactionId: reaction.reaction_id,
    type: reaction.type,
    chapterRef: reaction.chapter_ref,
    sectionRef: reaction.section_ref,
    anchorQuote: reaction.anchor_quote,
    content: reaction.content,
  }));
  if (featured.length > 0) {
    return featured;
  }
  return allItems.slice(0, maxItems);
}

async function loadApiPreview(): Promise<ResolvedLandingPreview | null> {
  if (LANDING_PREVIEW_CONFIG.mode !== "api") {
    return null;
  }

  const detail: BookDetailResponse = await fetchBookDetail(LANDING_PREVIEW_CONFIG.api.bookId);
  const fallbackChapter = detail.chapters.find((chapter) => chapter.result_ready);
  const chapterId = LANDING_PREVIEW_CONFIG.api.chapterId ?? fallbackChapter?.chapter_id;

  if (!chapterId) {
    return null;
  }

  const chapter = await fetchChapterDetail(LANDING_PREVIEW_CONFIG.api.bookId, chapterId);
  const items = selectPreviewItems(
    chapter,
    LANDING_PREVIEW_CONFIG.api.maxItems,
    LANDING_PREVIEW_CONFIG.api.selectedReactionIds,
  );
  if (items.length === 0) {
    return null;
  }

  return {
    sourceTitle: detail.title,
    sourceAuthor: detail.author,
    sourceLabel: "From",
    ctaTo: LANDING_PREVIEW_CONFIG.api.ctaTo ?? canonicalBookPath(detail.book_id),
    items,
  };
}

export function LandingPage() {
  const [preview, setPreview] = useState<ResolvedLandingPreview>(buildStaticPreview);
  const kickerParts = splitKickerText(LANDING_HERO.kicker);
  const topReactionCards = LANDING_REACTION_CARDS.slice(0, 3);
  const bottomReactionCards = LANDING_REACTION_CARDS.slice(3);

  useEffect(() => {
    let active = true;
    setPreview(buildStaticPreview());

    if (LANDING_PREVIEW_CONFIG.mode !== "api") {
      return () => {
        active = false;
      };
    }

    void loadApiPreview()
      .then((nextPreview) => {
        if (!active || !nextPreview) {
          return;
        }
        setPreview(nextPreview);
      })
      .catch(() => undefined);

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="overflow-hidden">
      <section className="relative isolate px-6 pt-18 pb-24 md:pt-24 md:pb-30">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-8 h-64 w-64 -translate-x-1/2 rounded-full bg-[var(--amber-accent)]/8 blur-3xl" />
          <div className="absolute -right-24 top-20 hidden xl:block h-96 w-96 rounded-full bg-[var(--association-color)] blur-3xl opacity-60" />
          <div className="absolute right-24 top-48 hidden xl:block h-72 w-72 rounded-full bg-[var(--retrospect-color)] blur-3xl opacity-50" />
          <div className="absolute left-16 bottom-10 hidden xl:block h-56 w-56 rounded-full bg-[var(--highlight-color)] blur-3xl opacity-60" />
        </div>

        <div className="relative z-10 max-w-5xl xl:max-w-[80rem] 2xl:max-w-[86rem] mx-auto xl:px-4 2xl:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="text-center xl:grid xl:grid-cols-[minmax(0,50rem)_22rem] 2xl:grid-cols-[minmax(0,54rem)_24rem] xl:items-center xl:gap-5 2xl:gap-6"
          >
            <div className="xl:pr-2 2xl:pr-4">
              <div className="xl:w-full">
                <h1 className="font-['Lora',Georgia,serif] text-[var(--warm-900)] mb-6" style={{ fontSize: "clamp(3rem, 4.4vw, 4.35rem)", fontWeight: 500, lineHeight: 1.08 }}>
                  <span className="inline-block xl:whitespace-nowrap">{LANDING_HERO.title}</span>
                  <br />
                  <span className="inline-block xl:whitespace-nowrap italic text-[var(--amber-accent)]">{LANDING_HERO.emphasis}</span>
                </h1>
                <p className="text-[var(--warm-600)] max-w-3xl md:max-w-4xl xl:max-w-[43rem] 2xl:max-w-[45rem] mx-auto mb-8" style={{ fontSize: "1.125rem", lineHeight: 1.8 }}>
                  {LANDING_HERO.description}
                  <br />
                  {kickerParts.lead}
                  {kickerParts.lead ? " " : null}
                  <span
                    className="inline-block whitespace-nowrap font-['Lora',Georgia,serif] italic text-[var(--amber-accent)]"
                    style={{ fontSize: "1em", fontWeight: 500, marginLeft: "0.18em" }}
                  >
                    {kickerParts.emphasis}
                  </span>
                </p>
                <div className="flex items-center justify-center gap-4 flex-wrap">
                  <Link
                    to={LANDING_HERO.primaryCta.to}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg no-underline transition-colors bg-[var(--amber-accent)] text-white hover:bg-[var(--warm-700)]"
                    style={{ fontSize: "0.9375rem", fontWeight: 500 }}
                  >
                    {LANDING_HERO.primaryCta.label}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                  <Link
                    to={LANDING_HERO.secondaryCta.to}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg no-underline transition-colors border border-[var(--warm-300)] text-[var(--warm-700)] hover:bg-[var(--warm-200)]"
                    style={{ fontSize: "0.9375rem", fontWeight: 500 }}
                  >
                    <Upload className="w-4 h-4" />
                    {LANDING_HERO.secondaryCta.label}
                  </Link>
                </div>
              </div>
            </div>
            <div className="hidden xl:flex xl:justify-end xl:self-center">
              <LandingHeroIllustration className="w-full max-w-[22rem] 2xl:max-w-[24rem]" />
            </div>
            <div className="mt-10 xl:hidden max-w-2xl mx-auto">
              <LandingHeroIllustration mobile className="w-full max-w-[20rem] mx-auto" />
            </div>
          </motion.div>
        </div>
      </section>

      <section className="px-6 py-18 bg-white/50">
        <div className="max-w-[76rem] mx-auto">
          <div className="text-center mb-8 lg:hidden">
            <p className="text-[var(--amber-accent)] mb-2 tracking-widest uppercase" style={{ fontSize: "0.75rem", fontWeight: 500, letterSpacing: "0.15em" }}>
              {LANDING_REACTION_SECTION.eyebrow}
            </p>
            <h2 className="font-['Lora',Georgia,serif] text-[var(--warm-900)] mb-3" style={{ fontSize: "1.75rem", fontWeight: 500 }}>
              {LANDING_REACTION_SECTION.title}
            </h2>
            <p className="text-[var(--warm-600)] max-w-[52rem] mx-auto" style={{ fontSize: "0.9875rem", lineHeight: 1.75 }}>
              {LANDING_REACTION_SECTION.description}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:hidden">
            {LANDING_REACTION_CARDS.map((item, index) => {
              const meta = reactionMeta[item.accentType];
              const Icon = landingIcons[item.key as keyof typeof landingIcons];
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.08 }}
                  className={`rounded-[1.35rem] border border-[var(--warm-300)]/38 p-5 ${meta.surfaceClass}`}
                >
                  <div className="mb-3 flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${meta.accentClass}`} />
                    <h3 className="font-['Lora',Georgia,serif] text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                      {item.title}
                    </h3>
                  </div>
                  <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.65 }}>
                    {item.description}
                  </p>
                </motion.div>
              );
            })}
          </div>

          <div className="hidden lg:block">
            <div className="ml-auto grid max-w-[74rem] grid-cols-[17rem_1fr] items-start gap-x-9 xl:max-w-[78rem] xl:grid-cols-[18.5rem_1fr] xl:gap-x-11 2xl:max-w-[81rem] 2xl:grid-cols-[19rem_1fr] 2xl:gap-x-12">
              <div className="flex justify-center pt-16 xl:pt-18 2xl:pt-20">
                <LandingReactionIllustration className="w-full max-w-[16.5rem] xl:max-w-[17.75rem] 2xl:max-w-[18.25rem]" />
              </div>

              <div className="space-y-5">
                <div className="mx-auto max-w-[55rem] text-center xl:max-w-[57rem]">
                  <p className="text-[var(--amber-accent)] mb-2 tracking-widest uppercase" style={{ fontSize: "0.75rem", fontWeight: 500, letterSpacing: "0.15em" }}>
                    {LANDING_REACTION_SECTION.eyebrow}
                  </p>
                  <h2 className="font-['Lora',Georgia,serif] text-[var(--warm-900)] mb-3" style={{ fontSize: "1.75rem", fontWeight: 500 }}>
                    {LANDING_REACTION_SECTION.title}
                  </h2>
                  <p className="text-[var(--warm-600)] max-w-[44rem] mx-auto" style={{ fontSize: "0.9875rem", lineHeight: 1.75 }}>
                    {LANDING_REACTION_SECTION.description}
                  </p>
                </div>

                <div className="space-y-3.5">
                  <div className="grid w-full max-w-[55rem] grid-cols-3 gap-3.5 xl:max-w-[57rem]">
                    {topReactionCards.map((item, index) => {
                      const meta = reactionMeta[item.accentType];
                      const Icon = landingIcons[item.key as keyof typeof landingIcons];
                      return (
                        <motion.div
                          key={item.title}
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.5, delay: index * 0.08 }}
                          className={`rounded-[1.35rem] border border-[var(--warm-300)]/45 p-5 min-h-[8.85rem] ${meta.surfaceClass}`}
                        >
                          <div className="mb-3 flex items-center gap-3">
                            <Icon className={`w-5 h-5 shrink-0 ${meta.accentClass}`} />
                            <h3 className="font-['Lora',Georgia,serif] text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                              {item.title}
                            </h3>
                          </div>
                          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.65 }}>
                            {item.description}
                          </p>
                        </motion.div>
                      );
                    })}
                  </div>

                  <div className="grid w-full max-w-[37.25rem] grid-cols-2 gap-3.5 mx-auto">
                    {bottomReactionCards.map((item, index) => {
                      const meta = reactionMeta[item.accentType];
                      const Icon = landingIcons[item.key as keyof typeof landingIcons];
                      return (
                        <motion.div
                          key={item.title}
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.5, delay: (index + topReactionCards.length) * 0.08 }}
                          className={`rounded-[1.35rem] border border-[var(--warm-300)]/45 p-5 min-h-[8.85rem] ${meta.surfaceClass}`}
                        >
                          <div className="mb-3 flex items-center gap-3">
                            <Icon className={`w-5 h-5 shrink-0 ${meta.accentClass}`} />
                            <h3 className="font-['Lora',Georgia,serif] text-[var(--warm-900)]" style={{ fontSize: "1rem", fontWeight: 600 }}>
                              {item.title}
                            </h3>
                          </div>
                          <p className="text-[var(--warm-600)]" style={{ fontSize: "0.875rem", lineHeight: 1.65 }}>
                            {item.description}
                          </p>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-[var(--amber-accent)] mb-2 tracking-widest uppercase" style={{ fontSize: "0.75rem", fontWeight: 500, letterSpacing: "0.15em" }}>
              {LANDING_PREVIEW_SECTION.eyebrow}
            </p>
            <h2 className="font-['Lora',Georgia,serif] text-[var(--warm-900)] mb-3" style={{ fontSize: "1.75rem", fontWeight: 500 }}>
              {LANDING_PREVIEW_SECTION.title}
            </h2>
            <p className="text-[var(--warm-600)] max-w-2xl mx-auto mb-3" style={{ fontSize: "0.9375rem", lineHeight: 1.7 }}>
              {LANDING_PREVIEW_SECTION.description}
            </p>
            <p className="text-[var(--warm-600)]" style={{ fontSize: "0.9375rem" }}>
              {preview.sourceLabel} <span className="italic">{preview.sourceTitle}</span> by {preview.sourceAuthor}
            </p>
          </div>

          <div className="space-y-4">
            {preview.items.map((reaction, index) => (
              <motion.div
                key={reaction.reactionId}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2 + index * 0.15 }}
                className="bg-white rounded-xl p-6 border border-[var(--warm-300)]/30 shadow-sm"
              >
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[var(--warm-900)] ${reactionMeta[reaction.type].surfaceClass}`}
                    style={{ fontSize: "0.75rem", fontWeight: 500 }}
                  >
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
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-10">
            <Link
              to={preview.ctaTo}
              className="inline-flex items-center gap-2 text-[var(--amber-accent)] no-underline hover:text-[var(--warm-700)] transition-colors"
              style={{ fontSize: "0.9375rem", fontWeight: 500 }}
            >
              {LANDING_PREVIEW_SECTION.ctaLabel}
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="px-6 py-12 border-t border-[var(--warm-300)]/30">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-[var(--warm-500)]" style={{ fontSize: "0.8125rem" }}>
            {LANDING_FOOTER_COPY}
          </p>
        </div>
      </footer>
    </div>
  );
}
