# API spec

`openapi.yaml` is the wire contract: the JSON for every request and response. Behavior (who may call a route, what the worker does next, which facts are copied) stays in `ARCHITECTURE.md`. If this file and that one disagree, `ARCHITECTURE.md` wins. Then fix this file to match.

Do not hand-write a second DTO in `api/` or `web/`. Add the field here and regenerate.

## Add a field or a path

1. Edit `openapi.yaml`.
2. From the repo root, regenerate:

```bash
python -m pip install -r requirements-dev.txt
npm ci --prefix api-spec
python api-spec/generate.py
```

Without a local Python environment, the Python half runs in the test image (it has the generator), and the TypeScript half runs with `npx`:

```bash
docker compose --profile test run --rm --no-deps -v "$PWD:/work" -w /work test \
  python -c "import sys; sys.path.insert(0, 'api-spec'); import generate; generate.generate_python(generate.spec_sha256())"
npm ci --prefix api-spec
python3 -c "import sys; sys.path.insert(0, 'api-spec'); import generate; generate.generate_typescript(generate.spec_sha256())"
```

`generate.py` rewrites two files and stamps the SHA-256 of `openapi.yaml` on the first line of each. Do not edit those files by hand.

Every string enum under `components/schemas` (`Role`, `ProcessState`, `Outcome`, `ReasonCode`, `Intent`, and the rest) also gets a named alias at the end of `api/contract_models.py`, for example `Role = Literal['customer', 'consultant']`. Python code imports those names; it does not declare the same list again. A closed set that never crosses the wire (command names, process rule ids) lives in the module that owns it. Event names do cross it, as the trace discriminator, so they are the `EventName` enum; their constants and the idempotency-key builders live in `api/domain/process/events.py`.

| Output | Consumer |
|---|---|
| `api/contract_models.py` | FastAPI. Pydantic v2 models |
| `web/src/api/schema.d.ts` | `web/src/api/client.ts`. TypeScript types for `openapi-fetch` |

`npm` is required (`npx` must be on `PATH`). The Python generator is `datamodel-code-generator`, pinned in `requirements-dev.txt`. The TypeScript generator is `openapi-typescript`, pinned in `api-spec/package.json`.

A new path must also be added to `EXPECTED_PATHS` in `api/tests/test_contract.py`. The test fails if a path appears or disappears, if the generated hash does not match the YAML, if a live FastAPI route is missing from the spec or returns a model that is not one of these schemas, or if a string enum has no named alias.

## Backend

Import the generated model and use it as the response type. FastAPI rejects a body that does not match.

```python
from api.contract_models import Health

@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")
```

The same import is the request body: a handler takes `CloseCaseRequest`, it does not declare its own class.

## Frontend

One client, typed by the generated schema. `baseUrl` is `/api` because the Vite dev proxy strips that prefix before the request reaches FastAPI. Paths in the spec do not include `/api`.

```ts
import { api } from "./api/client";

const { data, error, response } = await api.POST("/messages", {
  body: { text, client_message_id },
});
```

`data` is the response schema for that path. A field that is not in `openapi.yaml` does not type-check. Do not call `fetch` for these routes.
