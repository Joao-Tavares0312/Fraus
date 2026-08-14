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

-- Fonte de onde conversa entra. `variavel_segredo` guarda o NOME da variavel
-- de ambiente que carrega a credencial -- NUNCA o valor. Segredo em texto puro
-- num SQLite de arquivo vaza junto com o backup.
CREATE TABLE IF NOT EXISTS fontes_integracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    canal TEXT NOT NULL,
    tipo TEXT NOT NULL,
    variavel_segredo TEXT,
    ativa INTEGER NOT NULL DEFAULT 1,
    criada_em TEXT NOT NULL
);

-- Historico de importacao: sem ele, "importado com sucesso" e alegacao sem
-- lastro. `motivos` e o mesmo JSON que a resposta do endpoint ja devolve.
CREATE TABLE IF NOT EXISTS importacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ocorrida_em TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    aceitas INTEGER NOT NULL,
    rejeitadas INTEGER NOT NULL,
    motivos TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_importacoes_ocorrida_em ON importacoes(ocorrida_em);
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

    def listar_com_conversa(self) -> list[tuple[dict, Conversa]]:
        """Como `listar`, mas trazendo a conversa inteira junto de cada linha.

        Existe para a lista de atendimentos poder mostrar tempo de resposta,
        contagem de mensagens e desfecho -- coisas que so o `payload` sabe. A
        alternativa era o cliente pedir `/conversas/{id}` de cada linha, um
        N+1 que a dashboard ja pagou caro em outras telas.

        Os agregados sao DERIVADOS na leitura, nunca gravados em coluna. Coluna
        denormalizada envelheceria em silencio no dia em que a regra de
        latencia mudasse, e a tabela passaria a exibir um numero que o resto do
        sistema nao reconhece mais. O custo e ler e desserializar o JSON de
        todas as conversas do recorte -- aceitavel na ordem de grandeza deste
        projeto (milhares), e o ponto a trocar por uma materializacao se um dia
        deixar de ser.
        """
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT id, canal, iniciada_em, score, categoria, payload FROM conversas "
                "ORDER BY iniciada_em DESC"
            ).fetchall()
        return [
            (
                {
                    chave: linha[chave]
                    for chave in ("id", "canal", "iniciada_em", "score", "categoria")
                },
                Conversa(**json.loads(linha["payload"])),
            )
            for linha in linhas
        ]

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

    def criar_fonte(
        self, nome: str, canal: str, tipo: str, variavel_segredo: str | None, criada_em: str
    ) -> dict:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO fontes_integracao "
                "(nome, canal, tipo, variavel_segredo, ativa, criada_em) VALUES (?, ?, ?, ?, 1, ?)",
                (nome, canal, tipo, variavel_segredo, criada_em),
            )
            identificador = cursor.lastrowid
        return self.buscar_fonte(identificador)

    def listar_fontes(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT * FROM fontes_integracao ORDER BY criada_em, id"
            ).fetchall()
        return [self._fonte(linha) for linha in linhas]

    def buscar_fonte(self, identificador: int) -> dict | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT * FROM fontes_integracao WHERE id = ?", (identificador,)
            ).fetchone()
        return self._fonte(linha) if linha is not None else None

    def atualizar_fonte(
        self, identificador: int, nome: str | None = None, ativa: bool | None = None
    ) -> dict | None:
        campos, valores = [], []
        if nome is not None:
            campos.append("nome = ?")
            valores.append(nome)
        if ativa is not None:
            campos.append("ativa = ?")
            valores.append(1 if ativa else 0)
        if campos:
            with self._conectar() as conexao:
                conexao.execute(
                    f"UPDATE fontes_integracao SET {', '.join(campos)} WHERE id = ?",
                    (*valores, identificador),
                )
        return self.buscar_fonte(identificador)

    def apagar_fonte(self, identificador: int) -> bool:
        """Remove SO o cadastro da fonte. Nenhuma conversa e tocada aqui.

        Conversa que ja entrou e dado do atendimento, nao propriedade da fonte:
        apagar a origem nao pode reescrever o historico de satisfacao medido.
        """
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "DELETE FROM fontes_integracao WHERE id = ?", (identificador,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _fonte(linha: sqlite3.Row) -> dict:
        registro = dict(linha)
        registro["ativa"] = bool(registro["ativa"])
        return registro

    def registrar_importacao(
        self, ocorrida_em: str, arquivo: str, aceitas: int, rejeitadas: int, motivos: list[dict]
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT INTO importacoes (ocorrida_em, arquivo, aceitas, rejeitadas, motivos) "
                "VALUES (?, ?, ?, ?, ?)",
                (ocorrida_em, arquivo, aceitas, rejeitadas, json.dumps(motivos)),
            )

    def listar_importacoes(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT * FROM importacoes ORDER BY ocorrida_em DESC, id DESC"
            ).fetchall()
        return [{**dict(l), "motivos": json.loads(l["motivos"])} for l in linhas]

    def todas(self) -> list[tuple[Conversa, float | None]]:
        with self._conectar() as conexao:
            linhas = conexao.execute("SELECT payload, score FROM conversas").fetchall()
        return [(Conversa(**json.loads(l["payload"])), l["score"]) for l in linhas]
