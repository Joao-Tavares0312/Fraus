"""Testes da chave de API e da rota de ingestao.

O foco e o que custa caro se estiver errado: o segredo nao pode ser
recuperavel, o hash nao pode circular, e chave de uma fonte nao pode abrir
outra.
"""

import pytest
from fastapi.testclient import TestClient

from fraus import credencial
from fraus.api.main import criar_app
from fraus.db import Banco

from tests.test_api import MotorRespeitandoSinal

MENSAGENS = [
    {
        "autor": "cliente",
        "texto": "meu pedido nao chegou",
        "enviada_em": "2026-08-14T10:00:00+00:00",
    },
    {
        "autor": "bot",
        "texto": "vou verificar",
        "enviada_em": "2026-08-14T10:00:12+00:00",
    },
]


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorRespeitandoSinal(), raiz_importacao=tmp_path)
    )


def _fonte(cliente, nome="Suporte", canal="whatsapp") -> int:
    resposta = cliente.post(
        "/integracoes/fontes",
        json={"nome": nome, "canal": canal, "tipo": "webhook"},
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def _com_chave(cliente, fonte_id: int) -> str:
    return cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()["chave"]


# ---------------------------------------------------------------------------
# o modulo de credencial


def test_chave_carrega_o_id_da_fonte_e_um_segredo_sorteado():
    chave, _hash = credencial.gerar(42)
    assert chave.startswith("frs_42_")
    assert credencial.fonte_da_chave(chave) == 42


def test_duas_chamadas_nunca_geram_a_mesma_chave():
    primeira, _ = credencial.gerar(1)
    segunda, _ = credencial.gerar(1)
    assert primeira != segunda


def test_chave_fora_do_formato_nao_aponta_para_fonte_nenhuma():
    for lixo in ("", "abc", "frs_", "frs_x_y", "outro_1_abc", "frs_1_a_b"):
        assert credencial.fonte_da_chave(lixo) is None


def test_fonte_sem_chave_gerada_nunca_autoriza():
    """`None` no banco nao pode virar "confere" por acidente."""
    chave, _ = credencial.gerar(1)
    assert credencial.confere(chave, None) is False
    assert credencial.confere(chave, "") is False


def test_a_dica_e_curta_e_e_o_sufixo():
    chave, _ = credencial.gerar(7)
    assert credencial.dica(chave) == chave[-4:]
    assert len(credencial.dica(chave)) == 4


# ---------------------------------------------------------------------------
# a rota que gera


def test_a_chave_em_claro_aparece_uma_vez_e_nunca_mais(cliente):
    """Nao ha rota para reler a chave -- o banco guarda so o hash."""
    fonte_id = _fonte(cliente)
    corpo = cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()
    chave = corpo["chave"]
    assert chave.startswith(f"frs_{fonte_id}_")

    fontes = cliente.get("/integracoes/fontes").json()
    inteiro = str(fontes)
    assert chave not in inteiro, "a chave em claro vazou na listagem"


def test_o_hash_da_chave_nunca_sai_pela_api(cliente):
    """O hash nao e senha, e ainda assim confirma um palpite offline."""
    fonte_id = _fonte(cliente)
    cliente.post(f"/integracoes/fontes/{fonte_id}/chave")

    for corpo in (
        cliente.get("/integracoes/fontes").json(),
        [cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()],
    ):
        assert "chave_hash" not in str(corpo)


def test_a_fonte_mostra_a_dica_para_o_operador_reconhecer_a_chave(cliente):
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    fonte = next(f for f in cliente.get("/integracoes/fontes").json() if f["id"] == fonte_id)
    assert fonte["chave_dica"] == chave[-4:]
    assert fonte["chave_criada_em"] is not None


def test_gerar_de_novo_invalida_a_chave_anterior(cliente):
    """"Gerei outra" tem que significar que a de antes parou de funcionar."""
    fonte_id = _fonte(cliente)
    antiga = _com_chave(cliente, fonte_id)
    nova = _com_chave(cliente, fonte_id)
    assert antiga != nova

    recusada = cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {antiga}"},
    )
    assert recusada.status_code == 401


def test_gerar_chave_de_fonte_inexistente_e_404(cliente):
    assert cliente.post("/integracoes/fontes/999/chave").status_code == 404


def test_revogar_tira_a_chave_e_mantem_a_fonte(cliente):
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    assert cliente.delete(f"/integracoes/fontes/{fonte_id}/chave").status_code == 204

    fonte = next(f for f in cliente.get("/integracoes/fontes").json() if f["id"] == fonte_id)
    assert fonte["chave_dica"] is None
    assert cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave}"},
    ).status_code == 401


# ---------------------------------------------------------------------------
# a rota que recebe


def test_ingestao_com_chave_valida_grava_e_pontua(cliente):
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    resposta = cliente.post(
        "/ingestao",
        json={"id": "externa-1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["score"] == 90.0

    listagem = cliente.get("/conversas").json()
    assert resposta.json()["id_externo"] == "externa-1"
    assert [c["id"] for c in listagem] == [f"fonte:{fonte_id}:externa-1"]


def test_ids_iguais_de_fontes_diferentes_nao_se_sobrescrevem(cliente):
    primeira = _fonte(cliente, nome="Tars A", canal="telegram")
    segunda = _fonte(cliente, nome="Tars B", canal="webchat")
    for fonte_id in (primeira, segunda):
        chave = _com_chave(cliente, fonte_id)
        resposta = cliente.post(
            "/ingestao",
            json={"id": "chat-1", "mensagens": MENSAGENS},
            headers={"Authorization": f"Bearer {chave}"},
        )
        assert resposta.status_code == 201

    assert {c["id"] for c in cliente.get("/conversas").json()} == {
        f"fonte:{primeira}:chat-1",
        f"fonte:{segunda}:chat-1",
    }


def test_feedback_declarado_e_guardado_sem_escolher_o_score(cliente):
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)
    resposta = cliente.post(
        "/ingestao",
        json={
            "id": "com-feedback",
            "mensagens": MENSAGENS,
            "feedback_declarado": -1,
            "comentario_feedback": "nao resolveu meu pedido",
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.json()["score"] == 90.0
    detalhe = cliente.get(f"/conversas/fonte:{fonte_id}:com-feedback").json()
    assert detalhe["feedback_declarado"] == -1
    indicadores = cliente.get("/indicadores").json()
    assert indicadores["feedback_declarado_total"] == 1
    assert indicadores["concordancia_com_feedback"] == 0.0


def test_o_canal_vem_da_fonte_e_nao_do_corpo(cliente):
    """Quem manda o dado nao escolhe onde ele e contabilizado."""
    fonte_id = _fonte(cliente, canal="whatsapp")
    chave = _com_chave(cliente, fonte_id)

    cliente.post(
        "/ingestao",
        json={"id": "externa-1", "canal": "webchat", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert cliente.get("/conversas").json()[0]["canal"] == "whatsapp"


def test_score_e_categoria_do_corpo_sao_ignorados(cliente):
    """Mesma regra da importacao: veredito e sempre derivado no servidor."""
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    cliente.post(
        "/ingestao",
        json={
            "id": "externa-1",
            "mensagens": MENSAGENS,
            "score": 0,
            "categoria": "detrator",
            "nota": 0,
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    linha = cliente.get("/conversas").json()[0]
    assert linha["score"] == 90.0
    assert linha["categoria"] == "promotor"


def test_sem_cabecalho_e_401_dizendo_como_se_autenticar(cliente):
    resposta = cliente.post("/ingestao", json={"id": "c1", "mensagens": MENSAGENS})
    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_chave_inventada_e_401(cliente):
    _fonte(cliente)
    for falsa in ("frs_1_" + "0" * 64, "Bearer", "frs_999_abc", "lixo"):
        resposta = cliente.post(
            "/ingestao",
            json={"id": "c1", "mensagens": MENSAGENS},
            headers={"Authorization": f"Bearer {falsa}"},
        )
        assert resposta.status_code == 401, falsa


def test_a_recusa_nao_conta_se_a_fonte_existe(cliente):
    """Mensagem diferente por id existente/inexistente seria um oraculo."""
    fonte_id = _fonte(cliente)
    _com_chave(cliente, fonte_id)

    existente = cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer frs_{fonte_id}_{'0' * 64}"},
    )
    inexistente = cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer frs_4242_{'0' * 64}"},
    )
    assert existente.status_code == inexistente.status_code == 401
    assert existente.json()["detail"] == inexistente.json()["detail"]


def test_chave_de_uma_fonte_nao_vale_para_outra(cliente):
    primeira = _fonte(cliente, nome="Suporte", canal="whatsapp")
    segunda = _fonte(cliente, nome="Vendas", canal="instagram")
    chave_da_primeira = _com_chave(cliente, primeira)
    _com_chave(cliente, segunda)

    # A chave e da primeira: o atendimento tem que cair no canal DELA.
    cliente.post(
        "/ingestao",
        json={"id": "externa-1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave_da_primeira}"},
    )
    assert cliente.get("/conversas").json()[0]["canal"] == "whatsapp"


def test_fonte_desativada_recusa_com_403_e_diz_o_motivo(cliente):
    """O interruptor da tela precisa de fato desligar alguma coisa.

    403 e nao 401: a chave esta certa, o que esta desligado e a fonte. Recusar
    como "chave invalida" mandaria o integrador procurar problema onde nao ha.
    """
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)
    cliente.patch(f"/integracoes/fontes/{fonte_id}", json={"ativa": False})

    resposta = cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.status_code == 403
    assert "desativada" in resposta.json()["detail"]


def test_conversa_sem_mensagem_nenhuma_e_recusada(cliente):
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    resposta = cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": []},
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.status_code == 422


def test_mensagens_fora_de_ordem_sao_ordenadas_pelo_horario(cliente):
    """A latencia sai dos timestamps: ordem errada inventaria espera negativa."""
    fonte_id = _fonte(cliente)
    chave = _com_chave(cliente, fonte_id)

    cliente.post(
        "/ingestao",
        json={"id": "c1", "mensagens": [MENSAGENS[1], MENSAGENS[0]]},
        headers={"Authorization": f"Bearer {chave}"},
    )
    detalhe = cliente.get(f"/conversas/fonte:{fonte_id}:c1").json()
    assert [m["autor"] for m in detalhe["mensagens"]] == ["cliente", "bot"]
    assert detalhe["latencia_primeira_resposta_s"] == 12.0
