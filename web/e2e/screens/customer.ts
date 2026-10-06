import { expect, type Locator, type Page } from "@playwright/test";

import type { Messages } from "../../src/i18n/es";
import { LOGIN_PATH } from "../../src/routes";
import type { CertificateExpected, Flow, Locale, ProductKey } from "../oracle";
import { signInWithDemo } from "./login";

export async function signInAsCustomer(page: Page, t: Messages, flow: Flow): Promise<void> {
  await signInWithDemo(page, t, t.demo.customers.queryLabel, flow.customer.id);
  await expect(page.getByRole("heading", { level: 1, name: t.home.greeting(flow.customer.firstName) })).toBeVisible();
}

export function openCustomerLogin(page: Page): Promise<unknown> {
  return page.goto(LOGIN_PATH.customer);
}

export async function expectHomeBalances(page: Page, balances: string[]): Promise<void> {
  const cards = page.getByRole("article");
  await expect(cards).toHaveCount(balances.length);
  await expect(cards).toContainText(balances);
}

function productRow(page: Page, t: Messages, product: ProductKey): Locator {
  return page.getByRole("button", { name: t.products.askAbout[product] });
}

export async function startCase(page: Page, t: Messages, product: ProductKey): Promise<void> {
  await productRow(page, t, product).click();
  await page.getByRole("dialog").getByRole("button", { name: t.start.begin }).click();
  await expect(page).toHaveURL(/\/case\/[0-9a-f-]{36}$/);
}

export async function expectRowShowsResult(page: Page, t: Messages, product: ProductKey): Promise<void> {
  await expect(productRow(page, t, product)).toContainText(t.home.seeResult);
}

export async function expectSettledThread(page: Page, t: Messages, lines: number, locale: Locale): Promise<void> {
  const thread = page.getByRole("list", { name: t.chat.thread });
  await expect(page.getByText(t.chat.typing)).toHaveCount(0);
  await expect(thread.getByRole("listitem")).toHaveCount(lines);
  await expect(thread).toHaveAttribute("lang", locale);
}

export async function send(page: Page, t: Messages, text: string): Promise<void> {
  await page.getByLabel(t.chat.composer).fill(text);
  await page.getByRole("button", { name: t.chat.send, exact: true }).click();
}

export function certificate(page: Page, t: Messages, product: ProductKey): Locator {
  return page.getByRole("region", { name: t.products.askAbout[product] });
}

export async function expectNoCertificate(page: Page, t: Messages, product: ProductKey): Promise<void> {
  await expect(certificate(page, t, product)).toHaveCount(0);
}

export async function expectWithPerson(page: Page, t: Messages, withPerson: boolean): Promise<void> {
  await expect(page.getByText(t.chat.withPerson)).toHaveCount(withPerson ? 1 : 0);
}

export async function expectCertificate(
  page: Page,
  t: Messages,
  product: ProductKey,
  expected: CertificateExpected,
): Promise<void> {
  const card = certificate(page, t, product);
  await expect(card.getByText(t.certificate.tag[expected.outcome], { exact: true })).toBeVisible();
  const facts = card.getByRole("definition");
  const shown = [expected.income, expected.incomeUsd].filter((fact): fact is string => fact !== null);
  await expect(facts).toHaveCount(shown.length);
  await expect(facts).toContainText(shown);
  await expect(card.getByText(t.certificate.reviewed)).toHaveCount(expected.reviewed ? 1 : 0);
  await expect(card.getByRole("button", { name: t.certificate.appeal })).toHaveCount(expected.appealable ? 1 : 0);
}

export async function expectEnded(page: Page, t: Messages): Promise<void> {
  await expect(page.getByRole("link", { name: t.chat.backHome })).toBeVisible();
  await expect(page.getByLabel(t.chat.composer)).toHaveCount(0);
}
