FROM python:3.10-slim
WORKDIR /app
COPY requisitos.txt .
RUN pip install --no-cache-dir -r requisitos.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
