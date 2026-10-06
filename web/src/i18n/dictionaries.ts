import { es, type Messages } from "./es";
import type { Locale } from "./locale";
import { pt } from "./pt";

export const MESSAGES: Record<Locale, Messages> = { es, pt };
