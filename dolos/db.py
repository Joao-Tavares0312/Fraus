"""Persistencia SQLite. Sem ORM: o esquema e pequeno e estavel.

Latencia NAO e persistida -- e derivada dos timestamps na leitura.
"""

import json
import sqlite3
from pathlib import Path

from dolos.modelos import Conversa

ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversas (
    id TEXT PRIMARY KEY,
    canal TEXT NOT NULL,
    iniciada_em TEXT NOT NULL,
    score REAL,
    categoria TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversas_iniciada_em ON conversas(iniciada_em);
"""


class Banco:
    def __init__(self, caminho: Path) -> None:
        self._caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self._caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def migrar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript(ESQUEMA)

    def salvar(self, conversa: Conversa, score: float | None, categoria: str | None) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO conversas "
                "(id, canal, iniciada_em, score, categoria, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    conversa.id,
                    conversa.canal,
                    conversa.iniciada_em.isoformat(),
                    score,
                    categoria,
                    conversa.model_dump_json(),
                ),
            )

    def listar(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT id, canal, iniciada_em, score, categoria FROM conversas "
                "ORDER BY iniciada_em DESC"
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def buscar(self, conversa_id: str) -> tuple[Conversa, float | None, str | None] | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT payload, score, categoria FROM conversas WHERE id = ?", (conversa_id,)
            ).fetchone()
        if linha is None:
            return None
        return Conversa(**json.loads(linha["payload"])), linha["score"], linha["categoria"]

    def todas(self) -> list[tuple[Conversa, float | None]]:
        with self._conectar() as conexao:
            linhas = conexao.execute("SELECT payload, score FROM conversas").fetchall()
        return [(Conversa(**json.loads(l["payload"])), l["score"]) for l in linhas]
