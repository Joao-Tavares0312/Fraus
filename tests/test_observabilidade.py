"""Contrato dos tempos publicos e dos logs seguros."""

import json
import logging
import time

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.motor_preguicoso import ProvedorDeMotor
from fraus.db import Banco
from fraus.motor import Motor


class _Motor(Motor):
    def __init__(self):
        self.regua = lambda: "teste"

    def simular_texto(self, texto):
        time.sleep(0.002)
        return {
            "prob_insatisfeito": 0.1,
            "prob_neutro": 0.2,
            "prob_satisfeito": 0.7,
            "emojis": [],
        }


def _app(tmp_path, motor):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return criar_app(banco, motor, tmp_path)


def test_server_timing_expoe_total_e_banco_sem_vazar_query(tmp_path):
    app = _app(tmp_path, _Motor())
    cliente = TestClient(app)

    resposta = cliente.get("/indicadores")

    assert resposta.status_code == 200
    assert "total;dur=" in resposta.headers["server-timing"]
    assert "consulta_db;dur=" in resposta.headers["server-timing"]
    assert "SELECT" not in resposta.headers["server-timing"]


def test_cold_start_e_inferencia_aparecem_no_log_e_no_header(tmp_path, caplog):
    provedor = ProvedorDeMotor(lambda: _Motor())
    app = _app(tmp_path, provedor)
    cliente = TestClient(app)

    with caplog.at_level(logging.INFO, logger="fraus.requisicao"):
        resposta = cliente.post("/modelo/simular", json={"texto": "bom"})

    assert resposta.status_code == 200
    assert "carga_modelo;dur=" in resposta.headers["server-timing"]
    assert "inferencia;dur=" in resposta.headers["server-timing"]
    evento = json.loads(caplog.records[-1].message)
    assert evento["cold_start"] is True
    assert evento["carga_modelo_ms"] >= 0
    assert evento["inferencia_ms"] > 0
    assert "bom" not in caplog.records[-1].message
