#!/bin/sh
# install-deps.sh — Instala las dependencias del repositorio clonado en /workspace.
# Detecta automáticamente el gestor de paquetes: Poetry, pip, pnpm, yarn, npm,
# Pipfile, setup.py, setup.cfg, pyproject.toml genérico.
# Busca archivos de dependencias tanto en la raíz como en subdirectorios comunes.
set -e

cd /workspace

echo "🔍 Detectando sistema de paquetes en $(pwd)..."

# ── Helper: busca un archivo en la raíz y en subdirectorios de 1 nivel ─────
find_file() {
    target="$1"
    # Raíz
    if [ -f "$target" ]; then
        echo "."
        return 0
    fi
    # Un nivel de profundidad
    for d in */; do
        if [ -f "${d}${target}" ]; then
            echo "$d"
            return 0
        fi
    done
    return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. POETRY  (pyproject.toml con [tool.poetry] o poetry.lock presente)
# ─────────────────────────────────────────────────────────────────────────────
POETRY_DIR=$(find_file "pyproject.toml" 2>/dev/null || true)
POETRY_LOCK_DIR=$(find_file "poetry.lock" 2>/dev/null || true)

# Normalise path: "." → "./" so "${DIR}file" becomes "./file"
normalize_dir() {
    d="$1"
    case "$d" in
        */) echo "$d" ;;
        *)  echo "${d}/" ;;
    esac
}

is_poetry=0
if [ -n "$POETRY_DIR" ]; then
    POETRY_DIR=$(normalize_dir "$POETRY_DIR")
    # Use grep -F for literal match (no regex issues with brackets)
    if grep -qF "[tool.poetry]" "${POETRY_DIR}pyproject.toml" 2>/dev/null; then
        is_poetry=1
    fi
fi
# Also treat as Poetry if poetry.lock exists alongside a pyproject.toml
if [ "$is_poetry" -eq 0 ] && [ -n "$POETRY_LOCK_DIR" ]; then
    POETRY_DIR=$(normalize_dir "$POETRY_LOCK_DIR")
    if [ -f "${POETRY_DIR}pyproject.toml" ]; then
        is_poetry=1
    fi
fi

if [ "$is_poetry" -eq 1 ]; then
    echo "📦 Detectado: Poetry  (ruta: ${POETRY_DIR})"
    cd "/workspace/${POETRY_DIR%/}"
    poetry install --no-root --without dev 2>/dev/null \
        || poetry install --no-root \
        || poetry install
    cd /workspace
    echo "✅ Dependencias instaladas con Poetry"

# ─────────────────────────────────────────────────────────────────────────────
# 2. PIP — requirements.txt (raíz o requirements/)
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "requirements.txt" ]; then
    echo "📦 Detectado: requirements.txt"
    pip install --quiet -r requirements.txt
    echo "✅ Dependencias instaladas desde requirements.txt"

elif [ -f "requirements/base.txt" ]; then
    echo "📦 Detectado: requirements/base.txt"
    pip install --quiet -r requirements/base.txt
    echo "✅ Dependencias instaladas desde requirements/base.txt"

elif [ -f "requirements/dev.txt" ]; then
    echo "📦 Detectado: requirements/dev.txt"
    pip install --quiet -r requirements/dev.txt
    echo "✅ Dependencias instaladas desde requirements/dev.txt"

elif [ -f "requirements-dev.txt" ]; then
    echo "📦 Detectado: requirements-dev.txt"
    pip install --quiet -r requirements-dev.txt
    echo "✅ Dependencias instaladas desde requirements-dev.txt"

elif [ -f "requirements-test.txt" ]; then
    echo "📦 Detectado: requirements-test.txt"
    pip install --quiet -r requirements-test.txt
    echo "✅ Dependencias instaladas desde requirements-test.txt"

# ─────────────────────────────────────────────────────────────────────────────
# 3. PIPENV
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "Pipfile" ]; then
    echo "📦 Detectado: Pipfile (pipenv)"
    pip install --quiet pipenv
    PIPENV_VENV_IN_PROJECT=1 pipenv install --dev --system --deploy 2>/dev/null \
        || pipenv install --system
    echo "✅ Dependencias instaladas con Pipenv"

# ─────────────────────────────────────────────────────────────────────────────
# 4. SETUP.PY / SETUP.CFG
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "setup.py" ]; then
    echo "📦 Detectado: setup.py"
    pip install --quiet -e ".[test,dev]" 2>/dev/null || pip install --quiet -e .
    echo "✅ Dependencias instaladas desde setup.py"

elif [ -f "setup.cfg" ]; then
    echo "📦 Detectado: setup.cfg"
    pip install --quiet -e ".[test,dev]" 2>/dev/null || pip install --quiet -e .
    echo "✅ Dependencias instaladas desde setup.cfg"

# ─────────────────────────────────────────────────────────────────────────────
# 5. PYPROJECT.TOML genérico (sin poetry)
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "pyproject.toml" ]; then
    echo "📦 Detectado: pyproject.toml (instalación genérica con pip)"
    pip install --quiet -e ".[test,dev]" 2>/dev/null \
        || pip install --quiet -e . 2>/dev/null \
        || pip install --quiet --no-build-isolation .
    echo "✅ Dependencias instaladas desde pyproject.toml"

# ─────────────────────────────────────────────────────────────────────────────
# 6. PNPM (monorepo JS/TS)
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "pnpm-workspace.yaml" ] || [ -f "pnpm-lock.yaml" ]; then
    echo "📦 Detectado: pnpm workspace (proyecto JavaScript/TypeScript)"
    corepack enable 2>/dev/null || true
    if command -v pnpm >/dev/null 2>&1; then
        pnpm install --frozen-lockfile 2>/dev/null || pnpm install
        echo "✅ Dependencias instaladas con pnpm"
    else
        npm install -g pnpm
        pnpm install --frozen-lockfile 2>/dev/null || pnpm install
        echo "✅ Dependencias instaladas con pnpm (instalado vía npm)"
    fi

# ─────────────────────────────────────────────────────────────────────────────
# 7. YARN
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "yarn.lock" ]; then
    echo "📦 Detectado: yarn"
    if command -v yarn >/dev/null 2>&1; then
        yarn install --frozen-lockfile 2>/dev/null || yarn install
    else
        npm install -g yarn
        yarn install --frozen-lockfile 2>/dev/null || yarn install
    fi
    echo "✅ Dependencias instaladas con yarn"

# ─────────────────────────────────────────────────────────────────────────────
# 8. NPM (package.json sin lockfiles especializados)
# ─────────────────────────────────────────────────────────────────────────────
elif [ -f "package.json" ]; then
    echo "📦 Detectado: npm (package.json)"
    if [ -f "package-lock.json" ]; then
        npm ci 2>/dev/null || npm install
    else
        npm install
    fi
    echo "✅ Dependencias instaladas con npm"

# ─────────────────────────────────────────────────────────────────────────────
# 9. Sin gestor detectado
# ─────────────────────────────────────────────────────────────────────────────
else
    echo "ℹ️  No se encontró ningún archivo de dependencias conocido."
    echo "   El repositorio podría no requerir instalación previa,"
    echo "   o usa un gestor no estándar."
    echo "   Puedes configurar REPOSITORY_TEST_INSTALL_COMMAND manualmente."
    # Salir sin error — pytest se ejecutará igualmente
    exit 0
fi
