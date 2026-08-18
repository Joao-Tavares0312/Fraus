"""A mestra no banco: uma linha, hash nunca exposto, substituicao no lugar."""

import pytest

from fraus.db import Banco


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "t.db")
    b.migrar()
    return b


def test_banco_novo_nao_tem_mestra(banco):
    assert banco.hash_da_chave_mestra() is None
    assert banco.chave_mestra_registrada() is None


def test_gravar_e_ler_o_hash(banco):
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    assert banco.hash_da_chave_mestra() == "hash-1"


def test_registro_publico_nao_carrega_o_hash(banco):
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    registro = banco.chave_mestra_registrada()
    assert registro == {"dica": "9a3f", "criada_em": "2026-08-17T10:00:00+00:00"}
    assert "chave_hash" not in registro


def test_gravar_de_novo_substitui_no_lugar(banco):
    """Rotacao troca a mestra, nao acumula uma segunda valida."""
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    banco.gravar_chave_mestra("hash-2", "b7c1", "2026-08-17T11:00:00+00:00")
    assert banco.hash_da_chave_mestra() == "hash-2"
    assert banco.chave_mestra_registrada()["dica"] == "b7c1"
