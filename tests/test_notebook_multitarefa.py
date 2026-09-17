import ast
import json
from pathlib import Path


NOTEBOOK = Path(__file__).parents[1] / "notebooks" / "05_treino_multitarefa.ipynb"


def _notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def test_celulas_python_do_notebook_compilam():
    for indice, celula in enumerate(_notebook()["cells"]):
        if celula["cell_type"] != "code":
            continue
        codigo = "".join(
            linha
            for linha in celula["source"]
            if not linha.lstrip().startswith(("!", "%"))
        )
        try:
            ast.parse(codigo)
        except SyntaxError as erro:
            raise AssertionError(f"celula {indice} nao compila: {erro}") from erro


def test_notebook_nao_engole_falha_de_subprocesso():
    fonte = "\n".join(
        "".join(celula.get("source", [])) for celula in _notebook()["cells"]
    )
    assert "check=True" in fonte
    assert "!python" not in fonte
    assert "(DESTINO / 'model.onnx').is_file()" in fonte
    assert "SessaoMultitarefaOnnx(DESTINO)" in fonte
