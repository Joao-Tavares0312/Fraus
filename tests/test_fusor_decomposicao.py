"""Decomposicao EXATA do fusor: intercepto + contribuicoes = logit, e o score
sai dos logits sem aproximacao. E o que separa "explicacao" de "historia"."""
import math

import pytest

from fraus.fusor import (FAMILIAS, NOMES_FEATURES, Fusor, SATISFEITO,
                         familia_da_feature, score_dos_logits, vetorizar)


def _features(**sobrescritas):
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _fusor_tres_classes() -> Fusor:
    exemplos, rotulos = [], []
    for i in range(30):
        ruido = (i % 7) / 10
        exemplos.append(_features(texto_prob_satisfeito_media=0.8 + ruido / 10,
                                  emoji_score_medio=0.6, latencia_mediana_s=10.0 + i))
        rotulos.append(2)
        exemplos.append(_features(texto_prob_satisfeito_media=0.4, texto_prob_insatisfeito_media=0.4,
                                  estilo_frac_caixa_alta=ruido, latencia_mediana_s=60.0 + i))
        rotulos.append(1)
        exemplos.append(_features(texto_prob_insatisfeito_media=0.9 - ruido / 10,
                                  emoji_score_medio=-0.6, latencia_mediana_s=400.0 + i, escalou=1.0))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def _fusor_binario() -> Fusor:
    exemplos, rotulos = [], []
    for i in range(20):
        exemplos.append(_features(texto_prob_satisfeito_media=0.9, latencia_mediana_s=8.0 + i))
        rotulos.append(2)
        exemplos.append(_features(texto_prob_insatisfeito_media=0.9, latencia_mediana_s=300.0 + i))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


CASOS = [
    _features(texto_prob_satisfeito_media=0.7, emoji_score_medio=0.2, latencia_mediana_s=45.0),
    _features(texto_prob_insatisfeito_media=0.8, latencia_mediana_s=10800.0, escalou=1.0),
    _features(),
]


def test_familias_cobrem_o_contrato_exatamente_uma_vez():
    assert FAMILIAS == ("texto", "emoji", "tempo", "emocao", "lexico", "estilo", "incongruencia")
    assert [familia_da_feature(n) for n in NOMES_FEATURES].count("tempo") == 7
    assert {familia_da_feature(n) for n in NOMES_FEATURES} == set(FAMILIAS)


@pytest.mark.parametrize("fabrica", [_fusor_tres_classes, _fusor_binario])
@pytest.mark.parametrize("features", CASOS)
def test_intercepto_mais_contribuicoes_reproduz_o_log_da_razao(fabrica, features):
    fusor = fabrica()
    d = fusor.decompor(features)
    probabilidades = fusor._pipeline.predict_proba([vetorizar(features)])[0]
    classes = list(fusor._pipeline.named_steps["modelo"].classes_)
    p = dict(zip(classes, probabilidades))
    for eixo in d["eixos"]:
        soma = eixo["intercepto"] + sum(eixo["contribuicoes"].values())
        assert soma == pytest.approx(eixo["logit"], abs=1e-12)
        esperado = math.log(p[eixo["classe"]] / p[d["referencia"]])
        assert eixo["logit"] == pytest.approx(esperado, abs=1e-9)
        assert sum(eixo["por_familia"].values()) == pytest.approx(
            sum(eixo["contribuicoes"].values()), abs=1e-12)


@pytest.mark.parametrize("fabrica", [_fusor_tres_classes, _fusor_binario])
@pytest.mark.parametrize("features", CASOS)
def test_score_refeito_dos_logits_e_o_score_do_fusor(fabrica, features):
    fusor = fabrica()
    d = fusor.decompor(features)
    assert d["score"] == pytest.approx(fusor.pontuar(features), abs=1e-9)
    assert score_dos_logits(d["referencia"], d["eixos"]) == pytest.approx(d["score"], abs=1e-12)


def test_eixo_satisfeito_e_a_contribuicao_que_a_tela_ja_mostra():
    """Nada muda no numero que a tela mostra hoje: o eixo 2x0 E `contribuicoes`."""
    fusor = _fusor_tres_classes()
    features = CASOS[0]
    eixo = next(e for e in fusor.decompor(features)["eixos"] if e["classe"] == SATISFEITO)
    for nome, valor in fusor.contribuicoes(features).items():
        assert eixo["contribuicoes"][nome] == pytest.approx(valor, abs=1e-12)


def test_binario_tem_um_eixo_so():
    d = _fusor_binario().decompor(CASOS[0])
    assert d["referencia"] == 0
    assert [e["classe"] for e in d["eixos"]] == [2]


def test_familia_ja_na_media_tem_efeito_zero():
    fusor = _fusor_tres_classes()
    media = fusor._pipeline.named_steps["escala"].mean_
    features = dict(CASOS[0])
    # Coloca TODA feature de estilo exatamente na media do treino.
    for i, nome in enumerate(NOMES_FEATURES):
        if familia_da_feature(nome) == "estilo":
            features[nome] = float(media[i])
    assert fusor.efeitos_por_familia(features)["estilo"] == pytest.approx(0.0, abs=1e-9)


def test_efeito_e_score_atual_menos_score_com_a_familia_na_media():
    fusor = _fusor_tres_classes()
    features = CASOS[1]
    efeitos = fusor.efeitos_por_familia(features)
    assert set(efeitos) == set(FAMILIAS)
    for familia, efeito in efeitos.items():
        assert efeito == pytest.approx(
            fusor.pontuar(features) - fusor.score_com_familia_na_media(features, familia), abs=1e-9)


def test_texto_insatisfeito_pesa_contra():
    efeitos = _fusor_tres_classes().efeitos_por_familia(CASOS[1])
    assert efeitos["texto"] < 0


def test_familia_desconhecida_e_erro():
    with pytest.raises(ValueError, match="ironia"):
        _fusor_tres_classes().score_com_familia_na_media(CASOS[0], "ironia")
