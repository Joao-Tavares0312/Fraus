import pytest

from fraus.api.main import validar_configuracao_de_producao


def test_modo_local_continua_sem_segredos_obrigatorios():
    validar_configuracao_de_producao(None, None, None, None)


def test_producao_falha_fechada_quando_falta_trava():
    with pytest.raises(RuntimeError, match="FRAUS_CODIGO_CONVITE"):
        validar_configuracao_de_producao(
            "production", "m" * 32, "j" * 32, None, "postgresql://banco"
        )


def test_segredo_jwt_curto_e_recusado_em_qualquer_ambiente():
    with pytest.raises(RuntimeError, match="32 bytes"):
        validar_configuracao_de_producao(None, None, "curto", None)


def test_producao_recusa_banco_efemero():
    with pytest.raises(RuntimeError, match="FRAUS_DATABASE_URL"):
        validar_configuracao_de_producao(
            "production", "m" * 32, "j" * 32, "convite"
        )


def test_producao_aceita_estado_externo():
    validar_configuracao_de_producao(
        "production",
        "m" * 32,
        "j" * 32,
        "convite",
        "postgresql://pooler/fraus",
    )


@pytest.mark.parametrize("destino", ["fraus.db", "sqlite:///fraus.db", "https://banco"])
def test_producao_recusa_destino_que_banco_trataria_como_sqlite(destino):
    with pytest.raises(RuntimeError, match="FRAUS_DATABASE_URL.*PostgreSQL"):
        validar_configuracao_de_producao(
            "production", "m" * 32, "j" * 32, "convite", destino
        )


def test_producao_aceita_prefixo_postgres_curto():
    validar_configuracao_de_producao(
        "production", "m" * 32, "j" * 32, "convite", "postgres://pooler/fraus"
    )
