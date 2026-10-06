# Data quality report

What we found in the organizer dataset (the S3 bucket, snapshot of June 17, 2026), what the load checks on every run, and what each finding means for Alba. Every number names its file and sample. The analysis behind it is in `PLAN.md` §4.

## What Alba loads

`load` reads four files from `data/` in the bucket into `data/raw/`, then into Postgres: bronze (the files as downloaded), silver (typed tables), gold (`customer_credit_profile`, one row per customer for the policy). `ARCHITECTURE.md` "Data" is the contract.

| File | Rows expected | Used for |
|---|---|---|
| `customers.csv` | 150,000 | login (document number, email), the profile |
| `products.csv` | 400,000 | the home, `holds_product` (R09), days past due (R02, R03) |
| `daily_exchange_rates.csv` | 13,164 | the USD equivalent of an income on file |
| `service_agents.csv` | 1,200 | consultant login |

## Checks that stop the load

Each one fails the run with a message (`SystemExit`); nothing is loaded half-way.

| Check | Where | What it catches |
|---|---|---|
| Each file is present and not empty after download | `pipeline/bronze.py` | a missing or truncated download |
| Each file has the columns the loader reads | `pipeline/csv_header.py` | a renamed or dropped column |
| Each file has exactly its expected row count | `pipeline/checks.py`, `EXPECTED_ROW_COUNTS` in `pipeline/constants.py` | a partial or duplicated file |
| No product points at a customer that does not exist | `pipeline/silver.py` | orphan `products.customer_id` |
| A positive USD rate exists on June 17, 2026 for MXN, COP, and ARS | `pipeline/gold.py` | gold incomes that could not be converted |

The load writes a report of null counts (`pipeline/report.py`) and records each run in `load_batches`, so a second `docker compose up` does not reload an unchanged volume.

## Traps in the data

| Trap | Evidence (file, sample) | What Alba does |
|---|---|---|
| Transcripts are template-generated | `call_center_interactions`, Jan 2025, n=4,903: 42 distinct `customer_text`, 462 distinct `full_text`, every row with unfilled `{monto}` / `{moneda}` placeholders | No intent model is trained on them; the classifier is evaluated on a team-written held-out set instead (`eval/`) |
| Transcript labels carry no signal | same sample: `detected_intents` is `consulta_general` in 95%; the same text appears as Queja, Producto, and Transaccional | No usable text-to-intent labels exist in the supplied data |
| Complaint text is templated | `complaints`, Jan 2025, n=1,998: 5 distinct `description`, 5 distinct `resolution`, `origin_interaction_id` never filled | Complaints are not linked to calls or used |
| The delinquency label is noise | `products` x `customers`, n=125,350 credit products: every single-feature AUC 0.500 to 0.504; gradient boosting with customer-grouped folds 0.498 (DPD 30+) | No risk model is shipped; see `docs/model_card_risk.md` |
| Product types differ from the dictionary | the dictionary lists `Credit Card`; the file stores `Tarjeta Crédito`, `Préstamo Personal`, `Préstamo Hipotecario` | The stored strings are mapped once at the load boundary into product keys |
| Mexico's balances are in USD | `products`: no MXN balance in Mexico; incomes are local currency (median MX 39,220, CO 9,192,466, AR 801,955) | Balances are shown in the row's own currency; an income threshold would need conversion, and the policy has none |
| Shared emails | `customers.csv` (n=150,000): 24,203 addresses shared by 2 to 31 customers (79,930 rows); 2,984 rows (2.0%) with no email | Login is by document number with a code to the email on file; email never identifies a customer |
| Consultant identifiers are not unique alone | `service_agents.csv` (n=1,200): 12 shared emails, 13 shared employee codes; the pair is unique | Consultant login takes both |
| Missing credit data | gold `customer_credit_profile`: a null score or a null income is kept null, never imputed | A null score is `REFER` with no question; a null income is asked for in the chat |
| Timestamps cross partitions | `call_center_interactions_20260601.csv` (n=857): 289 rows (33.7%) dated June 2 between 00:00 and 07:59 | Looks like an 08:00 day boundary; not used by Alba, noted for anyone who loads the call tables |
| Ages | `customers.csv`: minimum 21, 14.1% over 75 | The policy has no age rule, deliberately |
| No Portuguese and no policy documents | the bucket has Spanish data only | The policy, the product catalog, and every Portuguese sentence are team-written and labeled so |

## Not checked

- Duplicates: the dictionary says about 2%; the four loaded files have 0 duplicate primary keys. The other tables were not checked (`PLAN.md` R1).
- Update correctness is tested on fixtures, not measured on the real data: `pipeline/tests/test_load_integration.py` reloads a changed file (`test_changed_file_is_reloaded`) and runs an unchanged batch twice (`test_silver_gold_and_idempotent_batch`) on the small CSVs in `pipeline/testdata/`.
