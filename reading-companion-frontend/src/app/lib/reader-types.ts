import type { ReactionCard, ReactionTargetLocator, SectionCard } from "./api-types";
import type { ReactionId, ReactionType } from "./contract";

export type ReaderTheme = "paper" | "night";
export type ReaderPanelMode = "notes" | "book";
export type ReaderJumpSource = "initial" | "deep-link" | "note-click" | "toolbar" | "section-click" | "section-query";
export type ReaderJumpResolution = "exact" | "normalized" | "nearby" | "chapter-start" | "book-start";

export interface ReaderJumpRequest {
  id: number;
  source: ReaderJumpSource;
  reactionId: ReactionId | null;
  reactionType: ReactionType | null;
  sectionRef: string | null;
  targetLocator: ReactionTargetLocator | null;
  sectionLocator: SectionCard["locator"] | null;
}

export interface ReaderLocation {
  cfi: string | null;
  href: string | null;
  progress: number | null;
  sectionRef: string | null;
}

export interface ReaderSyncState {
  followNotes: boolean;
  currentSectionRef: string | null;
  lastJumpId: number | null;
}

export interface ReaderCapability {
  cfiJump: boolean;
  hrefJump: boolean;
  textHighlight: boolean;
}

export interface ReaderLocationUpdate {
  location: ReaderLocation;
  programmatic: boolean;
}

export interface ReaderJumpFeedback {
  approximate: boolean;
  message: string;
  resolution: ReaderJumpResolution;
  sectionRef: string | null;
}

export interface ReactionSelection {
  reaction: ReactionCard;
  section: SectionCard;
}

export function normalizeReaderText(value: string): string {
  let output = "";
  let previousWasWhitespace = false;

  for (const character of value) {
    const normalized = normalizeReaderCharacter(character);
    if (normalized === " ") {
      if (previousWasWhitespace) {
        continue;
      }
      output += " ";
      previousWasWhitespace = true;
      continue;
    }
    output += normalized;
    previousWasWhitespace = false;
  }

  return output.trim();
}

export function buildReaderJumpRequest(
  selection: ReactionSelection,
  source: ReaderJumpSource,
  requestId: number,
): ReaderJumpRequest {
  return {
    id: requestId,
    source,
    reactionId: selection.reaction.reaction_id,
    reactionType: selection.reaction.type,
    sectionRef: selection.section.section_ref,
    targetLocator: selection.reaction.target_locator ?? null,
    sectionLocator: selection.section.locator ?? null,
  };
}

export function buildSectionJumpRequest(
  section: SectionCard,
  source: ReaderJumpSource,
  requestId: number,
): ReaderJumpRequest {
  return {
    id: requestId,
    source,
    reactionId: null,
    reactionType: null,
    sectionRef: section.section_ref,
    targetLocator: null,
    sectionLocator: section.locator ?? null,
  };
}

export function findSelectionByReactionId(
  sections: SectionCard[],
  reactionId: ReactionId | null,
): ReactionSelection | null {
  if (reactionId == null) {
    return null;
  }

  for (const section of sections) {
    const reaction = section.reactions.find((item) => item.reaction_id === reactionId);
    if (reaction) {
      return { reaction, section };
    }
  }

  return null;
}

export function firstReadableSection(sections: SectionCard[]): SectionCard | null {
  return sections.find((section) => section.locator?.href) ?? sections[0] ?? null;
}

export function reactionPreview(content: string, maxLength = 172): string {
  if (content.length <= maxLength) {
    return content;
  }
  return `${content.slice(0, maxLength).trimEnd()}...`;
}

export function normalizeReaderCharacter(character: string): string {
  switch (character) {
    case "\u00ad":
    case "\u200b":
    case "\u200c":
    case "\u200d":
    case "\u2060":
    case "\ufeff":
      return "";
    default:
      break;
  }

  if (/\s/u.test(character)) {
    return " ";
  }

  switch (character) {
    case "\u2018":
    case "\u2019":
    case "\u2032":
      return "'";
    case "\u201C":
    case "\u201D":
    case "\u2033":
      return '"';
    case "\u2013":
    case "\u2014":
    case "\u2212":
      return "-";
    default:
      return character.toLowerCase();
  }
}
