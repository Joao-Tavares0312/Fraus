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

# O TORCH DE CPU, E AS DUAS ARMADILHAS DE ARQUITETURA.
#
# x86_64: o pacote do PyPI arrasta as bibliotecas de CUDA (varios GB) que nunca
# serao usadas num host sem GPU. Por isso o indice proprio do PyTorch,
# `/whl/cpu`, que so tem a variante de CPU.
#
# aarch64 (ARM): o indice `/whl/cpu` NAO publica wheel de ARM, entao apontar
# para ele ali simplesmente nao resolve o pacote. E o PyPI mudou de lado
# embaixo: ate a versao 2.10, `pip install torch` em aarch64 trazia a variante
# de CPU; a partir da 2.11 ele passou a trazer a COM CUDA por padrao -- a mesma
# armadilha do x86, com a diferenca de que aqui nao ha indice alternativo para
# fugir dela.
#
# A saida em ARM e fixar a ultima serie em que o PyPI ainda entrega CPU. Isso e
# um PIN POR MOTIVO EXTERNO, nao preferencia: quando o PyTorch publicar wheel
# de CPU para ARM num indice proprio, esta linha some.
#
# MEDIDO no indice do PyPI em 11/09/2026, wheel cp312 manylinux_2_28_aarch64:
#
#     torch 2.10.0 -> 146 MB      <- CPU puro, e o que este pin busca
#     torch 2.11.0 -> 420 MB      <- o salto e a CUDA de ARM entrando
#     torch 2.14.0 -> 454 MB
#
# O triplo de tamanho e a evidencia: nada em CPU cresce assim entre duas
# versoes menores. Se um dia a 2.10 sair do indice, e por este numero que a
# substituta deve ser escolhida -- nao pela mais nova.
#
# A Oracle Always Free e ARM (Ampere A1) -- as VMs x86 gratuitas dela tem 1 GB
# de RAM e a API mede 1.056 MB, entao nao ha escolha de arquitetura ali.
#
# CONFIRA DEPOIS DE CONSTRUIR, porque o erro e silencioso -- a imagem funciona,
# so fica alguns GB maior:
#
#   docker run --rm fraus-api python -c "import torch; print(torch.__version__, torch.version.cuda)"
#
# Esperado: uma versao terminada em `+cpu` e `None` na segunda posicao.
#
# NAO MEDE POR TAMANHO. A versao anterior deste comentario mandava conferir
# "~500 MB" com `du`, e em 11/09/2026 o build x86 media 769 MB de torch
# 2.14.0+cpu -- CPU puro, sem um pacote nvidia sequer. O torch simplesmente
# engordou entre uma versao e outra, e a sonda de tamanho acusaria CUDA onde
# nao ha. `torch.version.cuda` e o fato; megabyte e palpite.
# O torch SOZINHO e primeiro, porque e a unica dependencia que precisa de
# tratamento por arquitetura -- e porque e a cara: isolada nesta camada, ela
# fica em cache e uma mudanca de codigo nao a reinstala.
COPY pyproject.toml README.md ./
RUN set -eux; \
    if [ "$(uname -m)" = "aarch64" ]; then \
        pip install --no-cache-dir "torch==2.10.*"; \
    else \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    fi

COPY fraus/ ./fraus/

# O RESTO VEM DO `pyproject.toml`, e isso e correcao de um defeito real, nao
# arrumacao. Ate 11/09/2026 esta linha era uma lista escrita A MAO em paralelo
# a do pyproject -- e as duas divergiram sem que nada reclamasse: faltavam
# `pyjwt`, `openpyxl`, `python-docx`, `pypdf` e `python-multipart`. A imagem
# CONSTRUIA normalmente e so morria no boot, com `ModuleNotFoundError: No
# module named 'jwt'`, longe da causa.
#
# Uma lista mantida a mao nao tem como envelhecer bem: quem acrescenta uma
# dependencia mexe no pyproject, nao aqui. Instalar o proprio projeto acaba com
# a classe inteira do problema -- o torch ja esta satisfeito pela camada acima,
# entao o indice de CPU escolhido la continua valendo.
#
# O `scikit-learn==1.6.1` continua PINADO, no pyproject: e a versao que gerou o
# `fusor.joblib`, e outra desserializa com aviso de que o resultado PODE ser
# invalido -- score silenciosamente errado e o pior defeito possivel aqui.
RUN pip install --no-cache-dir .

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
#
# `FRAUS_CHAVE_MESTRA` TAMBEM nao tem valor padrao aqui, pelo mesmo motivo:
# sem ela a API sobe aberta (uso local, com aviso no boot); com ela, toda rota
# exige `Authorization: Bearer`, exceto POST /ingestao (que segue exigindo
# chave de fonte). Defina antes de expor a URL na internet:
#
#   docker run -p 8000:8000 \
#     -v "$PWD/modelos:/modelos:ro" \
#     -v "$PWD/dados:/dados" \
#     -e FRAUS_ORIGENS=https://SUA-DASHBOARD.vercel.app \
#     -e FRAUS_CHAVE_MESTRA=$(openssl rand -hex 32) \
#     fraus-api

EXPOSE 8000

CMD ["uvicorn", "fraus.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
