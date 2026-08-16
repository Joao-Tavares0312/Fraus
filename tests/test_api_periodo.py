"""Recorte de periodo em /conversas e /indicadores, e o agregado /lexico.

Estes endpoints existem para tirar da dashboard o ultimo N+1: com filtro
ativo ela baixava TODAS as transcricoes so para agregar categoria, lexico e
tempo de resposta no cliente. As duas pontas do recorte sao INCLUSIVAS e
data malformada e 400 nomeando o parametro -- mesmo contrato do
/serie-temporal, que ja pagou essas decisoes.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem


class MotorFalso:
    """Nenhuma rota deste arquivo pontua: o motor nao pode ser exigido."""

    def pontuar_conversa(self, conversa):  # pragma: no cover - nao chamado
        raise AssertionError("rota de leitura nao deve pontuar")


def _quando(dia: str, hora: str = "12:00:00") -> datetime:
    return datetime.fromisoformat(f"{dia}T{hora}+00:00")


def _gravar(
    banco: Banco,
    id: str,
    dia: str,
    score: float | None,
    texto: str = "obrigado",
    escalou: bool = False,
) -> None:
    """Grava uma conversa de duas mensagens com 30 s de espera."""
    conversa = Conversa(
        id=id,
        canal="webchat",
        iniciada_em=_quando(dia),
        escalou_para_humano=escalou,
        mensagens=[
            Mensagem(autor="cliente", texto=texto, enviada_em=_quando(dia)),
            Mensagem(
                autor="humano" if escalou else "bot",
                texto="certo",
                enviada_em=_quando(dia, "12:00:30"),
            ),
        ],
    )
    banco.salvar(conversa, score, None)


@pytest.fixture()
def cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    # Tres dias, um por categoria: detrator (20 -> nota 2), neutro
    # (75 -> nota 8) e promotor (95 -> nota 10), mais uma sem sinal.
    _gravar(banco, "d1", "2026-08-01", 20.0, texto="pessimo atendimento horrivel")
    _gravar(banco, "n1", "2026-08-02", 75.0, texto="obrigado resolvido")
    _gravar(banco, "p1", "2026-08-03", 95.0, texto="otimo maravilha adorei 😍")
    _gravar(banco, "s1", "2026-08-03", None, texto="...")
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /conversas?de=&ate=
# ---------------------------------------------------------------------------


def test_conversas_sem_filtro_devolve_tudo(cliente):
    corpo = cliente.get("/conversas").json()
    assert {linha["id"] for linha in corpo} == {"d1", "n1", "p1", "s1"}


def test_conversas_recorta_pelas_duas_pontas_inclusivas(cliente):
    corpo = cliente.get("/conversas", params={"de": "2026-08-02", "ate": "2026-08-03"}).json()
    assert {linha["id"] for linha in corpo} == {"n1", "p1", "s1"}


def test_conversas_com_uma_ponta_so(cliente):
    corpo = cliente.get("/conversas", params={"ate": "2026-08-01"}).json()
    assert {linha["id"] for linha in corpo} == {"d1"}


def test_conversas_data_malformada_e_400_nomeando_o_parametro(cliente):
    resposta = cliente.get("/conversas", params={"de": "01/08/2026"})
    assert resposta.status_code == 400
    assert "de" in resposta.json()["detail"]


def test_conversas_periodo_invertido_e_400(cliente):
    resposta = cliente.get(
        "/conversas", params={"de": "2026-08-03", "ate": "2026-08-01"}
    )
    assert resposta.status_code == 400


# ---------------------------------------------------------------------------
# GET /indicadores?de=&ate=
# ---------------------------------------------------------------------------


def test_indicadores_sem_filtro_cobrem_o_banco_inteiro(cliente):
    corpo = cliente.get("/indicadores").json()
    assert corpo["total_conversas"] == 4
    assert corpo["sem_sinal"] == 1


def test_indicadores_recortados_respondem_so_pelo_periodo(cliente):
    corpo = cliente.get(
        "/indicadores", params={"de": "2026-08-03", "ate": "2026-08-03"}
    ).json()
    # So p1 (promotor) e s1 (sem sinal) comecam no dia 03.
    assert corpo["total_conversas"] == 2
    assert corpo["sem_sinal"] == 1
    assert corpo["nps"] == 100.0
    assert corpo["csat"] == 100.0


def test_indicadores_data_malformada_e_400(cliente):
    resposta = cliente.get("/indicadores", params={"ate": "amanha"})
    assert resposta.status_code == 400
    assert "ate" in resposta.json()["detail"]


def test_indicadores_trazem_tempo_mediano_derivado_dos_timestamps(cliente):
    corpo = cliente.get("/indicadores").json()
    # Toda conversa da fixture tem exatamente um par cliente -> resposta de 30 s.
    assert corpo["tempo_mediano_resposta_s"] == 30.0


def test_tempo_mediano_sem_par_e_null_nunca_zero(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    # Uma conversa so do bot: nenhum par cliente -> resposta.
    conversa = Conversa(
        id="mudo",
        canal="webchat",
        iniciada_em=_quando("2026-08-01"),
        mensagens=[
            Mensagem(autor="bot", texto="ola", enviada_em=_quando("2026-08-01")),
        ],
    )
    banco.salvar(conversa, None, None)
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    corpo = TestClient(app).get("/indicadores").json()
    assert corpo["tempo_mediano_resposta_s"] is None


# ---------------------------------------------------------------------------
# GET /lexico?de=&ate=
# ---------------------------------------------------------------------------


def test_lexico_agrega_por_categoria_com_distincao(cliente):
    corpo = cliente.get("/lexico").json()
    por_categoria = {classe["categoria"]: classe for classe in corpo["classes"]}
    assert set(por_categoria) == {"detrator", "neutro", "promotor"}

    detrator = por_categoria["detrator"]
    assert detrator["atendimentos"] == 1
    termos = {item["termo"] for item in detrator["palavras"]}
    assert "pessimo" in termos
    for item in detrator["palavras"]:
        assert item["ocorrencias"] >= 1
        assert -1.0 <= item["distincao"] <= 1.0

    promotor = por_categoria["promotor"]
    assert {item["termo"] for item in promotor["emojis"]} == {"😍"}


def test_lexico_recortado_ignora_conversa_fora_do_periodo(cliente):
    corpo = cliente.get("/lexico", params={"de": "2026-08-02"}).json()
    por_categoria = {classe["categoria"]: classe for classe in corpo["classes"]}
    # d1 (01/08) ficou fora: a classe detrator existe, mas vazia.
    assert por_categoria["detrator"]["atendimentos"] == 0
    assert por_categoria["detrator"]["palavras"] == []


def test_lexico_data_malformada_e_400(cliente):
    resposta = cliente.get("/lexico", params={"de": "ontem"})
    assert resposta.status_code == 400
