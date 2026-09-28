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


def test_liveness_nao_dispara_carga_e_readiness_distingue_estado(tmp_path):
    chamadas = 0

    def construir():
        nonlocal chamadas
        chamadas += 1
        return MotorRealFalsificado()

    provedor = ProvedorDeMotor(construir)
    app = criar_app(
        banco=Banco(tmp_path / "fraus.db"),
        motor=provedor,
        raiz_importacao=tmp_path,
    )
    cliente = TestClient(app)

    liveness = cliente.get("/saude")
    readiness = cliente.get("/saude/prontidao")

    assert liveness.status_code == 200
    assert liveness.json() == {
        "status": "ok",
        "motor": "real",
        "estado_motor": "frio",
    }
    assert readiness.status_code == 503
    assert readiness.json()["detail"]["estado_motor"] == "frio"
    assert chamadas == 0

    assert provedor.carregar().marcador == "pronto"
    assert cliente.get("/saude/prontidao").status_code == 200
    assert chamadas == 1
