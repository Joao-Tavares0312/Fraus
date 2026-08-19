import pytest

from fraus.fusor import NOMES_FEATURES, Fusor, vetorizar


def _features(**sobrescritas) -> dict[str, float]:
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _fusor_treinado() -> Fusor:
    exemplos, rotulos = [], []
    for _ in range(40):
        exemplos.append(_features(
            texto_prob_satisfeito_media=0.9,
            texto_prob_satisfeito_ultima=0.9,
            emoji_score_medio=0.8,
            latencia_mediana_s=8.0,
        ))
        rotulos.append(2)
        exemplos.append(_features(
            texto_prob_insatisfeito_media=0.9,
            texto_prob_insatisfeito_max=0.95,
            emoji_score_medio=-0.7,
            latencia_mediana_s=300.0,
            escalou=1.0,
        ))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def test_vetorizar_respeita_a_ordem_canonica():
    vetor = vetorizar(_features(emoji_contagem=3.0))
    assert len(vetor) == len(NOMES_FEATURES)
    assert vetor[NOMES_FEATURES.index("emoji_contagem")] == 3.0


def test_feature_faltando_e_erro_e_nao_zero_silencioso():
    incompleto = _features()
    del incompleto["emoji_contagem"]
    with pytest.raises(KeyError):
        vetorizar(incompleto)


def test_conversa_positiva_pontua_alto():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    assert score > 70


def test_conversa_negativa_pontua_baixo():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_insatisfeito_media=0.9,
        texto_prob_insatisfeito_max=0.95,
        emoji_score_medio=-0.7,
        latencia_mediana_s=300.0,
        escalou=1.0,
    ))
    assert score < 30


def test_score_fica_sempre_entre_zero_e_cem():
    fusor = _fusor_treinado()
    for valor in (-5.0, 0.0, 9999.0):
        score = fusor.pontuar(_features(latencia_mediana_s=valor))
        assert 0.0 <= score <= 100.0


def test_salvar_e_carregar_preserva_o_score(tmp_path):
    fusor = _fusor_treinado()
    entrada = _features(texto_prob_satisfeito_media=0.9, emoji_score_medio=0.8)
    esperado = fusor.pontuar(entrada)

    caminho = tmp_path / "fusor.joblib"
    fusor.salvar(caminho)
    assert Fusor.carregar(caminho).pontuar(entrada) == pytest.approx(esperado)


def test_importancias_cobrem_todas_as_features():
    assert set(_fusor_treinado().importancias()) == set(NOMES_FEATURES)


def test_contribuicoes_cobrem_as_dezesseis_features():
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(emoji_score_medio=0.8))
    assert set(contribuicoes) == set(NOMES_FEATURES)


def test_contribuicoes_conversa_positiva_soma_maior_que_negativa():
    fusor = _fusor_treinado()
    positiva = fusor.contribuicoes(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    negativa = fusor.contribuicoes(_features(
        texto_prob_insatisfeito_media=0.9,
        texto_prob_insatisfeito_max=0.95,
        emoji_score_medio=-0.7,
        latencia_mediana_s=300.0,
        escalou=1.0,
    ))
    assert sum(positiva.values()) > sum(negativa.values())


def test_contribuicoes_tem_sinal_interpretavel():
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    assert contribuicoes["texto_prob_satisfeito_media"] > 0


def test_prever_devolve_uma_das_tres_classes():
    fusor = _fusor_treinado()
    assert fusor.prever(_features(texto_prob_satisfeito_media=0.9)) in (0, 1, 2)


def test_eixo_global_vazio_sem_treino():
    """Fusor nao treinado nao tem eixo -- e dict vazio, nao dezesseis zeros.

    Zero e um peso valido ("esta feature nao importa"); ausencia de treino e
    outra coisa. O grafo usa essa diferenca para OMITIR as arestas de feature
    em vez de desenhar dezesseis fios de peso zero.
    """
    assert Fusor().eixo_global() == {}


def test_eixo_global_tem_sinal():
    """Positivo empurra para satisfeito, negativo para insatisfeito.

    `importancias()` nao serve para o grafo porque e valor ABSOLUTO: ela diz
    que `escalou` pesa, nao para que lado.
    """
    eixo = _fusor_treinado().eixo_global()

    assert set(eixo) == set(NOMES_FEATURES)
    # No conjunto de treino, `escalou` so aparece nos exemplos insatisfeitos
    # e `texto_prob_satisfeito_media` so nos satisfeitos.
    assert eixo["escalou"] < 0
    assert eixo["texto_prob_satisfeito_media"] > 0


def test_contribuicoes_seguem_iguais_depois_da_extracao():
    """Trava o refactor: extrair `_diferenca` nao pode mudar a atribuicao."""
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(escalou=1.0))

    assert set(contribuicoes) == set(NOMES_FEATURES)
    assert contribuicoes["escalou"] != 0.0
