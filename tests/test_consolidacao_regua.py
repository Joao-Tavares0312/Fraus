import pytest

from fraus.avaliacao_ironia import FraseDoRascunho
from fraus.consolidacao_regua import (conferir_ids, decidir_pares, fleiss_kappa, rotulo_humano,
                                      ultimas_respostas)


def test_fleiss_kappa_bate_com_o_exemplo_de_livro():
    # Exemplo classico (Fleiss 1971, reproduzido na Wikipedia): 10 itens,
    # 14 anotadores, 5 categorias, kappa = 0,210.
    contagens = [
        [0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1], [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0], [0, 2, 2, 3, 7],
    ]
    assert fleiss_kappa(contagens) == pytest.approx(0.210, abs=0.001)


def test_rotulo_por_maioria_e_ambiguo_no_empate_e_no_contexto():
    assert rotulo_humano(["ironico", "ironico", "nao_ironico"]) == 1
    assert rotulo_humano(["nao_ironico", "nao_ironico"]) == 0
    assert rotulo_humano(["ironico", "nao_ironico"]) is None
    assert rotulo_humano(["contexto", "contexto", "ironico"]) is None


def test_frase_com_resposta_insuficiente_e_ambigua():
    assert rotulo_humano(["ironico"]) is None
    assert rotulo_humano([]) is None


def test_ultima_resposta_do_anotador_vence():
    registros = [
        {"anotador": "a", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-09T10:00:00Z"},
        {"anotador": "a", "frase_id": "f1", "resposta": "nao_ironico", "instante": "2026-10-09T10:05:00Z"},
        {"anotador": "b", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-09T10:01:00Z"},
    ]
    assert sorted(ultimas_respostas(registros)["f1"]) == ["ironico", "nao_ironico"]


def _par(n, rotulo_texto):
    return [
        FraseDoRascunho(f"elogio-{n:02d}", "elogio", "banco", 0, f"sincera {n}{rotulo_texto}"),
        FraseDoRascunho(f"elogio-{n:02d}", "elogio", "banco", 1, f"ironica {n}{rotulo_texto}"),
    ]


def test_par_so_entra_com_os_dois_lados_confirmados():
    frases = _par(1, "") + _par(2, "") + _par(3, "")
    ids = {f.texto: f.frase_id for f in frases}
    respostas = {
        ids["sincera 1"]: ["nao_ironico"] * 3, ids["ironica 1"]: ["ironico"] * 3,
        ids["sincera 2"]: ["nao_ironico"] * 3, ids["ironica 2"]: ["contexto"] * 3,
        ids["sincera 3"]: ["ironico"] * 3, ids["ironica 3"]: ["ironico"] * 3,
    }
    mantidas, descartadas = decidir_pares(frases, respostas, minimo_pares=1)
    assert {m["par_id"] for m in mantidas} == {"elogio-01"}
    assert {(d["par_id"], d["motivo"]) for d in descartadas} == {
        ("elogio-02", "ambigua"), ("elogio-02", "par_incompleto"),
        ("elogio-03", "divergente"), ("elogio-03", "par_incompleto"),
    }
    assert mantidas[0]["concordancia"] == 1.0


def test_menos_pares_que_o_piso_falha_alto():
    frases = _par(1, "")
    ids = {f.texto: f.frase_id for f in frases}
    respostas = {ids["sincera 1"]: ["nao_ironico"] * 2, ids["ironica 1"]: ["ironico"] * 2}
    with pytest.raises(ValueError, match="faltam 99"):
        decidir_pares(frases, respostas)


def test_conferir_ids_aceita_ids_validos():
    frases = _par(1, "")
    ids = {f.texto: f.frase_id for f in frases}
    registros = [
        {"anotador": "a", "frase_id": ids["sincera 1"], "resposta": "nao_ironico", "instante": "2026-10-09T10:00:00Z"},
        {"anotador": "a", "frase_id": ids["ironica 1"], "resposta": "ironico", "instante": "2026-10-09T10:00:00Z"},
    ]
    conferir_ids(registros, frases)  # nao levanta


def test_conferir_ids_falha_com_ids_desconhecidos():
    frases = _par(1, "")
    registros = [
        {"anotador": "a", "frase_id": "id_desconhecido", "resposta": "ironico", "instante": "2026-10-09T10:00:00Z"},
    ]
    with pytest.raises(ValueError, match="id_desconhecido"):
        conferir_ids(registros, frases)
