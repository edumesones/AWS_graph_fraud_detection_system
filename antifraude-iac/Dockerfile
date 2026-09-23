# ==============================================================================
# Dockerfile para Aplicación Gradio + NetworkX
# Optimizado para Producción en AWS ECS Fargate
# ==============================================================================

FROM python:3.11-slim

# Metadatos
LABEL maintainer="data-science-team" \
      description="Fraud Detection Graph Analytics with Gradio + NetworkX" \
      version="1.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    GRADIO_ANALYTICS_ENABLED=False \
    GRADIO_ALLOW_FLAGGING=never \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad (matching EFS access point UID/GID)
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser

# Crear directorios con permisos apropiados
RUN mkdir -p /app/logs /app/exports /app/exports/layouts /app/data /app/persistent && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY --chown=appuser:appuser analysis ./analysis
COPY --chown=appuser:appuser dashboard ./dashboard
COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser visualization ./visualization
COPY --chown=appuser:appuser setup.py ./

# Instalar el paquete en modo editable
RUN pip install --no-cache-dir -e .

# Cambiar al usuario no-root
USER appuser

# Health check para ECS/ALB
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Exponer puerto de Gradio
EXPOSE 7860

# Comando de inicio
CMD ["python", "-m", "dashboard"]
