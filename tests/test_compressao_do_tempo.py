"""A espera entra no fusor em log1p -- nos dois lados, ou em nenhum.

O P0 de 08/09/2026: latencia sem teto fazia o `StandardScaler` produzir z
absurdo e o relogio mandar sozinho na nota (3 h de espera = score 0 com texto
86% satisfeito). Medido em 15/09 (`scripts/retreinar_fusor_local.py`, na versao de medicao), a
unica saida monotona e sem penhasco e `log1p`, sem teto.

O ACOPLAMENTO e o que estes testes trancam: o fusor aprende sobre valores ja
comprimidos, entao artefato treinado em segundos crus rodando num runtime que
comprime da nota errada SEM erro -- `n_features_in_` continua 39. Por isso o
artefato carrega a escala em que foi treinado, e a carga recusa a divergencia.
"""

import math

import joblib
import pytest

from fraus.fusor import (ESCALA_DO_TEMPO, FEATURES_EM_LOG, NOMES_FEATURES, Fusor,
                         FusorIncompativelError, vetorizar)


def _features(**sobrescritas):
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _treinado():
    exemplos, rotulos = [], []
    for i in range(30):
        exemplos.append(_features(texto_prob_satisfeito_media=0.9, latencia_mediana_s=5.0 + i))
        rotulos.append(2)
        exemplos.append(_features(texto_prob_insatisfeito_media=0.9, latencia_mediana_s=200.0 + i))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def test_as_quatro_de_espera_entram_em_log1p_e_so_elas():
    assert FEATURES_EM_LOG == (
        "latencia_mediana_s", "latencia_p90_s", "latencia_primeira_resposta_s", "duracao_total_s",
    )
    vetor = vetorizar(_features(latencia_mediana_s=10800.0, qtd_turnos_cliente=4.0))
    assert vetor[NOMES_FEATURES.index("latencia_mediana_s")] == pytest.approx(math.log1p(10800.0))
    # contagem nao cresce com o relogio: fica crua
    assert vetor[NOMES_FEATURES.index("qtd_turnos_cliente")] == 4.0


def test_artefato_guarda_a_escala_e_volta_intacto(tmp_path):
    caminho = tmp_path / "fusor.joblib"
    _treinado().salvar(caminho)
    assert Fusor.carregar(caminho).escala_do_tempo == ESCALA_DO_TEMPO == "log1p"


def test_artefato_treinado_em_segundos_crus_e_recusado_na_carga(tmp_path):
    """O fusor de antes de 15/09 nao tem a marca: carregar e falha alta."""
    fusor = _treinado()
    caminho = tmp_path / "antigo.joblib"
    pipeline = fusor._pipeline
    del pipeline.fraus_escala_do_tempo
    joblib.dump(pipeline, caminho)
    with pytest.raises(FusorIncompativelError, match="log1p"):
        Fusor.carregar(caminho)


def test_tres_horas_nao_pesam_mil_vezes_mais_que_dez_segundos():
    fusor = _treinado()
    z = lambda s: fusor.z_das_features(_features(latencia_mediana_s=s))["latencia_mediana_s"]
    assert abs(z(10800.0)) < 10 * abs(z(10.0) - z(200.0))


def test_distribuicao_de_treino_declara_a_escala():
    distribuicao = _treinado().distribuicao_de_treino()
    assert distribuicao["latencia_mediana_s"]["escala"] == "log1p"
    assert distribuicao["qtd_turnos_cliente"]["escala"] == "bruta"
