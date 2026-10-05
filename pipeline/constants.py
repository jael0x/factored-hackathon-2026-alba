from typing import Final

PRODUCT_TYPE_CREDIT_CARD: Final = "Tarjeta Crédito"
PRODUCT_TYPE_PERSONAL_LOAN: Final = "Préstamo Personal"
PRODUCT_TYPE_MORTGAGE: Final = "Préstamo Hipotecario"
PRODUCT_STATUS_ACTIVE: Final = "Active"

AS_OF_DATE: Final = "2026-06-17"
TARGET_CURRENCY_USD: Final = "USD"

COUNTRY_MEXICO: Final = "México"
COUNTRY_COLOMBIA: Final = "Colombia"
COUNTRY_ARGENTINA: Final = "Argentina"

INCOME_CURRENCY_BY_COUNTRY: Final = {
    COUNTRY_MEXICO: "MXN",
    COUNTRY_COLOMBIA: "COP",
    COUNTRY_ARGENTINA: "ARS",
}

S3_KEYS: Final = (
    "data/customers.csv",
    "data/products.csv",
    "data/daily_exchange_rates.csv",
    "data/service_agents.csv",
)

EXPECTED_ROW_COUNTS: Final = {
    "customers.csv": 150_000,
    "products.csv": 400_000,
    "daily_exchange_rates.csv": 13_164,
    "service_agents.csv": 1_200,
}

CUSTOMERS_COLUMNS: Final = (
    "customer_id",
    "document_number",
    "first_name",
    "last_name",
    "email",
    "country",
    "segment",
    "credit_score",
    "estimated_monthly_income",
    "customer_status",
)

PRODUCTS_COLUMNS: Final = (
    "product_id",
    "customer_id",
    "product_type",
    "product_number",
    "currency",
    "current_balance",
    "product_status",
    "days_past_due",
)

EXCHANGE_COLUMNS: Final = (
    "date",
    "source_currency",
    "target_currency",
    "exchange_rate",
)

AGENTS_COLUMNS: Final = (
    "agent_id",
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "agent_status",
    "specialty",
)
