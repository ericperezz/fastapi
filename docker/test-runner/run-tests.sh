#!/bin/sh
# run-tests.sh — Ejecuta los tests del repositorio clonado en /workspace.
# Detecta automáticamente si el proyecto tiene tests Python (pytest) o no.
# Si el repo no tiene tests Python, el script termina con éxito (exit 0).
set -e

cd /workspace

PYTEST_CMD="${PYTEST_CMD:-python -m pytest -q --tb=short --disable-warnings}"

echo "🔍 Detectando tipo de proyecto para ejecución de tests..."

# ── ¿Es un proyecto Python con tests? ────────────────────────────────────────
HAS_PYTHON_TESTS=0

# Buscar directorio tests/ o test/ con archivos .py
if find . -maxdepth 4 -type f -name "test_*.py" -o -name "*_test.py" 2>/dev/null | grep -q .; then
    HAS_PYTHON_TESTS=1
fi

# También considerar si hay pytest.ini, setup.cfg con [tool:pytest], pyproject.toml con pytest
if [ "$HAS_PYTHON_TESTS" -eq 0 ]; then
    if [ -f "pytest.ini" ] || [ -f "tox.ini" ] || [ -f "conftest.py" ]; then
        HAS_PYTHON_TESTS=1
    fi
fi

if [ "$HAS_PYTHON_TESTS" -eq 0 ] && [ -f "pyproject.toml" ]; then
    if grep -q "\[tool\.pytest" pyproject.toml 2>/dev/null; then
        HAS_PYTHON_TESTS=1
    fi
fi

if [ "$HAS_PYTHON_TESTS" -eq 0 ] && [ -f "setup.cfg" ]; then
    if grep -q "\[tool:pytest\]" setup.cfg 2>/dev/null; then
        HAS_PYTHON_TESTS=1
    fi
fi

# ── Ejecutar según lo detectado ───────────────────────────────────────────────
if [ "$HAS_PYTHON_TESTS" -eq 1 ]; then
    echo "🧪 Proyecto Python con tests detectado — ejecutando pytest..."
    eval "$PYTEST_CMD $@"
else
    echo "ℹ️  No se detectaron tests Python en este repositorio."
    echo "   Si el proyecto usa otro framework de tests (Jest, Vitest, etc.),"
    echo "   configura REPOSITORY_TEST_COMMAND manualmente con el comando adecuado."
    echo ""
    echo "✅ Ejecución finalizada sin errores (sin tests Python que ejecutar)."
    exit 0
fi
