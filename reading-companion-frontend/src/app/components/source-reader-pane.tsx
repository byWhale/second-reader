import {
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { copy } from "../config/controlled-copy";
import type { SectionCard } from "../lib/api-types";
import type { ReactionType } from "../lib/contract";
import { reactionMeta } from "../lib/reactions";
import type {
  ReaderCapability,
  ReaderJumpFeedback,
  ReaderJumpRequest,
  ReaderLocation,
  ReaderLocationUpdate,
  ReaderTheme,
} from "../lib/reader-types";
import { normalizeReaderCharacter, normalizeReaderText } from "../lib/reader-types";
import { useElementResponsiveTier } from "./ui/use-responsive-tier";

type EpubContents = {
  document?: Document;
  cfiFromRange?: (range: Range) => string;
};

type EpubRendition = {
  annotations?: {
    highlight: (cfiRange: string, data?: object, cb?: (...args: unknown[]) => void, className?: string, styles?: object) => void;
    remove: (cfiRange: string, type: string) => void;
  };
  destroy: () => void;
  display: (target?: string | number) => Promise<void>;
  getContents: () => EpubContents[] | EpubContents;
  hooks?: {
    content?: {
      register: (fn: (contents: EpubContents) => void) => void;
    };
  };
  next: () => Promise<void>;
  off: (type: string, listener: (...args: unknown[]) => void) => void;
  on: (type: string, listener: (...args: unknown[]) => void) => void;
  prev: () => Promise<void>;
  resize?: (width?: number, height?: number) => void;
  themes?: {
    fontSize: (size: string) => void;
    register: (name: string, rules: Record<string, Record<string, string>>) => void;
    select: (name: string) => void;
  };
};

type EpubBook = {
  destroy: () => void;
  locations?: {
    generate: (chars: number) => Promise<unknown>;
    percentageFromCfi?: (cfi: string) => number;
  };
  ready: Promise<void>;
  renderTo: (container: Element, options?: Record<string, unknown>) => EpubRendition;
};

type EpubCFIComparator = {
  compare: (a: string, b: string) => number;
};

type EpubCreateBook = (
  input: string | ArrayBuffer,
  options?: {
    openAs?: string;
  },
) => EpubBook;

type DisplayedLocation = {
  start?: {
    cfi?: string;
    href?: string;
    percentage?: number;
  };
};

interface SectionLocatorEntry {
  endCfi: string | null;
  href: string | null;
  sectionRef: string;
  startCfi: string | null;
}

export interface SourceReaderPaneProps {
  fontSizePercent: number;
  jumpRequest: ReaderJumpRequest | null;
  onLocationChange?: (update: ReaderLocationUpdate) => void;
  sections: SectionCard[];
  sourceUrl: string | null;
}
const JUMP_DISPLAY_TIMEOUT_CFI_MS = 300;
const JUMP_DISPLAY_TIMEOUT_HREF_MS = 1100;
const JUMP_SPINNER_GUARD_MS = 2200;
const JUMP_SPINNER_DELAY_MS = 180;
const CFI_DISPLAY_FAIL_LIMIT = 2;
const CFI_DEGRADE_MIN_ATTEMPTS = 6;
const CFI_DEGRADE_FAILURE_RATIO = 0.7;
const PAPER_CANVAS_HEX = "#FAF7F2";
const PAPER_SHEET_HEX = "#FFFCF5";
const PAPER_RAIL_BORDER_HEX = "rgba(183, 162, 124, 0.18)";
const NIGHT_CANVAS_HEX = "#16120f";
const NIGHT_SHEET_HEX = "#1d1712";
const NIGHT_RAIL_BORDER_HEX = "rgba(108, 88, 62, 0.42)";

const READER_CAPABILITY: ReaderCapability = {
  cfiJump: true,
  hrefJump: true,
  textHighlight: true,
};

const PAPER_THEME = {
  body: {
    "background-color": PAPER_SHEET_HEX,
    color: "#2c1810",
    "font-family": "'Lora', Georgia, serif",
    "line-height": "1.8",
    margin: "0 auto",
    "max-width": "min(84rem, calc(100vw - 2.5rem))",
    width: "100%",
    "box-sizing": "border-box",
    padding: "1.25rem 2rem 3.5rem",
  },
  p: {
    "margin-bottom": "1.05rem",
  },
};

const NIGHT_THEME = {
  body: {
    "background-color": NIGHT_SHEET_HEX,
    color: "#e8ddcb",
    "font-family": "'Lora', Georgia, serif",
    "line-height": "1.8",
    margin: "0 auto",
    "max-width": "min(84rem, calc(100vw - 2.5rem))",
    width: "100%",
    "box-sizing": "border-box",
    padding: "1.25rem 2rem 3.5rem",
  },
  p: {
    "margin-bottom": "1.05rem",
  },
};

type ReaderHighlightTone = {
  className: string;
  fill: string;
  opacity: string;
};

const READER_HIGHLIGHT_ALPHA_LIGHT = 0.78;
const READER_HIGHLIGHT_ALPHA_NIGHT = 0.42;
const READER_HIGHLIGHT_FALLBACK_HEX = "#F6E3A5";

function hexToRgba(value: string, alpha: number): string {
  const normalized = value.trim().replace(/^#/, "");
  const parsed = normalized.length === 3
    ? normalized.split("").map((character) => Number.parseInt(character.repeat(2), 16))
    : normalized.match(/.{1,2}/g)?.map((segment) => Number.parseInt(segment, 16));

  if (!parsed || parsed.length < 3 || parsed.some((channel) => Number.isNaN(channel))) {
    return `rgba(212, 168, 64, ${alpha})`;
  }

  const [red, green, blue] = parsed;
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function highlightToneForReactionType(
  reactionType: ReactionType | null | undefined,
  theme: ReaderTheme,
): ReaderHighlightTone {
  const alpha = theme === "night" ? READER_HIGHLIGHT_ALPHA_NIGHT : READER_HIGHLIGHT_ALPHA_LIGHT;
  const hex = reactionType ? reactionMeta[reactionType]?.surfaceHex : null;

  return {
    className: "rc-reader-highlight",
    fill: hexToRgba(hex ?? READER_HIGHLIGHT_FALLBACK_HEX, alpha),
    opacity: String(alpha),
  };
}

function normalizeHref(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const [withoutFragment] = value.split("#");
  const [path] = withoutFragment.split("?");
  const normalizedPath = path.replace(/^\.?\//, "").trim().toLowerCase();
  if (!normalizedPath) {
    return null;
  }
  try {
    return decodeURIComponent(normalizedPath);
  } catch {
    return normalizedPath;
  }
}

function hrefBaseName(value: string): string {
  const parts = value.split("/");
  return parts[parts.length - 1] ?? value;
}

function hrefEquivalent(left: string | null, right: string | null): boolean {
  if (!left || !right) {
    return false;
  }
  if (left === right) {
    return true;
  }
  if (left.endsWith(`/${right}`) || right.endsWith(`/${left}`)) {
    return true;
  }
  return hrefBaseName(left) === hrefBaseName(right);
}

function normalizeDisplayedLocation(raw: unknown): DisplayedLocation | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const candidate = raw as { start?: DisplayedLocation["start"] };
  return candidate.start ? { start: candidate.start } : null;
}

function compareCfi(comparator: EpubCFIComparator | null, first: string, second: string): number {
  if (!comparator) {
    return 0;
  }
  try {
    return comparator.compare(first, second);
  } catch {
    return 0;
  }
}

function cfiWithinRange(comparator: EpubCFIComparator | null, cfi: string, start: string | null, end: string | null): boolean {
  if (!start || !end) {
    return false;
  }

  const [lower, upper] = compareCfi(comparator, start, end) <= 0 ? [start, end] : [end, start];
  return compareCfi(comparator, cfi, lower) >= 0 && compareCfi(comparator, cfi, upper) <= 0;
}

function findSectionRefForLocation(
  entries: SectionLocatorEntry[],
  comparator: EpubCFIComparator | null,
  href: string | null,
  cfi: string | null,
): string | null {
  const normalizedHref = normalizeHref(href);
  const hrefMatches = normalizedHref
    ? entries.filter((entry) => hrefEquivalent(normalizeHref(entry.href), normalizedHref))
    : [];

  if (hrefMatches.length === 0) {
    return null;
  }
  if (!cfi) {
    return hrefMatches[0].sectionRef;
  }

  const precise = hrefMatches.find((entry) => cfiWithinRange(comparator, cfi, entry.startCfi, entry.endCfi));
  if (precise) {
    return precise.sectionRef;
  }

  if (!comparator) {
    return hrefMatches[0].sectionRef;
  }

  const withStart = hrefMatches.filter((entry) => entry.startCfi);
  if (withStart.length === 0) {
    return hrefMatches[0].sectionRef;
  }

  let closestBefore: SectionLocatorEntry | null = null;
  let closestAfter: SectionLocatorEntry | null = null;

  for (const entry of withStart) {
    const startCfi = entry.startCfi;
    if (!startCfi) {
      continue;
    }
    const delta = compareCfi(comparator, cfi, startCfi);
    if (delta >= 0) {
      if (
        !closestBefore ||
        compareCfi(comparator, startCfi, closestBefore.startCfi ?? startCfi) > 0
      ) {
        closestBefore = entry;
      }
      continue;
    }
    if (
      !closestAfter ||
      compareCfi(comparator, startCfi, closestAfter.startCfi ?? startCfi) < 0
    ) {
      closestAfter = entry;
    }
  }

  return closestBefore?.sectionRef ?? closestAfter?.sectionRef ?? hrefMatches[0].sectionRef;
}

function getContentsList(rendition: EpubRendition): EpubContents[] {
  const contents = rendition.getContents();
  if (!contents) {
    return [];
  }
  return Array.isArray(contents) ? contents : [contents];
}

function normalizedDocumentHref(contents: EpubContents): string | null {
  const document = contents.document;
  if (!document) {
    return null;
  }

  const candidates = [
    document.querySelector("base")?.getAttribute("href") ?? null,
    document.URL,
    document.baseURI,
  ];
  for (const candidate of candidates) {
    const normalized = normalizeHref(candidate);
    if (normalized) {
      return normalized;
    }
  }

  return null;
}

function prioritizeContentsByHref(contentsList: EpubContents[], href: string | null | undefined): EpubContents[] {
  const normalizedTarget = normalizeHref(href);
  if (!normalizedTarget) {
    return contentsList;
  }

  const matching = contentsList.filter((contents) => {
    const documentHref = normalizedDocumentHref(contents);
    return documentHref ? hrefEquivalent(documentHref, normalizedTarget) : false;
  });

  if (matching.length === 0) {
    return contentsList;
  }

  return [...matching, ...contentsList.filter((contents) => !matching.includes(contents))];
}

function preferredContentsByHref(contentsList: EpubContents[], href: string | null | undefined): EpubContents[] {
  const normalizedTarget = normalizeHref(href);
  if (!normalizedTarget) {
    return contentsList;
  }

  const matching = contentsList.filter((contents) => {
    const documentHref = normalizedDocumentHref(contents);
    return documentHref ? hrefEquivalent(documentHref, normalizedTarget) : false;
  });

  return matching;
}

function buildNormalizedIndexMap(value: string): { indices: number[]; normalized: string } {
  const indices: number[] = [];
  let normalized = "";
  let previousWhitespace = false;

  for (let index = 0; index < value.length; index += 1) {
    const normalizedCharacter = normalizeReaderCharacter(value[index]);
    if (normalizedCharacter === " ") {
      if (previousWhitespace) {
        continue;
      }
      previousWhitespace = true;
    } else {
      previousWhitespace = false;
    }

    normalized += normalizedCharacter;
    indices.push(index);
  }

  return { indices, normalized };
}

type NormalizedDocumentPosition = {
  node: Text;
  offset: number;
};

type NormalizedDocumentMap = {
  normalized: string;
  positions: NormalizedDocumentPosition[];
};

function nearestReadableBlock(node: Text): Element | null {
  return node.parentElement?.closest("p, li, blockquote, h1, h2, h3, h4, h5, h6, figcaption") ?? null;
}

function appendNormalizedCharacter(
  target: NormalizedDocumentMap,
  character: string,
  position: NormalizedDocumentPosition,
  previousWhitespaceRef: { value: boolean },
): void {
  const normalizedCharacter = normalizeReaderCharacter(character);
  if (normalizedCharacter === " ") {
    if (previousWhitespaceRef.value) {
      return;
    }
    previousWhitespaceRef.value = true;
  } else {
    previousWhitespaceRef.value = false;
  }

  target.normalized += normalizedCharacter;
  target.positions.push(position);
}

function buildNormalizedDocumentMap(root: HTMLElement): NormalizedDocumentMap {
  const result: NormalizedDocumentMap = {
    normalized: "",
    positions: [],
  };
  const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const previousWhitespaceRef = { value: false };
  let previousBlock: Element | null = null;
  let node = walker.nextNode();

  while (node) {
    const textNode = node as Text;
    const value = textNode.nodeValue ?? "";
    const currentBlock = nearestReadableBlock(textNode);

    if (
      currentBlock &&
      previousBlock &&
      currentBlock !== previousBlock &&
      result.positions.length > 0
    ) {
      appendNormalizedCharacter(
        result,
        " ",
        { node: textNode, offset: 0 },
        previousWhitespaceRef,
      );
    }

    for (let index = 0; index < value.length; index += 1) {
      appendNormalizedCharacter(
        result,
        value[index],
        { node: textNode, offset: index },
        previousWhitespaceRef,
      );
    }

    if (currentBlock) {
      previousBlock = currentBlock;
    }
    node = walker.nextNode();
  }

  return result;
}

function findRangeByText(node: Text, query: string): Range | null {
  const value = node.nodeValue ?? "";
  if (!value || !query) {
    return null;
  }

  const start = value.indexOf(query);
  if (start === -1) {
    return null;
  }

  const range = node.ownerDocument.createRange();
  range.setStart(node, start);
  range.setEnd(node, start + query.length);
  return range;
}

function findRangeByNormalizedText(node: Text, normalizedQuery: string): Range | null {
  const value = node.nodeValue ?? "";
  if (!value || !normalizedQuery) {
    return null;
  }

  const mapped = buildNormalizedIndexMap(value);
  const startInNormalized = mapped.normalized.indexOf(normalizedQuery);
  if (startInNormalized === -1) {
    return null;
  }

  const start = mapped.indices[startInNormalized];
  const endNormalizedIndex = startInNormalized + normalizedQuery.length - 1;
  const end = mapped.indices[endNormalizedIndex] + 1;

  const range = node.ownerDocument.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
  return range;
}

function findRangeByDocumentText(contents: EpubContents, text: string): Range | null {
  const document = contents.document;
  if (!document?.body) {
    return null;
  }

  const query = normalizeReaderText(text);
  if (!query) {
    return null;
  }

  const mapped = buildNormalizedDocumentMap(document.body);
  const startInNormalized = mapped.normalized.indexOf(query);
  if (startInNormalized === -1) {
    return null;
  }

  const endNormalizedIndex = startInNormalized + query.length - 1;
  const startPosition = mapped.positions[startInNormalized];
  const endPosition = mapped.positions[endNormalizedIndex];
  if (!startPosition || !endPosition) {
    return null;
  }

  const range = document.createRange();
  range.setStart(startPosition.node, startPosition.offset);
  range.setEnd(endPosition.node, endPosition.offset + 1);
  return range;
}

function collapseReaderWhitespace(value: string): string {
  return value.replace(/\s+/gu, " ").trim();
}

function readableBlockElements(root: HTMLElement): HTMLElement[] {
  return Array.from(
    root.querySelectorAll<HTMLElement>("p, li, blockquote, h1, h2, h3, h4, h5, h6, figcaption"),
  ).filter((element) => collapseReaderWhitespace(element.textContent ?? "").length > 0);
}

function buildLooseQueryPhrases(text: string): string[] {
  const tokens = normalizeReaderText(text)
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(" ")
    .map((token) => token.trim())
    .filter(Boolean);

  const phrases: string[] = [];
  const maxWindow = Math.min(tokens.length, 10);

  for (let windowSize = maxWindow; windowSize >= 4; windowSize -= 1) {
    for (let index = 0; index <= tokens.length - windowSize; index += 1) {
      const phrase = tokens.slice(index, index + windowSize).join(" ");
      if (phrase.length >= 18) {
        phrases.push(phrase);
      }
    }
  }

  return [...new Set(phrases)];
}

function findRangeByBlockText(contents: EpubContents, text: string, normalized: boolean): Range | null {
  const document = contents.document;
  if (!document?.body) {
    return null;
  }

  const blocks = readableBlockElements(document.body);
  if (blocks.length === 0) {
    return null;
  }

  const query = normalized ? normalizeReaderText(text) : collapseReaderWhitespace(text);
  if (!query) {
    return null;
  }

  for (const windowSize of [1, 2, 3]) {
    for (let index = 0; index <= blocks.length - windowSize; index += 1) {
      const slice = blocks.slice(index, index + windowSize);
      const candidate = slice.map((element) => element.textContent ?? "").join(" ");
      const haystack = normalized ? normalizeReaderText(candidate) : collapseReaderWhitespace(candidate);
      if (!haystack.includes(query)) {
        continue;
      }

      const range = document.createRange();
      range.setStartBefore(slice[0]);
      range.setEndAfter(slice[slice.length - 1]);
      return range;
    }
  }

  return null;
}

function findRangeByLoosePhrase(contents: EpubContents, text: string): Range | null {
  const document = contents.document;
  if (!document?.body) {
    return null;
  }

  const blocks = readableBlockElements(document.body);
  if (blocks.length === 0) {
    return null;
  }

  const phrases = buildLooseQueryPhrases(text);
  if (phrases.length === 0) {
    return null;
  }

  for (const windowSize of [1, 2, 3]) {
    for (let index = 0; index <= blocks.length - windowSize; index += 1) {
      const slice = blocks.slice(index, index + windowSize);
      const haystack = normalizeReaderText(slice.map((element) => element.textContent ?? "").join(" "));
      if (!haystack) {
        continue;
      }

      const matchedPhrase = phrases.find((phrase) => haystack.includes(phrase));
      if (!matchedPhrase) {
        continue;
      }

      const range = document.createRange();
      range.setStartBefore(slice[0]);
      range.setEndAfter(slice[slice.length - 1]);
      return range;
    }
  }

  return null;
}

function findTextRange(contents: EpubContents, text: string, normalized: boolean): Range | null {
  const document = contents.document;
  if (!document?.body) {
    return null;
  }

  const query = normalized ? normalizeReaderText(text) : text;
  if (!query) {
    return null;
  }

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const textNode = node as Text;
    const range = normalized
      ? findRangeByNormalizedText(textNode, query)
      : findRangeByText(textNode, text);
    if (range) {
      return range;
    }
    node = walker.nextNode();
  }

  return (
    findRangeByDocumentText(contents, text) ??
    findRangeByBlockText(contents, text, normalized) ??
    findRangeByLoosePhrase(contents, text)
  );
}

function findRangeByParagraphIndex(contents: EpubContents, paragraphIndex: number): Range | null {
  const document = contents.document;
  if (!document?.body) {
    return null;
  }

  const blocks = Array.from(
    document.body.querySelectorAll("p, li, blockquote, h1, h2, h3, h4, h5, h6"),
  ).filter((element) => (element.textContent ?? "").trim().length > 0);

  if (blocks.length === 0) {
    return null;
  }

  const targetIndex = Math.max(0, Math.min(blocks.length - 1, paragraphIndex));
  const targetBlock = blocks[targetIndex];
  const range = document.createRange();
  range.selectNodeContents(targetBlock);
  return range;
}

function isRangeVisible(range: Range): boolean {
  const view = range.startContainer.ownerDocument.defaultView;
  if (!view) {
    return false;
  }

  const rect = range.getBoundingClientRect();
  if (!rect || (rect.height === 0 && rect.width === 0)) {
    return false;
  }

  const topSafeMargin = view.innerHeight * 0.08;
  const bottomSafeMargin = view.innerHeight * 0.08;
  return rect.top >= topSafeMargin && rect.bottom <= view.innerHeight - bottomSafeMargin;
}

function cfiFromRangeSafely(contents: EpubContents, range: Range): string | null {
  if (!contents.cfiFromRange) {
    return null;
  }
  try {
    return contents.cfiFromRange(range);
  } catch {
    return null;
  }
}

function findReaderScrollContainer(frameElement: Element | null): HTMLElement | null {
  if (!frameElement) {
    return null;
  }
  if (frameElement instanceof HTMLElement) {
    const nearest = frameElement.closest(".epub-container");
    if (nearest instanceof HTMLElement) {
      return nearest;
    }
  }

  const ownerDocument = frameElement.ownerDocument;
  const candidates = Array.from(ownerDocument.querySelectorAll<HTMLElement>(".epub-container"));
  const containing = candidates.find((candidate) => candidate.contains(frameElement));
  if (containing) {
    return containing;
  }

  return frameElement.parentElement instanceof HTMLElement ? frameElement.parentElement : null;
}

async function scrollRangeIntoView(range: Range): Promise<void> {
  const container =
    (range.startContainer.nodeType === Node.ELEMENT_NODE
      ? (range.startContainer as Element)
      : range.startContainer.parentElement) ??
    null;

  if (!isRangeVisible(range) && container) {
    container.scrollIntoView({
      behavior: "auto",
      block: "center",
      inline: "nearest",
    });
  }

  const view = range.startContainer.ownerDocument.defaultView;
  const frameElement = view?.frameElement;
  if (!view || !(frameElement instanceof Element)) {
    return;
  }

  const outerContainer = findReaderScrollContainer(frameElement);
  if (!outerContainer) {
    return;
  }

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const innerRect = range.getBoundingClientRect();
    if (!innerRect || (innerRect.height === 0 && innerRect.width === 0)) {
      return;
    }

    const frameRect = frameElement.getBoundingClientRect();
    const outerRect = outerContainer.getBoundingClientRect();
    const targetTop = frameRect.top + innerRect.top;
    const targetBottom = frameRect.top + innerRect.bottom;
    const targetMid = (targetTop + targetBottom) / 2;
    const viewportMid = outerRect.top + outerRect.height / 2;
    const delta = targetMid - viewportMid;
    const comfortablyVisible =
      targetTop >= outerRect.top + 28 &&
      targetBottom <= outerRect.bottom - 24;

    if (Math.abs(delta) < 3 && comfortablyVisible) {
      return;
    }

    outerContainer.scrollTo({
      top: Math.max(0, outerContainer.scrollTop + delta),
      behavior: "auto",
    });
    await waitForReaderFrame(1);
  }
}

function disableSmoothScrollInHost(host: HTMLElement): void {
  host.style.scrollBehavior = "auto";
  const descendants = host.querySelectorAll<HTMLElement>("*");
  descendants.forEach((element) => {
    element.style.scrollBehavior = "auto";
  });
}

function applyReaderThemeFlag(doc: Document, theme: ReaderTheme): void {
  doc.documentElement.setAttribute("data-rc-theme", theme);
}

function applyReaderThemeToVisibleContents(rendition: EpubRendition, theme: ReaderTheme): void {
  const contentsList = getContentsList(rendition);
  contentsList.forEach((contents) => {
    if (contents.document) {
      applyReaderThemeFlag(contents.document, theme);
    }
  });
}

function noop(): void {}

function normalizeJumpTarget(target: string | null | undefined): string | null {
  if (!target) {
    return null;
  }
  const normalized = target.trim();
  return normalized.length > 0 ? normalized : null;
}

function isRangeCfi(target: string): boolean {
  const normalized = target.trim();
  if (!normalized.startsWith("epubcfi(")) {
    return false;
  }
  return normalized.includes(",");
}

function isCfiTarget(target: string): boolean {
  return target.trim().startsWith("epubcfi(");
}

function waitForReaderFrame(frameCount = 1): Promise<void> {
  return new Promise((resolve) => {
    let remaining = Math.max(1, frameCount);
    const step = () => {
      remaining -= 1;
      if (remaining <= 0) {
        resolve();
        return;
      }
      window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
  });
}

type ReaderHighlightRect = {
  height: number;
  width: number;
  x: number;
  y: number;
};

function sortedReaderHighlightRects<T extends ReaderHighlightRect>(rects: T[]): T[] {
  return [...rects].sort((left, right) => {
    if (Math.abs(left.y - right.y) > 1) {
      return left.y - right.y;
    }
    return left.x - right.x;
  });
}

function rangeClientRects(range: Range): ReaderHighlightRect[] {
  return sortedReaderHighlightRects(
    Array.from(range.getClientRects())
      .filter((rect) => rect.width > 0 && rect.height > 0)
      .map((rect) => ({
        height: rect.height,
        width: rect.width,
        x: rect.left,
        y: rect.top,
      })),
  );
}

async function alignHighlightOverlayToRange(range: Range): Promise<void> {
  const view = range.startContainer.ownerDocument.defaultView;
  const frameElement = view?.frameElement;
  if (!(frameElement instanceof Element)) {
    return;
  }

  for (let attempt = 0; attempt < 4; attempt += 1) {
    await waitForReaderFrame(attempt === 0 ? 2 : 1);

    const targetRects = rangeClientRects(range);
    if (targetRects.length === 0) {
      continue;
    }

    const overlayRects = sortedReaderHighlightRects(
      Array.from(document.querySelectorAll<SVGRectElement>("g.rc-reader-highlight rect"))
        .map((rect) => {
          const x = Number.parseFloat(rect.getAttribute("x") ?? "");
          const y = Number.parseFloat(rect.getAttribute("y") ?? "");
          const width = Number.parseFloat(rect.getAttribute("width") ?? "");
          const height = Number.parseFloat(rect.getAttribute("height") ?? "");
          return Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(width) && Number.isFinite(height)
            ? { element: rect, x, y, width, height }
            : null;
        })
        .filter((entry): entry is ReaderHighlightRect & { element: SVGRectElement } => entry != null),
    );

    if (overlayRects.length === 0) {
      continue;
    }

    if (overlayRects.length === targetRects.length) {
      overlayRects.forEach((overlayRect, index) => {
        const targetRect = targetRects[index];
        overlayRect.element.setAttribute("x", String(targetRect.x));
        overlayRect.element.setAttribute("y", String(targetRect.y));
        overlayRect.element.setAttribute("width", String(targetRect.width));
        overlayRect.element.setAttribute("height", String(targetRect.height));
      });
      return;
    }

    const referenceTarget = targetRects[0];
    const referenceOverlay = overlayRects[0];
    const deltaY = referenceTarget.y - referenceOverlay.y;
    const deltaX = referenceTarget.x - referenceOverlay.x;

    if (Math.abs(deltaY) < 0.5 && Math.abs(deltaX) < 0.5) {
      return;
    }

    overlayRects.forEach((overlayRect) => {
      overlayRect.element.setAttribute("x", String(overlayRect.x + deltaX));
      overlayRect.element.setAttribute("y", String(overlayRect.y + deltaY));
    });
    return;
  }
}

async function waitForPreferredContents(
  rendition: EpubRendition,
  preferredHref?: string | null,
  maxAttempts = 28,
): Promise<void> {
  const normalizedTarget = normalizeHref(preferredHref);

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const contentsList = getContentsList(rendition);
    const hasTargetDocument =
      !normalizedTarget ||
      contentsList.some((contents) => {
        const documentHref = normalizedDocumentHref(contents);
        return documentHref ? hrefEquivalent(documentHref, normalizedTarget) : false;
      });
    const allDocumentsReady =
      contentsList.length > 0 &&
      contentsList.every((contents) => {
        const readyState = contents.document?.readyState;
        return !readyState || readyState === "interactive" || readyState === "complete";
      });

    if (hasTargetDocument && allDocumentsReady) {
      return;
    }

    await waitForReaderFrame(1);
  }
}

function contentsIncludeText(contents: EpubContents, text: string): boolean {
  const body = contents.document?.body;
  if (!body) {
    return false;
  }
  return normalizeReaderText(body.innerText || body.textContent || "").includes(normalizeReaderText(text));
}

async function waitForMatchTextAvailability(
  rendition: EpubRendition,
  targetText: string,
  preferredHref?: string | null,
  maxAttempts = 28,
): Promise<void> {
  const normalizedTarget = normalizeReaderText(targetText);
  if (!normalizedTarget) {
    return;
  }

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const contentsList = preferredContentsByHref(getContentsList(rendition), preferredHref);
    const hasMatch = contentsList.some((contents) => contentsIncludeText(contents, targetText));
    if (hasMatch) {
      return;
    }
    await waitForReaderFrame(1);
  }
}

export function SourceReaderPane({
  sourceUrl,
  fontSizePercent,
  sections,
  jumpRequest,
  onLocationChange = noop,
}: SourceReaderPaneProps) {
  const sectionLocators = useMemo<SectionLocatorEntry[]>(
    () =>
      sections.map((section) => ({
        endCfi: section.locator?.end_cfi ?? null,
        href: section.locator?.href ?? null,
        sectionRef: section.section_ref,
        startCfi: section.locator?.start_cfi ?? null,
      })),
    [sections],
  );

  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [readerReady, setReaderReady] = useState(false);
  const [lastJumpFeedback, setLastJumpFeedback] = useState<ReaderJumpFeedback | null>(null);
  const [isJumping, setIsJumping] = useState(false);
  const [readerLocation, setReaderLocation] = useState<ReaderLocation>({
    cfi: null,
    href: null,
    progress: null,
    sectionRef: null,
  });

  const hostRef = useRef<HTMLDivElement | null>(null);
  const bookRef = useRef<EpubBook | null>(null);
  const renditionRef = useRef<EpubRendition | null>(null);
  const comparatorRef = useRef<EpubCFIComparator | null>(null);
  const currentHighlightRef = useRef<string | null>(null);
  const highlightCfisRef = useRef<Set<string>>(new Set());
  const lastHandledJumpIdRef = useRef<number | null>(null);
  const activeProgrammaticJumpRef = useRef<number | null>(null);
  const activeProgrammaticSectionRefRef = useRef<string | null>(null);
  const activeJumpRunRef = useRef(0);
  const failedDisplayTargetsRef = useRef<Map<string, number>>(new Map());
  const cfiDisplayStatsRef = useRef({
    attempts: 0,
    degraded: false,
    failures: 0,
  });
  const resizeRafRef = useRef<number | null>(null);
  const currentHighlightRangeRef = useRef<Range | null>(null);
  const sectionLocatorsRef = useRef<SectionLocatorEntry[]>(sectionLocators);
  const onLocationChangeRef = useRef(onLocationChange);
  const theme: ReaderTheme = "paper";
  const themeRef = useRef<ReaderTheme>("paper");

  useEffect(() => {
    sectionLocatorsRef.current = sectionLocators;
  }, [sectionLocators]);

  useEffect(() => {
    onLocationChangeRef.current = onLocationChange;
  }, [onLocationChange]);

  useEffect(() => {
    const host = hostRef.current;
    const rendition = renditionRef.current;
    if (!host || !rendition?.resize || typeof ResizeObserver === "undefined") {
      return;
    }

    const applyResize = () => {
      const rect = host.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) {
        return;
      }
      rendition.resize?.(Math.floor(rect.width), Math.floor(rect.height));
      if (currentHighlightRangeRef.current) {
        void alignHighlightOverlayToRange(currentHighlightRangeRef.current);
      }
    };

    applyResize();
    const observer = new ResizeObserver(() => {
      if (resizeRafRef.current != null) {
        window.cancelAnimationFrame(resizeRafRef.current);
      }
      resizeRafRef.current = window.requestAnimationFrame(() => {
        resizeRafRef.current = null;
        applyResize();
      });
    });
    observer.observe(host);

    return () => {
      observer.disconnect();
      if (resizeRafRef.current != null) {
        window.cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
    };
  }, [readerReady, sourceUrl]);

  useEffect(() => {
    const rendition = renditionRef.current;
    if (!rendition?.themes) {
      return;
    }
    rendition.themes.fontSize(`${fontSizePercent}%`);
    if (currentHighlightRangeRef.current) {
      void alignHighlightOverlayToRange(currentHighlightRangeRef.current);
    }
  }, [fontSizePercent]);

  useEffect(() => {
    const rendition = renditionRef.current;
    if (!rendition?.themes) {
      return;
    }
    rendition.themes.select(theme);
    applyReaderThemeToVisibleContents(rendition, theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;

    async function setupReader() {
      if (!sourceUrl || !hostRef.current) {
        return;
      }

      setIsLoading(true);
      setReaderReady(false);
      setLoadError(null);
      setLastJumpFeedback(null);
      lastHandledJumpIdRef.current = null;
      activeProgrammaticJumpRef.current = null;

      try {
        const module = await import("epubjs");
        const createBook = module.default as unknown as EpubCreateBook;
        const comparator = "EpubCFI" in module
          ? new (module.EpubCFI as unknown as { new (): EpubCFIComparator })()
          : null;

        if (cancelled) {
          return;
        }

        // Backend source endpoint does not end with ".epub", so force zip parsing mode.
        const book = createBook(sourceUrl, { openAs: "epub" });
        const rendition = book.renderTo(hostRef.current, {
          flow: "scrolled-doc",
          manager: "continuous",
          spread: "none",
          width: "100%",
          height: "100%",
        });
        disableSmoothScrollInHost(hostRef.current);

        bookRef.current = book;
        renditionRef.current = rendition;
        comparatorRef.current = comparator;

        rendition.hooks?.content?.register((contents) => {
          if (contents.document) {
            applyReaderThemeFlag(contents.document, themeRef.current);
          }
          // Inject one highlight class for annotation-driven target emphasis.
          void contents.document?.head?.insertAdjacentHTML(
            "beforeend",
            `<style id="rc-reader-highlight-style">
              html {
                box-sizing: border-box !important;
                background: ${PAPER_CANVAS_HEX} !important;
              }
              html[data-rc-theme="night"] {
                background: ${NIGHT_CANVAS_HEX} !important;
              }
              html, body {
                width: 100% !important;
                box-sizing: border-box !important;
              }
              body {
                background: ${PAPER_SHEET_HEX} !important;
                max-width: min(84rem, calc(100vw - 2.5rem)) !important;
                margin: 0 auto !important;
                padding: 1.25rem 2rem 3.5rem !important;
                min-height: 100vh !important;
                border-left: 1px solid ${PAPER_RAIL_BORDER_HEX} !important;
                border-right: 1px solid ${PAPER_RAIL_BORDER_HEX} !important;
              }
              html[data-rc-theme="night"] body {
                background: ${NIGHT_SHEET_HEX} !important;
                border-left-color: ${NIGHT_RAIL_BORDER_HEX} !important;
                border-right-color: ${NIGHT_RAIL_BORDER_HEX} !important;
              }
              html, body, * {
                scroll-behavior: auto !important;
              }
              html, body {
                scrollbar-width: thin !important;
                scrollbar-color: rgba(184, 168, 138, 0.64) transparent !important;
              }
              html::-webkit-scrollbar, body::-webkit-scrollbar {
                width: 8px !important;
                height: 8px !important;
              }
              html::-webkit-scrollbar-track, body::-webkit-scrollbar-track {
                background: transparent !important;
                margin-block: 10px !important;
              }
              html::-webkit-scrollbar-thumb, body::-webkit-scrollbar-thumb {
                border: 2px solid transparent !important;
                border-radius: 999px !important;
                background: linear-gradient(180deg, rgba(224, 212, 190, 0.94), rgba(184, 168, 138, 0.78)) !important;
                background-clip: padding-box !important;
                box-shadow: inset 0 0 0 1px rgba(255, 252, 245, 0.45) !important;
              }
              html[data-rc-theme="night"]::-webkit-scrollbar-thumb,
              html[data-rc-theme="night"] body::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, rgba(128, 106, 77, 0.78), rgba(78, 62, 44, 0.9)) !important;
                background-clip: padding-box !important;
              }
              img, svg, video {
                max-width: 100% !important;
                height: auto !important;
              }
              .rc-reader-highlight {
                mix-blend-mode: multiply;
              }
              html[data-rc-theme="night"] .rc-reader-highlight {
                mix-blend-mode: screen;
              }
            </style>`,
          );
        });

        rendition.themes?.register("paper", PAPER_THEME);
        rendition.themes?.register("night", NIGHT_THEME);
        rendition.themes?.select(theme);
        rendition.themes?.fontSize(`${fontSizePercent}%`);

        const onRelocated = (raw: unknown) => {
          const location = normalizeDisplayedLocation(raw);
          if (!location?.start) {
            return;
          }

          const progressFromEvent = typeof location.start.percentage === "number"
            ? location.start.percentage
            : null;
          const cfi = location.start.cfi ?? null;
          const fallbackProgress =
            cfi && book.locations?.percentageFromCfi
              ? book.locations.percentageFromCfi(cfi)
              : null;
          const href = location.start.href ?? null;
          const sectionRef = findSectionRefForLocation(
            sectionLocatorsRef.current,
            comparatorRef.current,
            href,
            cfi,
          );
          const effectiveSectionRef =
            activeProgrammaticJumpRef.current != null
              ? activeProgrammaticSectionRefRef.current ?? sectionRef
              : sectionRef;
          const update: ReaderLocation = {
            cfi,
            href,
            progress: progressFromEvent ?? fallbackProgress ?? null,
            sectionRef: effectiveSectionRef,
          };
          setReaderLocation(update);
          onLocationChangeRef.current({
            location: update,
            programmatic: activeProgrammaticJumpRef.current != null,
          });
        };

        rendition.on("relocated", onRelocated);

        await book.ready;
        if (cancelled) {
          return;
        }
        if (book.locations?.generate) {
          await book.locations.generate(1600);
        }

        const initialDisplayTarget =
          sectionLocatorsRef.current.find((entry) => entry.href)?.href ??
          sectionLocatorsRef.current.find((entry) => entry.startCfi)?.startCfi ??
          undefined;

        try {
          await rendition.display(initialDisplayTarget);
        } catch {
          await rendition.display();
        }
        if (cancelled) {
          return;
        }

        const initialSectionEntry =
          sectionLocatorsRef.current.find((entry) => entry.startCfi || entry.href) ?? null;
        const initialProgress =
          initialSectionEntry?.startCfi && book.locations?.percentageFromCfi
            ? book.locations.percentageFromCfi(initialSectionEntry.startCfi)
            : null;
        const initialLocation: ReaderLocation = {
          cfi: initialSectionEntry?.startCfi ?? null,
          href: initialSectionEntry?.href ?? null,
          progress: initialProgress,
          sectionRef: initialSectionEntry?.sectionRef ?? null,
        };
        setReaderLocation(initialLocation);
        onLocationChangeRef.current({
          location: initialLocation,
          programmatic: false,
        });

        setReaderReady(true);
        setLastJumpFeedback({
          approximate: false,
          message: "Reader ready.",
          resolution: "book-start",
          sectionRef: null,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : "Failed to initialize EPUB reader.";
        setLoadError(message);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void setupReader();

    return () => {
      cancelled = true;
      currentHighlightRef.current = null;
      highlightCfisRef.current.clear();
      currentHighlightRangeRef.current = null;
      comparatorRef.current = null;
      lastHandledJumpIdRef.current = null;
      activeProgrammaticJumpRef.current = null;
      activeProgrammaticSectionRefRef.current = null;
      const rendition = renditionRef.current;
      const book = bookRef.current;
      renditionRef.current = null;
      bookRef.current = null;
      cfiDisplayStatsRef.current = {
        attempts: 0,
        degraded: false,
        failures: 0,
      };

      if (rendition) {
        try {
          rendition.destroy();
        } catch {
          // ignore teardown errors
        }
      }
      if (book) {
        try {
          book.destroy();
        } catch {
          // ignore teardown errors
        }
      }
    };
  }, [fontSizePercent, sourceUrl]);

  function clearHighlight() {
    const rendition = renditionRef.current;
    const trackedHighlightCfis = Array.from(highlightCfisRef.current);
    if (!rendition || trackedHighlightCfis.length === 0 || !rendition.annotations) {
      highlightCfisRef.current.clear();
      currentHighlightRef.current = null;
      currentHighlightRangeRef.current = null;
      document.querySelectorAll("g.rc-reader-highlight").forEach((node) => node.remove());
      return;
    }
    try {
      trackedHighlightCfis.forEach((cfiRange) => {
        try {
          rendition.annotations?.remove(cfiRange, "highlight");
        } catch {
          // ignore stale annotation removal errors
        }
      });
    } catch {
      // ignore unexpected annotation cleanup errors
    } finally {
      highlightCfisRef.current.clear();
      currentHighlightRef.current = null;
      currentHighlightRangeRef.current = null;
      document.querySelectorAll("g.rc-reader-highlight").forEach((node) => node.remove());
    }
  }

  function highlightCfi(
    cfiRange: string,
    reactionType: ReactionType | null | undefined,
    rangeForAlignment?: Range | null,
  ): boolean {
    const rendition = renditionRef.current;
    if (!rendition?.annotations) {
      return false;
    }
    if (!isRangeCfi(cfiRange)) {
      return false;
    }
    const tone = highlightToneForReactionType(reactionType, themeRef.current);
    clearHighlight();
    try {
      rendition.annotations.highlight(cfiRange, { source: "reaction", reactionType: reactionType ?? null }, undefined, tone.className, {
        fill: tone.fill,
        "fill-opacity": tone.opacity,
      });
      currentHighlightRef.current = cfiRange;
      highlightCfisRef.current.add(cfiRange);
      currentHighlightRangeRef.current = rangeForAlignment ?? null;
      if (rangeForAlignment) {
        void alignHighlightOverlayToRange(rangeForAlignment);
      }
      return true;
    } catch {
      currentHighlightRangeRef.current = null;
      return false;
    }
  }

async function locateMatchText(
  targetText: string,
  reactionType: ReactionType | null | undefined,
  preferredHref?: string | null,
): Promise<"exact" | "normalized" | null> {
  const rendition = renditionRef.current;
  if (!rendition) {
    return null;
  }
  const contentsList = preferredContentsByHref(
    prioritizeContentsByHref(getContentsList(rendition), preferredHref),
    preferredHref,
  );
  if (contentsList.length === 0) {
    return null;
  }

    for (const mode of ["exact", "normalized"] as const) {
      for (const contents of contentsList) {
        const range = findTextRange(contents, targetText, mode === "normalized");
        if (!range) {
          continue;
        }
        await scrollRangeIntoView(range);
        const cfiRange = cfiFromRangeSafely(contents, range);
        if (!cfiRange || highlightCfi(cfiRange, reactionType, range)) {
          return mode;
        }
      }
    }

    return null;
  }

  async function locateSectionParagraph(
    locator: NonNullable<ReaderJumpRequest["sectionLocator"]>,
    reactionType: ReactionType | null | undefined,
  ): Promise<boolean> {
    const rendition = renditionRef.current;
    if (!rendition) {
      return false;
    }

    if (locator.href) {
      try {
        await rendition.display(locator.href);
      } catch {
        // Keep trying in currently loaded contents.
      }
    }

    const contentsList = preferredContentsByHref(
      prioritizeContentsByHref(getContentsList(rendition), locator.href),
      locator.href,
    );
    if (contentsList.length === 0) {
      return false;
    }

    const paragraphIndex = Math.max(0, (locator.paragraph_start ?? 1) - 1);
    for (const contents of contentsList) {
      const range = findRangeByParagraphIndex(contents, paragraphIndex);
      if (!range) {
        continue;
      }
      await scrollRangeIntoView(range);
      const cfiRange = cfiFromRangeSafely(contents, range);
      if (!cfiRange) {
        return true;
      }
      highlightCfi(cfiRange, reactionType, range);
      return true;
    }

    return false;
  }

  async function displayWithTimeout(rendition: EpubRendition, target: string): Promise<boolean> {
    const timeoutMs = isCfiTarget(target) ? JUMP_DISPLAY_TIMEOUT_CFI_MS : JUMP_DISPLAY_TIMEOUT_HREF_MS;
    try {
      await Promise.race([
        rendition.display(target),
        new Promise<never>((_, reject) => {
          window.setTimeout(() => reject(new Error("reader-display-timeout")), timeoutMs);
        }),
      ]);
      await waitForPreferredContents(rendition, isCfiTarget(target) ? null : target);
      return true;
    } catch {
      return false;
    }
  }

  async function jumpToRequest(request: ReaderJumpRequest): Promise<void> {
    const rendition = renditionRef.current;
    if (!rendition) {
      return;
    }
    const runId = activeJumpRunRef.current + 1;
    activeJumpRunRef.current = runId;
    const isStale = () => activeJumpRunRef.current !== runId;
    const spinnerDelay = window.setTimeout(() => {
      if (!isStale()) {
        setIsJumping(true);
      }
    }, JUMP_SPINNER_DELAY_MS);
    const spinnerGuard = window.setTimeout(() => {
      if (activeJumpRunRef.current !== runId) {
        return;
      }
      activeProgrammaticJumpRef.current = null;
      activeProgrammaticSectionRefRef.current = null;
      setIsJumping(false);
      setLastJumpFeedback((current) => current ?? {
        approximate: true,
        message: "Positioning timed out. Stayed near current location.",
        resolution: "nearby",
        sectionRef: request.sectionRef,
      });
    }, JUMP_SPINNER_GUARD_MS);

    const preferHrefFirst = Boolean(request.targetLocator?.match_text && request.targetLocator?.href);
    const targetDisplayPriority = preferHrefFirst
      ? [request.targetLocator?.href, request.targetLocator?.start_cfi]
      : [request.targetLocator?.start_cfi, request.targetLocator?.href];
    const sectionDisplayPriority = preferHrefFirst
      ? [request.sectionLocator?.href, request.sectionLocator?.start_cfi]
      : [request.sectionLocator?.start_cfi, request.sectionLocator?.href];
    const chapterDisplayPriority = preferHrefFirst
      ? [sectionLocators.find((entry) => entry.href)?.href, sectionLocators.find((entry) => entry.startCfi)?.startCfi]
      : [sectionLocators.find((entry) => entry.startCfi)?.startCfi, sectionLocators.find((entry) => entry.href)?.href];
    const displayTargets = request.targetLocator
      ? [
          ...targetDisplayPriority,
          ...sectionDisplayPriority,
          ...chapterDisplayPriority,
        ]
      : [
          ...sectionDisplayPriority,
          ...chapterDisplayPriority,
        ];
    const uniqueTargets = displayTargets.map(normalizeJumpTarget).filter((value): value is string => value != null);
    const dedupedTargets = [...new Set(uniqueTargets)];

    if (dedupedTargets.length === 0) {
        setLastJumpFeedback({
          approximate: true,
          message: "This note is missing a precise anchor, so we opened the chapter instead.",
          resolution: "book-start",
          sectionRef: request.sectionRef,
        });
      if (!isStale()) {
        setIsJumping(false);
      }
      window.clearTimeout(spinnerDelay);
      window.clearTimeout(spinnerGuard);
      return;
    }

    activeProgrammaticJumpRef.current = request.id;
    activeProgrammaticSectionRefRef.current = request.sectionRef;
    clearHighlight();

    try {
      let displayed = false;
      let displayedTarget: string | null = null;
      for (const target of dedupedTargets) {
        if (isStale()) {
          return;
        }
        const isCfi = isCfiTarget(target);
        if (isCfi && cfiDisplayStatsRef.current.degraded) {
          continue;
        }
        const failureCount = failedDisplayTargetsRef.current.get(target) ?? 0;
        if (isCfi && failureCount >= CFI_DISPLAY_FAIL_LIMIT) {
          continue;
        }
        if (isCfi) {
          cfiDisplayStatsRef.current.attempts += 1;
        }
        // Try each locator in priority order; skip hung/invalid targets quickly.
        const success = await displayWithTimeout(rendition, target);
        if (success) {
          failedDisplayTargetsRef.current.delete(target);
          displayed = true;
          displayedTarget = target;
          break;
        }
        if (isCfi) {
          failedDisplayTargetsRef.current.set(target, failureCount + 1);
          cfiDisplayStatsRef.current.failures += 1;
          const { attempts, failures } = cfiDisplayStatsRef.current;
          if (
            attempts >= CFI_DEGRADE_MIN_ATTEMPTS &&
            failures / attempts >= CFI_DEGRADE_FAILURE_RATIO
          ) {
            cfiDisplayStatsRef.current.degraded = true;
          }
        }
      }
      if (!displayed) {
        setLastJumpFeedback({
          approximate: true,
          message: "We couldn’t lock onto the exact passage, so we stayed near the current reading position.",
          resolution: "chapter-start",
          sectionRef: request.sectionRef,
        });
        return;
      }
      if (isStale()) {
        return;
      }

      if (request.targetLocator?.match_text) {
        const preferredHref = request.targetLocator.href ?? request.sectionLocator?.href ?? null;
        if (preferredHref && (!displayedTarget || isCfiTarget(displayedTarget))) {
          await displayWithTimeout(rendition, preferredHref);
          if (isStale()) {
            return;
          }
        }

        await waitForMatchTextAvailability(
          rendition,
          request.targetLocator.match_text,
          preferredHref,
        );
        if (isStale()) {
          return;
        }

        const mode = await locateMatchText(
          request.targetLocator.match_text,
          request.reactionType,
          preferredHref,
        );
        if (isStale()) {
          return;
        }
        if (mode === "exact") {
          setLastJumpFeedback({
            approximate: false,
            message: "Matched the quoted passage.",
            resolution: "exact",
            sectionRef: request.sectionRef,
          });
          return;
        }
        if (mode === "normalized") {
          setLastJumpFeedback({
            approximate: true,
            message: "Matched a nearby version of the quoted line.",
            resolution: "normalized",
            sectionRef: request.sectionRef,
          });
          return;
        }
        if (preferredHref) {
          await waitForMatchTextAvailability(
            rendition,
            request.targetLocator.match_text,
            preferredHref,
            12,
          );
          const retriedMode = await locateMatchText(
            request.targetLocator.match_text,
            request.reactionType,
            preferredHref,
          );
          if (isStale()) {
            return;
          }
          if (retriedMode === "exact") {
            setLastJumpFeedback({
              approximate: false,
              message: "Matched the quoted passage.",
              resolution: "exact",
              sectionRef: request.sectionRef,
            });
            return;
          }
          if (retriedMode === "normalized") {
            setLastJumpFeedback({
              approximate: true,
              message: "Matched a nearby version of the quoted line.",
              resolution: "normalized",
              sectionRef: request.sectionRef,
            });
            return;
          }
        }
      }

      if (request.targetLocator?.start_cfi) {
        await displayWithTimeout(rendition, request.targetLocator.start_cfi);
        if (isStale()) {
          return;
        }
        if (highlightCfi(request.targetLocator.start_cfi, request.reactionType)) {
          setLastJumpFeedback({
            approximate: true,
            message: "Opened the anchored source passage.",
            resolution: "nearby",
            sectionRef: request.sectionRef,
          });
          return;
        }
      }

      if (request.sectionLocator) {
        const locatedByParagraph = await locateSectionParagraph(request.sectionLocator, request.reactionType);
        if (isStale()) {
          return;
        }
        if (locatedByParagraph) {
          setLastJumpFeedback({
            approximate: true,
            message: "Opened the closest section context and highlighted nearby text.",
            resolution: "nearby",
            sectionRef: request.sectionRef,
          });
          return;
        }
      }

      if (request.sectionLocator?.start_cfi) {
        await displayWithTimeout(rendition, request.sectionLocator.start_cfi);
        if (isStale()) {
          return;
        }
      }

      if (request.sectionLocator?.start_cfi && highlightCfi(request.sectionLocator.start_cfi, request.reactionType)) {
        setLastJumpFeedback({
          approximate: true,
          message: "Opened the closest section context and highlighted nearby text.",
          resolution: "nearby",
          sectionRef: request.sectionRef,
        });
        return;
      }

      setLastJumpFeedback({
        approximate: true,
        message: "Precise passage unavailable, so we opened the start of this chapter.",
        resolution: "chapter-start",
        sectionRef: request.sectionRef,
      });
    } catch {
      setLastJumpFeedback({
        approximate: true,
        message: "We couldn’t reposition the reader, so it stayed near the current location.",
        resolution: "book-start",
        sectionRef: request.sectionRef,
      });
    } finally {
      window.setTimeout(() => {
        if (activeProgrammaticJumpRef.current === request.id && !isStale()) {
          activeProgrammaticJumpRef.current = null;
          activeProgrammaticSectionRefRef.current = null;
        }
      }, 140);
      if (!isStale()) {
        window.setTimeout(() => {
          if (!isStale()) {
            setIsJumping(false);
          }
        }, 120);
      }
      window.clearTimeout(spinnerDelay);
      window.clearTimeout(spinnerGuard);
    }
  }

  useEffect(() => {
    if (!jumpRequest || !readerReady) {
      return;
    }
    if (lastHandledJumpIdRef.current === jumpRequest.id) {
      return;
    }
    lastHandledJumpIdRef.current = jumpRequest.id;
    void jumpToRequest(jumpRequest);
  }, [jumpRequest, readerReady]);

  const { ref: paneRef, tier: readerTier } = useElementResponsiveTier<HTMLDivElement>();
  const readerCompact = readerTier === "compact" || readerTier === "narrow" || readerTier === "mobile";
  const readerShellClass = "bg-[var(--warm-100)]";
  const loadingOverlayClass = "bg-[var(--warm-50)]/86";
  const loadingTextClass = "text-[var(--warm-700)]";
  const errorOverlayClass = "bg-[var(--warm-100)]";
  const showReaderStatus = isJumping || Boolean(lastJumpFeedback?.approximate);

  return (
    <div ref={paneRef} className={`h-full flex flex-col ${readerShellClass}`} data-testid="source-reader-pane">
      <div className={`rc-reader-scroll-area ${readerCompact ? "rc-reader-scroll-area-compact" : ""} flex-1 relative overflow-hidden ${readerShellClass}`}>
        <div ref={hostRef} className={`absolute inset-0 ${readerShellClass}`} data-testid="source-reader-canvas" />

        {showReaderStatus ? (
          <div className="pointer-events-none absolute left-4 top-3 z-20 sm:left-5">
            <div
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 shadow-[0_1px_0_rgba(255,255,255,0.92),0_14px_26px_rgba(61,46,31,0.08)] ${
                isJumping
                  ? "border-[var(--warm-300)]/65 bg-white/94 text-[var(--warm-700)]"
                  : "border-[var(--amber-accent)]/22 bg-[var(--amber-bg)]/94 text-[var(--amber-accent)]"
              }`}
              style={{ fontSize: "0.73rem", fontWeight: 500, lineHeight: 1.45 }}
              data-testid="reader-jump-status"
            >
              {isJumping ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
              ) : (
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              )}
              <span>{isJumping ? "Positioning in source..." : lastJumpFeedback?.message}</span>
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <div className={`absolute inset-0 flex items-center justify-center ${loadingOverlayClass}`}>
            <p className={`inline-flex items-center gap-2 ${loadingTextClass}`} style={{ fontSize: "0.84rem" }}>
              <Loader2 className="w-4 h-4 animate-spin" />
              {copy("chapter.reader.loadingSource")}
            </p>
          </div>
        ) : null}

        {loadError ? (
          <div className={`absolute inset-0 flex items-center justify-center p-6 ${errorOverlayClass}`}>
            <div className="max-w-md text-center">
              <p className="text-[var(--destructive)] mb-2" style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                Reader unavailable
              </p>
              <p className="text-[var(--warm-700)]" style={{ fontSize: "0.84rem", lineHeight: 1.7 }}>
                {loadError}
              </p>
              <p className="mt-2 text-[var(--warm-500)]" style={{ fontSize: "0.78rem", lineHeight: 1.6 }}>
                Capability: CFI jump {READER_CAPABILITY.cfiJump ? "on" : "off"} · Href jump {READER_CAPABILITY.hrefJump ? "on" : "off"} ·
                Text highlight {READER_CAPABILITY.textHighlight ? "on" : "off"}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
