"""Onde a API le do disco -- e ate onde ela pode ler.

Duas coisas moram aqui: os caminhos configuraveis por ambiente (modelo,
fusor, banco, metricas, raiz de importacao) e a contencao da importacao, que
resolve todo caminho pedido DENTRO da raiz e recusa qualquer escape.
"""

import json
import os
from pathlib import Path

from fastapi import HTTPException

CAMINHO_MODELO_TEXTO = Path(os.environ.get("FRAUS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao"))
CAMINHO_MODELO_EMOCAO = Path(os.environ.get("FRAUS_CAMINHO_MODELO_EMOCAO", "modelos/bertimbau-emocao"))
CAMINHO_MODELO_IRONIA = Path(os.environ.get("FRAUS_CAMINHO_MODELO_IRONIA", "modelos/bertimbau-ironia"))
CAMINHO_FUSOR = Path(os.environ.get("FRAUS_CAMINHO_FUSOR", "modelos/fusor.joblib"))
CAMINHO_BANCO = Path(os.environ.get("FRAUS_CAMINHO_BANCO", "fraus.db"))

# ONDE o banco mora. `FRAUS_DATABASE_URL` (Postgres/Supabase) VENCE o caminho de
# arquivo quando definida: e a fonte declarada do deploy, do mesmo jeito que
# FRAUS_CHAVE_MESTRA vence a mestra gravada no banco.
#
# O motivo de existir: SQLite e um arquivo, e host de container com disco
# efemero descarta esse arquivo a cada deploy -- usuario cadastrado ontem
# simplesmente nao existe hoje, sem erro nenhum no caminho. Sem a variavel, nada
# muda: o padrao continua sendo o arquivo local.
URL_BANCO = os.environ.get("FRAUS_DATABASE_URL") or None
DESTINO_BANCO = URL_BANCO or CAMINHO_BANCO

# Onde a PRIMEIRA subida escreve a mestra e a chave de acesso que ela gera.
# E a unica copia em claro delas -- o banco guarda so o hash. Fica fora do git
# (`.gitignore`), e o servidor da dashboard le daqui para nao obrigar ninguem a
# copiar chave nenhuma para uma variavel de ambiente.
CAMINHO_CHAVES = Path(os.environ.get("FRAUS_CAMINHO_CHAVES", ".fraus-chaves.txt"))

# Exportado pelo notebook 01 (acuracia, F1-macro do BERTimbau). Ausente e
# esperado antes do treino: `/modelo` devolve `metricas: null`, nunca inventa.
# O padrao aponta para dentro da pasta do modelo porque e onde o notebook 01
# de fato grava -- metrica ao lado do peso que ela mediu, nao solta na raiz.
CAMINHO_METRICAS = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS", "modelos/bertimbau-satisfacao/metricas.json")
)
CAMINHO_METRICAS_EMOCAO = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS_EMOCAO", "modelos/metricas_emocao.json")
)
CAMINHO_METRICAS_IRONIA = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS_IRONIA", "modelos/metricas_ironia.json")
)

# Raiz unica de onde a importacao pode ler. O endpoint nao tem autenticacao
# (uso local, ver README) -- entao ele nao pode aceitar caminho arbitrario do
# sistema de arquivos: tudo que entra e resolvido DENTRO desta pasta.
RAIZ_IMPORTACAO = Path(os.environ.get("FRAUS_RAIZ_IMPORTACAO", "dados_brutos"))


def resolver_dentro_da_raiz(raiz: Path, caminho_pedido: str) -> Path:
    """Resolve `caminho_pedido` DENTRO de `raiz`, recusando qualquer escape.

    Trata os dois vetores de uma vez: `..` e caminho absoluto (que o operador
    `/` do pathlib faz substituir a raiz inteira). A verificacao de contencao
    e feita sobre os caminhos ja resolvidos -- `Path.resolve()` normaliza
    ligacao simbolica, `..` e maiusculas/minusculas do Windows.
    """
    raiz_resolvida = raiz.resolve()
    alvo = (raiz_resolvida / caminho_pedido).resolve()
    if alvo != raiz_resolvida and raiz_resolvida not in alvo.parents:
        raise HTTPException(
            status_code=400,
            detail=f"caminho fora da raiz de importacao ({raiz_resolvida}): {caminho_pedido}",
        )
    return alvo


def metricas_de(caminho: Path) -> dict | None:
    """Metricas de treino de uma cabeca, ou None se o notebook ainda nao exportou.

    None, nunca um dicionario vazio ou zerado: "nao medimos" e "medimos zero"
    sao respostas diferentes, e a interface precisa poder dizer a primeira.
    """
    if not caminho.is_file():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))
