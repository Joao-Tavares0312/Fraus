"""Perfis de mapeamento: o que o analista confirmou uma vez vale para o proximo arquivo.

A fronteira que estes testes sustentam: a previa e a analise NAO gravam nada;
o perfil grava so NOMES de coluna e papeis, nunca conteudo de conversa; e o
corpo que confirma mapeamento nao carrega score (invariante 3) -- so qual
coluna faz qual papel.
"""

import json

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorRespeitandoSinal

CSV = (
    "Protocolo;Remetente;Conteudo;Data/Hora\n"
    "P1;Cliente;minha internet caiu de novo;14/05/2026 10:00\n"
    "P1;Atendente;vou abrir um chamado;14/05/2026 10:07\n"
    "P1;Cliente;ok obrigado, cpf 529.982.247-25;25/05/2026 10:08\n"
).encode()


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorRespeitandoSinal(), raiz_importacao=tmp_path)), banco


def _previa(cliente, dados=CSV, nome="export.csv", **campos):
    return cliente.post("/analisar/previa", files={"arquivo": (nome, dados)}, data=campos)


# --- banco -------------------------------------------------------------------


def test_banco_grava_perfil_e_regravar_a_mesma_assinatura_edita(tmp_path):
    _, banco = _cliente(tmp_path)
    banco.salvar_perfil_mapeamento("Telecom", "abc", ["a", "b"], {"texto": "a"}, "dia/mes")
    banco.salvar_perfil_mapeamento("Telecom v2", "abc", ["a", "b"], {"texto": "b"}, None)
    perfis = banco.listar_perfis_mapeamento()
    assert len(perfis) == 1
    assert perfis[0]["nome"] == "Telecom v2"
    assert perfis[0]["papeis"] == {"texto": "b"}
    assert banco.perfil_por_assinatura("abc")["id"] == perfis[0]["id"]
    assert banco.apagar_perfil_mapeamento(perfis[0]["id"]) is True
    assert banco.perfil_por_assinatura("abc") is None


# --- previa ------------------------------------------------------------------


def test_previa_devolve_o_mapeamento_sugerido_e_nao_grava_nada(tmp_path):
    cliente, banco = _cliente(tmp_path)
    resposta = _previa(cliente)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mapeamento"]["papeis"]["texto"]["coluna"] == "Conteudo"
    assert corpo["mapeamento"]["papeis"]["autor"]["coluna"] == "Remetente"
    assert corpo["mapeamento"]["colunas"] == ["Protocolo", "Remetente", "Conteudo", "Data/Hora"]
    assert corpo["mapeamento"]["ordem_data"] == "dia/mes"
    assert corpo["conversas"] == 1 and corpo["mensagens"] == 3
    assert corpo["perfil"] is None
    assert banco.listar() == []


def test_previa_censura_a_amostra(tmp_path):
    cliente, _ = _cliente(tmp_path)
    amostra = json.dumps(_previa(cliente).json()["amostra"])
    assert "529.982.247-25" not in amostra


def test_previa_de_formato_reconhecido_nao_pede_conferencia(tmp_path):
    cliente, _ = _cliente(tmp_path)
    csv = (
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,web,cliente,oi,2026-05-14T10:00:00+00:00,false\n"
    ).encode()
    corpo = _previa(cliente, csv).json()
    assert corpo["mapeamento"] is None
    assert "Fraus" in corpo["formato"]


def test_previa_com_mapeamento_confirmado_reflete_a_escolha(tmp_path):
    cliente, _ = _cliente(tmp_path)
    corpo = _previa(cliente, mapeamento=json.dumps({"conversa_id": None})).json()
    assert "conversa_id" not in corpo["mapeamento"]["papeis"]


def test_mapeamento_que_nao_e_json_e_400(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = _previa(cliente, mapeamento="texto=Conteudo")
    assert resposta.status_code == 400
    assert "mapeamento" in resposta.json()["detail"]


def test_ordem_de_data_invalida_e_400(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert _previa(cliente, ordem_data="ano/dia").status_code == 400


# --- analise com mapeamento --------------------------------------------------


def test_analise_aceita_o_mapeamento_confirmado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("export.csv", CSV)},
        data={"mapeamento": json.dumps({"texto": "Conteudo", "autor": "Remetente"})},
    )
    assert resposta.status_code == 200, resposta.text
    assert "inferidas" in resposta.json()["formato"]


# --- perfis ------------------------------------------------------------------


def test_perfil_salvo_e_aplicado_sozinho_no_proximo_arquivo(tmp_path):
    cliente, _ = _cliente(tmp_path)
    colunas = _previa(cliente).json()["mapeamento"]["colunas"]
    criado = cliente.post("/perfis-mapeamento", json={
        "nome": "Export da telecom",
        "colunas": colunas,
        "papeis": {"texto": "Conteudo", "autor": "Remetente", "enviada_em": "Data/Hora",
                   "conversa_id": None},
        "ordem_data": "dia/mes",
    })
    assert criado.status_code == 201, criado.text
    assert "amostra" not in criado.json()

    corpo = _previa(cliente).json()
    assert corpo["perfil"]["nome"] == "Export da telecom"
    assert "conversa_id" not in corpo["mapeamento"]["papeis"]
    assert any("Export da telecom" in aviso for aviso in corpo["avisos"])

    assert [p["nome"] for p in cliente.get("/perfis-mapeamento").json()] == ["Export da telecom"]
    assert cliente.delete(f"/perfis-mapeamento/{criado.json()['id']}").status_code == 204
    assert _previa(cliente).json()["perfil"] is None


def test_perfil_sem_texto_ou_autor_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post("/perfis-mapeamento", json={
        "nome": "x", "colunas": ["a", "b"], "papeis": {"texto": "a"},
    })
    assert resposta.status_code == 400
    assert "autor" in resposta.json()["detail"]


def test_perfil_com_coluna_fora_do_arquivo_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post("/perfis-mapeamento", json={
        "nome": "x", "colunas": ["a", "b"], "papeis": {"texto": "a", "autor": "z"},
    })
    assert resposta.status_code == 400
    assert "z" in resposta.json()["detail"]


def test_apagar_perfil_inexistente_e_404(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.delete("/perfis-mapeamento/99").status_code == 404


def test_gravar_perfil_e_rota_administrativa_e_ler_nao():
    from fraus.api.seguranca import rota_administrativa

    assert rota_administrativa("POST", "/perfis-mapeamento") is True
    assert rota_administrativa("DELETE", "/perfis-mapeamento/1") is True
    assert rota_administrativa("GET", "/perfis-mapeamento") is False
    assert rota_administrativa("POST", "/analisar/previa") is False
