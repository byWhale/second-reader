import { APP_LOCALE, resolveLocalizedText, type LocalizedText } from "./app-locale";

type BrandLexicon = {
  productName: string;
  footerSignature: LocalizedText;
};

type ProductLexiconEntry = {
  en: string;
  zh: string;
  definition: string;
  usageNote: string;
  forbiddenAlternatives?: string[];
};

export const BRAND_LEXICON: BrandLexicon = {
  productName: "书虫",
  footerSignature: {
    en: "书虫 · An AI reading companion for those who read to think.",
    zh: "书虫 · 为深度思考型读者而生的 AI 共读伙伴。",
  },
};

export const PRODUCT_LEXICON = {
  "nav.books": {
    en: "Books",
    zh: "书架",
    definition: "Primary navigation label for the workspace home of uploaded books.",
    usageNote: "Use in global navigation and short cross-page return links.",
  },
  "nav.marks": {
    en: "My Marks",
    zh: "我的标记",
    definition: "Primary navigation label for the workspace-wide saved marks view.",
    usageNote: "Use in global navigation and page headers.",
  },
  "view.structure": {
    en: "Structure",
    zh: "结构",
    definition: "The chapter/section structure view for a book.",
    usageNote: "Use for tabs, section headers, and drawer labels.",
  },
  "view.bookOverview": {
    en: "Book overview",
    zh: "书籍总览",
    definition: "Return action label for the book overview page.",
    usageNote: "Use as a navigation destination label, not a section heading.",
  },
  "view.chapters": {
    en: "Chapters",
    zh: "章节",
    definition: "Label for the chapter list or chapter drawer.",
    usageNote: "Use for drawers, buttons, and compact nav contexts.",
  },
  "view.chapterShort": {
    en: "Ch",
    zh: "章",
    definition: "Compact abbreviation for chapter navigation in the chapter toolbar.",
    usageNote: "Use only in constrained toolbar layouts.",
  },
  "view.sectionShort": {
    en: "Sec",
    zh: "段",
    definition: "Compact abbreviation for section navigation in the chapter toolbar.",
    usageNote: "Use only in constrained toolbar layouts.",
  },
  "view.textSize": {
    en: "Text size",
    zh: "文字大小",
    definition: "Label for reading text-size controls.",
    usageNote: "Use in toolbar buttons and reading settings.",
  },
  "view.myMarks": {
    en: "My Marks",
    zh: "我的标记",
    definition: "Book-scoped marks tab label.",
    usageNote: "Use in book overview tabs.",
  },
  "state.notStarted": {
    en: "Not started",
    zh: "未开始",
    definition: "Book or chapter has not started deep reading yet.",
    usageNote: "Use for shelf cards and chapter status pills.",
  },
  "state.analyzing": {
    en: "In progress",
    zh: "分析中",
    definition: "Book is currently being processed by the deep-reading pipeline.",
    usageNote: "Use for live reading status, not for completed results.",
  },
  "state.paused": {
    en: "Paused",
    zh: "已暂停",
    definition: "Reading run is paused and can resume later.",
    usageNote: "Use concise label form; longer sentence-level copy belongs in controlled copy.",
  },
  "state.completed": {
    en: "Completed",
    zh: "已完成",
    definition: "Processing or a chapter result is fully completed.",
    usageNote: "Use as a status pill or result state.",
  },
  "state.needsAttention": {
    en: "Needs attention",
    zh: "需要处理",
    definition: "Run or chapter encountered an error and needs intervention.",
    usageNote: "Use for error-state summary labels.",
  },
  "state.openResult": {
    en: "Open result",
    zh: "可进入",
    definition: "Completed chapter result is ready to open.",
    usageNote: "Use as a status pill in structure lists.",
  },
  "state.reading": {
    en: "Reading",
    zh: "阅读中",
    definition: "Reader is actively reading a current chapter or section.",
    usageNote: "Use for current in-progress chapter pills.",
  },
  "state.segmenting": {
    en: "Segmenting",
    zh: "切分中",
    definition: "Semantic segmentation is actively preparing text structure.",
    usageNote: "Use for structure-preparation status.",
  },
  "state.waiting": {
    en: "Waiting",
    zh: "等待中",
    definition: "The run is waiting for the next dependency or step to be ready.",
    usageNote: "Use for passive waiting states.",
  },
  "reaction.highlight": {
    en: "Highlight",
    zh: "划线",
    definition: "Passages the agent thinks are worth carrying forward.",
    usageNote: "Use as the canonical label for this reaction type across all UI surfaces.",
    forbiddenAlternatives: ["Key line", "Important passage"],
  },
  "reaction.association": {
    en: "Association",
    zh: "联想",
    definition: "Connections to adjacent ideas or outside patterns.",
    usageNote: "Use as the canonical label for associative reactions.",
  },
  "reaction.curious": {
    en: "Curious",
    zh: "好奇",
    definition: "Questions that push into missing evidence or context.",
    usageNote: "Use as the canonical label for search-seeking reactions.",
  },
  "reaction.discern": {
    en: "Discern",
    zh: "审辩",
    definition: "Sharper distinctions or tensions inside the claim.",
    usageNote: "Use as the canonical label for distinction-making reactions.",
  },
  "reaction.retrospect": {
    en: "Retrospect",
    zh: "回溯",
    definition: "Callbacks to earlier threads in the same book.",
    usageNote: "Use as the canonical label for retrospective reactions.",
  },
  "mark.resonance": {
    en: "Resonance",
    zh: "共鸣",
    definition: "User mark for ideas that strongly resonate.",
    usageNote: "Use as a controlled mark label.",
  },
  "mark.blindspot": {
    en: "Blindspot",
    zh: "盲点",
    definition: "User mark for ideas that expose a blind spot.",
    usageNote: "Use as a controlled mark label.",
  },
  "mark.bookmark": {
    en: "Bookmark",
    zh: "书签",
    definition: "User mark for content worth returning to later.",
    usageNote: "Use as a controlled mark label.",
  },
} as const satisfies Record<string, ProductLexiconEntry>;

export type ProductLexiconKey = keyof typeof PRODUCT_LEXICON;

export function brandProductName() {
  return BRAND_LEXICON.productName;
}

export function brandFooterSignature() {
  return resolveLocalizedText(BRAND_LEXICON.footerSignature);
}

export function term(key: ProductLexiconKey): string {
  return resolveLocalizedText(PRODUCT_LEXICON[key], APP_LOCALE);
}
