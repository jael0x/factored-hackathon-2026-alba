import type { components } from "./api/schema";

type CaseTrace = components["schemas"]["CaseTrace"];
type TraceEvent = components["schemas"]["TraceEvent"];
type EventName = components["schemas"]["EventName"];

export type EventOf<N extends EventName> = Extract<TraceEvent, { event_name: N }>;

const PROCESS = "8f1c2a4e-1111-4111-8111-111111111111";
const AT = "2026-10-05T14:03:27.512Z";
const AS_OF = "2026-06-17";

const MESSAGE = "e0000001-0000-4000-8000-000000000001";
const STARTED = "e0000002-0000-4000-8000-000000000002";
const ANALYSIS = "e0000003-0000-4000-8000-000000000003";
const MOVED = "e0000004-0000-4000-8000-000000000004";
const TAKEN = "e0000005-0000-4000-8000-000000000005";
const NOTICE = "e0000006-0000-4000-8000-000000000006";

const base = { created_at: AT, actor: "system", process_id: PROCESS, process_state: "ai_active" } as const;

export const ALICIA_MESSAGE: EventOf<"conversation.message_received"> = {
  ...base,
  id: MESSAGE,
  event_name: "conversation.message_received",
  actor: "customer",
  process_id: null,
  caused_by_event_id: null,
  text: "Quiero una tarjeta de crédito",
  client_message_id: "c0000001-0000-4000-8000-000000000001",
  locale: "es",
  product: "credit_card",
};

export const ALICIA_STARTED: EventOf<"process.started"> = {
  ...base,
  id: STARTED,
  event_name: "process.started",
  caused_by_event_id: MESSAGE,
  process_key: "credit_prequalification",
  customer_id: "CLI-440CO5FZIY6A",
  locale: "es",
  product: "credit_card",
};

export const ALICIA_ANALYSIS: EventOf<"analysis.completed"> = {
  ...base,
  id: ANALYSIS,
  event_name: "analysis.completed",
  created_at: "2026-10-05T14:03:27.640Z",
  caused_by_event_id: STARTED,
  policy_version: "alba-credit-v1",
  product: "credit_card",
  outcome: "REFER",
  deciding_rule: "R05",
  rule_trace: [
    { rule_id: "R01", input: { customer_status: "Active" }, result: "passed" },
    { rule_id: "R02", input: { max_days_past_due: 0 }, result: "passed" },
    { rule_id: "R03", input: { max_days_past_due: 0 }, result: "passed" },
    { rule_id: "R09", input: { holds_product: false }, result: "passed" },
    { rule_id: "R04", input: { credit_score: 615 }, result: "passed" },
    { rule_id: "R06", input: { income_local: 4707334.28, declared_income: null, income_currency: "COP" }, result: "passed" },
    { rule_id: "R05", input: { credit_score: 615 }, result: "REFER" },
  ],
  facts: [
    { name: "credit_score", value: 615, source: "customer_credit_profile.credit_score", as_of: AS_OF },
    { name: "income_local", value: 4707334.28, source: "customer_credit_profile.income_local", as_of: AS_OF },
    { name: "income_currency", value: "COP", source: "customer_credit_profile.income_currency", as_of: AS_OF },
    { name: "income_usd", value: 1167.41890144, source: "customer_credit_profile.income_usd", as_of: AS_OF },
  ],
  locale: "es",
};

const referred: TraceEvent[] = [
  ALICIA_MESSAGE,
  ALICIA_STARTED,
  ALICIA_ANALYSIS,
  {
    ...base,
    id: MOVED,
    event_name: "process.state_changed",
    created_at: "2026-10-05T14:03:27.701Z",
    process_state: "human_active",
    caused_by_event_id: ANALYSIS,
    from_state: "ai_active",
    to_state: "human_active",
    end_reason: null,
  },
  {
    ...base,
    id: TAKEN,
    event_name: "conversation.thread_taken",
    created_at: "2026-10-05T14:03:27.701Z",
    process_state: "human_active",
    caused_by_event_id: ANALYSIS,
    reason_code: "policy_refer",
    from_state: "ai_active",
    to_state: "human_active",
  },
  {
    ...base,
    id: NOTICE,
    event_name: "conversation.template_sent",
    created_at: "2026-10-05T14:03:27.733Z",
    process_state: "human_active",
    caused_by_event_id: TAKEN,
    locale: "es",
    template_id: "refer_notice",
    body:
      "Tu historial crediticio necesita una revisión adicional. Una persona del banco va a revisar tu solicitud de una " +
      "tarjeta de crédito. Te avisaremos por aquí cuando tenga una respuesta.",
  },
];

// specs/09: Alicia's credit card request, referred by R05.
export const ALICIA_TRACE: CaseTrace = { process_id: PROCESS, events: referred };

const later = { ...base, created_at: "2026-10-05T14:20:00.000Z", caused_by_event_id: ANALYSIS } as const;

// One recorded event of every name: a name added to EventName fails tsc here until it has an example.
export const EVERY_EVENT: { [N in EventName]: EventOf<N> } = {
  "conversation.message_received": {
    ...later,
    id: "e1000001-0000-4000-8000-000000000001",
    event_name: "conversation.message_received",
    actor: "customer",
    caused_by_event_id: null,
    text: "gano 45000 pesos",
    client_message_id: "c1000001-0000-4000-8000-000000000001",
    locale: "es",
    product: null,
  },
  "process.started": {
    ...later,
    id: "e1000002-0000-4000-8000-000000000002",
    event_name: "process.started",
    process_key: "credit_prequalification",
    customer_id: "CLI-MD60UR8PNJDI",
    locale: "es",
    product: "personal_loan",
  },
  "conversation.turn_classified": {
    ...later,
    id: "e1000003-0000-4000-8000-000000000003",
    event_name: "conversation.turn_classified",
    intent: "provide_income",
    product: "personal_loan",
    language: "es",
    locale: "es",
    declared_income_amount: 45000,
    declared_income_currency: "MXN",
    reply_text: "Gracias.",
    reply_ok: true,
    reason_code: null,
    product_asked_count: 0,
    income_requested: true,
    open_case_product: null,
  },
  "conversation.template_sent": {
    ...later,
    id: "e1000004-0000-4000-8000-000000000004",
    event_name: "conversation.template_sent",
    locale: "es",
    template_id: "needs_income",
    body: "¿Cuál es tu ingreso mensual?",
  },
  "conversation.consultant_closed": {
    ...later,
    id: "e1000005-0000-4000-8000-000000000005",
    event_name: "conversation.consultant_closed",
    actor: "consultant",
    process_state: "human_active",
    outcome: "PREQUALIFIED",
    consultant_id: "AGT-00042",
    locale: "pt",
  },
  "conversation.thread_taken": {
    ...later,
    id: "e1000006-0000-4000-8000-000000000006",
    event_name: "conversation.thread_taken",
    process_state: "human_active",
    reason_code: "customer_requested_human",
    from_state: "ended",
    to_state: "human_active",
  },
  "analysis.completed": {
    ...later,
    id: "e1000007-0000-4000-8000-000000000007",
    event_name: "analysis.completed",
    policy_version: "alba-credit-v1",
    product: "personal_loan",
    outcome: "NEEDS_INFO",
    deciding_rule: "R06",
    rule_trace: [{ rule_id: "R06", input: { income_local: null, declared_income: null, income_currency: "MXN" }, result: "NEEDS_INFO" }],
    facts: [],
    locale: "es",
  },
  "prequalification.decided": {
    ...later,
    id: "e1000008-0000-4000-8000-000000000008",
    event_name: "prequalification.decided",
    locale: "es",
    outcome: "NOT_PREQUALIFIED",
    body: "No precalificas para un préstamo personal (simulado).",
    decided_by: "policy",
  },
  "process.state_changed": {
    ...later,
    id: "e1000009-0000-4000-8000-000000000009",
    event_name: "process.state_changed",
    process_state: "ended",
    from_state: "ai_active",
    to_state: "ended",
    end_reason: "not_prequalified",
  },
  "process.ended": {
    ...later,
    id: "e1000010-0000-4000-8000-000000000010",
    event_name: "process.ended",
    process_state: "ended",
    end_reason: "not_prequalified",
    policy_version: "alba-credit-v1",
  },
  "conversation.appeal_requested": {
    ...later,
    id: "e1000011-0000-4000-8000-000000000011",
    event_name: "conversation.appeal_requested",
    actor: "customer",
    process_state: "ended",
    locale: "es",
    product: "personal_loan",
  },
};
