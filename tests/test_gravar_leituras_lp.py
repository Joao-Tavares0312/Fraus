import pytest

from scripts.gravar_leituras_lp import IDS, LeituraRecusada, montar_conjunto


def _analise(score, nota=None, categoria=None, motivo=None):
    return {
        "analises": [
            {
                "conversa": {"id": "x", "mensagens": [{"autor": "cliente", "texto": "oi"}]},
                "score": score,
                "nota": nota,
                "categoria": categoria,
                "motivo_sem_sinal": motivo,
                "mensagens": [{"indice": 0, "prob_insatisfeito": 0.7, "prob_neutro": 0.2, "prob_satisfeito": 0.1}],
                "contribuicoes": [{"feature": "texto_prob_media", "valor": -0.4}],
                "importancias": [],
                "vocabulario": {"destaque": ["cobranca"], "referencia": 812},
            }
        ]
    }


def _respostas():
    respostas = {i: _analise(30.0, 3, "detrator") for i in IDS}
    respostas["promotor"] = _analise(92.0, 9, "promotor")
    respostas["sem-sinal"] = _analise(None, motivo="sem_fala_do_cliente")
    return respostas


def _montar(respostas):
    return montar_conjunto(
        respostas,
        modelo="fusor-2026-09-15",
        agora="2026-10-09T13:00:00+00:00",
        api="https://exemplo.invalid",
        shas={i: "ab" * 32 for i in IDS},
    )


def test_guarda_so_o_que_a_lp_mostra_e_descarta_o_vocabulario():
    conjunto = _montar(_respostas())
    leitura = conjunto["leituras"][0]
    # O vocabulario compara com contagens do banco de producao: nao pertence a pagina publica.
    assert "vocabulario" not in leitura
    assert "importancias" not in leitura
    assert set(leitura) == {
        "id", "score", "nota", "categoria", "motivo_sem_sinal",
        "mensagens", "contribuicoes", "conversa", "sha256",
    }


def test_carrega_a_procedencia_que_a_etiqueta_da_tela_escreve():
    conjunto = _montar(_respostas())
    assert conjunto["procedencia"] == {
        "gravado_em": "2026-10-09T13:00:00+00:00",
        "api": "https://exemplo.invalid",
        "modelo": "fusor-2026-09-15",
    }
    assert [l["id"] for l in conjunto["leituras"]] == list(IDS)


def test_recusa_quando_falta_uma_leitura():
    respostas = _respostas()
    del respostas["ironia"]
    with pytest.raises(LeituraRecusada, match="ironia"):
        _montar(respostas)


def test_recusa_sem_sinal_que_voltou_com_nota():
    respostas = _respostas()
    respostas["sem-sinal"] = _analise(40.0, 4, "detrator")
    with pytest.raises(LeituraRecusada, match="sem-sinal"):
        _montar(respostas)


def test_recusa_leitura_com_cliente_que_voltou_sem_nota():
    respostas = _respostas()
    respostas["espera"] = _analise(None)
    with pytest.raises(LeituraRecusada, match="espera"):
        _montar(respostas)


def test_identidade_do_modelo_e_a_impressao_digital_dos_pesos_servidos():
    from scripts.gravar_leituras_lp import identidade_do_modelo

    ficha = {"importancias": [{"feature": "texto_prob_media", "peso": 1.2}], "metricas": None}
    mesma = {"metricas": None, "importancias": [{"peso": 1.2, "feature": "texto_prob_media"}]}
    outra = {"importancias": [{"feature": "texto_prob_media", "peso": 1.3}]}
    assert identidade_do_modelo(ficha).startswith("fusor:")
    assert identidade_do_modelo(ficha) == identidade_do_modelo(mesma)
    assert identidade_do_modelo(ficha) != identidade_do_modelo(outra)


def test_identidade_recusa_ficha_sem_pesos():
    from scripts.gravar_leituras_lp import identidade_do_modelo

    with pytest.raises(LeituraRecusada):
        identidade_do_modelo({"importancias": []})


def test_recusa_resposta_sem_uma_chave_que_a_lp_mostra():
    respostas = _respostas()
    del respostas["ironia"]["analises"][0]["mensagens"]
    with pytest.raises(LeituraRecusada, match="ironia"):
        _montar(respostas)


def test_sem_sinal_exige_o_motivo_do_servidor_e_nao_qualquer_none():
    # Score nulo por transcricao sem horario (tem_tempo=False) nao e "sem fala do cliente".
    respostas = _respostas()
    respostas["sem-sinal"] = _analise(None, motivo=None)
    with pytest.raises(LeituraRecusada, match="sem-sinal"):
        _montar(respostas)


def test_recusa_api_sem_https_para_nao_mandar_o_token_em_claro():
    from scripts.gravar_leituras_lp import exigir_https

    with pytest.raises(LeituraRecusada):
        exigir_https("http://fraus-api.exemplo")
    assert exigir_https("https://fraus-api.exemplo/") == "https://fraus-api.exemplo"


def test_nao_segue_redirect_com_o_token():
    import urllib.request

    from scripts.gravar_leituras_lp import SemRedirect

    with pytest.raises(LeituraRecusada):
        SemRedirect().redirect_request(urllib.request.Request("https://a"), None, 302, "Found", {}, "https://b")
