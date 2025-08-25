#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Dashboard Handler - MaestroFin
Handler para integração do dashboard com o bot do Telegram
"""

import os
# Importar analytics
try:
    from analytics.bot_analytics import BotAnalytics
    from analytics.advanced_analytics import advanced_analytics
    analytics = BotAnalytics()
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False

def track_analytics(command_name):
    """Decorator para tracking de comandos"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                try:
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True
                    )
                    logging.info(f"📊 Analytics: {username} usou /{command_name}")
                except Exception as e:
                    logging.error(f"❌ Erro no analytics: {e}")
            
            return await func(update, context)
        return wrapper
    return decorator

import logging
import requests
import traceback
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard_handler.log')
    ]
)
logger = logging.getLogger(__name__)

class DashboardHandler:
    """Handler para funcionalidades do dashboard"""
    
    def __init__(self, dashboard_url: str = None):
        # 🚀 CORREÇÃO: Usar variável de ambiente para a URL base do dashboard.
        # Isso torna o código portátil e configurável para qualquer ambiente.
        # Fallback para localhost para desenvolvimento local.
        self.dashboard_url = os.getenv(
            'DASHBOARD_BASE_URL', 
            'http://localhost:5000'
        )
        if dashboard_url: # Permite sobrescrever, se necessário
            self.dashboard_url = dashboard_url
        else:
            logger.info(f"✅ URL do Dashboard configurada para: {self.dashboard_url}")
    
    def verificar_dashboard_online(self) -> bool:
        """Verifica se o dashboard está online"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/status", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao verificar dashboard: {e}")
            return False
    
    async def gerar_link_dashboard(self, user_id: int) -> dict:
        """Gera link temporário para acesso ao dashboard"""
        try:
            response = requests.get(
                f"{self.dashboard_url}/api/gerar-token/{user_id}", 
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
    loading_msg = None
    try:
        logger.info(f"Comando /dashboard iniciado para usuário {update.effective_user.id}")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Enviar mensagem de carregamento - usar effective_message para compatibilidade
        try:
            loading_msg = await update.effective_message.reply_text(
                "🔄 Gerando seu link personalizado do dashboard...",
                parse_mode='HTML'
            )
            logger.info("Mensagem de carregamento enviada")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de carregamento: {e}")
            # Fallback: tentar o método alternativo
            loading_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 Gerando seu link personalizado do dashboard...",
                parse_mode='HTML'
            )
            logger.info("Mensagem de carregamento enviada via fallback")
        
        dashboard_handler = DashboardHandler()
        
        # Verificar se dashboard está online
        logger.info("Verificando se dashboard está online...")
        dashboard_online = dashboard_handler.verificar_dashboard_online()
        logger.info(f"Dashboard online: {dashboard_online}")
        
        if not dashboard_online:
            logger.warning("Dashboard está offline")
            await loading_msg.edit_text(
                "❌ <b>Dashboard Indisponível</b>\n\n"
                "O dashboard web está temporariamente fora do ar.\n"
                "Tente novamente em alguns minutos.\n\n"
                "💡 <i>Você pode usar /relatorio para ver seus dados em formato texto.</i>",
                parse_mode='HTML'
            )
            return
        
        # Gerar link personalizado
        logger.info(f"Gerando link personalizado para usuário {user_id}")
        link_data = await dashboard_handler.gerar_link_dashboard(user_id)
        logger.info(f"Link data recebido: {link_data}")
        
        if not link_data:
            logger.warning("Falha ao gerar link personalizado - usando fallback")
            # Fallback: fornecer link direto sem token
            keyboard = [
                [InlineKeyboardButton("🌐 Acessar Dashboard", url=dashboard_handler.dashboard_url)],
                [InlineKeyboardButton("📱 Ver Demo", url=f"{dashboard_handler.dashboard_url}/dashboard/demo")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                "⚠️ <b>Link Temporário Indisponível</b>\n\n"
                "Não foi possível gerar um link personalizado,\n"
                "mas você pode acessar o dashboard diretamente.\n\n"
                f"🌐 <b>Dashboard:</b> {dashboard_handler.dashboard_url}\n"
                f"📱 <b>Demo:</b> {dashboard_handler.dashboard_url}/dashboard/demo\n\n"
                "💡 <i>Use seu ID de usuário para filtrar seus dados.</i>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
        
        # Criar mensagem com link
        logger.info("Criando mensagem com link personalizado")
        token = link_data['token']
        url = link_data['url']
        expires_hours = link_data.get('expires', 24)
        
        # Construir URL completa
        full_url = f"{dashboard_handler.dashboard_url}{url}"
        logger.info(f"URL completa gerada: {full_url}")
        
        # Botões sem URLs localhost (Telegram rejeita localhost em botões inline)
        keyboard = [
            [InlineKeyboardButton("🔄 Gerar Novo Link", callback_data="dashboard_new_link")],
            [InlineKeyboardButton("❌ Fechar", callback_data="delete_message")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            f"🌐 <b>Dashboard Personalizado</b>\n\n"
            f"✅ Link gerado com sucesso!\n\n"
            f"🔗 <b>Acesse seu dashboard:</b>\n"
            f"<code>{full_url}</code>\n\n"
            f"🆔 <b>Token:</b> <code>{token}</code>\n"
            f"⏰ <b>Válido por:</b> {expires_hours} horas\n\n"
            f"📊 <b>O que você encontrará:</b>\n"
            f"• 📈 Gráficos interativos\n"
            f"• 💰 Análise de gastos\n"
            f"• 🎯 Progresso de metas\n"
            f"• 📋 Relatórios detalhados\n\n"
            f"⚡ O link expira automaticamente por segurança.\n\n"
            f"💡 <b>Dica:</b> Toque no link acima para copiar e abrir no navegador.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        logger.info("Comando /dashboard executado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no comando /dashboard: {e}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        try:
            if loading_msg:
                await loading_msg.edit_text(
                    "❌ <b>Erro Interno</b>\n\n"
                    "Ocorreu um erro inesperado.\n"
                    "Tente novamente em alguns minutos.\n\n"
                    "💡 <i>Use /relatorio como alternativa.</i>",
                    parse_mode='HTML'
                )
            else:
                # Se não conseguiu criar loading_msg, usar context.bot
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ <b>Erro Interno</b>\n\n"
                         "Ocorreu um erro inesperado.\n"
                         "Tente novamente em alguns minutos.\n\n"
                         "💡 <i>Use /relatorio como alternativa.</i>",
                    parse_mode='HTML'
                )
        except Exception as edit_error:
            logger.error(f"Erro ao editar mensagem de erro: {edit_error}")
            # Se não conseguir editar, enviar nova mensagem via context.bot
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Erro inesperado. Tente novamente.",
                    parse_mode='HTML'
                )
            except Exception as reply_error:
                logger.error(f"Erro ao enviar mensagem de erro: {reply_error}")

async def cmd_dashstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /dashstatus - Verifica status do dashboard"""
    loading_msg = await update.message.reply_text(
        "🔍 Verificando status do dashboard..."
    )
    
    dashboard_handler = DashboardHandler()
    
    # Verificar se dashboard está online
    online = dashboard_handler.verificar_dashboard_online()
    
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

@track_analytics("dashboard")
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
