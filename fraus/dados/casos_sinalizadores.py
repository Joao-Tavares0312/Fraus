"""Casos construidos do E5: tres por regra (positivo, negativo e borda).

Sao escritos a mao e rotulados como CONSTRUIDOS: foram feitos para disparar (ou
nao) a regra, entao verificam a implementacao e NAO medem qualidade. O simulador
nao gera loop de bot, por isso a verificacao precisa destes casos. Nenhum texto
vem de cliente real. A lista segue a ordem de `REGRAS`, positivo primeiro.
"""

from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem

T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)


def _conv(*falas):
    """`falas` = pares (autor, texto); um minuto entre cada mensagem."""
    return Conversa(
        id="caso",
        canal="chat",
        iniciada_em=T0,
        mensagens=[
            Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k))
            for k, (a, t) in enumerate(falas)
        ],
    )


def _palavras(n, prefixo="p"):
    return " ".join(f"{prefixo}{k}" for k in range(n))


def _bots(n):
    return [("bot", f"resposta automatica numero {k}") for k in range(n)]


_RESPOSTA = "nao entendi sua pergunta, pode reformular por favor"
_PEDIDO = ("cliente", "quero falar com um atendente")
_HUMANO = ("cliente", "me passa para um humano")

CASOS = [
    # loop_do_bot
    ("loop_do_bot", "positivo", _conv(
        ("cliente", "meu pedido nao chegou"), ("bot", _RESPOSTA),
        ("cliente", "o pedido 123 nao chegou"), ("bot", _RESPOSTA + "!"),
        ("cliente", "ok")), True),
    ("loop_do_bot", "negativo", _conv(
        ("cliente", "meu pedido nao chegou"), ("bot", _RESPOSTA), ("bot", _RESPOSTA),
        ("cliente", "ok")), False),
    # Jaccard exato 0,85: 17 tokens em comum, uniao de 20.
    ("loop_do_bot", "borda", _conv(
        ("cliente", "oi"), ("bot", _palavras(17) + " xa xb"),
        ("cliente", "de novo"), ("bot", _palavras(17) + " xc"),
        ("cliente", "ok")), True),
    # cliente_repete
    ("cliente_repete", "positivo", _conv(
        ("cliente", "quero cancelar minha assinatura agora"),
        ("bot", "posso ajudar com outra coisa?"),
        ("cliente", "quero cancelar minha assinatura agora!!")), True),
    ("cliente_repete", "negativo", _conv(
        ("cliente", "quero cancelar minha assinatura agora"), ("bot", "certo"),
        ("cliente", "qual o prazo do reembolso no cartao")), False),
    # Jaccard exato 0,7: 7 em comum, uniao de 10.
    ("cliente_repete", "borda", _conv(
        ("cliente", _palavras(7) + " xa xb"), ("bot", "certo"),
        ("cliente", _palavras(7) + " xc")), True),
    # pedido_de_humano_ignorado
    ("pedido_de_humano_ignorado", "positivo", _conv(_PEDIDO, *_bots(3)), True),
    ("pedido_de_humano_ignorado", "negativo", _conv(
        _PEDIDO, *_bots(3), ("humano", "oi, sou a Ana")), False),
    ("pedido_de_humano_ignorado", "borda", _conv(_PEDIDO, *_bots(2)), False),
    # escalada_tardia
    ("escalada_tardia", "positivo", _conv(_HUMANO, *_bots(4), ("humano", "ola")), True),
    ("escalada_tardia", "negativo", _conv(
        ("cliente", "meu boleto venceu"), *_bots(5), ("humano", "ola")), False),
    ("escalada_tardia", "borda", _conv(_HUMANO, *_bots(3), ("humano", "ola")), False),
    # abandono
    ("abandono", "positivo", _conv(
        ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto")), True),
    ("abandono", "negativo", _conv(
        ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"),
        ("cliente", "valeu")), False),
    # humano por ultimo conta como respondente: dispara, e a evidencia aponta o cliente.
    ("abandono", "borda", _conv(
        ("cliente", "meu boleto venceu"), ("humano", "resolvido, ate logo")), True),
]
