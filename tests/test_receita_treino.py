"""A receita de treino que os notebooks 01, 03 e 04 importam.

O defeito que ela corrige: os tres notebooks escolhiam a melhor epoca NO
TESTE e reportavam nesse mesmo teste. Aqui a selecao mora na validacao, e o
teste so e tocado uma vez.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from fraus.receita_treino import (
    ajustar_temperatura,
    aplicar_temperatura,
    argumentos_padrao,
    dividir_treino_val_teste,
    metricas_completas,
    normalizar_texto,
    remover_duplicatas,
    resumir_sementes,
)


# --- duplicatas ---------------------------------------------------------------


def test_normalizar_texto_ignora_caixa_espaco_e_forma_unicode():
    assert normalizar_texto("  Ótimo   ATENDIMENTO ") == normalizar_texto("ótimo atendimento")
    # "o" + acento combinante (NFD) e "ó" pre-composto sao o mesmo texto
    assert normalizar_texto("ótimo") == normalizar_texto("ótimo")


def test_remover_duplicatas_mantem_a_primeira_e_descarta_conflito():
    textos = ["bom", "Bom ", "ruim", "meh", "MEH", "ok"]
    rotulos = [2, 2, 0, 1, 0, 1]
    resultado = remover_duplicatas(textos, rotulos)
    # "bom" aparece duas vezes com o mesmo rotulo: fica a primeira.
    # "meh" aparece com rotulos diferentes: sai inteiro, nao ha resposta certa.
    assert resultado.indices == [0, 2, 5]
    assert resultado.duplicatas == 1
    assert resultado.conflitos == 2


def test_remover_duplicatas_exige_tamanhos_iguais():
    with pytest.raises(ValueError):
        remover_duplicatas(["a", "b"], [0])


# --- divisao em tres --------------------------------------------------------


def _corpus(n=2000, semente=0):
    gerador = np.random.default_rng(semente)
    rotulos = gerador.choice([0, 1, 2], size=n, p=[0.3, 0.2, 0.5]).tolist()
    return rotulos


def test_divisao_em_tres_e_disjunta_cobre_tudo_e_respeita_fracoes():
    rotulos = _corpus()
    d = dividir_treino_val_teste(rotulos, fracao_val=0.1, fracao_teste=0.15, semente=42)
    treino, val, teste = set(d.treino), set(d.validacao), set(d.teste)
    assert not (treino & val) and not (treino & teste) and not (val & teste)
    assert treino | val | teste == set(range(len(rotulos)))
    assert abs(len(teste) / len(rotulos) - 0.15) < 0.01
    assert abs(len(val) / len(rotulos) - 0.10) < 0.01


def test_divisao_em_tres_e_estratificada():
    rotulos = _corpus()
    d = dividir_treino_val_teste(rotulos, semente=42)
    for lado in (d.treino, d.validacao, d.teste):
        parte = sum(1 for i in lado if rotulos[i] == 1) / len(lado)
        assert abs(parte - 0.2) < 0.03


def test_divisao_em_tres_e_deterministica_pela_semente():
    rotulos = _corpus()
    a = dividir_treino_val_teste(rotulos, semente=7)
    b = dividir_treino_val_teste(rotulos, semente=7)
    c = dividir_treino_val_teste(rotulos, semente=8)
    assert a.teste == b.teste and a.validacao == b.validacao
    assert a.teste != c.teste


def test_divisao_por_grupo_nao_repete_grupo_entre_lados():
    rotulos = _corpus(3000)
    grupos = [f"produto-{i // 3}" for i in range(len(rotulos))]  # 1000 produtos
    d = dividir_treino_val_teste(rotulos, grupos=grupos, semente=42)
    lados = [{grupos[i] for i in lado} for lado in (d.treino, d.validacao, d.teste)]
    assert not (lados[0] & lados[1]) and not (lados[0] & lados[2]) and not (lados[1] & lados[2])


def test_divisao_por_grupo_falha_alto_com_grupo_gigante():
    # Um grupo com metade do corpus nao cabe em 15% -- a divisao nao pode
    # entregar outra coisa em silencio (foi o que aconteceu em 02/10/2026).
    rotulos = _corpus(1000)
    grupos = ["mesmo"] * 500 + [f"g{i}" for i in range(500)]
    with pytest.raises(ValueError):
        dividir_treino_val_teste(rotulos, grupos=grupos, semente=42)


# --- temperatura ------------------------------------------------------------


def _logits_sobreconfiantes(n=3000, semente=0, escala=4.0):
    gerador = np.random.default_rng(semente)
    rotulos = gerador.integers(0, 3, size=n)
    # logit "verdadeiro" calibrado a T=1, depois multiplicado: o modelo
    # resultante e sobreconfiante por um fator `escala`.
    base = gerador.normal(0, 1, size=(n, 3))
    base[np.arange(n), rotulos] += 1.0
    return (base * escala).tolist(), rotulos.tolist()


def test_ajustar_temperatura_recupera_a_escala_da_sobreconfianca():
    logits, rotulos = _logits_sobreconfiantes(escala=4.0)
    t = ajustar_temperatura(logits, rotulos)
    assert 3.0 < t < 5.0


def test_aplicar_temperatura_um_e_softmax_puro_e_preserva_argmax():
    logits = [[2.0, 0.5, -1.0], [0.0, 0.0, 3.0]]
    p1 = aplicar_temperatura(logits, 1.0)
    p3 = aplicar_temperatura(logits, 3.0)
    for linha in p1 + p3:
        assert math.isclose(sum(linha), 1.0, rel_tol=1e-9)
    assert [int(np.argmax(x)) for x in p1] == [int(np.argmax(x)) for x in p3]
    assert max(p3[0]) < max(p1[0])


def test_temperatura_invalida_falha():
    with pytest.raises(ValueError):
        aplicar_temperatura([[1.0, 0.0]], 0.0)


# --- metricas e sementes ------------------------------------------------------


def test_metricas_completas_traz_f1_por_classe_e_ece():
    probs = [[0.9, 0.05, 0.05], [0.1, 0.8, 0.1], [0.2, 0.2, 0.6], [0.6, 0.3, 0.1]]
    rotulos = [0, 1, 2, 2]
    m = metricas_completas(probs, rotulos, nomes_classes=["insatisfeito", "neutro", "satisfeito"])
    assert m["acuracia"] == pytest.approx(0.75)
    assert [c["classe"] for c in m["por_classe"]] == ["insatisfeito", "neutro", "satisfeito"]
    assert 0.0 <= m["ece"] <= 1.0
    assert m["exemplos"] == 4


def test_resumir_sementes_da_media_desvio_e_semente_mediana():
    rodadas = [
        {"semente": 1, "f1_macro": 0.70},
        {"semente": 2, "f1_macro": 0.74},
        {"semente": 3, "f1_macro": 0.72},
    ]
    r = resumir_sementes(rodadas, chave="f1_macro")
    assert r["media"] == pytest.approx(0.72)
    assert r["desvio"] == pytest.approx(0.02)
    # promove a MEDIANA, nao a melhor: escolher a melhor de 3 e selecao no acaso
    assert r["semente_mediana"] == 3


def test_resumir_sementes_exige_pelo_menos_duas():
    with pytest.raises(ValueError):
        resumir_sementes([{"semente": 1, "f1_macro": 0.7}], chave="f1_macro")


# --- argumentos -----------------------------------------------------------------


def test_argumentos_padrao_selecionam_na_validacao_com_parada_antecipada():
    a = argumentos_padrao("/tmp/saida", semente=13, metrica="f1_macro")
    assert a["seed"] == 13
    assert a["metric_for_best_model"] == "f1_macro"
    assert a["load_best_model_at_end"] is True
    assert a["warmup_ratio"] == pytest.approx(0.1)
    assert a["weight_decay"] == pytest.approx(0.01)
    assert a["eval_strategy"] == a["save_strategy"] == "epoch"
    assert a["paciencia"] == 2  # vai para o EarlyStoppingCallback, nao para o TrainingArguments
