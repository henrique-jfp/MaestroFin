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

    # --- Lançamento Manual ---
    "manual_menu_intro": (
        "💰 <b>Novo Lançamento</b>\n\n"
        "Como você quer registrar essa movimentação agora?\n\n"
        "📸 <b>Mais fácil:</b> Me manda uma foto do cupom/nota que eu leio.\n"
        "⌨️ <b>Manual:</b> A gente preenche juntinho passo a passo."
    ),
    "manual_inicio_tipo": (
        "{emoji} <b>{tipo}</b>\n\n📝 <b>Descrição:</b>\n"
        "Me diz rapidinho o que foi isso aí.\n\n"
        "💡 <i>Exemplos: Almoço no restaurante, Salário, Uber pra casa</i>"
    ),
    "manual_desc_invalida": (
        "⚠️ <b>Descrição curtinha demais ou enorme</b>\n\n"
        "Escreve entre 2 e 200 caracteres, parceiro(a).\n"
        "💡 <i>Exemplo: Almoço no restaurante</i>"
    ),
    "manual_pedir_valor": (
        "{emoji} <b>{descricao}</b>\n\n💰 <b>Valor?</b>\n\n"
        "💡 <i>Exemplos:</i>\n• <code>150</code>\n• <code>25.50</code>\n• <code>1500.00</code>"
    ),
    "manual_valor_invalido": (
        "⚠️ <b>Valor estranho</b>\n\nManda só número (pode ter ponto).\n"
        "💡 <i>Exemplos válidos:</i>\n• <code>150</code>\n• <code>25.50</code>\n• <code>1500.00</code>"
    ),
    "manual_usuario_nao_encontrado": "Ôxe... não achei teu cadastro aqui. Faz um /start rapidinho e volta.",
    "manual_sem_contas": (
        "❌ <b>Nenhuma {tipo_texto} cadastrada</b>\n\nVai no /configurar e adiciona primeiro pra gente continuar."
    ),
    "manual_escolher_conta": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n\n🏦 <b>Qual {tipo_texto}?</b>\n"
        "De onde {origem_verbo} o dinheiro?"
    ),
    "manual_categoria": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n{conta_emoji} {conta_nome}\n\n"
        "📂 <b>Categoria:</b>\nEm que categoria encaixa melhor?"
    ),
    "manual_subcategoria": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n📂 {categoria}\n\n"
        "🏷️ <b>Subcategoria:</b>\nEscolhe algo mais específico (ou pula)."
    ),
    "manual_perguntar_data": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n📂 {categoria}\n\n"
        "📅 <b>Data da transação:</b>\nDigita a data ou 'hoje' pra facilitar.\n\n"
        "💡 <i>Formato: DD/MM/AAAA</i>\nEx: <code>15/01/2025</code> ou <code>hoje</code>"
    ),
    "manual_data_invalida": (
        "⚠️ <b>Data embolada</b>\n\nManda no formato <code>DD/MM/AAAA</code> ou digita <code>hoje</code>.\n\n"
        "💡 <i>Exemplos:</i>\n• <code>15/01/2025</code>\n• <code>hoje</code>"
    ),
    "manual_salvo_sucesso": (
        "✅ <b>Lançamento Salvo!</b>\n\n{emoji} <b>{descricao}</b>\n💰 {valor}\n🏦 {conta}\n📅 {data}\n\n"
        "💡 <i>Bora registrar outro? Tô por aqui.</i>"
    ),
    "manual_salvo_erro": (
        "❌ <b>Não consegui salvar</b>\n\nDeu um probleminha técnico. Tenta novamente daqui a pouco."
    ),
    "manual_ocr_salvo": "✅ Lançamento por OCR salvo! O que registramos agora?",
    "manual_ocr_cancelado": "Lançamento por OCR cancelado. O que fazemos agora, parceiro(a)?",
    "manual_sessao_finalizada": "✅ Sessão de lançamentos concluída. Ficou massa!",

    # --- Gamificação ---
    "gamif_usuario_nao_encontrado": "Vixe... não localizei seu perfil de jogo financeiro ainda.",
    "gamif_ranking_titulo": "🏆 <b>HALL DA FAMA GLOBAL</b> 🏆\n\n",
    "gamif_ranking_footer": "💪 <b>Continue evoluindo pra chegar no topo!</b>",
    "gamif_stats_header": (
        "╭─────────────────────╮\n"
        "│ 📊 ESTATÍSTICAS PRO │\n"
        "╰─────────────────────╯\n\n"
        "👤 <b>{nome}</b>\n🏆 Nível <b>{nivel}</b> | ⭐ <b>{xp} XP</b> Total\n🔥 Streak: <b>{streak} dias</b>\n\n"
    ),
    "gamif_stats_footer": "💪 <b>Segue firme que tá no caminho certo!</b>",
    "gamif_rewards_header": (
        "╭─────────────────────╮\n│ 💎 SISTEMA DE XP 💎 │\n╰─────────────────────╯\n\n"
        "🎯 <b>Como ganhar XP:</b>"
    ),
    "gamif_achievements_header": "╭─────────────────────╮\n│ 🏅 SUAS CONQUISTAS 🏅│\n╰─────────────────────╯\n\n",
    "gamif_achievements_footer": "💪 <b>Continue evoluindo para desbloquear mais!</b>",
    "gamif_desafios_header": (
        "╭─────────────────────╮\n│ 🎯 DESAFIOS DIÁRIOS │\n╰─────────────────────╯\n\n🔥 <b>Missões de hoje:</b>\n"
    ),
    "gamif_desafios_footer": "💪 <b>Aceite o desafio e domine suas finanças!</b>",
    "gamif_conquistas_desbloqueadas_label": "🏆 <b>CONQUISTAS DESBLOQUEADAS:</b>",
    "gamif_conquistas_proximas_label": "🎯 <b>PRÓXIMAS CONQUISTAS:</b>",
    "gamif_perfil_header": (
        "╭─────────────────────╮\n"
        "│  🎮 SEU PERFIL GAMER  │\n"
        "╰─────────────────────╯\n\n"
        "{user_emoji} <b>{nome_display_upper}</b>\n"
        "🏅 {titulo_especial}\n"
        "🏆 Nível {nivel} - {level_titulo}\n"
        "⭐ <b>{xp_formatado} XP</b> acumulados\n"
        "📊 <b>{total_transacoes}</b> transações registradas\n"
        "📅 <b>{transacoes_semana}</b> esta semana\n\n"
        "{streak_visual}\n"
        "🔥 <b>{streak_dias} DIAS</b> consecutivos\n\n"
        "{progress_text}\n\n"
    ),
    "gamif_perfil_footer": "🎮 <b>Use os botões abaixo para explorar mais!</b>",
    "gamif_perfil_progress_template": (
        "📊 PROGRESSO PARA NÍVEL {proximo_nivel}\n{progress_bar} {progresso_percent}%\n"
        "💫 Faltam apenas {xp_faltante} XP para subir!"
    ),
    "gamif_perfil_progress_max": "👑 NÍVEL MÁXIMO ALCANÇADO!\n⭐ {xp_formatado} XP - Você é uma LENDA!",
    "gamif_rankings_header": (
        "╭─────────────────────╮\n"
        "│ 🏆 HALL DA FAMA 🏆 │\n"
        "╰─────────────────────╯\n\n"
        "🔥 <b>TOP PLAYERS DO MUNDO!</b> 🔥\n\n"
    ),
    "gamif_rankings_position_footer": (
        "🎯 <b>SUA POSIÇÃO: #{posicao}</b>\n"
        "🏆 Nível {nivel} | ⭐ {xp_formatado} XP\n"
        "📈 Continue subindo no ranking!\n\n"
    ),
    "gamif_rankings_no_position": "🎯 <b>Sua posição aparecerá aqui quando ganhar XP!</b>",
    "gamif_rankings_weekly_placeholder": (
        "═══════════════════════\n\n"
        "💵 <b>RANKING SEMANAL DE ECONOMIA</b>\n"
        "🚧 Em desenvolvimento! Grandes novidades chegando!\n\n"
        "💡 <i>Dica: Use /perfil para ver seu progresso detalhado!</i>"
    ),
    "gamif_rewards_footer_hint": "💪 <b>Cada ação conta para sua evolução financeira!</b>",
    "gamif_challenges_body": (
        "🔥 <b>MISSÕES DE HOJE:</b>\n\n"
        "📝 Registre 3 transações (+30 XP)\n"
        "💬 Use a IA 2 vezes (+20 XP)\n"
        "📊 Gere 1 gráfico (+15 XP)\n"
        "🔥 Mantenha seu streak (+10 XP)\n\n"
        "🎁 <b>BÔNUS SEMANAL:</b>\n"
        "🏆 Complete 7 dias seguidos\n"
        "💎 Ganhe <b>100 XP EXTRA!</b>\n\n"
        "⏰ <b>Reinicia em:</b> Meia-noite\n\n"
        "{footer}"
    ),

    # --- Fatura / Importação PDF ---
    "fatura_start_intro": (
        "📄 <b>Analisador de Faturas de Cartão</b>\n\n"
        "🚧 <i>Função em evolução — pequenos comportamentos podem mudar.</i>\n\n"
        "Me envie o PDF da sua fatura que eu extraio e preparo tudo pra você revisar. ✨"
    ),
    "fatura_file_muito_grande": (
        "❌ <b>Arquivo muito grande!</b>\n\n"
        "📊 Tamanho: {tamanho_atual:.1f} MB (limite {tamanho_limite} MB)\n\n"
        "💡 Compacte o PDF ou deixe só as páginas de transações."
    ),
    "fatura_timeout_download": (
        "⏰ <b>Timeout no download</b>\n\n"
        "O arquivo demorou demais ou a conexão caiu. Tenta de novo com um PDF menor."
    ),
    "fatura_download_erro_generico": (
        "❌ <b>Erro ao baixar arquivo</b>\n\n"
        "Não consegui concluir o download. Reenvia ou tenta outro PDF."
    ),
    "fatura_layout_nao_reconhecido": (
        "📄 <b>Layout não reconhecido</b>\n\n"
        "⚠️ Ainda não sei ler esse formato de fatura.\n\n"
        "🤝 Quer ajudar? Envie um modelo ANONIMIZADO (sem dados pessoais) pro e-mail do dev.\n"
        "Enquanto isso, pode continuar usando /lancamento manual."
    ),
    "fatura_sem_cartoes": (
        "😕 Você não tem cartões de crédito cadastrados ainda. Use /configurar pra adicionar e volte em seguida."
    ),
    "fatura_recebida_processando": (
        "✅ Fatura recebida! Comecei o processamento em segundo plano.\n\n"
        "Pode levar até <b>1 minuto</b>. Assim que terminar eu aviso aqui."
    ),
    "fatura_analise_concluida": (
        "✅ Análise concluída! Encontrei <b>{qtd_transacoes}</b> transações válidas.\n\n"
        "{nota_parcelas}A qual cartão essa fatura pertence?"
    ),
    "fatura_nota_parcelas": (
        "📅 <b>Nota:</b> Detectei <b>{total_parcelas}</b> parcelamentos do {banco} (só a 1ª parcela entra).\n\n"
    ),
    "fatura_confirm_importacao": (
        "<b>Confirme a importação</b>\n\n"
        "Transações: <b>{qtd}</b>\nValor total: <b>{valor_total}</b>\n\n"
        "<b>Prévia:</b>\n{preview}\n\n"
        "Salvar todos estes lançamentos neste cartão?"
    ),
    "fatura_salvando": "💾 Verificando e salvando no banco de dados...",
    "fatura_dados_sessao_perdidos": (
        "❌ <b>Erro</b>\n\nOs dados da sessão se perderam. Operação cancelada."
    ),
    "fatura_importacao_concluida": (
        "✅ <b>Importação concluída!</b>\n\n"
        "📊 Processadas: <b>{total_processadas}</b>\n"
        "💾 Novas salvas: <b>{total_novas}</b>{linha_duplicadas}\n"
        "{nota_parcelas}{oferta_parcelas}"
    ),
    "fatura_linha_duplicadas": "\n🔄 Duplicadas ignoradas: <b>{total_duplicadas}</b>",
    "fatura_todas_duplicadas": (
        "🔄 <b>Todas as transações já existiam</b>\n\n"
        "Nada novo pra salvar — seus dados seguem atualizados."
    ),
    "fatura_nenhuma_valida": "🤔 Nenhuma transação válida pra salvar.",
    "fatura_erro_grave": (
        "❌ <b>Erro grave</b>\n\nNão consegui salvar as transações agora. Tente mais tarde."
    ),
    "fatura_parcelas_detectadas_resumo": (
        "📅 <b>Parcelas Futuras Detectadas ({banco})</b>\n"
        "Foram identificados <b>{total_parcelas}</b> parcelamentos (apenas primeiras parcelas incluídas).\n{exemplos}\n"
        "💡 Deseja gerar agendamentos para as futuras parcelas?"
    ),
    "fatura_exemplos_parcelas_item": "• {descricao}",
    "fatura_parcelas_criadas": (
        "✅ <b>Agendamentos criados!</b>\n\n"
        "📅 Parcelas: <b>{qtd}</b>\n🏦 Banco: <b>{banco}</b>\n📝 Tipo: Mensais\n\n"
        "Use /agendar pra ajustar valores conforme necessário."
    ),
    "fatura_parcelas_dados_expirados": (
        "❌ <b>Erro</b>\n\nNão há dados de parcelas disponíveis (expirou). Reprocese a fatura."
    ),
    "fatura_parcelas_erro_criar": (
        "❌ <b>Erro</b> ao criar agendamentos. Tente novamente depois ou use /agendar manualmente."
    ),
    "fatura_parcelas_nao_incluidas": (
        "✅ Tudo certo! Lançamentos salvos. Parcelas futuras não foram incluídas.\n\n"
        "Use /agendar se mudar de ideia."
    ),

    # --- Metas (Goals) ---
    "metas_erro_salvar": "❌ Houve um erro ao salvar sua meta. Tente novamente mais tarde.",
    "metas_erro_remover": "❌ Erro ao remover a meta. Ela pode já ter sido removida.",
    "metas_id_invalido": "❌ Erro: ID da meta inválido.",
    "metas_erro_inesperado": "❌ Ocorreu um erro inesperado.",
    "metas_erro_atualizar": "❌ Houve um erro ao tentar atualizar sua meta. Tente novamente.",

    # --- Relatório ---
    "relatorio_erro_gerar": "❌ Ocorreu um erro ao gerar o relatório. Tente novamente em alguns minutos.",
    "relatorio_erro_geral": "❌ Ops! Ocorreu um erro ao gerar seu relatório. A equipe já foi notificada.",

    # --- Agendamentos ---
    "ag_menu_intro": (
        "🗓️ <b>Gerenciador de Agendamentos</b>\n\n"
        "Automatize lançamentos recorrentes (salários, contas, assinaturas, parcelas)."
    ),
    "ag_novo_titulo": "🗓️ <b>Novo Agendamento</b>",
    "ag_pergunta_tipo": (
        "Primeiro: é uma entrada (recebimento) ou saída (pagamento)?\n\n"
        "🟢 Entrada: Salário, freelance, vendas\n🔴 Saída: Aluguel, contas, parcelas"
    ),
    "ag_prompt_descricao": (
        "{emoji} <b>Agendamento de {tipo}</b>\n\n📝 Descrição?\n\n"
        "Exemplos: {'Salário mensal / Freelance projeto X / Dividendos' if True else ''}"
    ),
    "ag_descricao_invalida": (
        "⚠️ <b>Descrição inválida</b>\nUse entre 2 e 200 caracteres. Ex: <i>Aluguel apartamento</i>"
    ),
    "ag_prompt_valor": (
        "{emoji} <b>{descricao}</b>\n\n💰 Valor? (se parcelado, valor da parcela)\n\n"
        "Exemplos: <code>1500</code>, <code>350.50</code>, <code>2500.00</code>"
    ),
    "ag_valor_invalido": (
        "⚠️ <b>Valor inválido</b>\nDigite só números (ponto opcional)."
    ),
    "ag_resumo_categoria_prompt": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n\n📂 Categoria: escolha uma."
    ),
    "ag_prompt_primeira_data": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n📂 {categoria}\n\n"
        "📅 Primeira ocorrência?\nFormato: <code>DD/MM/AAAA</code>"
    ),
    "ag_data_invalida": (
        "⚠️ <b>Data inválida</b>\nUse <code>DD/MM/AAAA</code> futuro."
    ),
    "ag_prompt_frequencia": (
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n📅 {data}\n\n"
        "🔁 Frequência?"
    ),
    "ag_prompt_recorrencia": (
        "🔁 <b>Repetição: {freq}</b>\n\nFixo (X vezes) ou contínuo?"
    ),
    "ag_prompt_total_parcelas": (
        "🔢 Quantas ocorrências no total?\nEx: 12, 6, 24"
    ),
    "ag_total_parcelas_invalido": (
        "⚠️ <b>Número inválido</b>\nDigite inteiro positivo."
    ),
    "ag_confirmacao_resumo": (
        "✅ <b>Confirme seu agendamento</b>\n\n"
        "{emoji} <b>{descricao}</b>\n💰 {valor}\n📂 {categoria}\n📅 Primeira: {data_primeira}\n"
        "🔁 {recorrencia}\n\n<i>Você receberá lembretes automáticos.</i>"
    ),
    "ag_salvando": "💾 Salvando agendamento...",
    "ag_criado_sucesso": (
        "✅ <b>Agendamento criado!</b>\n\n{emoji} <b>{descricao}</b>\n💰 {valor}\n🔁 {frequencia}\n📅 Próximo: {data_proxima}\n\n"
        "🔔 <i>Lembretes ativados.</i>"
    ),
    "ag_erro_salvar": (
        "❌ <b>Erro ao salvar</b>\nTente novamente logo mais."
    ),
    "ag_cancelado": (
        "❌ <b>Agendamento cancelado</b>\nNenhum dado foi salvo."
    ),
    "ag_lista_vazia": "Você não tem nenhum agendamento ativo.",
    "ag_lista_header": "📋 <b>Seus Agendamentos Ativos:</b>",
    "ag_cancelar_sucesso": (
        "✅ <b>Agendamento cancelado</b>\n{descricao} removido."
    ),
    "ag_cancelar_erro": (
        "❌ <b>Erro inesperado</b>\nTente novamente depois."
    ),
    "ag_nao_encontrado": (
        "❌ <b>Agendamento não encontrado</b> ou sem permissão."
    ),

    # --- Contato ---
    "contact_menu_intro": (
        "🙋‍♂️ <i><b>Desenvolvido com 💙 por Henrique</b></i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💬 <b>Quer falar comigo?</b>\n\n"
        "Manda sugestão, bug, ideia ou só um alô — até um café ☕🙂\n\n"
        "Escolhe uma opção abaixo:"
    ),
    "contact_assunto_prompt": (
        "✍️ <b>Qual o assunto?</b>\n\nExemplos: Sugestão para /gerente, Bug no OCR, Dúvida em metas..."
    ),
    "contact_assunto_registrado": (
        "✅ <b>Assunto registrado!</b>\n\nAgora me conte os detalhes. Inclua e-mail se quiser resposta."
    ),
    "contact_enviando": "Enviando sua mensagem... 🚀",
    "contact_email_sucesso": (
        "✅ Mensagem enviada! Muito obrigado pelo feedback."
    ),
    "contact_email_falha": (
        "❌ Não consegui enviar agora. Tente mais tarde, por favor."
    ),
    "contact_pix_info": (
        "❤️ <b>Gratidão pelo apoio!</b>\n\nSeu café ajuda a manter o projeto vivo.\n\n"
        "👇 Toque para copiar:\n<code>{pix_key}</code>"
    ),
    "contact_pix_indisponivel": (
        "❤️ <b>Pix indisponível</b> — chave não configurada. Obrigado mesmo assim!"
    ),
    "contact_close": "✅ Fechado! Qualquer coisa é só chamar.",

    # --- Edição de lançamentos ---
    "editar_intro": (
        "Vamos caçar esse lançamento pra ajeitar do jeitinho certo. Prefere ver os últimos ou buscar pelo nome?"
    ),
    "editar_cancelada": "Tranquilo, cancelei a edição aqui. Qualquer coisa é só chamar de novo!",
    "editar_busca_prompt": (
        "Manda um pedacinho do nome do lançamento (tipo: iFood, Mercado, Boleto)... que eu tento achar pra você."
    ),
    "editar_nenhum_recente": "Rapaz... não achei lançamento recente pra mostrar agora.",
    "editar_nenhum_busca": "Oxente, não achei nada com '{termo}'. Quer tentar outro nome?",
    "editar_selecione": "Achei esses aqui. Qual deles você quer editar?",
    "editar_cockpit": (
        "<b>⚙️ Editando Lançamento</b>\n\n"
        "<b>Descrição:</b> {descricao}\n"
        "<b>Valor:</b> <code>{valor}</code>\n"
        "<b>Data:</b> {data}\n"
        "<b>Categoria:</b> {categoria}\n\n"
        "Escolhe o que vamos mexer agora ou finaliza lá embaixo."
    ),
    "editar_prompt_descricao": "Qual a nova descrição que quer colocar?",
    "editar_prompt_valor": "Me diz o novo valor (ex: 54.30). Se tiver vírgula eu converto, relaxa.",
    "editar_prompt_data": "Qual a nova data? Manda no formato DD/MM/AAAA que eu entendo (ex: 15/12/2025).",
    "editar_formato_invalido": "Vixe... esse formato me enrolou. Tenta de novo, parceiro(a).",
    "editar_atualizado_sucesso": "Arretado! Lançamento atualizado com sucesso!",
    "editar_atualizado_erro": "Eita... não consegui salvar as mudanças agora. Tenta mais tarde?",
    "editar_deletado_sucesso": "Pronto. Tirei esse lançamento da sua vida. ✨",
    "editar_deletado_erro": "Rapaz... não consegui apagar. Quer tentar outra vez?",
    "editar_selecione_categoria": "Beleza. Agora escolhe a nova categoria aí:",
    "editar_selecione_subcategoria": "Se quiser, escolhe uma subcategoria também:",
    "editar_lancamento_nao_encontrado": "Vixe... não encontrei esse lançamento. Talvez já foi apagado?",
    
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
