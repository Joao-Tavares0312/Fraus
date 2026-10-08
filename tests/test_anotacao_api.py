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


def test_fila_e_a_ordem_do_anotador_dono_do_link(cliente, banco):
    """A rota serve `ordem_do_anotador` do id DESTE link; que ids distintos dao
    ordens distintas e conferido com ids fixos, sem depender do sorteio."""
    from fraus.anotacao_regua import ordem_do_anotador
    criado = criar_anotador(cliente)
    frases = cliente.get(f"/anotacao/{criado['token']}").json()["frases"]
    assert frases == ordem_do_anotador(carregar_rascunho(), criado["anotador"])


def test_ids_fixos_dao_ordens_distintas_com_as_mesmas_frases():
    from fraus.anotacao_regua import ordem_do_anotador
    rascunho = carregar_rascunho()
    a = [f["id"] for f in ordem_do_anotador(rascunho, "a_00000001")]
    b = [f["id"] for f in ordem_do_anotador(rascunho, "a_00000002")]
    assert a != b
    assert sorted(a) == sorted(b)


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


# ---- teto de volume, vazao da leitura e revogacao -------------------------


def test_link_que_ja_mandou_o_maximo_recebe_409(cliente, banco):
    from fraus.api.rotas.anotacao import MAXIMO_RESPOSTAS_POR_ANOTADOR
    criado = criar_anotador(cliente)
    frase = uma_frase()
    banco.guardar_documentos([
        ("resposta_regua", f"{criado['anotador']}:{i}", {
            "anotador": criado["anotador"], "frase_id": frase, "resposta": "ironico",
            "instante": f"2026-10-08T10:00:00.{i:06d}+00:00"})
        for i in range(MAXIMO_RESPOSTAS_POR_ANOTADOR)
    ])
    corpo = {"frase_id": frase, "resposta": "contexto"}
    barrada = cliente.post(f"/anotacao/{criado['token']}/respostas", json=corpo)
    assert barrada.status_code == 409
    assert barrada.json() == {"detail": "este link ja mandou o maximo de respostas"}
    outro = criar_anotador(cliente)["token"]
    assert cliente.post(f"/anotacao/{outro}/respostas", json=corpo).status_code == 201


def test_teto_e_cinco_respostas_por_frase():
    from fraus.api.rotas.anotacao import MAXIMO_RESPOSTAS_POR_ANOTADOR
    assert MAXIMO_RESPOSTAS_POR_ANOTADOR == 5 * len(carregar_rascunho()) == 1500


def test_leitura_publica_tem_teto_por_token_e_nao_por_ip(cliente):
    """Atras do proxy da dashboard todo anotador chega com o MESMO IP; contar
    por IP poria todos numa janela so. Conta pelo hash do token."""
    from fraus.api.vazao import LEITURAS_DE_ANOTACAO_POR_JANELA
    token, outro = criar_anotador(cliente)["token"], criar_anotador(cliente)["token"]
    for _ in range(LEITURAS_DE_ANOTACAO_POR_JANELA):
        assert cliente.get(f"/anotacao/{token}").status_code == 200
    barrada = cliente.get(f"/anotacao/{token}")
    assert barrada.status_code == 429
    assert int(barrada.headers["Retry-After"]) >= 1
    assert "aguarde" in barrada.json()["detail"]
    assert cliente.get(f"/anotacao/{outro}").status_code == 200


def test_token_inventado_tambem_tem_teto_na_leitura_e_na_escrita(cliente):
    from fraus.api.vazao import LEITURAS_DE_ANOTACAO_POR_JANELA, RESPOSTAS_DE_ANOTACAO_POR_JANELA
    for _ in range(LEITURAS_DE_ANOTACAO_POR_JANELA):
        assert cliente.get("/anotacao/inventado").status_code == 404
    assert cliente.get("/anotacao/inventado").status_code == 429
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    for _ in range(RESPOSTAS_DE_ANOTACAO_POR_JANELA):
        assert cliente.post("/anotacao/inventado/respostas", json=corpo).status_code == 404
    assert cliente.post("/anotacao/inventado/respostas", json=corpo).status_code == 429


def test_export_deixa_de_fora_anotador_revogado(cliente):
    fica, sai = criar_anotador(cliente), criar_anotador(cliente)
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    for criado in (fica, sai):
        assert cliente.post(f"/anotacao/{criado['token']}/respostas", json=corpo).status_code == 201
    cliente.post(f"/anotacao/anotadores/{sai['anotador']}/revogar", headers=DEV)
    registros = cliente.get("/anotacao/respostas", headers=DEV).json()
    assert {r["anotador"] for r in registros} == {fica["anotador"]}


@pytest.mark.parametrize("metodo,caminho", [
    ("GET", "/anotacao/%72espostas"),
    ("GET", "/anotacao/respostas%2F"),
    ("GET", "//anotacao/respostas"),
    ("HEAD", "/anotacao/respostas"),
    ("POST", "/anotacao/%61notadores"),
    ("POST", "/anotacao/anotadores/a_00000000/revogar"),
])
def test_variantes_das_rotas_de_dev_nao_escapam_da_credencial(cliente, metodo, caminho):
    assert cliente.request(metodo, caminho).status_code == 401


# ---- Banco: so as respostas de UM anotador --------------------------------


def _resposta(anotador, i):
    return ("resposta_regua", f"{anotador}:f{i}:2026-10-08T10:00:00.{i:06d}+00:00:abc123",
            {"anotador": anotador, "frase_id": f"f{i}", "resposta": "ironico",
             "instante": f"2026-10-08T10:00:00.{i:06d}+00:00"})


def test_banco_le_e_conta_so_o_prefixo_do_anotador(banco):
    banco.guardar_documentos([_resposta("a_0000000a", i) for i in range(3)]
                             + [_resposta("a_0000000b", i) for i in range(2)]
                             # `_` e curinga do LIKE: "aX0000000a" casaria com
                             # um padrao sem escape.
                             + [_resposta("aX0000000a", 9)]
                             + [("anotador_regua", "a_0000000a:intruso", {"anotador": "x"})])
    linhas = banco.documentos_com_prefixo("resposta_regua", "a_0000000a:")
    assert sorted(l["frase_id"] for l in linhas) == ["f0", "f1", "f2"]
    assert banco.contar_documentos_com_prefixo("resposta_regua", "a_0000000a:") == 3
    assert banco.contar_documentos_com_prefixo("resposta_regua", "a_0000000b:") == 2
    assert banco.contar_documentos_com_prefixo("resposta_regua", "a_%:") == 0


def test_revogar_anotador_derruba_o_link(cliente):
    criado = criar_anotador(cliente)
    resposta = cliente.post(f"/anotacao/anotadores/{criado['anotador']}/revogar", headers=DEV)
    assert resposta.status_code == 200
    assert resposta.json() == {"anotador": criado["anotador"], "revogado": True}
    assert cliente.get(f"/anotacao/{criado['token']}").status_code == 404
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    assert cliente.post(f"/anotacao/{criado['token']}/respostas", json=corpo).status_code == 404


def test_revogar_anotador_desconhecido_e_404(cliente):
    assert cliente.post("/anotacao/anotadores/a_00000000/revogar", headers=DEV).status_code == 404


def test_revogar_exige_dev(cliente):
    criado = criar_anotador(cliente)
    caminho = f"/anotacao/anotadores/{criado['anotador']}/revogar"
    assert cliente.post(caminho).status_code == 401
    token = token_de_usuario(cliente)
    assert cliente.post(caminho, headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert cliente.get(f"/anotacao/{criado['token']}").status_code == 200


def test_isencao_publica_nao_casa_rotas_de_dev():
    from fraus.api.seguranca import rota_administrativa, rota_publica_de_anotacao
    for metodo, caminho in (
        ("POST", "/anotacao/anotadores/a_1/revogar"),
        ("POST", "/anotacao/anotadores"),
        ("GET", "/anotacao/respostas"),
        ("POST", "/anotacao/anotadores/respostas"),
        ("POST", "/anotacao/x/respostas/mais"),
    ):
        assert not rota_publica_de_anotacao(metodo, caminho), caminho
    assert rota_administrativa("POST", "/anotacao/anotadores/a_1/revogar")
    assert rota_publica_de_anotacao("GET", "/anotacao/tok")
    assert rota_publica_de_anotacao("POST", "/anotacao/tok/respostas")


def test_rotas_publicas_nao_carregam_as_respostas_de_todos(cliente, banco, monkeypatch):
    token = criar_anotador(cliente)["token"]
    original = banco.documentos

    def vigiado(tipo):
        assert tipo != "resposta_regua", "rota publica leu a tabela inteira de respostas"
        return original(tipo)

    monkeypatch.setattr(banco, "documentos", vigiado)
    corpo = {"frase_id": uma_frase(), "resposta": "ironico"}
    assert cliente.post(f"/anotacao/{token}/respostas", json=corpo).status_code == 201
    assert cliente.get(f"/anotacao/{token}").json()["respostas"] == {uma_frase(): "ironico"}


def test_limitador_esquece_identidades_cuja_janela_ja_passou():
    """Contar por hash de token abre uma identidade por token inventado; sem
    varredura, o dicionario cresceria para sempre."""
    from fraus.api.vazao import LimitadorDeVazao
    limitador = LimitadorDeVazao(tentativas=1, janela_s=60.0, varrer_acima_de=100)
    for i in range(100):
        limitador.permite(f"velho-{i}", agora=0.0)
    for i in range(50):
        limitador.permite(f"novo-{i}", agora=1000.0)
    assert len(limitador._historico) <= 150
    limitador.permite("gatilho", agora=1000.0)
    assert len(limitador._historico) == 51
    assert not limitador.permite("novo-0", agora=1000.0)
