#!/usr/bin/env python3
"""
Gerador de PDF alternativo usando ReportLab
Para resolver o problema do WeasyPrint não estar disponível
"""

import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

def generate_financial_pdf(context_data, filename="relatorio_financeiro.pdf"):
    """
    Gera um PDF de relatório financeiro usando ReportLab
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#34495e'),
        spaceAfter=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=black,
        spaceAfter=6
    )
    
    # Elementos do documento
    elements = []
    
    # Título principal
    title = Paragraph("🎼 Relatório Financeiro MaestroFin", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Período
    periodo_inicio = context_data.get('periodo_inicio', 'N/A')
    periodo_fim = context_data.get('periodo_fim', 'N/A')
    periodo_text = f"<b>Período:</b> {periodo_inicio} até {periodo_fim}"
    elements.append(Paragraph(periodo_text, normal_style))
    elements.append(Spacer(1, 15))
    
    # Resumo Financeiro
    elements.append(Paragraph("💰 Resumo Financeiro", subtitle_style))
    
    resumo_data = [
        ['Descrição', 'Valor'],
        ['Total de Receitas', f"R$ {context_data.get('total_receitas', '0.00'):.2f}"],
        ['Total de Gastos', f"R$ {context_data.get('total_gastos', '0.00'):.2f}"],
        ['Saldo do Período', f"R$ {context_data.get('saldo_periodo', '0.00'):.2f}"],
    ]
    
    resumo_table = Table(resumo_data, colWidths=[3*inch, 2*inch])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, black)
    ]))
    
    elements.append(resumo_table)
    elements.append(Spacer(1, 20))
    
    # Gastos por Categoria
    if context_data.get('gastos_por_categoria'):
        elements.append(Paragraph("📊 Gastos por Categoria", subtitle_style))
        
        categoria_data = [['Categoria', 'Valor', 'Percentual']]
        for categoria in context_data['gastos_por_categoria']:
            categoria_data.append([
                categoria.get('nome', 'N/A'),
                f"R$ {categoria.get('total', 0.00):.2f}",
                f"{categoria.get('percentual', 0.0):.1f}%"
            ])
        
        categoria_table = Table(categoria_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
        categoria_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fadbd8')),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        elements.append(categoria_table)
        elements.append(Spacer(1, 20))
    
    # Top Gastos
    if context_data.get('top_gastos'):
        elements.append(Paragraph("🔥 Maiores Gastos", subtitle_style))
        
        gastos_data = [['Data', 'Descrição', 'Categoria', 'Valor']]
        for gasto in context_data['top_gastos'][:10]:  # Apenas top 10
            gastos_data.append([
                gasto.get('data', 'N/A')[:10],  # Apenas a data
                gasto.get('descricao', 'N/A')[:30],  # Limitar tamanho
                gasto.get('categoria', 'N/A')[:15],  # Limitar tamanho
                f"R$ {gasto.get('valor', 0.00):.2f}"
            ])
        
        gastos_table = Table(gastos_data, colWidths=[0.8*inch, 2.2*inch, 1*inch, 1*inch])
        gastos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f39c12')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fef9e7')),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        elements.append(gastos_table)
        elements.append(Spacer(1, 20))
    
    # Insights
    if context_data.get('insights'):
        elements.append(Paragraph("💡 Insights Financeiros", subtitle_style))
        for insight in context_data['insights'][:5]:  # Top 5 insights
            insight_text = f"• {insight}"
            elements.append(Paragraph(insight_text, normal_style))
        elements.append(Spacer(1, 20))
    
    # Rodapé
    elements.append(Spacer(1, 30))
    rodape_text = f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} pelo MaestroFin Bot"
    rodape_style = ParagraphStyle(
        'Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#7f8c8d'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph(rodape_text, rodape_style))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

if __name__ == "__main__":
    # Teste
    test_data = {
        'periodo_inicio': '01/01/2025',
        'periodo_fim': '31/01/2025',
        'total_receitas': 5000.00,
        'total_gastos': 3500.00,
        'saldo_periodo': 1500.00,
        'gastos_por_categoria': [
            {'nome': 'Alimentação', 'total': 1200.00, 'percentual': 34.3},
            {'nome': 'Transporte', 'total': 800.00, 'percentual': 22.9},
            {'nome': 'Lazer', 'total': 500.00, 'percentual': 14.3},
        ],
        'top_gastos': [
            {'data': '2025-01-15 14:30:00', 'descricao': 'Supermercado', 'categoria': 'Alimentação', 'valor': 350.00},
            {'data': '2025-01-10 09:15:00', 'descricao': 'Combustível', 'categoria': 'Transporte', 'valor': 200.00},
        ],
        'insights': [
            'Seus gastos com alimentação representam 34% do total',
            'Você economizou 15% comparado ao mês anterior',
            'Maior concentração de gastos na segunda quinzena'
        ]
    }
    
    pdf_content = generate_financial_pdf(test_data)
    with open('teste_relatorio.pdf', 'wb') as f:
        f.write(pdf_content)
    print("✅ PDF de teste gerado: teste_relatorio.pdf")
