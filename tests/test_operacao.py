"""Operacao real de codigo, isolamento, concorrencia e hipoteses explicitas."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem
from fraus.operacao import descobrir_temas, limitar_esperas, simular_escala
from tests.test_motor import _motor, _fusor_treinado
from tests.test_api import CSV

# 10h no relogio do PRODUTO: a escala le a hora de chegada no fuso do produto
# (fraus/fuso.py), nao no offset em que a conversa foi gravada.
BASE = datetime(2026, 9, 15, 10, tzinfo=timezone(timedelta(hours=-3)))


def conversa(i="c1", canal="chat", texto="cobranca duplicada preciso estorno", dia=0, humana=True):
    t = BASE + timedelta(days=dia)
    return Conversa(id=i, canal=canal, iniciada_em=t, escalou_para_humano=humana, mensagens=[
        Mensagem(autor="cliente", texto=texto, enviada_em=t),
        Mensagem(autor="humano" if humana else "bot", texto="vou verificar", enviada_em=t + timedelta(seconds=300))])


@pytest.fixture
def ambiente(tmp_path):
    banco = Banco(tmp_path / "operacao.db")
    banco.migrar()
    banco.salvar(conversa(), 25, "detrator")
    banco.salvar(conversa("c2", "email", dia=1), 90, "promotor")
    app = criar_app(banco, _motor(), raiz_importacao=tmp_path, chave_mestra="chave-teste-operacao", jwt_segredo="segredo-jwt-de-teste-operacao-123456", codigo_dev="convite-dev-teste")
    cliente = TestClient(app)
    usuarios = {}
    headers = {}
    for papel in ("dev", "usuario"):
        cadastro = {"nome": papel, "email": f"{papel}@empresa.com", "senha": "senha-teste-longa-123"}
        if papel == "dev":
            cadastro["codigo_dev"] = "convite-dev-teste"
        r = cliente.post("/auth/registrar", json=cadastro)
        assert r.status_code == 201, r.text
        usuarios[papel] = r.json()["id"]
        r = cliente.post("/auth/entrar", json={"email": cadastro["email"], "senha": cadastro["senha"]})
        assert r.status_code == 200, r.text
        headers[papel] = {"Authorization": "Bearer " + r.json()["token"]}
    return cliente, banco, headers, usuarios


def test_radar_alerta_taxas_e_evidencias():
    registros = [(conversa(f"r{i}", dia=-i), 25) for i in range(4)]
    registros += [(conversa(f"p{i}", texto="senha bloqueada acesso login", dia=-7-i), 80) for i in range(5)]
    r = descobrir_temas(registros, FAIXAS_NPS)
    tema = next(t for t in r["temas"] if "r0" in t["conversa_ids"])
    assert tema["emergente"] and tema["taxa_atual"] == 1 and tema["taxa_anterior"] == 0
    assert set(tema["conversa_ids"]) == {"r0", "r1", "r2", "r3"}
    assert tema["intervalo"]["nps"] is None


def test_radar_vazio_sem_tema_nao_inventa_numero():
    assert descobrir_temas([], FAIXAS_NPS)["janela"] is None
    assert descobrir_temas([(conversa(texto="obrigado"), None)], FAIXAS_NPS)["temas"] == []


def test_escala_capacidade_canais_e_fim_turno():
    registros = [(conversa(str(i)), 25) for i in range(3)]
    a = simular_escala(registros, [{"inicio": 10, "fim": 11, "pessoas": 1, "canais": ["chat"]}], 1200, 30)
    b = simular_escala(registros, [{"inicio": 10, "fim": 11, "pessoas": 3, "canais": ["chat"]}], 1200, 30)
    assert a["espera_mediana_s"] == 1200 and b["espera_mediana_s"] == 0
    assert b["custo"] == 90 and a["custo"] == 30
    c = simular_escala(registros, [{"inicio": 10, "fim": 11, "pessoas": 1, "canais": ["email"]}], 1200, 30)
    assert c["pendentes"] == 3 and c["espera_mediana_s"] is None
    d = simular_escala(registros, [{"inicio": 10, "fim": 11, "pessoas": 1, "canais": []}], 1800, 30)
    assert d["atendidas"] == 2 and d["pendentes"] == 1


def test_cenario_espera_preserva_ordem_original_e_mensagens_seguidas():
    c = conversa()
    c.mensagens.insert(1, Mensagem(autor="cliente", texto="alguem ai", enviada_em=BASE + timedelta(seconds=120)))
    antes = c.model_dump()
    nova = limitar_esperas(c, 30)
    assert nova.mensagens[-1].enviada_em == BASE + timedelta(seconds=120)
    assert c.model_dump() == antes
    assert sorted(m.enviada_em for m in nova.mensagens) == [m.enviada_em for m in nova.mensagens]


def test_replay_nao_le_falas_futuras_e_comparacao_mesmo_vetor():
    motor = _motor()
    c = conversa()
    prefixo = c.model_copy(update={"mensagens": c.mensagens[:1], "escalou_para_humano": False})
    a = motor.scores_do_replay(c)
    assert a[0] == motor.scores_do_replay(prefixo)[0]
    iguais = motor.comparar_fusor(c, _fusor_treinado())
    assert iguais["atual"] == iguais["candidato"]


def test_equipes_jornadas_problemas_auditoria(ambiente):
    cli, banco, h, u = ambiente
    equipe = {"nome": "Suporte", "membros": [u["usuario"]], "competencias": ["estorno"], "canais": ["chat"]}
    r = cli.post("/operacao/equipes", headers=h["dev"], json=equipe)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    equipe["membros"] = r.json()["membros"]
    assert cli.put(f"/operacao/equipes/{eid}", headers=h["dev"], json={**equipe, "nome": "Suporte financeiro"}).status_code == 200
    assert cli.get("/operacao/equipes", headers=h["usuario"]).json()["equipes"][0]["nome"] == "Suporte financeiro"
    assert cli.post("/operacao/equipes", headers=h["usuario"], json=equipe).status_code == 403
    r = cli.post("/operacao/jornadas", headers=h["usuario"], json={"referencia": "anonimo_123", "conversa_ids": ["c1", "c2"]})
    assert r.status_code == 200, r.text
    assert "anonimo_123" not in str(banco.documentos("jornada"))
    j = cli.get("/operacao/jornadas", headers=h["usuario"]).json()["jornadas"][0]
    assert j["recontatos"] == 1 and j["resolucao_declarada"] is None
    pedido = {"titulo": "Corrigir cobrança", "conversa_ids": ["c1", "c2"], "prazo": "2026-10-10", "termos": ["cobranca"], "equipe_id": eid}
    r = cli.post("/operacao/problemas", headers=h["dev"], json=pedido)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r = cli.patch(f"/operacao/problemas/{pid}", headers=h["dev"], json={"estado": "resolvido", "acao": "Corrigida a duplicação"})
    assert r.status_code == 200 and r.json()["medicao"]["delta_nps"] is None
    momento = r.json()["resolvido_em"]
    r = cli.patch(f"/operacao/problemas/{pid}", headers=h["dev"], json={"estado": "resolvido", "acao": "Verificada a correção"})
    assert r.json()["resolvido_em"] == momento and len(r.json()["acoes"]) == 2
    assert banco.auditoria()["integra"]


def test_escopo_isola_leituras_escritas_e_exportacao(ambiente):
    cli, banco, h, u = ambiente
    rota = f"/operacao/acesso/{u['usuario']}"
    assert cli.put(rota, headers=h["dev"], json={"canais": ["chat"]}).status_code == 200
    assert cli.get("/operacao/acesso", headers=h["usuario"]).status_code == 403
    assert [c["id"] for c in cli.get("/conversas", headers=h["usuario"]).json()] == ["c1"]
    assert cli.get("/conversas/c2", headers=h["usuario"]).status_code == 404
    assert cli.get("/indicadores", headers=h["usuario"]).json()["total_conversas"] == 1
    grafo = cli.get("/grafo", headers=h["usuario"])
    assert grafo.status_code == 200 and "conversa:c2" not in grafo.text
    assert cli.get("/operacao/replay/c2", headers=h["usuario"]).status_code == 404
    assert cli.post("/operacao/jornadas", headers=h["usuario"], json={"referencia": "anonimo_123", "conversa_ids": ["c1", "c2"]}).status_code == 404
    assert banco.documentos("jornada") == []
    assert cli.post("/analisar/registrar", headers=h["usuario"], files={"arquivo": ("c.csv", CSV, "text/csv")}).status_code == 403
    assert len(banco.todas()) == 2
    assert cli.get("/operacao/exportar", headers=h["usuario"]).status_code == 403
    assert cli.post("/operacao/exportacao/autorizar", headers=h["usuario"]).status_code == 403
    cli.put(rota, headers=h["dev"], json={"canais": ["chat"], "exportar_minutos": 10})
    r = cli.get("/operacao/exportar", headers=h["usuario"])
    assert r.status_code == 200 and "c1" in r.text and "c2" not in r.text
    assert cli.post("/operacao/exportacao/autorizar", headers=h["usuario"]).status_code == 200
    banco.guardar_documento("permissao", str(u["usuario"]), {"canais": ["chat"], "exporta_ate": "2020-01-01T00:00:00+00:00"})
    assert cli.post("/operacao/exportacao/autorizar", headers=h["usuario"]).status_code == 403


def test_revogacao_imediata_e_novo_login(ambiente):
    cli, banco, h, u = ambiente
    assert cli.post(f"/operacao/acesso/{u['usuario']}/revogar-sessoes", headers=h["dev"]).status_code == 200
    assert cli.get("/conversas", headers=h["usuario"]).status_code == 401
    assert cli.get("/auth/eu", headers=h["usuario"]).status_code == 401
    r = cli.post("/auth/entrar", json={"email": "usuario@empresa.com", "senha": "senha-teste-longa-123"})
    assert r.status_code == 200
    assert cli.get("/conversas", headers={"Authorization": "Bearer " + r.json()["token"]}).status_code == 200


def test_replay_cenario_e_comparacao_nao_gravam(ambiente, tmp_path, monkeypatch):
    cli, banco, h, u = ambiente
    antes = [(c.model_dump(), s) for c, s in banco.todas()]
    r = cli.get("/operacao/replay/c1", headers=h["usuario"])
    assert r.status_code == 200 and len(r.json()["pontos"]) == 2
    r = cli.post("/operacao/laboratorio/cenario", headers=h["usuario"], json={"conversa_id": "c1", "espera_maxima_s": 30})
    assert r.status_code == 200, r.text
    assert r.json()["mensagens_cenario"][-1]["enviada_em"] == (BASE + timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
    assert cli.post("/operacao/laboratorio/cenario", headers=h["usuario"], json={"conversa_id": "c1", "ocultar_mensagem": 1}).status_code == 400
    monkeypatch.delenv("FRAUS_FUSOR_CANDIDATO", raising=False)
    assert cli.post("/operacao/laboratorio/comparar", headers=h["usuario"], json={"conversa_ids": ["c1"]}).status_code == 503
    caminho = tmp_path / "candidato.joblib"
    _fusor_treinado().salvar(caminho)
    monkeypatch.setenv("FRAUS_FUSOR_CANDIDATO", str(caminho))
    r = cli.post("/operacao/laboratorio/comparar", headers=h["usuario"], json={"conversa_ids": ["c1", "c2"]})
    assert r.status_code == 200 and all(not x["mudou_categoria"] for x in r.json()["resultados"])
    assert [(c.model_dump(), s) for c, s in banco.todas()] == antes


def test_documento_concorrente_nao_perde_acoes_e_auditoria_detecta_alteracao(tmp_path):
    banco = Banco(tmp_path / "acoes.db")
    banco.migrar()
    banco.guardar_documento("teste", "1", {"acoes": []})
    def agir(i):
        def alterar(p):
            p["acoes"].append(i)
            return p
        banco.alterar_documento("teste", "1", alterar)
        banco.auditar("teste", "acao", str(i))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(agir, range(12)))
    assert sorted(banco.documento("teste", "1")["acoes"]) == list(range(12))
    assert banco.auditoria()["integra"] and banco.auditoria()["total"] == 12
    with banco._conectar() as conexao:
        conexao.execute("UPDATE auditoria_eventos SET payload = ? WHERE id = 1", ('{"ator":"alterado"}',))
    assert not banco.auditoria()["integra"]


def test_laboratorio_recusa_fusor_candidato_incompativel_com_503(ambiente, tmp_path, monkeypatch):
    """Auditoria de 13/10/2026: `FusorIncompativelError` herda de RuntimeError,
    e a rota so capturava FileNotFoundError/ValueError -- o candidato fora do
    contrato de 39 features virava 500 em vez do 503 que explica o motivo."""
    import joblib

    from fraus.fusor import NOMES_FEATURES, Fusor

    cli, _banco, h, _u = ambiente
    nomes = NOMES_FEATURES[:-2]
    velho = Fusor()
    velho._pipeline.fit([[0.0] * len(nomes)] * 4, [0, 1, 2, 1])
    caminho = tmp_path / "candidato_velho.joblib"
    joblib.dump(velho._pipeline, caminho)
    monkeypatch.setenv("FRAUS_FUSOR_CANDIDATO", str(caminho))
    r = cli.post("/operacao/laboratorio/comparar", headers=h["usuario"], json={"conversa_ids": ["c1"]})
    assert r.status_code == 503, r.text
    assert "incompativel" in r.json()["detail"]


def test_jornada_ordena_contatos_pelo_instante_e_nao_pelo_texto_do_offset(ambiente):
    """Auditoria de 13/10/2026: os contatos eram ordenados pela string ISO, e
    10:00-03:00 (13h UTC, o mais recente) vinha antes de 12:00+00:00 -- a
    resolucao declarada saia do contato errado."""
    cli, banco, h, _u = ambiente
    recente = conversa("jA").model_copy(update={
        "iniciada_em": datetime(2026, 9, 20, 10, tzinfo=timezone(timedelta(hours=-3))),
        "feedback_declarado": -1})
    antiga = conversa("jB").model_copy(update={
        "iniciada_em": datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
        "feedback_declarado": 1})
    banco.salvar(recente, 30, "detrator")
    banco.salvar(antiga, 90, "promotor")
    r = cli.post("/operacao/jornadas", headers=h["dev"], json={"referencia": "cliente-123", "conversa_ids": ["jA", "jB"]})
    assert r.status_code in (200, 201), r.text
    referencia = r.json()["referencia"]

    jornada = next(j for j in cli.get("/operacao/jornadas", headers=h["dev"]).json()["jornadas"]
                   if j["referencia"] == referencia)

    assert [c["id"] for c in jornada["contatos"]] == ["jB", "jA"]
    assert jornada["resolucao_declarada"] is False


def test_exportacao_do_servidor_leva_contestada_e_sai_em_ordem(ambiente):
    """Auditoria de 13/10/2026: a API (/conversas) e o CSV da tela marcam a
    contestacao; o CSV de /operacao/exportar nao, e saia sem ordem."""
    import csv as _csv
    import io as _io

    cli, banco, h, _u = ambiente
    elogio = conversa("z-elogio", texto="perfeito, adorei", dia=-1)  # humano respondeu em 300 s
    banco.salvar(elogio, 99, "promotor")

    r = cli.get("/operacao/exportar", headers=h["dev"])
    assert r.status_code == 200, r.text
    linhas = list(_csv.DictReader(_io.StringIO(r.text)))

    assert [linha["id"] for linha in linhas] == ["z-elogio", "c1", "c2"]
    marca = {linha["id"]: linha["contestada"] for linha in linhas}
    assert marca == {"z-elogio": "sim", "c1": "", "c2": ""}


def test_exportacao_do_servidor_neutraliza_tab_e_retorno_no_inicio():
    from fraus.api.rotas.operacao import celula_segura

    assert celula_segura("\t=1+1") == "'\t=1+1"
    assert celula_segura("\r=1") == "'\r=1"
    assert celula_segura("chat") == "chat"


def test_auditoria_declara_que_nao_detecta_remocao_do_fim(tmp_path):
    """Auditoria de 13/10/2026: sem ancora fora da tabela, apagar os eventos
    MAIS RECENTES mantem `integra: True`. O metodo dizia so que nao protege
    contra "reescrita integral" -- prometia mais do que a cadeia entrega."""
    banco = Banco(tmp_path / "aud.db")
    banco.migrar()
    for i in range(3):
        banco.auditar("dev", "acao", str(i))
    with banco._conectar() as conexao:
        conexao.execute("DELETE FROM auditoria_eventos WHERE id = (SELECT MAX(id) FROM auditoria_eventos)")

    relatorio = banco.auditoria()

    assert relatorio["integra"] is True  # o limite: a remocao do fim passa
    assert "mais recentes" in relatorio["metodo"]
