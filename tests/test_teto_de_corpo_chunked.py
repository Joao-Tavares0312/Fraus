"""O teto de corpo vale tambem para quem nao declara `Content-Length`.

Corpo em `Transfer-Encoding: chunked` nao tem tamanho para conferir antes de
ler. Rota que le JSON ou `request.body()` (ingestao, webhook) materializava o
corpo inteiro antes de qualquer teto -- o furo que o docstring de
`fraus/api/limites.py` declarava. Agora os bytes sao CONTADOS enquanto chegam.
"""

from fastapi.testclient import TestClient

from fraus.api.limites import TETO_CORPO
from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))


def _pedacos(total, tamanho=64_000):
    enviado = 0
    while enviado < total:
        pedaco = min(tamanho, total - enviado)
        enviado += pedaco
        yield b"x" * pedaco


def test_corpo_chunked_acima_do_teto_e_413(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post(
        "/analisar",
        content=_pedacos(TETO_CORPO + 1),
        headers={"content-type": "application/json"},
    )
    assert resposta.status_code == 413
    assert "limite" in resposta.json()["detail"]


def test_corpo_chunked_pequeno_segue_para_a_rota(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post(
        "/analisar",
        content=_pedacos(10, tamanho=5),
        headers={"content-type": "application/json"},
    )
    # corpo `xxxxxxxxxx` nao e JSON: quem responde e a validacao da rota, nao o teto
    assert resposta.status_code != 413

