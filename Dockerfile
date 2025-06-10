# Usa uma imagem Python oficial como base
FROM python:3.9-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# ---- A LINHA MÁGICA ----
# Cria o diretório que o Streamlit está tentando criar e dá permissão total a ele.
# Isso resolve o erro "Permission denied: '/.streamlit'" na sua origem.
RUN mkdir -p /.streamlit && chmod 777 /.streamlit

# O resto do processo continua como antes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]