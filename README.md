# 🎼 MaestroFin - Seu Maestro Financeiro Pessoal

**Orquestre suas finanças com a precisão de um maestro e a inteligência da IA.**

MaestroFin é mais do que um bot de controle financeiro; é um assistente pessoal que automatiza, analisa e gamifica a gestão de suas finanças, transformando dados em decisões inteligentes diretamente no seu Telegram.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg)
![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-4285F4.svg)
![License](https://img.shields.io/badge/License-Dual-green.svg)

---

## 🎯 O Problema: O Caos Financeiro do Dia a Dia

Controlar as finanças é um desafio constante. Anotar cada gasto, categorizar despesas, analisar faturas e acompanhar metas consome um tempo precioso. Ferramentas tradicionais são muitas vezes manuais, complexas e pouco intuitivas, tornando o processo uma tarefa árdua e desmotivadora. O resultado? Falta de clareza, perda de oportunidades de economia e dificuldade em atingir objetivos financeiros.

## ✨ A Solução: Inteligência e Automação no seu Bolso

**MaestroFin** atua como seu maestro financeiro pessoal, orquestrando todas as suas movimentações com simplicidade e poder. Ele utiliza Inteligência Artificial para entender seus hábitos, automatiza a entrada de dados com OCR de ponta e transforma números complexos em insights visuais e acionáveis, tudo através de uma conversa natural no Telegram.

---

## 🚀 Proposta de Valor: O Que Torna o MaestroFin Único?

| Funcionalidade | Descrição |
| :--- | :--- |
| 🧠 **IA Conversacional (Google Gemini)** | Registre despesas com linguagem natural ("*Gastei R$50 no mercado*") e faça perguntas complexas ("*Compare meus gastos com lazer de janeiro e fevereiro*"). O MaestroFin entende, categoriza e responde com análises precisas. |
| 📸 **OCR Inteligente de Faturas e Recibos** | Diga adeus à digitação manual. Envie uma foto de um recibo ou o PDF da fatura do seu cartão (Bradesco, Caixa, Nubank, etc.) e o MaestroFin extrai, categoriza e importa todas as transações em segundos. |
| 📊 **Dashboard Web Interativo** | Vá além do chat. Acesse um dashboard web responsivo com gráficos interativos, KPIs em tempo real e filtros avançados para uma visão macro de sua saúde financeira. |
| 🎯 **Sistema de Metas e Agendamentos** | Crie metas de economia por categoria, acompanhe seu progresso com barras visuais e automatize lançamentos recorrentes como salários e aluguéis. O bot te mantém na linha com alertas inteligentes. |
| 🎮 **Gamificação Motivacional** | Transforme a tarefa de controlar finanças em um jogo. Ganhe XP por cada ação, suba de nível para desbloquear bônus, acompanhe seu streak diário e veja sua posição no ranking global. |
| 📈 **Relatórios Profissionais em PDF** | Gere relatórios mensais completos em PDF com um único comando, incluindo resumo executivo, gráficos de distribuição, análise de tendências e insights gerados por IA. |

---

## 🎬 Demonstração: O MaestroFin em Ação

**1. Lançamento por Conversa Natural:**
> **Você:** `Paguei o almoço no iFood, R$ 45,50 no crédito`
>
> **MaestroFin:** ✅ Lançamento de **R$ 45,50** salvo!
> 🍔 **Categoria:** Alimentação → Restaurante/Delivery
> 💳 **Conta:** Cartão de Crédito
>
> 💡 *Insight: Seus gastos com delivery este mês já somam R$ 280,70.*

**2. Importação de Fatura via PDF:**
> **Você:** *[envia o arquivo fatura_nubank.pdf]*
>
> **MaestroFin:** 📄 Fatura recebida! Processando em segundo plano...
> *(15 segundos depois)*
> **MaestroFin:** ✅ Análise concluída! Encontrei **47** transações válidas na sua fatura do **Nubank**. A qual cartão deseja associar?
> `[💳 Nubank Roxinho]` `[💳 Inter Gold]`

**3. Análise com a IA:**
> **Você:** `/gerente qual foi meu maior gasto este mês?`
>
> **MaestroFin:** 🎯 **Análise de Despesas**
> Sua maior despesa em Agosto foi de **`R$ 1.500,00`** com **Aluguel** no dia 05/08.
>
> 💡 **Insights do Maestro:**
> Excluindo a moradia, seu maior gasto foi com **Supermercado** (R$ 850,40). Podemos analisar essa categoria para encontrar oportunidades de economia?
> `[Analisar Supermercado]` `[Top 5 despesas]`

---

## 🛠️ Tecnologias e Arquitetura

O MaestroFin é construído sobre uma stack moderna e robusta, pronta para escalar.

- **Backend:** Python 3.12+, `python-telegram-bot`, `Flask`, `Gunicorn`
- **Inteligência Artificial:** `google-generativeai` (Gemini Pro), `google-cloud-vision`
- **Banco de Dados:** `SQLAlchemy` ORM com `PostgreSQL` (produção) e `SQLite` (desenvolvimento)
- **Análise de Dados:** `pandas`, `matplotlib`, `seaborn`
- **Processamento de PDF:** `pdfplumber`
- **Frontend (Dashboard):** `HTML`, `CSS`, `JavaScript`, `Chart.js`, `Plotly`

### Estrutura do Banco de Dados

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

🚀 Instalação Rápida (Desenvolvimento Local)

Pré-requisitos:

    Python 3.12+

    Git

1. Clone o Repositório:
Bash

git clone [https://github.com/henrique-jfp/maestrofin.git](https://github.com/henrique-jfp/maestrofin.git)
cd maestrofin

2. Crie e Ative o Ambiente Virtual:
Bash

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\\venv\\Scripts\\activate

3. Instale as Dependências:
Bash

pip install -r requirements.txt

4. Configure as Variáveis de Ambiente:

    Copie o arquivo .env.example para .env.

    Preencha com suas chaves de API (Telegram, Google Gemini).

    Para desenvolvimento local, o DATABASE_URL pode ser deixado em branco para usar o SQLite padrão.

Bash

cp .env.example .env
# Agora, edite o arquivo .env com suas chaves

5. Execute o Bot:
Bash

python bot.py

📈 Roadmap e Futuro do Projeto

O MaestroFin está em constante evolução. Nosso roadmap inclui:

    [ ] 🏦 Integração com Open Banking: Sincronização automática com suas contas bancárias.

    [ ] 💰 Módulo de Investimentos: Acompanhamento de carteira e performance.

    [ ] 🤝 Contas Compartilhadas: Gerenciamento financeiro para casais e famílias.

    [ ] 🤖 IA Preditiva: Previsão de gastos futuros e detecção de anomalias.

Como Contribuir

Contribuições são muito bem-vindas!

    Faça um Fork do projeto.

    Crie sua Branch (git checkout -b feature/NovaFuncionalidade).

    Faça o Commit de suas mudanças (git commit -m 'Adiciona NovaFuncionalidade').

    Faça o Push (git push origin feature/NovaFuncionalidade).

    Abra um Pull Request.

📄 Licença

Este projeto utiliza Licenciamento Dual:

    Uso Não Comercial: Livre para visualização, estudo e uso em portfólio.

    Uso Comercial: Requer uma licença paga. Entre em contato para mais detalhes.

📞 Contato

Henrique de Jesus Freitas Pereira

    📧 Email: henriquejfp.dev@gmail.com

    💼 LinkedIn: linkedin.com/in/henrique-jfp

    🐙 GitHub: github.com/henrique-jfp

⭐ Se este projeto te ajudou, considere dar uma estrela!
