-- The consultant queue lists the cases with a person, in the order they were opened, then by id.
CREATE INDEX processes_human_active_queue_idx ON processes (created_at, id) WHERE state = 'human_active';
