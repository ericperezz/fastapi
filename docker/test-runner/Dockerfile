FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
# Poetry: no crear virtualenv dentro del contenedor, instalar en el sistema
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

WORKDIR /workspace

# Instalar herramientas del sistema, Node.js y curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && corepack enable \
    && rm -rf /var/lib/apt/lists/*

COPY docker/test-runner/requirements.txt /tmp/test-runner-requirements.txt

# Instalar dependencias base del runner + Poetry
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/test-runner-requirements.txt \
    && python -m pip install poetry

# Script inteligente de instalación de dependencias del repo clonado
COPY docker/test-runner/install-deps.sh /usr/local/bin/install-deps
RUN chmod +x /usr/local/bin/install-deps

CMD ["sh", "-lc", "python -m pytest -q --tb=short --disable-warnings"]