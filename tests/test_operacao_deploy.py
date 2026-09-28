import json

import pytest

from scripts.medir_latencia_deploy import _alvo, resumir
from scripts.smoke_deploy import _url_segura


@pytest.mark.parametrize("funcao", (_url_segura, lambda url: _alvo(url)))
def test_ferramentas_recusam_url_com_segredo(funcao):
    with pytest.raises(ValueError, match="credencial"):
        funcao("https://usuario:segredo@api.exemplo.test/saude")


def test_resumo_de_latencia_nao_expoe_host_ou_url():
    amostras = [{
        "status": 200,
        "dns_ms": 1.0,
        "conexao_tls_ms": 2.0,
        "ttfb_ms": 30.0,
        "transferencia_ms": 3.0,
        "server_timing": "total;dur=20, consulta_db;dur=4",
        "regiao": {"x-vercel-id": "gru1::abc"},
    }]
    resultado = resumir(amostras, "https://api-secreta.exemplo.test/saude")
    serializado = json.dumps(resultado)
    assert "api-secreta" not in serializado
    assert resultado["mediana_ms"]["ttfb_ms"] == 30.0
    assert resultado["regioes"] == [{"x-vercel-id": "gru1::abc"}]
