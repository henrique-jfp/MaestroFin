from jinja2 import Environment, FileSystemLoader, StrictUndefined
import traceback

env = Environment(loader=FileSystemLoader('templates'), undefined=StrictUndefined)

# Carrega e rendeia o template com um contexto de exemplo para validar runtime
try:
    t = env.get_template('relatorio_clean.html')
    contexto_exemplo = {
        'receita_total': 1959.06,
        'despesa_total': 3195.25,
        'saldo_mes': -1236.19,
        'taxa_poupanca': -63.1,
        'gastos_agrupados': [('Alimentação', 800.00), ('Transporte', 300.00)],
        'usuario': type('U', (), {'nome_completo': 'Teste Usuario'})(),
        'mes_nome': 'Novembro',
        'ano': 2025,
        'grafico_pizza_base64': None
    }
    # Disponibiliza now() similar ao que o handler fará
    contexto_exemplo['now'] = __import__('datetime').datetime.now

    html = t.render(contexto_exemplo)
    print('TEMPLATE_OK - render length:', len(html))
except Exception as e:
    traceback.print_exc()
