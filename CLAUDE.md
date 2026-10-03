# Alba

Before planning or editing, read `AGENTS.md` and `ARCHITECTURE.md` in this directory. Both bind. If code, a plan, or an idea contradicts them, stop and say so. Do not invent events, states, thresholds, reason codes, or outcomes.

- `ARCHITECTURE.md`: the product and build contract. It wins over every other file.
- `AGENTS.md`: the coding standard, including how docs are written.
- `DESIGN.md`: how `web/`, `mocks/index.html`, and `diagrams/c4.html` look and move. Read it before UI work. The contract wins over it.
- `PLAN.md`: hackathon requirements, data evidence, open decisions (§5), research backlog (§6), schedule. It does not override the contract.
- `IMPLEMENTATION.md`: build order. Interfaces first, then three tracks (Engine, Model and eval, Web) with no fixed owners. Take the first unblocked item, and tick it in the PR that finishes it. An item blocked by a decision waits for it.
- `README.md`: product view, repo map, data access.
- `diagrams/c4.html`: clickable C4 view of the contract. When a gap or decision closes, update the matching spec status there in the same change.
- `api-spec/openapi.yaml`: the wire contract. Change a request or response there, then regenerate (`api-spec/README.md`); never hand-write a DTO.
- `specs/`: Gherkin behavior specs, one feature per file, numbered by the customer journey. Use `/spec` to draft or update them. A contract change that alters behavior updates the matching feature in the same change.

Current phase: the compose load path, both logins, the customer home, and the language switch are built (`postgres`, one-shot `load`, `mailpit`, the customer and consultant login routes, `GET /me`, `GET /consultant/me`, and `GET /products` in `api/`, `/login`, `/consultant/login`, and `/` in `web/`, every label in Spanish, English, or Portuguese from `web/src/i18n/`). The pure parts of the engine are built in `api/domain/` with their tests: the policy engine, the event store and process lifecycle, and the process rules. Nothing runs the rules yet: the worker, the conversation, the templates, and the consultant queue and case are not implemented; the order is in `IMPLEMENTATION.md`. Work goes one C4 component at a time: screen, then API interface, then engine. `ARCHITECTURE.md` still wins. A contract change that alters behavior updates the matching `specs/` feature in the same change. When a C4 open item is closed by code (for example how `data/raw/` reaches `load`), update `diagrams/c4.html` in the same change.

Vocabulary: a person who reviews a handed-off case is a consultant ("asesor" on screen). Identifiers in `db/` and `pipeline/` keep the dataset's name, `service_agents` with `agent_id` and `agent_status`; everything else (`api/`, `web/`, `api-spec/`, docs, specs, the C4 page, and comments anywhere) says consultant, and agent is left for the AI agent. The rule is in `AGENTS.md`, "Consultants and service agents".

S3 credentials and `OPENAI_API_KEY` live only in `.env`. Never read, print, log, or commit them. Never commit `*.pdf` or anything under `data/`. Do not open page 2 of `docs/LATAM_Bank_Complete_Data_Dictionary.pdf`: it holds the keys.
