"""Modelo canonico de conversa. Toda fonte de dado e normalizada para ca."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

Autor = Literal["cliente", "bot", "humano"]


class Mensagem(BaseModel):
    autor: Autor
    texto: str
    enviada_em: datetime

    @field_validator("enviada_em")
    @classmethod
    def _exige_timezone(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            raise ValueError("enviada_em precisa ser timezone-aware")
        return valor


class Conversa(BaseModel):
    id: str
    canal: str
    iniciada_em: datetime
    encerrada_em: datetime | None = None
    escalou_para_humano: bool = False
    mensagens: list[Mensagem]

    @property
    def mensagens_cliente(self) -> list[Mensagem]:
        return [m for m in self.mensagens if m.autor == "cliente"]

    @property
    def tem_sinal_cliente(self) -> bool:
        return len(self.mensagens_cliente) > 0
