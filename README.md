# Alba: credit pre-qualification assistant

Alba is a customer-service demo for the synthetic LATAM bank of the Factored AI & Data Hackathon 2026. A customer asks about a credit card or a personal loan. A versioned policy decides. The language model only classifies the sentence and drafts a clarification. If income is missing, the case stays with the assistant and asks for it. If the case is borderline, the score is missing, or it is out of scope, the thread goes to a person. That person does not chat: they choose pre-qualified or not, and a template tells the customer.

It is not a production bank and it moves no money. "Alba" is the name of this interface. Customers, products, scores, incomes, and consultants come from the organizer dataset, snapshot of June 17, 2026.

**Status (Oct 5, 2026): logins, the customer home, the language switch, the customer's pre-qualification, and the consultant's screens built.** `docker compose up` brings up Postgres, the one-shot `load` container (bronze, silver, gold), the API with both logins, the customer's products and cases, and the worker, Mailpit for the login codes, the two login pages, the home, and the case screen. Every screen reads in Spanish or Portuguese, chosen in the app bar; a message in any other language goes to a person. A "Preguntar por" row on the home opens a consent dialog; "Empezar" runs the policy at once and shows the certificate, asks for the monthly income, or hands the case to a person. Each product has its own case, and its row continues it or shows its result (`PLAN.md` D24). A no from the policy can be sent once to a person for review (D25). Every move to a person tells the customer why, in one template sentence (D28). Typed messages are read by Claude Sonnet 5.5 (`PLAN.md` D27); without an `ANTHROPIC_API_KEY`, `LLM_MODEL=b0-keywords` reads them with B0, the keyword baseline (D23). On a frozen held-out set of 60 utterances, Claude reads 60 of 60 intents and routes all 60 as the labels do; B0 reads 44 and routes 48 (`eval/reports/`, `docs/model_card_conversation_turn.md`). The consultant's side is built, API and screens: the review queue, the case with its handoff packet and close (`PLAN.md` D15 (3)), and the trace. `mocks/index.html` remains the screen walkthrough. Submission is due Mon Oct 5.

Stack: FastAPI and PostgreSQL 16 in one Docker Compose stack, with Claude Sonnet 5.5 (`claude-sonnet-5-5`) on the Anthropic API reading each typed message (`PLAN.md` D27). Details in `ARCHITECTURE.md`.

## How to review

Copy `.env.example` to `.env` and fill the values. `S3_BUCKET` is the bucket name only; a trailing `/data` is accepted and stripped. Then:

```bash
docker compose up --build
```

`.env` needs a `JWT_SECRET` of at least 32 characters (`openssl rand -hex 32`); the API refuses to start without it.

Open http://localhost:5173/ (API health at http://localhost:8000/health). `load` downloads the four CSVs into `data/raw/` if missing, applies migrations, and builds gold. Login codes are emailed to Mailpit, a local mail catcher: read them at http://localhost:8025. Nothing is sent outside your machine. Default compose sets `DEMO_LOGIN=1`, which adds a "Demo" button to the login header; it opens a test-customer search right below it that fills the document field. With the demo on, the code step also reads the code from Mailpit and fills it, so a tester only presses "Abrir sesión": a consultant's is the code sent to the email typed, a customer's the newest one sent (`PLAN.md` D25, D26). Consultants log in at http://localhost:5173/consultant/login ("Acceso para asesores" under the customer form) with their email and employee code; there the Demo button searches active consultants and fills both fields. There is no cloud deploy for the submission; optional host steps will live in `docs/ops.md`.

If `load` stops on `events_locale_check`, the database holds an English case from before `PLAN.md` D22 (Oct 2 to 3). Reset it with `docker compose down -v`, then `docker compose up` again; the data reloads from `data/raw/`.

`api` and `web` mount the source tree and reload when a file is saved. A Python or TypeScript edit does not need another image build. A new package in `api/requirements.txt` or `web/package.json` does: `docker compose up --build api` or `web`. The first `up --build` after this change rebuilds `web`, because that image now runs Vite instead of nginx.

### Tests

One command runs both gates, on an image rebuilt from the current checkout: the web gate, `npm run check` in `web/` (`tsc`, Vitest, and the Vite build), then the Python gate, `scripts/check.sh`: ruff, mypy strict, and the full suite with branch coverage (unit and integration tests; the integration tests recreate and migrate throwaway databases, `alba_test` and `alba_api_test`, through one fixture in `conftest.py`). Preferred:

```bash
docker compose --profile test run --rm test
```

On the host (unit always; integration needs Postgres on host port **55432**, and is skipped without it unless `ALBA_REQUIRE_POSTGRES=1`):

```bash
docker compose up -d postgres
py -3.12 -m venv .venv            # python3.12 -m venv .venv outside Windows
. .venv/Scripts/activate          # . .venv/bin/activate outside Windows
python -m pip install -r requirements-dev.txt
sh scripts/check.sh
```

The host runs Python 3.12, as the images and CI do. The code uses 3.12 syntax, so 3.11 cannot import it.

The web gate on the host: `npm ci && npm run check` in `web/`.

The oracle check reads the database `docker compose up` filled, not a throwaway one, so it needs the full dataset and the gate leaves it out. It compares the four oracle customers, César, the as-of rates, and the product types in `api/fixtures/oracle_customers.json` with the loaded tables, and runs the policy on the loaded profiles (`IMPLEMENTATION.md`, M1):

```bash
docker compose up -d
docker compose --profile test run --rm test pytest -m dataset
```

The four oracle flows in a browser (`IMPLEMENTATION.md`, W7) run on their own copy of the stack, project `alba-e2e`: it starts with an empty volume, loads `data/raw/`, and is removed afterwards, so the demo's data and ports are not touched. It needs the dataset, so CI leaves it out. Two to three minutes, the load included:

```bash
sh scripts/e2e.sh
```

On a failure, `web/e2e-results/` holds the screenshot and the trace of each failed flow (open a trace with `npx playwright show-trace <path>` in `web/`), and `web/e2e-report/` the HTML report.

CI runs the same checks on every pull request to `main` and every push to `main`. The jobs, coverage floors, and what fails them are in `ARCHITECTURE.md`, "Quality gate".

## Where things are

| File | What it holds |
|---|---|
| `ARCHITECTURE.md` | The build contract: process, events, rules, commands, policy, model call, auth, database, Docker. It wins over every other file |
| `AGENTS.md` | The coding standard for every author and model |
| `DESIGN.md` | How the web app, the mock, and the C4 page look and move: tokens, type, components, motion, accessibility. The contract wins over it |
| `PLAN.md` | Hackathon requirements, data evidence, open decisions, research backlog, evaluation design, schedule |
| `IMPLEMENTATION.md` | Build order: interfaces first, then three tracks (Engine, Model and eval, Web) pulled by whoever is free, with the spec scenarios each item turns green |
| `CLAUDE.md` | Entry instructions for Claude Code sessions |
| `mocks/index.html` | Static screen walkthrough (Spanish UI), not the frontend |
| `diagrams/c4.html` | Clickable C4 model of the contract, four levels. Level 4 lists, per component, what the contract fixes and what is still open. Open the file in a browser; if it disagrees with `ARCHITECTURE.md`, the contract wins |
| `specs/` | Gherkin behavior specs, numbered in the order of the customer journey (`01-session-login.feature` to `10-data-load.feature`; the consultant login is `11-consultant-login.feature`). They restate the contract as examples; `ARCHITECTURE.md` wins |
| `api-spec/openapi.yaml` | Wire contract for the API. `python api-spec/generate.py` writes the Python models and the TypeScript types. `ARCHITECTURE.md` wins |
| `docs/` | Organizer PDFs, local only. Never committed: the data dictionary holds the S3 keys |
| `data/` | Local CSVs, never committed. `data/raw/` for the loader, `data/sample/` for spot checks |

## What a bank would see

A customer logs in with their document number. That says who they claim to be; a 6-digit code emailed to the address on file proves it and opens the session, bound to that customer. The login answers the same way whether or not the document is on file. In the demo the email lands in Mailpit, never in a real inbox: the dataset's addresses use real domains.

Inside the session, the customer sees only their own products. Typing another person's id changes nothing.

Any customer with an email on file can log in (147,016 of the 150,000; the rest have no address to send a code to). Consultants log in on their own page with their email and employee code, and the code goes to that email. Only the 1,090 consultants marked `Active` get one; the answer is the same for everyone else. These four rows cover every outcome; they are examples, not the list of who can try it:

| Person | What happens | Why |
|---|---|---|
| Juan Alberto Romero González, Querétaro | Pre-qualifies (simulated) | Score 812, income on file, mortgage current, no active card. Rule R05 |
| Juliana Castro Gómez, Ciudad de México | No decision until she states her income | Monthly income is empty. Rule R06. She stays `ai_active`. If she states an amount, that amount is this run's income and R05 pre-qualifies her (score 714). She does not go to the queue |
| Alicia Mariana Parra Álvarez, Cali | A specialist takes it | Score 615, review band 580-619. Rule R05. The process becomes `human_active` |
| Mariana Mónica Acosta Rojas, Rosario | Does not pre-qualify | Card ••••5476 is 180 days past due. Rule R02. Her score of 515 is never reached |

César González Sánchez (employee E75612, specialty Créditos) sees only the review queue. He does not reply in the thread. His only action is to close the case as pre-qualified or not. The packet carries the request, the score, the income, and the deciding rule. Full profiles are in `ARCHITECTURE.md`.

The policy is `alba-credit-v1`. It is synthetic, because the dataset ships no credit manual, and the certificate says so. It shows no credit limit.

| Rule | When | Result |
|---|---|---|
| R01 | Suspended or inactive | Review |
| R01 | Closed | Does not pre-qualify |
| R02 | A credit product 30+ days past due | Does not pre-qualify |
| R03 | A credit product 1-29 days past due | Review |
| R09 | Already holds the requested product | Review. A limit increase is not this workflow |
| R04 | No credit score | Review |
| R06 | No income on file | Ask for it. A typed amount is this run's income and evaluation continues. If the file already has income, the file wins |
| R05 | Score below 580 / 580-619 / 620 or more | Does not pre-qualify / review / pre-qualifies |

Mortgages, investments, transaction disputes, and a third party's balance are out of scope. They are clarified or escalated, not handled as a second product.

## View the mock

```bash
cd mocks
python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/. The dark bar at the top switches screens; it is part of the walkthrough, not of the bank.

## Data

### Labels

| Input | Label |
|---|---|
| Customers, products, consultants, exchange rates, transcripts, and every other table in the bucket | Synthetic, generated by the organizers (dataset v1.0.0) |
| Policy `alba-credit-v1`, product catalog | Team-generated, synthetic |
| Portuguese labels and templates | Team-written; the dataset is Spanish only. The language switch picks the language Alba writes in; a message in any other language, English included, goes to a person (`PLAN.md` D21, D22) |
| Evaluation utterances and labels | Team-generated; Portuguese may be machine-translated and is disclosed (`PLAN.md` D3, D6, D22) |

What reaches Anthropic: the customer's message text, the process state, four yes/no flags (income on file, score on file, has an active card, has an active personal loan), and the two-product catalog. No dataset row, score, income, name, document, email, or address. Masking ID-like numbers inside the typed text is still open (`PLAN.md` D11).

### Access

The bucket is read-only S3 in `us-east-2`. Its name and keys come from the organizers. They live only in `.env`, next to the other secrets the stack reads:

```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-2
S3_BUCKET=
ANTHROPIC_API_KEY=
ANTHROPIC_WORKSPACE_ID=
JWT_SECRET=
```

Typed messages are read by Claude Sonnet 5.5, which needs `ANTHROPIC_API_KEY`. Without a key, add `LLM_MODEL=b0-keywords` to `.env` to read them with the keyword baseline instead; a case started from the home never needs the model. The evaluation of both on the held-out set is in `eval/reports/` (`python -m eval.run_eval`, see `eval/run_eval.py`).

Layout under `data/` in the bucket:

- Dimension CSVs at the root: `customers.csv`, `products.csv`, `branches.csv`, `service_agents.csv`, `marketing_campaigns.csv`, `daily_exchange_rates.csv`.
- Fact tables as daily partitions: `data/<table>/year=YYYY/month=MM/day=DD/<table>_YYYYMMDD.csv`. Tables: `call_center_interactions`, `call_transcripts`, `campaign_sends`, `complaints`, `digital_events`, `satisfaction_surveys`, `transactions`. Range 2023-06-17 to 2026-06-17.
- Also in the bucket: `data_backup_20260831/` and a stray `marketing_campaigns.csv` at the root (research items R2 and R10 in `PLAN.md`).

Files are UTF-8 with a BOM. Read them with `encoding="utf-8-sig"`.

Without the AWS CLI, curl can sign requests itself. The `=` in partition paths must be sent as `%3D`, or S3 answers `SignatureDoesNotMatch`:

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

The running stack does not use the curl helper above. `load` runs `aws s3 cp` for four keys under `data/` (`customers.csv`, `products.csv`, `daily_exchange_rates.csv`, `service_agents.csv`) into `data/raw/`, then into Postgres. The API does not call S3. `data/sample/` currently holds three partitions used for spot checks: `call_center_interactions_20260601.csv`, `call_transcripts_20250315.csv`, `call_transcripts_20260601.csv`.

Data findings and their samples are in `PLAN.md` §4.
