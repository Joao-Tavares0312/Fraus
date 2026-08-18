"""A autenticacao que se liga sozinha na primeira subida.

O caso que estes testes existem para travar nao e o feliz: e o da ESCRITA que
falha. Ligar a autenticacao guardando a unica copia da chave em lugar nenhum
trancaria o dono para fora da propria instalacao, e a API precisa preferir subir
aberta -- com aviso -- a subir fechada e inacessivel.
"""

import pytest

from fraus.api.primeiro_uso import ligar_no_primeiro_uso
from fraus.db import Banco


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


def _lido(caminho) -> dict:
    return dict(
        linha.split("=", 1)
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if "=" in linha and not linha.startswith("#")
    )


def test_primeira_subida_liga_e_grava_as_duas_chaves(tmp_path):
    banco = _banco(tmp_path)
    arquivo = tmp_path / ".fraus-chaves.txt"

    assert ligar_no_primeiro_uso(banco, arquivo, None) == arquivo

    # O banco passa a exigir chave -- e o que o middleware consulta.
    assert banco.hash_da_chave_mestra() is not None

    chaves = _lido(arquivo)
    assert chaves["chave_mestra"].startswith("frm_")
    assert chaves["chave_acesso"].startswith("fra_")

    # A chave de acesso gravada em claro tem que ser a MESMA cujo hash foi
    # salvo: um arquivo com uma chave que nao autentica seria pior que arquivo
    # nenhum, porque parece funcionar.
    from fraus import acesso, credencial

    identificador = acesso.id_da_chave(chaves["chave_acesso"])
    guardado = banco.hash_da_chave_acesso(identificador)
    assert credencial.confere(chaves["chave_acesso"], guardado)


def test_segunda_subida_nao_faz_nada(tmp_path):
    """So a PRIMEIRA. Gerar de novo trocaria a credencial de quem ja esta dentro."""
    banco = _banco(tmp_path)
    arquivo = tmp_path / ".fraus-chaves.txt"
    ligar_no_primeiro_uso(banco, arquivo, None)
    hash_antes = banco.hash_da_chave_mestra()

    assert ligar_no_primeiro_uso(banco, arquivo, None) is None
    assert banco.hash_da_chave_mestra() == hash_antes


def test_mestra_no_ambiente_impede_a_geracao(tmp_path):
    """A variavel VENCE a gravada: gerar uma que perde para ela seria escrever
    no arquivo uma chave que nao abre nada."""
    banco = _banco(tmp_path)
    arquivo = tmp_path / ".fraus-chaves.txt"

    assert ligar_no_primeiro_uso(banco, arquivo, "do-ambiente") is None
    assert banco.hash_da_chave_mestra() is None
    assert not arquivo.exists()


def test_escrita_que_falha_deixa_a_api_aberta_e_o_banco_limpo(tmp_path, monkeypatch):
    """O caso que decide o desenho: sem arquivo, NADA e gravado.

    Aberta com aviso e recuperavel. Fechada com a unica copia da chave perdida
    no primeiro boot e um tijolo.
    """
    banco = _banco(tmp_path)
    arquivo = tmp_path / ".fraus-chaves.txt"

    def recusa(*_argumentos, **_nomeados):
        raise OSError("disco cheio")

    monkeypatch.setattr("fraus.api.primeiro_uso.escrever_credenciais", recusa)

    assert ligar_no_primeiro_uso(banco, arquivo, None) is None
    # A API continua ABERTA...
    assert banco.hash_da_chave_mestra() is None
    # ...e nao sobrou linha de chave de acesso orfa da tentativa.
    assert banco.listar_chaves_acesso() == []


def test_nao_sobrescreve_arquivo_existente(tmp_path):
    """Arquivo velho com banco novo: falhar e deixar o operador decidir qual
    copia morre, em vez de escolher por ele."""
    banco = _banco(tmp_path)
    arquivo = tmp_path / ".fraus-chaves.txt"
    arquivo.write_text("chave_mestra=frm_de_antes\n", encoding="utf-8")

    assert ligar_no_primeiro_uso(banco, arquivo, None) is None
    assert "frm_de_antes" in arquivo.read_text(encoding="utf-8")
    assert banco.hash_da_chave_mestra() is None


@pytest.mark.parametrize("subpasta", ["", "aninhada/mais"])
def test_cria_a_pasta_do_arquivo_quando_preciso(tmp_path, subpasta):
    banco = _banco(tmp_path)
    arquivo = tmp_path / subpasta / ".fraus-chaves.txt" if subpasta else tmp_path / ".fraus-chaves.txt"

    assert ligar_no_primeiro_uso(banco, arquivo, None) == arquivo
    assert arquivo.is_file()
