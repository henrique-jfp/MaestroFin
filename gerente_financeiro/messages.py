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
    # --- Fallback / error ---
    "generic_error": (
        "Vixe... me embolei aqui rapidinho. Dá uma repetida pra eu acertar?"
    ),
}


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
    try:
        text = template.format(**context)
    except KeyError:
        # Falta de placeholder não deve quebrar
        text = template

    # Ajustes simples por tom (placeholder para evolução futura)
    if tone == "success":
        # Poderíamos adicionar reforço positivo
        pass
    elif tone == "error":
        # Sutil suavização já embutida nas mensagens
        pass
    return BASE_PREFIX + text


def available_keys():  # utilitário para testes / auditoria
    return sorted(CATALOG.keys())
