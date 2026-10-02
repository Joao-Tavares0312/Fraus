"""Divisao treino/teste por autor: linha sem autor nao pode virar um grupo so."""

import math

import pytest

from fraus.divisao import (
    conferir_divisao,
    dividir_por_autor,
    grupos_por_autor,
    impressao_dos_textos,
)


def test_linha_sem_autor_vira_grupo_proprio():
    # O pandas le campo vazio como NaN; `astype(str)` fazia dele o autor "nan".
    grupos = grupos_por_autor(["ana", None, float("nan"), "", "  ", "ana"])
    assert grupos[0] == grupos[5] == "ana"
    sem_autor = [grupos[i] for i in (1, 2, 3, 4)]
    assert len(set(sem_autor)) == 4
    assert "ana" not in sem_autor


def test_grupo_de_quem_nao_tem_autor_nao_colide_com_autor_de_verdade():
    grupos = grupos_por_autor(["sem-autor:1", None])
    assert grupos[0] != grupos[1]


def test_autor_chamado_nan_continua_sendo_um_autor():
    grupos = grupos_por_autor(["nan", "nan", None])
    assert grupos[0] == grupos[1] != grupos[2]


def test_divisao_espalha_as_linhas_sem_autor_pelos_dois_lados():
    # O corpus real: metade com autor (tweets), metade sem (noticias).
    autores = [f"autor{i % 300}" for i in range(1000)] + [float("nan")] * 1000
    treino, teste = dividir_por_autor(autores, fracao_teste=0.15, semente=42)
    assert sorted(treino + teste) == list(range(2000))
    assert 0.10 <= len(teste) / 2000 <= 0.20
    sem_autor_no_teste = sum(1 for i in teste if i >= 1000)
    assert 100 <= sem_autor_no_teste <= 200


def test_mesmo_autor_nunca_fica_dos_dois_lados():
    autores = [f"autor{i % 50}" for i in range(500)] + [None] * 100
    treino, teste = dividir_por_autor(autores, fracao_teste=0.2, semente=7)
    assert {autores[i] for i in treino if i < 500}.isdisjoint(
        {autores[i] for i in teste if i < 500})


def test_divisao_e_deterministica():
    autores = [f"autor{i % 50}" for i in range(500)] + [None] * 100
    assert dividir_por_autor(autores, semente=42) == dividir_por_autor(autores, semente=42)


def test_conferir_aceita_divisao_equilibrada():
    conferir_divisao([0] * 430 + [1] * 420, [0] * 80 + [1] * 70, fracao_teste=0.15)


def test_conferir_recusa_teste_maior_que_o_pedido():
    # 02/10/2026: pediu 15% e saiu 63%.
    with pytest.raises(ValueError, match="63%"):
        conferir_divisao([0] * 185, [1] * 157 + [0] * 158, fracao_teste=0.15)


def test_conferir_recusa_proporcao_de_classe_diferente():
    # Treino 86% ironico, teste 43%: o modelo aprende a proporcao, nao a tarefa.
    with pytest.raises(ValueError, match="classe"):
        conferir_divisao([1] * 731 + [0] * 119, [1] * 65 + [0] * 85, fracao_teste=0.15)


def test_conferir_recusa_classe_ausente_de_um_lado():
    with pytest.raises(ValueError, match="classe"):
        conferir_divisao([0] * 800 + [1] * 50, [0] * 150, fracao_teste=0.15)


def test_impressao_nao_depende_da_ordem_e_muda_com_o_conteudo():
    a = impressao_dos_textos(["um", "dois", "tres"])
    assert a == impressao_dos_textos(["tres", "um", "dois"])
    assert a != impressao_dos_textos(["um", "dois"])
    assert a != impressao_dos_textos(["um", "dois tres"])
    assert len(a) == 64 and not math.isnan(int(a, 16))
