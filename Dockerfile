# Usamos una imagen base oficial de Python 3.12
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalamos dependencias del sistema y swig (para pyscard)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcsclite-dev \
    pcscd \
    libusb-1.0-0-dev \
    swig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalamos setuptools para pkg_resources
RUN pip install --upgrade pip setuptools wheel

WORKDIR /app
COPY . /app

# Instalamos dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "main.py"]
