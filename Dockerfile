# Usamos Python 3.13 base
FROM python:3.13-slim

# Instalar dependencias de sistema necesarias para pyscard
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcsclite-dev \
    swig \
    && rm -rf /var/lib/apt/lists/*

# Crear carpeta de la app
WORKDIR /app

# Copiar todo tu proyecto dentro del contenedor
COPY . /app

# Actualizar pip y luego instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Comando para arrancar la app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
