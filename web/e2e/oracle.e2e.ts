import { test as base, type Page } from "@playwright/test";

import { MESSAGES } from "../src/i18n/dictionaries";
import { ALICIA, ALICIA_INCOME, ALICIA_PACKET, CESAR, JUAN, JULIANA, JULIANA_INCOME, MARIANA, type Flow } from "./oracle";
import {
  closeCase,
  expectInQueue,
  expectPacket,
  expectReadOnlyThread,
  expectTraceRules,
  openQueuedCase,
  signInAsConsultant,
} from "./screens/consultant";
import {
  expectCertificate,
  expectEnded,
  expectHomeBalances,
  expectNoCertificate,
  expectRowShowsResult,
  expectSettledThread,
  expectWithPerson,
  openCustomerLogin,
  send,
  signInAsCustomer,
  startCase,
} from "./screens/customer";
import { chooseLocale } from "./screens/login";

const es = MESSAGES.es;

// The consultant works in a browser of their own: one tab holds one session (ARCHITECTURE.md "Auth and screens").
const test = base.extend<{ consultantPage: Page }>({
  consultantPage: async ({ browser, baseURL, locale, timezoneId, viewport }, use) => {
    const context = await browser.newContext({ baseURL, locale, timezoneId, viewport });
    await use(await context.newPage());
    await context.close();
  },
});

async function startFromHome(page: Page, flow: Flow): Promise<void> {
  const t = MESSAGES[flow.locale];
  await openCustomerLogin(page);
  await chooseLocale(page, es, flow.locale);
  await signInAsCustomer(page, t, flow);
  await expectHomeBalances(page, flow.homeBalances);
  await startCase(page, t, flow.product);
}

test("Juan pre-qualifies by R05 and his home row then shows the result (02, 05)", async ({ page }) => {
  const t = MESSAGES[JUAN.locale];
  await startFromHome(page, JUAN);
  await expectCertificate(page, t, JUAN.product, JUAN.certificate);
  await expectSettledThread(page, t, 2, JUAN.locale);
  await expectWithPerson(page, t, false);
  await expectEnded(page, t);
  await page.getByRole("link", { name: t.chat.backHome }).click();
  await expectRowShowsResult(page, t, JUAN.product);
});

test("Juliana is asked for her income, then pre-qualifies on the amount she types (05, 06)", async ({ page }) => {
  const t = MESSAGES[JULIANA.locale];
  await startFromHome(page, JULIANA);
  await expectSettledThread(page, t, 2, JULIANA.locale);
  await expectNoCertificate(page, t, JULIANA.product);
  await expectWithPerson(page, t, false);
  await send(page, t, JULIANA_INCOME);
  await expectCertificate(page, t, JULIANA.product, JULIANA.certificate);
  await expectSettledThread(page, t, 4, JULIANA.locale);
  await expectEnded(page, t);
});

test("Alicia, in Portuguese, is referred; César closes her case in Spanish (07, 08, 09, 12)", async ({
  page,
  consultantPage,
}) => {
  const t = MESSAGES[ALICIA.locale];
  await startFromHome(page, ALICIA);
  await expectSettledThread(page, t, 2, ALICIA.locale);
  await expectNoCertificate(page, t, ALICIA.product);
  await expectWithPerson(page, t, true);

  await signInAsConsultant(consultantPage, es, CESAR);
  await expectInQueue(consultantPage, ALICIA.customer, true);
  await openQueuedCase(consultantPage, ALICIA.customer);
  await expectReadOnlyThread(consultantPage, es, 2, ALICIA.locale);
  await expectPacket(consultantPage, es, [
    es.products.askAbout[ALICIA.product],
    ALICIA_PACKET.score,
    ALICIA_INCOME,
    ALICIA_PACKET.rule,
    ALICIA_PACKET.policy,
    ALICIA_PACKET.outcome,
    ALICIA_PACKET.reason,
  ]);
  await expectTraceRules(consultantPage, es, ALICIA_PACKET.rulesEvaluated);
  await closeCase(consultantPage, es, ALICIA.customer, ALICIA.certificate.outcome);

  await page.reload();
  await expectCertificate(page, t, ALICIA.product, ALICIA.certificate);
  await expectWithPerson(page, t, false);
  await expectEnded(page, t);
});

test("Mariana does not pre-qualify by R02 and never reaches a consultant (05)", async ({ page, consultantPage }) => {
  const t = MESSAGES[MARIANA.locale];
  await startFromHome(page, MARIANA);
  await expectCertificate(page, t, MARIANA.product, MARIANA.certificate);
  await expectSettledThread(page, t, 2, MARIANA.locale);
  await expectWithPerson(page, t, false);
  await expectEnded(page, t);

  await signInAsConsultant(consultantPage, es, CESAR);
  await expectInQueue(consultantPage, MARIANA.customer, false);
});
