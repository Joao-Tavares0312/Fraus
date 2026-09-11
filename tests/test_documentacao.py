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


# ---------------------------------------------------------------------------
# O RECORTE PUBLICO
#
# O repositorio do Fraus e privado e vai continuar privado. O site, nao -- ele
# mora num repositorio publico separado, porque GitHub Pages a partir de repo
# privado exige plano pago.
#
# Isso cria uma fronteira que NAO E VISIVEL no codigo: os mesmos arquivos
# Markdown geram dois sites, e so um deles sai para a internet. Estes testes
# sao a fronteira escrita, porque a alternativa e alguem acrescentar uma pagina
# e descobrir o vazamento pelo Google.
# ---------------------------------------------------------------------------

PUBLICO = RAIZ / "mkdocs-publico.yml"
PDF = RAIZ / "mkdocs-pdf.yml"

# O que nunca pode atravessar, e por que cada um.
FORA_DO_PUBLICO = {
    "superpowers/": "specs e planos -- o diario de decisao do projeto",
    "notas/": "notas de trabalho",
    "handoff.md": 'tem a secao "a porta destrancada", que descreve a '
                  "arquitetura de autenticacao pelo lado de dentro",
    "hospedagem.md": "nomes de variavel de segredo e topologia de deploy",
}


@pytest.mark.parametrize("caminho,motivo", sorted(FORA_DO_PUBLICO.items()))
def test_o_build_publico_exclui_o_que_e_interno(caminho, motivo):
    """`exclude_docs`, e NAO `not_in_nav` -- a diferenca e o vazamento.

    `not_in_nav` so silencia o aviso de pagina fora do menu: o MkDocs continua
    CONSTRUINDO o arquivo, que fica acessivel por URL direta e listado no
    `sitemap.xml`. Quem tira do build e `exclude_docs`.
    """
    texto = PUBLICO.read_text(encoding="utf-8")
    bloco = texto[texto.index("exclude_docs:"):texto.index("nav:")]
    assert caminho in bloco, f"{caminho} precisa sair do site publico: {motivo}"


@pytest.mark.parametrize("config", [PUBLICO, PDF])
def test_nenhum_artefato_publicado_embute_codigo_fonte(config):
    """`show_source: true` coloca o CORPO das funcoes dentro do HTML e do PDF.

    Num repositorio publico isso e um atalho util. Num que se decidiu manter
    privado, e publicar o codigo por outra porta -- e nada no build reclama.

    O PDF entra aqui junto porque ele reescreve a lista de plugins inteira (o
    MkDocs substitui listas em vez de somar), entao ele pode reintroduzir o
    `true` sem tocar no config publico. Ja aconteceu uma vez.

    A sonda le so as linhas de CONFIGURACAO, descartando comentario: os dois
    arquivos EXPLICAM o perigo em prosa, e a primeira versao deste teste
    falhou contra o proprio texto que documenta a regra. Sonda que casa
    comentario mede a documentacao, nao o comportamento.
    """
    linhas = [
        linha.split("#", 1)[0]
        for linha in config.read_text(encoding="utf-8").splitlines()
        if not linha.lstrip().startswith("#")
    ]
    configuracao = "\n".join(linhas)
    assert "show_source: false" in configuracao, (
        f"{config.name} precisa declarar `show_source: false` explicitamente"
    )
    assert "show_source: true" not in configuracao, (
        f"{config.name} embute o codigo-fonte no artefato publicado"
    )


def test_o_config_publico_herda_o_principal_em_vez_de_copiar():
    """Duas copias da configuracao divergem; a que diverge e a que ninguem le."""
    assert "INHERIT: mkdocs.yml" in PUBLICO.read_text(encoding="utf-8")


def test_o_pdf_herda_o_PUBLICO_e_nao_o_interno():
    """O anexo da monografia circula em banca e vai para biblioteca.

    PDF e o formato mais dificil de despublicar que existe: herdar o config
    interno levaria o codigo-fonte e as specs para dentro dele.
    """
    assert "INHERIT: mkdocs-publico.yml" in PDF.read_text(encoding="utf-8")
