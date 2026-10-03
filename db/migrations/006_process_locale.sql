-- PLAN.md D21 and I5: the case keeps the language the customer chose with the switch, as locale.
-- process.start stores the opening message's locale and each turn stores its own message's, so it is never empty.
-- The model's reading of a message stays on the turn as language and is not stored on the process.
ALTER TABLE processes RENAME COLUMN language TO locale;
ALTER TABLE processes ALTER COLUMN locale SET NOT NULL;
ALTER TABLE processes ADD CONSTRAINT processes_locale_check CHECK (locale IN ('es', 'en', 'pt'));
