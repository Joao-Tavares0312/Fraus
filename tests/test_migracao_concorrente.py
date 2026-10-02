"""Duas instancias frias migrando ao mesmo tempo nao podem se derrubar.

Em 02/10/2026, logo depois de um deploy, duas funcoes da Vercel subiram juntas
e as duas rodaram `Banco.migrar()` no boot. O DDL de uma esperou a tabela que a
outra segurava e vice-versa: `psycopg.errors.DeadlockDetected`, e as primeiras
requisicoes da dashboard voltaram 500.
"""

import threading

import pytest

from fraus.db import Banco
from tests.conftest import URL_POSTGRES


class _SemLinhas(list):
    """Cursor vazio: itera como lista e responde `fetchall`, como os reais."""

    def fetchall(self):
        return []


class _Gravador:
    """Conexao falsa: so anota o que `migrar` mandou executar, na ordem."""

    def __init__(self):
        self.comandos: list[str] = []

    def execute(self, sql, parametros=()):
        self.comandos.append(sql)
        return _SemLinhas()

    def executescript(self, sql):
        self.comandos.append(sql)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_no_postgres_a_migracao_pega_a_trava_antes_de_qualquer_ddl(monkeypatch):
    banco = Banco("postgresql://ninguem@localhost/nenhum")
    gravador = _Gravador()
    monkeypatch.setattr(banco, "_conectar", lambda: gravador)
    banco.migrar()
    assert "pg_advisory_xact_lock" in gravador.comandos[0]
    assert all("pg_advisory" not in comando for comando in gravador.comandos[1:])


def test_no_sqlite_nao_ha_trava_de_postgres(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "nao-existe.db")
    gravador = _Gravador()
    monkeypatch.setattr(banco, "_conectar", lambda: gravador)
    banco.migrar()
    assert all("pg_advisory" not in comando for comando in gravador.comandos)


@pytest.mark.skipif(not URL_POSTGRES, reason="exige FRAUS_TESTE_POSTGRES_URL")
def test_instancias_migrando_juntas_terminam_todas_sem_erro(tmp_path):
    instancias = 8
    largada = threading.Barrier(instancias)
    erros: list[BaseException] = []

    def subir(indice: int) -> None:
        banco = Banco(tmp_path / f"instancia-{indice}.db")
        try:
            largada.wait(timeout=30)
            banco.migrar()
        except BaseException as erro:  # noqa: BLE001 - o teste relata qualquer falha
            erros.append(erro)

    # Primeira rodada: schema inexistente, todas criam. As seguintes: o caso de
    # producao, em que as tabelas ja existem e so os ALTER e os indices rodam.
    for _ in range(3):
        linhas = [threading.Thread(target=subir, args=(i,)) for i in range(instancias)]
        for linha in linhas:
            linha.start()
        for linha in linhas:
            linha.join(timeout=120)
        assert not erros, f"{len(erros)} instancia(s) falharam: {erros[0]!r}"
