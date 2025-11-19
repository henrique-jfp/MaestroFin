
from ..base import PromptBase
from schemas import PromptContext

class Prompt1(PromptBase):
    def __init__(self):
        super().__init__(
            nome='sincronizacao_open_finance', 
            descricao='Simula a verificação de novas transações via Open Finance.'
        )

    def executar(self, contexto: "PromptContext") -> str:
        """
        Simula a verificação de novas transações de contas conectadas.
        """
        # Lógica simulada:
        novas_transacoes = 5
        banco_principal = "Banco X"
        
        user_name = "Usuário"
        if contexto.financial_report and contexto.financial_report.user_name:
            user_name = contexto.financial_report.user_name

        return (
            f"🔗 **Open Finance**\n"
            f"Olá, {user_name}! Sincronização concluída. Encontrei {novas_transacoes} novas transações em suas contas conectadas. "
            f"Seus dados estão atualizados."
        )

