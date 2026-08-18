"""Recorte de periodo das rotas de leitura -- `de` e `ate`, pontas INCLUSIVAS.

Data malformada e 400 que NOMEIA o parametro, nunca filtro descartado em
silencio: um recorte ignorado devolveria a serie inteira parecendo o recorte
pedido, e o grafico mentiria sem nenhum sinal de erro.

As tres funcoes sao puras -- nao sabem que existe banco nem motor. Viviam
dentro de `criar_app` so por vizinhanca, nao por dependencia.
"""

from datetime import date, datetime

from fastapi import HTTPException


def dia_ou_400(valor: str | None, nome: str) -> date | None:
    """AAAA-MM-DD, ou 400 nomeando o parametro -- nunca ignorado em silencio.

    Filtro de periodo malformado que e descartado sem aviso devolveria a
    serie INTEIRA parecendo o recorte pedido, e o grafico mentiria sem
    nenhum sinal de erro.
    """
    if valor is None:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"{nome} invalido: esperava AAAA-MM-DD, veio {valor!r}",
        )


def recorte_ou_400(de: str | None, ate: str | None) -> tuple[date | None, date | None]:
    """As duas pontas do recorte, validadas juntas -- inclusive a ordem."""
    inicio, fim = dia_ou_400(de, "de"), dia_ou_400(ate, "ate")
    if inicio and fim and inicio > fim:
        raise HTTPException(
            status_code=400,
            detail=f"periodo invertido: de {inicio} vem depois de ate {fim}",
        )
    return inicio, fim


def no_recorte(iniciada_em: datetime, inicio: date | None, fim: date | None) -> bool:
    dia = iniciada_em.date()
    return (inicio is None or dia >= inicio) and (fim is None or dia <= fim)
