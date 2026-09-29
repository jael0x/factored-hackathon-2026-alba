# Implementation plan

The build order for `ARCHITECTURE.md`, as of Tue Sep 29, 2026. The contract wins over this file: if an item here disagrees with it, the item is wrong. Open decisions live in `PLAN.md` §5, dates in `PLAN.md` §8, behavior in `specs/`. This file says what gets built, in which order, and which spec scenarios each item turns green.

## How the work is pulled

- Three tracks: **Engine** (E), **Model and eval** (M), **Web** (W). The **Interfaces** items (I) come first and unblock all three. Nobody owns a track. Whoever is free takes the first unblocked item of any track.
- Claim an item by pushing a branch named after it (`e3-rules`). One item, one branch, one PR, one concern (`AGENTS.md`). The PR that finishes an item ticks it here.
- An item or part marked **Blocked** waits for the named decision in `PLAN.md` §5. Do not build around it.
- Done means:
  - the listed scenarios have tests that run under `docker compose --profile test run --rm test`;
  - lint and the type checker are clean (I4);
  - a behavior change updates the matching feature in `specs/` (with `/spec update`) and the spec status in `diagrams/c4.html` in the same change;
  - an item that settles one of the C4 page's `New` open items updates that entry too.
- Leakage wall for the learned component: the held-out set (M4) is written and frozen, with its sha256 recorded, before anyone tunes the prompt (M3). Prompt tuning uses the dev set only. Whoever wrote held-out cases does not take prompt-tuning work afterwards.

## Where we are

Built and merged on Sep 29 (PR #1, plus the AWS CLI architecture fix): `compose.yaml` with `postgres`, the one-shot `load`, `api` with `/health` and `/ready`, a placeholder `web` behind nginx, and a `test` service. `db/migrations/001_init.sql` already creates every table the contract lists, cycle tables included.

The full load on Sep 29 read 150,000 customers, 400,000 products, and 1,200 agents, found 22,492 empty scores and 30,033 empty incomes, passed the products-to-customers check, and wrote 150,000 gold rows (`load` output, full files). That matches the contract's Sep 27 measurements.

`specs/10-data-load.feature` against the tests today:

| Scenario | Test |
|---|---|
| The first start copies only the four source files | None. The key list is a constant in `pipeline/constants.py` |
| Files already on disk are not copied again | None |
| Unchanged files are not loaded into the database again | `test_silver_gold_and_idempotent_batch` |
| A changed file is loaded again | `test_changed_file_is_reloaded` |
| A row count that differs from the snapshot stops the load | `test_assert_expected_row_counts_fails_on_mismatch` (unit) |
| A product with no matching customer stops the load | `test_orphan_product_fails_quality_check` |
| Missing keys and missing files stop the load with a named error | `test_download_fails_loud_without_aws_and_file` |
| Every customer gets one credit profile | `test_silver_gold_and_idempotent_batch` (3-row fixture) |
| Missing scores and incomes stay empty | `test_silver_gold_and_idempotent_batch` (Juliana's row) |
| The load report counts the customers without a score | `test_report_customer_nulls` |

"The application does not start" is carried by `compose.yaml`: `api` waits for `load` to finish successfully.

Gaps against the contract in what is built (item M0):

- `daily_exchange_rates.csv` has no expected row count. The contract asks for all four files, and its snapshot size is not written in the contract.
- The load report prints rows and empty scores and incomes, but not active products by type (**Data: what is touched and what is not**).
- No lint or type-check config exists yet (I4).

## Interfaces (do first)

- [ ] **I1. Closed sets in code.** Every closed set from `AGENTS.md` "No magic strings" is defined once, in the module that owns it in the contract's file tree:
  - `api/events.py`: event names, idempotency-key prefixes.
  - `api/processes.py`: states, end reasons, reason codes.
  - `api/worker.py`: command names.
  - `api/rules.py`: process rule ids.
  - `api/policy/engine.py`: outcomes, policy rule ids.
  - `api/policy/templates.py`: template ids, locales.
  - `api/llm/schema.py`: intents, products, languages.

  Web types are generated from the API's OpenAPI schema, so the client never retypes a closed set. The additions from D13 and D15 wait for those decisions.
- [ ] **I2. HTTP route contract.** Agree on the table below and write it into **Auth and screens** in `ARCHITECTURE.md`; that settles the C4 page's route items. Two points need an answer in the same change:
  - **Thread source.** The first customer message has no process when it is written, and `messages.process_id` is `NOT NULL`. Proposal: the thread is read from the process's `messages` rows plus the message event that `process.started` points to through `caused_by_event_id`.
  - **Updates.** How later worker output reaches the page. Proposal: while the typing indicator shows, the client polls the case about once a second.
- [ ] **I3. `ConversationTurn` and turn fixtures.** `api/llm/schema.py` in the contract's shape, plus one JSON turn per step of the four oracle flows and the spec examples. Engine tests inject them; the web fixtures reuse them. Depends on I1.
- [ ] **I4. Tooling.** ruff and mypy for Python, `tsc --noEmit` for the web app, all run by the `test` service. `README.md` names the one command.

Proposed routes (the web app calls them under `/api`; nginx and Vite strip the prefix):

| Method and path | Who | Body or result | In the contract |
|---|---|---|---|
| `GET /customers/search?q=` | anyone | up to 20 customers | yes |
| `GET /agents/search?q=` | anyone | up to 20 agents, with employee code | proposed |
| `POST /session/code` | anyone | `customer_id` or `random=true`; the code only with `DEMO_INBOX=1` | yes |
| `POST /session` | anyone | the code; returns the customer JWT | yes |
| `POST /agent/session/code`, `POST /agent/session` | anyone | the same for agents | "works the same"; paths proposed |
| `GET /products` | customer | the session's products; any id in the request is ignored | proposed |
| `POST /messages` | customer | `client_message_id`, `text`; returns 202 with the event id | proposed |
| `GET /cases` | customer | the session's processes, newest first | proposed |
| `GET /cases/{id}` | customer | state, product, language, thread, certificate if decided | proposed |
| `GET /agent/queue` | agent | processes in `human_active` | proposed |
| `GET /agent/case/{id}` | agent | the packet from `analysis.completed` | proposed |
| `POST /agent/case/{id}/close` | agent | `outcome` | yes |
| `GET /agent/case/{id}/events` | agent | the process's events, in order | proposed |

## Engine (E)

- [ ] **E1. Policy engine.** `api/policy/engine.py`, `api/policy/alba-credit-v1.yaml`, `Decision`. Pure. Rules in the contract's order, `rule_trace` accumulates, `facts` cite column, value, and `as_of`. Tests cover:
  - every branch;
  - the boundaries: scores 579, 580, 619, 620 and days past due 1, 29, 30;
  - an empty score;
  - an empty income, with and without a declared amount;
  - the file income winning over a typed amount;
  - one sabotage run.

  `api/fixtures/oracle_customers.json` after M1.
  - Specs: `05` status, days past due, product held, no score, and score band outlines; `06` "The income on file wins over a typed amount" and "marked as self-declared".
  - Depends on I1. **Blocked** by D16 (2) for the signature.
- [ ] **E2. Events and processes.** `api/events.py`: append with the idempotency key; a repeated key writes nothing and says so; stamps `process_id` and `process_state` on `conversation.message_received`. `api/processes.py`: start, transition (only the allowed table; anything else raises and writes nothing), end.
  - Specs: `05` "A message delivered twice does not produce a second decision", "A new message after an ended case opens a new case".
  - Depends on I1.
- [ ] **E3. Rules.** `api/rules.py`: the rules as pure functions over the event, in table order. Each rule has a test that it fires and a test that it does not.
  - Specs: `03` scenarios 1, 2, 4; `04` all; `07` the handoff outline and "The assistant stops replying once a person has the case".
  - Depends on E2. **Blocked** by D12, D14, D16 (1); `03` scenario 3 by D13.
- [ ] **E4. Worker and commands.** `api/worker.py`, a loop in the API process:
  - takes `pending` commands with `FOR UPDATE SKIP LOCKED`;
  - makes at most 3 attempts, then moves the case to `human_active` with `tool_failed`;
  - runs the eight handlers;
  - takes the model call as an injected function, so tests pass turns as JSON.

  Event-chain tests cross the worker (`AGENTS.md` "Tests"). Settles the C4 items on who calls `match_rules`, whether an event and its commands commit together, and the poll interval.
  - Specs: `07` "Repeated model failures send the case to a person".
  - Depends on E2 and E3. **Blocked** by D16 (3) in wording only.
- [ ] **E5. Templates.** `api/policy/templates.py`, ES and PT, for `confirm_prequalify`, `which_product`, `needs_income`, `refer_notice`, the policy certificate, and the two agent-path messages. The contract says these sentences are not written yet: they are written here, read by both of us, then noted in the contract. The certificate shows income in local currency with the USD equivalent and the rate date, and no limit or rate.
  - Specs: `05` certificate scenarios and "A request in Portuguese gets a Portuguese certificate"; `07` "The referral notice tells the customer a person will review".
  - Depends on E1. **Blocked** by D15 (1) for the non-`REFER` notice.
- [ ] **E6. Auth.** `api/auth.py`:
  - 6-digit codes valid 10 minutes in `login_codes`;
  - JWT HS256 for 15 minutes with `role`, and the `get_session` dependency;
  - 401 on expiry;
  - agent routes require `role = agent`;
  - a missing `JWT_SECRET` stops startup and names the variable.

  Settles the C4 items on code hashing, wrong-attempt limits, and which routes need the agent role.
  - Specs: `01` all.
  - Depends on I1 and I2.
- [ ] **E7. Read routes.** Customer and agent search, and products with the session filter. `api/tools/profile.py`, `products.py`, `catalog.py`.
  - Specs: `01` search scenarios; `02` all.
  - Depends on E6.
- [ ] **E8. Case and agent routes.** Post a message, list and read cases, agent queue, packet, close, trace. Queue and trace order use an explicit tie-break after `created_at`.
  - Specs: `08` for `REFER` cases; `09` all; the HTTP side of `03` to `07`.
  - Depends on E4 and E6. **Blocked** by D15 for packets and closes on non-`REFER` cases.
- [ ] **E9. Oracle integration test.** The four flows through HTTP and the worker with injected turns:
  - Juan: `PREQUALIFIED` by R05.
  - Juliana: `NEEDS_INFO`, then `PREQUALIFIED` after her income.
  - Alicia: `REFER`, then the agent close.
  - Mariana: `NOT_PREQUALIFIED` by R02.

  This is the contract's oracle test.
  - Depends on E1 to E8. **Blocked** by D12.

## Model and eval (M)

- [ ] **M0. Load gaps.** Measure the rows of `daily_exchange_rates.csv`, write the count into the contract, add it to `EXPECTED_ROW_COUNTS`. Add active products by type to the load report. Add tests for the two `10` scenarios that have none. No dependency.
- [ ] **M1. R8 and R9 against Postgres.** Confirm every oracle value in `ARCHITECTURE.md` from the loaded tables, and list the distinct `product_type` values. Feeds E1's fixture. No dependency.
- [ ] **M2. R11 probe.** `gpt-6-luna` on a small dev set (never the held-out set):
  - latency, tokens, and cost per turn;
  - Structured Outputs validity;
  - whether `temperature` 0 is accepted;
  - Spanish and Portuguese quality.

  Numbers go to `PLAN.md` §6 and feed D1, D6, D7.
- [ ] **M3. Model adapter and prompt.** `api/llm/conversation.py`:
  - one call with Structured Outputs, the Pydantic check, and one retry;
  - an `llm_turns` row on every call, with the model, tokens, and latency;
  - forbidden phrases set `reply_forbidden`;
  - a missing key fails the command and names the key.

  The prompt is built from the four booleans, the state, the catalog, and the text, and is versioned so eval runs can cite it. pytest never calls OpenAI.
  - Specs: `07` "A reply that states an outcome is withheld".
  - Depends on I3 and M2. **Blocked** by D11 for masking only, and by D13 if its option (a) is chosen.
- [ ] **M4. Held-out set.** Team-labeled utterances in ES-MX, ES-CO, ES-AR, and PT, with the expected intent, product, language, and route. Portuguese is team-written or machine-translated and disclosed. Frozen with its sha256 before M3's prompt tuning. **Blocked** by D7 for its size.
- [ ] **M5. B0 keyword baseline.** Pure, the same `ConversationTurn` output shape, runs offline. Depends on I3.
- [ ] **M6. Harness and metrics.** Intent level first: B0 against the model on M4. Then route level through the API once E9 passes: the §7 metrics of `PLAN.md` with denominators and intervals, written to `eval/reports/`. **Blocked** by D7 for B1, case counts, and spend.
- [ ] **M7. Data-quality report and model cards.** `docs/data_quality.md` (the traps in `PLAN.md` §4.3, the load checks, the update-correctness fixture labeled as such), `docs/model_card_risk.md` (`PLAN.md` §4.4), and a card for the `ConversationTurn` component. R1 to R7, R10, and R12 as time allows.

## Web (W)

Every screen follows `DESIGN.md` and `mocks/index.html`, and handles loading, error, and success on every fetch. Until E8 lands, screens read fixture JSON built from I2 and I3.

- [ ] **W1. App shell.** Routes from the contract's screen table, the generated API types, and a session-ended screen on 401. Depends on I1 and I2.
- [ ] **W2. Login.** Customer and agent search, random pick, and code entry. The demo inbox shows the code. Specs: `01`.
- [ ] **W3. Home.** Products in the row's currency. Specs: `02`.
- [ ] **W4. Case.** The thread; one uuid per send; the typing indicator "escribiendo…" while waiting, with no fixed sleep; the certificate when it exists. Specs: `03` to `07` as the customer sees them.
- [ ] **W5. Agent queue and case.** The packet, two close actions, and no reply field. Specs: `08`. **Blocked** by D15 for non-`REFER` cases.
- [ ] **W6. Trace.** The process's events in order, with the detail column of `09`. Specs: `09`.
- [ ] **W7. Real API.** Fixtures off. The four oracle flows in the browser, one of them in Portuguese. Depends on E9 and W2 to W6.

## Spec work from the Sep 29 review

- After each of D12 to D16 is decided: update `03`, `04`, `06`, `07`, and `08` to match, in the change that writes the decision into the contract.
- Scenarios missing for behavior the contract already defines. Each is added in the item that builds the behavior:
  - two invalid model outputs send the case to a person with `model_output_invalid` (`07`, M3);
  - an agent opens a session with a code (`01`, E6);
  - a customer session is refused on agent routes (`08`, E6).

## Milestones

| Milestone | Day | Done when |
|---|---|---|
| 1 | Wed Sep 30 | I1 to I4, E1 to E4, M0 to M2 are in. D12 to D16 are decided. pytest decides the four oracle cases through the worker with injected turns |
| 2 | Thu Oct 1 | E5 to E8, M3 to M5, and W1 to W6 on fixtures are in |
| 3 | Fri Oct 2, feature freeze | E9 and W7 pass, the first full eval run (M6) is written, M7 is started |

Saturday to Monday follow `PLAN.md` §8. The cut list is in `PLAN.md` §8.
