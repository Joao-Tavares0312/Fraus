"""Sinalizadores na leitura: lista e detalhe pelo mesmo caminho, filtro que
pagina DEPOIS de filtrar, escopo por canal e nenhum efeito no score."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso

T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)


def _conv(cid, *falas, canal="chat"):
    return Conversa(id=cid, canal=canal, iniciada_em=T0, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k))
        for k, (a, t) in enumerate(falas)])


def abandonada(cid, canal="chat"):
    return _conv(cid, ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"), canal=canal)


def fechada(cid):
    return _conv(cid, ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"),
                 ("cliente", "valeu"))


def sem_cliente(cid):
    return _conv(cid, ("bot", "ola, posso ajudar?"))


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "fraus.db")
    b.migrar()
    return b


@pytest.fixture
def cliente(banco, tmp_path):
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))


def test_lista_e_detalhe_trazem_os_mesmos_sinalizadores(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    linha = cliente.get("/conversas").json()[0]
    detalhe = cliente.get("/conversas/a").json()
    assert [s["regra"] for s in linha["sinalizadores"]] == ["abandono"]
    assert detalhe["sinalizadores"] == linha["sinalizadores"]


def test_sem_fala_do_cliente_e_null_e_nao_lista(cliente, banco):
    banco.salvar(sem_cliente("s"), None, None)
    assert cliente.get("/conversas").json()[0]["sinalizadores"] is None


def test_filtro_por_regra(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    banco.salvar(fechada("f"), 80.0, "neutro")
    banco.salvar(sem_cliente("s"), None, None)
    ids = [l["id"] for l in cliente.get("/conversas?sinalizador=abandono").json()]
    assert ids == ["a"]


def test_filtro_pagina_depois_de_filtrar(cliente, banco):
    for cid in ("f1", "a1", "f2", "a2", "f3"):
        banco.salvar(abandonada(cid) if cid.startswith("a") else fechada(cid), 50.0, "detrator")
    todas = [l["id"] for l in cliente.get("/conversas?sinalizador=abandono").json()]
    assert sorted(todas) == ["a1", "a2"]
    pagina2 = cliente.get("/conversas?sinalizador=abandono&limite=1&deslocamento=1").json()
    assert [l["id"] for l in pagina2] == todas[1:2]


def test_regra_desconhecida_e_400(cliente):
    r = cliente.get("/conversas?sinalizador=nota_do_atendente")
    assert r.status_code == 400
    assert "abandono" in r.json()["detail"]


def test_score_e_categoria_intactos(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    antes = cliente.get("/conversas").json()[0]
    cliente.get("/conversas?sinalizador=abandono")
    depois = cliente.get("/conversas").json()[0]
    assert (antes["score"], antes["nota"], antes["categoria"]) == (
        depois["score"], depois["nota"], depois["categoria"])
    assert depois["score"] == 40.0


def test_filtro_nao_vaza_canal_fora_do_escopo(tmp_path):
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    banco.salvar(abandonada("a", canal="chat"), 40.0, "detrator")
    banco.salvar(abandonada("b", canal="email"), 40.0, "detrator")
    app = criar_app(banco, MotorFalso(), raiz_importacao=tmp_path,
                    chave_mestra="chave-teste-operacao",
                    jwt_segredo="segredo-jwt-de-teste-operacao-123456",
                    codigo_dev="convite-dev-teste")
    cli = TestClient(app)
    headers, ids = {}, {}
    for papel in ("dev", "usuario"):
        cad = {"nome": papel, "email": f"{papel}@empresa.com", "senha": "senha-teste-longa-123"}
        if papel == "dev":
            cad["codigo_dev"] = "convite-dev-teste"
        ids[papel] = cli.post("/auth/registrar", json=cad).json()["id"]
        token = cli.post("/auth/entrar", json={"email": cad["email"], "senha": cad["senha"]}).json()["token"]
        headers[papel] = {"Authorization": "Bearer " + token}
    assert cli.put(f"/operacao/acesso/{ids['usuario']}", headers=headers["dev"],
                   json={"canais": ["chat"]}).status_code == 200
    vistos = [l["id"] for l in cli.get("/conversas?sinalizador=abandono", headers=headers["usuario"]).json()]
    assert vistos == ["a"]
