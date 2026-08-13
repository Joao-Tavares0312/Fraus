from datetime import datetime, timedelta, timezone

from dolos.modelos import Conversa, Mensagem
from dolos.sinais.tempo import features_tempo

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


def _ts(segundos: float) -> datetime:
    return BASE + timedelta(seconds=segundos)


def _conversa(pares: list[tuple[str, float]], escalou: bool = False) -> Conversa:
    mensagens = [
        Mensagem(autor=autor, texto="x", enviada_em=_ts(segundos))
        for autor, segundos in pares
    ]
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=mensagens[0].enviada_em,
        encerrada_em=mensagens[-1].enviada_em,
        escalou_para_humano=escalou,
        mensagens=mensagens,
    )


def test_latencia_e_o_intervalo_ate_a_resposta_do_bot():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 8)]))
    assert features["latencia_primeira_resposta_s"] == 8.0
    assert features["latencia_mediana_s"] == 8.0


def test_mediana_com_varias_respostas():
    features = features_tempo(
        _conversa([("cliente", 0), ("bot", 10), ("cliente", 20), ("bot", 50)])
    )
    assert features["latencia_mediana_s"] == 20.0
    assert features["latencia_p90_s"] == 30.0
    assert features["latencia_primeira_resposta_s"] == 10.0
    assert features["qtd_turnos_cliente"] == 2.0


def test_turno_unico_sem_resposta_zera_latencia():
    features = features_tempo(_conversa([("cliente", 0)]))
    assert features["latencia_mediana_s"] == 0.0
    assert features["latencia_p90_s"] == 0.0
    assert features["latencia_primeira_resposta_s"] == 0.0


def test_conversa_aberta_usa_ultima_mensagem_como_fim():
    conversa = _conversa([("cliente", 0), ("bot", 30)])
    conversa.encerrada_em = None
    assert features_tempo(conversa)["duracao_total_s"] == 30.0


def test_mensagem_de_humano_tambem_conta_como_resposta():
    features = features_tempo(_conversa([("cliente", 0), ("humano", 12)], escalou=True))
    assert features["latencia_primeira_resposta_s"] == 12.0
    assert features["escalou"] == 1.0


def test_cliente_que_nao_responde_o_bot_conta_como_abandono():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 5)]))
    assert features["abandonou"] == 1.0


def test_cliente_que_responde_por_ultimo_nao_e_abandono():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 5), ("cliente", 9)]))
    assert features["abandonou"] == 0.0
