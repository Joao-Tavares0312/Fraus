from datetime import datetime, timedelta, timezone

import pytest

from fraus.indicadores import (FAIXAS_NPS, calcular_csat, calcular_nps,
                               categoria_nps, containment_rate,
                               falso_containment, N_MINIMO_NPS,
                               nps_com_intervalo, nota_0_10,
                               serie_diaria, validar_faixas_nps)
from fraus.fusor import PESO_NEUTRO_NO_SCORE
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


# --- O neutro do modelo alcanca o neutro do NPS -------------------------------
#
# O score e uma projecao das tres probabilidades num eixo 0-100, e a categoria
# sai dele por faixa. Com peso 0.5 a classe neutra pousava em 50 -> nota 5 ->
# DETRATOR, e o NPS de um lote equilibrado saia negativo sem que o modelo
# tivesse errado nada (medido: -36,67 em 90 conversas do simulador).
#
# Estes testes fixam a composicao inteira -- peso, score, nota e categoria --
# porque cada elo dela ja quebrou ou e fragil, e nenhum deles avisa sozinho
# quando quebra: o NPS continua saindo um numero plausivel.


@pytest.mark.parametrize("classe,prob_satisfeito,prob_neutro,categoria", [
    ("insatisfeito", 0.0, 0.0, "detrator"),
    ("neutro", 0.0, 1.0, "neutro"),
    ("satisfeito", 1.0, 0.0, "promotor"),
])
def test_cada_classe_pura_cai_na_categoria_correspondente(
    classe, prob_satisfeito, prob_neutro, categoria
):
    """As tres classes do modelo -> as tres categorias do NPS, sem sobra.

    E o contrato que da sentido a categoria "neutro" existir: antes de
    PESO_NEUTRO_NO_SCORE = 0.75 ela era inalcancavel por predicao confiante --
    so um empate entre classes chegava la, e empate nao e neutralidade.
    """
    score = 100.0 * (prob_satisfeito + PESO_NEUTRO_NO_SCORE * prob_neutro)
    assert categoria_nps(score) == categoria, f"classe {classe} fora da sua categoria"


def test_neutro_puro_pontua_75_e_o_arredondamento_bancario_leva_para_oito():
    """A fronteira e FRAGIL de proposito explicito: 75 -> 7,5 -> 8.

    `round(7.5)` da 8 porque Python arredonda para o par mais proximo, e 8 e
    par. Nao ha margem: com peso 0.65 seria `round(6.5)` = 6 -- para BAIXO,
    de volta a detrator, pela mesma regra. O handoff registra que as fronteiras
    6/7 e 8/9 ja divergiram uma vez neste projeto por arredondamento, entao a
    escolha do peso fica presa aqui em vez de virar comentario.
    """
    score_do_neutro_puro = 100.0 * PESO_NEUTRO_NO_SCORE
    assert score_do_neutro_puro == 75.0
    assert nota_0_10(score_do_neutro_puro) == 8
    assert FAIXAS_NPS["neutro"] == (7, 8)


def test_lote_equilibrado_entre_as_classes_puras_da_nps_zero():
    """Um terco de cada classe se cancela: promotores - detratores = 0.

    E o criterio de aceite do conserto em miniatura. `scripts/medir_faixas.py`
    faz a mesma conta com o motor real em 90 conversas do simulador (mediu
    +0,00); aqui ela roda sem modelo nenhum, para a regressao aparecer em meio
    segundo de pytest e nao so em quem lembrar de rodar o script.
    """
    puros = [
        100.0 * (satisfeito + PESO_NEUTRO_NO_SCORE * neutro)
        for satisfeito, neutro in ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0))
    ]
    assert calcular_nps(puros) == 0.0


# --- falso containment ------------------------------------------------------


def _atendimento(indice: int, escalou: bool, score: float | None):
    conversa = Conversa(
        id=f"fc{indice}",
        canal="csv",
        iniciada_em=BASE,
        escalou_para_humano=escalou,
        mensagens=[Mensagem(autor="cliente", texto="ok", enviada_em=BASE)],
    )
    return (conversa, score)


def test_contido_e_detrator_conta_como_falso_containment():
    registros = [_atendimento(1, escalou=False, score=100.0),
                 _atendimento(2, escalou=False, score=20.0)]
    assert falso_containment(registros) == pytest.approx(50.0)


def test_contido_e_promotor_nao_conta():
    registros = [_atendimento(1, escalou=False, score=100.0)]
    assert falso_containment(registros) == pytest.approx(0.0)


def test_escalado_e_detrator_nao_conta_porque_nao_foi_contido():
    """O teste que pega a implementacao errada: escalar nao e conter.

    Quem conta detrator escalado esta medindo insatisfacao, nao falso
    sucesso -- e o indicador perde justamente o que o torna interessante.
    """
    registros = [_atendimento(1, escalou=True, score=20.0),
                 _atendimento(2, escalou=False, score=100.0)]
    assert falso_containment(registros) == pytest.approx(0.0)


def test_contido_sem_score_fica_fora_do_numerador_e_do_denominador():
    registros = [_atendimento(1, escalou=False, score=None),
                 _atendimento(2, escalou=False, score=20.0)]
    assert falso_containment(registros) == pytest.approx(100.0)


def test_nenhum_contido_com_score_e_ausencia_nao_zero():
    """0.0 se leria como "nenhum contido saiu insatisfeito" -- ninguem mediu."""
    assert falso_containment([]) is None
    assert falso_containment([_atendimento(1, escalou=False, score=None)]) is None
    assert falso_containment([_atendimento(2, escalou=True, score=20.0)]) is None


def test_falso_containment_usa_o_limiar_das_faixas_recebidas():
    """Invariante 4: o limiar de detrator vem das faixas, nunca digitado."""
    registros = [_atendimento(1, escalou=False, score=50.0)]  # nota 5
    assert falso_containment(registros) == pytest.approx(100.0)  # 5 e detrator de fabrica
    faixas = {"detrator": (0, 4), "neutro": (5, 7), "promotor": (8, 10)}
    assert falso_containment(registros, faixas) == pytest.approx(0.0)  # 5 vira neutro


# --- intervalo de confianca do NPS -----------------------------------------


def test_nps_com_intervalo_devolve_o_ponto_e_as_duas_pontas():
    """Com amostra suficiente, o ponto estimado bate com `calcular_nps`."""
    scores = [100.0] * 20 + [75.0] * 10 + [30.0] * 10
    saida = nps_com_intervalo(scores)
    assert saida["n"] == 40
    assert saida["nps"] == pytest.approx(calcular_nps(scores))
    assert saida["ic_inferior"] < saida["nps"] < saida["ic_superior"]


def test_o_intervalo_encolhe_conforme_a_amostra_cresce():
    """A propriedade que faz o indicador valer: mais dado, menos incerteza."""
    pequena = nps_com_intervalo([100.0] * 20 + [30.0] * 20)
    grande = nps_com_intervalo([100.0] * 200 + [30.0] * 200)
    assert pequena["nps"] == pytest.approx(grande["nps"])
    largura = lambda s: s["ic_superior"] - s["ic_inferior"]
    assert largura(grande) < largura(pequena)


def test_amostra_pequena_nao_mostra_ponto_estimado_mas_diz_quanto_tem():
    """n < 30: o ponto sugeriria precisao que nao existe.

    O `n` continua preenchido de proposito -- a tela precisa dizer QUANTO
    falta, nao so que nao sabe.
    """
    saida = nps_com_intervalo([100.0] * 8)
    assert saida["n"] == 8
    assert saida["nps"] is None


def test_sem_score_nenhum_nao_ha_intervalo_nenhum():
    assert nps_com_intervalo([]) is None


def test_o_intervalo_e_recortado_na_escala_do_nps():
    """NPS vive em [-100, 100]: ponta fora da escala seria numero impossivel."""
    saida = nps_com_intervalo([100.0] * 40)
    assert saida["nps"] == pytest.approx(100.0)
    assert saida["ic_superior"] == pytest.approx(100.0)
    assert saida["ic_inferior"] <= 100.0


def test_o_intervalo_usa_as_faixas_recebidas():
    scores = [80.0] * 40  # nota 8: neutro de fabrica, promotor com faixa alternativa
    assert nps_com_intervalo(scores)["nps"] == pytest.approx(0.0)
    faixas = {"detrator": (0, 4), "neutro": (5, 7), "promotor": (8, 10)}
    assert nps_com_intervalo(scores, faixas)["nps"] == pytest.approx(100.0)


def test_containment_de_conjunto_vazio_e_ausencia_nao_zero():
    """Nenhuma conversa nao e "0% de contencao" -- e nao houve o que conter.

    Era a UNICA funcao deste modulo que devolvia zero em colecao vazia. O
    `?? 0` proibido no front tambem mora no Python, na forma de `return 0.0`
    em early-return -- e ele e mais dificil de ver ali, porque parece
    inicializacao em vez de afirmacao.
    """
    assert containment_rate([]) is None
