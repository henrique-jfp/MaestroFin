
from ..base import PromptBase
from schemas import PromptContext

class Prompt2(PromptBase):
    def __init__(self):
        super().__init__(
            nome='verificador_de_metas', 
            descricao='Verifica o progresso de metas financeiras (simulado).'
        )

    def executar(self, contexto: "PromptContext") -> str:
        """
        Verifica o progresso do usuário em direção a uma meta financeira.
        Esta é uma implementação simulada.
        """
        user_name = "Usuário"
        if contexto.financial_report and contexto.financial_report.user_name:
            user_name = contexto.financial_report.user_name

        # Lógica simulada:
        progresso_meta = 67  # Em um caso real, isso viria do banco de dados através do contexto

        return (
            f"🎯 **Progresso da Meta**\n"
            f"Olá, {user_name}! Você já atingiu {progresso_meta}% da sua meta de 'Viagem para o Japão'. "
            f"Continue assim e logo estaremos celebrando essa conquista juntos! 🎌"
        )
