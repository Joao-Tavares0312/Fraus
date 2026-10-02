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


def test_contrato_de_hierarquia_na_criacao_listagem_edicao_e_promocao(ambiente):
    cli, banco, h, u = ambiente
    pedido = {"nome": "Suporte", "membros": [u["usuario"]], "canais": ["chat"]}
    criada = cli.post("/operacao/equipes", headers=h["dev"], json=pedido).json()
    eid = criada["id"]
    assert criada["meu_papel"] == "proprietario"
    assert {m["id"] for m in criada["integrantes"]} == {u["dev"], u["usuario"]}
    assert cli.get("/operacao/equipes", headers=h["dev"]).json()["equipes"][0] == criada
    editada = cli.put(f"/operacao/equipes/{eid}", headers=h["dev"], json={**pedido, "nome": "Suporte novo", "membros": criada["membros"]}).json()
    assert editada["integrantes"] == criada["integrantes"]
    promovida = cli.patch(f"/operacao/equipes/{eid}/membros/{u['usuario']}", headers=h["dev"], json={"papel": "gestor"}).json()
    assert next(m for m in promovida["integrantes"] if m["id"] == u["usuario"])["papel"] == "gestor"
    propria = cli.get("/operacao/equipes", headers=h["usuario"]).json()["equipes"][0]
    assert propria["meu_papel"] == "gestor"
    assert propria["integrantes"] == promovida["integrantes"]
    # Uma equipe gravada antes da hierarquia recebe os campos na leitura;
    # nomes e papeis nao sao inventados pelo navegador.
    banco.guardar_documento("equipe", "antiga", {**pedido, "competencias": []})
    antiga = next(e for e in cli.get("/operacao/equipes", headers=h["dev"]).json()["equipes"] if e["id"] == "antiga")
    assert antiga["meu_papel"] == "proprietario"
    assert antiga["integrantes"][0]["id"] == u["usuario"]
    assert antiga["integrantes"][0]["papel"] == "membro"


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


def entrar_sem_convite(cli, email):
    corpo = {"nome": "Ja tinha conta", "email": email, "senha": "senha-convidada-123"}
    assert cli.post("/auth/registrar", json=corpo).status_code == 201
    entrada = cli.post("/auth/entrar", json={"email": email, "senha": corpo["senha"]})
    return {"Authorization": "Bearer " + entrada.json()["token"]}


def test_ultimo_uso_nao_e_consumido_por_duas_pessoas_ao_mesmo_tempo(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    ho = entrar_sem_convite(cli, "outra@empresa.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(lambda cab: cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=cab).status_code, [h["usuario"], ho]))
    assert sorted(respostas) == [200, 410]
    assert len(banco.documento("convite", c["id"])["aceitos"]) == 1
    assert len(banco.documento("equipe", eid)["membros"]) == 2


def cadastro_por_convite(cli, token, email):
    return cli.post("/auth/registrar", json={"nome": "Pessoa convidada", "email": email, "senha": "senha-convidada-123", "convite_equipe": token})


def test_convite_de_um_uso_cria_uma_conta_so(ambiente):
    """Ate 02/10/2026 o uso so era contado no aceite: o link de limite 1 criava
    quantas contas alguem quisesse, numa instalacao fechada por codigo."""
    cli, banco, h, u = ambiente
    cli.app.state.contexto = replace(cli.app.state.contexto, codigo_convite="instalacao-fechada")
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    assert cadastro_por_convite(cli, c["token"], "primeira@empresa.com").status_code == 201
    segunda = cadastro_por_convite(cli, c["token"], "segunda@empresa.com")
    assert segunda.status_code == 410
    assert banco.buscar_usuario_por_email("segunda@empresa.com") is None
    assert cli.get(f"/operacao/convites/{c['token']}").status_code == 410
    usos = cli.get(f"/operacao/equipes/{eid}/convites", headers=h["dev"]).json()["convites"][0]["usos"]
    assert usos == 1


def test_quem_se_cadastrou_pelo_convite_ainda_ve_e_aceita_o_convite(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    nova, hn = registrar(cli, c["token"])
    # A vaga e de quem se cadastrou: outra conta nao entra no lugar dela.
    assert cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=h["usuario"]).status_code == 410
    # O cadastro reserva; quem filia e o aceite, com sessao (contrato de 30/09).
    assert cli.get("/conversas", headers=hn).json() == []
    assert cli.get(f"/operacao/convites/{c['token']}", headers=hn).status_code == 200
    aceite = cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=hn)
    assert aceite.status_code == 200 and aceite.json()["ja_membro"] is False
    convite = banco.documento("convite", c["id"])
    assert convite["aceitos"] == [nova["id"]] and convite["reservas"] == []
    assert cli.get(f"/operacao/equipes/{eid}/convites", headers=h["dev"]).json()["convites"][0]["usos"] == 1


def test_dois_cadastros_ao_mesmo_tempo_nao_dividem_o_ultimo_uso(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(lambda email: cadastro_por_convite(cli, c["token"], email).status_code, ["a@empresa.com", "b@empresa.com"]))
    assert sorted(respostas) == [201, 410]
    assert len(banco.documento("convite", c["id"])["reservas"]) == 1


def test_limite_maior_conta_cadastros_e_aceites_juntos(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid, limite=2)
    assert cli.post(f"/operacao/convites/{c['token']}/aceitar", headers=h["usuario"]).status_code == 200
    assert cadastro_por_convite(cli, c["token"], "a@empresa.com").status_code == 201
    assert cadastro_por_convite(cli, c["token"], "b@empresa.com").status_code == 410


def test_email_repetido_nao_gasta_o_uso_do_convite(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    assert cadastro_por_convite(cli, c["token"], "usuario@empresa.com").status_code == 409
    assert banco.documento("convite", c["id"]).get("reservas", []) == []
    assert cadastro_por_convite(cli, c["token"], "nova@empresa.com").status_code == 201


def test_convite_gravado_antes_das_reservas_continua_valendo(ambiente):
    cli, banco, h, u = ambiente
    eid = criar_equipe(cli, h)
    c = convidar(cli, h["dev"], eid)
    antigo = banco.documento("convite", c["id"])
    antigo.pop("reservas", None)
    banco.guardar_documento("convite", c["id"], antigo)
    assert cli.get(f"/operacao/convites/{c['token']}").status_code == 200
    assert cadastro_por_convite(cli, c["token"], "nova@empresa.com").status_code == 201
    assert cadastro_por_convite(cli, c["token"], "outra@empresa.com").status_code == 410