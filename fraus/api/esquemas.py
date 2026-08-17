"""Contratos de ENTRADA da API -- o que o cliente pode mandar.

Nenhum deles aceita veredito: score, nota e categoria sao derivados no
servidor em toda entrada, e um campo de entrada que os aceitasse seria a
porta para o cliente escolher a propria nota.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from fraus.modelos import Mensagem

# Tipos de fonte que a ingestao de fato sabe tratar hoje. Aceitar um tipo que
# nenhum adapter le seria cadastrar uma promessa: a tela mostraria uma fonte
# que nunca traz conversa nenhuma.
TIPOS_DE_FONTE = ("csv", "webhook")


class PedidoFonte(BaseModel):
    nome: str
    canal: str
    tipo: str
    variavel_segredo: str | None = None  # NOME da variavel, nunca o segredo


class PedidoAjusteFonte(BaseModel):
    nome: str | None = None
    ativa: bool | None = None


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


class PedidoSimulacao(BaseModel):
    texto: str  # unico campo aceito: probabilidade e derivada no servidor


class PedidoAnalise(BaseModel):
    csv: str  # conteudo do arquivo; veredito continua sendo derivado aqui
    nome: str | None = None  # so para escolher o leitor pela extensao


class PedidoChaveAcesso(BaseModel):
    nome: str = Field(min_length=1)


class PedidoIngestao(BaseModel):
    """Atendimento vindo de um sistema externo.

    NAO ha campo de canal, score, nota nem categoria. O canal vem da FONTE
    cadastrada e o veredito e derivado no servidor -- quem manda o dado nunca
    escolhe como ele e contabilizado.
    """

    id: str
    mensagens: list[Mensagem] = Field(min_length=1)
    encerrada_em: datetime | None = None
    escalou_para_humano: bool = False
