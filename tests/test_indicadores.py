from datetime import datetime, timedelta, timezone

import pytest

from fraus.indicadores import (FAIXAS_NPS, calcular_csat, calcular_nps,
                               categoria_nps, containment_rate, nota_0_10,
                               serie_diaria, validar_faixas_nps)
from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("nota,esperado", [
    (0, "detrator"), (6, "detrator"),
    (7, "neutro"), (8, "neutro"),
    (9, "promotor"), (10, "promotor"),
])
def test_fronteiras_das_faixas_de_nps(nota, esperado):
    assert categoria_nps(nota * 10) == esperado


def test_score_vira_nota_de_zero_a_dez():
    assert nota_0_10(0.0) == 0
    assert nota_0_10(64.0) == 6
    assert nota_0_10(66.0) == 7
    assert nota_0_10(100.0) == 10


@pytest.mark.parametrize("score,nota", [
    (0.0, 0),
    (5.0, 0),    # meio exato: arredondamento bancario desempata para o par
    (65.0, 6),   # fronteira detrator/neutro
    (85.0, 8),   # fronteira neutro/promotor
    (100.0, 10),
])
def test_nota_nos_pontos_limite(score, nota):
    """Trava o arredondamento do servidor -- ele e a fonte da verdade da nota.

    A dashboard nao recalcula: consome a `nota` que a API devolve. Se este
    teste mudar, a interface muda junto, por construcao.
    """
    assert nota_0_10(score) == nota


def test_nps_calculado_a_mao_confere():
    # 5 promotores (100), 2 neutros (75), 3 detratores (30)
    scores = [100.0] * 5 + [75.0] * 2 + [30.0] * 3
    assert calcular_nps(scores) == pytest.approx(20.0)  # 50% - 30%


def test_nps_de_lista_vazia_e_ausencia_nao_zero():
    """Sem score nenhum nao existe NPS: 0 seria um numero medido que ninguem mediu."""
    assert calcular_nps([]) is None


def test_csat_de_lista_vazia_e_ausencia_nao_zero():
    assert calcular_csat([]) is None


def test_csat_e_a_fracao_com_nota_sete_ou_mais():
    scores = [100.0, 80.0, 70.0, 30.0]
    assert calcular_csat(scores) == pytest.approx(75.0)


def test_containment_rate_ignora_conversas_escaladas():
    def conversa(escalou: bool, indice: int) -> Conversa:
        return Conversa(
            id=f"c{indice}",
            canal="csv",
            iniciada_em=BASE,
            escalou_para_humano=escalou,
            mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=BASE)],
        )

    conversas = [conversa(False, 1), conversa(False, 2), conversa(True, 3), conversa(True, 4)]
    assert containment_rate(conversas) == pytest.approx(50.0)


# --- faixas de NPS configuraveis -------------------------------------------


def test_categoria_aceita_faixas_alternativas_por_parametro():
    """Faixa vem por parametro -- nunca de estado global mutavel."""
    faixas = {"detrator": (0, 4), "neutro": (5, 7), "promotor": (8, 10)}
    assert categoria_nps(50.0, faixas) == "neutro"
    assert categoria_nps(50.0) == "detrator"  # padrao de fabrica intacto


def test_faixas_de_fabrica_sao_validas():
    validar_faixas_nps(FAIXAS_NPS)


@pytest.mark.parametrize("faixas,trecho", [
    ({"detrator": (0, 5), "neutro": (7, 8), "promotor": (9, 10)}, "buraco"),
    ({"detrator": (0, 7), "neutro": (7, 8), "promotor": (9, 10)}, "sobrepoe"),
    ({"detrator": (1, 6), "neutro": (7, 8), "promotor": (9, 10)}, "0"),
    ({"detrator": (0, 6), "neutro": (7, 8), "promotor": (9, 9)}, "10"),
    ({"detrator": (0, 6), "neutro": (8, 7), "promotor": (9, 10)}, "vazia"),
])
def test_faixas_invalidas_nomeiam_o_problema(faixas, trecho):
    with pytest.raises(ValueError) as erro:
        validar_faixas_nps(faixas)
    assert trecho in str(erro.value)


def test_faixas_sem_as_tres_categorias_sao_recusadas():
    with pytest.raises(ValueError) as erro:
        validar_faixas_nps({"detrator": (0, 6), "promotor": (7, 10)})
    assert "neutro" in str(erro.value)


def test_nps_agregado_usa_as_faixas_recebidas():
    """`/indicadores` e `/conversas` precisam concordar: mesma faixa, uma fonte."""
    scores = [80.0] * 4  # nota 8: neutro de fabrica, promotor com faixa alternativa
    assert calcular_nps(scores) == pytest.approx(0.0)
    faixas = {"detrator": (0, 4), "neutro": (5, 7), "promotor": (8, 10)}
    assert calcular_nps(scores, faixas) == pytest.approx(100.0)


# --- serie temporal diaria --------------------------------------------------


def _conversa(identificador: str, inicio: datetime, esperas_s: list[int]):
    """Conversa com uma espera por par cliente->bot, para fixar a latencia."""
    mensagens = []
    instante = inicio
    for espera in esperas_s:
        mensagens.append(Mensagem(autor="cliente", texto="oi", enviada_em=instante))
        instante = instante + timedelta(seconds=espera)
        mensagens.append(Mensagem(autor="bot", texto="ola", enviada_em=instante))
        instante = instante + timedelta(seconds=1)
    return Conversa(
        id=identificador, canal="csv", iniciada_em=inicio, mensagens=mensagens
    )


def test_serie_agrupa_por_dia_e_ordena_do_mais_antigo():
    dia2 = BASE + timedelta(days=1)
    registros = [
        (_conversa("b", dia2, [10]), 95.0),
        (_conversa("a", BASE, [10]), 95.0),
    ]
    pontos = serie_diaria(registros)
    assert [p["dia"] for p in pontos] == ["2026-08-13", "2026-08-14"]


def test_nps_do_dia_usa_a_faixa_recebida():
    registros = [
        (_conversa("a", BASE, [10]), 95.0),   # nota 10 -> promotor
        (_conversa("b", BASE, [10]), 10.0),   # nota 1  -> detrator
        (_conversa("c", BASE, [10]), 75.0),   # nota 8  -> neutro
    ]
    (ponto,) = serie_diaria(registros)
    assert ponto["nps"] == pytest.approx(0.0)  # 1 promotor - 1 detrator em 3

    # Faixa que joga o neutro para promotor: o MESMO dado vira NPS +33.33.
    outras = {"detrator": (0, 6), "neutro": (7, 7), "promotor": (8, 10)}
    (ponto,) = serie_diaria(registros, outras)
    assert ponto["nps"] == pytest.approx(33.33)


def test_latencia_do_dia_e_mediana_das_medianas_nao_de_todas_as_esperas():
    """Um atendimento tagarela nao pode dominar o dia inteiro.

    `a` tem uma espera de 100s; `b` tem cinco de 10s. No balde unico a mediana
    seria 10s (as cinco de `b` afogam `a`). Por atendimento, as medianas sao
    100 e 10, e a mediana delas e 55.
    """
    registros = [
        (_conversa("a", BASE, [100]), 50.0),
        (_conversa("b", BASE, [10, 10, 10, 10, 10]), 50.0),
    ]
    (ponto,) = serie_diaria(registros)
    assert ponto["latencia_mediana_s"] == pytest.approx(55.0)


def test_dia_sem_score_devolve_nps_none_e_nao_zero():
    """Ausencia de medicao nao e NPS 0 -- isso seria inventar numero."""
    registros = [(_conversa("mudo", BASE, [10]), None)]
    (ponto,) = serie_diaria(registros)
    assert ponto["nps"] is None
    assert ponto["atendimentos"] == 1
    assert ponto["com_score"] == 0


def test_conversa_sem_resposta_nao_falsifica_latencia_zero():
    """Sem par cliente->resposta a latencia e None, nunca 0.0 (=instantaneo)."""
    muda = Conversa(
        id="so-bot", canal="csv", iniciada_em=BASE,
        mensagens=[Mensagem(autor="bot", texto="ola", enviada_em=BASE)],
    )
    (ponto,) = serie_diaria([(muda, None)])
    assert ponto["latencia_mediana_s"] is None
