"""Importacao em lote de qualquer formato -- com a mesma conferencia da analise.

A analise avulsa (`/analisar`) nao grava nada; a importacao GRAVA, e o que ela
grava entra no NPS de todo mundo. Por isso a regra daqui e mais dura que a de
la: colunas inferidas pela heuristica NAO entram no banco sem um perfil que o
analista confirmou. Inferencia calada numa tela e um aviso; no banco, e um
indicador contaminado que ninguem ve.

O corpo de `/conversas/importar` continua aceitando SO `caminho`
(invariante 3). O mapeamento confirmado chega pelo perfil salvo, nunca pelo
corpo da importacao.
"""

import json

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorFalso

TELECOM = (
    "Protocolo;Remetente;Conteudo;Data/Hora\n"
    "P1;Cliente;minha internet caiu de novo;14/05/2026 10:00\n"
    "P1;Atendente;vou abrir um chamado;14/05/2026 10:07\n"
    "P2;Cliente;quero trocar de plano;25/05/2026 09:00\n"
    "P2;Bot;claro, qual plano?;25/05/2026 09:00\n"
)
PAPEIS = {"texto": "Conteudo", "autor": "Remetente", "enviada_em": "Data/Hora",
          "conversa_id": "Protocolo"}


@pytest.fixture
def ambiente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    raiz = tmp_path / "entrada"
    raiz.mkdir()
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=raiz)), banco, raiz


def _salvar_perfil(cliente):
    colunas = ["Protocolo", "Remetente", "Conteudo", "Data/Hora"]
    resposta = cliente.post("/perfis-mapeamento", json={
        "nome": "Telecom", "colunas": colunas, "papeis": PAPEIS, "ordem_data": "dia/mes"})
    assert resposta.status_code == 201, resposta.text


# --- a importacao ------------------------------------------------------------


def test_colunas_inferidas_sem_perfil_nao_entram_no_banco(ambiente):
    cliente, banco, raiz = ambiente
    (raiz / "telecom.csv").write_text(TELECOM, encoding="utf-8")
    resposta = cliente.post("/conversas/importar", json={"caminho": "telecom.csv"})
    assert resposta.status_code == 409
    detalhe = resposta.json()["detail"]
    assert "confirm" in detalhe and "perfil" in detalhe
    assert banco.listar() == []
    assert cliente.get("/integracoes/importacoes").json() == []


def test_com_perfil_confirmado_o_export_desconhecido_entra_e_e_pontuado(ambiente):
    cliente, banco, raiz = ambiente
    (raiz / "telecom.csv").write_text(TELECOM, encoding="utf-8")
    _salvar_perfil(cliente)
    resposta = cliente.post("/conversas/importar", json={"caminho": "telecom.csv"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["importadas"] == 2
    ids = {linha["id"] for linha in banco.listar()}
    assert ids == {"P1", "P2"}
    historico = cliente.get("/integracoes/importacoes").json()
    assert historico[0]["aceitas"] == 2


def test_arquivo_sem_horario_e_recusado_no_lote(ambiente):
    """Sem horario nao ha nota, e `score: null` no banco ja significa 'sem fala do
    cliente' (invariante 2) -- guardar 'tem fala mas nao tem nota' mentiria."""
    cliente, banco, raiz = ambiente
    (raiz / "transcricao.txt").write_text("Cliente: oi\nBot: ola, como posso ajudar?\n", encoding="utf-8")
    resposta = cliente.post("/conversas/importar", json={"caminho": "transcricao.txt"})
    assert resposta.status_code == 400
    assert "horário" in resposta.json()["detail"]
    assert banco.listar() == []


def test_json_com_colunas_reconhecidas_por_perfil_entra(ambiente):
    cliente, banco, raiz = ambiente
    dados = [
        {"ticket": "t1", "from": "customer", "message": "nao consigo logar", "timestamp": "2026-05-14T10:00:00Z"},
        {"ticket": "t1", "from": "agent", "message": "vou resetar sua senha", "timestamp": "2026-05-14T10:03:00Z"},
    ]
    (raiz / "tickets.json").write_text(json.dumps(dados), encoding="utf-8")
    cliente.post("/perfis-mapeamento", json={
        "nome": "Zendesk", "colunas": ["ticket", "from", "message", "timestamp"],
        "papeis": {"texto": "message", "autor": "from", "enviada_em": "timestamp", "conversa_id": "ticket"}})
    resposta = cliente.post("/conversas/importar", json={"caminho": "tickets.json"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["importadas"] == 1


def test_o_corpo_da_importacao_continua_aceitando_so_o_caminho(ambiente):
    cliente, banco, raiz = ambiente
    (raiz / "telecom.csv").write_text(TELECOM, encoding="utf-8")
    resposta = cliente.post("/conversas/importar", json={
        "caminho": "telecom.csv", "mapeamento": json.dumps(PAPEIS), "score": 99})
    # O mapeamento no corpo e IGNORADO: sem perfil, continua 409.
    assert resposta.status_code == 409


# --- a previa ----------------------------------------------------------------


def test_previa_da_importacao_nao_grava_e_diz_se_exige_confirmacao(ambiente):
    cliente, banco, raiz = ambiente
    (raiz / "telecom.csv").write_text(TELECOM, encoding="utf-8")
    corpo = cliente.post("/conversas/importar/previa", json={"caminho": "telecom.csv"}).json()
    assert corpo["exige_confirmacao"] is True
    assert corpo["mapeamento"]["papeis"]["texto"]["coluna"] == "Conteudo"
    assert corpo["conversas"] == 2
    assert banco.listar() == []

    _salvar_perfil(cliente)
    corpo = cliente.post("/conversas/importar/previa", json={"caminho": "telecom.csv"}).json()
    assert corpo["exige_confirmacao"] is False
    assert corpo["perfil"]["nome"] == "Telecom"


def test_previa_aceita_ajuste_de_colunas_sem_gravar(ambiente):
    cliente, _, raiz = ambiente
    (raiz / "telecom.csv").write_text(TELECOM, encoding="utf-8")
    corpo = cliente.post("/conversas/importar/previa", json={
        "caminho": "telecom.csv", "mapeamento": {"conversa_id": None}}).json()
    assert corpo["conversas"] == 1
    assert cliente.get("/perfis-mapeamento").json() == []


def test_previa_de_formato_reconhecido_nao_exige_confirmacao(ambiente):
    cliente, _, raiz = ambiente
    (raiz / "canonico.csv").write_text(
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,web,cliente,oi,2026-05-14T10:00:00+00:00,false\n", encoding="utf-8")
    corpo = cliente.post("/conversas/importar/previa", json={"caminho": "canonico.csv"}).json()
    assert corpo["exige_confirmacao"] is False
    assert corpo["mapeamento"] is None


def test_previa_recusa_caminho_fora_da_raiz(ambiente, tmp_path):
    cliente, _, _ = ambiente
    (tmp_path / "fora.csv").write_text(TELECOM, encoding="utf-8")
    resposta = cliente.post("/conversas/importar/previa", json={"caminho": "../fora.csv"})
    assert resposta.status_code == 400


def test_previa_da_importacao_e_rota_administrativa():
    from fraus.api.seguranca import rota_administrativa

    assert rota_administrativa("POST", "/conversas/importar/previa") is True


# --- a listagem --------------------------------------------------------------


def test_a_pasta_lista_todo_formato_que_a_leitura_aceita(ambiente):
    cliente, _, raiz = ambiente
    for nome in ("a.csv", "b.json", "c.txt", "d.xlsx", "e.docx", "f.png"):
        (raiz / nome).write_bytes(b"x")
    nomes = {a["caminho"] for a in cliente.get("/integracoes/arquivos").json()["arquivos"]}
    assert nomes == {"a.csv", "b.json", "c.txt", "d.xlsx", "e.docx"}
