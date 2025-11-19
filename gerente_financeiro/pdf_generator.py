#!/usr/bin/env python3
"""
Gerador de PDF profissional e moderno para relatórios financeiros
MaestroFin - Relatório Executivo Financeiro
"""

import os
import io
import math
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

def create_header_frame(canvas, doc):
    """Cria um cabeçalho elegante para cada página"""
    canvas.saveState()

    # Fundo gradiente do cabeçalho
    canvas.setFillColor(HexColor('#1a365d'))
    canvas.rect(0, A4[1] - 2*cm, A4[0], 2*cm, fill=1)

    # Linha decorativa superior
    canvas.setStrokeColor(HexColor('#fbbf24'))
    canvas.setLineWidth(3)
    canvas.line(0, A4[1] - 2*cm, A4[0], A4[1] - 2*cm)

    # Logo/Título
    canvas.setFillColor(HexColor('#fbbf24'))
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(2*cm, A4[1] - 1.2*cm, "🎼 MAESTROFIN")

    # Subtítulo
    canvas.setFillColor(HexColor('#e2e8f0'))
    canvas.setFont("Helvetica", 10)
    canvas.drawString(2*cm, A4[1] - 1.6*cm, "RELATÓRIO EXECUTIVO FINANCEIRO")

    # Data no canto direito
    canvas.setFillColor(HexColor('#cbd5e1'))
    canvas.setFont("Helvetica", 8)
    data_texto = datetime.now().strftime('%d/%m/%Y %H:%M')
    canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.4*cm, f"Gerado em: {data_texto}")

    canvas.restoreState()

def create_footer_frame(canvas, doc):
    """Cria um rodapé elegante para cada página"""
    canvas.saveState()

    # Linha decorativa inferior
    canvas.setStrokeColor(HexColor('#e5e7eb'))
    canvas.setLineWidth(1)
    canvas.line(0, 1.5*cm, A4[0], 1.5*cm)

    # Texto do rodapé
    canvas.setFillColor(HexColor('#6b7280'))
    canvas.setFont("Helvetica", 7)
    rodape = "MaestroFin Bot - Seu assistente financeiro inteligente | www.maestrofin.com"
    canvas.drawCentredString(A4[0]/2, 1*cm, rodape)

    # Numeração de página
    page_num = f"Página {doc.page}"
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, page_num)

    canvas.restoreState()

def create_kpi_card(title, value, subtitle, color, trend=None):
    """Cria um card KPI elegante"""
    # Fundo do card
    drawing = Drawing(4*cm, 3*cm)

    # Retângulo principal
    rect = Rect(0, 0, 4*cm, 3*cm, fillColor=color, strokeColor=color)
    drawing.add(rect)

    # Título
    title_text = String(0.3*cm, 2.3*cm, title, fontSize=8, fillColor=white, fontName="Helvetica-Bold")
    drawing.add(title_text)

    # Valor principal
    value_text = String(0.3*cm, 1.5*cm, f"R$ {value:,.2f}".replace(',', '.'), fontSize=14, fillColor=white, fontName="Helvetica-Bold")
    drawing.add(value_text)

    # Subtítulo
    subtitle_text = String(0.3*cm, 0.8*cm, subtitle, fontSize=6, fillColor=HexColor('#e2e8f0'), fontName="Helvetica")
    drawing.add(subtitle_text)

    # Indicador de tendência (se fornecido)
    if trend:
        trend_color = HexColor('#10b981') if trend > 0 else HexColor('#ef4444')
        trend_symbol = "↗" if trend > 0 else "↘"
        trend_text = String(3.2*cm, 0.8*cm, f"{trend_symbol} {abs(trend):.1f}%", fontSize=7, fillColor=trend_color, fontName="Helvetica-Bold")
        drawing.add(trend_text)

    return drawing

def create_pie_chart(data, labels, title):
    """Cria um gráfico de pizza elegante"""
    drawing = Drawing(8*cm, 6*cm)

    # Gráfico de pizza
    pie = Pie()
    pie.x = 2*cm
    pie.y = 1*cm
    pie.width = 4*cm
    pie.height = 4*cm
    pie.data = data
    pie.labels = labels

    # Cores modernas
    colors = [HexColor('#3b82f6'), HexColor('#ef4444'), HexColor('#10b981'), HexColor('#f59e0b'),
              HexColor('#8b5cf6'), HexColor('#06b6d4'), HexColor('#84cc16'), HexColor('#f97316')]
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = white

    for i, color in enumerate(colors[:len(data)]):
        pie.slices[i].fillColor = color

    drawing.add(pie)

    # Título
    title_text = String(4*cm, 5.5*cm, title, fontSize=12, fillColor=HexColor('#1f2937'), fontName="Helvetica-Bold", textAnchor='middle')
    drawing.add(title_text)

    return drawing

def generate_financial_pdf(context_data, filename="relatorio_financeiro.pdf"):
    """
    Gera um PDF de relatório financeiro profissional e moderno usando ReportLab
    """
    buffer = io.BytesIO()

    # Configuração do documento com cabeçalho e rodapé
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=3*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )

    # Frames para cabeçalho e rodapé
    def header_footer(canvas, doc):
        create_header_frame(canvas, doc)
        create_footer_frame(canvas, doc)

    doc.build([], onFirstPage=header_footer, onLaterPages=header_footer)

    # Reset buffer para conteúdo real
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=3*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )

    # Estilos modernos
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ModernTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName="Helvetica-Bold"
    )

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#1e40af'),
        spaceAfter=15,
        fontName="Helvetica-Bold",
        borderColor=HexColor('#3b82f6'),
        borderWidth=0,
        borderPadding=5
    )

    kpi_title_style = ParagraphStyle(
        'KPITitle',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=HexColor('#374151'),
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName="Helvetica-Bold"
    )

    normal_style = ParagraphStyle(
        'ModernNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#374151'),
        spaceAfter=8,
        leading=12
    )

    insight_style = ParagraphStyle(
        'InsightStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#059669'),
        spaceAfter=6,
        bulletIndent=20,
        leftIndent=20,
        fontName="Helvetica-Bold"
    )

    # Elementos do documento
    elements = []

    # === CAPA DO RELATÓRIO ===
    elements.append(Paragraph("RELATÓRIO EXECUTIVO FINANCEIRO", title_style))

    # Informações do período
    periodo_inicio = context_data.get('periodo_inicio', 'N/A')
    periodo_fim = context_data.get('periodo_fim', 'N/A')

    periodo_info = f"""
    <para alignment="center" fontSize="14" color="#6b7280">
    <b>Período Analisado:</b> {periodo_inicio} até {periodo_fim}<br/>
    <b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
    </para>
    """
    elements.append(Paragraph(periodo_info, normal_style))
    elements.append(Spacer(1, 50))

    # === SEÇÃO 1: RESUMO EXECUTIVO ===
    elements.append(Paragraph("📊 RESUMO EXECUTIVO", section_title_style))

    # Cards KPI
    receita_total = context_data.get('total_receitas', 0)
    gastos_total = context_data.get('total_gastos', 0)
    saldo_periodo = context_data.get('saldo_periodo', 0)

    # Calcular tendências (simuladas por enquanto)
    tendencia_receita = 5.2  # Simulado
    tendencia_gastos = -2.1   # Simulado

    kpi_data = [
        [create_kpi_card("RECEITAS", receita_total, "Total do período", HexColor('#10b981'), tendencia_receita),
         create_kpi_card("DESPESAS", gastos_total, "Total do período", HexColor('#ef4444'), tendencia_gastos)],
        [create_kpi_card("SALDO", saldo_periodo, "Resultado líquido", HexColor('#3b82f6') if saldo_periodo >= 0 else HexColor('#f59e0b'), None),
         create_kpi_card("ECONOMIA", receita_total - gastos_total, "Capacidade de poupança", HexColor('#8b5cf6'), None)]
    ]

    kpi_table = Table(kpi_data, colWidths=[4*cm, 4*cm])
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(kpi_table)
    elements.append(Spacer(1, 30))

    # === SEÇÃO 2: ANÁLISE DE GASTOS ===
    elements.append(Paragraph("💰 ANÁLISE DETALHADA DE GASTOS", section_title_style))

    # Gráfico de pizza para gastos por categoria
    if context_data.get('gastos_por_categoria'):
        categorias = context_data['gastos_por_categoria'][:8]  # Top 8 categorias
        valores = [cat.get('total', 0) for cat in categorias]
        labels = [f"{cat.get('nome', 'N/A')[:15]}\n{cat.get('percentual', 0):.1f}%" for cat in categorias]

        pie_chart = create_pie_chart(valores, labels, "Distribuição de Gastos por Categoria")
        elements.append(pie_chart)
        elements.append(Spacer(1, 20))

    # Tabela detalhada de categorias
    if context_data.get('gastos_por_categoria'):
        elements.append(Paragraph("📋 Detalhamento por Categoria", kpi_title_style))

        categoria_data = [['Categoria', 'Valor', 'Percentual', 'Status']]
        for categoria in context_data['gastos_por_categoria']:
            valor = categoria.get('total', 0)
            percentual = categoria.get('percentual', 0)

            # Determinar status baseado no percentual
            if percentual > 30:
                status = "🔴 Alto"
                status_color = HexColor('#ef4444')
            elif percentual > 15:
                status = "🟡 Médio"
                status_color = HexColor('#f59e0b')
            else:
                status = "🟢 Baixo"
                status_color = HexColor('#10b981')

            categoria_data.append([
                categoria.get('nome', 'N/A'),
                f"R$ {valor:,.2f}".replace(',', '.'),
                f"{percentual:.1f}%",
                status
            ])

        categoria_table = Table(categoria_data, colWidths=[3*cm, 2*cm, 1.5*cm, 1.5*cm])
        categoria_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9fafb')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f9fafb')])
        ]))

        elements.append(categoria_table)
        elements.append(Spacer(1, 30))

    # === SEÇÃO 3: TRANSAÇÕES DESTACADAS ===
    if context_data.get('top_gastos'):
        elements.append(Paragraph("🔥 TRANSAÇÕES MAIS RELEVANTES", section_title_style))

        # Top 10 maiores gastos
        top_gastos = context_data['top_gastos'][:10]

        transacao_data = [['Data', 'Descrição', 'Categoria', 'Valor']]
        for gasto in top_gastos:
            data_formatada = gasto.get('data', 'N/A')
            if len(data_formatada) > 10:
                data_formatada = data_formatada[:10]

            transacao_data.append([
                data_formatada,
                gasto.get('descricao', 'N/A')[:25] + ('...' if len(gasto.get('descricao', '')) > 25 else ''),
                gasto.get('categoria', 'N/A')[:15] + ('...' if len(gasto.get('categoria', '')) > 15 else ''),
                f"R$ {gasto.get('valor', 0):.2f}"
            ])

        transacao_table = Table(transacao_data, colWidths=[2*cm, 4*cm, 2.5*cm, 2*cm])
        transacao_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#fecaca')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#fef2f2')])
        ]))

        elements.append(transacao_table)
        elements.append(Spacer(1, 30))

    # === SEÇÃO 4: INSIGHTS E RECOMENDAÇÕES ===
    elements.append(Paragraph("💡 INSIGHTS INTELIGENTES", section_title_style))

    insights = context_data.get('insights', [])

    if not insights:
        # Insights padrão se não houver dados
        insights = [
            "🎯 Mantenha o controle dos gastos essenciais para garantir equilíbrio financeiro",
            "📈 Considere aumentar suas fontes de receita para melhorar o saldo mensal",
            "💰 Estabeleça metas de economia realistas baseadas no seu padrão de gastos",
            "📊 Monitore regularmente suas categorias de maior despesa",
            "🎪 Diversifique suas fontes de renda para maior segurança financeira"
        ]

    for insight in insights[:8]:  # Máximo 8 insights
        elements.append(Paragraph(f"• {insight}", insight_style))

    elements.append(Spacer(1, 40))

    # === SEÇÃO 5: MÉTRICAS DE PERFORMANCE ===
    elements.append(Paragraph("📈 MÉTRICAS DE PERFORMANCE", section_title_style))

    # Calcular métricas
    taxa_poupanca = (saldo_periodo / receita_total * 100) if receita_total > 0 else 0
    media_diaria_gastos = gastos_total / 30  # Aproximado
    media_diaria_receitas = receita_total / 30  # Aproximado

    metricas_data = [
        ['Métrica', 'Valor', 'Status'],
        ['Taxa de Poupança', f"{taxa_poupanca:.1f}%", "🟢 Excelente" if taxa_poupanca > 20 else "🟡 Regular" if taxa_poupanca > 10 else "🔴 Atenção"],
        ['Média Diária de Gastos', f"R$ {media_diaria_gastos:.2f}", "📊 Informativo"],
        ['Média Diária de Receitas', f"R$ {media_diaria_receitas:.2f}", "📊 Informativo"],
        ['Dias no Verde', "25/30" if saldo_periodo > 0 else "15/30", "🟢 Bom" if saldo_periodo > 0 else "🟡 Regular"],
        ['Controle de Gastos', "Bom" if gastos_total < receita_total else "Atenção", "🟢 Bom" if gastos_total < receita_total else "🔴 Atenção"]
    ]

    metricas_table = Table(metricas_data, colWidths=[3*cm, 2.5*cm, 2*cm])
    metricas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#7c3aed')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#faf5ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d8b4fe')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#faf5ff')])
    ]))

    elements.append(metricas_table)
    elements.append(Spacer(1, 50))

    # === RODAPÉ FINAL ===
    rodape_final = f"""
    <para alignment="center" fontSize="8" color="#9ca3af">
    Relatório gerado automaticamente pelo MaestroFin Bot<br/>
    Para mais informações, visite www.maestrofin.com ou entre em contato com nosso suporte<br/>
    © 2025 MaestroFin - Todos os direitos reservados
    </para>
    """
    elements.append(Paragraph(rodape_final, normal_style))

    # Construir PDF final
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
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
