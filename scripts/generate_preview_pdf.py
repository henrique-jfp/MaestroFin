#!/usr/bin/env python3
"""Gera um PDF de preview usando o gerador interno (ReportLab) para revisão local.

Uso:
  python3 scripts/generate_preview_pdf.py

Isso criará `preview_relatorio.pdf` na raiz do repositório.
"""
import os
import sys
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, ROOT)

from gerente_financeiro.pdf_generator import generate_financial_pdf


def main():
    test_data = {
        'periodo_inicio': '01/01/2025',
        'periodo_fim': '31/01/2025',
        'total_receitas': 8500.00,
        'total_gastos': 6200.00,
        'saldo_periodo': 2300.00,
        'gastos_por_categoria': [
            {'nome': 'Alimentação', 'total': 1850.00, 'percentual': 29.8},
            {'nome': 'Transporte', 'total': 1200.00, 'percentual': 19.4},
            {'nome': 'Lazer e Entretenimento', 'total': 980.00, 'percentual': 15.8},
            {'nome': 'Saúde', 'total': 750.00, 'percentual': 12.1},
            {'nome': 'Educação', 'total': 620.00, 'percentual': 10.0},
            {'nome': 'Vestuário', 'total': 450.00, 'percentual': 7.3},
            {'nome': 'Tecnologia', 'total': 250.00, 'percentual': 4.0},
            {'nome': 'Outros', 'total': 100.00, 'percentual': 1.6},
        ],
        'top_gastos': [],
        'insights': [],
        # opcional: injete 'grafico_pizza_png' como bytes se quiser testar com Gráfico Matplotlib
    }

    out = generate_financial_pdf(test_data)
    out_path = os.path.join(ROOT, 'preview_relatorio.pdf')
    with open(out_path, 'wb') as f:
        f.write(out)
    print(f'Preview gerado: {out_path}')


if __name__ == '__main__':
    main()
