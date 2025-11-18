# 🏗️ Arquitetura do Projeto

## Estrutura de Diretórios

```
MaestroFin/
├── bot.py                          # Ponto de entrada principal do bot
├── app.py                          # Aplicação Flask para dashboard e webhooks
├── config.py                       # Configurações e variáveis de ambiente
├── models.py                       # Modelos SQLAlchemy (schema do BD)
├── requirements.txt                # Dependências Python
│
├── gerente_financeiro/             # 📊 Módulo principal de gestão financeira
│   ├── handlers.py                 # Handler principal da conversa
│   ├── services.py                 # Lógica de negócios
│   ├── open_finance_oauth_handler.py # Integração Open Finance (100+ bancos)
│   ├── ocr_handler.py              # OCR do Google Vision para notas
│   ├── pdf_generator.py            # Geração de PDF de relatórios
│   ├── investment_handler.py       # Rastreamento de investimentos
│   ├── gamification_handler.py     # XP, rankings, conquistas
│   ├── relatorio_handler.py        # Relatórios financeiros mensais
│   ├── manual_entry_handler.py     # Entrada manual de transações
│   ├── agendamentos_handler.py     # Agendamentos de despesas recorrentes
│   ├── metas_handler.py            # Rastreamento de objetivos financeiros
│   ├── dashboard_handler.py        # Dados do dashboard e visualizações
│   ├── delete_user_handler.py      # LGPD: Exclusão de dados do usuário
│   ├── contact_handler.py          # Handler de informações de contato
│   ├── onboarding_handler.py       # Fluxo de boas-vindas do usuário
│   ├── editing_handler.py          # Edição de transações
│   ├── graficos.py                 # Geração de gráficos (matplotlib)
│   ├── prompts.py                  # Prompts de IA para Gemini
│   ├── ia_handlers.py              # Análises com IA
│   ├── external_data.py            # APIs externas (BCB, Yahoo Finance, etc)
│   ├── states.py                   # Estados da conversa
│   ├── utils_email.py              # Utilitários de email
│   ├── utils_google_calendar.py    # Integração Google Calendar
│   └── utils_validation.py         # Validação de entrada
│
├── open_finance/                   # 🏦 Open Finance / Open Banking
│   ├── pluggy_client.py            # Cliente da API Pluggy
│   ├── bank_connector.py           # Gerenciamento de conexão bancária
│   ├── data_sync.py                # Sincronização de contas e transações
│   ├── connector_map.py            # Mapeamento de conectores de bancos
│   └── README.md                   # Documentação da API Pluggy
│
├── database/                       # 🗄️ Camada de banco de dados
│   └── database.py                 # Gerenciamento de sessão SQLAlchemy
│
├── analytics/                      # 📈 Analytics e métricas
│   ├── bot_analytics.py            # Analytics SQLite (local)
│   ├── bot_analytics_postgresql.py # Analytics PostgreSQL (produção)
│   ├── advanced_analytics.py       # Métricas avançadas
│   └── metrics.py                  # Definição de métricas
│
├── migrations/                     # 🔄 Migrações de banco de dados
│   ├── 002_create_pluggy_tables.sql
│   └── 003_create_investments_table.sql
│
├── static/                         # 🎨 Arquivos web
│   ├── dashboard.css
│   └── relatorio.css
│
├── templates/                      # 🌐 Templates HTML
│   ├── dashboard/
│   │   ├── main.html
│   │   ├── index.html
│   │   └── 404.html, 500.html
│   └── relatorio.html              # Template do relatório financeiro
│
├── credenciais/                    # 🔐 Credenciais de API (gitignored)
│   ├── service-account-key.json    # Google Cloud
│   └── google_vision_credentials.json
│
├── debug_logs/                     # 📝 Logs de debug
│
└── [Documentação]
    ├── README.md                   # Documentação principal
    ├── CHANGELOG.md                # Histórico de versões
    ├── ARCHITECTURE.md             # Documentação dessa arquitetura
    └── LICENSE                     # Licença dupla
```

## 🔄 Fluxo de Dados

### Transações Financeiras

```
1. ENTRADA DO USUÁRIO
   └─ /start → Onboarding
   └─ /lancamento → Transação manual
   └─ /sincronizar → Sincronização bancária (Open Finance)
   └─ Foto → Extração OCR

2. PROCESSAMENTO
   └─ API Open Finance → Busca contas e transações
   └─ Google Vision → Extrai dados da nota fiscal
   └─ Gemini IA → Categorização e análise
   └─ Banco de dados → Armazena e valida

3. ARMAZENAMENTO
   └─ PluggyTransaction (transações bancárias)
   └─ Lancamento (entradas do usuário)
   └─ Investment (investimentos)
   └─ Agendamento (despesas recorrentes)

4. ANÁLISE
   └─ Agregação diária
   └─ Relatórios mensais
   └─ Pontuação de gamificação

5. SAÍDA
   └─ Visualização no Dashboard
   └─ Notificações no Telegram
   └─ Relatórios em PDF
   └─ Resumos por email
```

## 🏦 Integração Open Finance

```
Banco → API Pluggy → MaestroFin → Banco de Dados
 ↓
100+ bancos suportados (Bradesco, Itaú, Nubank, etc)
 ↓
Fluxo OAuth → Token → Lista de contas → Transações
```

## 🗄️ Principais Modelos de Banco de Dados

- **Usuario**: Perfil e configurações do usuário
- **PluggyItem**: Token de conexão com banco
- **PluggyAccount**: Detalhes da conta bancária
- **PluggyTransaction**: Transações do banco
- **Lancamento**: Entrada manual de transação
- **Investment**: Portfolio de investimentos
- **Meta**: Objetivo financeiro
- **Agendamento**: Despesas agendadas
- **PluggyInvestment**: Investimentos retornados pelos bancos

## ⚡ Performance e Concorrência

### Melhorias na v2.0

- **Sincronização não-bloqueante**: `asyncio.run_in_executor()` para operações longas
- **Pool de threads**: Thread separada para chamadas de API
- **Event loop**: Responsivo a múltiplas requisições simultâneas
- **Paginação completa**: Suporte total a paginação da API para datasets grandes

### Antes da v2.0
- ❌ Operações bloqueantes na thread principal
- ❌ 2+ usuários simultâneos → bot congela
- ❌ Resultados de API em uma única página

### Depois da v2.0
- ✅ Não-bloqueante com executor de threads
- ✅ N usuários simultâneos suportados
- ✅ Paginação completa para dados completos

## 🔐 Recursos de Segurança

- Gerenciamento de tokens OAuth2
- Armazenamento criptografado de credenciais
- Exclusão de dados do usuário (LGPD compatível)
- Rate limiting por usuário
- Validação e sanitização de entrada

## 📊 Pipeline de Analytics

```
Eventos do Bot → Banco de Dados → Agregação → Dashboard
              ↓
              Exportação CSV
              ↓
              Relatórios mensais
```

## 🚀 Arquitetura de Deploy

### Desenvolvimento Local
- Banco de dados SQLite
- Python 3.12+
- Configuração via .env

### Produção (Render)
- Banco de dados PostgreSQL
- Updates do bot via webhook
- Health check endpoint
- Auto-scaling

---

Para mais detalhes, veja [README.md](README.md) e os docstrings em cada módulo.
