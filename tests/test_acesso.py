"""Chave de ACESSO (le a API inteira) -- irma da chave de fonte de credencial.py."""

from fraus import acesso, credencial


def test_gerar_produz_chave_no_formato_fra_id_segredo():
    chave, chave_hash = acesso.gerar(7)
    partes = chave.split("_")
    assert partes[0] == "fra"
    assert partes[1] == "7"
    assert len(partes[2]) == credencial.BYTES_DO_SEGREDO * 2  # hex
    assert chave_hash == credencial.hash_da_chave(chave)


def test_id_da_chave_le_o_id_sem_confiar_nele():
    chave, _ = acesso.gerar(42)
    assert acesso.id_da_chave(chave) == 42


def test_id_da_chave_recusa_formatos_estranhos():
    assert acesso.id_da_chave("qualquer coisa") is None
    assert acesso.id_da_chave("fra_abc_123") is None
    # chave de FONTE nao e chave de acesso: prefixo distingue os papeis
    chave_de_fonte, _ = credencial.gerar(1)
    assert acesso.id_da_chave(chave_de_fonte) is None


def test_chaves_geradas_sao_diferentes():
    assert acesso.gerar(1)[0] != acesso.gerar(1)[0]
