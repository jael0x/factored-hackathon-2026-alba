import { expect, type Page } from "@playwright/test";

import type { Messages } from "../../src/i18n/es";
import { HOME_PATH, LOGIN_PATH } from "../../src/routes";
import type { CloseOutcome, Locale, Person } from "../oracle";
import { signInWithDemo } from "./login";

export async function signInAsConsultant(page: Page, t: Messages, consultant: Person): Promise<void> {
  await page.goto(LOGIN_PATH.consultant);
  await signInWithDemo(page, t, t.demo.consultants.queryLabel, consultant.id);
  await expect(page).toHaveURL(new RegExp(`${HOME_PATH.consultant}$`));
  await expectQueueLoaded(page, t);
}

// The layout and the queue each show a loading status until their fetch settles; none is left once both are read.
async function expectQueueLoaded(page: Page, t: Messages): Promise<void> {
  await expect(page.getByRole("heading", { level: 1, name: t.consultant.queue })).toBeVisible();
  await expect(page.getByRole("status")).toHaveCount(0);
}

export async function expectInQueue(page: Page, customer: Person, inQueue: boolean): Promise<void> {
  await expect(page.getByRole("link", { name: customer.name })).toHaveCount(inQueue ? 1 : 0);
}

export async function openQueuedCase(page: Page, customer: Person): Promise<void> {
  await page.getByRole("link", { name: customer.name }).click();
  await expect(page.getByRole("heading", { level: 1, name: customer.name })).toBeVisible();
}

export async function expectPacket(page: Page, t: Messages, rows: string[]): Promise<void> {
  await expect(page.getByRole("article", { name: t.consultant.packet }).getByRole("definition")).toHaveText(rows);
}

export async function expectReadOnlyThread(page: Page, t: Messages, lines: number, locale: Locale): Promise<void> {
  const conversation = page.getByRole("region", { name: t.consultant.conversation });
  await expect(conversation.getByRole("listitem")).toHaveCount(lines);
  await expect(conversation.getByRole("list")).toHaveAttribute("lang", locale);
  await expect(conversation.getByRole("textbox")).toHaveCount(0);
}

// AnalysisRecord.tsx: each evaluated rule is a row of its list, its id first.
export async function expectTraceRules(page: Page, t: Messages, rules: readonly string[]): Promise<void> {
  await page.getByRole("link", { name: t.trace.title }).click();
  await expect(page.getByRole("heading", { level: 1, name: t.trace.title })).toBeVisible();
  await expect(page.locator("ol.trace-rules > li > span:first-child")).toHaveText([...rules]);
  await page
    .getByRole("navigation", { name: t.consultant.crumbs })
    .getByRole("link", { name: t.trace.caseCrumb, exact: true })
    .click();
}

export async function closeCase(page: Page, t: Messages, customer: Person, outcome: CloseOutcome): Promise<void> {
  await page.getByRole("button", { name: t.consultant.close[outcome], exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: t.consultant.confirm }).click();
  await expectQueueLoaded(page, t);
  await expectInQueue(page, customer, false);
}
