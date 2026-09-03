"""PII nao pode sobreviver a entrada da API -- ver `fraus/seguranca/pii.py`.

Nao ha `conftest.py` no projeto nem fixture `ctx_de_teste` reaproveitavel:
`tests/test_api.py` monta banco temporario + motor duble e sobe a app inteira
via `TestClient(criar_app(...))`, mas este teste chama `registrar_conversa`
direto -- sem HTTP -- entao precisa de um `Contexto` de verdade, nao de um
cliente HTTP. A fixture abaixo segue o mesmo padrao de montagem de
`tests/test_api.py` (banco `Banco(tmp_path / "fraus.db")` migrado + motor
duble), so que devolve o `Contexto` em vez do `TestClient`.
"""

from datetime import datetime, timezone

import pytest

from fraus.api.contexto import Contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.db import Banco


class MotorFalso:
    """Motor duble minimo: so o que `registrar_conversa` chama."""

    def pontuar_conversa(self, conversa, curadoria=None):
        return 90.0


@pytest.fixture
def ctx_de_teste(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return Contexto(banco=banco, motor=MotorFalso(), raiz=tmp_path, chave_mestra=None)


def test_registrar_conversa_grava_texto_mascarado(ctx_de_teste):
    """PII nao pode chegar ao banco. O texto gravado ja vem mascarado."""
    from fraus.api.registro import registrar_conversa

    base = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    pedido = PedidoIngestao(
        id="c-pii",
        encerrada_em=base,
        escalou_para_humano=False,
        mensagens=[
            {
                "autor": "cliente",
                "texto": "meu cpf e 529.982.247-25 e o email joao@exemplo.com",
                "enviada_em": base,
            }
        ],
    )
    registrar_conversa(ctx_de_teste, pedido, {"canal": "csv", "nome": "teste"})

    conversa, _score = ctx_de_teste.banco.todas()[0]
    texto = conversa.mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "joao@exemplo.com" not in texto
    assert "[CPF]" in texto
    assert "[EMAIL]" in texto


def test_csv_driver_mascara_pii_na_leitura():
    """A outra porta de entrada. Mesma regra, senao ela vira o furo."""
    import io

    from fraus.ingest.csv_driver import carregar_linhas

    conteudo = (
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,csv,cliente,meu cpf e 529.982.247-25,2026-09-03T10:00:00+00:00,false\n"
    )
    resultado = carregar_linhas(io.StringIO(conteudo, newline=""))

    texto = resultado.conversas[0].mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "[CPF]" in texto


def test_totalk_mascara_pii_na_conversao():
    """Terceira porta de entrada: export da Totalk, dado real de cliente.

    `converter` recebe um Iterable[str] de linhas de CSV (o mesmo formato que
    `csv.DictReader` consome), nao uma lista de dicts -- por isso o `linhas`
    abaixo e montado como texto CSV com as colunas exigidas por `COLUNAS` e
    `DIRECAO`/`ID_NA_URL` (`Mensagem/Quem enviou` no formato "De: X Para: Y",
    e um id de conversa embutido na URL da coluna `Conversa`).
    """
    import io

    from fraus.ingest import totalk

    linhas = io.StringIO(
        "Conta/Nome,Mensagem/Data de criação,Mensagem/Quem enviou,"
        "Mensagem/Conteúdo,Conversa\n"
        "Empresa X,09/03/2026 10:00:00,De: Joao Para: Empresa X,"
        "meu cpf e 529.982.247-25,https://app.totalk.chat/c?id=abc-123\n",
        newline="",
    )

    resultado = totalk.converter(linhas)

    texto = resultado.conversas[0].mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "[CPF]" in texto


def test_transcricao_mascara_pii_inclusive_em_linha_de_continuacao():
    """Quarta armadilha: linha de continuacao e concatenada no texto ja montado.

    Censurar so no `Mensagem(...)` deixaria passar a PII que cair na segunda
    linha de uma fala que quebrou em duas.
    """
    from datetime import datetime, timezone

    from fraus.ingest.transcricao import ler

    inicio = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    texto_bruto = "Cliente: primeira linha\ne meu cpf e 529.982.247-25\n"
    resultado = ler(texto_bruto, inicio)

    juntado = " ".join(m.texto for m in resultado.mensagens)
    assert "529.982.247-25" not in juntado
    assert "[CPF]" in juntado


def test_toda_origem_de_dado_real_censura_pii():
    """Guarda contra a QUARTA porta que alguem abrir sem censura.

    O furo que originou esta task foi exatamente isto: o plano cobriu duas
    origens e existiam tres. Este teste falha quando surge uma quarta.
    """
    import pathlib
    import re

    raiz = pathlib.Path(__file__).parent.parent / "fraus" / "ingest"
    # O simulador esta fora de proposito: corpus fixo de templates, sem PII.
    isentos = {"simulador.py"}

    sem_censura = []
    for arquivo in raiz.glob("*.py"):
        if arquivo.name in isentos:
            continue
        fonte = arquivo.read_text(encoding="utf-8")
        if re.search(r"\bMensagem\(", fonte) and "censurar_pii" not in fonte:
            sem_censura.append(arquivo.name)

    assert not sem_censura, (
        f"origem de dado real sem censura de PII: {sem_censura}. "
        "Toda origem que monta Mensagem precisa chamar censurar_pii."
    )
