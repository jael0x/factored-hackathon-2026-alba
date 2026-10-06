import { expect, type Page } from "@playwright/test";

import type { Messages } from "../../src/i18n/es";
import type { Locale } from "../oracle";

// DemoSearchPopover.tsx: the trigger's label is the same word in every language, so no dictionary holds it.
const DEMO_TRIGGER = "Demo";

export async function chooseLocale(page: Page, t: Messages, locale: Locale): Promise<void> {
  const option = page.getByRole("group", { name: t.language }).locator(`button[lang="${locale}"]`);
  await option.click();
  await expect(option).toHaveAttribute("aria-pressed", "true");
}

// The demo search fills the identity, and the code step reads the emailed code back from Mailpit (PLAN.md D25):
// the browser goes through the same code check as a person, and the test never sees the code.
export async function signInWithDemo(page: Page, t: Messages, queryLabel: string, query: string): Promise<void> {
  await page.getByRole("button", { name: DEMO_TRIGGER, exact: true }).click();
  await page.getByLabel(queryLabel).fill(query);
  const hits = page.getByRole("list", { name: t.demo.results }).getByRole("button");
  await expect(hits).toHaveCount(1);
  await hits.click();
  await page.getByRole("button", { name: t.login.sendCode }).click();
  await expect(page.getByText(t.code.demoFilled)).toBeVisible();
  await page.getByRole("button", { name: t.code.open, exact: true }).click();
}
