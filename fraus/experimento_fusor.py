"""Manifesto e caches privados do experimento do fusor; nunca carrega o fusor ativo.

Schema do manifesto v1: fonte.sha256 identifica os bytes do CSV; cada lado
contem registros com indice_leitor (base zero entre exemplos aceitos por
ler_b2w), hash_texto normalizado, hash_grupo efetivo e rotulo_satisfacao.
O fingerprint_satisfacao usa o alvo de estrelas SOMENTE para conferir a
proveniencia da cabeca. O fusor usa recomendacao + nota 3, nunca esse alvo.
Gerar o manifesto ANTES do notebook 01; nao reconstruir historia dos pesos.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from fraus.corpora import CLASSES_SATISFACAO, ler_b2w, rotulo_por_estrelas
from fraus.fusor import (
    ESCALA_DO_TEMPO, FEATURES_EM_LOG, NOMES_FEATURES, familia_da_feature, vetorizar,
)
from fraus.generalizacao import (
    LADOS, dividir_auditavel, fingerprint_exemplos, hash_texto, identidade_grupo,
    recortar, sobreposicao,
)

RAIZ = Path(__file__).resolve().parent.parent
SIMULACAO = {
    "treino": {"quantidade": 900, "semente": 20260813, "frases_por_classe": 300},
    "validacao": {"quantidade": 120, "semente": 20261026, "frases_por_classe": 40},
    "teste": {"quantidade": 300, "semente": 999, "frases_por_classe": 100},
}
ROTULO_FUSOR = "recommend_to_a_friend (Yes/No); overall_rating == 3 tem precedencia neutra"


def hash_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def hash_json(dados: object) -> str:
    return hashlib.sha256(json.dumps(
        dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def gerar_manifesto(b2w: Path) -> dict:
    """Reserva os mesmos lados completos da cabeca, sem subamostrar o B2W."""
    exemplos = ler_b2w(b2w)
    lados, indices = dividir_auditavel(exemplos, agrupar=True)
    manifesto = {
        "versao": 1,
        "fonte": {"corpus": "B2W", "sha256": hash_arquivo(b2w),
                  "aceitos_leitor": len(exemplos.textos)},
        "divisao": {"semente": 42, "fracao_validacao": 0.10, "fracao_teste": 0.15,
                    "agrupamento": "produto; identidade textual sem produto; deduplicacao normalizada"},
        "lados": {
            lado: {
                "fingerprint_satisfacao": fingerprint_exemplos(lados[lado]),
                "registros": [
                    {"indice_leitor": i, "hash_texto": hash_texto(exemplos.textos[i]),
                     "hash_grupo": identidade_grupo(exemplos, i),
                     "rotulo_satisfacao": exemplos.rotulos[i]}
                    for i in indices[lado]
                ],
            } for lado in LADOS
        },
        "limite": "reserva prospectiva; nao comprova a divisao de checkpoints historicos",
    }
    _conferir_lados(lados)
    return manifesto


def _conferir_lados(lados: dict) -> None:
    for i, esquerda in enumerate(LADOS):
        if not lados[esquerda].textos:
            raise ValueError(f"lado vazio: {esquerda}")
        for direita in LADOS[i + 1:]:
            intersecao = sobreposicao(lados[esquerda], lados[direita])
            if intersecao["textos_normalizados"] or intersecao["grupos"]:
                raise ValueError(f"colisao de produto/texto entre {esquerda} e {direita}")


def carregar_manifesto(caminho: Path, b2w: Path) -> tuple[dict, dict]:
    """Confere bytes, indices aceitos, identidades, fingerprints e isolamento."""
    manifesto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if manifesto.get("versao") != 1 or manifesto.get("fonte", {}).get("sha256") != hash_arquivo(b2w):
        raise ValueError("fonte do manifesto divergente")
    exemplos = ler_b2w(b2w)
    if manifesto["fonte"]["aceitos_leitor"] != len(exemplos.textos):
        raise ValueError("contagem do leitor divergente")
    lados = {}
    usados: set[int] = set()
    for lado in LADOS:
        registros = manifesto["lados"][lado]["registros"]
        indices = []
        for registro in registros:
            i = registro["indice_leitor"]
            if type(i) is not int or not 0 <= i < len(exemplos.textos) or i in usados:
                raise ValueError("indice do leitor invalido ou repetido no manifesto")
            usados.add(i)
            esperado = {"indice_leitor": i, "hash_texto": hash_texto(exemplos.textos[i]),
                        "hash_grupo": identidade_grupo(exemplos, i),
                        "rotulo_satisfacao": exemplos.rotulos[i]}
            if registro != esperado:
                raise ValueError("registro do manifesto divergente")
            indices.append(i)
        lados[lado] = recortar(exemplos, indices)
        if fingerprint_exemplos(lados[lado]) != manifesto["lados"][lado]["fingerprint_satisfacao"]:
            raise ValueError("fingerprint de satisfacao divergente")
    _conferir_lados(lados)
    return manifesto, lados


def conferir_satisfacao(modelo: Path, manifesto: dict) -> dict:
    """Recusa receita divergente; ausencia historica nunca significa sem vazamento."""
    caminho = modelo / "fraus_receita.json"
    if not caminho.is_file():
        return {"estado": "independencia_nao_verificavel", "independence_unverifiable": True,
                "motivo": "receita historica ausente"}
    receita = json.loads(caminho.read_text(encoding="utf-8"))
    divisao = receita.get("manifesto_divisao", {})
    for lado in LADOS:
        fingerprint = divisao.get(lado, {}).get("fingerprint")
        if fingerprint and fingerprint != manifesto["lados"][lado]["fingerprint_satisfacao"]:
            raise ValueError(f"divisao supervisionada da satisfacao divergente: {lado}")
    if not all(divisao.get(lado, {}).get("fingerprint") for lado in LADOS):
        return {"estado": "independencia_nao_verificavel", "independence_unverifiable": True,
                "motivo": "manifestos historicos ausentes"}
    return {"estado": "alinhada_ao_manifesto", "independence_unverifiable": False,
            "receita_sha256": hash_arquivo(caminho),
            "fingerprints": {lado: divisao[lado]["fingerprint"] for lado in LADOS}}


def hash_checkpoint(diretorio: Path) -> str:
    """Bytes reais, nomes relativos e tokenizador; nao apenas nome do candidato."""
    if not diretorio.is_dir():
        raise ValueError(f"checkpoint ausente: {diretorio}")
    arquivos = sorted(p for p in diretorio.rglob("*") if p.is_file())
    if not arquivos:
        raise ValueError(f"checkpoint vazio: {diretorio}")
    return hash_json({p.relative_to(diretorio).as_posix(): hash_arquivo(p) for p in arquivos})


def identidade_cache(manifesto: dict, texto: Path, emocao: Path, *, backend: str) -> dict:
    """Inclui implementacao/lexicos: mesma lista de features nao garante mesmos valores."""
    fontes = [RAIZ / "fraus/fusor.py", RAIZ / "fraus/ingest/simulador.py",
              Path(__file__), RAIZ / "scripts/retreinar_fusor_local.py"]
    fontes += sorted((RAIZ / "fraus/sinais").glob("*.py"))
    fontes += sorted(p for p in (RAIZ / "fraus/dados").glob("*") if p.is_file())
    return {
        "versao": 1, "manifesto_sha256": hash_json(manifesto), "backend": backend,
        "checkpoints": {"satisfacao": hash_checkpoint(texto), "emocao": hash_checkpoint(emocao)},
        "features": list(NOMES_FEATURES), "features_em_log": list(FEATURES_EM_LOG),
        "escala_do_tempo": ESCALA_DO_TEMPO, "simulacao": SIMULACAO,
        "balanceamento": "menor classe por lado, RandomState(42), sem reposicao",
        "rotulo": ROTULO_FUSOR,
        "fontes_sha256": {p.relative_to(RAIZ).as_posix(): hash_arquivo(p) for p in fontes},
    }


def carregar_cache(caminho: Path, identidade: dict) -> dict:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if dados.get("identidade") != identidade or dados.get("identidade_sha256") != hash_json(identidade):
        raise ValueError("cache divergente: manifesto, checkpoint ou contrato mudou")
    for sufixo in ("t", "v", "e"):
        xs, ys = dados[f"x{sufixo}"], dados[f"y{sufixo}"]
        if not xs or len(xs) != len(ys) or set(ys) != {0, 1, 2}:
            raise ValueError("cache vazio ou rotulos invalidos")
        for linha in xs:
            if set(linha) != set(NOMES_FEATURES) or not np.isfinite(vetorizar(linha)).all():
                raise ValueError("features do cache divergentes ou nao finitas")
    return dados


def _recomendacoes(b2w: Path) -> list[int | None]:
    """Metadado ausente no leitor: mesma aceitacao de ler_b2w, conferida por indice.

    Nao escolhe divisao nem substitui ler_b2w: apenas associa recomendacao a
    cada exemplo aceito, inclusive None para recomendacao ausente/invalida.
    """
    rotulos = []
    with b2w.open(newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            if not (linha.get("review_text") or "").strip() or rotulo_por_estrelas(linha.get("overall_rating")) is None:
                continue
            rec = (linha.get("recommend_to_a_friend") or "").strip().lower()
            nota = int(linha["overall_rating"].strip())
            rotulos.append(None if rec not in ("yes", "no") else 1 if nota == 3 else 2 if rec == "yes" else 0)
    return rotulos


def frases_por_lado(b2w: Path, manifesto: dict, lados: dict) -> tuple[dict, dict]:
    recomendacoes = _recomendacoes(b2w)
    saida, metadados = {}, {}
    for lado in LADOS:
        registros = manifesto["lados"][lado]["registros"]
        pools = {r: [i for i, registro in enumerate(registros)
                     if recomendacoes[registro["indice_leitor"]] == r] for r in (0, 1, 2)}
        menor = min(map(len, pools.values()))
        if not menor:
            raise ValueError(f"classe de recomendacao ausente no lado {lado}")
        limite = min(menor, SIMULACAO[lado]["frases_por_classe"])
        escolhidos = {r: np.random.RandomState(42).choice(indices, limite, replace=False).tolist()
                      for r, indices in pools.items()}
        saida[lado] = {r: [lados[lado].textos[i] for i in indices] for r, indices in escolhidos.items()}
        metadados[lado] = {
            "aceitos_por_classe": {str(r): len(indices) for r, indices in pools.items()},
            "frases_por_classe": limite,
            "indices_leitor": {str(r): [registros[i]["indice_leitor"] for i in indices]
                               for r, indices in escolhidos.items()},
        }
    return saida, metadados


def nomes_ablacao(variante: str) -> list[str]:
    if variante == "completo":
        return list(NOMES_FEATURES)
    familia = {"somente_texto": "texto", "somente_tempo": "tempo"}[variante]
    return [nome for nome in NOMES_FEATURES if familia_da_feature(nome) == familia]


def matriz_ablacao(exemplos: list[dict], nomes: list[str]) -> np.ndarray:
    """Transforma com o runtime e REMOVE colunas; zero nao e ablacao."""
    indices = [NOMES_FEATURES.index(nome) for nome in nomes]
    return np.asarray([vetorizar(exemplo) for exemplo in exemplos], dtype=float)[:, indices]


def treinar_ablacao(xt: list[dict], yt: list[int], *, variante: str):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    nomes = nomes_ablacao(variante)
    pipeline = Pipeline([("escala", StandardScaler()),
                         ("modelo", LogisticRegression(max_iter=1000, random_state=42))])
    pipeline.fit(matriz_ablacao(xt, nomes), yt)
    pipeline.fraus_escala_do_tempo = ESCALA_DO_TEMPO
    pipeline.fraus_nomes_features = nomes
    return pipeline


def avaliar_ablacao(pipeline, exemplos: list[dict], rotulos: list[int]) -> dict:
    from fraus.receita_treino import metricas_completas

    probs = pipeline.predict_proba(matriz_ablacao(exemplos, pipeline.fraus_nomes_features))
    classes = list(pipeline.named_steps["modelo"].classes_)
    ordenadas = [[float(p[classes.index(r)]) for r in (0, 1, 2)] for p in probs]
    return metricas_completas(ordenadas, rotulos, nomes_classes=CLASSES_SATISFACAO)


def conferir_saida(saida: Path, modelos: list[Path]) -> Path:
    destino = saida.resolve()
    proibidos = [RAIZ, *(m.resolve() for m in modelos)]
    if any(destino == raiz or destino.is_relative_to(raiz) or raiz.is_relative_to(destino)
           for raiz in proibidos):
        raise ValueError("--saida deve ser externa ao repositorio e aos checkpoints de entrada")
    return destino
