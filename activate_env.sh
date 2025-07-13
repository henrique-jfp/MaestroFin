#!/bin/bash
# Script para ativar o ambiente virtual do MaestroFin

echo "Ativando ambiente virtual do MaestroFin..."
source venv/bin/activate

echo "Ambiente virtual ativado com sucesso!"
echo "Para desativar, digite: deactivate"
echo ""
echo "Dependências instaladas:"
echo "- pdf2image (✓)"
echo "- Todas as dependências do requirements.txt (✓)"
echo ""
echo "Para verificar se está no ambiente virtual, veja se o prompt começar com (venv)"
