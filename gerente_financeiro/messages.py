"""Camada de mensagens estilizadas (Persona: Alfredo)

Fase 1:
 - Catálogo inicial de mensagens centrais (/start, /help e seções)
 - Função render_message com placeholders seguros
 - Feature flag ALFREDO_STYLE (env) para permitir rollback (desliga estilo)
 - Suporte a tipos (success, error, info) para ajustes futuros

Boas práticas:
 - Nunca concatenar diretamente dados sensíveis sem normalizar
 - Placeholders: {name}, {section}, {command}, {value}, etc.
 - Evitar mensagens muito longas em fluxo rápido; moderar humor
"""

from __future__ import annotations
import os
from typing import Dict, Any

ALFREDO_STYLE = os.getenv("ALFREDO_STYLE", "on").lower() in {"1", "true", "on", "yes"}

BASE_PREFIX = ""  # Futuro: poderia permitir prefixo global

CATALOG: Dict[str, str] = {
    # --- Core /start ---
    "start_welcome": (
        "Opa, chegue mais, {name}! Eu sou o Alfredo – a mesa tá uma bagunça de papel, "
        "mas aqui no sistema eu deixo tudinho alinhado. Vamos ajeitar sua casa financeira agora.\n\n"
        "Só precisamos configurar umas coisinhas rápidas pra eu te ajudar do meu jeito. "
        "Se bater curiosidade sobre tudo que faço, manda um /help. Arretado demais!"
    ),
    # --- Help main ---
    "help_main_intro": (
        "{name}, sente aqui. Vou te mostrar com calma o que eu sei fazer. Nada de aperreio.\n\n"
        "Eu vigio teus lançamentos, monto relatórios, puxo gráficos, crio metas e até converso sobre estratégia. "
        "Escolhe uma dessas áreas abaixo que eu te oriento, parceiro(a)."
    ),
    # --- Help sections ---
    "help_lancamentos": (
        "📝 <b>Lançamentos</b>\n\n"
        "Registrar bem é metade do caminho. Dá pra digitar, usar OCR de nota e até importar fatura. \n"
        "Se errar, relaxa que a gente edita."
    ),
    "help_analise": (
        "🧠 <b>Análises Inteligentes</b>\n\n"
        "Me pergunta do jeito que fala com gente: 'Quanto foi iFood esse mês?', 'Maior gasto em Lazer', 'Cotação do dólar'.\n"
        "Eu respondo sem frescura e ainda aponto tendência."
    ),
    "help_planejamento": (
        "🎯 <b>Planejamento</b>\n\n"
        "Meta boa é meta que respira. Cria, acompanha progresso e agenda coisas repetitivas pra não esquecer."
    ),
    "help_config": (
        "⚙️ <b>Ferramentas e Ajustes</b>\n\n"
        "Aqui tu molda o bot pro teu jeito: contas, cartões, perfil e limites de alerta."
    ),
    "help_gamificacao": (
        "🎮 <b>Gamificação</b>\n\n"
        "Divertir aprendendo: XP, ranking, conquistas e aquele empurrãozinho pra manter consistência."
    ),
    
    # --- Onboarding e configuração ---
    "config_salvas": "Arretado! Suas configurações tão todas salvas, parceiro(a)! 🎯",
    "pergunta_proximo_cartao": "Ó, boa! Agora qual o nome do próximo cartão? (ex: XP Visa Infinite) 💳",
    "pergunta_proxima_conta": "🏦 Beleza! Agora manda o nome da próxima <b>conta</b>?",
    "perfil_definido": "Arretado! Perfil definido como: <b>{perfil}</b>! 🎯\n\nVoltando pro menu...",
    "conta_nao_encontrada_config": "Vixe... 🤔 Essa conta não tá aqui na lista não, parceiro(a). Pode verificar?",
    "cartao_nao_encontrado_config": "Eita... 😅 Esse cartão não tô vendo aqui não. Dá uma conferida aí!",
    "processando_solicitacao": "Processando sua solicitação, aguenta aí... ⏳",
    "operacao_cancelada": "✅ Ufa! Seus dados estão seguros. Operação cancelada.",
    
    # --- OCR e processamento ---
    "verificando_salvando": "💾 Verificando e salvando no banco de dados, aguenta aí...",
    "transacao_duplicada": "⚠️ Opa! Essa transação já tá aqui registrada, parceiro(a)! Operação cancelada pra não duplicar.",
    "falha_salvar_banco": "❌ Vixe... rolou um pepino ao salvar no banco. Já anotei o erro aqui pra gente resolver!",
    "erro_dados_sessao": "Eita... 😅 Os dados da sessão se perderam. Tenta enviar de novo aí!",
    
    # --- Extrato ---
    "sem_transacoes_validas": "Rapaz, não encontrei transações válidas nesse extrato não. Dá uma conferida e manda de novo?",
    "dados_insuficientes": "Ó, parceiro(a), tá faltando uns dados aqui pra salvar direitinho. Pode verificar?",
    "conta_nao_encontrada_extrato": "Essa conta não tô achando aqui na lista. Se continuar dando problema, me chama que a gente resolve!",
    "todas_transacoes_salvas": "Arretado! ✅ Todas as transações foram salvas certinho!",
    "erro_salvar_transacoes": "❌ Eita... deu um probleminha ao salvar suas transações. Tenta de novo mais tarde?",
    "extrato_cancelado": "Operação cancelada, parceiro(a). Pode enviar um novo extrato quando quiser!",
    
    # --- Confirmações/Sucessos ---
    "lancamento_criado": (
        "Prontinho, {name}! Lançamento de {valor} guardado aqui. "
        "Cada centavo no seu lugar, que é pra não dar dor de cabeça depois."
    ),
    "conta_criada": (
        "Arretado! Conta '{conta_nome}' tá registrada e funcionando. "
        "Agora é só usar nos lançamentos, viu só?"
    ),
    "cartao_criado": (
        "Beleza! Cartão '{cartao_nome}' cadastrado com limite de {valor}. "
        "Já pode usar ele nos gastos que eu fico de olho nas datas."
    ),
    "meta_atingida": (
        "Eita, que orgulho! Olha aí {name} batendo a meta '{meta_nome}'! "
        "Já pode ir sonhando com o objetivo, que o dinheiro tá garantido. Parabéns demais!"
    ),
    "operacao_cancelada": (
        "Tranquilo, {name}. Cancelei tudo aqui. Se mudar de ideia, é só chamar de novo."
    ),
    "configuracao_salva": (
        "Pronto! Salvei suas preferências. Agora o sistema tá do jeitinho que você gosta."
    ),
    
    # --- Erros e problemas ---
    "erro_usuario_nao_encontrado": (
        "Ô, {name}, parece que você ainda não se apresentou direito. "
        "Manda um /start pra gente se conhecer melhor, vai?"
    ),
    "erro_valor_invalido": (
        "Rapaz, esse valor não tá batendo certo aqui na minha calculadora. "
        "Tenta de novo só com números e ponto, tipo 150.50?"
    ),
    "erro_conta_nao_encontrada": (
        "Vixe, essa conta não tá na minha listinha. "
        "Dá uma olhada no /configurar pra ver quais tem cadastradas."
    ),
    "erro_permissao": (
        "Ó, me desculpa aí, mas não consegui fazer essa operação. "
        "Talvez seja algum pepino técnico. Tenta de novo daqui a pouquinho?"
    ),
    "erro_formato_data": (
        "Essa data me confundiu um tiquinho. Manda no formato DD/MM/AAAA, "
        "tipo 15/12/2024, que eu entendo melhor."
    ),
    "erro_limite_excedido": (
        "Eita! Parece que esse valor passou do limite. "
        "Vamos com calma que juntos a gente ajeita isso, né?"
    ),
    
    # --- Insights e alertas ---
    "alerta_gasto_alto": (
        "Rapaz... dei uma olhada aqui e vi que os gastos com {categoria} esse mês "
        "tão com a gota serena! Foram {valor}. A gente pode dar um jeito nisso?"
    ),
    "insight_economia": (
        "Ó, {name}, notei que você economizou {valor} comparado ao mês passado. "
        "Esse padrão tá arretado demais, continue assim!"
    ),
    "lembrete_meta": (
        "Psiu, {name}! Sua meta '{meta_nome}' tá em {progresso}%. "
        "Tá quase lá, não desiste agora não!"
    ),
    
    # --- Conversação ---
    "nao_entendi": (
        "Vixe... deu um nó aqui na minha cabeça. Não entendi direito o que você quis dizer. "
        "Pode explicar de um outro jeito pra esse seu gerente aqui?"
    ),
    "aguarde_processando": (
        "Ó, se avexe não que eu tô organizando isso aqui pra você..."
    ),
    "sem_dados": (
        "Rapaz, não achei nada sobre isso nos seus dados. "
        "Que tal a gente começar registrando alguns lançamentos?"
    ),
    
    # --- Fallback / error ---
    "generic_error": (
        "Vixe... me embolei aqui rapidinho. Dá uma repetida pra eu acertar?"
    ),
}


def format_money(value: float) -> str:
    """Formata valor monetário no padrão brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _plain_fallback(key: str, **context) -> str:
    """Retorna fallback simples sem persona (quando flag desativada)."""
    base = CATALOG.get(key, key)
    try:
        return base.format(**context)
    except Exception:
        return base


def render_message(key: str, *, tone: str = "info", **context: Any) -> str:
    """Renderiza mensagem Alfredo (ou fallback se desligado)."""
    if not ALFREDO_STYLE:
        return _plain_fallback(key, **context)

    template = CATALOG.get(key)
    if not template:
        # fallback persona amigável
        template = CATALOG.get("generic_error", "Algo deu errado.")
    
    # Auto-formatar valores monetários se presentes
    if 'valor' in context and isinstance(context['valor'], (int, float)):
        context['valor'] = format_money(context['valor'])
    
    try:
        text = template.format(**context)
    except KeyError:
        # Falta de placeholder não deve quebrar
        text = template

    # Ajustes dinâmicos por tom
    if tone == "success":
        # Reforço positivo já embutido nas mensagens
        pass
    elif tone == "error":
        # Suavização já embutida; poderia adicionar emoji consolador
        if not any(emoji in text for emoji in ["😅", "🤔", "😊"]):
            text = "😅 " + text
    elif tone == "insight":
        # Destaque para insights importantes
        if not text.startswith(("Ó,", "Psiu,", "Rapaz")):
            text = "💡 " + text
    
    return BASE_PREFIX + text


def available_keys():  # utilitário para testes / auditoria
    return sorted(CATALOG.keys())
