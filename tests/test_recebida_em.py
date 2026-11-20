"""QUANDO o atendimento chegou -- o que o selo "novo" e a releitura do painel usam.

`iniciada_em` e a hora da CONVERSA; um export de setembro enviado hoje comecou
em setembro. `recebida_em` e a hora em que o servidor gravou ou viu a conversa
mudar, e so ela responde "isto chegou depois da minha ultima visita?".

Tres regras, cada uma com o defeito que evita:

- reenvio IDENTICO nao mexe na hora: o mesmo arquivo reenviado nao vira novo;
- repontuar nao mexe na hora: trocar a regua nao e chegada de atendimento;
- linha anterior a coluna fica `None` -- nao se sabe, e ausencia nao vira data.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import fraus.db as modulo_db
from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso
from tests.test_vazao_de_ingestao import _fonte_com_chave


def _conversa(ident="c1", falas=1):
    return Conversa(
        id=ident,
        canal="tars",
        iniciada_em=datetime(2026, 9, 23, 15, 0, tzinfo=timezone.utc),
        mensagens=[
            Mensagem(autor="cliente", texto=f"fala {i}",
                     enviada_em=datetime(2026, 9, 23, 15, i, tzinfo=timezone.utc))
            for i in range(falas)
        ],
    )


def _relogio(monkeypatch, instantes):
    fila = iter(instantes)
    monkeypatch.setattr(modulo_db, "_agora_utc", lambda: next(fila))


def _recebida(banco, ident="c1"):
    return {linha["id"]: linha["recebida_em"] for linha, _ in banco.listar_com_conversa()}[ident]


def test_gravar_marca_a_hora_de_chegada(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00"])

    banco.salvar(_conversa(), 80.0, "promotor")

    assert _recebida(banco) == "2026-11-20T12:00:00+00:00"


def test_reenvio_com_fala_nova_atualiza_a_hora(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00", "2026-11-20T12:05:00+00:00"])

    banco.salvar(_conversa(falas=1), 80.0, "promotor")
    banco.salvar(_conversa(falas=2), 60.0, "neutro")

    assert _recebida(banco) == "2026-11-20T12:05:00+00:00"


def test_reenvio_identico_conserva_a_hora(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00", "2026-11-20T12:05:00+00:00"])

    banco.salvar(_conversa(), 80.0, "promotor")
    banco.salvar(_conversa(), 80.0, "promotor")

    assert _recebida(banco) == "2026-11-20T12:00:00+00:00"


def test_lote_segue_a_mesma_regra_por_conversa(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00", "2026-11-20T12:05:00+00:00"])

    banco.salvar_lote([(_conversa("a"), 80.0, "promotor"), (_conversa("b"), 80.0, "promotor")], 0, None)
    banco.salvar_lote(
        [(_conversa("a"), 80.0, "promotor"), (_conversa("b", falas=2), 80.0, "promotor"),
         (_conversa("c"), 80.0, "promotor")], 0, None)

    assert _recebida(banco, "a") == "2026-11-20T12:00:00+00:00"
    assert _recebida(banco, "b") == "2026-11-20T12:05:00+00:00"
    assert _recebida(banco, "c") == "2026-11-20T12:05:00+00:00"


def test_repontuar_nao_e_chegada(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00", "2026-11-20T12:05:00+00:00"])
    banco.salvar(_conversa(), 80.0, "promotor")

    assert banco.atualizar_pontuacao(_conversa(), 10.0, "detrator", 1, "regua-nova")

    assert _recebida(banco) == "2026-11-20T12:00:00+00:00"


def test_banco_anterior_a_coluna_migra_e_fica_sem_hora(tmp_path):
    """Derruba a coluna e migra de novo: e o banco de antes dela, nos dois dialetos."""
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    banco.salvar(_conversa(), 80.0, "promotor")
    with banco._conectar() as conexao:
        conexao.execute("ALTER TABLE conversas DROP COLUMN recebida_em")

    banco.migrar()

    # Nao se sabe quando chegou: `None`, nunca a hora da migracao nem a da conversa.
    assert _recebida(banco) is None
    # E reenviar a mesma conversa nao inventa uma chegada para ela.
    banco.salvar(_conversa(), 80.0, "promotor")
    assert _recebida(banco) is None


def _cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))


def _falas(n):
    return [{"autor": "cliente", "texto": f"pergunta {i}",
             "enviada_em": f"2026-09-23T12:{i:02d}:00-03:00"} for i in range(n)]


def test_lista_e_detalhe_devolvem_a_hora_de_chegada(tmp_path, monkeypatch):
    cliente = _cliente(tmp_path)
    chave = _fonte_com_chave(cliente, nome="TARS")
    _relogio(monkeypatch, ["2026-11-20T12:00:00+00:00"])
    criada = cliente.post("/ingestao", headers={"Authorization": f"Bearer {chave}"},
                          json={"id": "chat-1", "mensagens": _falas(1)})
    assert criada.status_code == 201, criada.text

    lista = cliente.get("/conversas").json()
    detalhe = cliente.get(f"/conversas/{criada.json()['id']}").json()

    assert lista[0]["recebida_em"] == "2026-11-20T12:00:00+00:00"
    assert detalhe["recebida_em"] == "2026-11-20T12:00:00+00:00"


def test_assinatura_muda_quando_chega_ou_cresce_um_atendimento(tmp_path):
    """A pergunta barata que o painel faz para saber se precisa reler.

    Contar linhas nao basta: o TARS reenvia o MESMO id a cada turno, e a
    conversa que cresceu nao muda o total.
    """
    cliente = _cliente(tmp_path)
    chave = _fonte_com_chave(cliente, nome="TARS")
    cabecalho = {"Authorization": f"Bearer {chave}"}

    vazia = cliente.get("/conversas/assinatura")
    assert vazia.status_code == 200, vazia.text
    assert vazia.json()["total"] == 0

    cliente.post("/ingestao", headers=cabecalho, json={"id": "chat-1", "mensagens": _falas(1)})
    com_uma = cliente.get("/conversas/assinatura").json()
    cliente.post("/ingestao", headers=cabecalho, json={"id": "chat-1", "mensagens": _falas(2)})
    cresceu = cliente.get("/conversas/assinatura").json()
    repetida = cliente.get("/conversas/assinatura").json()

    assert com_uma["total"] == 1 and cresceu["total"] == 1
    assert com_uma["assinatura"] != vazia.json()["assinatura"]
    assert cresceu["assinatura"] != com_uma["assinatura"]
    assert repetida == cresceu


def test_assinatura_nao_e_engolida_pelo_detalhe_por_id(tmp_path):
    """`/conversas/{id:path}` casa qualquer resto; a rota fixa vem antes."""
    cliente = _cliente(tmp_path)

    resposta = cliente.get("/conversas/assinatura")

    assert resposta.status_code == 200
    assert set(resposta.json()) == {"total", "assinatura"}
