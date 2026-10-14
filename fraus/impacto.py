"""Impacto de um tema no NPS inferido: NPS(tema) - NPS(resto do recorte), com IC.

Retrospectivo e em lote; marca, nao decide. E ASSOCIACAO, NAO CAUSA: um tema
pode andar junto com outro fator (canal, horario, produto) que e quem de fato
move a nota.

Ausencia nao vira zero (invariante 2): abaixo de `N_MINIMO_NPS` conversas com
sinal no tema OU no resto, a diferenca e `None` com motivo -- a mesma regra do
cartao de NPS. Conversa sem sinal fica fora da conta e e contada.

O IC e percentil 2,5-97,5 de bootstrap com reamostragem independente dos dois
lados, semente fixa. Captura so a incerteza AMOSTRAL, nunca a do modelo.
Spec: docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md
"""

import numpy as np

from fraus.indicadores import N_MINIMO_NPS, calcular_nps, categoria_nps

REAMOSTRAS = 1000
SEMENTE_IMPACTO = 20261014
ROTULO_IMPACTO = "associação, não causa"
MOTIVO_N_MINIMO = "n abaixo do mínimo"


def _proporcoes(scores, faixas) -> list[float]:
    # [promotor, neutro, detrator]; o NPS e 100 x (promotor - detrator).
    cats = [categoria_nps(s, faixas) for s in scores]
    n = len(cats)
    return [cats.count("promotor") / n, cats.count("neutro") / n, cats.count("detrator") / n]


def _nps_reamostrado(sorteio, proporcoes, n, reamostras) -> np.ndarray:
    contagens = sorteio.multinomial(n, proporcoes, size=reamostras)
    return 100.0 * (contagens[:, 0] - contagens[:, 2]) / n


def impacto_nps(scores_tema, scores_resto, faixas, reamostras=REAMOSTRAS,
                semente=SEMENTE_IMPACTO) -> dict:
    tema = [s for s in scores_tema if s is not None]
    resto = [s for s in scores_resto if s is not None]
    base = {"n_tema": len(tema), "n_resto": len(resto),
            "sem_sinal_tema": len(scores_tema) - len(tema),
            "minimo": N_MINIMO_NPS, "rotulo": ROTULO_IMPACTO}
    if len(tema) < N_MINIMO_NPS or len(resto) < N_MINIMO_NPS:
        return {**base, "impacto_nps": None, "ic_inferior": None, "ic_superior": None,
                "motivo": MOTIVO_N_MINIMO}
    impacto = round(calcular_nps(tema, faixas) - calcular_nps(resto, faixas), 2)
    # Contribuicoes so valem -1/0/+1: reamostrar n pontos e sortear (prom, neu, det)
    # de uma multinomial com as proporcoes observadas. Custo O(reamostras).
    sorteio = np.random.default_rng(semente)
    nps = [_nps_reamostrado(sorteio, _proporcoes(lado, faixas), len(lado), reamostras)
           for lado in (tema, resto)]
    inferior, superior = np.percentile(nps[0] - nps[1], [2.5, 97.5])
    return {**base, "impacto_nps": impacto, "ic_inferior": round(float(inferior), 2),
            "ic_superior": round(float(superior), 2), "motivo": None}
