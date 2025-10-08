#!/usr/bin/env python3
"""
🎮 SPX GAMIFICATION - Sistema de Conquistas e Metas SPX
Gamificação específica para entregadores
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, and_

from database.database import get_db
from models import EntregaSPX, MetaSPX, Conquista, ConquistaUsuario
from .spx_service import SPXService

logger = logging.getLogger(__name__)

class SPXGamification:
    """Sistema de gamificação para SPX"""
    
    # Conquistas específicas do SPX
    CONQUISTAS_SPX = {
        'spx_primeira_entrega': {
            'nome': '🔰 Primeira Entrega',
            'descricao': 'Registrou sua primeira entrega no SPX',
            'xp_recompensa': 50
        },
        'spx_streak_7': {
            'nome': '🔥 Semana Completa',
            'descricao': '7 dias consecutivos de entregas',
            'xp_recompensa': 200
        },
        'spx_streak_30': {
            'nome': '🏆 Mês Dedicado',
            'descricao': '30 dias de registros no SPX',
            'xp_recompensa': 500
        },
        'spx_eficiencia_80': {
            'nome': '⚡ Super Eficiente',
            'descricao': 'Eficiência acima de 80% em um dia',
            'xp_recompensa': 100
        },
        'spx_lucro_diario_200': {
            'nome': '💰 Dia Dourado',
            'descricao': 'Lucro líquido acima de R$ 200 em um dia',
            'xp_recompensa': 150
        },
        'spx_meta_semanal': {
            'nome': '🎯 Meta Semanal',
            'descricao': 'Atingiu meta semanal pela primeira vez',
            'xp_recompensa': 300
        },
        'spx_meta_mensal': {
            'nome': '🌟 Meta Mensal',
            'descricao': 'Atingiu meta mensal pela primeira vez',
            'xp_recompensa': 800
        },
        'spx_economico': {
            'nome': '💚 Econômico',
            'descricao': 'Custo por km abaixo de R$ 1,00',
            'xp_recompensa': 100
        },
        'spx_km_record': {
            'nome': '🏁 Maratonista',
            'descricao': 'Recorde pessoal de quilometragem',
            'xp_recompensa': 120
        },
        'spx_produtivo': {
            'nome': '📦 Produtivo',
            'descricao': 'Mais de 50 entregas em um dia',
            'xp_recompensa': 180
        }
    }
    
    def __init__(self):
        self.service = SPXService()
    
    def verificar_conquistas(self, telegram_id: int, entrega: EntregaSPX) -> List[str]:
        """Verifica e concede conquistas baseadas na entrega"""
        conquistas_obtidas = []
        
        try:
            # Verificar primeira entrega
            if self._is_primeira_entrega(telegram_id):
                if self._conceder_conquista(telegram_id, 'spx_primeira_entrega'):
                    conquistas_obtidas.append('spx_primeira_entrega')
            
            # Verificar eficiência alta
            if entrega.eficiencia_percentual >= 80:
                if self._conceder_conquista(telegram_id, 'spx_eficiencia_80'):
                    conquistas_obtidas.append('spx_eficiencia_80')
            
            # Verificar lucro alto
            if entrega.lucro_liquido >= 200:
                if self._conceder_conquista(telegram_id, 'spx_lucro_diario_200'):
                    conquistas_obtidas.append('spx_lucro_diario_200')
            
            # Verificar economia
            if entrega.custo_por_km < 1.0:
                if self._conceder_conquista(telegram_id, 'spx_economico'):
                    conquistas_obtidas.append('spx_economico')
            
            # Verificar produtividade
            if entrega.numero_entregas and entrega.numero_entregas > 50:
                if self._conceder_conquista(telegram_id, 'spx_produtivo'):
                    conquistas_obtidas.append('spx_produtivo')
            
            # Verificar recorde de quilometragem
            if self._is_km_record(telegram_id, entrega.quilometragem):
                if self._conceder_conquista(telegram_id, 'spx_km_record'):
                    conquistas_obtidas.append('spx_km_record')
            
            # Verificar streaks
            streak_dias = self._calcular_streak(telegram_id, entrega.data)
            
            if streak_dias >= 7:
                if self._conceder_conquista(telegram_id, 'spx_streak_7'):
                    conquistas_obtidas.append('spx_streak_7')
            
            if streak_dias >= 30:
                if self._conceder_conquista(telegram_id, 'spx_streak_30'):
                    conquistas_obtidas.append('spx_streak_30')
            
            return conquistas_obtidas
            
        except Exception as e:
            logger.error(f"Erro ao verificar conquistas SPX: {e}")
            return []
    
    def verificar_conquistas_meta(self, telegram_id: int, tipo_meta: str, atingida: bool) -> List[str]:
        """Verifica conquistas relacionadas a metas"""
        conquistas_obtidas = []
        
        if not atingida:
            return conquistas_obtidas
        
        try:
            if tipo_meta == 'semanal':
                if self._conceder_conquista(telegram_id, 'spx_meta_semanal'):
                    conquistas_obtidas.append('spx_meta_semanal')
            
            elif tipo_meta == 'mensal':
                if self._conceder_conquista(telegram_id, 'spx_meta_mensal'):
                    conquistas_obtidas.append('spx_meta_mensal')
            
            return conquistas_obtidas
            
        except Exception as e:
            logger.error(f"Erro ao verificar conquistas de meta: {e}")
            return []
    
    def _is_primeira_entrega(self, telegram_id: int) -> bool:
        """Verifica se é a primeira entrega do usuário"""
        try:
            db = next(get_db())
            count = db.query(func.count(EntregaSPX.id)).filter(
                EntregaSPX.telegram_id == telegram_id
            ).scalar()
            return count == 1
        except Exception as e:
            logger.error(f"Erro ao verificar primeira entrega: {e}")
            return False
        finally:
            db.close()
    
    def _is_km_record(self, telegram_id: int, km_atual: float) -> bool:
        """Verifica se é recorde pessoal de quilometragem"""
        try:
            db = next(get_db())
            max_km = db.query(func.max(EntregaSPX.quilometragem)).filter(
                and_(
                    EntregaSPX.telegram_id == telegram_id,
                    EntregaSPX.quilometragem < km_atual  # Menor que o atual
                )
            ).scalar()
            
            return max_km is not None  # Se existe um máximo anterior, é recorde
            
        except Exception as e:
            logger.error(f"Erro ao verificar recorde de km: {e}")
            return False
        finally:
            db.close()
    
    def _calcular_streak(self, telegram_id: int, data_atual: date) -> int:
        """Calcula streak de dias consecutivos"""
        try:
            db = next(get_db())
            
            # Buscar todas as datas de entrega ordenadas
            datas = db.query(EntregaSPX.data).filter(
                EntregaSPX.telegram_id == telegram_id
            ).order_by(EntregaSPX.data.desc()).all()
            
            if not datas:
                return 0
            
            datas_lista = [d[0] for d in datas]
            
            # Calcular streak a partir da data atual
            streak = 0
            data_esperada = data_atual
            
            for data_entrega in datas_lista:
                if data_entrega == data_esperada:
                    streak += 1
                    data_esperada = data_esperada - timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Erro ao calcular streak: {e}")
            return 0
        finally:
            db.close()
    
    def _conceder_conquista(self, telegram_id: int, conquista_id: str) -> bool:
        """Concede conquista se ainda não possui"""
        try:
            db = next(get_db())
            
            # Verificar se já possui a conquista
            ja_possui = db.query(ConquistaUsuario).join(
                Conquista, ConquistaUsuario.id_conquista == Conquista.id
            ).filter(
                and_(
                    ConquistaUsuario.id_usuario == telegram_id,
                    Conquista.id == conquista_id
                )
            ).first()
            
            if ja_possui:
                return False
            
            # Verificar se a conquista existe
            conquista = db.query(Conquista).filter(Conquista.id == conquista_id).first()
            
            if not conquista:
                # Criar conquista se não existe
                dados_conquista = self.CONQUISTAS_SPX.get(conquista_id)
                if dados_conquista:
                    conquista = Conquista(
                        id=conquista_id,
                        nome=dados_conquista['nome'],
                        descricao=dados_conquista['descricao'],
                        xp_recompensa=dados_conquista['xp_recompensa']
                    )
                    db.add(conquista)
                    db.flush()
            
            # Conceder conquista
            conquista_usuario = ConquistaUsuario(
                id_usuario=telegram_id,
                id_conquista=conquista_id
            )
            
            db.add(conquista_usuario)
            db.commit()
            
            logger.info(f"Conquista {conquista_id} concedida para user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conceder conquista: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def formatar_conquistas_obtidas(self, conquistas: List[str]) -> str:
        """Formata mensagem de conquistas obtidas"""
        if not conquistas:
            return ""
        
        mensagem = "\n🏆 **CONQUISTAS DESBLOQUEADAS!**\n"
        
        for conquista_id in conquistas:
            dados = self.CONQUISTAS_SPX.get(conquista_id)
            if dados:
                mensagem += f"• {dados['nome']} (+{dados['xp_recompensa']} XP)\n"
                mensagem += f"  _{dados['descricao']}_\n"
        
        return mensagem
    
    def get_ranking_spx(self, telegram_id: int, periodo: str = 'mensal') -> Dict[str, any]:
        """Retorna ranking SPX por período"""
        try:
            db = next(get_db())
            
            # Calcular período
            hoje = date.today()
            if periodo == 'semanal':
                inicio = hoje - timedelta(days=hoje.weekday())
                fim = inicio + timedelta(days=6)
            elif periodo == 'mensal':
                inicio = date(hoje.year, hoje.month, 1)
                if hoje.month == 12:
                    fim = date(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    fim = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
            else:  # all time
                inicio = date(2020, 1, 1)
                fim = hoje
            
            # Query ranking por lucro líquido
            ranking = db.query(
                EntregaSPX.telegram_id,
                func.sum(EntregaSPX.ganhos_brutos - EntregaSPX.combustivel - EntregaSPX.outros_gastos).label('lucro_total'),
                func.sum(EntregaSPX.quilometragem).label('km_total'),
                func.count(EntregaSPX.id).label('dias_trabalhados')
            ).filter(
                and_(
                    EntregaSPX.data >= inicio,
                    EntregaSPX.data <= fim
                )
            ).group_by(EntregaSPX.telegram_id).order_by(
                func.sum(EntregaSPX.ganhos_brutos - EntregaSPX.combustivel - EntregaSPX.outros_gastos).desc()
            ).limit(10).all()
            
            # Encontrar posição do usuário
            posicao_usuario = None
            for i, linha in enumerate(ranking, 1):
                if linha.telegram_id == telegram_id:
                    posicao_usuario = i
                    break
            
            # Se usuário não está no top 10, buscar sua posição
            if posicao_usuario is None:
                ranking_completo = db.query(
                    EntregaSPX.telegram_id,
                    func.sum(EntregaSPX.ganhos_brutos - EntregaSPX.combustivel - EntregaSPX.outros_gastos).label('lucro_total')
                ).filter(
                    and_(
                        EntregaSPX.data >= inicio,
                        EntregaSPX.data <= fim
                    )
                ).group_by(EntregaSPX.telegram_id).order_by(
                    func.sum(EntregaSPX.ganhos_brutos - EntregaSPX.combustivel - EntregaSPX.outros_gastos).desc()
                ).all()
                
                for i, linha in enumerate(ranking_completo, 1):
                    if linha.telegram_id == telegram_id:
                        posicao_usuario = i
                        break
            
            return {
                'ranking': ranking,
                'posicao_usuario': posicao_usuario,
                'periodo': periodo,
                'inicio': inicio,
                'fim': fim
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar ranking SPX: {e}")
            return {'ranking': [], 'posicao_usuario': None}
        finally:
            db.close()

# Instância global
spx_gamification = SPXGamification()
