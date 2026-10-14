"""Sinalizadores: positivo, negativo e borda por regra, e as duas guardas do spec.

As guardas que mais importam nao sao as das regras: sao `None` != `[]` (conversa
sem fala do cliente nao foi avaliada) e a de Conformidade (nenhuma regra le o
texto ou o relogio da fala humana).
"""

from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinalizadores import REGRAS, jaccard, sinalizadores

T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)


def conv(*falas, cid="c"):
    """`falas` = pares (autor, texto); um minuto entre cada mensagem."""
    return Conversa(
        id=cid,
        canal="chat",
        iniciada_em=T0,
        mensagens=[
            Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k))
            for k, (a, t) in enumerate(falas)
        ],
    )


def regras(c):
    return [s["regra"] for s in sinalizadores(c)]


def achado(c, regra):
    return next(s for s in sinalizadores(c) if s["regra"] == regra)


def palavras(n, prefixo="p"):
    return " ".join(f"{prefixo}{k}" for k in range(n))


# ---- contrato -------------------------------------------------------------

def test_sem_fala_do_cliente_e_none_e_nao_lista_vazia():
    assert sinalizadores(conv(("bot", "ola, posso ajudar?"))) is None


def test_conversa_comum_avaliada_devolve_lista_vazia():
    c = conv(("cliente", "quero a segunda via do boleto"),
             ("bot", "claro, enviei a segunda via no seu email"),
             ("cliente", "recebi, obrigado"))
    assert sinalizadores(c) == []


def test_regras_tem_ordem_fixa():
    assert REGRAS == ("loop_do_bot", "cliente_repete", "pedido_de_humano_ignorado",
                      "escalada_tardia", "abandono")


def test_jaccard_de_vazios_e_zero():
    assert jaccard(frozenset(), frozenset()) == 0.0


# ---- loop_do_bot ----------------------------------------------------------

RESPOSTA = "nao entendi sua pergunta, pode reformular por favor"


def test_loop_do_bot_positivo():
    c = conv(("cliente", "meu pedido nao chegou"), ("bot", RESPOSTA),
             ("cliente", "o pedido 123 nao chegou"), ("bot", RESPOSTA + "!"),
             ("cliente", "ok"))
    s = achado(c, "loop_do_bot")
    assert s["evidencia"] == [1, 3]
    assert "0,85" in s["detalhe"] and "sem procedência" in s["detalhe"]


def test_loop_do_bot_negativo_sem_cliente_entre_as_respostas():
    c = conv(("cliente", "meu pedido nao chegou"), ("bot", RESPOSTA), ("bot", RESPOSTA),
             ("cliente", "ok"))
    assert "loop_do_bot" not in regras(c)


def test_loop_do_bot_borda_exatamente_no_limiar_dispara():
    # 17 tokens em comum, uniao de 20: Jaccard = 0,85 exato.
    a = palavras(17) + " xa xb"
    b = palavras(17) + " xc"
    c = conv(("cliente", "oi"), ("bot", a), ("cliente", "de novo"), ("bot", b), ("cliente", "ok"))
    assert "loop_do_bot" in regras(c)


def test_loop_do_bot_borda_um_fio_abaixo_nao_dispara():
    # 17 em comum, uniao de 21: 0,8095.
    a = palavras(17) + " xa xb"
    b = palavras(17) + " xc xd"
    c = conv(("cliente", "oi"), ("bot", a), ("cliente", "de novo"), ("bot", b), ("cliente", "ok"))
    assert "loop_do_bot" not in regras(c)


def test_loop_do_bot_resposta_curta_nao_dispara():
    c = conv(("cliente", "oi"), ("bot", "Ok."), ("cliente", "e ai"), ("bot", "Ok."), ("cliente", "?"))
    assert "loop_do_bot" not in regras(c)


def test_so_pontuacao_nao_dispara_nada_por_similaridade():
    c = conv(("cliente", "???"), ("bot", "..."), ("cliente", "???"), ("bot", "..."),
             ("cliente", "???"))
    assert {"loop_do_bot", "cliente_repete"}.isdisjoint(regras(c))


# ---- cliente_repete -------------------------------------------------------

def test_cliente_repete_positivo():
    c = conv(("cliente", "quero cancelar minha assinatura agora"), ("bot", "posso ajudar com outra coisa?"),
             ("cliente", "quero cancelar minha assinatura agora!!"))
    assert achado(c, "cliente_repete")["evidencia"] == [0, 2]


def test_cliente_repete_negativo_falas_diferentes():
    c = conv(("cliente", "quero cancelar minha assinatura agora"), ("bot", "certo"),
             ("cliente", "qual o prazo do reembolso no cartao"))
    assert "cliente_repete" not in regras(c)


def test_cliente_repete_borda_tres_tokens_nao_conta():
    c = conv(("cliente", "nao funcionou ainda"), ("bot", "tente de novo"),
             ("cliente", "nao funcionou ainda"))
    assert "cliente_repete" not in regras(c)


def test_cliente_repete_borda_exatamente_07_dispara():
    # 7 em comum, uniao de 10.
    a = palavras(7) + " xa xb"
    b = palavras(7) + " xc"
    c = conv(("cliente", a), ("bot", "certo"), ("cliente", b))
    assert "cliente_repete" in regras(c)


# ---- pedido_de_humano_ignorado / escalada_tardia ----------------------------

def _bots(n):
    return [("bot", f"resposta automatica numero {k}") for k in range(n)]


def test_pedido_ignorado_positivo():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(3))
    s = achado(c, "pedido_de_humano_ignorado")
    assert s["evidencia"] == [0, 1, 2, 3]
    assert "sem procedência" in s["detalhe"]


def test_pedido_ignorado_borda_duas_respostas_nao_dispara():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(2))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_pedido_ignorado_negativo_humano_entrou():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(3), ("humano", "oi, sou a Ana"))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_palavra_que_contem_o_termo_nao_e_pedido():
    c = conv(("cliente", "o robo humanoide do anuncio e pessoal?"), *_bots(3))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_pedido_com_acento_e_maiuscula_conta():
    c = conv(("cliente", "Quero FALAR COM ALGUÉM, por favor"), *_bots(3))
    assert "pedido_de_humano_ignorado" in regras(c)


def test_escalada_tardia_positivo_e_humano_fora_da_evidencia():
    c = conv(("cliente", "me passa para um humano"), *_bots(4), ("humano", "ola"))
    s = achado(c, "escalada_tardia")
    assert s["evidencia"] == [0, 1, 2, 3, 4]
    assert 5 not in s["evidencia"]
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_escalada_tardia_borda_tres_respostas_nao_dispara():
    c = conv(("cliente", "me passa para um humano"), *_bots(3), ("humano", "ola"))
    assert "escalada_tardia" not in regras(c)


def test_escalada_sem_pedido_nao_dispara():
    c = conv(("cliente", "meu boleto venceu"), *_bots(5), ("humano", "ola"))
    assert "escalada_tardia" not in regras(c)


# ---- abandono ---------------------------------------------------------------

def test_abandono_positivo_ultima_fala_do_bot():
    c = conv(("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"))
    assert achado(c, "abandono")["evidencia"] == [0]  # a ultima fala do CLIENTE


def test_abandono_com_humano_por_ultimo_nao_aponta_o_humano():
    c = conv(("cliente", "meu boleto venceu"), ("humano", "resolvido, ate logo"))
    assert achado(c, "abandono")["evidencia"] == [0]


def test_abandono_negativo_cliente_fecha():
    c = conv(("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"), ("cliente", "valeu"))
    assert "abandono" not in regras(c)


# ---- Conformidade -------------------------------------------------------------

def test_texto_e_relogio_da_fala_humana_nao_mudam_nada():
    """O Fraus nao pontua atendente. So presenca e posicao da fala humana contam."""
    base = [("cliente", "me passa para um humano"), *_bots(4), ("humano", "ola, sou a Ana"),
            ("cliente", "me passa para um humano"), ("humano", "resolvido")]
    original = conv(*base)
    alterada = original.model_copy(deep=True)
    for k, m in enumerate(alterada.mensagens):
        if m.autor == "humano":
            alterada.mensagens[k] = Mensagem(
                autor="humano", texto="!!! qualquer coisa ofensiva e longa !!!",
                enviada_em=T0 + timedelta(days=3, seconds=k),
            )
    assert {s["regra"] for s in sinalizadores(original)} >= {"escalada_tardia", "abandono"}
    assert sinalizadores(alterada) == sinalizadores(original)


def test_loop_do_bot_nao_e_cubico_em_conversa_longa():
    import time

    falas = [("cliente", "preciso de ajuda")] + [
        ("bot", f"resposta automatica numero {k}") for k in range(1000)
    ]
    c = conv(*falas)
    t0 = time.perf_counter()
    sinalizadores(c)
    assert time.perf_counter() - t0 < 2.0


def test_pedido_ignorado_com_humano_antes_do_pedido_dispara_e_diz_depois_do_pedido():
    c = conv(
        ("cliente", "oi, tudo bem com voce hoje"), ("humano", "ola"),
        ("cliente", "quero falar com um atendente"),
        ("bot", "um momento"), ("bot", "entendi"), ("bot", "ainda aqui"),
    )
    assert "pedido_de_humano_ignorado" in regras(c)
    assert "depois do pedido" in achado(c, "pedido_de_humano_ignorado")["detalhe"]
