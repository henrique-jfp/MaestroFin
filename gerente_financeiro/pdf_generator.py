#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAESTROFIN - Relatório Executivo Financeiro 2025
Versão Profissional Premium - Design Bank-Level
Autor: Henrique JFP (com melhorias by Grok)
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepInFrame, PageBreak
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Registrar fontes Google (baixe no Google Fonts se quiser usar local)
# Ou use Helvetica como fallback elegante
try:
    pdfmetrics.registerFont(TTFont('Inter', 'fonts/Inter-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Inter-Regular', 'fonts/Inter-Regular.ttf'))
except:
    # Fallback para Helvetica
    pass

# ====================== CORES PREMIUM ======================
AZUL_ESCURO = colors.HexColor("#0F172A")      # Fundo cabeçalho
AZUL_PRINCIPAL = colors.HexColor("#1E40AF")
VERDE = colors.HexColor("#10B981")
VERMELHO = colors.HexColor("#EF4444")
AMARELO = colors.HexColor("#F59E0B")
ROXO = colors.HexColor("#8B5CF6")
CINZA_TEXTO = colors.HexColor("#475569")
CINZA_CLARO = colors.HexColor("#F8FAFC")
GRADIENTE_TOP = [AZUL_ESCURO, colors.HexColor("#1E293B")]

# ====================== ESTILOS ======================
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleMain', fontName='Helvetica-Bold', fontSize=32, textColor=AZUL_ESCURO, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle(name='Subtitle', fontName='Helvetica', fontSize=14, textColor=CINZA_TEXTO, alignment=TA_CENTER, spaceAfter=40))
styles.add(ParagraphStyle(name='SectionTitle', fontName='Helvetica-Bold', fontSize=18, textColor=AZUL_PRINCIPAL, spaceBefore=30, spaceAfter=15, leftIndent=10))
styles.add(ParagraphStyle(name='Insight', fontName='Helvetica-Bold', fontSize=11, textColor=VERDE, leading=16, leftIndent=20, spaceAfter=10))
styles.add(ParagraphStyle(name='NormalCenter', fontName='Helvetica', fontSize=10, alignment=TA_CENTER, textColor=CINZA_TEXTO))
styles.add(ParagraphStyle(name='FooterText', fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER))

def header_footer(canvas, doc):
    width, height = A4
    canvas.saveState()

    # Cabeçalho com gradiente
    canvas.setFillColor(AZUL_ESCURO)
    canvas.rect(0, height - 2.8*cm, width, 2.8*cm, fill=1, stroke=0)

    # Logo/Título
    canvas.setFillColor(colors.HexColor("#FBBF24"))
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawString(2*cm, height - 1.8*cm, "MAESTROFIN")

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 11)
    canvas.drawString(2*cm, height - 2.4*cm, "Relatório Executivo Financeiro")

    canvas.setFillColor(colors.HexColor("#CBD5E1"))
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(width - 2*cm, height - 2.2*cm, f"Gerado em {datetime.now():%d/%m/%Y às %H:%M}")

    # Rodapé
    canvas.setFillColor(colors.HexColor("#E2E8F0"))
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.setLineWidth(1)
    canvas.line(2*cm, 1.5*cm, width - 2*cm, 1.5*cm)

    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width/2, 1*cm, "MaestroFin © 2025 • Seu assistente financeiro inteligente • @maestrofin_bot")

    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(width - 2*cm, 1*cm, f"Página {doc.page}")

    canvas.restoreState()

def create_premium_pie(data, labels, title):
    drawing = Drawing(500, 380)
    pie = Pie()
    pie.x = 120
    pie.y = 50
    pie.width = pie.height = 120
    pie.data = data
    pie.labels = []  # sem labels internas
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = colors.white
    pie.slices.popout = 8
    pie.sideLabels = True

    # Cores premium
    premium_colors = [
        colors.HexColor("#3B82F6"), colors.HexColor("#8B5CF6"), colors.HexColor("#10B981"),
        colors.HexColor("#F59E0B"), colors.HexColor("#EF4444"), colors.HexColor("#06B6D4"),
        colors.HexColor("#EC4899"), colors.HexColor("#14B8A6")
    ]
    for i, col in enumerate(premium_colors[:len(data)]):
        pie.slices[i].fillColor = col

    drawing.add(pie)

    # Legenda externa
    legend = Legend()
    legend.x = 280
    legend.y = 100
    legend.columnMaximum = 1
    legend.boxAnchor = 'w'
    legend.colorNamePairs = [(premium_colors[i], f"{labels[i]} ({data[i]:,.0f})") for i in range(len(data))]
    legend.fontName = 'Helvetica'
    legend.fontSize = 10
    legend.strokeWidth = 0
    drawing.add(legend)

    # Título
    title_str = String(250, 320, title, fontName="Helvetica-Bold", fontSize=14, fillColor=AZUL_ESCURO, textAnchor="middle")
    drawing.add(title_str)

    return drawing

def create_kpi_card(title, value, subtitle, bg_color, trend=None):
    data = f"""
    <font name="Helvetica-Bold" size="18" color="white">{value:,.2f}</font><br/>
    <font name="Helvetica" size="10" color="#E0E7FF">{title}</font><br/>
    <font name="Helvetica" size="9" color="#CDD6F5">{subtitle}</font>
    """
    if trend is not None:
        arrow = "↑" if trend > 0 else "↓"
        color_trend = VERDE if trend > 0 else VERMELHO
        data += f'<font name="Helvetica-Bold" size="9" color="{color_trend.toHex()}"> {arrow} {abs(trend):.1f}%</font>'

    p = Paragraph(data, ParagraphStyle('kpi', fontName='Helvetica', alignment=TA_CENTER))
    card = Table([[p]], colWidths=80*mm, rowHeights=45*mm)
    card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('ROUNDEDCORNERS', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FFFFFF22")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    return card

def generate_professional_pdf(context_data, filename="maestrofin_relatorio.pdf"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=3.5*cm, bottomMargin=2.5*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )

    elements = []

    # === CAPA PREMIUM ===
    capa_title = Paragraph("RELATÓRIO EXECUTIVO<br/>FINANCEIRO", styles['TitleMain'])
    capa_sub = Paragraph(
        f"<b>Período:</b> {context_data.get('periodo_inicio', '')} até {context_data.get('periodo_fim', '')}<br/>"
        f"<b>Gerado em:</b> {datetime.now().strftime('%d de %B de %Y')}",
        styles['Subtitle']
    )
    elements.extend([Spacer(1, 60), capa_title, Spacer(1, 20), capa_sub, PageBreak()])

    # === RESUMO EXECUTIVO ===
    elements.append(Paragraph("RESUMO EXECUTIVO", styles['SectionTitle']))

    receita = context_data.get('total_receitas', 0)
    despesa = context_data.get('total_gastos', 0)
    saldo = context_data.get('saldo_periodo', 0)

    kpis = [
        [create_kpi_card("RECEITAS", receita, "Total no período", colors.HexColor("#10B981"), +8.4),
         create_kpi_card("DESPESAS", despesa, "Total no período", colors.HexColor("#EF4444"), -3.2)],
        [create_kpi_card("SALDO LÍQUIDO", saldo, "Resultado do mês", AZUL_PRINCIPAL),
         create_kpi_card("CAPACIDADE DE POUPANÇA", max(saldo, 0), "Disponível para investir", ROXO)]
    ]
    kpi_table = Table(kpis, colWidths=[90*mm, 90*mm])
    kpi_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 30))

    # === GRÁFICO DE GASTOS ===
    if context_data.get('gastos_por_categoria'):
        cats = context_data['gastos_por_categoria'][:8]
        valores = [c['total'] for c in cats]
        nomes = [c['nome'] for c in cats]
        elements.append(Paragraph("DISTRIBUIÇÃO DE GASTOS", styles['SectionTitle']))
        elements.append(create_premium_pie(valores, nomes, "Gastos por Categoria"))
        elements.append(Spacer(1, 30))

    # === DETALHAMENTO POR CATEGORIA ===
    elements.append(Paragraph("DETALHAMENTO POR CATEGORIA", styles['SectionTitle']))
    cat_data = [['Categoria', 'Valor', '% do Total', 'Status']]
    for c in context_data.get('gastos_por_categoria', [])[:10]:
        perc = c.get('percentual', 0)
        status = "Alto" if perc > 30 else "Médio" if perc > 15 else "Controlado"
        color_status = VERMELHO if perc > 30 else AMARELO if perc > 15 else VERDE
        cat_data.append([
            c.get('nome', 'N/A'),
            f"R$ {c.get('total', 0):,.2f}",
            f"{perc:.1f}%",
            Paragraph(f"<font color='{color_status.toHex()}'><b>{status}</b></font>", styles['NormalCenter'])
        ])

    cat_table = Table(cat_data, colWidths=[80*mm, 40*mm, 30*mm, 40*mm])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), AZUL_ESCURO),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,1), (0,-1), 10),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 30))

    # === INSIGHTS ===
    elements.append(Paragraph("INSIGHTS & RECOMENDAÇÕES", styles['SectionTitle']))
    insights = context_data.get('insights', [
        "Seus gastos com alimentação dominaram o mês — considere planejar refeições semanais",
        "Você está no caminho certo para formar reserva de emergência",
        "Redução de 12% em gastos supérfluos comparado ao último mês",
        "Sugestão: automatize aportes mensais de R$ 300 em investimentos"
    ])
    for i in insights[:7]:
        elements.append(Paragraph(f"• {i}", styles['Insight']))
    elements.append(Spacer(1, 40))

    # === FINAL ===
    final_msg = Paragraph(
        "Continue no controle com o MaestroFin!<br/>"
        "Acompanhe diariamente pelo Telegram: <b>@maestrofin_bot</b>",
        ParagraphStyle('Final', fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER, textColor=AZUL_PRINCIPAL, spaceBefore=50)
    )
    elements.append(final_msg)

    # Build
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return buffer.getvalue()


# ====================== TESTE ======================
if __name__ == "__main__":
    test_data = {
        'periodo_inicio': '01/11/2025',
        'periodo_fim': '30/11/2025',
        'total_receitas': 8420.00,
        'total_gastos': 5870.50,
        'saldo_periodo': 2549.50,
        'gastos_por_categoria': [
            {'nome': 'Alimentação', 'total': 1890.00, 'percentual': 32.2},
            {'nome': 'Transporte', 'total': 980.00, 'percentual': 16.7},
            {'nome': 'Moradia', 'total': 1500.00, 'percentual': 25.6},
            {'nome': 'Lazer', 'total': 620.00, 'percentual': 10.6},
            {'nome': 'Saúde', 'total': 380.00, 'percentual': 6.5},
        ],
        'insights': [
            "Você economizou R$ 420 em relação ao mês anterior!",
            "Alimentação ainda é o maior vilão — que tal meal prep aos domingos?",
            "Seu saldo permite iniciar um investimento de R$ 1.000 este mês",
            "Parabéns por manter 23 dias no verde!"
        ]
    }

    pdf = generate_professional_pdf(test_data)
    with open("MaestroFin_Relatorio_Profissional.pdf", "wb") as f:
        f.write(pdf)
    print("PDF PROFISSIONAL GERADO: MaestroFin_Relatorio_Profissional.pdf")