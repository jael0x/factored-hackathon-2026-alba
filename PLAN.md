# Plan: Alba at the Factored AI & Data Hackathon 2026

Status on Wed Sep 30, 2026: **build phase.** Built: the compose load path (PR #1), the customer login end to end (document number, a code emailed to Mailpit, the session, `GET /me`, the login screen), and the consultant login (email and employee code, the same emailed code, `GET /consultant/me`, `/consultant/login`). Not built yet: home, conversation, policy, and the consultant queue and case.

`ARCHITECTURE.md` is the contract. This file tracks what the brief asks for, what the data shows, what is still open, and when each piece happens. `IMPLEMENTATION.md` holds the build order: what gets built, in which order, and which scenarios in `specs/` each item turns green. Where this file and the contract disagree, the contract wins and the disagreement is an open decision in §5. A closed decision is written into `ARCHITECTURE.md` in the same change, and its entry here moves to the decision log (§10).

Sources: the organizer PDFs in `docs/` (problem statement, kickoff deck, dataset summary, data dictionary; local only, never committed) and profiling of the S3 bucket on Sep 27-28. Every data number says which sample it comes from.

## 0. Repo hygiene

- [x] Organizer PDFs removed from git history (Sep 28). They stay in `docs/`, ignored by `.gitignore`.
- [x] Old commit with the PDFs purged (Sep 28): `main` and `rebranch` both start from the clean root, the reflog was expired, and `git gc` found no unreachable objects or PDF blobs.
- [x] Secret scan (Sep 28, gitleaks 8.30.1): all 3 commits on every branch and the committable working-tree files, no leaks found. A planted fake AWS key was caught, so the scanner works.
- [x] Secret scan after the repo reached GitHub (Sep 29, gitleaks 8.30.1): 44 commits on every branch, no leaks found. The purged PDF commit is not in the object store.
- [ ] Add a secret scanner as a pre-commit hook.
- [x] `.env.example` committed (Sep 29, PR #1) with the six variable names and empty values.
- [ ] The public repo must be named `factored-hackathon-2026-<team name>`. Today it is `jael0x/alba` on GitHub. Keep it private until submission day.
- [ ] Both team members commit to the repo: organizers treat the GitHub contributors at submission as the team. Both have commits as of Sep 29. Before submission, check that every commit email is linked to its author's GitHub account. If a registration email differs from the GitHub email, say so in the submission.

## 1. The event

- Factored AI & Data Hackathon 2026 (the "Datathon"). Challenge launch Sep 25. **Submissions close Mon Oct 5 at 11:59 pm UTC-5.** Finalists announced Oct 15, award ceremony Oct 16. About 750 participants and 180 teams. Prizes US$6,000 / 3,000 / 1,000, plus an interview with Factored's engineering and talent team.
- Deliverables, all sent to `hackathon.admin@factored.ai`:
  1. link to the public GitHub repo `factored-hackathon-2026-<team name>`
  2. link to the deployed tool
  3. a 4-6 slide presentation
  4. a short, mandatory video pitch that demonstrates the working solution and explains the core architecture decisions
- Judging (kickoff deck): "First and foremost our solution should work." Then: project rationale and documentation; AI engineering (backend, frontend, deployment); data analytics (data quality, relevant insights); data engineering (extraction and transformation); machine learning (model selection, optimization, implementation, tracking).
- Kickoff framing: "Don't build a chatbot, build a customer-service system." The loop is Understand → Decide → Act → Verify → Escalate. "AI should not be autonomous just because it can be." Final takeaway: "Build something that works, prove that it works, and know when it should not act. And show us what it would take to make it real."
- Any language or tools are allowed. Mentors are in Slack `#technical-help`; organizers said teams get mentor details the week of Sep 28.

### Organizer clarifications in Slack (read Sep 28)

Answers from organizer staff in `#general`, `#technical-help`, and `#challenge-help`. They refine the brief; the PDFs stay the primary source.

- **Deadline and video:** Oct 5, 11:59 pm UTC-5. The video is at most 3 minutes (`#challenge-help`, Sep 28).
- **Team:** up to 4 people, each registered individually. The team is whoever contributed to the GitHub repo at submission (`#general`, Sep 25). A bot account may make commits as long as every member appears in the contributor list (`#general`, Sep 28).
- **External LLM APIs** are allowed (`#challenge-help`, Sep 25).
- **External data**, Kaggle included, is allowed if the team justifies it (`#technical-help`, Sep 27).
- **Learned component:** it does not have to be trained from scratch. A prompted or fine-tuned LLM counts if the team defines what it does, evaluates it rigorously, and justifies it. The baseline is not prescribed (deterministic rules, TF-IDF + logistic regression, a zero-shot LLM, or another justified option); both are compared on the same held-out data with valid labels and leakage prevention (`#technical-help`, Sep 25).
- **Deployment:** cloud deployment is not a strict requirement. What is judged is a credible path to production: scalability, reproducibility, monitoring, security, reliability, and the remaining work. Local tooling is fine if the deploy and scaling path is explained (`#technical-help`, Sep 26). Paid cloud tiers are allowed at the team's own cost; no credits are given (`#general`, Sep 27-28). The kickoff deck still lists a deployed link among the submission items.
- **Sizing:** a prototype is not expected to handle full production volume; stating its sizing limits is valued (`#technical-help`, Sep 27).
- **Data semantics:** organizers decline questions whose answer would shape the problem definition (for example, what `process_date` means). The dataset has features teams are expected to detect and handle; the assumption is ours to make and document (`#technical-help`, Sep 28).

Questions for the organizers:

- [x] Exact submission time and time zone on Oct 5: 11:59 pm UTC-5.
- [ ] Is machine-translated Portuguese test data acceptable if it is disclosed? Not asked yet. External data is allowed with justification, which suggests yes if disclosed.
- [x] Are external public datasets allowed? Yes, with justification.

## 2. Brief requirements against the contract

Source: the problem statement PDF. "Status" says whether `ARCHITECTURE.md` answers the requirement today.

| Brief requirement | Where the contract answers it | Status |
|---|---|---|
| One coherent workflow | `credit_prequalification`, credit card and personal loan | Covered |
| Normal, ambiguous or unsupported, and human-required paths | Juan (normal), "quiero un crédito" (clarify), Juliana (ask for income, then R05), mortgage and others (`out_of_scope`), Alicia (human) | Covered, except a second vague request cannot reach `out_of_scope` (D13) and Juliana's income run repeats a key (D12) |
| Spanish and Portuguese interactions; report language limits | `es` and `pt` templates; model sets `language` per turn; PT copy team-written / MT disclosed (D6) | Partial: PT quality of `gpt-6-luna` still measured in R11 |
| 1. Problem supported by data (contact reasons, demand, data quality, constraints) | §4 of this file | Partial: Jan 2025 numbers come from one month and need a full-table recount (R5) |
| 2. Context, clarification, grounding, tools, only verified actions reported | events per process, `conversation.turn_classified`, `facts` cite source columns | Covered in design |
| 3. What it answers, what needs confirmation, when it abstains or transfers | rules table, transitions, `out_of_scope`, soft consent before `policy.run` (D8) | Covered, except an income typed before consent runs the policy (D14) |
| 3. Permissions and policy enforced outside model prose | JWT `customer_id`, pure policy, templates | Covered |
| 3. Handoff with request, verified facts, actions taken, evidence, open questions | packet read from `analysis.completed`: request, score, income, deciding rule. The consultant does not chat | Partial: a separate "open questions" field is not in the contract, and the packet of a handoff other than `REFER` carries only the reason code (`ARCHITECTURE.md` "HTTP contract") |
| 4. Repeatable prep with contracts, quality checks, lineage, update/freshness policy | `load` checks, `load_batches` sha256, update fixture (D5). No policy freshness rule | Covered for the static snapshot. Built Sep 29; two load gaps are items in `IMPLEMENTATION.md` |
| 4. At least one learned component against a baseline; valid labels, no leakage, justified splits | `ConversationTurn` vs B0 keyword baseline (D3) | Covered in design; harness is D7 |
| 5. Held-out eval incl. bad or missing data, expired sessions, unauthorized access, prompt injection, tool failures, multilingual ambiguity; report success, unsafe outcomes, handoffs, latency, cost, sample sizes | `eval/` "comes later" | Open (D7); design carried in §7 |
| 6. Tracing, bounded retries, safe fallback, reproducible setup | events and trace screen, 3 attempts, fallback to `human_active`, `docker compose up` with a documented `.env` | Covered in design. The reproducible setup is built (Sep 29) |
| 6. Capacity limits, monitoring, access control, data retention, remaining deployment work | per-query `customer_id` filter | Partial: capacity, monitoring, retention not written. Organizers value stated sizing limits (§1). Deploy path documented only (D2) |
| 6. Explanations from sources, rules, execution records; no chain-of-thought | `rule_trace`, `facts` with source column, `events` | Covered |
| Credit: separate conversation, predictive risk estimate, eligibility policy | model; dataset `credit_score` as risk estimate; pure policy (D4) | Covered |
| Credit: approved rules or a labeled synthetic policy; the model does not invent rules or approve | `alba-credit-v1`, synthetic, templates only | Covered |
| Credit: explanations, uncertainty, review paths for missing or borderline data | R04, R06, R05 review band | Partial: how uncertainty is shown is not specified |
| Auth: trusted test session; an ID number alone is not identity; access enforced in the service layer | one-time code, JWT, per-query filter | Covered. Customer login built Sep 29-30 (document number plus an emailed code); consultant login built Sep 30 (D18: email and employee code plus an emailed code, `Active` consultants only) |
| Label every input as real, de-identified, synthetic, or team-generated | `README.md` data labels | Covered |
| No private records or credentials in the public repo or external model requests | PDFs and data ignored; the OpenAI request carries booleans and the message text, no profile values | Partial: customer-typed text goes to OpenAI as is (D11). History rewritten and purged Sep 28 (§0) |
| Baseline vs proposed on the same held-out workload; case mix, label quality, model and prompt versions, run variability; LLM-judge rubric validated | §7 | Open (D7) |
| Results by language and customer segment; offline results labeled as such | §7 | Open (D7) |
| Deployed link | local `docker compose up` + browser; optional host steps in ops docs only (D2) | Closed: no cloud deploy for submission. Organizers: path to production may be explained (§1) |

Not required by the brief: training a new model, multiple agents, a tool-count target, streaming, forecasting, a dashboard.

## 3. Team and working agreements

- Two people, both generalists, full-time until Oct 5. There are no fixed owners: whoever is free pulls the next unblocked item from one of three tracks in `IMPLEMENTATION.md` (Engine; Model and eval; Web). The A/B split was dropped on Sep 29 (§10).
- Nobody on the team is fluent in Portuguese. PT copy and PT test data are team-written or machine-generated and disclosed as a limitation.
- Decisions listed in §5 are asked, not assumed. The answer goes into `ARCHITECTURE.md`.
- Docs follow the "Writing docs" rules in `AGENTS.md`.

## 4. Evidence from the data

### 4.1 Demand and constraints (why this workflow)

| Evidence | Value | Sample |
|---|---|---|
| "Comercial" calls have the longest median handle time | 533 s (vs 206 s Transaccional), FCR 65%, follow-up 45% | Jan 2025 interactions, n=19,496 |
| Credit card is the most-promoted product | 52 of 200 campaigns | full `marketing_campaigns` |
| Credit pages are the top pages after login and logout | "Tarjeta de Crédito" 1,428 and "Préstamos" 1,364 page views | `digital_events` 2025-01-15, n=18,482 |
| Addressable customers | 51.2% have no credit card; 64,977 (43.3%) have an active one | full `customers` + `products` |
| Cases that cannot be auto-decided | 32.0% lack `credit_score` (15.0%) or `estimated_monthly_income` (20.0%) | full `customers`, n=150,000 |
| Existing delinquency | 14,864 customers (9.9%) have a credit product 30+ days past due | full `products` |

Consequence: about a third of customers are missing a score or an income. Missing income stays with the assistant until the customer states it. A missing score, a review-band score, or another `REFER` goes to a person. That is a design requirement, not a failure.

### 4.2 Contact reasons (Jan 2025 `call_center_interactions`, n=19,496; `contact_reason` equals `reason_category`)

| contact_reason | n | FCR | escalated | follow-up | median duration s | median wait s |
|---|---|---|---|---|---|---|
| Transaccional | 6,831 | 0.914 | 0.100 | 0.220 | 206 | 119 |
| Producto | 4,300 | 0.895 | 0.099 | 0.233 | 262 | 120 |
| Queja | 3,348 | 0.440 | 0.096 | 0.629 | 429 | 117 |
| Técnico | 2,977 | 0.686 | 0.097 | 0.412 | 363 | 120 |
| Comercial | 1,498 | 0.650 | 0.089 | 0.447 | 533 | 114 |
| Retención | 542 | 0.607 | 0.114 | 0.504 | 474.5 | 121 |

- Escalation is flat at about 10% across reasons, so it looks randomly generated.
- Channel mix: Phone 85%, then Email, App, Web Chat, WhatsApp.
- Null rates: `wait_time_seconds` 30%, `duration_seconds` 14%.

### 4.3 Data traps (for the data-quality report)

| Trap | Finding | Consequence |
|---|---|---|
| Transcripts are template-generated | Jan 2025, n=4,903: 42 distinct `customer_text`, 462 distinct `full_text`, 100% with unfilled `{monto}` / `{moneda}`. Local samples agree: 2025-03-15 (n=113) 27 distinct, 2026-06-01 (n=222) 38 distinct, all with placeholders, all `detected_language = es`. A participant reported the full table (171,321 records) has no dispute dialogue and Queja-labeled calls hold balance inquiries | An intent model trained on them memorizes; random splits leak. Do not train on them |
| Transcript labels carry no signal | `detected_intents` is `consulta_general` in 95%; the same balance-inquiry text is labeled Queja, Producto, or Transaccional; `main_topics` copies the interaction's `contact_reason` 100% of the time | No usable text-to-intent labels in the supplied data |
| Complaint text is templated | Jan 2025, n=1,998: 5 distinct `description`, 5 distinct `resolution`; `origin_interaction_id` 0% filled | Complaints cannot be linked to calls or used for NLP |
| Delinquency label is noise | see §4.4 | No predictive risk model can be learned |
| Product types differ from the dictionary | The dictionary lists English types (`Credit Card`, `Personal Loan`, `Mortgage`); the file stores `Tarjeta Crédito`, `Préstamo Personal`, `Préstamo Hipotecario` | Map the stored strings once at the load boundary (contract rule) |
| Currency inconsistency | No MXN balances in `products` or `transactions` (Mexico is in USD); incomes are local currency (median MX 39,220, CO 9,192,466, AR 801,955) | A fixed income threshold without FX would pass almost every Colombian. Convert with `daily_exchange_rates` |
| Country spelling | "México" and "Mexico" both appear in `transactions.transaction_country` | Normalize in silver if transactions are ever loaded |
| Age distribution | min 21, 14.1% over 75 | A max-age rule would be a fairness problem; we deliberately use none |
| Duplicates | Docs claim about 2%; 0 duplicate primary keys in the four loaded files and in the samples | Open: R1 |
| Timestamps vs partitions | Local sample `call_center_interactions_20260601.csv` (n=857): partition `2026-06-01` holds timestamps from 06-01 08:00 to 06-02 07:59; the 289 rows (33.7%) dated 06-02 are all between 00:00 and 07:59 | Looks like a fixed 08:00 day boundary, not random late arrival. A participant reported `transaction_date` later than `process_date` in `transactions` too. Organizers will not define `process_date`, so the assumption goes in the data-quality report. One partition checked: R4 |
| Shared emails | Full `customers.csv` (Sep 29, n=150,000): 24,203 addresses are shared by 2 to 31 customers, 79,930 rows (53.3%); in 18,615 of those groups every member shares the first word of the first and last name, so the generator built addresses from names. 2,984 rows (2.0%) have no email. `document_number` is unique. Full `service_agents.csv` (n=1,200): 12 shared addresses, 13 shared `employee_code` values; the (email, `employee_code`) pair is unique, also with case ignored; every email is lower case with no spaces; `agent_status` Active 1,090, Vacation 62, Leave 29, Inactive 19; `specialty` empty for 476 (Sep 30) | Email cannot identify a customer. Login is by document number, with the code sent to the email on file (§10, Sep 29) |
| No Portuguese, no policy documents | The bucket has only Spanish data and no policy or product-terms documents | Product catalog and policy are team-generated synthetic and labeled so |

### 4.4 The delinquency label is noise (full `products` × `customers`)

- Setup: credit products with non-null DPD, n=125,350. Targets: y30 = DPD ≥ 30 (12.5%), y90 = DPD ≥ 90 (7.5%). DPD buckets: 0 → 106,585 · 1-29 → 3,114 · 30-59 → 3,117 · 60-89 → 3,112 · 90+ → 9,422 · null → 6,622.
- Single-feature AUCs are all 0.500-0.504: credit score, income, age, customer tenure, product tenure, utilization, balance/income, limit/income, balance, limit, interest rate, number of products.
- Category rates are flat: segment 0.123-0.127, gender 0.124-0.125, country 0.124-0.125, product_status 0.124-0.131 (Blocked and Suspended no worse than Active), occupation 0.118-0.139, opening_channel 0.117-0.126.
- Full model: HistGradientBoosting, 5-fold `GroupKFold` by `customer_id`: AUC 0.498 (y30), 0.501 (y90).
- Transaction behavior does not help: Jan 2025 per-customer features (count, payments, declines, code-51 declines, amount, fraud) give AUC 0.500-0.503 on 78,499 credit products.
- Conclusion: no predictive risk model is learnable from this data. A team reporting AUC > 0.55 likely has leakage. This becomes the "model we did not ship" slide and model card.

### 4.5 Structure that does exist

- Credit score by segment (mean): Basic 600, Plus 699, Premium 797, Student 649.
- Correlations: score vs income 0.356 (income mixes currencies), credit limit vs score 0.000, credit limit vs income 0.433 (probably a currency-scale effect).
- Campaign objectives: Retention 62, Cross-sell 51, Acquisition 38, Reactivation 25, Up-sell 24. Campaign sends on 2025-01-15: credit card 648 of 1,667, open rate 36%, 0 conversions (one day only; do not quote before checking the full table).

### 4.6 Schema notes that matter for the credit workflow

- **customers** (150,000; no duplicate `customer_id` or `document_number`): `document_type` DNI 70%, CE, CC, Pasaporte (DNI appears even for Mexico and Colombia); `gender` F/M/O about a third each; `country` México 74,907, Colombia 45,251, Argentina 29,842; `segment` Basic, Plus, Premium, Student; `credit_score` observed 422-850 (dictionary says 300-850), mean 647, 15% null; `estimated_monthly_income` local currency, 20% null; `customer_status` Active 85.1%, Inactive 9.9%, Suspended 2.9%, Closed 2.0%; `detected_accent` 30% null.
- **products** (400,000; every `customer_id` exists in customers): Tarjeta Crédito 100,102, Préstamo Personal 19,960, Préstamo Hipotecario 11,910; `days_past_due` filled only for credit products (about 5% null there); credit card currency USD 55,236, COP 27,035, ARS 17,831, no MXN; `product_status` Active, Closed, Blocked, Suspended; median `credit_limit` about 45k in every segment.
- **daily_exchange_rates**: 12 directed pairs among ARS, COP, MXN, USD, daily 2023-06-17 to 2026-06-17. Columns `exchange_rate`, `buy_rate`, `sell_rate`, `source` (Central Bank, Internal, Bloomberg).
- **transactions** (Jan 2025, n=122,056): status Approved 91.8%, Declined 5.2%, Pending 2.0%, Reversed 1.0%; `response_code` 0 when approved and uniformly 05/14/51/54 otherwise (Pending and Reversed also carry them); currency USD, COP, ARS only; `amount_usd` 57% null; 24 distinct merchants; `is_fraud` 0.1%, `fraud_score` separates cleanly (non-fraud max 30.0, fraud mean 51); every transaction's `customer_id` matches its product's owner.

## 5. Open decisions

Each entry says what the Sep 27 plan assumed, what the contract says now, and what is still undecided. Decided parts are written into `ARCHITECTURE.md` and logged in §10. D12 to D16 come from the Sep 29 review of `specs/` against the contract; each one names the items it blocks in `IMPLEMENTATION.md`.

**D1. Model choice evidence and cost.** Partly closed on Sep 28: the model is GPT-6 Luna (`gpt-6-luna`) on the OpenAI API. Cost per case comes from the token usage stored in `llm_turns` times the list price ($0.10 input, $0.01 cached input, $0.50 output per 1M tokens on Sep 28, 2026; [model page](https://developers.openai.com/api/docs/models/gpt-6-luna)). Still open: whether a second model is compared on the eval subset to show model selection (ML criterion). The comparison is first on the cut list.

**D2. Deployment target.** Closed on Sep 28 (evening): no cloud deploy for the submission. Anyone tries the project with `docker compose up` and the browser. Login codes go to a local mail catcher (Mailpit), and `DEMO_LOGIN=1` turns on the test-user search (§10, Sep 29). Optional host steps are documentation only (`docs/ops.md`). Organizers said cloud deploy is not strictly required when the path to production is explained.

**D3. The evaluated learned component.** Closed on Sep 28: the `ConversationTurn` classifier (`gpt-6-luna`) on a team-labeled held-out set; baseline B0 (keyword rules). No separate runtime router.

**D4. Risk-estimate layer.** Closed on Sep 28: the dataset's `credit_score` is the external risk estimate. No risk microservice. The rejected delinquency model is documented in the model card only.

**D5. Data engineering scope.** Closed on Sep 28: load quality checks (counts, null rates, FK), `load_batches` lineage, and an update-correctness fixture. No pandera/GE suite and no policy freshness rule (R10).

**D6. Portuguese coverage.** Closed on Sep 28: the model sets `language` on each turn; PT templates are team-written; PT eval utterances are team-written or machine-translated and disclosed. R11 still measures PT quality of `gpt-6-luna` (research, not a new product decision). The UI shows a typing indicator while waiting for the API; it does not add a fixed sleep for "analysis time".

**D7. Evaluation harness and baselines.** The contract defers `eval/`. The brief makes it mandatory. The Sep 27 design is in §7. Still open: whether B0/B1/P stay as designed (B1 would also run on `gpt-6-luna`), how many cases and repeated runs fit the API budget and rate limits, and the spend cap for eval runs.

**D8. Confirmation step.** Closed on Sep 28: soft consent before the first `policy.run`. After `prequalify_card` / `prequalify_loan`, template `confirm_prequalify`; only `confirm_prequalify` with a product set runs the policy. `decline_prequalify` leaves `ai_active`. Income follow-up on the same process does not ask again.

**D9. Prompt-injection defense.** Closed on Sep 28: structural defense only (booleans, JWT, no tools, `reply_forbidden`). Evaluated in the held-out suite. No injection classifier.

**D10. Contract known gaps.** Closed on Sep 28. The thirteen gaps are written into `ARCHITECTURE.md`. None remain open. Template sentences are still not written; that is named in the contract, not left as a gap.

**D11. Customer text sent to OpenAI.** The model is now an external service, and the brief forbids private records in external model requests. The prompt already carries only booleans, the process state, the catalog, and the message text. Still open: whether ID-like numbers typed by the customer are masked before the call, and what `docs/ops.md` says about OpenAI's handling and retention of API data.

**D12. The policy run key repeats after `NEEDS_INFO`.** The contract keys `policy.run` as `policy:{process_id}:alba-credit-v1:{product}` (**Events**, idempotency keys). Juliana's first run, after "sí", returns `NEEDS_INFO`. Her second run, after she states an income, has the same process and product, so the key collides and the run is dropped as a duplicate. `specs/06-income-request.feature` "A stated income lets the decision continue" cannot pass, and neither can Juliana's oracle flow. Options: (a) add the triggering event, `policy:{process_id}:alba-credit-v1:{product}:{triggered_by_event_id}`; a message sent twice still maps to one turn, so it still collides; (b) a run counter on the process. Recommendation: (a), the same pattern as the turn, template, and transition keys. Blocks E3 and E9.

**D13. A second vague request cannot reach `out_of_scope`.** The contract says "el crédito" is `clarify` the first time and `out_of_scope` when it still names no product after one clarification (**How the model is called**). The prompt carries the message text, the process state, four booleans, and the catalog. Nothing tells the model that a clarification already happened, so the second "el crédito" is classified `clarify` again and the case never leaves the loop. Blocks `specs/03-product-clarification.feature` "A request that still names no product goes to a person". Options: (a) one more boolean in the prompt, `product_already_asked`, computed by `conversation.generate` from this process's events; the model still decides; (b) send earlier turns of the thread, which sends more customer text to OpenAI (D11); (c) decide it outside the model: `conversation.generate` stamps the number of earlier `clarify` turns on the turn, a new rule moves a second `clarify` with no product to `human_active` with `out_of_scope`, and `show_reply` stops matching that turn. Recommendation: (c). It is testable in pytest with injected JSON and does not rely on the model following the prompt; it costs one rule and one payload field. Blocks E3 and M2.

**D14. An income typed before consent runs the policy.** `ask_confirm_prequalify` stores the product on the process. If the customer answers the consent question with an amount ("gano 45,000 pesos al mes") instead of "sí", the turn is `provide_income` with the stored product, and `run_policy_income` enqueues `policy.run` without consent. That goes against consent before any `policy.run` (**What gets built**, **What the customer can be asked**). No spec covers it. Options: (a) `run_policy_income` also requires that the last analysis on this process for that product was `NEEDS_INFO`, a fact `conversation.generate` stamps on the turn because rules cannot query; an income before consent gets the consent question again, and the typed amount is not kept; (b) treat an income before consent as consent, and write that down. Recommendation: (a), plus a scenario in `specs/04-prequalification-consent.feature`. Blocks E3.

**D15. Handoffs that are not a policy `REFER`.** `hand_off_human`, `hand_off_scope`, `hand_off_language`, `hand_off_reply`, and the third failed attempt (`tool_failed`) move a case to `human_active` with no `analysis.completed`. Three things were undefined: (1) the customer gets no message, so the thread goes silent; only `REFER` sends `refer_notice`; (2) the consultant packet is read from `analysis.completed`, which these cases do not have; (3) the consultant can only close as `PREQUALIFIED` or `NOT_PREQUALIFIED`, which renders a certificate for a policy that never ran, sometimes with `product` null. (2) is settled in `ARCHITECTURE.md` "HTTP contract" (Sep 29, e0e3532): the analysis fields of the packet are null when there is no `analysis.completed`, and `reason_code` comes from `conversation.thread_taken`. Options for (1): send `refer_notice` on every move to `human_active`, or add a handoff template. For (3): (a) allow the close only on a case with a product and an analysis, and leave the others in the queue; (b) a third close outcome with its own template, which brings back something like the removed `referred_closed`. Recommendation for (1): `refer_notice` for every handoff. (3) needs a team answer. Blocks the non-`REFER` parts of E8 and W5, and their scenarios in `specs/07-handoff-to-consultant.feature` and `specs/08-consultant-close.feature`.

**D16. Contract wording the code cannot follow as written.** (2) Closed Sep 30: `decide(profile, product, declared_income)`, null when none was stated. Written into `ARCHITECTURE.md` "Policy `alba-credit-v1`". (1) Still open: `ask_which_product` has no `language` check, so a `provide_income` or `confirm_prequalify` turn with `language = other` matches it and `hand_off_language` at once, and `template.send` has no `other` locale. Recommendation: add "`language` is `es` or `pt`" as in the other rules. Blocks E3. (3) Still open: "Only the `process.transition` worker changes `processes.state`", yet `process.end` sets `state = ended`. Recommendation: name both commands in that sentence. Blocks E4 in wording only.

**D17. No route lists a customer's cases.** `ARCHITECTURE.md` "HTTP contract" has `GET /case/{process_id}` but no list. After a reload or a new login, the web app cannot find an open case or an issued certificate unless it kept the `process_id` from a `POST /messages` response. `specs/05-prequalification-decision.feature` "When Juan opens his certificate" depends on it. Options: (a) `GET /cases`, the session customer's processes, newest first; (b) the session or products response carries the open process id; (c) `GET /case/latest`. Recommendation: (a). Blocks the case screen after a reload (W4) and E8.

**D18. How a consultant identifies at login.** Closed and built on Sep 30. Consultants log in on their own page, `/consultant/login`, with their email and employee code. Neither is unique alone (§4.3), but the pair is unique for all 1,200 consultants. The code goes to that email, with the customer code's rules. Only `agent_status = Active` (1,090 of 1,200) gets a code; every pair and status gets the same answer. `POST /consultant/session` takes the email, the employee code, and the code, which closes the code-only route. `consultant_id` is unique too, but it was not chosen. Built choices, Sep 30: both fields are trimmed and matched without case; `Active` is checked again when the session opens; the demo search lists only `Active` consultants and has a random pick; `GET /consultant/me` feeds the `/consultant` greeting; each login page links to the other. Written into `ARCHITECTURE.md` "Auth and screens".

## 6. Research backlog (research phase)

1. **R1 Duplicates.** The docs claim about 2%; the samples and the four loaded files show no duplicate primary keys. Find the business key per fact table (for transactions, for example customer + amount + timestamp).
2. **R2 `data_backup_20260831/` vs `data/`.** Compare file lists, headers, row counts per partition, and changed rows. Probably the schema-evolution or late-arrival case the docs mention. The backup has the dimension CSVs plus 5 fact tables (no `call_transcripts`, no `satisfaction_surveys`).
3. **R3 Schema evolution.** Compare CSV headers of 2023 and 2026 partitions for every fact table.
4. **R4 Timestamp vs `process_date`.** One partition shows a fixed 08:00 day boundary (§4.3). Check other partitions and tables before writing the freshness policy.
5. **R5 Full-table recount** of the Jan 2025 numbers (contact reasons, complaints, campaigns) before they go on slides.
6. **R6 `satisfaction_surveys`**: not profiled yet.
7. **R7 FX sanity check**: convert incomes to USD per country and confirm the medians land in a similar range.
8. **R8 Oracle rows**: re-read the four oracle customers and César from `data/raw/` in this checkout and confirm every value in `ARCHITECTURE.md` (the Sep 27 numbers were measured in an earlier session).
9. **R9 `product_type` values**: list every distinct value in `products.csv` and record the mapping to product keys.
10. **R10 Stray files**: a `marketing_campaigns.csv` sits at the bucket root, outside `data/`. Check whether it differs from `data/marketing_campaigns.csv`.
11. **R11 `gpt-6-luna` on the API**: latency per turn, tokens and cost per turn, Structured Outputs validity rate, whether `temperature` 0 is accepted (it is a reasoning model and the docs do not say), and Spanish and Portuguese intent quality on a small hand-written set. Feeds D1, D6, D7.
12. **R12 Other call transcripts.** Asked whether dispute transcripts exist, an organizer replied to look in the documentation "to find other call transcripts" (`#technical-help`, Sep 27). Check the data dictionary, the bucket listing, and `data_backup_20260831/` for another transcript source.

## 7. Evaluation design (carried from Sep 27; pending D1, D3, D7)

### 7.1 Scenario suite

About 300 held-out cases built from real customer profiles, stratified by policy outcome × country × segment × language. Each case has an `expected_route` (answer, clarify, pre-qualify, refer, refuse) and an `expected_decision` (the policy run on the profile). Customers in the test suite are disjoint from any customer used while tuning prompts.

| Slice | Share | Examples |
|---|---|---|
| Normal | ~45% | pre-qualify (every outcome), product questions |
| Ambiguous or unsupported | ~20% | "quiero un crédito", mortgage, missing amount, mixed ES/PT |
| Human-required | ~15% | review-band score, DPD 1-29, missing score, customer asks for a human |
| Adversarial or failure | ~20% | prompt injection (ES/PT), asking for another customer's data, expired session, injected tool timeout or 500, missing profile fields |

### 7.2 Systems on the same suite

- **B0, rules bot:** keyword menu plus the policy (status-quo automation).
- **B1, naive LLM agent:** the policy described in the prompt, no external enforcement. Expected to produce unsafe outcomes; that is the contrast.
- **P:** the proposed system.

### 7.3 Metrics (the brief's names)

- **Safe automated resolution:** rate over all in-scope cases, plus the share where automation was attempted.
- **Containment:** reported separately, never as success.
- **Escalation quality:** missed and unnecessary transfers; handoff completeness.
- **Unsafe outcomes:** counts with denominators and Wilson 95% intervals. Categories: cross-customer disclosure, invented eligibility or rate, action without confirmation, materially wrong decision.
- **Efficiency:** p50/p95 end-to-end latency; cost per attempted case and per safe resolution ("not defined" if none), from token usage times the list price on the run date (D1).
- **Breakdowns:** by language (ES-MX, ES-CO, ES-AR, PT) and by segment, gender, age band, with small-sample caveats.
- **Variability:** repeated runs on a subset for the LLM systems.
- **LLM judge:** only for tone, clarity, and language correctness, with a written rubric validated on 60 items labeled by both of us (report agreement). Correctness is checked deterministically.
- Offline results, simulations, and projected savings are labeled as such and kept apart.

## 8. Schedule (updated Sep 29)

The dates fixed on Sep 27 are kept: feature freeze Fri Oct 2 night, pairing Sat and Sun, submission by midday Mon Oct 5. Each day ends at a milestone of `IMPLEMENTATION.md`; the items behind each milestone are listed there.

| Day | Target by that night | Status |
|---|---|---|
| Mon Sep 28 | Definition: D2 to D6 and D8 to D10 closed into `ARCHITECTURE.md`. C4 page and `specs/` drafted | Done |
| Tue Sep 29 | Compose load path: migrations, bronze, silver, gold, load checks per D5 (planned for Wed). Spec review, D12 to D16 logged, `IMPLEMENTATION.md` | Done |
| Wed Sep 30 | Milestone 1: interfaces agreed. D12 to D16 decided. Policy engine and event loop decide the four oracle cases in pytest with injected turns. R8, R9, R11 done | Behind: the customer and consultant logins were built first (I1, E6, W2, W8 done; D18 decided). D12 to D16, E1 to E4, and R8, R9, R11 not started |
| Thu Oct 1 | Milestone 2: model adapter live, auth and every route, templates ES and PT, web screens against the local stack, held-out set frozen, B0 | |
| Fri Oct 2 | Milestone 3: web on the real API, the four oracle flows in the browser, first full eval run, ops path docs per D2. **Feature freeze at night** | |
| Sat Oct 3 | **Pair:** fix top failures, repeated runs, model comparison per D1, language and segment breakdowns, latency and cost tables, judge validation | |
| Sun Oct 4 | **Pair:** README, docs, limitations, video, slides; numbers locked from a tagged commit | |
| Mon Oct 5 | Buffer. Submit by midday | |

Cut list if behind, in order: model comparison, LLM judge, B0, PT templates for rarer intents, trace screen. Never cut: policy enforcement outside the model, held-out eval with unsafe-outcome counts, the handoff packet, the data-quality report.

## 9. Submission package

1. Public repo `factored-hackathon-2026-<team name>`, for review: README with local `docker compose up` first, architecture diagram, `docs/data_quality.md`, `docs/model_card_risk.md` (the model we did not ship), a model card for the D3 component, `docs/policy.md`, `docs/ops.md` (optional deploy path), `docs/limitations.md`, `eval/reports/`.
2. How to try it: `docker compose up` + browser, with test-login instructions (synthetic customers only; codes read in Mailpit; the `DEMO_LOGIN=1` search). No cloud deploy link for submission (D2).
3. Slides (4-6):
   1. Problem and evidence (demand, the 32% missing-data constraint, data traps)
   2. Architecture: conversation, risk estimate (`credit_score`), and policy separated; soft consent; customer isolation
   3. ML: the model we did not ship, and the D3 component against its baseline
   4. Evaluation: B0 vs B1 vs P, unsafe outcomes with intervals
   5. Language and segment breakdowns
   6. Route to production (compose locally; optional host) and honest limitations
4. Video (at most 3 minutes, per organizers): normal pre-qualification in Spanish (incl. consent); ambiguous request and clarification; review case and the packet in the consultant console; a Portuguese conversation; an injection or cross-customer attempt blocked; 60 s of metrics and architecture. Trim the list to fit 3 minutes.

## 10. Decision log

| Date | Decision | Why |
|---|---|---|
| Sep 27 | Workflow: simulated credit pre-qualification for credit card and personal loan | Demand and constraint evidence in §4.1. Kept after the delinquency label turned out to be noise |
| Sep 27 | No delinquency model is shipped | AUC 0.50 (§4.4). It becomes a rigor slide |
| Sep 27 | Parked: disputed-charge intake | It was the first recommendation (a learned transaction matcher with labels by construction; "Cobro indebido" plus "Cargo no reconocido" are 37% of complaints). Jael chose credit pre-qualification instead |
| Sep 27 | Parked: card declines and blocking | Decline codes 05/14/51/54, 5.2% of transactions. Simplest, but a low ML ceiling |
| Sep 27 | Parked: balance inquiries | It is what the transcripts contain, so many teams will build it |
| Sep 28 | The contract replaces the Sep 27 stack: Ollama `llama3.2:3b` instead of the Claude API; Postgres 16 in Docker and an own JWT instead of Supabase Auth and RLS. The Ollama part is superseded below | `docker compose up` gives the same chat with no key or account |
| Sep 28 | Model: GPT-6 Luna (`gpt-6-luna`) on the OpenAI API replaces Ollama `llama3.2:3b`. Stack stays FastAPI and Postgres | Team decision. Consequences: runs need `OPENAI_API_KEY` and cost money per call; the deploy host no longer needs RAM for a local model; customer text now reaches an external service (D11) |
| Sep 28 | Postgres runs inside the Docker Compose stack (local try path; optional host later) | Team decision |
| Sep 28 | Reviewers use the deployed link and read the repo; they are not expected to run the stack. The team provides keys on request | Team decision. Drops the earlier goal of running with no key |
| Sep 28 | Policy trimmed to R01-R06 and R09. R07 (income threshold), R08 (indicative limit), and R10 (freshness) removed; R05 bands are <580, 580-619, ≥620 | R08: a limit number would be a promise. R07 is left open on purpose in the contract. No reason was recorded for dropping R10 (see D5) |
| Sep 28 | Docs standardized in English; `ARQUITECTURA.md` became `ARCHITECTURE.md`; `HANDOFF.md` folded into this file and `README.md` | One home per fact |
| Sep 28 | Organizer PDFs removed from git history | The data dictionary holds the S3 keys and the repo will be public |
| Sep 28 | The thirteen known gaps are closed | First message, turn event, templates for `NEEDS_INFO` and `REFER`, language on the event, product on the process, closed `reason_code` list, consultant close, file wins on income, JWT for another customer |
| Sep 28 | A typed income fills a null and evaluation continues. The file wins when income is present. Juliana, score 714, pre-qualifies after she states an amount | She is not sent to review only because the number was typed |
| Sep 28 | The consultant does not chat. Close is `PREQUALIFIED` or `NOT_PREQUALIFIED`, plus a template | `referred_closed` is not an end reason |
| Sep 28 | `load` copies four S3 keys with `aws s3 cp` into Postgres read tables and gold. The API does not call S3 | Chat reads one gold row |
| Sep 28 (evening) | No cloud deploy for submission. Try via `docker compose up` + browser; `DEMO_INBOX=1` locally; optional host steps in ops docs only (D2) | Team decision. Aligns with organizer note that deploy is not strict when the production path is explained |
| Sep 28 (evening) | Soft consent before first `policy.run`: template `confirm_prequalify`; intents `confirm_prequalify` / `decline_prequalify` (D8) | Brief requires naming what needs confirmation; only action in-scope is simulated pre-qualification |
| Sep 28 (evening) | Prompt-injection defense is structural only; measured in eval (D9) | Keeps permissions outside the model; classifier would be cut-list work |
| Sep 28 (evening) | Learned component: `ConversationTurn` vs B0 keywords (D3). Risk estimate: dataset `credit_score` (D4). Load checks + update fixture (D5). PT: model `language` + team/MT copy disclosed (D6) | Closes definition items for Mon-Tue |
| Sep 29 | Work is pulled from three tracks in `IMPLEMENTATION.md` (Engine; Model and eval; Web) with no fixed owners. Replaces the A/B split | Team decision. With the load path done, B waited on the system while A held the policy, the loop, the model, auth, and all six screens, and the web app waited on the backend |
| Sep 29 | The contract holes found by the spec review are logged as D12 to D16, not closed | Team decision. Each is decided before the items it blocks |
| Sep 29 | Customer login is a real login: the document number, then a 6-digit code emailed to the address on file. `POST /session` takes the document with the code; 5 wrong tries spend a code; codes are stored hashed; the send-code answer is the same for every document. Codes go only to Mailpit in the compose stack. Search and random pick stay as demo helpers behind `DEMO_LOGIN=1`, which replaces `DEMO_INBOX` | Team decision. Email alone cannot identify a customer (53% of rows share one, §4.3); the dataset's addresses are on real domains; a public search over 150,000 names and documents would leak them |
| Sep 30 | Consultant login (D18): a separate `/consultant/login` page, email plus employee code, the code emailed, `Active` consultants only. Built later; the customer login stays the focus | Team decision. The pair is the unique login a staff member would know; `employee_code` and email are each shared by a few consultants |
| Sep 30 | Consultant login built: the `/consultant` landing greets the consultant from `GET /consultant/me` (name, employee code, specialty); email and employee code are trimmed and matched without case; the demo search lists only `Active` consultants and picks one at random; the customer login links to `/consultant/login` and the README names it | Team decision. The sidebar in `DESIGN.md` needs the same fields; consultants type their own email and code by hand; an away consultant in the search would never get a code; reviewers need to find the page |
| Sep 30 | Build one C4 component at a time (screen, then routes, then engine) against the local stack. The MSW browser mock tried on Sep 29 was removed | Team decision. A component that runs end to end is easier to judge than a track of items; the mock was extra code nobody needed |
| Sep 30 | Wire enums get named aliases in `api/contract_models.py`, appended by `api-spec/generate.py` (I1 in `IMPLEMENTATION.md`) | Team decision. One source for every closed set on the wire; the generator's `--collapse-root-models` left no names to import |
| Sep 30 | The people who review handed-off cases are consultants ("asesor" on screen) in the API, the web app, the wire contract, events, rules, and docs. `db/` and `pipeline/` keep `service_agents`, `agent_id`, and `agent_status`. | Team decision. The team needs the word agent for the AI agent (`AGENTS.md`, "Consultants and service agents") |
