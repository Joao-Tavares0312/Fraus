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
