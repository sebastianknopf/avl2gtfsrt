FROM python:3.10-slim

RUN apt update -y && apt install -y git

WORKDIR /app

COPY .git/ /app/.git
RUN mkdir -p /app/src/itcs435/common

COPY pyproject.toml /app
RUN pip install --no-cache-dir .
RUN pip install debugpy

COPY ./config /app/config
COPY src/ /app/src
RUN pip install --no-deps .

STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "-m", "itcs435", "main"]