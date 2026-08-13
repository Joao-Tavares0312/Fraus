"""Indicadores agregados.

NPS aqui e INFERIDO do texto, nao declarado pelo cliente. A dashboard rotula
como estimativa -- apresentar como NPS declarado seria falso.

Faixas canonicas: 0-6 detrator, 7-8 neutro, 9-10 promotor.
Categoria SEMPRE derivada no servidor.
"""

from typing import Literal

from fraus.modelos import Conversa

Categoria = Literal["detrator", "neutro", "promotor"]
NOTA_MINIMA_SATISFEITO = 7

# Fonte UNICA das faixas de NPS: qualquer lugar que precise das faixas (a API,
# a dashboard) le daqui -- nunca digita os numeros 0, 6, 7, 8, 9, 10 de novo.
FAIXAS_NPS: dict[Categoria, tuple[int, int]] = {
    "detrator": (0, 6),
    "neutro": (7, 8),
    "promotor": (9, 10),
}


def nota_0_10(score_0_100: float) -> int:
    return int(round(max(0.0, min(100.0, score_0_100)) / 10))


def categoria_nps(score_0_100: float) -> Categoria:
    nota = nota_0_10(score_0_100)
    for categoria, (minima, maxima) in FAIXAS_NPS.items():
        if minima <= nota <= maxima:
            return categoria
    raise ValueError(f"nota {nota} fora de qualquer faixa de FAIXAS_NPS")


def calcular_nps(scores: list[float]) -> float | None:
    """Percentual de promotores menos percentual de detratores, em [-100, 100].

    Sem score algum devolve None -- ausencia de dado nao e insatisfacao, e
    "NPS +0" seria apresentar como medido um numero que ninguem mediu.
    """
    if not scores:
        return None
    categorias = [categoria_nps(s) for s in scores]
    total = len(categorias)
    promotores = categorias.count("promotor") / total
    detratores = categorias.count("detrator") / total
    return round(100.0 * (promotores - detratores), 2)


def calcular_csat(scores: list[float]) -> float | None:
    """Percentual de atendimentos com nota >= 7. Sem score algum devolve None."""
    if not scores:
        return None
    satisfeitos = sum(1 for s in scores if nota_0_10(s) >= NOTA_MINIMA_SATISFEITO)
    return round(100.0 * satisfeitos / len(scores), 2)


def containment_rate(conversas: list[Conversa]) -> float:
    """Percentual de conversas resolvidas sem intervencao humana."""
    if not conversas:
        return 0.0
    contidas = sum(1 for c in conversas if not c.escalou_para_humano)
    return round(100.0 * contidas / len(conversas), 2)
