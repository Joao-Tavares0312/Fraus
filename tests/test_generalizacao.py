"""Contratos de isolamento e evidencia; nenhum teste carrega os pesos do Fraus."""
import csv
import io
import json
import zipfile
from dataclasses import replace

import pytest

from fraus.corpora import Exemplos
from fraus.generalizacao import (
    conferir_holdout, dividir_auditavel, fingerprint_exemplos, hash_texto,
    identidade_grupo, isolar_treino_auxiliar, resumo_conjunto, sobreposicao,
)
from scripts.auditar_generalizacao import auditar, fatias_posicionais_fusor


def _ex(textos, rotulos=None, grupos=None):
    return Exemplos(textos=list(textos), rotulos=list(rotulos or [0] * len(textos)),
                    grupos=grupos, nomes_classes=["negativo", "neutro", "positivo"])


def test_hash_normaliza_caixa_espacos_e_unicode():
    assert hash_texto("  Café\n BOM ") == hash_texto("cafe\u0301 bom")
    assert hash_texto("café bom") != hash_texto("café ruim")


def test_fingerprint_inclui_rotulo_grupo_classes_e_multiplicidade():
    a = _ex([" Café ", "outro"], [0, 1], ["autor", ""])
    b = _ex(["OUTRO", "cafe\u0301"], [1, 0], ["", "autor"])
    assert fingerprint_exemplos(a) == fingerprint_exemplos(b)
    assert fingerprint_exemplos(a) != fingerprint_exemplos(replace(a, rotulos=[2, 1]))
    assert fingerprint_exemplos(a) != fingerprint_exemplos(replace(a, grupos=["outro", ""]))
    assert fingerprint_exemplos(a) != fingerprint_exemplos(replace(a, nomes_classes=["x", "y", "z"]))
    assert fingerprint_exemplos(a) != fingerprint_exemplos(
        _ex([" Café ", "outro", "outro"], [0, 1, 1], ["autor", "", ""]))


@pytest.mark.parametrize("alteracoes", [{"rotulos": [0, 1, 2]}, {"grupos": ["um"]}])
def test_fingerprint_recusa_registros_truncados(alteracoes):
    with pytest.raises(ValueError, match="tamanhos divergentes"):
        fingerprint_exemplos(replace(_ex(["um", "dois"]), **alteracoes))


def test_identidade_textual_nao_colide_com_identificador_real():
    sem = _ex(["frase"])
    real = _ex(["frase"], grupos=[identidade_grupo(sem, 0)])
    assert identidade_grupo(sem, 0).startswith("texto:")
    assert identidade_grupo(real, 0).startswith("grupo:")
    assert identidade_grupo(sem, 0) != identidade_grupo(real, 0)
    assert identidade_grupo(_ex(["frase"], grupos=["  "]), 0) == identidade_grupo(sem, 0)


def test_auxiliar_exclui_texto_normalizado_grupo_conflito_e_duplicata():
    treino = _ex(["conflitante"], [0], ["treino"])
    validacao = _ex(["Cafe\u0301 bom"], [2], ["produto-v"])
    teste = _ex(["teste intocado"], [1], ["produto-t"])
    auxiliar = _ex(
        [" CAFÉ   BOM ", "outra resposta", "CONFLITANTE", "livre", " LIVRE ", "novo"],
        [2, 0, 2, 1, 1, 0], ["distinto", "produto-t", "distinto", "a", "b", "c"],
    )
    antes = [fingerprint_exemplos(ex) for ex in (treino, validacao, teste)]
    resultado = isolar_treino_auxiliar(auxiliar, treino=treino, validacao=validacao, teste=teste)
    assert resultado.indices == [3, 5]
    assert resultado.exemplos.textos == ["livre", "novo"]
    assert resultado.exclusoes == {
        "conflito_rotulo": 1, "texto_holdout": 1, "grupo_holdout": 1,
        "duplicata_treino_principal": 0, "duplicata": 1,
    }
    assert [fingerprint_exemplos(ex) for ex in (treino, validacao, teste)] == antes


def test_conflito_interno_auxiliar_exclui_todas_as_ocorrencias():
    resultado = isolar_treino_auxiliar(
        _ex(["igual", " IGUAL ", "livre"], [0, 2, 1]),
        treino=_ex(["treino"]), validacao=_ex(["validacao"]), teste=_ex(["teste"]),
    )
    assert resultado.indices == [2]
    assert resultado.exclusoes["conflito_rotulo"] == 2


def test_auxiliar_nao_duplica_texto_ja_presente_no_treino_principal():
    resultado = isolar_treino_auxiliar(
        _ex([" MESMO  TEXTO ", "outro"], [0, 1]), treino=_ex(["mesmo texto"]),
        validacao=_ex(["validacao"]), teste=_ex(["teste"]),
    )
    assert resultado.indices == [1]
    assert resultado.exclusoes["duplicata_treino_principal"] == 1


@pytest.mark.parametrize("validacao,teste", [
    (_ex(["mesma frase"]), _ex([" MESMA  FRASE "])),
    (_ex(["primeira"], grupos=["autor"]), _ex(["segunda"], grupos=["autor"])),
])
def test_colisao_validacao_teste_bloqueia_novo_treino(validacao, teste):
    with pytest.raises(ValueError, match="colisao entre validacao e teste"):
        conferir_holdout(validacao, teste)
    with pytest.raises(ValueError, match="novo treino bloqueado"):
        isolar_treino_auxiliar(_ex(["auxiliar"]), treino=_ex(["treino"]),
                              validacao=validacao, teste=teste, comparar_grupos=False)


def test_alvos_diferentes_nao_comparam_inteiros_como_mesma_classe():
    resultado = sobreposicao(_ex(["igual"], [0]), _ex(["igual"], [2]),
                             comparar_rotulos=False, comparar_grupos=False)
    assert resultado["textos_normalizados"] == 1
    assert resultado["textos_com_rotulos_conflitantes"] is None
    assert resultado["grupos"] is None
    with pytest.raises(ValueError, match="mesmo contrato"):
        isolar_treino_auxiliar(replace(_ex(["aux"]), nomes_classes=["ironia"]),
                              treino=_ex(["t"]), validacao=_ex(["v"]), teste=_ex(["e"]))


def test_grupos_de_dominios_distintos_nao_excluem_auxiliar_por_acaso():
    resultado = isolar_treino_auxiliar(
        _ex(["auxiliar"], grupos=["42"]), treino=_ex(["treino"], grupos=["1"]),
        validacao=_ex(["validacao"], grupos=["42"]), teste=_ex(["teste"], grupos=["99"]),
        comparar_grupos=False,
    )
    assert resultado.indices == [0]


def _corpus_agrupado(prefixo, quantidade=300):
    return _ex([f"{prefixo} {grupo} classe {classe}" for grupo in range(quantidade) for classe in range(3)],
               [classe for _ in range(quantidade) for classe in range(3)],
               [str(grupo) for grupo in range(quantidade) for _ in range(3)])


def test_divisao_reutiliza_split_42_sem_autor_produto_ou_post_entre_lados():
    ex = _corpus_agrupado("grupo")
    lados, indices = dividir_auditavel(ex)
    repetidos, outros_indices = dividir_auditavel(ex)
    assert indices == outros_indices
    assert sorted(i for lado in indices.values() for i in lado) == list(range(len(ex.textos)))
    for lado in lados:
        assert fingerprint_exemplos(lados[lado]) == fingerprint_exemplos(repetidos[lado])
        assert lados[lado].textos == [ex.textos[i] for i in indices[lado]]
    for a, b in (("treino", "validacao"), ("treino", "teste"), ("validacao", "teste")):
        assert sobreposicao(lados[a], lados[b])["grupos"] == 0
        assert sobreposicao(lados[a], lados[b])["textos_normalizados"] == 0


def test_contagens_separam_duplicata_e_conflito():
    resumo = resumo_conjunto(_ex(["a", " A ", "b", "B", "c"], [0, 0, 1, 2, 2]))
    assert resumo["aceitos"] == 5
    assert resumo["apos_deduplicacao"] == 2
    assert resumo["duplicatas_excluidas"] == 1
    assert resumo["linhas_conflitantes_excluidas"] == 2
    assert resumo["grupos"]["sem_identificador"] == 5


def _csv(caminho, campos, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def _cache_minimo(raiz):
    # Cada produto/autor/post tem todas as classes: split agrupado equilibrado.
    _csv(raiz / "b2w/B2W-Reviews01.csv",
         ["review_text", "overall_rating", "product_id", "recommend_to_a_friend"],
         [{"review_text": f"b2w privado {g} {c}", "overall_rating": [1, 3, 5][c],
           "product_id": str(g), "recommend_to_a_friend": "No" if c == 0 else "Yes"}
          for g in range(600) for c in range(3)])
    memoria = io.StringIO()
    escritor = csv.DictWriter(memoria, fieldnames=["avaliacao_comentario", "avaliacao_nota", "empresa"])
    escritor.writeheader()
    escritor.writerows({"avaliacao_comentario": f"consumer privado {g} {c}",
                        "avaliacao_nota": f"Nota {[1, 3, 5][c]}", "empresa": "empresa unica"}
                       for g in range(300) for c in range(3))
    (raiz / "consumerbr").mkdir()
    with zipfile.ZipFile(raiz / "consumerbr/ConsumerBR.zip", "w") as pacote:
        pacote.writestr("ConsumerBR.csv", memoria.getvalue())
    mapa = {nome: [nome] for nome in ("anger", "disgust", "fear", "joy", "sadness", "surprise")}
    classes = [*mapa, "neutral"]
    campos = ["id", "texto", "author", "example_very_unclear", *classes]
    linhas = [{"id": f"{g}-{c}", "texto": f"go privado {g} {c}", "author": str(g),
               "example_very_unclear": "false", **{nome: int(nome == c) for nome in classes}}
              for g in range(100) for c in classes for _ in range(2)]
    for i in (1, 2, 3):
        _csv(raiz / f"goemotions/goemotions_{i}_pt.csv", campos, linhas if i == 1 else [])
    (raiz / "goemotions/ekman_mapping.json").write_text(json.dumps(mapa), encoding="utf-8")
    (raiz / "xed").mkdir()
    (raiz / "xed/pt-projections.tsv").write_text("xed privado\t1\n", encoding="utf-8")
    _csv(raiz / "multipico/multipico_anonimized.csv",
         ["post_id", "reply_id", "reply", "label", "language"],
         [{"post_id": str(g), "reply_id": str(c), "reply": f"mp privado {g} {c}",
           "label": c, "language": "pt"} for g in range(100) for c in range(2)])


def test_auditoria_completa_hashes_manifesto_privado_e_alvos_separados(tmp_path):
    cache, modelos, saida = tmp_path / "cache", tmp_path / "modelos", tmp_path / "saida/auditoria.json"
    _cache_minimo(cache)
    modelos.mkdir()
    # Falharia caso algum caminho tentasse desserializar isto como pickle.
    (modelos / "fusor.joblib").write_bytes(b"nao e um pickle")
    (modelos / "fraus_receita.json").write_text(json.dumps({"impressao_teste": "historico"}))
    resultado = auditar(caminho_corpora=cache, caminho_modelos=modelos, saida=saida)
    assert resultado["versao"] == 1
    assert set(resultado["corpora"]) == {"b2w", "consumerbr", "goemotions", "xed", "multipico"}
    assert resultado["divisoes"]["consumerbr"]["agrupar"] is False
    assert resultado["divisoes"]["xed"]["tipo"] == "benchmark_integral"
    assert resultado["divisoes"]["multipico"]["fracoes_solicitadas"] == {
        "treino": 0.60, "validacao": 0.15, "teste": 0.25}
    assert resultado["artefatos"]["independencia_supervisionada_historica"] == "nao verificavel"
    assert len(resultado["artefatos"]["arquivos"]) == 2
    assert all(len(a["sha256"]) == 64 for a in resultado["artefatos"]["arquivos"])
    privado = saida.with_name("auditoria.manifesto.jsonl")
    assert privado.stat().st_mode & 0o777 == 0o600
    registros = [json.loads(linha) for linha in privado.read_text().splitlines()]
    assert any(r.get("indice_leitor") == 0 and r["corpus"] == "b2w" for r in registros)
    assert all("texto" not in r for r in registros)
    assert "b2w privado" not in privado.read_text()
    assert "b2w privado" not in saida.read_text()
    fusor_b2w = [r for r in resultado["sobreposicoes"]
                 if "fusor/" in r["esquerda"] + r["direita"]
                 and "b2w/" in r["esquerda"] + r["direita"]]
    assert fusor_b2w
    assert all(not r["rotulos_comparaveis"] for r in fusor_b2w)
    pools, indices, regra = fatias_posicionais_fusor(cache / "b2w/B2W-Reviews01.csv")
    assert regra["por_classe_balanceada"] == 600
    assert len(pools["treino"].textos) == 900
    assert len(pools["teste"].textos) == 300
    assert set(indices["treino"]).isdisjoint(indices["teste"])
    assert indices == fatias_posicionais_fusor(cache / "b2w/B2W-Reviews01.csv")[1]
    with pytest.raises(ValueError, match="alterar corpora ou modelos"):
        auditar(caminho_corpora=cache, caminho_modelos=modelos, saida=modelos / "auditoria.json")
