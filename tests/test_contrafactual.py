"""Contrafactual de espera: so o relogio muda, nada e gravado, e fora da faixa recusa.

O fusor da fixture e treinado aqui com tempo que VARIA (o `_motor()` de
`tests/test_motor.py` treina com tempo constante 0, e nesse fusor qualquer
conversa real ja nasce com |z| > 4 e toda requisicao seria recusada). As
features de texto e emocao saem dos mesmos dublês do inferencia, entao sao
constantes no treino e dao z = 0 na rota.
"""

import random
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.fusor import Fusor, montar_features
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor
from fraus.operacao import ajustar_primeira_resposta
from fraus.sinais.tempo import latencias_da_conversa
from tests.test_motor import _EmocaoDuble, _IroniaDuble, _TextoDuble

BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _c(*falas, id_="c1", canal="csv"):
    return Conversa(id=id_, canal=canal, iniciada_em=BASE, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=BASE + timedelta(seconds=s)) for a, t, s in falas])


def test_ajusta_so_a_primeira_resposta_e_preserva_os_intervalos_seguintes():
    c = _c(("cliente", "oi", 0), ("bot", "ola", 600), ("cliente", "e ai", 620), ("bot", "ok", 680))
    alterada = ajustar_primeira_resposta(c, 60)
    assert latencias_da_conversa(alterada) == [60.0, 60.0]


def test_sem_par_cliente_resposta_devolve_none():
    assert ajustar_primeira_resposta(_c(("bot", "ola", 0)), 60) is None


def test_alvo_antes_de_fala_anterior_do_cliente_e_recusado():
    c = _c(("cliente", "oi", 0), ("cliente", "alo", 100), ("bot", "ola", 300))
    with pytest.raises(ValueError):
        ajustar_primeira_resposta(c, 30)


def _fusor_com_tempo_variando() -> Fusor:
    """Treina com conversas sinteticas de espera 5..600 s, sobrepostas entre classes."""
    sorteio = random.Random(20261014)
    texto, emocao = _TextoDuble(), _EmocaoDuble()
    exemplos, rotulos = [], []
    for i in range(60):
        primeira = sorteio.uniform(5, 600)
        segunda = sorteio.uniform(5, 300)
        turnos = sorteio.choice([1, 2, 3])
        falas = [("cliente", "oi", 0), ("bot", "ola", primeira)]
        t = primeira
        for _ in range(turnos - 1):
            t += 10
            falas.append(("cliente", "e ai", t))
            t += segunda
            falas.append(("bot", "ok", t))
        exemplos.append(montar_features(_c(*falas, id_=f"t{i}"), texto, emocao))
        rotulos.append(sorteio.choice([0, 1, 2]))
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def _motor_com_tempo() -> Motor:
    return Motor(_TextoDuble(), _fusor_com_tempo_variando(), _EmocaoDuble(), _IroniaDuble())


def _conversas():
    return [
        _c(("cliente", "oi", 0), ("bot", "ola", 120), ("cliente", "valeu", 130)),
        _c(("bot", "ola", 0), id_="mudo"),
    ]


@pytest.fixture
def api(tmp_path):
    motor = _motor_com_tempo()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    conversas = _conversas()
    banco.salvar_lote([(c, motor.pontuar_conversa(c), None) for c in conversas],
                      lexico_versao=banco.lexico_versao(), regua=motor.regua())
    return TestClient(criar_app(banco=banco, motor=motor)), banco, motor


def test_dentro_da_faixa_responde_antes_e_depois_sem_gravar(api):
    cliente, banco, _ = api
    gravado = banco.buscar("c1")[1]
    r = cliente.post("/conversas/c1/contrafactual", json={"primeira_resposta_s": 60})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["antes"]["score"] == pytest.approx(gravado, abs=1e-9)
    assert corpo["depois"]["score"] != corpo["antes"]["score"]
    assert "sintético" in corpo["metodo"]
    assert banco.buscar("c1")[1] == gravado


def test_espera_maxima_tambem_responde(api):
    cliente, _, _ = api
    r = cliente.post("/conversas/c1/contrafactual", json={"espera_maxima_s": 60})
    assert r.status_code == 200, r.text
    assert r.json()["hipotese"] == {"espera_maxima_s": 60}


def test_exatamente_uma_hipotese(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/c1/contrafactual", json={}).status_code == 422
    assert cliente.post("/conversas/c1/contrafactual",
                        json={"primeira_resposta_s": 60, "espera_maxima_s": 60}).status_code == 422


def test_fora_da_faixa_de_treino_e_recusado(api):
    cliente, _, _ = api
    r = cliente.post("/conversas/c1/contrafactual", json={"primeira_resposta_s": 86400})
    assert r.status_code == 422
    assert "faixa de treino" in r.json()["detail"]


def test_sem_sinal_do_cliente_e_422(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/mudo/contrafactual",
                        json={"espera_maxima_s": 60}).status_code == 422


def test_inexistente_e_404(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/nada/contrafactual",
                        json={"espera_maxima_s": 60}).status_code == 404


def test_regua_antiga_e_409(api):
    cliente, banco, motor = api
    c = _c(("cliente", "oi", 0), ("bot", "ola", 120), id_="velha")
    banco.salvar_lote([(c, motor.pontuar_conversa(c), None)],
                      lexico_versao=banco.lexico_versao(), regua="outra")
    r = cliente.post("/conversas/velha/contrafactual", json={"espera_maxima_s": 60})
    assert r.status_code == 409
    assert "repontue" in r.json()["detail"]


def test_canal_fora_do_escopo_e_404(tmp_path):
    motor = _motor_com_tempo()
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    dentro = _c(("cliente", "oi", 0), ("bot", "ola", 120), id_="a", canal="chat")
    fora = _c(("cliente", "oi", 0), ("bot", "ola", 120), id_="b", canal="email")
    banco.salvar_lote([(c, motor.pontuar_conversa(c), None) for c in (dentro, fora)],
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
    corpo = {"espera_maxima_s": 60}
    assert cli.post("/conversas/a/contrafactual", headers=headers["usuario"], json=corpo).status_code == 200
    assert cli.post("/conversas/b/contrafactual", headers=headers["usuario"], json=corpo).status_code == 404


def test_original_ja_fora_da_faixa_nao_culpa_a_hipotese(api):
    cliente, banco, motor = api
    c = _c(("cliente", "oi", 0), ("bot", "ola", 80000), ("cliente", "alo", 80010), id_="extrema")
    banco.salvar_lote([(c, motor.pontuar_conversa(c), None)],
                      lexico_versao=banco.lexico_versao(), regua=motor.regua())
    r = cliente.post("/conversas/extrema/contrafactual", json={"espera_maxima_s": 60})
    assert r.status_code == 422
    detalhe = r.json()["detail"]
    assert "original ja esta fora da faixa de treino" in detalhe
    assert "hipotese leva" not in detalhe


def test_hipotese_que_sai_da_faixa_diz_que_e_a_hipotese(api):
    cliente, _, _ = api
    r = cliente.post("/conversas/c1/contrafactual", json={"primeira_resposta_s": 86400})
    assert "a hipotese leva a conversa para fora da faixa de treino" in r.json()["detail"]


def test_campo_desconhecido_e_422(api):
    cliente, _, _ = api
    r = cliente.post("/conversas/c1/contrafactual", json={"teto_espera_s": 60})
    assert r.status_code == 422
    r = cliente.post("/conversas/c1/contrafactual",
                     json={"espera_maxima_s": 60, "teto_espera_s": 60})
    assert r.status_code == 422
