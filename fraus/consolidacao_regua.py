"""Da anotacao as cegas a regua congelada. Parte pura.

Regra de entrada (spec, secao 3): o rotulo humano de uma frase e a maioria
simples das respostas; empate, maioria "contexto" ou menos de dois anotadores
deixam a frase ambigua. Um par so entra se OS DOIS lados tem rotulo humano
igual ao pretendido. O resto e descartado COM MOTIVO -- e dado publicado.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from fraus.avaliacao_ironia import FraseDoRascunho
from fraus.sinais.ironia import IRONICO

RESPOSTAS = ("ironico", "nao_ironico", "contexto")
_ROTULO_DA_RESPOSTA = {"ironico": IRONICO, "nao_ironico": 1 - IRONICO}


def ultimas_respostas(registros: Sequence[dict]) -> dict[str, list[str]]:
    ultima: dict[tuple[str, str], dict] = {}
    for registro in registros:
        if registro["resposta"] not in RESPOSTAS:
            raise ValueError(f"resposta desconhecida: {registro['resposta']!r}")
        chave = (registro["anotador"], registro["frase_id"])
        if chave not in ultima or registro["instante"] > ultima[chave]["instante"]:
            ultima[chave] = registro
    por_frase: dict[str, list[str]] = {}
    for (_, frase_id), registro in ultima.items():
        por_frase.setdefault(frase_id, []).append(registro["resposta"])
    return por_frase


def fleiss_kappa(contagens: Sequence[Sequence[int]]) -> float:
    totais = {sum(linha) for linha in contagens}
    if len(totais) != 1 or 0 in totais:
        raise ValueError("todo item precisa do mesmo numero (positivo) de anotadores")
    n = totais.pop()
    itens = len(contagens)
    p_itens = [(sum(c * c for c in linha) - n) / (n * (n - 1)) for linha in contagens]
    p_medio = sum(p_itens) / itens
    proporcoes = [sum(linha[j] for linha in contagens) / (itens * n) for j in range(len(contagens[0]))]
    p_acaso = sum(p * p for p in proporcoes)
    return (p_medio - p_acaso) / (1 - p_acaso) if p_acaso < 1 else 1.0


def rotulo_humano(respostas: Sequence[str], *, minimo: int = 2) -> int | None:
    if len(respostas) < minimo:
        return None
    ranking = Counter(respostas).most_common()
    if len(ranking) > 1 and ranking[0][1] == ranking[1][1]:
        return None
    return _ROTULO_DA_RESPOSTA.get(ranking[0][0])


def decidir_pares(
    frases: Sequence[FraseDoRascunho],
    respostas: dict[str, list[str]],
    *,
    minimo_pares: int = 100,
) -> tuple[list[dict], list[dict]]:
    por_par: dict[str, list[FraseDoRascunho]] = {}
    for frase in frases:
        por_par.setdefault(frase.par_id, []).append(frase)
    mantidas, descartadas = [], []
    for par_id in sorted(por_par):
        lados = por_par[par_id]
        motivos = {}
        for frase in lados:
            humano = rotulo_humano(respostas.get(frase.frase_id, []))
            if humano is None:
                motivos[frase.frase_id] = "ambigua"
            elif humano != frase.rotulo:
                motivos[frase.frase_id] = "divergente"
        for frase in lados:
            dados = respostas.get(frase.frase_id, [])
            if motivos:
                descartadas.append({
                    "par_id": par_id, "estrato": frase.estrato, "rotulo": frase.rotulo,
                    "texto": frase.texto,
                    "motivo": motivos.get(frase.frase_id, "par_incompleto"),
                    "respostas": "|".join(sorted(dados)),
                })
            else:
                alvo = "ironico" if frase.rotulo == IRONICO else "nao_ironico"
                mantidas.append({
                    "par_id": par_id, "estrato": frase.estrato, "texto": frase.texto,
                    "rotulo": frase.rotulo, "concordancia": dados.count(alvo) / len(dados),
                })
    pares = len({m["par_id"] for m in mantidas})
    if pares < minimo_pares:
        raise ValueError(f"a anotacao confirmou {pares} pares; o piso e {minimo_pares}")
    return mantidas, descartadas
