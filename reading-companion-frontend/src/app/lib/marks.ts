import type { MarkType } from "./contract";
import { term } from "../config/product-lexicon";

type MarkMeta = {
  label: string;
};

const markMeta: Record<MarkType, MarkMeta> = {
  resonance: { label: term("mark.resonance") },
  blindspot: { label: term("mark.blindspot") },
  bookmark: { label: term("mark.bookmark") },
};

export function markLabel(type: MarkType | string): string {
  return markMeta[type as MarkType]?.label ?? type;
}
