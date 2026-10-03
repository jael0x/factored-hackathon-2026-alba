import { LOCALE_NAMES, LOCALES, setLocale, useLocale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";

export function LanguageSwitch() {
  const locale = useLocale();
  const t = useMessages();
  return (
    <div className="lang-switch glass" role="group" aria-label={t.language}>
      {LOCALES.map((option) => (
        <button
          key={option}
          type="button"
          lang={option}
          aria-pressed={option === locale}
          onClick={() => setLocale(option)}
        >
          <span aria-hidden="true">{option.toUpperCase()}</span>
          <span className="sr-only">{LOCALE_NAMES[option]}</span>
        </button>
      ))}
    </div>
  );
}
