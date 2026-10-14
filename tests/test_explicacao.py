from fraus.explicacao import AVISO, LIMIAR_PONTOS, explicar, formatar_duracao
from fraus.fusor import FAMILIAS


def _efeitos(**v):
    base = dict.fromkeys(FAMILIAS, 0.0)
    base.update(v)
    return base


FEATURES = {"latencia_mediana_s": 720.0, "latencia_primeira_resposta_s": 95.0}


def test_formatar_duracao():
    assert formatar_duracao(42) == "42 s"
    assert formatar_duracao(720) == "12 min"
    assert formatar_duracao(10800) == "3 h"
    assert formatar_duracao(5430) == "1 h 30 min"


def test_contra_e_a_favor_com_detalhe_de_tempo():
    r = explicar(_efeitos(tempo=-23.4, texto=31.0, emoji=2.0), FEATURES, ha_latencia=True)
    assert r["frases"][0] == (
        "Pesou contra: o ritmo do atendimento (espera mediana de 12 min; "
        "primeira resposta em 2 min), −23,4 pontos.")
    assert r["frases"][1] == "Pesou a favor: o texto do cliente, +31,0 pontos; os emojis, +2,0 pontos."
    assert r["aviso"] == AVISO


def test_no_maximo_dois_por_lado_em_ordem_de_magnitude():
    r = explicar(_efeitos(texto=-5, emoji=-9, estilo=-2, lexico=-30), FEATURES, ha_latencia=True)
    assert [i["familia"] for i in r["contra"]] == ["lexico", "emoji"]


def test_abaixo_do_limiar_nao_entra():
    r = explicar(_efeitos(texto=LIMIAR_PONTOS - 0.01), FEATURES, ha_latencia=True)
    assert r["contra"] == [] and r["a_favor"] == []
    assert r["frases"] == ["Nenhum sinal sozinho moveu a nota em 1 ponto ou mais."]


def test_sem_par_cliente_resposta_nao_inventa_espera():
    r = explicar(_efeitos(tempo=-8.0), {"latencia_mediana_s": 0.0,
                                        "latencia_primeira_resposta_s": 0.0}, ha_latencia=False)
    assert r["contra"][0]["detalhe"] is None
    assert "0 s" not in r["frases"][0]


def test_aviso_declara_associacao_tempo_sintetico_e_nao_aditividade():
    for trecho in ("não causa", "sintéticos", "não somam"):
        assert trecho in AVISO
