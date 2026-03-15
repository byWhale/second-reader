import { copy } from "./controlled-copy";
import { BRAND_LEXICON, term } from "./product-lexicon";

export const BRAND_CONFIG = {
  productName: BRAND_LEXICON.productName,
  navigation: {
    booksLabel: term("nav.books"),
    marksLabel: term("nav.marks"),
  },
  footer: {
    signature: BRAND_LEXICON.footerSignature.en,
  },
} as const;

export function getDocumentTitle(pathname: string): string {
  const normalized = pathname || "/";

  if (normalized === "/") {
    return BRAND_CONFIG.productName;
  }
  if (normalized === "/books") {
    return `${BRAND_CONFIG.productName} · ${copy("page.books.title")}`;
  }
  if (normalized === "/marks") {
    return `${BRAND_CONFIG.productName} · ${copy("page.marks.title")}`;
  }
  if (normalized === "/upload") {
    return `${BRAND_CONFIG.productName} · ${copy("page.upload.title")}`;
  }
  if (/^\/books\/[^/]+\/analysis$/.test(normalized)) {
    return `${BRAND_CONFIG.productName} · ${copy("page.analysis.title")}`;
  }
  if (/^\/books\/[^/]+\/chapters\/[^/]+$/.test(normalized)) {
    return `${BRAND_CONFIG.productName} · ${copy("page.chapter.title")}`;
  }
  if (/^\/books\/[^/]+$/.test(normalized)) {
    return `${BRAND_CONFIG.productName} · ${copy("page.book.title")}`;
  }
  return BRAND_CONFIG.productName;
}
