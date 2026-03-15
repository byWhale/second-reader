import type { ReactionType } from "./contract";
import { term } from "../config/product-lexicon";

type ReactionMeta = {
  label: string;
  description: string;
  accentClass: string;
  surfaceClass: string;
  surfaceHex: string;
};

export const reactionMeta: Record<ReactionType, ReactionMeta> = {
  highlight: {
    label: term("reaction.highlight"),
    description: "Passages the agent thinks are worth carrying forward.",
    accentClass: "text-[var(--amber-accent)]",
    surfaceClass: "bg-[var(--highlight-color)]",
    surfaceHex: "#FFF3CD",
  },
  association: {
    label: term("reaction.association"),
    description: "Connections to adjacent ideas or outside patterns.",
    accentClass: "text-[var(--warm-700)]",
    surfaceClass: "bg-[var(--association-color)]",
    surfaceHex: "#F0E8FF",
  },
  curious: {
    label: term("reaction.curious"),
    description: "Questions that push into missing evidence or context.",
    accentClass: "text-emerald-700",
    surfaceClass: "bg-[var(--curious-color)]",
    surfaceHex: "#E8FFE8",
  },
  discern: {
    label: term("reaction.discern"),
    description: "Sharper distinctions or tensions inside the claim.",
    accentClass: "text-orange-700",
    surfaceClass: "bg-[var(--discern-color)]",
    surfaceHex: "#FFE8E0",
  },
  retrospect: {
    label: term("reaction.retrospect"),
    description: "Callbacks to earlier threads in the same book.",
    accentClass: "text-blue-700",
    surfaceClass: "bg-[var(--retrospect-color)]",
    surfaceHex: "#E8F0FF",
  },
};

export function reactionLabel(type: ReactionType | string): string {
  return reactionMeta[type]?.label ?? type;
}
