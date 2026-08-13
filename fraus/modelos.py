"""Modelo canonico de conversa. Toda fonte de dado e normalizada para ca."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Autor = Literal["cliente", "bot", "humano"]


def _exige_timezone(valor: datetime) -> datetime:
    """Valida que datetime é timezone-aware. Rejeita datetime naive."""
    if valor.tzinfo is None:
        raise ValueError("timestamp precisa ser timezone-aware")
    return valor


class Mensagem(BaseModel):
    autor: Autor
    texto: str
    enviada_em: datetime

    @field_validator("enviada_em")
    @classmethod
    def _valida_enviada_em(cls, valor: datetime) -> datetime:
        return _exige_timezone(valor)


class Conversa(BaseModel):
    id: str
    canal: str
    iniciada_em: datetime
    encerrada_em: datetime | None = None
    escalou_para_humano: bool = False
    mensagens: list[Mensagem] = Field(min_length=1)

    @field_validator("iniciada_em")
    @classmethod
    def _valida_iniciada_em(cls, valor: datetime) -> datetime:
        return _exige_timezone(valor)

    @field_validator("encerrada_em")
    @classmethod
    def _valida_encerrada_em(cls, valor: datetime | None) -> datetime | None:
        if valor is not None:
            return _exige_timezone(valor)
        return valor

    @property
    def mensagens_cliente(self) -> list[Mensagem]:
        return [m for m in self.mensagens if m.autor == "cliente"]

    @property
    def tem_sinal_cliente(self) -> bool:
        return len(self.mensagens_cliente) > 0
