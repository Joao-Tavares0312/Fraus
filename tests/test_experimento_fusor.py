"""Contratos experimentais: identidade, isolamento e scaler sem acesso ao holdout."""
from __future__ import annotations

import copy
import csv
import json

import numpy as np
import pytest

from fraus.corpora import ler_b2w
from fraus.experimento_fusor import (
    SIMULACAO, avaliar_ablacao, carregar_cache, carregar_manifesto, conferir_saida,
    conferir_satisfacao, frases_por_lado, gerar_manifesto, hash_arquivo, hash_json,
    identidade_cache, matriz_ablacao, nomes_ablacao, treinar_ablacao,
)
from fraus.fusor import FEATURES_EM_LOG, NOMES_FEATURES, vetorizar
from fraus.generalizacao import LADOS, fingerprint_exemplos, hash_texto, identidade_grupo, recortar


def _csv(tmp_path, linhas=None):
    caminho = tmp_path / "b2w.csv"
    if linhas is None:
        # Cada produto tem as tres classes, sem depender da proporcao sorteada.
        linhas = [(f"produto-{p}", f"opiniao unica {p} classe {r}", nota, rec)
                  for p in range(60) for r, nota, rec in ((0, 1, "yes"), (1, 3, "no"), (2, 5, "no"))]
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["product_id", "review_text", "overall_rating", "recommend_to_a_friend"])
        escritor.writerows(linhas)
    return caminho


def _gravar(tmp_path, manifesto):
    caminho = tmp_path / "manifesto.json"
    caminho.write_text(json.dumps(manifesto), encoding="utf-8")
    return caminho


def _manifesto_manual(b2w, indices):
    exemplos = ler_b2w(b2w)
    return {"versao": 1, "fonte": {"sha256": hash_arquivo(b2w), "aceitos_leitor": len(exemplos.textos)},
            "lados": {lado: {
                "fingerprint_satisfacao": fingerprint_exemplos(recortar(exemplos, selecionados)),
                "registros": [{"indice_leitor": i, "hash_texto": hash_texto(exemplos.textos[i]),
                               "hash_grupo": identidade_grupo(exemplos, i),
                               "rotulo_satisfacao": exemplos.rotulos[i]} for i in selecionados],
            } for lado, selecionados in zip(LADOS, indices)}}


def test_manifesto_reproduz_split42_e_preserva_indices_aceitos(tmp_path):
    b2w = _csv(tmp_path)
    manifesto = gerar_manifesto(b2w)
    assert gerar_manifesto(b2w) == manifesto
    _, lados = carregar_manifesto(_gravar(tmp_path, manifesto), b2w)
    assert sum(len(ex.textos) for ex in lados.values()) == 180
    for a, b in (("treino", "validacao"), ("treino", "teste"), ("validacao", "teste")):
        assert not set(lados[a].grupos) & set(lados[b].grupos)
        assert not {hash_texto(t) for t in lados[a].textos} & {hash_texto(t) for t in lados[b].textos}


@pytest.mark.parametrize("colisao", ["produto", "texto"])
def test_manifesto_recusa_colisao_mesmo_com_fingerprints_validos(tmp_path, colisao):
    linhas = [("p1", "mesmo texto", 1, "no"),
              ("p1" if colisao == "produto" else "p2", "outro texto" if colisao == "produto" else " MESMO   TEXTO ", 1, "no"),
              ("p3", "terceiro", 5, "yes")]
    b2w = _csv(tmp_path, linhas)
    manifesto = _manifesto_manual(b2w, [[0], [1], [2]])
    with pytest.raises(ValueError, match="colisao de produto/texto"):
        carregar_manifesto(_gravar(tmp_path, manifesto), b2w)


def test_manifesto_recusa_fonte_modificada_e_indice_falso(tmp_path):
    b2w = _csv(tmp_path)
    manifesto = gerar_manifesto(b2w)
    adulterado = copy.deepcopy(manifesto)
    adulterado["lados"]["treino"]["registros"][0]["hash_texto"] = "falso"
    with pytest.raises(ValueError, match="registro do manifesto"):
        carregar_manifesto(_gravar(tmp_path, adulterado), b2w)
    with b2w.open("a", encoding="utf-8") as arquivo:
        arquivo.write("\n")
    with pytest.raises(ValueError, match="fonte do manifesto"):
        carregar_manifesto(_gravar(tmp_path, manifesto), b2w)


def test_satisfacao_exige_alinhamento_treino_validacao_teste(tmp_path):
    manifesto = gerar_manifesto(_csv(tmp_path))
    modelo = tmp_path / "modelo"
    modelo.mkdir()
    assert conferir_satisfacao(modelo, manifesto)["estado"] == "independencia_nao_verificavel"
    receita = {"manifesto_divisao": {lado: {"fingerprint": manifesto["lados"][lado]["fingerprint_satisfacao"]}
                                    for lado in LADOS}}
    caminho = modelo / "fraus_receita.json"
    caminho.write_text(json.dumps(receita), encoding="utf-8")
    assert conferir_satisfacao(modelo, manifesto)["estado"] == "alinhada_ao_manifesto"
    for lado in LADOS:
        errada = copy.deepcopy(receita)
        errada["manifesto_divisao"][lado]["fingerprint"] = "outro"
        caminho.write_text(json.dumps(errada), encoding="utf-8")
        with pytest.raises(ValueError, match=lado):
            conferir_satisfacao(modelo, manifesto)


def test_pools_usam_recomendacao_nao_estrelas_e_balanceiam_por_lado(tmp_path):
    b2w = _csv(tmp_path)
    manifesto = gerar_manifesto(b2w)
    _, lados = carregar_manifesto(_gravar(tmp_path, manifesto), b2w)
    frases, metadados = frases_por_lado(b2w, manifesto, lados)
    for lado in LADOS:
        assert all("classe 0" in t for t in frases[lado][2])  # nota1 mas yes => satisfeito
        assert all("classe 2" in t for t in frases[lado][0])  # nota5 mas no => insatisfeito
        assert all("classe 1" in t for t in frases[lado][1])
        assert len({len(pool) for pool in frases[lado].values()}) == 1
        assert metadados[lado]["frases_por_classe"] <= SIMULACAO[lado]["frases_por_classe"]


def _features(valor):
    return {nome: float(valor) for nome in NOMES_FEATURES}


def _identidade(tmp_path):
    texto, emocao = tmp_path / "texto", tmp_path / "emocao"
    for diretorio in (texto, emocao):
        diretorio.mkdir()
        (diretorio / "model.safetensors").write_bytes(b"pesos explicitos de teste")
        (diretorio / "tokenizer.json").write_text("{}", encoding="utf-8")
    return texto, emocao, identidade_cache({"versao": 1}, texto, emocao, backend="torch")


def _cache(tmp_path, identidade):
    dados = {"identidade": identidade, "identidade_sha256": hash_json(identidade)}
    for sufixo in ("t", "v", "e"):
        dados[f"x{sufixo}"] = [_features(v) for v in (1, 2, 3)]
        dados[f"y{sufixo}"] = [0, 1, 2]
    caminho = tmp_path / "cache.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


@pytest.mark.parametrize("mudanca", ["manifesto", "pesos", "tokenizador", "log1p", "simulador"])
def test_cache_recusa_identidade_divergente(tmp_path, mudanca):
    texto, emocao, identidade = _identidade(tmp_path)
    caminho = _cache(tmp_path, identidade)
    assert len(carregar_cache(caminho, identidade)["xv"]) == 3
    outra = copy.deepcopy(identidade)
    if mudanca in ("pesos", "tokenizador"):
        arquivo = "model.safetensors" if mudanca == "pesos" else "tokenizer.json"
        (texto / arquivo).write_bytes(b"alterado mantendo nome")
        outra = identidade_cache({"versao": 1}, texto, emocao, backend="torch")
    elif mudanca == "manifesto":
        outra = identidade_cache({"versao": 1, "outro": True}, texto, emocao, backend="torch")
    elif mudanca == "log1p":
        outra["features_em_log"] = []
    else:
        outra["simulacao"]["teste"]["semente"] += 1
    with pytest.raises(ValueError, match="cache divergente"):
        carregar_cache(caminho, outra)


def test_cache_posicional_antigo_e_recusado(tmp_path):
    caminho = tmp_path / "cache.json"
    caminho.write_text(json.dumps({"xt": [], "yt": [], "xe": [], "ye": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="cache divergente"):
        carregar_cache(caminho, {})


@pytest.mark.parametrize("variante,n", [("completo", 39), ("somente_texto", 4), ("somente_tempo", 7)])
def test_ablacao_remove_colunas_aplica_runtime_e_scaler_ve_so_treino(variante, n):
    xt = [_features(v) for v in (1, 2, 3, 4, 5, 6)]
    yt = [0, 1, 2, 0, 1, 2]
    pipeline = treinar_ablacao(xt, yt, variante=variante)
    nomes = nomes_ablacao(variante)
    matriz = matriz_ablacao(xt, nomes)
    assert matriz.shape == (6, n)
    assert pipeline.named_steps["escala"].n_features_in_ == n
    assert pipeline.named_steps["modelo"].coef_.shape[1] == n
    np.testing.assert_allclose(pipeline.named_steps["escala"].mean_, matriz.mean(axis=0))
    for j, nome in enumerate(nomes):
        esperado = np.log1p(1) if nome in FEATURES_EM_LOG else 1
        assert matriz[0, j] == pytest.approx(esperado)
    media = pipeline.named_steps["escala"].mean_.copy()
    aval = avaliar_ablacao(pipeline, [_features(10_000)] * 3, [0, 1, 2])
    np.testing.assert_array_equal(pipeline.named_steps["escala"].mean_, media)
    assert pipeline.named_steps["escala"].n_samples_seen_ == 6
    assert set(aval) >= {"por_classe", "matriz", "ece", "acuracia", "f1_macro"}
    if variante == "completo":
        np.testing.assert_allclose(matriz[0], vetorizar(xt[0]))


def test_saida_nao_pode_tocar_repositorio_ou_cabecas(tmp_path):
    from fraus.experimento_fusor import RAIZ
    modelo = tmp_path / "cabecas"
    for saida in (RAIZ / "modelos", modelo, modelo / "fusor", tmp_path):
        with pytest.raises(ValueError, match="externa"):
            conferir_saida(saida, [modelo])
    assert conferir_saida(tmp_path / "candidato", [modelo]) == tmp_path / "candidato"
