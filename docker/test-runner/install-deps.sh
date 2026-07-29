#!/bin/sh
# install-deps.sh — Instala las dependencias del repositorio clonado en /workspace
# Detecta automáticamente el sistema de paquetes (Poetry, pip requirements.txt, pyproject.toml)
set -e

cd /workspace

echo "🔍 Detectando sistema de paquetes..."

if [ -f "pyproject.toml" ] && grep -q "\[tool.poetry\]" pyproject.toml 2>/dev/null; then
    echo "📦 Detectado: Poetry"
    echo "   Instalando dependencias con: poetry install --no-root --without dev || poetry install --no-root"
    poetry install --no-root --without dev 2>/dev/null || poetry install --no-root
    echo "✅ Dependencias instaladas con Poetry"

elif [ -f "requirements.txt" ]; then
    echo "📦 Detectado: requirements.txt"
    pip install -r requirements.txt
    echo "✅ Dependencias instaladas desde requirements.txt"

elif [ -f "requirements-dev.txt" ]; then
    echo "📦 Detectado: requirements-dev.txt"
    pip install -r requirements-dev.txt
    echo "✅ Dependencias instaladas desde requirements-dev.txt"

elif [ -f "pyproject.toml" ]; then
    echo "📦 Detectado: pyproject.toml (instalación genérica)"
    pip install -e . --no-build-isolation 2>/dev/null || pip install .
    echo "✅ Dependencias instaladas desde pyproject.toml"

else
    echo "⚠️  No se encontró ningún archivo de dependencias reconocido (pyproject.toml, requirements.txt)."
    echo "   Asegúrate de configurar REPOSITORY_TEST_INSTALL_COMMAND manualmente si es necesario."
fi
