"""O aviso de regua misturada conta tambem troca de MODELO, nao so de lexico.

O `score` e gravado na importacao. Ate 15/09/2026 a unica regua rastreada era a
`lexico_versao`: retreinar o fusor (a espera em log1p) ou mudar a regra da
cortesia deixava o banco inteiro pontuado com a regua anterior, e a tela nao
dizia nada. Agora cada conversa grava a ASSINATURA do motor que a pontuou.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.fusor import NOMES_FEATURES, Fusor
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor

T = datetime(2026, 9, 15, 10, tzinfo=timezone.utc)


def _conversa(id_="c1"):
    return Conversa(id=id_, canal="csv", iniciada_em=T,
                    mensagens=[Mensagem(autor="cliente", texto="o boleto nao chegou", enviada_em=T)])


def _fusor(peso):
    exemplos, rotulos = [], []
    for i in range(20):
        exemplos.append({**{n: 0.0 for n in NOMES_FEATURES}, "texto_prob_satisfeito_media": peso + i / 100})
        rotulos.append(2)
        exemplos.append({**{n: 0.0 for n in NOMES_FEATURES}, "texto_prob_insatisfeito_media": 0.9 - i / 100})
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def test_assinatura_e_estavel_e_muda_com_os_pesos():
    a, b = _fusor(0.5), _fusor(0.9)
    assert a.assinatura() == a.assinatura()
    assert a.assinatura() != b.assinatura()


def test_motor_expoe_a_regua_e_dubles_nao_tem():
    motor = Motor(object(), _fusor(0.5), object(), object())
    assert isinstance(motor.regua(), str) and len(motor.regua()) >= 12
    # A regua cobre tambem a regra da cortesia, que muda nota sem mudar peso.
    import fraus.cortesia as cortesia
    antes = motor.regua()
    original = cortesia.FORMULAS_DE_CORTESIA
    try:
        cortesia.FORMULAS_DE_CORTESIA = original | {"xyz"}
        assert Motor(object(), motor._fusor, object(), object()).regua() != antes
    finally:
        cortesia.FORMULAS_DE_CORTESIA = original


def test_linha_sem_regua_ou_com_regua_antiga_conta_como_defasada(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa("antiga"), 50.0, "neutro", lexico_versao=0)
    banco.salvar(_conversa("outra"), 50.0, "neutro", lexico_versao=0, regua="r-velha")
    banco.salvar(_conversa("em-dia"), 50.0, "neutro", lexico_versao=0, regua="r-nova")
    assert banco.contar_defasadas(regua_vigente="r-nova") == (2, 3)
    # Sem regua vigente (motor duble), so o lexico conta -- como sempre.
    assert banco.contar_defasadas() == (0, 3)


def test_importar_grava_a_regua_do_motor_e_o_aviso_zera(tmp_path):
    class MotorComRegua:
        def pontuar_conversa(self, conversa, curadoria=None):
            return 50.0

        def regua(self):
            return "r-vigente"

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa("de-antes"), 50.0, "neutro", lexico_versao=0)
    cliente = TestClient(criar_app(banco=banco, motor=MotorComRegua(), raiz_importacao=tmp_path))
    corpo = cliente.get("/indicadores").json()
    assert corpo["pontuadas_com_regua_antiga"] == 1
    assert corpo["pontuadas_com_lexico_antigo"] == 0  # o campo antigo nao muda de sentido

    cliente.post("/conversas/repontuar")
    import time
    for _ in range(200):
        if cliente.get("/conversas/repontuar").json()["estado"] != "rodando":
            break
        time.sleep(0.02)
    assert cliente.get("/indicadores").json()["pontuadas_com_regua_antiga"] == 0
