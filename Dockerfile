# API do Fraus, para hospedar onde houver disco e memoria de verdade.
#
# POR QUE NAO SERVERLESS (Vercel, Lambda, Cloud Functions): so o torch ocupa
# 497 MB instalado, contra o teto de 250 MB de uma funcao da Vercel -- e os
# tres BERTimbau somam mais 1,3 GB. Alem do tamanho, cada requisicao roda
# inferencia em CPU (a rota /analisar roda uma passada por palavra), o que nao
# cabe no tempo maximo de uma funcao, e o SQLite precisa de disco que sobreviva
# entre requisicoes. Isto aqui quer um container comum: Render, Railway, Fly.io
# ou uma VM.
#
# OS PESOS NAO ENTRAM NA IMAGEM. Assar 1,3 GB de modelo aqui faria cada deploy
# empurrar 1,3 GB de novo por uma mudanca de uma linha, e os pesos mudam muito
# menos que o codigo. Eles vem por volume montado em /modelos (ver
# docs/hospedagem.md). O boot falha alto se nao estiverem la -- servir predicao
# sem modelo carregado e pior do que estar fora do ar.

FROM python:3.12-slim

# libgomp: o torch de CPU precisa dele em runtime e a imagem slim nao traz.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# O torch de CPU vem do indice proprio do PyTorch: o pacote do PyPI arrasta as
# bibliotecas de CUDA (varios GB) que nunca serao usadas num host sem GPU.
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
        "pydantic>=2.7" "emoji>=2.12" "transformers>=4.44" \
        "scikit-learn==1.6.1" "joblib>=1.4" "fastapi>=0.115" "uvicorn>=0.30"

# scikit-learn PINADO em 1.6.1: e a versao que gerou o `fusor.joblib`. Versao
# diferente desserializa com aviso de que o resultado PODE ser invalido, e um
# score silenciosamente errado e o pior defeito possivel neste projeto.

COPY fraus/ ./fraus/

ENV FRAUS_CAMINHO_MODELO_TEXTO=/modelos/bertimbau-satisfacao \
    FRAUS_CAMINHO_MODELO_EMOCAO=/modelos/bertimbau-emocao \
    FRAUS_CAMINHO_MODELO_IRONIA=/modelos/bertimbau-ironia \
    FRAUS_CAMINHO_FUSOR=/modelos/fusor.joblib \
    FRAUS_CAMINHO_METRICAS=/modelos/bertimbau-satisfacao/metricas.json \
    FRAUS_CAMINHO_METRICAS_EMOCAO=/modelos/metricas_emocao.json \
    FRAUS_CAMINHO_METRICAS_IRONIA=/modelos/metricas_ironia.json \
    FRAUS_CAMINHO_BANCO=/dados/fraus.db \
    FRAUS_RAIZ_IMPORTACAO=/dados/importacao

# `FRAUS_ORIGENS` NAO tem valor padrao aqui de proposito. Ele precisa nomear a
# URL exata da dashboard publicada, e um padrao esquecido em producao seria um
# convite a liberar demais. Sem ele, a API so aceita as origens locais e a
# dashboard hospedada recebe erro de CORS -- falha visivel, que se conserta,
# em vez de uma porta aberta que ninguem nota.

EXPOSE 8000

CMD ["uvicorn", "fraus.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
