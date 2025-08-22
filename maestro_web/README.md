# 🎼 Maestro Financeiro Web

Transformação do bot do Telegram em uma aplicação web moderna com interface tipo ChatGPT.

## 🎯 Visão Geral

Esta é uma aplicação web completa para gerenciamento financeiro pessoal, com:

- **Chat IA**: Interface conversacional para consultas financeiras
- **Sidebar com Cards**: Funções específicas organizadas em mini-cards
- **Dashboard**: Visualizações e métricas financeiras
- **API REST**: Backend robusto com FastAPI
- **Interface Moderna**: Frontend responsivo com Next.js e TailwindCSS

## 🏗️ Arquitetura

### Backend (FastAPI)
```
app/
├── api/
│   ├── auth.py          # Autenticação JWT
│   ├── chat.py          # Chat com IA
│   ├── dashboard.py     # Dashboard e métricas
│   ├── lancamentos.py   # Lançamentos financeiros
│   ├── metas.py         # Metas e objetivos
│   ├── contas.py        # Contas bancárias
│   ├── categorias.py    # Categorias de gastos
│   ├── agendamentos.py  # Agendamentos automáticos
│   ├── relatorios.py    # Relatórios detalhados
│   └── graficos.py      # Gráficos e visualizações
├── core/
│   ├── config.py        # Configurações
│   ├── database.py      # Conexão com banco
│   └── security.py      # Segurança e JWT
├── models/
│   ├── models.py        # Modelos SQLAlchemy
│   └── schemas.py       # Schemas Pydantic
├── services/
│   └── ai_service.py    # Serviço de IA
└── main.py              # Aplicação principal
```

### Frontend (Next.js)
```
src/
├── app/
│   ├── page.tsx         # Página principal
│   ├── layout.tsx       # Layout principal
│   └── globals.css      # Estilos globais
├── components/
│   ├── ChatInterface.tsx    # Interface de chat
│   ├── Sidebar.tsx          # Sidebar com cards
│   ├── LoginForm.tsx        # Formulário de login
│   └── ...
├── hooks/
│   ├── useAuth.ts           # Hook de autenticação
│   ├── useChat.ts           # Hook do chat
│   └── ...
└── lib/
    ├── api.ts               # Cliente API
    └── utils.ts             # Utilitários
```

## 🚀 Funcionalidades

### Chat IA (Maestro)
- **Consultas em linguagem natural**: "Quanto gastei este mês?"
- **Análises financeiras**: Padrões de gastos, tendências
- **Recomendações personalizadas**: Baseadas no perfil do usuário
- **Sugestões de ações**: Botões para executar tarefas rapidamente

### Cards da Sidebar
- **💰 Contas**: Gerenciar contas bancárias e saldos
- **📊 Lançamentos**: Registrar gastos e receitas
- **🎯 Metas**: Definir e acompanhar objetivos financeiros
- **📈 Relatórios**: Análises detalhadas e gráficos
- **⏰ Agendamentos**: Tarefas automáticas e lembretes

### Dashboard
- **Visão geral financeira**: Saldos, gastos, receitas
- **Métricas de saúde financeira**: Score personalizado
- **Gráficos interativos**: Visualizações dos dados
- **Alertas e notificações**: Lembretes importantes

## 🔧 Configuração

### Backend
```bash
cd maestro_web
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd maestrofin-web
npm install
npm run dev
```

## 🤖 Sistema de IA

O Maestro utiliza processamento de linguagem natural para:

### Detecção de Intenções
- **Saldo**: "Quanto tenho na conta?"
- **Gastos**: "Onde mais gastei?"
- **Metas**: "Como estão meus objetivos?"
- **Relatórios**: "Gere um resumo mensal"

### Análises Inteligentes
- **Padrões de consumo**: Identifica tendências
- **Recomendações**: Sugere melhorias
- **Alertas**: Notifica sobre situações importantes
- **Insights**: Fornece análises profundas

### Contexto Financeiro
- **Histórico**: Acesso a dados históricos
- **Personalização**: Respostas baseadas no perfil
- **Tempo real**: Informações atualizadas
- **Predições**: Projeções futuras

## 📊 Endpoints da API

### Autenticação
- `POST /auth/login` - Login do usuário
- `POST /auth/register` - Registro de usuário
- `POST /auth/refresh` - Refresh do token

### Chat
- `POST /chat/message` - Enviar mensagem para IA
- `GET /chat/history` - Histórico de conversas
- `WebSocket /chat/ws` - Chat em tempo real

### Dashboard
- `GET /dashboard/overview` - Visão geral
- `GET /dashboard/cards-data` - Dados dos cards
- `GET /dashboard/financial-health` - Saúde financeira

### Recursos Financeiros
- `GET /lancamentos` - Listar lançamentos
- `POST /lancamentos` - Criar lançamento
- `GET /metas` - Listar metas
- `POST /metas` - Criar meta
- `GET /contas` - Listar contas
- `POST /contas` - Criar conta

## 🎨 Interface do Usuário

### Design System
- **Cores**: Azul primário, tons de cinza neutros
- **Tipografia**: Inter/system fonts
- **Componentes**: Reutilizáveis e consistentes
- **Responsividade**: Mobile-first

### Experiência do Usuário
- **Chat fluido**: Semelhante ao ChatGPT
- **Navegação intuitiva**: Sidebar com cards
- **Feedback visual**: Loading states, animações
- **Acessibilidade**: Padrões WCAG

## 🔐 Segurança

### Autenticação
- **JWT**: Tokens seguros
- **Refresh tokens**: Renovação automática
- **Bcrypt**: Hash de senhas
- **Rate limiting**: Proteção contra spam

### Validação
- **Pydantic**: Validação de dados
- **CORS**: Configuração adequada
- **Input sanitization**: Prevenção de ataques
- **HTTPS**: Comunicação segura

## 🚀 Próximos Passos

### Fase 1: Implementação Base ✅
- [x] Estrutura do backend
- [x] Interface básica do chat
- [x] Sistema de autenticação
- [x] Cards da sidebar

### Fase 2: Funcionalidades Avançadas
- [ ] Implementar WebSocket para chat em tempo real
- [ ] Conectar com API de IA (OpenAI/Gemini)
- [ ] Desenvolver componentes dos cards
- [ ] Adicionar gráficos e visualizações

### Fase 3: Otimizações
- [ ] Cache de dados
- [ ] Otimização de performance
- [ ] Testes automatizados
- [ ] Deploy e CI/CD

### Fase 4: Recursos Extras
- [ ] Modo offline
- [ ] Notificações push
- [ ] Exportação de dados
- [ ] Integração com bancos

## 🛠️ Tecnologias Utilizadas

### Backend
- **FastAPI**: Framework web moderno
- **SQLAlchemy**: ORM para banco de dados
- **Pydantic**: Validação de dados
- **JWT**: Autenticação
- **WebSockets**: Chat em tempo real

### Frontend
- **Next.js 15**: Framework React
- **TailwindCSS**: Estilização
- **TypeScript**: Tipagem estática
- **React Query**: Gerenciamento de estado
- **Socket.io**: WebSocket client

### Banco de Dados
- **PostgreSQL**: Banco principal
- **SQLite**: Desenvolvimento local
- **Redis**: Cache e sessões

## 📈 Métricas e Monitoramento

### Analytics
- **Uso do chat**: Mensagens por usuário
- **Funcionalidades**: Cards mais utilizados
- **Performance**: Tempo de resposta
- **Erros**: Logs e monitoring

### Saúde Financeira
- **Score personalizado**: Baseado em múltiplos fatores
- **Tendências**: Análise de padrões
- **Alertas**: Notificações automáticas
- **Recomendações**: Sugestões personalizadas

## 🤝 Contribuição

Este projeto está em desenvolvimento ativo. Sugestões e contribuições são bem-vindas!

## 📄 Licença

Este projeto está sob a licença MIT.

---

**Feito com ❤️ para tornar o controle financeiro mais inteligente e acessível.**
