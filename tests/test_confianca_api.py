import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.rotas.confianca import wilson
from fraus.conformal import GARANTIA, conjunto, serializar
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso
from tests.test_motor import _motor

BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)
# classe 0 e 1 se sobrepoem em [30, 50]; a 2 comeca em 80; ninguem cobre 61-79.
LIMITES = {0: {"inferior": 0.0, "superior": 50.0, "n": 20},
           1: {"inferior": 30.0, "superior": 60.0, "n": 20},
           2: {"inferior": 80.0, "superior": 100.0, "n": 20}}


def _c(id_, canal="csv", cliente=True):
    msgs = [Mensagem(autor="bot", texto="ola", enviada_em=BASE)]
    if cliente:
        msgs.insert(0, Mensagem(autor="cliente", texto="ruim", enviada_em=BASE))
    return Conversa(id=id_, canal=canal, iniciada_em=BASE, mensagens=msgs)


def _artefato(tmp_path, regua, nome="conformal.json"):
    caminho = tmp_path / nome
    caminho.write_text(json.dumps(serializar(LIMITES, 0.9, regua, 1, "teste")), encoding="utf-8")
    return caminho


def _montar(tmp_path, com_artefato=True):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    banco.salvar_lote(
        [(_c("unico"), 10.0, None), (_c("multiplo"), 40.0, None), (_c("vazio"), 65.0, None),
         (_c("alto"), 90.0, None), (_c("mudo", cliente=False), None, None)],
        lexico_versao=banco.lexico_versao(), regua=motor.regua())
    caminho = _artefato(tmp_path, motor.regua()) if com_artefato else tmp_path / "nao-existe.json"
    return motor, banco, TestClient(criar_app(banco=banco, motor=motor, caminho_conformal=caminho))


def test_detalhe_conjunto_coerente_e_abstencoes(tmp_path):
    _, _, cli = _montar(tmp_path)
    for id_, score in (("unico", 10.0), ("multiplo", 40.0), ("vazio", 65.0), ("alto", 90.0)):
        corpo = cli.get(f"/conversas/{id_}/confianca").json()
        assert corpo["conjunto"] == conjunto(score, LIMITES)
        assert corpo["garantia"] == GARANTIA.format(alvo="90%")
        assert corpo["alvo"] == 0.9
    assert cli.get("/conversas/unico/confianca").json()["abstencao"] is False
    m = cli.get("/conversas/multiplo/confianca").json()
    assert m["abstencao"] is True and m["criterios"][0] == "conjunto_multiplo"
    assert m["rotulos_conjunto"] == ["insatisfeito", "neutro"]
    v = cli.get("/conversas/vazio/confianca").json()
    assert v["abstencao"] is True and v["criterios"][0] == "conjunto_vazio" and v["conjunto"] == []


def test_sem_score_e_200_com_nulos(tmp_path):
    _, _, cli = _montar(tmp_path)
    r = cli.get("/conversas/mudo/confianca")
    corpo = r.json()
    assert r.status_code == 200
    assert corpo["conjunto"] is None and corpo["abstencao"] is None
    assert corpo["rotulos_conjunto"] is None and corpo["score"] is None


def test_artefato_ausente_503_e_conversas_segue_200(tmp_path):
    _, _, cli = _montar(tmp_path, com_artefato=False)
    assert cli.get("/conversas/unico/confianca").status_code == 503
    assert cli.get("/indicadores/confianca").status_code == 503
    assert cli.get("/conversas").status_code == 200
    assert cli.get("/conversas/unico").status_code == 200


def test_artefato_de_outra_regua_ou_malformado_e_503(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    for caminho in (_artefato(tmp_path, "outra"), tmp_path / "ruim.json"):
        if caminho.name == "ruim.json":
            caminho.write_text("{nao e json", encoding="utf-8")
        cli = TestClient(criar_app(banco=banco, motor=motor, caminho_conformal=caminho))
        assert cli.get("/indicadores/confianca").status_code == 503


def test_duble_sem_regua_503_mesmo_com_artefato_sem_regua(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    caminho = tmp_path / "sem-regua.json"
    caminho.write_text(json.dumps(serializar(LIMITES, 0.9, None, 1, "t")), encoding="utf-8")
    cli = TestClient(criar_app(banco=banco, motor=MotorFalso(), caminho_conformal=caminho))
    r = cli.get("/indicadores/confianca")
    assert r.status_code == 503 and "motor real" in r.json()["detail"]
    assert cli.get("/conversas/x/confianca").status_code == 503


def test_conversa_de_outra_regua_409_no_detalhe_e_defasada_no_agregado(tmp_path):
    _, banco, cli = _montar(tmp_path)
    banco.salvar_lote([(_c("velha"), 10.0, None)], lexico_versao=banco.lexico_versao(), regua="outra")
    assert cli.get("/conversas/velha/confianca").status_code == 409
    corpo = cli.get("/indicadores/confianca").json()
    assert corpo["defasadas"] == 1 and corpo["avaliadas"] == 4 and corpo["com_sinal"] == 5


def test_agregado_conta_criterios_e_wilson(tmp_path):
    _, _, cli = _montar(tmp_path)
    corpo = cli.get("/indicadores/confianca").json()
    assert corpo["avaliadas"] == 4 and corpo["abstencoes"] == 2
    assert corpo["por_criterio"] == {"conjunto_vazio": 1, "conjunto_multiplo": 1}
    assert corpo["tamanho_conjunto"] == {"0": 1, "1": 2, "2": 1, "3": 0}
    assert corpo["fracao_abstencao"] == 0.5
    lo, hi = corpo["ic_fracao"]
    assert lo < 0.5 < hi and (lo, hi) == wilson(2, 4)
    assert "sem passagem de modelo" in corpo["metodo"]


def test_agregado_sem_avaliadas_e_nulo(tmp_path):
    _, _, cli = _montar(tmp_path)
    corpo = cli.get("/indicadores/confianca?canal=inexistente").json()
    assert corpo["avaliadas"] == 0 and corpo["fracao_abstencao"] is None and corpo["ic_fracao"] is None


def test_wilson_valores_conhecidos():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and 0.25 < hi < 0.32
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and 0.68 < lo < 0.75


def test_nps_e_score_identicos_com_e_sem_artefato(tmp_path):
    motor, banco, cli = _montar(tmp_path)
    sem = TestClient(criar_app(banco=banco, motor=motor, caminho_conformal=tmp_path / "nao.json"))
    antes = banco.buscar("multiplo")[1]
    com_ind = cli.get("/indicadores").json()
    cli.get("/conversas/multiplo/confianca")
    cli.get("/indicadores/confianca")
    assert sem.get("/indicadores").json() == com_ind
    assert cli.get("/indicadores").json() == com_ind
    assert banco.buscar("multiplo")[1] == antes == 40.0


def test_escopo(tmp_path):
    motor, banco, _ = _montar(tmp_path)
    banco.salvar_lote([(_c("a", canal="chat"), 10.0, None), (_c("b", canal="email"), 40.0, None)],
                      lexico_versao=banco.lexico_versao(), regua=motor.regua())
    app = criar_app(banco, motor, raiz_importacao=tmp_path, chave_mestra="chave-teste-operacao",
                    jwt_segredo="segredo-jwt-de-teste-operacao-123456", codigo_dev="convite-dev-teste",
                    caminho_conformal=_artefato(tmp_path, motor.regua(), "e.json"))
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
    u = headers["usuario"]
    assert cli.get("/conversas/a/confianca", headers=u).status_code == 200
    assert cli.get("/conversas/b/confianca", headers=u).status_code == 404
    assert cli.get("/indicadores/confianca", headers=u).json()["avaliadas"] == 1
    assert cli.get("/indicadores/confianca", headers=headers["dev"]).json()["avaliadas"] == 6


# ---- rodada final do E2 ----

def _resumo_deriva(*dentro):
    return {"features": [{"nome": f"f{i}", "dentro_da_faixa": d} for i, d in enumerate(dentro)]}


def test_deriva_fora_da_faixa_entra_nos_criterios(tmp_path, monkeypatch):
    motor, _, cli = _montar(tmp_path)
    monkeypatch.setattr(motor, "deriva_da_amostra", lambda *a, **k: _resumo_deriva(True, False))
    corpo = cli.get("/conversas/unico/confianca").json()
    assert "deriva" in corpo["criterios"]
    assert corpo["features_fora_da_faixa"] == ["f1"]
    assert corpo["abstencao"] is True
    assert corpo["deriva_nao_avaliada"] is False


def test_deriva_toda_dentro_nao_abstem(tmp_path, monkeypatch):
    motor, _, cli = _montar(tmp_path)
    monkeypatch.setattr(motor, "deriva_da_amostra", lambda *a, **k: _resumo_deriva(True, True))
    corpo = cli.get("/conversas/unico/confianca").json()
    assert "deriva" not in corpo["criterios"]
    assert corpo["features_fora_da_faixa"] == []
    assert corpo["abstencao"] is False and corpo["deriva_nao_avaliada"] is False


def test_conversa_longa_pula_a_deriva_sem_400(tmp_path, monkeypatch):
    motor, banco, cli = _montar(tmp_path)
    chamadas = []
    monkeypatch.setattr(motor, "deriva_da_amostra", lambda *a, **k: chamadas.append(1))
    longa = Conversa(id="longa", canal="csv", iniciada_em=BASE, mensagens=[
        Mensagem(autor="cliente", texto="ruim", enviada_em=BASE + timedelta(seconds=i))
        for i in range(41)])
    banco.salvar_lote([(longa, 10.0, None)], lexico_versao=banco.lexico_versao(), regua=motor.regua())
    r = cli.get("/conversas/longa/confianca")
    assert r.status_code == 200
    corpo = r.json()
    assert chamadas == []
    assert corpo["features_fora_da_faixa"] is None
    assert corpo["deriva_nao_avaliada"] is True
    assert "40 mensagens do cliente" in corpo["motivo"]
    assert "deriva" not in corpo["criterios"]
    assert corpo["conjunto"] == conjunto(10.0, LIMITES)


def test_503_nao_vaza_caminho_nem_repr(tmp_path):
    for com_artefato in (False, True):
        motor = _motor()
        banco = Banco(tmp_path / f"f{com_artefato}.db")
        banco.migrar()
        caminho = tmp_path / "ruim.json"
        if com_artefato:
            caminho.write_text("{nao e json", encoding="utf-8")
        cli = TestClient(criar_app(banco=banco, motor=motor, caminho_conformal=caminho))
        detalhe = cli.get("/indicadores/confianca").json()["detail"]
        assert "/" not in detalhe and "Error(" not in detalhe and "conformal" in detalhe
