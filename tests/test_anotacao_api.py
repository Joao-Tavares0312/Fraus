"""Anotacao as cegas da regua de ironia DENTRO do Fraus.

Quem anota nao tem conta: recebe um link com token opaco, como o convite de
equipe. Por isso duas rotas sao PUBLICAS (ler a propria fila, gravar resposta)
e duas sao so de dev (criar anotador, exportar respostas). A colisao de nome
entre `/anotacao/respostas` (fixa, dev) e `/anotacao/{token}` (publica) e o
que estes testes mais vigiam: uma isencao larga demais no middleware abriria
a exportacao para qualquer um.
"""

import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.avaliacao_ironia import carregar_rascunho
from fraus.db import Banco
from tests.test_api import MotorFalso

SEGREDO_JWT = "segredo-jwt-de-teste-bem-longo"
MESTRA = "mestra-de-teste-com-entropia-suficiente"
DEV = {"Authorization": f"Bearer {MESTRA}"}


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


def criar_anotador(cliente) -> dict:
    resposta = cliente.post("/anotacao/anotadores", headers=DEV)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def token_de_usuario(cliente) -> str:
    corpo = {"nome": "Ana", "email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    assert cliente.post("/auth/registrar", json=corpo).status_code == 201
    return cliente.post("/auth/entrar", json={"email": corpo["email"], "senha": corpo["senha"]}).json()["token"]


def uma_frase() -> str:
    return carregar_rascunho()[0].frase_id


# ---- criar anotador (dev) -------------------------------------------------


def test_criar_anotador_devolve_token_uma_vez_e_guarda_so_o_hash(cliente, banco):
    corpo = criar_anotador(cliente)
    assert set(corpo) == {"anotador", "token"}
    assert re.fullmatch(r"a_[0-9a-f]{8}", corpo["anotador"])
    assert len(corpo["token"]) >= 40
    guardado = banco.documento("anotador_regua", hashlib.sha256(corpo["token"].encode()).hexdigest())
    assert guardado["anotador"] == corpo["anotador"]
    assert guardado["revogado"] is False
    assert "criado_em" in guardado
    assert corpo["token"] not in json.dumps(banco.documentos("anotador_regua"))


def test_criar_anotador_sem_credencial_e_401(cliente):
    assert cliente.post("/anotacao/anotadores").status_code == 401


def test_criar_anotador_com_jwt_de_usuario_e_403(cliente):
    token = token_de_usuario(cliente)
    resposta = cliente.post("/anotacao/anotadores", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 403


# ---- ler a fila (publica) -------------------------------------------------


def test_fila_e_publica_e_nao_entrega_o_rotulo(cliente):
    token = criar_anotador(cliente)["token"]
    resposta = cliente.get(f"/anotacao/{token}")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {"frases", "respostas"}
    assert len(corpo["frases"]) == 300
    assert all(set(f) == {"id", "texto"} for f in corpo["frases"])
    assert corpo["respostas"] == {}
    bruto = resposta.text
    for proibido in ("par_id", "estrato", "rotulo", "dominio", '"g"'):
        assert proibido not in bruto


def test_cada_anotador_tem_a_propria_ordem(cliente):
    a = cliente.get(f"/anotacao/{criar_anotador(cliente)['token']}").json()["frases"]
    b = cliente.get(f"/anotacao/{criar_anotador(cliente)['token']}").json()["frases"]
    assert [f["id"] for f in a] != [f["id"] for f in b]
    assert sorted(f["id"] for f in a) == sorted(f["id"] for f in b)


def test_token_inexistente_e_revogado_dao_o_mesmo_404(cliente, banco):
    token = criar_anotador(cliente)["token"]
    banco.alterar_documento(
        "anotador_regua", hashlib.sha256(token.encode()).hexdigest(),
        lambda d: {**d, "revogado": True},
    )
    revogado = cliente.get(f"/anotacao/{token}")
    inexistente = cliente.get("/anotacao/nao-existe-este-token")
    assert revogado.status_code == inexistente.status_code == 404
    assert revogado.json() == inexistente.json()


# ---- gravar resposta (publica) --------------------------------------------


def test_resposta_gravada_volta_na_fila_e_a_ultima_vence(cliente):
    token = criar_anotador(cliente)["token"]
    frase = uma_frase()
    primeira = cliente.post(f"/anotacao/{token}/respostas", json={"frase_id": frase, "resposta": "ironico"})
    assert primeira.status_code == 201
    cliente.post(f"/anotacao/{token}/respostas", json={"frase_id": frase, "resposta": "contexto"})
    assert cliente.get(f"/anotacao/{token}").json()["respostas"] == {frase: "contexto"}


def test_resposta_de_um_anotador_nao_aparece_para_outro(cliente):
    um, outro = criar_anotador(cliente)["token"], criar_anotador(cliente)["token"]
    cliente.post(f"/anotacao/{um}/respostas", json={"frase_id": uma_frase(), "resposta": "ironico"})
    assert cliente.get(f"/anotacao/{outro}").json()["respostas"] == {}


def test_resposta_com_token_invalido_e_404(cliente):
    resposta = cliente.post("/anotacao/lixo/respostas", json={"frase_id": uma_frase(), "resposta": "ironico"})
    assert resposta.status_code == 404


@pytest.mark.parametrize("corpo", [
    {"frase_id": "frase-que-nao-existe", "resposta": "ironico"},
    {"frase_id": "PLACEHOLDER", "resposta": "valor-proibido-xyz"},
    {"frase_id": "PLACEHOLDER", "resposta": "ironico", "instante": "1999-01-01T00:00:00Z"},
    {"frase_id": "PLACEHOLDER", "resposta": "ironico", "campo-inventado-xyz": 1},
    {"frase_id": "PLACEHOLDER"},
    ["lista-no-lugar-do-objeto"],
])
def test_corpo_invalido_e_422_sem_devolver_o_que_veio(cliente, corpo):
    token = criar_anotador(cliente)["token"]
    if isinstance(corpo, dict):
        corpo = {k: (uma_frase() if v == "PLACEHOLDER" else v) for k, v in corpo.items()}
    resposta = cliente.post(f"/anotacao/{token}/respostas", json=corpo)
    assert resposta.status_code == 422
    for proibido in ("frase-que-nao-existe", "valor-proibido-xyz", "1999-01-01",
                     "campo-inventado-xyz", "lista-no-lugar"):
        assert proibido not in resposta.text


def test_json_malformado_e_422_sem_ecoar_o_corpo(cliente):
    token = criar_anotador(cliente)["token"]
    resposta = cliente.post(
        f"/anotacao/{token}/respostas", content=b'{"segredo-cru": ',
        headers={"Content-Type": "application/json"},
    )
    assert resposta.status_code == 422
    assert "segredo-cru" not in resposta.text


def test_servidor_carimba_o_instante_em_utc(cliente):
    token = criar_anotador(cliente)["token"]
    cliente.post(f"/anotacao/{token}/respostas", json={"frase_id": uma_frase(), "resposta": "ironico"})
    [registro] = cliente.get("/anotacao/respostas", headers=DEV).json()
    assert registro["instante"].endswith("+00:00")


def test_vazao_por_token_corta_em_429_com_retry_after(cliente):
    token = criar_anotador(cliente)["token"]
    outro = criar_anotador(cliente)["token"]
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    for _ in range(60):
        assert cliente.post(f"/anotacao/{token}/respostas", json=corpo).status_code == 201
    barrada = cliente.post(f"/anotacao/{token}/respostas", json=corpo)
    assert barrada.status_code == 429
    assert int(barrada.headers["Retry-After"]) >= 1
    assert cliente.post(f"/anotacao/{outro}/respostas", json=corpo).status_code == 201


# ---- exportar (dev) -------------------------------------------------------


def test_exportar_sem_credencial_e_401_mesmo_parecendo_token(cliente):
    assert cliente.get("/anotacao/respostas").status_code == 401
    assert cliente.get("/anotacao/respostas/").status_code == 401


def test_exportar_com_jwt_de_usuario_e_403(cliente):
    token = token_de_usuario(cliente)
    resposta = cliente.get("/anotacao/respostas", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 403


def test_exportar_devolve_registros_no_formato_da_consolidacao(cliente):
    criado = criar_anotador(cliente)
    frase = uma_frase()
    cliente.post(f"/anotacao/{criado['token']}/respostas", json={"frase_id": frase, "resposta": "ironico"})
    cliente.post(f"/anotacao/{criado['token']}/respostas", json={"frase_id": frase, "resposta": "nao_ironico"})
    registros = cliente.get("/anotacao/respostas", headers=DEV).json()
    assert len(registros) == 2
    assert all(set(r) == {"anotador", "frase_id", "resposta", "instante"} for r in registros)
    assert {r["anotador"] for r in registros} == {criado["anotador"]}
    assert [r["instante"] for r in registros] == sorted(r["instante"] for r in registros)
    from fraus.consolidacao_regua import ultimas_respostas
    assert ultimas_respostas(registros) == {frase: ["nao_ironico"]}
