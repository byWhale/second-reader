import { BRAND_CONFIG } from "../config/brand";
import { canonicalBookPath, type BookId, type ReactionId, type ReactionType } from "../lib/contract";

const DEFAULT_PREVIEW_BOOK_ID: BookId = 2488754074399462;

export const LANDING_HERO = {
  title: "What AI Thinks About",
  emphasis: "When AI Reads",
  description: "An AI reading companion that reads alongside you, noticing what you might miss, questioning what you might accept, and connecting what you might not link.",
  kicker: "Helping you find your UNKNOWN UNKNOWNS.",
  primaryCta: {
    label: "View Sample",
    to: canonicalBookPath(DEFAULT_PREVIEW_BOOK_ID),
  },
  secondaryCta: {
    label: "Upload EPUB",
    to: "/upload",
  },
} as const;

export const LANDING_HERO_ART = {
  src: "/landing-hero-illustration.png",
  alt: "A brass reading automaton leaning over an open book at a cluttered desk.",
  desktopObjectPosition: "50% 50%",
  mobileObjectPosition: "52% 44%",
} as const;

export const LANDING_REACTION_SECTION = {
  eyebrow: "Reactions That Emerge",
  title: "How the agent thinks as it reads",
  description:
    "It reads paragraph by paragraph, letting different reactions emerge from the text itself rather than forcing every passage through a fixed sequence.",
} as const;

export const LANDING_REACTION_ART = {
  src: "/landing/reactions-robot-illustration.png",
  alt: "A brass robot thinking through books, questions, patterns, and distinctions.",
} as const;

export const LANDING_PREVIEW_SECTION = {
  eyebrow: "Live Preview",
  title: "A taste of deep reading",
  description: "See how one book turns into a trail of highlighted passages, distinctions, questions, and callbacks.",
  ctaLabel: "Explore the full sample",
} as const;

export const LANDING_REACTION_CARDS = [
  {
    key: "highlight",
    accentType: "highlight",
    title: "Highlight",
    description: "Key passages that carry the most weight in the argument.",
  },
  {
    key: "association",
    accentType: "association",
    title: "Association",
    description: "Cross-domain connections the author does not explicitly make.",
  },
  {
    key: "discern",
    accentType: "discern",
    title: "Discern",
    description: "Tensions, assumptions, or tradeoffs that deserve sharper attention.",
  },
  {
    key: "retrospect",
    accentType: "retrospect",
    title: "Retrospect",
    description: "Earlier passages that gain new meaning in light of what comes later.",
  },
  {
    key: "curious",
    accentType: "curious",
    title: "Curious",
    description: "Questions that send the AI searching for missing context or evidence.",
  },
] as const satisfies ReadonlyArray<{
  key: string;
  accentType: ReactionType;
  title: string;
  description: string;
}>;

export const LANDING_SAMPLE_TEASERS = [
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
] as const satisfies ReadonlyArray<{
  reactionId: ReactionId;
  type: ReactionType;
  chapterRef: string;
  sectionRef: string;
  anchorQuote: string;
  content: string;
}>;

type LandingPreviewConfig = {
  mode: "api" | "static";
  api: {
    bookId: BookId;
    chapterId?: number;
    selectedReactionIds?: readonly ReactionId[];
    maxItems: number;
    ctaTo: string;
  };
  static: {
    sourceTitle: string;
    sourceAuthor: string;
    sourceLabel: string;
    ctaTo: string;
    items: readonly {
      reactionId: ReactionId;
      type: ReactionType;
      chapterRef: string;
      sectionRef: string;
      anchorQuote: string;
      content: string;
    }[];
  };
};

export const LANDING_PREVIEW_CONFIG = {
  mode: "api",
  api: {
    bookId: DEFAULT_PREVIEW_BOOK_ID,
    chapterId: undefined as number | undefined,
    // To hand-pick real preview notes, set chapterId and add public reaction IDs here.
    // selectedReactionIds: [4101, 4102, 4103],
    selectedReactionIds: undefined as readonly ReactionId[] | undefined,
    maxItems: 3,
    ctaTo: canonicalBookPath(DEFAULT_PREVIEW_BOOK_ID),
  },
  static: {
    sourceTitle: "The Value of Others",
    sourceAuthor: "Orion Taraban",
    sourceLabel: "From",
    ctaTo: canonicalBookPath(DEFAULT_PREVIEW_BOOK_ID),
    items: LANDING_SAMPLE_TEASERS,
  },
} as const satisfies LandingPreviewConfig;

export const LANDING_FOOTER_COPY = BRAND_CONFIG.footer.signature;
