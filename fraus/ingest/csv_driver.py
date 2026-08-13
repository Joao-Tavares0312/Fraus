"""Driver de ingestao CSV. Uma linha por mensagem, agrupada por conversa_id."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from fraus.modelos import Conversa, Mensagem

VERDADEIROS = {"true", "1", "sim", "yes"}


class LinhaRejeitada(BaseModel):
    numero_linha: int
    motivo: str


class ResultadoIngestao(BaseModel):
    conversas: list[Conversa]
    rejeitadas: list[LinhaRejeitada]


def carregar_csv(caminho: Path) -> ResultadoIngestao:
    """Le o CSV e devolve conversas validas mais o relato das linhas rejeitadas.

    Uma linha malformada nunca derruba o lote inteiro: ela e isolada com motivo.
    """
    por_conversa: dict[str, list[Mensagem]] = defaultdict(list)
    metadados: dict[str, dict] = {}
    rejeitadas: list[LinhaRejeitada] = []

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for numero_linha, linha in enumerate(leitor, start=2):
            try:
                enviada_em = datetime.fromisoformat(linha["enviada_em"])
                mensagem = Mensagem(
                    autor=linha["autor"],
                    texto=linha["texto"],
                    enviada_em=enviada_em,
                )
            except (ValueError, ValidationError) as erro:
                rejeitadas.append(LinhaRejeitada(numero_linha=numero_linha, motivo=str(erro)))
                continue

            conversa_id = linha["conversa_id"]
            por_conversa[conversa_id].append(mensagem)
            meta = metadados.setdefault(
                conversa_id, {"canal": linha["canal"], "escalou": False}
            )
            if linha["escalou_para_humano"].strip().lower() in VERDADEIROS:
                meta["escalou"] = True

    conversas = []
    for conversa_id, mensagens in por_conversa.items():
        mensagens.sort(key=lambda m: m.enviada_em)
        meta = metadados[conversa_id]
        conversas.append(
            Conversa(
                id=conversa_id,
                canal=meta["canal"],
                iniciada_em=mensagens[0].enviada_em,
                encerrada_em=mensagens[-1].enviada_em,
                escalou_para_humano=meta["escalou"],
                mensagens=mensagens,
            )
        )

    return ResultadoIngestao(conversas=conversas, rejeitadas=rejeitadas)
