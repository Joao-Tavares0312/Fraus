"""Onde a API le do disco -- e ate onde ela pode ler.

Duas coisas moram aqui: os caminhos configuraveis por ambiente (modelo,
fusor, banco, metricas, raiz de importacao) e a contencao da importacao, que
resolve todo caminho pedido DENTRO da raiz e recusa qualquer escape.
"""

import json
import os
from pathlib import Path

from fastapi import HTTPException

# A raiz do projeto, deduzida do proprio arquivo: fraus/api/caminhos.py -> ../..
RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent


def artefato(variavel: str, padrao: str) -> Path:
    """Caminho de um artefato de treino, ancorado no PROJETO e nao no cwd.

    O DEFEITO QUE ISTO TRANCA, pago em 04/09/2026: estes caminhos eram
    relativos puros, logo resolvidos contra o diretorio de trabalho de quem
    lancou o processo. Um uvicorn iniciado de fora da raiz nao achava nenhum
    dos quatro artefatos, e o `scripts/api_demo.py` -- que escolhe o motor pela
    PRESENCA dos arquivos -- caia para o dublê sem que nada quebrasse. A tela
    seguiu mostrando numero sintetico com cara de predicao. O lugar de onde se
    digita o comando nao pode decidir se voce recebe medicao ou invencao.

    A variavel de ambiente continua VENCENDO e nao e reancorada: quem a exporta
    esta declarando onde o arquivo esta, e mover isso para dentro do projeto
    seria desobedecer configuracao explicita. O conserto vale para o PADRAO.
    """
    declarado = os.environ.get(variavel)
    if declarado:
        return Path(declarado)
    return RAIZ_PROJETO / padrao


CAMINHO_MODELO_TEXTO = artefato("FRAUS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao")
CAMINHO_MODELO_EMOCAO = artefato("FRAUS_CAMINHO_MODELO_EMOCAO", "modelos/bertimbau-emocao")
CAMINHO_MODELO_IRONIA = artefato("FRAUS_CAMINHO_MODELO_IRONIA", "modelos/bertimbau-ironia")
CAMINHO_FUSOR = artefato("FRAUS_CAMINHO_FUSOR", "modelos/fusor.joblib")

# QUEM EXECUTA os tres BERTimbau: "torch" (os checkpoints de `modelos/`) ou
# "onnx" (os grafos de `modelos-onnx/`, sem torch instalado). Nao ha deteccao
# nem fallback: um backend escolhido pela PRESENCA de arquivo e o defeito que
# `artefato` ja documenta, e cair do onnx para o torch em silencio seria servir
# um executor que ninguem declarou (invariante 7). Valor desconhecido e erro no
# boot, em `backend_declarado`.
#
# A variante aceita em docs/encolhimento.md: satisfacao e emocao em fp32 (as
# duas pontuam e nao toleram int8) e ironia em int8 (nao pontua) -- 0 de 180
# categorias trocadas, e ~1,5x mais rapida que o torch na mesma CPU.
BACKENDS = ("torch", "onnx", "onnx-multitarefa")
CAMINHO_ONNX_TEXTO = artefato("FRAUS_CAMINHO_ONNX_TEXTO", "modelos-onnx/bertimbau-satisfacao")
CAMINHO_ONNX_EMOCAO = artefato("FRAUS_CAMINHO_ONNX_EMOCAO", "modelos-onnx/bertimbau-emocao")
CAMINHO_ONNX_IRONIA = artefato("FRAUS_CAMINHO_ONNX_IRONIA", "modelos-onnx/bertimbau-ironia")
CAMINHO_ONNX_MULTITAREFA = artefato(
    "FRAUS_CAMINHO_ONNX_MULTITAREFA", "modelos-onnx/bertimbau-multitarefa"
)


def backend_declarado() -> str:
    """`FRAUS_BACKEND`, padrao "torch". Lido no boot, recusado se desconhecido."""
    valor = (os.environ.get("FRAUS_BACKEND") or "torch").strip().lower()
    if valor not in BACKENDS:
        raise ValueError(
            f"FRAUS_BACKEND={valor!r} nao existe. Use um de {BACKENDS}."
        )
    return valor
# O BANCO nao entra na regra acima: ele nao e artefato de treino, e sim estado
# de quem opera. `fraus.db` relativo ao cwd continua sendo o comportamento de
# sempre, e `FRAUS_DATABASE_URL` e o caminho de deploy de verdade.
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
# Ancoradas no projeto pelo mesmo motivo dos pesos: metrica que some por causa
# do cwd faz `/modelo` devolver `metricas: null`, e a tela passa a dizer "nao
# medimos" sobre um treino que MEDIU. E mentira por acidente de lancamento.
CAMINHO_METRICAS = artefato(
    "FRAUS_CAMINHO_METRICAS", "modelos/bertimbau-satisfacao/metricas.json"
)
CAMINHO_METRICAS_EMOCAO = artefato(
    "FRAUS_CAMINHO_METRICAS_EMOCAO", "modelos/metricas_emocao.json"
)
CAMINHO_METRICAS_IRONIA = artefato(
    "FRAUS_CAMINHO_METRICAS_IRONIA", "modelos/metricas_ironia.json"
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
