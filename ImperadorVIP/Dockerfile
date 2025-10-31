# Imagem base Python
FROM python:3.11-slim

# Define diretório
WORKDIR /app

# Copia arquivos
COPY . /app

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe porta
EXPOSE 8080

# Comando padrão
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
