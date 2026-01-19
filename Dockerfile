# -----------------------------------#
# Stage 1: Build Python dependencies #
# -----------------------------------#
FROM python:3.13-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
        libssl-dev \
        curl \
        ca-certificates \
        zlib1g-dev \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

RUN python -m venv /venv 

COPY src/ ./src/

COPY pyproject.toml ./

RUN /venv/bin/pip install --no-cache-dir .


# -----------------------------------#
#    Stage 2: Build Runtime Image    #
# -----------------------------------#
FROM python:3.13-slim

LABEL org.opencontainers.image.title="GH0STB1T"
LABEL org.opencontainers.image.description="A multi-format steganography toolkit"
LABEL org.opencontainers.image.source="https://github.com/kariemoorman/ghostbit"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV HOME=/home/appuser
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=build /venv /venv

ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH=/app/ghostbit

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data
RUN chown -R appuser:appuser /data

USER appuser

WORKDIR /data

ENTRYPOINT ["ghostbit"]
CMD ["--help"]
