export type Tone = "standard" | "esl" | "phd";

export interface ToneOption {
  value: Tone;
  label: string;
}

export interface ParaphraseRequest {
  text: string;
  tone: Tone;
  protectedTerms: string[];
  humanizationStrength: number;
}
