-- Events written in one transaction share now(), and their uuid ids are random, so neither column keeps the order they were written in.
ALTER TABLE events ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;

CREATE UNIQUE INDEX events_seq_key ON events (seq);

CREATE INDEX events_process_id_seq_idx ON events (process_id, seq);
