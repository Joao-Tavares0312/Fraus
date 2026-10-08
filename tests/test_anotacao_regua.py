from fraus.anotacao_regua import frases_para_anotacao
from fraus.avaliacao_ironia import carregar_rascunho


def test_pagina_nao_recebe_par_estrato_nem_rotulo():
    payload = frases_para_anotacao(carregar_rascunho())
    assert all(set(item) == {"id", "texto"} for item in payload)
    assert len(payload) == 300


def test_lados_do_par_nunca_vizinhos_nem_na_volta():
    frases = carregar_rascunho()
    par_de = {f.frase_id: f.par_id for f in frases}
    payload = frases_para_anotacao(frases)
    ids = [item["id"] for item in payload]
    for i, atual in enumerate(ids):
        seguinte = ids[(i + 1) % len(ids)]
        assert par_de[atual] != par_de[seguinte]


def test_ordem_e_deterministica():
    frases = carregar_rascunho()
    assert frases_para_anotacao(frases) == frases_para_anotacao(frases)
