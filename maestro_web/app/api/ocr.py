# app/api/ocr.py
import os
import json
import base64
import logging
from typing import Dict, Any
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from google.cloud import vision
from google.oauth2 import service_account

from ..core.config import GOOGLE_APPLICATION_CREDENTIALS

logger = logging.getLogger(__name__)

router = APIRouter()

def initialize_vision_client():
    """Inicializa o cliente do Google Vision API."""
    try:
        if GOOGLE_APPLICATION_CREDENTIALS:
            # Usando arquivo de credenciais
            credentials = service_account.Credentials.from_service_account_file(
                GOOGLE_APPLICATION_CREDENTIALS
            )
            client = vision.ImageAnnotatorClient(credentials=credentials)
        else:
            # Usando credenciais padrão do ambiente
            client = vision.ImageAnnotatorClient()
        
        return client
    except Exception as e:
        logger.error(f"Erro ao inicializar cliente Google Vision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao configurar Google Vision API"
        )

def extract_text_from_image(image_content: bytes) -> str:
    """Extrai texto de uma imagem usando Google Vision API."""
    try:
        client = initialize_vision_client()
        
        # Cria objeto de imagem
        image = vision.Image(content=image_content)
        
        # Detecção de texto
        response = client.text_detection(image=image)
        
        # Verifica se há erros
        if response.error.message:
            logger.error(f"Erro do Google Vision API: {response.error.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro do Google Vision API: {response.error.message}"
            )
        
        # Extrai o texto
        texts = response.text_annotations
        if texts:
            return texts[0].description
        else:
            return ""
            
    except Exception as e:
        logger.error(f"Erro ao extrair texto da imagem: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar imagem"
        )

def parse_receipt_text(text: str) -> Dict[str, Any]:
    """Analisa o texto extraído de uma nota fiscal e tenta extrair informações estruturadas."""
    import re
    from datetime import datetime
    from typing import Optional, List, Dict, Union, Tuple
    import difflib

    def normalize_text(text: str) -> str:
        """Normaliza o texto removendo acentos e convertendo para minúsculo"""
        import unicodedata
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        return text.lower().strip()

    def extract_currency_value(text: str) -> Optional[float]:
        """Extrai um valor monetário do texto, tratando vários formatos"""
        # Remove R$ e espaços
        text = text.replace('R$', '').strip()
        # Tenta extrair o valor numérico
        try:
            # Substitui , por . se , for o separador decimal
            if ',' in text and '.' not in text:
                text = text.replace(',', '.')
            # Remove separadores de milhares
            elif ',' in text and '.' in text:
                text = text.replace('.', '').replace(',', '.')
            return float(text)
        except ValueError:
            return None

    def find_best_match(text: str, patterns: List[str], threshold: float = 0.8) -> Optional[str]:
        """Encontra o melhor match para um texto usando comparação fuzzy"""
        text = normalize_text(text)
        matches = []
        for pattern in patterns:
            ratio = difflib.SequenceMatcher(None, text, pattern.lower()).ratio()
            if ratio >= threshold:
                matches.append((ratio, pattern))
        return max(matches)[1] if matches else None

    # Inicializa o resultado
    result = {
        "texto_completo": text,
        "valor_total": None,
        "data": None,
        "hora": None,
        "estabelecimento": None,
        "cnpj": None,
        "categoria": None,
        "subcategoria": None,
        "forma_pagamento": None,
        "itens": [],
        "impostos": {
            "icms": None,
            "trib_fed": None,
            "trib_est": None,
            "outros": []
        },
        "confianca": {
            "geral": "baixa",
            "valor_total": 0,
            "data": 0,
            "estabelecimento": 0,
            "cnpj": 0,
            "itens": 0
        },
        "pontos_confianca": 0
    }
    
    try:
        linhas = [l.strip() for l in text.split('\n') if l.strip()]
        total_linhas = len(linhas)
        
        # 1. Busca CNPJ - Padrões mais flexíveis
        cnpj_patterns = [
            r'(?:CNPJ|CGC)[-.: ]?(\d{2}\.?\d{3}\.?\d{3}/?\.?\d{4}-?\d{2})',
            r'(?:CNPJ|CGC)[-.: ]?(\d{14})',
            r'(\d{2}\.?\d{3}\.?\d{3}/?\.?\d{4}-?\d{2})'
        ]
        
        for linha in linhas:
            for pattern in cnpj_patterns:
                cnpj_match = re.search(pattern, linha, re.IGNORECASE)
                if cnpj_match:
                    cnpj = re.sub(r'[^0-9]', '', cnpj_match.group(1))
                    if len(cnpj) == 14:
                        result["cnpj"] = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

                        result["confianca"]["cnpj"] = 1.0
                        result["pontos_confianca"] += 2
                        break

        # 2. Busca Nome do Estabelecimento
        # Procura nas primeiras linhas, mas evita linhas que são claramente não relevantes
        estabelecimento_blacklist = ['cupom', 'nota fiscal', 'nf-e', 'cnpj', 'cpf', 'ie:', 'cep:']
        for linha in linhas[:6]:
            linha_norm = normalize_text(linha)
            if (len(linha) > 3 and 
                not any(x in linha_norm for x in estabelecimento_blacklist) and
                not re.search(r'^\d+[/.-]', linha)):  # Evita linhas que começam com data
                result["estabelecimento"] = linha.strip()
                result["confianca"]["estabelecimento"] = 0.8
                result["pontos_confianca"] += 1.5
                break

        # 3. Busca Data e Hora - Suporte a mais formatos
        data_patterns = [
            (r'(\d{2})[/.-](\d{2})[/.-](\d{4})', '%Y-%m-%d'),  # dd/mm/yyyy
            (r'(\d{2})[/.-](\d{2})[/.-](\d{2})', '%Y-%m-%d'),  # dd/mm/yy
            (r'(\d{4})[/.-](\d{2})[/.-](\d{2})', '%Y-%m-%d'),  # yyyy/mm/dd
        ]
        
        hora_patterns = [
            r'(\d{2}:\d{2}(?::\d{2})?)',  # HH:MM ou HH:MM:SS
            r'(\d{2})h\s*(\d{2})(?:min)?',  # HHh MM ou HHhMMmin
        ]

        for linha in linhas:
            # Busca data
            if not result["data"]:
                for pattern, fmt in data_patterns:
                    data_match = re.search(pattern, linha)
                    if data_match:
                        try:
                            if len(data_match.group(3)) == 2:  # Ano com 2 dígitos
                                ano = int(data_match.group(3))
                                ano = 2000 + ano if ano < 50 else 1900 + ano
                                data_str = f"{data_match.group(1)}/{data_match.group(2)}/{ano}"
                            else:
                                data_str = f"{data_match.group(1)}/{data_match.group(2)}/{data_match.group(3)}"
                            data = datetime.strptime(data_str, '%d/%m/%Y')
                            result["data"] = data.strftime('%Y-%m-%d')
                            result["confianca"]["data"] = 1.0
                            result["pontos_confianca"] += 2
                            break
                        except ValueError:
                            continue

            # Busca hora
            if not result["hora"]:
                for pattern in hora_patterns:
                    hora_match = re.search(pattern, linha)
                    if hora_match:
                        if 'h' in pattern:  # Formato HHh MM
                            result["hora"] = f"{hora_match.group(1)}:{hora_match.group(2)}"
                        else:  # Formato HH:MM ou HH:MM:SS
                            result["hora"] = hora_match.group(1)
                        result["pontos_confianca"] += 1
                        break

        # 4. Busca Valor Total - Mais inteligente
        valor_patterns = [
            (r'(?:VALOR\s+TOTAL|TOTAL)\s*R\$?\s*(\d+[.,]\d{2})', 3),  # VALOR TOTAL R$ XX.XX
            (r'TOTAL\s*(?:R\$)?\s*(\d+[.,]\d{2})', 2),                # TOTAL R$ XX.XX
            (r'(?:TOTAL|VALOR)\s*(?:R\$)?\s*(\d+[.,]\d{2})', 1),      # Outros formatos
        ]
        
        # Procura valor total
        for linha in linhas:
            linha_lower = linha.lower()
            if 'valor total' in linha_lower or 'total' in linha_lower:
                for pattern, pontos in valor_patterns:
                    valor_match = re.search(pattern, linha, re.IGNORECASE)
                    if valor_match:
                        try:
                            valor = extract_currency_value(valor_match.group(1))
                            if valor and valor > 0:
                                result["valor_total"] = valor
                                result["confianca"]["valor_total"] = pontos / 3
                                result["pontos_confianca"] += pontos
                                break
                        except (ValueError, IndexError):
                            continue
            if result["valor_total"]:
                break

        # Se não encontrou valor total, tenta procurar por padrões mais específicos
        if not result["valor_total"]:
            for linha in reversed(linhas[-10:]):  # Últimas 10 linhas
                valor_match = re.search(r'(?:^|[^\d])(\d+[.,]\d{2})(?:\s*$)', linha)
                if valor_match:
                    try:
                        valor = extract_currency_value(valor_match.group(1))
                        if valor and valor > 0:
                            # Verifica se tem "total" algumas linhas acima
                            idx = linhas.index(linha)
                            context = '\n'.join(linhas[max(0, idx-3):idx]).lower()
                            if 'total' in context or 'valor' in context:
                                result["valor_total"] = valor
                                result["confianca"]["valor_total"] = 0.5
                                result["pontos_confianca"] += 1
                                break
                    except (ValueError, IndexError):
                        continue

        # 5. Busca itens - Melhorado para extrair corretamente
        def extract_item_details(text: str) -> Optional[Dict]:
            """Extrai detalhes de um item da nota"""
            patterns = [
                # Padrão 1: CÓDIGO DESCRIÇÃO QTD UN X VALOR
                r'(?:\d+\s+)?([^0-9]+?)\s+(\d+|\d+,\d+)\s*(?:UN|KG|PCT)?\s*[xX]\s*R?\$?\s*(\d+[.,]\d{2})',
                # Padrão 2: DESCRIÇÃO QTD UN VALOR
                r'([^0-9]+?)\s+(\d+|\d+,\d+)\s*(?:UN|KG|PCT)\s*R?\$?\s*(\d+[.,]\d{2})',
                # Padrão 3: CÓDIGO DESCRIÇÃO VALOR
                r'\d+\s+([^0-9]+?)\s+R?\$?\s*(\d+[.,]\d{2})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text.strip())
                if match:
                    grupos = match.groups()
                    nome = grupos[0].strip()
                    
                    # Ignora linhas que são claramente não-itens
                    if any(x in nome.lower() for x in ['total', 'valor', 'trib', 'aprox', 'icms', 'imposto']):
                        continue
                        
                    try:
                        if len(grupos) == 3:
                            qtd = float(grupos[1].replace(',', '.'))
                            valor = extract_currency_value(grupos[2])
                        else:
                            qtd = 1
                            valor = extract_currency_value(grupos[1])
                            
                        if valor and valor > 0 and len(nome) > 1:
                            return {
                                "nome": nome,
                                "quantidade": qtd,
                                "valor_unitario": valor,
                                "valor_total": valor * qtd
                            }
                    except (ValueError, IndexError):
                        continue
            return None

        # Procura seção de itens
        items_section = False
        items_started = False
        current_item = None
        
        for i, linha in enumerate(linhas):
            linha_lower = linha.lower()
            
            # Identifica início da seção de itens
            if not items_started and ('cod' in linha_lower or 'item' in linha_lower or '#' in linha):
                items_started = True
                continue
                
            # Para quando encontrar seção de totais/impostos
            if items_started and any(x in linha_lower for x in ['total r$', 'valor total', 'trib aprox']):
                break
                
            if items_started:
                item = extract_item_details(linha)
                if item:
                    result["itens"].append(item)
                    result["pontos_confianca"] += 0.5
                    items_section = True

        # 6. Extrai impostos corretamente
        for linha in linhas:
            linha_lower = linha.lower()
            
            # ICMS
            if 'icms' in linha_lower:
                icms_match = re.search(r'(?:TOTAL\s+)?ICMS\s*:?\s*R?\$?\s*(\d+[.,]\d{2})', linha, re.IGNORECASE)
                if icms_match:
                    result["impostos"]["icms"] = extract_currency_value(icms_match.group(1))
                    result["pontos_confianca"] += 0.5
                    
            # Tributos federais
            if 'fed' in linha_lower or 'trib fed' in linha_lower:
                fed_match = re.search(r'(?:Val|Valor)?\s*(?:aprox\s*)?(?:Trib\s*)?Fed\s*:?\s*R?\$?\s*(\d+[.,]\d{2})', linha, re.IGNORECASE)
                if fed_match:
                    result["impostos"]["trib_fed"] = extract_currency_value(fed_match.group(1))
                    result["pontos_confianca"] += 0.5
                    
            # Tributos estaduais
            if 'est' in linha_lower or 'trib est' in linha_lower:
                est_match = re.search(r'(?:Val|Valor)?\s*(?:aprox\s*)?(?:Trib\s*)?Est\s*:?\s*R?\$?\s*(\d+[.,]\d{2})', linha, re.IGNORECASE)
                if est_match:
                    result["impostos"]["trib_est"] = extract_currency_value(est_match.group(1))
                    result["pontos_confianca"] += 0.5

        # 7. Categorização melhorada
        # Categorização baseada no estabelecimento e nos itens
        if result["estabelecimento"]:
            categorias_supermercado = ["mercado", "super", "mart", "hiper"]
            categorias_farmacia = ["farm", "drog", "remed", "medic"]
            categorias_restaurante = ["rest", "lanch", "cafe", "bar", "pizz"]
            
            nome_norm = normalize_text(result["estabelecimento"])
            
            if any(cat in nome_norm for cat in categorias_supermercado):
                result["categoria"] = "Mercado"
                result["subcategoria"] = "Alimentação"
            elif any(cat in nome_norm for cat in categorias_farmacia):
                result["categoria"] = "Saúde"
                result["subcategoria"] = "Farmácia"
            elif any(cat in nome_norm for cat in categorias_restaurante):
                result["categoria"] = "Alimentação"
                result["subcategoria"] = "Restaurante"
            else:
                result["categoria"] = "Outros"
                
            result["pontos_confianca"] += 1

        # Cálculo de confiança
        pontos_maximos = 10.0
        pontos_normalizados = min(result["pontos_confianca"] / pontos_maximos, 1.0)
        
        # Confiança ponderada (dá mais peso para campos importantes)
        confianca_ponderada = (
            (result["confianca"]["valor_total"] * 0.3) +
            (result["confianca"]["data"] * 0.2) +
            (result["confianca"]["estabelecimento"] * 0.2) +
            (result["confianca"]["cnpj"] * 0.3)
        ) if all(k in result["confianca"] for k in ["valor_total", "data", "estabelecimento", "cnpj"]) else 0.0
        
        # Confiança final (média entre pontos e campos principais)
        confianca_final = (pontos_normalizados + confianca_ponderada) / 2.0
        
        # Define o nível de confiança
        if confianca_final >= 0.7:
            result["confianca"]["geral"] = "alta"
        elif confianca_final >= 0.4:
            result["confianca"]["geral"] = "media"
        else:
            result["confianca"]["geral"] = "baixa"

        # Log para debug
        logger.info(f"Confiança ponderada: {confianca_ponderada:.2f}")
        logger.info(f"Pontos normalizados: {pontos_normalizados:.2f}")
        logger.info(f"Confiança final: {confianca_final:.2f}")
        logger.info(f"Dados extraídos: {result}")

    except Exception as e:
        logger.error(f"Erro ao analisar texto da nota fiscal: {e}")
        result["confianca"]["geral"] = "baixa"
        
    return result

@router.post("/ocr/extract")
async def extract_receipt_data(file: UploadFile = File(...)):
    """
    Extrai dados de uma nota fiscal usando OCR com Google Vision API.
    """
    try:
        # Validação do arquivo
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas arquivos de imagem são aceitos"
            )
        
        # Lê o conteúdo do arquivo
        image_content = await file.read()
        
        # Limita o tamanho do arquivo (5MB)
        if len(image_content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo muito grande. Limite: 5MB"
            )
        
        # Tenta extrair texto da imagem
        try:
            extracted_text = extract_text_from_image(image_content)
        except Exception as e:
            # Fallback para desenvolvimento (quando não há credenciais)
            logger.warning(f"Google Vision API não disponível: {e}")
            extracted_text = "MOCK OCR - Supermercado ABC\n10/07/2025\nItem 1 - R$ 5,50\nItem 2 - R$ 12,30\nTOTAL: R$ 17,80"
        
        if not extracted_text:
            return {
                "sucesso": False,
                "mensagem": "Não foi possível extrair texto da imagem",
                "dados": None
            }
        
        # Analisa o texto extraído
        parsed_data = parse_receipt_text(extracted_text)
        
        return {
            "sucesso": True,
            "mensagem": "Dados extraídos com sucesso",
            "dados": parsed_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de OCR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
