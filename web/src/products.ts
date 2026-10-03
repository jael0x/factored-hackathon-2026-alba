import type { components } from "./api/schema";

type Product = components["schemas"]["Product"];
type ProductKey = components["schemas"]["ProductKey"];

type Gender = "feminine" | "masculine";

type ProductName = { label: string; gender: Gender };

const PRODUCT_TYPES: ReadonlyMap<string, ProductName> = new Map([
  ["Cuenta Ahorro", { label: "Cuenta de ahorro", gender: "feminine" }],
  ["Cuenta Corriente", { label: "Cuenta corriente", gender: "feminine" }],
  ["Tarjeta Crédito", { label: "Tarjeta de crédito", gender: "feminine" }],
  ["Tarjeta Débito", { label: "Tarjeta de débito", gender: "feminine" }],
  ["Préstamo Personal", { label: "Préstamo personal", gender: "masculine" }],
  ["Préstamo Hipotecario", { label: "Préstamo hipotecario", gender: "masculine" }],
  ["Inversión", { label: "Inversión", gender: "feminine" }],
  ["Seguro", { label: "Seguro", gender: "masculine" }],
]);

const PRODUCT_STATUSES: ReadonlyMap<string, Record<Gender, string>> = new Map([
  ["Active", { feminine: "Activa", masculine: "Activo" }],
  ["Blocked", { feminine: "Bloqueada", masculine: "Bloqueado" }],
  ["Suspended", { feminine: "Suspendida", masculine: "Suspendido" }],
]);

const MASKED_ENDING: Record<Gender, string> = { feminine: "terminada en", masculine: "terminado en" };

export const ASK_ABOUT: { key: ProductKey; label: string }[] = [
  { key: "credit_card", label: "Tarjeta de crédito" },
  { key: "personal_loan", label: "Préstamo personal" },
];

export type ProductLabels = { name: string; status: string; maskedEnding: string };

export function productLabels(product: Product): ProductLabels {
  const known = PRODUCT_TYPES.get(product.product_type);
  const gender = known?.gender ?? "masculine";
  return {
    name: known?.label ?? product.product_type,
    status: PRODUCT_STATUSES.get(product.product_status)?.[gender] ?? product.product_status,
    maskedEnding: MASKED_ENDING[gender],
  };
}
