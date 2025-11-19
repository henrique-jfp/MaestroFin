# Dockerfile para rodar MaestroFin com suporte a WeasyPrint (HTML -> PDF)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia apenas requirements primeiro para aproveitar cache do Docker
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia o resto da aplicação
COPY . /app

# Permitir passagem de porta via env (Railway define PORT automaticamente)
ENV PORT=8000

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app", "--workers", "2", "--timeout", "120"]
