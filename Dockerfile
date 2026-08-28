# Imagen del backend FastAPI de gi-ocr (sirve tambien frontend/ por
# StaticFiles, mismo origen). Ver docs/tecnica/empaquetado-despliegue.md
# para el detalle de arquitectura y decisiones (ADR-009).
#
# Base python:3.12-slim (Debian, no Alpine): onnxruntime y
# opencv-python-headless dependen de wheels manylinux (glibc); Alpine/musl
# forzaria compilar desde fuente, fuera de alcance de esta feature.
FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema minimas requeridas por opencv-python-headless
# en tiempo de ejecucion (libgl/libglib), sin herramientas de compilacion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python del backend.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# Codigo de la aplicacion.
COPY backend/ backend/
COPY frontend/ frontend/

# Directorios de estado runtime: se aseguran dentro de la imagen para que
# el contenedor arranque incluso sin volumenes montados (mismo
# comportamiento que en desarrollo local, donde estas carpetas se
# autocrean si faltan: storage_bridge_writer.py, inbound_watcher.py,
# job_store.py). docker-compose.yml los monta como volumenes de host para
# persistencia real entre recreaciones del contenedor.
RUN mkdir -p storage_bridge/inbound storage_bridge/ready storage_bridge/failed \
    output \
    inbound

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
