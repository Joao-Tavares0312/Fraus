"""Driver de ingestao CSV. Uma linha por mensagem, agrupada por conversa_id.

O texto de cada mensagem passa por `censurar_pii` AQUI, na leitura, e nao
depois: esta e a segunda porta de entrada do sistema (a outra e
`fraus/api/registro.py`), e uma porta sem a censura torna a outra inutil.
"""

import csv
import io
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from fraus.modelos import Conversa, Mensagem
from fraus.seguranca.pii import censurar_pii

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


def _exigir(linha: dict, coluna: str, numero_linha: int) -> str:
    """O valor da coluna, recusando a linha que acabou antes dela.

    `linha[coluna]` levanta KeyError quando a coluna nao existe no cabecalho --
    e esse KeyError e deixado passar de proposito (ver o laco). O None e outra
    coisa: e a linha que terminou cedo, e vira ValueError porque e assim que
    este modulo rejeita UMA linha sem derrubar as outras.
    """
    valor = linha[coluna]
    if valor is None:
        raise ValueError(
            f"a linha {numero_linha} termina antes da coluna '{coluna}'"
        )
    return valor


def carregar_linhas(arquivo: Iterable[str]) -> ResultadoIngestao:
    """Nucleo compartilhado: agrupa mensagens por conversa e isola o que falhou."""
    por_conversa: dict[str, list[Mensagem]] = defaultdict(list)
    metadados: dict[str, dict] = {}
    rejeitadas: list[LinhaRejeitada] = []

    leitor = csv.DictReader(arquivo)
    for numero_linha, linha in enumerate(leitor, start=2):
        # KeyError NAO e capturado em lugar nenhum deste laco, de proposito:
        # coluna ausente no CABECALHO e defeito do ARQUIVO, nao da linha. Toda
        # linha estaria errada pelo mesmo motivo, e transformar isso em milhares
        # de rejeicoes individuais esconderia a causa unica. A API converte esse
        # KeyError num 400 que nomeia a coluna.
        #
        # Linha CURTA e o caso oposto, e por isso `_exigir` existe: o cabecalho
        # esta certo e so ESTA linha acabou cedo. O `DictReader` devolve None
        # para o que ela nao alcancou, e ate 03/09/2026 esse None seguia adiante
        # -- `fromisoformat(None)` levantava TypeError, que nao estava no except
        # nem nas bordas HTTP, e uma linha truncada derrubava o lote inteiro com
        # 500. Agora vira ValueError nomeando a coluna, que e a mesma rejeicao
        # por linha que uma data invalida ja recebia.
        try:
            mensagem = Mensagem(
                autor=_exigir(linha, "autor", numero_linha),
                texto=censurar_pii(_exigir(linha, "texto", numero_linha)),
                enviada_em=datetime.fromisoformat(
                    _exigir(linha, "enviada_em", numero_linha)
                ),
            )
            conversa_id = _exigir(linha, "conversa_id", numero_linha)
            canal = _exigir(linha, "canal", numero_linha)
            escalou = _exigir(linha, "escalou_para_humano", numero_linha)
        except (ValueError, ValidationError) as erro:
            rejeitadas.append(LinhaRejeitada(numero_linha=numero_linha, motivo=str(erro)))
            continue

        por_conversa[conversa_id].append(mensagem)
        meta = metadados.setdefault(conversa_id, {"canal": canal, "escalou": False})
        if escalou.strip().lower() in VERDADEIROS:
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
