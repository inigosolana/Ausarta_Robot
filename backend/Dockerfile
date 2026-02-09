# Backend Dockerfile - API + Agent
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto de la API
EXPOSE 8001

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1
ENV BRIDGE_SERVER_URL=http://127.0.0.1:8001

# Script de inicio que lanza API y Agent
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
