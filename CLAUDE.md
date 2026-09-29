# Alba

Before planning or editing, read `AGENTS.md` and `ARCHITECTURE.md` in this directory. Both bind. If code, a plan, or an idea contradicts them, stop and say so. Do not invent events, states, thresholds, reason codes, or outcomes.

- `ARCHITECTURE.md`: the product and build contract. It wins over every other file.
- `AGENTS.md`: the coding standard, including how docs are written.
- `DESIGN.md`: how `web/`, `mocks/index.html`, and `diagrams/c4.html` look and move. Read it before UI work. The contract wins over it.
- `PLAN.md`: hackathon requirements, data evidence, open decisions (§5), research backlog (§6), schedule. It does not override the contract.
- `README.md`: product view, repo map, data access.
- `diagrams/c4.html`: clickable C4 view of the contract. When a gap or decision closes, update the matching spec status there in the same change.
- `specs/`: Gherkin behavior specs, one feature per file, numbered by the customer journey. Use `/spec` to draft or update them. A contract change that alters behavior updates the matching feature in the same change.

Current phase: research and definition. There is no application code yet. The known gaps in `ARCHITECTURE.md` are closed. Work now closes a research item (`PLAN.md` §6) or an open decision (`PLAN.md` §5). A closed decision is written into `ARCHITECTURE.md` in the same change.

S3 credentials and `OPENAI_API_KEY` live only in `.env`. Never read, print, log, or commit them. Never commit `*.pdf` or anything under `data/`. Do not open page 2 of `docs/LATAM_Bank_Complete_Data_Dictionary.pdf`: it holds the keys.
