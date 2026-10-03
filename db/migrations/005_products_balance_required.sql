-- An empty balance loads as 0 (ARCHITECTURE.md, "Data"), so the column is required like the wire field it feeds.
-- The file measured on Oct 1 has no empty balance, and the update covers a volume loaded before the load wrote 0.
UPDATE products SET current_balance = 0 WHERE current_balance IS NULL;

ALTER TABLE products ALTER COLUMN current_balance SET NOT NULL;
