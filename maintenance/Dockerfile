FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system oracle \
    && useradd --system --gid oracle --home-dir /nonexistent --no-create-home oracle \
    && mkdir --parents /app/scripts /app/certs \
    && chown --recursive oracle:oracle /app

RUN python -m pip install --no-cache-dir "psycopg[binary]==3.3.3"

COPY --chown=oracle:oracle database.py /app/database.py
COPY --chown=oracle:oracle scripts/maintain_analytics.py /app/scripts/maintain_analytics.py
COPY --chown=oracle:oracle certs/ /app/certs/

USER oracle

CMD ["python", "scripts/maintain_analytics.py"]
