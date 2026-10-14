import json
import random

import pytest

from fraus.conformal import (ConformalIndisponivel, abstencao, ajustar, carregar_conformal,
                             conjunto, dividir_estratificado, serializar)


def test_limites_por_ordem_com_correcao_de_amostra_finita():
    # n = 19, alvo 0.9: k_inf = floor(20*0.05) = 1, k_sup = ceil(20*0.95) = 19
    scores = list(range(1, 20))  # 1..19
    limites = ajustar({0: scores, 1: scores, 2: scores}, alvo=0.9)
    assert limites[0] == {"inferior": 1.0, "superior": 19.0, "n": 19}


def test_amostra_pequena_abre_para_os_extremos():
    # n = 5, alvo 0.9: k_inf = floor(6*0.05) = 0 -> 0.0 ; k_sup = ceil(6*0.95) = 6 > 5 -> 100.0
    limites = ajustar({0: [10, 20, 30, 40, 50], 1: [1], 2: [99]}, alvo=0.9)
    assert limites[0]["inferior"] == 0.0 and limites[0]["superior"] == 100.0


def test_classe_sem_exemplo_e_erro():
    with pytest.raises(ValueError, match="1"):
        ajustar({0: [1.0], 1: [], 2: [3.0]}, alvo=0.9)


def test_alvo_fora_de_0_1_e_erro():
    with pytest.raises(ValueError):
        ajustar({0: [1.0]}, alvo=1.0)


def test_conjunto_inclui_borda_e_pode_ser_vazio_ou_multiplo():
    limites = {0: {"inferior": 0.0, "superior": 30.0, "n": 9},
               1: {"inferior": 25.0, "superior": 70.0, "n": 9},
               2: {"inferior": 80.0, "superior": 100.0, "n": 9}}
    assert conjunto(30.0, limites) == [0, 1]
    assert conjunto(75.0, limites) == []
    assert conjunto(100.0, limites) == [2]
    assert abstencao([0, 1]) == "conjunto_multiplo"
    assert abstencao([]) == "conjunto_vazio"
    assert abstencao([2]) is None


def test_cobertura_empirica_por_classe_em_dado_permutavel():
    """Simulacao: calibracao e avaliacao da MESMA distribuicao; cobertura media >= alvo - 0.02."""
    sorteio = random.Random(20261014)
    medias = {0: 15.0, 1: 55.0, 2: 85.0}
    coberturas = {c: [] for c in medias}
    for _ in range(200):
        calib = {c: [sorteio.gauss(m, 12) for _ in range(50)] for c, m in medias.items()}
        limites = ajustar(calib, alvo=0.9)
        for c, m in medias.items():
            novos = [sorteio.gauss(m, 12) for _ in range(50)]
            coberturas[c].append(sum(c in conjunto(s, limites) for s in novos) / 50)
    for c in medias:
        assert sum(coberturas[c]) / 200 >= 0.88


def test_divisao_estratificada_disjunta_e_reprodutivel():
    rotulos = [0] * 100 + [1] * 100 + [2] * 100
    a1, b1 = dividir_estratificado(rotulos, 0.5, semente=7)
    a2, b2 = dividir_estratificado(rotulos, 0.5, semente=7)
    assert (a1, b1) == (a2, b2)
    assert set(a1).isdisjoint(b1) and sorted(a1 + b1) == list(range(300))
    assert [rotulos[i] for i in a1].count(0) == 50


def test_artefato_com_regua_diferente_e_indisponivel(tmp_path):
    caminho = tmp_path / "c.json"
    limites = ajustar({0: [1.0, 2.0], 1: [50.0, 51.0], 2: [90.0, 99.0]}, alvo=0.9)
    caminho.write_text(json.dumps(serializar(limites, 0.9, "regua-a", 1, "teste")))
    assert carregar_conformal(caminho, "regua-a")["alvo"] == 0.9
    with pytest.raises(ConformalIndisponivel, match="régua"):
        carregar_conformal(caminho, "regua-b")


def test_artefato_ausente_ou_malformado_e_indisponivel(tmp_path):
    with pytest.raises(ConformalIndisponivel):
        carregar_conformal(tmp_path / "nao-existe.json", "r")
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{nao e json")
    with pytest.raises(ConformalIndisponivel):
        carregar_conformal(ruim, "r")


# ---- validacao de conteudo do artefato ----

def _bruto(**mud):
    base = serializar(ajustar({0: [1.0, 2.0], 1: [50.0, 51.0], 2: [90.0, 99.0]}, 0.9),
                      0.9, "regua-a", 1, "teste")
    base.update(mud)
    return base


def _escrever(tmp_path, bruto):
    caminho = tmp_path / "c.json"
    caminho.write_text(json.dumps(bruto))
    return caminho


def _lim(i, s, n=2):
    return {"inferior": i, "superior": s, "n": n}


@pytest.mark.parametrize("mud", [
    {"limites": {"0": _lim(1, 2), "1": _lim(1, 2), "3": _lim(1, 2)}},
    {"limites": {"0": _lim(1, 2), "1": _lim(1, 2)}},
    {"limites": {}},
    {"limites": {"0": _lim(float("nan"), 2), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"limites": {"0": _lim(1, float("inf")), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"limites": {"0": _lim(5, 2), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"limites": {"0": _lim(-1, 2), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"limites": {"0": _lim(1, 101), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"limites": {"0": _lim(1, 2, 0), "1": _lim(1, 2), "2": _lim(1, 2)}},
    {"alvo": 1.5}, {"alvo": 0}, {"alvo": 1},
    {"regua": ""}, {"regua": 3},
])
def test_conteudo_invalido_vira_indisponivel(tmp_path, mud):
    caminho = _escrever(tmp_path, _bruto(**mud))
    regua = mud.get("regua", "regua-a")
    with pytest.raises(ConformalIndisponivel):
        carregar_conformal(caminho, regua if isinstance(regua, str) else "regua-a")


def test_garantia_em_percentual_e_holdout_b2w(tmp_path):
    caminho = _escrever(tmp_path, _bruto())
    g = carregar_conformal(caminho, "regua-a")["garantia"]
    assert "90%" in g and "0.9" not in g
    assert "holdout B2W (texto de resenha real, tempo sintético)" in g
    assert "holdout sintético" not in g
