"""Leitura de um comando so nao abre transacao; `/indicadores` conta uma vez.

Producao tem poucas conversas: o que custa numa leitura nao e CPU, e a IDA ao
Postgres. Cada `with self._conectar()` pagava tres -- BEGIN, a consulta e
COMMIT -- e `/indicadores` fazia nove leituras (27 comandos por chamada,
medidos em 20/11/2026 com `log_statement=all`). Uma transacao em volta de UM
`SELECT` nao protege nada: nao ha segundo comando para ser coerente com ele.

Quem ESCREVE, ou le mais de uma vez esperando o mesmo retrato, continua em
transacao -- e por isso a leitura e uma escolha explicita (`_ler`), nao o padrao.
"""

from datetime import datetime, timezone

import pytest

from fraus.api.escopo import BancoComEscopo
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.conftest import URL_POSTGRES


def _conversa(ident, canal="chat"):
    quando = datetime(2026, 9, 23, 15, 0, tzinfo=timezone.utc)
    return Conversa(id=ident, canal=canal, iniciada_em=quando,
                    mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=quando)])


def _banco(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    banco.salvar(_conversa("em-dia"), 80.0, "promotor", lexico_versao=0, regua="r")
    banco.salvar(_conversa("outra-regua"), 80.0, "promotor", lexico_versao=0, regua="velha")
    banco.salvar(_conversa("sem-regua", canal="email"), 80.0, "promotor", lexico_versao=0)
    return banco


def test_as_duas_contagens_numa_consulta_batem_com_as_separadas(tmp_path):
    banco = _banco(tmp_path)

    lexico, total, regua = banco.contar_defasagens("r")

    assert (lexico, total) == banco.contar_defasadas()
    assert (regua, total) == banco.contar_defasadas("r")
    assert (lexico, total, regua) == (0, 3, 2)


def test_sem_regua_vigente_as_duas_contagens_sao_a_do_lexico(tmp_path):
    """Motor duble nao tem regua: so o lexico conta, nos dois campos."""
    banco = _banco(tmp_path)

    lexico, total, regua = banco.contar_defasagens(None)

    assert (lexico, total) == banco.contar_defasadas()
    assert regua == banco.contar_defasadas(None)[0]


def test_com_escopo_a_contagem_unica_respeita_os_canais(tmp_path):
    banco = _banco(tmp_path)
    escopo = BancoComEscopo(banco, ["chat"])

    lexico, total, regua = escopo.contar_defasagens("r")

    assert (lexico, total) == escopo.contar_defasadas()
    assert (regua, total) == escopo.contar_defasadas("r")
    assert total == 2
    assert BancoComEscopo(banco, []).contar_defasagens("r") == (0, 0, 0)


def test_leitura_devolve_o_mesmo_que_antes(tmp_path):
    """`_ler` troca o envelope da consulta, nunca o resultado."""
    banco = _banco(tmp_path)

    with banco._ler() as conexao:
        total = conexao.execute("SELECT COUNT(*) AS n FROM conversas").fetchone()["n"]

    assert total == 3
    assert len(banco.todas()) == 3
    assert banco.buscar("em-dia")[1] == 80.0


def test_erro_numa_leitura_nao_estraga_a_proxima(tmp_path):
    banco = _banco(tmp_path)

    with pytest.raises(Exception):
        with banco._ler() as conexao:
            conexao.execute("SELECT * FROM tabela_que_nao_existe")

    assert len(banco.todas()) == 3


@pytest.mark.skipif(not URL_POSTGRES, reason="exige FRAUS_TESTE_POSTGRES_URL")
def test_leitura_nao_abre_transacao_e_devolve_a_conexao_como_veio(tmp_path):
    from psycopg.pq import TransactionStatus

    banco = _banco(tmp_path)

    with banco._ler() as conexao:
        conexao.execute("SELECT 1")
        bruta = conexao._conexao
        # Em transacao seria INTRANS: e o BEGIN que nao queremos pagar.
        assert bruta.info.transaction_status == TransactionStatus.IDLE
        assert bruta.autocommit is True
    # De volta ao pool no modo de sempre: a proxima a pegar pode ser uma escrita.
    assert bruta.autocommit is False

    with banco._conectar() as conexao:
        conexao.execute("SELECT 1")
        assert conexao._conexao.info.transaction_status == TransactionStatus.INTRANS


@pytest.mark.skipif(not URL_POSTGRES, reason="exige FRAUS_TESTE_POSTGRES_URL")
def test_escrita_depois_de_leitura_continua_atomica(tmp_path):
    """A conexao que serviu uma leitura volta a reverter erro no meio da escrita."""
    banco = _banco(tmp_path)
    banco.todas()

    with pytest.raises(RuntimeError):
        with banco._conectar() as conexao:
            conexao.execute("DELETE FROM conversas")
            raise RuntimeError("falha no meio")

    assert len(banco.todas()) == 3
