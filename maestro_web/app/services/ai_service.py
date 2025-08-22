# app/services/ai_service.py
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

@dataclass
class AIResponse:
    content: str
    type: str  # "text", "action", "visualization"
    suggestions: List[str]
    actions: List[Dict[str, Any]]

class GerenteFinanceiroAI:
    """
    Serviço de IA para o Gerente Financeiro.
    Processa mensagens em linguagem natural e fornece insights financeiros.
    """
    
    def __init__(self):
        self.conversation_patterns = {
            'saldo': [
                'saldo', 'quanto tenho', 'dinheiro', 'valor', 'conta'
            ],
            'gastos': [
                'gastei', 'gasto', 'despesa', 'saída', 'paguei'
            ],
            'receitas': [
                'recebi', 'ganho', 'entrada', 'renda', 'salário'
            ],
            'metas': [
                'meta', 'objetivo', 'sonho', 'planejamento', 'guardar'
            ],
            'relatório': [
                'relatório', 'resumo', 'análise', 'balanço'
            ],
            'categorias': [
                'categoria', 'tipo', 'classificação', 'onde gastei'
            ],
            'ajuda': [
                'ajuda', 'help', 'como', 'o que posso', 'funcionalidades'
            ]
        }
        
        # Prompts base do sistema
        self.system_prompts = {
            'default': """
            Você é o Maestro, um assistente financeiro inteligente e amigável.
            Suas principais funções são:
            - Analisar gastos e receitas
            - Ajudar com planejamento financeiro
            - Fornecer insights sobre padrões de consumo
            - Sugerir melhorias nos hábitos financeiros
            - Responder perguntas sobre finanças pessoais
            
            Sempre seja educado, claro e forneça informações úteis.
            Use dados do contexto financeiro do usuário para personalizar respostas.
            """
        }
    
    async def process_message(self, message: str, context: Dict[str, Any], user_id: int) -> AIResponse:
        """
        Processa uma mensagem do usuário e retorna uma resposta inteligente.
        """
        message_lower = message.lower()
        intent = self._detect_intent(message_lower)
        
        if intent == 'saldo':
            return self._handle_balance_query(context)
        elif intent == 'gastos':
            return self._handle_expenses_query(context, message)
        elif intent == 'receitas':
            return self._handle_income_query(context, message)
        elif intent == 'metas':
            return self._handle_goals_query(context)
        elif intent == 'relatório':
            return self._handle_report_query(context)
        elif intent == 'categorias':
            return self._handle_categories_query(context)
        elif intent == 'ajuda':
            return self._handle_help_query()
        else:
            return self._handle_general_query(message, context)
    
    def _detect_intent(self, message: str) -> str:
        """
        Detecta a intenção do usuário baseado na mensagem.
        """
        for intent, patterns in self.conversation_patterns.items():
            if any(pattern in message for pattern in patterns):
                return intent
        return 'general'
    
    def _handle_balance_query(self, context: Dict[str, Any]) -> AIResponse:
        """
        Responde perguntas sobre saldo e contas.
        """
        accounts = context.get('accounts', [])
        
        if not accounts:
            return AIResponse(
                content="Você ainda não tem contas cadastradas. Que tal adicionar uma conta para começar a controlar suas finanças?",
                type="text",
                suggestions=["Criar nova conta", "Ver tutoriais"],
                actions=[{"type": "create_account"}]
            )
        
        total_balance = sum(account['saldo'] for account in accounts)
        
        response = f"💰 **Resumo das suas contas:**\n\n"
        
        for account in accounts:
            response += f"• **{account['nome']}**: R$ {account['saldo']:,.2f}\n"
        
        response += f"\n💵 **Total geral**: R$ {total_balance:,.2f}"
        
        if total_balance < 0:
            response += "\n\n⚠️ Atenção: Você tem saldo negativo. Considere revisar seus gastos."
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Ver gastos do mês", "Analisar categorias", "Criar meta de economia"],
            actions=[
                {"type": "view_expenses"},
                {"type": "view_categories"},
                {"type": "create_goal"}
            ]
        )
    
    def _handle_expenses_query(self, context: Dict[str, Any], message: str) -> AIResponse:
        """
        Responde perguntas sobre gastos.
        """
        monthly_summary = context.get('monthly_summary', {})
        recent_launches = context.get('recent_launches', [])
        
        total_expenses = monthly_summary.get('Saída', 0)
        
        response = f"📊 **Seus gastos este mês:**\n\n"
        response += f"💸 **Total gasto**: R$ {total_expenses:,.2f}\n\n"
        
        if recent_launches:
            expenses = [l for l in recent_launches if l['tipo'] == 'Saída'][:5]
            response += "🔍 **Últimos gastos:**\n"
            for expense in expenses:
                date_str = datetime.fromisoformat(expense['data']).strftime('%d/%m')
                response += f"• {date_str}: {expense['descricao']} - R$ {expense['valor']:,.2f}\n"
        
        # Análise de padrões
        if len(recent_launches) > 5:
            avg_expense = total_expenses / len([l for l in recent_launches if l['tipo'] == 'Saída'])
            response += f"\n📈 **Gasto médio por transação**: R$ {avg_expense:,.2f}"
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Ver categorias", "Criar meta de redução", "Analisar padrões"],
            actions=[
                {"type": "view_categories"},
                {"type": "create_expense_goal"},
                {"type": "expense_analysis"}
            ]
        )
    
    def _handle_income_query(self, context: Dict[str, Any], message: str) -> AIResponse:
        """
        Responde perguntas sobre receitas.
        """
        monthly_summary = context.get('monthly_summary', {})
        recent_launches = context.get('recent_launches', [])
        
        total_income = monthly_summary.get('Entrada', 0)
        
        response = f"📈 **Suas receitas este mês:**\n\n"
        response += f"💰 **Total recebido**: R$ {total_income:,.2f}\n\n"
        
        if recent_launches:
            income = [l for l in recent_launches if l['tipo'] == 'Entrada'][:5]
            if income:
                response += "🔍 **Últimas receitas:**\n"
                for inc in income:
                    date_str = datetime.fromisoformat(inc['data']).strftime('%d/%m')
                    response += f"• {date_str}: {inc['descricao']} - R$ {inc['valor']:,.2f}\n"
        
        # Análise de receitas vs gastos
        total_expenses = monthly_summary.get('Saída', 0)
        if total_expenses > 0:
            balance = total_income - total_expenses
            response += f"\n⚖️ **Balanço do mês**: R$ {balance:,.2f}"
            
            if balance > 0:
                response += " ✅ (Superávit)"
            else:
                response += " ⚠️ (Déficit)"
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Ver balanço completo", "Analisar gastos", "Criar meta de poupança"],
            actions=[
                {"type": "monthly_report"},
                {"type": "view_expenses"},
                {"type": "create_savings_goal"}
            ]
        )
    
    def _handle_goals_query(self, context: Dict[str, Any]) -> AIResponse:
        """
        Responde perguntas sobre metas.
        """
        goals = context.get('goals', [])
        
        if not goals:
            return AIResponse(
                content="🎯 Você ainda não tem metas definidas. Que tal criar uma meta para começar a poupar?",
                type="text",
                suggestions=["Criar meta de poupança", "Meta de redução de gastos", "Ver dicas"],
                actions=[{"type": "create_goal"}]
            )
        
        response = f"🎯 **Suas metas:**\n\n"
        
        for goal in goals:
            progress = goal['progresso']
            progress_bar = "🟩" * int(progress // 10) + "⬜" * (10 - int(progress // 10))
            
            response += f"• **{goal['descricao']}**\n"
            response += f"  💰 R$ {goal['valor_atual']:,.2f} / R$ {goal['valor_meta']:,.2f}\n"
            response += f"  📊 {progress_bar} {progress:.1f}%\n\n"
        
        # Sugestões baseadas no progresso
        low_progress_goals = [g for g in goals if g['progresso'] < 30]
        if low_progress_goals:
            response += "💡 **Dica**: Considere revisar suas metas com baixo progresso."
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Atualizar meta", "Criar nova meta", "Ver estratégias"],
            actions=[
                {"type": "update_goal"},
                {"type": "create_goal"},
                {"type": "goal_strategies"}
            ]
        )
    
    def _handle_categories_query(self, context: Dict[str, Any]) -> AIResponse:
        """
        Responde perguntas sobre categorias de gastos.
        """
        top_categories = context.get('top_categories', [])
        
        if not top_categories:
            return AIResponse(
                content="📊 Você ainda não tem gastos categorizados. Comece adicionando lançamentos para ter uma visão melhor dos seus padrões.",
                type="text",
                suggestions=["Adicionar lançamento", "Ver categorias"],
                actions=[{"type": "add_transaction"}]
            )
        
        response = f"📊 **Suas principais categorias de gasto:**\n\n"
        
        for i, category in enumerate(top_categories, 1):
            response += f"{i}. **{category['nome']}**: {category['count']} transações\n"
        
        response += "\n💡 **Insight**: Foque em otimizar suas categorias com mais gastos."
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Analisar categoria", "Ver gastos detalhados", "Criar meta por categoria"],
            actions=[
                {"type": "category_analysis"},
                {"type": "detailed_expenses"},
                {"type": "category_goal"}
            ]
        )
    
    def _handle_report_query(self, context: Dict[str, Any]) -> AIResponse:
        """
        Gera relatórios personalizados.
        """
        monthly_summary = context.get('monthly_summary', {})
        goals = context.get('goals', [])
        top_categories = context.get('top_categories', [])
        
        total_income = monthly_summary.get('Entrada', 0)
        total_expenses = monthly_summary.get('Saída', 0)
        balance = total_income - total_expenses
        
        response = f"📋 **Relatório Financeiro - {datetime.now().strftime('%B %Y')}**\n\n"
        
        response += f"💰 **Receitas**: R$ {total_income:,.2f}\n"
        response += f"💸 **Gastos**: R$ {total_expenses:,.2f}\n"
        response += f"⚖️ **Saldo**: R$ {balance:,.2f}\n\n"
        
        if goals:
            active_goals = len(goals)
            avg_progress = sum(g['progresso'] for g in goals) / len(goals)
            response += f"🎯 **Metas**: {active_goals} ativas (progresso médio: {avg_progress:.1f}%)\n\n"
        
        if top_categories:
            response += f"📊 **Categoria principal**: {top_categories[0]['nome']}\n\n"
        
        # Análise e recomendações
        if balance > 0:
            response += "✅ **Análise**: Parabéns! Você teve superávit este mês.\n"
            response += "💡 **Recomendação**: Considere aumentar sua poupança ou investir o excedente."
        else:
            response += "⚠️ **Análise**: Você teve déficit este mês.\n"
            response += "💡 **Recomendação**: Revise seus gastos e considere criar metas de redução."
        
        return AIResponse(
            content=response,
            type="visualization",
            suggestions=["Relatório detalhado", "Análise de tendências", "Comparar com mês anterior"],
            actions=[
                {"type": "detailed_report"},
                {"type": "trend_analysis"},
                {"type": "monthly_comparison"}
            ]
        )
    
    def _handle_help_query(self) -> AIResponse:
        """
        Fornece ajuda sobre funcionalidades.
        """
        response = """
        🎼 **Bem-vindo ao Maestro Financeiro!**
        
        Eu sou seu assistente financeiro pessoal. Aqui estão algumas coisas que posso fazer:
        
        📊 **Consultas que posso responder:**
        • "Qual meu saldo?" - Mostra saldo de todas as contas
        • "Quanto gastei este mês?" - Resumo de gastos
        • "Como estão minhas metas?" - Progresso das metas
        • "Gere um relatório" - Análise completa
        
        💡 **Funcionalidades:**
        • Análise de padrões de gastos
        • Acompanhamento de metas
        • Insights personalizados
        • Relatórios detalhados
        
        💬 **Dica**: Converse comigo naturalmente! Posso entender perguntas como:
        "Em que categoria mais gasto?" ou "Como posso economizar?"
        """
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Ver meu saldo", "Adicionar lançamento", "Criar meta"],
            actions=[
                {"type": "view_balance"},
                {"type": "add_transaction"},
                {"type": "create_goal"}
            ]
        )
    
    def _handle_general_query(self, message: str, context: Dict[str, Any]) -> AIResponse:
        """
        Responde perguntas gerais usando contexto.
        """
        # Aqui você pode integrar com APIs de IA como OpenAI, Gemini, etc.
        # Por enquanto, vou usar uma resposta padrão inteligente
        
        response = f"""
        🤔 Entendi sua pergunta: "{message}"
        
        Com base no que vejo em suas finanças, posso ajudar você de várias formas:
        
        📊 **Dados disponíveis:**
        • {len(context.get('recent_launches', []))} transações recentes
        • {len(context.get('goals', []))} metas ativas
        • {len(context.get('accounts', []))} contas cadastradas
        
        💡 **Sugestões:**
        Que tal ser mais específico? Por exemplo:
        • "Mostra meu saldo"
        • "Analisa meus gastos"
        • "Como estão minhas metas?"
        """
        
        return AIResponse(
            content=response,
            type="text",
            suggestions=["Ver saldo", "Analisar gastos", "Conferir metas"],
            actions=[
                {"type": "view_balance"},
                {"type": "view_expenses"},
                {"type": "view_goals"}
            ]
        )
