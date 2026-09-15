"""Contratos de ENTRADA da API -- o que o cliente pode mandar.

Nenhum deles aceita veredito: score, nota e categoria sao derivados no
servidor em toda entrada, e um campo de entrada que os aceitasse seria a
porta para o cliente escolher a propria nota.
"""

from datetime import datetime
from typing import Literal

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
    # Ausente = nao mexe; null = a fonte deixa de nomear variavel. A diferenca
    # sai de `model_fields_set`, porque os dois chegam como None no atributo.
    variavel_segredo: str | None = None


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


class PedidoPreviaImportacao(BaseModel):
    """A previa NAO grava, entao pode receber o ajuste de colunas em teste.

    A importacao em si continua aceitando so `caminho`: o mapeamento que vale
    para gravar e o do perfil salvo, nunca um que chegue no corpo.
    """

    caminho: str
    mapeamento: dict[str, str | None] | None = None
    ordem_data: str | None = None


class PedidoCadastro(BaseModel):
    nome: str = Field(min_length=1)
    # Validacao minima e honesta: um @ com algo dos dois lados. EmailStr do
    # Pydantic exigiria a dependencia email-validator para pegar um punhado a
    # mais de casos -- e quem digita o proprio e-mail errado nao entra depois,
    # o que ja e o custo natural do erro.
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    senha: str = Field(min_length=8)
    codigo_dev: str | None = None  # o que diferencia o cadastro de dev


class PedidoEntrada(BaseModel):
    email: str
    senha: str


class PedidoSimulacao(BaseModel):
    texto: str  # unico campo aceito: probabilidade e derivada no servidor


class PedidoAnalise(BaseModel):
    csv: str  # conteudo do arquivo; veredito continua sendo derivado aqui
    nome: str | None = None  # so para escolher o leitor pela extensao


class PedidoChaveAcesso(BaseModel):
    nome: str = Field(min_length=1)


class PedidoPerfilMapeamento(BaseModel):
    """So nomes de coluna e papeis. Sem campo de conteudo, sem campo de nota."""

    nome: str = Field(min_length=1, max_length=80)
    colunas: list[str] = Field(min_length=1, max_length=200)
    papeis: dict[str, str | None]
    ordem_data: str | None = None


class PedidoCurado(BaseModel):
    """Entrada de `POST /lexico/curado`.

    NENHUM campo de veredito -- invariante 3. O analista diz o que a PALAVRA
    vale para o lexico; o score continua saindo do fusor. Campo extra que o
    cliente mande e ignorado pelo pydantic, e e por isso que este modelo e a
    fronteira e nao um dicionario cru.
    """

    tipo: Literal["palavra", "emoji"]
    termo: str = Field(min_length=1, max_length=64)
    peso: float
    motivo: str | None = Field(default=None, max_length=280)


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
