#!/bin/bash

# Script de desenvolvimento para o Maestro Financeiro

echo "🎼 Maestro Financeiro - Setup de Desenvolvimento"
echo "=============================================="

# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependências
echo "📋 Verificando dependências..."

if ! command_exists python3; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js não encontrado. Instale Node.js 18+ primeiro."
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm não encontrado. Instale npm primeiro."
    exit 1
fi

echo "✅ Dependências verificadas"

# Configurar Backend
echo ""
echo "🔧 Configurando Backend..."
cd "$(dirname "$0")"

# Criar virtual environment se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando virtual environment..."
    python3 -m venv venv
fi

# Ativar virtual environment
echo "🔄 Ativando virtual environment..."
source venv/bin/activate

# Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

# Configurar Frontend
echo ""
echo "🎨 Configurando Frontend..."
cd maestrofin-web

# Instalar dependências Node.js
echo "📦 Instalando dependências Node.js..."
npm install

# Voltar ao diretório raiz
cd ..

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo "📝 Criando arquivo .env..."
    cat > .env << EOL
# Database
DATABASE_URL=sqlite:///./maestro_financeiro.db

# JWT
SECRET_KEY=sua-chave-secreta-muito-segura-aqui-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI (opcional)
OPENAI_API_KEY=sua-chave-openai-aqui

# Desenvolvimento
DEBUG=True
ENV=development
EOL
    echo "⚠️  Lembre-se de configurar as variáveis no arquivo .env"
fi

# Função para iniciar o desenvolvimento
start_dev() {
    echo ""
    echo "🚀 Iniciando servidores de desenvolvimento..."
    
    # Iniciar backend em background
    echo "🔧 Iniciando backend (FastAPI)..."
    source venv/bin/activate
    python -m uvicorn app.main:app --reload --port 8000 &
    BACKEND_PID=$!
    
    # Esperar um pouco para o backend iniciar
    sleep 3
    
    # Iniciar frontend em background
    echo "🎨 Iniciando frontend (Next.js)..."
    cd maestrofin-web
    npm run dev &
    FRONTEND_PID=$!
    
    # Função para cleanup
    cleanup() {
        echo ""
        echo "🛑 Parando servidores..."
        kill $BACKEND_PID 2>/dev/null
        kill $FRONTEND_PID 2>/dev/null
        exit 0
    }
    
    # Capturar Ctrl+C
    trap cleanup INT
    
    echo ""
    echo "✅ Servidores iniciados!"
    echo "🔧 Backend: http://localhost:8000"
    echo "🎨 Frontend: http://localhost:3000"
    echo "📚 Docs API: http://localhost:8000/docs"
    echo ""
    echo "Pressione Ctrl+C para parar os servidores..."
    
    # Aguardar
    wait
}

# Perguntar se quer iniciar os servidores
echo ""
echo "✅ Setup concluído!"
echo ""
read -p "Deseja iniciar os servidores de desenvolvimento? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    start_dev
else
    echo "Para iniciar manualmente:"
    echo "Backend:  source venv/bin/activate && python -m uvicorn app.main:app --reload"
    echo "Frontend: cd maestrofin-web && npm run dev"
fi

echo ""
echo "🎼 Maestro Financeiro está pronto para desenvolvimento!"
echo "📖 Consulte o README.md para mais informações"
