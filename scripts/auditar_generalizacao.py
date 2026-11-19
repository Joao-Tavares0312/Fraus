"""Audita corpus, splits reconstruidos e proveniencia local, sem treinar ou inferir.

    uv run python scripts/auditar_generalizacao.py --corpora ~/.cache/fraus/corpora \
        --modelos modelos --saida /tmp/fraus-overfitting-20261026/auditoria.json

O JSON agregado e o manifesto privado adjacente NAO contem texto bruto.
Hashes calculados agora nao comprovam a origem historica de um checkpoint.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

from fraus import corpora  # noqa: E402
from fraus.generalizacao import (  # noqa: E402
    LADOS, dividir_auditavel, hash_texto, identidade_grupo, isolar_treino_auxiliar,
    indexar_sobreposicao, recortar, resumo_conjunto, sobreposicao,
)
from fraus.receita_treino import remover_duplicatas  # noqa: E402


LIMITACOES = [
    "Indices do manifesto sao posicoes aceitas pelos leitores, nao linhas brutas; "
    "votos de GoEmotions/MultiPICo ja foram agregados.",
    "Hashes e splits reconstruidos hoje nao demonstram a origem historica dos pesos. "
    "Sem manifesto supervisionado historico verificavel: independencia nao verificavel.",
    "Grupos ausentes usam identidade textual; nao demonstram isolamento de autores, "
    "produtos ou posts desconhecidos.",
    "ConsumerBR usa agrupar=False, como o benchmark: empresas grandes impedem o split "
    "agrupado da receita. Empresas podem atravessar lados; nao ha independencia por empresa.",
    "Satisfacao por estrelas e recomendacao/neutro do fusor sao alvos diferentes; "
    "seus rotulos nao sao comparados como se fossem o mesmo alvo.",
    "ConsumerBR e XED ja foram consultados como benchmarks de transferencia; nao sao teste virgem.",
    "A auditoria nao mede overfitting: sem curvas comparaveis nao ha diagnostico de sobreajuste.",
    "Pools posicionais do fusor sao reconstruidos, nao as conversas sinteticas sorteadas; "
    "grupos e textos dos pools podem se repetir no sistema e nao provam independencia das cabecas.",
]


def sha256_arquivo(caminho: Path) -> str:
    with caminho.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def _arquivo(caminho: Path) -> dict:
    return {"caminho": str(caminho), "bytes": caminho.stat().st_size,
            "sha256": sha256_arquivo(caminho)}


def _inventariar_modelos(raiz: Path) -> dict:
    arquivos = [_arquivo(p) for p in sorted(raiz.rglob("*")) if p.is_file()]
    receitas = []
    for arquivo in arquivos:
        caminho = Path(arquivo["caminho"])
        if caminho.name != "fraus_receita.json":
            continue
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            if not isinstance(dados, dict):
                raise ValueError("receita nao e um objeto")
            receitas.append({
                "caminho": str(caminho), "sha256": arquivo["sha256"],
                "impressao_teste_declarada": dados.get("impressao_teste"),
                "manifesto_divisao_presente": "manifesto_divisao" in dados,
                "independencia": "nao verificavel: declaracao local sem cadeia de proveniencia",
            })
        except (ValueError, UnicodeError) as erro:
            receitas.append({"caminho": str(caminho), "erro": str(erro)})
    return {
        "arquivos": arquivos, "receitas": receitas,
        "desserializacao": "nenhuma; pesos, pickle e joblib apenas hasheados",
        "independencia_supervisionada_historica": "nao verificavel",
    }


def _ler_corpora(raiz: Path) -> tuple[dict, dict]:
    arquivos = {
        "b2w": [raiz / "b2w/B2W-Reviews01.csv"],
        "consumerbr": [raiz / "consumerbr/ConsumerBR.zip"],
        "goemotions": [*[raiz / f"goemotions/goemotions_{i}_pt.csv" for i in (1, 2, 3)],
                       raiz / "goemotions/ekman_mapping.json"],
        "xed": [raiz / "xed/pt-projections.tsv"],
        "multipico": [raiz / "multipico/multipico_anonimized.csv"],
    }
    faltantes = [str(p) for lista in arquivos.values() for p in lista if not p.is_file()]
    if faltantes:
        raise FileNotFoundError("corpora ausentes: " + ", ".join(faltantes))
    mapa = json.loads(arquivos["goemotions"][-1].read_text(encoding="utf-8"))
    exemplos = {
        "b2w": corpora.ler_b2w(arquivos["b2w"][0]),
        "consumerbr": corpora.ler_consumerbr(arquivos["consumerbr"][0]),
        "goemotions": corpora.ler_goemotions_ptbr(arquivos["goemotions"][:-1], mapa),
        "xed": corpora.ler_xed_pt(arquivos["xed"][0]),
        "multipico": corpora.ler_multipico(arquivos["multipico"][0]),
    }
    return exemplos, arquivos


def fatias_posicionais_fusor(caminho: Path) -> tuple[dict, dict, dict]:
    """Reconstroi pools do script local, sem importar motor nem ler pickle.

    O alvo exige a coluna adicional de recomendacao que ler_b2w nao devolve.
    O parse do alvo fica aqui; satisfacao continua usando o leitor canonico.
    RandomState.choice reproduz sample(random_state=42) sem depender de pandas.
    """
    textos, rotulos, grupos, linhas = [], [], [], []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        for indice, linha in enumerate(csv.DictReader(arquivo)):
            texto = linha.get("review_text") or ""
            nota = corpora.rotulo_por_estrelas(linha.get("overall_rating"))
            recomenda = (linha.get("recommend_to_a_friend") or "").strip().lower()
            if not texto or nota is None or recomenda not in ("yes", "no"):
                continue
            textos.append(texto)
            rotulos.append(1 if nota == 1 else (2 if recomenda == "yes" else 0))
            grupos.append((linha.get("product_id") or "").strip())
            linhas.append(indice)
    if not rotulos:
        raise ValueError("B2W sem recomendacoes elegiveis para o fusor")
    contagens = {r: rotulos.count(r) for r in (0, 1, 2)}
    menor = min(contagens.values())
    if menor < 400:
        raise ValueError("B2W precisa de 400 exemplos por classe para reconstruir pools do fusor")
    balanceados = []
    for r in (0, 1, 2):
        candidatos = [i for i, rotulo in enumerate(rotulos) if rotulo == r]
        posicoes = np.random.RandomState(42).choice(len(candidatos), size=menor, replace=False)
        balanceados.extend(candidatos[int(i)] for i in posicoes)
    permutacao = np.random.RandomState(42).choice(len(balanceados), size=len(balanceados), replace=False)
    balanceados = [balanceados[int(i)] for i in permutacao]
    completo = corpora.Exemplos(textos=textos, rotulos=rotulos, grupos=grupos,
                               nomes_classes=list(corpora.CLASSES_SATISFACAO))
    pools, indices = {}, {}
    for lado, inicio, fim in (("treino", 0, 300), ("teste", 300, 400)):
        escolhidos = []
        for r in (0, 1, 2):
            classe = [i for i in balanceados if rotulos[i] == r][inicio:fim]
            escolhidos.extend(i for i in classe if textos[i].strip())
        pools[lado] = recortar(completo, escolhidos)
        pools[lado].textos = [t.strip() for t in pools[lado].textos]
        indices[lado] = [linhas[i] for i in escolhidos]
    return pools, indices, {
        "elegiveis": len(rotulos), "contagens_antes_balanceamento": contagens,
        "por_classe_balanceada": menor, "semente_balanceamento": 42,
        "fatias_por_classe": {"treino": [0, 300], "teste": [300, 400]},
        "unidade_indice": "posicao de registro CSV original, cabecalho excluido",
        "ressalva_parse": "alvo com notas validas 1..5; tokens NA literais do pandas nao sao "
        "reclassificados aqui. Reconstrucao da regra, nao prova do pool historico.",
    }


def _gravar_linhas(arquivo, corpus: str, tarefa: str, exemplos, indices: dict) -> None:
    lado_por_indice = {i: lado for lado, lista in indices.items() for i in lista}
    dedup = remover_duplicatas(exemplos.textos, exemplos.rotulos)
    unicos = set(dedup.indices)
    for i, (texto, rotulo) in enumerate(zip(exemplos.textos, exemplos.rotulos)):
        registro = {
            "corpus": corpus, "tarefa": tarefa, "indice_leitor": i,
            "lado": lado_por_indice.get(i, "excluido_duplicata_ou_conflito"),
            "sobrevive_deduplicacao": i in unicos, "hash_texto": hash_texto(texto),
            "rotulo": int(rotulo), "grupo": identidade_grupo(exemplos, i),
        }
        arquivo.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")


def auditar(*, caminho_corpora: Path, caminho_modelos: Path, saida: Path) -> dict:
    """Grava apenas saidas externas aos dados/modelos, com manifesto privado 0600."""
    caminho_corpora, caminho_modelos, saida = (
        p.resolve() for p in (caminho_corpora, caminho_modelos, saida)
    )
    manifesto = saida.with_name(saida.stem + ".manifesto.jsonl")
    if not caminho_modelos.is_dir():
        raise FileNotFoundError(f"diretorio de modelos ausente: {caminho_modelos}")
    for destino in (saida, manifesto.resolve()):
        if any(destino.is_relative_to(p) for p in (caminho_corpora, caminho_modelos)):
            raise ValueError("saida nao pode alterar corpora ou modelos")
    exemplos, fontes = _ler_corpora(caminho_corpora)
    tarefas = {"b2w": "satisfacao_estrelas", "consumerbr": "satisfacao_estrelas",
               "goemotions": "emocao", "xed": "emocao", "multipico": "ironia"}
    dominios = {"b2w": "produto_b2w", "consumerbr": "empresa_consumerbr",
                "goemotions": "autor_reddit", "xed": "texto_xed", "multipico": "post_multipico"}
    relatorio = {
        "versao": 1, "emitido_em": datetime.now(timezone.utc).isoformat(),
        "corpora": {}, "artefatos": _inventariar_modelos(caminho_modelos),
        "divisoes": {}, "sobreposicoes": [], "limitacoes": list(LIMITACOES),
        "codigo": [_arquivo(Path(__file__).resolve()), _arquivo(RAIZ / "fraus/generalizacao.py"),
                   _arquivo(RAIZ / "fraus/receita_treino.py"), _arquivo(RAIZ / "fraus/corpora.py")],
    }
    conjuntos, lados_por_corpus = {}, {}
    saida.parent.mkdir(parents=True, exist_ok=True)
    # Mesmo que o arquivo ja exista, nunca deixa hashes/indices privados world-readable.
    descritor = os.open(manifesto, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descritor, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as privado:
        for nome, ex in exemplos.items():
            print(f"Auditando {nome}: {len(ex.textos)} exemplos aceitos", flush=True)
            relatorio["corpora"][nome] = {
                "tarefa": tarefas[nome], "fontes": [_arquivo(p) for p in fontes[nome]],
                **resumo_conjunto(ex),
            }
            conjuntos[nome + "/aceitos"] = (nome, ex)
            if nome == "xed":
                # Benchmark integral externo: nao inventar um split de treino XED.
                indices = {"benchmark_integral": list(range(len(ex.textos)))}
                relatorio["divisoes"][nome] = {"tipo": "benchmark_integral", "lados": {
                    "benchmark_integral": resumo_conjunto(ex)}}
            else:
                fracoes = corpora.FRACOES_MULTIPICO if nome == "multipico" else {}
                lados, indices = dividir_auditavel(ex, agrupar=nome != "consumerbr", **fracoes)
                lados_por_corpus[nome] = lados
                relatorio["divisoes"][nome] = {
                    "tipo": "reconstrucao_receita_atual", "semente": 42,
                    "agrupar": nome != "consumerbr",
                    "fracoes_solicitadas": {"treino": 0.60 if nome == "multipico" else 0.75,
                                             "validacao": 0.15 if nome == "multipico" else 0.10,
                                             "teste": 0.25 if nome == "multipico" else 0.15},
                    "lados": {lado: resumo_conjunto(lados[lado]) for lado in LADOS},
                }
                for lado in LADOS:
                    conjuntos[nome + "/" + lado] = (nome, lados[lado])
            _gravar_linhas(privado, nome, tarefas[nome], ex, indices)
        pools, indices_fusor, regra = fatias_posicionais_fusor(fontes["b2w"][0])
        tarefas["fusor"] = "recomendacao_neutro"
        dominios["fusor"] = "produto_b2w"
        relatorio["divisoes"]["fusor_posicional"] = {
            "tipo": "reconstrucao_pools_posicionais_nao_conversas", **regra,
            "lados": {lado: resumo_conjunto(ex) for lado, ex in pools.items()},
            "independencia_das_cabecas": "nao verificavel sem manifesto historico de treino",
        }
        for lado, ex in pools.items():
            conjuntos["fusor/" + lado] = ("fusor", ex)
            for i, indice in enumerate(indices_fusor[lado]):
                privado.write(json.dumps({
                    "corpus": "b2w_fusor", "tarefa": tarefas["fusor"], "indice_csv": indice,
                    "lado": lado, "hash_texto": hash_texto(ex.textos[i]),
                    "rotulo": ex.rotulos[i], "grupo": identidade_grupo(ex, i),
                }, sort_keys=True) + "\n")
        # Simulacao de isolamento, nao alteracao do corpus nem recomendacao de
        # acrescentar ConsumerBR a campanha fechada de satisfacao.
        principal = lados_por_corpus["b2w"]
        isolamento = isolar_treino_auxiliar(
            lados_por_corpus["consumerbr"]["treino"], **principal, comparar_grupos=False,
        )
        relatorio["isolamento_auxiliar_demonstrativo"] = {
            "auxiliar": "consumerbr/treino", "principal": "b2w", "aplicado_ao_treino": False,
            "grupos_comparaveis": False, "exclusoes": isolamento.exclusoes,
            "resultado": resumo_conjunto(isolamento.exemplos),
        }
        for indice in isolamento.indices:
            auxiliar = lados_por_corpus["consumerbr"]["treino"]
            privado.write(json.dumps({"corpus": "consumerbr", "tarefa": tarefas["consumerbr"],
                "indice_no_treino_reconstruido": indice,
                "lado": "auxiliar_isolado_demonstrativo",
                "hash_texto": hash_texto(auxiliar.textos[indice]),
                "rotulo": auxiliar.rotulos[indice],
                "grupo": identidade_grupo(auxiliar, indice)}, sort_keys=True) + "\n")
    print("Comparando intersecoes normalizadas", flush=True)
    indexados = {
        nome: (corpus, indexar_sobreposicao(ex)) for nome, (corpus, ex) in conjuntos.items()
    }
    for (nome_a, (corpus_a, a)), (nome_b, (corpus_b, b)) in combinations(indexados.items(), 2):
        # Aceitos contem seus proprios lados: essa inclusao trivial nao e vazamento.
        if corpus_a == corpus_b and (nome_a.endswith("/aceitos") or nome_b.endswith("/aceitos")):
            continue
        relatorio["sobreposicoes"].append({
            "esquerda": nome_a, "direita": nome_b,
            **sobreposicao(a, b, comparar_rotulos=tarefas[corpus_a] == tarefas[corpus_b],
                           comparar_grupos=dominios[corpus_a] == dominios[corpus_b]),
        })
    relatorio["manifesto_privado"] = {**_arquivo(manifesto), "formato": "JSONL", "permissoes": "0600",
        "conteudo": "indices, hashes normalizados, rotulos e grupos; sem texto bruto"}
    saida.write_text(json.dumps(relatorio, ensure_ascii=False, sort_keys=True, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")
    return relatorio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpora", type=Path, required=True)
    parser.add_argument("--modelos", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    auditar(caminho_corpora=args.corpora, caminho_modelos=args.modelos, saida=args.saida)
    print(f"Auditoria: {args.saida}; manifesto privado adjacente. Nenhum modelo carregado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
