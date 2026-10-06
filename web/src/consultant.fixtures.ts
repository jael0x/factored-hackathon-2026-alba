import type { components } from "./api/schema";

type ConsultantCase = components["schemas"]["ConsultantCase"];

export const ALICIA: ConsultantCase = {
  process_id: "8f1c2a4e-1111-4111-8111-111111111111",
  state: "human_active",
  customer_id: "CLI-440CO5FZIY6A",
  first_name: "Alicia Mariana",
  last_name: "Parra Álvarez",
  product: "credit_card",
  credit_score: 615,
  income_local: 4707334.28,
  income_currency: "COP",
  income_usd: 1167.41890144,
  deciding_rule: "R05",
  policy_version: "alba-credit-v1",
  outcome: "REFER",
  reason_code: "policy_refer",
  locale: "pt",
  closable: true,
  messages: [
    { id: "a1", author: "customer", body: "Quero um cartão de crédito", event_id: "e1" },
    { id: "a2", author: "template", body: "Uma pessoa do banco vai revisar seu pedido.", event_id: "e2" },
    { id: "a3", author: "customer", body: "já revisaram meu caso?", event_id: "e3" },
  ],
};

export const JULIANA: ConsultantCase = {
  ...ALICIA,
  customer_id: "CLI-MD60UR8PNJDI",
  first_name: "Juliana",
  last_name: "Castro Gómez",
  credit_score: 714,
  income_local: null,
  income_currency: "MXN",
  income_usd: null,
  deciding_rule: "R06",
  outcome: "NEEDS_INFO",
  reason_code: "customer_requested_human",
  locale: "es",
  closable: false,
};

export const BEFORE_THE_POLICY: ConsultantCase = {
  ...ALICIA,
  product: null,
  credit_score: null,
  income_local: null,
  income_currency: null,
  income_usd: null,
  deciding_rule: null,
  policy_version: null,
  outcome: null,
  reason_code: "tool_failed",
  closable: false,
};
