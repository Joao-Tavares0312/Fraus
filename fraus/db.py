"""Persistencia SQLite. Sem ORM: o esquema e pequeno e estavel.

Latencia NAO e persistida -- e derivada dos timestamps na leitura.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fraus.modelos import Conversa
from fraus.sinais.curadoria import Curadoria

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
-- `chave_hash` guarda o SHA-256 da chave de API, nunca a chave. `chave_dica`
-- sao os quatro ultimos caracteres, so para o operador reconhecer qual chave
-- esta em uso. Ver fraus/credencial.py para o porque de cada escolha.
CREATE TABLE IF NOT EXISTS fontes_integracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    canal TEXT NOT NULL,
    tipo TEXT NOT NULL,
    variavel_segredo TEXT,
    ativa INTEGER NOT NULL DEFAULT 1,
    criada_em TEXT NOT NULL,
    chave_hash TEXT,
    chave_dica TEXT,
    chave_criada_em TEXT
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

-- Chave de ACESSO: autoriza a leitura da API inteira quando FRAUS_CHAVE_MESTRA
-- esta definida. `chave_hash`/`dica` seguem o desenho de fontes_integracao:
-- hash no banco, nunca a chave; dica de 4 chars para o operador reconhecer.
-- Revogar e DELETE: chave sem linha e chave que nao autoriza.
CREATE TABLE IF NOT EXISTS chaves_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    chave_hash TEXT,
    dica TEXT,
    criada_em TEXT NOT NULL
);

-- Chave MESTRA gravada pela tela (`POST /acesso/mestra`), a segunda procedencia
-- da mestra ao lado de FRAUS_CHAVE_MESTRA -- que continua vencendo. Existe para
-- a autenticacao ligada por botao SOBREVIVER a reiniciar o processo: mestra que
-- mora so em memoria volta a API para aberta em silencio, e "parece protegido e
-- nao esta" e a pior falha possivel aqui.
--
-- `CHECK (id = 1)` faz do "existe no maximo UMA mestra" uma garantia do banco,
-- nao uma regra que a aplicacao precisa lembrar de conferir. A chave em claro
-- nunca chega aqui: so o hash, como em toda credencial deste projeto.
CREATE TABLE IF NOT EXISTS chave_mestra (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    chave_hash TEXT NOT NULL,
    dica TEXT NOT NULL,
    criada_em TEXT NOT NULL
);

-- O que o analista ensinou ao lexico: termos que o SentiLex-PT02 e o Emoji
-- Sentiment Ranking nao trazem, ou trazem com polaridade errada para o dominio
-- de atendimento. Ver fraus/sinais/curadoria.py.
--
-- O INDICE UNICO e o que faz recadastrar o mesmo termo ser EDICAO em vez de
-- duplicata silenciosa com uma das duas vencendo por ordem de leitura.
--
-- `motivo` e opcional e existe para a decisao sobreviver a quem a tomou: um
-- peso sem porque, seis meses depois, e indistinguivel de erro de digitacao.
CREATE TABLE IF NOT EXISTS lexico_curado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    termo TEXT NOT NULL,
    peso REAL NOT NULL,
    motivo TEXT,
    criado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexico_curado_termo
    ON lexico_curado(tipo, termo);
"""


class Banco:
    def __init__(self, caminho: Path) -> None:
        self._caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self._caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    # Colunas acrescentadas depois que a tabela ja existia em disco.
    # `CREATE TABLE IF NOT EXISTS` cria o banco novo com elas e nao faz nada
    # num banco antigo -- que continuaria sem as colunas e quebraria na leitura.
    COLUNAS_ACRESCENTADAS = (
        ("fontes_integracao", "chave_hash", "TEXT"),
        ("fontes_integracao", "chave_dica", "TEXT"),
        ("fontes_integracao", "chave_criada_em", "TEXT"),
        ("conversas", "lexico_versao", "INTEGER"),
    )

    def migrar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript(ESQUEMA)
            for tabela, coluna, tipo in self.COLUNAS_ACRESCENTADAS:
                existentes = {
                    linha["name"]
                    for linha in conexao.execute(f"PRAGMA table_info({tabela})")
                }
                if coluna not in existentes:
                    conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")

    def salvar(
        self,
        conversa: Conversa,
        score: float | None,
        categoria: str | None,
        lexico_versao: int | None = None,
    ) -> None:
        """Grava a conversa e COM QUAL LEXICO ela foi pontuada.

        `lexico_versao` e opcional e vai ao fim porque todo chamador anterior a
        curadoria continua valendo -- e `None` ali significa exatamente o que
        significa numa linha de banco antigo: nao se sabe, logo defasada.
        """
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO conversas "
                "(id, canal, iniciada_em, score, categoria, payload, lexico_versao) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    conversa.id,
                    conversa.canal,
                    conversa.iniciada_em.isoformat(),
                    score,
                    categoria,
                    conversa.model_dump_json(),
                    lexico_versao,
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

    def hash_da_chave_da_fonte(self, identificador: int) -> str | None:
        """O unico caminho para ler o hash. Explicito no nome e de uso unico.

        Existe separado de `buscar_fonte` para que o hash nunca viaje dentro do
        dicionario que a API serializa -- ver `_fonte`.
        """
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT chave_hash FROM fontes_integracao WHERE id = ?", (identificador,)
            ).fetchone()
        return linha["chave_hash"] if linha is not None else None

    def gravar_chave(
        self, identificador: int, chave_hash: str, dica: str, criada_em: str
    ) -> dict | None:
        """Grava a chave nova SUBSTITUINDO a anterior.

        Uma chave ativa por fonte, sempre. Duas chaves validas ao mesmo tempo
        dariam a impressao de rotacao sem risco, mas a antiga continuaria
        aceita e ninguem saberia quem ainda a usa -- gerar uma chave tem que
        invalidar a de antes, para "gerei outra" significar de fato que a
        anterior parou de funcionar.
        """
        with self._conectar() as conexao:
            conexao.execute(
                "UPDATE fontes_integracao "
                "SET chave_hash = ?, chave_dica = ?, chave_criada_em = ? WHERE id = ?",
                (chave_hash, dica, criada_em, identificador),
            )
        return self.buscar_fonte(identificador)

    def revogar_chave(self, identificador: int) -> dict | None:
        """Apaga a chave da fonte. A fonte e o historico dela continuam."""
        with self._conectar() as conexao:
            conexao.execute(
                "UPDATE fontes_integracao "
                "SET chave_hash = NULL, chave_dica = NULL, chave_criada_em = NULL "
                "WHERE id = ?",
                (identificador,),
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
        """Fonte como ela pode circular. O HASH DA CHAVE NAO SAI POR AQUI.

        O `chave_hash` e removido neste unico ponto, e nao na borda HTTP, de
        proposito: `_fonte_publica` monta a resposta com `{**fonte}`, entao
        qualquer coluna nova da tabela apareceria sozinha na API sem ninguem
        decidir isso. Tirando o campo na origem, esquecer de esconder deixa de
        ser possivel -- quem precisa dele chama `hash_da_chave_da_fonte`, que e
        explicito no nome e no uso.

        O hash nao e senha e nem por isso pode circular: ele e o suficiente
        para confirmar um palpite de chave offline, sem nenhuma requisicao.
        """
        registro = dict(linha)
        registro["ativa"] = bool(registro["ativa"])
        registro.pop("chave_hash", None)
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

    def criar_chave_acesso(self, nome: str, criada_em: str) -> dict:
        """Cria a LINHA da chave. O hash chega depois, por gravar_chave_acesso:
        a chave embute o id, entao o id precisa existir antes do segredo."""
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO chaves_acesso (nome, criada_em) VALUES (?, ?)",
                (nome, criada_em),
            )
            identificador = cursor.lastrowid
        return {"id": identificador, "nome": nome, "dica": None, "criada_em": criada_em}

    def gravar_chave_acesso(self, identificador: int, chave_hash: str, dica: str) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                "UPDATE chaves_acesso SET chave_hash = ?, dica = ? WHERE id = ?",
                (chave_hash, dica, identificador),
            )

    def listar_chaves_acesso(self) -> list[dict]:
        """O HASH NAO SAI POR AQUI -- mesma regra de _fonte: removido na origem."""
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT id, nome, dica, criada_em FROM chaves_acesso ORDER BY criada_em, id"
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def hash_da_chave_acesso(self, identificador: int) -> str | None:
        """O unico caminho para ler o hash -- explicito no nome, uso unico."""
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT chave_hash FROM chaves_acesso WHERE id = ?", (identificador,)
            ).fetchone()
        return linha["chave_hash"] if linha is not None else None

    def apagar_chave_acesso(self, identificador: int) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "DELETE FROM chaves_acesso WHERE id = ?", (identificador,)
            )
            return cursor.rowcount > 0

    def gravar_chave_mestra(self, chave_hash: str, dica: str, criada_em: str) -> None:
        """Grava a mestra NO LUGAR da anterior, se houver.

        `INSERT OR REPLACE` com `id = 1` fixo: a rotacao TROCA a credencial em
        vez de acumular uma segunda valida -- duas mestras aceitas ao mesmo
        tempo pareceriam rotacao sem risco, mas a antiga seguiria autorizando
        sem ninguem saber quem ainda a usa.
        """
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO chave_mestra (id, chave_hash, dica, criada_em)"
                " VALUES (1, ?, ?, ?)",
                (chave_hash, dica, criada_em),
            )

    def hash_da_chave_mestra(self) -> str | None:
        """O unico caminho para ler o hash da mestra -- explicito no nome."""
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT chave_hash FROM chave_mestra WHERE id = 1"
            ).fetchone()
        return linha["chave_hash"] if linha is not None else None

    def apagar_chave_mestra(self) -> bool:
        """Remove a mestra do banco. Devolve se havia alguma para remover.

        NAO existe rota que chame isto, e a ausencia e a decisao: desligar a
        autenticacao pela rede seria uma chamada que baixa a defesa, e a API
        pode estar aberta justamente quando ela e feita. O unico chamador e
        `scripts/resetar_mestra.py`, que exige o disco e a mao de quem opera --
        e e a saida para quem perdeu a chave gerada pela tela.

        A autenticacao e decidida POR REQUISICAO, entao o efeito vale na
        chamada seguinte, sem reiniciar a API.
        """
        with self._conectar() as conexao:
            cursor = conexao.execute("DELETE FROM chave_mestra WHERE id = 1")
            return cursor.rowcount > 0

    def chave_mestra_registrada(self) -> dict | None:
        """Dica e data da mestra gravada. O HASH NAO SAI POR AQUI.

        `None` quando nao ha mestra no banco -- que e diferente de "nao ha
        mestra": a do ambiente nao passa por esta tabela.
        """
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT dica, criada_em FROM chave_mestra WHERE id = 1"
            ).fetchone()
        if linha is None:
            return None
        return {"dica": linha["dica"], "criada_em": linha["criada_em"]}

    # ---- lexico curado --------------------------------------------------

    # A versao mora na tabela de configuracoes, e nao numa tabela propria: ela e
    # UM inteiro, e a tabela chave/valor existe exatamente para isso. Comeca em
    # 0 e sobe a cada ESCRITA -- curar e revogar contam igual, porque as duas
    # mudam o que o lexico responde.
    CHAVE_VERSAO = "lexico_versao"

    def lexico_versao(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT valor FROM configuracoes WHERE chave = ?", (self.CHAVE_VERSAO,)
            ).fetchone()
        return int(json.loads(linha["valor"])) if linha else 0

    def _incrementar_versao(self, conexao) -> int:
        """Sobe a versao DENTRO da transacao de quem chamou.

        Recebe a conexao em vez de abrir a propria: gravar o termo e subir a
        versao precisam acontecer juntos ou nenhum dos dois. Em transacoes
        separadas, uma falha no meio deixaria termo curado com versao antiga --
        e a tela diria que o banco esta em dia quando nao esta.
        """
        linha = conexao.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (self.CHAVE_VERSAO,)
        ).fetchone()
        proxima = (int(json.loads(linha["valor"])) if linha else 0) + 1
        conexao.execute(
            "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (self.CHAVE_VERSAO, json.dumps(proxima)),
        )
        return proxima

    def curar(self, tipo: str, termo: str, peso: float, motivo: str | None) -> dict:
        """Cadastra ou EDITA um termo curado. Devolve o registro gravado."""
        agora = datetime.now(timezone.utc).isoformat()
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT INTO lexico_curado (tipo, termo, peso, motivo, criado_em) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(tipo, termo) DO UPDATE SET "
                "peso = excluded.peso, motivo = excluded.motivo, "
                "criado_em = excluded.criado_em",
                (tipo, termo, peso, motivo, agora),
            )
            self._incrementar_versao(conexao)
            linha = conexao.execute(
                "SELECT * FROM lexico_curado WHERE tipo = ? AND termo = ?",
                (tipo, termo),
            ).fetchone()
        return dict(linha)

    def listar_curados(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT * FROM lexico_curado ORDER BY criado_em DESC, id DESC"
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def revogar_curado(self, curado_id: int) -> bool:
        """`False` quando nao havia o que revogar -- e ai a versao NAO sobe.

        Subir a versao numa revogacao que nao aconteceu marcaria o banco inteiro
        como defasado sem nenhuma mudanca de lexico por tras.
        """
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "DELETE FROM lexico_curado WHERE id = ?", (curado_id,)
            )
            if cursor.rowcount == 0:
                return False
            self._incrementar_versao(conexao)
        return True

    def carregar_curadoria(self) -> Curadoria:
        """Monta o objeto que os sinais consomem. Lido a cada requisicao."""
        palavras: dict[str, int] = {}
        emojis: dict[str, float] = {}
        with self._conectar() as conexao:
            for linha in conexao.execute("SELECT tipo, termo, peso FROM lexico_curado"):
                if linha["tipo"] == "palavra":
                    palavras[linha["termo"]] = int(linha["peso"])
                else:
                    emojis[linha["termo"]] = float(linha["peso"])
        return Curadoria(palavras=palavras, emojis=emojis, versao=self.lexico_versao())

    def contar_defasadas(self) -> tuple[int, int]:
        """(pontuadas com lexico anterior, total). Do banco INTEIRO.

        `lexico_versao IS NULL` conta como defasada: e linha de banco anterior a
        este mecanismo, e "nao sei com qual lexico" nao e "em dia".
        """
        vigente = self.lexico_versao()
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN lexico_versao IS NULL OR lexico_versao <> ? "
                "THEN 1 ELSE 0 END) AS defasadas "
                "FROM conversas",
                (vigente,),
            ).fetchone()
        return int(linha["defasadas"] or 0), int(linha["total"] or 0)
