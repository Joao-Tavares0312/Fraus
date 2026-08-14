"""Driver de ingestao CSV. Uma linha por mensagem, agrupada por conversa_id."""

import csv
import io
from collections import defaultdict
from collections.abc import Iterable
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
    """Le o CSV do disco. Uma linha malformada nunca derruba o lote inteiro."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return carregar_linhas(arquivo)


def carregar_texto(conteudo: str) -> ResultadoIngestao:
    """Mesma leitura, a partir do CONTEUDO do CSV em vez de um caminho.

    Existe para a analise avulsa: o arquivo chega no corpo da requisicao, e
    interpretado em memoria e nunca toca o disco. E por isso que ela nao viola
    a decisao que recusa upload na tela de Integracoes -- ali o problema era
    abrir superficie de ESCRITA numa API sem autenticacao; aqui nada e gravado,
    nem no banco nem em arquivo.

    A regra de leitura e literalmente a mesma funcao de `carregar_csv`: um
    segundo parser para o mesmo formato acabaria aceitando coisas diferentes
    das que a importacao aceita, e a analise avulsa passaria a discordar do que
    entra no banco.
    """
    return carregar_linhas(io.StringIO(conteudo, newline=""))


def carregar_linhas(arquivo: Iterable[str]) -> ResultadoIngestao:
    """Nucleo compartilhado: agrupa mensagens por conversa e isola o que falhou."""
    por_conversa: dict[str, list[Mensagem]] = defaultdict(list)
    metadados: dict[str, dict] = {}
    rejeitadas: list[LinhaRejeitada] = []

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

        # KeyError aqui NAO e capturado, de proposito: coluna ausente e defeito
        # do ARQUIVO, nao da linha. Toda linha estaria errada pelo mesmo motivo,
        # e transformar isso em milhares de rejeicoes individuais esconderia a
        # causa unica. A API converte esse KeyError num 400 que nomeia a coluna.
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
