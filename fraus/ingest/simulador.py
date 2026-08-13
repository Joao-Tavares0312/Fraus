"""Simulador de conversas sinteticas.

Nenhum corpus publico de review PT-BR tem timestamps de dialogo, logo nenhum
deles treina o sinal de tempo. Este modulo costura frases rotuladas desses
corpora em dialogos cliente-bot, com latencias amostradas de distribuicoes
calibradas pelos benchmarks de live chat (pico de CSAT em 5-10s, queda acima
de 1min, abandono acima de 3min).

LIMITACAO METODOLOGICA, a declarar no relatorio: o sinal de tempo e treinado
em dados sinteticos calibrados por literatura, nao observados.
"""

import random
from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem

INICIO = datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)

# (latencia_min_s, latencia_max_s, prob_escalacao, prob_abandono)
PERFIL_POR_ROTULO = {
    0: (60.0, 400.0, 0.55, 0.40),
    1: (15.0, 60.0, 0.15, 0.15),
    2: (3.0, 15.0, 0.03, 0.05),
}

RESPOSTAS_BOT = [
    "Entendi, vou verificar isso para voce.",
    "Um momento, por favor.",
    "Consegui localizar seu pedido.",
    "Posso ajudar em algo mais?",
]


def gerar_conversa(rotulo: int, frases_cliente: list[str], semente: int) -> Conversa:
    """Gera uma conversa deterministica para a semente dada."""
    aleatorio = random.Random(semente)
    lat_min, lat_max, prob_escalacao, prob_abandono = PERFIL_POR_ROTULO[rotulo]

    qtd_turnos = aleatorio.randint(1, min(3, len(frases_cliente)))
    escalou = aleatorio.random() < prob_escalacao
    abandonou = aleatorio.random() < prob_abandono

    mensagens: list[Mensagem] = []
    relogio = INICIO + timedelta(minutes=aleatorio.randint(0, 60 * 24 * 20))
    inicio = relogio

    for turno in range(qtd_turnos):
        mensagens.append(
            Mensagem(
                autor="cliente",
                texto=aleatorio.choice(frases_cliente),
                enviada_em=relogio,
            )
        )
        relogio += timedelta(seconds=aleatorio.uniform(lat_min, lat_max))
        ultimo_turno = turno == qtd_turnos - 1
        mensagens.append(
            Mensagem(
                autor="humano" if escalou and ultimo_turno else "bot",
                texto=aleatorio.choice(RESPOSTAS_BOT),
                enviada_em=relogio,
            )
        )
        relogio += timedelta(seconds=aleatorio.uniform(2.0, 20.0))

    if not abandonou:
        mensagens.append(
            Mensagem(autor="cliente", texto=aleatorio.choice(frases_cliente), enviada_em=relogio)
        )

    return Conversa(
        id=f"sim-{rotulo}-{semente}",
        canal="simulado",
        iniciada_em=inicio,
        encerrada_em=mensagens[-1].enviada_em,
        escalou_para_humano=escalou,
        mensagens=mensagens,
    )


def gerar_lote(
    frases_por_rotulo: dict[int, list[str]], quantidade: int, semente: int
) -> list[tuple[Conversa, int]]:
    """Gera `quantidade` conversas com rotulos equilibrados entre as classes."""
    aleatorio = random.Random(semente)
    rotulos = sorted(frases_por_rotulo)
    sementes = aleatorio.sample(range(10**9), quantidade)
    lote = []
    for indice in range(quantidade):
        rotulo = rotulos[indice % len(rotulos)]
        lote.append(
            (
                gerar_conversa(rotulo, frases_por_rotulo[rotulo], semente=sementes[indice]),
                rotulo,
            )
        )
    return lote
