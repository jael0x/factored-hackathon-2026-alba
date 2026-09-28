# Alba architecture: credit pre-qualification

This is the build contract. Anyone who implements from this file, person or model, must end up with what is written here. What is not decided is listed under **Not decided** and **Known gaps**. Filling those in on your own changes the demo.

Related files: `README.md` (product view and data access), `mocks/index.html` (screens), `AGENTS.md` (coding standard), `PLAN.md` (hackathon requirements, data evidence, open decisions, schedule). If `PLAN.md` offers an alternative (another host, another model, a credit limit), this file wins.

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
- Any row of `customers.csv` can open a session. The four profiles below are the test oracle, not an allowlist.

## What gets built

A web service. The customer asks about a credit card or a personal loan. If the request is ambiguous, the assistant asks which of the two and does not decide. If the data is enough, the policy issues a certificate (`constancia` in the UI): pre-qualifies, does not pre-qualify, or goes to a person. The certificate is a template filled with the policy result.

Four outcomes, from real rows of the file (snapshot of June 17, 2026):

| Customer | `customer_id` | Outcome | Rule | Final process state |
|---|---|---|---|---|
| Juan Alberto Romero González | `CLI-9EDEKZ8OUNUR` | `PREQUALIFIED` | R05, score 812 | `ended` / `prequalified` |
| Juliana Castro Gómez | `CLI-MD60UR8PNJDI` | `NEEDS_INFO` | R06, empty income | stays `ai_active` |
| Alicia Mariana Parra Álvarez | `CLI-440CO5FZIY6A` | `REFER` | R05, score 615 | `human_active` |
| Mariana Mónica Acosta Rojas | `CLI-ZGOY1V6ZC46J` | `NOT_PREQUALIFIED` | R02, 180 days past due | `ended` / `not_prequalified` |

These four rows are the oracle of an integration test. If an outcome changes, the test fails. Login does not hardcode them: it searches the 150,000 customers and the 1,200 agents.

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

**César González Sánchez** (agent) · `AGT-OJ9N4FGYV9` · employee `E75612` · specialty Créditos · Senior · morning shift · CSAT 4.23 · Spanish. The mock uses him. He is not the only agent.

## Closed stack

| Layer | Choice |
|---|---|
| API language | Python 3.12 |
| HTTP | FastAPI |
| Validation | Pydantic v2 |
| Frontend | TypeScript, React, Vite. One app |
| Database | PostgreSQL 16 as a service of the same `docker compose` stack, locally and on the deploy host. No managed database. The schema lives in `db/migrations/` |
| How it runs | `docker compose up` applies the schema, downloads the missing CSVs, and builds the profile. Nobody runs SQL by hand. Reviewers use the deployed link and read the repo; they are not expected to run the stack |
| Auth | Own JWT, HS256, 15 minutes, issued by this API |
| Pipeline | Python, in the `load` container. Reads local CSVs. DuckDB only if the aggregate needs it; the result lands in Postgres |
| LLM | OpenAI API, model `gpt-6-luna` (GPT-6 Luna). The adapter `api/llm/conversation.py` makes one call with Structured Outputs (the `ConversationTurn` JSON schema) and returns `ConversationTurn`. The policy does not use this adapter |
| Tests | pytest in the API. Vitest only if the client has logic; business logic does not live in the client |
| Running processes | A loop inside the API process that takes `commands` rows with `status = pending`. No Kafka, no Redis, no Inngest |

## File tree

```
api/
  main.py                 # FastAPI, routers
  settings.py             # env: DATABASE_URL, JWT_SECRET, OPENAI_API_KEY, LLM_MODEL, DEMO_INBOX
  db.py                   # connection
  auth.py                 # one-time code, JWT, get_session dependency
  events.py               # append to events, idempotency
  rules.py                # catalog and pure match
  worker.py               # takes commands and runs handlers
  processes.py            # start / transition / end
  policy/
    engine.py             # pure function
    alba-credit-v1.yaml   # rules and thresholds
    templates.py          # certificate, ES and PT
  llm/
    conversation.py       # one call, JSON schema
    schema.py             # ConversationTurn
  tools/
    profile.py            # reads gold by the session's customer_id
    products.py
    catalog.py
  fixtures/
    oracle_customers.json # the four profiles and César
web/
  src/pages/Login.tsx
  src/pages/Home.tsx
  src/pages/Case.tsx          # customer: chat, plus the certificate if it exists
  src/pages/AgentQueue.tsx
  src/pages/AgentCase.tsx     # chat plus handoff packet
  src/pages/Trace.tsx         # the process's events table
pipeline/
  bronze.py
  silver.py
  gold.py
db/migrations/001_init.sql
eval/                       # comes later; does not block the flow
compose.yaml
docker/api.Dockerfile
docker/web.Dockerfile
docker/load.Dockerfile
.env.example                # no secrets; the real .env is not committed
mocks/index.html            # static walkthrough, not the frontend
```

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
| `ai_active` | the assistant, if a rule enqueues `conversation.generate` | clarify, ask for income, decide, hand off to a person |
| `human_active` | only the agent | the customer writes and the message is stored; the model is not called |
| `ended` | nobody | the certificate exists. A new message opens another process |

Allowed transitions. Any other is an error and is not written.

| From | To | `end_reason` | Trigger |
|---|---|---|---|
| `ai_active` | `ai_active` | none | clarification or `NEEDS_INFO` |
| `ai_active` | `ended` | `prequalified` | policy `PREQUALIFIED` |
| `ai_active` | `ended` | `not_prequalified` | policy `NOT_PREQUALIFIED` |
| `ai_active` | `human_active` | none | policy `REFER`, request for a human, tool failure, unsupported language, attempt to see another customer |
| `human_active` | `ended` | `referred_closed` | the agent closes |
| `ended` | none | none | not reopened. Another message creates a new process |

`started` is not persisted. The process `INSERT` is born in `ai_active`, and the `process.started` event records it.

A customer has at most one process with `state <> 'ended'`. A partial unique index guarantees it.

## Events

Table `events`. Append-only. No `UPDATE` of `payload`.

Columns: `id uuid`, `event_name text`, `payload jsonb`, `customer_id text`, `process_id uuid`, `actor text` (`customer` | `agent` | `system` | `rule`), `caused_by_event_id uuid`, `caused_by_command_id uuid`, `idempotency_key text unique`, `created_at timestamptz`.

Closed names. No others are invented in v1.

| `event_name` | When it is written | Minimum payload |
|---|---|---|
| `conversation.message_received` | customer POST | `text`, `process_state`, `customer_id` (from the JWT) |
| `conversation.agent_message_sent` | agent POST | `text`, `agent_id` |
| `conversation.thread_taken` | the transition to `human_active` | `reason_code`, `from_state`, `to_state` |
| `analysis.completed` | `policy.run` finished | `policy_version`, `product`, `outcome`, `deciding_rule`, `rule_trace`, `facts` |
| `prequalification.decided` | the template was rendered | `locale`, `template_id`, `outcome`, `body` |
| `process.started` | the process was inserted | `process_key`, `customer_id` |
| `process.state_changed` | `processes.state` changed | `from_state`, `to_state`, `end_reason` |
| `process.ended` | reached `ended` | `end_reason`, `policy_version` |

`rule_trace` is a list of `{rule_id, input, result}`. `facts` cites column and value, for example `{name: "credit_score", value: 812, source: "customer_credit_profile.credit_score", as_of: "2026-06-17"}`.

Idempotency keys:

| Action | Key |
|---|---|
| Customer message | `msg:{process_id}:{client_message_id}` |
| Open process | `process:{customer_id}:credit_prequalification:open` |
| Run policy | `policy:{process_id}:alba-credit-v1:{product}` |
| Transition | `transition:{process_id}:{to_state}:{caused_by_event_id}` |

The frontend sends `client_message_id` (one uuid per send). Repeating the POST creates no new event and no new decision.

## Process rules

Source: `api/rules.py`. An in-memory list, sorted by ascending `priority`. There is no `rules` table in v1 and no per-organization override. Each rule appears once; a copy would fire twice.

A rule is `{id, trigger_event_name, when, actions}`. `when` is a pure function over the event. `actions` is an ordered list of commands.

| Id | Trigger | When | Commands |
|---|---|---|---|
| `open_process` | `conversation.message_received` | `payload.process_id` is null | `process.start` |
| `generate_while_ai` | `conversation.message_received` | `payload.process_state == "ai_active"` | `conversation.generate` |
| `record_only_when_human` | `conversation.message_received` | `payload.process_state == "human_active"` | none. The message is already in the event |
| `take_thread` | `analysis.completed` | `payload.outcome == "REFER"` | `process.transition` to `human_active`; that command writes `conversation.thread_taken` |
| `render_decision` | `analysis.completed` | `outcome` is `PREQUALIFIED` or `NOT_PREQUALIFIED` | `decision.render` |
| `end_after_decision` | `prequalification.decided` | always | `process.end` |
| `ask_income` | `analysis.completed` | `outcome == "NEEDS_INFO"` | none. The question text comes from the R06 template, not from the model |

`generate_while_ai` does not run if the state stamped on the event is `human_active`. The prompt is not the brake.

## Commands

Table `commands`: `id`, `command_name`, `payload jsonb`, `triggered_by_event_id`, `emitted_by_rule_id`, `idempotency_key unique`, `status` (`pending` | `done` | `failed`), `attempt_count int`, `last_error text`, `created_at`.

The worker takes `pending` rows with `FOR UPDATE SKIP LOCKED`, increments `attempt_count`, runs the command, and marks it `done` or `failed`. At most 3 attempts. On the third failure it writes a handoff event and transitions to `human_active` with `reason_code = tool_failed`. It does not retry in a loop.

| `command_name` | Does | Does not |
|---|---|---|
| `process.start` | inserts `processes` and `process.started` | call the model |
| `process.transition` | changes `state`, writes `process.state_changed` and, if the target is `human_active`, `conversation.thread_taken` | call the model |
| `process.end` | `state = ended`, `process.ended` | call the model |
| `conversation.generate` | one LLM call, persists the JSON | write `analysis.completed` |
| `policy.run` | reads the profile by the event's `customer_id`, runs the engine, writes `analysis.completed` | write the certificate |
| `decision.render` | picks the ES or PT template, writes `prequalification.decided` | call the model |

Order inside `policy.run`: read profile → engine → insert the event. Whether the engine returns `PREQUALIFIED`, `NOT_PREQUALIFIED`, `REFER`, or `NEEDS_INFO`, the worker interprets nothing more. The rules above react to the new event.

## Policy `alba-credit-v1`

File `api/policy/alba-credit-v1.yaml`. Function `decide(profile, product) -> Decision`. `product` is `credit_card` or `personal_loan`.

Input `profile`, already materialized in `customer_credit_profile`:

| Field | Source |
|---|---|
| `customer_status` | `customers.customer_status` |
| `credit_score` | `customers.credit_score`, null if empty |
| `income_local` | `customers.estimated_monthly_income`, null if empty |
| `income_currency` | MXN if `country = México`, COP if Colombia, ARS if Argentina |
| `income_usd` | `income_local * exchange_rate` for June 17, 2026, `source_currency` local, `target_currency` USD. Null if income is missing |
| `max_days_past_due` | max `days_past_due` over active products whose `product_type` is `Tarjeta Crédito`, `Préstamo Personal`, or `Préstamo Hipotecario`. Empty counts as 0 |
| `holds_product` | an active product of the requested type exists |
| `as_of` | `2026-06-17` |

Exchange rates for that day, read from `daily_exchange_rates.csv` (USD per one unit of local currency): 1 MXN = 0.058641 USD, 1 COP = 0.000248 USD, 1 ARS = 0.002873 USD.

Evaluation order. `rule_trace` accumulates. The first rule with a terminal result wins and later rules are not evaluated.

| Id | Condition | Terminal |
|---|---|---|
| R01 | `customer_status` is `Suspended` or `Inactive` | `REFER` |
| R01 | `customer_status` is `Closed` | `NOT_PREQUALIFIED` |
| R02 | `max_days_past_due >= 30` | `NOT_PREQUALIFIED` |
| R03 | `max_days_past_due` between 1 and 29 | `REFER` |
| R09 | `holds_product` is true | `REFER` |
| R04 | `credit_score` is null | `REFER`. The customer is not asked for their score |
| R06 | `income_local` is null and the message carries no declared income | `NEEDS_INFO` |
| R06 | the message carries declared income | `REFER`. The number is marked `self_declared` |
| R05 | score < 580 | `NOT_PREQUALIFIED` |
| R05 | score between 580 and 619 inclusive | `REFER` |
| R05 | score >= 620 | `PREQUALIFIED` |

R07 and R08 do not exist in the code. An income threshold or a `k * income` limit is not implemented. The certificate carries no limit amount and no rate for the new product.

`Decision` holds `outcome`, `deciding_rule`, `rule_trace`, `facts`, `policy_version = "alba-credit-v1"`.

Templates in `templates.py`, two locales: `es` and `pt`. The Portuguese is text written by the team; the dataset has none. The template receives the `Decision` and builds the paragraph. The model does not see this step.

Outcome phrases the template may emit, and the model is forbidden to emit on its own: `precalifica`, `no precalifica`, `pré-qualificado`, `não pré-qualifica`.

## How the model is called

The model is GPT-6 Luna on the OpenAI API, model id `gpt-6-luna`. It only classifies the sentence and drafts the clarification. Juan pre-qualifies the same with this model or with the test JSON, because `api/policy/engine.py` decides that.

`OPENAI_API_KEY` lives in `.env` locally and in the deploy host's secrets. It never enters git, the image, a log, or a prompt. `LLM_MODEL` defaults to `gpt-6-luna`. Only `api/llm/conversation.py` imports the OpenAI SDK. Whether it calls Chat Completions or Responses is an adapter detail: both support Structured Outputs for this model.

If the key is missing, Postgres, login, and the policy still start. `conversation.generate` fails with an error that says the key is missing. A failed API call (timeout, rate limit, server error) is a failed attempt of the command, under the worker's limit of 3 attempts; after the third, `human_active` with `reason_code = tool_failed`. The model is not silently replaced with another one.

The model is called only from `conversation.generate`, and only if the `generate_while_ai` rule enqueued that command.

One call, no streaming, Structured Outputs with the `ConversationTurn` JSON schema. `temperature` 0 if the model accepts it; GPT-6 Luna is a reasoning model and its docs do not say (`PLAN.md` R11). The response must also validate as `ConversationTurn` in Pydantic. If it does not, one retry. If the second also fails, `human_active` with `reason_code = model_output_invalid`. The request and the raw response are stored in `llm_turns` either way, including when parsing fails, with the model id and token usage. pytest does not call OpenAI: it injects the JSON.

```text
ConversationTurn
  intent: product_info | prequalify_card | prequalify_loan | provide_income
          | human_request | out_of_scope | clarify | chit_chat
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
- The instruction not to state eligibility or a limit. If `reply_text` contains those phrases, the worker discards `reply_text`, stores the turn as invalid, and escalates.

What the worker does with the JSON, besides storing it:

| `intent` | Next command |
|---|---|
| `clarify`, or `product` null when the text names no product | none. `clarification_question` is shown. Stays `ai_active`. The policy is not called |
| `prequalify_card` or `prequalify_loan` | `policy.run` with that `product` |
| `provide_income` | `policy.run`, with `declared_income_amount` in the payload |
| `human_request` | `process.transition` to `human_active`, `reason_code = customer_requested_human` |
| `out_of_scope` | `process.transition` to `human_active`, `reason_code = out_of_scope` |
| `language = other` | same, `reason_code = language_unsupported` |
| `language = pt` | continues. The certificate, if any, uses the `pt` template. The model may clarify in Portuguese |

`out_of_scope` covers a new mortgage, investments, a limit increase, disputing a transaction, a third party's balance, and "el crédito" when it still names no product after one clarification. The first time the customer says only "un crédito", the intent is `clarify`, not `out_of_scope`.

The model gets no tool that accepts a `customer_id`. There is no tool-calling into the policy. The policy is not a model tool: it is a command that runs afterwards, with the session's id.

## Auth and screens

Any customer in gold can log in. `GET /customers/search?q=` searches by name, document, or `customer_id` over the 150,000 rows, limit 20. `POST /session/code` takes an existing `customer_id`, or `random=true` to pick one at random. It creates a 6-digit code, valid 10 minutes, in `login_codes`. With `DEMO_INBOX=1` the response includes the code. `POST /session` with the code returns the JWT. Claims: `sub` = `customer_id`, `role` = `customer`, `exp` 15 minutes.

`POST /agent/session` works the same against the 1,200 rows of `service_agents`, by search or at random. Claims: `sub` = `agent_id`, `role` = `agent`.

Expired JWT: 401. The customer sees that the session ended. It is not silently renewed during the case being shown.

| Frontend route | Who | What it renders |
|---|---|---|
| `/login` | both | search and code |
| `/` | customer | their products, in the row's currency |
| `/case/:id` | customer | thread, plus the certificate if `prequalification.decided` exists |
| `/agent` | agent | processes in `human_active` |
| `/agent/case/:id` | agent | thread and handoff packet read from `analysis.completed` |
| `/agent/case/:id/trace` | agent | the process's `events`, in order |

A customer whose process is `ended` with `prequalified` or `not_prequalified` sees the certificate. They do not see the queue. The agent does not see `ended` processes in the queue. Juan does not appear in César's queue. Neither does Mariana. Alicia does.

Currency on the home screen: the row's `products.currency` column. For customers in Mexico the file stores those balances in USD. They are not converted to MXN for display. On the certificate, income is shown in local currency with the USD equivalent and the exchange-rate date beside it. Alicia in COP. Mariana in ARS.

## Database

`db/migrations/001_init.sql` creates:

- `events`, `processes`, `commands`, `login_codes`, `llm_turns`, `messages`, `customer_credit_profile`, `load_batches`
- `messages`: `id`, `process_id`, `author` (`customer` | `assistant` | `agent` | `template`), `body`, `event_id`
- `llm_turns`: `id`, `process_id`, `command_id`, `request jsonb`, `raw_response text`, `parsed jsonb`, `parse_ok bool`, `model text`, `input_tokens int`, `output_tokens int`, `latency_ms int`, `created_at`
- a partial unique index on `processes (customer_id, process_key) where state <> 'ended'`
- the filter `customer_id = jwt.sub` is in every API query. A test calls `products` with Juan's JWT and asks for Alicia's id: the response carries no rows of Alicia's

`customer_credit_profile` is the gold projection. One row per `customer_id`. Columns: the policy inputs, plus `country`, `segment`, `first_name`, `last_name`, `as_of`, `batch_id`. The customer API does not list this table. `policy.run` reads one row, the one for the event's `customer_id`.

Raw CSVs are not committed. They live in `data/raw/`, which `.gitignore` excludes. S3 keys and the OpenAI key live only in `.env` (or the deploy host's secrets): never in the repo, the image, or the prompt.

## Docker

`docker compose up` leaves the demo usable. The same stack runs locally and on the deploy host, with Postgres inside it. The host is not chosen yet (`PLAN.md` D2). Services:

| Service | Role | Keeps running |
|---|---|---|
| `postgres` | PostgreSQL 16, named volume | yes |
| `load` | waits for Postgres, applies `db/migrations/`, downloads CSVs if missing, fills the read tables and gold, exits with code 0 | no |
| `api` | starts when `load` finished successfully | yes |
| `web` | the frontend, proxies to the API | yes |

Who runs it: the team, locally and on the deploy host. Reviewers use the deployed link and read the repo; they are not expected to run the stack themselves. If a reviewer does need to run it, the team provides the keys.

With a `.env` holding `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-east-2`, `S3_BUCKET`, `OPENAI_API_KEY`, and `JWT_SECRET`, `docker compose up` needs no other command. `.env.example` lists the same names with empty values. `load` copies only these objects from the bucket, prefix `data/`:

- `customers.csv`
- `products.csv`
- `daily_exchange_rates.csv`
- `service_agents.csv`

It does not download transactions, transcripts, digital events, or anything else. Those do not feed login or the policy. If `data/raw/` already has the four files, it does not download them again.

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

1. Bronze: the CSV in `data/raw/`, plus a manifest `{path, bytes, sha256}` in `load_batches`.
2. Silver, inside Postgres: types, empty `days_past_due` as null, currency copied, product names untranslated.
3. Gold: `customer_credit_profile`, one row for each of the 150,000 customers, with the maximum days past due and the active-product booleans.

No model is trained on the transcripts. They are templates. They do not feed the policy or the prompt. `load` does not download them.

## Juan's flow, step by step

1. Login. JWT `sub = CLI-9EDEKZ8OUNUR`.
2. Home. Savings `1,559.57 USD`, mortgage `109,159.57 USD`, 0 days past due. No credit card.
3. He writes "quiero una tarjeta de crédito". Event `conversation.message_received` with `process_state` still empty and the `customer_id` from the JWT.
4. `open_process` inserts the process in `ai_active`.
5. `generate_while_ai` calls the model. The JSON carries `prequalify_card`. `reply_text` does not say he pre-qualifies. (See known gap 1.)
6. `policy.run` reads the profile: score 812, income 306,753.45 MXN (17,988 USD), 0 days past due, no active card. R05 wins. Event `analysis.completed`.
7. `render_decision` writes the certificate in Spanish. Event `prequalification.decided`.
8. `end_after_decision` leaves the process `ended` / `prequalified`.
9. The customer screen shows the certificate. César does not see it.

If the text had been "quiero un crédito", step 5 returns `clarify` and `product` null. There is no step 6. The process stays `ai_active`. The question is which of the two products: credit card or personal loan.

## The other three flows

Juliana, `CLI-MD60UR8PNJDI`, score 714, income null, account `2,528.58 USD`. She asks for a card. R06 returns `NEEDS_INFO`. She stays `ai_active`. The message she sees is the template that asks for her income and says a declared amount goes to a person. If she answers with an amount, the next `policy.run` lands on R06 `REFER` and the process moves to `human_active`.

Alicia, `CLI-440CO5FZIY6A`, score 615, income 4,707,334.28 COP (1,167 USD), no card. R05 `REFER`. `conversation.thread_taken`. César sees the packet: request, score, income, rule R05, policy `alba-credit-v1`. A message from Alicia in that state is stored and does not call the model.

Mariana, `CLI-ZGOY1V6ZC46J`, active card ending in 5476, `days_past_due` 180, balance 111,079.25 ARS, score 515. R02 wins before R05. Certificate: does not pre-qualify. Process `ended`. She does not enter the queue.

## Not decided

These points are left open on purpose. Implementing them on your own breaks the contract.

- A limit multiplier, a per-segment cap, an income threshold in USD.
- A model that predicts `days_past_due`.
- Training intent on `call_transcripts`.
- Converting Mexican home-screen balances from USD to MXN.
- Supabase, Redis, Kafka, Inngest, Twilio, a second process, rules in the database, model tool-calling into the policy.
- Tying login to the four oracle profiles, or seeding only those four rows.
- Filling empty scores or incomes, or converting to MXN balances the file stores in USD.

Decisions the hackathon brief forces but this contract does not make yet (deployment host, the evaluated learned component, the risk-estimate layer, data contracts and freshness, evaluation harness) are tracked in `PLAN.md` §5. Each one that gets decided is written into this file.

## Known gaps

Found in a review on Sep 28, 2026. Each one blocks a correct implementation, and none is decided here. Close them in the definition phase (`PLAN.md` §5, D10): write the answer into the section it belongs to and delete the entry.

1. **The first message never reaches the model.** `open_process` matches when the event has no process. `generate_while_ai` matches only when `process_state == "ai_active"`. The first message of a new process has no state, so no rule enqueues `conversation.generate`, yet Juan's flow (step 5) expects the model to run. No rule reacts to `process.started` either.
2. **The first message's idempotency key needs a process that does not exist yet.** `msg:{process_id}:{client_message_id}` has no `process_id` before `process.start` runs.
3. **`open_process` reads `payload.process_id`,** but `process_id` is an `events` column and is not a listed payload field.
4. **The model turn is not an event.** The worker reads the `ConversationTurn` JSON and enqueues `policy.run` or `process.transition` itself. No event records the classified turn and no rule owns `policy.run`, which breaks "rules react to events" and leaves those commands without a `triggered_by_event_id`. The event list is closed, so closing this is a contract change.
5. **`NEEDS_INFO` has no renderer.** `ask_income` says the question comes from the R06 template, but `decision.render` runs only for `PREQUALIFIED` and `NOT_PREQUALIFIED`, and no event records the question that was sent.
6. **The customer-facing message on `REFER` is not specified.** The mock shows Alba telling Alicia her score is in the review band. The model cannot write that (it does not see the score), and no template or command is named for it.
7. **The template locale is not on the event.** `decision.render` picks `es` or `pt`, but `analysis.completed` does not carry the language, so the command would have to read outside the event.
8. **`provide_income` does not carry the product.** After `NEEDS_INFO`, the next intent is `provide_income`. `policy.run` needs `product`, and the contract does not say where it comes from.
9. **R06 with income on file.** "The message carries declared income → `REFER`" does not say whether it applies when `income_local` is present.
10. **`reason_code` is not a closed list.** Named in the text: `customer_requested_human`, `out_of_scope`, `language_unsupported`, `model_output_invalid`, `tool_failed`. Policy `REFER`, a forbidden phrase in `reply_text`, and an attempt to see another customer have no named code.
11. **"Attempt to see another customer" has no detector.** It is listed as a trigger for `human_active`, but no `intent` covers it (`out_of_scope` covers a third party's balance).
12. **The agent's close has no path.** `human_active → ended` (`referred_closed`) is allowed, but no endpoint, rule, or event is defined for the agent's action, and the agent's own outcome is not recorded.
13. **Ending writes which events?** It is not stated whether `process.end` writes `process.state_changed` as well as `process.ended`.

## What we take from Sxxxxx, and what we don't

We take the shape of the cycle and the state names `ai_active` and `human_active`. The agent takes the thread through an event, and from that event on the model rule no longer matches. The certificate and the packet are rebuilt by reading events, not the model's free text.

We do not take the recruiting process catalog, per-organization rules, the Sxxxxx SQL dispatcher, or the analyzer that scores forms. The analyzer of this demo is `api/policy/engine.py`.
