from datetime import datetime, timedelta, timezone

from fraus.fatias import fatias_de, metricas_por_fatia
from fraus.modelos import Conversa, Mensagem

T = datetime(2026, 8, 13, 10, tzinfo=timezone.utc)


def _conversa(*falas, espera=10, escalou=False):
    mensagens = []
    for i, texto in enumerate(falas):
        mensagens.append(Mensagem(autor="cliente", texto=texto, enviada_em=T + timedelta(seconds=i * 2 * espera)))
        mensagens.append(Mensagem(autor="bot", texto="certo", enviada_em=T + timedelta(seconds=i * 2 * espera + espera)))
    return Conversa(id="c", canal="csv", iniciada_em=T, mensagens=mensagens, escalou_para_humano=escalou)


def test_fatias_de_uma_conversa():
    fatias = fatias_de(_conversa("pessimo 😡", espera=300, escalou=True))
    assert fatias == {
        "falas do cliente": "1",
        "latencia mediana": ">180 s",
        "emoji": "com",
        "escalou para humano": "sim",
    }


def test_f1_macro_usa_so_as_classes_da_fatia():
    registros = [({"e": "a"}, 0, 0), ({"e": "a"}, 2, 2), ({"e": "b"}, 1, 0)]
    m = metricas_por_fatia(registros)
    assert m["e"]["a"] == {"n": 2, "acuracia": 1.0, "f1_macro": 1.0}
    assert m["e"]["b"]["acuracia"] == 0.0
