"""As rotas de autenticacao de usuario: registrar, entrar, quem sou.

O cadastro nasce `usuario`; `dev` exige o codigo de convite que mora em
FRAUS_CODIGO_DEV -- privilegio se liga por decisao explicita do operador,
nunca por padrao. A mensagem de recusa do login e UNICA: distinguir "e-mail
nao existe" de "senha errada" contaria a quem tenta quais e-mails tem conta.
"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus import token_acesso
from fraus.api.main import criar_app
from fraus.db import Banco

SEGREDO_JWT = "segredo-jwt-de-teste"
CODIGO_DEV = "convite-dev-de-teste"
MESTRA = "mestra-de-teste-com-entropia-suficiente"


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0

    def importancias(self):
        return None


def _cliente(tmp_path, chave_mestra=None, jwt_segredo=SEGREDO_JWT, codigo_dev=CODIGO_DEV):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra, jwt_segredo=jwt_segredo, codigo_dev=codigo_dev,
    )
    return TestClient(app)


def _cadastro(**mudancas) -> dict:
    corpo = {"nome": "Ana", "email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    corpo.update(mudancas)
    return corpo


# --- registrar --------------------------------------------------------------


def test_registrar_nasce_usuario_e_nao_devolve_hash(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post("/auth/registrar", json=_cadastro())
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["papel"] == "usuario"
    assert corpo["email"] == "ana@empresa.com"
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_registrar_com_codigo_certo_nasce_dev(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post(
        "/auth/registrar", json=_cadastro(codigo_dev=CODIGO_DEV)
    )
    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "dev"


def test_registrar_com_codigo_errado_e_403_e_nao_cria_conta(tmp_path):
    # 403 explicito, nao rebaixamento silencioso: quem digitou o codigo queria
    # ser dev, e nascer usuario sem aviso e a falha silenciosa da casa.
    cliente = _cliente(tmp_path)
    resposta = cliente.post(
        "/auth/registrar", json=_cadastro(codigo_dev="chute-errado")
    )
    assert resposta.status_code == 403
    entrada = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    )
    assert entrada.status_code == 401


def test_sem_variavel_de_codigo_dev_nao_nasce(tmp_path):
    # Sem FRAUS_CODIGO_DEV no ambiente nao ha como nascer dev -- e a recusa e a
    # MESMA do codigo errado: dizer "a variavel nao esta definida" a um anonimo
    # descreveria a configuracao do servidor para quem esta de fora.
    cliente = _cliente(tmp_path, codigo_dev=None)
    resposta = cliente.post(
        "/auth/registrar", json=_cadastro(codigo_dev=CODIGO_DEV)
    )
    assert resposta.status_code == 403


def test_email_duplicado_e_409_mesmo_com_caixa_diferente(tmp_path):
    cliente = _cliente(tmp_path)
    assert cliente.post("/auth/registrar", json=_cadastro()).status_code == 201
    resposta = cliente.post(
        "/auth/registrar", json=_cadastro(email="Ana@Empresa.com")
    )
    assert resposta.status_code == 409


def test_senha_curta_e_recusada_na_validacao(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post("/auth/registrar", json=_cadastro(senha="curta"))
    assert resposta.status_code == 422


# --- entrar -----------------------------------------------------------------


def test_entrar_devolve_token_que_o_proprio_modulo_confere(tmp_path):
    cliente = _cliente(tmp_path)
    cliente.post("/auth/registrar", json=_cadastro(codigo_dev=CODIGO_DEV))
    resposta = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    sessao = token_acesso.conferir(
        corpo["token"], SEGREDO_JWT, agora=datetime.now(timezone.utc)
    )
    assert sessao is not None and sessao["papel"] == "dev"
    assert corpo["usuario"]["email"] == "ana@empresa.com"
    assert "senha_hash" not in corpo["usuario"]


def test_a_recusa_de_entrar_e_uniforme(tmp_path):
    # E-mail inexistente e senha errada respondem o MESMO status e o MESMO
    # detail -- qualquer diferenca contaria quais e-mails tem conta.
    cliente = _cliente(tmp_path)
    cliente.post("/auth/registrar", json=_cadastro())
    sem_conta = cliente.post(
        "/auth/entrar", json={"email": "ninguem@empresa.com", "senha": "tanto-faz-aqui"}
    )
    senha_errada = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-que-nao-e"}
    )
    assert sem_conta.status_code == senha_errada.status_code == 401
    assert sem_conta.json()["detail"] == senha_errada.json()["detail"]


def test_entrar_sem_segredo_jwt_e_503(tmp_path):
    # O mesmo contrato do webhook sem variavel de segredo: culpa do AMBIENTE,
    # nao de quem chamou -- 503, nunca 401.
    cliente = _cliente(tmp_path, jwt_segredo=None)
    cliente.post("/auth/registrar", json=_cadastro())
    resposta = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    )
    assert resposta.status_code == 503


def test_conta_desativada_recusa_com_403(tmp_path):
    # 403, nao 401: a credencial esta certa, o que esta desligada e a conta --
    # o mesmo contrato da fonte desativada.
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        jwt_segredo=SEGREDO_JWT, codigo_dev=None,
    )
    cliente = TestClient(app)
    cliente.post("/auth/registrar", json=_cadastro())
    with sqlite3.connect(tmp_path / "t.db") as conexao:
        conexao.execute("UPDATE usuarios SET ativo = 0")
    resposta = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    )
    assert resposta.status_code == 403


# --- quem sou ---------------------------------------------------------------


def test_auth_eu_devolve_a_ficha_de_quem_esta_no_token(tmp_path):
    cliente = _cliente(tmp_path)
    cliente.post("/auth/registrar", json=_cadastro())
    token = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    ).json()["token"]
    resposta = cliente.get("/auth/eu", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@empresa.com"
    assert "senha_hash" not in resposta.json()


def test_auth_eu_sem_token_ou_com_lixo_e_401(tmp_path):
    cliente = _cliente(tmp_path)
    assert cliente.get("/auth/eu").status_code == 401
    assert cliente.get(
        "/auth/eu", headers={"Authorization": "Bearer nao-e-um-jwt"}
    ).status_code == 401


# --- convivencia com a mestra ----------------------------------------------


def test_registrar_e_entrar_ficam_isentos_com_a_mestra_ligada(tmp_path):
    # Sao as rotas de quem ainda nao tem credencial nenhuma -- o mesmo
    # argumento de /acesso/estado.
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    assert cliente.post("/auth/registrar", json=_cadastro()).status_code == 201
    assert cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": "senha-longa-o-bastante"}
    ).status_code == 200
