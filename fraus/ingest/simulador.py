"""Simulador de conversas sinteticas.

Nenhum corpus publico de review PT-BR tem timestamps de dialogo, logo nenhum
deles treina o sinal de tempo. Este modulo costura frases rotuladas desses
corpora em dialogos cliente-bot, com latencias amostradas de distribuicoes
calibradas pelos benchmarks de live chat (pico de CSAT em 5-10s, queda acima
de 1min, abandono acima de 3min).

LIMITACAO METODOLOGICA, a declarar no relatorio: o sinal de tempo e treinado
em dados sinteticos calibrados por literatura, nao observados.
"""

import math
import random
from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem

INICIO = datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)

# (latencia_mediana_s, dispersao, prob_escalacao, prob_abandono)
#
# A latencia e log-normal, nao uniforme entre um minimo e um maximo. A versao
# anterior sorteava de faixas DISJUNTAS (0: 60-400s, 1: 15-60s, 2: 3-15s) e
# isso vazava o gabarito: sabendo so a latencia dava para dizer o rotulo sem
# ler uma letra do texto. O fusor treinado nela chegou a 99,3% de acuracia no
# sintetico, aprendeu o relogio e ignorou o BERTimbau -- em conversa real
# pontuava ~50 para tudo.
#
# Com log-normal as medianas continuam ordenadas (atendimento ruim demora
# mais, como manda a literatura de live chat), mas as caudas se cruzam: existe
# atendimento rapido que termina mal e atendimento lento que termina bem. O
# tempo volta a ser sinal fraco, que e o que ele e de verdade.
# Sobreposicao medida: ~11% das satisfeitas ficam acima da mediana das
# insatisfeitas e vice-versa, com as medias ainda separadas por 4x.
PERFIL_POR_ROTULO = {
    0: (70.0, 1.2, 0.45, 0.30),
    1: (34.0, 1.2, 0.20, 0.15),
    2: (16.0, 1.2, 0.08, 0.07),
}

# Emojis por rotulo, com CRUZAMENTO deliberado: a ultima entrada de cada lista
# tem polaridade OPOSTA a do rotulo no lexicon. Cliente irritado manda 🙏
# (+0.418) ao implorar ajuda; cliente satisfeito manda 😩 (-0.368) quando o
# caso demorou mas terminou bem. Sem esse cruzamento o emoji viraria o novo
# gabarito, trocando um vazamento por outro.
#
# Todos os emojis daqui tem polaridade NAO NULA no Emoji Sentiment Ranking --
# ❤️ e 🥰, por exemplo, ficam de fora porque valem 0.0 no lexicon e nao
# moveriam a feature.
EMOJIS_POR_ROTULO = {
    0: ["😡", "😠", "😤", "👎", "😞", "😒", "🙏"],
    1: ["😐", "👍", "😕", "😅"],
    2: ["😍", "😊", "👏", "👍", "😩"],
}

# Fracao das falas do cliente que levam emoji. Nem toda mensagem tem: se todas
# tivessem, a ausencia de emoji viraria informacao por si so.
PROB_EMOJI = 0.45

# Marcas de estilo por rotulo, com o MESMO cruzamento deliberado dos emojis: a
# ultima entrada de cada lista pertence ao registro da classe OPOSTA. Cliente
# satisfeito tambem grita ("OBRIGADOOO"), cliente insatisfeito tambem escreve
# em minusculas e agradece.
#
# Sem esse cruzamento o palavrao viraria o novo gabarito e a regressao
# logistica leria a gritaria em vez do texto -- exatamente o que a latencia
# disjunta fez com o primeiro fusor.
#
# Cada entrada e (sufixo, transforma_em_caixa_alta).
ESTILO_POR_ROTULO = {
    0: [
        ("que MERDA de atendimento", True),
        ("ja e a QUARTA vez!!!", True),
        ("que p*rra e essa???", False),
        ("nao aguento maisss", False),
        ("voces sao uns incompetentes", False),
        ("por favor, poderia verificar?", False),
    ],
    1: [
        ("ok???", False),
        ("hmmmm", False),
        ("que droga, mas tudo bem", False),
        ("CERTO", True),
        ("entendi", False),
        ("c*ralho, demorou mas resolveu", False),
        ("o atendente foi meio incompetente, mas ok", False),
    ],
    2: [
        ("OBRIGADOOO", True),
        ("kkkk PERFEITO", True),
        ("que caralho de suporte bom", False),
        ("valeuuuu", False),
        ("muito bom!!!", False),
        ("obrigado", False),
        ("p*rra, ate que enfim, valeu", False),
        ("o outro atendente foi meio trouxa, mas voces resolveram", False),
    ],
}

# Fracao das falas do cliente que recebem marca de estilo. Como no emoji: se
# todas tivessem, a AUSENCIA de estilo viraria informacao por si so.
PROB_ESTILO = 0.40

RESPOSTAS_BOT = [
    "Entendi, vou verificar isso para voce.",
    "Um momento, por favor.",
    "Consegui localizar seu pedido.",
    "Posso ajudar em algo mais?",
]

# Frases rotuladas do cliente: 0 insatisfeito, 1 neutro, 2 satisfeito.
#
# Moram AQUI, e nao no script que as usa, porque passaram a ter dois
# consumidores: a demo (`scripts/api_demo.py`) e a medicao das faixas
# (`scripts/medir_faixas.py`). Duas copias de um corpus de referencia
# envelhecem separadas, e a que envelhece e sempre a que ninguem le -- so que
# aqui as duas produzem NUMERO, e dois numeros medidos em corpora que
# divergiram silenciosamente e a pior versao desse defeito.
#
# O neutro e o caso que da nome ao trabalho: "ok, obrigado 🙂" e uma despedida
# educada que nao declara satisfacao nenhuma.
#
# CRUZAMENTO de intensificador (`incongruencia_hiperbole`): a versao anterior
# tinha "muito obrigado", "rapidos demais" e "valeu mesmo" no rotulo 2 e ZERO
# intensificador colado a termo polar nos rotulos 0/1. Formalmente a guarda de
# disjuncao passava -- as tres faixas incluiam 0 -- mas na pratica
# `hiperbole > 0` so acontecia no rotulo 2: 45/60 conversas satisfeitas contra
# 0/60 nas outras duas classes, um previsor unilateral com 100% de certeza. O
# fusor aprenderia "hiperbole implica satisfeito", o INVERSO do que a feature
# existe para detectar -- elogio hiperbolico ("atendimento maravilhoso, so
# esperei 3 horas") e a forma classica da ironia, nao da satisfacao genuina.
# E a latencia disjunta do invariante 10 com outra roupa.
#
# "muito ruim" e tao natural em portugues quanto "muito bom": a ausencia era
# lacuna do corpus, nao fato da lingua. Removê-la de novo reintroduz o mesmo
# vazamento.
FRASES_POR_ROTULO: dict[int, list[str]] = {
    0: [
        "ja e a terceira vez que eu explico a mesma coisa e ninguem resolve 😡",
        "isso nao me ajudou em nada, quero falar com um atendente de verdade",
        "cancela minha assinatura, perdi a paciencia com esse atendimento",
        "voces cobraram duas vezes no meu cartao e ninguem me da retorno 😤",
        "pessimo, fiquei quase uma hora esperando por uma resposta automatica",
        "nao foi isso que eu perguntei, voce esta lendo o que eu escrevo?",
        "atendimento muito ruim, demorou demais e nao resolveu nada",
        "extremamente decepcionado, isso foi pessimo demais",
    ],
    1: [
        "ok, obrigado 🙂",
        "entendi, vou verificar aqui e retorno depois",
        "ta bom entao",
        "certo, e quanto tempo costuma demorar?",
        "so isso mesmo, valeu",
        "hmm, acho que da pra tentar assim",
        "demorou um pouco demais, mas tudo bem",
    ],
    2: [
        "perfeito, resolveu na hora, muito obrigado! 😄",
        "atendimento excelente, voces sao rapidos demais 👏",
        "era exatamente isso que eu precisava, gratidao ❤️",
        "otimo, ja consegui acompanhar meu pedido, valeu mesmo",
        "nossa, que rapidez, adorei o suporte de voces 😍",
        "resolvido! obrigado pela atencao e paciencia",
    ],
}


def _latencia(aleatorio: random.Random, mediana: float, dispersao: float) -> float:
    """Latencia log-normal em segundos, com piso de 1s e teto de 900s.

    A mediana da log-normal e exp(mu), entao mu vem do log da mediana pedida.
    O teto evita que a cauda longa gere conversa de horas, que o sinal de
    tempo trataria como abandono e nao como demora.
    """
    bruta = aleatorio.lognormvariate(math.log(mediana), dispersao)
    return max(1.0, min(900.0, bruta))


def _com_emoji(aleatorio: random.Random, texto: str, rotulo: int) -> str:
    """Anexa um emoji do perfil do rotulo, as vezes. Ver EMOJIS_POR_ROTULO."""
    if aleatorio.random() >= PROB_EMOJI:
        return texto
    return f"{texto} {aleatorio.choice(EMOJIS_POR_ROTULO[rotulo])}"


def _com_estilo(aleatorio: random.Random, texto: str, rotulo: int) -> str:
    """Anexa uma marca de estilo do perfil do rotulo, as vezes.

    Ver ESTILO_POR_ROTULO para o motivo do cruzamento entre classes.

    Efeito colateral registrado no sinal de emoji: em `gerar_conversa` esta
    funcao envolve `_com_emoji` (`_com_estilo(aleatorio, _com_emoji(...),
    rotulo)`), entao o sufixo de estilo vem DEPOIS do emoji sempre que os dois
    caem na mesma fala -- em ate PROB_ESTILO * PROB_EMOJI das falas o emoji
    deixa de ser o ultimo token. Isso muda `emoji_posicao_relativa_media`, que
    antes desta task era quase constante em ~1.0 (emoji quase sempre no fim) e
    agora varia de verdade. E MELHORA, nao regressao -- feature quase
    constante e o mesmo bug de peso zero que matou `emoji_score_medio` no
    primeiro fusor -- mas e uma mudanca de distribuicao em OUTRA feature que
    ninguem pediu, por isso o registro aqui. Nao inverta a ordem do
    aninhamento: ela e proposital.
    """
    if aleatorio.random() >= PROB_ESTILO:
        return texto
    sufixo, gritar = aleatorio.choice(ESTILO_POR_ROTULO[rotulo])
    return f"{texto} {sufixo.upper() if gritar else sufixo}"


def gerar_conversa(rotulo: int, frases_cliente: list[str], semente: int) -> Conversa:
    """Gera uma conversa deterministica para a semente dada."""
    aleatorio = random.Random(semente)
    mediana, dispersao, prob_escalacao, prob_abandono = PERFIL_POR_ROTULO[rotulo]

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
                texto=_com_estilo(
                    aleatorio,
                    _com_emoji(aleatorio, aleatorio.choice(frases_cliente), rotulo),
                    rotulo,
                ),
                enviada_em=relogio,
            )
        )
        relogio += timedelta(seconds=_latencia(aleatorio, mediana, dispersao))
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
            Mensagem(
                autor="cliente",
                texto=_com_estilo(
                    aleatorio,
                    _com_emoji(aleatorio, aleatorio.choice(frases_cliente), rotulo),
                    rotulo,
                ),
                enviada_em=relogio,
            )
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
