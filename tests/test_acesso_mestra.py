"""POST /acesso/mestra: primeiro uso, recusa de sobrescrita e rotacao.

O caminho que existe para a autenticacao ser ligada SEM terminal. As duas
garantias que os testes daqui cobram: ligar tem que valer no mesmo processo, e
a rota nunca pode sobrescrever a mestra de quem esta dentro.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    ))


def test_primeiro_uso_liga_e_devolve_as_duas_chaves(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post("/acesso/mestra")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["chave_mestra"].startswith("frm_")
    assert corpo["chave_acesso"].startswith("fra_")
    assert "aviso" in corpo

    # Ligou de verdade, no mesmo processo.
    assert cliente.get("/conversas").status_code == 401
    # E a chave de acesso emitida junto FUNCIONA -- sem isso o clique deixaria
    # a propria dashboard em 401, e o passo seguinte seria o terminal que o
    # botao veio eliminar.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave_acesso']}"}
    ).status_code == 200
    # A mestra tambem entra.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave_mestra']}"}
    ).status_code == 200


def test_a_chave_de_acesso_emitida_aparece_na_listagem(tmp_path):
    """Ela e uma chave de acesso normal -- some da vista se nao for listavel."""
    cliente = _cliente(tmp_path)
    corpo = cliente.post("/acesso/mestra").json()
    listagem = cliente.get(
        "/acesso/chaves", headers={"Authorization": f"Bearer {corpo['chave_mestra']}"}
    ).json()
    assert [item["nome"] for item in listagem] == ["dashboard"]
    assert "chave_hash" not in listagem[0]


def test_segunda_chamada_sem_a_mestra_atual_e_409(tmp_path):
    cliente = _cliente(tmp_path)
    primeira = cliente.post("/acesso/mestra").json()

    conflito = cliente.post(
        "/acesso/mestra",
        headers={"Authorization": f"Bearer {primeira['chave_acesso']}"},
    )
    assert conflito.status_code == 409
    # A mestra de quem esta dentro continua valendo: nada foi sobrescrito.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {primeira['chave_mestra']}"}
    ).status_code == 200


def test_rotacao_com_a_mestra_atual_invalida_a_antiga(tmp_path):
    cliente = _cliente(tmp_path)
    antiga = cliente.post("/acesso/mestra").json()["chave_mestra"]

    resposta = cliente.post(
        "/acesso/mestra", headers={"Authorization": f"Bearer {antiga}"}
    )
    assert resposta.status_code == 201
    nova = resposta.json()["chave_mestra"]
    assert nova != antiga
    # Rotacao NAO emite chave de acesso: a da dashboard continua valendo, e
    # emitir outra a cada rotacao encheria a tabela de credencial viva.
    assert resposta.json()["chave_acesso"] is None

    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {antiga}"}
    ).status_code == 401
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {nova}"}
    ).status_code == 200


def test_com_mestra_de_ambiente_a_rota_recusa(tmp_path):
    """Quem opera por ambiente nao troca a credencial por HTTP.

    A variavel e a fonte e vence o banco: gravar por cima criaria duas
    verdades com a do ambiente ganhando -- o botao pareceria funcionar e nao
    mudaria nada.
    """
    cliente = _cliente(tmp_path, chave_mestra="segredo-do-ambiente")
    resposta = cliente.post(
        "/acesso/mestra", headers={"Authorization": "Bearer segredo-do-ambiente"}
    )
    assert resposta.status_code == 409
    assert "ambiente" in resposta.json()["detail"]


def test_resposta_nunca_carrega_hash(tmp_path):
    cliente = _cliente(tmp_path)
    corpo = cliente.post("/acesso/mestra").json()
    assert set(corpo) == {"chave_mestra", "chave_acesso", "dica", "aviso"}


def test_estado_passa_a_dizer_banco_depois_de_ligar(tmp_path):
    cliente = _cliente(tmp_path)
    cliente.post("/acesso/mestra")
    assert cliente.get("/acesso/estado").json() == {"ligada": True, "origem": "banco"}


def test_ligou_continua_ligada_depois_de_reiniciar(tmp_path):
    """O que separa esta feature de um interruptor em memoria.

    Mestra que mora so no processo volta a API para ABERTA no reinicio, em
    silencio -- e "parece protegido e nao esta" e a pior falha possivel neste
    caminho. Um app NOVO sobre o MESMO banco e o reinicio.
    """
    cliente = _cliente(tmp_path)
    chaves = cliente.post("/acesso/mestra").json()

    banco = Banco(tmp_path / "t.db")  # mesmo arquivo, processo "novo"
    reiniciado = TestClient(criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
    ))

    assert reiniciado.get("/conversas").status_code == 401
    assert reiniciado.get("/acesso/estado").json() == {
        "ligada": True, "origem": "banco",
    }
    for chave in (chaves["chave_mestra"], chaves["chave_acesso"]):
        assert reiniciado.get(
            "/conversas", headers={"Authorization": f"Bearer {chave}"}
        ).status_code == 200
