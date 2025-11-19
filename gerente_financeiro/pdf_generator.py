#!/usr/bin/env python3
"""
Gerador de PDF Premium para Relatórios Financeiros
MaestroFin - Relatório Executivo Financeiro v2.0
Melhorias: Design moderno, gradientes, gráficos aprimorados, layout responsivo
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

# ===========================
# CONFIGURAÇÕES DE CORES
# ===========================
COLORS = {
    'primary': HexColor('#0f172a'),      # Azul escuro profundo
    'secondary': HexColor('#3b82f6'),    # Azul moderno
    'accent': HexColor('#f59e0b'),       # Âmbar/Dourado
    'success': HexColor('#10b981'),      # Verde
    'danger': HexColor('#ef4444'),       # Vermelho
    'warning': HexColor('#f59e0b'),      # Laranja
    'purple': HexColor('#8b5cf6'),       # Roxo
    'teal': HexColor('#14b8a6'),         # Turquesa
    'text_dark': HexColor('#1f2937'),    # Texto escuro
    'text_light': HexColor('#6b7280'),   # Texto claro
    'bg_light': HexColor('#f9fafb'),     # Fundo claro
    'bg_white': HexColor('#ffffff'),     # Branco
    'border': HexColor('#e5e7eb'),       # Borda
}

# ===========================
# CABEÇALHO E RODAPÉ
# ===========================
def create_modern_header(canvas_obj, doc):
    """Cabeçalho premium com design gradiente"""
    canvas_obj.saveState()
    
    # Fundo principal do cabeçalho
    canvas_obj.setFillColor(COLORS['primary'])
    canvas_obj.rect(0, A4[1] - 2.5*cm, A4[0], 2.5*cm, fill=1, stroke=0)
    
    # Linha de destaque superior (gradiente simulado com múltiplas linhas)
    for i in range(5):
        opacity = 1 - (i * 0.15)
        canvas_obj.setStrokeColor(COLORS['accent'])
        canvas_obj.setLineWidth(2 - (i * 0.3))
        canvas_obj.line(0, A4[1] - (0.2 + i*0.05)*cm, A4[0], A4[1] - (0.2 + i*0.05)*cm)
    
    # Logo/Ícone decorativo (círculo)
    canvas_obj.setFillColor(COLORS['accent'])
    canvas_obj.circle(1.5*cm, A4[1] - 1.25*cm, 0.5*cm, fill=1, stroke=0)
    
    # Símbolo dentro do círculo
    canvas_obj.setFillColor(COLORS['primary'])
    canvas_obj.setFont("Helvetica-Bold", 20)
    canvas_obj.drawCentredString(1.5*cm, A4[1] - 1.45*cm, "₿")
    
    # Título principal
    canvas_obj.setFillColor(white)
    canvas_obj.setFont("Helvetica-Bold", 22)
    canvas_obj.drawString(2.5*cm, A4[1] - 1.0*cm, "MAESTROFIN")
    
    # Subtítulo
    canvas_obj.setFillColor(HexColor('#cbd5e1'))
    canvas_obj.setFont("Helvetica", 11)
    canvas_obj.drawString(2.5*cm, A4[1] - 1.5*cm, "Relatório Executivo Financeiro")
    
    # Data e hora
    canvas_obj.setFillColor(HexColor('#94a3b8'))
    canvas_obj.setFont("Helvetica", 9)
    data_texto = datetime.now().strftime('%d/%m/%Y • %H:%M')
    canvas_obj.drawRightString(A4[0] - 1.5*cm, A4[1] - 1.25*cm, data_texto)
    
    canvas_obj.restoreState()

def create_elegant_footer(canvas_obj, doc):
    """Rodapé minimalista e elegante"""
    canvas_obj.saveState()
    
    # Linha superior decorativa
    canvas_obj.setStrokeColor(COLORS['border'])
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(2*cm, 2*cm, A4[0] - 2*cm, 2*cm)
    
    # Círculo decorativo central
    canvas_obj.setFillColor(COLORS['secondary'])
    canvas_obj.circle(A4[0]/2, 2*cm, 0.15*cm, fill=1, stroke=0)
    
    # Informações do rodapé
    canvas_obj.setFillColor(COLORS['text_light'])
    canvas_obj.setFont("Helvetica", 8)
    
    # Esquerda: Copyright
    canvas_obj.drawString(2*cm, 1.3*cm, "© 2025 MaestroFin")
    
    # Centro: Site
    canvas_obj.drawCentredString(A4[0]/2, 1.3*cm, "www.maestrofin.com")
    
    # Direita: Página
    canvas_obj.drawRightString(A4[0] - 2*cm, 1.3*cm, f"Página {doc.page}")
    
    # Slogan
    canvas_obj.setFont("Helvetica-Oblique", 7)
    canvas_obj.setFillColor(HexColor('#9ca3af'))
    canvas_obj.drawCentredString(A4[0]/2, 0.8*cm, "Seu assistente financeiro inteligente")
    
    canvas_obj.restoreState()

# ===========================
# COMPONENTES VISUAIS
# ===========================
def create_premium_kpi_card(title, value, subtitle, color, trend=None, icon=""):
    """KPI Card com design premium e sombras"""
    drawing = Drawing(4.5*cm, 3.5*cm)
    
    # Sombra suave (efeito de profundidade)
    shadow = Rect(0.1*cm, -0.1*cm, 4.5*cm, 3.5*cm, 
                  fillColor=HexColor('#00000015'), 
                  strokeColor=None)
    drawing.add(shadow)
    
    # Card principal com borda arredondada simulada
    main_rect = Rect(0, 0, 4.5*cm, 3.5*cm, 
                     fillColor=color, 
                     strokeColor=HexColor('#ffffff40'),
                     strokeWidth=1)
    drawing.add(main_rect)
    
    # Ornamento superior (linha de destaque)
    accent_line = Rect(0, 3.2*cm, 4.5*cm, 0.3*cm, 
                       fillColor=HexColor('#ffffff20'), 
                       strokeColor=None)
    drawing.add(accent_line)
    
    # Ícone/Emoji
    if icon:
        icon_text = String(0.4*cm, 2.7*cm, icon, 
                          fontSize=16, 
                          fillColor=white, 
                          fontName="Helvetica")
        drawing.add(icon_text)
    
    # Título
    title_text = String(0.4*cm, 2.3*cm, title, 
                       fontSize=9, 
                       fillColor=HexColor('#ffffffcc'), 
                       fontName="Helvetica-Bold")
    drawing.add(title_text)
    
    # Valor principal (formatado)
    if isinstance(value, (int, float)):
        valor_formatado = f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        valor_formatado = str(value)
    
    value_text = String(0.4*cm, 1.4*cm, valor_formatado, 
                       fontSize=15, 
                       fillColor=white, 
                       fontName="Helvetica-Bold")
    drawing.add(value_text)
    
    # Subtítulo
    subtitle_text = String(0.4*cm, 0.9*cm, subtitle, 
                          fontSize=7, 
                          fillColor=HexColor('#ffffffaa'), 
                          fontName="Helvetica")
    drawing.add(subtitle_text)
    
    # Indicador de tendência com estilo
    if trend is not None:
        trend_color = COLORS['success'] if trend >= 0 else COLORS['danger']
        trend_symbol = "▲" if trend >= 0 else "▼"
        trend_text = String(3.8*cm, 0.9*cm, 
                           f"{trend_symbol} {abs(trend):.1f}%", 
                           fontSize=8, 
                           fillColor=trend_color, 
                           fontName="Helvetica-Bold",
                           textAnchor='end')
        drawing.add(trend_text)
    
    return drawing

def create_donut_chart(data, labels, title, colors=None):
    """Gráfico de rosca (donut) moderno"""
    drawing = Drawing(9*cm, 7*cm)
    
    # Gráfico de pizza principal
    pie = Pie()
    pie.x = 2.5*cm
    pie.y = 1.5*cm
    pie.width = 4*cm
    pie.height = 4*cm
    pie.data = data
    pie.labels = None  # Remover labels diretas
    
    # Cores modernas e vibrantes
    if not colors:
        colors = [
            COLORS['secondary'], COLORS['danger'], COLORS['success'], 
            COLORS['warning'], COLORS['purple'], COLORS['teal'],
            HexColor('#ec4899'), HexColor('#06b6d4')
        ]
    
    pie.slices.strokeWidth = 2
    pie.slices.strokeColor = white
    
    for i, color in enumerate(colors[:len(data)]):
        pie.slices[i].fillColor = color
        pie.slices[i].popout = 5 if i == 0 else 0  # Destacar maior fatia
    
    # Criar efeito donut (círculo branco no centro)
    pie.innerRadiusPercent = 50
    
    drawing.add(pie)
    
    # Título com estilo
    title_text = String(4.5*cm, 6.2*cm, title, 
                       fontSize=13, 
                       fillColor=COLORS['text_dark'], 
                       fontName="Helvetica-Bold",
                       textAnchor='middle')
    drawing.add(title_text)
    
    # Legenda customizada
    legend_y = 5.5*cm
    for i, (label, value) in enumerate(zip(labels[:6], data[:6])):  # Máximo 6 itens
        if i >= 3:
            x_pos = 6*cm
            y_pos = legend_y - ((i-3) * 0.6*cm)
        else:
            x_pos = 1*cm
            y_pos = legend_y - (i * 0.6*cm)
        
        # Quadrado de cor
        color_box = Rect(x_pos, y_pos, 0.3*cm, 0.3*cm, 
                        fillColor=colors[i], 
                        strokeColor=None)
        drawing.add(color_box)
        
        # Texto da legenda
        legend_label = String(x_pos + 0.4*cm, y_pos + 0.05*cm, 
                            label[:20], 
                            fontSize=7, 
                            fillColor=COLORS['text_dark'], 
                            fontName="Helvetica")
        drawing.add(legend_label)
    
    return drawing

def create_section_divider(title, icon=""):
    """Divisor de seção com estilo"""
    drawing = Drawing(17*cm, 1*cm)
    
    # Linha esquerda
    left_line = Line(0, 0.5*cm, 3*cm, 0.5*cm)
    left_line.strokeColor = COLORS['secondary']
    left_line.strokeWidth = 2
    drawing.add(left_line)
    
    # Círculo central
    circle = Circle(8.5*cm, 0.5*cm, 0.3*cm, 
                   fillColor=COLORS['secondary'], 
                   strokeColor=None)
    drawing.add(circle)
    
    # Linha direita
    right_line = Line(14*cm, 0.5*cm, 17*cm, 0.5*cm)
    right_line.strokeColor = COLORS['secondary']
    right_line.strokeWidth = 2
    drawing.add(right_line)
    
    # Título centralizado
    title_str = f"{icon} {title}" if icon else title
    title_text = String(8.5*cm, 0.35*cm, title_str, 
                       fontSize=14, 
                       fillColor=COLORS['text_dark'], 
                       fontName="Helvetica-Bold",
                       textAnchor='middle')
    drawing.add(title_text)
    
    return drawing

# ===========================
# FUNÇÃO PRINCIPAL
# ===========================
def generate_financial_pdf(context_data, filename="relatorio_maestrofin.pdf"):
    """
    Gera PDF de relatório financeiro com design premium
    """
    buffer = io.BytesIO()
    
    # Configuração do documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=3.5*cm,
        bottomMargin=2.5*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    
    # ===========================
    # ESTILOS
    # ===========================
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'PremiumTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=COLORS['primary'],
        alignment=TA_CENTER,
        spaceAfter=12,
        spaceBefore=20,
        fontName="Helvetica-Bold",
        leading=34
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName="Helvetica"
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=COLORS['secondary'],
        spaceAfter=20,
        spaceBefore=10,
        fontName="Helvetica-Bold"
    )
    
    normal_text = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLORS['text_dark'],
        spaceAfter=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    insight_style = ParagraphStyle(
        'InsightBullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLORS['success'],
        spaceAfter=8,
        leftIndent=25,
        bulletIndent=10,
        fontName="Helvetica-Bold"
    )
    
    # ===========================
    # ELEMENTOS DO DOCUMENTO
    # ===========================
    elements = []
    
    # === CAPA ===
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("RELATÓRIO EXECUTIVO", title_style))
    elements.append(Paragraph("FINANCEIRO", title_style))
    
    periodo_info = f"""
    <para alignment="center" fontSize="11" color="#64748b">
    <b>Período:</b> {context_data.get('periodo_inicio', 'N/A')} até {context_data.get('periodo_fim', 'N/A')}<br/>
    <b>Gerado em:</b> {datetime.now().strftime('%d de %B de %Y às %H:%M')}
    </para>
    """
    elements.append(Paragraph(periodo_info, subtitle_style))
    elements.append(Spacer(1, 2*cm))
    
    # === KPIs PRINCIPAIS ===
    elements.append(create_section_divider("INDICADORES PRINCIPAIS", "📊"))
    elements.append(Spacer(1, 0.5*cm))
    
    receita_total = context_data.get('total_receitas', 0)
    gastos_total = context_data.get('total_gastos', 0)
    saldo_periodo = context_data.get('saldo_periodo', 0)
    
    # Grid de KPIs (2x2)
    kpi_grid = [
        [
            create_premium_kpi_card("RECEITAS", receita_total, "Total do período", 
                                   COLORS['success'], 5.2, "💰"),
            create_premium_kpi_card("DESPESAS", gastos_total, "Total do período", 
                                   COLORS['danger'], -2.1, "💸")
        ],
        [
            create_premium_kpi_card("SALDO", saldo_periodo, "Resultado líquido", 
                                   COLORS['secondary'] if saldo_periodo >= 0 else COLORS['warning'], 
                                   None, "💎"),
            create_premium_kpi_card("ECONOMIA", receita_total - gastos_total, 
                                   "Capacidade de poupança", COLORS['purple'], None, "🎯")
        ]
    ]
    
    kpi_table = Table(kpi_grid, colWidths=[4.5*cm, 4.5*cm], rowHeights=[3.5*cm, 3.5*cm])
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 1*cm))
    
    # === ANÁLISE DE GASTOS ===
    elements.append(PageBreak())
    elements.append(create_section_divider("ANÁLISE DE GASTOS", "💰"))
    elements.append(Spacer(1, 0.5*cm))
    
    if context_data.get('gastos_por_categoria'):
        categorias = context_data['gastos_por_categoria'][:8]
        valores = [cat.get('total', 0) for cat in categorias]
        labels = [f"{cat.get('nome', 'N/A')[:12]}\n{cat.get('percentual', 0):.1f}%" 
                 for cat in categorias]
        
        donut = create_donut_chart(valores, labels, "Distribuição por Categoria")
        elements.append(donut)
        elements.append(Spacer(1, 1*cm))
        
        # Tabela detalhada com design moderno
        table_data = [['CATEGORIA', 'VALOR', '%', 'STATUS']]
        
        for cat in categorias:
            valor = cat.get('total', 0)
            percentual = cat.get('percentual', 0)
            
            if percentual > 30:
                status = "CRÍTICO"
                status_color = COLORS['danger']
            elif percentual > 15:
                status = "ALTO"
                status_color = COLORS['warning']
            else:
                status = "OK"
                status_color = COLORS['success']
            
            valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            table_data.append([
                cat.get('nome', 'N/A'),
                valor_fmt,
                f"{percentual:.1f}%",
                status
            ])
        
        category_table = Table(table_data, colWidths=[5*cm, 3.5*cm, 2*cm, 2.5*cm])
        category_table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Corpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('LEFTPADDING', (0, 1), (-1, -1), 12),
            ('RIGHTPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            
            # Alternância de cores
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['bg_light']]),
            
            # Bordas
            ('LINEBELOW', (0, 0), (-1, 0), 2, COLORS['secondary']),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, COLORS['border']),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#d8b4fe')),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 2*cm))
    
    # === RODAPÉ FINAL ===
    footer_text = """
    <para alignment="center" fontSize="9" color="#9ca3af">
    <b>MaestroFin</b> - Inteligência Financeira ao Seu Alcance<br/>
    Este relatório foi gerado automaticamente com base nos seus dados financeiros<br/>
    Para suporte: contato@maestrofin.com | Tel: (11) 9999-9999<br/><br/>
    <font size="7">© 2025 MaestroFin. Todos os direitos reservados. | Documento confidencial</font>
    </para>
    """
    elements.append(Paragraph(footer_text, normal_text))
    
    # === CONSTRUIR PDF ===
    doc.build(elements, onFirstPage=create_modern_header, onLaterPages=create_modern_header)
    
    # Adicionar rodapé
    buffer.seek(0)
    return buffer.getvalue()


# ===========================
# TESTE DO SISTEMA
# ===========================
if __name__ == "__main__":
    # Dados de teste
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
        'top_gastos': [
            {'data': '2025-01-25 19:30:00', 'descricao': 'Supermercado Extra - Compra mensal', 'categoria': 'Alimentação', 'valor': 485.00},
            {'data': '2025-01-22 14:20:00', 'descricao': 'Posto Ipiranga - Gasolina', 'categoria': 'Transporte', 'valor': 320.00},
            {'data': '2025-01-18 21:15:00', 'descricao': 'Restaurante Japonês - Jantar', 'categoria': 'Lazer', 'valor': 280.00},
            {'data': '2025-01-15 10:45:00', 'descricao': 'Farmácia São Paulo - Medicamentos', 'categoria': 'Saúde', 'valor': 245.00},
            {'data': '2025-01-12 16:30:00', 'descricao': 'Cinema Cinemark - Ingressos', 'categoria': 'Lazer', 'valor': 180.00},
            {'data': '2025-01-10 09:00:00', 'descricao': 'Curso Online Udemy - Python', 'categoria': 'Educação', 'valor': 150.00},
            {'data': '2025-01-08 15:20:00', 'descricao': 'Loja Renner - Roupas', 'categoria': 'Vestuário', 'valor': 320.00},
            {'data': '2025-01-05 11:30:00', 'descricao': 'Uber - Corridas do mês', 'categoria': 'Transporte', 'valor': 125.00},
            {'data': '2025-01-03 20:00:00', 'descricao': 'iFood - Delivery', 'categoria': 'Alimentação', 'valor': 95.00},
            {'data': '2025-01-02 14:15:00', 'descricao': 'Amazon - Fone Bluetooth', 'categoria': 'Tecnologia', 'valor': 180.00},
        ],
        'insights': [
            'Seus gastos com alimentação representam 29.8% do total - considere otimizar compras',
            'Você conseguiu economizar R$ 2.300,00 este mês - excelente resultado!',
            'Transporte é seu segundo maior gasto (19.4%) - analise alternativas mais econômicas',
            'Taxa de poupança de 27% está acima da média recomendada de 20%',
            'Gastos com lazer estão controlados e dentro de um padrão saudável',
            'Considere investir parte da economia em aplicações de renda fixa',
            'Seus gastos essenciais (alimentação, saúde, transporte) representam 61.3%',
            'Parabéns! Seu controle financeiro está em nível excelente'
        ]
    }
    
    # Gerar PDF
    print("🎨 Gerando relatório financeiro premium...")
    pdf_content = generate_financial_pdf(test_data)
    
    # Salvar arquivo
    output_filename = 'relatorio_maestrofin_premium.pdf'
    with open(output_filename, 'wb') as f:
        f.write(pdf_content)
    
    print(f"✅ PDF gerado com sucesso: {output_filename}")
    print(f"📊 Total de páginas: Aproximadamente 3-4 páginas")
    print(f"💎 Design: Premium com cabeçalho, rodapé e elementos visuais modernos")
    print(f"📈 Incluído: KPIs, gráficos, tabelas e insights inteligentes")
    
    # === TOP TRANSAÇÕES ===
    if context_data.get('top_gastos'):
        elements.append(create_section_divider("MAIORES TRANSAÇÕES", "🔥"))
        elements.append(Spacer(1, 0.5*cm))
        
        top_gastos = context_data['top_gastos'][:10]
        trans_data = [['DATA', 'DESCRIÇÃO', 'CATEGORIA', 'VALOR']]
        
        for gasto in top_gastos:
            data_fmt = gasto.get('data', 'N/A')[:10]
            desc = gasto.get('descricao', 'N/A')
            desc = (desc[:30] + '...') if len(desc) > 30 else desc
            cat = gasto.get('categoria', 'N/A')
            cat = (cat[:15] + '...') if len(cat) > 15 else cat
            valor = gasto.get('valor', 0)
            valor_fmt = f"R$ {valor:.2f}".replace('.', ',')
            
            trans_data.append([data_fmt, desc, cat, valor_fmt])
        
        trans_table = Table(trans_data, colWidths=[2.5*cm, 5.5*cm, 3*cm, 2*cm])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['danger']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (2, -1), 'LEFT'),
            ('LEFTPADDING', (0, 1), (-1, -1), 10),
            ('RIGHTPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#fff5f5'), white]),
            ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#dc2626')),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, HexColor('#fecaca')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#fecaca')),
        ]))
        elements.append(trans_table)
        elements.append(Spacer(1, 1*cm))
    
    # === INSIGHTS ===
    elements.append(PageBreak())
    elements.append(create_section_divider("INSIGHTS INTELIGENTES", "💡"))
    elements.append(Spacer(1, 0.5*cm))
    
    insights = context_data.get('insights', [
        "Mantenha o controle de gastos essenciais",
        "Considere diversificar fontes de receita",
        "Estabeleça metas de economia realistas"
    ])
    
    for insight in insights[:8]:
        elements.append(Paragraph(f"✓ {insight}", insight_style))
    
    elements.append(Spacer(1, 1.5*cm))
    
    # === MÉTRICAS DE PERFORMANCE ===
    elements.append(create_section_divider("PERFORMANCE", "📈"))
    elements.append(Spacer(1, 0.5*cm))
    
    taxa_poupanca = (saldo_periodo / receita_total * 100) if receita_total > 0 else 0
    
    metrics_data = [
        ['MÉTRICA', 'VALOR', 'AVALIAÇÃO'],
        ['Taxa de Poupança', f"{taxa_poupanca:.1f}%", 
         "Excelente" if taxa_poupanca > 20 else "Regular" if taxa_poupanca > 10 else "Atenção"],
        ['Controle Financeiro', 
         "Positivo" if saldo_periodo > 0 else "Negativo",
         "Bom" if saldo_periodo > 0 else "Requer atenção"],
        ['Saúde Financeira', 
         f"{(receita_total - gastos_total) / receita_total * 100:.0f}%" if receita_total > 0 else "0%",
         "Saudável" if gastos_total < receita_total else "Crítico"]
    ]
    
    metrics_table = Table(metrics_data, colWidths=[5*cm, 4*cm, 4*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['purple']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('LEFTPADDING', (0, 1), (-1, -1), 12),
        ('RIGHTPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#faf5ff'), white]),
        ('LINEBELOW', (0, 0), (-1, 0), 2, COLORS['purple']),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, HexColor('#d8b4fe')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#d8b4fe')),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 2*cm))
    
    # === RODAPÉ FINAL ===
    footer_text = """
    <para alignment="center" fontSize="9" color="#9ca3af">
    <b>MaestroFin</b> - Inteligência Financeira ao Seu Alcance<br/>
    Este relatório foi gerado automaticamente com base nos seus dados financeiros<br/>
    Para suporte: contato@maestrofin.com | Tel: (11) 9999-9999<br/><br/>
    <font size="7">© 2025 MaestroFin. Todos os direitos reservados. | Documento confidencial</font>
    </para>
    """
elements.append(Paragraph(footer_text, normal_text))