-- The thread and the cycle wait follow caused_by_event_id, and the thread reads a case's messages rows by process.
CREATE INDEX events_caused_by_event_id_idx ON events (caused_by_event_id);

CREATE INDEX messages_process_id_idx ON messages (process_id);
