#!/usr/bin/env python3
"""
🎯 SPX METAS HANDLER - Handler para gestão de metas SPX
Conversation handler para criar e gerenciar metas
"""

import logging
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from .spx_metas_service import SPXMetasService, spx_metas_service
from .spx_utils import SPXValidator

logger = logging.getLogger(__name__)

# Estados da conversa de criação de meta
(META_TIPO, META_VALOR, META_PERIODO, META_CONFIRMACAO) = range(4)

class SPXMetasHandler:
    """Handler para gestão de metas SPX"""
    
    def __init__(self):
        self.service = spx_metas_service
        self.validator = SPXValidator()
    
    def get_conversation_handler(self):
        """Retorna ConversationHandler para metas"""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.iniciar_criacao_meta, pattern="^spx_criar_meta$"),
                CommandHandler('spx_meta', self.comando_criar_meta)
            ],
            states={
                META_TIPO: [
                    CallbackQueryHandler(self.processar_tipo_meta, pattern="^meta_tipo_")
                ],
                META_VALOR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.processar_valor_meta),
                    CallbackQueryHandler(self.sugerir_valor_meta, pattern="^meta_sugestao_")
                ],
                META_PERIODO: [
                    CallbackQueryHandler(self.processar_periodo_meta, pattern="^meta_periodo_")
                ],
                META_CONFIRMACAO: [
                    CallbackQueryHandler(self.confirmar_meta, pattern="^meta_confirmar$"),
                    CallbackQueryHandler(self.cancelar_meta, pattern="^meta_cancelar$")
                ]
            },
            fallbacks=[
                CommandHandler('cancelar', self.cancelar_meta),
                CallbackQueryHandler(self.cancelar_meta, pattern="^meta_cancelar$")
            ]
        )
    
    async def comando_criar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_meta - Inicia criação de meta"""
        user = update.effective_user
        
        # Verificar se já tem muitas metas ativas
        metas_ativas = self.service.get_metas_ativas(user.id)
        if len(metas_ativas) >= 5:
            await update.message.reply_text(
                "❌ **Limite de metas atingido!**\n\n"
                "Você já possui 5 metas ativas.\n"
                "Desative algumas metas antigas antes de criar novas.\n\n"
                "Use /spx_metas para ver suas metas.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        return await self.iniciar_criacao_meta(update, context)
    
    async def iniciar_criacao_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de criação de meta"""
        # Inicializar dados da meta
        context.user_data['spx_meta'] = {}
        
        # Keyboard com tipos de meta
        keyboard = [
            [
                InlineKeyboardButton("💰 Lucro Diário", callback_data="meta_tipo_lucro_diario"),
                InlineKeyboardButton("📅 Lucro Semanal", callback_data="meta_tipo_lucro_semanal")
            ],
            [
                InlineKeyboardButton("🗓️ Lucro Mensal", callback_data="meta_tipo_lucro_mensal"),
                InlineKeyboardButton("⚡ Eficiência", callback_data="meta_tipo_eficiencia_media")
            ],
            [
                InlineKeyboardButton("🛣️ Quilometragem", callback_data="meta_tipo_km_periodo"),
                InlineKeyboardButton("📦 Entregas", callback_data="meta_tipo_entregas_periodo")
            ],
            [InlineKeyboardButton("❌ Cancelar", callback_data="meta_cancelar")]
        ]
        
        mensagem = (
            "🎯 **Nova Meta SPX**\n\n"
            "Escolha o **tipo de meta** que deseja criar:\n\n"
            "💰 **Lucro** - Meta de faturamento\n"
            "⚡ **Eficiência** - Meta de performance\n"
            "🛣️ **Quilometragem** - Meta de distância\n"
            "📦 **Entregas** - Meta de produtividade"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                mensagem, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return META_TIPO
    
    async def processar_tipo_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa tipo de meta selecionado"""
        query = update.callback_query
        await query.answer()
        
        tipo_meta = query.data.replace("meta_tipo_", "")
        context.user_data['spx_meta']['tipo'] = tipo_meta
        
        # Informações do tipo de meta
        tipo_info = self.service.TIPOS_META.get(tipo_meta, {})
        
        # Gerar sugestões baseadas no histórico
        user = update.effective_user
        sugestoes = self.service.get_sugestoes_metas(user.id)
        
        # Keyboard com sugestões ou entrada manual
        keyboard = []
        
        if sugestoes['tem_dados']:
            # Adicionar sugestões específicas para o tipo
            sugestoes_tipo = [s for s in sugestoes['sugestoes'] if s['tipo'] == tipo_meta]
            
            for sugestao in sugestoes_tipo[:2]:  # Máximo 2 sugestões
                valor = sugestao['valor']
                justificativa = sugestao['justificativa']
                keyboard.append([
                    InlineKeyboardButton(
                        f"✨ {valor} {tipo_info.get('unidade', '')} (sugestão)", 
                        callback_data=f"meta_sugestao_{valor}"
                    )
                ])
        
        keyboard.extend([
            [InlineKeyboardButton("✏️ Digitar valor personalizado", callback_data="meta_valor_manual")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="meta_cancelar")]
        ])
        
        mensagem = f"🎯 **{tipo_info.get('nome', tipo_meta)}**\n\n"
        mensagem += f"_{tipo_info.get('descricao', '')}_\n\n"
        
        if sugestoes['tem_dados']:
            mensagem += f"💡 **{sugestoes['recomendacao']}**\n\n"
        
        mensagem += f"**Digite o valor da meta**\n"
        mensagem += f"Faixa: {tipo_info.get('minimo', 0)} - {tipo_info.get('maximo', 999999)} {tipo_info.get('unidade', '')}"
        
        await query.edit_message_text(
            mensagem,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return META_VALOR
    
    async def sugerir_valor_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Usa valor sugerido"""
        query = update.callback_query
        await query.answer()
        
        valor = float(query.data.replace("meta_sugestao_", ""))
        context.user_data['spx_meta']['valor'] = valor
        
        return await self._solicitar_periodo(update, context)
    
    async def processar_valor_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa valor da meta digitado"""
        try:
            valor_str = update.message.text.replace(',', '.')
            valor = float(valor_str)
            
            tipo_meta = context.user_data['spx_meta']['tipo']
            tipo_info = self.service.TIPOS_META.get(tipo_meta, {})
            
            # Validar faixa
            minimo = tipo_info.get('minimo', 0)
            maximo = tipo_info.get('maximo', 999999)
            
            if valor < minimo or valor > maximo:
                await update.message.reply_text(
                    f"❌ **Valor inválido!**\n\n"
                    f"O valor deve estar entre **{minimo}** e **{maximo}** {tipo_info.get('unidade', '')}.\n\n"
                    f"💡 Digite novamente:",
                    parse_mode='Markdown'
                )
                return META_VALOR
            
            context.user_data['spx_meta']['valor'] = valor
            
            return await self._solicitar_periodo(update, context)
            
        except ValueError:
            await update.message.reply_text(
                "❌ **Valor inválido!**\n\n"
                "Digite apenas números.\n"
                "💡 *Exemplo: 150 ou 75.5*",
                parse_mode='Markdown'
            )
            return META_VALOR
    
    async def _solicitar_periodo(self, update, context):
        """Solicita período da meta"""
        tipo_meta = context.user_data['spx_meta']['tipo']
        
        # Períodos baseados no tipo de meta
        if 'diario' in tipo_meta:
            periodos = [
                ("📅 Esta semana", "esta_semana"),
                ("🗓️ Próxima semana", "proxima_semana"),
                ("📆 Escolher datas", "personalizado")
            ]
        elif 'semanal' in tipo_meta:
            periodos = [
                ("🗓️ Este mês", "este_mes"),
                ("📅 Próximo mês", "proximo_mes"),
                ("📆 Escolher datas", "personalizado")
            ]
        elif 'mensal' in tipo_meta:
            periodos = [
                ("📅 Próximos 3 meses", "trimestre"),
                ("🗓️ Próximos 6 meses", "semestre"),
                ("📆 Escolher datas", "personalizado")
            ]
        else:
            periodos = [
                ("📅 Esta semana", "esta_semana"),
                ("🗓️ Este mês", "este_mes"),
                ("📆 Escolher datas", "personalizado")
            ]
        
        keyboard = []
        for nome, periodo in periodos:
            keyboard.append([InlineKeyboardButton(nome, callback_data=f"meta_periodo_{periodo}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="meta_cancelar")])
        
        mensagem = (
            "📅 **Período da Meta**\n\n"
            "Escolha o **período** para sua meta:"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return META_PERIODO
    
    async def processar_periodo_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa período selecionado"""
        query = update.callback_query
        await query.answer()
        
        periodo = query.data.replace("meta_periodo_", "")
        
        # Calcular datas baseadas no período
        hoje = date.today()
        
        if periodo == "esta_semana":
            inicio = hoje - timedelta(days=hoje.weekday())
            fim = inicio + timedelta(days=6)
        elif periodo == "proxima_semana":
            inicio = hoje - timedelta(days=hoje.weekday()) + timedelta(days=7)
            fim = inicio + timedelta(days=6)
        elif periodo == "este_mes":
            inicio = date(hoje.year, hoje.month, 1)
            if hoje.month == 12:
                fim = date(hoje.year + 1, 1, 1) - timedelta(days=1)
            else:
                fim = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
        elif periodo == "proximo_mes":
            if hoje.month == 12:
                inicio = date(hoje.year + 1, 1, 1)
                fim = date(hoje.year + 1, 2, 1) - timedelta(days=1)
            else:
                inicio = date(hoje.year, hoje.month + 1, 1)
                if hoje.month == 11:
                    fim = date(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    fim = date(hoje.year, hoje.month + 2, 1) - timedelta(days=1)
        elif periodo == "trimestre":
            inicio = hoje
            fim = hoje + timedelta(days=90)
        elif periodo == "semestre":
            inicio = hoje
            fim = hoje + timedelta(days=180)
        else:  # personalizado - por enquanto usar próxima semana
            inicio = hoje
            fim = hoje + timedelta(days=7)
        
        context.user_data['spx_meta']['data_inicio'] = inicio
        context.user_data['spx_meta']['data_fim'] = fim
        
        return await self._confirmar_meta(update, context)
    
    async def _confirmar_meta(self, update, context):
        """Exibe confirmação da meta"""
        dados_meta = context.user_data['spx_meta']
        tipo_info = self.service.TIPOS_META.get(dados_meta['tipo'], {})
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar meta", callback_data="meta_confirmar")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="meta_cancelar")]
        ]
        
        mensagem = "🎯 **Confirmação da Meta**\n\n"
        mensagem += f"**Tipo:** {tipo_info.get('nome', dados_meta['tipo'])}\n"
        mensagem += f"**Meta:** {dados_meta['valor']} {tipo_info.get('unidade', '')}\n"
        mensagem += f"**Período:** {dados_meta['data_inicio'].strftime('%d/%m/%Y')} - {dados_meta['data_fim'].strftime('%d/%m/%Y')}\n\n"
        mensagem += f"_{tipo_info.get('descricao', '')}_\n\n"
        mensagem += "Confirma a criação desta meta?"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return META_CONFIRMACAO
    
    async def confirmar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirma e cria a meta"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        dados_meta = context.user_data['spx_meta']
        
        try:
            # Criar meta
            meta = self.service.criar_meta(
                telegram_id=user.id,
                tipo_meta=dados_meta['tipo'],
                valor_meta=dados_meta['valor'],
                data_inicio=dados_meta['data_inicio'],
                data_fim=dados_meta['data_fim']
            )
            
            if meta:
                tipo_info = self.service.TIPOS_META.get(dados_meta['tipo'], {})
                
                mensagem = "✅ **Meta criada com sucesso!**\n\n"
                mensagem += f"🎯 **{tipo_info.get('nome', '')}**\n"
                mensagem += f"Meta: {dados_meta['valor']} {tipo_info.get('unidade', '')}\n"
                mensagem += f"Período: {dados_meta['data_inicio'].strftime('%d/%m')} - {dados_meta['data_fim'].strftime('%d/%m')}\n\n"
                mensagem += "💪 Agora é só focar e alcançar!\n"
                mensagem += "Use /spx_metas para acompanhar o progresso."
                
                await query.edit_message_text(mensagem, parse_mode='Markdown')
                
                # Limpar dados
                context.user_data.pop('spx_meta', None)
                
                return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Erro ao criar meta: {e}")
            await query.edit_message_text(
                f"❌ **Erro ao criar meta:**\n\n{str(e)}\n\nTente novamente mais tarde.",
                parse_mode='Markdown'
            )
        
        context.user_data.pop('spx_meta', None)
        return ConversationHandler.END
    
    async def cancelar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela criação da meta"""
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Criação de meta cancelada.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Criação de meta cancelada.",
                parse_mode='Markdown'
            )
        
        context.user_data.pop('spx_meta', None)
        return ConversationHandler.END
    
    async def comando_listar_metas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_metas - Lista metas ativas"""
        user = update.effective_user
        
        # Buscar metas ativas
        metas_ativas = self.service.get_metas_ativas(user.id)
        
        if not metas_ativas:
            keyboard = [
                [InlineKeyboardButton("🎯 Criar primeira meta", callback_data="spx_criar_meta")]
            ]
            
            await update.message.reply_text(
                "📋 **Suas Metas SPX**\n\n"
                "_Nenhuma meta ativa encontrada._\n\n"
                "💡 Crie sua primeira meta para acompanhar seu progresso!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # Atualizar progresso das metas
        self.service.atualizar_progresso_metas(user.id)
        
        # Buscar metas atualizadas
        metas_ativas = self.service.get_metas_ativas(user.id)
        
        # Formatar resumo
        resumo = self.service.formatar_resumo_metas(metas_ativas)
        
        # Keyboard com ações
        keyboard = [
            [InlineKeyboardButton("🎯 Nova meta", callback_data="spx_criar_meta")],
            [InlineKeyboardButton("📊 Ver histórico", callback_data="spx_historico_metas")]
        ]
        
        await update.message.reply_text(
            resumo,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# Instância global
spx_metas_handler = SPXMetasHandler()
