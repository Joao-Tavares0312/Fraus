"""O "dia" de uma conversa e o dia no fuso do produto, em todo lugar.

Ate 02/10/2026 cada ponto usava o dia no offset em que a conversa chegou: uma
fonte que manda horario em UTC punha o atendimento das 22h30 de Brasilia no dia
SEGUINTE, enquanto o CSV do mesmo atendimento (sem fuso, lido como -03:00)
ficava no dia certo. Recorte de periodo, serie diaria e ordenacao discordavam
entre si conforme a origem do dado.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.fuso import FUSO_DO_PRODUTO, dia_do_produto, no_fuso_do_produto
from fraus.indicadores import serie_diaria
from fraus.modelos import Conversa, Mensagem

# 13/09 01:30 UTC e 12/09 22:30 em Brasilia: o mesmo instante, dois "dias".
MADRUGADA_UTC = datetime(2026, 9, 13, 1, 30, tzinfo=timezone.utc)


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):  # pragma: no cover
        raise AssertionError("rota de leitura nao deve pontuar")


def _conversa(id_: str, inicio: datetime) -> Conversa:
    return Conversa(
        id=id_, canal="webchat", iniciada_em=inicio,
        mensagens=[
            Mensagem(autor="cliente", texto="oi", enviada_em=inicio),
            Mensagem(autor="bot", texto="ola", enviada_em=inicio + timedelta(seconds=30)),
        ],
    )


def test_o_fuso_do_produto_e_brasilia_sem_horario_de_verao():
    assert FUSO_DO_PRODUTO.utcoffset(None) == timedelta(hours=-3)


def test_dia_do_produto_converte_antes_de_cortar():
    assert dia_do_produto(MADRUGADA_UTC) == date(2026, 9, 12)
    mesma_hora_local = datetime(2026, 9, 12, 22, 30, tzinfo=FUSO_DO_PRODUTO)
    assert dia_do_produto(mesma_hora_local) == date(2026, 9, 12)
    assert no_fuso_do_produto(MADRUGADA_UTC) == mesma_hora_local
    assert no_fuso_do_produto(MADRUGADA_UTC).isoformat() == "2026-09-12T22:30:00-03:00"


def test_a_serie_diaria_poe_a_conversa_no_dia_de_brasilia():
    serie = serie_diaria([(_conversa("c1", MADRUGADA_UTC), 80.0)])
    assert [ponto["dia"] for ponto in serie] == ["2026-09-12"]


def test_a_coluna_de_inicio_e_gravada_no_fuso_do_produto(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    banco.salvar(_conversa("c1", MADRUGADA_UTC), 80.0, "promotor")
    banco.salvar_lote([(_conversa("c2", MADRUGADA_UTC), 80.0, "promotor")], 0, None)
    with banco._conectar() as conexao:
        gravadas = {
            linha["id"]: linha["iniciada_em"]
            for linha in conexao.execute("SELECT id, iniciada_em FROM conversas")
        }
    assert gravadas == {"c1": "2026-09-12T22:30:00-03:00", "c2": "2026-09-12T22:30:00-03:00"}
    # O payload guarda o que a fonte mandou: o instante e o mesmo, o texto nao muda.
    assert banco.buscar("c1")[0].iniciada_em == MADRUGADA_UTC


def test_recorte_e_ordenacao_usam_o_dia_de_brasilia(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    banco.salvar(_conversa("utc", MADRUGADA_UTC), 80.0, "promotor")
    # 23:00 de Brasilia do dia 12: DEPOIS da outra no relogio, e antes no texto
    # cru ("2026-09-12T23:00-03:00" < "2026-09-13T01:30+00:00").
    banco.salvar(_conversa("local", datetime(2026, 9, 12, 23, 0, tzinfo=FUSO_DO_PRODUTO)),
                 80.0, "promotor")
    cliente = TestClient(criar_app(banco, MotorFalso()))

    no_dia_12 = cliente.get("/conversas", params={"de": "2026-09-12", "ate": "2026-09-12"})
    assert sorted(c["id"] for c in no_dia_12.json()) == ["local", "utc"]
    assert cliente.get("/conversas", params={"de": "2026-09-13"}).json() == []
    # Mais recente primeiro, pelo instante.
    assert [c["id"] for c in cliente.get("/conversas").json()] == ["local", "utc"]


def test_migrar_normaliza_as_linhas_gravadas_no_offset_de_origem(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    banco.salvar(_conversa("antiga", MADRUGADA_UTC), 80.0, "promotor")
    banco.salvar(_conversa("certa", datetime(2026, 9, 12, 9, 0, tzinfo=FUSO_DO_PRODUTO)),
                 80.0, "promotor")
    with banco._conectar() as conexao:  # como a linha era gravada antes
        conexao.execute("UPDATE conversas SET iniciada_em = ? WHERE id = ?",
                        (MADRUGADA_UTC.isoformat(), "antiga"))
    banco.migrar()
    banco.migrar()  # idempotente
    with banco._conectar() as conexao:
        gravadas = {
            linha["id"]: linha["iniciada_em"]
            for linha in conexao.execute("SELECT id, iniciada_em FROM conversas")
        }
    assert gravadas == {"antiga": "2026-09-12T22:30:00-03:00",
                        "certa": "2026-09-12T09:00:00-03:00"}
