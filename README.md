# Alba: credit pre-qualification assistant

Alba is a customer-service system for the synthetic LATAM bank of the Factored AI & Data Hackathon 2026. A customer asks about a credit card or a personal loan, in Spanish or Portuguese. A versioned policy decides. The language model only reads the customer's sentence and never decides. When the case is borderline, a score is missing, or the request is out of scope, the thread goes to a person, who closes it as pre-qualified or not.

It is not a production bank and it moves no money. Customers, products, scores, incomes, and consultants come from the organizer dataset (snapshot of June 17, 2026). The policy is synthetic, and the certificate says so.

## Contents

- [What it does](#what-it-does): the workflow, from login to the consultant's close.
- [Status](#status): what is built, what is not, and the known limitations.
- [How it works](#how-it-works): the architecture, the key decisions and where each is documented, and the stack.
- [Run it locally](#run-it-locally): `.env`, `docker compose up`, the URLs, demo mode, and troubleshooting.
- [Try the four flows](#try-the-four-flows): the four test customers, the consultant, and the policy rules.
- [Tests and quality gate](#tests-and-quality-gate): the one test command, host setup, the dataset checks, browser flows, and CI.
- [Deploying (Vercel and a container host)](#deploying-vercel-and-a-container-host): how it would go online, step by step.
- [Evaluation](#evaluation): Claude Sonnet 5.5 against the keyword baseline on the held-out set.
- [Data](#data): where the data comes from, what the load checks, and the main data-quality findings.
- [What to read next](#what-to-read-next): which documents to read, and in what order.
- [Repository map](#repository-map): what each folder holds.
- [Team](#team): who built it.

## What it does

The hackathon brief asked for "a customer-service system, not a chatbot": understand, decide, act, verify, escalate, and know when the AI should not act. Alba answers that for one workflow, credit pre-qualification:

1. **Login.** A customer types their document number; a 6-digit code is emailed to the address on file and opens a session bound to that customer. Consultants log in on their own page with email and employee code. The login answers the same way whether or not the person exists.
2. **Home.** The customer sees only their own products, plus a "Preguntar por" row for each product they can ask about (credit card, personal loan).
3. **Consent and decision.** The row opens a consent dialog. "Empezar" runs policy `alba-credit-v1` at once and shows a certificate, asks for the monthly income, or hands the case to a person. Each product has its own case.
4. **Conversation.** Typed messages are read by Claude Sonnet 5.5 into a fixed JSON shape (intent, product, language, stated income). Process rules, not the model, decide the next step. A message in any language other than Spanish or Portuguese goes to a person.
5. **Handoff.** Every move to a person tells the customer why, in one template sentence. A "no" from the policy can be sent once to a person for review.
6. **Consultant console.** The consultant sees a review queue, the handoff packet (request, score, income, deciding rule), and the full event trace. They do not chat: they close the case as pre-qualified or not, and a template tells the customer.

## Status

**Feature-complete for the submission (Oct 5, 2026).** Every item in `IMPLEMENTATION.md` is ticked:

- Data load (bronze, silver, gold) from S3 into Postgres, with row-count and quality checks that stop the load.
- Both logins, the customer home, the case screen, the consultant queue, case, and trace, all in Spanish and Portuguese.
- The policy engine, templates, event store, process rules, and the command worker.
- Claude Sonnet 5.5 as the turn reader, with B0 (a keyword baseline) as the offline fallback, both evaluated on a frozen held-out set.
- The quality gate (ruff, mypy strict, pytest with branch coverage, `tsc`, Vitest, Vite build) in CI, and the four oracle flows tested end to end in a real browser (Playwright).

Not built, on purpose:

- **No cloud deployment** (`PLAN.md` D2): the project is tried with `docker compose up`. The section [Deploying](#deploying-vercel-and-a-container-host) describes how it would go online.
- **No credit limit or rate** on the certificate: the dataset ships no credit manual, and a number there would be a promise.
- **No risk model**: the dataset's delinquency label carries no signal, so the organizers' `credit_score` is the risk estimate (`docs/model_card_risk.md`).
- **No real email**: login codes go to Mailpit only, because the dataset's addresses use real domains.

Known limitations:

- Portuguese copy and Portuguese test data are team-written or machine-translated; nobody on the team is fluent.
- The held-out labels were drafted by one team member and not reviewed by a second.
- Two decisions remain open (`PLAN.md` §5): D1, an optional second-model comparison, and D11, masking ID-like numbers in typed text before it reaches the model.
- Everything left out of scope on purpose (a second process, filling empty scores, an injection classifier, and more) is listed in `ARCHITECTURE.md` "Not decided".

## How it works

```
 Browser (React + Vite)
     │  /api/*  (bearer JWT)
     ▼
 FastAPI ──── writes events and commands ───► PostgreSQL 16
     │                                          ▲
     │  worker loop in the same process ────────┘  takes pending commands
     │        ├─ process rules (pure)               (FOR UPDATE SKIP LOCKED)
     │        ├─ policy alba-credit-v1 (pure, YAML)
     │        └─ turn reader: Claude Sonnet 5.5, or B0 keywords
     │
     └─ SMTP ──► Mailpit (login codes, never a real inbox)

 load (one-shot): S3 CSVs ► data/raw/ ► bronze ► silver ► gold (credit profile)
```

Key decisions, each with its home in the docs:

| Decision | Why | Where |
|---|---|---|
| The policy decides, the model only reads | Eligibility must be auditable and repeatable; a prompt is neither | `ARCHITECTURE.md` "Policy", "How the model is called" |
| Event-sourced process with a command queue | Every step of a case is a stored event, so the consultant's trace is the real history | `ARCHITECTURE.md` "Events", "Commands" |
| One structured call per typed message | Fixed `ConversationTurn` schema, one retry, a failed read goes to a person | `ARCHITECTURE.md` "How the model is called", `docs/model_card_conversation_turn.md` |
| No risk model shipped | The dataset's delinquency label is noise; the organizers' `credit_score` is used as is | `docs/model_card_risk.md`, `PLAN.md` §4.4 |
| Consultants close, they do not chat | Keeps the human step a decision with a template, not free text | `PLAN.md` D15, `specs/08-consultant-close.feature` |
| Spanish and Portuguese only | The dataset is Spanish; Portuguese is team-written and disclosed | `PLAN.md` D21, D22 |

Stack: Python 3.12, FastAPI, Pydantic v2, psycopg, PostgreSQL 16; TypeScript, React 19, Vite; the Anthropic API (`claude-sonnet-5-5`); Docker Compose. The wire contract is `api-spec/openapi.yaml`, generated into Python and TypeScript types.

## Run it locally

Requirements: Docker with Compose v2. The organizers' S3 keys, to download the dataset on the first run. An Anthropic API key is optional.

1. Create `.env` from the template:

   ```bash
   cp .env.example .env
   ```

2. Fill it:

   | Variable | Required | Value |
   |---|---|---|
   | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | First run only | Organizer keys, read-only |
   | `AWS_DEFAULT_REGION` | First run only | `us-east-2` |
   | `S3_BUCKET` | First run only | Bucket name only; a trailing `/data` is stripped |
   | `JWT_SECRET` | Yes | At least 32 characters: `openssl rand -hex 32`. The API refuses to start without it |
   | `ANTHROPIC_API_KEY` | No | Without it, add `LLM_MODEL=b0-keywords` to read messages with the keyword baseline |
   | `ANTHROPIC_WORKSPACE_ID` | No | Only if your key belongs to a workspace |

   Once `data/raw/` holds the four CSVs, the AWS values are no longer needed.

3. Start the stack:

   ```bash
   docker compose up --build
   ```

   The first run takes a few minutes: `load` downloads `customers.csv`, `products.csv`, `daily_exchange_rates.csv`, and `service_agents.csv` into `data/raw/`, applies the migrations, and builds the gold profile for 150,000 customers. `api` starts only after `load` succeeds.

4. Open:

   | URL | What |
   |---|---|
   | http://localhost:5173/ | Customer login |
   | http://localhost:5173/consultant/login | Consultant login ("Acceso para asesores" under the customer form) |
   | http://localhost:8025 | Mailpit: every login code lands here. Nothing leaves your machine |
   | http://localhost:8000/health, `/ready` | API health and database readiness |

`api` and `web` mount the source tree and reload on save. A new package in `api/requirements.txt` or `web/package.json` needs `docker compose up --build api` (or `web`).

**Demo mode.** Compose sets `DEMO_LOGIN=1`. The login header gets a "Demo" button that searches test customers (or active consultants) and fills the form, and the code step reads the code from Mailpit, so a tester only presses "Abrir sesión" (`PLAN.md` D25, D26).

**Troubleshooting.**

- `load` stops on `events_locale_check`: the volume holds a case from before `PLAN.md` D22. Run `docker compose down -v`, then `docker compose up`; the data reloads from `data/raw/`.
- `load` stops with a named error about keys or files: `data/raw/` is missing a CSV and `.env` has no S3 keys.
- The API exits at startup: `JWT_SECRET` is missing or shorter than 32 characters.

### View the static mock

`mocks/index.html` is a click-through of every screen, without the API:

```bash
cd mocks && python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/. The dark bar at the top switches screens; it is part of the walkthrough, not of the bank.

## Try the four flows

Any customer with an email on file can log in (147,016 of 150,000). These four oracle customers cover every outcome; type their name in the Demo search:

| Customer | What happens | Why |
|---|---|---|
| Juan Alberto Romero González, Querétaro | Pre-qualifies (simulated) | Score 812, income on file, mortgage current, no active card. Rule R05 |
| Juliana Castro Gómez, Ciudad de México | Asked for her income | Monthly income is empty (R06). If she states an amount, it is this run's income, and R05 pre-qualifies her (score 714) |
| Alicia Mariana Parra Álvarez, Cali | Goes to a person | Score 615, review band 580-619. Rule R05 |
| Mariana Mónica Acosta Rojas, Rosario | Does not pre-qualify | Card ••••5476 is 180 days past due. Rule R02 |

Then log in as consultant César González Sánchez (employee E75612, Créditos) to see Alicia's case in the queue, read the packet and the trace, and close it. Only the 1,090 consultants marked `Active` can log in. Full profiles are in `ARCHITECTURE.md` "Oracle fixtures".

Policy `alba-credit-v1` (rules in order; the first terminal result wins):

| Rule | When | Result |
|---|---|---|
| R01 | Suspended or inactive / closed | Review / does not pre-qualify |
| R02 | A credit product 30+ days past due | Does not pre-qualify |
| R03 | A credit product 1-29 days past due | Review |
| R09 | Already holds the requested product | Review (a limit increase is not this workflow) |
| R04 | No credit score | Review |
| R06 | No income on file | Ask for it. If the file has income, the file wins |
| R05 | Score below 580 / 580-619 / 620 or more | Does not pre-qualify / review / pre-qualifies |

The certificate shows no credit limit and no rate. Mortgages, investments, disputes, and a third party's balance are out of scope: they are clarified or handed off.

## Tests and quality gate

One command runs both gates on an image built from the current checkout: `npm run check` in `web/` (`tsc`, Vitest, Vite build), then `scripts/check.sh` (ruff, mypy strict, pytest with branch coverage; integration tests use throwaway databases `alba_test` and `alba_api_test`):

```bash
docker compose --profile test run --rm test
```

On the host instead (Python 3.12; the code uses 3.12 syntax). Integration tests need Postgres on host port 55432 and are skipped without it unless `ALBA_REQUIRE_POSTGRES=1`:

```bash
docker compose up -d postgres
py -3.12 -m venv .venv            # python3.12 -m venv .venv outside Windows
. .venv/Scripts/activate          # . .venv/bin/activate outside Windows
python -m pip install -r requirements-dev.txt
sh scripts/check.sh
cd web && npm ci && npm run check
```

Two checks need the full dataset, so CI leaves them out:

- **Oracle data check** (`IMPLEMENTATION.md` M1): compares the oracle customers, César, the as-of rates, and the product types in `api/fixtures/oracle_customers.json` with the loaded tables, and runs the policy on them.

  ```bash
  docker compose up -d
  docker compose --profile test run --rm test pytest -m dataset
  ```

- **Browser flows** (`IMPLEMENTATION.md` W7): the four oracle flows in Playwright, one in Portuguese, on a separate project `alba-e2e` with its own empty volume, so the demo's data and ports are untouched. Two to three minutes:

  ```bash
  sh scripts/e2e.sh
  ```

  On a failure, `web/e2e-results/` holds a screenshot and trace per flow (`npx playwright show-trace <path>` in `web/`), and `web/e2e-report/` the HTML report.

CI (`.github/workflows/quality.yml`) runs the gate on every pull request to `main` and every push to `main`. Jobs and coverage floors are in `ARCHITECTURE.md` "Quality gate".

## Deploying (Vercel and a container host)

The submission runs locally only (`PLAN.md` D2). This is the path we would take to put it online. It has not been run; treat it as a plan.

**Why not everything on Vercel.** The web app is a static Vite build, which suits Vercel. The API does not suit Vercel Functions: the command worker is a loop inside the API process (`RUN_WORKER=1`) that must keep running between requests, and the API holds a Postgres connection pool. Both need a long-lived container.

| Piece | Where | Notes |
|---|---|---|
| `web/` | Vercel | Static build; rewrites forward `/api` to the API |
| `api` | A container host: Render, Railway, Fly.io, or similar | `docker/api.Dockerfile` as is, with the worker on |
| Postgres 16 | Managed: Neon (also through the Vercel Marketplace), Supabase, or the host's own | Any Postgres 16 reachable by URL |
| Mailpit | Same container host as the API | The dataset's emails use real domains: never send login codes through a real mail provider with this data |
| `load` | Run once, from any machine with Docker | Fills the managed database |

Steps:

1. **Database.** Create a Postgres 16 database and copy its URL (with `?sslmode=require` if the provider asks).

2. **Load the data** once, from a checkout with `.env` filled:

   ```bash
   docker build -f docker/load.Dockerfile -t alba-load .
   docker run --rm --env-file .env \
     -e DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/alba?sslmode=require" \
     -v "$PWD/data/raw:/data/raw" alba-load
   ```

   It applies `db/migrations/`, downloads the CSVs if missing, and builds gold. Running it again loads only changed files.

3. **Mailpit.** Deploy the image `axllent/mailpit:v1.30.2` on the container host. Keep SMTP (port 1025) on the private network and expose the web UI (port 8025) over HTTPS. The API's mailer is plain SMTP with no auth or TLS, which is what Mailpit expects.

4. **API.** Deploy from `docker/api.Dockerfile` (it runs `uvicorn api.main:app` on port 8000, without `--reload`) with:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | The managed database URL |
   | `JWT_SECRET` | A new 32+ character secret |
   | `ANTHROPIC_API_KEY` | Your key, or set `LLM_MODEL=b0-keywords` instead |
   | `RUN_WORKER` | `1` |
   | `DEMO_LOGIN` | `1` for a public demo, `0` otherwise |
   | `SMTP_HOST`, `SMTP_PORT` | Mailpit's private host name, `1025` |
   | `MAIL_FROM` | `Alba <no-reply@alba.local>` |

   Use `/ready` as the health check: it answers 503 until the database is reachable. The worker claims commands with `FOR UPDATE SKIP LOCKED`, so more than one instance is safe, but one is enough for a demo.

5. **Web on Vercel.** Import the repository, set **Root Directory** to `web`, framework preset **Vite** (build `npm run build`, output `dist`). Add `web/vercel.json`:

   ```json
   {
     "rewrites": [
       { "source": "/api/:path*", "destination": "https://YOUR-API-HOST/:path*" },
       { "source": "/mailpit/:path*", "destination": "https://YOUR-MAILPIT-HOST/:path*" },
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```

   The web client calls the relative path `/api` (`web/src/api/client.ts`). Locally the Vite dev server proxies it; on Vercel the rewrite does, so the browser stays on one origin and the API needs no CORS setup and the build needs no environment variables. The `/mailpit` rewrite is only for demo mode, which reads the code from Mailpit; drop it with `DEMO_LOGIN=0`. The last rule sends deep links such as `/consultant/login` to the single-page app. Vercel serves HTTPS, which the client needs (`crypto.randomUUID` gives each message its id).

6. **Check.** `https://YOUR-APP.vercel.app/api/ready` answers `ready`; log in as Juan through the Demo button; read his code in Mailpit's UI.

Before real customers, more would be needed: a real identity check and mail provider, secret rotation, monitoring, data retention, capacity limits, and masking ID-like numbers in typed text before it reaches the model (`PLAN.md` D11 and §2, item 6).

## Evaluation

The turn reader was measured on a frozen held-out set of 60 utterances (ES-MX, ES-CO, ES-AR, PT, mixed, English, and adversarial), sha256 recorded before any prompt tuning. Latest run, `eval/reports/2026-10-06-0212-b0-keywords-vs-claude-sonnet-5-5.md`:

| Metric | B0 keywords | Claude Sonnet 5.5 |
|---|---|---|
| Intent | 44/60 (73%) | 60/60 (100%) |
| Route (rules the engine fires) | 48/60 (80%) | 60/60 (100%) |
| Missed handoff to a person | 8/60 | 0/60 |
| Policy run without consent | 0/60 | 0/60 |
| p50 latency, cost for 60 turns | 0 ms, $0 | 2.1 s, $0.10 |

Intervals (Wilson 95%), per-slice results, and every item off are in the report. Labels were drafted by one team member and not reviewed by a second; Portuguese is team-written. Rerun with `python -m eval.run_eval` (`eval/run_eval.py`).

What reaches Anthropic: the message text, the process state, four yes/no flags (income on file, score on file, active card, active personal loan), and the two-product catalog. No dataset row, score, income, name, document, email, or address.

## Data

### What is synthetic

| Input | Label |
|---|---|
| Customers, products, consultants, exchange rates, and every other table in the bucket | Synthetic, generated by the organizers (dataset v1.0.0) |
| Policy `alba-credit-v1`, product catalog | Team-generated, synthetic |
| Portuguese labels and templates | Team-written; the dataset is Spanish only |
| Evaluation utterances and labels | Team-generated; Portuguese may be machine-translated and is disclosed |

### Source and load

The bucket is read-only S3 in `us-east-2`; its name and keys come from the organizers and live only in `.env`. `load` copies four root CSVs with `aws s3 cp` into `data/raw/`, then into Postgres in three layers: bronze (the files as downloaded), silver (typed tables), and gold (`customer_credit_profile`, one row per customer, which the policy reads). The API never calls S3. Files are UTF-8 with a BOM (`encoding="utf-8-sig"`).

| File | Rows | Used for |
|---|---|---|
| `customers.csv` | 150,000 | Login (document number, email) and the credit profile |
| `products.csv` | 400,000 | The home, R09 (already holds the product), R02 and R03 (days past due) |
| `daily_exchange_rates.csv` | 13,164 | The USD equivalent of an income on file |
| `service_agents.csv` | 1,200 | Consultant login |

The load stops, and loads nothing half-way, when a file is missing or empty, a column is missing, a row count differs from the snapshot, a product points at a customer that does not exist, or the June 17, 2026 rate for MXN, COP, or ARS is missing. Each run is recorded in `load_batches`, so an unchanged file is not loaded again.

Bucket layout under `data/`: dimension CSVs at the root, and fact tables as daily partitions `data/<table>/year=YYYY/month=MM/day=DD/<table>_YYYYMMDD.csv` (2023-06-17 to 2026-06-17) for `call_center_interactions`, `call_transcripts`, `campaign_sends`, `complaints`, `digital_events`, `satisfaction_surveys`, and `transactions`. Alba loads none of the fact tables.

### Main findings

From `docs/data_quality.md`, which names the file and sample of each number:

| Finding | Evidence | What Alba does |
|---|---|---|
| Missing credit data | `customers.csv` (n=150,000): 22,492 empty scores, 30,033 empty incomes (Sep 29 load) | Never imputed. No score goes to a person (R04); no income is asked for in the chat (R06) |
| The delinquency label is noise | `products` x `customers`, n=125,350 credit products: every single-feature AUC 0.500 to 0.504 | No risk model is shipped |
| Transcripts are templates | `call_center_interactions`, Jan 2025, n=4,903: 42 distinct customer texts, unfilled `{monto}` placeholders | No intent model is trained on them; the reader is evaluated on a team-written held-out set |
| Shared emails | `customers.csv`: 24,203 addresses shared by 2 to 31 customers | Login is by document number; the email only receives the code |
| Mexico's balances are in USD | `products`: no MXN balance in Mexico, while incomes are in local currency | Balances are shown in the row's own currency |
| Product names are Spanish | The file stores `Tarjeta Crédito`, `Préstamo Personal`; the dictionary says `Credit Card` | Mapped once at the load boundary to product keys |

The full list, and what was not checked, is in `docs/data_quality.md`. The analysis behind it is in `PLAN.md` §4.

<details>
<summary>Reading the bucket without the AWS CLI</summary>

curl can sign requests. The `=` in partition paths must be sent as `%3D`, or S3 answers `SignatureDoesNotMatch`:

```bash
set -a; source .env; set +a
s3get() {  # s3get <key> <outfile>
  local key="${1//=/%3D}"
  curl -sf --aws-sigv4 "aws:amz:${AWS_DEFAULT_REGION}:s3" --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
    -o "$2" "https://${S3_BUCKET}.s3.${AWS_DEFAULT_REGION}.amazonaws.com/${key}"
}
s3ls() {   # s3ls <prefix>: XML, max 1000 keys; page with &continuation-token=...
  curl -s --aws-sigv4 "aws:amz:${AWS_DEFAULT_REGION}:s3" --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
    "https://${S3_BUCKET}.s3.${AWS_DEFAULT_REGION}.amazonaws.com/?list-type=2&prefix=$1"
}
mkdir -p data/raw && s3get "data/customers.csv" data/raw/customers.csv
```

</details>

## What to read next

In this order, depending on how deep you want to go:

1. **`diagrams/c4.html`**: open it in a browser. A clickable C4 model, from the system context down to each component.
2. **`ARCHITECTURE.md`**: the build contract (process, events, rules, commands, policy, model call, auth, HTTP, database, Docker, quality gate). It wins over every other file. Start with "What gets built", "Process-native loop", and "Juan's flow, step by step".
3. **`specs/`**: Gherkin scenarios in the order of the customer journey (`01-session-login` to `13-cases-per-product`). The behavior as examples.
4. **`docs/`**: `data_quality.md` (the dataset's traps and the load checks), `model_card_conversation_turn.md` (the shipped model component), `model_card_risk.md` (the risk model we chose not to ship, and why).
5. **`eval/reports/`**: the held-out results above, in full.
6. **`PLAN.md`**: the hackathon brief against the contract (§2), data evidence (§4), every decision with its reasons (§5, D1 to D28, and the log in §10).
7. **`IMPLEMENTATION.md`**: how the work was split and built, item by item, with the scenarios each turned green.
8. **`AGENTS.md`** and **`DESIGN.md`**: the coding standard and the visual system. Read them before contributing.

## Repository map

| Path | What it holds |
|---|---|
| `api/` | FastAPI app in layers: `domain/` (pure policy, rules, templates), `application/` (use cases, the worker cycle), `infrastructure/` (Postgres, Claude adapter, SMTP, settings), `presentation/` (HTTP routes, worker loop) |
| `web/` | React + Vite app: `src/pages/`, `src/components/`, `src/i18n/` (Spanish and Portuguese), `e2e/` (Playwright flows) |
| `pipeline/` | The `load` container: bronze, silver, gold, checks, and the load report |
| `db/migrations/` | The schema, applied by `load` |
| `api-spec/` | `openapi.yaml`, the wire contract, and `generate.py` for the Python and TypeScript types |
| `eval/` | Held-out set (`heldout/`), metrics, route replay, and reports |
| `specs/` | Gherkin behavior specs |
| `docs/` | Data-quality report and model cards. Organizer PDFs stay local and are never committed |
| `diagrams/c4.html` | C4 model |
| `mocks/index.html` | Static screen walkthrough |
| `docker/`, `compose.yaml`, `compose.e2e.yaml` | Images and the stacks (demo, tests, browser flows) |
| `scripts/` | `check.sh` (Python gate) and `e2e.sh` (browser flows) |
| `data/` | Local CSVs, never committed |
| `CLAUDE.md` | Entry instructions for Claude Code sessions |

## Team

Built by a team of two for the Factored AI & Data Hackathon 2026:

- **Jael Armas**: [GitHub](https://github.com/jael0x) · [LinkedIn](https://www.linkedin.com/in/jael0x/)
- **Katherine Zambrano**: [GitHub](https://github.com/KattyGZC) · [LinkedIn](https://www.linkedin.com/in/kathy-gzc/)
