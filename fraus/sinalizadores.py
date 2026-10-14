"""Sinalizadores por regra: conversas de risco destacadas sem modelo e sem LLM.

Cinco regras de superficie sobre falas do cliente, falas do bot, contagens e
posicao. DERIVADAS NA LEITURA, como a contestacao: nada e gravado, e a marca
vale retroativamente para o que ja esta no banco. Marca e informa, nao
corrige -- score, nota e categoria ficam intactos.

O LIMITE DE CONFORMIDADE E DURO: nenhuma regra le o texto ou o relogio de uma
fala `humano`. Da fala humana so contam a PRESENCA e a POSICAO, e ela nunca
entra na `evidencia` -- a tela nao destaca a fala do atendente. Medir o
humano seria pontua-lo (docs/conformidade.md).

Conversa sem fala do cliente devolve `None`, nao `[]`: "nao avaliado" e
diferente de "nada disparou" (invariante 2).

Os limiares sao SEM PROCEDENCIA (como o 95 da contestacao) e o `detalhe` de
cada achado diz isso. Spec: docs/superpowers/specs/2026-10-14-e5-sinalizadores-design.md
"""

from itertools import combinations

from fraus.cortesia import normalizar_fala
from fraus.modelos import Conversa
from fraus.sinais.tempo import features_tempo

REGRAS = (
    "loop_do_bot",
    "cliente_repete",
    "pedido_de_humano_ignorado",
    "escalada_tardia",
    "abandono",
)

LIMIAR_LOOP_BOT = 0.85
MIN_TOKENS_BOT = 3
LIMIAR_CLIENTE_REPETE = 0.7
MIN_TOKENS_CLIENTE = 4
MAX_RESPOSTAS_SEM_HUMANO = 2
N_ESCALADA_TARDIA = 3

# Fechado de proposito: e uma limitacao declarada, nao um esquecimento.
PEDIDOS_DE_HUMANO = ("atendente", "humano", "humana", "pessoa", "operador", "falar com alguem")


def _tokens(texto: str) -> frozenset[str]:
    return frozenset(normalizar_fala(texto).split())


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    uniao = a | b
    return len(a & b) / len(uniao) if uniao else 0.0


def _pede_humano(texto: str) -> bool:
    fala = f" {normalizar_fala(texto)} "
    return any(f" {termo} " in fala for termo in PEDIDOS_DE_HUMANO)


def _achado(regra: str, evidencia, detalhe: str) -> dict:
    return {"regra": regra, "evidencia": sorted(set(evidencia)), "detalhe": detalhe}


def _loop_do_bot(conversa: Conversa) -> dict | None:
    msgs = conversa.mensagens
    bots = [(i, _tokens(m.texto)) for i, m in enumerate(msgs) if m.autor == "bot"]
    bots = [(i, t) for i, t in bots if len(t) >= MIN_TOKENS_BOT]
    # pref[k] = falas do cliente em msgs[:k]; evita varrer o intervalo por par.
    pref = [0]
    for m in msgs:
        pref.append(pref[-1] + (m.autor == "cliente"))
    evidencia: set[int] = set()
    for (i, a), (j, b) in combinations(bots, 2):
        cliente_entre = pref[j] > pref[i + 1]
        if cliente_entre and jaccard(a, b) >= LIMIAR_LOOP_BOT:
            evidencia |= {i, j}
    if not evidencia:
        return None
    return _achado(
        "loop_do_bot", evidencia,
        f"{len(evidencia)} respostas do bot quase idênticas, com fala do cliente "
        "entre elas (Jaccard ≥ 0,85; limiar sem procedência)",
    )


def _cliente_repete(conversa: Conversa) -> dict | None:
    falas = [(i, _tokens(m.texto)) for i, m in enumerate(conversa.mensagens)
             if m.autor == "cliente"]
    falas = [(i, t) for i, t in falas if len(t) >= MIN_TOKENS_CLIENTE]
    evidencia: set[int] = set()
    for (i, a), (j, b) in combinations(falas, 2):
        if jaccard(a, b) >= LIMIAR_CLIENTE_REPETE:
            evidencia |= {i, j}
    if not evidencia:
        return None
    return _achado(
        "cliente_repete", evidencia,
        f"o cliente repetiu {len(evidencia)} falas quase iguais (Jaccard ≥ 0,7, "
        "mínimo de 4 palavras; limiar sem procedência)",
    )


def _primeiro_pedido(conversa: Conversa) -> int | None:
    return next((i for i, m in enumerate(conversa.mensagens)
                 if m.autor == "cliente" and _pede_humano(m.texto)), None)


def _primeiro_humano_depois(conversa: Conversa, inicio: int) -> int | None:
    # So a POSICAO da fala humana. Texto e relogio dela nunca sao lidos.
    return next((i for i in range(inicio + 1, len(conversa.mensagens))
                 if conversa.mensagens[i].autor == "humano"), None)


def _bots_entre(conversa: Conversa, inicio: int, fim: int) -> list[int]:
    return [i for i in range(inicio + 1, fim) if conversa.mensagens[i].autor == "bot"]


def _pedido_ignorado(conversa: Conversa) -> dict | None:
    pedido = _primeiro_pedido(conversa)
    if pedido is None or _primeiro_humano_depois(conversa, pedido) is not None:
        return None
    bots = _bots_entre(conversa, pedido, len(conversa.mensagens))
    if len(bots) <= MAX_RESPOSTAS_SEM_HUMANO:
        return None
    return _achado(
        "pedido_de_humano_ignorado", [pedido, *bots],
        f"o cliente pediu atendimento humano e o bot respondeu {len(bots)} vezes "
        "sem um humano responder depois do pedido (mais de 2; limiar sem procedência)",
    )


def _escalada_tardia(conversa: Conversa) -> dict | None:
    pedido = _primeiro_pedido(conversa)
    if pedido is None:
        return None
    humano = _primeiro_humano_depois(conversa, pedido)
    if humano is None:
        return None
    bots = _bots_entre(conversa, pedido, humano)
    if len(bots) <= N_ESCALADA_TARDIA:
        return None
    return _achado(
        "escalada_tardia", [pedido, *bots],
        f"o humano entrou depois de {len(bots)} respostas do bot ao pedido "
        "(mais de 3; limiar sem procedência). Conta falas do bot, nunca o tempo do humano",
    )


def _abandono(conversa: Conversa) -> dict | None:
    if features_tempo(conversa)["abandonou"] != 1.0:
        return None
    # A evidencia e a ultima fala do CLIENTE, nunca a ultima mensagem: ela
    # pode ser do humano, e a fala humana nao entra em evidencia.
    ultima_do_cliente = max(i for i, m in enumerate(conversa.mensagens) if m.autor == "cliente")
    return _achado(
        "abandono", [ultima_do_cliente],
        "a última fala é de quem responde e o cliente não voltou depois desta mensagem",
    )


_DETECTORES = (_loop_do_bot, _cliente_repete, _pedido_ignorado, _escalada_tardia, _abandono)


def sinalizadores(conversa: Conversa) -> list[dict] | None:
    """Achados na ordem de `REGRAS`; `None` quando nao ha fala do cliente."""
    if not conversa.tem_fala_cliente:
        return None
    return [a for a in (detector(conversa) for detector in _DETECTORES) if a is not None]
