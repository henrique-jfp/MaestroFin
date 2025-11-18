# database/database.py
import logging
from typing import List
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Lancamento, Usuario, Categoria, Subcategoria, Objetivo
from datetime import datetime, timedelta
import config
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_
from models import Lancamento, Usuario, Categoria, Subcategoria, Objetivo, ItemLancamento

class DatabaseError(Exception):
    """Exceção personalizada para erros de banco de dados."""
    pass

class ServiceError(Exception):
    """Exceção personalizada para erros de serviço interno (regra de negócio, processamento, etc)."""
    pass

# --- Configuração da Conexão com SQLAlchemy ---
engine = None
SessionLocal = None
_last_check_time = None
_last_check_result = False
_last_check_error: str | None = None

try:
    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada em config.py")

    engine = create_engine(config.DATABASE_URL, client_encoding='utf8')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with engine.connect() as connection:
        logging.info("✅ Conexão com o banco de dados estabelecida com sucesso!")

except Exception as e:
    logging.critical(f"❌ ERRO CRÍTICO AO CONFIGURAR O BANCO DE DADOS: {e}")
    engine = None


def is_db_available(ttl_seconds: int = 30) -> bool:
    """Retorna True se o banco estiver acessível.

    Implementa um cache simples (TTL) para evitar abrir conexão a cada chamada
    do endpoint /bot_status. Em caso de falha, registra a última mensagem de erro.
    """
    import time
    global _last_check_time, _last_check_result, _last_check_error

    # Cache TTL
    now = time.time()
    if _last_check_time and (now - _last_check_time) < ttl_seconds:
        return _last_check_result

    if engine is None:
        _last_check_time = now
        _last_check_result = False
        _last_check_error = "engine_not_initialized"
        return False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _last_check_result = True
        _last_check_error = None
    except Exception as e:
        _last_check_result = False
        _last_check_error = str(e)
        logging.warning(f"⚠️ Verificação de disponibilidade do DB falhou: {e}")
    finally:
        _last_check_time = now

    return _last_check_result


def get_db_error() -> str | None:
    """Retorna a última mensagem de erro registrada por is_db_available."""
    return _last_check_error


def deletar_todos_dados_usuario(telegram_id: int) -> bool:
    """
    Encontra um usuário pelo seu telegram_id e deleta o registro dele.
    Devido ao cascade, todos os dados associados (lançamentos, metas, etc.)
    serão deletados automaticamente.
    
    IMPORTANTE: Também deleta conexões bancárias na API Pluggy (Open Finance).
    """
    db = next(get_db())
    try:
        # Encontra o usuário para garantir que ele exista
        usuario_a_deletar = db.query(Usuario).filter(Usuario.telegram_id == telegram_id).first()
        
        if not usuario_a_deletar:
            logging.warning(f"⚠️ Tentativa de deletar dados de um usuário inexistente: {telegram_id}")
            return False
        
        logging.info(f"🗑️ Iniciando deleção COMPLETA do usuário {telegram_id} (DB ID: {usuario_a_deletar.id})...")
        
        # ==================== DELETAR CONEXÕES OPEN FINANCE ====================
        try:
            from models import PluggyItem, PluggyAccount, PluggyTransaction
            from gerente_financeiro.open_finance_oauth_handler import pluggy_request
            
            # Buscar todos os items do usuário
            pluggy_items = db.query(PluggyItem).filter(PluggyItem.id_usuario == usuario_a_deletar.id).all()
            
            if pluggy_items:
                logging.info(f"🔄 Deletando {len(pluggy_items)} conexão(ões) Open Finance do usuário {telegram_id}...")
                
                # 1. Deletar na API Pluggy (isso remove tudo na Pluggy)
                for item in pluggy_items:
                    try:
                        pluggy_request("DELETE", f"/items/{item.pluggy_item_id}")
                        logging.info(f"✅ Item {item.pluggy_item_id} ({item.connector_name}) deletado na Pluggy")
                    except Exception as e:
                        logging.warning(f"⚠️ Erro ao deletar item {item.pluggy_item_id} na Pluggy: {e}")
                
            # 2. Deletar do banco LOCAL na ORDEM CORRETA (evitar FK violation)
            item_ids = [item.id for item in pluggy_items]
            
            # 2.1. Primeiro: pluggy_transactions (referencia pluggy_accounts via id_account)
            deleted_txns = db.query(PluggyTransaction).filter(
                PluggyTransaction.id_account.in_(
                    db.query(PluggyAccount.id).filter(PluggyAccount.id_item.in_(item_ids))
                )
            ).delete(synchronize_session=False)
            logging.info(f"✅ {deleted_txns} transações Open Finance deletadas")
            
            # 2.2. Segundo: pluggy_accounts (referencia pluggy_items via id_item)
            deleted_accounts = db.query(PluggyAccount).filter(
                PluggyAccount.id_item.in_(item_ids)
            ).delete(synchronize_session=False)
            logging.info(f"✅ {deleted_accounts} contas Open Finance deletadas")
            
            # 2.3. Terceiro: pluggy_items (agora sem dependências)
            deleted_items = db.query(PluggyItem).filter(
                PluggyItem.id_usuario == usuario_a_deletar.id
            ).delete(synchronize_session=False)
            logging.info(f"✅ {deleted_items} conexões Open Finance deletadas")
            db.flush()  # Aplica as mudanças imediatamente
        
        except ImportError:
            logging.info("ℹ️ Tabelas Open Finance ainda não existem, pulando deleção...")
        except Exception as e:
            logging.error(f"❌ Erro ao deletar conexões Open Finance: {e}", exc_info=True)
            db.rollback()
            raise  # Re-raise para abortar a deleção completa
        
        # ==================== DELETAR TOKENS BANCÁRIOS (user_bank_tokens) ====================
        # Alguns tokens bancários (ex: tokens de OAuth/Pluggy) podem estar em tabelas
        # auxiliares que referenciam diretamente "usuarios" sem ON DELETE CASCADE.
        # Para evitar ForeignKeyViolation ao deletar o usuário, limpamos essas
        # tabelas explicitamente aqui.

        try:
            # Usamos SQL direto porque a tabela pode não ter modelo SQLAlchemy
            deleted_tokens = db.execute(
                text("DELETE FROM user_bank_tokens WHERE id_usuario = :id_usuario"),
                {"id_usuario": usuario_a_deletar.id}
            ).rowcount
            logging.info(f"✅ {deleted_tokens} tokens bancários (user_bank_tokens) deletados")
            db.flush()
        except Exception as e:
            # Em caso de erro, fazemos rollback e abortamos a deleção completa
            logging.error(
                f"❌ Erro ao deletar tokens bancários (user_bank_tokens) do usuário {telegram_id}: {e}",
                exc_info=True,
            )
            db.rollback()
            raise

        # ==================== DELETAR USUÁRIO ====================
        # A mágica acontece aqui! Cascade deleta:
        # - lancamentos, contas, objetivos, agendamentos, conquistas_usuario
        # - pluggy_items → pluggy_accounts → pluggy_transactions (cascade)
        
        logging.info(f"🔥 Deletando usuário {telegram_id} do banco...")
        db.delete(usuario_a_deletar)
        db.commit()
        db.flush()  # Garante que a deleção foi persistida
        
        # Verificar se realmente foi deletado
        verificacao = db.query(Usuario).filter(Usuario.telegram_id == telegram_id).first()
        if verificacao:
            logging.error(f"❌ ERRO: Usuário {telegram_id} ainda existe após deleção!")
            db.rollback()
            return False
        
        logging.info(f"✅ SUCESSO: Todos os dados do usuário {telegram_id} foram deletados permanentemente!")
        logging.info(f"   📊 Lançamentos: deletados (cascade)")
        logging.info(f"   🎯 Metas: deletadas (cascade)")
        logging.info(f"   📅 Agendamentos: deletados (cascade)")
        logging.info(f"   🏦 Conexões Open Finance: deletadas na API + banco")
        logging.info(f"   🎮 Gamificação: deletada (cascade)")
        logging.info(f"   ⚙️ Configurações: deletadas (cascade)")
        
        return True
            
    except Exception as e:
        db.rollback()
        logging.error(f"❌ Erro CRÍTICO ao deletar dados do usuário {telegram_id}: {e}", exc_info=True)
        return False
    finally:
        db.close()    

# --- Funções Auxiliares ---
def criar_tabelas():
    if not engine:
        logging.error("Engine do banco de dados não inicializada. Tabelas não podem ser criadas.")
        return
    try:
        logging.info("Verificando e criando tabelas a partir dos modelos...")
        Base.metadata.create_all(bind=engine)
        logging.info("Tabelas prontas.")
    except Exception as e:
        logging.error(f"Erro ao criar tabelas: {e}")

def get_db():
    """Fornece uma sessão do banco de dados."""
    if not SessionLocal:
        logging.error("A sessão do banco de dados não foi inicializada.")
        raise ConnectionError("A conexão com o banco de dados falhou na inicialização.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db_session: Session, telegram_id: int, full_name: str) -> Usuario:
    """Busca um usuário pelo telegram_id ou cria um novo se não existir."""
    user = db_session.query(Usuario).filter(Usuario.telegram_id == telegram_id).first()
    if not user:
        logging.info(f"Criando novo usuário para telegram_id: {telegram_id}")
        user = Usuario(telegram_id=telegram_id, nome_completo=full_name)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

def popular_dados_iniciais(db_session: Session):
    """
    Verifica e popula o banco com categorias e subcategorias padrão,
    garantindo que não haja duplicatas e adicionando novas se necessário.
    """
    logging.info("Verificando e populando categorias e subcategorias padrão...")

    # Dicionário de categorias e suas subcategorias padrão
    categorias_padrao = {
        "Moradia": ["Aluguel", "Condomínio", "Contas (Luz, Água, Gás)", "Manutenção/Reforma"],
        "Alimentação": ["Supermercado", "Restaurante/Delivery"],
        "Transporte": ["Combustível", "App de Transporte", "Transporte Público", "Manutenção Veicular"],
        "Saúde": ["Farmácia", "Consulta Médica", "Plano de Saúde"],
        "Lazer": ["Cinema/Streaming", "Viagens", "Hobbies", "Eventos/Shows"],
        "Educação": ["Cursos", "Livros/Material"],
        "Serviços": ["Assinaturas (Internet, Celular)", "Serviços Profissionais"],
        "Compras": ["Roupas e Acessórios", "Eletrônicos", "Casa e Decoração"],
        "Receitas": ["Salário", "Freelance", "Vendas", "Rendimentos", "Outras Receitas"],
        "Investimentos": ["Aporte", "Resgate"],
        # --- CATEGORIAS ESPECIAIS PARA ANÁLISE AUTOMÁTICA ---
        "Transferência": ["Entre Contas", "PIX Enviado", "PIX Recebido"],
        "Financeiro": ["Juros", "Taxas Bancárias", "Empréstimos"],
        "Outros": ["Presentes", "Doações", "Despesas não categorizadas"]
    }

    # (O resto da função continua exatamente igual)
    for nome_cat, subs in categorias_padrao.items():
        categoria_obj = db_session.query(Categoria).filter(func.lower(Categoria.nome) == func.lower(nome_cat)).first()
        if not categoria_obj:
            categoria_obj = Categoria(nome=nome_cat)
            db_session.add(categoria_obj)
            db_session.commit()
            db_session.refresh(categoria_obj)
            logging.info(f"Categoria '{nome_cat}' criada.")

        for nome_sub in subs:
            subcategoria_obj = db_session.query(Subcategoria).filter(
                and_(Subcategoria.id_categoria == categoria_obj.id, func.lower(Subcategoria.nome) == func.lower(nome_sub))
            ).first()
            if not subcategoria_obj:
                nova_sub = Subcategoria(nome=nome_sub, id_categoria=categoria_obj.id)
                db_session.add(nova_sub)
                logging.info(f"Subcategoria '{nome_sub}' criada para '{nome_cat}'.")

    db_session.commit()
    logging.info("Verificação de dados iniciais concluída.")
    

def criar_novo_objetivo(telegram_user_id: int, descricao: str, valor_meta: float, data_final: datetime.date) -> Objetivo | str | None:
    db = next(get_db())
    try:
        usuario = db.query(Usuario).filter(Usuario.telegram_id == telegram_user_id).first()
        if not usuario:
            logging.error(f"Usuário com telegram_id {telegram_user_id} não encontrado para criar objetivo.")
            return None
        meta_existente = db.query(Objetivo).filter(
            Objetivo.id_usuario == usuario.id,
            func.lower(Objetivo.descricao) == func.lower(descricao)
        ).first()
        if meta_existente:
            logging.warning(f"Tentativa de criar meta duplicada: '{descricao}' para o usuário {telegram_user_id}")
            return "DUPLICATE"
        novo_objetivo = Objetivo(
            id_usuario=usuario.id,
            descricao=descricao,
            valor_meta=valor_meta,
            data_meta=data_final,
            valor_atual=0.0
        )
        db.add(novo_objetivo)
        db.commit()
        db.refresh(novo_objetivo)
        logging.info(f"Novo objetivo '{descricao}' criado para o usuário {telegram_user_id}.")
        return novo_objetivo
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao criar objetivo no DB: {e}", exc_info=True)
        return None
    finally:
        db.close()

def listar_objetivos_usuario(telegram_user_id: int):
    db = next(get_db())
    try:
        usuario = db.query(Usuario).filter(Usuario.telegram_id == telegram_user_id).first()
        if not usuario:
            return []
        return db.query(Objetivo).filter(Objetivo.id_usuario == usuario.id).order_by(Objetivo.data_meta.asc()).all()
    finally:
        db.close()

def deletar_objetivo_por_id(objetivo_id: int, telegram_user_id: int) -> bool:
    db = next(get_db())
    try:
        objetivo_para_deletar = db.query(Objetivo).join(Usuario).filter(
            Objetivo.id == objetivo_id,
            Usuario.telegram_id == telegram_user_id
        ).first()
        if objetivo_para_deletar:
            db.delete(objetivo_para_deletar)
            db.commit()
            logging.info(f"Objetivo {objetivo_id} deletado com sucesso pelo usuário {telegram_user_id}.")
            return True
        else:
            logging.warning(f"Falha ao deletar objetivo {objetivo_id}. Motivo: Não encontrado ou permissão negada para o usuário {telegram_user_id}.")
            return False
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao deletar objetivo {objetivo_id} no DB: {e}", exc_info=True)
        return False
    finally:
        db.close()

# --- FUNÇÕES ADICIONADAS PARA OS ALERTAS ---

def listar_todos_objetivos_ativos():
    """Busca todos os objetivos de todos os usuários que ainda estão ativos."""
    db = next(get_db())
    try:
        return db.query(Objetivo).join(Usuario).filter(Objetivo.data_meta >= datetime.now().date()).all()
    except Exception as e:
        logging.error(f"Erro ao listar todos os objetivos ativos: {e}", exc_info=True)
        return []
    finally:
        db.close()

def atualizar_valor_objetivo(objetivo_id: int, novo_valor: float):
    """Atualiza o valor atual de um objetivo."""
    db = next(get_db())
    try:
        objetivo = db.query(Objetivo).filter(Objetivo.id == objetivo_id).first()
        if objetivo:
            objetivo.valor_atual = novo_valor
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao atualizar valor do objetivo {objetivo_id}: {e}", exc_info=True)
        return False
    finally:
        db.close()

def atualizar_objetivo_por_id(objetivo_id: int, telegram_user_id: int, novo_valor: float, nova_data: datetime.date) -> Objetivo | None:
    """Atualiza o valor e a data de uma meta específica."""
    db = next(get_db())
    try:
        # Garante que o usuário só pode editar suas próprias metas
        objetivo_para_atualizar = db.query(Objetivo).join(Usuario).filter(
            Objetivo.id == objetivo_id,
            Usuario.telegram_id == telegram_user_id
        ).first()

        if objetivo_para_atualizar:
            objetivo_para_atualizar.valor_meta = novo_valor
            objetivo_para_atualizar.data_meta = nova_data
            db.commit()
            db.refresh(objetivo_para_atualizar)
            logging.info(f"Objetivo {objetivo_id} atualizado com sucesso pelo usuário {telegram_user_id}.")
            return objetivo_para_atualizar
        else:
            logging.warning(f"Falha ao atualizar objetivo {objetivo_id}. Motivo: Não encontrado ou permissão negada para o usuário {telegram_user_id}.")
            return None
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao atualizar objetivo {objetivo_id} no DB: {e}", exc_info=True)
        return None
    finally:
        db.close()

def buscar_lancamentos_usuario(
    telegram_user_id: int,
    limit: int = 10,
    query: str = None,
    lancamento_id: int = None,
    categoria_nome: str = None,
    data_inicio: datetime = None,
    data_fim: datetime = None,
    tipo: str = None,
    id_conta: int = None,
    forma_pagamento: str = None
) -> List[Lancamento]:
    """
    Busca lançamentos para um usuário, com filtros avançados.
    """
    db = next(get_db())
    try:
        # Busca o usuário para garantir que ele existe
        usuario = db.query(Usuario).filter(Usuario.telegram_id == telegram_user_id).first()
        if not usuario:
            return []

        # Inicia a query base, já otimizando para carregar os relacionamentos
        base_query = db.query(Lancamento).filter(Lancamento.id_usuario == usuario.id).options(
            joinedload(Lancamento.categoria),
            joinedload(Lancamento.subcategoria),
            joinedload(Lancamento.itens)
        )

        # --- APLICAÇÃO CORRETA E INDEPENDENTE DOS FILTROS ---

        # Filtro 1: Por tipo ('Entrada' ou 'Saída')
        if tipo:
            base_query = base_query.filter(Lancamento.tipo == tipo)

        # Filtro 2: Por ID específico do lançamento
        if lancamento_id:
            base_query = base_query.filter(Lancamento.id == lancamento_id)

        # Filtro 3: Por texto de busca (na descrição ou nos itens)
        if query:
            base_query = base_query.outerjoin(Lancamento.itens).filter(
                (Lancamento.descricao.ilike(f'%{query}%')) |
                (Lancamento.itens.any(ItemLancamento.nome_item.ilike(f'%{query}%')))
            )

        # Filtro 4: Por nome da categoria
        if categoria_nome:
            base_query = base_query.join(Lancamento.categoria).filter(
                Categoria.nome.ilike(f'%{categoria_nome}%')
            )

        # Filtro 5: Por data de início
        if data_inicio:
            base_query = base_query.filter(Lancamento.data_transacao >= data_inicio)

        # Filtro 6: Por data de fim
        if data_fim:
            base_query = base_query.filter(Lancamento.data_transacao <= data_fim)

        # Filtro 7: Por ID da conta (se necessário)
        if id_conta:
            base_query = base_query.filter(Lancamento.id_conta == id_conta)

        if id_conta:
            base_query = base_query.filter(Lancamento.id_conta == id_conta)

        if forma_pagamento:
            # Usamos ilike para ser case-insensitive (não importa se é 'pix' ou 'PIX')
            base_query = base_query.filter(Lancamento.forma_pagamento.ilike(f'%{forma_pagamento}%'))        

        # Retorna o resultado final, ordenado por data e com limite aplicado.
        # O .distinct() é crucial para evitar duplicatas quando há join com os itens.
        return base_query.distinct().order_by(Lancamento.data_transacao.desc()).limit(limit).all()

    except Exception as e:
        logging.error(f"Erro ao buscar lançamentos no banco de dados: {e}", exc_info=True)
        return []
    finally:
        db.close()

def atualizar_lancamento_por_id(lancamento_id: int, telegram_user_id: int, dados: dict):
    """Atualiza um lançamento específico, verificando a permissão do usuário."""
    db = next(get_db())
    try:
        lancamento = db.query(Lancamento).join(Usuario).filter(
            Lancamento.id == lancamento_id,
            Usuario.telegram_id == telegram_user_id
        ).first()
        
        if lancamento:
            for key, value in dados.items():
                setattr(lancamento, key, value)
            db.commit()
            return lancamento
        return None
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao atualizar lançamento {lancamento_id}: {e}", exc_info=True)
        return None
    finally:
        db.close()

def deletar_lancamento_por_id(lancamento_id: int, telegram_user_id: int) -> bool:
    """Deleta um lançamento específico, verificando a permissão do usuário."""
    db = next(get_db())
    try:
        lancamento = db.query(Lancamento).join(Usuario).filter(
            Lancamento.id == lancamento_id,
            Usuario.telegram_id == telegram_user_id
        ).first()
        
        if lancamento:
            db.delete(lancamento)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao deletar lançamento {lancamento_id}: {e}", exc_info=True)
        return False
    finally:
        db.close()

async def verificar_transacao_duplicada(user_id: int, descricao: str, valor: float, data_transacao: str) -> bool:
    """
    Verifica se uma transação específica já existe no banco.
    Critério: mesmo usuário + mesma descrição + mesmo valor + mesma data
    """
    db = next(get_db())
    try:
        from datetime import datetime
        data_obj = datetime.strptime(data_transacao, '%d/%m/%Y')
        
        # 🎯 BUSCA PRECISA: Mesmo usuário, descrição, valor e data
        query = text("""
            SELECT COUNT(*) as count 
            FROM lancamentos l 
            JOIN usuarios u ON l.id_usuario = u.id 
            WHERE u.telegram_id = :user_id 
            AND l.descricao = :descricao
            AND l.valor = :valor 
            AND DATE(l.data_transacao) = :data_transacao
        """)
        
        result = db.execute(query, {
            'user_id': user_id,
            'descricao': descricao,
            'valor': valor,
            'data_transacao': data_obj.date()
        }).scalar()
        
        return result > 0
        
    except Exception as e:
        logging.warning(f"Erro ao verificar transação duplicada: {e}")
        return False  # Em caso de erro, permitir o processamento
    finally:
        db.close()  # 🔧 CORREÇÃO: Sempre fechar a conexão


async def verificar_fatura_recente(user_id: int, file_name: str, file_size: int) -> bool:
    """
    🗑️ FUNÇÃO DEPRECADA - Mantida apenas para compatibilidade.
    Agora usamos verificação por transação individual.
    """
    return False  # Sempre permite processamento