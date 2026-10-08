import json
from collections import Counter

from fraus.anotacao_regua import frases_para_anotacao
from fraus.avaliacao_ironia import carregar_rascunho


def test_pagina_nao_recebe_par_estrato_nem_rotulo():
    payload = frases_para_anotacao(carregar_rascunho())
    assert all(set(item) == {"id", "texto", "g"} for item in payload)
    bruto = json.dumps(payload, ensure_ascii=False)
    for proibido in ("par_id", "estrato", "rotulo", "dominio"):
        assert proibido not in bruto
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


def test_grupo_g_aparece_duas_vezes_e_une_os_lados_do_par():
    frases = carregar_rascunho()
    par_de = {f.frase_id: f.par_id for f in frases}
    payload = frases_para_anotacao(frases)
    assert set(Counter(item["g"] for item in payload).values()) == {2}
    grupos = {}
    for item in payload:
        grupos.setdefault(par_de[item["id"]], set()).add(item["g"])
    assert all(len(g) == 1 for g in grupos.values())
    assert len({next(iter(g)) for g in grupos.values()}) == len(grupos)


def test_grupo_g_nao_acompanha_a_ordem_do_rascunho():
    frases = carregar_rascunho()
    payload = frases_para_anotacao(frases)
    par_de = {f.frase_id: f.par_id for f in frases}
    pares_na_ordem = list(dict.fromkeys(par_de[i["id"]] for i in payload))
    g_na_ordem = [next(i["g"] for i in payload if par_de[i["id"]] == p) for p in pares_na_ordem]
    assert g_na_ordem != sorted(g_na_ordem)


# ---- ordem por anotador e ultima resposta (rota publica /anotacao) --------

from fraus.anotacao_regua import ordem_do_anotador, respostas_do_anotador  # noqa: E402


def test_ordem_do_anotador_so_tem_id_e_texto():
    payload = ordem_do_anotador(carregar_rascunho(), "a_00000001")
    assert all(set(item) == {"id", "texto"} for item in payload)
    assert len(payload) == 300


def test_ordem_do_anotador_e_estavel_e_muda_entre_anotadores():
    frases = carregar_rascunho()
    a = ordem_do_anotador(frases, "a_00000001")
    assert a == ordem_do_anotador(frases, "a_00000001")
    assert [i["id"] for i in a] != [i["id"] for i in ordem_do_anotador(frases, "a_00000002")]


def test_ordem_do_anotador_sem_lados_do_par_em_sequencia():
    frases = carregar_rascunho()
    par_de = {f.frase_id: f.par_id for f in frases}
    for anotador in ("a_00000001", "a_deadbeef", "a_12345678"):
        ids = [i["id"] for i in ordem_do_anotador(frases, anotador)]
        assert all(par_de[x] != par_de[y] for x, y in zip(ids, ids[1:]))


def test_respostas_do_anotador_ultima_vence_e_ignora_outros():
    registros = [
        {"anotador": "a1", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-08T10:00:00.000000+00:00"},
        {"anotador": "a1", "frase_id": "f1", "resposta": "contexto", "instante": "2026-10-08T10:00:01.000000+00:00"},
        {"anotador": "a1", "frase_id": "f2", "resposta": "nao_ironico", "instante": "2026-10-08T09:00:00.000000+00:00"},
        {"anotador": "a2", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-08T11:00:00.000000+00:00"},
    ]
    assert respostas_do_anotador(registros, "a1") == {"f1": "contexto", "f2": "nao_ironico"}
    assert respostas_do_anotador(list(reversed(registros)), "a1") == {"f1": "contexto", "f2": "nao_ironico"}
