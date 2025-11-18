-- Migration: Criar tabelas Open Finance/Pluggy
-- Data: 2025-11-18
-- Descrição: Adiciona tabelas para persistir dados do Open Finance (Pluggy)
--            e garantir deleção completa de dados do usuário incluindo conexões bancárias

-- ==================== PLUGGY ITEMS ====================
CREATE TABLE IF NOT EXISTS pluggy_items (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    
    -- Dados da Pluggy
    pluggy_item_id VARCHAR(255) UNIQUE NOT NULL,
    connector_id VARCHAR(255) NOT NULL,
    connector_name VARCHAR(255) NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL,
    status_detail TEXT,
    execution_status VARCHAR(50),
    last_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_pluggy_items_usuario ON pluggy_items(id_usuario);
CREATE INDEX IF NOT EXISTS idx_pluggy_items_pluggy_id ON pluggy_items(pluggy_item_id);

-- ==================== PLUGGY ACCOUNTS ====================
CREATE TABLE IF NOT EXISTS pluggy_accounts (
    id SERIAL PRIMARY KEY,
    id_item INTEGER NOT NULL REFERENCES pluggy_items(id) ON DELETE CASCADE,
    
    -- Dados da Pluggy
    pluggy_account_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Informações da conta
    type VARCHAR(50) NOT NULL,
    subtype VARCHAR(50),
    number VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    
    -- Saldos
    balance NUMERIC(15, 2),
    currency_code VARCHAR(3) DEFAULT 'BRL',
    credit_limit NUMERIC(15, 2),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_pluggy_accounts_item ON pluggy_accounts(id_item);
CREATE INDEX IF NOT EXISTS idx_pluggy_accounts_pluggy_id ON pluggy_accounts(pluggy_account_id);

-- ==================== PLUGGY TRANSACTIONS ====================
CREATE TABLE IF NOT EXISTS pluggy_transactions (
    id SERIAL PRIMARY KEY,
    id_account INTEGER NOT NULL REFERENCES pluggy_accounts(id) ON DELETE CASCADE,
    
    -- Dados da Pluggy
    pluggy_transaction_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Informações da transação
    description VARCHAR(500) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    date DATE NOT NULL,
    
    -- Categoria
    category VARCHAR(255),
    
    -- Status
    status VARCHAR(50),
    type VARCHAR(50),
    
    -- Merchant
    merchant_name VARCHAR(255),
    merchant_category VARCHAR(255),
    
    -- Controle de importação
    imported_to_lancamento BOOLEAN DEFAULT FALSE,
    id_lancamento INTEGER REFERENCES lancamentos(id) ON DELETE SET NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_pluggy_transactions_account ON pluggy_transactions(id_account);
CREATE INDEX IF NOT EXISTS idx_pluggy_transactions_pluggy_id ON pluggy_transactions(pluggy_transaction_id);
CREATE INDEX IF NOT EXISTS idx_pluggy_transactions_date ON pluggy_transactions(date);

-- ==================== COMENTÁRIOS ====================
COMMENT ON TABLE pluggy_items IS 'Conexões bancárias do usuário via Pluggy/Open Finance';
COMMENT ON TABLE pluggy_accounts IS 'Contas bancárias específicas dentro de cada conexão';
COMMENT ON TABLE pluggy_transactions IS 'Transações bancárias sincronizadas da Pluggy';

COMMENT ON COLUMN pluggy_items.pluggy_item_id IS 'ID único do item na API Pluggy';
COMMENT ON COLUMN pluggy_items.status IS 'Status da conexão: UPDATED, UPDATING, LOGIN_ERROR, etc';
COMMENT ON COLUMN pluggy_accounts.type IS 'Tipo de conta: BANK, CREDIT, INVESTMENT';
COMMENT ON COLUMN pluggy_accounts.subtype IS 'Subtipo: CHECKING_ACCOUNT, CREDIT_CARD, SAVINGS_ACCOUNT';
COMMENT ON COLUMN pluggy_transactions.amount IS 'Valor da transação (positivo=entrada, negativo=saída)';
COMMENT ON COLUMN pluggy_transactions.imported_to_lancamento IS 'Se a transação já foi importada para a tabela lancamentos';

-- ==================== VERIFICAÇÃO ====================
-- Verificar se as tabelas foram criadas
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name IN ('pluggy_items', 'pluggy_accounts', 'pluggy_transactions')
    ) THEN
        RAISE NOTICE '✅ Tabelas Open Finance criadas com sucesso!';
    ELSE
        RAISE EXCEPTION '❌ Erro ao criar tabelas Open Finance';
    END IF;
END $$;
