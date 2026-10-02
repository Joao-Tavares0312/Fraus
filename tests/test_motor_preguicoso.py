"""Carga tardia do motor sem duplicar sessoes sob concorrencia."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.motor_preguicoso import ProvedorDeMotor
from fraus.db import Banco
from fraus.motor import Motor


class MotorRealFalsificado(Motor):
    def __init__(self):  # noqa: D107 - evita carregar artefatos neste teste
        self.marcador = "pronto"


def test_provedor_carrega_uma_vez_sob_concorrencia():
    chamadas = 0
    barreira = threading.Barrier(8)

    def construir():
        nonlocal chamadas
        chamadas += 1
        time.sleep(0.05)
        return MotorRealFalsificado()

    provedor = ProvedorDeMotor(construir)
    resultados = []

    def ler():
        barreira.wait()
        resultados.append(provedor.marcador)

    threads = [threading.Thread(target=ler) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert chamadas == 1
    assert resultados == ["pronto"] * 8
    assert provedor.estado == "pronto"


def test_provedor_memoriza_erro_sem_tentar_fallback():
    chamadas = 0

    def falhar():
        nonlocal chamadas
        chamadas += 1
        raise FileNotFoundError("modelo ausente")

    provedor = ProvedorDeMotor(falhar)
    for _ in range(2):
        with pytest.raises(FileNotFoundError, match="modelo ausente"):
            provedor.qualquer_metodo()

    assert chamadas == 1
    assert provedor.estado == "erro"


def test_liveness_aquece_sem_bloquear_e_readiness_espera_a_carga(tmp_path):
    """`/saude` inicia a carga em segundo plano, mas nunca espera por ela.

    Contrato de 30/09/2026: antes, liveness nao disparava nada e cada instancia
    serverless nova ficava `frio` ate a primeira predicao pagar a carga.
    """
    chamadas = 0
    liberar = threading.Event()

    def construir():
        nonlocal chamadas
        chamadas += 1
        liberar.wait(timeout=5)
        return MotorRealFalsificado()

    provedor = ProvedorDeMotor(construir)
    app = criar_app(
        banco=Banco(tmp_path / "fraus.db"),
        motor=provedor,
        raiz_importacao=tmp_path,
    )
    cliente = TestClient(app)

    liveness = cliente.get("/saude")  # volta com a carga ainda presa
    assert liveness.status_code == 200
    assert liveness.json()["motor"] == "real"
    assert liveness.json()["estado_motor"] in {"frio", "carregando"}

    readiness = cliente.get("/saude/prontidao")
    assert readiness.status_code == 503  # ainda carregando

    liberar.set()
    assert provedor.carregar().marcador == "pronto"
    assert cliente.get("/saude/prontidao").status_code == 200
    assert chamadas == 1


def test_aquecer_carrega_em_segundo_plano_e_so_uma_vez():
    chamadas = 0
    liberar = threading.Event()

    def construir():
        nonlocal chamadas
        chamadas += 1
        liberar.wait(timeout=5)
        return MotorRealFalsificado()

    provedor = ProvedorDeMotor(construir)
    assert provedor.estado == "frio"

    assert provedor.aquecer() is True  # volta sem esperar a carga
    assert provedor.aquecer() is False  # ja iniciada: idempotente
    liberar.set()
    provedor.carregar()  # espera a mesma carga terminar

    assert chamadas == 1
    assert provedor.estado == "pronto"
    assert provedor.aquecer() is False


def test_aquecer_com_falha_memoriza_erro_sem_propagar():
    def falhar():
        raise FileNotFoundError("modelo ausente")

    provedor = ProvedorDeMotor(falhar)
    assert provedor.aquecer() is True
    for _ in range(100):
        if provedor.estado == "erro":
            break
        time.sleep(0.02)
    assert provedor.estado == "erro"
    with pytest.raises(FileNotFoundError, match="modelo ausente"):
        provedor.carregar()


def test_saude_dispara_o_aquecimento_da_instancia_fria(tmp_path):
    provedor = ProvedorDeMotor(lambda: MotorRealFalsificado())
    cliente = TestClient(
        criar_app(banco=Banco(tmp_path / "t.db"), motor=provedor, raiz_importacao=tmp_path)
    )
    assert cliente.get("/saude").json()["motor"] == "real"
    for _ in range(100):
        if provedor.estado == "pronto":
            break
        time.sleep(0.02)
    assert provedor.estado == "pronto"


def test_regua_nao_espera_a_carga_dos_modelos():
    """`/indicadores` pergunta a regua em toda abertura da Visao geral.

    Ate 02/10/2026 a pergunta passava pelo `__getattr__` e esperava as tres
    sessoes ONNX: 10 a 12 s numa instancia nova (medido em producao), a
    dashboard desistia e mostrava o agregado de reserva.
    """
    def construir():
        raise AssertionError("a regua nao pode construir o motor")

    chamadas = []

    def regua_barata():
        chamadas.append(1)
        return "abc-123"

    provedor = ProvedorDeMotor(construir, regua=regua_barata)
    assert provedor.regua() == "abc-123"
    assert provedor.regua() == "abc-123"
    assert len(chamadas) == 1
    assert provedor.estado == "frio"


def test_regua_do_motor_carregado_e_a_mesma_regra():
    from fraus.motor import regua_do_fusor

    class FusorComAssinatura:
        def assinatura(self):
            return "pesos"

    class MotorComFusor(Motor):
        def __init__(self):  # noqa: D107
            self._fusor = FusorComAssinatura()

    barata = regua_do_fusor(FusorComAssinatura())
    assert barata is not None and barata.startswith("pesos-")
    assert MotorComFusor().regua() == barata
    provedor = ProvedorDeMotor(MotorComFusor)
    assert provedor.regua() == barata  # sem atalho, cai no motor


def test_fusor_sem_assinatura_nao_tem_regua():
    from fraus.motor import regua_do_fusor

    assert regua_do_fusor(object()) is None


def test_indicadores_respondem_com_o_motor_ainda_frio(tmp_path):
    banco = Banco(tmp_path / "frio.db")
    banco.migrar()

    def construir():
        raise AssertionError("rota de leitura nao carrega modelo")

    provedor = ProvedorDeMotor(construir, regua=lambda: "abc-123")
    cliente = TestClient(criar_app(banco=banco, motor=provedor, raiz_importacao=tmp_path))
    resposta = cliente.get("/indicadores")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["pontuadas_com_regua_antiga"] == 0
    assert provedor.estado == "frio"
