import pytest

from fraus.comparacao_modelos import bootstrap_da_diferenca, f1_macro, mcnemar_exato


def test_f1_macro_trata_classe_ausente_como_zero():
    rotulos = [0, 0, 1, 1, 2, 2]
    preditos = [0, 0, 1, 1, 1, 1]
    # classes 0 e 1: F1 1,0 e 0,667; classe 2 nunca prevista: 0.
    assert f1_macro(rotulos, preditos, classes=[0, 1, 2]) == pytest.approx((1.0 + 2 / 3 + 0.0) / 3)


def test_mcnemar_conta_so_os_discordantes():
    acertos_a = [True] * 10 + [True] * 8 + [False] * 1 + [False] * 5
    acertos_b = [True] * 10 + [False] * 8 + [True] * 1 + [False] * 5
    resultado = mcnemar_exato(acertos_a, acertos_b)
    assert (resultado.so_a, resultado.so_b) == (8, 1)
    # binomial exato bilateral com n=9: 2 * (C(9,0) + C(9,1)) / 2^9
    assert resultado.p_valor == pytest.approx(2 * 10 / 512)


def test_mcnemar_sem_discordancia_nao_e_evidencia():
    resultado = mcnemar_exato([True, False], [True, False])
    assert resultado.p_valor == 1.0


def test_mcnemar_recusa_listas_desalinhadas():
    with pytest.raises(ValueError):
        mcnemar_exato([True], [True, False])


def test_bootstrap_e_deterministico_e_cobre_a_diferenca_observada():
    rotulos = [0, 1] * 50
    bom = list(rotulos)
    ruim = [0] * 100
    a = bootstrap_da_diferenca(rotulos, bom, ruim, classes=[0, 1], reamostras=200, semente=7)
    b = bootstrap_da_diferenca(rotulos, bom, ruim, classes=[0, 1], reamostras=200, semente=7)
    assert a == b
    assert a.diferenca == pytest.approx(1.0 - (2 / 3) / 2)
    assert a.ic_inferior <= a.diferenca <= a.ic_superior
    assert a.ic_inferior > 0  # o modelo bom ganha em qualquer reamostra


def test_bootstrap_de_modelos_iguais_cruza_o_zero():
    rotulos = [0, 1, 1, 0] * 10
    preditos = [0, 1, 0, 0] * 10
    resultado = bootstrap_da_diferenca(rotulos, preditos, preditos, classes=[0, 1], reamostras=100)
    assert resultado.diferenca == 0.0
    assert resultado.ic_inferior == resultado.ic_superior == 0.0


# --- laudo: matriz de confusao, contagens por classe e relatorio --------------

from fraus.comparacao_modelos import (  # noqa: E402
    avaliar_conjunto,
    contagens_por_classe,
    matriz_de_confusao,
    montar_laudo,
    relatorio_markdown,
    validar_laudo,
)


def test_matriz_tem_o_real_na_linha_e_o_predito_na_coluna():
    matriz = matriz_de_confusao([0, 0, 1, 1, 1], [0, 1, 1, 1, 0], classes=[0, 1])
    assert matriz == [[1, 1], [1, 2]]


def test_contagens_por_classe_sao_uma_contra_o_resto():
    matriz = [[1, 1], [1, 2]]
    nao, sim = contagens_por_classe(matriz, ["nao-ironico", "ironico"])
    assert (sim["vp"], sim["fp"], sim["fn"], sim["vn"]) == (2, 1, 1, 1)
    assert (nao["vp"], nao["fp"], nao["fn"], nao["vn"]) == (1, 1, 1, 2)
    assert sim["precisao"] == pytest.approx(2 / 3)
    assert sim["recall"] == pytest.approx(2 / 3)
    assert sim["exemplos"] == 3


def test_classe_nunca_prevista_tem_precisao_ausente_e_nao_zero():
    # Sem nenhuma predicao da classe nao ha o que medir: None, nunca 0.
    matriz = matriz_de_confusao([0, 1], [0, 0], classes=[0, 1])
    _, rara = contagens_por_classe(matriz, ["a", "b"])
    assert rara["precisao"] is None
    assert rara["recall"] == 0.0
    assert rara["f1"] is None


def _conjunto():
    rotulos = [0, 1] * 20
    return avaliar_conjunto(
        identificador="ironia_interno",
        tarefa="ironia",
        nome="Ironia — teste interno",
        independente=False,
        rotulos=rotulos,
        preditos_por_modelo={"bertimbau": [0] * 40, "laya_treinado": list(rotulos)},
        classes=[0, 1],
        nomes_classes=["nao-ironico", "ironico"],
        reamostras=200,
    )


def test_conjunto_avaliado_carrega_matriz_contagens_e_comparacao():
    conjunto = _conjunto()
    assert conjunto["exemplos"] == 40
    assert conjunto["modelos"]["laya_treinado"]["acuracia"] == 1.0
    assert conjunto["modelos"]["bertimbau"]["matriz"] == [[20, 0], [20, 0]]
    comparacao = conjunto["comparacao"]
    assert (comparacao["candidato"], comparacao["referencia"]) == ("laya_treinado", "bertimbau")
    assert comparacao["mcnemar"]["so_candidato"] == 20
    assert comparacao["diferenca_demonstrada"] is True


def test_modelos_iguais_nao_tem_diferenca_demonstrada():
    rotulos = [0, 1] * 20
    conjunto = avaliar_conjunto(
        identificador="x", tarefa="ironia", nome="x", independente=True, rotulos=rotulos,
        preditos_por_modelo={"bertimbau": list(rotulos), "laya_treinado": list(rotulos)},
        classes=[0, 1], nomes_classes=["a", "b"], reamostras=100,
    )
    assert conjunto["comparacao"]["diferenca_demonstrada"] is False


def test_conjunto_recusa_predicoes_de_tamanho_diferente():
    with pytest.raises(ValueError):
        avaliar_conjunto(
            identificador="x", tarefa="ironia", nome="x", independente=True, rotulos=[0, 1],
            preditos_por_modelo={"bertimbau": [0], "laya_treinado": [0, 1]},
            classes=[0, 1], nomes_classes=["a", "b"],
        )


def _laudo(**extras):
    return montar_laudo(
        conjuntos=[_conjunto()],
        latencia={
            "hardware": "CPU do Colab, 2 nucleos",
            "amostra": 50,
            "medidas": [
                {"modelo": "bertimbau", "tarefa": "ironia", "executor": "torch",
                 "mediana_ms": 41.5, "p95_ms": 60.0},
            ],
        },
        procedencia={"fraus_commit": "abc1234"},
        rodada_de_fumaca=extras.get("fumaca", False),
        gerado_em="2026-10-02T13:00:00+00:00",
    )


def test_laudo_montado_passa_na_validacao():
    laudo = _laudo()
    assert laudo["schema"] == 1
    validar_laudo(laudo)


def test_validacao_recusa_laudo_de_outro_schema_ou_sem_conjuntos():
    with pytest.raises(ValueError):
        validar_laudo({"schema": 2, "conjuntos": []})
    with pytest.raises(ValueError):
        validar_laudo({"schema": 1})
    with pytest.raises(ValueError):
        validar_laudo([])


def test_relatorio_traz_os_numeros_do_laudo_e_a_procedencia():
    texto = relatorio_markdown(_laudo())
    assert "# Comparação de modelos" in texto
    assert "Ironia — teste interno" in texto
    assert "| ironico | 20 | 0 | 0 | 20 |" in texto  # VP FP FN VN do Laya treinado
    assert "41,5 ms" in texto
    assert "CPU do Colab, 2 nucleos" in texto
    assert "abc1234" in texto


def test_relatorio_de_fumaca_avisa_que_nao_e_resultado():
    assert "rodada de fumaça" in relatorio_markdown(_laudo(fumaca=True)).lower()
    assert "rodada de fumaça" not in relatorio_markdown(_laudo()).lower()


def test_relatorio_escreve_sem_diferenca_quando_o_intervalo_cruza_o_zero():
    rotulos = [0, 1] * 20
    conjunto = avaliar_conjunto(
        identificador="x", tarefa="ironia", nome="Empate", independente=True, rotulos=rotulos,
        preditos_por_modelo={"bertimbau": list(rotulos), "laya_treinado": list(rotulos)},
        classes=[0, 1], nomes_classes=["a", "b"], reamostras=100,
    )
    laudo = montar_laudo(conjuntos=[conjunto], latencia=None, procedencia={},
                         rodada_de_fumaca=False, gerado_em="2026-10-02T13:00:00+00:00")
    texto = relatorio_markdown(laudo)
    assert "sem diferença demonstrada" in texto
    assert "não foi medida" in texto  # latencia ausente e nomeada, nao zerada


def test_modelo_pode_prever_classe_que_o_conjunto_nao_tem():
    # XED-pt nao tem `neutro`, mas o modelo pode responder `neutro`: a predicao
    # entra na matriz como erro, e o F1 continua sobre as classes do conjunto.
    conjunto = avaliar_conjunto(
        identificador="xed", tarefa="emocao", nome="XED", independente=True,
        rotulos=[0, 0, 1, 1],
        preditos_por_modelo={"bertimbau": [0, 2, 1, 2], "laya_treinado": [0, 0, 1, 1]},
        classes=[0, 1, 2], nomes_classes=["a", "b", "neutro"], classes_do_f1=[0, 1],
        reamostras=50,
    )
    bertimbau = conjunto["modelos"]["bertimbau"]
    assert bertimbau["matriz"] == [[1, 0, 1], [0, 1, 1], [0, 0, 0]]
    neutro = bertimbau["por_classe"][2]
    assert (neutro["exemplos"], neutro["fp"], neutro["recall"]) == (0, 2, None)
    assert bertimbau["f1_macro"] == pytest.approx(2 / 3)  # so a e b; neutro nao entra
    assert conjunto["modelos"]["laya_treinado"]["f1_macro"] == 1.0


def test_classe_fora_da_matriz_e_erro_nomeado():
    with pytest.raises(ValueError, match="classe 6"):
        matriz_de_confusao([0, 1], [0, 6], classes=[0, 1])
