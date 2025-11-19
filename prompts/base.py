
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Usamos TYPE_CHECKING para evitar importação circular em tempo de execução
# schemas.py não precisa conhecer os prompts, mas os prompts precisam conhecer os schemas.
if TYPE_CHECKING:
    from schemas import PromptContext

@dataclass
class PromptBase(ABC):
    """
    Classe base abstrata e evoluída para todos os prompts do sistema.

    Um prompt agora opera dentro de um 'PromptContext', que fornece todos os
    dados e serviços necessários para executar lógicas complexas e personalizadas.
    """
    nome: str
    descricao: str

    @abstractmethod
    def executar(self, contexto: "PromptContext") -> str:
        """
        Método principal que executa a lógica do prompt.

        Args:
            contexto: Um objeto PromptContext contendo todos os dados
                      e dependências necessárias para a execução.

        Returns:
            Uma string contendo a resposta gerada pelo prompt.
        """
        pass

    # Manteremos os métodos antigos por enquanto para não quebrar o código
    # que ainda não foi refatorado, mas eles se tornarão obsoletos.
    
    def obter_resposta(self) -> str:
        """[DEPRECATED] Use executar(contexto) em vez disso."""
        return f"Este prompt ({self.nome}) ainda não foi migrado para a nova arquitetura de contexto."

    def validar_entrada(self, entrada: str) -> bool:
        """[DEPRECATED] A validação agora deve ocorrer dentro do método executar."""
        return True
