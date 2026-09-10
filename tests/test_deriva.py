"""A invariante 10 virando alarme de runtime, e nao mais disciplina de notebook.

A guarda de vazamento existente olha a distribuicao NO CORPUS. O corpus de
treino do sinal de tempo nunca passou de minutos, entao ele nao tem nada a
dizer sobre a conversa de tres horas que aparece em producao -- e nessa
conversa o relogio assume a nota (medido em 08/09/2026: latencia pesando 20x o
texto, score em 4,4e-24).

A parte pura mora aqui de proposito: ela nao precisa de BERTimbau nenhum, e
por isso a regra falha em milissegundos de pytest.
"""

import pytest

from fraus.deriva import LIMIAR_Z, resumo_de_deriva

DISTRIBUICAO = {
    "latencia_mediana_s": {"media": 30.0, "desvio": 20.0},
    "texto_prob_satisfeito_media": {"media": 0.5, "desvio": 0.2},
}


def test_sem_amostra_nenhuma_nao_se_afirma_deriva():
    """Zero conversas nao e "tudo dentro da faixa" -- e nao medimos nada.

    O `z_absoluto_observado` vem None, nunca 0.0: zero ali se leria como
    "exatamente na media do treino", a afirmacao mais tranquilizadora
    possivel, sobre uma amostra que nao existe.
    """
    saida = resumo_de_deriva([], DISTRIBUICAO)
    assert saida["conversas_na_amostra"] == 0
    assert saida["fora_da_faixa"] == []
    for feature in saida["features"]:
        assert feature["z_absoluto_observado"] is None
        assert feature["dentro_da_faixa"] is None


def test_amostra_dentro_da_faixa_nao_acusa_nada():
    zs = [{"latencia_mediana_s": 0.5, "texto_prob_satisfeito_media": -1.2}]
    saida = resumo_de_deriva(zs, DISTRIBUICAO)
    assert saida["fora_da_faixa"] == []
    assert all(f["dentro_da_faixa"] for f in saida["features"])


def test_a_feature_fora_da_faixa_e_nomeada():
    """Nomear a feature e o produto da rota -- "deriva detectada" nao aciona ninguem."""
    zs = [{"latencia_mediana_s": 537.0, "texto_prob_satisfeito_media": 0.3}]
    saida = resumo_de_deriva(zs, DISTRIBUICAO)
    assert saida["fora_da_faixa"] == ["latencia_mediana_s"]
    fora = next(f for f in saida["features"] if f["nome"] == "latencia_mediana_s")
    assert fora["dentro_da_faixa"] is False
    assert fora["z_absoluto_observado"] == pytest.approx(537.0)
    assert fora["media_treino"] == pytest.approx(30.0)
    assert fora["desvio_treino"] == pytest.approx(20.0)


def test_o_z_reportado_e_o_PIOR_da_amostra_nao_a_media():
    """Uma conversa fora da faixa entre cem dentro ainda e o caso a investigar.

    Media de z diluiria exatamente o evento que a rota existe para achar: com
    99 conversas normais, a de tres horas viraria ruido de arredondamento.
    """
    zs = [
        {"latencia_mediana_s": 0.1, "texto_prob_satisfeito_media": 0.0},
        {"latencia_mediana_s": -12.0, "texto_prob_satisfeito_media": 0.0},
        {"latencia_mediana_s": 0.2, "texto_prob_satisfeito_media": 0.0},
    ]
    saida = resumo_de_deriva(zs, DISTRIBUICAO)
    pior = next(f for f in saida["features"] if f["nome"] == "latencia_mediana_s")
    assert pior["z_absoluto_observado"] == pytest.approx(12.0)  # o modulo, e o pior


def test_o_limiar_e_parametro_e_o_default_esta_declarado():
    zs = [{"latencia_mediana_s": 5.0, "texto_prob_satisfeito_media": 0.0}]
    assert resumo_de_deriva(zs, DISTRIBUICAO)["fora_da_faixa"] == ["latencia_mediana_s"]
    assert resumo_de_deriva(zs, DISTRIBUICAO, limiar=10.0)["fora_da_faixa"] == []
    assert resumo_de_deriva(zs, DISTRIBUICAO)["limiar_z"] == pytest.approx(LIMIAR_Z)


def test_sem_distribuicao_de_treino_nao_ha_diagnostico_nenhum():
    """Fusor sem retrato: None, nao um relatorio vazio que parece saudavel."""
    assert resumo_de_deriva([{"x": 1.0}], {}) is None
