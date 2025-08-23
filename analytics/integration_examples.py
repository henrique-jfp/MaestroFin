"""
Exemplo de como integrar o sistema de analytics no MaestroFin Bot
"""

from datetime import datetime
from analytics.bot_analytics import analytics, track_command
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from telegram import Update

# EXEMPLO 1: Usando decorator para rastrear comandos automaticamente
@track_command("/start")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando start com tracking automático"""
    user = update.effective_user
    
    # Seu código normal do comando
    await update.message.reply_text(f"Olá {user.first_name}! Bem-vindo ao MaestroFin!")
    
    # O decorator já registra automaticamente:
    # - ID do usuário
    # - Nome do comando
    # - Tempo de execução
    # - Se foi sucesso ou erro
    # - Timestamp

# EXEMPLO 2: Tracking manual para eventos específicos
async def donation_button_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quando usuário clica no botão de doação"""
    user = update.effective_user
    
    # Registrar que usuário chegou até a doação
    analytics.track_donation_event(
        user_id=user.id,
        username=user.username or user.first_name,
        event_type="donation_clicked",
        metadata={
            "source": "help_menu",
            "user_level": context.user_data.get("level", 1)
        }
    )
    
    await update.message.reply_text("Obrigado pelo interesse em apoiar o projeto!")

# EXEMPLO 3: Tracking de doação completada
async def process_donation(user_id: int, username: str, amount: float, payment_method: str):
    """Quando uma doação é efetivamente completada"""
    analytics.track_donation_event(
        user_id=user_id,
        username=username,
        event_type="donation_completed",
        amount=amount,
        metadata={
            "payment_method": payment_method,
            "timestamp": datetime.now().isoformat()
        }
    )

# EXEMPLO 4: Tracking de erro customizado
@track_command("/grafico")
async def grafico_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de gráfico com error handling customizado"""
    try:
        user = update.effective_user
        
        # Seu código de geração de gráfico
        # ... código do gráfico ...
        
        await update.message.reply_text("Gráfico gerado com sucesso!")
        
    except Exception as e:
        # Log erro específico com contexto
        analytics.log_error(
            error_type="GraficoGenerationError",
            error_message=str(e),
            user_id=update.effective_user.id,
            username=update.effective_user.username,
            command="/grafico",
            metadata={
                "chart_type": context.args[0] if context.args else "default",
                "user_data_size": len(str(context.user_data)),
            }
        )
        
        await update.message.reply_text("Ops! Erro ao gerar gráfico. Já estamos cientes do problema!")
        raise

# EXEMPLO 5: Tracking de funcionalidades específicas
def track_feature_usage(feature_name: str, user_id: int, username: str, success: bool = True, **kwargs):
    """Helper para tracking de features específicas"""
    analytics.track_command_usage(
        user_id=user_id,
        username=username,
        command=f"feature:{feature_name}",
        success=success,
        parameters=kwargs
    )

# EXEMPLO 6: Middleware para tracking global
class AnalyticsMiddleware:
    """Middleware para capturar todas as interações"""
    
    @staticmethod
    async def pre_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Executado antes de processar qualquer comando"""
        if update.message and update.message.text:
            user = update.effective_user
            
            # Detectar se é mensagem de doação
            if "doar" in update.message.text.lower() or "doação" in update.message.text.lower():
                analytics.track_donation_event(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    event_type="donation_message_shown"
                )

# EXEMPLO 7: Integração com o bot principal
def setup_analytics_in_bot(application):
    """Configurar analytics no bot principal"""
    
    # Adicionar middleware
    application.add_handler(
        MessageHandler(filters.ALL, AnalyticsMiddleware.pre_process),
        group=-1  # Executa antes de outros handlers
    )
    
    # Handlers já com decorators de tracking
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("grafico", grafico_command))
    
    # Callback para botões de doação
    application.add_handler(CallbackQueryHandler(
        donation_button_clicked, 
        pattern="^donation_"
    ))

# EXEMPLO 8: Sistema de alertas baseado em analytics
async def check_system_health():
    """Verificar saúde do sistema baseado em métricas"""
    
    # Verificar taxa de erro
    today_stats = analytics.get_daily_stats()
    error_summary = analytics.get_error_summary(days_back=1)
    
    total_commands = today_stats['total_commands']
    total_errors = len(error_summary['recent_errors'])
    
    if total_commands > 0:
        error_rate = (total_errors / total_commands) * 100
        
        if error_rate > 10:  # Mais de 10% de erro
            # Enviar alerta para admin
            print(f"🚨 ALERTA: Taxa de erro alta: {error_rate:.1f}%")
            
    # Verificar comandos que não estão funcionando
    commands_stats = analytics.get_commands_ranking(days=1)
    for cmd in commands_stats:
        if cmd['errors'] > cmd['successes']:
            print(f"⚠️ Comando {cmd['command']} com muitos erros")

# EXEMPLO 9: Relatório diário automático
def generate_daily_report():
    """Gerar relatório diário de uso"""
    stats = analytics.get_daily_stats()
    donation_stats = analytics.get_donation_stats()
    error_summary = analytics.get_error_summary(days_back=1)
    
    report = f"""
📊 RELATÓRIO DIÁRIO - MAESTROFIN BOT
    
👥 Usuários: {stats['unique_users']}
🤖 Comandos: {stats['total_commands']}
💰 Taxa Doação: {donation_stats['conversion_rate']:.1f}%
🚨 Erros: {len(error_summary['recent_errors'])}

🏆 TOP COMANDOS:
{chr(10).join([f"  {i+1}. {cmd['command']} ({cmd['count']} usos)" 
               for i, cmd in enumerate(stats['top_commands'][:5])])}
    """
    
    return report

# EXEMPLO 10: Dashboard launch script
if __name__ == "__main__":
    """Script para iniciar dashboard analytics"""
    from analytics.dashboard_app import app
    
    print("🚀 Iniciando MaestroFin Analytics Dashboard...")
    print("📊 Acesse: http://localhost:5000")
    print("📱 Dashboard será atualizado automaticamente a cada 30s")
    
    # Iniciar servidor Flask
    app.run(debug=True, host='0.0.0.0', port=5000)
