const LANGUAGE_LABELS: Record<string, string> = { en: 'English', bn: 'বাংলা', banglish: 'Banglish', mixed: 'Mixed' }

export function languageLabel(code: string): string {
  return LANGUAGE_LABELS[code] ?? code
}
