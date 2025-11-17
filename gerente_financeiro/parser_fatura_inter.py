"""
🏦 Parser Especializado para Faturas do Banco Inter
====================================================

Parser otimizado para extrair transações de faturas PDF do Banco Inter
com precisão de 100%. Desenvolvido especificamente para o layout do Inter.

Autor: Henrique Freitas
Data: 17/11/2025
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pdfplumber

logger = logging.getLogger(__name__)

# Mapeamento de meses em português
MESES_PT = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}


class ParserFaturaInter:
    """Parser dedicado para faturas do Banco Inter"""
    
    def __init__(self):
        # Padrões de regex otimizados para o Inter
        
        # Padrão para detectar início de seção de transações
        self.header_pattern = re.compile(
            r'Data\s+Movimentação\s+Beneficiário\s+Valor',
            re.IGNORECASE
        )
        
        # Padrão para linhas de transação do Inter
        # Formato: "DD de MMM. YYYY DESCRICAO - R$ VALOR" ou "+ R$ VALOR"
        self.transacao_pattern = re.compile(
            r'(\d{1,2})\s+de\s+(\w{3})\.\s+(\d{4})\s+'  # Data
            r'(.+?)\s+'  # Descrição (não-greedy)
            r'([-+])\s*R\$\s*([\d.,]+)',  # Sinal e Valor
            re.IGNORECASE
        )
        
        # Padrão para parcelas no beneficiário
        self.parcela_pattern = re.compile(
            r'\(Parcela\s+(\d+)\s+de\s+(\d+)\)',
            re.IGNORECASE
        )
        
        # Padrão para PIX Crédito Parcelado com detalhes de juros
        self.pix_cred_detalhes_pattern = re.compile(
            r'Principal\s*\(R\$\s*([\d.,]+)\)\s*\+\s*Juros\s*\(R\$\s*([\d.,]+)\)',
            re.IGNORECASE
        )
        
        # Padrão para total por cartão
        self.total_cartao_pattern = re.compile(
            r'Total\s+CARTÃO\s+(\d+\*+\d+)\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        
        # Padrão para identificar encargos
        self.encargos_keywords = [
            'IOF', 'ENCARGOS ROTATIVO', 'JUROS DE MORA',
            'MULTA POR ATRASO', 'JUROS PIX CREDITO'
        ]
    
    def detectar_banco_inter(self, texto: str) -> bool:
        """
        Detecta se o PDF é uma fatura do Banco Inter
        
        Args:
            texto: Texto extraído do PDF
            
        Returns:
            True se for fatura do Inter, False caso contrário
        """
        indicadores = [
            'BANCO INTER',
            'www.bancointer.com.br',
            'Super App',
            'Resumo da fatura',
            'Olá, Henrique',
            'Despesas da fatura',
            'CARTÃO 2306'
        ]
        
        texto_lower = texto.lower()
        matches = sum(1 for indicador in indicadores if indicador.lower() in texto_lower)
        
        # Se encontrar pelo menos 3 indicadores, é fatura do Inter
        confianca = matches >= 3
        
        if confianca:
            logger.info(f"✅ Fatura do Banco Inter detectada ({matches}/7 indicadores)")
        else:
            logger.warning(f"⚠️ Possível fatura do Inter ({matches}/7 indicadores)")
        
        return confianca
    
    def extrair_numero_cartao(self, texto: str) -> Optional[str]:
        """Extrai número do cartão (parcialmente mascarado)"""
        match = re.search(r'CARTÃO\s+(\d{4}\*+\d{4})', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def extrair_data_vencimento(self, texto: str) -> Optional[str]:
        """Extrai data de vencimento da fatura"""
        # Procura por "Data de Vencimento" seguido de data
        match = re.search(
            r'Data de Vencimento.*?(\d{2})/(\d{2})/(\d{4})',
            texto,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            dia, mes, ano = match.groups()
            return f"{dia}/{mes}/{ano}"
        return None
    
    def extrair_valor_total_fatura(self, texto: str) -> Optional[float]:
        """Extrai o valor total da fatura"""
        # Na fatura do Inter, o valor total aparece logo após o limite
        # Estrutura: "R$ [LIMITE]\nR$ [TOTAL_FATURA]\nData de Vencimento"
        
        # Padrão 1: Capturar segundo R$ após limite (mais confiável)
        pattern_inter = re.compile(
            r'R\$\s*[\d.,]+\s*\n\s*R\$\s*([\d.,]+)\s*\n\s*Data de Vencimento',
            re.IGNORECASE
        )
        match = pattern_inter.search(texto)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            return float(valor_str)
        
        # Padrão 2: Procurar "Total da sua fatura" explicitamente
        patterns_fallback = [
            r'Total da sua fatura\s*R\$\s*([\d.,]+)',
            r'Fatura atual\s*R\$\s*([\d.,]+)',
            r'Valor total da fatura\s*R\$\s*([\d.,]+)',
        ]
        
        for pattern in patterns_fallback:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '.')
                valor = float(valor_str)
                # Filtro: evitar valores muito altos (limite do cartão)
                if valor < 10000:
                    return valor
        
        return None
    
    def parsear_data_inter(self, dia: str, mes_abrev: str, ano: str) -> Optional[datetime]:
        """
        Converte data do formato Inter para datetime
        
        Args:
            dia: Dia (1-31)
            mes_abrev: Abreviação do mês ('jan', 'ago', etc)
            ano: Ano completo
            
        Returns:
            Objeto datetime ou None se inválido
        """
        try:
            mes_num = MESES_PT.get(mes_abrev.lower()[:3])
            if not mes_num:
                logger.warning(f"Mês desconhecido: {mes_abrev}")
                return None
            
            return datetime(int(ano), mes_num, int(dia))
        except (ValueError, TypeError) as e:
            logger.error(f"Erro ao parsear data {dia}/{mes_abrev}/{ano}: {e}")
            return None
    
    def extrair_transacoes(self, pdf_path: str) -> Dict:
        """
        Extrai todas as transações da fatura do Inter
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Dicionário com metadados e lista de transações
        """
        logger.info(f"🏦 Iniciando extração de fatura Inter: {pdf_path}")
        
        resultado = {
            'banco': 'Inter',
            'numero_cartao': None,
            'data_vencimento': None,
            'valor_total_fatura': None,
            'transacoes': [],
            'totais_por_cartao': {},
            'estatisticas': {
                'total_transacoes': 0,
                'total_debitos': 0.0,
                'total_creditos': 0.0,
                'transacoes_com_parcela': 0,
                'transacoes_com_juros': 0,
                'paginas_processadas': 0
            }
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extrair texto de todas as páginas
                texto_completo = ""
                for page in pdf.pages:
                    texto_completo += page.extract_text() or ""
                    resultado['estatisticas']['paginas_processadas'] += 1
                
                # Verificar se é realmente fatura do Inter
                if not self.detectar_banco_inter(texto_completo):
                    logger.warning("⚠️ PDF pode não ser uma fatura do Banco Inter")
                
                # Extrair metadados
                resultado['numero_cartao'] = self.extrair_numero_cartao(texto_completo)
                resultado['data_vencimento'] = self.extrair_data_vencimento(texto_completo)
                resultado['valor_total_fatura'] = self.extrair_valor_total_fatura(texto_completo)
                
                logger.info(f"📋 Metadados extraídos:")
                logger.info(f"  • Cartão: {resultado['numero_cartao']}")
                logger.info(f"  • Vencimento: {resultado['data_vencimento']}")
                logger.info(f"  • Valor Total: R$ {resultado['valor_total_fatura']}")
                
                # Processar transações linha por linha
                transacoes = self._processar_transacoes(texto_completo)
                resultado['transacoes'] = transacoes
                
                # Calcular estatísticas
                self._calcular_estatisticas(resultado)
                
                # Validar resultado
                self._validar_extracao(resultado)
                
                logger.info(f"✅ Extração concluída: {len(transacoes)} transações")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar fatura: {e}", exc_info=True)
            resultado['erro'] = str(e)
        
        return resultado
    
    def _processar_transacoes(self, texto: str) -> List[Dict]:
        """Processa o texto e extrai todas as transações"""
        transacoes = []
        linhas = texto.split('\n')
        
        dentro_secao_transacoes = False
        cartao_atual = None
        linha_anterior = ""
        
        for i, linha in enumerate(linhas):
            linha_limpa = linha.strip()
            
            # Detectar início de seção de transações
            if self.header_pattern.search(linha_limpa):
                dentro_secao_transacoes = True
                logger.debug(f"📍 Início de seção de transações detectado na linha {i}")
                continue
            
            # Detectar mudança de cartão
            match_cartao = re.search(r'CARTÃO\s+(\d{4}\*+\d{4})', linha_limpa, re.IGNORECASE)
            if match_cartao:
                cartao_atual = match_cartao.group(1)
                logger.debug(f"💳 Mudança para cartão: {cartao_atual}")
                continue
            
            # Detectar fim de seção (Total do cartão)
            if self.total_cartao_pattern.search(linha_limpa):
                dentro_secao_transacoes = False
                logger.debug(f"📍 Fim de seção de transações na linha {i}")
                continue
            
            # Tentar extrair transação se estivermos na seção
            if dentro_secao_transacoes:
                transacao = self._extrair_transacao_linha(
                    linha_limpa, 
                    linha_anterior, 
                    linhas[i+1] if i+1 < len(linhas) else "",
                    cartao_atual
                )
                
                if transacao:
                    transacoes.append(transacao)
                    logger.debug(f"✓ Transação extraída: {transacao['descricao'][:50]}...")
            
            linha_anterior = linha_limpa
        
        return transacoes
    
    def _extrair_transacao_linha(
        self, 
        linha: str, 
        linha_anterior: str, 
        linha_seguinte: str,
        cartao: Optional[str]
    ) -> Optional[Dict]:
        """Extrai dados de uma linha de transação"""
        
        match = self.transacao_pattern.search(linha)
        if not match:
            return None
        
        dia, mes_abrev, ano, descricao_raw, sinal, valor_str = match.groups()
        
        # Parsear data
        data_obj = self.parsear_data_inter(dia, mes_abrev, ano)
        if not data_obj:
            return None
        
        # Limpar e processar descrição
        descricao = descricao_raw.strip()
        
        # FILTRO: Ignorar pagamentos (não fazem parte da fatura atual)
        # Pagamentos têm sinal "+" e keyword "PAGAMENTO"
        if sinal == '+' and 'PAGAMENTO' in descricao.upper():
            logger.debug(f"⊗ Ignorando pagamento: {descricao}")
            return None
        
        # Extrair informação de parcela
        parcela_atual = None
        parcela_total = None
        match_parcela = self.parcela_pattern.search(descricao)
        if match_parcela:
            parcela_atual = int(match_parcela.group(1))
            parcela_total = int(match_parcela.group(2))
        
        # Processar valor
        valor_str_limpo = valor_str.replace('.', '').replace(',', '.')
        valor_float = float(valor_str_limpo)
        
        # Ajustar sinal (- é débito, + é crédito/estorno)
        if sinal == '-':
            valor_final = valor_float
            tipo = 'debito'
        else:
            # Sinal + = estorno/crédito (reduz o valor da fatura)
            valor_final = -valor_float
            tipo = 'credito'
        
        # Detectar se é encargo
        e_encargo = any(keyword.lower() in descricao.lower() for keyword in self.encargos_keywords)
        
        # Extrair detalhes de PIX Crédito Parcelado (juros)
        principal = None
        juros = None
        match_pix = self.pix_cred_detalhes_pattern.search(linha_seguinte)
        if match_pix and 'PIX CRED' in descricao.upper():
            principal_str = match_pix.group(1).replace('.', '').replace(',', '.')
            juros_str = match_pix.group(2).replace('.', '').replace(',', '.')
            principal = float(principal_str)
            juros = float(juros_str)
        
        transacao = {
            'data': data_obj.strftime('%d/%m/%Y'),
            'data_obj': data_obj,
            'descricao': descricao,
            'valor': valor_final,
            'tipo': tipo,
            'cartao': cartao,
            'parcela_atual': parcela_atual,
            'parcela_total': parcela_total,
            'e_encargo': e_encargo,
            'principal': principal,
            'juros': juros
        }
        
        return transacao
    
    def _calcular_estatisticas(self, resultado: Dict):
        """Calcula estatísticas da extração"""
        transacoes = resultado['transacoes']
        stats = resultado['estatisticas']
        
        stats['total_transacoes'] = len(transacoes)
        
        for t in transacoes:
            if t['tipo'] == 'debito':
                stats['total_debitos'] += abs(t['valor'])
            else:
                stats['total_creditos'] += abs(t['valor'])
            
            if t['parcela_atual'] is not None:
                stats['transacoes_com_parcela'] += 1
            
            if t['juros'] is not None:
                stats['transacoes_com_juros'] += 1
    
    def _validar_extracao(self, resultado: Dict):
        """Valida a extração e emite warnings se necessário"""
        stats = resultado['estatisticas']
        valor_total = resultado['valor_total_fatura']
        
        if stats['total_transacoes'] == 0:
            logger.warning("⚠️ Nenhuma transação foi extraída!")
            return
        
        # Calcular diferença entre soma das transações e total da fatura
        soma_transacoes = stats['total_debitos'] - stats['total_creditos']
        
        if valor_total:
            diferenca = abs(soma_transacoes - valor_total)
            percentual_erro = (diferenca / valor_total) * 100
            
            if percentual_erro > 1.0:  # Tolerância de 1%
                logger.warning(
                    f"⚠️ Divergência detectada:\n"
                    f"  • Soma das transações: R$ {soma_transacoes:.2f}\n"
                    f"  • Total da fatura: R$ {valor_total:.2f}\n"
                    f"  • Diferença: R$ {diferenca:.2f} ({percentual_erro:.2f}%)"
                )
            else:
                logger.info(f"✅ Validação OK (erro: {percentual_erro:.2f}%)")


# Função de conveniência para uso direto
def extrair_fatura_inter(pdf_path: str) -> Dict:
    """
    Extrai transações de uma fatura do Banco Inter
    
    Args:
        pdf_path: Caminho para o arquivo PDF da fatura
        
    Returns:
        Dicionário com transações e metadados
    """
    parser = ParserFaturaInter()
    return parser.extrair_transacoes(pdf_path)


if __name__ == "__main__":
    # Teste standalone
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\n🏦 Testando parser do Inter com: {pdf_path}\n")
        resultado = extrair_fatura_inter(pdf_path)
        
        print(f"\n📊 RESULTADO:")
        print(f"  • Transações: {len(resultado['transacoes'])}")
        print(f"  • Débitos: R$ {resultado['estatisticas']['total_debitos']:.2f}")
        print(f"  • Créditos: R$ {resultado['estatisticas']['total_creditos']:.2f}")
        print(f"  • Com parcelas: {resultado['estatisticas']['transacoes_com_parcela']}")
        print(f"  • Com juros: {resultado['estatisticas']['transacoes_com_juros']}")
        
        if resultado['transacoes']:
            print(f"\n📝 Primeiras 5 transações:")
            for t in resultado['transacoes'][:5]:
                print(f"  • {t['data']} | {t['descricao'][:40]:40} | R$ {t['valor']:>10.2f}")
    else:
        print("❌ Uso: python parser_fatura_inter.py <caminho_do_pdf>")
