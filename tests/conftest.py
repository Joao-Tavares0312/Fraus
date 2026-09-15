"""A suite inteira contra Postgres, sem reescrever teste nenhum.

Producao e Supabase; os testes nasceram em SQLite porque sao de segundos e sem
servidor. Os dois dialetos ja divergem no DDL (`REAL`, `NOCASE`, collation de
data), entao passar so no SQLite nao prova producao.

Com `FRAUS_TESTE_POSTGRES_URL` definida, todo `Banco(<arquivo>.db)` criado por
um teste passa a apontar para esse Postgres, e o schema `fraus` e apagado ao
fim de cada teste -- o equivalente ao `tmp_path` novo. Sem a variavel, nada
muda. Roda no CI (`.github/workflows/testes.yml`); localmente:

    docker run -d --rm --name fraus-pg -e POSTGRES_PASSWORD=teste -p 55432:5432 postgres:16
    FRAUS_TESTE_POSTGRES_URL=postgresql://postgres:teste@localhost:55432/postgres uv run pytest -q
"""

import os
from pathlib import Path

import pytest

from fraus.db import SCHEMA_POSTGRES, Banco

URL_POSTGRES = os.environ.get("FRAUS_TESTE_POSTGRES_URL")

# Destinos que o teste escolheu JUSTAMENTE por nao existirem ou por serem de
# outro dialeto -- redirecionar mudaria o que eles verificam.
_NAO_REDIRECIONAR = {"nao-existe.db"}


if URL_POSTGRES:

    @pytest.fixture(autouse=True)
    def _banco_em_postgres(monkeypatch):
        import psycopg

        criados: list[Banco] = []
        original = Banco.__init__

        def redirecionado(self, destino):
            texto = str(destino)
            if texto.endswith(".db") and Path(texto).name not in _NAO_REDIRECIONAR:
                destino = URL_POSTGRES
            original(self, destino)
            criados.append(self)

        monkeypatch.setattr(Banco, "__init__", redirecionado)
        yield
        for banco in criados:
            banco.fechar()
        with psycopg.connect(URL_POSTGRES, autocommit=True) as conexao:
            conexao.execute(f"DROP SCHEMA IF EXISTS {SCHEMA_POSTGRES} CASCADE")
