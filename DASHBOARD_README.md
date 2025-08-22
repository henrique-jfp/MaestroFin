# 🌐 MaestroFin Dashboard

Dashboard web interativo para visualização de dados financeiros integrado ao bot Telegram MaestroFin.

## 🎯 Funcionalidades

### 📊 Visualizações Interativas
- **Gráfico de Pizza**: Distribuição de gastos por categoria
- **Gráfico de Evolução**: Tendência de receitas vs despesas ao longo do tempo  
- **Gráfico de Barras**: Ranking de gastos por categoria
- **KPIs em Tempo Real**: Receitas, despesas, saldo e taxa de poupança

### 🔒 Segurança
- **Links Temporários**: Acesso via tokens únicos com expiração de 1 hora
- **Integração Telegram**: Geração de links diretamente pelo bot
- **Dados Privados**: Cada usuário acessa apenas seus próprios dados

### 📱 Interface Responsiva
- **Design Moderno**: Interface Bootstrap 5 com animações CSS
- **Mobile-First**: Totalmente adaptado para dispositivos móveis
- **UX Otimizada**: Carregamento rápido e navegação intuitiva

## 🚀 Como Usar

### Via Bot Telegram
1. Envie `/dashboard` no chat com o MaestroFin
2. Clique no link gerado (válido por 1 hora)
3. Acesse seu dashboard personalizado

### Demonstração
- Acesse: http://localhost:5000/dashboard/demo
- Veja o dashboard com dados de exemplo

### Verificar Status
- Comando: `/dashstatus` no bot
- API: GET `/api/status`

## 🛠️ Instalação e Configuração

### Dependências
```bash
pip install flask==3.0.0 flask-cors==4.0.1 plotly==5.17.0 pandas==2.1.4
```

### Executar Dashboard
```bash
# Dashboard simples (recomendado)
python dashboard_simple.py

# Dashboard completo (com integração BD)
python dashboard_app.py

# Launcher completo (bot + dashboard)
python launcher.py
```

### Portas e URLs
- **Dashboard**: http://localhost:5000
- **Demo**: http://localhost:5000/dashboard/demo
- **API Status**: http://localhost:5000/api/status

## 📁 Estrutura de Arquivos

```
├── dashboard_simple.py          # Dashboard básico funcional
├── dashboard_app.py            # Dashboard completo (em desenvolvimento)
├── launcher.py                 # Script para iniciar bot + dashboard
├── templates/dashboard/        # Templates HTML
│   ├── index.html             # Página inicial
│   ├── main.html              # Dashboard principal
│   ├── 404.html               # Página de erro 404
│   └── 500.html               # Página de erro 500
├── static/dashboard.css        # Estilos CSS modernos
└── gerente_financeiro/
    └── dashboard_handler.py    # Integração com bot Telegram
```

## 🔧 APIs Disponíveis

### Gerar Token de Acesso
```http
GET /api/gerar-token/<user_id>
```
**Resposta:**
```json
{
    "token": "uuid-token",
    "url": "http://localhost:5000/dashboard/uuid-token",
    "expires": "2025-07-22T04:00:00"
}
```

### Status do Sistema
```http
GET /api/status
```
**Resposta:**
```json
{
    "status": "online",
    "timestamp": "2025-07-22T03:00:00",
    "version": "1.0.0",
    "tokens_ativos": 5
}
```

### Gráficos por Usuário
```http
GET /api/graficos/<user_id>?mes=7&ano=2025
```

### KPIs por Usuário
```http
GET /api/kpis/<user_id>?mes=7&ano=2025
```

## 🎨 Recursos Visuais

### KPIs Cards
- **Receitas**: Total de entradas com variação mensal
- **Despesas**: Total de saídas com gasto médio diário
- **Saldo**: Resultado líquido com indicador visual
- **Taxa Poupança**: Percentual com meta de referência

### Gráficos Interativos
- **Hover Effects**: Detalhes ao passar o mouse
- **Zoom e Pan**: Navegação nos gráficos
- **Responsivos**: Redimensionamento automático
- **Cores Temáticas**: Paleta consistente com identidade

### Interface
- **Loading States**: Spinners durante carregamento
- **Error Handling**: Páginas de erro personalizadas
- **Smooth Animations**: Transições fluidas
- **Dark Mode Ready**: Preparado para tema escuro

## 🔗 Integração com Bot

### Comandos Disponíveis
- `/dashboard` - Gera link personalizado
- `/dashstatus` - Verifica status do dashboard

### Handlers Registrados
- `cmd_dashboard()` - Comando principal
- `cmd_dashstatus()` - Verificação de status
- `callback_dashboard_new_link()` - Regenerar link

### Fluxo de Segurança
1. Usuário solicita `/dashboard`
2. Sistema gera token único
3. Token válido por 1 hora
4. Link expira automaticamente
5. Tokens expirados são limpos automaticamente

## 📈 Roadmap

### ✅ Implementado
- [x] Dashboard básico funcional
- [x] Gráficos interativos (Plotly)
- [x] Interface responsiva (Bootstrap)
- [x] Sistema de tokens temporários
- [x] Integração com bot Telegram
- [x] APIs RESTful
- [x] Dados de demonstração

### 🔄 Em Desenvolvimento
- [ ] Integração completa com banco de dados
- [ ] Filtros avançados por período
- [ ] Exportação de dados (PDF/Excel)
- [ ] Notificações push
- [ ] Comparativos históricos
- [ ] Alertas personalizados

### 🎯 Futuro
- [ ] Tema escuro
- [ ] Múltiplos idiomas
- [ ] Relatórios automáticos
- [ ] Integração com bancos
- [ ] Machine Learning para insights
- [ ] App mobile nativo

## 🐛 Troubleshooting

### Dashboard não carrega
1. Verificar se o processo está rodando: `ps aux | grep dashboard`
2. Testar API: `curl http://localhost:5000/api/status`
3. Verificar logs: `cat dashboard_simple.log`

### Erro de dependências
```bash
# Reinstalar dependências
pip install -r requirements.txt

# Verificar versões
pip list | grep -E "(flask|plotly|pandas)"
```

### Port 5000 em uso
```bash
# Encontrar processo usando a porta
lsof -i :5000

# Matar processo
kill -9 <PID>
```

## 📞 Suporte

- **Logs**: Verifique `dashboard_simple.log` para erros
- **Status**: Use `/dashstatus` no bot para diagnóstico
- **Demo**: Teste sempre com `/dashboard/demo` primeiro

---

**MaestroFin Dashboard v1.0** - Sistema completo de visualização financeira 📊✨
