from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.emoji import features_emoji, score_do_emoji


def _conversa(textos: list[str]) -> Conversa:
    base = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="cliente", texto=t, enviada_em=base) for t in textos
        ],
    )


def test_emoji_positivo_tem_score_positivo():
    assert score_do_emoji("\N{HEAVY BLACK HEART}") > 0


def test_emoji_negativo_tem_score_negativo():
    assert score_do_emoji("\N{ANGRY FACE}") < 0


def test_emoji_desconhecido_tem_score_zero():
    # U+1FAE0 MELTING FACE nao esta no lexicon
    assert score_do_emoji("\U0001fae0") == 0.0


def test_texto_sem_emoji_zera_as_features():
    features = features_emoji(_conversa(["obrigado pelo atendimento"]))
    assert features["emoji_contagem"] == 0
    assert features["emoji_score_medio"] == 0.0
    assert features["emoji_posicao_relativa_media"] == 0.0


def test_conta_apenas_emoji_do_cliente():
    base = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="bot", texto="\N{HEAVY BLACK HEART}" * 5, enviada_em=base),
            Mensagem(autor="cliente", texto="ok", enviada_em=base),
        ],
    )
    assert features_emoji(conversa)["emoji_contagem"] == 0


def test_emoji_no_fim_tem_posicao_relativa_alta():
    features = features_emoji(_conversa(["muito obrigado \N{HEAVY BLACK HEART}"]))
    assert features["emoji_posicao_relativa_media"] > 0.9


def test_emoji_no_inicio_tem_posicao_relativa_baixa():
    features = features_emoji(_conversa(["\N{HEAVY BLACK HEART} muito obrigado"]))
    assert features["emoji_posicao_relativa_media"] < 0.1


def test_fracoes_somam_no_maximo_um():
    features = features_emoji(
        _conversa(["\N{HEAVY BLACK HEART}\N{ANGRY FACE}"])
    )
    assert features["emoji_frac_positivos"] + features["emoji_frac_negativos"] <= 1.0
    assert features["emoji_contagem"] == 2


# --- A CURADORIA -----------------------------------------------------------
# O Emoji Sentiment Ranking anotou 751 emojis em 2015: tudo que o Unicode
# acrescentou depois vale 0 aqui, e e esse buraco que o analista preenche.

from fraus.sinais.curadoria import Curadoria  # noqa: E402


def test_emoji_curado_vence_o_ranking():
    assert score_do_emoji("\N{GRINNING FACE}") > 0
    c = Curadoria(emojis={"\N{GRINNING FACE}": -0.9})
    assert score_do_emoji("\N{GRINNING FACE}", c) == -0.9


def test_emoji_fora_do_ranking_e_nao_curado_continua_zero():
    assert score_do_emoji("\N{MELTING FACE}") == 0.0
    assert score_do_emoji("\N{MELTING FACE}", Curadoria()) == 0.0


def test_emoji_curado_preenche_o_que_o_ranking_de_2015_nao_tem():
    c = Curadoria(emojis={"\N{MELTING FACE}": -0.7})
    assert score_do_emoji("\N{MELTING FACE}", c) == -0.7


def test_curadoria_de_emoji_move_as_features():
    c = Curadoria(emojis={"\N{MELTING FACE}": -0.8})
    conversa = _conversa(["acabou assim \N{MELTING FACE}"])
    sem = features_emoji(conversa)
    com = features_emoji(conversa, c)
    assert sem["emoji_score_medio"] == 0.0
    assert com["emoji_score_medio"] == -0.8
    assert com["emoji_frac_negativos"] == 1.0


def test_sem_curadoria_o_comportamento_e_o_de_antes():
    conversa = _conversa(["tudo certo \N{GRINNING FACE}"])
    assert features_emoji(conversa) == features_emoji(conversa, None)
