#!/usr/bin/env python3
"""
🎯 SPX METAS - Sistema de Metas e Desafios SPX
Gestão de metas e objetivos para entregadores
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_

from database.database import get_db
from models import EntregaSPX, MetaSPX
from .spx_service import SPXService
from .spx_gamification import spx_gamification

logger = logging.getLogger(__name__)

class SPXMetasService:
    """Serviço de metas SPX"""
    
    TIPOS_META = {
        'lucro_diario': {
            'nome': '💰 Lucro Diário',
            'descricao': 'Meta de lucro líquido por dia',
            'unidade': 'R$',
            'minimo': 50,
            'maximo': 1000
        },
        'lucro_semanal': {
            'nome': '📅 Lucro Semanal',
            'descricao': 'Meta de lucro líquido por semana',
            'unidade': 'R$',
            'minimo': 200,
            'maximo': 5000
        },
        'lucro_mensal': {
            'nome': '🗓️ Lucro Mensal',
            'descricao': 'Meta de lucro líquido por mês',
            'unidade': 'R$',
            'minimo': 800,
            'maximo': 20000
        },
        'eficiencia_media': {
            'nome': '⚡ Eficiência Média',
            'descricao': 'Meta de eficiência média do período',
            'unidade': '%',
            'minimo': 40,
            'maximo': 95
        },
        'km_periodo': {
            'nome': '🛣️ Quilometragem',
            'descricao': 'Meta de quilometragem no período',
            'unidade': 'km',
            'minimo': 100,
            'maximo': 5000
        },
        'entregas_periodo': {
            'nome': '📦 Entregas',
            'descricao': 'Meta de número de entregas',
            'unidade': 'entregas',
            'minimo': 50,
            'maximo': 2000
        }
    }
    
    def __init__(self):
        self.spx_service = SPXService()
    
    def criar_meta(self, telegram_id: int, tipo_meta: str, valor_meta: float, 
                   data_inicio: date, data_fim: date, descricao: str = None) -> MetaSPX:
        """Cria nova meta SPX"""
        try:
            db = next(get_db())
            
            # Validar tipo de meta
            if tipo_meta not in self.TIPOS_META:
                raise ValueError(f"Tipo de meta inválido: {tipo_meta}")
            
            # Validar valor
            tipo_info = self.TIPOS_META[tipo_meta]
            if valor_meta < tipo_info['minimo'] or valor_meta > tipo_info['maximo']:
                raise ValueError(f"Valor deve estar entre {tipo_info['minimo']} e {tipo_info['maximo']}")
            
            # Validar datas
            if data_inicio >= data_fim:
                raise ValueError("Data de início deve ser anterior à data fim")
            
            # Verificar se já existe meta ativa para o período
            meta_existente = db.query(MetaSPX).filter(
                and_(
                    MetaSPX.telegram_id == telegram_id,
                    MetaSPX.tipo_meta == tipo_meta,
                    MetaSPX.ativo == True,
                    or_(
                        and_(MetaSPX.data_inicio <= data_inicio, MetaSPX.data_fim >= data_inicio),
                        and_(MetaSPX.data_inicio <= data_fim, MetaSPX.data_fim >= data_fim),
                        and_(MetaSPX.data_inicio >= data_inicio, MetaSPX.data_fim <= data_fim)
                    )
                )
            ).first()
            
            if meta_existente:
                raise ValueError(f"Já existe uma meta {tipo_info['nome']} ativa para este período")
            
            # Criar meta
            meta = MetaSPX(
                telegram_id=telegram_id,
                tipo_meta=tipo_meta,
                valor_meta=valor_meta,
                data_inicio=data_inicio,
                data_fim=data_fim,
                descricao=descricao,
                ativo=True,
                criado_em=datetime.now()
            )
            
            db.add(meta)
            db.commit()
            db.refresh(meta)
            
            logger.info(f"Meta SPX criada: {tipo_meta} - {valor_meta} para user {telegram_id}")
            return meta
            
        except Exception as e:
            logger.error(f"Erro ao criar meta SPX: {e}")
            db.rollback()
            raise e
        finally:
            db.close()
    
    def atualizar_progresso_metas(self, telegram_id: int, data_entrega: date = None):
        """Atualiza progresso de todas as metas ativas"""
        if data_entrega is None:
            data_entrega = date.today()
        
        try:
            db = next(get_db())
            
            # Buscar metas ativas para a data
            metas_ativas = db.query(MetaSPX).filter(
                and_(
                    MetaSPX.telegram_id == telegram_id,
                    MetaSPX.ativo == True,
                    MetaSPX.data_inicio <= data_entrega,
                    MetaSPX.data_fim >= data_entrega
                )
            ).all()
            
            metas_atualizadas = []
            
            for meta in metas_ativas:
                progresso_anterior = meta.progresso_atual
                novo_progresso = self._calcular_progresso(meta, db)
                
                if novo_progresso != progresso_anterior:
                    meta.progresso_atual = novo_progresso
                    meta.atualizado_em = datetime.now()
                    
                    # Verificar se meta foi atingida
                    if not meta.atingida and novo_progresso >= meta.valor_meta:
                        meta.atingida = True
                        meta.data_atingida = date.today()
                        
                        # Conceder conquistas de meta
                        if meta.tipo_meta.endswith('_semanal'):
                            conquistas = spx_gamification.verificar_conquistas_meta(
                                telegram_id, 'semanal', True
                            )
                        elif meta.tipo_meta.endswith('_mensal'):
                            conquistas = spx_gamification.verificar_conquistas_meta(
                                telegram_id, 'mensal', True
                            )
                    
                    metas_atualizadas.append(meta)
            
            db.commit()
            return metas_atualizadas
            
        except Exception as e:
            logger.error(f"Erro ao atualizar progresso das metas: {e}")
            db.rollback()
            return []
        finally:
            db.close()
    
    def _calcular_progresso(self, meta: MetaSPX, db) -> float:
        """Calcula progresso atual da meta"""
        try:
            # Base query para o período da meta
            base_query = db.query(EntregaSPX).filter(
                and_(
                    EntregaSPX.telegram_id == meta.telegram_id,
                    EntregaSPX.data >= meta.data_inicio,
                    EntregaSPX.data <= meta.data_fim
                )
            )
            
            if meta.tipo_meta in ['lucro_diario', 'lucro_semanal', 'lucro_mensal']:
                # Somar lucro líquido
                lucro_total = base_query.with_entities(
                    func.sum(
                        EntregaSPX.ganhos_brutos - 
                        EntregaSPX.combustivel - 
                        func.coalesce(EntregaSPX.outros_gastos, 0)
                    )
                ).scalar() or 0
                return float(lucro_total)
                
            elif meta.tipo_meta == 'eficiencia_media':
                # Calcular eficiência média
                entregas = base_query.all()
                if not entregas:
                    return 0
                
                eficiencias = []
                for entrega in entregas:
                    if entrega.quilometragem > 0:
                        lucro = entrega.ganhos_brutos - entrega.combustivel - (entrega.outros_gastos or 0)
                        eficiencia = (lucro / entrega.quilometragem) * 100
                        eficiencias.append(max(0, eficiencia))  # Não permitir eficiência negativa
                
                return sum(eficiencias) / len(eficiencias) if eficiencias else 0
                
            elif meta.tipo_meta == 'km_periodo':
                # Somar quilometragem
                km_total = base_query.with_entities(
                    func.sum(EntregaSPX.quilometragem)
                ).scalar() or 0
                return float(km_total)
                
            elif meta.tipo_meta == 'entregas_periodo':
                # Somar entregas
                entregas_total = base_query.with_entities(
                    func.sum(func.coalesce(EntregaSPX.numero_entregas, 0))
                ).scalar() or 0
                return float(entregas_total)
            
            return 0
            
        except Exception as e:
            logger.error(f"Erro ao calcular progresso da meta {meta.id}: {e}")
            return 0
    
    def get_metas_ativas(self, telegram_id: int) -> List[MetaSPX]:
        """Retorna metas ativas do usuário"""
        try:
            db = next(get_db())
            
            metas = db.query(MetaSPX).filter(
                and_(
                    MetaSPX.telegram_id == telegram_id,
                    MetaSPX.ativo == True,
                    MetaSPX.data_fim >= date.today()
                )
            ).order_by(MetaSPX.data_inicio.asc()).all()
            
            return metas
            
        except Exception as e:
            logger.error(f"Erro ao buscar metas ativas: {e}")
            return []
        finally:
            db.close()
    
    def get_historico_metas(self, telegram_id: int, limit: int = 10) -> List[MetaSPX]:
        """Retorna histórico de metas"""
        try:
            db = next(get_db())
            
            metas = db.query(MetaSPX).filter(
                MetaSPX.telegram_id == telegram_id
            ).order_by(MetaSPX.criado_em.desc()).limit(limit).all()
            
            return metas
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de metas: {e}")
            return []
        finally:
            db.close()
    
    def desativar_meta(self, meta_id: int, telegram_id: int) -> bool:
        """Desativa uma meta"""
        try:
            db = next(get_db())
            
            meta = db.query(MetaSPX).filter(
                and_(
                    MetaSPX.id == meta_id,
                    MetaSPX.telegram_id == telegram_id
                )
            ).first()
            
            if not meta:
                return False
            
            meta.ativo = False
            meta.atualizado_em = datetime.now()
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao desativar meta: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def formatar_resumo_metas(self, metas: List[MetaSPX]) -> str:
        """Formata resumo das metas"""
        if not metas:
            return "📋 **Suas Metas SPX**\n\n_Nenhuma meta ativa encontrada._\n\n💡 Use /spx_meta para criar sua primeira meta!"
        
        mensagem = "📋 **Suas Metas SPX**\n\n"
        
        for meta in metas:
            tipo_info = self.TIPOS_META.get(meta.tipo_meta, {})
            nome = tipo_info.get('nome', meta.tipo_meta)
            unidade = tipo_info.get('unidade', '')
            
            # Calcular percentual
            percentual = (meta.progresso_atual / meta.valor_meta * 100) if meta.valor_meta > 0 else 0
            percentual = min(100, percentual)  # Máximo 100%
            
            # Status
            if meta.atingida:
                status_icon = "✅"
                status_text = "ATINGIDA!"
            elif percentual >= 80:
                status_icon = "🔥"
                status_text = "Quase lá!"
            elif percentual >= 50:
                status_icon = "💪"
                status_text = "No caminho"
            else:
                status_icon = "🎯"
                status_text = "Começando"
            
            # Barra de progresso visual
            barra_progresso = self._criar_barra_progresso(percentual)
            
            # Período
            periodo = f"{meta.data_inicio.strftime('%d/%m')} - {meta.data_fim.strftime('%d/%m')}"
            
            mensagem += f"{status_icon} **{nome}**\n"
            mensagem += f"🎯 Meta: {meta.valor_meta:.1f} {unidade}\n"
            mensagem += f"📊 Atual: {meta.progresso_atual:.1f} {unidade}\n"
            mensagem += f"{barra_progresso} {percentual:.1f}%\n"
            mensagem += f"📅 {periodo} • _{status_text}_\n\n"
        
        return mensagem
    
    def _criar_barra_progresso(self, percentual: float) -> str:
        """Cria barra de progresso visual"""
        blocos_cheios = int(percentual / 10)
        barra = "█" * blocos_cheios + "░" * (10 - blocos_cheios)
        return f"[{barra}]"
    
    def get_sugestoes_metas(self, telegram_id: int) -> Dict[str, any]:
        """Gera sugestões de metas baseadas no histórico"""
        try:
            # Buscar dados dos últimos 30 dias
            relatorio = self.spx_service.gerar_relatorio(telegram_id, 'mensal')
            
            if not relatorio or not relatorio.get('entregas'):
                return {
                    'tem_dados': False,
                    'sugestoes': [],
                    'recomendacao': "Registre algumas entregas primeiro para receber sugestões personalizadas!"
                }
            
            estatisticas = relatorio['estatisticas']
            
            # Gerar sugestões baseadas na performance
            sugestoes = []
            
            # Meta de lucro diário (10-20% acima da média)
            if estatisticas['lucro_liquido_medio'] > 0:
                meta_lucro = estatisticas['lucro_liquido_medio'] * 1.15
                sugestoes.append({
                    'tipo': 'lucro_diario',
                    'valor': round(meta_lucro, 2),
                    'justificativa': f"15% acima da sua média atual de R$ {estatisticas['lucro_liquido_medio']:.2f}"
                })
            
            # Meta de eficiência (5-10% acima da atual)
            if estatisticas['eficiencia_media'] > 0:
                meta_eficiencia = min(95, estatisticas['eficiencia_media'] * 1.08)
                sugestoes.append({
                    'tipo': 'eficiencia_media',
                    'valor': round(meta_eficiencia, 1),
                    'justificativa': f"8% acima da sua eficiência atual de {estatisticas['eficiencia_media']:.1f}%"
                })
            
            # Meta de quilometragem semanal
            if estatisticas['quilometragem_total'] > 0:
                km_medio_dia = estatisticas['quilometragem_total'] / max(1, len(relatorio['entregas']))
                meta_km_semanal = km_medio_dia * 7 * 1.1
                sugestoes.append({
                    'tipo': 'km_periodo',
                    'valor': round(meta_km_semanal),
                    'justificativa': f"Baseado na sua média de {km_medio_dia:.1f} km/dia"
                })
            
            return {
                'tem_dados': True,
                'sugestoes': sugestoes,
                'estatisticas': estatisticas,
                'recomendacao': "Sugestões baseadas na sua performance dos últimos 30 dias:"
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões de metas: {e}")
            return {
                'tem_dados': False,
                'sugestoes': [],
                'recomendacao': "Erro ao analisar seu histórico. Tente novamente."
            }

# Instância global
spx_metas_service = SPXMetasService()
