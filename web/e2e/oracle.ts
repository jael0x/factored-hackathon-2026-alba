import { readFileSync } from "node:fs";

import type { components } from "../src/api/schema";
import { fullName } from "../src/format";

type Schemas = components["schemas"];
export type CloseOutcome = Schemas["CloseOutcome"];
export type ProductKey = Schemas["ProductKey"];
export type Locale = Schemas["Locale"];

const FIXTURES = new URL("../../api/fixtures/", import.meta.url);

type Fields = Map<string, unknown>;

function fieldsOf(value: unknown, where: string): Fields {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`${where} is not an object`);
  }
  return new Map<string, unknown>(Object.entries(value));
}

function textAt(fields: Fields, key: string, where: string): string {
  const value = fields.get(key);
  if (typeof value !== "string" || value === "") {
    throw new TypeError(`${where}.${key} is not a non-empty string`);
  }
  return value;
}

function listAt(fields: Fields, key: string, where: string): unknown[] {
  const value = fields.get(key);
  if (!Array.isArray(value)) {
    throw new TypeError(`${where}.${key} is not a list`);
  }
  return value;
}

function readFixture(path: string): Fields {
  return fieldsOf(JSON.parse(readFileSync(new URL(path, FIXTURES), "utf8")), path);
}

export type Person = { id: string; firstName: string; name: string };

function personOf(fields: Fields, idKey: string, where: string): Person {
  const person = { first_name: textAt(fields, "first_name", where), last_name: textAt(fields, "last_name", where) };
  return { id: textAt(fields, idKey, where), firstName: person.first_name, name: fullName(person) };
}

const ORACLE = readFixture("oracle_customers.json");

function oracleCustomer(customerId: string): Person {
  const found = listAt(ORACLE, "customers", "oracle_customers.json")
    .map((entry, index) => personOf(fieldsOf(entry, `customers[${index}]`), "customer_id", `customers[${index}]`))
    .filter((person) => person.id === customerId);
  if (found.length !== 1) {
    throw new Error(`oracle_customers.json holds ${found.length} customers with id ${customerId}`);
  }
  return found[0];
}

export const CESAR = personOf(fieldsOf(ORACLE.get("consultant"), "consultant"), "employee_code", "consultant");

export const JULIANA_INCOME = textAt(readFixture("turns/es-gano-45000-pesos.json"), "text", "es-gano-45000-pesos");

// A consultant's certificate shows no income: its decision names no analysis (api/domain/process/case.py).
export type CertificateExpected = {
  outcome: CloseOutcome;
  income: string | null;
  incomeUsd: string | null;
  reviewed: boolean;
  appealable: boolean;
};

export type Flow = {
  customer: Person;
  locale: Locale;
  product: ProductKey;
  homeBalances: string[];
  certificate: CertificateExpected;
};

// ARCHITECTURE.md "What gets built", "Oracle fixtures", and the four flows, as the screens show them. Written here,
// not read from the fixture, so a fixture edit that moves an outcome turns the flows red instead of following it.
export const JUAN: Flow = {
  customer: oracleCustomer("CLI-9EDEKZ8OUNUR"),
  locale: "es",
  product: "credit_card",
  homeBalances: ["1,559.57 USD", "109,159.57 USD"],
  certificate: {
    outcome: "PREQUALIFIED",
    income: "306,753.45 MXN",
    incomeUsd: "17,988.33 USD",
    reviewed: false,
    appealable: false,
  },
};

export const JULIANA: Flow = {
  customer: oracleCustomer("CLI-MD60UR8PNJDI"),
  locale: "es",
  product: "credit_card",
  homeBalances: ["2,528.58 USD"],
  certificate: { outcome: "PREQUALIFIED", income: "45,000.00 MXN", incomeUsd: null, reviewed: false, appealable: false },
};

export const ALICIA: Flow = {
  customer: oracleCustomer("CLI-440CO5FZIY6A"),
  locale: "pt",
  product: "credit_card",
  homeBalances: ["422,017.11 COP", "3,910,126.60 COP", "13,192,324.57 COP", "0.00 USD"],
  certificate: { outcome: "PREQUALIFIED", income: null, incomeUsd: null, reviewed: true, appealable: false },
};

export const ALICIA_INCOME = "4,707,334.28 COP";

export const ALICIA_PACKET = {
  score: "615",
  rule: "R05",
  policy: "alba-credit-v1",
  outcome: "REFER",
  reason: "policy_refer",
  rulesEvaluated: ["R01", "R02", "R03", "R09", "R04", "R06", "R05"],
} as const satisfies {
  rule: Schemas["RuleId"];
  policy: Schemas["PolicyVersion"];
  outcome: Schemas["Outcome"];
  reason: Schemas["ReasonCode"];
  rulesEvaluated: readonly Schemas["RuleId"][];
  score: string;
};

export const MARIANA: Flow = {
  customer: oracleCustomer("CLI-ZGOY1V6ZC46J"),
  locale: "es",
  product: "credit_card",
  homeBalances: ["111,079.25 ARS", "622,677.69 ARS", "1,594,012.45 ARS", "235,969.92 ARS"],
  certificate: {
    outcome: "NOT_PREQUALIFIED",
    income: "801,583.70 ARS",
    incomeUsd: "2,302.95 USD",
    reviewed: false,
    appealable: true,
  },
};
