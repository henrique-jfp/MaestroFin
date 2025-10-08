#!/usr/bin/env python3
"""
🎨 SPX UTILS - Formatadores e Validadores SPX
Utilitários para formatação de dados e validação de entrada
"""

import re
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal, InvalidOperation

class SPXFormatter:
    """Formatador de dados SPX para exibição"""
    
    @staticmethod
    def formatar_moeda(valor: float) -> str:
        """Formata valor monetário"""
        return f"R$ {valor:.2f}".replace('.', ',')
    
    @staticmethod
    def formatar_percentual(valor: float) -> str:
        """Formata percentual"""
        return f"{valor:.1f}%"
    
    @staticmethod
    def formatar_data_br(data: date) -> str:
        """Formata data no padrão brasileiro"""
        return data.strftime("%d/%m/%Y")
    
    @staticmethod
    def formatar_data_extenso(data: date) -> str:
        """Formata data por extenso"""
        meses = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        return f"{data.day} de {meses[data.month-1]} de {data.year}"
    
    @staticmethod
    def formatar_resumo_detalhado(entrega) -> str:
        """Formata resumo detalhado de uma entrega"""
        emoji_eficiencia = "🟢" if entrega.eficiencia_percentual >= 70 else "🟡" if entrega.eficiencia_percentual >= 60 else "🔴"
        emoji_custo = "💚" if entrega.custo_por_km <= 1.0 else "🟡" if entrega.custo_por_km <= 1.5 else "🔴"
        
        resumo = f"""📦 **Entrega SPX - {SPXFormatter.formatar_data_br(entrega.data)}**

💰 **Financeiro:**
• Ganhos brutos: {SPXFormatter.formatar_moeda(entrega.ganhos_brutos)}
• Combustível: {SPXFormatter.formatar_moeda(entrega.combustivel)}
• Outros gastos: {SPXFormatter.formatar_moeda(entrega.outros_gastos)}
• **Lucro líquido: {SPXFormatter.formatar_moeda(entrega.lucro_liquido)}**

🚗 **Operacional:**
• Quilometragem: {entrega.quilometragem:.1f} km
"""
        
        if entrega.horas_trabalhadas:
            resumo += f"• Horas trabalhadas: {entrega.horas_trabalhadas:.1f}h\n"
        
        if entrega.numero_entregas:
            resumo += f"• Número de entregas: {entrega.numero_entregas}\n"
        
        resumo += f"""
📊 **Performance:**
• {emoji_eficiencia} Eficiência: {SPXFormatter.formatar_percentual(entrega.eficiencia_percentual)}
• {emoji_custo} Custo/km: {SPXFormatter.formatar_moeda(entrega.custo_por_km)}
• Ganho/km: {SPXFormatter.formatar_moeda(entrega.ganho_por_km)}
"""
        
        if entrega.numero_entregas:
            resumo += f"• Ganho/entrega: {SPXFormatter.formatar_moeda(entrega.ganho_por_entrega)}\n"
        
        if entrega.horas_trabalhadas:
            resumo += f"• Lucro/hora: {SPXFormatter.formatar_moeda(entrega.lucro_por_hora)}\n"
        
        if entrega.observacoes:
            resumo += f"\n📝 **Observações:** {entrega.observacoes}"
        
        return resumo
    
    @staticmethod
    def formatar_relatorio_semanal(relatorio: Dict[str, Any]) -> str:
        """Formata relatório semanal"""
        periodo = relatorio['periodo']
        totais = relatorio['totais']
        medias = relatorio['medias']
        extremos = relatorio['extremos']
        meta = relatorio['meta']
        
        # Emoji para meta
        emoji_meta = "✅" if meta.get('atingida') else "⏳" if meta.get('existe') else "❌"
        
        resumo = f"""📈 **RELATÓRIO SEMANAL SPX**
{SPXFormatter.formatar_data_br(periodo['inicio'])} a {SPXFormatter.formatar_data_br(periodo['fim'])}

💰 **Totais da Semana:**
• Ganhos brutos: {SPXFormatter.formatar_moeda(totais['ganhos_brutos'])}
• Combustível: {SPXFormatter.formatar_moeda(totais['combustivel'])}
• Outros gastos: {SPXFormatter.formatar_moeda(totais['outros_gastos'])}
• **Lucro líquido: {SPXFormatter.formatar_moeda(totais['lucro_liquido'])}**
• Quilometragem: {totais['quilometragem']:.1f} km
"""
        
        if totais['numero_entregas']:
            resumo += f"• Total de entregas: {totais['numero_entregas']}\n"
        
        resumo += f"""
📊 **Médias Diárias:**
• Lucro/dia: {SPXFormatter.formatar_moeda(medias['lucro_por_dia'])}
• Quilometragem/dia: {medias['km_por_dia']:.1f} km
• Custo/km: {SPXFormatter.formatar_moeda(medias['custo_por_km'])}
• Eficiência média: {SPXFormatter.formatar_percentual(medias['eficiencia_percentual'])}

🏆 **Extremos:**
• Melhor dia: {SPXFormatter.formatar_data_br(extremos['melhor_dia']['data'])} ({SPXFormatter.formatar_moeda(extremos['melhor_dia']['lucro'])})
• Pior dia: {SPXFormatter.formatar_data_br(extremos['pior_dia']['data'])} ({SPXFormatter.formatar_moeda(extremos['pior_dia']['lucro'])})

🎯 **Meta Semanal:** {emoji_meta}
"""
        
        if meta.get('existe'):
            resumo += f"• Objetivo: {SPXFormatter.formatar_moeda(meta['valor'])}\n"
            if meta.get('atingida'):
                diferenca = totais['lucro_liquido'] - meta['valor']
                resumo += f"• **META ATINGIDA!** (+{SPXFormatter.formatar_moeda(diferenca)})\n"
            else:
                falta = meta['valor'] - totais['lucro_liquido']
                resumo += f"• Faltam: {SPXFormatter.formatar_moeda(falta)}\n"
        else:
            resumo += "• Configure uma meta com /spx_meta\n"
        
        # Insights
        if medias['eficiencia_percentual'] >= 70:
            resumo += "\n💡 **Insight:** Semana excelente! Eficiência acima de 70%"
        elif periodo['dias_trabalhados'] >= 6:
            resumo += "\n💡 **Insight:** Semana produtiva! Manteve consistência"
        
        return resumo
    
    @staticmethod
    def formatar_relatorio_mensal(relatorio: Dict[str, Any]) -> str:
        """Formata relatório mensal"""
        periodo = relatorio['periodo']
        totais = relatorio['totais']
        medias = relatorio['medias']
        meta = relatorio['meta']
        comparativo = relatorio.get('comparativo')
        projecao = relatorio.get('projecao')
        
        meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        
        nome_mes = meses[periodo['mes'] - 1]
        emoji_meta = "✅" if meta.get('atingida') else "⏳" if meta.get('existe') else "❌"
        
        resumo = f"""📊 **RELATÓRIO MENSAL SPX**
{nome_mes} de {periodo['ano']}

📈 **Performance do Mês:**
• Dias trabalhados: {periodo['dias_trabalhados']}/{periodo['dias_no_mes']}
• **Lucro líquido: {SPXFormatter.formatar_moeda(totais['lucro_liquido'])}**
• Ganhos brutos: {SPXFormatter.formatar_moeda(totais['ganhos_brutos'])}
• Total gasto: {SPXFormatter.formatar_moeda(totais['combustivel'] + totais['outros_gastos'])}
• Quilometragem: {totais['quilometragem']:.1f} km

📊 **Médias:**
• Lucro/dia trabalhado: {SPXFormatter.formatar_moeda(medias['lucro_por_dia_trabalhado'])}
• Lucro/dia do mês: {SPXFormatter.formatar_moeda(medias['lucro_por_dia_mes'])}
• Quilometragem/dia: {medias['km_por_dia']:.1f} km
"""
        
        # Comparativo com mês anterior
        if comparativo:
            emoji_lucro = "📈" if comparativo['variacao_lucro'] > 0 else "📉"
            emoji_km = "📈" if comparativo['variacao_km'] > 0 else "📉"
            
            resumo += f"""
📊 **Comparativo (mês anterior):**
• {emoji_lucro} Lucro: {comparativo['variacao_lucro']:+.1f}%
• {emoji_km} Quilometragem: {comparativo['variacao_km']:+.1f}%
"""
        
        # Projeção
        if projecao:
            resumo += f"""
🔮 **Projeção do Mês:**
• Estimativa de lucro: {SPXFormatter.formatar_moeda(projecao)}
"""
        
        # Meta mensal
        resumo += f"\n🎯 **Meta Mensal:** {emoji_meta}\n"
        
        if meta.get('existe'):
            resumo += f"• Objetivo: {SPXFormatter.formatar_moeda(meta['valor'])}\n"
            if meta.get('atingida'):
                diferenca = totais['lucro_liquido'] - meta['valor']
                resumo += f"• **META ATINGIDA!** (+{SPXFormatter.formatar_moeda(diferenca)})\n"
            else:
                falta = meta['valor'] - totais['lucro_liquido']
                resumo += f"• Faltam: {SPXFormatter.formatar_moeda(falta)}\n"
                if projecao:
                    if projecao >= meta['valor']:
                        resumo += "• 🎯 **Meta provável de ser atingida!**\n"
                    else:
                        resumo += f"• ⚠️ Intensificar para atingir meta\n"
        else:
            resumo += "• Configure uma meta com /spx_meta\n"
        
        return resumo

class SPXValidator:
    """Validador de entradas SPX"""
    
    @staticmethod
    def validar_valor_monetario(valor_str: str) -> Optional[Decimal]:
        """Valida e converte valor monetário"""
        try:
            # Remover símbolos e espaços
            valor_limpo = re.sub(r'[R$\s]', '', valor_str)
            # Trocar vírgula por ponto
            valor_limpo = valor_limpo.replace(',', '.')
            
            # Converter para Decimal
            valor = Decimal(valor_limpo)
            
            # Validar range
            if valor < 0:
                return None
            if valor > 9999999:  # 10 milhões - limite razoável
                return None
                
            return valor
            
        except (InvalidOperation, ValueError):
            return None
    
    @staticmethod
    def validar_quilometragem(km_str: str) -> Optional[float]:
        """Valida quilometragem"""
        try:
            km_limpo = km_str.replace(',', '.')
            km = float(km_limpo)
            
            # Validar range razoável
            if km <= 0 or km > 2000:  # máximo 2000km por dia
                return None
                
            return km
            
        except ValueError:
            return None
    
    @staticmethod
    def validar_horas(horas_str: str) -> Optional[float]:
        """Valida horas trabalhadas"""
        try:
            horas_limpo = horas_str.replace(',', '.')
            horas = float(horas_limpo)
            
            # Validar range (máximo 24h)
            if horas <= 0 or horas > 24:
                return None
                
            return horas
            
        except ValueError:
            return None
    
    @staticmethod
    def validar_numero_entregas(entregas_str: str) -> Optional[int]:
        """Valida número de entregas"""
        try:
            entregas = int(entregas_str)
            
            # Validar range razoável
            if entregas <= 0 or entregas > 500:  # máximo 500 entregas por dia
                return None
                
            return entregas
            
        except ValueError:
            return None
    
    @staticmethod
    def validar_data(data_str: str) -> Optional[date]:
        """Valida data no formato DD/MM/YYYY"""
        try:
            # Formatos aceitos
            formatos = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y']
            
            for formato in formatos:
                try:
                    data_obj = datetime.strptime(data_str, formato).date()
                    
                    # Validar range razoável (não muito no passado nem futuro)
                    hoje = date.today()
                    if data_obj > hoje:
                        return None
                    if (hoje - data_obj).days > 365:  # máximo 1 ano atrás
                        return None
                        
                    return data_obj
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None

class SPXInsights:
    """Gerador de insights inteligentes"""
    
    @staticmethod
    def analisar_tendencia_semanal(semanas: List[Dict[str, Any]]) -> List[str]:
        """Analisa tendência das últimas semanas"""
        insights = []
        
        if len(semanas) < 2:
            return insights
        
        # Ordenar por semana
        semanas_ordenadas = sorted(semanas, key=lambda s: (s['ano'], s['semana']))
        
        # Comparar últimas 2 semanas
        ultima = semanas_ordenadas[-1]
        penultima = semanas_ordenadas[-2]
        
        variacao_lucro = ((ultima['total_lucro'] - penultima['total_lucro']) / 
                         penultima['total_lucro'] * 100) if penultima['total_lucro'] > 0 else 0
        
        if variacao_lucro > 10:
            insights.append(f"📈 Crescimento de {variacao_lucro:.1f}% na última semana!")
        elif variacao_lucro < -10:
            insights.append(f"📉 Queda de {abs(variacao_lucro):.1f}% na última semana. Revisar estratégia.")
        
        # Analisar consistência
        lucros = [s['total_lucro'] for s in semanas_ordenadas[-4:]]  # últimas 4 semanas
        if len(lucros) >= 3:
            desvio = SPXInsights._calcular_desvio_padrao(lucros)
            media = sum(lucros) / len(lucros)
            coef_variacao = (desvio / media) * 100 if media > 0 else 0
            
            if coef_variacao < 15:
                insights.append("🎯 Excelente consistência nas últimas semanas!")
            elif coef_variacao > 30:
                insights.append("⚠️ Muita variação. Tente padronizar sua rotina.")
        
        return insights
    
    @staticmethod
    def _calcular_desvio_padrao(valores: List[float]) -> float:
        """Calcula desvio padrão simples"""
        if not valores:
            return 0
        
        media = sum(valores) / len(valores)
        variancia = sum((x - media) ** 2 for x in valores) / len(valores)
        return variancia ** 0.5
    
    @staticmethod
    def sugerir_melhorias(entrega, historico: List) -> List[str]:
        """Sugere melhorias baseadas no histórico"""
        sugestoes = []
        
        if not historico:
            return sugestoes
        
        # Análise de eficiência
        media_eficiencia = sum(e.eficiencia_percentual for e in historico) / len(historico)
        
        if entrega.eficiencia_percentual < media_eficiencia - 5:
            sugestoes.append("💡 Eficiência abaixo da sua média. Revise rotas ou negocie melhores entregas.")
        
        # Análise de custo por km
        media_custo_km = sum(e.custo_por_km for e in historico) / len(historico)
        
        if entrega.custo_por_km > media_custo_km * 1.1:
            sugestoes.append("⛽ Custo por km acima do normal. Verifique preço do combustível ou rotas.")
        
        # Análise de quilometragem vs lucro
        entregas_alto_km = [e for e in historico if e.quilometragem > 100]
        entregas_baixo_km = [e for e in historico if e.quilometragem <= 80]
        
        if entregas_alto_km and entregas_baixo_km:
            media_efic_alto = sum(e.eficiencia_percentual for e in entregas_alto_km) / len(entregas_alto_km)
            media_efic_baixo = sum(e.eficiencia_percentual for e in entregas_baixo_km) / len(entregas_baixo_km)
            
            if media_efic_baixo > media_efic_alto + 5:
                sugestoes.append("🎯 Dias com menos km têm melhor eficiência. Foque em qualidade vs quantidade.")
        
        return sugestoes
