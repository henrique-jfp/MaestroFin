#!/usr/bin/env pfrom .spx_service import SPXService
from .spx_utils import SPXFormatter, SPXValidator
from .spx_gamification import spx_gamification
from analytics.advanced_analytics import AdvancedAnalytics
"""
🚗 SPX HANDLER - Sistema de Controle de Entregas
Gerencia registro e análise de entregas para entregadores de aplicativos
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.database import get_db
from models import EntregaSPX, MetaSPX
from .spx_service import SPXService
from .spx_utils import SPXFormatter, SPXValidator
from analytics.advanced_analytics import advanced_analytics

logger = logging.getLogger(__name__)

# Estados da conversa
(SPX_GANHOS, SPX_COMBUSTIVEL, SPX_OUTROS_GASTOS, SPX_QUILOMETRAGEM, 
 SPX_HORAS, SPX_ENTREGAS, SPX_OBSERVACOES, SPX_CONFIRMAR) = range(8)

class SPXHandler:
    """Handler principal para funcionalidades SPX"""
    
    def __init__(self):
        self.service = SPXService()
        self.formatter = SPXFormatter()
        self.validator = SPXValidator()
    
    async def comando_spx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando principal /spx"""
        try:
            user = update.effective_user
            hoje = date.today()
            
            # Verificar se já existe registro para hoje
            entrega_hoje = self.service.get_entrega_por_data(user.id, hoje)
            
            if entrega_hoje:
                return await self._mostrar_resumo_existente(update, entrega_hoje)
            
            # Menu inicial
            keyboard = [
                [InlineKeyboardButton("📝 Registrar dia completo", callback_data="spx_registro_completo")],
                [InlineKeyboardButton("⚡ Registro rápido", callback_data="spx_registro_rapido")],
                [InlineKeyboardButton("📊 Ver relatórios", callback_data="spx_relatorios")],
                [InlineKeyboardButton("🎯 Configurar metas", callback_data="spx_metas")]
            ]
            
            mensagem = (
                "🚗 **SPX - Sistema de Controle de Entregas**\n\n"
                f"📅 **{hoje.strftime('%d/%m/%Y')}** - Como você quer começar?\n\n"
                "💡 **Dica**: Registre seus dados diariamente para insights precisos!"
            )
            
            await update.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Analytics
            advanced_analytics.track_command_usage(user.id, user.username, 'spx_inicio')
            
        except Exception as e:
            logger.error(f"Erro no comando SPX: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Erro ao iniciar SPX. Tente novamente em alguns instantes."
            )
    
    async def _mostrar_resumo_existente(self, update: Update, entrega: EntregaSPX):
        """Mostra resumo de entrega já registrada"""
        resumo = self.formatter.formatar_resumo_detalhado(entrega)
        
        keyboard = [
            [InlineKeyboardButton("✏️ Editar", callback_data=f"spx_editar_{entrega.id}")],
            [InlineKeyboardButton("📊 Ver gráficos", callback_data="spx_graficos")],
            [InlineKeyboardButton("📈 Comparar períodos", callback_data="spx_comparar")]
        ]
        
        await update.message.reply_text(
            resumo,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def iniciar_registro_completo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de registro completo"""
        query = update.callback_query
        await query.answer()
        
        mensagem = (
            "💰 **Registro Completo - Passo 1/7**\n\n"
            "Quanto você **ganhou** hoje? (valor bruto total)\n\n"
            "💡 *Exemplo: 240.50 ou R$ 240,50*"
        )
        
        await query.edit_message_text(mensagem, parse_mode='Markdown')
        
        # Inicializar dados do contexto
        context.user_data['spx_registro'] = {}
        
        return SPX_GANHOS
    
    async def processar_ganhos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa entrada de ganhos"""
        try:
            valor_str = update.message.text
            valor = self.validator.validar_valor_monetario(valor_str)
            
            if valor is None:
                await update.message.reply_text(
                    "❌ Valor inválido. Digite apenas números.\n"
                    "💡 *Exemplo: 240.50*"
                )
                return SPX_GANHOS
            
            context.user_data['spx_registro']['ganhos_brutos'] = float(valor)
            
            mensagem = (
                f"✅ Ganhos: R$ {valor:.2f}\n\n"
                "⛽ **Passo 2/7**\n\n"
                "Quanto gastou com **combustível**?\n\n"
                "💡 *Exemplo: 80.00*"
            )
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            return SPX_COMBUSTIVEL
            
        except Exception as e:
            logger.error(f"Erro ao processar ganhos: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_GANHOS
    
    async def processar_combustivel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa entrada de combustível"""
        try:
            valor_str = update.message.text
            valor = self.validator.validar_valor_monetario(valor_str)
            
            if valor is None:
                await update.message.reply_text(
                    "❌ Valor inválido. Digite apenas números.\n"
                    "💡 *Exemplo: 80.00*"
                )
                return SPX_COMBUSTIVEL
            
            context.user_data['spx_registro']['combustivel'] = float(valor)
            
            mensagem = (
                f"✅ Combustível: R$ {valor:.2f}\n\n"
                "🅿️ **Passo 3/7**\n\n"
                "Teve outros gastos? (estacionamento, pedágio, manutenção)\n\n"
                "💡 *Digite 0 se não teve gastos extras*"
            )
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            return SPX_OUTROS_GASTOS
            
        except Exception as e:
            logger.error(f"Erro ao processar combustível: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_COMBUSTIVEL
    
    async def processar_outros_gastos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa outros gastos"""
        try:
            valor_str = update.message.text
            valor = self.validator.validar_valor_monetario(valor_str)
            
            if valor is None:
                await update.message.reply_text(
                    "❌ Valor inválido. Digite apenas números.\n"
                    "💡 *Exemplo: 15.00 ou 0*"
                )
                return SPX_OUTROS_GASTOS
            
            context.user_data['spx_registro']['outros_gastos'] = float(valor)
            
            mensagem = (
                f"✅ Outros gastos: R$ {valor:.2f}\n\n"
                "🚗 **Passo 4/7**\n\n"
                "Quantos **quilômetros** você rodou?\n\n"
                "💡 *Exemplo: 120 ou 85.5*"
            )
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            return SPX_QUILOMETRAGEM
            
        except Exception as e:
            logger.error(f"Erro ao processar outros gastos: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_OUTROS_GASTOS
    
    async def processar_quilometragem(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa quilometragem"""
        try:
            km_str = update.message.text
            km = self.validator.validar_quilometragem(km_str)
            
            if km is None:
                await update.message.reply_text(
                    "❌ Quilometragem inválida. Digite apenas números.\n"
                    "💡 *Exemplo: 120 ou 85.5*"
                )
                return SPX_QUILOMETRAGEM
            
            context.user_data['spx_registro']['quilometragem'] = float(km)
            
            # Mostrar botões para próximo passo
            keyboard = [
                [InlineKeyboardButton("⏰ Informar horas trabalhadas", callback_data="spx_informar_horas")],
                [InlineKeyboardButton("⏭️ Pular para entregas", callback_data="spx_pular_horas")]
            ]
            
            mensagem = (
                f"✅ Quilometragem: {km} km\n\n"
                "⏰ **Passo 5/7** (Opcional)\n\n"
                "Quer informar quantas **horas** trabalhou?"
            )
            
            await update.message.reply_text(
                mensagem, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return SPX_HORAS
            
        except Exception as e:
            logger.error(f"Erro ao processar quilometragem: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_QUILOMETRAGEM
    
    async def processar_horas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa horas trabalhadas"""
        try:
            horas_str = update.message.text
            horas = self.validator.validar_horas(horas_str)
            
            if horas is None:
                await update.message.reply_text(
                    "❌ Valor inválido. Digite apenas números.\n"
                    "💡 *Exemplo: 8 ou 7.5*"
                )
                return SPX_HORAS
            
            context.user_data['spx_registro']['horas_trabalhadas'] = float(horas)
            
            # Prosseguir para número de entregas
            return await self._solicitar_numero_entregas(update, context)
            
        except Exception as e:
            logger.error(f"Erro ao processar horas: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_HORAS
    
    async def pular_horas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pula informação de horas"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['spx_registro']['horas_trabalhadas'] = None
        return await self._solicitar_numero_entregas(update, context)
    
    async def _solicitar_numero_entregas(self, update, context):
        """Solicita número de entregas"""
        keyboard = [
            [InlineKeyboardButton("📦 Informar entregas", callback_data="spx_informar_entregas")],
            [InlineKeyboardButton("⏭️ Finalizar registro", callback_data="spx_finalizar_sem_entregas")]
        ]
        
        mensagem = (
            "📦 **Passo 6/7** (Opcional)\n\n"
            "Quantas **entregas** você fez hoje?"
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
        
        return SPX_ENTREGAS
    
    async def processar_entregas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa número de entregas"""
        try:
            entregas_str = update.message.text
            entregas = self.validator.validar_numero_entregas(entregas_str)
            
            if entregas is None:
                await update.message.reply_text(
                    "❌ Número inválido. Digite apenas números inteiros.\n"
                    "💡 *Exemplo: 25*"
                )
                return SPX_ENTREGAS
            
            context.user_data['spx_registro']['numero_entregas'] = entregas
            
            return await self._solicitar_observacoes(update, context)
            
        except Exception as e:
            logger.error(f"Erro ao processar entregas: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_ENTREGAS
    
    async def finalizar_sem_entregas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finaliza sem informar entregas"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['spx_registro']['numero_entregas'] = None
        return await self._solicitar_observacoes(update, context)
    
    async def _solicitar_observacoes(self, update, context):
        """Solicita observações opcionais"""
        keyboard = [
            [InlineKeyboardButton("📝 Adicionar observação", callback_data="spx_adicionar_obs")],
            [InlineKeyboardButton("✅ Finalizar registro", callback_data="spx_confirmar_registro")]
        ]
        
        mensagem = (
            "📝 **Passo 7/7** (Opcional)\n\n"
            "Quer adicionar alguma **observação**?\n"
            "*(ex: trânsito pesado, chuva, zona específica)*"
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
        
        return SPX_OBSERVACOES
    
    async def processar_observacoes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa observações"""
        try:
            observacoes = update.message.text.strip()
            
            if len(observacoes) > 500:
                await update.message.reply_text(
                    "❌ Observação muito longa. Máximo 500 caracteres."
                )
                return SPX_OBSERVACOES
            
            context.user_data['spx_registro']['observacoes'] = observacoes
            
            return await self._confirmar_registro(update, context)
            
        except Exception as e:
            logger.error(f"Erro ao processar observações: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
            return SPX_OBSERVACOES
    
    async def pular_observacoes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pula observações"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['spx_registro']['observacoes'] = None
        return await self._confirmar_registro(update, context)
    
    async def _confirmar_registro(self, update, context):
        """Mostra resumo para confirmação"""
        dados = context.user_data['spx_registro']
        
        # Calcular métricas
        ganhos = dados['ganhos_brutos']
        combustivel = dados['combustivel']
        outros = dados.get('outros_gastos', 0)
        km = dados['quilometragem']
        
        lucro = ganhos - combustivel - outros
        custo_km = (combustivel + outros) / km if km > 0 else 0
        eficiencia = (lucro / ganhos * 100) if ganhos > 0 else 0
        
        resumo = (
            "📋 **Confirme os dados:**\n\n"
            f"💰 Ganhos: R$ {ganhos:.2f}\n"
            f"⛽ Combustível: R$ {combustivel:.2f}\n"
            f"🅿️ Outros gastos: R$ {outros:.2f}\n"
            f"🚗 Quilometragem: {km:.1f} km\n"
        )
        
        if dados.get('horas_trabalhadas'):
            resumo += f"⏰ Horas: {dados['horas_trabalhadas']:.1f}h\n"
        
        if dados.get('numero_entregas'):
            resumo += f"📦 Entregas: {dados['numero_entregas']}\n"
        
        resumo += (
            f"\n📊 **Resultados:**\n"
            f"💚 Lucro líquido: R$ {lucro:.2f}\n"
            f"💸 Custo/km: R$ {custo_km:.2f}\n"
            f"⚡ Eficiência: {eficiencia:.1f}%"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data="spx_salvar")],
            [InlineKeyboardButton("✏️ Editar", callback_data="spx_voltar_inicio")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="spx_cancelar")]
        ]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                resumo, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                resumo, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return SPX_CONFIRMAR
    
    async def salvar_registro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Salva o registro no banco"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = update.effective_user
            dados = context.user_data['spx_registro']
            
            # Criar entrega
            entrega = self.service.criar_entrega(
                telegram_id=user.id,
                data=date.today(),
                **dados
            )
            
            if entrega:
                # Verificar conquistas
                conquistas = spx_gamification.verificar_conquistas(user.id, entrega)
                
                # Gerar resumo com insights
                resumo = self.formatter.formatar_resumo_detalhado(entrega)
                insights = self.service.gerar_insights(entrega)
                
                mensagem_final = f"{resumo}\n\n{insights}"
                
                # Adicionar conquistas se houver
                if conquistas:
                    mensagem_final += "\n" + spx_gamification.formatar_conquistas_obtidas(conquistas)
                
                await query.edit_message_text(
                    mensagem_final,
                    parse_mode='Markdown'
                )
                
                # Analytics
                advanced_analytics.track_command_usage(user.id, user.username, 'spx_registro_sucesso')
                
                # Limpar dados do contexto
                context.user_data.pop('spx_registro', None)
                
                return ConversationHandler.END
            else:
                await query.edit_message_text(
                    "❌ Erro ao salvar registro. Tente novamente."
                )
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Erro ao salvar registro SPX: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Erro interno ao salvar. Tente novamente mais tarde."
            )
            return ConversationHandler.END
    
    async def cancelar_registro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela o registro"""
        query = update.callback_query
        await query.answer()
        
        # Limpar dados
        context.user_data.pop('spx_registro', None)
        
        await query.edit_message_text(
            "❌ Registro cancelado.\n\n"
            "Digite /spx novamente quando quiser registrar."
        )
        
        return ConversationHandler.END
    
    async def comando_spx_hoje(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_hoje - resumo do dia"""
        try:
            user = update.effective_user
            hoje = date.today()
            
            entrega = self.service.get_entrega_por_data(user.id, hoje)
            
            if not entrega:
                await update.message.reply_text(
                    "📅 Nenhum registro encontrado para hoje.\n\n"
                    "Digite /spx para registrar suas entregas!"
                )
                return
            
            resumo = self.formatter.formatar_resumo_detalhado(entrega)
            await update.message.reply_text(resumo, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro em spx_hoje: {e}")
            await update.message.reply_text("❌ Erro ao buscar dados de hoje.")
    
    async def comando_spx_semana(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_semana - relatório semanal"""
        try:
            user = update.effective_user
            relatorio = self.service.gerar_relatorio_semanal(user.id)
            
            if not relatorio:
                await update.message.reply_text(
                    "📊 Nenhum dado encontrado para esta semana.\n\n"
                    "Registre suas entregas com /spx!"
                )
                return
            
            resumo = self.formatter.formatar_relatorio_semanal(relatorio)
            await update.message.reply_text(resumo, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro em spx_semana: {e}")
            await update.message.reply_text("❌ Erro ao gerar relatório semanal.")
    
    async def comando_spx_mes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /spx_mes - relatório mensal"""
        try:
            user = update.effective_user
            relatorio = self.service.gerar_relatorio_mensal(user.id)
            
            if not relatorio:
                await update.message.reply_text(
                    "📊 Nenhum dado encontrado para este mês.\n\n"
                    "Registre suas entregas com /spx!"
                )
                return
            
            resumo = self.formatter.formatar_relatorio_mensal(relatorio)
            await update.message.reply_text(resumo, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro em spx_mes: {e}")
            await update.message.reply_text("❌ Erro ao gerar relatório mensal.")

# Instância global
spx_handler = SPXHandler()
