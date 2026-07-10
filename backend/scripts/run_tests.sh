#!/bin/bash

# Script para executar testes
# Executa todos os testes com coverage

echo "🧪 Executando testes do TrançaPro"
echo "=================================="
echo ""

# Verifica se está no diretório correto
if [ ! -f "pytest.ini" ]; then
    echo "❌ Erro: Execute este script do diretório backend/"
    exit 1
fi

# Executa testes
echo "Executando todos os testes..."
pytest -v

echo ""
echo "Executando testes com coverage..."
pytest --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Testes concluídos!"
echo "📊 Relatório de coverage em: htmlcov/index.html"

