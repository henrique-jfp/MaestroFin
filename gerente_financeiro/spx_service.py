#!/usr/bin/env python3
"""
🔧 SPX SERVICE - Lógica de Negócio SPX
Gerencia operações de dados, cálculos e relatórios para entregas
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from database.database import get_db
from models import EntregaSPX, MetaSPX, MetaSPX
from analytics.advanced_analytics import advanced_analytics

logger = logging.getLogger(__name__)

class SPXService:
    """Serviços de negócio para SPX"""
    
    def criar_entrega(self, telegram_id: int, data: date = None, **kwargs) -> Optional[EntregaSPX]:
        """Cria nova entrega SPX"""
        try:
            db = next(get_db())
            
            if data is None:
                data = date.today()
            
            # Verificar se já existe entrega para essa data
            entrega_existente = db.query(EntregaSPX).filter(
                and_(
                    EntregaSPX.telegram_id == telegram_id,
                    EntregaSPX.data == data
                )
            ).first()
            
            if entrega_existente:
                # Atualizar entrega existente
                for key, value in kwargs.items():
                    if hasattr(entrega_existente, key) and value is not None:
                        setattr(entrega_existente, key, value)
                entrega_existente.updated_at = datetime.utcnow()
                entrega = entrega_existente
            else:
                # Criar nova entrega
                entrega = EntregaSPX(
                    telegram_id=telegram_id,
                    data=data,
                    **kwargs
                )
                db.add(entrega)
            
            db.commit()
            db.refresh(entrega)
            
            # Atualizar progresso das metas após criar entrega
            try:
                from .spx_metas_service import spx_metas_service
                spx_metas_service.atualizar_progresso_metas(telegram_id, data)
            except Exception as e:
                logger.warning(f"Erro ao atualizar metas após entrega: {e}")
            
            # Analytics
            advanced_analytics.track_command_usage(
                telegram_id, f"user_{telegram_id}", 
                'spx_entrega_criada', success=True
            )
            
            logger.info(f"Entrega SPX criada/atualizada para user {telegram_id} em {data}")
            return entrega
            
        except Exception as e:
            logger.error(f"Erro ao criar entrega SPX: {e}", exc_info=True)
            db.rollback()
            return None
        finally:
            db.close()
    
    def get_entrega_por_data(self, telegram_id: int, data: date) -> Optional[EntregaSPX]:
        """Busca entrega por data específica"""
        try:
            db = next(get_db())
            
            entrega = db.query(EntregaSPX).filter(
                and_(
                    EntregaSPX.telegram_id == telegram_id,
                    EntregaSPX.data == data
                )
            ).first()
            
            return entrega
            
        except Exception as e:
            logger.error(f"Erro ao buscar entrega: {e}")
            return None
        finally:
            db.close()
    
    def get_entregas_periodo(self, telegram_id: int, data_inicio: date, data_fim: date) -> List[EntregaSPX]:
        """Busca entregas em um período"""
        try:
            db = next(get_db())
            
            entregas = db.query(EntregaSPX).filter(
                and_(
                    EntregaSPX.telegram_id == telegram_id,
                    EntregaSPX.data >= data_inicio,
                    EntregaSPX.data <= data_fim
                )
            ).order_by(EntregaSPX.data.desc()).all()
            
            return entregas
            
        except Exception as e:
            logger.error(f"Erro ao buscar entregas do período: {e}")
            return []
        finally:
            db.close()
    
    def gerar_relatorio_semanal(self, telegram_id: int, data_referencia: date = None) -> Optional[Dict[str, Any]]:
        """Gera relatório da semana"""
        try:
            if data_referencia is None:
                data_referencia = date.today()
            
            # Calcular início da semana (segunda-feira)
            dias_desde_segunda = data_referencia.weekday()
            inicio_semana = data_referencia - timedelta(days=dias_desde_segunda)
            fim_semana = inicio_semana + timedelta(days=6)
            
            entregas = self.get_entregas_periodo(telegram_id, inicio_semana, fim_semana)
            
            if not entregas:
                return None
            
            # Calcular totais
            total_ganhos = sum(e.ganhos_brutos for e in entregas)
            total_combustivel = sum(e.combustivel for e in entregas)
            total_outros = sum(e.outros_gastos for e in entregas)
            total_km = sum(e.quilometragem for e in entregas)
            total_horas = sum(e.horas_trabalhadas for e in entregas if e.horas_trabalhadas)
            total_entregas = sum(e.numero_entregas for e in entregas if e.numero_entregas)
            
            lucro_total = total_ganhos - total_combustivel - total_outros
            dias_trabalhados = len(entregas)
            
            # Melhor e pior dia
            melhor_dia = max(entregas, key=lambda e: e.lucro_liquido)
            pior_dia = min(entregas, key=lambda e: e.lucro_liquido)
            
            # Médias
            media_lucro_dia = lucro_total / dias_trabalhados if dias_trabalhados > 0 else 0
            media_km_dia = total_km / dias_trabalhados if dias_trabalhados > 0 else 0
            custo_medio_km = (total_combustivel + total_outros) / total_km if total_km > 0 else 0
            eficiencia_media = (lucro_total / total_ganhos * 100) if total_ganhos > 0 else 0
            
            # Verificar meta semanal
            meta_semanal = self.get_meta_ativa(telegram_id, 'semanal')
            meta_atingida = None
            if meta_semanal and meta_semanal.meta_lucro_liquido:
                meta_atingida = lucro_total >= meta_semanal.meta_lucro_liquido
            
            return {
                'periodo': {
                    'inicio': inicio_semana,
                    'fim': fim_semana,
                    'dias_trabalhados': dias_trabalhados
                },
                'totais': {
                    'ganhos_brutos': total_ganhos,
                    'combustivel': total_combustivel,
                    'outros_gastos': total_outros,
                    'lucro_liquido': lucro_total,
                    'quilometragem': total_km,
                    'horas_trabalhadas': total_horas,
                    'numero_entregas': total_entregas
                },
                'medias': {
                    'lucro_por_dia': media_lucro_dia,
                    'km_por_dia': media_km_dia,
                    'custo_por_km': custo_medio_km,
                    'eficiencia_percentual': eficiencia_media
                },
                'extremos': {
                    'melhor_dia': {
                        'data': melhor_dia.data,
                        'lucro': melhor_dia.lucro_liquido
                    },
                    'pior_dia': {
                        'data': pior_dia.data,
                        'lucro': pior_dia.lucro_liquido
                    }
                },
                'meta': {
                    'existe': meta_semanal is not None,
                    'valor': meta_semanal.meta_lucro_liquido if meta_semanal else None,
                    'atingida': meta_atingida
                },
                'entregas': entregas
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório semanal: {e}")
            return None
    
    def gerar_relatorio_mensal(self, telegram_id: int, ano: int = None, mes: int = None) -> Optional[Dict[str, Any]]:
        """Gera relatório do mês"""
        try:
            if ano is None or mes is None:
                hoje = date.today()
                ano = hoje.year
                mes = hoje.month
            
            # Primeiro e último dia do mês
            inicio_mes = date(ano, mes, 1)
            if mes == 12:
                fim_mes = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = date(ano, mes + 1, 1) - timedelta(days=1)
            
            entregas = self.get_entregas_periodo(telegram_id, inicio_mes, fim_mes)
            
            if not entregas:
                return None
            
            # Calcular totais (similar ao semanal)
            total_ganhos = sum(e.ganhos_brutos for e in entregas)
            total_combustivel = sum(e.combustivel for e in entregas)
            total_outros = sum(e.outros_gastos for e in entregas)
            total_km = sum(e.quilometragem for e in entregas)
            lucro_total = total_ganhos - total_combustivel - total_outros
            
            dias_trabalhados = len(entregas)
            dias_no_mes = (fim_mes - inicio_mes).days + 1
            
            # Análise por semana
            semanas = self._agrupar_por_semana(entregas)
            
            # Comparar com mês anterior
            mes_anterior = mes - 1 if mes > 1 else 12
            ano_anterior = ano if mes > 1 else ano - 1
            relatorio_anterior = self.gerar_relatorio_mensal(telegram_id, ano_anterior, mes_anterior)
            
            comparativo = None
            if relatorio_anterior:
                comparativo = {
                    'variacao_lucro': ((lucro_total - relatorio_anterior['totais']['lucro_liquido']) / 
                                     relatorio_anterior['totais']['lucro_liquido'] * 100) 
                                     if relatorio_anterior['totais']['lucro_liquido'] > 0 else 0,
                    'variacao_km': ((total_km - relatorio_anterior['totais']['quilometragem']) / 
                                   relatorio_anterior['totais']['quilometragem'] * 100) 
                                   if relatorio_anterior['totais']['quilometragem'] > 0 else 0
                }
            
            # Verificar meta mensal
            meta_mensal = self.get_meta_ativa(telegram_id, 'mensal')
            meta_atingida = None
            if meta_mensal and meta_mensal.meta_lucro_liquido:
                meta_atingida = lucro_total >= meta_mensal.meta_lucro_liquido
            
            # Projeção para o final do mês (se ainda não terminou)
            hoje = date.today()
            projecao = None
            if fim_mes > hoje and dias_trabalhados > 0:
                dias_passados = (hoje - inicio_mes).days + 1
                media_diaria = lucro_total / dias_trabalhados
                dias_restantes_uteis = max(0, dias_no_mes - dias_passados)
                projecao = lucro_total + (media_diaria * dias_restantes_uteis)
            
            return {
                'periodo': {
                    'ano': ano,
                    'mes': mes,
                    'inicio': inicio_mes,
                    'fim': fim_mes,
                    'dias_trabalhados': dias_trabalhados,
                    'dias_no_mes': dias_no_mes
                },
                'totais': {
                    'ganhos_brutos': total_ganhos,
                    'combustivel': total_combustivel,
                    'outros_gastos': total_outros,
                    'lucro_liquido': lucro_total,
                    'quilometragem': total_km
                },
                'medias': {
                    'lucro_por_dia_trabalhado': lucro_total / dias_trabalhados if dias_trabalhados > 0 else 0,
                    'lucro_por_dia_mes': lucro_total / dias_no_mes,
                    'km_por_dia': total_km / dias_trabalhados if dias_trabalhados > 0 else 0
                },
                'semanas': semanas,
                'comparativo': comparativo,
                'meta': {
                    'existe': meta_mensal is not None,
                    'valor': meta_mensal.meta_lucro_liquido if meta_mensal else None,
                    'atingida': meta_atingida
                },
                'projecao': projecao,
                'entregas': entregas
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório mensal: {e}")
            return None
    
    def _agrupar_por_semana(self, entregas: List[EntregaSPX]) -> List[Dict[str, Any]]:
        """Agrupa entregas por semana"""
        semanas = {}
        
        for entrega in entregas:
            # Número da semana do ano
            ano, semana, _ = entrega.data.isocalendar()
            chave = f"{ano}-{semana:02d}"
            
            if chave not in semanas:
                semanas[chave] = {
                    'semana': semana,
                    'ano': ano,
                    'entregas': [],
                    'total_lucro': 0,
                    'total_km': 0
                }
            
            semanas[chave]['entregas'].append(entrega)
            semanas[chave]['total_lucro'] += entrega.lucro_liquido
            semanas[chave]['total_km'] += entrega.quilometragem
        
        return list(semanas.values())
    
    def gerar_insights(self, entrega: EntregaSPX) -> str:
        """Gera insights personalizados para uma entrega"""
        try:
            insights = []
            
            # Insight de eficiência
            if entrega.eficiencia_percentual >= 70:
                insights.append("🎯 Excelente eficiência! Acima de 70%")
            elif entrega.eficiencia_percentual >= 60:
                insights.append("👍 Boa eficiência! Mantenha esse ritmo")
            else:
                insights.append("⚠️ Eficiência baixa. Analise custos ou rotas")
            
            # Insight de custo por km
            if entrega.custo_por_km <= 1.0:
                insights.append("💚 Custo por km excelente!")
            elif entrega.custo_por_km <= 1.5:
                insights.append("👌 Custo por km razoável")
            else:
                insights.append("🔴 Custo por km alto. Verifique rotas")
            
            # Comparar com histórico
            historico = self.get_entregas_periodo(
                entrega.telegram_id,
                entrega.data - timedelta(days=30),
                entrega.data - timedelta(days=1)
            )
            
            if historico:
                media_lucro_historico = sum(e.lucro_liquido for e in historico) / len(historico)
                if entrega.lucro_liquido > media_lucro_historico * 1.1:
                    insights.append("📈 Lucro 10% acima da sua média!")
                elif entrega.lucro_liquido < media_lucro_historico * 0.9:
                    insights.append("📉 Lucro abaixo da média. Análise necessária")
            
            # Insight por quilometragem
            if entrega.quilometragem > 100:
                insights.append("🏁 Alto volume de km hoje!")
            
            # Insight por ganho por entrega (se informado)
            if entrega.numero_entregas and entrega.ganho_por_entrega:
                if entrega.ganho_por_entrega >= 10:
                    insights.append("💰 Ótimo ganho por entrega!")
                elif entrega.ganho_por_entrega < 7:
                    insights.append("💡 Ganho por entrega baixo. Priorize entregas melhores")
            
            if insights:
                return "💡 **Insights:**\n" + "\n".join(f"• {insight}" for insight in insights)
            else:
                return "📊 Dados registrados com sucesso!"
                
        except Exception as e:
            logger.error(f"Erro ao gerar insights: {e}")
            return "📊 Dados registrados com sucesso!"
    
    def get_meta_ativa(self, telegram_id: int, tipo: str) -> Optional[MetaSPX]:
        """Busca meta ativa por tipo"""
        try:
            db = next(get_db())
            
            meta = db.query(MetaSPX).filter(
                and_(
                    MetaSPX.telegram_id == telegram_id,
                    MetaSPX.tipo == tipo,
                    MetaSPX.ativa == True
                )
            ).first()
            
            return meta
            
        except Exception as e:
            logger.error(f"Erro ao buscar meta: {e}")
            return None
        finally:
            db.close()
    
    def criar_meta(self, telegram_id: int, tipo: str, **kwargs) -> Optional[MetaSPX]:
        """Cria nova meta SPX"""
        try:
            db = next(get_db())
            
            # Desativar metas anteriores do mesmo tipo
            db.query(MetaSPX).filter(
                and_(
                    MetaSPX.telegram_id == telegram_id,
                    MetaSPX.tipo == tipo
                )
            ).update({'ativa': False})
            
            # Criar nova meta
            meta = MetaSPX(
                telegram_id=telegram_id,
                tipo=tipo,
                ativa=True,
                **kwargs
            )
            
            db.add(meta)
            db.commit()
            db.refresh(meta)
            
            logger.info(f"Meta SPX {tipo} criada para user {telegram_id}")
            return meta
            
        except Exception as e:
            logger.error(f"Erro ao criar meta SPX: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def get_estatisticas_gerais(self, telegram_id: int) -> Dict[str, Any]:
        """Retorna estatísticas gerais do usuário"""
        try:
            db = next(get_db())
            
            # Estatísticas básicas
            total_entregas = db.query(func.count(EntregaSPX.id)).filter(
                EntregaSPX.telegram_id == telegram_id
            ).scalar() or 0
            
            if total_entregas == 0:
                return {'total_entregas': 0}
            
            # Somas totais
            somas = db.query(
                func.sum(EntregaSPX.ganhos_brutos),
                func.sum(EntregaSPX.combustivel),
                func.sum(EntregaSPX.outros_gastos),
                func.sum(EntregaSPX.quilometragem)
            ).filter(EntregaSPX.telegram_id == telegram_id).first()
            
            total_ganhos, total_combustivel, total_outros, total_km = somas
            total_lucro = (total_ganhos or 0) - (total_combustivel or 0) - (total_outros or 0)
            
            # Primeira e última entrega
            primeira_entrega = db.query(EntregaSPX).filter(
                EntregaSPX.telegram_id == telegram_id
            ).order_by(EntregaSPX.data.asc()).first()
            
            ultima_entrega = db.query(EntregaSPX).filter(
                EntregaSPX.telegram_id == telegram_id
            ).order_by(EntregaSPX.data.desc()).first()
            
            # Melhor dia
            melhor_entrega = db.query(EntregaSPX).filter(
                EntregaSPX.telegram_id == telegram_id
            ).order_by(desc(EntregaSPX.ganhos_brutos - EntregaSPX.combustivel - EntregaSPX.outros_gastos)).first()
            
            dias_ativos = (ultima_entrega.data - primeira_entrega.data).days + 1 if primeira_entrega and ultima_entrega else 1
            
            return {
                'total_entregas': total_entregas,
                'dias_registrados': dias_ativos,
                'primeira_entrega': primeira_entrega.data if primeira_entrega else None,
                'ultima_entrega': ultima_entrega.data if ultima_entrega else None,
                'totais': {
                    'ganhos_brutos': total_ganhos or 0,
                    'combustivel': total_combustivel or 0,
                    'outros_gastos': total_outros or 0,
                    'lucro_liquido': total_lucro,
                    'quilometragem': total_km or 0
                },
                'medias': {
                    'lucro_por_dia': total_lucro / total_entregas if total_entregas > 0 else 0,
                    'km_por_dia': (total_km or 0) / total_entregas if total_entregas > 0 else 0,
                    'eficiencia_geral': (total_lucro / (total_ganhos or 1)) * 100
                },
                'recordes': {
                    'melhor_lucro': melhor_entrega.lucro_liquido if melhor_entrega else 0,
                    'melhor_data': melhor_entrega.data if melhor_entrega else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar estatísticas: {e}")
            return {'total_entregas': 0}
        finally:
            db.close()
