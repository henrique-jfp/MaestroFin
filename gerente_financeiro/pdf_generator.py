#!/usr/bin/env python3
"""
MAESTROFIN PRO - Gerador de Relatórios Financeiros Premium
Design: Modern Dashboard Style
Author: AI Assistant
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing, Rect, String, Group, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.legends import Legend
from reportlab.lib.colors import HexColor

# --- CONFIGURAÇÃO DE DESIGN SYSTEM ---
class Theme:
    # Cores Principais
    PRIMARY = HexColor('#0F172A')    # Midnight Blue
    ACCENT = HexColor('#3B82F6')     # Bright Blue
    SECONDARY = HexColor('#64748B')  # Slate
    
    # Cores de Status
    SUCCESS = HexColor('#10B981')    # Emerald
    DANGER = HexColor('#EF4444')     # Red
    WARNING = HexColor('#F59E0B')    # Amber
    
    # Cores de Fundo/Texto
    BG_LIGHT = HexColor('#F8FAFC')
    TEXT_MAIN = HexColor('#1E293B')
    TEXT_LIGHT = HexColor('#94A3B8')
    WHITE = HexColor('#FFFFFF')

    # Fontes
    FONT_BOLD = 'Helvetica-Bold'
    FONT_REG = 'Helvetica'

def format_currency(value):
    """Formata moeda para o padrão brasileiro"""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- ELEMENTOS GRÁFICOS PERSONALIZADOS ---

def create_header(canvas, doc):
    """Cabeçalho Premium Minimalista"""
    canvas.saveState()
    w, h = A4
    
    # Barra lateral decorativa
    canvas.setFillColor(Theme.ACCENT)
    canvas.rect(0, h - 3.5*cm, 0.8*cm, 3.5*cm, fill=1, stroke=0)
    
    # Logo Simulado (Círculo com M)
    canvas.setFillColor(Theme.PRIMARY)
    canvas.circle(2.5*cm, h - 1.8*cm, 0.6*cm, fill=1, stroke=0)
    canvas.setFillColor(Theme.WHITE)
    canvas.setFont(Theme.FONT_BOLD, 20)
    canvas.drawCentredString(2.5*cm, h - 2.0*cm, "M")
    
    # Título da Empresa
    canvas.setFillColor(Theme.PRIMARY)
    canvas.setFont(Theme.FONT_BOLD, 22)
    canvas.drawString(3.5*cm, h - 1.8*cm, "MAESTROFIN")
    
    # Subtítulo
    canvas.setFillColor(Theme.SECONDARY)
    canvas.setFont(Theme.FONT_REG, 9)
    canvas.drawString(3.5*cm, h - 2.3*cm, "INTELLIGENT FINANCIAL SOLUTIONS")
    
    # Data e Info no canto direito
    canvas.setFillColor(Theme.TEXT_MAIN)
    canvas.setFont(Theme.FONT_BOLD, 10)
    canvas.drawRightString(w - 1.5*cm, h - 1.8*cm, "RELATÓRIO EXECUTIVO")
    
    canvas.setFillColor(Theme.SECONDARY)
    canvas.setFont(Theme.FONT_REG, 8)
    data_atual = datetime.now().strftime('%d/%m/%Y')
    canvas.drawRightString(w - 1.5*cm, h - 2.2*cm, f"Data de Emissão: {data_atual}")
    
    # Linha divisória sutil
    canvas.setStrokeColor(HexColor('#E2E8F0'))
    canvas.line(1*cm, h - 3.5*cm, w - 1*cm, h - 3.5*cm)
    
    canvas.restoreState()

def create_footer(canvas, doc):
    """Rodapé Limpo com Numeração"""
    canvas.saveState()
    w, h = A4
    
    # Linha fina
    canvas.setStrokeColor(HexColor('#E2E8F0'))
    canvas.line(1*cm, 1.5*cm, w - 1*cm, 1.5*cm)
    
    # Texto legal
    canvas.setFillColor(Theme.TEXT_LIGHT)
    canvas.setFont(Theme.FONT_REG, 7)
    canvas.drawString(1*cm, 1*cm, "Documento confidencial gerado pelo MaestroFin Bot.")
    canvas.drawString(1*cm, 0.7*cm, "© 2025 MaestroFin. Todos os direitos reservados.")
    
    # Paginação estilizada
    page = f"{doc.page}"
    canvas.setFillColor(Theme.PRIMARY)
    canvas.setFont(Theme.FONT_BOLD, 9)
    canvas.drawRightString(w - 1*cm, 1*cm, page)
    
    canvas.restoreState()

def draw_kpi_card(label, value, subtext, color_theme, width=4.5*cm, height=2.8*cm):
    """Desenha um Card KPI vetorial moderno com cantos arredondados"""
    d = Drawing(width, height)
    
    # Fundo com borda arredondada (simulada) e sombra leve
    # Sombra
    shadow = Rect(2, -2, width-4, height-4, rx=8, ry=8)
    shadow.fillColor = HexColor('#E2E8F0')
    shadow.strokeColor = None
    d.add(shadow)
    
    # Card Principal
    bg = Rect(0, 0, width, height, rx=8, ry=8)
    bg.fillColor = Theme.WHITE
    bg.strokeColor = HexColor('#E2E8F0')
    bg.strokeWidth = 1
    d.add(bg)
    
    # Barra lateral colorida indicando categoria
    bar = Rect(0, 0, 4, height, rx=2, ry=2) # Lado esquerdo curvo
    # Hack para "clipar" o lado esquerdo: apenas desenha uma linha grossa vertical
    line = Line(2, 4, 2, height-4)
    line.strokeColor = color_theme
    line.strokeWidth = 4
    d.add(line)
    
    # Texto Label (Upper, pequeno)
    lbl = String(15, height-20, label.upper())
    lbl.fontName = Theme.FONT_BOLD
    lbl.fontSize = 7
    lbl.fillColor = Theme.SECONDARY
    d.add(lbl)
    
    # Valor Principal
    val = String(15, height-45, value)
    val.fontName = Theme.FONT_BOLD
    val.fontSize = 13
    val.fillColor = Theme.PRIMARY
    d.add(val)
    
    # Subtexto (ex: tendência)
    sub = String(15, 10, subtext)
    sub.fontName = Theme.FONT_REG
    sub.fontSize = 6
    sub.fillColor = color_theme if "↗" in subtext or "↘" in subtext else Theme.TEXT_LIGHT
    d.add(sub)
    
    return d

def draw_donut_chart(data, labels, title=""):
    """Cria um Donut Chart elegante com legenda lateral"""
    width = 16*cm
    height = 7*cm
    d = Drawing(width, height)
    
    # Cores profissionais
    chart_colors = [
        HexColor('#3B82F6'), HexColor('#10B981'), HexColor('#F59E0B'), 
        HexColor('#EF4444'), HexColor('#8B5CF6'), HexColor('#EC4899')
    ]
    
    # Gráfico Pie (Donut)
    pie = Pie()
    pie.x = 0.5*cm
    pie.y = 0.5*cm
    pie.width = 6*cm
    pie.height = 6*cm
    pie.data = data
    pie.labels = None  # Labels na legenda, não no gráfico
    pie.simpleLabels = 0
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = Theme.WHITE
    pie.innerRadiusFraction = 0.6 # Transforma pizza em donut
    
    for i, col in enumerate(chart_colors):
        if i < len(pie.data):
            pie.slices[i].fillColor = col
            
    d.add(pie)
    
    # Texto Central no Donut (Total ou Label)
    center_text = String(3.5*cm, 3.5*cm, "TOTAL")
    center_text.fontName = Theme.FONT_BOLD
    center_text.fontSize = 8
    center_text.fillColor = Theme.SECONDARY
    center_text.textAnchor = 'middle'
    d.add(center_text)
    
    # Legenda
    legend = Legend()
    legend.x = 7.5*cm
    legend.y = 5.5*cm
    legend.dx = 8
    legend.dy = 8
    legend.fontName = Theme.FONT_REG
    legend.fontSize = 9
    legend.boxAnchor = 'nw'
    legend.columnMaximum = 8
    legend.strokeWidth = 0
    legend.strokeColor = None
    legend.alignment = 'right'
    
    # Preparar cores e textos da legenda
    legend_colors = chart_colors[:len(data)]
    legend_labels = labels
    
    legend.colorNamePairs = list(zip(legend_colors, legend_labels))
    d.add(legend)
    
    return d

# --- GERADOR PRINCIPAL ---

def generate_financial_pdf(context_data):
    buffer = io.BytesIO()
    
    # Margens configuradas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=4.0*cm, # Espaço para header
        bottomMargin=2.5*cm,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos Personalizados
    style_h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontName=Theme.FONT_BOLD, fontSize=14, textColor=Theme.PRIMARY, spaceAfter=15, spaceBefore=20)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName=Theme.FONT_REG, fontSize=9, textColor=Theme.TEXT_MAIN, leading=14)
    style_period = ParagraphStyle('Period', parent=styles['Normal'], fontName=Theme.FONT_BOLD, fontSize=10, textColor=Theme.SECONDARY, alignment=TA_RIGHT)

    elements = []
    
    # --- 1. BARRA DE INFORMAÇÕES DO PERÍODO ---
    p_inicio = context_data.get('periodo_inicio', '-')
    p_fim = context_data.get('periodo_fim', '-')
    elements.append(Paragraph(f"PERÍODO ANALISADO: {p_inicio} — {p_fim}", style_period))
    elements.append(Spacer(1, 15))
    
    # --- 2. GRID DE KPIS (Dashboard Top) ---
    rec = context_data.get('total_receitas', 0)
    desp = context_data.get('total_gastos', 0)
    saldo = context_data.get('saldo_periodo', 0)
    poupanca = rec - desp
    
    # Desenhar cards
    kpi1 = draw_kpi_card("Receitas Totais", format_currency(rec), "Entradas consolidadas", Theme.SUCCESS)
    kpi2 = draw_kpi_card("Despesas", format_currency(desp), "Saídas operacionais", Theme.DANGER)
    kpi3 = draw_kpi_card("Resultado Líquido", format_currency(saldo), "Saldo final do período", Theme.ACCENT)
    
    # Determinar texto de tendência (mockado para exemplo)
    rate_poupanca = (poupanca / rec * 100) if rec > 0 else 0
    kpi4 = draw_kpi_card("Margem Econ.", f"{rate_poupanca:.1f}%", "Taxa de poupança", Theme.WARNING)
    
    # Tabela Container para os KPIs (1 linha, 4 colunas)
    kpi_table = Table([[kpi1, kpi2, kpi3, kpi4]], colWidths=[4.6*cm]*4)
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 30))
    
    # --- 3. ANÁLISE GRÁFICA E TABULAR (Split View) ---
    elements.append(Paragraph("ANÁLISE DE COMPOSIÇÃO DE GASTOS", style_h1))
    
    # Preparar dados
    cats = context_data.get('gastos_por_categoria', [])
    top_cats = cats[:5] # Top 5 para o gráfico
    
    # Dados Gráfico
    chart_vals = [c.get('total', 0) for c in top_cats]
    chart_labels = [f"{c.get('nome')[:12]} ({c.get('percentual',0):.0f}%)" for c in top_cats]
    donut = draw_donut_chart(chart_vals, chart_labels)
    
    # Dados Tabela (Lista completa compacta)
    tbl_data = [['CATEGORIA', 'VALOR', '%']]
    for c in cats[:8]: # Listar até 8
        tbl_data.append([
            c.get('nome', ''),
            format_currency(c.get('total', 0)),
            f"{c.get('percentual', 0):.1f}%"
        ])
    
    # Estilizar Tabela Lateral
    cat_table = Table(tbl_data, colWidths=[3.5*cm, 2.5*cm, 1.5*cm])
    cat_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), Theme.FONT_BOLD),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('TEXTCOLOR', (0,0), (-1,0), Theme.SECONDARY),
        ('LINEBELOW', (0,0), (-1,0), 1, Theme.ACCENT), # Linha abaixo do header
        
        ('FONTNAME', (0,1), (-1,-1), Theme.FONT_REG),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('TEXTCOLOR', (0,1), (-1,-1), Theme.TEXT_MAIN),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'), # Numeros alinhados direita
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [Theme.WHITE, Theme.BG_LIGHT]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    
    # Layout Mestre: Gráfico à Esquerda, Tabela à Direita
    master_table = Table([[donut, cat_table]], colWidths=[9.5*cm, 8.5*cm])
    master_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'LEFT'), # Gráfico na esquerda
        ('ALIGN', (1,0), (1,0), 'RIGHT'), # Tabela na direita
    ]))
    elements.append(master_table)
    elements.append(Spacer(1, 20))
    
    # --- 4. DETALHAMENTO DE TRANSAÇÕES (Top Gastos) ---
    if context_data.get('top_gastos'):
        elements.append(Paragraph("PRINCIPAIS MOVIMENTAÇÕES (TOP 5)", style_h1))
        
        trans_data = [['DATA', 'DESCRIÇÃO', 'CATEGORIA', 'VALOR']]
        for t in context_data['top_gastos'][:5]:
            d_fmt = t.get('data', '')[:10]
            # Formatar data de YYYY-MM-DD para DD/MM se necessário
            try:
                d_obj = datetime.strptime(d_fmt, '%Y-%m-%d')
                d_fmt = d_obj.strftime('%d/%m/%Y')
            except:
                pass
                
            trans_data.append([
                d_fmt,
                t.get('descricao', '')[:35].title(),
                t.get('categoria', '').upper(),
                format_currency(t.get('valor', 0))
            ])
            
        t_table = Table(trans_data, colWidths=[2.5*cm, 8*cm, 4*cm, 3.5*cm])
        t_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0,0), (-1,0), Theme.PRIMARY),
            ('TEXTCOLOR', (0,0), (-1,0), Theme.WHITE),
            ('FONTNAME', (0,0), (-1,0), Theme.FONT_BOLD),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            
            # Body
            ('FONTNAME', (0,1), (-1,-1), Theme.FONT_REG),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('TEXTCOLOR', (0,1), (-1,-1), Theme.TEXT_MAIN),
            ('ALIGN', (-1,1), (-1,-1), 'RIGHT'), # Valor direita
            ('LINEBELOW', (0,1), (-1,-2), 0.5, HexColor('#E2E8F0')), # Linhas sutis entre rows
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [Theme.WHITE]), # Fundo branco limpo
            ('BOTTOMPADDING', (0,1), (-1,-1), 8),
            ('TOPPADDING', (0,1), (-1,-1), 8),
        ]))
        elements.append(t_table)
        
    elements.append(Spacer(1, 25))

    # --- 5. INSIGHTS (Caixa de Destaque) ---
    if context_data.get('insights'):
        # Estilo para caixa de insight
        elements.append(Paragraph("INSIGHTS DO CONSULTOR", style_h1))
        
        insight_style = ParagraphStyle(
            'Insight', 
            parent=styles['Normal'],
            fontSize=10, 
            textColor=Theme.TEXT_MAIN,
            backColor=HexColor('#F0FDF4'), # Verde bem claro
            borderColor=Theme.SUCCESS,
            borderWidth=0,
            borderPadding=10,
            spaceAfter=5,
            leading=14,
            leftIndent=5
        )
        
        for txt in context_data['insights'][:3]:
            # Adicionar ícone de lâmpada via caractere
            p = Paragraph(f"<font color='#10B981'><b>💡 DICA:</b></font> {txt}", insight_style)
            elements.append(p)
            elements.append(Spacer(1, 5))

    # Build
    doc.build(elements, onFirstPage=create_header, onLaterPages=create_header, canvasmaker=PageFooterCanvas)
    
    buffer.seek(0)
    return buffer.getvalue()

# Classe auxiliar para rodapé em todas as páginas
from reportlab.pdfgen import canvas
class PageFooterCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            create_footer(self, None) # Chama o footer manual
            self._code.append('QP') # Encerra pagina
        canvas.Canvas.save(self)

    def _startPage(self):
        self._code.append('q') # Salva estado
        canvas.Canvas._startPage(self)

# --- EXECUÇÃO DE TESTE ---
if __name__ == "__main__":
    # Dados Mockados
    data_mock = {
        'periodo_inicio': '01/01/2025',
        'periodo_fim': '31/01/2025',
        'total_receitas': 15450.00,
        'total_gastos': 8320.50,
        'saldo_periodo': 7129.50,
        'gastos_por_categoria': [
            {'nome': 'Habitação', 'total': 3200.00, 'percentual': 38.4},
            {'nome': 'Alimentação', 'total': 1800.00, 'percentual': 21.6},
            {'nome': 'Transporte', 'total': 950.00, 'percentual': 11.4},
            {'nome': 'Lazer & Hobbies', 'total': 850.00, 'percentual': 10.2},
            {'nome': 'Saúde', 'total': 600.00, 'percentual': 7.2},
            {'nome': 'Educação', 'total': 500.00, 'percentual': 6.0},
            {'nome': 'Outros', 'total': 420.50, 'percentual': 5.2},
        ],
        'top_gastos': [
            {'data': '2025-01-05', 'descricao': 'Aluguel Residencial', 'categoria': 'Habitação', 'valor': 2500.00},
            {'data': '2025-01-12', 'descricao': 'Supermercado Carrefour', 'categoria': 'Alimentação', 'valor': 850.20},
            {'data': '2025-01-15', 'descricao': 'Seguro Automóvel', 'categoria': 'Transporte', 'valor': 450.00},
            {'data': '2025-01-20', 'descricao': 'Jantar Comemorativo', 'categoria': 'Lazer', 'valor': 320.00},
            {'data': '2025-01-22', 'descricao': 'Farmácia Pague Menos', 'categoria': 'Saúde', 'valor': 125.90},
        ],
        'insights': [
            "Sua despesa com Habitação está 5% acima da média recomendada.",
            "Excelente taxa de poupança este mês (46%). Considere investir o excedente.",
            "Gastos variáveis reduziram em relação ao mês anterior."
        ]
    }

    pdf_bytes = generate_financial_pdf(data_mock)
    with open("MaestroFin_Relatorio_Premium.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("✅ Relatório Premium gerado com sucesso!")