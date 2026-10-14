"""Confianca do score: conjunto conformal e abstencao, sobre o score GRAVADO.

Nada aqui altera score, nota ou categoria, e a conversa que se abstem continua
no NPS e no CSAT. Sem artefato calibrado para a regua vigente, 503 com o motivo.
"""

import math

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.motor_preguicoso import motor_e_real
from fraus.api.rotas.conversas import _exigir_regua_vigente
from fraus.conformal import METODO, ConformalIndisponivel, abstencao, conjunto

router = APIRouter()

ROTULOS = {0: "insatisfeito", 1: "neutro", 2: "satisfeito"}
METODO_AGREGADO = (
    f"{METODO}; só o critério do conjunto (vazio ou múltiplo) entra, sem passagem "
    "de modelo; o critério de deriva só existe no detalhe; IC 95% de Wilson")


def _artefato(ctx: Contexto) -> dict:
    try:
        return ctx.conformal_vigente()
    except ConformalIndisponivel as erro:
        raise HTTPException(503, str(erro)) from erro


def wilson(sucessos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para uma proporcao; `n` precisa ser positivo."""
    p = sucessos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centro - meia), min(1.0, centro + meia)


ORCAMENTO_CLIENTE = 40  # o mesmo de `exigir_orcamento` (E1)
MOTIVO_SEM_DERIVA = "acima do orçamento de 40 mensagens do cliente por leitura"


def _fora_da_faixa(ctx: Contexto, conversa) -> list[str] | None:
    if not motor_e_real(ctx.motor):
        return None
    resumo = ctx.motor.deriva_da_amostra([conversa], ctx.curadoria_vigente())
    if resumo is None:
        return None
    return [f["nome"] for f in resumo["features"] if f["dentro_da_faixa"] is False]


@router.get("/indicadores/confianca")
def confianca_do_recorte(de: str | None = None, ate: str | None = None,
                         canal: str | None = None,
                         ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Quantas conversas do recorte o conjunto conformal nao consegue cravar."""
    artefato = _artefato(ctx)
    registros = ctx.registros_do_recorte(de, ate)
    if canal is not None:
        registros = [r for r in registros if r[0].canal == canal]
    defasadas = ctx.banco.ids_defasadas(ctx.curadoria_vigente().versao, ctx.regua_vigente())
    com_score = [(c, s) for c, s in registros if s is not None]
    avaliaveis = [(c, s) for c, s in com_score if c.id not in defasadas]
    por_criterio = {"conjunto_vazio": 0, "conjunto_multiplo": 0}
    tamanhos = {"0": 0, "1": 0, "2": 0, "3": 0}
    for _, score in avaliaveis:
        conj = conjunto(score, artefato["limites"])
        tamanhos[str(min(len(conj), 3))] += 1
        criterio = abstencao(conj)
        if criterio:
            por_criterio[criterio] += 1
    n, abst = len(avaliaveis), sum(por_criterio.values())
    return {"recorte": {"de": de, "ate": ate, "canal": canal},
            "com_sinal": len(com_score), "defasadas": len(com_score) - n,
            "avaliadas": n, "abstencoes": abst,
            "fracao_abstencao": abst / n if n else None,
            "ic_fracao": list(wilson(abst, n)) if n else None,
            "por_criterio": por_criterio, "tamanho_conjunto": tamanhos,
            "alvo": artefato["alvo"], "garantia": artefato["garantia"],
            "metodo": METODO_AGREGADO}


@router.get("/conversas/{conversa_id:path}/confianca")
def confianca_da_conversa(conversa_id: str, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Conjunto conformal e criterios de abstencao desta conversa."""
    artefato = _artefato(ctx)
    achado = ctx.banco.buscar(conversa_id)
    if achado is None:
        raise HTTPException(404, "conversa nao encontrada")
    conversa, score = achado[0], achado[1]
    base = {"conversa_id": conversa_id, "score": score, "alvo": artefato["alvo"],
            "garantia": artefato["garantia"], "metodo": METODO}
    if score is None:
        return {**base, "conjunto": None, "rotulos_conjunto": None, "abstencao": None,
                "criterios": [], "features_fora_da_faixa": None,
                "deriva_nao_avaliada": False}
    _exigir_regua_vigente(ctx, conversa_id)
    conj = conjunto(score, artefato["limites"])
    criterios = [c for c in [abstencao(conj)] if c]
    extra: dict = {"deriva_nao_avaliada": False}
    if len(conversa.mensagens_cliente) > ORCAMENTO_CLIENTE:
        # Conversa longa: nao ha passagem de modelo sem orcamento. Nao e erro.
        fora = None
        extra = {"deriva_nao_avaliada": True, "motivo": MOTIVO_SEM_DERIVA}
    else:
        fora = _fora_da_faixa(ctx, conversa)
    if fora:
        criterios.append("deriva")
    return {**base, "conjunto": conj, "rotulos_conjunto": [ROTULOS[c] for c in conj],
            "abstencao": bool(criterios), "criterios": criterios,
            "features_fora_da_faixa": fora, **extra}
