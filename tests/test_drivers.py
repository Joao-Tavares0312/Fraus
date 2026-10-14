from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.explicacao import ROTULO_ASSOCIACAO, drivers
from fraus.fusor import FAMILIAS
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso
from tests.test_motor import _motor


def _linha(categoria, **v):
    base = dict.fromkeys(FAMILIAS, 0.0)
    base.update(v)
    return (categoria, base)


def test_media_por_grupo_e_ic_reprodutivel():
    linhas = [_linha("detrator", tempo=-2.0 - i / 10) for i in range(10)] + \
             [_linha("promotor", texto=1.5 + i / 10) for i in range(10)]
    a, b = drivers(linhas), drivers(linhas)
    assert a == b
    tempo = next(f for f in a if f["familia"] == "tempo")
    assert tempo["detratores"]["media"] == pytest.approx(-2.45)
    lo, hi = tempo["detratores"]["ic"]
    assert lo <= -2.45 <= hi


def test_grupo_vazio_e_none_e_nao_zero():
    r = drivers([_linha("promotor", texto=1.0), _linha("promotor", texto=2.0)])
    texto = next(f for f in r if f["familia"] == "texto")
    assert texto["detratores"] == {"n": 0, "media": None, "ic": None}


def test_um_so_tem_media_e_nao_tem_ic():
    r = drivers([_linha("detrator", texto=-1.0)])
    assert next(f for f in r if f["familia"] == "texto")["detratores"] == {"n": 1, "media": -1.0, "ic": None}


def test_neutro_nao_entra_em_grupo():
    r = drivers([_linha("neutro", texto=9.0)])
    assert all(f["detratores"]["n"] == 0 and f["promotores"]["n"] == 0 for f in r)


BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _c(id_, texto, canal="csv"):
    return Conversa(id=id_, canal=canal, iniciada_em=BASE, mensagens=[
        Mensagem(autor="cliente", texto=texto, enviada_em=BASE),
        Mensagem(autor="bot", texto="ok", enviada_em=BASE + timedelta(seconds=10))])


def test_rota_conta_sem_sinal_e_defasadas_e_rotula(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    mudo = Conversa(id="mudo", canal="csv", iniciada_em=BASE,
                    mensagens=[Mensagem(autor="bot", texto="ola", enviada_em=BASE)])
    banco.salvar_lote([(_c("a", "ruim"), motor.pontuar_conversa(_c("a", "ruim")), None),
                       (mudo, None, None)], lexico_versao=banco.lexico_versao(), regua=motor.regua())
    banco.salvar_lote([(_c("velha", "ruim"), 10.0, None)], lexico_versao=banco.lexico_versao(), regua="outra")
    corpo = TestClient(criar_app(banco=banco, motor=motor)).get("/indicadores/drivers").json()
    assert corpo["sem_sinal"] == 1 and corpo["defasadas"] == 1 and corpo["amostra"] == 1
    assert corpo["rotulo"] == ROTULO_ASSOCIACAO


def test_n_fora_do_teto_e_400_e_duble_e_503(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    real = TestClient(criar_app(banco=banco, motor=_motor()))
    assert real.get("/indicadores/drivers?n=201").status_code == 400
    duble = TestClient(criar_app(banco=banco, motor=MotorFalso()))
    assert duble.get("/indicadores/drivers").status_code == 503


def test_filtro_de_canal(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    banco.salvar_lote([(_c(f"x{i}", "ruim", canal="x"), 20.0, None) for i in range(3)] +
                      [(_c("y", "ruim", canal="y"), 20.0, None)], lexico_versao=banco.lexico_versao(), regua=motor.regua())
    corpo = TestClient(criar_app(banco=banco, motor=motor)).get("/indicadores/drivers?canal=y").json()
    assert corpo["elegiveis"] == 1


def _lote(banco, motor, n):
    banco.salvar_lote([(_c(f"k{i:03d}", "ruim"), 20.0, None) for i in range(n)],
                      lexico_versao=banco.lexico_versao(), regua=motor.regua())


def test_amostra_padrao_e_50_e_n_explicito_vale(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    _lote(banco, motor, 60)
    cli = TestClient(criar_app(banco=banco, motor=motor))
    padrao = cli.get("/indicadores/drivers").json()
    assert padrao["elegiveis"] == 60 and padrao["amostra"] == 50 and padrao["n_pedido"] == 50
    assert cli.get("/indicadores/drivers?n=60").json()["amostra"] == 60


def test_canal_fora_do_escopo_nao_entra_em_elegiveis(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    banco.salvar_lote([(_c("a", "ruim", canal="chat"), 20.0, None),
                       (_c("b", "ruim", canal="email"), 20.0, None)],
                      lexico_versao=banco.lexico_versao(), regua=motor.regua())
    app = criar_app(banco, motor, raiz_importacao=tmp_path, chave_mestra="chave-teste-operacao",
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
    assert cli.get("/indicadores/drivers", headers=headers["usuario"]).json()["elegiveis"] == 1
    assert cli.get("/indicadores/drivers", headers=headers["dev"]).json()["elegiveis"] == 2
