#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Dashboard Handler - MaestroFin
Handler para integração do dashboard com o bot do Telegram
"""

import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class DashboardHandler:
    """Handler para funcionalidades do dashboard"""
    
    def __init__(self, dashboard_url: str = "http://localhost:5000"):
        self.dashboard_url = dashboard_url
    
    async def verificar_dashboard_online(self) -> bool:
        """Verifica se o dashboard está online"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/status", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao verificar dashboard: {e}")
            return False
    
    async def gerar_link_dashboard(self, user_id: int) -> dict:
        """Gera link temporário para acesso ao dashboard"""
        try:
            response = requests.post(
                f"{self.dashboard_url}/api/gerar-token", 
                json={"user_id": str(user_id)},
                headers={"Content-Type": "application/json"},
                timeout=8
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro na API: Status {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Erro ao gerar link do dashboard: {e}")
            return None

async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /dashboard - Gera link para acessar o dashboard web"""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Enviar mensagem de carregamento
        loading_msg = await update.message.reply_text(
            "🔄 Gerando seu link personalizado do dashboard...",
            parse_mode='HTML'
        )
        
        dashboard_handler = DashboardHandler()
        
        # Verificar se dashboard está online
        if not await dashboard_handler.verificar_dashboard_online():
            await loading_msg.edit_text(
                "❌ <b>Dashboard Indisponível</b>\n\n"
                "O dashboard web está temporariamente fora do ar.\n"
                "Tente novamente em alguns minutos.\n\n"
                "💡 <i>Você pode usar /relatorio para ver seus dados em formato texto.</i>",
                parse_mode='HTML'
            )
            return
        
        # Gerar link personalizado
        link_data = await dashboard_handler.gerar_link_dashboard(user_id)
        
        if not link_data:
            # Fallback: fornecer link direto sem token
            keyboard = [
                [InlineKeyboardButton("🌐 Acessar Dashboard", url=dashboard_handler.dashboard_url)],
                [InlineKeyboardButton("📱 Ver Demo", url=f"{dashboard_handler.dashboard_url}/dashboard/demo")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                "⚠️ <b>Link Temporário Indisponível</b>\n\n"
                "Não foi possível gerar um link personalizado,\n"
                "mas você pode acessar o dashboard diretamente:\n\n"
                "🌐 <b>Dashboard:</b> http://localhost:5000\n"
                "📱 <b>Demo:</b> http://localhost:5000/dashboard/demo\n\n"
                "💡 <i>Use seu ID de usuário para filtrar seus dados.</i>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
        
        # Criar mensagem com link
        token = link_data['token']
        url = link_data['url']
        expires_hours = link_data.get('expires', 24)
        
        keyboard = [
            [InlineKeyboardButton("🌐 Abrir Dashboard", url=url)],
            [InlineKeyboardButton("🔄 Gerar Novo Link", callback_data="dashboard_new_link")],
            [InlineKeyboardButton("📱 Ver Demo", url=f"{dashboard_handler.dashboard_url}/dashboard/demo")],
            [InlineKeyboardButton("❌ Fechar", callback_data="delete_message")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            f"🌐 <b>Dashboard Personalizado</b>\n\n"
            f"✅ Link gerado com sucesso!\n\n"
            f"🔗 <b>Token:</b> <code>{token}</code>\n"
            f"⏰ <b>Válido por:</b> {expires_hours} horas\n\n"
            f"📊 Acesse seus dados financeiros:\n"
            f"• 📈 Gráficos interativos\n"
            f"• 💰 Análise de gastos\n"
            f"• 🎯 Progresso de metas\n"
            f"• 📋 Relatórios detalhados\n\n"
            f"⚡ O link expira automaticamente por segurança.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erro no comando /dashboard: {e}")
        try:
            await loading_msg.edit_text(
                "❌ <b>Erro Interno</b>\n\n"
                "Ocorreu um erro inesperado.\n"
                "Tente novamente em alguns minutos.\n\n"
                "💡 <i>Use /relatorio como alternativa.</i>",
                parse_mode='HTML'
            )
        except:
            # Se não conseguir editar, enviar nova mensagem
            await update.message.reply_text(
                "❌ Erro inesperado. Tente novamente.",
                parse_mode='HTML'
            )

async def cmd_dashstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /dashstatus - Verifica status do dashboard"""
    loading_msg = await update.message.reply_text(
        "🔍 Verificando status do dashboard..."
    )
    
    dashboard_handler = DashboardHandler()
    
    # Verificar se dashboard está online
    online = await dashboard_handler.verificar_dashboard_online()
    
    if online:
        try:
            response = requests.get(f"{dashboard_handler.dashboard_url}/api/status", timeout=5)
            status_data = response.json() if response.status_code == 200 else {}
            
            uptime = status_data.get('uptime', 'N/A')
            version = status_data.get('version', 'N/A')
            active_sessions = status_data.get('active_sessions', 0)
            
            keyboard = [
                [InlineKeyboardButton("🌐 Acessar Dashboard", url=dashboard_handler.dashboard_url)],
                [InlineKeyboardButton("📱 Ver Demo", url=f"{dashboard_handler.dashboard_url}/dashboard/demo")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                f"✅ <b>Dashboard Online</b>\n\n"
                f"🌐 <b>URL:</b> {dashboard_handler.dashboard_url}\n"
                f"⚡ <b>Status:</b> Funcionando\n"
                f"⏱️ <b>Uptime:</b> {uptime}\n"
                f"🔧 <b>Versão:</b> {version}\n"
                f"👥 <b>Sessões Ativas:</b> {active_sessions}\n\n"
                f"📊 O dashboard está funcionando normalmente!",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception as e:
            await loading_msg.edit_text(
                f"⚠️ <b>Dashboard com Problemas</b>\n\n"
                f"O dashboard está online mas com problemas.\n"
                f"Erro: {str(e)[:100]}...\n\n"
                f"💡 <i>Tente usar /dashboard em alguns minutos.</i>",
                parse_mode='HTML'
            )
    else:
        await loading_msg.edit_text(
            "❌ <b>Dashboard Offline</b>\n\n"
            "O dashboard web não está respondendo.\n"
            "Possíveis causas:\n"
            "• Serviço temporariamente indisponível\n"
            "• Manutenção em andamento\n"
            "• Problema de conectividade\n\n"
            "💡 <i>Tente novamente em alguns minutos ou use /relatorio.</i>",
            parse_mode='HTML'
        )

async def dashboard_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para callbacks dos botões do dashboard"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "dashboard_new_link":
        # Regenerar link
        await cmd_dashboard(update, context)
    elif query.data == "delete_message":
        # Deletar mensagem
        await query.delete_message()
