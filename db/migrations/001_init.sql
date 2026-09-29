CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE customers (
    customer_id text PRIMARY KEY,
    document_number text NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    country text NOT NULL,
    segment text NOT NULL,
    credit_score integer,
    estimated_monthly_income numeric,
    customer_status text NOT NULL
);

CREATE INDEX customers_document_number_idx ON customers (document_number);
CREATE INDEX customers_name_idx ON customers (last_name, first_name);

CREATE TABLE products (
    product_id text PRIMARY KEY,
    customer_id text NOT NULL REFERENCES customers (customer_id),
    product_type text NOT NULL,
    product_number text NOT NULL,
    currency text NOT NULL,
    current_balance numeric,
    product_status text NOT NULL,
    days_past_due integer
);

CREATE INDEX products_customer_id_idx ON products (customer_id);

CREATE TABLE daily_exchange_rates (
    date date NOT NULL,
    source_currency text NOT NULL,
    target_currency text NOT NULL,
    exchange_rate numeric NOT NULL,
    PRIMARY KEY (date, source_currency, target_currency)
);

CREATE TABLE service_agents (
    agent_id text PRIMARY KEY,
    employee_code text NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL
);

CREATE TABLE load_batches (
    path text NOT NULL,
    bytes bigint NOT NULL,
    sha256 text NOT NULL,
    batch_id uuid NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (path, sha256)
);

CREATE TABLE customer_credit_profile (
    customer_id text PRIMARY KEY REFERENCES customers (customer_id),
    first_name text NOT NULL,
    last_name text NOT NULL,
    country text NOT NULL,
    segment text NOT NULL,
    customer_status text NOT NULL,
    credit_score integer,
    income_local numeric,
    income_currency text,
    income_usd numeric,
    max_days_past_due integer NOT NULL,
    has_active_card boolean NOT NULL,
    has_active_personal_loan boolean NOT NULL,
    as_of date NOT NULL,
    batch_id uuid NOT NULL
);

CREATE TABLE processes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id text NOT NULL,
    process_key text NOT NULL,
    state text NOT NULL,
    end_reason text,
    product text,
    language text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX processes_one_open_per_customer_idx
    ON processes (customer_id, process_key)
    WHERE state <> 'ended';

CREATE TABLE events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name text NOT NULL,
    payload jsonb NOT NULL,
    customer_id text,
    process_id uuid,
    process_state text,
    actor text NOT NULL,
    caused_by_event_id uuid,
    caused_by_command_id uuid,
    idempotency_key text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX events_process_id_created_at_idx ON events (process_id, created_at);

CREATE TABLE commands (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    command_name text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    triggered_by_event_id uuid,
    emitted_by_rule_id text,
    idempotency_key text NOT NULL UNIQUE,
    status text NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX commands_pending_idx ON commands (status) WHERE status = 'pending';

CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id uuid NOT NULL REFERENCES processes (id),
    author text NOT NULL,
    body text NOT NULL,
    event_id uuid,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE llm_turns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id uuid NOT NULL,
    command_id uuid,
    request jsonb NOT NULL,
    raw_response text,
    parsed jsonb,
    parse_ok boolean NOT NULL,
    model text NOT NULL,
    input_tokens integer,
    output_tokens integer,
    latency_ms integer,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE login_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL,
    subject_id text NOT NULL,
    role text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
