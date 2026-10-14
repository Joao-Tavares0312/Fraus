"""O instrumento de aditividade: parte pura medida e recusa de artefato ruim."""

import importlib.util
import sys
from pathlib import Path

import pytest

from fraus.fusor import FusorIncompativelError
from fraus.fusor import montar_features
from tests.test_contrafactual import _c, _fusor_com_tempo_variando
from tests.test_motor import _EmocaoDuble, _TextoDuble

RAIZ = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("medir_aditividade", RAIZ / "scripts" / "medir_aditividade.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["medir_aditividade"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def test_erros_de_aditividade_ficam_abaixo_de_1e_9():
    fusor = _fusor_com_tempo_variando()
    lote = [montar_features(_c(("cliente", "oi", 0), ("bot", "ola", s), id_=f"x{s}"),
                            _TextoDuble(), _EmocaoDuble()) for s in (5, 60, 300, 600)]
    r = _script().medir_aditividade(fusor, lote)
    assert r["conversas"] == 4
    assert r["erro_score"] < 1e-9
    assert r["erro_logit"] < 1e-9


def test_artefato_ausente_falha_alto(tmp_path):
    with pytest.raises(Exception):  # FileNotFoundError do joblib: sem fallback sintetico
        _script().main(["--fusor", str(tmp_path / "nao_existe.joblib")])


def test_artefato_incompativel_falha_alto(tmp_path):
    import joblib
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    ruim = Pipeline([("escala", StandardScaler().fit([[0.0, 1.0], [1.0, 2.0]]))])
    caminho = tmp_path / "velho.joblib"
    joblib.dump(ruim, caminho)
    with pytest.raises(FusorIncompativelError):
        _script().main(["--fusor", str(caminho)])
