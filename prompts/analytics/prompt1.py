
from ..base import PromptBase
from schemas import PromptContext

class Prompt1(PromptBase):
    def __init__(self):
        super().__init__(
            nome='deteccao_de_anomalia', 
            descricao='Simula a detecção de uma anomalia nos gastos do usuário.'
        )

    def executar(self, contexto: "PromptContext") -> str:
        """
        Simula a detecção de um gasto anômalo em comparação com a média.
        """
        if not contexto.financial_report:
            return "Não tenho dados para analisar. Por favor, sincronize suas contas."

        user_name = contexto.financial_report.user_name

        # Lógica simulada:
        gasto_anomalo = {
            "categoria": "Lazer",
            "valor": 350.00,
            "media": 120.00
        }
        
        percentual_acima = ((gasto_anomalo['valor'] - gasto_anomalo['media']) / gasto_anomalo['media']) * 100

        return (
            f"📊 **Análise Automática**\n"
            f"Atenção, {user_name}! Detectei um gasto com '{gasto_anomalo['categoria']}' que está {percentual_acima:.0f}% "
            f"acima da sua média mensal. Gostaria de dar uma olhada nos detalhes?"
        )

