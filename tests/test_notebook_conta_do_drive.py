"""Os notebooks 04 e 07 so gravam no Drive da conta da Unis.

O `colab-mcp` se liga a aba do Colab que estiver aberta e nao escolhe conta:
em 02/10/2026 ele rodou celula na conta errada. O runtime pode ser de
qualquer conta; o Drive onde o BERTimbau e o Laya moram, nao.
"""

import ast
import json
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).parents[1] / "notebooks"
CONTA = "joao.tavaresvicente@alunos.unis.edu.br"


def _celula_do_mount(nome: str) -> str:
    celulas = json.loads((NOTEBOOKS / nome).read_text(encoding="utf-8"))["cells"]
    for celula in celulas:
        fonte = "".join(celula["source"])
        if "drive.mount(" in fonte:
            return fonte
    raise AssertionError(f"{nome} nao monta o Drive")


@pytest.mark.parametrize("nome", ["04_treino_ironia.ipynb", "07_treino_laya.ipynb"])
def test_notebook_confere_a_conta_do_drive_depois_de_montar(nome):
    fonte = _celula_do_mount(nome)
    assert f"CONTA_DRIVE = '{CONTA}'" in fonte
    assert fonte.index("drive.mount(") < fonte.index("conferir_conta_do_drive(CONTA_DRIVE)")


@pytest.mark.parametrize("nome", ["04_treino_ironia.ipynb", "07_treino_laya.ipynb"])
def test_conta_errada_nao_cai_no_fallback_silencioso(nome):
    fonte = _celula_do_mount(nome)
    # A conferencia fica FORA do try do mount: conta errada nao pode virar
    # "Drive indisponivel" e seguir gravando em /content.
    codigo = "".join(
        linha for linha in fonte.splitlines(keepends=True)
        if not linha.lstrip().startswith(("!", "%"))
    )
    arvore = ast.parse(codigo)
    for no in ast.walk(arvore):
        if isinstance(no, ast.Try):
            dentro = ast.unparse(no)
            assert "conferir_conta_do_drive(CONTA_DRIVE)" not in dentro


def test_notebook_04_le_so_o_corpus_que_a_celula_3_escolheu():
    # Em 08/10/2026 um `sintetico_s42.csv` de 28/09 esquecido na pasta do Drive
    # ia entrar no treino junto do IDPT: a leitura relia a pasta inteira em vez da
    # lista `encontrados` que a celula 3 monta para a ORIGEM escolhida.
    celulas = json.loads(
        (NOTEBOOKS / "04_treino_ironia.ipynb").read_text(encoding="utf-8")
    )["cells"]
    leitura = next(
        "".join(c["source"]) for c in celulas
        if "".join(c["source"]).startswith("# 4. Corpus lido")
    )
    assert "caminhos = encontrados" in leitura
    assert "_tabelas_em(DIR_CORPUS)" not in leitura
