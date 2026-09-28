# Plan: Alba at the Factored AI & Data Hackathon 2026

Status on Mon Sep 28, 2026: **research and definition phase.** There is no application code yet.

`ARCHITECTURE.md` is the contract. This file tracks what the brief asks for, what the data shows, what is still open, and when each piece happens. Where this file and the contract disagree, the contract wins and the disagreement is an open decision in §5. A closed decision is written into `ARCHITECTURE.md` in the same change, and its entry here moves to the decision log (§10).

Sources: the organizer PDFs in `docs/` (problem statement, kickoff deck, dataset summary, data dictionary; local only, never committed) and profiling of the S3 bucket on Sep 27-28. Every data number says which sample it comes from.

## 0. Repo hygiene

- [x] Organizer PDFs removed from git history (Sep 28). They stay in `docs/`, ignored by `.gitignore`.
- [x] Old commit with the PDFs purged (Sep 28): `main` and `rebranch` both start from the clean root, the reflog was expired, and `git gc` found no unreachable objects or PDF blobs.
- [x] Secret scan (Sep 28, gitleaks 8.30.1): all 3 commits on every branch and the committable working-tree files, no leaks found. A planted fake AWS key was caught, so the scanner works. Re-run before the first push.
- [ ] Add a secret scanner as a pre-commit hook.
- [ ] Commit `.env.example` with empty values for the variables listed in `README.md` (AWS, `S3_BUCKET`, `OPENAI_API_KEY`, `JWT_SECRET`).
- [ ] The public repo must be named `factored-hackathon-2026-<team name>`. Keep it private until submission day.
- [ ] Both team members commit to the repo: organizers treat the GitHub contributors at submission as the team. If a registration email differs from the GitHub email, say so in the submission.

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
| Normal, ambiguous or unsupported, and human-required paths | Juan (normal), "quiero un crédito" (clarify), mortgage and others (`out_of_scope`), Alicia and Juliana (human) | Covered |
| Spanish and Portuguese interactions; report language limits | `es` and `pt` templates; the model may clarify in Portuguese | Partial: PT test data and PT quality of `gpt-6-luna` not measured (D6) |
| 1. Problem supported by data (contact reasons, demand, data quality, constraints) | §4 of this file | Partial: Jan 2025 numbers come from one month and need a full-table recount (R5) |
| 2. Context, clarification, grounding, tools, only verified actions reported | events per process, `ConversationTurn`, `facts` cite source columns | Covered in design, but see known gaps 1, 4, 5 in the contract |
| 3. What it answers, what needs confirmation, when it abstains or transfers | rules table, transitions, `out_of_scope` | Partial: which actions need confirmation is not defined (D8) |
| 3. Permissions and policy enforced outside model prose | JWT `customer_id`, pure policy, templates | Covered |
| 3. Handoff with request, verified facts, actions taken, evidence, open questions | packet read from `analysis.completed` | Partial: the packet schema and "open questions" field are not specified |
| 4. Repeatable prep with contracts, quality checks, lineage, update/freshness policy | `load` container, `load_batches` sha256, load report counts | Partial: contracts, lineage, freshness, and an update-correctness fixture are open (D5) |
| 4. At least one learned component against a baseline; valid labels, no leakage, justified splits | not in the contract | Open (D3) |
| 5. Held-out eval incl. bad or missing data, expired sessions, unauthorized access, prompt injection, tool failures, multilingual ambiguity; report success, unsafe outcomes, handoffs, latency, cost, sample sizes | `eval/` "comes later" | Open (D7); design carried in §7 |
| 6. Tracing, bounded retries, safe fallback, reproducible setup | events and trace screen, 3 attempts, fallback to `human_active`, `docker compose up` with a documented `.env` (reviewers use the deployed link; the team provides keys on request) | Covered |
| 6. Capacity limits, monitoring, access control, data retention, remaining deployment work | per-query `customer_id` filter | Partial: capacity, monitoring, retention not written |
| 6. Explanations from sources, rules, execution records; no chain-of-thought | `rule_trace`, `facts` with source column, `events` | Covered |
| Credit: separate conversation, predictive risk estimate, eligibility policy | model and policy separated | Partial: the risk-estimate layer is not named (D4) |
| Credit: approved rules or a labeled synthetic policy; the model does not invent rules or approve | `alba-credit-v1`, synthetic, templates only | Covered |
| Credit: explanations, uncertainty, review paths for missing or borderline data | R04, R06, R05 review band | Partial: how uncertainty is shown is not specified |
| Auth: trusted test session; an ID number alone is not identity; access enforced in the service layer | one-time code, JWT, per-query filter | Covered |
| Label every input as real, de-identified, synthetic, or team-generated | `README.md` data labels | Covered |
| No private records or credentials in the public repo or external model requests | PDFs and data ignored; the OpenAI request carries booleans and the message text, no profile values | Partial: customer-typed text goes to OpenAI as is (D11). History rewritten and purged Sep 28 (§0) |
| Baseline vs proposed on the same held-out workload; case mix, label quality, model and prompt versions, run variability; LLM-judge rubric validated | §7 | Open (D7) |
| Results by language and customer segment; offline results labeled as such | §7 | Open (D7) |
| Deployed link | the same compose stack, Postgres included, on a deploy host | Open: host not chosen (D2) |

Not required by the brief: training a new model, multiple agents, a tool-count target, streaming, forecasting, a dashboard.

## 3. Team and working agreements

- Two people, both generalists, full-time until Oct 5. Work is split by component: **A** owns the system (API, worker, policy, frontend, deploy), **B** owns data and evaluation (pipeline, research items, eval harness, analysis).
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

Consequence: about a third of pre-qualification requests must take a collect-info or human-review path. That is a design requirement, not a failure.

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
| Transcripts are template-generated | Jan 2025, n=4,903: 42 distinct `customer_text`, 462 distinct `full_text`, 100% with unfilled `{monto}` / `{moneda}`. Local samples agree: 2025-03-15 (n=113) 27 distinct, 2026-06-01 (n=222) 38 distinct, all with placeholders, all `detected_language = es` | An intent model trained on them memorizes; random splits leak. Do not train on them |
| Transcript labels carry no signal | `detected_intents` is `consulta_general` in 95%; the same balance-inquiry text is labeled Queja, Producto, or Transaccional; `main_topics` copies the interaction's `contact_reason` 100% of the time | No usable text-to-intent labels in the supplied data |
| Complaint text is templated | Jan 2025, n=1,998: 5 distinct `description`, 5 distinct `resolution`; `origin_interaction_id` 0% filled | Complaints cannot be linked to calls or used for NLP |
| Delinquency label is noise | see §4.4 | No predictive risk model can be learned |
| Product types differ from the dictionary | The dictionary lists English types (`Credit Card`, `Personal Loan`, `Mortgage`); the file stores `Tarjeta Crédito`, `Préstamo Personal`, `Préstamo Hipotecario` | Map the stored strings once at the load boundary (contract rule) |
| Currency inconsistency | No MXN balances in `products` or `transactions` (Mexico is in USD); incomes are local currency (median MX 39,220, CO 9,192,466, AR 801,955) | A fixed income threshold without FX would pass almost every Colombian. Convert with `daily_exchange_rates` |
| Country spelling | "México" and "Mexico" both appear in `transactions.transaction_country` | Normalize in silver if transactions are ever loaded |
| Age distribution | min 21, 14.1% over 75 | A max-age rule would be a fairness problem; we deliberately use none |
| Duplicates | Docs claim about 2%; 0 duplicate primary keys in the four loaded files and in the samples | Open: R1 |
| Timestamps vs partitions | Local sample `call_center_interactions_20260601.csv` (n=857): partition `2026-06-01` holds timestamps from 06-01 08:00 to 06-02 07:59; the 289 rows (33.7%) dated 06-02 are all between 00:00 and 07:59 | Looks like a fixed 08:00 day boundary, not random late arrival. One partition only: R4 |
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

## 5. Open decisions (definition phase)

Each entry says what the Sep 27 plan assumed, what the contract says now, and what is still undecided. Decided parts are written into `ARCHITECTURE.md` and logged in §10.

**D1. Model choice evidence and cost.** Partly closed on Sep 28: the model is GPT-6 Luna (`gpt-6-luna`) on the OpenAI API. Cost per case comes from the token usage stored in `llm_turns` times the list price ($0.10 input, $0.01 cached input, $0.50 output per 1M tokens on Sep 28, 2026; [model page](https://developers.openai.com/api/docs/models/gpt-6-luna)). Still open: whether a second model is compared on the eval subset to show model selection (ML criterion). The comparison is first on the cut list.

**D2. Deployment target.** The brief requires a link to the deployed tool. Decided on Sep 28: the deploy host runs the same `docker compose` stack as local, with Postgres inside it (no managed database), and `OPENAI_API_KEY` in the host's secrets. Reviewers use the deployed link and read the repo; they are not expected to run it, and the team provides keys if one needs to. With the model on the OpenAI API, the host no longer needs RAM for a local model. Still open: the host, and whether the public deploy runs with `DEMO_INBOX=1`.

**D3. The evaluated learned component.** The brief requires at least one learned component evaluated against a baseline, with valid labels and leakage prevention. The Sep 27 plan had a separate intent and out-of-scope router (keyword rules vs TF-IDF + LR vs multilingual-e5 + LR vs zero-shot LLM) trained on team-created labels. The contract has no router: the LLM classifies intent through `ConversationTurn`. Still open: which component is evaluated (the LLM classifier on a team-labeled set, or an added router, which is a contract change), its baseline, and the label set.

**D4. Risk-estimate layer.** The brief asks to keep conversation, predictive risk estimate, and eligibility policy separate. The Sep 27 plan had a risk service (v0: score to band, synthetic PD table) plus a model card for the rejected delinquency model. The contract forbids a delinquency model and R05 reads `credit_score` directly. Still open: whether the dataset's `credit_score` is presented as the external risk estimate (with the model card as evidence), or a separate risk service exists (a contract change).

**D5. Data engineering scope.** The contract loads four static dimension files with a sha256 manifest and a count report. The brief asks for contracts, quality checks, lineage, a freshness policy, and, with static data, a labeled fixture proving update correctness. The Sep 27 plan had pandera or Great Expectations checks, `source_files[]` and `batch_id` lineage, a freshness rule (R10, now absent from the policy), and a late-arrival plus schema-evolution fixture. Still open: which of those enter the contract.

**D6. Portuguese coverage.** The contract has a `pt` template and lets the model clarify in Portuguese. Still open: where PT test utterances come from, how they are disclosed, and how well `gpt-6-luna` handles PT (measure, R11).

**D7. Evaluation harness and baselines.** The contract defers `eval/`. The brief makes it mandatory. The Sep 27 design is in §7. Still open: whether B0/B1/P stay as designed (B1 would also run on `gpt-6-luna`), how many cases and repeated runs fit the API budget and rate limits, and the spend cap for eval runs.

**D8. Confirmation step.** The brief asks which actions require confirmation. The Sep 27 plan had a soft-check consent before running a pre-qualification. The contract has none. Still open: whether `policy.run` requires explicit consent.

**D9. Prompt-injection defense.** The Sep 27 plan had input guards (injection heuristics and classifier) and an output guard (every number in a reply must appear in tool results). The contract relies on structure: the model sees only booleans, has no tools, `customer_id` comes from the JWT, and forbidden phrases in `reply_text` escalate. Still open: whether that is enough and how it is evaluated.

**D10. Contract known gaps.** Thirteen internal gaps listed at the end of `ARCHITECTURE.md` (first message never reaches the model, the model turn is not an event, no `NEEDS_INFO` or `REFER` renderer, open `reason_code` list, and others). They block implementation of the worker and rules. The switch to OpenAI does not change them.

**D11. Customer text sent to OpenAI.** The model is now an external service, and the brief forbids private records in external model requests. The prompt already carries only booleans, the process state, the catalog, and the message text. Still open: whether ID-like numbers typed by the customer are masked before the call, and what `docs/ops.md` says about OpenAI's handling and retention of API data.

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

## 7. Evaluation design (carried from Sep 27; pending D1, D3, D7)

### 7.1 Scenario suite

About 300 held-out cases built from real customer profiles, stratified by policy outcome × country × segment × language. Each case has an `expected_route` (answer, clarify, pre-qualify, refer, refuse) and an `expected_decision` (the policy run on the profile). Customers in the test suite are disjoint from any customer used while tuning prompts.

| Slice | Share | Examples |
|---|---|---|
| Normal | ~45% | pre-qualify (every outcome), product questions |
| Ambiguous or unsupported | ~20% | "quiero un crédito", mortgage, missing amount, mixed ES/PT |
| Human-required | ~15% | review-band score, DPD 1-29, missing income, customer asks for a human |
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

## 8. Schedule (proposed Sep 28; confirm)

The Sep 27 day-by-day assumed the old stack. The dates that were fixed then are kept: feature freeze Fri Oct 2 night, pairing Sat and Sun, submission by midday Mon Oct 5.

| Days | A (system) | B (data and eval) |
|---|---|---|
| Mon Sep 28 - Tue Sep 29 | Definition: close D2, D8, D9, D10 into `ARCHITECTURE.md`. Repo skeleton, compose with Postgres | Research R1-R11 (R8, R9, R11 first). Close D3, D4, D5, D6. Start the data-quality report |
| Wed Sep 30 | Migrations, events, rules, worker, policy engine with unit tests (oracle test green) | Pipeline bronze, silver, gold; contracts per D5; eval labels and splits per D3 |
| Thu Oct 1 | Model adapter, templates ES and PT, auth and login codes | Eval harness, scenario generator, B0 and B1 |
| Fri Oct 2 | Frontend screens from the mock; deploy per D2. **Feature freeze at night** | First full eval run, error analysis, ranked fix list |
| Sat Oct 3 | **Pair:** fix top failures, repeated runs, model comparison per D1 | **Pair:** language and segment breakdowns, latency and cost tables, judge validation |
| Sun Oct 4 | **Pair:** README, docs, limitations, video | **Pair:** slides; numbers locked from a tagged commit |
| Mon Oct 5 | Buffer. Submit by midday | Buffer |

Cut list if behind, in order: model comparison, LLM judge, B0, PT templates for rarer intents, trace screen. Never cut: policy enforcement outside the model, held-out eval with unsafe-outcome counts, the handoff packet, the data-quality report.

## 9. Submission package

1. Public repo `factored-hackathon-2026-<team name>`, for review: README with the deployed link first, then the setup the team uses (keys provided on request), architecture diagram, `docs/data_quality.md`, `docs/model_card_risk.md` (the model we did not ship), a model card for the D3 component, `docs/policy.md`, `docs/ops.md`, `docs/limitations.md`, `eval/reports/`.
2. Deployed link (D2), with test-login instructions (synthetic customers only). This is how reviewers try the system.
3. Slides (4-6):
   1. Problem and evidence (demand, the 32% missing-data constraint, data traps)
   2. Architecture: conversation, risk estimate, and policy separated; customer isolation
   3. ML: the model we did not ship, and the D3 component against its baseline
   4. Evaluation: B0 vs B1 vs P, unsafe outcomes with intervals
   5. Language and segment breakdowns
   6. Route to production and honest limitations
4. Video (3-4 min): normal pre-qualification in Spanish; ambiguous request and clarification; review case and the packet in the agent console; a Portuguese conversation; an injection or cross-customer attempt blocked; 60 s of metrics and architecture.

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
| Sep 28 | Postgres runs inside the Docker Compose stack, locally and on the deploy host | Team decision |
| Sep 28 | Reviewers use the deployed link and read the repo; they are not expected to run the stack. The team provides keys on request | Team decision. Drops the earlier goal of running with no key |
| Sep 28 | Policy trimmed to R01-R06 and R09. R07 (income threshold), R08 (indicative limit), and R10 (freshness) removed; R05 bands are <580, 580-619, ≥620 | R08: a limit number would be a promise. R07 is left open on purpose in the contract. No reason was recorded for dropping R10 (see D5) |
| Sep 28 | Docs standardized in English; `ARQUITECTURA.md` became `ARCHITECTURE.md`; `HANDOFF.md` folded into this file and `README.md` | One home per fact |
| Sep 28 | Organizer PDFs removed from git history | The data dictionary holds the S3 keys and the repo will be public |
