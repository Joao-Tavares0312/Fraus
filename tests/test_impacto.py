"""Impacto do tema no NPS inferido: diferenca contra o resto, com IC, e nunca 0
no lugar de "nao ha dado"."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.impacto import MOTIVO_N_MINIMO, ROTULO_IMPACTO, impacto_nps
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem
from fraus.operacao import descobrir_temas
from tests.test_api import MotorFalso

T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def test_diferenca_de_nps_com_ic_reprodutivel():
    tema = [20.0] * 30 + [95.0] * 10          # NPS -50
    resto = [95.0] * 30 + [20.0] * 10         # NPS +50
    r = impacto_nps(tema, resto, FAIXAS_NPS)
    assert r["impacto_nps"] == -100.0
    assert r["ic_inferior"] <= -100.0 <= r["ic_superior"]
    assert r == impacto_nps(tema, resto, FAIXAS_NPS)
    assert r["rotulo"] == ROTULO_IMPACTO and r["motivo"] is None


def test_abaixo_do_minimo_e_null_com_motivo_nunca_zero():
    r = impacto_nps([20.0] * 29, [95.0] * 40, FAIXAS_NPS)
    assert r["impacto_nps"] is None and r["ic_inferior"] is None and r["ic_superior"] is None
    assert r["motivo"] == MOTIVO_N_MINIMO and r["n_tema"] == 29 and r["minimo"] == 30


def test_resto_abaixo_do_minimo_tambem_e_null():
    assert impacto_nps([20.0] * 40, [95.0] * 5, FAIXAS_NPS)["impacto_nps"] is None


def test_sem_sinal_fica_fora_e_e_contado():
    r = impacto_nps([None] * 50 + [20.0] * 10, [95.0] * 40, FAIXAS_NPS)
    assert r["n_tema"] == 10 and r["sem_sinal_tema"] == 50 and r["impacto_nps"] is None


def test_faixa_vigente_por_parametro():
    # score 75 -> nota 8: neutro na fabrica, promotor numa faixa 0-6/7-7/8-10.
    faixas = {"detrator": (0, 6), "neutro": (7, 7), "promotor": (8, 10)}
    fab = impacto_nps([75.0] * 30, [20.0] * 30, FAIXAS_NPS)["impacto_nps"]
    outra = impacto_nps([75.0] * 30, [20.0] * 30, faixas)["impacto_nps"]
    assert fab == 100.0 and outra == 200.0


def _conv(i, texto, canal="chat", dia=0):
    t = T0 + timedelta(days=dia)
    return Conversa(id=i, canal=canal, iniciada_em=t, mensagens=[
        Mensagem(autor="cliente", texto=texto, enviada_em=t),
        Mensagem(autor="bot", texto="vou verificar", enviada_em=t + timedelta(seconds=30))])


def test_radar_traz_impacto_por_tema():
    registros = [(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0) for i in range(30)]
    registros += [(_conv(f"b{i}", "senha bloqueada acesso login"), 95.0) for i in range(30)]
    temas = descobrir_temas(registros, FAIXAS_NPS)["temas"]
    cobranca = next(t for t in temas if "a0" in t["conversa_ids"])
    assert cobranca["impacto"]["impacto_nps"] == -200.0
    assert cobranca["impacto"]["n_resto"] == 30


def test_radar_pequeno_tem_impacto_null_e_nao_quebra():
    registros = [(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0) for i in range(3)]
    tema = descobrir_temas(registros, FAIXAS_NPS)["temas"][0]
    assert tema["impacto"]["impacto_nps"] is None and tema["impacto"]["motivo"] == MOTIVO_N_MINIMO


def test_rota_respeita_escopo_e_nao_grava(tmp_path):
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    for i in range(3):
        banco.salvar(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0, "detrator")
        banco.salvar(_conv(f"e{i}", "cobranca duplicada preciso estorno", canal="email"), 20.0, "detrator")
    antes = [(c.model_dump(), s) for c, s in banco.todas()]
    app = criar_app(banco, MotorFalso(), raiz_importacao=tmp_path, chave_mestra="chave-teste-operacao",
                    jwt_segredo="segredo-jwt-de-teste-operacao-123456", codigo_dev="convite-dev-teste")
    cli = TestClient(app)
    headers, ids = {}, {}
    for papel in ("dev", "usuario"):
        cad = {"nome": papel, "email": f"{papel}@empresa.com", "senha": "senha-teste-longa-123"}
        if papel == "dev":
            cad["codigo_dev"] = "convite-dev-teste"
        ids[papel] = cli.post("/auth/registrar", json=cad).json()["id"]
        token = cli.post("/auth/entrar", json={"email": cad["email"], "senha": cad["senha"]}).json()["token"]
        headers[papel] = {"Authorization": "Bearer " + token}
    assert cli.put(f"/operacao/acesso/{ids['usuario']}", headers=headers["dev"],
                   json={"canais": ["chat"]}).status_code == 200
    tema_u = cli.get("/operacao/radar", headers=headers["usuario"]).json()["temas"][0]
    tema_d = cli.get("/operacao/radar", headers=headers["dev"]).json()["temas"][0]
    assert tema_u["impacto"]["n_tema"] + tema_u["impacto"]["n_resto"] == 3
    assert tema_d["impacto"]["n_tema"] + tema_d["impacto"]["n_resto"] == 6
    assert [(c.model_dump(), s) for c, s in banco.todas()] == antes


def test_custo_independe_de_n():
    import time
    tema = ([20.0, 95.0, 70.0] * 500)
    resto = ([95.0, 20.0, 70.0] * 500)
    t0 = time.perf_counter()
    r = impacto_nps(tema, resto, FAIXAS_NPS)
    assert time.perf_counter() - t0 < 0.5
    assert r["n_tema"] == 1500 and r["n_resto"] == 1500
    # O custo e O(reamostras), nao O(reamostras x n): n 10x maior segue rapido.
    t0 = time.perf_counter()
    impacto_nps(tema * 10, resto * 10, FAIXAS_NPS)
    assert time.perf_counter() - t0 < 0.5
