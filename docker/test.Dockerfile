FROM python:3.12-slim

WORKDIR /app
COPY requirements-dev.txt /app/requirements-dev.txt
COPY pipeline/requirements.txt /app/pipeline/requirements.txt
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

COPY pipeline /app/pipeline
COPY api /app/api
COPY api-spec/openapi.yaml api-spec/generate.py /app/api-spec/
COPY web/src/api /app/web/src/api
COPY db /app/db
COPY pytest.ini /app/pytest.ini
COPY conftest.py /app/conftest.py

ENV PYTHONPATH=/app
ENV ALBA_TEST_ADMIN_DATABASE_URL=postgresql://alba:alba@postgres:5432/postgres

CMD ["pytest", "-v"]
