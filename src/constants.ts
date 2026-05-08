import type { ToneOption } from "./types";

export const TONE_OPTIONS: ToneOption[] = [
  { value: "phd", label: "Ph.D. Level" },
  { value: "standard", label: "Standard Academic" },
  { value: "esl", label: "ESL / Simple Academic" },
];

export const MIN_HUMANIZATION = 1;
export const MAX_HUMANIZATION = 10;
export const DEFAULT_HUMANIZATION = 7;
