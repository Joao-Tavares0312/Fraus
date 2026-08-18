"""Apagar a mestra do banco -- o caminho de quem perdeu a chave.

Nenhuma ROTA chama isto, e e a decisao: desligar a autenticacao pela rede seria
uma chamada que baixa a defesa, alcancavel justamente quando a API esta aberta.
O chamador e `scripts/resetar_mestra.py`, que exige o disco.
"""

from fraus.db import Banco


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


def test_apagar_devolve_falso_quando_nao_havia_mestra(tmp_path):
    """Distinguir "apaguei" de "nao havia" e o que deixa o script honesto."""
    assert _banco(tmp_path).apagar_chave_mestra() is False


def test_apagar_remove_a_mestra_e_reabre_a_api(tmp_path):
    banco = _banco(tmp_path)
    banco.gravar_chave_mestra(
        chave_hash="hash", dica="··3f9a", criada_em="2026-08-17T10:00:00+00:00"
    )
    assert banco.hash_da_chave_mestra() is not None

    assert banco.apagar_chave_mestra() is True

    # As duas leituras precisam concordar: `hash_da_chave_mestra` e o que o
    # middleware consulta a cada requisicao para decidir se a API exige chave.
    assert banco.hash_da_chave_mestra() is None
    assert banco.chave_mestra_registrada() is None


def test_apagar_a_mestra_nao_toca_nas_chaves_de_acesso(tmp_path):
    """Elas voltam a valer quando a autenticacao for ligada de novo.

    Apagar tudo junto seria mais simples e mais destrutivo do que o problema
    pede: quem perdeu a MESTRA nao perdeu as chaves que ja distribuiu.
    """
    banco = _banco(tmp_path)
    banco.gravar_chave_mestra(
        chave_hash="hash", dica="··3f9a", criada_em="2026-08-17T10:00:00+00:00"
    )
    registro = banco.criar_chave_acesso(nome="dashboard", criada_em="2026-08-17T10:00:00+00:00")
    banco.gravar_chave_acesso(registro["id"], chave_hash="outro", dica="··b1c7")

    banco.apagar_chave_mestra()

    assert banco.hash_da_chave_acesso(registro["id"]) == "outro"
    assert [chave["nome"] for chave in banco.listar_chaves_acesso()] == ["dashboard"]
