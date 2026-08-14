import pytest

from fraus.configuracao import (PADROES, carregar, faixas_de, salvar,
                                validar_configuracao)
from fraus.db import Banco
from fraus.indicadores import FAIXAS_NPS


@pytest.fixture()
def banco(tmp_path):
    b = Banco(tmp_path / "fraus.db")
    b.migrar()
    return b


def test_banco_vazio_se_comporta_como_o_padrao_de_fabrica(banco):
    """Sem linha nenhuma na tabela, o sistema roda exatamente como antes."""
    assert carregar(banco) == PADROES
    assert faixas_de(carregar(banco)) == FAIXAS_NPS


def test_migrar_e_idempotente_e_preserva_o_que_ja_estava_gravado(banco):
    salvar(banco, {"limiares_latencia_s": [5, 30, 90]})
    banco.migrar()
    assert carregar(banco)["limiares_latencia_s"] == [5, 30, 90]


def test_salvar_grava_so_a_chave_enviada_e_mantem_o_resto_de_fabrica(banco):
    salvar(banco, {"faixas_nps": {"detrator": [0, 4], "neutro": [5, 7], "promotor": [8, 10]}})
    vigente = carregar(banco)
    assert faixas_de(vigente) == {"detrator": (0, 4), "neutro": (5, 7), "promotor": (8, 10)}
    assert vigente["limiares_latencia_s"] == PADROES["limiares_latencia_s"]


def test_faixa_invalida_e_recusada_antes_de_tocar_no_banco(banco):
    with pytest.raises(ValueError) as erro:
        salvar(banco, {"faixas_nps": {"detrator": [0, 5], "neutro": [7, 8], "promotor": [9, 10]}})
    assert "buraco" in str(erro.value)
    assert carregar(banco) == PADROES


@pytest.mark.parametrize("limiares", [[60, 10, 180], [10, 10, 180]])
def test_limiares_de_latencia_precisam_ser_crescentes(banco, limiares):
    with pytest.raises(ValueError) as erro:
        validar_configuracao({"limiares_latencia_s": limiares})
    assert "crescente" in str(erro.value)


def test_limiares_de_latencia_precisam_ser_tres_numeros_positivos(banco):
    with pytest.raises(ValueError) as erro:
        validar_configuracao({"limiares_latencia_s": [0, 60, 180]})
    assert "positivo" in str(erro.value)
    with pytest.raises(ValueError) as erro:
        validar_configuracao({"limiares_latencia_s": [10, 60]})
    assert "tres" in str(erro.value)


def test_chave_desconhecida_e_recusada_nomeando_a_chave(banco):
    with pytest.raises(ValueError) as erro:
        salvar(banco, {"cor_do_botao": "azul"})
    assert "cor_do_botao" in str(erro.value)
