"""O site publicado nao pode prometer pagina que nao existe.

O `mkdocs build --strict` ja pega isso -- mas ele so roda no CI, depois do
merge, e a falha aparece como job vermelho num push para `main`. Estes testes
rodam junto com o resto e falham em milissegundos, antes do commit.

Eles NAO reimplementam o MkDocs: conferem duas coisas que o `--strict` pegaria
tarde demais e uma que ele nao pega (segredo em pagina publica).
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "mkdocs.yml"
DOCS = RAIZ / "docs"

# Gerado no build por `scripts/reunir_docs.py`, entao nao existe no repositorio
# limpo -- e ausencia dele aqui e o esperado, nao um defeito.
GERADOS = {"design.md"}


def _paginas_do_nav() -> list[str]:
    """Os caminhos `.md` citados no nav, sem carregar YAML.

    Ler com `yaml.safe_load` exigiria a dependencia so para isto, e o `nav`
    deste projeto e uma lista de `rotulo: arquivo.md` -- a expressao alcanca
    todos, e um formato que ela nao alcancasse apareceria como pagina
    "faltando" no teste, que e o lado certo de errar.
    """
    texto = CONFIG.read_text(encoding="utf-8")
    nav = texto[texto.index("\nnav:"):]
    return re.findall(r":\s*([\w./-]+\.md)\s*$", nav, flags=re.MULTILINE)


def test_o_nav_cita_paginas_de_verdade():
    """Renomear um `.md` sem mexer no nav publicaria um link quebrado."""
    ausentes = [
        pagina
        for pagina in _paginas_do_nav()
        if pagina not in GERADOS and not (DOCS / pagina).exists()
    ]
    assert ausentes == [], f"o nav do mkdocs.yml aponta para arquivos que nao existem: {ausentes}"


def test_o_nav_nao_esta_vazio():
    """Guarda da propria sonda: expressao que nao casa nada passaria por vacuidade."""
    assert len(_paginas_do_nav()) >= 10


@pytest.mark.parametrize(
    "modulo",
    [
        "fraus.indicadores",
        "fraus.modelos",
        "fraus.fusor",
        "fraus.evidencia",
        "fraus.deriva",
    ],
)
def test_os_modulos_da_referencia_sao_importaveis(modulo):
    """`::: fraus.x` numa pagina so vira documentacao se `fraus.x` existir.

    Sem isto, mover um modulo deixa a pagina de referencia publicada vazia --
    e vazia em silencio, porque o mkdocstrings avisa em INFO, nao em erro.
    """
    __import__(modulo)


def test_nenhuma_pagina_publica_carrega_valor_de_segredo():
    """O site e PUBLICO. Documentar que a variavel existe e certo; publicar
    exemplo com valor plausivel e como um TCC vaza credencial.

    A sonda procura ATRIBUICAO com valor concreto -- `<placeholder>`,
    `$(openssl ...)` e `"..."` passam de proposito, porque sao exatamente a
    forma certa de documentar.
    """
    suspeitos = re.compile(
        r"(FRAUS_CHAVE_MESTRA|FRAUS_CODIGO_CONVITE|FRAUS_CODIGO_DEV|FRAUS_JWT_SEGREDO)"
        r"\s*=\s*[\"']?(?![<$\"'.]|\.\.\.)([A-Za-z0-9_-]{8,})"
    )
    achados = []
    for pagina in DOCS.rglob("*.md"):
        for numero, linha in enumerate(pagina.read_text(encoding="utf-8").splitlines(), 1):
            if suspeitos.search(linha):
                achados.append(f"{pagina.relative_to(RAIZ)}:{numero}")
    assert achados == [], f"valor plausivel de segredo em pagina publicada: {achados}"
