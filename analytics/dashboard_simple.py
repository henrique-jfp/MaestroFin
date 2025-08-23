#!/usr/bin/env python3
"""
Dashboard Simples - Teste
"""

import os
import sys
from flask import Flask, render_template, jsonify

# Configurar paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
template_dir = os.path.join(parent_dir, 'templates')
static_dir = os.path.join(parent_dir, 'static')

print(f"📁 Current dir: {current_dir}")
print(f"📁 Parent dir: {parent_dir}")  
print(f"📁 Template dir: {template_dir}")
print(f"📁 Template exists: {os.path.exists(template_dir)}")

# Criar app Flask
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    try:
        return render_template('dashboard_analytics.html')
    except Exception as e:
        return f"<h1>ERRO NO TEMPLATE</h1><p>{str(e)}</p><p>Template dir: {template_dir}</p>"

@app.route('/api/test')
def api_test():
    """Teste da API"""
    return jsonify({
        "status": "ok",
        "message": "API funcionando!",
        "template_dir": template_dir,
        "template_exists": os.path.exists(os.path.join(template_dir, 'dashboard_analytics.html'))
    })

@app.route('/health')
def health():
    """Health check"""
    return "OK - Dashboard funcionando!"

if __name__ == '__main__':
    print("🚀 Iniciando dashboard de teste...")
    print("📊 Acesse: http://localhost:5000")
    print("🔧 API teste: http://localhost:5000/api/test")
    print("❤️ Health: http://localhost:5000/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
