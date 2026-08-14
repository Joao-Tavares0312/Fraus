"""Testes da ficha operacional da conversa.

O que se protege aqui e, quase todo, a diferenca entre AUSENCIA e ZERO. Numa
coluna de tempo de resposta, `0.0` se le como "respondeu na hora" -- e a
conversa que nunca teve resposta humana nenhuma acabaria exibida como a mais
agil da operacao.
"""

from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.resumo import desfecho, latencias_por_respondente, resumir

INICIO = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


def _conversa(falas, encerrada_em=None, escalou=False, ident="c1"):
    """Monta conversa a partir de (autor, segundos_desde_o_inicio)."""
    return Conversa(
        id=ident,
        canal="webchat",
        iniciada_em=INICIO,
        encerrada_em=encerrada_em,
        escalou_para_humano=escalou,
        mensagens=[
            Mensagem(autor=autor, texto=f"fala de {autor}", enviada_em=INICIO + timedelta(seconds=s))
            for autor, s in falas
        ],
    )


def test_separa_o_tempo_do_bot_do_tempo_do_humano():
    """A media unica apaga as duas historias; e por isso que elas vem separadas."""
    conversa = _conversa([
        ("cliente", 0),
        ("bot", 2),        # bot responde em 2s
        ("cliente", 10),
        ("humano", 250),   # humano responde em 240s
    ])

    por_autor = latencias_por_respondente(conversa)
    assert por_autor["bot"] == [2.0]
    assert por_autor["humano"] == [240.0]

    ficha = resumir(conversa)
    assert ficha["latencia_mediana_bot_s"] == 2.0
    assert ficha["latencia_mediana_humano_s"] == 240.0
    # A mediana geral fica entre as duas e nao descreve nenhuma delas -- e
    # exatamente o motivo de as duas colunas existirem.
    assert ficha["latencia_mediana_s"] == 121.0


def test_sem_atendente_humano_a_latencia_humana_e_nula_e_nao_zero():
    """Zero na coluna de tempo se le como instantaneo. A conversa nem teve humano."""
    conversa = _conversa([("cliente", 0), ("bot", 5)])

    ficha = resumir(conversa)
    assert ficha["latencia_mediana_humano_s"] is None
    assert ficha["latencia_mediana_bot_s"] == 5.0


def test_conversa_sem_fala_do_cliente_nao_inventa_tempo_de_espera():
    """Sem cliente nao ha espera de cliente: os tres tempos saem nulos."""
    conversa = _conversa([("bot", 0), ("bot", 30)])

    ficha = resumir(conversa)
    assert ficha["latencia_primeira_resposta_s"] is None
    assert ficha["latencia_mediana_s"] is None
    assert ficha["latencia_mediana_bot_s"] is None
    assert ficha["desfecho"] == "sem_sinal"


def test_conta_mensagens_por_autor():
    conversa = _conversa([
        ("cliente", 0), ("bot", 1), ("cliente", 5), ("humano", 9), ("cliente", 20),
    ])

    ficha = resumir(conversa)
    assert ficha["qtd_mensagens"] == 5
    assert ficha["qtd_cliente"] == 3
    assert ficha["qtd_bot"] == 1
    assert ficha["qtd_humano"] == 1


# ---------------------------------------------------------------------------
# desfecho -- a ordem de precedencia E a definicao, entao cada degrau tem teste


def test_sem_sinal_vence_todo_o_resto():
    """Cliente que nao falou e a informacao mais importante da conversa."""
    conversa = _conversa(
        [("bot", 0)], encerrada_em=INICIO + timedelta(minutes=5), escalou=True
    )
    assert desfecho(conversa) == "sem_sinal"


def test_escalada_vence_encerrada():
    """Escalada que terminou bem continua sendo escalada -- e o custo a medir."""
    conversa = _conversa(
        [("cliente", 0), ("humano", 60)],
        encerrada_em=INICIO + timedelta(minutes=5),
        escalou=True,
    )
    assert desfecho(conversa) == "escalada"


def test_ultima_fala_do_cliente_sem_resposta():
    """O desfecho mais grave que da para provar so com o dado."""
    conversa = _conversa([("cliente", 0), ("bot", 3), ("cliente", 40)])
    assert desfecho(conversa) == "sem_resposta"


def test_encerrada_quando_fechou_com_o_respondente_por_ultimo():
    conversa = _conversa(
        [("cliente", 0), ("bot", 3)], encerrada_em=INICIO + timedelta(minutes=2)
    )
    assert desfecho(conversa) == "encerrada"


def test_em_aberto_sem_encerrada_em():
    conversa = _conversa([("cliente", 0), ("bot", 3)])
    assert desfecho(conversa) == "em_aberto"


def test_nao_existe_desfecho_de_resolucao():
    """Resolucao e julgamento sobre o problema do cliente, e nada no dado a sustenta.

    Este teste existe para travar a tentacao de acrescentar "resolvida" mais
    tarde: o conjunto de desfechos e fechado, e cada um deles e verificavel.
    """
    variacoes = [
        _conversa([("bot", 0)]),
        _conversa([("cliente", 0), ("humano", 9)], escalou=True),
        _conversa([("cliente", 0), ("bot", 3), ("cliente", 40)]),
        _conversa([("cliente", 0), ("bot", 3)], encerrada_em=INICIO + timedelta(minutes=2)),
        _conversa([("cliente", 0), ("bot", 3)]),
    ]
    possiveis = {"sem_sinal", "escalada", "sem_resposta", "encerrada", "em_aberto"}
    assert {desfecho(c) for c in variacoes} == possiveis
