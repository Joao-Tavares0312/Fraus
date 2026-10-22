"""O benchmark local: estrutura do laudo, sem modelo nem download (dubles)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fraus.corpora import Exemplos
from scripts import benchmark_motores as bm


@pytest.fixture
def dubles(monkeypatch):
    ex = Exemplos(textos=["a", "b", "c", "d"], rotulos=[0, 1, 0, 1],
                  nomes_classes=["nao_ironico", "ironico"])
    monkeypatch.setitem(bm.CONJUNTOS, "ironia", lambda amostra: [{
        "id": "x", "nome": "X", "independente": True, "exemplos": ex, "ressalvas": [],
    }])
    respostas = {
        "ref": [[0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0.2, 0.8]],   # 3/4
        "cand": [[0.9, 0.1], [0.1, 0.9], [0.7, 0.3], [0.2, 0.8]],  # 4/4
    }
    monkeypatch.setattr(bm, "prever", lambda caminho, textos: respostas[Path(caminho).name])


def test_linha_de_base_com_um_modelo_nao_compara(dubles):
    laudo = bm.medir("ironia", {"bertimbau": Path("ref")}, None)
    (c,) = laudo["conjuntos"]
    assert c["modelos"]["bertimbau"]["acuracia"] == pytest.approx(0.75)
    assert "comparacao" not in c
    assert len(c["impressao"]) == 64


def test_dois_modelos_geram_comparacao_pareada_com_o_segundo_como_candidato(dubles, tmp_path):
    saida = tmp_path / "laudo.json"
    assert bm.main(["ironia", "--modelo", "base=ref", "--modelo", "novo=cand",
                    "--saida", str(saida)]) == 0
    laudo = json.loads(saida.read_text())
    k = laudo["conjuntos"][0]["comparacao"]
    assert (k["referencia"], k["candidato"]) == ("base", "novo")
    assert k["mcnemar"]["so_candidato"] == 1 and k["mcnemar"]["so_referencia"] == 0
    assert laudo["procedencia"]["modelos"] == {"base": "ref", "novo": "cand"}


def test_numero_de_classes_divergente_falha_alto(dubles, monkeypatch):
    monkeypatch.setattr(bm, "prever", lambda caminho, textos: [[0.3, 0.3, 0.4]] * len(textos))
    with pytest.raises(ValueError, match="classes"):
        bm.medir("ironia", {"bertimbau": Path("ref")}, None)


def test_regua_de_ironia_tem_dez_de_cada_lado(monkeypatch, tmp_path):
    from fraus.corpora import Exemplos

    monkeypatch.setattr(bm, "baixar", lambda url, destino: tmp_path)
    monkeypatch.setattr(bm.corpora, "ler_multipico", lambda caminho: Exemplos(
        textos=[f"t{i}" for i in range(3000)], rotulos=[int(i % 3 == 0) for i in range(3000)],
        grupos=[f"p{i}" for i in range(3000)], nomes_classes=["nao_ironico", "ironico"]))
    mp, c = bm.conjuntos_ironia(None)
    assert mp["id"] == "ironia_multipico" and mp["independente"]
    assert c["exemplos"].rotulos.count(0) == c["exemplos"].rotulos.count(1) == 10
