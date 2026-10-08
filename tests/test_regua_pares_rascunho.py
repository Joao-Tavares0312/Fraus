from collections import Counter

import pytest

from fraus.avaliacao_ironia import (IRONIAS_SEM_MARCADOR, SINCERAS_COM_MARCADOR,
                                    carregar_rascunho, conferir_registro_equilibrado)

SONDAS_DO_04 = {
    "otimo servico, so esperei 3 horas",
    "parabens pelo atendimento, nota mil, so 5 dias sem resposta",
    "qual o prazo de entrega do meu pedido",
    "obrigado, resolveram rapido",
}


def test_rascunho_tem_150_pares_50_por_estrato_um_lado_de_cada():
    frases = carregar_rascunho()
    assert len(frases) == 300
    por_par = {}
    for frase in frases:
        por_par.setdefault(frase.par_id, []).append(frase)
    assert len(por_par) == 150
    assert all(sorted(f.rotulo for f in lados) == [0, 1] for lados in por_par.values())
    assert all(len({f.estrato for f in lados}) == 1 for lados in por_par.values())
    assert Counter(lados[0].estrato for lados in por_par.values()) == {
        "elogio": 50, "reclamacao": 50, "neutra": 50,
    }
    assert len({f.dominio for f in frases}) >= 6


def test_rascunho_sem_repeticao_nem_frase_da_regua_antiga():
    textos = [f.texto for f in carregar_rascunho()]
    assert len(set(textos)) == len(textos)
    assert len({f.frase_id for f in carregar_rascunho()}) == len(textos)
    proibidas = {t.lower() for t in (*SINCERAS_COM_MARCADOR, *IRONIAS_SEM_MARCADOR, *SONDAS_DO_04)}
    assert not proibidas & {t.lower() for t in textos}


def test_rascunho_tem_registro_equilibrado():
    frases = carregar_rascunho()
    conferir_registro_equilibrado([f.texto for f in frases], [f.rotulo for f in frases])


def test_conferencia_reprova_ponto_final_so_nos_ironicos():
    textos = ["a b"] * 10 + ["a b."] * 10
    with pytest.raises(ValueError, match="termina_ponto"):
        conferir_registro_equilibrado(textos, [0] * 10 + [1] * 10)
