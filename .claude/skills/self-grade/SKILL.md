---
name: self-grade
description: Grade completed Alba work against AGENTS.md and ARCHITECTURE.md before presenting it. Trigger when a task or IMPLEMENTATION.md item is complete, before a commit or PR, when the user asks to review or grade code, or on phrases like "are you done", "is this ready", "let me see it", "show me what you've got".
---

# Self-grade against the Alba standard

You have finished (or are about to present) a change. Before you call it done, grade it against `AGENTS.md` (the coding standard) and `ARCHITECTURE.md` (the contract, which wins over every other file).

## No shortcuts

**Produce the full grading table.** "All pass" or "self-grade clean" is not a self-grade. The reviewer needs the evidence for every applicable row. A table without evidence is the same as no table.

Evidence follows the `AGENTS.md` rule: a grade of A or above cites an artifact from this session (`path:line`, a test name and its result, a query, a command output). A claim you did not check is labeled `inferred`, and an inferred claim cannot earn more than B.

## Process

1. **Stop.** Do not present the work yet.
2. **Re-read `AGENTS.md` and the parts of `ARCHITECTURE.md` this change touches.** Re-read `DESIGN.md` if `web/`, `mocks/`, or `diagrams/` changed.
3. **List every file created or modified** (`git status` and `git diff --stat`).
4. **Run the checks** that exist and record the output:
   - `pytest` (or `docker compose --profile test run --rm test`). Name which tests cover the change and confirm their files sit under `testpaths` in `pytest.ini`.
   - `npm run check` in `web/` if anything under `web/` changed (the `test` service already runs it).
   - `python api-spec/generate.py` if `api-spec/openapi.yaml` changed, then confirm `git diff` on the generated files matches.
   - `ruff check .`, `ruff format --check .`, and `mypy` (all run by `scripts/check.sh`). Record their output in row P1.
5. **Grade every row** with the table format below.
6. **Fix every F.** Do not ask. Fix it through the owner.
7. **Re-grade after the fixes.** Repeat until no F remains.
8. **Present the full table** with the work, and state the overall grade.

## Hard stops (automatic F, overall F)

Any one of these fails the whole change, whatever the other rows say:

- The path is `around`, not `through` (the Owner table in `AGENTS.md`).
- The change does not survive a reset: wiping the volume and running `docker compose` again breaks it, or it needs SQL by hand.
- An event, state, threshold, column, reason code, outcome, rule id, limit, or rate that `ARCHITECTURE.md` does not define.
- A `customer_id` branch, or any special case for one of the four oracle customers.
- Eligibility decided in the model, the prompt, the UI, or an HTTP handler.
- A hand-written DTO that `api-spec/openapi.yaml` should generate.
- A secret, `*.pdf`, or anything under `data/` staged, logged, printed, or sent to the model.

## Grading scale

| Grade | Meaning |
|-------|---------|
| A+ | Beyond the rule (for example, a sabotage run proved the exact test goes red, or a negative-path test the rule did not strictly require) |
| A | Fully compliant, with proven evidence |
| B | Minor imperfection that does not affect correctness, or the evidence is inferred |
| C | Noticeable deviation, justified with a written trade-off |
| F | Violation. Fix before presenting |
| N/A | The rule does not apply to this change. Say why in a few words |

## Required format

Every row appears. If a row does not apply, mark it N/A. Row numbers 1 to 19 follow `AGENTS.md`. The other sections use letter ids.

```markdown
## Self-grade: [task or IMPLEMENTATION.md item]

**Files touched:** every file created or modified
**Checks run:** command, result (for example `pytest`: 84 passed; `npm run typecheck`: clean)

### Before the first edit
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| G1 | Owner check | A | Cause: ... Owner: `api/domain/session/codes.py`. Path: through |
| G2 | Survives reset | A | Volume wiped, `docker compose up` re-run, login still works |
| G3 | Evidence labeled | A | Every load-bearing claim proven: `ARCHITECTURE.md:412`, `test_codes.py::test_expired_code` |

### How to think
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| 1 | Start with why | A | Customer sees ...; `processes.state` becomes ...; new `events` row ... |
| 2 | First principles | | |
| 3 | Root cause | | |
| 4 | Edge cases first | | |
| 5 | Evidence | | |
| 6 | Scope | | |
| 7 | Decompose | | |
| 8 | Personas | | |
| 9 | Plan, then build | | |

### Code shape
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| 10 | Functional flow | | |
| 11 | Single responsibility | | |
| 12 | No god functions | | Longest function: name, N lines |
| 13 | Pure core | | |
| 14 | Composition | | |
| 15 | DRY (loser deleted) | | grep for the old implementation: no hits |
| 16 | Adapter at the boundary | | |
| 17 | Explicit | | |
| 18 | Fail loud | | No catch-log-continue |
| 19 | Colocation | | |
| S1 | Naming is design | | |
| S2 | Early return, nesting <= 3 | | |

### Strings and comments
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| M1 | No magic strings (closed sets are constants) | | grep for raw literals of the touched closed sets |
| M2 | No bracket access when a typed field exists | | |
| M3 | No unnecessary comments | | Comments added: N, each a non-obvious why |

### Types
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| T1 | No `Any` without justification | | |
| T2 | Closed sets as `Literal` / enum / union, declared once | | |
| T3 | Discriminated unions, not booleans | | |
| T4 | Narrowing over casting | | |
| T5 | `None` is absence | | |
| T6 | Derive, do not store a second copy | | |
| T7 | Wire types generated from `openapi.yaml` | | |

### Data fetching and UI
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| U1 | Fetch at the level that owns the session | | |
| U2 | UI renders API fields, recomputes nothing | | |
| U3 | Loading, error, success on every fetch | | |
| U4 | Reason codes are not customer copy | | |
| U5 | Matches `DESIGN.md` | | |

### Database
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| D1 | Needed columns only, starts from the small set, no N+1 | | |
| D2 | Parameterized SQL only | | |
| D3 | `events` append-only, `caused_by_event_id` set | | |
| D4 | Migration one-way, works with the same change's code, never edited after it ran | | |
| D5 | Schema is the contract (no imputing, no USD conversion) | | |
| D6 | Views set `security_invoker = true` | | |
| D7 | Idempotency keys derived, no clock or random | | |
| D8 | Explicit tie-break comparator | | |

### Events, rules, commands
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| E1 | Event carries every fact a rule matches on | | |
| E2 | Matched fields are typed columns | | |
| E3 | One owner per trigger | | |
| E4 | `human_active` never calls the model | | |
| E5 | Deterministic links, never time proximity | | |

### Model
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| L1 | Prompt holds only the `ARCHITECTURE.md` list (booleans and the message) | | |
| L2 | Model never emits the decision words | | |
| L3 | Only `api/infrastructure/llm/conversation.py` imports the OpenAI SDK | | |

### Tests
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| X1 | Behavior, not private steps | | |
| X2 | Edge cases (None income/score, delinquency 29/30, Closed, held product, bad JSON, repeated idempotency key) | | |
| X3 | Negative path for every new branch | | |
| X4 | Full expected values, no soft asserts | | |
| X5 | Tied rows permuted | | |
| X6 | Sabotage once | | Broke X, test Y went red, restored |
| X7 | No OpenAI call, no mocked policy | | |
| X8 | Event-chain test crosses the worker | | |
| X9 | Test files on a path the command runs | | |
| X10 | Pre-existing failures fixed or reported | | |

### Process and contract sync
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| P1 | Lint and type check clean | | |
| P2 | One concern per change | | |
| P3 | Lockfile diff limited to the bumped package | | |
| P4 | `specs/` feature updated when behavior changed | | |
| P5 | `diagrams/c4.html` status updated when a gap closed | | |
| P6 | `IMPLEMENTATION.md` item ticked in the change that finishes it | | |
| P7 | `ARCHITECTURE.md` updated if the contract changed; no new session-note files | | |

### Security
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| K1 | External input validated at the boundary | | |
| K2 | No secret in git, image, log, or prompt | | |
| K3 | No `*.pdf` or `data/` staged; no dataset rows outside oracle fixtures | | |
| K4 | Login codes hashed, never in a log or response body | | |
| K5 | Customer API reads only that session's rows | | |

### Docs (only if docs changed)
| # | Rule | Grade | Evidence |
|---|------|-------|----------|
| W1 | English, straight quotes, no em-dashes | | |
| W2 | Data numbers name source and sample | | |
| W3 | One home per fact | | |

### Fixes applied
1. Moved the outcome `if` from `routes/session.py` into the policy engine (#13: F to A)

### Overall grade: B
```

## Overall grade

- **A+**: every applicable row A or A+, at least two A+, no hard stop.
- **A**: every applicable row A or above.
- **B**: mostly A, some B, no C or F.
- **C**: some C rows, each with its trade-off written out.
- **F**: any F or any hard stop remains. Not ready to present. Fix first.

## After fixing an F

For each fix, show:
- the row id, what was wrong, and what you changed (through which owner)
- the new grade for that row
- the recalculated overall grade

A fix that patches around the owner turns the row into a hard stop, not an A.

## If you skip this

`AGENTS.md` says: do not declare done while a rule in that file or in `ARCHITECTURE.md` is still broken. Presenting work without the full table breaks that rule, and the reviewer will send it back.
