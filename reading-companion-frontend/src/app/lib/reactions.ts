export const reactionMeta: Record<string, { label: string; description: string; accentClass: string; surfaceClass: string }> = {
  highlight: {
    label: "Highlight",
    description: "Passages the agent thinks are worth carrying forward.",
    accentClass: "text-[var(--amber-accent)]",
    surfaceClass: "bg-[var(--highlight-color)]",
  },
  association: {
    label: "Association",
    description: "Connections to adjacent ideas or outside patterns.",
    accentClass: "text-[var(--warm-700)]",
    surfaceClass: "bg-[var(--association-color)]",
  },
  curious: {
    label: "Curious",
    description: "Questions that push into missing evidence or context.",
    accentClass: "text-emerald-700",
    surfaceClass: "bg-[var(--curious-color)]",
  },
  discern: {
    label: "Discern",
    description: "Sharper distinctions or tensions inside the claim.",
    accentClass: "text-orange-700",
    surfaceClass: "bg-[var(--discern-color)]",
  },
  retrospect: {
    label: "Retrospect",
    description: "Callbacks to earlier threads in the same book.",
    accentClass: "text-blue-700",
    surfaceClass: "bg-[var(--retrospect-color)]",
  },
};

export function reactionLabel(type: string): string {
  return reactionMeta[type]?.label ?? type;
}
