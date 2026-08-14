"""Persistencia das chaves de acesso. O hash nunca sai nas listagens."""

from fraus.db import Banco


def _banco(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return banco


def test_criar_e_listar_sem_expor_hash(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("dashboard", "2026-08-14T00:00:00+00:00")
    banco.gravar_chave_acesso(registro["id"], chave_hash="abc123", dica="3f9a")
    listadas = banco.listar_chaves_acesso()
    assert len(listadas) == 1
    assert listadas[0]["nome"] == "dashboard"
    assert listadas[0]["dica"] == "3f9a"
    assert "chave_hash" not in listadas[0]
    assert "chave_hash" not in registro


def test_hash_so_sai_pelo_caminho_explicito(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("ci", "2026-08-14T00:00:00+00:00")
    banco.gravar_chave_acesso(registro["id"], chave_hash="abc123", dica="9z9z")
    assert banco.hash_da_chave_acesso(registro["id"]) == "abc123"
    assert banco.hash_da_chave_acesso(999) is None


def test_apagar_revoga(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("temporaria", "2026-08-14T00:00:00+00:00")
    assert banco.apagar_chave_acesso(registro["id"]) is True
    assert banco.apagar_chave_acesso(registro["id"]) is False
    assert banco.listar_chaves_acesso() == []
    assert banco.hash_da_chave_acesso(registro["id"]) is None
