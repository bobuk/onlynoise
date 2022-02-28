FROM python:3.10-slim AS on-compile-image
RUN groupadd -g 2000 py && useradd -u 2000 --gid py -m -d /app --shell /bin/bash py
RUN mkdir -p /app/routers && chown py:py /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libssl-dev libffi-dev python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip && pip install poetry

USER py
WORKDIR /app

COPY --chown=py:py pyproject.toml poetry.toml /app/

RUN poetry update --no-dev && poetry install

############################################################################################

FROM python:3.10-slim AS onlynoise
RUN groupadd -g 2000 py && useradd -u 2000 --gid py -m -d /app --shell /bin/bash py

RUN mkdir -p /app/routers && chown py:py /app

USER py
WORKDIR /app

COPY --chown=py:py *.py /app/
COPY --chown=py:py routers/*.py /app/routers/
COPY --from=on-compile-image /app/.venv /app/.venv

ENTRYPOINT ["/app/.venv/bin/uvicorn", "--port", "8080", "--workers", "4", "--host", "0.0.0.0", "--proxy-headers"]
CMD ["index:app"]
