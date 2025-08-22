# 🎼 MaestroFin - Maestro das Suas Finanças

> **Seu Assistente Financeiro Inteligente no Telegram com IA Generativa**

[![Python](https://img.shields.io/badge/Python-3.12+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)
[![AI](https://img.shields.io/badge/Google-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://gemini.google.com)
[![License](https://img.shields.io/badge/License-Dual-yellow?style=for-the-badge)](./LICENSE)

---

## 📋 Índice

- [🎯 Sobre o Projeto](#-sobre-o-projeto)
- [✨ Funcionalidades Principais](#-funcionalidades-principais)
- [🎬 Demonstração](#-demonstração)
- [🏗️ Arquitetura Técnica](#️-arquitetura-técnica)
- [🛠️ Tecnologias Utilizadas](#️-tecnologias-utilizadas)
- [⚡ Instalação e Configuração](#-instalação-e-configuração)
- [📱 Como Usar](#-como-usar)
- [📊 Estrutura do Banco de Dados](#-estrutura-do-banco-de-dados)
- [🤖 Inteligência Artificial](#-inteligência-artificial)
- [🔒 Segurança e Privacidade](#-segurança-e-privacidade)
- [🧪 Desenvolvimento](#-desenvolvimento)
- [📈 Roadmap](#-roadmap)
- [📄 Licença](#-licença)
- [📞 Contato](#-contato)

---

## 🎯 Sobre o Projeto

**MaestroFin** é um bot de Telegram revolucionário para controle financeiro pessoal que combina **Inteligência Artificial Generativa**, **OCR avançado** e **análise de dados** para transformar a forma como você gerencia suas finanças.

### 🌟 **Por que MaestroFin?**

- **🧠 IA Conversacional**: Converse naturalmente sobre suas finanças
- **📸 OCR Inteligente**: Extraia dados de faturas em PDF automaticamente  
- **📊 Análises Avançadas**: Gráficos, relatórios e insights personalizados
- **⚡ Automação Total**: Categorização, agendamentos e alertas automáticos
- **🔒 Privacidade Máxima**: Seus dados ficam no seu servidor

### 🎪 **Casos de Uso**

- **Freelancers**: Controle de receitas e despesas profissionais
- **Estudantes**: Gestão de mesada e gastos universitários  
- **Famílias**: Orçamento doméstico e planejamento financeiro
- **Investidores**: Acompanhamento de carteira e metas
- **Empresários**: Análise de fluxo de caixa pessoal

---

## ✨ Funcionalidades Principais

### 💬 **Gerenciamento Conversacional**
```
👤 "Gastei R$ 45 no almoço no McDonald's"
🤖 "Registrado! Categoria: Alimentação → Fast Food. 
    Você já gastou R$ 230 em alimentação este mês."
```

### 📸 **OCR para Faturas de Cartão**
- **Upload de PDF**: Envie fatura do cartão em PDF
- **Extração Automática**: Sistema detecta banco (Bradesco, Caixa, etc.)
- **Categorização IA**: Gemini categoriza cada transação automaticamente
- **Importação em Lote**: Centenas de transações em segundos

### 📊 **Relatórios e Análises**
- **Gráficos Interativos**: Pizza, barras, linhas temporais
- **Análise de Tendências**: Gastos por categoria ao longo do tempo
- **Comparativos**: Este mês vs mês anterior
- **Projeções**: Estimativas baseadas em padrões históricos

### 🎯 **Sistema de Metas**
- **Metas Mensais**: Limite de gastos por categoria
- **Acompanhamento**: Progresso em tempo real
- **Alertas Inteligentes**: Notificações quando próximo do limite
- **Análise de Impacto**: "Se economizar R$ 100/mês, em 1 ano terá R$ 1.200"

### 📅 **Agendamentos e Automação**
- **Lançamentos Recorrentes**: Salário, aluguel, assinaturas
- **Notificações Personalizadas**: Horário configurável
- **Lembretes**: Pagamentos, vencimentos, metas

### 🔍 **Integração com Dados Externos**
- **Cotações**: Dólar, Euro, Bitcoin
- **Indicadores**: IPCA, Selic, CDI
- **Ações**: Preços de ações brasileiras

---

## 🎬 Demonstração

### 📱 **Interface Principal**
```
🎼 MAESTRO FINANCEIRO

Olá! Eu sou seu assistente financeiro pessoal.

📊 RESUMO RÁPIDO
💰 Saldo atual: R$ 2.847,50
📈 Receitas (mês): R$ 4.500,00  
📉 Despesas (mês): R$ 1.652,50
🎯 Meta mensal: 67% atingida

🚀 O que posso fazer por você?

🔹 /gerente - Menu principal
🔹 /fatura - Importar fatura de cartão
🔹 /grafico - Gerar gráficos
🔹 /relatorio - Relatório detalhado
🔹 /metas - Gerenciar metas
```

### 💬 **Conversa Natural**
```
👤: "Comprei um livro por R$ 35"

🤖: "✅ Lançamento registrado!
    📚 Categoria: Educação → Livros
    💰 Valor: R$ 35,00
    📅 Data: Hoje
    
    📊 Resumo da categoria Educação:
    • Este mês: R$ 135,00 (3 lançamentos)
    • Meta mensal: R$ 200,00 (67% usado)
    • Ainda pode gastar: R$ 65,00"
```

### 📸 **Processamento de Fatura**
```
👤: [Envia PDF da fatura do cartão]

🤖: "📄 Fatura recebida! Processando...
    
    ✅ Análise concluída!
    🏦 Banco: Bradesco detectado
    📊 Encontrei 47 transações válidas
    💰 Total: R$ 1.247,83
    
    🎯 A qual cartão pertence esta fatura?
    
    [💳 Bradesco Mastercard]
    [💳 Nubank Roxinho]"
```

---

## 🏗️ Arquitetura Técnica

### 🎨 **Design Patterns Utilizados**

#### **1. MVC (Model-View-Controller)**
```python
# Model (models.py)
class Lancamento(Base):
    __tablename__ = 'lancamentos'
    id = Column(Integer, primary_key=True)
    valor = Column(Float, nullable=False)
    
# View (Telegram Interface)
await update.message.reply_text("💰 Lançamento criado!")

# Controller (handlers.py)  
async def criar_lancamento(update, context):
    # Lógica de negócio
```

#### **2. Repository Pattern**
```python
class LancamentoRepository:
    def get_by_user(self, user_id: int) -> List[Lancamento]:
        return self.db.query(Lancamento).filter_by(id_usuario=user_id).all()
```

#### **3. Factory Pattern**
```python
def create_conversation_handler(handler_type: str) -> ConversationHandler:
    # Cria handlers específicos baseado no tipo
```

### 🔄 **Fluxo de Dados**

```mermaid
graph TD
    A[👤 Usuário Telegram] --> B[🤖 Bot Handler]
    B --> C[🧠 Processamento IA]
    C --> D[💾 Banco de Dados]
    D --> E[📊 Análise/Relatório]
    E --> F[📱 Resposta ao Usuário]
    
    G[📸 Upload PDF] --> H[🔍 OCR Processing]
    H --> I[🏷️ Categorização IA]
    I --> D
```

### 🗂️ **Estrutura Modular**

```
📦 MaestroFin/
├── 🤖 bot.py                 # Ponto de entrada principal
├── ⚙️ config.py              # Configurações centralizadas
├── 📊 models.py              # Modelos de dados (ORM)
├── 🔔 alerts.py              # Sistema de alertas
├── 📈 jobs.py                # Tarefas agendadas
├── 
├── 🗄️ database/
│   └── database.py           # Conexão e operações DB
├── 
├── 🎯 gerente_financeiro/    # Módulo principal
│   ├── 🎮 handlers.py        # Manipuladores de comandos
│   ├── 🧠 services.py        # Lógica de negócio
│   ├── 💬 prompts.py         # Prompts para IA
│   ├── 📊 graficos.py        # Geração de gráficos
│   ├── 📄 fatura_handler.py  # Processamento de faturas
│   ├── 🎯 metas_handler.py   # Gestão de metas
│   ├── 📅 agendamentos_handler.py # Agendamentos
│   ├── ✏️ manual_entry_handler.py # Entrada manual
│   ├── 📈 relatorio_handler.py    # Relatórios
│   ├── ⚙️ onboarding_handler.py   # Configuração inicial
│   ├── 🔧 editing_handler.py      # Edição de dados
│   ├── 📞 contact_handler.py      # Contato/suporte
│   ├── 🗑️ delete_user_handler.py # Exclusão de dados
│   ├── 📊 extrato_handler.py      # Extratos bancários
│   ├── 🔍 ocr_handler.py          # OCR de imagens
│   ├── 🌐 external_data.py        # APIs externas
│   ├── 📧 utils_email.py          # Utilitários de email
│   ├── 📅 utils_google_calendar.py # Google Calendar
│   ├── ✅ utils_validation.py     # Validações
│   └── 🔄 states.py              # Estados de conversação
├── 
├── 🔐 credenciais/           # Chaves de API (não versionado)
├── 🎨 static/                # Arquivos estáticos (CSS)
├── 📄 templates/             # Templates HTML
└── 📋 requirements.txt       # Dependências
```

---

## 🛠️ Tecnologias Utilizadas

### 🐍 **Backend & Core**
- **Python 3.12+**: Linguagem principal
- **python-telegram-bot**: Framework para bot Telegram
- **SQLAlchemy**: ORM para banco de dados
- **asyncio**: Programação assíncrona
- **pydantic**: Validação de dados

### 🧠 **Inteligência Artificial**
- **Google Gemini Pro**: IA generativa para conversação
- **Google Vision API**: OCR para imagens
- **pdfplumber**: Extração de texto de PDFs
- **pandas**: Manipulação e análise de dados
- **scikit-learn**: Machine learning (futuro)

### 📊 **Visualização & Relatórios**
- **matplotlib**: Gráficos estáticos
- **plotly**: Gráficos interativos (futuro)
- **Jinja2**: Templates para relatórios HTML
- **weasyprint**: Geração de PDFs

### 🗄️ **Banco de Dados**
- **PostgreSQL**: Banco principal (produção)
- **SQLite**: Desenvolvimento local
- **Redis**: Cache e sessões (futuro)

### 🌐 **APIs & Integrações**
- **aiohttp**: Cliente HTTP assíncrono
- **google-api-python-client**: APIs do Google
- **yfinance**: Dados financeiros
- **requests**: HTTP síncrono

### 🔧 **DevOps & Deployment**
- **Docker**: Containerização
- **GitHub Actions**: CI/CD
- **Railway/Heroku**: Deploy
- **Sentry**: Monitoramento de erros

---

## ⚡ Instalação e Configuração

### 🔧 **Pré-requisitos**

- **Python 3.12+** 
- **PostgreSQL 14+** (ou SQLite para desenvolvimento)
- **Git**

### 📋 **APIs Necessárias**

1. **Telegram Bot Token**
   - Acesse [@BotFather](https://t.me/botfather)
   - Crie um novo bot: `/newbot`
   - Guarde o token gerado

2. **Google Cloud Platform**
   - Ative Gemini API e Vision API
   - Crie service account e baixe JSON
   - Configure cotas e billing

3. **APIs Financeiras (Opcional)**
   - Alpha Vantage (dados de ações)
   - Yahoo Finance (gratuito)

### 🚀 **Instalação Passo a Passo**

#### **1. Clone o Repositório**
```bash
git clone https://github.com/henriquejfp/MaestroFin.git
cd MaestroFin
```

#### **2. Ambiente Virtual**
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Linux/Mac)
source venv/bin/activate
```

#### **3. Instalar Dependências**
```bash
pip install -r requirements.txt
```

#### **4. Configurar Banco de Dados**

**PostgreSQL (Produção):**
```bash
# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Criar usuário e banco
sudo -u postgres createuser --interactive maestrofin
sudo -u postgres createdb maestrofin_db
```

**SQLite (Desenvolvimento):**
```bash
# Automático - será criado na primeira execução
```

#### **5. Variáveis de Ambiente**

Crie arquivo `.env`:
```bash
# Bot Configuration
TELEGRAM_TOKEN=1234567890:ABCDEFghijklmnopqrstuvwxyz
BOT_USERNAME=maestrofin_bot

# Database  
DATABASE_URL=postgresql://user:password@localhost/maestrofin_db
# ou para SQLite:
# DATABASE_URL=sqlite:///maestrofin.db

# Google Cloud
GEMINI_API_KEY=AIzaSyA...
GOOGLE_APPLICATION_CREDENTIALS=./credenciais/service-account-key.json

# Optional APIs
ALPHA_VANTAGE_API_KEY=DEMO

# Email (opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=seuemail@gmail.com
EMAIL_PASSWORD=suasenha
```

#### **6. Credenciais Google**

Coloque os arquivos na pasta `credenciais/`:
```
credenciais/
├── service-account-key.json    # Service Account do Google Cloud
├── googlevision2.json          # Credenciais Vision API (se separado)
└── credentials.json            # OAuth2 (se usar)
```

#### **7. Executar**
```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Executar bot
python bot.py
```

### 🐳 **Docker (Alternativo)**

```bash
# Build da imagem
docker build -t maestrofin .

# Executar container
docker run -d \
  --name maestrofin \
  --env-file .env \
  -v $(pwd)/credenciais:/app/credenciais \
  maestrofin
```

---

## 📱 Como Usar

### 🎬 **Primeiro Uso**

1. **Iniciar conversa**: `/start`
2. **Configuração inicial**: `/configurar`
   - Definir categorias personalizadas
   - Adicionar contas bancárias
   - Configurar horário de notificações
   - Escolher moeda padrão

### 💬 **Comandos Principais**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/gerente` | Menu principal interativo | - |
| `/fatura` | Importar fatura de cartão (PDF) | Upload de arquivo |
| `/grafico` | Gerar gráficos personalizados | Gastos por categoria |
| `/relatorio` | Relatório completo em HTML | Mensal, anual |
| `/metas` | Gerenciar metas financeiras | Limite R$ 500/mês |
| `/agendar` | Criar lançamentos recorrentes | Salário todo dia 5 |
| `/notificacoes` | Configurar alertas | Horário, frequência |
| `/help` | Ajuda e comandos | - |

### 💰 **Tipos de Lançamento**

#### **1. Entrada Manual**
```
💬 Conversa natural:
"Recebi R$ 3000 de salário"
"Paguei R$ 50 de combustível no posto Shell"
"Gastei 45 reais no supermercado"
```

#### **2. Menu Interativo**
```
📊 GERENTE FINANCEIRO

🆕 Novo Lançamento
📊 Ver Gráficos  
📈 Relatórios
🎯 Metas
⚙️ Configurações
```

#### **3. Importação de Fatura**
```
1. Envie /fatura
2. Faça upload do PDF da fatura
3. Selecione o cartão de crédito
4. Confirme a importação
5. ✅ Transações importadas automaticamente
```

### 📊 **Categorização Inteligente**

O sistema categoriza automaticamente baseado em:
- **Palavras-chave**: "McDonald's" → Alimentação → Fast Food
- **Histórico**: Aprendizado com categorizações anteriores  
- **IA Gemini**: Análise contextual avançada

**Categorias Padrão:**
- 🍕 **Alimentação**: Restaurantes, Supermercado, Fast Food
- 🚗 **Transporte**: Combustível, Uber, Transporte Público  
- 🏠 **Moradia**: Aluguel, Condomínio, Utilities
- 💊 **Saúde**: Médico, Farmácia, Plano de Saúde
- 🎮 **Lazer**: Cinema, Jogos, Viagens
- 👔 **Trabalho**: Material, Cursos, Equipamentos
- 📚 **Educação**: Livros, Cursos, Faculdade

### 🎯 **Sistema de Metas**

#### **Criar Meta**
```
🎯 NOVA META

📋 Categoria: Alimentação
💰 Valor limite: R$ 600,00  
📅 Período: Mensal
🔔 Alertas: 80% e 95%

[✅ Criar Meta]
```

#### **Acompanhamento**
```
🎯 METAS DO MÊS

🍕 Alimentação: R$ 480/R$ 600 (80%) ⚠️
🚗 Transporte: R$ 120/R$ 300 (40%) ✅  
🎮 Lazer: R$ 250/R$ 200 (125%) ❌

💡 Dica: Você está 25% acima da meta de lazer.
Que tal reduzir os gastos nos próximos dias?
```

---

## 📊 Estrutura do Banco de Dados

### 🗄️ **Modelo Relacional**

```sql
-- Usuários do sistema
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    nome_completo VARCHAR(255),
    email VARCHAR(255),
    horario_notificacao TIME DEFAULT '09:00',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Categorias de lançamentos
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    icone VARCHAR(10),
    cor VARCHAR(7)
);

-- Subcategorias
CREATE TABLE subcategorias (
    id SERIAL PRIMARY KEY,
    id_categoria INTEGER REFERENCES categorias(id),
    nome VARCHAR(100) NOT NULL
);

-- Contas bancárias/cartões
CREATE TABLE contas (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id),
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50), -- 'Conta Corrente', 'Cartão de Crédito'
    banco VARCHAR(100),
    saldo_inicial DECIMAL(10,2) DEFAULT 0
);

-- Lançamentos financeiros
CREATE TABLE lancamentos (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id),
    id_categoria INTEGER REFERENCES categorias(id),
    id_subcategoria INTEGER REFERENCES subcategorias(id),
    id_conta INTEGER REFERENCES contas(id),
    descricao TEXT NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    tipo VARCHAR(10) NOT NULL, -- 'Entrada' ou 'Saída'
    data_transacao DATE NOT NULL,
    forma_pagamento VARCHAR(100),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metas financeiras
CREATE TABLE metas (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id),
    id_categoria INTEGER REFERENCES categorias(id),
    nome VARCHAR(200),
    valor_limite DECIMAL(10,2),
    periodo VARCHAR(20), -- 'mensal', 'anual'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agendamentos recorrentes
CREATE TABLE agendamentos (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id),
    id_categoria INTEGER REFERENCES categorias(id),
    id_conta INTEGER REFERENCES contas(id),
    descricao TEXT,
    valor DECIMAL(10,2),
    tipo VARCHAR(10),
    dia_vencimento INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    proximo_vencimento DATE
);
```

### 🔗 **Relacionamentos**

```mermaid
erDiagram
    Usuario ||--o{ Lancamento : possui
    Usuario ||--o{ Meta : define
    Usuario ||--o{ Conta : tem
    Usuario ||--o{ Agendamento : programa
    
    Categoria ||--o{ Subcategoria : contem
    Categoria ||--o{ Lancamento : classifica
    Categoria ||--o{ Meta : limita
    
    Conta ||--o{ Lancamento : origina
    
    Lancamento }o--|| Subcategoria : pertence
```

---

## 🤖 Inteligência Artificial

### 🧠 **Google Gemini Integration**

#### **1. Processamento de Linguagem Natural**
```python
# Análise conversacional
prompt = f"""
Usuário disse: "{user_message}"

Extraia:
- Valor: (número)
- Descrição: (texto)
- Categoria: (uma das disponíveis)
- Tipo: (Entrada/Saída)

Categorias disponíveis: {categorias_string}
"""

response = gemini.generate_content(prompt)
```

#### **2. Categorização Automática**
```python
# Categorização inteligente de transações
def categorizar_transacao(descricao: str) -> dict:
    prompt = f"""
    Categorize esta transação: "{descricao}"
    
    Retorne JSON:
    {{
        "categoria": "nome_categoria",
        "subcategoria": "nome_subcategoria", 
        "confianca": 0.95
    }}
    """
    
    return gemini.generate_content(prompt)
```

#### **3. Análise e Insights**
```python
# Geração de insights financeiros
def gerar_insights(dados_usuario: dict) -> str:
    prompt = f"""
    Dados financeiros do usuário:
    {json.dumps(dados_usuario, indent=2)}
    
    Gere insights personalizados:
    - Padrões de gastos
    - Oportunidades de economia  
    - Tendências preocupantes
    - Sugestões de melhoria
    """
    
    return gemini.generate_content(prompt)
```

### 🔍 **Google Vision OCR**

#### **1. Extração de Texto de Imagens**
```python
def extract_text_from_image(image_bytes: bytes) -> str:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    return texts[0].description if texts else ""
```

#### **2. Processamento de Faturas PDF**
```python
def processar_fatura_pdf(pdf_bytes: bytes) -> List[dict]:
    # Detectar banco pelo cabeçalho
    banco = detectar_banco(pdf_bytes)
    
    # Parser específico por banco
    if banco == "bradesco":
        return parse_bradesco(pdf_bytes)
    elif banco == "caixa":
        return parse_caixa(pdf_bytes)
    else:
        return parse_generico(pdf_bytes)
```

### 📊 **Machine Learning (Futuro)**

#### **Análise Preditiva**
- **Previsão de Gastos**: Modelo que prevê gastos futuros
- **Detecção de Anomalias**: Identifica gastos atípicos
- **Recomendações**: Sugere categorias baseado no histórico

```python
# Exemplo de modelo futuro
class GastoPredictor:
    def __init__(self):
        self.model = LinearRegression()
    
    def predict_next_month(self, historical_data):
        # Treinar modelo com dados históricos
        # Fazer previsão para próximo mês
        pass
```

---

## 🔒 Segurança e Privacidade

### 🛡️ **Proteção de Dados**

#### **1. Criptografia**
```python
# Dados sensíveis criptografados
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str) -> str:
    key = os.getenv('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()
```

#### **2. Validação de Entrada**
```python
# Sanitização e validação rigorosa
from pydantic import BaseModel, validator

class LancamentoInput(BaseModel):
    valor: float
    descricao: str
    
    @validator('valor')
    def validate_valor(cls, v):
        if v <= 0:
            raise ValueError('Valor deve ser positivo')
        if v > 1000000:
            raise ValueError('Valor muito alto')
        return v
```

#### **3. Rate Limiting**
```python
# Limite de requisições por usuário
@rate_limit(requests=10, window=60)  # 10 req/min
async def handle_message(update, context):
    pass
```

### 🔐 **Controle de Acesso**

#### **1. Autenticação de Usuário**
```python
def is_authorized_user(telegram_id: int) -> bool:
    # Verificar se usuário está autorizado
    user = db.query(Usuario).filter_by(telegram_id=telegram_id).first()
    return user is not None and user.is_active
```

#### **2. Logs de Auditoria**
```python
# Log de todas as ações sensíveis
def log_user_action(user_id: int, action: str, details: dict):
    logger.info(f"User {user_id} - {action}", extra=details)
```

### 🗄️ **Proteção do Banco de Dados**

#### **1. Conexão Segura**
```python
# SSL obrigatório em produção
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"
```

#### **2. Backup Automático**
```bash
# Script de backup diário
#!/bin/bash
pg_dump maestrofin_db > backup_$(date +%Y%m%d).sql
```

#### **3. Isolamento de Dados**
```python
# Cada usuário só acessa seus próprios dados
def get_user_data(user_id: int, data_type: str):
    return db.query(Lancamento).filter_by(id_usuario=user_id).all()
```

---

## 🧪 Desenvolvimento

### 🔧 **Ambiente de Desenvolvimento**

#### **1. Setup Inicial**
```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Executar testes
python -m pytest tests/
```

#### **2. Estrutura de Testes**
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_handlers.py
├── integration/
│   ├── test_database.py
│   └── test_telegram_bot.py
└── e2e/
    └── test_user_journey.py
```

#### **3. Variáveis de Ambiente de Desenvolvimento**
```bash
# .env.development
ENVIRONMENT=development
DATABASE_URL=sqlite:///test.db
TELEGRAM_TOKEN=test_token
LOG_LEVEL=DEBUG
```

### 🔍 **Debug e Monitoramento**

#### **1. Logging Estruturado**
```python
import structlog

logger = structlog.get_logger()

# Log com contexto
logger.info(
    "Lançamento criado",
    user_id=123,
    valor=45.50,
    categoria="alimentacao"
)
```

#### **2. Métricas de Performance**
```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper
```

#### **3. Health Checks**
```python
# Endpoint de saúde da aplicação
async def health_check():
    checks = {
        "database": await test_database_connection(),
        "telegram_api": await test_telegram_connection(),
        "gemini_api": await test_gemini_connection()
    }
    return {"status": "healthy", "checks": checks}
```

### 🚀 **Deploy e CI/CD**

#### **1. GitHub Actions**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: python -m pytest
      
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Railway
        run: railway deploy
```

#### **2. Docker Multi-stage**
```dockerfile
# Dockerfile
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
CMD ["python", "bot.py"]
```

#### **3. Monitoramento em Produção**
```python
# Integração com Sentry
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn",
    integrations=[SqlalchemyIntegration()],
    traces_sample_rate=1.0
)
```

---

## 📈 Roadmap

### 🎯 **Versão 2.1.0** (Em Desenvolvimento)
- [ ] 🔧 **Correção da função de fatura** - Sistema de importação 100% funcional
- [ ] 📊 **Gráficos interativos** - Plotly.js integration
- [ ] 🔄 **Sincronização automática** - API Open Banking
- [ ] 📱 **Interface web** - Dashboard complementar

### 🚀 **Versão 2.2.0** (Próxima)
- [ ] 🧠 **IA Preditiva** - Modelos de machine learning
- [ ] 📈 **Análise de investimentos** - Carteira e performance
- [ ] 🔔 **Notificações push** - WebApp notifications
- [ ] 👥 **Multi-usuário** - Contas familiares

### 🌟 **Versão 3.0.0** (Futuro)
- [ ] 🏦 **Open Banking** - Integração com bancos brasileiros
- [ ] 🤖 **Assistente voz** - Comando por áudio
- [ ] 📊 **Business Intelligence** - Dashboards avançados  
- [ ] 🌐 **API pública** - Integração com outros apps

### 💡 **Ideias em Avaliação**
- **Marketplace de integrações** - Plugins da comunidade
- **Análise comportamental** - Psicologia financeira
- **Gamificação** - Pontos e conquistas
- **Social features** - Comparação com amigos
- **Consultoria IA** - Planejamento financeiro personalizado

---

## 📄 Licença

Este projeto utiliza **Licenciamento Dual**:

### 🆓 **Uso Não Comercial**
- ✅ Visualização e estudo do código
- ✅ Uso educacional e portfólio  
- ✅ Execução local para testes
- ✅ Contribuições via Pull Request

### 💼 **Uso Comercial**
- ❌ Requer licença comercial paga
- ❌ Uso empresarial em produção
- ❌ Monetização ou venda

**Para licenciamento comercial**: henriquejfp.dev@gmail.com

Leia o arquivo [LICENSE](./LICENSE) completo para mais detalhes.

---

## 📞 Contato

### 👨‍💻 **Desenvolvedor**
**Henrique de Jesus Freitas Pereira**

- 📧 **Email**: henriquejfp.dev@gmail.com
- 💼 **LinkedIn**: [henrique-jfp](https://www.linkedin.com/in/henrique-jfp)
- 🐙 **GitHub**: [henrique-jfp](https://github.com/henrique-jfp)
- 🎓 **Estudante**: Engenharia de Software

### 🤝 **Contribuições**

Contribuições são bem-vindas! Por favor:

1. **Fork** o repositório
2. **Crie** um branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. **Push** para o branch (`git push origin feature/AmazingFeature`)
5. **Abra** um Pull Request

### 🐛 **Reportar Bugs**

Encontrou um bug? [Abra uma issue](https://github.com/henriquejfp/MaestroFin/issues) com:

- **Descrição clara** do problema
- **Passos para reproduzir**
- **Comportamento esperado vs atual**
- **Screenshots** (se aplicável)
- **Ambiente** (OS, Python version, etc.)

### 💬 **Suporte**

- 📋 **Issues**: Para bugs e features requests
- 📧 **Email**: Para dúvidas gerais e parcerias
- 💼 **LinkedIn**: Para oportunidades profissionais

---

<div align="center">

### 🎼 **MaestroFin - Orquestrar suas finanças nunca foi tão simples!**

*Desenvolvido com ❤️ por [Henrique Freitas](https://github.com/henrique-jfp)*

[![Star this repo](https://img.shields.io/github/stars/henriquejfp/MaestroFin?style=social)](https://github.com/henriquejfp/MaestroFin)
[![Follow me](https://img.shields.io/github/followers/henriquejfp?style=social)](https://github.com/henriquejfp)

</div>
