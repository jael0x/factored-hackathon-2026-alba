# Alba architecture: credit pre-qualification

This is the build contract. Anyone who implements from this file, person or model, must end up with what is written here. What is not decided is listed under **Not decided** and **Known gaps**. Filling those in on your own changes the demo.

Related files: `README.md` (product view and data access), `mocks/index.html` (screens), `DESIGN.md` (look and motion), `AGENTS.md` (coding standard), `PLAN.md` (hackathon requirements, data evidence, open decisions, schedule), `IMPLEMENTATION.md` (build order), `specs/` (behavior as examples), `api-spec/openapi.yaml` (the wire contract). If `PLAN.md` offers an alternative (another host, another model, a credit limit), this file wins.

This file is in English. Dataset literals, customer-facing copy, and the phrases the model must not emit stay in Spanish or Portuguese exactly as written.

## Contract for implementers

- The language model does not decide eligibility, does not compute a credit limit, and does not write the certificate.
- The `alba-credit-v1` policy is a pure function. Same input, same output. It lives in git.
- Process rules read the event already written. They do not query the customer again when deciding whether a rule matches.
- The `customer_id` of every query comes from the session JWT. Never from chat text or from a model argument.
- There is one process: `credit_prequalification`. No parallel processes are added.
- Delinquency is not predicted. A model trained on `days_past_due` is not shipped.
- No credit limit is shown. There is no income multiplier.
- Product names in the file are Spanish, with these exact strings: `Tarjeta Crédito`, `Préstamo Personal`, `Préstamo Hipotecario`. Do not translate them to `Credit Card` when reading the CSV. The organizer data dictionary lists English product types; the measured file does not use them.
- Any customer with an email on file can open a session: 147,016 of the 150,000 rows. The four profiles below are the test oracle, not an allowlist.

## What gets built

A web service. The customer asks about a credit card or a personal loan. If the request is ambiguous, the assistant asks which of the two and does not decide. When the product is known, the assistant asks for explicit consent before any `policy.run`. If the customer declines, the process stays `ai_active` and the policy is not called. If they confirm and the data is enough, the policy issues a certificate (`constancia` in the UI): pre-qualifies, does not pre-qualify, or goes to a person. The certificate is a template filled with the policy result.

Four outcomes, from real rows of the file (snapshot of June 17, 2026):

| Customer | `customer_id` | Outcome | Rule | Final process state |
|---|---|---|---|---|
| Juan Alberto Romero González | `CLI-9EDEKZ8OUNUR` | `PREQUALIFIED` | R05, score 812 | `ended` / `prequalified` |
| Juliana Castro Gómez | `CLI-MD60UR8PNJDI` | `NEEDS_INFO` | R06, empty income | stays `ai_active` |
| Alicia Mariana Parra Álvarez | `CLI-440CO5FZIY6A` | `REFER` | R05, score 615 | `human_active` |
| Mariana Mónica Acosta Rojas | `CLI-ZGOY1V6ZC46J` | `NOT_PREQUALIFIED` | R02, 180 days past due | `ended` / `not_prequalified` |

These four rows are the oracle of an integration test. If an outcome changes, the test fails. Login does not hardcode them: any customer with an email on file logs in with their document number and an emailed code (**Auth and screens**).

### Oracle fixtures

Stored in `api/fixtures/oracle_customers.json`. Values read from the file on Sep 27, 2026. Amounts use the file's currency.

**Juan Alberto Romero González** · `CLI-9EDEKZ8OUNUR` · Querétaro, México · DNI ••••4840 · Premium · Active · score 812 · income 306,753.45 MXN · lawyer.

- Savings ••••5725: 1,559.57 USD, rate 1.15%.
- Mortgage LOAN-31561597: balance 109,159.57 USD, rate 8.38%, 0 days past due.
- No credit card.

**Juliana Castro Gómez** · `CLI-MD60UR8PNJDI` · Ciudad de México · Plus · score 714 · income empty.

- Checking ••••7377: 2,528.58 USD.
- No credit card.

**Alicia Mariana Parra Álvarez** · `CLI-440CO5FZIY6A` · Cali, Colombia · CC ••••5213 · Basic · score 615 · income 4,707,334.28 COP · engineer.

- Checking ••••2955: 13,192,324.57 COP.
- No credit card.

**Mariana Mónica Acosta Rojas** · `CLI-ZGOY1V6ZC46J` · Rosario, Argentina · DNI ••••9643 · Basic · score 515 · income 801,583.70 ARS.

- Credit card ••••5476: balance 111,079.25 ARS, limit 12,196,884.68 ARS, rate 21.08%, 180 days past due, Active.

**César González Sánchez** (consultant) · `AGT-OJ9N4FGYV9` · employee `E75612` · specialty Créditos · Senior · morning shift · CSAT 4.23 · Spanish. The mock uses him. He is not the only consultant.

A consultant is a bank employee who reviews the cases the assistant hands off. The dataset calls them service agents, and `db/` and `pipeline/` keep that name: the table and file `service_agents`, the columns `agent_id` and `agent_status`, and the `AGT-` ids. The API, the web app, the wire contract, events, rules, and docs say consultant; the screens say "asesor". The word agent is left for the AI agent (`AGENTS.md`, "Consultants and service agents").

## Closed stack

| Layer | Choice |
|---|---|
| API language | Python 3.12 |
| HTTP | FastAPI |
| Validation | Pydantic v2 |
| Frontend | TypeScript, React, Vite. One app |
| Database | PostgreSQL 16 as a service of the same `docker compose` stack. No managed database. The schema lives in `db/migrations/` |
| How it runs | `docker compose up` applies the schema, downloads the missing CSVs, and builds the profile. Nobody runs SQL by hand. Reviewers (and anyone else) run that stack locally and open the app in the browser. There is no cloud deploy for the submission. `docs/ops.md` will list optional steps if a host is used later |
| Auth | Customers: document number plus a one-time code emailed to the address on file. Consultants: email and employee code plus the same kind of code. Mailpit receives every code in the compose stack. Then an own JWT, HS256, 15 minutes, issued by this API |
| Pipeline | Python, in the `load` container. Reads local CSVs. DuckDB only if the aggregate needs it; the result lands in Postgres |
| LLM | OpenAI API, model `gpt-6-luna` (GPT-6 Luna). The adapter `api/infrastructure/llm/conversation.py` makes one call with Structured Outputs (the `ConversationTurn` JSON schema) and returns `ConversationTurn`. The policy does not use this adapter |
| Tests | pytest in the API. Vitest only if the client has logic; business logic does not live in the client |
| Running processes | A loop inside the API process that takes `commands` rows with `status = pending`. No Kafka, no Redis, no Inngest |

## File tree

```
api-spec/
  openapi.yaml            # wire contract; generate both clients from this file
  generate.py
api/
  main.py                 # process: opens the pool, includes the routers
  contract_models.py      # generated from api-spec/openapi.yaml
  domain/                 # pure rules. No FastAPI, no psycopg, no settings
    session/
      codes.py            # one-time code: hash, 10 minutes, five wrong tries
      tokens.py           # JWT and session claims
    customers/
      identity.py         # CustomerIdentity and the search hit
    consultants/
      identity.py         # ConsultantIdentity and the search hit
      login.py            # the login key (trimmed, case ignored) and who can receive a code (Active)
    search.py             # exactly one search criterion, for both demo searches
    policy/               # credit rules, when that component is built
      engine.py           # pure function
      alba-credit-v1.yaml # rules and thresholds
      templates.py        # certificate, ES and PT
    process/
      rules.py            # pure match over the event already written, when the cycle is built
  application/            # one file per use case. Defines the ports
    session/
      ports.py
      issue_code.py
      open_session.py
      read_current_customer.py
      read_current_consultant.py
    customers/
      search_customers.py
    consultants/
      search_consultants.py
    processes.py          # start, transition, end, when that component is built
  infrastructure/
    config/settings.py    # env, including DB_POOL_MIN and DB_POOL_MAX
    db/
      pool.py             # connection pool, opened in the process lifespan
      login_codes.py      # SQL for login_codes
      customers.py        # SQL for customers
      consultants.py      # SQL for service_agents
      search.py           # the demo search limit and LIKE escaping, shared by both searches
      events.py           # append to events, when that component is built
      profile.py          # gold by customer_id, when that read is built
      products.py
      catalog.py
    mail/smtp.py          # sends the login code by SMTP; the only module that opens SMTP
    llm/                  # the only module that imports the OpenAI SDK, when the model is built
      conversation.py     # one call, JSON schema
      schema.py           # ConversationTurn
  presentation/
    http/
      errors.py           # {error: ...} bodies for 401, 403, 404, 422
      dependencies.py     # wires a request to a use case. get_session lives here
      routes/             # session (/session and /consultant/session), customers (/me and /customers), consultants (/consultant/me and /consultants), config, health
    worker/               # takes commands, when that loop is built
  fixtures/
    oracle_customers.json # the four profiles and César
web/
  src/api/client.ts             # openapi-fetch client, typed by schema.d.ts; adds the bearer token, ends the session on 401
  src/session/session.ts        # the session in sessionStorage; never renewed
  src/styles/tokens.css         # DESIGN.md tokens
  src/api/schema.d.ts           # generated from api-spec/openapi.yaml
  src/pages/Login.tsx           # customer login; shares LoginShell, IdentityForm, CodeStep with the consultant login
  src/pages/ConsultantLogin.tsx # email and employee code, then the code
  src/pages/Home.tsx
  src/pages/ConsultantHome.tsx  # greeting from GET /consultant/me until the queue is built
  src/pages/Case.tsx            # customer: chat, plus the certificate if it exists
  src/pages/ConsultantQueue.tsx
  src/pages/ConsultantCase.tsx  # handoff packet and the two close actions
  src/pages/Trace.tsx           # the process's events table
pipeline/
  bronze.py
  silver.py
  gold.py
db/migrations/001_init.sql
db/migrations/002_login.sql
db/migrations/003_consultant_login.sql
eval/                       # comes later; does not block the flow
compose.yaml
docker/api.Dockerfile
docker/web.Dockerfile
docker/load.Dockerfile
.env.example                # no secrets; the real .env is not committed
mocks/index.html            # static walkthrough, not the frontend
```

A new capability adds a rule under `domain/`, a use case under `application/`, a repository under `infrastructure/db/` when it reads Postgres, and a route under `presentation/http/routes/`. It does not add another kind of folder.

The client does not compute the policy. It renders what the API returns: products, messages, certificate, process state.

## Process-native loop

The system stores immutable events, rules that look at an event, queued commands, and a process row that is the projection. When the worker finishes a command, it writes another event. This repo runs that same cycle with one process and no organizations.

```
HTTP message
  → insert events (fact)
  → match_rules(event) → commands rows
  → worker runs the command
  → the command may insert another event and change processes.state
  → match_rules on that new event
```

Forbidden in `match_rules`: a `SELECT` on `customers`, `products`, or `customer_credit_profile`. If a condition needs that data, it is already inside `events.payload`, copied when the event was written.

Forbidden: the model handler calling the policy and also writing the state. Only the `policy.run` worker writes `analysis.completed`. Only the `process.transition` worker changes `processes.state`.

### Process

A catalog of one row.

| Field | Value |
|---|---|
| `process_key` | `credit_prequalification` |
| Initial state | `ai_active` |
| Who opens it | the first `conversation.message_received` from a customer with no open process |

States. There are no others.

| State | Who talks | What can happen |
|---|---|---|
| `ai_active` | the assistant, if a rule enqueues `conversation.generate` | clarify, ask for consent to run pre-qualification, ask for income, decide, hand off to a person |
| `human_active` | nobody in the thread | the customer may write and the message is stored; the model is not called. The consultant does not reply. The only action is to close with prequalified or not |
| `ended` | nobody | the certificate exists. A new message opens another process |

Allowed transitions. Any other is an error and is not written.

| From | To | `end_reason` | Trigger |
|---|---|---|---|
| `ai_active` | `ai_active` | none | clarification or `NEEDS_INFO` |
| `ai_active` | `ended` | `prequalified` | policy `PREQUALIFIED` |
| `ai_active` | `ended` | `not_prequalified` | policy `NOT_PREQUALIFIED` |
| `ai_active` | `human_active` | none | policy `REFER`, request for a human, tool failure, unsupported language |
| `human_active` | `ended` | `prequalified` or `not_prequalified` | the consultant closes with that choice |
| `ended` | none | none | not reopened. Another message creates a new process |

`reason_code` is a closed list: `customer_requested_human`, `out_of_scope`, `language_unsupported`, `model_output_invalid`, `tool_failed`, `policy_refer`, `reply_forbidden`. No others. The policy rule that fired stays on `deciding_rule` (R05, R06, and the rest). `policy_refer` is the one code for every policy `REFER`.

`started` is not persisted. The process `INSERT` is born in `ai_active`, and the `process.started` event records it.

The process row also holds `product` (`credit_card` | `personal_loan` | null) and `language` (`es` | `pt` | null). Both stay null until a turn sets them.

A customer has at most one process with `state <> 'ended'`. A partial unique index guarantees it.

### Consultant close

The consultant does not send messages, does not chat, and does not leave a comment that becomes an outcome. On a case in `human_active` the only action is `POST /consultant/case/:id/close`. The body is `outcome`: `PREQUALIFIED` or `NOT_PREQUALIFIED`. Any other body is rejected. There is no text field.

That POST writes `conversation.consultant_closed`, with `outcome`, `consultant_id`, and `language` copied from the process. The rule `close_on_consultant_decision` then enqueues two commands, in this order, before another event is taken:

1. `decision.render`. An automatic message to the customer for that outcome. The wording is not written in this contract yet. The model does not draft it. The row in `messages` has `author = template`. The event is `prequalification.decided` with `decided_by = consultant`.
2. `process.end`. `end_reason` is `prequalified` or `not_prequalified`, the same choice. The policy engine is not run again.

The same case cannot be closed twice. The event key is `consultant_close:{process_id}`.

## Events

Table `events`. Append-only. No `UPDATE` of `payload`.

Columns: `id uuid`, `event_name text`, `payload jsonb`, `customer_id text`, `process_id uuid`, `process_state text`, `actor text` (`customer` | `consultant` | `system` | `rule`), `caused_by_event_id uuid`, `caused_by_command_id uuid`, `idempotency_key text unique`, `created_at timestamptz`.

`process_id` and `process_state` are columns. They are not payload fields. The customer does not send them.

Closed names. No others are invented in v1.

| `event_name` | When it is written | Minimum payload |
|---|---|---|
| `conversation.message_received` | `POST /messages` | `text`, `client_message_id` |
| `conversation.turn_classified` | `conversation.generate` finished | `intent`, `product`, `language`, `declared_income_amount`, `declared_income_currency`, `reply_text`, `reply_ok`, `reason_code` |
| `conversation.template_sent` | a non-terminal template was sent | `locale`, `template_id`, `body` |
| `conversation.consultant_closed` | the consultant closes the case | `outcome`, `consultant_id`, `language` |
| `conversation.thread_taken` | the transition to `human_active` | `reason_code`, `from_state`, `to_state` |
| `analysis.completed` | `policy.run` finished | `policy_version`, `product`, `outcome`, `deciding_rule`, `rule_trace`, `facts`, `language` |
| `prequalification.decided` | the certificate template was rendered | `locale`, `template_id`, `outcome`, `body`, `decided_by` |
| `process.started` | the process was inserted | `process_key`, `customer_id` |
| `process.state_changed` | `processes.state` changed | `from_state`, `to_state`, `end_reason` |
| `process.ended` | reached `ended` | `end_reason`, `policy_version` |

`rule_trace` is a list of `{rule_id, input, result}`. `result` is `passed`, `self_declared`, or an outcome, as defined under Policy `alba-credit-v1`. `facts` cites column and value, for example `{name: "credit_score", value: 812, source: "customer_credit_profile.credit_score", as_of: "2026-06-17"}`.

Idempotency keys:

| Action | Key |
|---|---|
| Customer message | `msg:{client_message_id}` |
| Classified turn | `turn:{triggered_by_event_id}` |
| Template sent | `template:{template_id}:{triggered_by_event_id}` |
| Open process | `process:{customer_id}:credit_prequalification:{triggered_by_event_id}` |
| Run policy | `policy:{process_id}:alba-credit-v1:{product}` |
| Transition | `transition:{process_id}:{to_state}:{caused_by_event_id}` |
| Consultant close | `consultant_close:{process_id}` |
| End process | `end:{process_id}` |

The frontend sends `client_message_id` (one uuid per send). The message key is that uuid. It does not wait for a `process_id`. Repeating the POST creates no new event and no new decision.

When `conversation.message_received` is inserted, the API stamps the two columns:

- If the customer already has a process with `state <> 'ended'`, `process_id` is that process and `process_state` is its state.
- If not, `process_id` stays null and `process_state` is `ai_active`, the state a new process is born in. The event does not open the process. The `open_process` rule does.

The message is an event. It is not the case. The case is the process. A new thread is born `ai_active`, so the model rule matches the first message of a new case. The customer message is not copied into a second event.

`conversation.generate` writes `conversation.turn_classified` and does not enqueue the next command. Rules on that event do. When the message column `process_id` is set, the turn copies it. When that column is null, the turn takes the id of the process `process.start` just inserted in this same cycle, the one open process for that `customer_id`. The first message is always the customer's. The partial unique index makes a second open process impossible. The message row is not updated.

`reply_ok` is false when `reply_text` contains `precalifica`, `no precalifica`, `pré-qualificado`, or `não pré-qualifica`, and when the JSON does not validate. That text is not shown. `reason_code` on the turn is `reply_forbidden` or `model_output_invalid`. Otherwise `reason_code` is null and `reply_ok` is true.

If the model sends no product and the process already has one, the turn's `product` is the stored one. If the turn's `product` is set, the process stores it. The turn's `language` is stored on the process.

## Process rules

Source: `api/rules.py`. An in-memory list, sorted by ascending `priority`. There is no `rules` table in v1 and no per-organization override. Each rule appears once; a copy would fire twice.

A rule is `{id, trigger_event_name, when, actions}`. `when` is a pure function over the event. `actions` is an ordered list of commands.

| Id | Trigger | When | Commands |
|---|---|---|---|
| `open_process` | `conversation.message_received` | the `process_id` column is null | `process.start` |
| `generate_while_ai` | `conversation.message_received` | the `process_state` column is `ai_active` | `conversation.generate` |
| `record_only_when_human` | `conversation.message_received` | the `process_state` column is `human_active` | none. The message is already in the event |
| `ask_confirm_prequalify` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `prequalify_card` or `prequalify_loan` | `template.send` for `confirm_prequalify`. Stores the product on the process. Stays `ai_active`. The policy is not called |
| `run_policy` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `confirm_prequalify` and `product` is set | `policy.run` with that `product` |
| `decline_prequalify` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `decline_prequalify` | `conversation.show_reply`. Stays `ai_active`. The policy is not called |
| `run_policy_income` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `provide_income` and `product` is set | `policy.run` with that `product` and the declared amount |
| `ask_which_product` | `conversation.turn_classified` | `reply_ok` and `intent` is `provide_income` or `confirm_prequalify` and `product` is null | `template.send` for `which_product`. Stays `ai_active`. The policy is not called |
| `hand_off_human` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `human_request` | `process.transition` to `human_active`, `reason_code = customer_requested_human` |
| `hand_off_scope` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `out_of_scope` | `process.transition` to `human_active`, `reason_code = out_of_scope` |
| `hand_off_language` | `conversation.turn_classified` | `reply_ok` and `language` is `other` | `process.transition` to `human_active`, `reason_code = language_unsupported` |
| `hand_off_reply` | `conversation.turn_classified` | `reply_ok` is false | `process.transition` to `human_active`, with the turn's `reason_code`. `reply_text` is not shown |
| `show_reply` | `conversation.turn_classified` | `reply_ok` and `language` is `es` or `pt` and `intent` is `clarify`, `product_info`, or `chit_chat` | `conversation.show_reply`. The policy is not called |
| `render_needs_info` | `analysis.completed` | `outcome == "NEEDS_INFO"` | `template.send` for `needs_income`. Stays `ai_active` |
| `render_refer_notice` | `analysis.completed` | `outcome == "REFER"` | `template.send` for `refer_notice`. The notice does not include the score and does not say whether the customer pre-qualifies |
| `take_thread` | `analysis.completed` | `payload.outcome == "REFER"` | `process.transition` to `human_active`, `reason_code = policy_refer`; that command writes `conversation.thread_taken` |
| `render_decision` | `analysis.completed` | `outcome` is `PREQUALIFIED` or `NOT_PREQUALIFIED` | `decision.render`, with `decided_by = policy` |
| `end_after_decision` | `prequalification.decided` | `payload.decided_by == "policy"` | `process.end` |
| `close_on_consultant_decision` | `conversation.consultant_closed` | `outcome` is `PREQUALIFIED` or `NOT_PREQUALIFIED` | `decision.render` with `decided_by = consultant`, then `process.end` |

`generate_while_ai` does not run if the `process_state` column is `human_active`. The prompt is not the brake.

The first message of a new case is stamped `ai_active` with `process_id` null. Both `open_process` and `generate_while_ai` match. The loop inserts those commands in the order of the table and runs them in that order before taking another event. `process.start` creates the process. Then `conversation.generate` classifies the sentence and writes the turn with that new `process_id`.

## Commands

Table `commands`: `id`, `command_name`, `payload jsonb`, `triggered_by_event_id`, `emitted_by_rule_id`, `idempotency_key unique`, `status` (`pending` | `done` | `failed`), `attempt_count int`, `last_error text`, `created_at`.

The worker takes `pending` rows with `FOR UPDATE SKIP LOCKED`, increments `attempt_count`, runs the command, and marks it `done` or `failed`. At most 3 attempts. On the third failure it writes a handoff event and transitions to `human_active` with `reason_code = tool_failed`. It does not retry in a loop.

| `command_name` | Does | Does not |
|---|---|---|
| `process.start` | inserts `processes` and `process.started` | call the model |
| `process.transition` | changes `state`, writes `process.state_changed` and, if the target is `human_active`, `conversation.thread_taken` | call the model |
| `process.end` | `state = ended`. Writes `process.state_changed` and `process.ended`, both with the same `end_reason` | call the model, and does not run the policy again |
| `conversation.generate` | one LLM call, persists the JSON, writes `conversation.turn_classified`. If the message `process_id` is null, the turn uses the process this cycle just opened for that customer. Stores `language` and, when set, `product` on the process | write `analysis.completed`, enqueue `policy.run` or `process.transition`, copy the customer message, update the message row |
| `conversation.show_reply` | inserts `messages` with `author = assistant` and the turn's `reply_text` | call the model |
| `template.send` | writes `conversation.template_sent`. `template_id` is `needs_income`, `refer_notice`, `which_product`, or `confirm_prequalify`. Locale comes from the triggering event's `language` | call the model, end the process. The sentences are not written in this contract yet |
| `policy.run` | reads the profile by the event's `customer_id`, runs the engine, writes `analysis.completed`, and copies `language` from the triggering turn | write the certificate |
| `decision.render` | reads `language` from the triggering event, picks the ES or PT template, writes `prequalification.decided` | call the model. The consultant-path sentences are not written in this contract yet |

Order inside `policy.run`: read profile → engine → insert the event. Whether the engine returns `PREQUALIFIED`, `NOT_PREQUALIFIED`, `REFER`, or `NEEDS_INFO`, the worker interprets nothing more. The rules above react to the new event.

## Policy `alba-credit-v1`

File `api/domain/policy/alba-credit-v1.yaml`. Function `decide(profile, product, declared_income) -> Decision`. `product` is `credit_card` or `personal_loan`. `declared_income` is the amount stated for this run, in the profile's `income_currency`, or null when none was stated. Zero is an amount. A negative or non-finite amount is not an income: `decide` rejects it, and the caller does not pass one. The function does not change the profile: a stated amount leaves `income_local` null.

Input `profile`, already materialized in `customer_credit_profile`:

| Field | Source |
|---|---|
| `customer_status` | `customers.customer_status` |
| `credit_score` | `customers.credit_score`, null if empty |
| `income_local` | `customers.estimated_monthly_income`, null if empty |
| `income_currency` | MXN if `country = México`, COP if Colombia, ARS if Argentina |
| `income_usd` | `income_local * exchange_rate` for June 17, 2026, `source_currency` local, `target_currency` USD. Null if income is missing |
| `max_days_past_due` | max `days_past_due` over active products whose `product_type` is `Tarjeta Crédito`, `Préstamo Personal`, or `Préstamo Hipotecario`. Empty counts as 0 |
| `holds_product` | the gold boolean of the requested product: `has_active_card` or `has_active_personal_loan`. Cached from `products`. The source stays `products` |
| `as_of` | `2026-06-17` |

Exchange rates for that day, read from `daily_exchange_rates` (USD per one unit of local currency): 1 MXN = 0.058641 USD, 1 COP = 0.000248 USD, 1 ARS = 0.002873 USD.

Evaluation order. `rule_trace` lists every rule that was evaluated, in this order, and stops at the first terminal result. Later rules are not evaluated. `result` is a closed set: `passed` when the rule was evaluated and did not close, `self_declared` when R06 takes a stated amount and evaluation continues, or one of `PREQUALIFIED`, `NOT_PREQUALIFIED`, `REFER`, `NEEDS_INFO` when the rule closes. `PREQUALIFIED` is reached only when every earlier rule returned `passed` (or R06 returned `self_declared` for a stated amount) and R05 then closes on a score of 620 or more.

| Id | Condition | Terminal |
|---|---|---|
| R01 | `customer_status` is `Suspended` or `Inactive` | `REFER` |
| R01 | `customer_status` is `Closed` | `NOT_PREQUALIFIED` |
| R02 | `max_days_past_due >= 30` | `NOT_PREQUALIFIED` |
| R03 | `max_days_past_due` between 1 and 29 | `REFER` |
| R09 | `holds_product` is true | `REFER` |
| R04 | `credit_score` is null | `REFER`. The customer is not asked for their score |
| R06 | `income_local` is null and the message carries no declared income | `NEEDS_INFO` |
| R06 | `income_local` is null and the message carries declared income | not terminal. That amount is this run's income, marked `self_declared`. The gold row stays null. Evaluation continues |
| R05 | score < 580 | `NOT_PREQUALIFIED` |
| R05 | score between 580 and 619 inclusive | `REFER` |
| R05 | score >= 620 | `PREQUALIFIED` |

When `income_local` is present, a number typed in the message is ignored. The file is the income for the run. R06 does not fire.

### What the customer can be asked

Three things, and no others.

| Asked | When |
|---|---|
| Which product, credit card or personal loan | the turn names no product |
| Whether to start this run's pre-qualification | the turn is `prequalify_card` or `prequalify_loan` (product known). Soft consent before any `policy.run` for that product request |
| Monthly income | `income_local` is null after a consented `policy.run` returned `NEEDS_INFO` |

The income amount is read in the country's currency. The gold row is not filled in.

The customer is not asked for `credit_score`, `days_past_due`, `customer_status`, or whether they already hold the product. Those stay on the file. A null score is `REFER` with no question.

Consent is once per product request on the process. A `confirm_prequalify` is what first enqueues `policy.run`. A later `provide_income` on the same process does not ask again. `decline_prequalify` leaves the process `ai_active`; a later `prequalify_card` or `prequalify_loan` asks for consent again.

Once those asks are done for this case, the engine runs. `PREQUALIFIED` and `NOT_PREQUALIFIED` end it. `REFER` goes to the consultant. There is no further question.

No other bank action exists in this demo. There is no money movement and no account change. The only action that requires confirmation is starting the (simulated) pre-qualification.

R07 and R08 do not exist in the code. An income threshold or a `k * income` limit is not implemented. The certificate carries no limit amount and no rate for the new product.

`Decision` holds `outcome`, `deciding_rule`, `rule_trace`, `facts`, `policy_version = "alba-credit-v1"`.

`facts` cites the column of the rule that closed, with its value and `as_of`. When R06 returned `self_declared`, that income is also cited, ahead of the closing fact: `{name: "income_local", value: the amount, source: "self_declared", as_of: the profile's as_of}`. A stated amount while `income_local` is present is ignored: R06 returns `passed`, its `input` records both numbers, and no `self_declared` fact is written. File income is cited as `customer_credit_profile.income_local`. `holds_product` is cited with source `products`. The other facts use the profile column.

Templates in `templates.py`, two locales: `es` and `pt`. The Portuguese is text written by the team; the dataset has none. The template receives the `Decision` and builds the paragraph. The model does not see this step.

Outcome phrases the template may emit, and the model is forbidden to emit on its own: `precalifica`, `no precalifica`, `pré-qualificado`, `não pré-qualifica`.

## How the model is called

The model is GPT-6 Luna on the OpenAI API, model id `gpt-6-luna`. It only classifies the sentence and drafts the clarification. Juan pre-qualifies the same with this model or with the test JSON, because `api/domain/policy/engine.py` decides that.

`OPENAI_API_KEY` lives in `.env`. It never enters git, the image, a log, or a prompt. `LLM_MODEL` defaults to `gpt-6-luna`. Only `api/infrastructure/llm/conversation.py` imports the OpenAI SDK. Whether it calls Chat Completions or Responses is an adapter detail: both support Structured Outputs for this model.

If the key is missing, Postgres, login, and the policy still start. `conversation.generate` fails with an error that says the key is missing. A failed API call (timeout, rate limit, server error) is a failed attempt of the command, under the worker's limit of 3 attempts; after the third, `human_active` with `reason_code = tool_failed`. The model is not silently replaced with another one.

The model is called only from `conversation.generate`, and only if the `generate_while_ai` rule enqueued that command.

One call, no streaming, Structured Outputs with the `ConversationTurn` JSON schema. `temperature` 0 if the model accepts it; GPT-6 Luna is a reasoning model and its docs do not say (`PLAN.md` R11). The response must also validate as `ConversationTurn` in Pydantic. If it does not, one retry. If the second also fails, the turn is written with `reply_ok` false and `reason_code = model_output_invalid`. `hand_off_reply` moves the case to `human_active`. The request and the raw response are stored in `llm_turns` either way, including when parsing fails, with the model id and token usage. pytest does not call OpenAI: it injects the JSON.

```text
ConversationTurn
  intent: product_info | prequalify_card | prequalify_loan | confirm_prequalify
          | decline_prequalify | provide_income | human_request | out_of_scope
          | clarify | chit_chat
  product: credit_card | personal_loan | null
  declared_income_amount: number | null
  declared_income_currency: MXN | COP | ARS | null
  language: es | pt | other
  needs_clarification: bool
  clarification_question: string | null
  reply_text: string
```

What goes into the prompt. This is everything that leaves the service for OpenAI; the brief forbids private records in external model requests.

- The message text, as the customer typed it. Whether ID-like numbers in it are masked first is open (`PLAN.md` D11).
- The process state.
- Booleans: `income_on_file`, `score_on_file`, `has_active_card`, `has_active_personal_loan`. Not the amounts, the score, the days past due, the full name, the document, the email, or the address.
- The catalog: two products, names in Spanish and Portuguese, no rates.
- The instruction not to state eligibility or a limit. If `reply_text` contains those phrases, the turn is written with `reply_ok` false and `reason_code = reply_forbidden`. The text is not shown. `hand_off_reply` escalates.

`conversation.generate` stores the JSON and writes the turn. It does not choose the next command. The rules on `conversation.turn_classified` do. A clarification ("tarjeta o préstamo") may be `reply_text`. `language` is set by the model on every turn (`es`, `pt`, or `other`); that is how the locale for templates is chosen. `language = pt` continues, and the certificate uses the `pt` template. Portuguese template sentences are team-written; the dataset has none. Portuguese eval utterances are team-written or machine-translated and disclosed as a limitation (`PLAN.md` D6).

`prequalify_card` and `prequalify_loan` do not run the policy. They store the product and trigger `confirm_prequalify` (template). Only `confirm_prequalify` with a product set enqueues `policy.run`. `decline_prequalify` shows the model's `reply_text` and leaves the case open.

`out_of_scope` covers a new mortgage, investments, a limit increase, disputing a transaction, a third party's balance, and "el crédito" when it still names no product after one clarification. The first time the customer says only "un crédito", the intent is `clarify`, not `out_of_scope`.

The model gets no tool that accepts a `customer_id`. There is no tool-calling into the policy. The policy is not a model tool: it is a command that runs afterwards, with the session's id.

### Prompt-injection defense

Defense is structural, not a second classifier. The model sees only booleans, process state, the catalog, and the message text. It has no tools. `customer_id` comes from the JWT. Forbidden eligibility phrases in `reply_text` set `reply_forbidden` and escalate. Held-out eval includes injection and cross-customer attempts (`PLAN.md` §7). No input-heuristic guard and no separate injection model are part of this contract.

### Risk estimate

Conversation, risk estimate, and eligibility stay separate. The risk estimate is the dataset's `credit_score` (treated as an external bureau-style score already on the gold row). `alba-credit-v1` reads that field in R04/R05; it does not compute a score. No delinquency or PD model is shipped. The model card for the rejected delinquency probe lives in `docs/model_card_risk.md` when written.

### Learned component (evaluation)

The learned component evaluated against a baseline is the `ConversationTurn` classifier (`gpt-6-luna` via Structured Outputs): intents including product, consent (`confirm_prequalify` / `decline_prequalify`), clarify, and out-of-scope. The baseline is B0, a keyword-rules bot, on the same team-labeled held-out set. There is no separate intent router in the runtime. Labels and splits are team-generated; customers used while tuning prompts are disjoint from the held-out set (`PLAN.md` §7).

### UI wait state

While the client waits for the API after a customer send, the chat shows a typing indicator ("escribiendo…"). That covers real model and worker latency. The UI does not add a fixed sleep to "give the model time"; language and intent are classified inside the same `conversation.generate` call that produces the turn.

## Auth and screens

A customer logs in with their document number, and a one-time code sent to the email on file proves it is them. The document says who someone claims to be; the code opens the session.

- `POST /session/code` takes `document_number`. When it matches a customer with an email, the API stores a 6-digit code for that customer in `login_codes`, valid 10 minutes, and emails it to that address. A new request replaces any unused code for the same customer.
- The answer is the same whether or not the document matches and whether or not the customer has an email: `{expires_in_seconds: 600}`. It never carries the code, the address, or the name, so the form cannot be used to learn who is on file.
- `POST /session` takes `document_number` and `code`. It opens a session only when the code is the latest unused one for that customer, is under 10 minutes old, and has had fewer than 5 wrong tries. The fifth wrong code spends it. Every failure is the same 401. A used code does not open a second session.
- Claims: `sub` = `customer_id`, `role` = `customer`, `exp` 15 minutes. The JSON repeats `sub` and `role` next to `token`.
- `login_codes` stores a hash of the code, never the code. The code is not logged.

The email is Spanish copy written in `api/infrastructure/mail/smtp.py`: the code and its 10-minute validity. It goes out by SMTP. The compose stack sends only to Mailpit, a local mail catcher, and anyone trying the demo reads the code in its inbox at http://localhost:8025. Nothing leaves the machine. The dataset's addresses use real domains (gmail.com, yahoo.com, and others), so the stack must never point SMTP at a real provider while it holds this dataset.

Email is the channel, not the identifier. 24,203 addresses are shared by 2 to 31 customers, 79,930 rows in all, Juliana's and Mariana's among them (`PLAN.md` §4.3). `document_number` is unique. The 2,984 customers with no email (2.0%) cannot log in: their request gets the same answer and no code. That one answer tells anyone who gets no code to register an email at a branch (`DESIGN.md`, "Login"); it does not single them out. That is a stated limitation.

Demo helpers. With `DEMO_LOGIN=1`, `GET /customers/search?q=` searches by name, document, or `customer_id`, limit 20, ordered by `last_name`, `first_name`, `customer_id`, and `GET /customers/search?random=true` returns one customer with an email on file, at random. The login screen uses them only to fill the document field; the code still goes by mail. `GET /consultants/search?q=` and `GET /consultants/search?random=true` do the same over `Active` consultants only, by name, employee code, or `consultant_id`, ordered by `last_name`, `first_name`, `consultant_id`. They also return the email, so a pick fills both fields of the consultant login; the code still goes by mail. With `DEMO_LOGIN` off those routes are 404. `GET /config` tells the web app whether the helpers are on. The local compose stack sets `DEMO_LOGIN=1`.

Consultants log in on their own page, `/consultant/login` (`PLAN.md` D18, decided and built Sep 30), and land on `/consultant`. The consultant types their email and employee code. Neither is unique alone (13 employee codes and 12 emails are each shared by two consultants), but the pair is unique for all 1,200, also with case ignored. The API trims both fields and compares the email in lower case and the employee code in upper case. A unique index on that pair keeps it unique.

- `POST /consultant/session/code` takes `email` and `employee_code`. When the pair matches a consultant whose `agent_status` is `Active` (1,090 of 1,200), the API emails a 6-digit code to that address with the customer code's rules: 10 minutes, latest code only, five wrong tries, one use, stored hashed. The answer is `{expires_in_seconds: 600}` for every pair and every status, so a consultant on `Vacation`, `Leave`, or `Inactive` gets no code and no hint.
- `POST /consultant/session` takes `email`, `employee_code`, and `code`. The pair must still match an `Active` consultant. Every failure is the same 401. Claims: `sub` = `consultant_id`, `role` = `consultant`, `exp` 15 minutes. A customer code does not open a consultant session, and a consultant code does not open a customer session.
- `GET /consultant/me` gives the consultant screens the name, `employee_code`, and `specialty`, which is null for the 476 consultants the file gives none.

The consultant's email is the same Spanish message as the customer's. Each login page links to the other: "Acceso para asesores" on `/login`, "Acceso para clientes" on `/consultant/login`. One browser tab holds one session; logging in on the other page replaces it.

Expired JWT: 401. The customer sees that the session ended. It is not silently renewed during the case being shown.

| Frontend route | Who | What it renders |
|---|---|---|
| `/login` | customer | document number, then the code from the email. The demo helpers when `DEMO_LOGIN=1` |
| `/consultant/login` | consultant | email and employee code, then the code from the email. The demo helpers when `DEMO_LOGIN=1` |
| `/` | customer | their products, in the row's currency |
| `/case/:id` | customer | thread, plus the certificate if `prequalification.decided` exists |
| `/consultant` | consultant | processes in `human_active` |
| `/consultant/case/:id` | consultant | the handoff packet read from `analysis.completed`, and two actions: prequalify or do not. No reply box |
| `/consultant/case/:id/trace` | consultant | the process's `events`, in order |

A customer whose process is `ended` with `prequalified` or `not_prequalified` sees the certificate. They do not see the queue. The consultant does not see `ended` processes in the queue. Juan does not appear in César's queue. Neither does Mariana. Alicia does.

Currency on the home screen: the row's `products.currency` column. For customers in Mexico the file stores those balances in USD. They are not converted to MXN for display. On the certificate, income is shown in local currency with the USD equivalent and the exchange-rate date beside it. Alicia in COP. Mariana in ARS.

## HTTP contract

`api-spec/openapi.yaml` is the wire contract. `python api-spec/generate.py` writes `api/contract_models.py` and `web/src/api/schema.d.ts`, and appends to the Python file a named `Literal` alias for every string enum in the spec (`Role`, `ProcessState`, `Outcome`, and the rest). Python code imports those aliases and does not declare the same list again. Handlers type requests and responses with the generated models. The web client is `web/src/api/client.ts` (`openapi-fetch` over those types). A hand-written DTO for one of these bodies is a bug. FastAPI does not publish a second OpenAPI document.

Regenerate after every edit to `openapi.yaml`. `api/tests/test_contract.py` fails if the generated files do not carry the spec hash, if a path appears or disappears, if a live route is missing from the spec or returns a model from anywhere else, or if a string enum has no alias.

| Method and path | Who | Body in | Body out |
|---|---|---|---|
| `GET /health` | public | | `{status: ok}` |
| `GET /ready` | public | | `{status: ready}` or 503 `{status: not_ready, error}` |
| `GET /config` | public | | `{demo_login}` |
| `GET /customers/search?q=` or `?random=true` | public, only with `DEMO_LOGIN=1` | | up to 20 `{customer_id, document_number, first_name, last_name, country}`; one for `random`. 404 when off |
| `POST /session/code` | public | `{document_number}` | `{expires_in_seconds: 600}`, the same for every document |
| `POST /session` | public | `{document_number, code}` | `{token, sub, role}`. 401 for any failure |
| `GET /consultants/search?q=` or `?random=true` | public, only with `DEMO_LOGIN=1` | | up to 20 `Active` consultants `{consultant_id, employee_code, first_name, last_name, email}`; one for `random`. 404 when off |
| `POST /consultant/session/code` | public | `{email, employee_code}` | `{expires_in_seconds: 600}`, the same for every pair and status |
| `POST /consultant/session` | public | `{email, employee_code, code}` | `{token, sub, role}`. 401 for any failure |
| `GET /me` | customer | | `{customer_id, first_name, last_name}` of the token's customer. The login responses never carry a name |
| `GET /consultant/me` | consultant | | `{consultant_id, employee_code, first_name, last_name, specialty}` of the token's consultant. `specialty` may be null |
| `GET /products` | customer | optional `customer_id` query | that customer's products, or `[]` if the query id is not the token `sub` |
| `POST /messages` | customer | `{text, client_message_id}` | the `Case` after the worker finishes that cycle's commands |
| `GET /case/{process_id}` | customer | | `Case` for the token's customer. Another customer's id is 404 |
| `GET /consultant/queue` | consultant | | processes in `human_active` |
| `GET /consultant/case/{process_id}` | consultant | | handoff packet. 404 unless the process is `human_active` |
| `GET /consultant/case/{process_id}/trace` | consultant | | events, discriminated on `event_name` |
| `POST /consultant/case/{process_id}/close` | consultant | `{outcome}` | ended process. 409 if it was already ended |

A customer token on a consultant route is 403. A consultant token on a customer route is 403. Expired or missing token is 401. A body that is not in the schema is 422 `invalid_body`.

`GET /products` returns `product_id`, `product_type` (the dataset literal), `product_number`, `currency`, `current_balance`, `product_status`, ordered by `product_id`. It does not return `days_past_due`, `credit_limit`, or `interest_rate`.

`POST /messages` appends `conversation.message_received` and does not choose an outcome. The response waits until the worker has finished the commands enqueued from that event. The same `client_message_id` returns the case again and appends nothing.

`Case.messages` is one list. Customer lines are the `conversation.message_received` events for that process, including the opening message reached only by `process.started.caused_by_event_id` when that event's `process_id` is null. Assistant and template lines are `messages` rows. A row with a null `event_id` is omitted and logged, not attached by time. Order is the linked event's `created_at`, then event `id`.

`Case.certificate` is null until `prequalification.decided` exists. It carries `locale`, `outcome`, `body`, `product`, and the income fields copied from `analysis.completed` facts named `income_local`, `income_currency`, and `income_usd`. `as_of` is the `as_of` of the `income_local` fact. A missing fact is null. The certificate has no credit limit and no rate. It does not include the score or the deciding rule.

The consultant queue is ordered by `processes.created_at`, then process id. Each item carries the customer name, `product`, `reason_code` from `conversation.thread_taken`, and `language`.

The packet copies `product`, `credit_score`, the income fields, `deciding_rule`, `policy_version`, and `outcome` from `analysis.completed`. Those fields are null when that event does not exist. `reason_code` comes from `conversation.thread_taken`.

The trace includes events with this `process_id`, plus that one opening message by `caused_by_event_id`. Order is `created_at`, then event `id`. `rule_trace.input` is an open object (`dict[str, Any]` in the generated model): the engine records the condition snapshot, and no matcher branches on it.

`POST /consultant/case/{process_id}/close` accepts only `PREQUALIFIED` or `NOT_PREQUALIFIED`. A text field is rejected. A process that is not `human_active` is 404, except one already `ended`, which is 409 and does not append a second `conversation.consultant_closed`.

## Database

PostgreSQL 16. `load` is the only process that reads S3. The API and `policy.run` read Postgres.

`db/migrations/001_init.sql` creates the four read tables, gold, the cycle tables, and `load_batches`. `002_login.sql` adds `customers.email`, makes `document_number` unique, turns `login_codes` into hashed codes with wrong tries and use, and clears `load_batches` so an already loaded volume reloads with email. `003_consultant_login.sql` adds `service_agents.email`, `agent_status`, and `specialty` and the unique login pair, and clears `load_batches` the same way. The API process keeps a Postgres pool (`DB_POOL_MIN` 1, `DB_POOL_MAX` 10 unless the environment says otherwise). Repositories receive a connection from that pool. They do not open one.

### Read tables

Copied from the four CSVs. Other columns in the data dictionary are not copied.

| Table | Columns |
|---|---|
| `customers` | `customer_id`, `document_number`, `first_name`, `last_name`, `email`, `country`, `segment`, `credit_score`, `estimated_monthly_income`, `customer_status` |
| `products` | `product_id`, `customer_id`, `product_type`, `product_number`, `currency`, `current_balance`, `product_status`, `days_past_due` |
| `daily_exchange_rates` | `date`, `source_currency`, `target_currency`, `exchange_rate` |
| `service_agents` | `agent_id`, `employee_code`, `first_name`, `last_name`, `email`, `agent_status`, `specialty` |

### Gold

`customer_credit_profile` is one row per `customer_id`. Columns: the policy inputs, plus `country`, `segment`, `first_name`, `last_name`, `as_of`, `batch_id`, `has_active_card`, `has_active_personal_loan`.

Those two booleans are a cache of `products` for the two products in this version. `holds_product` at decide time is the boolean of the requested product. The source stays `products`. A new product type is computed from `products`. It does not add another boolean.

The customer API does not list this table. `policy.run` reads one row, the one for the event's `customer_id`.

### Cycle

- `events`, `processes`, `commands`, `login_codes`, `llm_turns`, `messages`. Column lists for `events` and `commands` are in those sections.
- `processes` also holds `product` and `language`, null until a turn sets them
- `messages`: `id`, `process_id`, `author` (`customer` | `assistant` | `template`), `body`, `event_id`
- `llm_turns`: `id`, `process_id`, `command_id`, `request jsonb`, `raw_response text`, `parsed jsonb`, `parse_ok bool`, `model text`, `input_tokens int`, `output_tokens int`, `latency_ms int`, `created_at`
- `login_codes`: a hash of the 6-digit code, the customer or consultant it belongs to, the 10-minute expiry, the count of wrong tries, and when it was used
- `load_batches`: `path`, `bytes`, `sha256` of each file on disk

### Indexes

- `customers`: primary key `customer_id`, unique index on `document_number`, index on `(last_name, first_name)`
- `products (customer_id)`
- `service_agents`: primary key `agent_id`, unique index on `(lower(email), upper(employee_code))`
- `customer_credit_profile`: primary key `customer_id`
- `commands (status)` where `status = 'pending'`
- `events (process_id, created_at)`
- a partial unique index on `processes (customer_id, process_key) where state <> 'ended'`

The filter `customer_id = jwt.sub` is in every API query. A test calls `products` with Juan's JWT and asks for Alicia's id: the response carries no rows of Alicia's.

Raw CSVs are not committed. They live in `data/raw/`, which `.gitignore` excludes. S3 keys and the OpenAI key live only in `.env`: never in the repo, the image, or the prompt.

## Docker

`docker compose up` leaves the demo usable in the browser. Postgres runs inside the same stack. There is no cloud deployment for the submission (`PLAN.md` D2). Optional host steps, if someone later wants them, belong in `docs/ops.md` and are not required to try the project. Services:

| Service | Role | Keeps running |
|---|---|---|
| `postgres` | PostgreSQL 16, named volume | yes |
| `load` | waits for Postgres, applies `db/migrations/`, downloads CSVs if missing, fills the read tables and gold, exits with code 0 | no |
| `api` | starts when `load` finished successfully. Mounts `api/` and reloads on save | yes |
| `web` | the frontend, Vite, proxies `/api` to the API. Mounts `web/` and reloads on save | yes |
| `mailpit` | local mail catcher. The API's only SMTP target; its inbox is at http://localhost:8025 | yes |

Who runs it: anyone with the repo, a `.env`, and Docker. The default local demo sets `DEMO_LOGIN=1` and sends every login code to Mailpit. There is no SMS and no real email. Reviewers run `docker compose up` and open the web URL from the compose file. Secrets stay in `.env`; they are not committed.

With a `.env` holding `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-east-2`, `S3_BUCKET`, `OPENAI_API_KEY`, and `JWT_SECRET`, `docker compose up` needs no other command. `JWT_SECRET` must be at least 32 characters; the API refuses to start without it and names the variable. `.env.example` lists the same names with empty values. `load` uses the AWS CLI and runs `aws s3 cp` for these four keys, prefix `data/`:

- `customers.csv`
- `products.csv`
- `daily_exchange_rates.csv`
- `service_agents.csv`

It does not list the bucket. It does not download transactions, transcripts, digital events, or anything else. Those do not feed login or the policy. The API does not call S3. If `data/raw/` already has the four files, it does not download them again. The `sha256` is of the file on disk. If `load_batches` already holds that hash, the file is not copied into Postgres again.

Without the AWS variables and without the CSVs, `load` exits with an error that says what is missing. It does not start an empty demo or one with the four profiles made up.

The Postgres volume keeps gold. A second `up` does not reload if `load_batches` already holds the same `sha256` of the four files. Deleting the volume reloads.

## Data: what is touched and what is not

Measured on Sep 27, 2026 over `data/raw/`:

| Check | Result |
|---|---|
| `customers.csv` | 150,000 rows, 0 duplicate `customer_id`, 0 empty |
| `products.csv` | 400,000 rows, 0 duplicate `product_id`, 0 orphan `customer_id` |
| `service_agents.csv` | 1,200 rows, 0 duplicate `agent_id` |
| `customers.country` | only `México`, `Colombia`, `Argentina` |
| Empty score | 22,492 (15.0%) |
| Empty income | 30,033 (20.0%) |
| At least one of the two empty | 48,002 (32.0%) |

There is no legacy database to migrate and no cutover. The CSV is the source. "Migration" here means only this Postgres's `db/migrations/`, plus the load.

The score gap and the income gap are not cleaned. Those nulls are the R04 and R06 paths. Imputing a mean score or income erases Juliana's case and the 32% that cannot be decided.

Mexican balances are not reconciled to MXN. The `currency` column is copied as is. For products of customers in Mexico, the file says USD.

No deduplication by name. The keys are `customer_id` and `product_id`, and these four files have no duplicates. The dictionary mentions about 2% duplicates across the full dataset: if they show up in a table this flow does not load, they are not touched.

Empty `days_past_due` stays null in silver. When computing the maximum, the policy treats null as 0. The CSV is not filled in.

`Inactive`, `Suspended`, and `Closed` customers are not dropped. R01 handles them. There are 14,914, 4,407, and 2,979 of them.

The load report writes counts: rows read, null scores, null incomes, active products by type. Those nulls do not fail startup.

## Pipeline

1. Bronze: `aws s3 cp` into `data/raw/`, plus a manifest `{path, bytes, sha256}` in `load_batches`.
2. Silver, inside Postgres: the four read tables, only the columns listed above. Types, empty `days_past_due` as null, currency copied, product names untranslated.
3. Gold: `customer_credit_profile`, one row for each of the 150,000 customers, with the maximum days past due and `has_active_card`, `has_active_personal_loan`.

Load quality checks (fail the `load` container if any fail): row counts for the four files match the expected snapshot sizes; null rates for `credit_score` and `estimated_monthly_income` are reported; every `products.customer_id` exists in `customers`. Lineage for this demo is `load_batches` (`path`, `bytes`, `sha256`, `batch_id` on gold). There is no freshness rule in the policy (data are a static snapshot). An update-correctness fixture changes one file on disk, observes a new `sha256`, and proves `load` reloads silver and gold; that fixture is labeled as such in `docs/data_quality.md` when written.

No model is trained on the transcripts. They are templates. They do not feed the policy or the prompt. `load` does not download them.

## Juan's flow, step by step

1. Login with his document number and the code emailed to him. JWT `sub = CLI-9EDEKZ8OUNUR`.
2. Home. Savings `1,559.57 USD`, mortgage `109,159.57 USD`, 0 days past due. No credit card.
3. He writes "quiero una tarjeta de crédito". Event `conversation.message_received`. Columns: `customer_id` from the JWT, `process_id` null, `process_state` `ai_active`. Payload: the text and the `client_message_id`.
4. `open_process` inserts the process in `ai_active`.
5. `generate_while_ai` calls the model. It writes `conversation.turn_classified` with `prequalify_card` and the `process_id` from step 4. The message row stays `process_id` null. The process stores `product = credit_card`. `reply_text` does not say he pre-qualifies.
6. `ask_confirm_prequalify` sends `confirm_prequalify` (template). The policy is not called. The process stays `ai_active`.
7. He writes "sí". The turn is `confirm_prequalify` with `product = credit_card`. `run_policy` enqueues `policy.run`. It reads the profile: score 812, income 306,753.45 MXN (17,988 USD), 0 days past due, no active card. R05 wins. Event `analysis.completed`, with `language` copied from the turn.
8. `render_decision` writes the certificate in Spanish. Event `prequalification.decided`.
9. `end_after_decision` leaves the process `ended` / `prequalified`.
10. The customer screen shows the certificate. César does not see it.

If the text had been "quiero un crédito", step 5 returns `clarify` and `product` null. There is no consent ask and no policy. The process stays `ai_active`. The question is which of the two products: credit card or personal loan. When he later names a product (`prequalify_card` or `prequalify_loan`), step 6 asks for consent.

If at step 7 he writes "no", the intent is `decline_prequalify`. The policy is not called. The process stays `ai_active`.

## The other three flows

Juliana, `CLI-MD60UR8PNJDI`, score 714, income null, account `2,528.58 USD`. She asks for a card. After she confirms pre-qualification, R06 returns `NEEDS_INFO`. `template.send` writes `conversation.template_sent` (`needs_income`). She stays `ai_active`. The message asks for her monthly income. The sentences are not written in this contract yet. If she answers with an amount, that amount is this run's income, marked `self_declared`, and the gold row stays null. The process already holds `credit_card`, so `run_policy_income` runs the policy with that product (no second consent). Score 714 continues to R05 and the result is `PREQUALIFIED`. She does not go to César.

Alicia, `CLI-440CO5FZIY6A`, score 615, income 4,707,334.28 COP (1,167 USD), no card. After she confirms, R05 `REFER`. `template.send` writes `conversation.template_sent` (`refer_notice`): a person will review. The notice does not include the score and does not say whether she pre-qualifies. The sentences are not written in this contract yet. Then `conversation.thread_taken` with `reason_code = policy_refer`. César sees the packet: request, score, income, rule R05, policy `alba-credit-v1`. He does not answer in the thread. His only action is to close with `PREQUALIFIED` or `NOT_PREQUALIFIED`. That writes `conversation.consultant_closed`, then the automatic message and `process.end`. Which of the two he picks for Alicia is not fixed here. A message from Alicia while the case is still `human_active` is stored and does not call the model.

Mariana, `CLI-ZGOY1V6ZC46J`, active card ending in 5476, `days_past_due` 180, balance 111,079.25 ARS, score 515. After she confirms, R02 wins before R05. Certificate: does not pre-qualify. Process `ended`. She does not enter the queue.

## Not decided

These points are left open on purpose. Implementing them on your own breaks the contract.

- A limit multiplier, a per-segment cap, an income threshold in USD.
- A model that predicts `days_past_due`.
- Training intent on `call_transcripts`.
- Converting Mexican home-screen balances from USD to MXN.
- Supabase, Redis, Kafka, Inngest, Twilio, a second process, rules in the database, model tool-calling into the policy.
- Tying login to the four oracle profiles, or seeding only those four rows.
- Filling empty scores or incomes, or converting to MXN balances the file stores in USD.
- A cloud deploy for the submission (local `docker compose up` is how the project is tried; optional host steps are documentation only).
- Sending login codes to the dataset's addresses through a real mail provider.
- Search or a random pick in the login outside `DEMO_LOGIN=1`.
- A separate injection classifier or input-heuristic guard beyond the structural defense above.
- A separate risk microservice; the dataset `credit_score` is the risk estimate.
- A separate intent router beside `ConversationTurn`.
- Full pandera/Great Expectations suites or a policy freshness rule (R10).

Decisions still open in `PLAN.md` §5: D1 (optional second-model comparison), D7 (eval harness sizing and spend), D11 (masking ID-like digits in customer text before OpenAI), D12 to D15, D16 (1) and D16 (3) (the `ask_which_product` language check, and which commands change `processes.state`), and D17 (no route lists a customer's cases). D16 (2) is closed: `decide` takes `declared_income`. Each one that gets decided is written into this file.

## Known gaps

Found in a review on Sep 28, 2026. Each one is closed. The decision is in the section named on the entry.

1. **The first message reaches the model.** A new thread is born `ai_active`. The API stamps that column when it inserts `conversation.message_received`, so `generate_while_ai` matches the first message. `open_process` also matches, because `process_id` is still null, and creates the case. No rule on `process.started` is required. See **Events** and **Process rules**, and Juan's flow steps 3–5.
2. **The message key does not need a process.** It is `msg:{client_message_id}`. The uuid of the send is enough. See **Events**, idempotency keys.
3. **`open_process` reads the `process_id` column,** not a payload field. The customer does not send `process_id` or `process_state`. See **Events** and the `open_process` row.

The open-process key includes the triggering event id, so a later message after `ended` can open another case. The same send cannot open two.

12. **The consultant closes with a credit outcome and does not chat.** `POST /consultant/case/:id/close` writes `conversation.consultant_closed` with `PREQUALIFIED` or `NOT_PREQUALIFIED`. The rule enqueues the automatic message and `process.end`. There is no reply and no `referred_closed`. See **Consultant close**, the transition table, and `/consultant/case/:id`.
13. **`process.end` writes both events.** `process.state_changed` and `process.ended` carry the same `end_reason`. From the consultant, that reason is `prequalified` or `not_prequalified`. See the `process.end` command.
9. **The file is the income when it has one.** A typed amount is ignored if `income_local` is present. If it is null, the typed amount is this run's income, marked `self_declared`, and evaluation continues. It is not by itself `REFER`. See R06 and **What the customer can be asked**.
11. **Another customer's rows are the JWT filter.** The transition table does not list an attempt to see another customer. No intent detects it. A query for another customer's id returns no rows.
5. **`NEEDS_INFO` is a template event.** `template.send` writes `conversation.template_sent` with `template_id = needs_income`. The case stays `ai_active`. `prequalification.decided` is not used. The sentences are not in this contract yet. See `render_needs_info` and Juliana's flow.
6. **The `REFER` notice is a template event.** `template.send` writes `conversation.template_sent` with `template_id = refer_notice`, then the case moves to `human_active` with `reason_code = policy_refer`. The notice does not include the score and does not say whether the customer pre-qualifies. The sentences are not in this contract yet. See `render_refer_notice` and Alicia's flow.
7. **`language` travels on the event.** The turn carries it. `policy.run` copies it onto `analysis.completed`. `decision.render` and `template.send` read it from the triggering event. The process stores it, and the consultant close copies it onto `conversation.consultant_closed`. Nothing reads `llm_turns` for the locale.
8. **`provide_income` carries the product on the turn.** A turn that names a product stores it on the process. A later `provide_income` copies that stored product onto the turn when the model sends none. If it is still null, `ask_which_product` sends `which_product` and the policy waits.
10. **`reason_code` is a closed list.** `customer_requested_human`, `out_of_scope`, `language_unsupported`, `model_output_invalid`, `tool_failed`, `policy_refer`, `reply_forbidden`. The policy rule stays on `deciding_rule`. See the list under **Process**.
4. **The first turn takes the process this cycle just opened.** The first message is always the customer's, and its `process_id` column stays null. `process.start` runs first. `conversation.generate` then writes `conversation.turn_classified` with that process id. There is one open process per customer. The message row is not updated, and the message is not copied. See **Events**, the `conversation.generate` command, and Juan's flow step 5.

## What we take from Sxxxxx, and what we don't

We take the shape of the cycle and the state names `ai_active` and `human_active`. The customer's message is an event, `conversation.message_received`, and it is not the case. The case is the process. A new thread is born `ai_active`: the API stamps that column when it inserts the event, and the model rule matches that stamp, including on the first message. The message key is the send id, not `process_id`. The consultant takes the thread through an event, and from that event on the model rule no longer matches. The consultant does not write in the thread. Closing is `conversation.consultant_closed`, and the customer-facing sentence is a template. The certificate and the packet are rebuilt by reading events, not the model's free text.

We do not take the recruiting process catalog, the `interactions` table, the SQL trigger that stamps the mode, per-organization rules, the Sxxxxx SQL dispatcher, or the analyzer that scores forms. The analyzer of this demo is `api/domain/policy/engine.py`. This API stamps `process_state` when it inserts the event.
