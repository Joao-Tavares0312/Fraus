"""Quem pode CRIAR CONTA nesta instalacao.

O BURACO QUE ISTO FECHA. `POST /auth/registrar` e isento de credencial por
desenho -- tem de ser, porque quem se cadastra ainda nao tem nenhuma. Isso era
inofensivo enquanto a API so existia em `localhost`. Publicada por tunel, virou
o caminho mais curto para os dados: qualquer pessoa que descobrisse o endereco
fazia um POST, recebia um JWT e passava a LER todos os atendimentos -- porque
`acesso_autorizado` aceita qualquer sessao valida do mesmo jeito que aceita a
mestra. A mestra protegia a leitura contra o anonimo; deixar de ser anonimo era
de graca. Reproduzido contra a instalacao publicada, em 02/09/2026.

DOIS CODIGOS, DOIS PRIVILEGIOS, e confundi-los seria o proximo bug:
`FRAUS_CODIGO_DEV` decide COM QUAL PAPEL a conta nasce; `FRAUS_CODIGO_CONVITE`
decide SE ela pode nascer.

SEM `FRAUS_CODIGO_CONVITE` NADA MUDA -- e metade destes testes existe para
provar isso. Instalacao local nao deve ter que digitar codigo para entrar na
propria ferramenta.
"""

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorFalso

DEV = "codigo-de-dev"
CONVITE = "codigo-de-convite"


def montar(tmp_path, **segredos) -> TestClient:
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(
            banco=banco,
            motor=MotorFalso(),
            raiz_importacao=tmp_path,
            jwt_segredo="segredo-de-teste-bem-longo",
            **segredos,
        )
    )


def cadastrar(cliente, email, codigo=None):
    corpo = {"nome": "Alguem", "email": email, "senha": "senha-bem-longa"}
    if codigo is not None:
        corpo["codigo_dev"] = codigo
    return cliente.post("/auth/registrar", json=corpo)


# ---- instalacao ABERTA: nada mudou -------------------------------------


@pytest.fixture
def aberta(tmp_path):
    return montar(tmp_path, codigo_dev=DEV)


def test_sem_convite_definido_qualquer_um_cadastra(aberta):
    resposta = cadastrar(aberta, "a@b.co")
    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "usuario"


def test_sem_convite_definido_o_codigo_de_dev_continua_promovendo(aberta):
    assert cadastrar(aberta, "d@b.co", DEV).json()["papel"] == "dev"


def test_codigo_errado_continua_403_e_nao_rebaixamento_silencioso(aberta):
    """Quem digitou um codigo queria algo. Nascer `usuario` sem aviso seria a
    falha silenciosa que este projeto persegue."""
    resposta = cadastrar(aberta, "x@b.co", "chute")
    assert resposta.status_code == 403


def test_estado_diz_que_o_codigo_e_dispensavel(aberta):
    assert aberta.get("/auth/estado").json()["cadastro_exige_codigo"] is False


# ---- instalacao FECHADA: o cadastro exige convite -----------------------


@pytest.fixture
def fechada(tmp_path):
    return montar(tmp_path, codigo_dev=DEV, codigo_convite=CONVITE)


def test_anonimo_sem_codigo_NAO_cria_conta(fechada):
    """O buraco em si. Este e o teste que impede a regressao."""
    resposta = cadastrar(fechada, "invasor@b.co")
    assert resposta.status_code == 403
    assert "codigo de convite" in resposta.json()["detail"]


def test_com_o_convite_cadastra_como_usuario(fechada):
    resposta = cadastrar(fechada, "convidado@b.co", CONVITE)
    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "usuario"


def test_o_codigo_de_dev_tambem_da_entrada_e_promove(fechada):
    """Ele e o codigo mais privilegiado: nao faria sentido exigir os dois."""
    resposta = cadastrar(fechada, "dev@b.co", DEV)
    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "dev"


def test_codigo_errado_recusa(fechada):
    assert cadastrar(fechada, "y@b.co", "chute").status_code == 403


def test_estado_avisa_a_tela_que_o_codigo_e_obrigatorio(fechada):
    """Sem isto o formulario rotularia o campo como "(opcional)" numa
    instalacao onde ele nao e -- e o 403 pareceria defeito."""
    corpo = fechada.get("/auth/estado").json()
    assert corpo["cadastro_exige_codigo"] is True
    # E nao vaza QUAL e o codigo, so que existe exigencia.
    assert CONVITE not in str(corpo)


def test_a_recusa_nao_distingue_ausente_de_errado(fechada):
    """Mensagens diferentes contariam a configuracao do servidor a quem esta
    do lado de fora -- por exemplo, que o codigo tentado nao e o de dev."""
    sem = cadastrar(fechada, "p@b.co")
    errado = cadastrar(fechada, "q@b.co", "chute")
    assert sem.status_code == errado.status_code == 403


def test_login_de_quem_ja_tem_conta_nao_e_afetado(fechada):
    """O convite governa a CRIACAO. Quem ja entrou continua entrando."""
    cadastrar(fechada, "antigo@b.co", CONVITE)
    entrada = fechada.post(
        "/auth/entrar", json={"email": "antigo@b.co", "senha": "senha-bem-longa"}
    )
    assert entrada.status_code == 200
    assert entrada.json()["token"]
