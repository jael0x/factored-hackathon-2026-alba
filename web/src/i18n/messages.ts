import { es, type Messages } from "./es";
import { useLocale, type Locale } from "./locale";
import { pt } from "./pt";

const MESSAGES: Record<Locale, Messages> = { es, pt };

export function useMessages(): Messages {
  return MESSAGES[useLocale()];
}
