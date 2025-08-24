import logging
import json
import re
import os
from datetime import datetime, timedelta
import io

from pdf2image import convert_from_bytes
import google.generativeai as genai
from google.cloud import vision
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import Session, joinedload 
from sqlalchemy import and_, func 

import config
from database.database import get_or_create_user, get_db
from models import Lancamento, ItemLancamento, Categoria, Subcategoria, Usuario
from .states import OCR_CONFIRMATION_STATE

logger = logging.getLogger(__name__)

# Configurar credenciais do Google Vision
def setup_google_credentials():
    """Configura as credenciais do Google Vision para local e Render"""
    try:
        # � RENDER FIX - Suporte para variável JSON direta
        
        # 1. RENDER: Tentar credenciais JSON diretamente da variável de ambiente
        google_creds_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        if google_creds_json:
            try:
                # Criar arquivo temporário com as credenciais
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_creds_file = os.path.join(temp_dir, 'google_vision_creds.json')
                
                with open(temp_creds_file, 'w') as f:
                    f.write(google_creds_json)
                
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_file
                logger.info("✅ RENDER: Credenciais Google Vision configuradas via JSON")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao configurar credenciais JSON: {e}")
        
        # 2. LOCAL: Verificar se já está configurado no ambiente
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if os.path.exists(cred_path):
                logger.info(f"✅ LOCAL: Credenciais já configuradas: {cred_path}")
                return True
        
        # 3. LOCAL: Tentar arquivos de credenciais locais
        base_dir = os.path.dirname(os.path.dirname(__file__))
        possible_paths = [
            os.path.join(base_dir, 'credenciais', 'googlevision2.json'),
            os.path.join(base_dir, 'credenciais', 'service-account-key.json'),
            os.path.join(base_dir, 'credenciais', 'credentials.json'),
        ]
        
        for credentials_path in possible_paths:
            if os.path.exists(credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                logger.info(f"✅ LOCAL: Credenciais configuradas: {credentials_path}")
                return True
                
        # 4. Se nenhum método funcionou
        logger.warning("⚠️ Nenhuma credencial Google Vision encontrada (local ou Render)")
        logger.info("📋 Tentando usar credenciais do ambiente Render...")
        return True  # Continua mesmo sem arquivo local (para Render)
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar credenciais: {e}")
        return False

# Configurar credenciais na inicialização
setup_google_credentials()

PROMPT_IA_OCR = """
**TAREFA:** Você é uma API especialista em analisar notas fiscais e comprovantes brasileiros para extrair e classificar os dados em um objeto JSON.
**REGRAS CRÍTICAS:**
- **SEMPRE** retorne um único objeto JSON válido, sem nenhum texto antes ou depois.
- Se um campo não for encontrado, retorne `null`.
**CONTEXTO DE CATEGORIAS DISPONÍVEIS:**
Use **EXATAMENTE** uma das seguintes categorias e suas respectivas subcategorias para classificar a transação.
{categorias_disponiveis}
**REGRAS DE EXTRAÇÃO:**
1. `documento_fiscal`: CNPJ/CPF do estabelecimento (apenas números).
2. `nome_estabelecimento`: Nome da loja/empresa. Para PIX, o nome do pagador. Para maquininhas (Cielo, Rede), use "Compra no Cartão".
3. `valor_total`: Valor final da transação.
4. `data` e `hora`: Data (dd/mm/yyyy) e hora (HH:MM:SS) da transação.
5. `forma_pagamento`: PIX, Crédito, Débito, Dinheiro, etc.
6. `tipo_transacao`: "Entrada" para recebimentos, "Saída" para compras.
7. `itens`: Uma lista de objetos com `nome_item`, `quantidade`, `valor_unitario`. Para comprovantes sem itens detalhados, retorne `[]`.
8. `categoria_sugerida`: Com base nos itens e no estabelecimento, escolha a MELHOR categoria da lista fornecida.
9. `subcategoria_sugerida`: Após escolher a categoria, escolha a MELHOR subcategoria correspondente da lista.
**EXEMPLO DE SAÍDA PERFEITA (FARMÁCIA):**
```json
{{
    "documento_fiscal": "12345678000199",
    "nome_estabelecimento": "DROGARIA PACHECO",
    "valor_total": 55.80,
    "data": "28/06/2025",
    "hora": "15:30:00",
    "forma_pagamento": "Crédito",
    "tipo_transacao": "Saída",
    "itens": [
        {{"nome_item": "DORFLEX", "quantidade": 1, "valor_unitario": 25.50}},
        {{"nome_item": "VITAMINA C", "quantidade": 1, "valor_unitario": 30.30}}
    ],
    "categoria_sugerida": "Saúde",
    "subcategoria_sugerida": "Farmácia"
}}
TEXTO EXTRAÍDO DO OCR PARA ANÁLISE:
{texto_ocr}
"""

async def _reply_with_summary(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """
    Gera e envia o resumo da transação lida pelo OCR. (Função sem alterações)
    """
    dados_ia = context.user_data.get('dados_ocr')
    if not dados_ia:
        return
    # ... (O código desta função permanece exatamente o mesmo que o seu original) ...
    tipo_atual = dados_ia.get('tipo_transacao', 'Saída')
    tipo_emoji = "🔴" if tipo_atual == 'Saída' else "🟢"
    novo_tipo_texto = "Marcar como Entrada" if tipo_atual == 'Saída' else "Marcar como Saída"
    doc = dados_ia.get('documento_fiscal') or "N/A"
    tipo_doc = "CNPJ" if len(str(doc)) == 14 else "CPF"
    categoria_sugerida = dados_ia.get('categoria_sugerida', 'N/A')
    subcategoria_sugerida = dados_ia.get('subcategoria_sugerida', 'N/A')
    categoria_str = f"{categoria_sugerida} / {subcategoria_sugerida}" if subcategoria_sugerida != 'N/A' else categoria_sugerida
    valor_float = float(dados_ia.get('valor_total', 0.0))

    itens_str = ""
    itens_lista = dados_ia.get('itens', [])
    if itens_lista:
        itens_formatados = []
        for item in itens_lista:
            nome = item.get('nome_item', 'N/A')
            qtd = item.get('quantidade', 1)
            val_unit = float(item.get('valor_unitario', 0.0))
            itens_formatados.append(f"  • {qtd}x {nome} - <code>R$ {val_unit:.2f}</code>")
        itens_str = "\n🛒 <b>Itens Comprados:</b>\n" + "\n".join(itens_formatados)

    msg = (
        f"🧾 <b>Resumo da Transação</b>\n\n"
        f"🏢 <b>Estabelecimento:</b> {dados_ia.get('nome_estabelecimento', 'N/A')}\n"
        f"🆔 <b>{tipo_doc}:</b> {doc}\n"
        f"📂 <b>Categoria Sugerida:</b> {categoria_str}\n"
        f"📅 <b>Data:</b> {dados_ia.get('data', 'N/A')} 🕒 <b>Hora:</b> {dados_ia.get('hora', 'N/A')}\n"
        f"💳 <b>Pagamento:</b> {dados_ia.get('forma_pagamento', 'N/A')}"
        f"{itens_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Tipo:</b> {tipo_atual} {tipo_emoji}\n"
        f"💰 <b>Valor Total:</b> <code>R$ {valor_float:.2f}</code>\n\n"
        f"✅ <b>Está tudo correto?</b>"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar e Salvar", callback_data="ocr_salvar")],
        [InlineKeyboardButton(f"🔄 {novo_tipo_texto}", callback_data="ocr_toggle_type")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="ocr_cancelar")]
    ]

    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.message.reply_html(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def ocr_iniciar_como_subprocesso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    🚨 VERSÃO COMPLETAMENTE REESCRITA - OCR Ultra Robusto
    """
    
    # 🔥 LOGS DETALHADOS PARA DEBUG
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"🚀 OCR iniciado por usuário: {username} (ID: {user_id})")
    
    message = await update.message.reply_text("📸 Iniciando processamento OCR...")
    
    try:
        # ===== FASE 1: CAPTURA DO ARQUIVO =====
        logger.info("📥 FASE 1: Capturando arquivo do Telegram")
        
        is_photo = bool(update.message.photo)
        file_source = update.message.photo[-1] if is_photo else update.message.document
        
        logger.info(f"📄 Tipo de arquivo: {'Foto' if is_photo else 'Documento'}")
        
        if not is_photo and update.message.document:
            logger.info(f"📎 MIME Type: {update.message.document.mime_type}")
            logger.info(f"📎 Nome arquivo: {update.message.document.file_name}")
        
        await message.edit_text("📥 Baixando arquivo do Telegram...")
        
        telegram_file = await file_source.get_file()
        file_bytearray = await telegram_file.download_as_bytearray()
        file_bytes = bytes(file_bytearray)
        
        logger.info(f"✅ Arquivo baixado: {len(file_bytes)} bytes")
        
        # ===== FASE 2: PROCESSAMENTO DE PDF/IMAGEM =====
        logger.info("🔄 FASE 2: Processando arquivo para OCR")
        
        image_content_for_vision = None
        
        if not is_photo and file_source.mime_type == 'application/pdf':
            await message.edit_text("📄 Convertendo PDF para imagem...")
            logger.info("📄 Detectado PDF - convertendo...")
            
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(file_bytes, first_page=1, last_page=1, fmt='png')
                
                if not images:
                    logger.error("❌ Falha na conversão PDF->Imagem")
                    await message.edit_text("❌ PDF não pôde ser convertido.")
                    return ConversationHandler.END
                
                with io.BytesIO() as output:
                    images[0].save(output, format="PNG")
                    image_content_for_vision = output.getvalue()
                    
                logger.info(f"✅ PDF convertido: {len(image_content_for_vision)} bytes")
                
            except Exception as pdf_error:
                logger.error(f"❌ Erro conversão PDF: {pdf_error}")
                await message.edit_text(f"❌ Erro ao processar PDF: {str(pdf_error)}")
                return ConversationHandler.END
        else:
            image_content_for_vision = file_bytes
            logger.info(f"✅ Imagem direta: {len(image_content_for_vision)} bytes")
        
        if not image_content_for_vision:
            logger.error("❌ Conteúdo da imagem está vazio")
            await message.edit_text("❌ Arquivo não pôde ser processado.")
            return ConversationHandler.END
        
        # ===== FASE 3: OCR COM DUPLO FALLBACK =====
        logger.info("🔍 FASE 3: Executando OCR")
        await message.edit_text("🔎 Lendo texto da imagem...")
        
        texto_ocr = ""
        ocr_method_used = "Nenhum"
        
        # 🥇 MÉTODO 1: Google Vision (Primário)
        logger.info("🔍 Tentativa 1: Google Vision API")
        try:
            setup_google_credentials()
            
            client = vision.ImageAnnotatorClient()
            vision_image = vision.Image(content=image_content_for_vision)
            response = client.document_text_detection(image=vision_image)
            
            if response.error.message:
                logger.error(f"❌ Google Vision API Error: {response.error.message}")
                raise Exception(f"Google Vision API: {response.error.message}")
            
            texto_ocr = response.full_text_annotation.text
            ocr_method_used = "Google Vision"
            
            logger.info(f"✅ Google Vision: {len(texto_ocr)} caracteres extraídos")
            
        except Exception as vision_error:
            logger.warning(f"⚠️ Google Vision falhou: {vision_error}")
            
            # 🥈 MÉTODO 2: Gemini Vision (Fallback)
            logger.info("🔄 Tentativa 2: Gemini Vision (Fallback)")
            await message.edit_text("🔄 Tentando método alternativo...")
            
            try:
                if not config.GEMINI_API_KEY:
                    raise Exception("GEMINI_API_KEY não configurado")
                
                genai.configure(api_key=config.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Converter para PIL Image
                from PIL import Image
                pil_image = Image.open(io.BytesIO(image_content_for_vision))
                
                prompt = """
                TAREFA: Extrair TODO o texto visível desta imagem de nota fiscal ou comprovante.
                
                INSTRUÇÕES:
                - Leia TODOS os números, valores, nomes, datas que conseguir
                - Mantenha a estrutura original do texto
                - Inclua estabelecimento, valor total, data, forma de pagamento
                - Se não conseguir ler NADA, retorne exatamente: ERRO_OCR
                
                RESPOSTA: Apenas o texto extraído, sem comentários.
                """
                
                response = await model.generate_content_async([prompt, pil_image])
                texto_gemini = response.text.strip()
                
                if texto_gemini and texto_gemini != 'ERRO_OCR' and len(texto_gemini) > 10:
                    texto_ocr = texto_gemini
                    ocr_method_used = "Gemini Vision"
                    logger.info(f"✅ Gemini Vision: {len(texto_ocr)} caracteres extraídos")
                else:
                    logger.warning(f"⚠️ Gemini Vision retornou: '{texto_gemini[:50]}...'")
                    
            except Exception as gemini_error:
                logger.error(f"❌ Gemini Vision falhou: {gemini_error}")
        
        # ===== VERIFICAÇÃO FINAL DO TEXTO =====
        logger.info(f"🔍 Verificação final: Método={ocr_method_used}, Tamanho={len(texto_ocr)}")
        
        if not texto_ocr or len(texto_ocr.strip()) < 10:
            logger.error(f"❌ OCR FALHOU: Texto insuficiente (tamanho: {len(texto_ocr)})")
            logger.error(f"Texto extraído: '{texto_ocr[:100] if texto_ocr else 'VAZIO'}'")
            
            await message.edit_text(
                "❌ <b>Falha na Leitura do OCR</b>\n\n"
                f"🔧 <b>Método testado:</b> {ocr_method_used}\n"
                f"� <b>Caracteres extraídos:</b> {len(texto_ocr)}\n\n"
                "💡 <b>Soluções:</b>\n"
                "📸 Foto mais clara e bem iluminada\n"
                "� Zoom na parte importante da nota\n"
                "📝 Ou digite os dados manualmente:\n\n"
                "<code>Local: Nome do estabelecimento\n"
                "Valor: 25.50\n"
                "Data: 24/08/2025</code>",
                parse_mode='HTML'
            )
            return ConversationHandler.END
        
        logger.info(f"✅ OCR SUCESSO: {len(texto_ocr)} caracteres - Método: {ocr_method_used}")
        
        # ===== FASE 4: PROCESSAMENTO COM IA =====
        logger.info("🧠 FASE 4: Analisando com IA")
        await message.edit_text(f"🧠 Texto extraído! Analisando com IA...\n<i>Método: {ocr_method_used}</i>", parse_mode='HTML')
        
        # Buscar categorias
        db: Session = next(get_db())
        try:
            categorias_db = db.query(Categoria).options(joinedload(Categoria.subcategorias)).all()
            categorias_formatadas = [
                f"- {cat.nome}: ({', '.join(sub.nome for sub in cat.subcategorias)})" for cat in categorias_db
            ]
            categorias_contexto = "\n".join(categorias_formatadas)
        finally:
            db.close()
        
        # Processar com IA
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        prompt = PROMPT_IA_OCR.format(texto_ocr=texto_ocr, categorias_disponiveis=categorias_contexto)
        
        ia_response = await model.generate_content_async(prompt)
        response_text = ia_response.text
        
        # Extrair JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            logger.error(f"❌ IA não retornou JSON válido: {response_text[:200]}...")
            await message.edit_text("❌ IA não conseguiu processar os dados. Tente novamente.")
            return ConversationHandler.END
        
        json_str = json_match.group(0)
        
        try:
            dados_ia = json.loads(json_str)
            logger.info("✅ Dados da IA processados com sucesso")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON inválido da IA: {e}\nJSON: {json_str[:200]}...")
            await message.edit_text("❌ IA retornou dados inválidos. Tente novamente.")
            return ConversationHandler.END
        
        # Processar valor
        valor_bruto = dados_ia.get('valor_total')
        valor_str = str(valor_bruto or '0').replace(',', '.')
        dados_ia['valor_total'] = float(valor_str) if valor_str else 0.0
        
        # Armazenar dados
        context.user_data['dados_ocr'] = dados_ia
        
        logger.info(f"✅ PROCESSO COMPLETO: {dados_ia.get('nome_estabelecimento', 'N/A')} - R${dados_ia['valor_total']}")
        
        # ===== FASE 5: MOSTRAR RESUMO =====
        await message.delete()
        await _reply_with_summary(update, context)
        
        return OCR_CONFIRMATION_STATE
        
    except Exception as e:
        logger.error(f"💥 ERRO CRÍTICO no OCR: {type(e).__name__}: {e}", exc_info=True)
        
        try:
            await message.edit_text(
                f"💥 <b>Erro Crítico no OCR</b>\n\n"
                f"🚨 <b>Tipo:</b> {type(e).__name__}\n"
                f"📝 <b>Detalhes:</b> {str(e)[:100]}...\n\n"
                f"👤 <b>Usuário:</b> {username}\n"
                f"🕒 <b>Timestamp:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
                "💡 Tente enviar outra imagem ou digite os dados manualmente.",
                parse_mode='HTML'
            )
        except Exception as msg_error:
            logger.error(f"❌ Falha ao editar mensagem de erro: {msg_error}")
            
        return ConversationHandler.END

async def ocr_action_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa a ação do botão de confirmação do OCR.
    Esta função não retorna um estado, apenas realiza a ação (salvar, etc.).
    """
    query = update.callback_query
    action = query.data
    dados = context.user_data.get('dados_ocr')
    if not dados and action != 'ocr_cancelar':
        await query.answer("Erro: Dados da sessão perdidos.", show_alert=True)
        return

    if action == "ocr_toggle_type":
        dados['tipo_transacao'] = 'Entrada' if dados.get('tipo_transacao') == 'Saída' else 'Saída'
        context.user_data['dados_ocr'] = dados
        await _reply_with_summary(query, context)
        return  # Permanece no mesmo estado, apenas atualiza a mensagem

    if action == "ocr_salvar":
        await query.edit_message_text("💾 Verificando e salvando no banco de dados...")
        db: Session = next(get_db())
        try:
            # Lógica de verificação de duplicidade e salvamento (sem alterações)
            user_info = query.from_user
            usuario_db = get_or_create_user(db, user_info.id, user_info.full_name)
            data_str = dados.get('data', datetime.now().strftime('%d/%m/%Y'))
            hora_str = dados.get('hora', '00:00:00')
            try:
                data_obj = datetime.strptime(f"{data_str} {hora_str}", '%d/%m/%Y %H:%M:%S')
            except ValueError:
                data_obj = datetime.strptime(data_str, '%d/%m/%Y')
            doc_fiscal = re.sub(r'\D', '', str(dados.get('documento_fiscal', ''))) or None
            time_window_start = data_obj - timedelta(minutes=5)
            time_window_end = data_obj + timedelta(minutes=5)
            existing_lancamento = db.query(Lancamento).filter(
                and_(
                    Lancamento.id_usuario == usuario_db.id,
                    Lancamento.valor == dados.get('valor_total'),
                    Lancamento.documento_fiscal == doc_fiscal,
                    Lancamento.data_transacao.between(time_window_start, time_window_end)
                )
            ).first()
            if existing_lancamento:
                await query.edit_message_text("⚠️ Transação Duplicada! Operação cancelada.", parse_mode='Markdown')
                return

            # Lógica de encontrar categoria/subcategoria (sem alterações)
            id_categoria, id_subcategoria = None, None
            if cat_sugerida := dados.get('categoria_sugerida'):
                categoria_obj = db.query(Categoria).filter(func.lower(Categoria.nome) == func.lower(cat_sugerida)).first()
                if categoria_obj:
                    id_categoria = categoria_obj.id
            if sub_sugerida := dados.get('subcategoria_sugerida'):
                if id_categoria:
                    subcategoria_obj = db.query(Subcategoria).filter(and_(Subcategoria.id_categoria == id_categoria, func.lower(Subcategoria.nome) == func.lower(sub_sugerida))).first()
                    if subcategoria_obj:
                        id_subcategoria = subcategoria_obj.id

            # Criação do lançamento e itens (sem alterações)
            novo_lancamento = Lancamento(
                id_usuario=usuario_db.id,
                data_transacao=data_obj,
                descricao=dados.get('nome_estabelecimento'),
                valor=dados.get('valor_total'),
                tipo=dados.get('tipo_transacao', 'Saída'),
                forma_pagamento=dados.get('forma_pagamento'),
                documento_fiscal=doc_fiscal,
                id_categoria=id_categoria,
                id_subcategoria=id_subcategoria
            )
            for item_data in dados.get('itens', []):
                valor_unit_str = str(item_data.get('valor_unitario', '0')).replace(',', '.')
                valor_unit = float(valor_unit_str) if valor_unit_str else 0.0
                qtd_str = str(item_data.get('quantidade', '1')).replace(',', '.')
                qtd = float(qtd_str) if qtd_str else 1.0
                novo_item = ItemLancamento(
                    nome_item=item_data.get('nome_item', 'Item desconhecido'),
                    quantidade=qtd,
                    valor_unitario=valor_unit
                )
                novo_lancamento.itens.append(novo_item)

            db.add(novo_lancamento)
            db.commit()

            # Mensagem de sucesso será enviada pelo handler principal
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar no banco (ocr_action_handler): {e}", exc_info=True)
            await query.edit_message_text("❌ Falha ao salvar no banco de dados. O erro foi registrado.")
        finally:
            db.close()
            context.user_data.pop('dados_ocr', None)

# 🚨 MÉTODO FALLBACK MELHORADO - OCR com Gemini Vision
async def ocr_fallback_gemini(image_content):
    """🔄 Método alternativo ultra robusto usando Gemini Vision"""
    try:
        logger.info("🔄 INICIANDO FALLBACK - Gemini Vision")
        
        if not config.GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY não configurado para fallback")
            return None
        
        # Configurar Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Gemini configurado")
        
        # Converter bytes para PIL Image com validação
        import PIL.Image
        import io
        
        try:
            image = PIL.Image.open(io.BytesIO(image_content))
            logger.info(f"✅ Imagem PIL criada: {image.size} - Modo: {image.mode}")
            
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
                logger.info("🔄 Imagem convertida para RGB")
                
        except Exception as img_error:
            logger.error(f"❌ Erro ao processar imagem PIL: {img_error}")
            return None
        
        # Prompt otimizado para OCR
        prompt = """
        🎯 TAREFA CRÍTICA: Extrair TODO o texto desta imagem de documento/nota fiscal.

        📋 INSTRUÇÕES ESPECÍFICAS:
        - Leia TODOS os textos visíveis: números, valores, nomes, datas
        - Inclua: estabelecimento, CNPJ, valor total, data, forma pagamento
        - Mantenha estrutura e pontuação originais
        - NÃO invente informações que não estão visíveis
        - Se a imagem estiver ilegível, retorne: ERRO_OCR

        ⚡ RESPOSTA: Apenas o texto extraído, sem explicações.
        """
        
        logger.info("🚀 Enviando para Gemini Vision...")
        
        # Enviar para Gemini Vision com timeout
        response = await model.generate_content_async([prompt, image])
        
        if not response or not response.text:
            logger.warning("⚠️ Gemini Vision retornou resposta vazia")
            return None
            
        texto_extraido = response.text.strip()
        
        logger.info(f"📝 Gemini Vision Response: '{texto_extraido[:100]}...' (Total: {len(texto_extraido)} chars)")
        
        # Validação rigorosa do texto extraído
        if texto_extraido and texto_extraido != 'ERRO_OCR' and len(texto_extraido) > 15:
            
            # Verificar se contém informações úteis
            useful_patterns = [
                r'\d+[.,]\d{2}',  # Valores monetários
                r'\d{2}[/.-]\d{2}[/.-]\d{2,4}',  # Datas
                r'CNPJ|CPF|\d{2}\.\d{3}\.\d{3}',  # Documentos
                r'[A-Za-z]{3,}',  # Palavras com pelo menos 3 letras
            ]
            
            useful_content = any(re.search(pattern, texto_extraido, re.IGNORECASE) for pattern in useful_patterns)
            
            if useful_content:
                logger.info(f"✅ Gemini Vision SUCESSO: {len(texto_extraido)} caracteres úteis extraídos")
                return texto_extraido
            else:
                logger.warning(f"⚠️ Gemini Vision: texto sem conteúdo útil: '{texto_extraido[:50]}...'")
                return None
        else:
            logger.warning(f"⚠️ Gemini Vision falhou: '{texto_extraido}' (len: {len(texto_extraido)})")
            return None
            
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO no fallback Gemini Vision: {type(e).__name__}: {e}", exc_info=True)
        return None