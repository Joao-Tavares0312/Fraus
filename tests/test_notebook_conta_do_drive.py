"""Os notebooks de treino (01, 03, 04 e 07) so gravam no Drive da conta da Unis.

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


@pytest.mark.parametrize("nome", ["01_treino_bertimbau.ipynb", "03_treino_emocao.ipynb",
                                  "04_treino_ironia.ipynb", "07_treino_laya.ipynb"])
def test_notebook_confere_a_conta_do_drive_depois_de_montar(nome):
    fonte = _celula_do_mount(nome)
    assert f"CONTA_DRIVE = '{CONTA}'" in fonte
    assert fonte.index("drive.mount(") < fonte.index("conferir_conta_do_drive(CONTA_DRIVE)")


@pytest.mark.parametrize("nome", ["01_treino_bertimbau.ipynb", "03_treino_emocao.ipynb",
                                  "04_treino_ironia.ipynb", "07_treino_laya.ipynb"])
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


@pytest.mark.parametrize("nome", ["01_treino_bertimbau.ipynb", "03_treino_emocao.ipynb",
                                  "04_treino_ironia.ipynb"])
def test_corpus_e_lido_so_pelo_que_a_celula_baixa(nome):
    # Em 08/10/2026 um `sintetico_s42.csv` de 28/09 esquecido na pasta do Drive
    # ia entrar no treino junto do IDPT: a leitura relia a pasta inteira. Desde
    # 19/10/2026 o corpus vem de `fraus.corpora` sobre arquivos que a propria
    # celula baixa -- nenhuma listagem de pasta pode voltar.
    celulas = json.loads((NOTEBOOKS / nome).read_text(encoding="utf-8"))["cells"]
    corpus = next(
        "".join(c["source"]) for c in celulas
        if "".join(c["source"]).startswith("# 3. Corpus lido por fraus.corpora")
    )
    assert "glob" not in corpus and "listdir" not in corpus
    assert "preparar_divisao(" in corpus


@pytest.mark.parametrize("nome", ["01_treino_bertimbau.ipynb", "03_treino_emocao.ipynb",
                                  "04_treino_ironia.ipynb"])
def test_treino_nunca_avalia_no_teste_para_escolher_epoca(nome):
    fonte = json.loads((NOTEBOOKS / nome).read_text(encoding="utf-8"))
    codigo = "".join("".join(c["source"]) for c in fonte["cells"] if c["cell_type"] == "code")
    assert "eval_dataset" not in codigo  # o Trainer mora em treinar_uma_semente
    assert "treinar_uma_semente(" in codigo
    assert "resumir_sementes(rodadas, chave='f1_macro_validacao')" in codigo
