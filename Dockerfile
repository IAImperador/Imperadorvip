# Base
FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Copiar dependências
COPY requisitos.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requisitos.txt

# Copiar o restante dos arquivos
COPY . .

# Porta padrão Railway
EXPOSE 8080

# Executar o app com Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
