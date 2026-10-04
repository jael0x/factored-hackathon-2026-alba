-- PLAN.md D22: an event's locale is es or pt, as processes_locale_check already holds for processes.
-- 007 moved English cases to es but left their events saying en, which the stored-event parser refuses.
-- This check fails on such a database instead of loading it: reset the volume (docker compose down -v).
ALTER TABLE events ADD CONSTRAINT events_locale_check
    CHECK (payload->>'locale' IS NULL OR payload->>'locale' IN ('es', 'pt'));
