export type AppLocale = "en" | "zh";

export const DEFAULT_APP_LOCALE: AppLocale = "en";

export const APP_LOCALE = DEFAULT_APP_LOCALE;

export type LocalizedText = Record<AppLocale, string>;

export function resolveLocalizedText(text: LocalizedText, locale: AppLocale = APP_LOCALE): string {
  return text[locale];
}

export function formatTemplate(template: string, params: Record<string, string | number | null | undefined> = {}): string {
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const value = params[key];
    return value == null ? "" : String(value);
  });
}
