import { MESSAGES } from "./dictionaries";
import type { Messages } from "./es";
import { useLocale } from "./locale";

export function useMessages(): Messages {
  return MESSAGES[useLocale()];
}
