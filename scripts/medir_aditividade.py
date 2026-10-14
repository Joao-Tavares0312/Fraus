"""Mede se a decomposicao do fusor SOMA de verdade, e quanto custa explicar.

A explicacao do E1 afirma que intercepto + contribuicoes = logit e que o score
sai dos logits. Esta afirmacao e numerica, entao tem de ser medida com o fusor
REAL, e nao apenas com o sintetico dos testes. O que este script verifica: o
maior erro de score e de logit sobre 90 conversas do simulador, nada alem disso.

O que ele faz:

1. gera 90 conversas do simulador (semente fixa) e monta as features com o
   motor real;
2. mede o maior |decompor(f)["score"] - pontuar(f)| e o maior
   |logit - log(p_c / p_ref)| (sobre predict_proba);
3. mede o tempo medio de `atribuir_conversa` (que ja traz a explicacao).

Falha ALTO: fusor ausente ou incompativel levanta o erro do carregador
(invariante 7). Nao ha fusor sintetico de reserva -- medir a aditividade num
artefato que nao e o de producao seria medir outra coisa. Nao escreve nada.

Como rodar:
    uv run python scripts/medir_aditividade.py
    FRAUS_BACKEND=onnx uv run python scripts/medir_aditividade.py

Os classificadores saem de `montar_classificadores(backend_declarado())`, o
mesmo caminho da API, entao `FRAUS_BACKEND` vale aqui como la.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.fusor import Fusor, vetorizar  # noqa: E402

SEMENTE = 20261014
QUANTIDADE = 90


def medir_aditividade(fusor: Fusor, lote_de_features: list[dict[str, float]]) -> dict:
    """Maiores erros de aditividade do `lote_de_features`. Parte pura: sem disco, sem modelo."""
    pipeline = fusor._pipeline
    classes = [int(c) for c in pipeline.named_steps["modelo"].classes_]
    erro_score = 0.0
    erro_logit = 0.0
    for features in lote_de_features:
        decomposicao = fusor.decompor(features)
        erro_score = max(erro_score, abs(decomposicao["score"] - fusor.pontuar(features)))
        probabilidades = dict(zip(classes, pipeline.predict_proba([vetorizar(features)])[0]))
        referencia = decomposicao["referencia"]
        for eixo in decomposicao["eixos"]:
            esperado = math.log(probabilidades[eixo["classe"]] / probabilidades[referencia])
            soma = eixo["intercepto"] + sum(eixo["contribuicoes"].values())
            erro_logit = max(erro_logit, abs(eixo["logit"] - esperado), abs(soma - eixo["logit"]))
    return {"conversas": len(lote_de_features), "erro_score": erro_score, "erro_logit": erro_logit}


def carregar_fusor(caminho: Path) -> Fusor:
    """Sem fallback: ausente ou incompativel propaga o erro do carregador."""
    return Fusor.carregar(caminho)


def medir_no_motor_real(caminho_fusor: Path) -> dict:
    from fraus.api.caminhos import backend_declarado
    from fraus.api.main import montar_classificadores
    from fraus.fusor import montar_features
    from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
    from fraus.motor import Motor

    fusor = carregar_fusor(caminho_fusor)  # primeiro: falha antes de gastar tempo com modelos
    texto, emocao, ironia = montar_classificadores(backend_declarado())
    motor = Motor(texto, fusor, emocao, ironia)
    conversas = [c for c, _ in gerar_lote(FRASES_POR_ROTULO, QUANTIDADE, SEMENTE) if c.tem_sinal_cliente]
    resultado = medir_aditividade(fusor, [montar_features(c, texto, emocao) for c in conversas])
    inicio = time.perf_counter()
    for c in conversas:
        motor.atribuir_conversa(c)
    resultado["ms_por_atribuicao"] = 1000 * (time.perf_counter() - inicio) / len(conversas)
    return resultado


def main(argv: list[str] | None = None) -> int:
    from fraus.api.caminhos import CAMINHO_FUSOR

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fusor", type=Path, default=CAMINHO_FUSOR, help="artefato do fusor")
    argumentos = parser.parse_args(argv)
    resultado = medir_no_motor_real(argumentos.fusor)
    print(f"{resultado['conversas']} conversas do simulador, semente {SEMENTE}")
    print(f"maior erro de score:  {resultado['erro_score']:.3e}")
    print(f"maior erro de logit:  {resultado['erro_logit']:.3e}")
    print(f"tempo por atribuicao: {resultado['ms_por_atribuicao']:.1f} ms (com explicacao)")
    return 0 if resultado["erro_score"] < 1e-9 and resultado["erro_logit"] < 1e-9 else 1


if __name__ == "__main__":
    sys.exit(main())
