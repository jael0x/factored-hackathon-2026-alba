# Model card: the delinquency model we did not ship

Alba ships no risk model. This card records the one we tried and why it was dropped. The numbers are in `PLAN.md` §4.4.

## Intended use

Estimate the probability that a customer falls 30 or more days past due, as an input to pre-qualification beside the credit score.

## Data

- Credit products with a non-null `days_past_due`, joined to their customers: n=125,350 (`products.csv` x `customers.csv`, snapshot June 17, 2026).
- Targets: 30+ days past due (12.5%) and 90+ days past due (7.5%).
- Features tried: credit score, income, age, customer tenure, product tenure, utilization, balance to income, limit to income, balance, limit, interest rate, number of products, segment, gender, country, product status, occupation, opening channel; and, on 78,499 credit products, January 2025 transaction behavior (count, payments, declines, code-51 declines, amount, fraud flags).

## Evaluation

| Model | AUC (30+ days) | AUC (90+ days) |
|---|---|---|
| Each feature alone | 0.500 to 0.504 | |
| Gradient boosting (HistGradientBoosting), 5-fold, folds grouped by customer | 0.498 | 0.501 |
| Transaction features alone | 0.500 to 0.503 | |

Default rates are flat across every category: segment 12.3% to 12.7%, country 12.4% to 12.5%, and a blocked or suspended product no worse than an active one.

## Decision

The label is noise: no feature, alone or combined, separates who falls behind. A model trained on it would look like a risk score and carry no information. A reported AUC above 0.55 on this data would most likely be leakage.

What Alba uses instead: the dataset's `credit_score`, treated as an external bureau-style score already on the gold row, and the current days past due on the customer's products. The policy `alba-credit-v1` reads them in fixed rules (`ARCHITECTURE.md`, "Policy"). No probability is estimated.

## Limitations

- One snapshot; a real portfolio would need a time-split evaluation.
- Fairness slices (gender, age band, country) were checked only as default-rate tables, which are flat; there is no model to audit.
