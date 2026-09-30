-- Login is the document number plus a code emailed to the address on file (ARCHITECTURE.md, "Auth and screens").

ALTER TABLE customers ADD COLUMN email text;

CREATE UNIQUE INDEX customers_document_number_key ON customers (document_number);

DROP INDEX customers_document_number_idx;

-- Nothing wrote login_codes before this migration, so the plain code column goes without a copy step.
ALTER TABLE login_codes DROP COLUMN code;

ALTER TABLE login_codes ADD COLUMN code_hash text NOT NULL;

ALTER TABLE login_codes ADD COLUMN wrong_codes integer NOT NULL DEFAULT 0;

ALTER TABLE login_codes ADD COLUMN used_at timestamptz;

CREATE INDEX login_codes_subject_idx ON login_codes (role, subject_id, created_at DESC);

-- An already loaded volume holds the same file hashes, so load would skip the reload and leave email empty.
-- Clearing load_batches makes the next load copy the CSVs again and fill it.
DELETE FROM load_batches;
