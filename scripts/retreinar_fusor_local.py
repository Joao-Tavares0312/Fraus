"""Experimento candidato do fusor: manifesto prospectivo, tres ablacões, sem promocao.

Primeiro reserve B2W ANTES de treinar a cabeca de satisfacao:
    python scripts/retreinar_fusor_local.py --b2w /dados/B2W.csv \
        --manifesto /tmp/experimento/manifesto.json --gerar-manifesto
Depois passe esse manifesto ao notebook 01 (FRAUS_MANIFESTO_FUSOR).
Somente apos exportar os candidatos das cabecas:
    python scripts/retreinar_fusor_local.py --b2w /dados/B2W.csv \
        --manifesto /tmp/experimento/manifesto.json --modelos /tmp/cabecas \
        --cache /tmp/experimento/features.json --saida /tmp/experimento/candidato

Schema privado v1 documentado em fraus.experimento_fusor. O manifesto usa
indices aceitos por ler_b2w, hashes de fonte/texto/grupo e fingerprints dos
lados completos. Cache antigo sem identidade e recusado, nao migrado por nome.
Nenhum fusor ativo e lido ou escrito. A avaliacao e sintetica, nao evidencia
em atendimentos reais. Proveniencia historica ausente continua nao verificavel.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.experimento_fusor import (  # noqa: E402
    ROTULO_FUSOR, SIMULACAO, avaliar_ablacao, carregar_cache, carregar_manifesto,
    conferir_saida, conferir_satisfacao, frases_por_lado, gerar_manifesto,
    hash_json, identidade_cache, treinar_ablacao,
)
from fraus.fusor import ESCALA_DO_TEMPO, Fusor, montar_features  # noqa: E402
from fraus.generalizacao import LADOS  # noqa: E402
from fraus.ingest.simulador import gerar_lote  # noqa: E402


def _gravar(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _extrair(b2w: Path, manifesto: dict, lados: dict, texto: Path, emocao: Path,
             *, backend: str, identidade: dict) -> dict:
    if backend == "torch":
        from fraus.sinais.emocao import ClassificadorEmocao
        from fraus.sinais.texto import ClassificadorTexto
        classificador = ClassificadorTexto(texto)
        classificador_emocao = ClassificadorEmocao(emocao)
    else:
        from fraus.sinais.onnx import ClassificadorOnnx
        classificador = ClassificadorOnnx(texto)
        classificador_emocao = ClassificadorOnnx(emocao)
    frases, metadados = frases_por_lado(b2w, manifesto, lados)
    dados = {"identidade": identidade, "identidade_sha256": hash_json(identidade),
             "pools": metadados}
    for lado, sufixo in zip(LADOS, ("t", "v", "e")):
        config = SIMULACAO[lado]
        lote = gerar_lote(frases[lado], quantidade=config["quantidade"], semente=config["semente"])
        dados[f"x{sufixo}"] = [montar_features(c, classificador, classificador_emocao) for c, _ in lote]
        dados[f"y{sufixo}"] = [r for _, r in lote]
    return dados


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--b2w", type=Path, required=True, help="CSV local exato; bytes conferidos pelo manifesto")
    ap.add_argument("--manifesto", type=Path, required=True)
    ap.add_argument("--gerar-manifesto", action="store_true", help="reserva split42 antes do treino; nao faz inferencia")
    ap.add_argument("--modelos", type=Path, help="raiz explicita contendo bertimbau-satisfacao e bertimbau-emocao")
    ap.add_argument("--modelo-texto", type=Path, help="checkpoint candidato de satisfacao (sobrepoe --modelos)")
    ap.add_argument("--modelo-emocao", type=Path, help="checkpoint candidato de emocao (sobrepoe --modelos)")
    ap.add_argument("--backend", choices=("torch", "onnx"), default="torch")
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--saida", type=Path, help="diretorio externo ao repositorio e checkpoints; nunca modelos ativos")
    args = ap.parse_args(argv)
    if args.gerar_manifesto:
        if args.manifesto.exists():
            ap.error("manifesto ja existe; nao sobrescrever uma reserva congelada")
        manifesto = gerar_manifesto(args.b2w)
        _gravar(args.manifesto, manifesto)
        print(f"manifesto reservado: {args.manifesto}; sha256 canonico {hash_json(manifesto)}")
        return 0
    if args.cache is None or args.saida is None:
        ap.error("treino exige --cache e --saida")
    texto = args.modelo_texto or (args.modelos / "bertimbau-satisfacao" if args.modelos else None)
    emocao = args.modelo_emocao or (args.modelos / "bertimbau-emocao" if args.modelos else None)
    if texto is None or emocao is None:
        ap.error("declare --modelos ou ambos --modelo-texto e --modelo-emocao")
    saida = conferir_saida(args.saida, [texto, emocao])
    conferir_saida(args.cache, [texto, emocao])
    manifesto, lados = carregar_manifesto(args.manifesto, args.b2w)
    proveniencia = {
        "satisfacao": conferir_satisfacao(texto, manifesto),
        "emocao": {"estado": "independencia_nao_verificavel", "independence_unverifiable": True,
                   "motivo": "fingerprint agregado de outro corpus nao comprova ausencia de sobreposicao textual com B2W"},
    }
    identidade = identidade_cache(manifesto, texto, emocao, backend=args.backend)
    if args.cache.exists():
        dados = carregar_cache(args.cache, identidade)
    else:
        dados = _extrair(args.b2w, manifesto, lados, texto, emocao,
                         backend=args.backend, identidade=identidade)
        _gravar(args.cache, dados)
        dados = carregar_cache(args.cache, identidade)
    # Congelar antes de qualquer leitura de metricas de teste; nao ha selecao por teste.
    selecao = {"versao": 1, "manifesto_sha256": hash_json(manifesto),
               "cache_identidade_sha256": hash_json(identidade),
               "variantes": ["completo", "somente_texto", "somente_tempo"],
               "modelo": "LogisticRegression", "max_iter": 1000, "random_state": 42,
               "scaler": "StandardScaler ajustado somente no treino", "selecao": "configuracao fixa; nenhuma busca"}
    _gravar(saida / "configuracao_congelada.json", selecao)
    relatorio = {
        "versao": 1, "configuracao": selecao, "proveniencia": proveniencia,
        "teste_independente_sistema": False,
        "independence_unverifiable": True,
        "limites": ["conversas e tempos sinteticos; nao valida atendimentos reais rotulados",
                    "sem manifesto historico individual de todas as cabecas, independencia do sistema nao verificavel",
                    "novo candidato nao constitui campanha Colab executada nem promove modelo"],
        "rotulo": ROTULO_FUSOR, "escala_do_tempo": ESCALA_DO_TEMPO,
        "pools": dados["pools"], "ablacoes": {},
    }
    import joblib
    for variante in selecao["variantes"]:
        pipeline = treinar_ablacao(dados["xt"], dados["yt"], variante=variante)
        validacao = avaliar_ablacao(pipeline, dados["xv"], dados["yv"])
        teste = avaliar_ablacao(pipeline, dados["xe"], dados["ye"])
        relatorio["ablacoes"][variante] = {
            "features": pipeline.fraus_nomes_features, "validacao": validacao, "teste": teste,
        }
        if variante == "completo":
            fusor = Fusor()
            fusor._pipeline = pipeline
            fusor.salvar(saida / "fusor.joblib")
            _gravar(saida / "importancias.json", {
                "importancias": fusor.importancias(), "acuracia": teste["acuracia"],
                "f1_macro": teste["f1_macro"], "rotulo": ROTULO_FUSOR,
                "escala_do_tempo": ESCALA_DO_TEMPO, "candidato": True,
                "conversas_treino": len(dados["yt"]), "conversas_validacao": len(dados["yv"]),
                "conversas_teste": len(dados["ye"]), "teste_independente_sistema": False,
            })
        else:
            # Artefatos experimentais com matriz reduzida: nao sao Fusor de runtime.
            joblib.dump(pipeline, saida / f"ablacao-{variante}.joblib")
    _gravar(saida / "metricas.json", relatorio)
    _gravar(saida / "manifesto.json", manifesto)
    print(f"candidato externo salvo em {saida}; independencia do sistema NAO comprovada; sem promocao")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
