"""
Sistema de Jobs e Tarefas Agendadas - MaestroFin
"""
import logging
from datetime import datetime, time
from telegram.ext import ContextTypes
from alerts import agendar_notificacoes_diarias, checar_objetivos_semanal

logger = logging.getLogger(__name__)

def configurar_jobs(job_queue):
    """Configura todos os jobs agendados do sistema"""
    try:
        logger.info("⚙️ Configurando jobs agendados...")
        
        # Job diário às 01:00 - Agendamento de notificações
        job_queue.run_daily(
            agendar_notificacoes_diarias,
            time=time(hour=1, minute=0),
            name="agendador_mestre_diario"
        )
        
        # Job semanal aos sábados às 10:00 - Verificar objetivos
        job_queue.run_daily(
            checar_objetivos_semanal,
            time=time(hour=10, minute=0),
            days=(6,),  # Sábado
            name="checar_metas_semanalmente"
        )
        
        logger.info("✅ Jobs agendados configurados com sucesso:")
        logger.info("   📅 Notificações diárias: 01:00")
        logger.info("   🎯 Verificação de metas: Sábado 10:00")
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar jobs: {e}")
