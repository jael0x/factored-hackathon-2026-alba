# Implementation plan

The build order for `ARCHITECTURE.md`, as of Wed Sep 30, 2026. The contract wins over this file: if an item here disagrees with it, the item is wrong. Open decisions live in `PLAN.md` §5, dates in `PLAN.md` §8, behavior in `specs/`. This file says what gets built, in which order, and which spec scenarios each item turns green.

## How the work is pulled

- Three tracks: **Engine** (E), **Model and eval** (M), **Web** (W). The **Interfaces** items (I) come first and unblock all three. Nobody owns a track. Whoever is free takes the first unblocked item of any track.
- Claim an item by pushing a branch named after it (`e3-rules`). One item, one branch, one PR, one concern (`AGENTS.md`). The PR that finishes an item ticks it here.
- An item or part marked **Blocked** waits for the named decision in `PLAN.md` §5. Do not build around it.
- Done means:
  - the listed scenarios have tests that run under `docker compose --profile test run --rm test`;
  - lint and the type checker are clean (I4);
  - a request or response shape changes only in `api-spec/openapi.yaml`, followed by `python api-spec/generate.py`; handlers and the web client use the generated types (`ARCHITECTURE.md` "HTTP contract", `api-spec/README.md`);
  - a behavior change updates the matching feature in `specs/` (with `/spec update`) and the spec status in `diagrams/c4.html` in the same change;
  - an item that settles one of the C4 page's `New` open items updates that entry too.
- Leakage wall for the learned component: the held-out set (M4) is written and frozen, with its sha256 recorded, before anyone tunes the prompt (M3). Prompt tuning uses the dev set only. Whoever wrote held-out cases does not take prompt-tuning work afterwards.

## Where we are

Built and merged on Sep 29 (PR #1, plus the AWS CLI architecture fix): `compose.yaml` with `postgres`, the one-shot `load`, `api` with `/health` and `/ready`, a placeholder `web` behind nginx, and a `test` service. `db/migrations/001_init.sql` already creates every table the contract lists, cycle tables included.

Also on Sep 29 (e0e3532), the wire contract:
- `api-spec/openapi.yaml` holds the paths: 15 in e0e3532, 17 after `/config` and `/me` (Sep 29), 18 after `/consultant/me` (Sep 30).
- It is generated into `api/contract_models.py` (Pydantic) and `web/src/api/schema.d.ts` (TypeScript).
- `api/tests/test_contract.py` guards it.
- `/health` and `/ready` already return the generated models, and the web shell calls them through `web/src/api/client.ts`.

The full load on Sep 29 read 150,000 customers, 400,000 products, and 1,200 consultants, found 22,492 empty scores and 30,033 empty incomes, passed the products-to-customers check, and wrote 150,000 gold rows (`load` output, full files). That matches the contract's Sep 27 measurements.

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
- No lint or type-check config existed yet (I4, done Oct 4).
- Customer login built on Sep 29 and refined on Sep 30 (the two-column layout, the demo popover), one C4 component at a time: the screen (W2), the routes, and the engine. A browser mock (MSW) was tried and removed on Sep 30; screens are built against the local stack. `002_login.sql` adds `customers.email` and hashed codes; `mailpit` receives every code. `api/tests/test_login_integration.py` covers the `01` scenarios against Postgres, and `api/tests/test_code_rules_integration.py` runs the code rules (expiry, five wrong tries, replacement, one use) for both roles.
- Consultant login built on Sep 30 the same way (D18): `/consultant/login` and a `/consultant` greeting (W8), `POST /consultant/session/code`, `POST /consultant/session`, and `GET /consultant/me`. On the layers of 537e417: `api/domain/consultants` (the login key and the `Active` rule), the consultant use cases in `api/application/session` on the same code steps as the customer's, `api/infrastructure/db/consultants.py`, and `api/presentation/http/routes/consultants.py`. `003_consultant_login.sql` adds `service_agents.email`, `agent_status`, and `specialty`. `specs/11-consultant-login.feature` holds its scenarios, because `01` had reached 15; `api/tests/test_consultant_login_integration.py` covers them.
- Customer home built on Oct 1 (W3, and the products part of E7): `GET /products` and `/` with the product cards. `api/tests/test_products_integration.py` and `api/application/products/test_list_products.py` cover the API side of `02`; the Spanish names and the empty state were checked in the browser, since the web app has no test runner yet (I4). E7 closed Oct 5: `profile.py` came with E4, and the catalog is not a module (see E7). Decided and built the same day: `GET /products` leaves out `Closed` products and loans at 0 (`api/domain/products/listing.py`), and `005_products_balance_required.sql` with the load writes 0 for an empty balance (`specs/10`).
- I1, decided Sep 30: `api-spec/generate.py` appends a named alias for every string enum in `openapi.yaml` (`Role = Literal['customer', 'consultant']` and 18 more) to `api/contract_models.py`. Since Oct 1 `api/domain/session/tokens.py` imports `Role` from there too, so no set the wire carries is declared twice. `test_every_spec_enum_has_a_named_alias` guards the list.
- I1, Oct 1 (D19): event names became the wire enum `EventName`, and `api/domain/process/events.py` holds their constants, every idempotency-key builder, and the actor of each event. Command names and process rule ids stay with E4 and E3.
- E2, built Oct 2 (D20): `events.seq` (`004_event_sequence.sql`) orders every event; `api/domain/process/lifecycle.py` holds the three moves and the message stamp; `new_events.py` builds each event with its key, actor, and `process_state`; `api/application/processes.py` records a message and starts, hands off, and ends a case through `PostgresEvents` and `PostgresProcesses`. Two-connection tests cover a second start and a message sent during a handoff. `POST /messages` declares 409 `message_id_reused`; the route itself is E8.
- Language switch built Oct 2 (W9, D21): every label in Spanish or Portuguese from `web/src/i18n/` (English removed Oct 3, D22), the switch in every app bar, and the login code email in the request's `locale`. The conversation part of D21 is I5, written into the contract the same day: each message carries `locale`, the case stores it from its opening message, and the model's `language` only sends an unreadable message to a person.
- E3, built Oct 2: the 21 process rules in `api/domain/process/rules.py`, pure over the typed record `stored_events.py` parses, with the command names and payloads in `commands.py`. The command key is written into the contract ("Commands"). Nothing calls `match_rules` yet; that is E4.
- E1, built Sep 30 and hardened Oct 1: `decide(profile, product, declared_income)` in `api/domain/policy/engine.py`, thresholds and rule order in `alba-credit-v1.yaml`. D16 (2) is closed. The trace lists every evaluated rule and stops at the first terminal result. The policy file is checked when it loads (every status and every rule listed once, no gap between bands, R04 before R05), and a negative or non-finite declared income is rejected. `api/domain/policy/test_engine.py` covers the branches. `api/fixtures/oracle_customers.json` stays with M1.
- E1, Oct 4: every decision also cites `credit_score`, `income_local`, `income_currency`, and `income_usd` from the profile, after the closing fact and each name once, because `Case.certificate` and the packet copy them from `analysis.completed` (E5, E8). Sabotage runs: dropping the cited facts and citing a name twice each turn the engine tests red.

## Interfaces (do first)

- [x] **I1. Closed sets in code.** Every closed set from `AGENTS.md` "No magic strings" is defined once.
  - Sets the wire carries are generated as named `Literal` aliases at the end of `api/contract_models.py` from `api-spec/openapi.yaml` (decided Sep 30). Python code imports them and does not declare them again. These are: role, state, end reason, product, locale, language, outcome, close outcome, currency, reason code, intent, template id, `decided_by`, policy rule id, actor, message author, policy version, process key, and event name.
  - Sets the wire does not carry live in the module that owns them in the contract's file tree:
    - `api/domain/process/commands.py`: command names and their payloads (since Oct 2, E3: the domain rules emit them, and the domain cannot import the worker);
    - `api/domain/process/rules.py`: process rule ids.
  - Event names and idempotency keys, done Oct 1 (D19): `EventName` is a wire enum in `openapi.yaml`, referenced by `TraceEventBase.event_name`; `test_event_names_are_the_trace_discriminator` checks it equals the discriminator mapping. `api/domain/process/events.py` holds the ten constants, the key builders (a two-event action keys each event `{action key}:{event_name}`), and the actor of each event, so the pure rules can import them.
  - Closed Oct 4: `api/tests/test_closed_sets.py` holds the rule (`ARCHITECTURE.md`, "Quality gate"). `Locale` got its constants in `api/domain/locale.py`, the login email reads them, and the web narrows a stored role through `HOME_PATH` instead of repeating the two roles.
  - D13 and D14 (Oct 2) add the process rule ids `ask_consent_for_income` and `hand_off_no_product`; they are defined with the other rule ids in E3. The additions from D15 wait for that decision.
- [x] **I2. HTTP route contract.** Done in e0e3532: `api-spec/openapi.yaml` and `ARCHITECTURE.md` "HTTP contract" (15 paths, roles, error codes, the `Case`, the packet, and the trace).
  - **Thread source (settled):** customer lines come from the process's `conversation.message_received` events, plus the opening message reached through `process.started.caused_by_event_id`. Assistant and template lines come from `messages` rows.
  - **Updates (settled):** `POST /messages` returns the `Case` after the worker finishes that cycle's commands, so the page does not poll.
  - **Still open:** no route lists a customer's processes. After a reload or a new login, the client cannot find an open case or an issued certificate unless it kept the `process_id` from a `POST /messages` response.
- [x] **I3. `ConversationTurn` and turn fixtures.** `api/infrastructure/llm/schema.py` in the contract's shape (`language` is `es`, `pt`, or `other`; D22), plus one JSON turn per step of the four oracle flows and the spec examples. Engine tests inject them. Depends on I1.
  - Done Oct 4. `ConversationTurn` takes its sets from `contract_models.py`, is strict and frozen, and refuses any other field. `parse_conversation_turn` is the one parse for M3's adapter and the fixtures: it decodes every number as an exact `Decimal` and refuses a quoted or negative amount, `NaN`, and a repeated key (Pydantic's own JSON parser accepts the first and keeps the last of the second), raising `InvalidConversationTurn`. The JSON schema gives the amount as a number only, for Structured Outputs. `pydantic` is pinned at 2.13.5, the version both images resolved, since `test_schema.py` asserts the whole schema.
  - 22 turns in `api/fixtures/turns/`, each the message text, its `locale`, and the model's turn. `api/tests/test_turn_fixtures.py` runs each step through `api/tests/turn_harness.py` (the stamps `conversation.generate` adds) and `match_rules`, and asserts the exact rule and command. A bare "sí" carries `product` null, and the stored product reaches the event ("Events"). "pesos" names no country, so its currency is null (written into "How the model is called"). `test_rules.py` keeps its inline payloads: the domain tests stay pure.
  - Not a fixture: "no" in `05` (refused with 409 before any turn), "¿ya revisaron mi caso?" in `07` (no model call), and "y también un préstamo" in `05`, whose label the spec does not give; E8 chooses it.
  - Sabotage runs: no `extra="forbid"`, a float decoder, `es-si` with a product, and English labeled `es`; each turns its exact tests red.
- [x] **I4. Tooling.** ruff and mypy for Python, `tsc --noEmit` for the web app, all run by the `test` service. `README.md` names the one command. Since Oct 1 `scripts/check.sh` runs ruff, mypy strict, and pytest with coverage floors in the `test` service, and CI runs it plus `tsc` (`ARCHITECTURE.md`, "Quality gate"). Since Oct 4 the `web` job also runs Vitest (`npm test`).
  - Done Oct 4. `npm run check` in `web/` is the web gate (`tsc`, Vitest, the Vite build); the `test` service runs it before `scripts/check.sh`, and the `web` job runs the same script. `docker/test.Dockerfile` installs the web packages with `npm ci` in a Node stage on the same Debian release as the Python base and copies Node in; `node --version` fails the build if its libraries are missing. Both base images are pinned by digest, and Node is 22.23.3 there and in CI.
  - `docker compose --profile test run --rm test` reused a built image, so it checked the code the image was built from (`--dry-run` showed no build step). The service now sets `pull_policy: build`.
- [x] **I5. Language on the wire (D21).** The switch's language rides on each message and decides what Alba writes. `api-spec/openapi.yaml`: `SendMessageRequest` carries it, and `Locale` names the template locale (`es`, `pt`; D22 dropped the `en` that I5 added). `ARCHITECTURE.md`: the sections where the model's `language` picks the template locale say the message's language picks it, and `other` still hands off. The matching scenarios in `03` to `08` are updated. Blocks the language parts of E3, E5, E8, M3, and M4.
  - Done Oct 2. Names: `locale` (`es`, `pt`) is the switch's choice everywhere Alba writes (the message, the process, the turn, `analysis.completed`, the consultant close, the templates, the certificate, the `Case`, the queue, the packet); `language` (`es`, `pt`, `other`) is only what the model read. `TemplateLocale` is gone; `Locale` is the one set.
  - `process.start` stores the opening message's `locale` and `process.started` carries it; each turn stores its message's. `006_process_locale.sql` renames `processes.language` to `locale`, `NOT NULL`. E2's `record_customer_message` and `start_process` take the locale; `api/tests/test_process_cycle_integration.py` covers a case opened in Portuguese and a message id reused with another locale.
  - D16 (1) closed with it: `ask_which_product` checks `language` like the other turn rules.
  - Specs: `05` "The certificate is written in the language the customer chose", `07` uses French for the unsupported language, `08` "The outcome is written in the customer's language, not the consultant's", `12` the two answer-language scenarios.

## Engine (E)

- [x] **E1. Policy engine.** `api/domain/policy/engine.py`, `api/domain/policy/alba-credit-v1.yaml`, `Decision`. Pure. Rules in the contract's order, `rule_trace` accumulates, `facts` cite column, value, and `as_of`. Tests cover:
  - every branch;
  - the boundaries: scores 579, 580, 619, 620 and days past due 1, 29, 30;
  - an empty score;
  - an empty income, with and without a declared amount;
  - the file income winning over a typed amount;
  - one sabotage run.

  `api/fixtures/oracle_customers.json` after M1.
  - Specs: `05` status, days past due, product held, no score, and score band outlines; `06` "The income on file wins over a typed amount" and "marked as self-declared".
  - Depends on I1. D16 (2) closed Sep 30: `decide(profile, product, declared_income)`.
- [x] **E2. Events and processes.** `api/infrastructure/db/events.py`: append with the idempotency key; a repeated key writes nothing and says so; the same key for another fact raises. `api/application/processes.py`: stamps `process_id` and `process_state` on `conversation.message_received`; start, transition (only the allowed table; anything else raises and writes nothing), end. Built Oct 2 (D20).
  - Specs: `05` "A message delivered twice does not produce a second decision", "A new message after an ended case opens a new case", "A message id sent again with another text is refused", "Two messages sent before the case opens join one case". `api/tests/test_process_cycle_integration.py` covers them at the store; the certificate and the thread wait for E3 to E5 and E8.
  - Depends on I1.
- [x] **E3. Rules.** `api/domain/process/rules.py`: the rules as pure functions over the event, in table order. Each rule has a test that it fires and a test that it does not. Built Oct 2.
  - `stored_events.py` parses a stored event into the typed record a rule reads, and refuses what the contract does not allow: a message stamped `ended`, or `human_active` with no process; a shown turn with a `reason_code`; a withheld turn with any reason but `reply_forbidden` or `model_output_invalid`; an amount read as a float. `commands.py` holds the command names and one payload type per command. `match_rules(event)` returns the planned commands, each with its rule, its event, and its key (`ARCHITECTURE.md`, "Commands").
  - Tests in `api/domain/process/test_rules.py` and `test_stored_events.py`: the 1,920 turn combinations, every rule firing and not firing, every other trigger, the four oracle flows and Juan in Portuguese as event sequences, and the table checks. Sabotage runs: a third ask still asking which product, `ask_which_product` without the language check, the handoff before the referral notice, and `end_after_decision` ignoring `decided_by`; each turns its exact tests red. These are pure tests; the same scenarios over HTTP pass with E4, E8, and E9.
  - Specs: `03` scenarios 1, 2, 4; `04` all; `07` the handoff outline and "The assistant stops replying once a person has the case".
  - Specs, from D13 and D14 (Oct 2): `03` the second and third requests with no product; `04` an income instead of the consent answer, and a yes with an income; `07` another language with no product.
  - A test enumerates every combination of `reply_ok`, `language`, `intent`, `product`, `product_asked_count`, and `income_requested`, and asserts that exactly one `conversation.turn_classified` rule matches each.
  - Depends on E2. D12, D13, D14, and D16 (1) closed Oct 2. D16 (1) closed with I5: every turn rule but `hand_off_language` and `hand_off_reply` requires `language` in `es` or `pt`. `open_process` passes the message's `locale` to `process.start` (`StartPayload`).
- [x] **E4. Worker and commands.** `api/presentation/worker/loop.py` (the contract's file tree), a loop in the API process:
  - takes `pending` commands with `FOR UPDATE SKIP LOCKED`;
  - makes at most 3 attempts, then moves the case to `human_active` with `tool_failed`;
  - runs the eight handlers; `conversation.generate` stamps `product_asked_count` and `income_requested` on the turn from this process's earlier events (D13, D14), and `policy.run` uses the key with the triggering turn (D12);
  - takes the model call as an injected function, so tests pass turns as JSON: the fixtures in `api/fixtures/turns/` (I3);
  - builds the `conversation.turn_classified` payload from the turn and its stamps, in `new_events.py` with the other event builders. `PayloadValue` (`str | None`) cannot hold a turn's amount, booleans, and count yet. Today two test helpers write that payload by hand: `classified_turn` in `api/tests/turn_harness.py` (I3) and `turn()` in `api/domain/process/test_rules.py` (E3). E4 is not done until both build it through that one builder, with no payload dict of their own, so a field added to the event cannot reach one test and miss the other;
  - decides what `policy.run` does with a turn's `declared_income_currency` that differs from the profile's `income_currency`: the contract reads the amount in the country's currency and says nothing of a turn that names another;
  - lets the `POST /messages` handler wait until the commands enqueued from its event are done, because the response is the `Case` after that cycle. The handler waits; it does not run commands itself;
  - reads each event through `parse_stored_event`, inserts the `PlannedCommand` rows from `match_rules` in their order and on their keys (a key already present inserts nothing), and stores a payload's amount as an exact decimal: psycopg loads jsonb numbers as `float` unless the loader uses `parse_float=Decimal`, and the rules refuse a float (E3).

  Event-chain tests cross the worker (`AGENTS.md` "Tests"). Settles the C4 items on who calls `match_rules`, whether an event and its commands commit together, and the poll interval.
  - Specs: `07` "Repeated model failures send the case to a person".
  - Depends on E2 and E3. D16 (3) closed Oct 5.
  - Built Oct 5. `api/application/cycle/` holds the ports, `PlanningEvents` (the one owner that turns an append into commands, in the same transaction), one handler per command, and the attempts; `api/presentation/worker/loop.py` the thread, `run_next`, `run_until_idle`, and `wait_for_cycle`; `009_command_queue.sql` adds `commands.seq` and a unique `messages.event_id`. The claim takes the lowest `seq` whose customer has nothing pending ahead. `json_codec.py` keeps amounts exact in jsonb both ways. `PayloadValue` became `JsonValue`; `turn_classified` in `new_events.py` is the one turn builder, and `test_rules.py` and `turn_harness.py` build through it.
  - Decided Oct 5: an amount in another country's currency is not an income (asked again); the certificate key is `decision:{process_id}` and the event carries no `template_id`; `process.ended` takes `policy_version` from the analysis behind a policy certificate; `conversation.generate` writes nothing on a case that left `ai_active`; the third failure also fails the event's later commands; `RUN_WORKER` turns the thread on, the loop polls every second, and a failed attempt is retried at once. Until M3, the wired model fails and names the adapter.
  - Tests: `api/tests/test_worker_integration.py` runs the four oracle flows, Juan in Portuguese, the referral and the consultant close, three model failures, one failure then a turn, the missing adapter and profile, a replayed message, a message after a queued handoff, two first messages, two connections claiming at once, a withheld reply, a shown reply, a certificate that cannot be written, the thread, and the lifespan, against Postgres. `api/application/cycle/test_guards.py`, `test_turns.py`, `test_commands.py`, `test_declared_income.py`, and `test_json_codec.py` cover the pure parts and the refusals. Sabotage runs: no per-customer order, a float loader, four attempts, the model called on a handed-off case, no failing of later commands, and a foreign amount read as local; each turns its exact tests red.
- [x] **E5. Templates.** `api/domain/policy/templates.py`, ES and PT (D21, D22), for `confirm_prequalify`, `which_product`, `needs_income`, `refer_notice`, the policy certificate, and the two consultant-path messages. The certificate shows income in local currency with the USD equivalent and the rate date, and no limit or rate.
  - Built Oct 4. The certificate paragraph is one sentence (outcome, product, simulated); the income, the USD equivalent, and the date are the `facts` the screen shows beside it, cited by every decision since E1's Oct 4 change. A self-declared income has no USD equivalent (`DESIGN.md`, "Open"). Product names follow `web/src/i18n/`. The tables are checked when the module loads.
  - `api/domain/policy/test_templates.py` asserts every sentence in both locales, the refusals (no product, a `REFER` or `NEEDS_INFO` decision), the referral notice without an outcome or a score, and each table check. Sabotage runs: a wrong Portuguese product name, the missing-product check removed, and a referral notice that states an outcome; each turns its exact tests red. These are pure tests; the scenarios over HTTP pass with E4 and E8.
  - Specs: `05` certificate scenarios and "The certificate is written in the language the customer chose"; `08` "The outcome is written in the customer's language, not the consultant's"; `07` "The referral notice tells the customer a person will review".
  - Depends on E1. **Blocked** by D15 (1) for the non-`REFER` notice.
- [x] **E6. Auth.** `api/domain/session`, `api/domain/consultants`, `api/application/session`, and `api/presentation/http`. The customer half was built Sep 29, the consultant half Sep 30 (D18: `/consultant/login`, email plus employee code, `Active` consultants only):
  - 6-digit codes valid 10 minutes, stored hashed in `login_codes`, emailed by `api/infrastructure/mail/smtp.py` to Mailpit; a new code replaces the unused one; the fifth wrong code spends it;
  - the same answer for every document on `POST /session/code` and every pair on `POST /consultant/session/code`, and the same 401 for every failure on `POST /session` and `POST /consultant/session`;
  - JWT HS256 for 15 minutes with `role`, and the `get_session` dependency;
  - 401 on a missing or expired token;
  - 403 for a customer token on a consultant route, and the reverse;
  - a customer code does not open a consultant session, and the reverse;
  - a missing `JWT_SECRET` stops startup and names the variable.

  Settles the C4 items on code hashing and wrong-attempt limits.
  - Specs: `01` all, `11` all.
  - Depends on I1 and I2.
- [x] **E7. Read routes.** Customer and consultant search, and products with the session filter. The demo customer and consultant searches, `GET /me`, and `GET /consultant/me` are built (Sep 29-30). `api/infrastructure/db/profile.py` and `products.py`.
  - Catalog, decided Oct 5: `api/infrastructure/db/catalog.py` is dropped from the contract. The catalog has no table and no dataset source (`PLAN.md` §4, "No Portuguese, no policy documents"); it is the two `ProductKey` values with their `PRODUCT_NAMES` from `api/domain/policy/templates.py`, and its only reader is the prompt, so M3 builds it. `ARCHITECTURE.md` "How the model is called" fixes the order.
  - `profile.py` was built Oct 5 with E4 (`policy.run` and the model's booleans read it).
  - Products, built Oct 1 with W3: `GET /products` on the layers of the login. `routes/products.py`, `application/products/list_products.py`, the product record under `domain/products/`, and the SQL in `infrastructure/db/products.py`. The query filters on the token `sub` and orders by `product_id`. A `customer_id` that is not the `sub` returns `[]` without a query. `domain/products/listing.py` leaves out `Closed` products and loans at 0.
  - Product tests: the use case alone (no id, its own id, another id with the repository untouched), and against Postgres (Juan's two rows exactly, Juliana in USD, Alicia in COP, Juan asking for Alicia's id, a customer with no products, a loan at 0 left out and a card at 0 kept, 403 for a consultant token, 401 without one). The listing rule alone, per type and status. Sabotage runs drop the filter, the own-id rule, and the paid-loan rule.
  - Specs: `01` and `11` search scenarios; `02` all.
  - Depends on E6.
- [ ] **E8. Case and consultant routes.** `POST /messages`, `GET /case/{process_id}`, the consultant queue, packet, trace, and close, exactly as in `ARCHITECTURE.md` "HTTP contract", typed with the generated models. That section already fixes the order (`created_at`, then id), the 404 and 409 cases, and the packet with null analysis fields when no `analysis.completed` exists.
  - The trace declares `declared_income_amount` as a `float` (`TraceTurnClassified`), while the turn and the rules hold an exact decimal; settle how it is written on the wire. The label of "y también un préstamo" (`05`, two messages before the case opens) is chosen here (I3 left it out).
  - Specs: `08` for `REFER` cases; `09` all; the HTTP side of `03` to `07`. `POST /messages` takes `locale` (I5) and passes it to `record_customer_message`; the `Case`, the queue items, and the packet carry the case's `locale`.
  - Depends on E4 and E6. **Blocked** by D15 (3) for closes on non-`REFER` cases.
- [ ] **E9. Oracle integration test.** The four flows through HTTP and the worker with injected turns:
  - Juan: `PREQUALIFIED` by R05.
  - Juliana: `NEEDS_INFO`, then `PREQUALIFIED` after her income.
  - Alicia: `REFER`, then the consultant close.
  - Mariana: `NOT_PREQUALIFIED` by R02.

  This is the contract's oracle test.
  - Depends on E1 to E8. D12 closed Oct 2.

## Model and eval (M)

- [ ] **M0. Load gaps.** Measure the rows of `daily_exchange_rates.csv`, write the count into the contract, add it to `EXPECTED_ROW_COUNTS`. Add active products by type to the load report. Add tests for the two `10` scenarios that have none. No dependency.
- [ ] **M1. R8 and R9 against Postgres.** Confirm every oracle value in `ARCHITECTURE.md` from the loaded tables, and list the distinct `product_type` values. Feeds E1's fixture. No dependency.
- [ ] **M2. R11 probe.** `gpt-6-luna` on a small dev set (never the held-out set):
  - latency, tokens, and cost per turn;
  - Structured Outputs validity;
  - whether `temperature` 0 is accepted;
  - Spanish and Portuguese quality.

  Numbers go to `PLAN.md` §6 and feed D1, D6, D7.
- [ ] **M3. Model adapter and prompt.** `api/infrastructure/llm/conversation.py`:
  - one call with Structured Outputs, the Pydantic check, and one retry;
  - an `llm_turns` row on every call, with the model, tokens, and latency;
  - forbidden phrases set `reply_forbidden`; the detector runs over every fixture in `api/fixtures/turns/`, and only `es-si-reply-states-outcome` is withheld. "Events" still lists `pre-qualif` and `prequalif`, which D22 (4) removed, while "Policy" lists the four Spanish and Portuguese phrases: settle the one list here;
  - the adapter parses with `parse_conversation_turn` and retries on `InvalidConversationTurn` (I3);
  - a turn whose intent names one product and whose `product` names another, or none, is invalid output, so `confirm_prequalify` always has a product to name (E3);
  - the contract says a turn with `model_output_invalid` is written, but `intent` and `language` are required and there is no valid value to write; settle it in `openapi.yaml` here. The rules read only `reason_code` on a withheld turn (E3);
  - a missing key fails the command and names the key.
  - implements `ReadTurn` from `api/application/cycle/ports.py` (a `TurnRequest` in, a `ModelReading` out) and replaces `model_not_built` in `api/main.py`. The `llm_turns` row must survive a failed attempt, which rolls back the command's transaction, so it is written on its own connection (E4).
  - an amount in a currency outside `IncomeCurrency` ("dólares") leaves `declared_income_amount` null, as "pesos" leaves the currency null, so it is asked for again instead of being read as pesos (E4, Oct 5).

  The prompt is built from the four booleans, the state, the catalog in Spanish and Portuguese (`PRODUCT_NAMES` in the fixed order `credit_card`, `personal_loan`, never by iterating `PRODUCT_KEYS`, whose order changes between processes; a test asserts the catalog text exactly and that it names every `ProductKey`), the text, and the message's `locale` to write `reply_text` in (I5), and is versioned so eval runs can cite it. pytest never calls OpenAI.
  - Specs: `07` "A reply that states an outcome is withheld".
  - Depends on I3 and M2. **Blocked** by D11 for masking only. D13 chose option (c), so the prompt carries no count of earlier questions.
- [ ] **M4. Held-out set.** Team-labeled utterances in ES-MX, ES-CO, ES-AR, and PT, with the expected intent, product, language, and route. Portuguese is team-written or machine-translated and disclosed. It includes multilingual-ambiguity cases: Portuguese typed with Spanish chosen and the reverse, mixed Spanish and Portuguese, and English, which must go to a person (D22). Frozen with its sha256 before M3's prompt tuning. **Blocked** by D7 for its size.
- [ ] **M5. B0 keyword baseline.** Pure, the same `ConversationTurn` output shape, runs offline. Depends on I3.
- [ ] **M6. Harness and metrics.** Intent level first: B0 against the model on M4. Then route level through the API once E9 passes: the §7 metrics of `PLAN.md` with denominators and intervals, written to `eval/reports/`. **Blocked** by D7 for B1, case counts, and spend.
- [ ] **M7. Data-quality report and model cards.** `docs/data_quality.md` (the traps in `PLAN.md` §4.3, the load checks, the update-correctness fixture labeled as such), `docs/model_card_risk.md` (`PLAN.md` §4.4), and a card for the `ConversationTurn` component. R1 to R7, R10, and R12 as time allows.

## Web (W)

Every screen follows `DESIGN.md` and `mocks/index.html`, and handles loading, error, and success on every fetch. Every call goes through `web/src/api/client.ts` with the generated types; no screen calls `fetch` directly. Screens are built against the local stack, not a mock API (Sep 30): a screen is built together with, or after, the routes it calls.

- [x] **W1. App shell.** Built Sep 29: routing, the aurora and tokens, the bearer token on every call, and the "Tu sesión terminó" card on 401. Each later page adds its own route.
- [x] **W2. Customer login.** The document number, then the code from the email (Mailpit in the demo), and the demo search and random pick when `GET /config` says `demo_login`. Built Sep 29-30 against the real API. Specs: `01`.
- [x] **W3. Home.** Products in the row's currency. Specs: `02`.
  - Built Oct 1 with E7's products part, against the local stack. White cards in a two-column grid, in the API's order. The top line is the Spanish name of `product_type` and the number masked to its last four. Then the amount with its code (`1,559.57 USD`), then the status in Spanish, in the gender of the product ("Activa", "Activo"). Closed products and paid loans do not reach the screen.
  - One map in `web/src/products.ts` names the types and statuses that `ARCHITECTURE.md` "Data" lists. A value outside it shows as the file has it.
  - No rate and no days past due: `GET /products` does not return them.
  - A customer with no products reads "Todavía no tienes productos con nosotros.".
  - The two "Preguntar por" rows show disabled until W4 wires them to `POST /messages`.
- [ ] **W4. Case.** The thread; one uuid per send, with the switch's `locale` in the same body so a retry repeats it; the typing indicator ("escribiendo…", and its Portuguese label in `web/src/i18n/`) until the `POST /messages` response arrives, with no fixed sleep and no polling; the returned `Case` replaces the thread; the certificate when it exists. The "Preguntar por" rows on `/` start sending here. Specs: `03` to `07` as the customer sees them.
- [ ] **W5. Consultant queue and case.** The packet, two close actions, and no reply field. Specs: `08`. **Blocked** by D15 (3) for closes on non-`REFER` cases.
- [ ] **W6. Trace.** The process's events in order, with the detail column of `09`. Specs: `09`.
- [ ] **W7. Oracle flows in the browser.** The four oracle flows, one of them in Portuguese. Depends on E9 and W2 to W6.
- [x] **W8. Consultant login page.** `/consultant/login` (D18): email and employee code, then the emailed code; `Active` consultants only; the demo consultant search and random pick; a link to and from `/login`. `/consultant` greets the consultant until W5 replaces it. Built Sep 30 against the real API. Specs: `11`.
- [x] **W9. Language switch (D21).** Spanish and Portuguese in the app bar of every screen (English removed Oct 3, D22), both login pages included. One dictionary per language in `web/src/i18n/`: the Spanish one defines the keys, and a missing or extra key fails `tsc`. The product names and statuses carry each language's own gender. A first visit follows the browser, else Spanish; the choice is kept in the browser and sets `<html lang>`. The code request carries the language, and `api/infrastructure/mail/smtp.py` writes the email in it. Specs: `12`.
  - Built Oct 2 against the local stack. `Locale` (`es`, `pt`) is a wire enum, required on both code requests; a request without it is a 422. `api/infrastructure/mail/test_smtp.py` and the two login integration tests cover the email side of `12`; the switch, the first visit, the labels, and the product genders were checked in the browser, at 360 and 375 px too, since the web app had no test runner yet (I4). Since Oct 4 (#15) `web/src/i18n/locale.test.ts` covers the first visit, the kept choice, and blocked storage.
  - On phones the name pill hides so the switch fits; the greeting already names the customer.

## Spec work from the Sep 29 review

- After each of D12 to D16 is decided: update `03`, `04`, `06`, `07`, and `08` to match, in the change that writes the decision into the contract. D12, D13, D14, and D16 (1) done Oct 2 (`03`, `04`, `07`; `06` needed no change).
- Scenarios missing for behavior the contract already defines. Each is added in the item that builds the behavior:
  - two invalid model outputs send the case to a person with `model_output_invalid` (`07`, M3);
  - the consultant login (email and employee code, `Active` consultants only, D18): written Sep 30 as `11-consultant-login.feature`, since `01` had reached 15 scenarios;
  - a customer session is refused on consultant routes: written Sep 30 in `11` against `GET /consultant/me`; E8 checks the same 403 on its own routes.

## Milestones

| Milestone | Day | Done when |
|---|---|---|
| 1 | Wed Sep 30 | I1 to I4, E1 to E4, M0 to M2 are in. D12 to D16 are decided. pytest decides the four oracle cases through the worker with injected turns |
| 2 | Thu Oct 1 | E5 to E8, M3 to M5, and W1 to W6 are in |
| 3 | Fri Oct 2, feature freeze | E9 and W7 pass, the first full eval run (M6) is written, M7 is started |

Saturday to Monday follow `PLAN.md` §8. The cut list is in `PLAN.md` §8.
