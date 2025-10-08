#!/usr/bin/env python3
"""
📊 SPX DASHBOARD - Dashboard completo SPX
Visualização avançada com métricas, rankings e insights
"""

import logging
from datetime import date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .spx_service import SPXService
from .spx_metas_service import spx_metas_service
from .spx_gamification import spx_gamification
from .spx_utils import SPXFormatter

logger = logging.getLogger(__name__)

class SPXDashboard:
    """Dashboard SPX completo"""
    
    def __init__(self):
        self.service = SPXService()
        self.formatter = SPXFormatter()
    
    async def comando_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_dashboard - Dashboard principal"""
        user = update.effective_user
        
        # Keyboard principal do dashboard
        keyboard = [
            [
                InlineKeyboardButton("📈 Resumo Mensal", callback_data="spx_dash_resumo_mensal"),
                InlineKeyboardButton("📅 Resumo Semanal", callback_data="spx_dash_resumo_semanal")
            ],
            [
                InlineKeyboardButton("🎯 Minhas Metas", callback_data="spx_dash_metas"),
                InlineKeyboardButton("🏆 Rankings", callback_data="spx_dash_rankings")
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data="spx_dash_analytics"),
                InlineKeyboardButton("🎮 Conquistas", callback_data="spx_dash_conquistas")
            ],
            [InlineKeyboardButton("🔄 Atualizar", callback_data="spx_dash_refresh")]
        ]
        
        # Gerar resumo rápido
        resumo_rapido = await self._gerar_resumo_rapido(user.id)
        
        mensagem = "📊 **SPX Dashboard**\n\n"
        mensagem += resumo_rapido
        mensagem += "\n📋 **Selecione uma opção:**"
        
        await update.message.reply_text(
            mensagem,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def callback_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks do dashboard"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        action = query.data.replace("spx_dash_", "")
        
        if action == "resumo_mensal":
            await self._mostrar_resumo_mensal(query, user.id)
        elif action == "resumo_semanal":
            await self._mostrar_resumo_semanal(query, user.id)
        elif action == "metas":
            await self._mostrar_metas(query, user.id)
        elif action == "rankings":
            await self._mostrar_rankings(query, user.id)
        elif action == "analytics":
            await self._mostrar_analytics(query, user.id)
        elif action == "conquistas":
            await self._mostrar_conquistas(query, user.id)
        elif action == "refresh":
            await self._refresh_dashboard(query, user.id)
    
    async def _gerar_resumo_rapido(self, telegram_id: int) -> str:
        """Gera resumo rápido para o dashboard"""
        try:
            # Dados de hoje
            hoje = date.today()
            entrega_hoje = self.service.get_entrega_por_data(telegram_id, hoje)
            
            if entrega_hoje:
                resumo = f"📅 **Hoje ({hoje.strftime('%d/%m')})**\n"
                resumo += f"💰 Lucro: R$ {entrega_hoje.lucro_liquido:.2f}\n"
                resumo += f"⚡ Eficiência: {entrega_hoje.eficiencia_percentual:.1f}%\n"
                resumo += f"🛣️ KM: {entrega_hoje.quilometragem} km\n"
            else:
                resumo = f"📅 **Hoje ({hoje.strftime('%d/%m')})**\n"
                resumo += "_Ainda não há registros para hoje_\n"
            
            # Dados da semana
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            relatorio_semana = self.service.gerar_relatorio(telegram_id, 'semanal')
            
            if relatorio_semana and relatorio_semana.get('estatisticas'):
                stats = relatorio_semana['estatisticas']
                resumo += f"\n📊 **Esta Semana**\n"
                resumo += f"💰 Lucro Total: R$ {stats['lucro_liquido_total']:.2f}\n"
                resumo += f"📦 Dias Trabalhados: {stats['dias_trabalhados']}\n"
            
            return resumo
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo rápido: {e}")
            return "📊 **Dashboard SPX**\n_Carregando dados..._"
    
    async def _mostrar_resumo_mensal(self, query, telegram_id: int):
        """Mostra resumo mensal detalhado"""
        try:
            relatorio = self.service.gerar_relatorio(telegram_id, 'mensal')
            
            if not relatorio or not relatorio.get('estatisticas'):
                await query.edit_message_text(
                    "📅 **Resumo Mensal**\n\n"
                    "_Nenhum dado encontrado para este mês._\n\n"
                    "💡 Registre algumas entregas primeiro!",
                    parse_mode='Markdown'
                )
                return
            
            stats = relatorio['estatisticas']
            
            mensagem = "📅 **Resumo Mensal**\n\n"
            mensagem += f"💰 **Financeiro**\n"
            mensagem += f"• Lucro Total: R$ {stats['lucro_liquido_total']:.2f}\n"
            mensagem += f"• Lucro Médio/Dia: R$ {stats['lucro_liquido_medio']:.2f}\n"
            mensagem += f"• Ganhos Brutos: R$ {stats['ganhos_brutos_total']:.2f}\n"
            mensagem += f"• Gastos Total: R$ {stats['gastos_total']:.2f}\n\n"
            
            mensagem += f"📊 **Performance**\n"
            mensagem += f"• Eficiência Média: {stats['eficiencia_media']:.1f}%\n"
            mensagem += f"• Quilometragem: {stats['quilometragem_total']:.0f} km\n"
            mensagem += f"• Custo/KM: R$ {stats['custo_por_km']:.2f}\n"
            mensagem += f"• Dias Trabalhados: {stats['dias_trabalhados']}\n\n"
            
            if stats.get('entregas_total', 0) > 0:
                mensagem += f"📦 **Entregas**\n"
                mensagem += f"• Total: {stats['entregas_total']}\n"
                mensagem += f"• Média/Dia: {stats['entregas_media']:.1f}\n\n"
            
            # Insights
            insights = self.service.gerar_insights_periodo(telegram_id, 'mensal')
            if insights:
                mensagem += f"💡 **Insights**\n{insights}"
            
            # Keyboard de volta
            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]]
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar resumo mensal: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar resumo mensal. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _mostrar_resumo_semanal(self, query, telegram_id: int):
        """Mostra resumo semanal detalhado"""
        try:
            relatorio = self.service.gerar_relatorio(telegram_id, 'semanal')
            
            if not relatorio or not relatorio.get('estatisticas'):
                await query.edit_message_text(
                    "📅 **Resumo Semanal**\n\n"
                    "_Nenhum dado encontrado para esta semana._\n\n"
                    "💡 Registre algumas entregas primeiro!",
                    parse_mode='Markdown'
                )
                return
            
            stats = relatorio['estatisticas']
            
            # Determinar período da semana
            hoje = date.today()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            
            mensagem = f"📅 **Resumo Semanal**\n"
            mensagem += f"_{inicio_semana.strftime('%d/%m')} - {fim_semana.strftime('%d/%m')}_\n\n"
            
            mensagem += f"💰 **Financeiro**\n"
            mensagem += f"• Lucro Total: R$ {stats['lucro_liquido_total']:.2f}\n"
            mensagem += f"• Lucro Médio: R$ {stats['lucro_liquido_medio']:.2f}\n"
            mensagem += f"• Melhor Dia: R$ {stats.get('melhor_dia_lucro', 0):.2f}\n\n"
            
            mensagem += f"📊 **Performance**\n"
            mensagem += f"• Eficiência: {stats['eficiencia_media']:.1f}%\n"
            mensagem += f"• Quilometragem: {stats['quilometragem_total']:.0f} km\n"
            mensagem += f"• Dias Trabalhados: {stats['dias_trabalhados']}/7\n\n"
            
            # Progress bar da semana
            dias_trabalhados = stats['dias_trabalhados']
            barra_semana = "█" * dias_trabalhados + "░" * (7 - dias_trabalhados)
            mensagem += f"📈 **Progresso Semanal**\n[{barra_semana}] {dias_trabalhados}/7 dias\n\n"
            
            # Metas da semana
            metas_ativas = spx_metas_service.get_metas_ativas(telegram_id)
            metas_semana = [m for m in metas_ativas if 'semanal' in m.tipo_meta or 
                           (m.data_inicio <= hoje <= m.data_fim and 
                            (m.data_fim - m.data_inicio).days <= 7)]
            
            if metas_semana:
                mensagem += f"🎯 **Metas da Semana**\n"
                for meta in metas_semana[:2]:  # Máximo 2 metas
                    tipo_info = spx_metas_service.TIPOS_META.get(meta.tipo_meta, {})
                    percentual = (meta.progresso_atual / meta.valor_meta * 100) if meta.valor_meta > 0 else 0
                    status = "✅" if meta.atingida else "🎯"
                    mensagem += f"• {status} {tipo_info.get('nome', '')}: {percentual:.1f}%\n"
                mensagem += "\n"
            
            # Keyboard de volta
            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]]
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar resumo semanal: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar resumo semanal. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _mostrar_metas(self, query, telegram_id: int):
        """Mostra metas ativas"""
        try:
            # Atualizar progresso das metas
            spx_metas_service.atualizar_progresso_metas(telegram_id)
            
            # Buscar metas ativas
            metas_ativas = spx_metas_service.get_metas_ativas(telegram_id)
            
            if not metas_ativas:
                keyboard = [
                    [InlineKeyboardButton("🎯 Criar primeira meta", callback_data="spx_criar_meta")],
                    [InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]
                ]
                
                await query.edit_message_text(
                    "🎯 **Suas Metas SPX**\n\n"
                    "_Nenhuma meta ativa encontrada._\n\n"
                    "💡 Crie sua primeira meta para acompanhar seu progresso!",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
            
            # Formatar resumo das metas
            resumo = spx_metas_service.formatar_resumo_metas(metas_ativas)
            
            # Keyboard com ações
            keyboard = [
                [InlineKeyboardButton("🎯 Nova meta", callback_data="spx_criar_meta")],
                [InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]
            ]
            
            await query.edit_message_text(
                resumo,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar metas: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar metas. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _mostrar_rankings(self, query, telegram_id: int):
        """Mostra rankings SPX"""
        try:
            # Buscar ranking mensal
            ranking_dados = spx_gamification.get_ranking_spx(telegram_id, 'mensal')
            
            if not ranking_dados['ranking']:
                await query.edit_message_text(
                    "🏆 **Rankings SPX**\n\n"
                    "_Ainda não há dados suficientes para rankings._\n\n"
                    "💡 Registre mais entregas para aparecer nos rankings!",
                    parse_mode='Markdown'
                )
                return
            
            mensagem = "🏆 **Rankings SPX - Este Mês**\n\n"
            
            # Top 10
            for i, linha in enumerate(ranking_dados['ranking'], 1):
                if i <= 3:
                    medalha = ["🥇", "🥈", "🥉"][i-1]
                else:
                    medalha = f"{i}º"
                
                user_id = linha.telegram_id
                lucro = linha.lucro_total or 0
                km = linha.km_total or 0
                dias = linha.dias_trabalhados or 0
                
                # Destacar usuário atual
                destaque = "👤 " if user_id == telegram_id else ""
                
                mensagem += f"{medalha} {destaque}User{user_id}\n"
                mensagem += f"    💰 R$ {lucro:.2f} • 🛣️ {km:.0f}km • 📅 {dias}d\n"
            
            # Posição do usuário se não estiver no top 10
            if ranking_dados['posicao_usuario'] and ranking_dados['posicao_usuario'] > 10:
                mensagem += f"\n...\n"
                mensagem += f"👤 **Sua posição: {ranking_dados['posicao_usuario']}º**\n"
            
            # Keyboard de volta
            keyboard = [
                [InlineKeyboardButton("📊 Ranking Semanal", callback_data="spx_ranking_semanal")],
                [InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]
            ]
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar rankings: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar rankings. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _mostrar_analytics(self, query, telegram_id: int):
        """Mostra analytics avançados"""
        try:
            # Gerar insights avançados
            insights_mensal = self.service.gerar_insights_periodo(telegram_id, 'mensal')
            insights_semanal = self.service.gerar_insights_periodo(telegram_id, 'semanal')
            
            mensagem = "📊 **Analytics SPX**\n\n"
            
            if insights_mensal:
                mensagem += "📅 **Insights Mensais**\n"
                mensagem += insights_mensal + "\n\n"
            
            if insights_semanal:
                mensagem += "📈 **Insights Semanais**\n"
                mensagem += insights_semanal + "\n\n"
            
            if not insights_mensal and not insights_semanal:
                mensagem += "_Registre mais entregas para receber insights personalizados!_"
            
            # Keyboard de volta
            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]]
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar analytics: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar analytics. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _mostrar_conquistas(self, query, telegram_id: int):
        """Mostra conquistas do usuário"""
        try:
            # Por enquanto, mostrar placeholder
            mensagem = "🎮 **Conquistas SPX**\n\n"
            mensagem += "_Sistema de conquistas em desenvolvimento!_\n\n"
            mensagem += "🏆 **Próximas features:**\n"
            mensagem += "• 🔰 Primeira Entrega\n"
            mensagem += "• 🔥 Streaks de trabalho\n"
            mensagem += "• ⚡ Eficiência alta\n"
            mensagem += "• 💰 Metas atingidas\n"
            mensagem += "• 🏁 Recordes pessoais"
            
            # Keyboard de volta
            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="spx_dash_refresh")]]
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar conquistas: {e}")
            await query.edit_message_text(
                "❌ Erro ao carregar conquistas. Tente novamente.",
                parse_mode='Markdown'
            )
    
    async def _refresh_dashboard(self, query, telegram_id: int):
        """Atualiza dashboard principal"""
        try:
            # Keyboard principal do dashboard
            keyboard = [
                [
                    InlineKeyboardButton("📈 Resumo Mensal", callback_data="spx_dash_resumo_mensal"),
                    InlineKeyboardButton("📅 Resumo Semanal", callback_data="spx_dash_resumo_semanal")
                ],
                [
                    InlineKeyboardButton("🎯 Minhas Metas", callback_data="spx_dash_metas"),
                    InlineKeyboardButton("🏆 Rankings", callback_data="spx_dash_rankings")
                ],
                [
                    InlineKeyboardButton("📊 Analytics", callback_data="spx_dash_analytics"),
                    InlineKeyboardButton("🎮 Conquistas", callback_data="spx_dash_conquistas")
                ],
                [InlineKeyboardButton("🔄 Atualizar", callback_data="spx_dash_refresh")]
            ]
            
            # Gerar resumo rápido atualizado
            resumo_rapido = await self._gerar_resumo_rapido(telegram_id)
            
            mensagem = "📊 **SPX Dashboard**\n\n"
            mensagem += resumo_rapido
            mensagem += "\n📋 **Selecione uma opção:**"
            
            await query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao atualizar dashboard: {e}")
            await query.edit_message_text(
                "❌ Erro ao atualizar dashboard. Tente novamente.",
                parse_mode='Markdown'
            )

# Instância global
spx_dashboard = SPXDashboard()
