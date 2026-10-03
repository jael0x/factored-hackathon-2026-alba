import type { components } from "./api/schema";

type Product = components["schemas"]["Product"];
type ProductKey = components["schemas"]["ProductKey"];

export type Gender = "feminine" | "masculine";

export type ProductName = { label: string; gender: Gender };

// The product_type and product_status values ARCHITECTURE.md "Data" lists. Closed never reaches the screen.
const PRODUCT_TYPES = [
  "Cuenta Ahorro",
  "Cuenta Corriente",
  "Tarjeta Crédito",
  "Tarjeta Débito",
  "Préstamo Personal",
  "Préstamo Hipotecario",
  "Inversión",
  "Seguro",
] as const;

const PRODUCT_STATUSES = ["Active", "Blocked", "Suspended"] as const;

type ProductType = (typeof PRODUCT_TYPES)[number];
type ProductStatus = (typeof PRODUCT_STATUSES)[number];

// Gender belongs to each language: "Tarjeta" is feminine in Spanish, "Cartão" masculine in Portuguese.
export type ProductCopy = {
  types: Record<ProductType, ProductName>;
  statuses: Record<ProductStatus, Record<Gender, string>>;
  maskedEnding: Record<Gender, string>;
  askAbout: Record<ProductKey, string>;
};

export const ASK_ABOUT: ProductKey[] = ["credit_card", "personal_loan"];

export type ProductLabels = { name: string; status: string; maskedEnding: string };

export function productLabels(product: Product, copy: ProductCopy): ProductLabels {
  const known = isOneOf(PRODUCT_TYPES, product.product_type) ? copy.types[product.product_type] : undefined;
  const gender = known?.gender ?? "masculine";
  return {
    name: known?.label ?? product.product_type,
    status: isOneOf(PRODUCT_STATUSES, product.product_status)
      ? copy.statuses[product.product_status][gender]
      : product.product_status,
    maskedEnding: copy.maskedEnding[gender],
  };
}

function isOneOf<Value extends string>(values: readonly Value[], value: string): value is Value {
  return values.some((known) => known === value);
}
