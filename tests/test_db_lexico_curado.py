"""O lexico curado no banco, e a VERSAO que impede a regua misturada."""

from datetime import datetime, timezone

import pytest

from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "t.db")
    b.migrar()
    return b


def _conversa(id_):
    quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
    return Conversa(
        id=id_, canal="csv", iniciada_em=quando,
        mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=quando)],
    )


def test_banco_novo_comeca_na_versao_zero(banco):
    assert banco.lexico_versao() == 0
    assert banco.listar_curados() == []


def test_curar_incrementa_a_versao(banco):
    banco.curar("palavra", "lentissimo", -1, "gente reclama de lentidao")
    assert banco.lexico_versao() == 1
    banco.curar("emoji", "🙄", -0.62, None)
    assert banco.lexico_versao() == 2


def test_curar_o_mesmo_termo_EDITA_em_vez_de_duplicar(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.curar("palavra", "lentissimo", 0, "na verdade e neutro aqui")
    curados = banco.listar_curados()
    assert len(curados) == 1
    assert curados[0]["peso"] == 0
    assert curados[0]["motivo"] == "na verdade e neutro aqui"


def test_o_mesmo_termo_em_tipos_DIFERENTES_coexiste(banco):
    banco.curar("palavra", "x", 1, None)
    banco.curar("emoji", "x", 1.0, None)
    assert len(banco.listar_curados()) == 2


def test_revogar_apaga_e_incrementa_a_versao(banco):
    registro = banco.curar("palavra", "lentissimo", -1, None)
    assert banco.revogar_curado(registro["id"]) is True
    assert banco.listar_curados() == []
    assert banco.lexico_versao() == 2  # curar=1, revogar=2


def test_revogar_o_que_nao_existe_devolve_False_e_nao_mexe_na_versao(banco):
    banco.curar("palavra", "a", 1, None)
    assert banco.revogar_curado(999) is False
    assert banco.lexico_versao() == 1


def test_carregar_curadoria_separa_palavra_de_emoji(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.curar("emoji", "🙄", -0.62, None)
    c = banco.carregar_curadoria()
    assert c.polaridade_de("lentissimo") == -1
    assert c.score_de("🙄") == -0.62
    assert c.versao == 2


def test_a_conversa_grava_a_versao_que_a_pontuou(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.salvar(_conversa("c1"), 70.0, "neutro", lexico_versao=1)
    defasadas, total = banco.contar_defasadas()
    assert (defasadas, total) == (0, 1)


def test_conversa_pontuada_antes_da_mudanca_conta_como_defasada(banco):
    banco.salvar(_conversa("c1"), 70.0, "neutro", lexico_versao=0)
    banco.curar("palavra", "lentissimo", -1, None)  # versao vira 1
    assert banco.contar_defasadas() == (1, 1)


def test_versao_NULA_SEM_curadoria_nenhuma_NAO_e_defasada(banco):
    """Sem nenhum termo curado nao existe "lexico anterior" a que ficar atras.

    A regra generica -- NULL e defasada -- estava certa e incompleta: num banco
    que nunca teve curadoria ela marcava TODA conversa como pontuada com outra
    regua, e a Visao geral abria com um alarme falso de 64 de 64. Pego rodando a
    interface contra a API de demonstracao, nao pelos testes: nenhum deles tinha
    a combinacao "versao nula E versao vigente zero".

    NULL e zero sao a mesma coisa AQUI, e so aqui: os dois dizem "pontuada antes
    de existir curadoria". O que distingue defasada de em dia e a versao
    VIGENTE ter andado desde entao.
    """
    banco.salvar(_conversa("c1"), 70.0, "neutro")  # sem passar a versao
    assert banco.contar_defasadas() == (0, 1)


def test_conversa_de_banco_antigo_com_versao_NULA_conta_como_defasada(banco):
    """Coluna acrescentada depois: linha antiga fica NULL e e anterior ao
    mecanismo -- que e defasada, nao 'em dia'."""
    banco.salvar(_conversa("c1"), 70.0, "neutro")  # sem passar a versao
    banco.curar("palavra", "x", -1, None)
    assert banco.contar_defasadas() == (1, 1)
