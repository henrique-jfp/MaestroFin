# gerente_financeiro/pdf_generator.py

import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Group, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

# --- CONFIGURAÇÃO DE CORES PREMIUM (Paleta Private Bank) ---
COLOR_PRIMARY = HexColor('#0F172A')    # Navy Blue Profundo
COLOR_ACCENT = HexColor('#F59E0B')     # Gold/Amber
COLOR_BG_LIGHT = HexColor('#F8FAFC')   # Slate 50
COLOR_TEXT_MAIN = HexColor('#1E293B')  # Slate 800
COLOR_TEXT_LIGHT = HexColor('#64748B') # Slate 500
COLOR_SUCCESS = HexColor('#10B981')    # Emerald
COLOR_DANGER = HexColor('#EF4444')     # Red
COLOR_WHITE = colors.white

# --- REGISTRO DE FONTES ---
def register_fonts():
    """Tenta registrar fontes premium (Inter), fallback para Helvetica"""
    font_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts')
    try:
        pdfmetrics.registerFont(TTFont('Inter-Bold', os.path.join(font_dir, 'Inter-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('Inter-Regular', os.path.join(font_dir, 'Inter-Regular.ttf')))
        return 'Inter-Regular', 'Inter-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'

FONT_REG, FONT_BOLD = register_fonts()

class GradientCover(Flowable):
    """Gera a capa com gradiente e tipografia impactante"""
    def __init__(self, width, height, user_name, period_str):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.user_name = user_name
        self.period_str = period_str

    def draw(self):
        c = self.canv
        
        # Fundo Gradiente (Simulado com linhas para compatibilidade)
        # Na prática, um rect sólido escuro fica mais elegante em PDFs gerados via código
        c.setFillColor(COLOR_PRIMARY)
        c.rect(0, 0, self.width, self.height, fill=True, stroke=False)
        
        # Elemento Decorativo (Círculo Dourado)
        c.setFillColor(COLOR_ACCENT)
        c.setFillAlpha(0.1)
        c.circle(self.width, self.height, 300, fill=True, stroke=False)
        c.setFillAlpha(1)

        # Logo / Nome do Bot
        c.setFillColor(COLOR_WHITE)
        c.setFont(FONT_BOLD, 14)
        c.drawString(20*mm, self.height - 30*mm, "MAESTROFIN PRIVATE")
        
        # Título Gigante
        c.setFont(FONT_BOLD, 42)
        c.drawString(20*mm, self.height - 80*mm, "Relatório")
        c.drawString(20*mm, self.height - 95*mm, "Financeiro")
        
        # Linha divisória
        c.setStrokeColor(COLOR_ACCENT)
        c.setLineWidth(2)
        c.line(20*mm, self.height - 110*mm, 60*mm, self.height - 110*mm)
        
        # Período
        c.setFont(FONT_REG, 16)
        c.setFillColor(colors.white)
        c.drawString(20*mm, self.height - 125*mm, self.period_str)
        
        # Badge do Usuário
        c.setFillColor(HexColor('#1E293B')) # Lighter blue
        c.roundRect(20*mm, self.height - 160*mm, 120*mm, 14*mm, 7*mm, fill=True, stroke=False)
        c.setFillColor(COLOR_ACCENT)
        c.setFont(FONT_BOLD, 10)
        c.drawString(25*mm, self.height - 156*mm, "PREPARADO EXCLUSIVAMENTE PARA")
        c.setFillColor(COLOR_WHITE)
        c.setFont(FONT_BOLD, 14)
        c.drawString(25*mm, self.height - 151*mm, self.user_name.upper())

class KPICard(Flowable):
    """Card de KPI estilo Banco"""
    def __init__(self, title, value, subtitle, trend="neutral", width=80*mm, height=40*mm):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.trend = trend

    def draw(self):
        c = self.canv
        x, y = 0, 0
        
        # Sombra (Simulada)
        c.setFillColor(colors.Color(0,0,0,0.1))
        c.roundRect(x+2, y-2, self.width, self.height, 6, fill=True, stroke=False)
        
        # Fundo Card
        c.setFillColor(COLOR_WHITE)
        c.setStrokeColor(HexColor('#E2E8F0'))
        c.roundRect(x, y, self.width, self.height, 6, fill=True, stroke=True)
        
        # Título
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.setFont(FONT_REG, 9)
        c.drawString(x + 5*mm, y + self.height - 8*mm, self.title.upper())
        
        # Valor
        c.setFillColor(COLOR_PRIMARY)
        c.setFont(FONT_BOLD, 18)
        c.drawString(x + 5*mm, y + self.height - 18*mm, self.value)
        
        # Subtítulo / Trend
        c.setFont(FONT_REG, 8)
        if self.trend == "up":
            c.setFillColor(COLOR_SUCCESS)
            icon = "▲"
        elif self.trend == "down":
            c.setFillColor(COLOR_DANGER)
            icon = "▼"
        else:
            c.setFillColor(COLOR_TEXT_LIGHT)
            icon = "•"
            
        c.drawString(x + 5*mm, y + 5*mm, f"{icon} {self.subtitle}")

def create_header_footer(canvas, doc):
    """Desenha cabeçalho e rodapé em todas as páginas exceto capa"""
    canvas.saveState()
    
    # Rodapé
    canvas.setFont(FONT_REG, 8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawString(20*mm, 10*mm, "MaestroFin • Relatório Confidencial")
    canvas.drawRightString(A4[0] - 20*mm, 10*mm, f"Página {doc.page}")
    
    # Linha decorativa rodapé
    canvas.setStrokeColor(COLOR_ACCENT)
    canvas.setLineWidth(1)
    canvas.line(20*mm, 14*mm, A4[0]-20*mm, 14*mm)
    
    canvas.restoreState()

def generate_financial_pdf(context):
    """Função principal de geração"""
    buffer = io.BytesIO()
    
    # Margens estilo editorial
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos Customizados
    style_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName=FONT_BOLD, fontSize=16, textColor=COLOR_PRIMARY, spaceAfter=10, spaceBefore=20)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName=FONT_REG, fontSize=10, textColor=COLOR_TEXT_MAIN, leading=14)
    style_insight = ParagraphStyle('Insight', parent=styles['Normal'], fontName=FONT_REG, fontSize=10, textColor=HexColor('#065F46'), backColor=HexColor('#ECFDF5'), padding=10, borderColor=HexColor('#10B981'), borderWidth=0.5, borderRadius=5, spaceAfter=5)

    # --- 1. CAPA ---
    # Remove margens para a capa preencher tudo
    elements.append(GradientCover(
        width=A4[0], 
        height=A4[1], 
        user_name=context.get('usuario_nome', 'Investidor'),
        period_str=context.get('periodo_extenso', 'Mês Atual')
    ))
    elements.append(PageBreak())

    # --- 2. RESUMO EXECUTIVO (KPIs) ---
    elements.append(Paragraph("Resumo Executivo", style_h2))
    elements.append(Spacer(1, 5*mm))
    
    # Preparar dados dos cards
    rec = context.get('receita_total', 0)
    desp = context.get('despesa_total', 0)
    saldo = context.get('saldo_mes', 0)
    poup = context.get('taxa_poupanca', 0)
    
    # Grid 2x2 de Cards
    card_w = 82*mm
    card_h = 35*mm
    
    kpi_data = [
        [
            KPICard("Receitas", f"R$ {rec:,.2f}", "Entradas confirmadas", "up", card_w, card_h),
            KPICard("Despesas", f"R$ {desp:,.2f}", "Saídas totais", "down", card_w, card_h)
        ],
        [
            KPICard("Saldo Líquido", f"R$ {saldo:,.2f}", "Disponível em caixa", "neutral", card_w, card_h),
            KPICard("Taxa de Poupança", f"{poup:.1f}%", "Meta: 20%", "up" if poup > 20 else "down", card_w, card_h)
        ]
    ]
    
    t_kpi = Table(kpi_data, colWidths=[85*mm, 85*mm], rowHeights=[40*mm, 40*mm])
    t_kpi.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t_kpi)
    
    elements.append(Spacer(1, 10*mm))

    # --- 3. GRÁFICO E CATEGORIAS ---
    elements.append(Paragraph("Distribuição de Gastos", style_h2))
    
    # Gráfico de Pizza (ReportLab nativo para qualidade vetorial)
    d = Drawing(400, 200)
    pc = Pie()
    pc.x = 100
    pc.y = 25
    pc.width = 150
    pc.height = 150
    
    # Dados do gráfico
    cats = context.get('gastos_agrupados', [])[:6] # Top 6
    if cats:
        pc.data = [x[1] for x in cats]
        pc.labels = [f"{x[0]}" for x in cats]
        # Cores Premium
        pc.slices.strokeWidth = 0.5
        pc.slices.strokeColor = colors.white
        colors_list = [COLOR_PRIMARY, COLOR_ACCENT, COLOR_SUCCESS, COLOR_DANGER, HexColor('#6366F1'), HexColor('#8B5CF6')]
        for i, color in enumerate(colors_list):
            if i < len(pc.data):
                pc.slices[i].fillColor = color
    else:
        pc.data = [1]
        pc.labels = ["Sem dados"]

    d.add(pc)
    elements.append(d)
    
    # Tabela de Categorias
    elements.append(Spacer(1, 5*mm))
    
    table_data = [['Categoria', 'Valor', '% Total']]
    for cat, val in cats:
        perc = (val / desp * 100) if desp > 0 else 0
        table_data.append([cat, f"R$ {val:,.2f}", f"{perc:.1f}%"])
        
    t_cat = Table(table_data, colWidths=[90*mm, 40*mm, 30*mm])
    t_cat.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), FONT_BOLD),
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), COLOR_WHITE),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), FONT_REG),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [COLOR_BG_LIGHT, COLOR_WHITE]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#E2E8F0')),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]), # Se suportado pela versão, senão ignora
    ]))
    elements.append(t_cat)
    
    elements.append(PageBreak())

    # --- 4. INSIGHTS E RECOMENDAÇÕES ---
    elements.append(Paragraph("Insights Inteligentes", style_h2))
    
    insights = context.get('insights', [])
    if not insights:
        insights = [
            "Mantenha seus gastos essenciais abaixo de 50% da receita.",
            "Tente aumentar sua taxa de poupança em 1% no próximo mês.",
            "Revise assinaturas mensais que não está utilizando."
        ]
        
    for insight in insights:
        # Adiciona ícone de lâmpada (texto unicode)
        text = f"💡 {insight}"
        elements.append(Paragraph(text, style_insight))
        elements.append(Spacer(1, 2*mm))

    # --- 5. TOP TRANSAÇÕES ---
    elements.append(Paragraph("Maiores Movimentações", style_h2))
    
    top_transacoes = context.get('top_transacoes', [])
    if top_transacoes:
        t_data = [['Data', 'Descrição', 'Valor']]
        for t in top_transacoes:
            # Formatação segura
            val_fmt = f"R$ {float(t.get('valor', 0)):,.2f}"
            data_fmt = t.get('data', '').strftime('%d/%m') if hasattr(t.get('data'), 'strftime') else str(t.get('data'))[:5]
            t_data.append([data_fmt, t.get('descricao', 'N/A')[:30], val_fmt])
            
        t_top = Table(t_data, colWidths=[30*mm, 90*mm, 40*mm])
        t_top.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), FONT_BOLD),
            ('TEXTCOLOR', (0,0), (-1,0), COLOR_PRIMARY),
            ('LINEBELOW', (0,0), (-1,0), 1, COLOR_ACCENT),
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [COLOR_WHITE, COLOR_BG_LIGHT]),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        elements.append(t_top)
    else:
        elements.append(Paragraph("Nenhuma transação relevante encontrada.", style_normal))

    # --- 6. CALL TO ACTION FINAL ---
    elements.append(Spacer(1, 20*mm))
    
    # Caixa de conclusão
    elements.append(Paragraph("Próximos Passos", style_h2))
    elements.append(Paragraph("Para detalhar estes lançamentos ou criar novas metas de economia, acesse o menu principal do bot.", style_normal))
    
    # Build
    doc.build(elements, onFirstPage=lambda c, d: None, onLaterPages=create_header_footer)
    
    buffer.seek(0)
    return buffer.getvalue()