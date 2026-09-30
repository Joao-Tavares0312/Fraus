"""Convites, hierarquia e cadastro restrito; sem token em texto no banco."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from dataclasses import replace

import pytest
from tests.test_operacao import ambiente


def criar_equipe(cli, h):
    r = cli.post("/operacao/equipes", headers=h["dev"], json={"nome": "Equipe financeira", "canais": ["chat"]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def convidar(cli, h, eid, papel="membro", limite=1):
    r = cli.post(f"/operacao/equipes/{eid}/convites", headers=h, json={"papel": papel, "validade_horas": 24, "limite": limite})
    assert r.status_code == 200, r.text
    return r.json()


def registrar(cli, token, email="nova@empresa.com"):
    r = cli.post("/auth/registrar", json={"nome": "Pessoa convidada", "email": email, "senha": "senha-convidada-123", "convite_equipe": token})
    assert r.status_code == 201, r.text
    entrada = cli.post("/auth/entrar", json={"email": email, "senha": "senha-convidada-123"})
    return r.json(), {"Authorization": "Bearer " + entrada.json()["token"]}


def test_convite_publico_cadastro_restrito_aceite_idempotente_e_remocao(ambiente):
    cli, banco, h, u = ambiente
    cli.app.state.contexto = replace(cli.app.state.contexto, codigo_convite="instalacao-fechada")
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    token = c["token"]
    assert banco.documento("convite", hashlib.sha256(token.encode()).hexdigest())
    assert token not in str(banco.documentos("convite")) and token not in str(banco.auditoria())
    assert cli.get(f"/operacao/convites/{token}").status_code == 200
    assert cli.post(f"/operacao/convites/{token}/aceitar").status_code == 401
    nova, hn = registrar(cli, token)
    assert nova["papel"] == "usuario"
    assert cli.get("/conversas", headers=hn).json() == []
    r = cli.post(f"/operacao/convites/{token}/aceitar", headers=hn)
    assert r.status_code == 200 and r.json()["papel"] == "membro"
    assert [c["id"] for c in cli.get("/conversas", headers=hn).json()] == ["c1"]
    assert cli.post(f"/operacao/convites/{token}/aceitar", headers=hn).json()["ja_membro"]
    assert cli.post(f"/operacao/convites/{token}/aceitar", headers=h["usuario"]).status_code == 410
    assert cli.get("/operacao/acesso", headers=hn).status_code == 403
    assert cli.post(f"/operacao/equipes/{eid}/convites", headers=hn, json={}).status_code == 403
    assert cli.patch(f"/operacao/equipes/{eid}/membros/{u['dev']}", headers=hn, json={"papel": None}).status_code == 403
    assert cli.patch(f"/operacao/equipes/{eid}/membros/{nova['id']}", headers=h["dev"], json={"papel": None}).status_code == 200
    assert cli.get("/conversas", headers=hn).json() == []


def test_gestor_convida_membro_mas_nao_promove_e_preserva_ultimo_proprietario(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid, "gestor")
    assert cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=h["usuario"]).status_code == 200
    assert cli.post(f"/operacao/equipes/{eid}/convites", headers=h["usuario"], json={"papel": "membro"}).status_code == 200
    assert cli.post(f"/operacao/equipes/{eid}/convites", headers=h["usuario"], json={"papel": "gestor"}).status_code == 403
    assert cli.patch(f"/operacao/equipes/{eid}/membros/{u['usuario']}", headers=h["usuario"], json={"papel": "proprietario"}).status_code == 403
    assert cli.patch(f"/operacao/equipes/{eid}/membros/{u['dev']}", headers=h["dev"], json={"papel": None}).status_code == 409


@pytest.mark.parametrize("modo", ["revogado", "expirado"])
def test_convite_indisponivel_nao_cadastra_nem_aceita(ambiente, modo):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    if modo == "revogado":
        assert cli.post(f"/operacao/equipes/{eid}/convites/{c['id']}/revogar", headers=h["dev"]).status_code == 200
    else:
        valor = banco.documento("convite", c["id"])
        valor["expira_em"] = "2000-01-01T00:00:00+00:00"
        banco.guardar_documento("convite", c["id"], valor)
    assert cli.get(f"/operacao/convites/{c['token']}").status_code == 410
    assert cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=h["usuario"]).status_code == 410
    assert cli.post("/auth/registrar", json={"nome": "Teste", "email": "a@empresa.com", "senha": "senha-convidada-123", "convite_equipe": c["token"]}).status_code == 410


def test_ultimo_uso_nao_e_consumido_por_duas_pessoas_ao_mesmo_tempo(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    nova, hn = registrar(cli, c["token"])
    outra, ho = registrar(cli, c["token"], "outra@empresa.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(lambda cab: cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=cab).status_code, [hn, ho]))
    assert sorted(respostas) == [200, 410]
    assert len(banco.documento("convite", c["id"])["aceitos"]) == 1
    assert len(banco.documento("equipe", eid)["membros"]) == 2
