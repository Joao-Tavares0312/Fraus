"""A mesma consulta tem de significar a mesma coisa nos dois bancos.

O BUG QUE ISTO PEGA. As datas deste banco sao TEXTO, e isso funciona porque
ISO-8601 em UTC ordena igual lexicograficamente -- mas so quando a comparacao e
por BYTE. O Postgres do Supabase nasce com `datcollate = en_US.UTF-8`, e essa
collation ignora pontuacao no nivel primario. Medido no banco de producao:

    '2026-03-01T10:00:00+00:00' < '2026-03-01T10:00:00.500000+00:00'
      Python/SQLite ....... True
      Postgres padrao ..... False   <-- o ponto e ignorado
      Postgres COLLATE C .. True

`datetime.now(timezone.utc).isoformat()` sempre carrega microssegundos, entao
UMA conversa com fracao de segundo bastava para `/conversas` listar fora de
ordem -- e SO em producao. Foi uma regressao da migracao de 02/09/2026.

POR QUE ESTE TESTE NAO PRECISA DE POSTGRES PARA VALER. Ele nao compara os dois
bancos rodando (isso exigiria servidor na suite, e a suite e de segundos). Ele
verifica que o SQL EMITIDO carrega `COLLATE "C"` no dialeto postgres e nao
carrega no sqlite, e prova em SQLite que a ordem esperada e a de byte. A
divergencia so pode voltar por alguem escrever um `ORDER BY` novo sem o helper
-- e e exatamente isso que `test_nenhuma_ordenacao_de_data_escapou` cobre, lendo
o proprio arquivo.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem

RAIZ = Path(__file__).resolve().parents[1]

# As colunas TEXT que guardam data ISO. Ordenar qualquer uma delas sem
# `_ordem()` reabre o bug.
COLUNAS_DE_DATA = (
    "iniciada_em",
    "criada_em",
    "criado_em",
    "recebida_em",
    "ocorrida_em",
)


def conversa_em(identificador: str, instante: str) -> Conversa:
    momento = datetime.fromisoformat(instante)
    return Conversa(
        id=identificador,
        canal="whatsapp",
        iniciada_em=momento,
        mensagens=[
            Mensagem(autor="cliente", texto="oi", enviada_em=momento),
            Mensagem(autor="bot", texto="ola", enviada_em=momento + timedelta(minutes=1)),
        ],
    )


def test_o_dialeto_postgres_ordena_por_byte_e_o_sqlite_nao_precisa():
    postgres = Banco("postgresql://exemplo/naovaiconectar")
    sqlite = Banco(Path("nao-existe.db"))
    assert postgres._ordem("iniciada_em") == 'iniciada_em COLLATE "C"'
    # No SQLite a comparacao ja e por byte; acrescentar COLLATE ali seria erro
    # de sintaxe, e o helper nao pode "consertar" o que nao esta quebrado.
    assert sqlite._ordem("iniciada_em") == "iniciada_em"


def test_fracao_de_segundo_ordena_pelo_relogio(tmp_path):
    """A ordem que a collation `en_US.UTF-8` errava.

    `10:00:00` e mais ANTIGA que `10:00:00.5`, entao no DESC ela vem depois.
    """
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    for identificador, instante in [
        ("meio", "2026-03-01T10:00:00.500000+00:00"),
        ("cheio", "2026-03-01T10:00:00+00:00"),
        ("depois", "2026-03-01T10:00:01+00:00"),
    ]:
        banco.salvar(conversa_em(identificador, instante), score=50.0, categoria="neutro")

    assert [linha["id"] for linha in banco.listar()] == ["depois", "meio", "cheio"]


def test_nenhuma_ordenacao_de_data_escapou():
    """Le o proprio `db.py` e exige que TODA ordenacao por coluna de data passe
    pelo helper.

    E uma trava de contrato, e nao paranoia: o defeito nao aparece em teste
    nenhum que rode em SQLite, entao um `ORDER BY criada_em` novo entraria
    verde e quebraria so em producao -- que foi exatamente como ele entrou da
    primeira vez.
    """
    fonte = (RAIZ / "fraus" / "db.py").read_text(encoding="utf-8")
    escapadas = []
    for linha in fonte.splitlines():
        if "ORDER BY" not in linha or "_ordem(" in linha:
            continue
        for coluna in COLUNAS_DE_DATA:
            # `ORDER BY <coluna>` cru, sem o helper.
            if re.search(rf"ORDER BY[^\"']*\b{coluna}\b", linha):
                escapadas.append(linha.strip())
    assert not escapadas, (
        "ordenacao por coluna de data sem `self._ordem()` -- ela vai divergir "
        f"entre SQLite e Postgres em silencio: {escapadas}"
    )
