"""Paginacao de `listar_com_conversa` (auditoria de 13/10/2026).

Rode tambem com `FRAUS_TESTE_POSTGRES_URL`: o empate so perde linha no
Postgres, que nao garante ordem estavel entre paginas sem desempate.
"""

from datetime import datetime, timedelta, timezone

from fraus.api.escopo import BancoComEscopo
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem

INICIO = datetime(2026, 9, 15, 10, tzinfo=timezone(timedelta(hours=-3)))


def _conversa(i: int, inicio: datetime = INICIO) -> Conversa:
    return Conversa(
        id=f"c{i:03d}", canal="chat", iniciada_em=inicio,
        mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=inicio)],
    )


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "paginas.db")
    banco.migrar()
    return banco


def test_paginas_com_o_mesmo_inicio_nao_perdem_nem_repetem_conversa(tmp_path):
    """Lote importado e relogio de minuto da Totalk empatam `iniciada_em`."""
    banco = _banco(tmp_path)
    for i in range(200):
        banco.salvar(_conversa(i), 50.0, "detrator")

    lidos = []
    for pagina in range(0, 200, 7):
        lidos += [c.id for _, c in banco.listar_com_conversa(limite=7, deslocamento=pagina)]

    assert len(lidos) == 200
    assert set(lidos) == {f"c{i:03d}" for i in range(200)}


def test_deslocamento_sem_limite_vale_igual_com_e_sem_escopo(tmp_path):
    banco = _banco(tmp_path)
    for i in range(3):
        banco.salvar(_conversa(i, INICIO + timedelta(minutes=i)), 50.0, "detrator")

    direto = [c.id for _, c in banco.listar_com_conversa(deslocamento=2)]
    com_escopo = [c.id for _, c in BancoComEscopo(banco, frozenset({"chat"})).listar_com_conversa(deslocamento=2)]

    assert direto == com_escopo == ["c000"]
