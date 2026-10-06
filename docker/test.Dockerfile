FROM node:22.23.3-trixie-slim@sha256:b26b04c123d9ff8ab646ceb18b9d75a1173acf64b9a401094b906d27b29338d4 AS node

# Same Debian release and libc as the Python base: Rollup and esbuild install native binaries for the libc npm ci runs on.
FROM node AS web-deps
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM python:3.12.15-slim@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && node --version \
    && npm --version
ENV NPM_CONFIG_UPDATE_NOTIFIER=false

WORKDIR /app
COPY requirements-dev.txt /app/requirements-dev.txt
COPY pipeline/requirements.txt /app/pipeline/requirements.txt
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

COPY --from=web-deps /app/web/node_modules /app/web/node_modules
COPY web /app/web
COPY pipeline /app/pipeline
COPY api /app/api
COPY eval /app/eval
COPY api-spec/openapi.yaml api-spec/generate.py /app/api-spec/
COPY db /app/db
COPY pytest.ini pyproject.toml /app/
COPY scripts /app/scripts
COPY conftest.py /app/conftest.py

ENV PYTHONPATH=/app
ENV ALBA_TEST_ADMIN_DATABASE_URL=postgresql://alba:alba@postgres:5432/postgres

CMD ["sh", "-c", "npm --prefix web run check && sh scripts/check.sh"]
