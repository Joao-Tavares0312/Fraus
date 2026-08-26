"""As rotas do lexico curado, e a VALIDACAO que sustenta a fronteira.

A fronteira: o analista edita o DICIONARIO, nunca a nota. Por isso o modelo de
entrada nao tem campo que se pareca com score, e a escala de cada lexico e
imposta aqui -- valor fora dela injetaria na media de polaridade um numero que o
fusor nunca viu no treino.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    return TestClient(app), banco


def test_lista_vazia_num_banco_novo(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.get("/lexico/curado").json() == []


def test_cadastra_palavra_e_ela_aparece_na_lista(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado",
        json={"tipo": "palavra", "termo": "lentissimo", "peso": -1,
              "motivo": "reclamacao comum aqui"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["termo"] == "lentissimo"

    lista = cliente.get("/lexico/curado").json()
    assert [(c["tipo"], c["termo"], c["peso"]) for c in lista] == [
        ("palavra", "lentissimo", -1.0)
    ]


def test_palavra_e_normalizada_para_minusculas(tmp_path):
    cliente, _ = _cliente(tmp_path)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "LentÍssimo", "peso": -1})
    assert cliente.get("/lexico/curado").json()[0]["termo"] == "lentíssimo"


def test_peso_fracionario_em_PALAVRA_e_recusado(tmp_path):
    """A escala da palavra e a do SentiLex: -1/0/+1. Um -0,7 injetaria na media
    de polaridade um valor fora da distribuicao de treino do fusor."""
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -0.7}
    )
    assert resposta.status_code == 400
    assert "-1" in resposta.json()["detail"]


def test_peso_fracionario_em_EMOJI_e_aceito(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄", "peso": -0.62}
    )
    assert resposta.status_code == 201


def test_peso_de_emoji_fora_da_faixa_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄", "peso": 1.5}
    ).status_code == 400


def test_termo_de_emoji_com_dois_emojis_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄🎉", "peso": 0.1}
    )
    assert resposta.status_code == 400


def test_termo_de_emoji_que_nao_e_emoji_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "abc", "peso": 0.1}
    ).status_code == 400


def test_tipo_invalido_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "frase", "termo": "x", "peso": 1}
    ).status_code == 422


def test_o_corpo_NAO_aceita_score_nem_categoria(tmp_path):
    """Invariante 3: veredito nunca entra pelo corpo. Campo extra e ignorado
    por construcao, e o registro gravado nao carrega nada disso."""
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado",
        json={"tipo": "palavra", "termo": "x", "peso": 1,
              "score": 99, "categoria": "promotor"},
    )
    assert resposta.status_code == 201
    assert "score" not in resposta.json()
    assert "categoria" not in resposta.json()


def test_revogar_tira_da_lista(tmp_path):
    cliente, _ = _cliente(tmp_path)
    criado = cliente.post(
        "/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": 1}
    ).json()
    assert cliente.delete(f"/lexico/curado/{criado['id']}").status_code == 204
    assert cliente.get("/lexico/curado").json() == []


def test_revogar_o_que_nao_existe_da_404(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.delete("/lexico/curado/999").status_code == 404
