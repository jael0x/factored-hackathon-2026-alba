-- Commands enqueued in one transaction share now(), and their uuid ids are random, so neither column keeps the order
-- the rules planned them in (ARCHITECTURE.md, "Process rules"). The worker takes commands in seq order.
ALTER TABLE commands ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;

CREATE UNIQUE INDEX commands_seq_key ON commands (seq);

CREATE INDEX commands_triggered_by_event_id_idx ON commands (triggered_by_event_id);

CREATE INDEX events_caused_by_command_id_idx ON events (caused_by_command_id);

-- A thread line is written by the command that wrote its event, so one event has at most one line.
CREATE UNIQUE INDEX messages_event_id_key ON messages (event_id);
