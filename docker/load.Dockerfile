FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip \
    && curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip /var/lib/apt/lists/*

WORKDIR /app
COPY pipeline/requirements.txt /app/pipeline/requirements.txt
RUN pip install --no-cache-dir -r /app/pipeline/requirements.txt
COPY pipeline /app/pipeline
COPY db/migrations /app/db/migrations

ENV PYTHONPATH=/app
ENV RAW_DIR=/data/raw
ENV MIGRATIONS_DIR=/app/db/migrations

CMD ["python", "-m", "pipeline"]
