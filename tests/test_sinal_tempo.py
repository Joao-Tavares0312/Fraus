from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.tempo import features_tempo

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


def test_conversa_sem_resposta_nao_tem_latencia_em_vez_de_zero():
    # B01 da auditoria de 13/10/2026: 0,0 era a mesma codificacao de
    # "respondeu na hora", e a conversa ignorada pontuava alto.
    features = features_tempo(_conversa([("cliente", 0), ("cliente", 600)]))
    assert features["latencia_mediana_s"] is None
    assert features["latencia_p90_s"] is None
    assert features["latencia_primeira_resposta_s"] is None
    assert features["duracao_total_s"] == 600.0
    assert features["abandonou"] == 0.0


def test_resposta_instantanea_continua_sendo_zero_medido():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 0)]))
    assert features["latencia_mediana_s"] == 0.0


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


def test_demo_pontua_conversa_sem_resposta_sem_estourar():
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[1] / "scripts" / "api_demo.py"
    spec = importlib.util.spec_from_file_location("api_demo_teste", caminho)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    duble = next(v for v in vars(demo).values()
                 if isinstance(v, type) and hasattr(v, "pontuar_conversa") and v.__module__ == "api_demo_teste")
    score = duble.__new__(duble).pontuar_conversa(_conversa([("cliente", 0), ("cliente", 600)]))
    assert score is not None
