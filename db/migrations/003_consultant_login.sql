-- Consultants log in with their email and employee code, and only Active consultants get a code (ARCHITECTURE.md, "Auth and screens").

-- Rows loaded before this migration have no email or status, and every consultant in the file has both.
-- Clearing the old rows lets the new columns be NOT NULL, and clearing load_batches below makes load copy them again in the same run.
DELETE FROM service_agents;

ALTER TABLE service_agents ADD COLUMN email text NOT NULL;

ALTER TABLE service_agents ADD COLUMN agent_status text NOT NULL;

ALTER TABLE service_agents ADD COLUMN specialty text;

-- Neither field is unique alone. The pair is, also when compared the way the login compares it.
CREATE UNIQUE INDEX service_agents_login_key ON service_agents (lower(email), upper(employee_code));

DELETE FROM load_batches;
