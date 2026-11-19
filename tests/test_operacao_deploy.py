import io
import json
import urllib.error

import pytest

import scripts.smoke_deploy as smoke
from scripts.medir_latencia_deploy import _alvo, resumir
from scripts.smoke_deploy import _url_segura

BASE = "https://api.exemplo.test/"
INDICADORES = {
    "nps": 10.0, "sem_sinal": 2, "total_conversas": 40,
    "feedback_declarado_total": 3, "concordancia_com_feedback": None,
}


def _servidor(monkeypatch, respostas):
    """`urlopen` falso: rota -> (status, corpo). Nada sai da maquina."""
    vistas = []

    def urlopen(requisicao, timeout):
        rota = requisicao.full_url.removeprefix(BASE)
        vistas.append((rota, requisicao.headers.get("Authorization")))
        status, corpo = respostas[rota]
        if status >= 400:
            raise urllib.error.HTTPError(requisicao.full_url, status, "erro", {}, io.BytesIO(b"{}"))
        return io.BytesIO(json.dumps(corpo).encode())

    monkeypatch.setattr(smoke.urllib.request, "urlopen", urlopen)
    return vistas


def test_contrato_completo_passa_com_o_token(monkeypatch):
    vistas = _servidor(monkeypatch, {
        "indicadores": (200, INDICADORES),
        "indicadores/confianca": (200, {"fracao_abstencao": 0.1}),
    })
    resultado = smoke.conferir_contrato(BASE, {"Authorization": "Bearer t"})
    assert resultado == {"contrato": "conferido"}
    assert [rota for rota, _ in vistas] == ["indicadores", "indicadores/confianca"]
    assert all(autorizacao == "Bearer t" for _, autorizacao in vistas)


def test_contrato_sem_chave_do_voto_falha_nomeando_a_chave(monkeypatch):
    sem_voto = {k: v for k, v in INDICADORES.items() if k != "concordancia_com_feedback"}
    _servidor(monkeypatch, {
        "indicadores": (200, sem_voto),
        "indicadores/confianca": (200, {}),
    })
    with pytest.raises(RuntimeError, match="^contrato: indicadores sem a chave concordancia_com_feedback$"):
        smoke.conferir_contrato(BASE, {})


def test_confianca_sem_artefato_falha_com_o_status(monkeypatch):
    _servidor(monkeypatch, {
        "indicadores": (200, INDICADORES),
        "indicadores/confianca": (503, None),
    })
    with pytest.raises(RuntimeError, match="^contrato: indicadores/confianca respondeu 503$"):
        smoke.conferir_contrato(BASE, {})


def test_sem_token_o_contrato_nao_e_conferido_e_a_liveness_basta(monkeypatch, capsys):
    vistas = _servidor(monkeypatch, {
        "saude": (200, {"status": "ok", "motor": "real", "estado_motor": "pronto"}),
        "auth/estado": (200, {}),
    })
    assert smoke.executar(BASE, None, tentativas=1)["status"] == "ok"
    assert [rota for rota, _ in vistas] == ["saude", "auth/estado"]
    assert "contrato nao conferido: FRAUS_SMOKE_TOKEN ausente" in capsys.readouterr().err


def test_falha_de_contrato_nao_imprime_url_nem_token(monkeypatch, capsys):
    _servidor(monkeypatch, {
        "saude": (200, {"status": "ok", "motor": "real", "estado_motor": "pronto"}),
        "auth/estado": (200, {}),
        "indicadores": (401, None),
    })
    monkeypatch.setenv("FRAUS_SMOKE_URL", BASE)
    monkeypatch.setenv("FRAUS_SMOKE_TOKEN", "segredo-do-token")
    assert smoke.main() == 1
    saida = capsys.readouterr()
    assert "contrato: indicadores respondeu 401" in saida.err
    assert "segredo-do-token" not in saida.err + saida.out
    assert "exemplo.test" not in saida.err + saida.out


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
