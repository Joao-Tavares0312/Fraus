"""Toda resposta sai com os tres cabecalhos que protegem transcricao.

A API devolve fala de cliente -- dado pessoal. `no-store` impede cache de proxy
e de navegador guardar a transcricao; `nosniff` impede o navegador de
reinterpretar JSON como HTML; `no-referrer` nao vaza a URL (com id de conversa)
para terceiros. Inclusive nas recusas: um 401 ou 413 tambem passa por proxy.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco

ESPERADOS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path, **extra):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path, **extra))


def test_resposta_comum_carrega_os_cabecalhos(tmp_path):
    resposta = _cliente(tmp_path).get("/conversas")
    for nome, valor in ESPERADOS.items():
        assert resposta.headers.get(nome) == valor, nome


def test_recusa_de_credencial_tambem_carrega(tmp_path):
    resposta = _cliente(tmp_path, chave_mestra="m" * 32).get("/conversas")
    assert resposta.status_code == 401
    for nome, valor in ESPERADOS.items():
        assert resposta.headers.get(nome) == valor, nome
