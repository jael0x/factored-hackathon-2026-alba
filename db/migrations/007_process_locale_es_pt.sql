-- PLAN.md D22: the conversation is Spanish and Portuguese only, as the brief asks. English is no longer a locale.
-- A case opened in English on a local database before D22 is moved to Spanish, the default locale.
UPDATE processes SET locale = 'es' WHERE locale = 'en';
ALTER TABLE processes DROP CONSTRAINT processes_locale_check;
ALTER TABLE processes ADD CONSTRAINT processes_locale_check CHECK (locale IN ('es', 'pt'));
