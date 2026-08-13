from dolos.ingest.simulador import gerar_conversa, gerar_lote
from dolos.sinais.tempo import features_tempo

FRASES = {
    0: ["que absurdo, ninguem resolve", "pessimo atendimento"],
    1: ["ok", "entendi"],
    2: ["muito obrigado, resolveu", "excelente atendimento"],
}


def test_conversa_gerada_e_valida_e_tem_fala_do_cliente():
    conversa = gerar_conversa(rotulo=2, frases_cliente=FRASES[2], semente=42)
    assert conversa.tem_sinal_cliente
    assert conversa.mensagens[0].autor == "cliente"


def test_mesma_semente_gera_a_mesma_conversa():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    assert a.model_dump() == b.model_dump()


def test_sementes_diferentes_geram_conversas_diferentes():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=1)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=2)
    assert a.model_dump() != b.model_dump()


def test_insatisfeito_tem_latencia_maior_que_satisfeito():
    satisfeitas = [
        features_tempo(gerar_conversa(2, FRASES[2], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    insatisfeitas = [
        features_tempo(gerar_conversa(0, FRASES[0], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    media_satisfeitas = sum(satisfeitas) / len(satisfeitas)
    media_insatisfeitas = sum(insatisfeitas) / len(insatisfeitas)
    assert media_insatisfeitas > media_satisfeitas * 3


def test_lote_respeita_a_quantidade_e_devolve_rotulos():
    lote = gerar_lote(FRASES, quantidade=30, semente=3)
    assert len(lote) == 30
    assert {rotulo for _, rotulo in lote} == {0, 1, 2}
    assert len({conversa.id for conversa, _ in lote}) == 30
