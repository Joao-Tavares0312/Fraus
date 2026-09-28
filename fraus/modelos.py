"""Modelo canonico de conversa. Toda fonte de dado e normalizada para ca."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from fraus.cortesia import e_so_cortesia

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
    # Rotulo declarado pelo proprio cliente na fonte (ex.: Resolveu/nao
    # resolveu do Tars). Nunca move o score: serve para validar a inferencia.
    feedback_declarado: Literal[-1, 1] | None = None
    comentario_feedback: str | None = None
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
    def tem_fala_cliente(self) -> bool:
        """O cliente escreveu alguma coisa -- e o que importa para a OPERACAO."""
        return len(self.mensagens_cliente) > 0

    @property
    def tem_sinal_cliente(self) -> bool:
        """Ha fala do cliente que diga algo sobre satisfacao -- e o que a NOTA exige.

        Desde 15/09/2026, conversa em que toda fala do cliente e formula de
        cortesia ("ok, obrigado", "valeu") nao tem sinal: a mesma formula fecha
        atendimento bom e ruim. Ver `fraus/cortesia.py`.
        """
        return any(not e_so_cortesia(m.texto) for m in self.mensagens_cliente)

    @property
    def motivo_sem_sinal(self) -> Literal["sem_fala_do_cliente", "so_cortesia"] | None:
        """POR QUE nao ha nota -- `None` quando ha sinal.

        Existe para a tela nao dizer "o cliente nao falou" a quem escreveu "ok,
        obrigado", e para ela nao precisar reimplementar a regra da cortesia em
        TypeScript (invariante 3: regra derivada mora no servidor).
        """
        if not self.tem_fala_cliente:
            return "sem_fala_do_cliente"
        if not self.tem_sinal_cliente:
            return "so_cortesia"
        return None
