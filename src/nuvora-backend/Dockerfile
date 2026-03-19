FROM python:3.11-slim

WORKDIR /app

# Copiar archivo de dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del backend
COPY . .

# Exponer el puerto 8000
EXPOSE 8000

# Iniciar la API FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]