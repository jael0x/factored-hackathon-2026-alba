from uuid import UUID

import psycopg

from pipeline.constants import (
    AS_OF_DATE,
    COUNTRY_ARGENTINA,
    COUNTRY_COLOMBIA,
    COUNTRY_MEXICO,
    PRODUCT_STATUS_ACTIVE,
    PRODUCT_TYPE_CREDIT_CARD,
    PRODUCT_TYPE_MORTGAGE,
    PRODUCT_TYPE_PERSONAL_LOAN,
    TARGET_CURRENCY_USD,
)


def rebuild_gold(conn: psycopg.Connection, batch_id: UUID) -> None:
    conn.execute("TRUNCATE customer_credit_profile")
    conn.execute(
        """
        INSERT INTO customer_credit_profile (
            customer_id,
            first_name,
            last_name,
            country,
            segment,
            customer_status,
            credit_score,
            income_local,
            income_currency,
            income_usd,
            max_days_past_due,
            has_active_card,
            has_active_personal_loan,
            as_of,
            batch_id
        )
        SELECT
            c.customer_id,
            c.first_name,
            c.last_name,
            c.country,
            c.segment,
            c.customer_status,
            c.credit_score,
            c.estimated_monthly_income,
            CASE c.country
                WHEN %s THEN 'MXN'
                WHEN %s THEN 'COP'
                WHEN %s THEN 'ARS'
                ELSE NULL
            END AS income_currency,
            CASE
                WHEN c.estimated_monthly_income IS NULL THEN NULL
                ELSE c.estimated_monthly_income * fx.exchange_rate
            END AS income_usd,
            COALESCE(dpd.max_days_past_due, 0) AS max_days_past_due,
            COALESCE(flags.has_active_card, FALSE) AS has_active_card,
            COALESCE(flags.has_active_personal_loan, FALSE) AS has_active_personal_loan,
            %s::date AS as_of,
            %s::uuid AS batch_id
        FROM customers c
        LEFT JOIN (
            SELECT
                p.customer_id,
                MAX(COALESCE(p.days_past_due, 0)) AS max_days_past_due
            FROM products p
            WHERE p.product_status = %s
              AND p.product_type IN (%s, %s, %s)
            GROUP BY p.customer_id
        ) dpd ON dpd.customer_id = c.customer_id
        LEFT JOIN (
            SELECT
                p.customer_id,
                BOOL_OR(p.product_type = %s) AS has_active_card,
                BOOL_OR(p.product_type = %s) AS has_active_personal_loan
            FROM products p
            WHERE p.product_status = %s
            GROUP BY p.customer_id
        ) flags ON flags.customer_id = c.customer_id
        LEFT JOIN (
            SELECT e.source_currency, e.exchange_rate
            FROM daily_exchange_rates e
            WHERE e.date = %s::date
              AND e.target_currency = %s
        ) fx ON fx.source_currency = CASE c.country
            WHEN %s THEN 'MXN'
            WHEN %s THEN 'COP'
            WHEN %s THEN 'ARS'
        END
        """,
        (
            COUNTRY_MEXICO,
            COUNTRY_COLOMBIA,
            COUNTRY_ARGENTINA,
            AS_OF_DATE,
            str(batch_id),
            PRODUCT_STATUS_ACTIVE,
            PRODUCT_TYPE_CREDIT_CARD,
            PRODUCT_TYPE_PERSONAL_LOAN,
            PRODUCT_TYPE_MORTGAGE,
            PRODUCT_TYPE_CREDIT_CARD,
            PRODUCT_TYPE_PERSONAL_LOAN,
            PRODUCT_STATUS_ACTIVE,
            AS_OF_DATE,
            TARGET_CURRENCY_USD,
            COUNTRY_MEXICO,
            COUNTRY_COLOMBIA,
            COUNTRY_ARGENTINA,
        ),
    )
    count = conn.execute("SELECT COUNT(*) FROM customer_credit_profile").fetchone()
    print(f"gold rows={count[0] if count else 0} batch_id={batch_id}")
