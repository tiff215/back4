# Usamos una imagen base oficial de Python 3.12
FROM python:3.12-slim

# Evitamos preguntas interactivas durante instalación
ENV DEBIAN_FRONTEND=noninteractive

# Actualizamos paquetes y añadimos dependencias necesarias para pyscard
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcsclite-dev \
    pcscd \
    libusb-1.0-0-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos del proyecto
COPY . /app

# Instalamos pip y dependencias de Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Exponemos el puerto (cámbialo según tu app)
EXPOSE 8000

# Comando por defecto para correr tu app
CMD ["python", "app.py"]
