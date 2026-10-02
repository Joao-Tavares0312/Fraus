"""O id de uma conversa cujo arquivo nao traz id, e o dia de uma que nao traz dia.

Dois defeitos da auditoria de 02/10/2026:

- arquivo sem coluna de conversa virava a conversa de id "conversa". O segundo
  arquivo importado assim gravava por cima do primeiro, sem erro e sem aviso;
- transcricao em prosa so traz a hora (`[10:03] Cliente: ...`). O dia era o do
  envio, lido em UTC, e entrava no id: o mesmo arquivo reenviado no dia
  seguinte virava outra conversa e contava duas vezes no NPS.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.ingest import arquivos
from fraus.ingest.arquivos import extrair
from tests.test_api import CSV, MotorFalso, MotorRespeitandoSinal

SEM_CONVERSA = (
    "Remetente;Conteudo;Data/Hora\n"
    "Cliente;{fala};14/05/2026 10:00\n"
    "Atendente;vou abrir um chamado;14/05/2026 10:07\n"
)
COLUNAS = ["Remetente", "Conteudo", "Data/Hora"]
PAPEIS = {"texto": "Conteudo", "autor": "Remetente", "enviada_em": "Data/Hora"}

PROSA = "[22:30] Cliente: demorou demais\n[22:41] Atendente: desculpe a espera\n"


@pytest.fixture
def importacao(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    raiz = tmp_path / "entrada"
    raiz.mkdir()
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=raiz))
    resposta = cliente.post("/perfis-mapeamento", json={
        "nome": "Sem protocolo", "colunas": COLUNAS, "papeis": PAPEIS, "ordem_data": "dia/mes"})
    assert resposta.status_code == 201, resposta.text
    return cliente, banco, raiz


@pytest.fixture
def analise(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "dados.db")
    banco.migrar()
    monkeypatch.setattr("fraus.api.rotas.analise.motor_e_real", lambda motor: True)
    cliente = TestClient(criar_app(banco, MotorRespeitandoSinal(), raiz_importacao=tmp_path))
    return cliente, banco


def _importar(cliente, caminho):
    resposta = cliente.post("/conversas/importar", json={"caminho": caminho})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _no_dia(monkeypatch, instante: str):
    monkeypatch.setattr(arquivos, "_agora", lambda: datetime.fromisoformat(instante))


def _registrar(cliente, nome="conversa.txt", texto=PROSA):
    resposta = cliente.post(
        "/analisar/registrar", files={"arquivo": (nome, texto, "text/plain")})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --- importacao: arquivo sem coluna de conversa -------------------------------


def test_dois_arquivos_sem_coluna_de_conversa_nao_se_sobrescrevem(importacao):
    cliente, banco, raiz = importacao
    (raiz / "segunda.csv").write_text(SEM_CONVERSA.format(fala="internet caiu"), encoding="utf-8")
    (raiz / "terca.csv").write_text(SEM_CONVERSA.format(fala="quero cancelar"), encoding="utf-8")
    _importar(cliente, "segunda.csv")
    _importar(cliente, "terca.csv")
    ids = [linha["id"] for linha in banco.listar()]
    assert len(set(ids)) == 2
    assert all(i.startswith("arquivo:") for i in ids)
    assert "conversa" not in ids


def test_reimportar_o_mesmo_arquivo_corrigido_substitui_e_nao_duplica(importacao):
    cliente, banco, raiz = importacao
    (raiz / "segunda.csv").write_text(SEM_CONVERSA.format(fala="internet caiu"), encoding="utf-8")
    _importar(cliente, "segunda.csv")
    (raiz / "segunda.csv").write_text(SEM_CONVERSA.format(fala="internet voltou"), encoding="utf-8")
    _importar(cliente, "segunda.csv")
    (linha,) = banco.listar()
    conversa, _, _ = banco.buscar(linha["id"])
    assert conversa.mensagens[0].texto == "internet voltou"


def test_mesmo_nome_em_pastas_diferentes_sao_conversas_diferentes(importacao):
    cliente, banco, raiz = importacao
    for pasta, fala in (("maio", "internet caiu"), ("junho", "quero cancelar")):
        (raiz / pasta).mkdir()
        (raiz / pasta / "atendimento.csv").write_text(
            SEM_CONVERSA.format(fala=fala), encoding="utf-8")
        _importar(cliente, f"{pasta}/atendimento.csv")
    assert len(banco.listar()) == 2


def test_arquivo_com_coluna_de_conversa_continua_com_o_id_que_trouxe(tmp_path):
    extracao = extrair("conversa.csv", CSV.encode())
    assert extracao.id_do_arquivo is False and extracao.tem_data is True


def test_transcricao_importada_nao_ocupa_o_id_de_uma_integracao(importacao, monkeypatch):
    cliente, banco, raiz = importacao
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    (raiz / "P1.txt").write_text(PROSA, encoding="utf-8")
    _importar(cliente, "P1.txt")
    (linha,) = banco.listar()
    assert linha["id"].startswith("arquivo:") and linha["id"] != "P1"


# --- transcricao que traz a hora e nao o dia ---------------------------------


def test_prosa_declara_que_nao_tem_dia(monkeypatch):
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    extracao = extrair("conversa.txt", PROSA.encode())
    assert extracao.tem_tempo is True
    assert extracao.tem_data is False
    assert extracao.id_do_arquivo is True
    assert any("dia" in aviso and "envio" in aviso for aviso in extracao.avisos)


def test_hora_da_transcricao_e_hora_de_brasilia(monkeypatch):
    # 02:00 UTC do dia 3 ainda e 23:00 do dia 2 em Brasilia: o dia do envio e
    # o dia de quem enviou, e "22:30" no texto e o relogio dele.
    _no_dia(monkeypatch, "2026-10-03T02:00:00+00:00")
    (conversa,) = extrair("conversa.txt", PROSA.encode()).conversas
    assert conversa.iniciada_em.isoformat() == "2026-10-02T22:30:00-03:00"
    assert conversa.encerrada_em.isoformat() == "2026-10-02T22:41:00-03:00"


def test_mesma_transcricao_reenviada_outro_dia_nao_duplica(analise, monkeypatch):
    cliente, banco = analise
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    primeiro = _registrar(cliente)["gravacao"]
    _no_dia(monkeypatch, "2026-10-05T15:00:00+00:00")
    segundo = _registrar(cliente, nome="copia renomeada.txt")["gravacao"]
    assert primeiro["ids"] == segundo["ids"]
    assert len(banco.todas()) == 1


def test_reenvio_nao_muda_o_dia_ja_gravado(analise, monkeypatch):
    # A serie de um dia passado nao pode mudar porque alguem reenviou o arquivo.
    cliente, banco = analise
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    _registrar(cliente)
    _no_dia(monkeypatch, "2026-10-05T15:00:00+00:00")
    gravacao = _registrar(cliente)["gravacao"]
    assert gravacao["de"] == gravacao["ate"] == "2026-10-02"
    conversa, _, _ = banco.buscar(gravacao["ids"][0])
    assert conversa.iniciada_em.isoformat() == "2026-10-02T22:30:00-03:00"
    assert conversa.mensagens[-1].enviada_em.isoformat() == "2026-10-02T22:41:00-03:00"


def test_transcricoes_diferentes_no_mesmo_dia_sao_duas_conversas(analise, monkeypatch):
    cliente, banco = analise
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    _registrar(cliente)
    _registrar(cliente, texto=PROSA.replace("demorou demais", "resolveu rapido"))
    assert len(banco.todas()) == 2


def test_resposta_avisa_que_o_dia_e_o_do_envio(analise, monkeypatch):
    cliente, _ = analise
    _no_dia(monkeypatch, "2026-10-02T15:00:00+00:00")
    avisos = " ".join(_registrar(cliente)["avisos"])
    assert "dia" in avisos and "envio" in avisos


def test_id_de_arquivo_com_data_nao_mudou(analise):
    """Quem ja gravou analise com data continua deduplicando contra o que gravou."""
    cliente, banco = analise
    resposta = cliente.post(
        "/analisar/registrar", files={"arquivo": ("conversa.csv", CSV, "text/csv")})
    import hashlib
    import json
    (conversa,) = extrair("conversa.csv", CSV.encode()).conversas
    esperado = "analise:" + hashlib.sha256(json.dumps(
        conversa.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
    ).encode()).hexdigest()[:32]
    assert resposta.json()["gravacao"]["ids"] == [esperado]


def test_relogio_padrao_e_timezone_aware():
    assert arquivos._agora().tzinfo is not None
    assert arquivos._agora().utcoffset() == timezone.utc.utcoffset(None)
