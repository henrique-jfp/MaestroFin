# models.py
# models.py
from datetime import datetime, timezone, time
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey, BigInteger, Boolean, Date, Time, JSON, Float, Text, func
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    nome_completo = Column(String, nullable=True)
    perfil_investidor = Column(String, nullable=True)
    horario_notificacao = Column(Time, default=time(hour=9, minute=0))
    email_notificacao = Column(String, nullable=True)
    alerta_gastos_ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # --- CAMPOS DE GAMIFICAÇÃO ---
    xp = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    streak_dias = Column(Integer, default=0, nullable=False)
    ultimo_login = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    
    lancamentos = relationship("Lancamento", back_populates="usuario", cascade="all, delete-orphan")
    contas = relationship("Conta", back_populates="usuario", cascade="all, delete-orphan")
    objetivos = relationship("Objetivo", back_populates="usuario", cascade="all, delete-orphan")
    agendamentos = relationship("Agendamento", back_populates="usuario", cascade="all, delete-orphan")
    conquistas = relationship("ConquistaUsuario", back_populates="usuario", cascade="all, delete-orphan")

class Conquista(Base):
    __tablename__ = 'conquistas'
    id = Column(String, primary_key=True) # Ex: 'primeiro_passo', 'fotografo'
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    xp_recompensa = Column(Integer, nullable=False)

class ConquistaUsuario(Base):
    __tablename__ = 'conquistas_usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    id_conquista = Column(String, ForeignKey('conquistas.id'), nullable=False)
    data_conquista = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="conquistas")
    conquista = relationship("Conquista")


class Objetivo(Base):
    __tablename__ = 'objetivos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    descricao = Column(String, nullable=False)
    valor_meta = Column(Numeric(12, 2), nullable=False)
    valor_atual = Column(Numeric(12, 2), default=0.0)
    data_meta = Column(Date, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="objetivos")

# --- TABELA DE CONTAS REFORMULADA ---
class Conta(Base):
    __tablename__ = 'contas'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    nome = Column(String, nullable=False) # Ex: "Nubank", "Inter Gold"
    tipo = Column(String, nullable=False) # "Conta Corrente", "Cartão de Crédito", "Carteira Digital", "Outro"
    
    # Campos específicos para Cartão de Crédito
    dia_fechamento = Column(Integer, nullable=True)
    dia_vencimento = Column(Integer, nullable=True)
    limite_cartao = Column(Numeric(12, 2), nullable=True)
    email_notificacao = Column(String, nullable=True)
    
    usuario = relationship("Usuario", back_populates="contas")
    lancamentos = relationship("Lancamento", back_populates="conta")

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)
    
    subcategorias = relationship("Subcategoria", back_populates="categoria", cascade="all, delete-orphan")
    lancamentos = relationship("Lancamento", back_populates="categoria")

class Subcategoria(Base):
    __tablename__ = 'subcategorias'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    id_categoria = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    
    categoria = relationship("Categoria", back_populates="subcategorias")
    lancamentos = relationship("Lancamento", back_populates="subcategoria")

class Lancamento(Base):
    __tablename__ = 'lancamentos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String)
    valor = Column(Numeric(10, 2), nullable=False)
    tipo = Column(String, nullable=False)
    data_transacao = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    forma_pagamento = Column(String) # Será preenchido com o nome da conta/cartão
    documento_fiscal = Column(String, nullable=True)
    
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    id_conta = Column(Integer, ForeignKey('contas.id'), nullable=True) # Link para a conta/cartão usado
    id_categoria = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    id_subcategoria = Column(Integer, ForeignKey('subcategorias.id'), nullable=True)
    
    usuario = relationship("Usuario", back_populates="lancamentos")
    conta = relationship("Conta", back_populates="lancamentos")
    categoria = relationship("Categoria", back_populates="lancamentos")
    subcategoria = relationship("Subcategoria", back_populates="lancamentos")
    itens = relationship("ItemLancamento", back_populates="lancamento", cascade="all, delete-orphan")

class ItemLancamento(Base):
    __tablename__ = 'itens_lancamento'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_lancamento = Column(Integer, ForeignKey('lancamentos.id'), nullable=False)
    nome_item = Column(String, nullable=False)
    quantidade = Column(Numeric(10, 3))
    valor_unitario = Column(Numeric(10, 2))
    
    lancamento = relationship("Lancamento", back_populates="itens")

class Agendamento(Base):
    __tablename__ = 'agendamentos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)
    tipo = Column(String, nullable=False)
    
    id_categoria = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    id_subcategoria = Column(Integer, ForeignKey('subcategorias.id'), nullable=True)
    
    data_primeiro_evento = Column(Date, nullable=False)
    frequencia = Column(String, nullable=False)
    
    total_parcelas = Column(Integer, nullable=True)
    parcela_atual = Column(Integer, default=0)
    
    proxima_data_execucao = Column(Date, nullable=False, index=True)
    ativo = Column(Boolean, default=True, index=True)
    
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="agendamentos")
    categoria = relationship("Categoria")
    subcategoria = relationship("Subcategoria")

class EntregaSPX(Base):
    __tablename__ = 'entregas_spx'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    data = Column(Date, default=func.current_date(), nullable=False, index=True)
    
    # Dados financeiros
    ganhos_brutos = Column(Float, nullable=False)
    combustivel = Column(Float, nullable=False)
    outros_gastos = Column(Float, default=0.0)  # estacionamento, pedágio, manutenção
    
    # Dados operacionais
    quilometragem = Column(Float, nullable=False)
    horas_trabalhadas = Column(Float)  # opcional
    numero_entregas = Column(Integer)  # opcional
    
    # Dados do veículo/combustível
    tipo_combustivel = Column(String(20), default='gasolina')  # gasolina, etanol, gnv, flex
    consumo_medio = Column(Float)  # km/l ou km/m³
    
    # Observações
    observacoes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Propriedades calculadas
    @property
    def lucro_liquido(self):
        """Lucro líquido do dia"""
        return self.ganhos_brutos - self.combustivel - self.outros_gastos
    
    @property
    def custo_por_km(self):
        """Custo total por quilômetro"""
        if self.quilometragem == 0:
            return 0
        return (self.combustivel + self.outros_gastos) / self.quilometragem
    
    @property
    def eficiencia_percentual(self):
        """Percentual de eficiência (lucro/ganhos)"""
        if self.ganhos_brutos == 0:
            return 0
        return (self.lucro_liquido / self.ganhos_brutos) * 100
    
    @property
    def ganho_por_km(self):
        """Ganho bruto por quilômetro"""
        if self.quilometragem == 0:
            return 0
        return self.ganhos_brutos / self.quilometragem
    
    @property
    def ganho_por_entrega(self):
        """Ganho médio por entrega"""
        if not self.numero_entregas or self.numero_entregas == 0:
            return 0
        return self.ganhos_brutos / self.numero_entregas
    
    @property
    def lucro_por_hora(self):
        """Lucro por hora trabalhada"""
        if not self.horas_trabalhadas or self.horas_trabalhadas == 0:
            return 0
        return self.lucro_liquido / self.horas_trabalhadas
    
    @property
    def consumo_estimado(self):
        """Estimativa de combustível consumido (se tem consumo_medio)"""
        if not self.consumo_medio or self.consumo_medio == 0:
            return None
        return self.quilometragem / self.consumo_medio
    
    def __repr__(self):
        return f"<EntregaSPX(data={self.data}, lucro=R${self.lucro_liquido:.2f}, km={self.quilometragem})>"

class MetaSPX(Base):
    __tablename__ = 'metas_spx'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    
    # Tipo de meta
    tipo = Column(String(20), nullable=False)  # 'diaria', 'semanal', 'mensal'
    
    # Valores alvo
    meta_lucro_liquido = Column(Float)
    meta_quilometragem = Column(Float)
    meta_eficiencia = Column(Float)  # percentual
    meta_ganhos_brutos = Column(Float)
    
    # Período (para metas semanais/mensais)
    ano = Column(Integer)
    mes = Column(Integer)  # para metas mensais
    semana = Column(Integer)  # para metas semanais
    
    # Status
    ativa = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MetaSPX(tipo={self.tipo}, lucro_meta=R${self.meta_lucro_liquido})>"


# ==================== TOKEN AUTENTICAÇÃO COM BANCOS ====================

class UserBankToken(Base):
    """Armazena tokens de autenticação com bancos de forma segura (criptografado)"""
    __tablename__ = 'user_bank_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False, index=True)
    banco = Column(String(20), nullable=False)  # 'inter', 'itau', 'bradesco', etc
    
    # Token criptografado (nunca plain text!)
    encrypted_token = Column(Text, nullable=False)
    token_type = Column(String(50), nullable=False)  # 'isafe', 'itoken', 'cpf_token', 'bearer', etc
    
    # Metadata
    conectado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_acesso = Column(DateTime, nullable=True)
    ativo = Column(Boolean, default=True, index=True)
    
    # Relacionamento com usuário
    usuario = relationship("Usuario", backref="bank_tokens")
    
    def __repr__(self):
        return f"<UserBankToken(usuario_id={self.id_usuario}, banco={self.banco}, tipo={self.token_type})>"