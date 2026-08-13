"""Persistencia SQLite. Sem ORM: o esquema e pequeno e estavel.

Latencia NAO e persistida -- e derivada dos timestamps na leitura.
"""

import json
import sqlite3
from pathlib import Path

from fraus.modelos import Conversa

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

-- Configuracao chave/valor JSON. A tabela guarda SO o que foi mudado: o valor
-- de fabrica vive no codigo (fraus/configuracao.py), entao banco vazio se
-- comporta exatamente como antes desta tabela existir.
CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
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

    def ler_configuracoes(self) -> dict:
        """So o que foi de fato alterado. O padrao de fabrica nao mora no banco."""
        with self._conectar() as conexao:
            linhas = conexao.execute("SELECT chave, valor FROM configuracoes").fetchall()
        return {linha["chave"]: json.loads(linha["valor"]) for linha in linhas}

    def escrever_configuracoes(self, valores: dict) -> None:
        """Grava as chaves recebidas numa transacao so -- meia configuracao seria pior."""
        with self._conectar() as conexao:
            conexao.executemany(
                "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
                [(chave, json.dumps(valor)) for chave, valor in valores.items()],
            )

    def todas(self) -> list[tuple[Conversa, float | None]]:
        with self._conectar() as conexao:
            linhas = conexao.execute("SELECT payload, score FROM conversas").fetchall()
        return [(Conversa(**json.loads(l["payload"])), l["score"]) for l in linhas]
