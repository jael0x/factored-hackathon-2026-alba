# Coding standard: Alba

Read this before the first edit. It binds every author and every model (Cursor, Claude, Copilot, or another). The product contract is `ARCHITECTURE.md`. If code, a test, or an idea contradicts that file, stop and say so. Do not invent events, states, thresholds, columns, reason codes, or outcomes to make the task close.

`PLAN.md` tracks the hackathon requirements, data evidence, open decisions, and schedule. It does not redefine policy, the model, or startup. Where it disagrees with `ARCHITECTURE.md`, the contract wins until the open decision is closed and written into the contract.

## Before the first edit

Do not write code until both blocks are in the thread.

```
Owner check:
- Symptom:
- Cause (mechanism, not the symptom):
- Owner (where this system already decides it):
- Path: through | around
- Reset: if the volume is wiped and docker compose is run again, does this still hold? yes | no
```

`around` means stop. It is not done if someone must run SQL by hand, remember a value in the UI, or special-case one of the four oracle customers.

```
Evidence:
- Claim:
- Label: proven | inferred
- Artifact (if proven): path:line, type, query, or measured row
```

Proven means an artifact in this session. Inferred means the source is silent. An inferred claim cannot justify a patch.

Absence is not evidence. "I did not find a threshold / column / rule" is a gap to report. It is not permission to add one.

Reason in this system's pieces, not in the shape of the task. Eligibility is a pure policy. A process rule reads an event already written. A command changes state. The model only classifies a sentence and drafts a clarification.

The first answer from a model is usually a local patch. Discard it until cause and owner are named.

A correct diagnosis plus a patch that skips the owner is a failed fix. The smallest change is the one that still goes through the owner.

## Owners in this system

| Concern | Owner (through) | Around (forbidden) |
|---|---|---|
| Prequalified, not prequalified, refer, needs info | `api/domain/policy/engine.py` and `alba-credit-v1` | The model says it, or the UI computes it |
| Whether a process rule matches | Fields already stamped on `events` | Re-read the customer inside the match |
| What the system does next | A `commands` row and the worker | An `if` in the HTTP handler that changes state |
| Who the customer is | `customer_id` on the JWT | Chat text, national id, or a model argument |
| History | Append to `events`, with `caused_by_event_id` | `UPDATE` a past event, or join two facts by clock time |
| Decision wording | `api/domain/policy/templates.py` | Model prose |
| Model call | `api/infrastructure/llm/conversation.py` | Import the OpenAI SDK from policy or UI |
| Login codes and sessions | `api/domain/session` and `api/application/session`: codes stored hashed, JWT; `get_session` in `api/presentation/http/dependencies.py` | A code in a log, a response body, or a plain-text column |
| Sending email | `api/infrastructure/mail/smtp.py`, to Mailpit in the compose stack | Opening SMTP from another module, or pointing it at a real provider while the stack holds this dataset |
| HTTP request and response | `api-spec/openapi.yaml`, generated into `api/contract_models.py` and `web/src/api/schema.d.ts` | A hand-written DTO in `api/` or `web/` |
| Facts the policy reads | `customer_credit_profile` | Recompute score, delinquency, or income on the request |
| Limit, new rate, delinquency prediction | They do not exist | Invent them because a plan or a chat mentioned them |

## How to think

1. **Start with why.** One sentence: what the customer sees, what `processes.state` becomes, what new `events` row exists. If that sentence is vague, do not code yet.
2. **First principles.** Start from the problem. "Because the last patch did it that way" is a reason to stop.
3. **Root cause.** Do not cache a bad pattern. Do not add a workaround for a design problem.
4. **Edge cases before the happy path.** What happens when this fails? What happens on the next customer, not only Juan? Will someone else understand it in six months?
5. **Evidence.** Read the code and the rows. Label every load-bearing claim proven or inferred.
6. **Scope.** Smallest change that still goes through the owner. Do not refactor adjacent code in the same change.
7. **Decompose.** Each step has an input, an output, and a check. Then implement.
8. **Personas.** The policy author justifies an outcome in the engine. The API author exposes that outcome as fields. The UI author renders those fields. A screen convenience must not drive a schema shortcut or a hidden eligibility branch.
9. **Plan, then build.** Lasting decisions stay in `ARCHITECTURE.md`. Do not add a second design doc for a one-session tweak.

Fix the class, not one row. A bug that shows up on Juan is a bug in the pure function for every customer with those facts. A `customer_id` branch in shared policy is the forbidden special case.

## Consultants and service agents

A person who reviews a handed-off case is a consultant (`ARCHITECTURE.md`, "Oracle fixtures"). Do not call that person an agent: agent is the AI agent's word.

- Identifiers in `db/` and `pipeline/` keep the dataset's name: the `service_agents` table and `service_agents.csv`, the columns `agent_id` and `agent_status`, `AGENTS_COLUMNS`, and the `AGT-` ids. Comments there say consultant.
- Everywhere else the word is consultant: Python and TypeScript names, routes (`/consultant/...`, `/consultants/search`), the JWT role, wire fields (`consultant_id`), event names, rule ids, idempotency keys, comments, docs, specs, and `diagrams/c4.html`.
- SQL is the only code that names the dataset columns. `api/infrastructure/db/consultants.py` reads `agent_id` and `agent_status` and returns a `ConsultantIdentity`; nothing above it sees those names.
- Spanish screens say "asesor". `mocks/index.html` still says "Agente", `conversation.agent_closed`, and `agent_close:`; read them as asesor, `conversation.consultant_closed`, and `consultant_close:`.

## No magic strings

Identifiers from a closed set are constants or unions, defined once. Call sites use the constant. They do not repeat the raw literal.

Closed sets in this repo, each defined in `ARCHITECTURE.md`: event names, command names, process states (`ai_active`, `human_active`, `ended`), end reasons (`prequalified`, `not_prequalified`), outcomes (`PREQUALIFIED`, `NOT_PREQUALIFIED`, `REFER`, `NEEDS_INFO`), policy rule ids (`R01` to `R06`, `R09`), process rule ids (`open_process` …), `process_key`, intent names (including `confirm_prequalify`, `decline_prequalify`), product keys (`credit_card`, `personal_loan`), template locales (`es`, `pt`), template ids (`needs_income`, `refer_notice`, `which_product`, `confirm_prequalify`), reason codes (`customer_requested_human`, `out_of_scope`, `language_unsupported`, `model_output_invalid`, `tool_failed`, `policy_refer`, `reply_forbidden`), idempotency-key prefixes.

Wrong: `if event_name == "analysis.completed"` in a second file. Right: `EVENT_NAME.ANALYSIS_COMPLETED` from the one module that defines names.

Wrong: matching a chat headline or a Spanish sentence to decide a branch. Right: a typed field (`intent`, `outcome`, `reason_code`).

Allowed raw strings:

- Customer-facing copy and template text.
- The YAML/SQL value at the single definition site.
- A test that asserts the value of a named constant.
- Dataset literals that are data, not code: `Tarjeta Crédito`, `Préstamo Personal`, `Préstamo Hipotecario`, country names as stored. Those strings are read at the load boundary and mapped once into typed product keys. They are not re-typed inside rules.
- Log text that is not a cross-layer identifier.

Bracket access on a typed object (`row["state"]`) is a magic string when the attribute exists. Use the typed field.

## No unnecessary comments

The default is zero comments. Before writing `#`, `//`, `/*`, or a docstring, stop.

Forbidden:

- Restating the line (`# fetch user`, `# return early`).
- Section banners (`# --- helpers ---`).
- Step labels (`# 1. validate`).
- Change notes (`# added for the demo`, `# TODO`, `# FIXME`, `# HACK`, `# NOTE`).
- A docstring that only says what the function name already says.

The only comment that may stay explains a non-obvious *why* the code cannot carry: an external constraint, a file-format trap, a trade-off a careful reader would not infer. If a competent reader would reach the same understanding without it, delete it. When unsure, delete it.

Do not use comments to talk to the user. Say that in the chat. If the user removes a comment, do not put it back.

Prefer a better name or an extracted function over a comment.

## Code shape

10. **Functional flow.** Prefer `map` / `filter` / comprehensions over long imperative loops. Side effects stay at the edges.
11. **Single responsibility.** One function, one job. One module, one concern.
12. **No god functions.** Past about fifty lines, split.
13. **Pure core.** Policy, rule match, and row choice are pure. Database, HTTP, and the OpenAI API sit in thin functions that call the pure ones.
14. **Composition.** If a function does A then B, export A and B and compose them. Do not nest B inside A.
15. **DRY.** Copying a block means extract it. After a refactor, grep and delete the loser. Two live implementations of the same decision is a bug. Deleting the dead one is part of the change.
16. **Adapter at the boundary.** Business logic does not import a provider SDK. Only `api/infrastructure/llm/conversation.py` imports the OpenAI SDK. Swapping the model changes that module.
17. **Explicit.** A side effect is in the name. A nullable value is in the type. A dependency is passed in or imported, not read from ambient global state.
18. **Fail loud.** Validate at the boundary. Unexpected state surfaces immediately. Do not swallow an exception and continue.
19. **Colocation.** Tests next to the pure module. Types next to the code that uses them. Constants next to the domain.

**Naming is design.** `process_data` says nothing. `decide_credit` does. If you cannot name it, you do not understand it yet.

**Early return.** Invalid cases leave at the top. The happy path stays at low indentation. Do not nest more than two or three levels.

**Catch-log-continue is not resilience.** A `try/except` that logs and proceeds after a failed load, a failed JSON parse, or a missing model drops the fail-loud path. Fail the command. Name what is missing. Do not invent a decision so the screen still moves.

## Types

- No `Any` without a written justification that says why a real type cannot be used. Do not reach for `Any` to silence a checker.
- Closed sets are unions or `Literal` / enums. Do not widen them to `str` so a call site compiles. Do not re-declare the same union in a second module.
- Discriminated unions, not two booleans. Process state is `ai_active | human_active | ended`. A decision is one outcome, not `is_prequalified` plus `needs_human`.
- Narrow with control flow. A cast (`as`, unchecked assertion) is a lie to the checker. Use it only after narrowing is exhausted, and justify that one line.
- `None` is absence. `0`, `""`, and an all-zero id are not stand-ins for missing.
- Derive, do not store a second copy. The certificate text comes from `Decision`. A display name comes from `first_name` and `last_name`. One function renders a derived field. Grep every mapper that emits it (API, queue card, case file) and call that function. A second formula will drift.

## Data fetching and UI

- Fetch at the level that owns the session. Do not make every child request the same profile.
- Policy YAML and event-name constants are config. Load them once. Do not treat them as per-keystroke state.
- The UI renders structured fields from the API. It does not recompute eligibility, currency conversion, or certificate prose.
- Every fetch has loading, error, and success. Handle all three when the fetch is written, not as a later polish.
- Config that decides a field's behavior lives on the policy spec, not on a frontend list that sniffs ids.
- An internal reason code is not customer copy. The customer reads the template. The consultant packet may show the rule id and the facts.

## Database

- Select only the columns you need. Batch writes. Index what you filter.
- A list or a count starts from the small set: this session's process, this `customer_id`'s gold row, `commands` where `status = pending`. A `LATERAL` or a per-row function over all `customers` or all `products` is an N+1. Copying the previous query is not a pass.
- Parameterized SQL only. Never concatenate request input into a statement.
- `events` are append-only. A new fact points at the previous one with `caused_by_event_id`. Do not hard-delete history.
- Migrations are one-way and safe while old code might still be running. No destructive drop in the same step that introduces the replacement.
- A migration keeps its filename once it has run anywhere: `schema_migrations` is keyed by it, and a renamed file runs again. If one must be renamed, map the new name to the old one in `FORMER_NAMES` in `pipeline/migrate.py`, with a test.
- The schema is the contract. `NOT NULL` means the app does not hunt for nulls. A nullable column means the app handles null. Empty income stays null. Do not impute. Do not convert Mexico balances out of USD.
- If you create or replace a view, the same migration sets `security_invoker = true`. Otherwise the view runs as the owner and skips privileges.
- Idempotency keys are derived from the gap that already exists (`process_id`, client message id, policy version, causing event id). No `Date.now()` and no random. Two runs of the same fact collide on the same key.
- When several rows could win, the tie-break is an explicit comparator (named fields, in a fixed order). `ORDER BY … LIMIT 1` with no tie-break is not a decision. `NULL` sorts where you say it sorts, not where the engine happens to put it.
- Compare timestamps as the database stores them. Do not round through a millisecond parser and call two different instants equal.

## Events, rules, commands

- An event carries every fact a downstream rule needs. If the match must query the customer again, the event is too thin. Stamp the facts at emit time, when they are already known.
- Fields the rule matches on are typed columns. A shapeless JSON blob is for context the matcher does not branch on.
- One owner per trigger. Two paths that can enqueue the same command are a bug.
- `human_active` means the "call the model" rule does not match. Do not call the model anyway.
- Deterministic link, not a guess. The edge is an id written at emit (`caused_by_event_id`). It is not "nearest event in the last few seconds", not the newest unlinked row, and not a headline string.
- If the link is missing, show nothing for that link and fail loud in logs. Do not attach a plausible row in silence.

## Model

- The model classifies the utterance and drafts the clarification. It does not see score, income, delinquency, name, document, email, or address. It sees booleans and the message.
- The model is an external service. Nothing leaves the API for OpenAI beyond the list under "What goes into the prompt" in `ARCHITECTURE.md`.
- It must not emit `precalifica`, `no precalifica`, `pré-qualificado`, or `não pré-qualifica`. The template emits those.
- A document number or `customer_id` does not prove identity. A one-time code opens the session.
- Permissions and eligibility stay outside the model.

## Tests

- Test behavior, not the private steps. If a refactor keeps the outcome and breaks the test, the test was coupled to the implementation.
- Test the pure functions hard, including branches.
- Edge cases first: income `None`, score `None`, delinquency 30, delinquency 29, status `Closed`, product already held, invalid model JSON, a second message with the same idempotency key.
- **Negative path.** Every new rule or branch has a test that it does **not** fire. Mariana is decided by delinquency (R02) even though her score would also fail. Juan's session does not return Alicia's products. `human_active` does not call the model.
- **Fail both ways.** Assert the full expected value, not a boolean that only grows. A field that disappears must turn the test red. A field that appears and was not in the expected value must turn the test red.
- **No soft asserts.** `if field is present: assert else: assert empty == empty` always passes. If the fixture includes the field, assert it unconditionally.
- **Tied rows.** Permute input order. The comparator, not scan order, picks the winner.
- **Sabotage once.** Break the pure function on purpose (return the wrong outcome, drop the tie-break) and confirm the exact test goes red. Then restore it.
- If a test is hard to write, the design is wrong. Do not mock the policy to hide that. Unit tests inject `ConversationTurn` JSON. They do not call OpenAI to learn whether Juan is prequalified.
- An event-chain test crosses the worker. The command is completed, the new state is persisted, and the new event is in the database. A queued payload alone is not the assertion.
- A test file must live on a path the test command actually runs. Say which command. A file no command globs is not coverage.
- Fix pre-existing failures you hit in the suite you ran. Do not leave them as "not this task" without saying so.

## Process

- Lint and the type checker are clean before the change is called done.
- One concern per change. Do not mix a refactor with the feature.
- A lockfile diff contains only the package you bumped and its direct tree.
- Do not declare done while a rule in this file or in `ARCHITECTURE.md` is still broken. Fix it first.
- A doc earns a file only when it records a real decision, a contract, or a deferral the code cannot show. A bug with one obvious cause does not get a new markdown file. Update `ARCHITECTURE.md` when the contract changes. Do not stack session notes or handoff files beside it.

## Security

- External input is hostile until the boundary validates it.
- S3 keys, `OPENAI_API_KEY`, and any other secret live in `.env` locally and in the host's secrets when deployed. They do not enter git, the image, a log, or the prompt.
- Never commit `*.pdf` or anything under `data/`. Organizer PDFs stay local in `docs/`; page 2 of the data dictionary holds the S3 keys. Rows from the dataset do not go into docs beyond the oracle fixtures, and never into a request to an external model.
- Before the first push to any remote, scan the full history for secrets.
- Each service gets the minimum it needs. The customer API reads that session's rows and no one else's.

## Writing docs

- Docs are in English. Customer-facing copy (templates, the mock) is Spanish or Portuguese. Dataset literals keep their stored spelling.
- Straight quotes. No em-dashes: use a colon, a comma, or parentheses.
- Every number about the data names its source and sample (file, date, n). A claim the data does not show is labeled inferred.
- One home per fact. The contract lives in `ARCHITECTURE.md`. Evidence, open decisions, and the schedule live in `PLAN.md`. Other files link to them instead of copying.

## When you delegate to another model

The other model does not inherit the chat. The prompt includes these five points verbatim, plus the exact file allowlist:

1. `ARCHITECTURE.md` is authoritative. If schema, seed, or code diverges from the task, stop and report. Do not invent enums, states, columns, or event names.
2. This file binds the code: no narrative comments, no magic strings, pure policy, no widening a closed union to `str`, no model call from policy or UI.
3. Touch only the named files. Do not stage anything else.
4. Before calling the increment done, review the diff against this file. A violation is fixed, not noted for later.
5. One concern per change.

## Do not

- Decide eligibility in the prompt, in the screen, or in a client-side `if`.
- Invent a credit limit, a rate for the new product, or a model that predicts delinquency.
- Impute nulls, or translate `Tarjeta Crédito` while reading the CSV.
- Restrict login to the four oracle customers.
- Join two events by time proximity.
- Swallow a load error or a bad model JSON and continue as if a decision existed.
- Leave two functions that do the same job.
- Add a comment a reviewer would mark as noise.
- Compare a raw identifier literal when a constant already exists.
- Widen a closed union to `str`.
- Use `None`-as-zero, or zero-as-missing.
- Put `Date.now()` in an idempotency key.
- Special-case one `customer_id` inside shared policy.
- Hand-write a request or response type that `api-spec/openapi.yaml` already defines. Add the field there and regenerate.
- Ship a test whose `else` branch cannot fail.
