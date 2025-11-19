from jinja2 import Environment, FileSystemLoader, StrictUndefined
import traceback

env = Environment(loader=FileSystemLoader('templates'), undefined=StrictUndefined)
try:
    # Validar o novo template limpo
    t = env.get_template('relatorio_clean.html')
    print('TEMPLATE_OK')
except Exception as e:
    traceback.print_exc()
