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

NOTA_MINIMA = 0
NOTA_MAXIMA = 10


def nota_0_10(score_0_100: float) -> int:
    return int(round(max(0.0, min(100.0, score_0_100)) / 10))


def categoria_nps(
    score_0_100: float, faixas: dict[Categoria, tuple[int, int]] | None = None
) -> Categoria:
    """Categoria da nota segundo `faixas` -- por PARAMETRO, nunca global mutavel.

    Quando a configuracao muda as faixas, quem le passa as faixas vigentes; o
    default e o padrao de fabrica. Assim a faixa continua morando num lugar so
    e nao existe estado global que mude sob os pes de quem ja calculou.
    """
    if faixas is None:
        faixas = FAIXAS_NPS
    nota = nota_0_10(score_0_100)
    for categoria, (minima, maxima) in faixas.items():
        if minima <= nota <= maxima:
            return categoria
    raise ValueError(f"nota {nota} fora de qualquer faixa de NPS")


def validar_faixas_nps(faixas: dict[str, tuple[int, int]]) -> None:
    """Recusa faixa que nao cubra 0..10 de forma contigua, nomeando o problema.

    Faixa de NPS com buraco ou sobreposicao nao e preferencia de gosto: seria
    nota sem categoria (ou com duas), e o erro apareceria muito depois, na
    leitura de um atendimento qualquer. Levanta ValueError -- a borda HTTP
    traduz para 400 com a mesma frase.
    """
    faltando = [c for c in ("detrator", "neutro", "promotor") if c not in faixas]
    if faltando:
        raise ValueError(f"faixa de NPS ausente: {', '.join(faltando)}")
    sobrando = [c for c in faixas if c not in ("detrator", "neutro", "promotor")]
    if sobrando:
        raise ValueError(f"categoria de NPS desconhecida: {', '.join(sorted(sobrando))}")

    for categoria, (minima, maxima) in faixas.items():
        if minima > maxima:
            raise ValueError(
                f"faixa vazia em {categoria}: minima {minima} maior que maxima {maxima}"
            )

    ordenadas = sorted(faixas.items(), key=lambda item: item[1][0])
    primeira, (inicio, _) = ordenadas[0][0], ordenadas[0][1]
    if inicio != NOTA_MINIMA:
        raise ValueError(
            f"as faixas comecam em {inicio} na categoria {primeira}, "
            f"mas precisam comecar em {NOTA_MINIMA}"
        )
    ultima, (_, fim) = ordenadas[-1][0], ordenadas[-1][1]
    if fim != NOTA_MAXIMA:
        raise ValueError(
            f"as faixas terminam em {fim} na categoria {ultima}, "
            f"mas precisam terminar em {NOTA_MAXIMA}"
        )

    for (nome_anterior, (_, fim_anterior)), (nome, (inicio_atual, _)) in zip(
        ordenadas, ordenadas[1:]
    ):
        if inicio_atual <= fim_anterior:
            raise ValueError(
                f"a faixa {nome} sobrepoe {nome_anterior}: "
                f"{nome_anterior} vai ate {fim_anterior} e {nome} comeca em {inicio_atual}"
            )
        if inicio_atual > fim_anterior + 1:
            raise ValueError(
                f"buraco entre {nome_anterior} e {nome}: "
                f"nenhuma faixa cobre a nota {fim_anterior + 1}"
            )


def calcular_nps(
    scores: list[float], faixas: dict[Categoria, tuple[int, int]] | None = None
) -> float | None:
    """Percentual de promotores menos percentual de detratores, em [-100, 100].

    Sem score algum devolve None -- ausencia de dado nao e insatisfacao, e
    "NPS +0" seria apresentar como medido um numero que ninguem mediu.
    """
    if not scores:
        return None
    categorias = [categoria_nps(s, faixas) for s in scores]
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
