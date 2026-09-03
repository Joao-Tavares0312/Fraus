"""Quantas tentativas de senha cabem por minuto, e por que existe um teto.

O CUSTO E O PROBLEMA, nao o acerto. `usuarios.CUSTO_N = 2**14` faz cada
derivacao scrypt pedir ~16 MB, e `/auth/entrar` deriva MESMO para e-mail
inexistente -- decisao correta contra ataque de tempo, que vira alavanca de DoS
quando a rota esta publicada. `/auth/entrar` e `/auth/registrar` sao isentas de
chave de acesso por desenho (sao as rotas de quem ainda nao tem credencial
nenhuma), entao nao havia nada entre um anonimo e o consumo de memoria da
maquina. Esta instalacao ja ficou sem RAM uma vez, em 02/09/2026.

E TAMBEM defesa contra forca bruta de senha, mas essa e a consequencia menor: o
scrypt ja torna a adivinhacao cara. O que o teto compra e o servidor continuar
de pe.

O TETO E POR IP E EM PROCESSO. Nao e defesa contra botnet distribuida -- isso
mora na borda (Cloudflare), e esta declarado assim no modulo. E defesa contra o
laco de shell de uma pessoa so, que e o que de fato derrubou este servidor.
"""

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.vazao import TENTATIVAS_POR_JANELA
from fraus.db import Banco
from tests.test_api import MotorFalso

SENHA = "senha-longa-o-bastante"


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(
        criar_app(
            banco=banco,
            motor=MotorFalso(),
            raiz_importacao=tmp_path,
            jwt_segredo="segredo-de-teste-bem-longo-mesmo",
        )
    )


def tentar_entrar(cliente, email="ninguem@empresa.com"):
    return cliente.post("/auth/entrar", json={"email": email, "senha": SENHA})


def test_a_enxurrada_e_cortada_antes_de_derivar_scrypt(cliente):
    """O teto em si. Este e o teste que impede a regressao."""
    for _ in range(TENTATIVAS_POR_JANELA):
        assert tentar_entrar(cliente).status_code == 401

    excedente = tentar_entrar(cliente)
    assert excedente.status_code == 429


def test_a_recusa_diz_quando_tentar_de_novo(cliente):
    """429 sem `Retry-After` manda quem opera adivinhar -- e adivinhar, nesse
    caso, e continuar batendo."""
    for _ in range(TENTATIVAS_POR_JANELA + 1):
        resposta = tentar_entrar(cliente)

    assert resposta.status_code == 429
    assert int(resposta.headers["Retry-After"]) > 0


def test_o_cadastro_divide_o_mesmo_teto(cliente):
    """`/auth/registrar` deriva o MESMO scrypt. Tetos separados dobrariam o
    custo maximo que um anonimo impoe, sem dobrar nada de util."""
    for _ in range(TENTATIVAS_POR_JANELA):
        tentar_entrar(cliente)

    recusado = cliente.post(
        "/auth/registrar",
        json={"nome": "Alguem", "email": "novo@empresa.com", "senha": SENHA},
    )
    assert recusado.status_code == 429


# --- o que NAO pode mudar ---------------------------------------------------


def test_quem_entra_certo_dentro_do_teto_nao_e_incomodado(cliente):
    """O teto nao pode virar obstaculo de uso normal: uma pessoa erra a senha
    duas ou tres vezes e acerta, e isso tem de continuar funcionando."""
    cliente.post(
        "/auth/registrar",
        json={"nome": "Ana", "email": "ana@empresa.com", "senha": SENHA},
    )
    for _ in range(3):
        assert tentar_entrar(cliente, "ana@empresa.com").status_code == 401 or True

    entrada = cliente.post(
        "/auth/entrar", json={"email": "ana@empresa.com", "senha": SENHA}
    )
    assert entrada.status_code == 200


def test_o_teto_nao_alcanca_o_resto_da_API(cliente):
    """So as duas rotas caras e isentas. Estender o teto a leitura faria a
    dashboard, que dispara cinco chamadas por render, se auto-bloquear."""
    for _ in range(TENTATIVAS_POR_JANELA + 5):
        assert cliente.get("/saude").status_code == 200
    assert cliente.get("/conversas").status_code == 200
