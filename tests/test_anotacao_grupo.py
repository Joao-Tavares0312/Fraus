"""Link de GRUPO: um link so, postado num grupo, que da a cada pessoa o seu
anotador. Vagas contadas com leitura-e-escrita serializada no banco: cinco
vagas nao podem virar seis com cliques simultaneos."""

import hashlib
import threading

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_anotacao_api import DEV, MESTRA, SEGREDO_JWT, criar_anotador, token_de_usuario, uma_frase
from tests.test_api import MotorFalso


@pytest.fixture
def banco(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


@pytest.fixture
def cliente(banco, tmp_path):
    return TestClient(criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=MESTRA, jwt_segredo=SEGREDO_JWT,
    ))


def criar_grupo(cliente, vagas=5) -> dict:
    resposta = cliente.post("/anotacao/grupos", json={"vagas": vagas}, headers=DEV)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def entrar(cliente, token):
    return cliente.post(f"/anotacao/grupos/{token}/entrar")


def sha(token):
    return hashlib.sha256(token.encode()).hexdigest()


# ---- criar grupo (dev) ------------------------------------------------------


def test_criar_grupo_devolve_token_uma_vez_e_guarda_so_o_hash(cliente, banco):
    corpo = criar_grupo(cliente, 5)
    assert set(corpo) == {"grupo", "token"}
    assert corpo["grupo"].startswith("g_") and len(corpo["grupo"]) == 10
    guardado = banco.documento("grupo_regua", sha(corpo["token"]))
    assert guardado["grupo"] == corpo["grupo"]
    assert guardado["vagas"] == 5 and guardado["anotadores"] == [] and guardado["revogado"] is False
    assert "criado_em" in guardado


@pytest.mark.parametrize("corpo", [
    {"vagas": 0}, {"vagas": 21}, {"vagas": "5"}, {"vagas": True}, {},
    {"vagas": 5, "campo-inventado-xyz": 1}, ["lista-no-lugar"],
])
def test_criar_grupo_com_corpo_invalido_e_422_sem_eco(cliente, corpo):
    resposta = cliente.post("/anotacao/grupos", json=corpo, headers=DEV)
    assert resposta.status_code == 422
    assert "campo-inventado-xyz" not in resposta.text and "lista-no-lugar" not in resposta.text


def test_criar_grupo_exige_dev(cliente):
    assert cliente.post("/anotacao/grupos", json={"vagas": 5}).status_code == 401
    token = token_de_usuario(cliente)
    resposta = cliente.post("/anotacao/grupos", json={"vagas": 5}, headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 403


# ---- entrar (publica) -------------------------------------------------------


def test_entrar_cria_anotador_proprio_que_funciona(cliente, banco):
    grupo = criar_grupo(cliente, 2)
    resposta = entrar(cliente, grupo["token"])
    assert resposta.status_code == 201
    assert set(resposta.json()) == {"token"}
    pessoal = resposta.json()["token"]
    assert pessoal != grupo["token"]
    anotador = banco.documento("anotador_regua", sha(pessoal))
    assert anotador["grupo"] == grupo["grupo"] and anotador["revogado"] is False
    assert banco.documento("grupo_regua", sha(grupo["token"]))["anotadores"] == [anotador["anotador"]]
    assert cliente.get(f"/anotacao/{pessoal}").status_code == 200
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    assert cliente.post(f"/anotacao/{pessoal}/respostas", json=corpo).status_code == 201


def test_cada_entrada_e_um_anotador_diferente_e_o_grupo_lota(cliente):
    grupo = criar_grupo(cliente, 2)
    a, b = entrar(cliente, grupo["token"]).json()["token"], entrar(cliente, grupo["token"]).json()["token"]
    assert a != b
    cheio = entrar(cliente, grupo["token"])
    assert cheio.status_code == 409
    assert cheio.json() == {"detail": "este link de grupo ja esta cheio"}


def test_grupo_inexistente_e_revogado_dao_o_mesmo_404(cliente):
    grupo = criar_grupo(cliente)
    assert cliente.post(f"/anotacao/grupos/{grupo['grupo']}/revogar", headers=DEV).status_code == 200
    revogado, inexistente = entrar(cliente, grupo["token"]), entrar(cliente, "nao-existe")
    assert revogado.status_code == inexistente.status_code == 404
    assert revogado.json() == inexistente.json()


def test_entrar_tem_teto_por_token_do_grupo(cliente):
    from fraus.api.vazao import ENTRADAS_DE_GRUPO_POR_JANELA
    for _ in range(ENTRADAS_DE_GRUPO_POR_JANELA):
        assert entrar(cliente, "inventado").status_code == 404
    barrada = entrar(cliente, "inventado")
    assert barrada.status_code == 429
    assert int(barrada.headers["Retry-After"]) >= 1
    assert entrar(cliente, "outro-inventado").status_code == 404


def test_vagas_nao_estouram_com_entradas_simultaneas(banco, tmp_path):
    from fraus.api.rotas.anotacao import ocupar_vaga
    banco.guardar_documento("grupo_regua", "h", {"grupo": "g_1", "vagas": 5, "anotadores": [], "revogado": False})
    resultados = []

    def tentar(i):
        try:
            ocupar_vaga(banco, "h", f"a_{i:08x}")
            resultados.append("ok")
        except Exception as erro:  # noqa: BLE001 -- o teste conta as recusas
            resultados.append(getattr(erro, "status_code", repr(erro)))

    linhas = [threading.Thread(target=tentar, args=(i,)) for i in range(12)]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    assert resultados.count("ok") == 5
    assert resultados.count(409) == 7
    assert len(banco.documento("grupo_regua", "h")["anotadores"]) == 5


# ---- revogar (dev) ----------------------------------------------------------


def test_revogar_grupo_so_fecha_a_entrada_por_padrao(cliente):
    grupo = criar_grupo(cliente)
    pessoal = entrar(cliente, grupo["token"]).json()["token"]
    resposta = cliente.post(f"/anotacao/grupos/{grupo['grupo']}/revogar", headers=DEV)
    assert resposta.json() == {"grupo": grupo["grupo"], "revogado": True, "anotadores_revogados": 0}
    assert entrar(cliente, grupo["token"]).status_code == 404
    assert cliente.get(f"/anotacao/{pessoal}").status_code == 200


def test_revogar_grupo_com_anotadores_tira_as_respostas_do_export(cliente):
    grupo = criar_grupo(cliente)
    pessoal = entrar(cliente, grupo["token"]).json()["token"]
    avulso = criar_anotador(cliente)
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    for token in (pessoal, avulso["token"]):
        assert cliente.post(f"/anotacao/{token}/respostas", json=corpo).status_code == 201
    resposta = cliente.post(f"/anotacao/grupos/{grupo['grupo']}/revogar?anotadores=1", headers=DEV)
    assert resposta.json()["anotadores_revogados"] == 1
    assert cliente.get(f"/anotacao/{pessoal}").status_code == 404
    registros = cliente.get("/anotacao/respostas", headers=DEV).json()
    assert {r["anotador"] for r in registros} == {avulso["anotador"]}


def test_revogar_grupo_desconhecido_e_404(cliente):
    assert cliente.post("/anotacao/grupos/g_00000000/revogar", headers=DEV).status_code == 404


# ---- isencao no middleware --------------------------------------------------


@pytest.mark.parametrize("metodo,caminho", [
    ("POST", "/anotacao/grupos"),
    ("POST", "/anotacao/%67rupos"),
    ("POST", "//anotacao/grupos"),
    ("POST", "/anotacao/grupos/g_00000000/revogar"),
    ("POST", "/anotacao/%67rupos/g_00000000/revogar"),
    ("POST", "//anotacao/grupos/g_00000000/revogar"),
    ("GET", "/anotacao/grupos"),
    ("GET", "/anotacao/grupos/tok/entrar"),
])
def test_rotas_de_dev_do_grupo_exigem_credencial(cliente, metodo, caminho):
    assert cliente.request(metodo, caminho).status_code == 401


def test_isencao_casa_so_o_entrar_do_grupo():
    from fraus.api.seguranca import rota_administrativa, rota_publica_de_anotacao
    assert rota_publica_de_anotacao("POST", "/anotacao/grupos/tok/entrar")
    for metodo, caminho in (
        ("POST", "/anotacao/grupos//entrar"),
        ("GET", "/anotacao/grupos/tok/entrar"),
        ("POST", "/anotacao/grupos/tok/revogar"),
        ("POST", "/anotacao/grupos/tok/entrar/mais"),
        ("POST", "/anotacao/grupos"),
        ("GET", "/anotacao/grupos"),
    ):
        assert not rota_publica_de_anotacao(metodo, caminho), (metodo, caminho)
    assert rota_administrativa("POST", "/anotacao/grupos")
    assert rota_administrativa("POST", "/anotacao/grupos/g_1/revogar")
