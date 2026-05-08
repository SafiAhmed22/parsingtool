export function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

export function countChars(text: string): number {
  return text.length;
}

export function getSliderBackground(
  value: number,
  min: number,
  max: number
): string {
  const pct = ((value - min) / (max - min)) * 100;
  return `linear-gradient(to right, #3d6b5e ${pct}%, #d4d9de ${pct}%)`;
}

export function getStrengthLabel(value: number): string {
  if (value <= 3) return "Low";
  if (value <= 6) return "Medium";
  return "High";
}
