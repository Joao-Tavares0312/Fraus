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


def test_resumir_sementes_seleciona_por_validacao_por_padrao():
    rodadas = [
        {"semente": 13, "f1_macro_validacao": 0.7, "f1_macro": 0.99},
        {"semente": 42, "f1_macro_validacao": 0.9, "f1_macro": 0.50},
        {"semente": 77, "f1_macro_validacao": 0.8, "f1_macro": 0.40},
    ]
    r = resumir_sementes(rodadas)
    assert r["chave"] == "f1_macro_validacao"
    assert r["semente_mediana"] == 77


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


# --- preparar_divisao: o caminho unico de notebook e benchmark ------------------


def test_preparar_divisao_tira_duplicata_antes_e_devolve_os_tres_lados():
    from fraus.corpora import Exemplos
    from fraus.divisao import impressao_dos_textos
    from fraus.receita_treino import preparar_divisao

    rotulos = _corpus(1500)
    textos = [f"texto {i}" for i in range(len(rotulos))]
    textos[10] = textos[11] = "repetido"
    rotulos[10] = rotulos[11]
    ex = Exemplos(textos=textos, rotulos=rotulos, grupos=None, nomes_classes=["a", "b", "c"])
    lados = preparar_divisao(ex, semente=42)
    total = sum(len(l.textos) for l in lados.values())
    assert set(lados) == {"treino", "validacao", "teste"}
    assert total == len(textos) - 1
    todos = [t for l in lados.values() for t in l.textos]
    assert todos.count("repetido") == 1
    assert lados["teste"].nomes_classes == ["a", "b", "c"]
    # deterministico: a impressao do teste e o que notebook e benchmark comparam
    de_novo = preparar_divisao(ex, semente=42)
    assert impressao_dos_textos(de_novo["teste"].textos) == impressao_dos_textos(
        lados["teste"].textos
    )


def test_amostra_estratificada_mantem_proporcao_e_e_deterministica():
    from fraus.corpora import Exemplos
    from fraus.receita_treino import amostra_estratificada

    rotulos = _corpus(5000)
    ex = Exemplos(textos=[str(i) for i in range(5000)], rotulos=rotulos, nomes_classes=["a", "b", "c"])
    a = amostra_estratificada(ex, 1000, semente=1)
    assert len(a.textos) == 1000
    assert abs(sum(r == 1 for r in a.rotulos) / 1000 - 0.2) < 0.02
    assert a.textos == amostra_estratificada(ex, 1000, semente=1).textos
    assert amostra_estratificada(ex, 99999, semente=1).textos == ex.textos


def test_pesos_de_classe_favorecem_a_rara():
    from fraus.receita_treino import pesos_de_classe

    pesos = pesos_de_classe([0, 0, 0, 1], 3)
    assert pesos[1] > pesos[0]
    assert pesos[2] == pytest.approx(4 / 3)  # ausente: conta como 1


def test_treinar_uma_semente_ponta_a_ponta_com_bert_minusculo(tmp_path, monkeypatch):
    """Fumaca em CPU: modelo aleatorio de 2 camadas, montado aqui, sem download."""
    torch = pytest.importorskip("torch")
    pytest.importorskip("accelerate")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 0)
    import json

    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase

    from fraus.corpora import Exemplos
    import fraus.receita_treino as receita
    from fraus.generalizacao import fingerprint_exemplos
    from fraus.receita_treino import (
        ARQUIVO_AVALIACAO_FINAL,
        ARQUIVO_RECEITA,
        avaliar_teste_final,
        preparar_divisao,
        treinar_uma_semente,
    )

    palavras = ["bom", "otimo", "ruim", "pessimo", "ok", "normal", "atendimento", "foi"]
    vocab = tmp_path / "vocab.txt"
    vocab.write_text("\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *palavras]))
    base = tmp_path / "base"
    BertTokenizerFast(vocab_file=str(vocab), do_lower_case=True).save_pretrained(base)
    torch.manual_seed(0)
    BertForSequenceClassification(BertConfig(
        vocab_size=len(palavras) + 5, hidden_size=16, num_hidden_layers=2,
        num_attention_heads=2, intermediate_size=32, num_labels=3,
    )).save_pretrained(base)

    frases = {0: ["foi ruim", "pessimo atendimento"], 1: ["foi ok", "atendimento normal"],
              2: ["foi bom", "otimo atendimento"]}
    textos, rotulos = [], []
    for i in range(300):
        classe = i % 3
        textos.append(f"{frases[classe][i % 2]} {i}")  # numero vira [UNK]; texto unico
        rotulos.append(classe)
    lados = preparar_divisao(Exemplos(textos=textos, rotulos=rotulos, grupos=None,
                                      nomes_classes=["insatisfeito", "neutro", "satisfeito"]))
    tokenizados = []
    chamar_original = PreTrainedTokenizerBase.__call__

    def registrar_tokenizacao(self, texto, *args, **kwargs):
        tokenizados.extend([texto] if isinstance(texto, str) else list(texto))
        return chamar_original(self, texto, *args, **kwargs)

    monkeypatch.setattr(PreTrainedTokenizerBase, "__call__", registrar_tokenizacao)
    saida = tmp_path / "saida"
    r = treinar_uma_semente(
        modelo_base=str(base), lados=lados, semente=7, dir_checkpoint=str(tmp_path / "ck"),
        dir_saida=str(saida), epocas=2, lote=16, fp16=False, taxa=5e-3,
        tamanho_maximo=24,
    )
    assert r["tamanhos"]["teste"] == len(lados["teste"].textos)
    assert r["temperatura"] > 0
    assert "f1_macro" not in r and "teste" not in r
    assert 0 <= r["f1_macro_validacao"] <= 1
    assert not set(tokenizados).intersection(lados["teste"].textos)
    assert r["manifesto_divisao"]["teste"]["fingerprint"] == fingerprint_exemplos(lados["teste"])
    assert r["argumentos_efetivos"]["seed"] == 7
    assert r["argumentos_efetivos"]["num_train_epochs"] == 2
    assert r["diagnostico_treino"]["exemplos"] == len(lados["treino"].textos)
    assert r["diagnostico_treino"]["exemplos"] <= 2000
    assert r["diagnostico_treino"]["semente"] == 42

    def curvas(resultado):
        return [
            {k: v for k, v in registro.items() if k.startswith("diagnostico_") or k == "epoch"}
            for registro in resultado["historico"] if "diagnostico_treino_loss" in registro
        ]

    curva = curvas(r)
    assert len(curva) == 2
    assert [linha["epoch"] for linha in curva] == [1.0, 2.0]
    for linha in curva:
        assert all(math.isfinite(valor) for valor in linha.values())
        for lado in ("treino", "validacao"):
            assert linha[f"diagnostico_{lado}_loss"] > 0
            assert 0 <= linha[f"diagnostico_{lado}_f1_macro"] <= 1
    avaliacoes = [linha for linha in r["historico"] if "eval_f1_macro" in linha]
    assert r["melhor_epoca"] == max(avaliacoes, key=lambda linha: linha["eval_f1_macro"])["epoch"]
    assert not (saida / ARQUIVO_AVALIACAO_FINAL).exists()

    # So os rotulos de teste mudam. Trajetoria, checkpoint escolhido e
    # calibracao permanecem identicos, mas a identidade do teste muda.
    teste_alterado = Exemplos(
        textos=list(lados["teste"].textos),
        rotulos=[(rotulo + 1) % 3 for rotulo in lados["teste"].rotulos],
        grupos=lados["teste"].grupos,
        nomes_classes=list(lados["teste"].nomes_classes),
    )
    repeticao = treinar_uma_semente(
        modelo_base=str(base), lados={**lados, "teste": teste_alterado}, semente=7,
        dir_checkpoint=str(tmp_path / "ck-repeticao"), dir_saida=str(tmp_path / "repeticao"),
        epocas=2, lote=16, fp16=False, taxa=5e-3, tamanho_maximo=24,
    )
    assert curvas(repeticao) == curva
    assert repeticao["melhor_epoca"] == r["melhor_epoca"]
    assert repeticao["temperatura"] == r["temperatura"]
    assert repeticao["f1_macro_validacao"] == r["f1_macro_validacao"]
    assert repeticao["manifesto_divisao"]["teste"] != r["manifesto_divisao"]["teste"]
    assert not set(tokenizados).intersection(lados["teste"].textos)

    from transformers import AutoModelForSequenceClassification

    pesos_a = AutoModelForSequenceClassification.from_pretrained(saida).state_dict()
    pesos_b = AutoModelForSequenceClassification.from_pretrained(tmp_path / "repeticao").state_dict()
    assert all(torch.equal(pesos_a[nome], pesos_b[nome]) for nome in pesos_a)
    gravado = json.loads((saida / ARQUIVO_RECEITA).read_text())
    assert gravado["semente"] == 7 and gravado["impressao_teste"] == r["impressao_teste"]
    assert gravado["historico"] == r["historico"]
    assert gravado["manifesto_divisao"] == r["manifesto_divisao"]
    assert gravado["argumentos_efetivos"] == r["argumentos_efetivos"]
    assert "teste" not in gravado and "f1_macro" not in gravado
    receita_antes = (saida / ARQUIVO_RECEITA).read_bytes()
    chamadas = []
    inferir_original = receita._prever_logits

    def registrar_inferencia(dir_modelo, textos, **kwargs):
        chamadas.append((list(textos), kwargs))
        return inferir_original(dir_modelo, textos, **kwargs)

    monkeypatch.setattr(receita, "_prever_logits", registrar_inferencia)
    final = avaliar_teste_final(
        dir_modelo=str(saida), exemplos=lados["teste"],
        manifesto_esperado=r["manifesto_divisao"]["teste"]["fingerprint"],
    )
    assert chamadas == [(lados["teste"].textos, {"tamanho_maximo": 24})]
    assert 0 <= final["f1_macro"] <= 1
    assert 0 <= final["ece"] <= 1 and 0 <= final["ece_sem_temperatura"] <= 1
    assert final["fingerprint_teste"] == fingerprint_exemplos(lados["teste"])
    assert len(final["hash_modelo"]) == 64
    assert "model.safetensors" in final["hashes_modelo"]
    assert json.loads((saida / ARQUIVO_AVALIACAO_FINAL).read_text()) == final
    assert (saida / ARQUIVO_RECEITA).read_bytes() == receita_antes
    with pytest.raises(ValueError, match="^manifesto de teste divergente$"):
        avaliar_teste_final(
            dir_modelo=str(saida), exemplos=teste_alterado,
            manifesto_esperado=fingerprint_exemplos(teste_alterado),
        )
    assert len(chamadas) == 1
    from transformers import AutoConfig

    from fraus.receita_treino import prever_probabilidades

    probs = prever_probabilidades(str(saida), ["foi bom", "foi ruim"],
                                  temperatura=r["temperatura"])
    assert len(probs) == 2 and all(abs(sum(p) - 1) < 1e-6 for p in probs)
    assert AutoConfig.from_pretrained(saida).id2label == {0: "insatisfeito", 1: "neutro",
                                                          2: "satisfeito"}


@pytest.mark.parametrize("alteracao", ["texto", "rotulo", "grupo", "classes", "esperado", "salvo"])
def test_avaliacao_final_recusa_manifesto_antes_de_carregar_modelo(tmp_path, monkeypatch, alteracao):
    import json

    import fraus.receita_treino as receita
    from fraus.corpora import Exemplos
    from fraus.generalizacao import fingerprint_exemplos

    exemplos = Exemplos(["frase"], [0], ["grupo"], ["nao", "sim"])
    esperado = fingerprint_exemplos(exemplos)
    (tmp_path / receita.ARQUIVO_RECEITA).write_text(json.dumps({
        "manifesto_divisao": {"teste": {"fingerprint": esperado}},
    }))
    if alteracao == "texto":
        exemplos.textos[0] = "outra frase"
    elif alteracao == "rotulo":
        exemplos.rotulos[0] = 1
    elif alteracao == "grupo":
        exemplos.grupos[0] = "outro grupo"
    elif alteracao == "classes":
        exemplos.nomes_classes.reverse()
    elif alteracao == "esperado":
        esperado = "nao corresponde"
    else:
        (tmp_path / receita.ARQUIVO_RECEITA).write_text(json.dumps({
            "manifesto_divisao": {"teste": {"fingerprint": "nao corresponde"}},
        }))

    def nao_inferir(*args, **kwargs):
        pytest.fail("manifesto divergente chegou ao carregamento/inferencia")

    monkeypatch.setattr(receita, "_prever_logits", nao_inferir)
    with pytest.raises(ValueError, match="^manifesto de teste divergente$"):
        receita.avaliar_teste_final(
            dir_modelo=str(tmp_path), exemplos=exemplos, manifesto_esperado=esperado
        )
    assert not (tmp_path / receita.ARQUIVO_AVALIACAO_FINAL).exists()


def test_juntar_concatena_e_exige_as_mesmas_classes():
    from fraus.corpora import Exemplos
    from fraus.receita_treino import juntar

    a = Exemplos(["x"], [0], ["g1"], ["n", "s"])
    b = Exemplos(["y", "z"], [1, 0], None, ["n", "s"])
    j = juntar(a, b)
    assert j.textos == ["x", "y", "z"] and j.rotulos == [0, 1, 0]
    assert j.grupos == ["g1", "", ""]
    with pytest.raises(ValueError):
        juntar(a, Exemplos(["w"], [0], None, ["outra", "ordem"]))
