import pytest

from fraus.api.main import validar_configuracao_de_producao


def test_modo_local_continua_sem_segredos_obrigatorios():
    validar_configuracao_de_producao(None, None, None, None)


def test_producao_falha_fechada_quando_falta_trava():
    with pytest.raises(RuntimeError, match="FRAUS_CODIGO_CONVITE"):
        validar_configuracao_de_producao(
            "production", "m" * 32, "j" * 32, None
        )


def test_segredo_jwt_curto_e_recusado_em_qualquer_ambiente():
    with pytest.raises(RuntimeError, match="32 bytes"):
        validar_configuracao_de_producao(None, None, "curto", None)
